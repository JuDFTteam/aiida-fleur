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
This module contains the FleurBaseRelaxWorkChain.
FleurBaseRelaxWorkChain is a workchain that wraps the submission of
the Relax workchain. Inheritance from the BaseRestartWorkChain
allows to add scenarios to restart a calculation in an
automatic way if an expected failure occurred.
"""

from aiida.common import AttributeDict
from aiida.common.exceptions import ValidationError
from aiida.engine import while_
from aiida.orm import Dict, WorkChainNode
from aiida.plugins import WorkflowFactory, DataFactory
from aiida.engine.processes.workchains import BaseRestartWorkChain
from aiida.engine.processes.workchains.utils import process_handler, ProcessHandlerReport

from masci_tools.util.schema_dict_util import evaluate_attribute

# pylint: disable=invalid-name
RelaxProcess = WorkflowFactory('fleur.relax')
FleurinpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name


class FleurBaseRelaxWorkChain(BaseRestartWorkChain):
    """Workchain to run Relax WorkChain with automated error handling and restarts"""
    _workflowversion = '0.3.0'

    _process_class = RelaxProcess

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(RelaxProcess)
        spec.input('description', valid_type=str, required=False, non_db=True, help='Calculation description.')
        spec.input('label', valid_type=str, required=False, non_db=True, help='Calculation label.')

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_process)(
                cls.set_pop_shift,
                cls.run_process,
                cls.inspect_process,
                cls.pop_non_stacking_inpxml_changes,
            ),
            cls.results,
        )

        spec.expose_outputs(RelaxProcess)

        spec.exit_code(399,
                       'ERROR_SOMETHING_WENT_WRONG',
                       message='FleurRelaxWorkChain failed and FleurBaseRelaxWorkChain has no'
                       ' strategy to resolve this')

    def validate_inputs(self):
        """
        Validate inputs that might depend on each other and cannot be validated by the spec.
        Also define dictionary `inputs` in the context, that will contain the inputs for the
        calculation that will be launched in the `run_calculation` step.
        """
        self.ctx.inputs = AttributeDict(self.exposed_inputs(RelaxProcess))

        if 'description' in self.inputs:
            self.ctx.inputs.metadata.description = self.inputs.description
        else:
            self.ctx.inputs.metadata.description = ''
        if 'label' in self.inputs:
            self.ctx.inputs.metadata.label = self.inputs.label
        else:
            self.ctx.inputs.metadata.label = ''

        if 'wf_parameters' in self.ctx.inputs.scf:
            self.ctx.initial_mixing = self.ctx.inputs.scf.wf_parameters.get_dict()['force_dict']['forcemix']
        else:
            self.ctx.initial_mixing = 'BFGS'

    def set_pop_shift(self):
        """
        Sets use_stashed_shift_methods to False.
        Whenever this function is entered it means that shift_value changes were already set
        """
        self.ctx.use_stashed_shift_methods = False
        self.ctx.fixing_methods = []

    def pop_non_stacking_inpxml_changes(self):
        """
        pops some inpxml_changes that do not stack, for example shift_value.
        """

        if 'wf_parameters' in self.ctx.inputs.scf:
            wf_param = self.ctx.inputs.scf.wf_parameters.get_dict()
        else:
            wf_param = {}

        old_changes = wf_param.get('inpxml_changes', [])
        new_changes = []
        stashed_changes = []

        if self.ctx.use_stashed_shift_methods:  # if calculation is restarted from scratch, re-apply all shift methods
            self.report('INFO: Returning all shift_value methods')
            new_changes.extend(old_changes)
            if 'shift_value_methods_stash' in self.ctx:
                new_changes.extend(self.ctx.shift_value_methods_stash)
            new_changes.extend(self.ctx.fixing_methods)
            self.ctx.fixing_methods = []
        elif not self.ctx.fixing_methods:  # if fixing_methods are not empty, we should use them
            self.report('INFO: Removing shift_value methods from subsequent Relax submissions')
            for change in old_changes:
                if 'shift_value' not in change[0]:
                    new_changes.append(change)
                else:
                    stashed_changes.append(change)
            self.ctx.shift_value_methods_stash = stashed_changes
        else:
            raise ValidationError('Stashed methods are not used and fixing_methods is not empty')

        wf_param['inpxml_changes'] = new_changes
        self.ctx.inputs.scf.wf_parameters = Dict(wf_param)

    # @process_handler(priority=50, exit_codes=RelaxProcess.exit_codes.ERROR_DID_NOT_RELAX)
    # def _handle_not_conv_error(self, calculation):
    #     """
    #     Calculation failed for unknown reason.
    #     """

    #     self.ctx.is_finished = False
    #     self.report('Relax WC did not lead to convergence, submit next RelaxWC')
    #     last_scf_calc = load_node(calculation.outputs.output_relax_wc_para.get_dict()['last_scf_wc_uuid'])
    #     last_fleur_calc = last_scf_calc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid']
    #     last_fleur_calc = load_node(last_fleur_calc)
    #     remote = last_fleur_calc.get_outgoing().get_node_by_label('remote_folder')
    #     if 'wf_parameters' in self.ctx.inputs:
    #         parameters = self.ctx.inputs.wf_parameters
    #         run_final = parameters.get_dict().get('run_final_scf', False)
    #     else:
    #         run_final = False

    #     self.ctx.inputs.scf.remote_data = remote
    #     if 'structure' in self.ctx.inputs.scf:
    #         del self.ctx.inputs.scf.structure
    #     if 'inpgen' in self.ctx.inputs.scf:
    #         if run_final:
    #             self.ctx.inputs.final_scf.inpgen = self.ctx.inputs.scf.inpgen
    #         del self.ctx.inputs.scf.inpgen
    #     if 'calc_parameters' in self.ctx.inputs.scf:
    #         if run_final and 'calc_parameters' not in self.ctx.inputs.final_scf:
    #             self.ctx.inputs.final_scf.calc_parameters = self.ctx.inputs.scf.calc_parameters
    #         del self.ctx.inputs.scf.calc_parameters

    #     return ProcessHandlerReport(True)

    @process_handler(priority=49, exit_codes=RelaxProcess.exit_codes.ERROR_SWITCH_BFGS)
    def _handle_switch_to_bfgs(self, calculation):
        """
        SCF can be switched to BFGS. For now cdn and relax.xml are kept because the current progress is
        treated as successful.
        """

        self.ctx.is_finished = False
        self.report('It is time to switch from straight to BFGS relaxation')
        remote = calculation.outputs.last_scf.last_calc.remote_folder
        if 'wf_parameters' in self.ctx.inputs:
            parameters = self.ctx.inputs.wf_parameters
            run_final = parameters.get_dict().get('run_final_scf', False)
        else:
            run_final = False

        self.ctx.inputs.scf.remote_data = remote

        scf_para = self.ctx.inputs.scf.wf_parameters.get_dict()
        scf_para['force_dict']['forcemix'] = 'BFGS'
        self.ctx.inputs.scf.wf_parameters = Dict(scf_para)

        if 'structure' in self.ctx.inputs.scf:
            del self.ctx.inputs.scf.structure
        if 'inpgen' in self.ctx.inputs.scf:
            if run_final:
                self.ctx.inputs.final_scf.inpgen = self.ctx.inputs.scf.inpgen
            del self.ctx.inputs.scf.inpgen
        if 'calc_parameters' in self.ctx.inputs.scf:
            if run_final and 'calc_parameters' not in self.ctx.inputs.final_scf:
                self.ctx.inputs.final_scf.calc_parameters = self.ctx.inputs.scf.calc_parameters
            del self.ctx.inputs.scf.calc_parameters

        return ProcessHandlerReport(True)

    @process_handler(priority=1,
                     exit_codes=[
                         RelaxProcess.exit_codes.ERROR_INVALID_INPUT_PARAM,
                         RelaxProcess.exit_codes.ERROR_SCF_FAILED,
                         RelaxProcess.exit_codes.ERROR_NO_RELAX_OUTPUT,
                         RelaxProcess.exit_codes.ERROR_NO_SCF_OUTPUT,
                         RelaxProcess.exit_codes.ERROR_DID_NOT_RELAX,
                     ])
    def _handle_general_error(self, calculation):
        """
        Calculation failed for a reason that can not be fixed automatically.
        """

        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for a reason that can not be fixed automatically')
        self.results()
        return ProcessHandlerReport(True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)

    @process_handler(priority=100, exit_codes=RelaxProcess.exit_codes.ERROR_VACUUM_SPILL_RELAX)
    def _handle_vacuum_spill(self, calculation):
        """
        Calculation failed because atom spilled to the vacuum region.
        """

        if 'remote_data' in self.ctx.inputs.scf:
            inputs = find_inputs_relax(self.ctx.inputs.scf.remote_data)
            del self.ctx.inputs.scf.remote_data
            if isinstance(inputs, FleurinpData):
                self.ctx.inputs.scf.fleurinp = inputs
            else:
                self.ctx.inputs.scf.structure = inputs[0]
                self.ctx.inputs.scf.inpgen = inputs[1]
                if len(inputs) == 3:
                    self.ctx.inputs.scf.calc_parameters = inputs[2]

        self.ctx.is_finished = False
        self.report('Relax WC failed because atom was spilled to the vacuum, I change the vacuum parameter')

        wf_para_dict = self.ctx.inputs.scf.wf_parameters.get_dict()
        if wf_para_dict['force_dict']['forcemix'] != self.ctx.initial_mixing:
            wf_para_dict['force_dict']['forcemix'] = self.ctx.initial_mixing
            self.ctx.inputs.scf.wf_parameters = Dict(wf_para_dict)

        self.ctx.use_stashed_shift_methods = True
        self.ctx.fixing_methods = [('shift_value', {'change_dict': {'dTilda': 0.2, 'dVac': 0.2}})]

        return ProcessHandlerReport(True)

    @process_handler(priority=101, exit_codes=RelaxProcess.exit_codes.ERROR_MT_RADII_RELAX)
    def _handle_mt_overlap(self, calculation):
        """
        Calculation failed because MT overlapped during calculation.
        """

        if 'remote_data' in self.ctx.inputs.scf:
            inputs = find_inputs_relax(self.ctx.inputs.scf.remote_data)
            del self.ctx.inputs.scf.remote_data
            if isinstance(inputs, FleurinpData):
                self.ctx.inputs.scf.fleurinp = inputs
            else:
                self.ctx.inputs.scf.structure = inputs[0]
                self.ctx.inputs.scf.inpgen = inputs[1]
                if len(inputs) == 3:
                    self.ctx.inputs.scf.calc_parameters = inputs[2]

        error_params = calculation.outputs.last_scf.last_calc.error_params.get_dict()
        label1 = int(error_params['overlapped_indices'][0])
        label2 = int(error_params['overlapped_indices'][1])
        value = -(float(error_params['overlaping_value']) + 0.01) / 2

        self.ctx.is_finished = False
        self.report('Relax WC failed because MT overlapped during relaxation. Try to fix this')
        wf_para_dict = self.ctx.inputs.scf.wf_parameters.get_dict()

        xmltree, schema_dict = calculation.outputs.last_scf.fleurinp.load_inpxml()
        mixing = evaluate_attribute(xmltree, schema_dict, 'forcemix', optional=True)
        if not mixing:
            mixing = 'BFGS'

        if value < -0.2 and error_params['iteration_number'] >= 3 and mixing == 'BFGS':
            self.ctx.initial_mixing = 'straight'

            self_wf_para = self.ctx.inputs.wf_parameters.get_dict()
            self_wf_para['change_mixing_criterion'] = self_wf_para['change_mixing_criterion'] / 1.4
            self.ctx.inputs.wf_parameters = Dict(self_wf_para)
            self.report('Seems it is too early for BFGS. I switch back to straight mixing'
                        ' and reduce change_mixing_criterion by a factor of 1.25')
        elif error_params['iteration_number'] == 2:
            wf_para_dict['force_dict']['forcealpha'] = wf_para_dict['force_dict']['forcealpha'] / 2
            self.report('forcealpha might be too large.')
        else:  # reduce MT radii
            self.report('MT radii might be too large. I reduce them.')

            self.ctx.fixing_methods = [('shift_value_species_label', {
                'label': f'{label1: >20}',
                'att_name': 'radius',
                'value': value,
                'mode': 'abs'
            })]

            self.ctx.fixing_methods.append(('shift_value_species_label', {
                'label': f'{label2: >20}',
                'att_name': 'radius',
                'value': value,
                'mode': 'abs'
            }))

        self.ctx.use_stashed_shift_methods = True  # even if we set mixing only, calculation should restart from scratch

        if wf_para_dict['force_dict']['forcemix'] != self.ctx.initial_mixing:
            wf_para_dict['force_dict']['forcemix'] = self.ctx.initial_mixing
            self.ctx.inputs.scf.wf_parameters = Dict(wf_para_dict)

        return ProcessHandlerReport(True)


def find_inputs_relax(remote_node):
    """
    Finds the original inputs of the relaxation workchain which can be either
    FleurinpData or structure+inpgen+calc_param.
    """
    inc_nodes = remote_node.get_incoming().all()
    for link in inc_nodes:
        if isinstance(link.node, WorkChainNode):
            base_wc = link.node
            break

    scf_wc_node = base_wc.get_incoming().get_node_by_label('CALL')

    if 'remote_data' in scf_wc_node.inputs:
        return find_inputs_relax(scf_wc_node.inputs.remote_data)

    if 'structure' in scf_wc_node.inputs:
        if 'calc_parameters' in scf_wc_node.inputs:
            return scf_wc_node.inputs.structure, scf_wc_node.inputs.inpgen, scf_wc_node.inputs.calc_parameters
        return scf_wc_node.inputs.structure, scf_wc_node.inputs.inpgen

    if 'fleurinp' in scf_wc_node.inputs:
        return scf_wc_node.inputs.fleurinp

    raise ValueError('Did not find original inputs for Relax WC')
