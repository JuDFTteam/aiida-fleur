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
the FLEUR calculation. Inheritence from the BaseRestartWorkChain
allows to add scenarious to restart a calculation in an
automatic way if an expected failure occured.
"""
from __future__ import absolute_import
import six

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.plugins import CalculationFactory, DataFactory
from aiida_fleur.common.workchain.base.restart import BaseRestartWorkChain
from aiida_fleur.tools.common_fleur_wf import optimize_calc_options

FleurProcess = CalculationFactory('fleur.fleur')
FleurInpData = DataFactory('fleur.fleurinp')

class FleurBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a FLEUR calculation with automated error handling and restarts"""

    _calculation_class = FleurProcess
    _error_handler_entry_point = 'aiida_fleur.workflow_error_handlers.pw.base'

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
        spec.input('fleurinpdata', valid_type=FleurInpData,
                   help='Optional parameter set up a ready-to-use fleurinp.')
        spec.input('description', valid_type=six.string_types, required=False, non_db=True,
                   help='Calculation description.')
        spec.input('label', valid_type=six.string_types, required=False, non_db=True,
                   help='Calculation label.')

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            cls.check_kpts,
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

        spec.exit_code(399, 'ERROR_SOMETHING_WENT_WRONG',
                       message='Something went wrong. More verbose output will be implemented.')
        spec.exit_code(303, 'ERROR_INVALID_INPUT_RESOURCES',
                       message='Neither the `options` nor `automatic_parallelization` input was '
                       'specified.')
        spec.exit_code(333, 'ERROR_NOT_OPTIMAL_RESOURSES',
                       message="Computational resourses are not optimal.")

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

        resourses_input = self.ctx.inputs.metadata.options['resources']
        try:
            self.ctx.num_machines = int(resourses_input['num_machines'])
            self.ctx.max_wallclock_seconds = int(resourses_input['num_mpiprocs_per_machine'])
        except KeyError:
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

    def check_kpts(self):
        """
        This routine checks if the total number of requested cpus
        is a factor of kpts and makes small optimisation.
        """
        fleurinp = self.ctx.inputs.fleurinpdata
        mach = self.ctx.num_machines
        procs = self.ctx.max_wallclock_seconds
        adv_nodes, adv_cpu_nodes, message, exit_code = optimize_calc_options(fleurinp, mach, procs)

        self.report(message)

        if exit_code:
            self.report('ERROR: Not optimal computational resourses.')
            return self.exit_codes.ERROR_NOT_OPTIMAL_RESOURSES

        self.ctx.inputs.metadata.options['resources']['num_machines'] = adv_nodes
        self.ctx.inputs.metadata.options['resources']['num_mpiprocs_per_machine'] = adv_cpu_nodes