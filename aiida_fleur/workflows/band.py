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
This is the workflow 'band' for the Fleur code, which calculates an
electronic band structure.

This workflow follows the design of the VASP ``VaspBandsWorkChain``. It performs
the following steps:

1. (Optional) Run an SCF workchain to converge the charge density if no
   ``RemoteData`` containing a converged density is provided.
2. (Optional) Use :py:func:`aiida.tools.data.array.kpoints.get_explicit_kpoints_path`
   to obtain the primitive structure and an explicit k-point path along the
   high-symmetry lines of the Brillouin zone. Alternatively, the user may
   supply an explicit :py:class:`~aiida.orm.KpointsData` node with a precomputed
   path.
3. Run a non-self-consistent FLEUR calculation on the k-point path with
   ``output/@band`` set to ``T`` (see section 4.3 of the FLEUR input manual).
4. Parse the resulting ``banddos.hdf`` file into an
   :py:class:`~aiida.orm.BandsData` node.

The workflow exposes the ``scf`` and ``band`` namespaces from
``FleurScfWorkChain`` and ``FleurBaseWorkChain`` respectively, so that most
common calculation parameters can be customised.
"""
import copy
import numpy as np

from aiida.orm import Code, Dict, RemoteData, KpointsData, BandsData, StructureData
from aiida.orm import load_node, FolderData
from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent
from aiida.common import AttributeDict
from aiida.tools.data.array.kpoints import get_explicit_kpoints_path

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, test_and_get_codenode
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data


class FleurBandWorkChain(WorkChain):
    """
    Workchain for running FLEUR band structure calculations.

    :param structure: (StructureData), Crystal structure
    :param wf_parameters: (Dict), Workchain specifications
    :param fleur: (Code), FLEUR code
    :param scf: namespace, inputs for the (optional) ``FleurScfWorkChain``.
        If not provided the workflow will require a ``remote_data`` input.
    :param remote_data: (RemoteData), Remote folder from a previous FLEUR run.
    :param fleurinp: (FleurinpData), FleurinpData to use as a starting point.
    :param kpoints: (KpointsData), Explicit k-point path to use. If not provided,
        a path is generated via SeeK-path.
    :param options: (Dict), Computational resources.

    :return output_band_wc_para: (Dict), information about the workflow result
    :return band_structure: (BandsData), the computed band structure
    :return primitive_structure: (StructureData), the primitive structure used
    :return seekpath_parameters: (Dict), parameters used by SeeK-path
    :return band_calc: namespace, outputs of the underlying ``FleurBaseWorkChain``
    """
    _workflowversion = '0.1.0'

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }

    _default_wf_para = {
        # Seek-path parameters
        'kpath': 'seek',  # 'seek' or 'auto' or None (use kpoints input)
        'reference_distance': 0.025,
        'symprec': 1e-5,
        'angle_tolerance': -1.0,
        # Number of k-points to be used in the band path when 'auto' is used
        'kpoints_number': None,
        # sigma and energy window for the band output. These only affect the
        # text band output and not the HDF5 file content.
        'sigma': 0.005,
        'emin': -0.50,
        'emax': 0.90,
        # Optional list of inp.xml modifications to apply to the SCF output
        # before the band calculation. Same format as in FleurBandDosWorkChain.
        'inpxml_changes': [],
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(
            FleurScfWorkChain,
            namespace='scf',
            namespace_options={
                'required': False,
                'populate_defaults': False,
                'help': 'Inputs for the SCF workchain. If provided, the SCF '
                'calculation is run before the band calculation.'
            },
        )

        spec.input('structure', valid_type=StructureData, required=False)
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote_data', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('kpoints', valid_type=KpointsData, required=False)
        spec.input('options', valid_type=Dict, required=False)
        spec.input(
            'settings',
            valid_type=Dict,
            required=False,
            help='Optional settings passed to the band structure FLEUR calculation.',
        )
        spec.input(
            'add_comp_para',
            valid_type=Dict,
            required=False,
            help='Optional override of the computational parameters for the '
            'band structure FLEUR calculation.',
        )

        spec.outline(
            cls.start,
            if_(cls.scf_needed)(
                cls.run_scf,
                cls.verify_scf,
            ),
            cls.generate_kpoints_path,
            cls.change_fleurinp,
            cls.run_band,
            cls.inspect_band,
            cls.return_results,
        )

        spec.output('output_band_wc_para', valid_type=Dict)
        spec.output('band_structure', valid_type=BandsData, required=False)
        spec.output('primitive_structure', valid_type=StructureData, required=False)
        spec.output('seekpath_parameters', valid_type=Dict, required=False)
        spec.expose_outputs(FleurBaseWorkChain, namespace='band_calc')

        # Exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233, 'ERROR_INVALID_CODE_PROVIDED', message='Invalid code node specified, check fleur code node.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(334, 'ERROR_SCF_CALCULATION_FAILED', message='SCF calculation failed.')
        spec.exit_code(335, 'ERROR_SCF_CALCULATION_NOREMOTE', message='Found no SCF calculation remote repository.')
        spec.exit_code(336, 'ERROR_GENERATING_KPOINTS_FAILED', message='Generating the k-point path failed.')
        spec.exit_code(337, 'ERROR_BAND_CALCULATION_FAILED', message='Band structure calculation failed.')
        spec.exit_code(338, 'ERROR_NO_BAND_FILE', message='No band structure output file was retrieved.')

    def start(self):
        """
        Initialise the workchain, validate inputs and merge parameters.
        """
        self.report(f'Started FleurBandWorkChain workflow version {self._workflowversion}')

        self.ctx.scf_needed = False
        self.ctx.scf = None
        self.ctx.band_calc = None
        self.ctx.fleurinp_band = None
        self.ctx.successful = False
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.kpath_kpoints = None
        self.ctx.primitive_structure = None

        inputs = self.inputs

        # Merge workflow parameters with defaults
        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in inputs:
            wf_dict = inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            if isinstance(val, dict):
                wf_dict[key] = {**val, **wf_dict.get(key, {})}
            else:
                wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # Detect unknown keys to fail early
        extra_keys = [k for k in self.ctx.wf_dict if k not in wf_default]
        if extra_keys:
            self.report(f'ERROR: input wf_parameters contains extra keys: {extra_keys}')
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # Merge options
        defaultoptions = copy.deepcopy(self._default_options)
        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = defaultoptions
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        # Validate FLEUR code node
        try:
            test_and_get_codenode(inputs.fleur, 'fleur.fleur')
        except ValueError:
            error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # Validate the combination of inputs.
        # We accept one of:
        #   * (a) ``scf`` namespace input, or
        #   * (b) a ``remote_data`` (from a previous FLEUR run), or
        #   * (c) a ``fleurinp`` plus a ``structure`` (the structure is used to
        #         obtain the k-path; the SCF run is mandatory to obtain a charge
        #         density).
        if 'scf' in inputs:
            self.ctx.scf_needed = True
            if 'remote_data' in inputs:
                self.report('ERROR: you gave SCF input and remote_data for the band calculation.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in inputs:
                self.report('ERROR: you gave SCF input and fleurinp for the band calculation.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote_data' in inputs:
            self.ctx.scf_needed = False
            if 'fleurinp' in inputs:
                self.report('ERROR: you gave remote_data and fleurinp for the band calculation.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'fleurinp' in inputs and 'structure' in inputs:
            # Without remote_data, an SCF is required to converge a charge density.
            self.ctx.scf_needed = True
        else:
            self.report('ERROR: you gave neither SCF input nor remote_data nor fleurinp+structure.')
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        # Validate k-path related inputs
        if self.ctx.wf_dict['kpath'] not in ('seek', 'auto', None) and 'kpoints' not in inputs:
            self.report(
                f"ERROR: unknown kpath '{self.ctx.wf_dict['kpath']}'. Use 'seek', 'auto' or provide 'kpoints'.")
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def scf_needed(self):
        """Return whether an SCF run is required."""
        return self.ctx.scf_needed

    def run_scf(self):
        """Submit the SCF workchain."""
        self.report('INFO: run SCF calculation before band structure')
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(scf=res)

    def verify_scf(self):
        """Verify that the SCF calculation finished successfully."""
        calc = self.ctx.scf
        if not calc.is_finished_ok:
            self.report('The SCF calculation was not successful.')
            self.ctx.errors.append('SCF calculation failed.')
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        # Make the output available
        self.ctx.remote_data = self._find_remote_data(calc)
        if self.ctx.remote_data is None:
            self.report('Found no remote folder of the reference SCF calculation.')
            return self.exit_codes.ERROR_SCF_CALCULATION_NOREMOTE

    def get_inputs_scf(self):
        """Build the inputs for the SCF sub-workchain."""
        return AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

    @staticmethod
    def _find_remote_data(scf_workchain):
        """Locate the ``RemoteData`` produced by the last FLEUR run inside the SCF workchain."""
        pk_last = 0
        for called in scf_workchain.called:
            if called.node_type.startswith('process.workflow.workchain.WorkChainNode'):
                if called.process_class is FleurBaseWorkChain and called.pk > pk_last:
                    pk_last = called.pk
        if pk_last == 0:
            return None
        try:
            return load_node(pk_last).outputs.remote_folder
        except (AttributeError, NotExistent):
            return None

    def generate_kpoints_path(self):
        """
        Build the explicit k-point path either from the user supplied
        :py:class:`~aiida.orm.KpointsData` or by invoking SeeK-path / ASE.
        """
        wf_dict = self.ctx.wf_dict

        if 'kpoints' in self.inputs:
            # The user supplied the full path explicitly
            self.ctx.kpath_kpoints = self.inputs.kpoints
            return

        # We need a structure to derive the path. Use the one from ``structure``,
        # or extract it from the ``fleurinp`` / remote SCF output.
        structure = None
        if 'structure' in self.inputs:
            structure = self.inputs.structure
        elif self.ctx.scf is not None and self.ctx.scf.is_finished_ok:
            try:
                fleurin = self.ctx.scf.outputs.fleurinp
                structure = fleurin.get_structuredata_ncf()
            except (NotExistent, AttributeError, ValueError):
                structure = None
        elif 'fleurinp' in self.inputs:
            structure = self.inputs.fleurinp.get_structuredata_ncf()

        if structure is None:
            self.report('ERROR: could not obtain a structure for k-path generation.')
            return self.exit_codes.ERROR_GENERATING_KPOINTS_FAILED

        if wf_dict['kpath'] == 'seek':
            try:
                output = get_explicit_kpoints_path(
                    structure,
                    reference_distance=wf_dict['reference_distance'],
                    symprec=wf_dict['symprec'],
                    angle_tolerance=wf_dict['angle_tolerance'],
                )
            except Exception as exc:  # noqa: BLE001
                self.report(f'ERROR: SeeK-path failed with: {exc}')
                return self.exit_codes.ERROR_GENERATING_KPOINTS_FAILED

            primitive = output['primitive_structure']
            output['explicit_kpoints'].store()

            # Optionally warn if the primitive cell differs from the input cell
            maxdiff_cell = float(np.max(np.abs(np.array(primitive.cell) - np.array(structure.cell))))
            if maxdiff_cell > 3e-9:
                self.report('WARNING: The primitive structure differs from the input structure. '
                            'The primitive structure will be used for the band calculation.')

            self.ctx.primitive_structure = primitive
            self.ctx.kpath_kpoints = output['explicit_kpoints']
            self.ctx.seekpath_parameters = output.get('parameters')
        else:
            # 'auto' or anything else: use ASE bandpath with the default path.
            from ase.dft.kpoints import bandpath
            nkpts = wf_dict.get('kpoints_number') or 500
            path = bandpath(cell=structure.cell, npoints=nkpts)
            special_points = path.special_points

            labels = []
            for label, special_kpoint in special_points.items():
                for index, kpoint in enumerate(path.kpts):
                    if float(np.max(np.abs(np.asarray(special_kpoint) - np.asarray(kpoint)))) < 1e-12:
                        labels.append((index, label))
            labels = sorted(labels, key=lambda x: x[0])

            kpts = KpointsData()
            kpts.set_cell(structure.cell)
            kpts.pbc = structure.pbc
            weights = np.ones(len(path.kpts)) / len(path.kpts)
            kpts.set_kpoints(kpoints=path.kpts, cartesian=False, weights=weights, labels=labels)
            kpts.store()

            self.ctx.kpath_kpoints = kpts

    def change_fleurinp(self):
        """
        Create a new FleurinpData by activating the band output on the SCF
        result (or the supplied ``fleurinp``) and switching to the k-point path.
        """
        wf_dict = self.ctx.wf_dict

        if self.ctx.scf is not None and self.ctx.scf.is_finished_ok:
            try:
                fleurin = self.ctx.scf.outputs.fleurinp
            except (NotExistent, AttributeError):
                self.report('Fleurinp generated in the SCF calculation is not found.')
                return self.exit_codes.ERROR_SCF_CALCULATION_FAILED
        elif 'fleurinp' in self.inputs:
            fleurin = self.inputs.fleurinp
        else:
            fleurin = get_fleurinp_from_remote_data(self.ctx.remote_data)

        fleurmode = FleurinpModifier(fleurin)

        # Apply user defined inp.xml changes
        fchanges = wf_dict.get('inpxml_changes', [])
        if fchanges:
            try:
                fleurmode.add_task_list(fchanges)
            except (ValueError, TypeError) as exc:
                self.report(f'ERROR: applying inpxml_changes failed with: {exc}')
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # Switch on the band output
        fleurmode.set_inpchanges({
            'band': True,
            'minEnergy': wf_dict['emin'],
            'maxEnergy': wf_dict['emax'],
            'sigma': wf_dict['sigma'],
        })

        # Switch to the explicit k-point path
        kpoint_type = 'path'
        fleurmode.set_kpointsdata(self.ctx.kpath_kpoints, switch=True, kpoint_type=kpoint_type)

        try:
            fleurmode.show(display=False, validate=True)
        except Exception as exc:  # noqa: BLE001
            self.report(f'ERROR: input file validation failed with: {exc}')
            return self.exit_codes.ERROR_INVALID_INPUT_FILE

        self.ctx.fleurinp_band = fleurmode.freeze()

    def run_band(self):
        """
        Submit the non-self-consistent FLEUR band structure calculation.
        """
        self.report('INFO: run band structure calculation')

        fleurin = self.ctx.fleurinp_band
        if fleurin is None:
            self.report('ERROR: Creating the band structure Fleurinp failed for an unknown reason.')
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # The starting charge density is either the user-supplied remote_data,
        # or the remote folder produced by the SCF sub-workchain.
        if 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = self.ctx.remote_data

        if remote is None:
            self.report('ERROR: no remote data available to start the band calculation.')
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        # Avoid copying the mixing history, which would clash with the band
        # input file.
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}
        if 'settings' in self.inputs:
            user_settings = self.inputs.settings.get_dict()
            settings = {**user_settings, **settings}

        code = self.inputs.fleur
        options = copy.deepcopy(self.ctx.options)

        # Optional overrides for the band structure FLEUR calculation
        add_comp_para = wf_dict_add_comp_para(self.ctx.wf_dict)
        if 'add_comp_para' in self.inputs:
            add_comp_para = {**add_comp_para, **self.inputs.add_comp_para.get_dict()}

        label = 'band_calculation'
        description = 'Band structure is calculated for the given structure'

        inputs_builder = get_inputs_fleur(
            code,
            remote,
            fleurin,
            options,
            label=label,
            description=description,
            settings=settings,
            add_comp_para=add_comp_para,
        )

        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(band_calc=future)

    def inspect_band(self):
        """Verify that the band calculation finished successfully."""
        calc = self.ctx.band_calc
        if calc is None or not calc.is_finished_ok:
            self.report('Band structure calculation was not successful.')
            return self.exit_codes.ERROR_BAND_CALCULATION_FAILED

        # Check that the band files are retrieved
        try:
            retrieved = calc.outputs.retrieved
            res_files = retrieved.list_object_names()
        except (NotExistent, AttributeError):
            res_files = []

        bandfiles = ['bands.1', 'bands.2', 'banddos.hdf']
        if not any(name in res_files for name in bandfiles):
            self.report('No bandstructure file was retrieved, something went wrong.')
            return self.exit_codes.ERROR_NO_BAND_FILE

        self.ctx.successful = True

    def return_results(self):
        """
        Attach the output nodes to the workchain.
        """
        self.report('Band workflow Done')

        # Build the output parameter node
        output_dict = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
            'successful': self.ctx.successful,
            'mode': 'band',
        }
        outpara = Dict(output_dict)
        outpara.label = 'output_band_wc_para'
        outpara.description = 'Contains band calculation results'
        self.out('output_band_wc_para', outpara)

        # Attach the primitive structure / SeeK-path parameters if available
        if self.ctx.primitive_structure is not None:
            self.out('primitive_structure', self.ctx.primitive_structure)
        if getattr(self.ctx, 'seekpath_parameters', None) is not None:
            self.out('seekpath_parameters', self.ctx.seekpath_parameters)

        # Build BandsData from the banddos.hdf file if possible
        if self.ctx.band_calc is not None:
            self.out_many(self.exposed_outputs(self.ctx.band_calc, FleurBaseWorkChain, namespace='band_calc'))
            try:
                retrieved = self.ctx.band_calc.outputs.retrieved
                fleurinp = self.ctx.band_calc.inputs.fleurinp
                bands = create_aiida_bands_data(fleurinp=fleurinp, retrieved=retrieved)
                if isinstance(bands, BandsData):
                    self.out('band_structure', bands)
            except (NotExistent, AttributeError):
                pass

    def control_end_wc(self, errormsg):
        """Controlled way to shut the workchain down with a helpful message."""
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


def wf_dict_add_comp_para(wf_dict):
    """Return the ``add_comp_para`` block from the wf_parameters dictionary."""
    return wf_dict.get('add_comp_para', {})


@cf
def create_aiida_bands_data(fleurinp, retrieved):
    """
    Create :py:class:`~aiida.orm.BandsData` from the ``banddos.hdf`` file
    produced by a FLEUR band structure calculation.

    :param fleurinp: :class:`~aiida_fleur.data.fleurinp.FleurinpData` for the
        calculation
    :param retrieved: :class:`~aiida.orm.FolderData` for the band structure
        calculation
    :return: :class:`~aiida.orm.BandsData` for the band structure calculation
    """
    from masci_tools.io.parsers.hdf5 import HDF5Reader, HDF5TransformationError
    from masci_tools.io.parsers.hdf5.recipes import FleurSimpleBands
    from aiida.engine import ExitCode

    try:
        kpoints = fleurinp.get_kpointsdata_ncf(only_used=True)
    except ValueError as exc:
        return ExitCode(320, message=f'Retrieving kpoints data from fleurinp failed with: {exc}')

    if 'banddos.hdf' in retrieved.list_object_names():
        try:
            with retrieved.open('banddos.hdf', 'rb') as f:
                with HDF5Reader(f) as reader:
                    data, attributes = reader.read(recipe=FleurSimpleBands)
        except (HDF5TransformationError, ValueError) as exc:
            return ExitCode(310, message=f'banddos.hdf reading failed with: {exc}')
    else:
        return ExitCode(300, message='banddos.hdf file not in the retrieved files')

    bands = BandsData()
    bands.set_kpointsdata(kpoints)

    nkpts, nbands = attributes['nkpts'], attributes['nbands']
    eigenvalues = data['eigenvalues_up'].reshape((nkpts, nbands))
    if 'eigenvalues_down' in data:
        eigenvalues_dn = data['eigenvalues_down'].reshape((nkpts, nbands))
        eigenvalues = [eigenvalues, eigenvalues_dn]

    bands.set_bands(eigenvalues, units='eV')
    bands.label = 'output_band_wc_bands'
    bands.description = 'Contains BandsData for the bandstructure calculation'
    return bands