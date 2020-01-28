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
This module contains the FleurBaseWorkChain.
FleurBaseWorkChain is a workchain that wraps the submission of
the FLEUR calculation. Inheritance from the BaseRestartWorkChain
allows to add scenarios to restart a calculation in an
automatic way if an expected failure occurred.
"""
from __future__ import absolute_import
from aiida_fleur.data.fleurinp import FleurinpData
import six

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.plugins import CalculationFactory, DataFactory
from aiida_fleur.common.workchain.base.restart import BaseRestartWorkChain
from aiida_fleur.tools.common_fleur_wf import optimize_calc_options
from aiida_fleur.common.workchain.utils import register_error_handler, ErrorHandlerReport

from aiida_fleur.calculation.fleur import FleurCalculation as FleurProcess


class FleurBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a FLEUR calculation with automated error handling and restarts"""
    _workflowversion = "0.1.0"

    _calculation_class = FleurProcess
    # _error_handler_entry_point = 'aiida_fleur.workflow_error_handlers.pw.base'

    @classmethod
    def define(cls, spec):
        super(FleurBaseWorkChain, cls).define(spec)
        spec.input('code', valid_type=orm.Code, help='The FLEUR code.')
        spec.input('parent_folder', valid_type=orm.RemoteData, required=False,
                   help='An optional working directory of a previously completed calculation to '
                   'restart from.')
        spec.input('settings', valid_type=orm.Dict, required=False,
                   help='Optional parameters to affect the way the calculation job and the parsing'
                   ' are performed.')
        spec.input('options', valid_type=orm.Dict,
                   help='Optional parameters to set up computational details.')
        spec.input('fleurinpdata', valid_type=FleurinpData,
                   help='Optional parameter set up a ready-to-use fleurinp.')
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

        spec.output('output_parameters', valid_type=orm.Dict, required=False)
        spec.output('output_params_complex', valid_type=orm.Dict, required=False)
        spec.output('relax_parameters', valid_type=orm.Dict, required=False)
        spec.output('retrieved', valid_type=orm.FolderData, required=False)
        spec.output('remote_folder', valid_type=orm.RemoteData, required=False)
        spec.output('final_calc_uuid', valid_type=orm.Str, required=False)

        spec.exit_code(311, 'ERROR_VACUUM_SPILL_RELAX',
                       message='FLEUR calculation failed because an atom spilled to the'
                               'vacuum during relaxation')
        spec.exit_code(313, 'ERROR_MT_RADII_RELAX',
                       message='Overlapping MT-spheres during relaxation.')
        spec.exit_code(390, 'ERROR_NOT_OPTIMAL_RESOURCES',
                       message="Computational resources are not optimal.")
        spec.exit_code(399, 'ERROR_SOMETHING_WENT_WRONG',
                       message='FleurCalculation failed and FleurBaseWorkChain has no strategy '
                               'to resolve this')

    def validate_inputs(self):
        """
        Validate inputs that might depend on each other and cannot be validated by the spec.
        Also define dictionary `inputs` in the context, that will contain the inputs for the
        calculation that will be launched in the `run_calculation` step.
        """
        self.ctx.inputs = AttributeDict({
            'code': self.inputs.code,
            'fleurinpdata': self.inputs.fleurinpdata,
            'metadata': AttributeDict()
        })

        self.ctx.inputs.metadata.options = self.inputs.options.get_dict()

        if 'parent_folder' in self.inputs:
            self.ctx.inputs.parent_folder = self.inputs.parent_folder

        if 'description' in self.inputs:
            self.ctx.inputs.metadata.description = self.inputs.description
        else:
            self.ctx.inputs.metadata.description = ''
        if 'label' in self.inputs:
            self.ctx.inputs.metadata.label = self.inputs.label
        else:
            self.ctx.inputs.metadata.label = ''

        if 'settings' in self.inputs:
            self.ctx.inputs.settings = self.inputs.settings.get_dict()
        else:
            self.ctx.inputs.settings = {}

        resources_input = self.ctx.inputs.metadata.options['resources']
        try:
            self.ctx.num_machines = int(resources_input['num_machines'])
            self.ctx.num_mpiprocs_per_machine = int(resources_input['num_mpiprocs_per_machine'])
        except KeyError:
            self.report('WARNING: Computation resources were not optimised.')
        else:
            try:
                self.check_kpts()
            except Warning:
                self.report('ERROR: Not optimal computational resources.')
                return self.exit_codes.ERROR_NOT_OPTIMAL_RESOURCES

    def check_kpts(self):
        """
        This routine checks if the total number of requested cpus
        is a factor of kpts and makes an optimisation.

        If suggested number of num_mpiprocs_per_machine is 60% smaller than
        requested, it throws an exit code and calculation stop withour submission.
        """
        fleurinp = self.ctx.inputs.fleurinpdata
        mach = self.ctx.num_machines
        procs = self.ctx.num_mpiprocs_per_machine
        adv_nodes, adv_cpu_nodes, message, exit_code = optimize_calc_options(fleurinp, mach, procs)

        self.report(message)

        if exit_code:
            raise Warning('Not optimal computational resources, load less than 60%')

        self.ctx.inputs.metadata.options['resources']['num_machines'] = adv_nodes
        self.ctx.inputs.metadata.options['resources']['num_mpiprocs_per_machine'] = adv_cpu_nodes


@register_error_handler(FleurBaseWorkChain, 999)
def _handle_general_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_FLEUR_CALC_FAILED', 'ERROR_MT_RADII']):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for unknown reason, stop the Base workchain')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)


@register_error_handler(FleurBaseWorkChain, 52)
def _handle_vacuum_spill_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_VACUUM_SPILL_RELAX']):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('FLEUR calculation failed because an atom spilled to the vacuum during'
                    'relaxation. Please, change the MT radii.')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_VACUUM_SPILL_RELAX)


@register_error_handler(FleurBaseWorkChain, 51)
def _handle_mt_relax_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_MT_RADII_RELAX']):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('FLEUR calculation failed due to MT overlap.')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_MT_RADII_RELAX)


@register_error_handler(FleurBaseWorkChain, 50)
def _handle_not_enough_memory(self, calculation):
    """
    Calculation failed due to lack of memory.
    Probably works for JURECA only, has to be tested for other systems.
    """

    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_NOT_ENOUGH_MEMORY']):
        self.ctx.restart_calc = None
        self.ctx.is_finished = False
        self.report('Calculation failed due to lack of memory, I resubmit it with twice larger'
                    ' amount of computational nodes')
        self.ctx.num_machines = self.ctx.num_machines * 2
        self.check_kpts()

        return ErrorHandlerReport(True, True)
