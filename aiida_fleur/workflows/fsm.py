###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
"""
Workchain for fixed spin moment (FSM) calculations with FLEUR.

Runs a series of SCF calculations with different fixed total spin moments
to map out the free energy vs. magnetisation curve.
"""
from __future__ import annotations

import copy

from lxml import etree

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import WorkChain, ToContext, calcfunction as cf

from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_inpgen, test_and_get_codenode
from aiida_fleur.workflows.scf import FleurScfWorkChain


# d-block and f-block atomic number ranges used to decide which l-channel gets LDA+U
_D_BLOCK_Z = set(range(21, 31)) | set(range(39, 49)) | set(range(72, 81)) | set(range(104, 113))
_F_BLOCK_Z = set(range(57, 72)) | set(range(89, 104))


class FleurFsmWorkChain(WorkChain):
    """
    Workchain for fixed spin moment (FSM) calculations.

    Starting from a crystal structure it:
      1. Runs inpgen to generate the FLEUR input with spin polarisation enabled
         (jspins=2) and zero initial magnetic moments (bmu=0).
      2. Creates one modified inp.xml per requested fixed-moment value by setting
         the ``fixed_moment`` attribute and adding zero-cost LDA+U (U=J=0) for
         every d- and f-shell species so that density matrices are produced.
      3. Submits the resulting SCF calculations in parallel.
      4. Collects free energies, both spin Fermi energies, density matrices and
         SCF UUIDs into the ``output_fsm_wc_para`` output node.

    Inputs
    ------
    scf.*         : exposed inputs of FleurScfWorkChain
                    Required: scf.structure, scf.inpgen, scf.fleur
                    Optional: scf.calc_parameters (kpt grid etc.), scf.wf_parameters,
                              scf.settings, scf.options
    wf_parameters : Dict, optional
                    Keys:
                      fsmList  – list of fixed spin moment values (mu_B).
                                 Final FSM = magOffset + value.
                      magOffset – float added to every fsmList entry (default 0.0).
    inpgenCompRes : Dict, optional
                    Compute resources for the inpgen step (overrides scf.options).
    """

    _workflowversion = '0.3.0'

    _default_wf_para = {
        'fsmList': [-0.1, 0.0, 0.1],
        'magOffset': 0.0,
    }

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 2 * 60 * 60,
        'queue_name': '',
        'withmpi': False,
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace='scf',
                           namespace_options={
                               'required': True,
                               'populate_defaults': False
                           })
        spec.input('wf_parameters', valid_type=orm.Dict, required=False)
        spec.input('inpgenCompRes', valid_type=orm.Dict, required=False)

        spec.outline(
            cls.start,
            cls.run_inpgen,
            cls.adapt_inputs,
            cls.run_fsm_calcs,
            cls.get_results,
        )

        spec.output('output_fsm_wc_para', valid_type=orm.Dict)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message='Input file was corrupted after modifications.')
        spec.exit_code(360, 'ERROR_INPGEN_CALCULATION_FAILED', message='Inpgen calculation failed.')
        spec.exit_code(370, 'ERROR_ALL_FSM_CALCS_FAILED', message='All FSM SCF calculations failed.')

    # -------------------------------------------------------------------------
    # Workchain steps
    # -------------------------------------------------------------------------

    def start(self):
        """Initialise context and validate wf_parameters."""
        self.report(f'INFO: started FleurFsmWorkChain version {self._workflowversion}')

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = [k for k in wf_dict if k not in wf_default]
        if extra_keys:
            error = f'ERROR: input wf_parameters for FleurFsmWorkChain contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        for key, val in wf_default.items():
            wf_dict.setdefault(key, val)
        self.ctx.wf_dict = wf_dict

        # Build the actual list of fixed moments to compute
        fsm_list = [wf_dict['magOffset'] + v for v in wf_dict['fsmList']]
        self.ctx.fsm_values = fsm_list

        # Validate codes
        scf_inputs = self.inputs.scf
        if 'inpgen' not in scf_inputs:
            error = 'ERROR: scf.inpgen code is required for the FSM workchain'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        if 'structure' not in scf_inputs:
            error = 'ERROR: scf.structure is required for the FSM workchain'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        if 'fleur' not in scf_inputs:
            error = 'ERROR: scf.fleur code is required for the FSM workchain'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        try:
            test_and_get_codenode(scf_inputs.inpgen, 'fleur.inpgen')
        except ValueError:
            error = 'The code provided for inpgen does not use the plugin fleur.inpgen'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_CODE_PROVIDED
        try:
            test_and_get_codenode(scf_inputs.fleur, 'fleur.fleur')
        except ValueError:
            error = 'The code provided for FLEUR does not use the plugin fleur.fleur'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # Inpgen compute resources: explicit inpgenCompRes beats scf.options
        if 'inpgenCompRes' in self.inputs:
            self.ctx.inpgen_options = self.inputs.inpgenCompRes.get_dict()
        elif 'options' in scf_inputs:
            base_options = scf_inputs.options.get_dict()
            self.ctx.inpgen_options = {
                'resources': base_options.get('resources', self._default_options['resources']),
                'max_wallclock_seconds': base_options.get('max_wallclock_seconds',
                                                          self._default_options['max_wallclock_seconds']),
                'queue_name': base_options.get('queue_name', ''),
                'withmpi': False,
            }
        else:
            self.ctx.inpgen_options = copy.deepcopy(self._default_options)

    def run_inpgen(self):
        """
        Run the FLEUR input generator.

        Augments the user-provided calc_parameters with:
          - comp.jspins = 2          (activate spin polarisation)
          - atom<i>.z  = <Z>        (atomic number, required by inpgen)
          - atom<i>.bmu = 0.0       (start from a non-magnetic reference density)
        One &atom entry per species is written; for a single-species structure
        the key is 'atom', for multi-species 'atom0', 'atom1', …
        Keeps any kpt specification already present in calc_parameters.
        """
        from masci_tools.util.constants import ATOMIC_NUMBERS

        scf_inputs = self.inputs.scf
        structure = scf_inputs.structure
        inpgen_code = scf_inputs.inpgen

        # Build calc_parameters for inpgen
        if 'calc_parameters' in scf_inputs:
            params_dict = scf_inputs.calc_parameters.get_dict()
        else:
            params_dict = {}

        # Ensure spin-polarised run
        comp = params_dict.setdefault('comp', {})
        comp['jspins'] = 2

        # Build one &atom entry per species with z (required) and bmu=0.0.
        # For a single kind the key is 'atom'; for multiple kinds 'atom0', 'atom1', …
        # Any existing per-species settings from calc_parameters are preserved;
        # z and bmu are always overwritten to ensure correctness.
        kinds = structure.kinds
        n_kinds = len(kinds)
        # Remove a z-less catch-all 'atom' entry if we are about to write per-species ones
        if n_kinds > 1 and 'atom' in params_dict and 'z' not in params_dict['atom']:
            del params_dict['atom']
        for i, kind in enumerate(kinds):
            element = kind.symbols[0]
            z = ATOMIC_NUMBERS.get(element, 0)
            atom_key = 'atom' if n_kinds == 1 else f'atom{i}'
            atom_entry = params_dict.setdefault(atom_key, {})
            atom_entry['z'] = z
            atom_entry['bmu'] = 0.0

        params = orm.Dict(params_dict)

        settings = scf_inputs.get('settings', None)

        label = 'fsm: inpgen'
        description = f'Inpgen for FSM workflow on {structure.get_formula()}'

        inputs_build = get_inputs_inpgen(structure,
                                         inpgen_code,
                                         self.ctx.inpgen_options,
                                         label,
                                         description,
                                         settings=settings,
                                         params=params)

        self.report('INFO: submitting inpgen')
        future = self.submit(inputs_build)
        return ToContext(inpgen=future)

    def adapt_inputs(self):
        """
        Create one FleurinpData per requested FSM value.

        For each value in self.ctx.fsm_values:
          - set ``fixed_moment`` in the magnetism tag
          - add U=J=0 LDA+U for every d-shell species (l=2) and
            every f-shell species (l=3) so that density matrices are written

        The list of species that received LDA+U is stored in
        self.ctx.ldau_species_info for later use in get_results.
        """
        if not self.ctx.inpgen.is_finished_ok:
            error = 'ERROR: inpgen calculation failed'
            self.report(error)
            self.ctx.errors.append(error)
            return self.exit_codes.ERROR_INPGEN_CALCULATION_FAILED

        base_fleurinp = self.ctx.inpgen.outputs.fleurinp

        # Determine which species carry d or f electrons
        ldau_species_info = self._get_ldau_species_info(base_fleurinp)
        self.ctx.ldau_species_info = ldau_species_info
        self.report(f'INFO: LDA+U will be added for species: '
                    f'{[s["name"] for s in ldau_species_info]}')

        fleurinps = {}
        for i, fsm_val in enumerate(self.ctx.fsm_values):
            fleurmode = FleurinpModifier(base_fleurinp)

            # Set the fixed total spin moment (in mu_B)
            try:
                fleurmode.set_inpchanges({'fixed_moment': fsm_val})
            except (ValueError, KeyError) as exc:
                error = (f'ERROR: Setting fixed_moment={fsm_val} failed: {exc}')
                self.report(error)
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

            # Add zero-cost LDA+U so that density matrices are tracked
            for species_info in ldau_species_info:
                try:
                    fleurmode.set_species(
                        species_info['name'],
                        {'ldaU': {
                            'l': species_info['l'],
                            'U': 0.0,
                            'J': 0.0,
                            'l_amf': False,
                        }},
                        create=True,
                    )
                except (ValueError, KeyError) as exc:
                    error = (f'ERROR: Adding LDA+U to species {species_info["name"]} failed: {exc}')
                    self.report(error)
                    return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

            # Validate
            try:
                fleurmode.show(display=False, validate=True)
            except etree.DocumentInvalid:
                error = f'ERROR: Modified inp.xml for FSM={fsm_val} did not validate'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_FILE
            except ValueError as exc:
                error = (f'ERROR: Inp.xml modification for FSM={fsm_val} could not be applied: {exc}')
                self.report(error)
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

            fleurinps[f'fleurinp_{i}'] = fleurmode.freeze()

        self.ctx.fleurinps = fleurinps
        self.report(f'INFO: prepared {len(fleurinps)} FleurinpData nodes for FSM calculations')

    def run_fsm_calcs(self):
        """Submit one FleurScfWorkChain per fixed-moment value in parallel."""
        scf_inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        # Remove structure/inpgen from the scf inputs – we provide a fleurinp instead
        scf_inputs.pop('structure', None)
        scf_inputs.pop('inpgen', None)
        scf_inputs.pop('calc_parameters', None)
        scf_inputs.pop('settings', None)

        futures = {}
        for i, fsm_val in enumerate(self.ctx.fsm_values):
            scf_run_inputs = AttributeDict(scf_inputs)
            scf_run_inputs.fleurinp = self.ctx.fleurinps[f'fleurinp_{i}']

            future = self.submit(FleurScfWorkChain, **scf_run_inputs)
            future.label = f'fsm_scf_{i}'
            future.description = f'FSM SCF for fixed_moment={fsm_val:.4f} mu_B'
            futures[f'scf_{i}'] = future

        self.report(f'INFO: submitted {len(futures)} FSM SCF calculations')
        return ToContext(**futures)

    def get_results(self):
        """
        Collect results from all FSM SCF calculations into output_fsm_wc_para.

        For each calculation extracts:
          - free energy (eV) from the last FleurCalculation output_parameters
          - spin-up and spin-down Fermi energies (eV) by re-parsing out.xml
          - density matrices from the n_mmp_mat file in the retrieved folder
          - the UUID of the FleurScfWorkChain node
        """
        n_calcs = len(self.ctx.fsm_values)

        fsm_list_out = []
        free_energies = []
        fermi_energies_up = []
        fermi_energies_down = []
        density_matrices = []
        scf_uuids = []

        num_failed = 0

        for i, fsm_val in enumerate(self.ctx.fsm_values):
            scf_wc = self.ctx[f'scf_{i}']
            scf_uuids.append(scf_wc.uuid)

            if not scf_wc.is_finished_ok:
                warning = (f'WARNING: FSM SCF for fixed_moment={fsm_val:.4f} did not finish '
                           f'successfully (exit_status={scf_wc.exit_status}). '
                           'Skipping this point.')
                self.report(warning)
                self.ctx.warnings.append(warning)
                num_failed += 1
                continue

            # --- Free energy ---
            free_energy = None
            try:
                out_params = scf_wc.outputs.last_calc.output_parameters.get_dict()
                # 'energy' is the free energy in eV (converted from Hartree by the parser)
                free_energy = out_params.get('energy', None)
                if free_energy is None:
                    # Fall back to Hartree value and convert manually
                    energy_htr = out_params.get('energy_hartree', None)
                    if energy_htr is not None:
                        free_energy = energy_htr * 27.21138602
            except Exception as exc:  # pylint: disable=broad-except
                self.report(f'WARNING: Could not extract free energy for FSM={fsm_val:.4f}: {exc}')

            retrieved = scf_wc.outputs.last_calc.retrieved

            # Parse out.xml once with lxml; use XPath for Fermi energies and density matrices.
            outxml_tree = None
            try:
                with retrieved.open(FleurCalculation._OUTXML_FILE_NAME, 'rb') as outxml_file:
                    outxml_tree = etree.parse(outxml_file)
            except Exception as exc:  # pylint: disable=broad-except
                self.report(f'WARNING: Could not parse out.xml for FSM={fsm_val:.4f}: {exc}')

            # --- Fermi energies for both spin channels ---
            # For FSM calculations FLEUR writes a FixedTotalMoment element inside each
            # iteration block with fermiEnergyUp and fermiEnergyDown attributes (in Htr).
            # masci-tools has no dedicated parse task for this element.
            ef_up = None
            ef_down = None
            if outxml_tree is not None:
                try:
                    htr_to_ev = 27.21138602
                    last_ftm = outxml_tree.xpath('//iteration[last()]/FixedTotalMoment')
                    if last_ftm:
                        ef_up = float(last_ftm[0].get('fermiEnergyUp')) * htr_to_ev
                        ef_down = float(last_ftm[0].get('fermiEnergyDown')) * htr_to_ev
                    else:
                        self.report(f'WARNING: FixedTotalMoment element not found in out.xml '
                                    f'for FSM={fsm_val:.4f}')
                except Exception as exc:  # pylint: disable=broad-except
                    self.report(f'WARNING: Could not extract Fermi energies for FSM={fsm_val:.4f}: {exc}')

            # --- Density matrices from ldaUDensityMatrix in last iteration ---
            density_matrix_set = []
            if outxml_tree is not None:
                try:
                    density_matrix_set = _extract_density_matrix_set(outxml_tree,
                                                                      self.ctx.ldau_species_info)
                except Exception as exc:  # pylint: disable=broad-except
                    self.report(f'WARNING: Could not extract density matrices for FSM={fsm_val:.4f}: {exc}')

            # Collect
            fsm_list_out.append(fsm_val)
            free_energies.append(free_energy)
            fermi_energies_up.append(ef_up)
            fermi_energies_down.append(ef_down)
            density_matrices.append({'densityMatrixSet': density_matrix_set})

        if num_failed == n_calcs:
            error = 'ERROR: All FSM SCF calculations failed'
            self.report(error)
            self.ctx.errors.append(error)
            return self.exit_codes.ERROR_ALL_FSM_CALCS_FAILED

        out_dict = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'fsmList': fsm_list_out,
            'freeEnergiesList': free_energies,
            'fermiEnergiesUp': fermi_energies_up,
            'fermiEnergiesDown': fermi_energies_down,
            'densityMatrices': density_matrices,
            'scfUUIDs': scf_uuids,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
        }

        out_node = _save_fsm_output_node(orm.Dict(out_dict))
        output_node = out_node['output_fsm_wc_para']
        output_node.label = 'output_fsm_wc_para'
        output_node.description = ('Results of a FleurFsmWorkChain run: free energies, '
                                   'Fermi energies and density matrices vs. fixed spin moment.')
        self.out('output_fsm_wc_para', output_node)
        self.report(f'INFO: FleurFsmWorkChain finished. '
                    f'{n_calcs - num_failed}/{n_calcs} FSM calculations succeeded.')

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def control_end_wc(self, errormsg):
        """Controlled shutdown: log the error and append to ctx.errors."""
        self.report(errormsg)
        self.ctx.errors.append(errormsg)

    @staticmethod
    def _get_ldau_species_info(fleurinp: FleurinpData) -> list[dict]:
        """
        Inspect the FleurinpData to find species that carry d or f electrons
        and return the information needed to add LDA+U and later parse
        density matrices.

        Returns a list of dicts with keys: name, element, l, atom_type_index.
        """
        from masci_tools.util.constants import ATOMIC_NUMBERS

        inp_dict = fleurinp.inp_dict
        atom_species_block = inp_dict.get('atomSpecies', {})
        if isinstance(atom_species_block, list):
            # masci-tools returns atomSpecies as a flat list of atomType dicts
            atom_types = atom_species_block
        else:
            atom_types = atom_species_block.get('atomType', [])
            if isinstance(atom_types, dict):
                atom_types = [atom_types]

        ldau_species = []
        for idx, atom_type in enumerate(atom_types):
            name = atom_type.get('name', '')
            element = atom_type.get('element', '')
            z = ATOMIC_NUMBERS.get(element, 0)

            if z in _F_BLOCK_Z:
                l_channel = 3
            elif z in _D_BLOCK_Z:
                l_channel = 2
            else:
                continue  # not a d- or f-block element

            ldau_species.append({
                'name': name,
                'element': element,
                'l': l_channel,
                'atom_type_index': idx + 1,  # 1-based, matches FLEUR convention
            })

        return ldau_species


# ---------------------------------------------------------------------------
# Module-level helpers and calcfunctions
# ---------------------------------------------------------------------------


def _extract_density_matrix_set(tree, ldau_species_info: list[dict]) -> list[dict]:
    """
    Extract density matrices from the last SCF iteration of an already-parsed out.xml tree.

    FLEUR writes the density matrices as ``ldaUDensityMatrix/densityMatrixFor``
    elements inside each iteration block.  Each ``densityMatrixFor`` element
    carries ``spin``, ``atomType``, ``uIndex``, ``l``, ``U``, ``J`` attributes
    and n² space-separated ``(real,imag)`` complex numbers as text content
    (the n×n density matrix in row-major order, where n = 2*l+1).

    Returns an empty list if no density matrix data is found.
    """
    # Build a map from atom-type index to species name for the output dict
    atom_type_to_species = {s['atom_type_index']: s['name'] for s in ldau_species_info}

    # densityMatrixFor elements from the last iteration only
    dm_elements = tree.xpath('//iteration[last()]/ldaUDensityMatrix/densityMatrixFor')

    if not dm_elements:
        return []

    density_matrix_set = []
    for elem in dm_elements:
        spin = int(elem.get('spin'))
        atom_type = int(elem.get('atomType'))
        l_val = int(elem.get('l'))
        species_name = atom_type_to_species.get(atom_type, f'atomType{atom_type}')

        # Text contains n×n "(real,imag)" tokens where n = 2*l+1
        n = 2 * l_val + 1
        tokens = (elem.text or '').split()
        matrix_rows = [' '.join(tokens[row * n:(row + 1) * n]) for row in range(n)]

        density_matrix_set.append({
            'densityMatrix': {
                'atomTypeIndex': atom_type,
                'l': l_val,
                'matrix': matrix_rows,
                'species': species_name,
                'spin': spin,
            }
        })

    return density_matrix_set


@cf
def _save_fsm_output_node(out: orm.Dict) -> dict:
    """
    Calcfunction wrapper to create the output node with proper provenance.
    """
    output_node = out.clone()
    output_node.label = 'output_fsm_wc_para'
    output_node.description = 'Output parameters of FleurFsmWorkChain.'
    return {'output_fsm_wc_para': output_node}
