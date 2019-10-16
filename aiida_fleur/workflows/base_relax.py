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
from aiida.orm import load_node
from aiida.plugins import WorkflowFactory, DataFactory
from aiida_fleur.common.workchain.base.restart import BaseRestartWorkChain
from aiida_fleur.common.workchain.utils import register_error_handler, ErrorHandlerReport

# pylint: disable=invalid-name
RelaxProcess = WorkflowFactory('fleur.relax')
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurBaseRelaxWorkChain(BaseRestartWorkChain):
    """Workchain to run Relax WorkChain with automated error handling and restarts"""
    _workflowversion = "0.1.0"

    _calculation_class = RelaxProcess
    # _error_handler_entry_point = 'aiida_fleur.workflow_error_handlers.pw.base'

    @classmethod
    def define(cls, spec):
        super(FleurBaseRelaxWorkChain, cls).define(spec)
        spec.expose_inputs(RelaxProcess)
        spec.input('description', valid_type=six.string_types, required=False, non_db=True,
                   help='Calculation description.')
        spec.input('label', valid_type=six.string_types, required=False, non_db=True,
                   help='Calculation label.')

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_calculation)(
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.results,
        )

        spec.expose_outputs(RelaxProcess)

        spec.exit_code(399, 'ERROR_SOMETHING_WENT_WRONG',
                       message='Something went wrong. More verbose output will be implemented.')
        spec.exit_code(230, 'ERROR_INVALID_INPUT_RESOURCES',
                       message='Neither the `options` nor `automatic_parallelisation` input was '
                       'specified.')

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


@register_error_handler(FleurBaseRelaxWorkChain, 50)
def _handle_not_conv_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in RelaxProcess.get_exit_statuses(['ERROR_DID_NOT_CONVERGE']):
        self.ctx.is_finished = False
        self.report('Relax WC did not lead to convergence, submit next RelaxWC')
        last_scf_calc = load_node(calculation.outputs.out.get_dict()['last_scf_wc_uuid'])
        last_fleur_calc = last_scf_calc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid']
        last_fleur_calc = load_node(last_fleur_calc)
        remote = last_fleur_calc.get_outgoing().get_node_by_label('remote_folder')

        self.ctx.inputs.remote = remote
        return ErrorHandlerReport(True, True)

@register_error_handler(FleurBaseRelaxWorkChain, 999)
def _handle_general_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status not in RelaxProcess.get_exit_statuses(['ERROR_DID_NOT_CONVERGE']):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for unknown reason, stop the Base workchain')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)
