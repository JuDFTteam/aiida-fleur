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

###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
###############################################################################

from __future__ import annotations

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import WorkChain, ToContext, calcfunction
from aiida.orm import Dict
from aiida.plugins import CalculationFactory

from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.workflows.scf import FleurScfWorkChain

InpgenCalculation = CalculationFactory('fleur.inpgen')


@calcfunction
def create_result_node(result_data: Dict) -> Dict:
    """
    Create the final stored result node with provenance.
    """
    outnode = orm.Dict(dict=result_data.get_dict())
    outnode.label = 'output_convergence_wc_para'
    outnode.description = 'Contains Kmax, k-point and smearing convergence results.'
    return outnode


@calcfunction
def create_plot_nodes(result_data: Dict):
    """
    Create plot-ready Dict nodes from the final results.
    Energies remain in Htr.
    """
    data = result_data.get_dict()

    kmax_results = data.get('kmax_results', [])
    kpoint_results = data.get('kpoints_results', [])
    smearing_results = data.get('smearing_results', [])

    kmax_plot = orm.Dict(dict={
        'x': [entry['kmax'] for entry in kmax_results],
        'y': [entry['total_energy'] for entry in kmax_results],
        'y_diff_htr': [entry.get('delta_to_previous_Htr') for entry in kmax_results],
        'xlabel': 'Kmax',
        'ylabel': f"Total energy ({kmax_results[0]['total_energy_units']})" if kmax_results else 'Total energy (Htr)',
        'title': 'Total energy vs Kmax',
    })
    kmax_plot.label = 'output_kmax_plot'
    kmax_plot.description = 'Plot-ready data for Total energy vs Kmax.'

    kpoints_plot = orm.Dict(dict={
        'x': [entry['mesh'][0] for entry in kpoint_results],
        'mesh_labels': ['x'.join(map(str, entry['mesh'])) for entry in kpoint_results],
        'y': [entry['total_energy'] for entry in kpoint_results],
        'y_diff_htr': [entry.get('delta_to_previous_Htr') for entry in kpoint_results],
        'xlabel': 'k-point mesh',
        'ylabel': f"Total energy ({kpoint_results[0]['total_energy_units']})" if kpoint_results else 'Total energy (Htr)',
        'title': 'Total energy vs k-point mesh',
    })
    kpoints_plot.label = 'output_kpoints_plot'
    kpoints_plot.description = 'Plot-ready data for Total energy vs k-point mesh.'

    smearing_plot = orm.Dict(dict={
        'x': [entry['smearing'] for entry in smearing_results],
        'y': [entry['total_energy'] for entry in smearing_results],
        'y_diff_htr': [entry.get('delta_to_previous_Htr') for entry in smearing_results],
        'xlabel': 'Fermi smearing energy (Htr)',
        'ylabel': f"Total energy ({smearing_results[0]['total_energy_units']})" if smearing_results else 'Total energy (Htr)',
        'title': 'Total energy vs smearing',
    })
    smearing_plot.label = 'output_smearing_plot'
    smearing_plot.description = 'Plot-ready data for Total energy vs smearing.'

    return {
        'output_kmax_plot': kmax_plot,
        'output_kpoints_plot': kpoints_plot,
        'output_smearing_plot': smearing_plot,
    }


class FleurCutoffConvWorkChain(WorkChain):
    """
    Sequential Kmax, k-point, and smearing convergence workflow starting from StructureData.

    Stage 0:
      Run inpgen from structure to generate the initial FleurinpData.

    Stage 1:
      Converge Kmax using the generated FleurinpData.

    Stage 2:
      For each k-point mesh, rerun inpgen from the same structure with a new k-mesh,
      obtain a fresh FleurinpData, set the converged Kmax, and run SCF.

    Stage 3:
      Using the converged k-mesh FleurinpData and converged Kmax, vary the
      Fermi smearing energy and run SCF.
    """

    _workflowversion = '1.3.0'

    _default_wf_para = {
        'kmax_values': [3.0, 3.3, 3.6, 3.9, 4.2, 4.5],
        'kpoint_meshes': [
            [2, 2, 2], [4, 4, 4], [6, 6, 6], [8, 8, 8],
            [10, 10, 10], [12, 12, 12], [14, 14, 14], [16, 16, 16],
            [18, 18, 18], [20, 20, 20], [22, 22, 22], [24, 24, 24],
        ],
        'smearing_values': [0.02, 0.01, 0.005, 0.002, 0.001],
        'kmax_energy_tol_meV': 1.0,
        'kpoints_energy_tol_meV': 1.0,
        'smearing_energy_tol_meV': 1.0,
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(
            FleurScfWorkChain,
            namespace='scf',
            exclude=('structure', 'remote_data', 'fleurinp', 'inpgen')
        )

        spec.input('structure', valid_type=orm.StructureData, required=True)

        spec.input_namespace('inpgen', required=True)
        spec.input('inpgen.code', valid_type=orm.Code, required=True)
        spec.input('inpgen.options', valid_type=orm.Dict, required=True)
        spec.input('inpgen.parameters', valid_type=orm.Dict, required=False)
        spec.input('inpgen.settings', valid_type=orm.Dict, required=False)

        spec.input('wf_parameters', valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            cls.run_initial_inpgen,
            cls.inspect_initial_inpgen,
            cls.run_kmax_series,
            cls.inspect_kmax_series,
            cls.determine_converged_kmax,
            cls.run_kmesh_inpgen_series,
            cls.inspect_kmesh_inpgen_series,
            cls.run_kpoints_series,
            cls.inspect_kpoints_series,
            cls.determine_converged_kpoints,
            cls.run_smearing_series,
            cls.inspect_smearing_series,
            cls.determine_converged_smearing,
            cls.return_results,
        )

        spec.output('output_convergence_wc_para', valid_type=Dict)
        spec.output('output_kmax_plot', valid_type=Dict, required=False)
        spec.output('output_kpoints_plot', valid_type=Dict, required=False)
        spec.output('output_smearing_plot', valid_type=Dict, required=False)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INITIAL_INPGEN_FAILED', message='Initial inpgen calculation failed.')
        spec.exit_code(232, 'ERROR_INITIAL_FLEURINP_MISSING', message='Initial inpgen did not produce a FleurinpData.')
        spec.exit_code(233, 'ERROR_NO_SUCCESSFUL_KMAX_RUN', message='No successful Kmax calculation available.')
        spec.exit_code(234, 'ERROR_NO_SUCCESSFUL_KMESH_INPGEN_RUN', message='No successful inpgen calculation available for the k-point stage.')
        spec.exit_code(235, 'ERROR_NO_SUCCESSFUL_KPOINT_RUN', message='No successful k-point calculation available.')
        spec.exit_code(236, 'ERROR_NO_SUCCESSFUL_SMEARING_RUN', message='No successful smearing calculation available.')

    def start(self):
        self.report(f'Started FleurCutoffConvWorkChain version {self._workflowversion}')

        wf_dict = dict(self._default_wf_para)
        if 'wf_parameters' in self.inputs:
            user_dict = self.inputs.wf_parameters.get_dict()
            extra_keys = [key for key in user_dict if key not in wf_dict]
            if extra_keys:
                self.report(f'ERROR: extra keys in wf_parameters: {extra_keys}')
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM
            wf_dict.update(user_dict)

        self.ctx.kmax_values = [float(x) for x in wf_dict['kmax_values']]
        self.ctx.kpoint_meshes = [[int(a), int(b), int(c)] for a, b, c in wf_dict['kpoint_meshes']]
        self.ctx.smearing_values = [float(x) for x in wf_dict['smearing_values']]
        self.ctx.kmax_energy_tol_meV = float(wf_dict['kmax_energy_tol_meV'])
        self.ctx.kpoints_energy_tol_meV = float(wf_dict['kpoints_energy_tol_meV'])
        self.ctx.smearing_energy_tol_meV = float(wf_dict['smearing_energy_tol_meV'])

        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        self.ctx.kmax_labels = []
        self.ctx.kmax_results = []

        self.ctx.kmesh_inpgen_labels = []
        self.ctx.kmesh_inpgen_results = []

        self.ctx.kpoints_labels = []
        self.ctx.kpoints_results = []

        self.ctx.smearing_labels = []
        self.ctx.smearing_results = []

    def _scf_inputs(self):
        inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        inputs.pop('inpgen', None)
        inputs.pop('calc_parameters', None)

        settings_dict = {}
        if 'settings' in inputs:
            settings_dict = inputs.settings.get_dict()

        settings_dict['skip_kpoint_parallelization_check'] = True
        inputs.settings = orm.Dict(dict=settings_dict)

        return inputs

    def _inpgen_base_inputs(self):
        inputs = AttributeDict()
        inputs.code = self.inputs.inpgen.code
        inputs.structure = self.inputs.structure

        inputs.metadata = AttributeDict()
        inputs.metadata.options = self.inputs.inpgen.options.get_dict()

        if 'parameters' in self.inputs.inpgen:
            inputs.parameters = self.inputs.inpgen.parameters
        if 'settings' in self.inputs.inpgen:
            inputs.settings = self.inputs.inpgen.settings

        return inputs

    def _extract_fleurinp_from_calc(self, calc):
        if 'fleurinp' in calc.outputs:
            return calc.outputs.fleurinp
        if 'output_fleurinp' in calc.outputs:
            return calc.outputs.output_fleurinp
        if 'fleurinpData' in calc.outputs:
            return calc.outputs.fleurinpData
        return None

    def _make_fleurinp_with_kmax(self, fleurinp: FleurinpData, kmax_value: float) -> FleurinpData:
        fm = FleurinpModifier(fleurinp)
        fm.set_inpchanges({
            'Kmax': float(kmax_value),
            'Gmax': float(3.0 * kmax_value),
            'GmaxXC': float(3.0 * kmax_value),
        })
        return fm.freeze()

    def _make_fleurinp_with_smearing(self, fleurinp: FleurinpData, smearing: float) -> FleurinpData:
        """
        Set the Fermi smearing energy in Htr.

        If your local modifier version does not accept the direct key
        'fermiSmearingEnergy', replace this with the corresponding XML modifier
        call for bzIntegration.
        """
        fm = FleurinpModifier(fleurinp)
        fm.set_inpchanges({
            'fermiSmearingEnergy': float(smearing),
        })
        return fm.freeze()

    def _make_inpgen_parameters_with_mesh(self, mesh):
        base = {}
        if 'parameters' in self.inputs.inpgen:
            base = self.inputs.inpgen.parameters.get_dict()

        kpt = dict(base.get('kpt', {}))
        kpt['div1'] = int(mesh[0])
        kpt['div2'] = int(mesh[1])
        kpt['div3'] = int(mesh[2])

        base['kpt'] = kpt
        return orm.Dict(dict=base)

    @staticmethod
    def _add_energy_deltas(results):
        prev_energy = None
        for entry in results:
            if prev_energy is None:
                entry['delta_to_previous_Htr'] = None
                entry['delta_to_previous_meV'] = None
            else:
                delta_htr = abs(entry['total_energy'] - prev_energy)
                entry['delta_to_previous_Htr'] = delta_htr
                entry['delta_to_previous_meV'] = delta_htr * 27.211386245988 * 1000.0
            prev_energy = entry['total_energy']

    @staticmethod
    def _determine_converged_value(results, key_name, tol_meV):
        converged = results[-1][key_name]
        for i in range(len(results)):
            tail = results[i + 1:]
            if not tail:
                converged = results[i][key_name]
                break
            if all(
                item['delta_to_previous_meV'] is not None and item['delta_to_previous_meV'] <= tol_meV
                for item in tail
            ):
                converged = results[i][key_name]
                break
        return converged

    def run_initial_inpgen(self):
        inputs = self._inpgen_base_inputs()
        future = self.submit(InpgenCalculation, **inputs)
        self.report('Submitted initial inpgen generation from structure')
        return ToContext(initial_inpgen=future)

    def inspect_initial_inpgen(self):
        calc = self.ctx.initial_inpgen

        if not calc.is_finished_ok:
            self.ctx.successful = False
            self.ctx.errors.append('Initial inpgen calculation failed')
            return self.exit_codes.ERROR_INITIAL_INPGEN_FAILED

        generated_fleurinp = self._extract_fleurinp_from_calc(calc)
        if generated_fleurinp is None:
            self.ctx.successful = False
            self.ctx.errors.append('Initial inpgen produced no FleurinpData')
            return self.exit_codes.ERROR_INITIAL_FLEURINP_MISSING

        self.ctx.initial_fleurinp = generated_fleurinp
        self.ctx.info.append(f'Initial FleurinpData generated from structure: {generated_fleurinp.uuid}')

    def run_kmax_series(self):
        calcs = {}
        for kmax in self.ctx.kmax_values:
            label = f'kmax_{kmax}'.replace('.', '_')
            inputs = self._scf_inputs()
            inputs.fleurinp = self._make_fleurinp_with_kmax(self.ctx.initial_fleurinp, kmax)
            future = self.submit(FleurScfWorkChain, **inputs)
            self.ctx.kmax_labels.append(label)
            calcs[label] = future
            self.report(f'Submitted Kmax convergence calculation for Kmax={kmax}')
        return ToContext(**calcs)

    def inspect_kmax_series(self):
        for label, kmax in zip(self.ctx.kmax_labels, self.ctx.kmax_values):
            calc = self.ctx[label]
            if not calc.is_finished_ok:
                self.ctx.successful = False
                self.ctx.warnings.append(f'Kmax run failed for {kmax}')
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()
            energy = outpara.get('total_energy', float('nan'))
            units = outpara.get('total_energy_units', 'Htr')

            self.ctx.kmax_results.append({
                'kmax': float(kmax),
                'gmax': float(3.0 * kmax),
                'gmaxxc': float(3.0 * kmax),
                'total_energy': float(energy),
                'total_energy_units': units,
                'distance_charge': outpara.get('distance_charge'),
                'distance_charge_units': outpara.get('distance_charge_units'),
                'scf_uuid': calc.uuid,
            })

        if not self.ctx.kmax_results:
            return self.exit_codes.ERROR_NO_SUCCESSFUL_KMAX_RUN

        self.ctx.kmax_results = sorted(self.ctx.kmax_results, key=lambda x: x['kmax'])
        self._add_energy_deltas(self.ctx.kmax_results)

    def determine_converged_kmax(self):
        tol = self.ctx.kmax_energy_tol_meV
        self.ctx.converged_kmax = float(self._determine_converged_value(self.ctx.kmax_results, 'kmax', tol))
        self.report(f'Converged Kmax = {self.ctx.converged_kmax} (criterion: all later ΔE <= {tol} meV)')
        self.ctx.info.append(f'Converged Kmax determined as {self.ctx.converged_kmax} with tolerance {tol} meV')

    def run_kmesh_inpgen_series(self):
        calcs = {}

        for mesh in self.ctx.kpoint_meshes:
            label = f'inpgen_{mesh[0]}x{mesh[1]}x{mesh[2]}'
            inputs = self._inpgen_base_inputs()
            inputs.parameters = self._make_inpgen_parameters_with_mesh(mesh)
            future = self.submit(InpgenCalculation, **inputs)
            self.ctx.kmesh_inpgen_labels.append(label)
            calcs[label] = future
            self.report(f'Submitted inpgen generation for mesh={mesh}')

        return ToContext(**calcs)

    def inspect_kmesh_inpgen_series(self):
        for label, mesh in zip(self.ctx.kmesh_inpgen_labels, self.ctx.kpoint_meshes):
            calc = self.ctx[label]
            if not calc.is_finished_ok:
                self.ctx.successful = False
                self.ctx.warnings.append(f'inpgen run failed for {mesh}')
                continue

            generated_fleurinp = self._extract_fleurinp_from_calc(calc)
            if generated_fleurinp is None:
                self.ctx.successful = False
                self.ctx.warnings.append(f'inpgen produced no FleurinpData for {mesh}')
                continue

            self.ctx.kmesh_inpgen_results.append({
                'mesh': list(mesh),
                'nkpts_full_grid': int(mesh[0] * mesh[1] * mesh[2]),
                'generated_fleurinp': generated_fleurinp,
                'inpgen_uuid': calc.uuid,
            })

        if not self.ctx.kmesh_inpgen_results:
            return self.exit_codes.ERROR_NO_SUCCESSFUL_KMESH_INPGEN_RUN

    def run_kpoints_series(self):
        calcs = {}
        for item in self.ctx.kmesh_inpgen_results:
            mesh = item['mesh']
            label = f'kpts_{mesh[0]}x{mesh[1]}x{mesh[2]}'

            inputs = self._scf_inputs()
            inputs.fleurinp = self._make_fleurinp_with_kmax(
                item['generated_fleurinp'],
                self.ctx.converged_kmax
            )

            future = self.submit(FleurScfWorkChain, **inputs)
            self.ctx.kpoints_labels.append(label)
            calcs[label] = future
            self.report(
                f'Submitted k-point convergence SCF for mesh={mesh} '
                f'at fixed Kmax={self.ctx.converged_kmax}'
            )

        return ToContext(**calcs)

    def inspect_kpoints_series(self):
        mesh_list = [item['mesh'] for item in self.ctx.kmesh_inpgen_results]

        for label, mesh in zip(self.ctx.kpoints_labels, mesh_list):
            calc = self.ctx[label]
            if not calc.is_finished_ok:
                self.ctx.successful = False
                self.ctx.warnings.append(f'k-point run failed for {mesh}')
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()
            energy = outpara.get('total_energy', float('nan'))
            units = outpara.get('total_energy_units', 'Htr')

            self.ctx.kpoints_results.append({
                'mesh': list(mesh),
                'nkpts_full_grid': int(mesh[0] * mesh[1] * mesh[2]),
                'kmax_used': float(self.ctx.converged_kmax),
                'gmax_used': float(3.0 * self.ctx.converged_kmax),
                'gmaxxc_used': float(3.0 * self.ctx.converged_kmax),
                'total_energy': float(energy),
                'total_energy_units': units,
                'distance_charge': outpara.get('distance_charge'),
                'distance_charge_units': outpara.get('distance_charge_units'),
                'scf_uuid': calc.uuid,
            })

        if not self.ctx.kpoints_results:
            return self.exit_codes.ERROR_NO_SUCCESSFUL_KPOINT_RUN

        self.ctx.kpoints_results = sorted(self.ctx.kpoints_results, key=lambda x: x['mesh'][0])
        self._add_energy_deltas(self.ctx.kpoints_results)

    def determine_converged_kpoints(self):
        tol = self.ctx.kpoints_energy_tol_meV
        self.ctx.converged_kpoint_mesh = list(self._determine_converged_value(self.ctx.kpoints_results, 'mesh', tol))
        self.report(f'Converged k-point mesh = {self.ctx.converged_kpoint_mesh} (criterion: all later ΔE <= {tol} meV)')
        self.ctx.info.append(f'Converged k-point mesh determined as {self.ctx.converged_kpoint_mesh} with tolerance {tol} meV')

        # keep the matching FleurinpData for Stage 3
        for item in self.ctx.kmesh_inpgen_results:
            if item['mesh'] == self.ctx.converged_kpoint_mesh:
                self.ctx.converged_kmesh_fleurinp = item['generated_fleurinp']
                break

    def run_smearing_series(self):
        calcs = {}

        base_fleurinp = self._make_fleurinp_with_kmax(
            self.ctx.converged_kmesh_fleurinp,
            self.ctx.converged_kmax
        )

        for smearing in self.ctx.smearing_values:
            label = f'smear_{str(smearing).replace(".", "_")}'
            inputs = self._scf_inputs()
            inputs.fleurinp = self._make_fleurinp_with_smearing(base_fleurinp, smearing)

            future = self.submit(FleurScfWorkChain, **inputs)
            self.ctx.smearing_labels.append(label)
            calcs[label] = future
            self.report(f'Submitted smearing convergence SCF for fermiSmearingEnergy={smearing} Htr')

        return ToContext(**calcs)

    def inspect_smearing_series(self):
        for label, smearing in zip(self.ctx.smearing_labels, self.ctx.smearing_values):
            calc = self.ctx[label]
            if not calc.is_finished_ok:
                self.ctx.successful = False
                self.ctx.warnings.append(f'smearing run failed for {smearing}')
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()
            energy = outpara.get('total_energy', float('nan'))
            units = outpara.get('total_energy_units', 'Htr')

            self.ctx.smearing_results.append({
                'smearing': float(smearing),
                'total_energy': float(energy),
                'total_energy_units': units,
                'distance_charge': outpara.get('distance_charge'),
                'distance_charge_units': outpara.get('distance_charge_units'),
                'scf_uuid': calc.uuid,
            })

        if not self.ctx.smearing_results:
            return self.exit_codes.ERROR_NO_SUCCESSFUL_SMEARING_RUN

        self.ctx.smearing_results = sorted(self.ctx.smearing_results, key=lambda x: x['smearing'])
        self._add_energy_deltas(self.ctx.smearing_results)

    def determine_converged_smearing(self):
        tol = self.ctx.smearing_energy_tol_meV
        self.ctx.converged_smearing = float(self._determine_converged_value(self.ctx.smearing_results, 'smearing', tol))
        self.report(f'Converged smearing = {self.ctx.converged_smearing} Htr (criterion: all later ΔE <= {tol} meV)')
        self.ctx.info.append(f'Converged smearing determined as {self.ctx.converged_smearing} Htr with tolerance {tol} meV')

    def return_results(self):
        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'successful': self.ctx.successful,
            'structure_uuid': self.inputs.structure.uuid,
            'initial_fleurinp_uuid': getattr(self.ctx, 'initial_fleurinp', None).uuid if hasattr(self.ctx, 'initial_fleurinp') else None,
            'kmax_values': self.ctx.kmax_values,
            'kpoint_meshes': self.ctx.kpoint_meshes,
            'smearing_values': self.ctx.smearing_values,
            'kmax_energy_tol_meV': self.ctx.kmax_energy_tol_meV,
            'kpoints_energy_tol_meV': self.ctx.kpoints_energy_tol_meV,
            'smearing_energy_tol_meV': self.ctx.smearing_energy_tol_meV,
            'converged_kmax': getattr(self.ctx, 'converged_kmax', None),
            'converged_kpoint_mesh': getattr(self.ctx, 'converged_kpoint_mesh', None),
            'converged_smearing': getattr(self.ctx, 'converged_smearing', None),
            'kmax_results': self.ctx.kmax_results,
            'kpoints_results': self.ctx.kpoints_results,
            'smearing_results': self.ctx.smearing_results,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
        }

        result_input = orm.Dict(dict=out)
        result_dict = create_result_node(result_input)
        self.out('output_convergence_wc_para', result_dict)

        plot_nodes = create_plot_nodes(result_input)
        self.out('output_kmax_plot', plot_nodes['output_kmax_plot'])
        self.out('output_kpoints_plot', plot_nodes['output_kpoints_plot'])
        self.out('output_smearing_plot', plot_nodes['output_smearing_plot'])

        if self.ctx.successful:
            self.report('Done, convergence workflow completed successfully')
        else:
            self.report('Done, but one or more convergence calculations failed')