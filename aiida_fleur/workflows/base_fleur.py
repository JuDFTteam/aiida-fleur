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
import six

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.plugins import CalculationFactory, DataFactory
from aiida_fleur.common.workchain.base.restart import BaseRestartWorkChain
from aiida_fleur.tools.common_fleur_wf import optimize_calc_options
from aiida_fleur.common.workchain.utils import register_error_handler, ErrorHandlerReport
from aiida_fleur.calculation.fleur import FleurCalculation as FleurProcess
from aiida_fleur.data.fleurinp import FleurinpData


class FleurBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a FLEUR calculation with automated error handling and restarts"""
    _workflowversion = '0.1.1'

    _calculation_class = FleurProcess
    # _error_handler_entry_point = 'aiida_fleur.workflow_error_handlers.pw.base'

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('code', valid_type=orm.Code, help='The FLEUR code.')
        spec.input('parent_folder',
                   valid_type=orm.RemoteData,
                   required=False,
                   help='An optional working directory of a previously completed calculation to '
                   'restart from.')
        spec.input('settings',
                   valid_type=orm.Dict,
                   required=False,
                   help='Optional parameters to affect the way the calculation job and the parsing'
                   ' are performed.')
        spec.input('options', valid_type=orm.Dict, help='Optional parameters to set up computational details.')
        spec.input('fleurinpdata', valid_type=FleurinpData, help='Optional parameter set up a ready-to-use fleurinp.')
        spec.input('description',
                   valid_type=six.string_types,
                   required=False,
                   non_db=True,
                   help='Calculation description.')
        spec.input('label', valid_type=six.string_types, required=False, non_db=True, help='Calculation label.')
        spec.input(
            'add_comp_para',
            valid_type=orm.Dict,
            default=lambda: orm.Dict(dict={
                'only_even_MPI': False,
                'max_queue_nodes': 20,
                'max_queue_wallclock_sec': 86400
            }),
            help='Gives additional control over computational parameters'
            'only_even_MPI: set to true if you want to suppress odd number of MPI processes in parallelisation.'
            'This might speedup a calculation for machines having even number of sockets per node.'
            'max_queue_nodes: maximal number of nodes allowed on the remote machine. Used only to automatically solve some FLEUR failures.'
            'max_queue_wallclock_sec: maximal wallclock time allowed on the remote machine. Used only to automatically solve some FLEUR failures.'
        )

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

        spec.exit_code(311,
                       'ERROR_VACUUM_SPILL_RELAX',
                       message='FLEUR calculation failed because an atom spilled to the'
                       'vacuum during relaxation')
        spec.exit_code(313, 'ERROR_MT_RADII_RELAX', message='Overlapping MT-spheres during relaxation.')
        spec.exit_code(315,
                       'ERROR_INVALID_ELEMENTS_MMPMAT',
                       message='The LDA+U density matrix contains invalid elements.'
                       ' Consider a less aggresive mixing scheme')
        spec.exit_code(389, 'ERROR_MEMORY_ISSUE_NO_SOLUTION', message='Computational resources are not optimal.')
        spec.exit_code(390, 'ERROR_NOT_OPTIMAL_RESOURCES', message='Computational resources are not optimal.')
        spec.exit_code(399,
                       'ERROR_SOMETHING_WENT_WRONG',
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

        self.ctx.max_queue_nodes = self.inputs.add_comp_para['max_queue_nodes']
        self.ctx.max_queue_wallclock_sec = self.inputs.add_comp_para['max_queue_wallclock_sec']

        input_options = self.inputs.options.get_dict()
        self.ctx.optimize_resources = input_options.pop('optimize_resources', False)
        self.ctx.inputs.metadata.options = input_options

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

        if not self.ctx.optimize_resources:
            self.ctx.can_be_optimised = False  # set this for handlers to not change resources
            return

        resources_input = self.ctx.inputs.metadata.options['resources']
        try:
            self.ctx.num_machines = int(resources_input['num_machines'])
            self.ctx.num_mpiprocs_per_machine = int(resources_input['num_mpiprocs_per_machine'])
        except KeyError:
            self.ctx.can_be_optimised = False
            self.report('WARNING: Computation resources were not optimised.')
        else:
            try:
                self.ctx.num_cores_per_mpiproc = int(resources_input['num_cores_per_mpiproc'])
                self.ctx.use_omp = True
                self.ctx.suggest_mpi_omp_ratio = self.ctx.num_mpiprocs_per_machine / self.ctx.num_cores_per_mpiproc
            except KeyError:
                self.ctx.num_cores_per_mpiproc = 1
                self.ctx.use_omp = False
                self.ctx.suggest_mpi_omp_ratio = 1

            try:
                self.check_kpts()
                self.ctx.can_be_optimised = True
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
        machines = self.ctx.num_machines
        mpi_proc = self.ctx.num_mpiprocs_per_machine
        omp_per_mpi = self.ctx.num_cores_per_mpiproc
        only_even_MPI = self.inputs.add_comp_para['only_even_MPI']
        try:
            adv_nodes, adv_mpi_tasks, adv_omp_per_mpi, message = optimize_calc_options(machines,
                                                                                       mpi_proc,
                                                                                       omp_per_mpi,
                                                                                       self.ctx.use_omp,
                                                                                       self.ctx.suggest_mpi_omp_ratio,
                                                                                       fleurinp,
                                                                                       only_even_MPI=only_even_MPI)
        except ValueError as exc:
            raise Warning('Not optimal computational resources, load less than 60%') from exc

        self.report(message)

        self.ctx.inputs.metadata.options['resources']['num_machines'] = adv_nodes
        self.ctx.inputs.metadata.options['resources']['num_mpiprocs_per_machine'] = adv_mpi_tasks
        if self.ctx.use_omp:
            self.ctx.inputs.metadata.options['resources']['num_cores_per_mpiproc'] = adv_omp_per_mpi
            if self.ctx.inputs.metadata.options['environment_variables']:
                self.ctx.inputs.metadata.options['environment_variables']['OMP_NUM_THREADS'] = str(adv_omp_per_mpi)
            else:
                self.ctx.inputs.metadata.options['environment_variables'] = {}
                self.ctx.inputs.metadata.options['environment_variables']['OMP_NUM_THREADS'] = str(adv_omp_per_mpi)


@register_error_handler(FleurBaseWorkChain, 1)
def _handle_general_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in FleurProcess.get_exit_statuses([
            'ERROR_FLEUR_CALC_FAILED', 'ERROR_MT_RADII', 'ERROR_NO_RETRIEVED_FOLDER', 'ERROR_OPENING_OUTPUTS',
            'ERROR_NO_OUTXML', 'ERROR_XMLOUT_PARSING_FAILED', 'ERROR_RELAX_PARSING_FAILED'
    ]):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for a reason that can not be resolved automatically')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)
    else:
        raise ValueError('Calculation failed for unknown reason, please register the '
                         'corresponding exit code in this error handler')


@register_error_handler(FleurBaseWorkChain, 48)
def _handle_dirac_equation(self, calculation):
    """
    Sometimes relaxation calculation fails with Diraq problem which is usually caused by
    problems with reusing charge density. In this case we resubmit the calculation, dropping the input cdn.
    """

    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_DROP_CDN']):

        # try to drop remote folder and see if it helps
        is_fleurinp_from_relax = False
        if 'fleurinpdata' in self.ctx.inputs:
            if 'relax.xml' in self.ctx.inputs.fleurinpdata.files:
                is_fleurinp_from_relax = True

        if 'parent_folder' in self.ctx.inputs and is_fleurinp_from_relax:
            del self.ctx.inputs.parent_folder
            self.ctx.restart_calc = None
            self.ctx.is_finished = False
            self.report('Calculation seems to fail due to corrupted charge density (can happen'
                        'during relaxation). I drop cdn from previous step')
            return ErrorHandlerReport(True, True)

        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Can not drop charge density. If I drop the remote folder, there will be' 'no inp.xml')
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
                    'relaxation. Can be fixed via RelaxBaseWorkChain.')
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
        self.report('FLEUR calculation failed due to MT overlap.' ' Can be fixed via RelaxBaseWorkChain')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_MT_RADII_RELAX)


@register_error_handler(FleurBaseWorkChain, 51)
def _handle_invalid_elements_mmpmat(self, calculation):
    """
    Calculation failed due to invalid elements in the LDA+U density matrix.
    Mixing history is reset.
    TODO: HOw to handle consecutive errors
    """
    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_INVALID_ELEMENTS_MMPMAT']):
        self.ctx.restart_calc = None
        self.ctx.is_finished = False
        self.report('FLEUR calculation failed due to invalid elements in mmpmat. Resetting mixing_history')

        if 'settings' not in self.ctx.inputs:
            self.ctx.inputs.settings = {}
        else:
            self.ctx.inputs.settings = self.inputs.settings.get_dict()
        self.ctx.inputs.settings.setdefault('remove_from_remotecopy_list', []).append('mixing_history*')
        return ErrorHandlerReport(True, True)


@register_error_handler(FleurBaseWorkChain, 50)
def _handle_not_enough_memory(self, calculation):
    """
    Calculation failed due to lack of memory.
    Probably works for JURECA only, has to be tested for other systems.
    """

    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_NOT_ENOUGH_MEMORY']):
        if self.ctx.can_be_optimised:
            self.ctx.restart_calc = None
            self.ctx.is_finished = False
            self.report('Calculation failed due to lack of memory, I resubmit it with twice larger'
                        ' amount of computational nodes and smaller MPI/OMP ratio')

            # increase number of nodes
            propose_nodes = self.ctx.num_machines * 2
            if propose_nodes > self.ctx.max_queue_nodes:
                propose_nodes = self.ctx.max_queue_nodes
            self.ctx.num_machines = propose_nodes

            self.ctx.suggest_mpi_omp_ratio = self.ctx.suggest_mpi_omp_ratio / 2
            self.check_kpts()

            if 'settings' not in self.ctx.inputs:
                self.ctx.inputs.settings = {}
            else:
                self.ctx.inputs.settings = self.inputs.settings.get_dict()
            self.ctx.inputs.settings.setdefault('remove_from_remotecopy_list', []).append('mixing_history*')

            return ErrorHandlerReport(True, True)
        else:
            self.ctx.restart_calc = calculation
            self.ctx.is_finished = True
            self.report('I am not allowed to optimize your settings. Consider providing at least'
                        'num_machines and num_mpiprocs_per_machine')
            self.results()
            return ErrorHandlerReport(True, True, self.exit_codes.ERROR_MEMORY_ISSUE_NO_SOLUTION)


@register_error_handler(FleurBaseWorkChain, 47)
def _handle_time_limits(self, calculation):
    """
    If calculation fails due to time limits, we simply resubmit it.
    """
    from aiida.common.exceptions import NotExistent

    if calculation.exit_status in FleurProcess.get_exit_statuses(['ERROR_TIME_LIMIT']):

        # if previous calculation failed for the same reason, do not restart
        try:
            prev_calculation_remote = calculation.get_incoming().get_node_by_label('parent_folder')
            prev_calculation_status = prev_calculation_remote.get_incoming().all()[-1].exit_status
            if prev_calculation_status in FleurProcess.get_exit_statuses(['ERROR_TIME_LIMIT']):
                self.ctx.is_finished = True
                return ErrorHandlerReport(True, True)
        except NotExistent:
            pass

        self.report('FleurCalculation failed due to time limits, I restart it from where it ended')

        # increase wallclock time
        propose_wallclock = self.ctx.inputs.metadata.options['max_wallclock_seconds'] * 2
        if propose_wallclock > self.ctx.max_queue_wallclock_sec:
            propose_wallclock = self.ctx.max_queue_wallclock_sec
        self.ctx.inputs.metadata.options['max_wallclock_seconds'] = propose_wallclock

        # increase number of nodes
        propose_nodes = self.ctx.num_machines * 2
        if propose_nodes > self.ctx.max_queue_nodes:
            propose_nodes = self.ctx.max_queue_nodes
        self.ctx.num_machines = propose_nodes

        remote = calculation.get_outgoing().get_node_by_label('remote_folder')

        # resubmit providing inp.xml and cdn from the remote folder
        self.ctx.is_finished = False

        if 'fleurinpdata' in self.ctx.inputs:
            modes = self.ctx.inputs.fleurinpdata.get_fleur_modes()
            if not (modes['force_theorem'] or modes['dos'] or modes['band']):
                # in modes listed above it makes no sense copying cdn.hdf
                self.ctx.inputs.parent_folder = remote
                del self.ctx.inputs.fleurinpdata
        else:
            # it is harder to extract modes in this case - simply try to reuse cdn.hdf and hope it works
            self.ctx.inputs.parent_folder = remote

        return ErrorHandlerReport(True, True)
