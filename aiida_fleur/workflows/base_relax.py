# -*- coding: utf-8 -*-
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
from __future__ import absolute_import
import six

from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.orm import load_node, Dict
from aiida.plugins import WorkflowFactory, DataFactory
from aiida_fleur.common.workchain.base.restart import BaseRestartWorkChain
from aiida_fleur.common.workchain.utils import register_error_handler, ErrorHandlerReport

# pylint: disable=invalid-name
RelaxProcess = WorkflowFactory('fleur.relax')
FleurinpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name


class FleurBaseRelaxWorkChain(BaseRestartWorkChain):
    """Workchain to run Relax WorkChain with automated error handling and restarts"""
    _workflowversion = '0.1.2'

    _calculation_class = RelaxProcess
    # _error_handler_entry_point = 'aiida_fleur.workflow_error_handlers.pw.base'

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(RelaxProcess)
        spec.input('description',
                   valid_type=six.string_types,
                   required=False,
                   non_db=True,
                   help='Calculation description.')
        spec.input('label', valid_type=six.string_types, required=False, non_db=True, help='Calculation label.')

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_calculation)(
                cls.run_calculation,
                cls.inspect_calculation,
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

    def pop_non_stacking_inpxml_changes(self):
        """
        pops some inpxml_changes that do not stack, for example shift_value.
        """
        if 'wf_parameters' in self.ctx.inputs.scf:
            wf_param = self.ctx.inputs.scf.wf_parameters.get_dict()
        else:
            wf_param = {}

        if 'inpxml_changes' not in wf_param:
            return

        self.report('Removing shift_value methods from subsequent Relax submissions')

        old_changes = wf_param['inpxml_changes']
        new_changes = []
        for change in old_changes:
            if 'shift_value' not in change[0]:
                new_changes.append(change)
        wf_param['inpxml_changes'] = new_changes
        self.ctx.inputs.scf.wf_parameters = Dict(dict=wf_param)


@register_error_handler(FleurBaseRelaxWorkChain, 50)
def _handle_not_conv_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in RelaxProcess.get_exit_statuses(['ERROR_DID_NOT_RELAX']):
        self.ctx.is_finished = False
        self.report('Relax WC did not lead to convergence, submit next RelaxWC')
        last_scf_calc = load_node(calculation.outputs.output_relax_wc_para.get_dict()['last_scf_wc_uuid'])
        last_fleur_calc = last_scf_calc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid']
        last_fleur_calc = load_node(last_fleur_calc)
        remote = last_fleur_calc.get_outgoing().get_node_by_label('remote_folder')
        if 'wf_parameters' in self.ctx.inputs:
            parameters = self.ctx.inputs.wf_parameters
            run_final = parameters.get_dict().get('run_final_scf', False)
        else:
            run_final = False

        self.ctx.inputs.scf.remote_data = remote
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

        return ErrorHandlerReport(True, True)


@register_error_handler(FleurBaseRelaxWorkChain, 49)
def _handle_switch_to_bfgs(self, calculation):
    """
    SCF can be switched to BFGS. For now cdn and relax.xml are kept because the current progress is
    treated as successful.
    """
    if calculation.exit_status in RelaxProcess.get_exit_statuses(['ERROR_SWITCH_BFGS']):
        self.ctx.is_finished = False
        self.report('It is time to switch from straight to BFGS relaxation')
        last_scf_calc = load_node(calculation.outputs.output_relax_wc_para.get_dict()['last_scf_wc_uuid'])
        last_fleur_calc = last_scf_calc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid']
        last_fleur_calc = load_node(last_fleur_calc)
        remote = last_fleur_calc.get_outgoing().get_node_by_label('remote_folder')
        if 'wf_parameters' in self.ctx.inputs:
            parameters = self.ctx.inputs.wf_parameters
            run_final = parameters.get_dict().get('run_final_scf', False)
        else:
            run_final = False

        self.ctx.inputs.scf.remote_data = remote

        scf_para = self.ctx.inputs.scf.wf_parameters.get_dict()
        scf_para['force_dict']['forcemix'] = 'BFGS'
        self.ctx.inputs.scf.wf_parameters = Dict(dict=scf_para)

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

        return ErrorHandlerReport(True, True)


@register_error_handler(FleurBaseRelaxWorkChain, 1)
def _handle_general_error(self, calculation):
    """
    Calculation failed for a reason that can not be fixed automatically.
    """
    if calculation.exit_status in RelaxProcess.get_exit_statuses(
        ['ERROR_INVALID_INPUT_PARAM', 'ERROR_SCF_FAILED', 'ERROR_NO_RELAX_OUTPUT', 'ERROR_NO_SCF_OUTPUT']):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for a reason that can not be fixed automatically')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)
    else:
        raise ValueError('Calculation failed for unknown reason, please register the '
                         'corresponding exit code in this error handler')


@register_error_handler(FleurBaseRelaxWorkChain, 100)
def _handle_vacuum_spill(self, calculation):
    """
    Calculation failed because atom spilled to the vacuum region.
    """
    if calculation.exit_status in RelaxProcess.get_exit_statuses(['ERROR_VACUUM_SPILL_RELAX']):
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
        self.report('Relax WC failed because atom was spilled to the vacuum, I change the vacuum ' 'parameter')
        wf_para_dict = self.ctx.inputs.scf.wf_parameters.get_dict()
        inpxml_changes = wf_para_dict.get('inpxml_changes', [])
        inpxml_changes.append(('shift_value', {'change_dict': {'dTilda': 0.2, 'dVac': 0.2}}))
        wf_para_dict['inpxml_changes'] = inpxml_changes
        self.ctx.inputs.scf.wf_parameters = Dict(dict=wf_para_dict)
        return ErrorHandlerReport(True, True)


@register_error_handler(FleurBaseRelaxWorkChain, 101)
def _handle_mt_overlap(self, calculation):
    """
    Calculation failed because MT overlapped during calculation.
    """
    if calculation.exit_status in RelaxProcess.get_exit_statuses(['ERROR_MT_RADII_RELAX']):
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

        last_scf_wc_uuid = calculation.outputs.output_relax_wc_para.get_dict()['last_scf_wc_uuid']
        last_scf = load_node(last_scf_wc_uuid)
        last_fleur = load_node(last_scf.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])
        error_params = last_fleur.outputs.error_params.get_dict()
        label1 = int(error_params['overlapped_indices'][0])
        label2 = int(error_params['overlapped_indices'][1])
        value = -(float(error_params['overlaping_value']) + 0.01) / 2

        self.ctx.is_finished = False
        self.report('Relax WC failed because MT overlapped during relaxation. Try to fix this')
        wf_para_dict = self.ctx.inputs.scf.wf_parameters.get_dict()

        if value < -0.2 and error_params['iteration_number'] >= 3:
            wf_para_dict['force_dict']['forcealpha'] = wf_para_dict['force_dict']['forcealpha'] * 1.5
            wf_para_dict['force_dict']['forcemix'] = 'straight'

            self_wf_para = self.ctx.inputs.wf_parameters.get_dict()
            self_wf_para['change_mixing_criterion'] = self_wf_para['change_mixing_criterion'] / 1.25
            self.ctx.inputs.wf_parameters = Dict(dict=self_wf_para)
            self.report('Seems it is too early for BFGS. I switch back to straight mixing'
                        ' and reduce change_mixing_criterion by a factor of 1.25')
        elif value < -0.1 and error_params['iteration_number'] == 2:
            wf_para_dict['force_dict']['forcealpha'] = wf_para_dict['force_dict']['forcealpha'] / 2
            self.report('forcealpha might be too large.')
        else:  # reduce MT radii
            self.report('MT radii might be too large.')
            inpxml_changes = wf_para_dict.get('inpxml_changes', [])
            inpxml_changes.append(('shift_value_species_label', {
                'label': '{: >20}'.format(label1),
                'att_name': 'radius',
                'value': value,
                'mode': 'abs'
            }))
            inpxml_changes.append(('shift_value_species_label', {
                'label': '{: >20}'.format(label2),
                'att_name': 'radius',
                'value': value,
                'mode': 'abs'
            }))
            wf_para_dict['inpxml_changes'] = inpxml_changes

        self.ctx.inputs.scf.wf_parameters = Dict(dict=wf_para_dict)
        return ErrorHandlerReport(True, True)


def find_inputs_relax(remote_node):
    """
    Finds the original inputs of the relaxation workchain which can be either
    FleurinpData or structure+inpgen+calc_param.
    """
    from aiida.orm import WorkChainNode
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
    elif 'fleurinp' in scf_wc_node.inputs:
        return scf_wc_node.inputs.fleurinp

    raise ValueError('Did not find original inputs for Relax WC')
