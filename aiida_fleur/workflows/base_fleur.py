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
from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.engine.processes.workchains import BaseRestartWorkChain
from aiida.engine.processes.workchains.utils import process_handler, ProcessHandlerReport

from aiida_fleur.tools.common_fleur_wf import optimize_calc_options
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinp import get_fleurinp_from_remote_data


class FleurBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a FLEUR calculation with automated error handling and restarts"""
    _workflowversion = '0.2.1'
    _process_class = FleurCalculation

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(FleurCalculation, exclude=('metadata.options',))
        spec.input('options', valid_type=orm.Dict, help='Optional parameters to set up computational details.')
        spec.input('description', valid_type=str, required=False, non_db=True, help='Calculation description.')
        spec.input('label', valid_type=str, required=False, non_db=True, help='Calculation label.')
        spec.input(
            'add_comp_para',
            valid_type=orm.Dict,
            default=lambda: orm.Dict(dict={
                'only_even_MPI': False,
                'forbid_single_mpi': False,
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
            while_(cls.should_run_process)(
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )

        spec.expose_outputs(FleurCalculation)

        spec.exit_code(311,
                       'ERROR_VACUUM_SPILL_RELAX',
                       message='FLEUR calculation failed because an atom spilled to the'
                       'vacuum during relaxation')
        spec.exit_code(313, 'ERROR_MT_RADII_RELAX', message='Overlapping MT-spheres during relaxation.')
        spec.exit_code(388, 'ERROR_TIME_LIMIT_NO_SOLUTION', message='Computational resources are not optimal.')
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
        self.ctx.inputs = AttributeDict(self.exposed_inputs(FleurCalculation))

        self.ctx.max_queue_nodes = self.inputs.add_comp_para['max_queue_nodes']
        self.ctx.max_queue_wallclock_sec = self.inputs.add_comp_para['max_queue_wallclock_sec']

        input_options = self.inputs.options.get_dict()
        self.ctx.optimize_resources = input_options.pop('optimize_resources', True)
        self.ctx.inputs.metadata.options = input_options

        if 'description' in self.inputs:
            self.ctx.inputs.metadata.description = self.inputs.description
        else:
            self.ctx.inputs.metadata.description = ''
        if 'label' in self.inputs:
            self.ctx.inputs.metadata.label = self.inputs.label
        else:
            self.ctx.inputs.metadata.label = ''

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

            status = self.check_kpts()
            if status is None:
                self.ctx.can_be_optimised = True
            else:
                self.report('ERROR: Not optimal computational resources.')
                return status

    def check_kpts(self):
        """
        This routine checks if the total number of requested cpus
        is a factor of kpts and makes an optimisation.

        If suggested number of num_mpiprocs_per_machine is 60% smaller than
        requested, it throws an exit code and calculation stop withour submission.
        """
        if 'fleurinp' in self.ctx.inputs:
            fleurinp = self.ctx.inputs.fleurinp
        else:
            fleurinp = get_fleurinp_from_remote_data(self.ctx.inputs.parent_folder)

        only_even_MPI = self.inputs.add_comp_para['only_even_MPI']
        forbid_single_mpi = self.inputs.add_comp_para['forbid_single_mpi']
        try:
            machines, mpi_tasks, omp_threads, message = optimize_calc_options(self.ctx.num_machines,
                                                                              self.ctx.num_mpiprocs_per_machine,
                                                                              self.ctx.num_cores_per_mpiproc,
                                                                              self.ctx.use_omp,
                                                                              self.ctx.suggest_mpi_omp_ratio,
                                                                              fleurinp,
                                                                              only_even_MPI=only_even_MPI,
                                                                              forbid_single_mpi=forbid_single_mpi)
        except ValueError as exc:
            self.report(exc)
            return self.exit_codes.ERROR_NOT_OPTIMAL_RESOURCES

        self.report(message)

        self.ctx.inputs.metadata.options['resources']['num_machines'] = machines
        self.ctx.inputs.metadata.options['resources']['num_mpiprocs_per_machine'] = mpi_tasks
        if self.ctx.use_omp:
            self.ctx.inputs.metadata.options['resources']['num_cores_per_mpiproc'] = omp_threads
            if 'environment_variables' not in self.ctx.inputs.metadata.options:
                self.ctx.inputs.metadata.options['environment_variables'] = {}
            self.ctx.inputs.metadata.options['environment_variables']['OMP_NUM_THREADS'] = str(omp_threads)

    @process_handler(priority=1,
                     exit_codes=[
                         FleurCalculation.exit_codes.ERROR_FLEUR_CALC_FAILED,
                         FleurCalculation.exit_codes.ERROR_MT_RADII,
                         FleurCalculation.exit_codes.ERROR_NO_RETRIEVED_FOLDER,
                         FleurCalculation.exit_codes.ERROR_OPENING_OUTPUTS,
                         FleurCalculation.exit_codes.ERROR_NO_OUTXML,
                         FleurCalculation.exit_codes.ERROR_XMLOUT_PARSING_FAILED,
                         FleurCalculation.exit_codes.ERROR_RELAX_PARSING_FAILED,
                         FleurCalculation.exit_codes.ERROR_MISSING_DEPENDENCY,
                     ])
    def _handle_general_error(self, calculation):
        """
        Calculation failed for unknown reason.
        """
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for a reason that can not be resolved automatically')
        self.results()
        return ProcessHandlerReport(True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)

    @process_handler(priority=48, exit_codes=FleurCalculation.exit_codes.ERROR_DROP_CDN)
    def _handle_dirac_equation(self, calculation):
        """
        Sometimes relaxation calculation fails with Diraq problem which is usually caused by
        problems with reusing charge density. In this case we resubmit the calculation, dropping the input cdn.
        """

        # try to drop remote folder and see if it helps
        is_fleurinp_from_relax = False
        if 'fleurinp' in self.ctx.inputs:
            if 'relax.xml' in self.ctx.inputs.fleurinp.files:
                is_fleurinp_from_relax = True

        if 'parent_folder' in self.ctx.inputs and is_fleurinp_from_relax:
            del self.ctx.inputs.parent_folder
            self.ctx.restart_calc = None
            self.ctx.is_finished = False
            self.report('Calculation seems to fail due to corrupted charge density (can happen'
                        'during relaxation). I drop cdn from previous step')
            return ProcessHandlerReport(True)

        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Can not drop charge density. If I drop the remote folder, there will be no inp.xml')
        self.results()
        return ProcessHandlerReport(True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)

    @process_handler(priority=52, exit_codes=FleurCalculation.exit_codes.ERROR_VACUUM_SPILL_RELAX)
    def _handle_vacuum_spill_error(self, calculation):
        """
        Calculation failed for unknown reason.
        """

        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('FLEUR calculation failed because an atom spilled to the vacuum during'
                    'relaxation. Can be fixed via RelaxBaseWorkChain.')
        self.results()
        return ProcessHandlerReport(True, self.exit_codes.ERROR_VACUUM_SPILL_RELAX)

    @process_handler(priority=51, exit_codes=FleurCalculation.exit_codes.ERROR_MT_RADII_RELAX)
    def _handle_mt_relax_error(self, calculation):
        """
        Calculation failed for unknown reason.
        """
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('FLEUR calculation failed due to MT overlap. Can be fixed via RelaxBaseWorkChain')
        self.results()
        return ProcessHandlerReport(True, self.exit_codes.ERROR_MT_RADII_RELAX)

    @process_handler(priority=50, exit_codes=FleurCalculation.exit_codes.ERROR_NOT_ENOUGH_MEMORY)
    def _handle_not_enough_memory(self, calculation):
        """
        Calculation failed due to lack of memory.
        Probably works for JURECA only, has to be tested for other systems.
        """

        if not self.ctx.can_be_optimised:
            self.ctx.restart_calc = calculation
            self.ctx.is_finished = True
            self.report('I am not allowed to optimize your settings. Consider providing at least'
                        'num_machines and num_mpiprocs_per_machine')
            self.results()
            return ProcessHandlerReport(True, self.exit_codes.ERROR_MEMORY_ISSUE_NO_SOLUTION)

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

        status = self.check_kpts()
        if status is not None:
            self.ctx.is_finished = True
            self.results()
            return ProcessHandlerReport(True, self.exit_codes.ERROR_NOT_OPTIMAL_RESOURCES)

        if 'settings' not in self.ctx.inputs:
            settings = {}
        else:
            settings = self.ctx.inputs.settings.get_dict()
        settings.setdefault('remove_from_remotecopy_list', [])
        if 'mixing_history*' not in settings['remove_from_remotecopy_list']:
            settings['remove_from_remotecopy_list'].append('mixing_history*')
        self.ctx.inputs.settings = orm.Dict(dict=settings)

        #check if the cdn.hdf can be reused
        #Out of memory can also occur after a couple of iterations if the mixing_history gets too large
        remote = calculation.base.links.get_outgoing().get_node_by_label('remote_folder')
        if _is_remote_reusable(self.ctx.inputs, calculation):
            if 'fleurinp' in self.ctx.inputs:
                del self.ctx.inputs.fleurinp
            self.ctx.inputs.parent_folder = remote

        return ProcessHandlerReport(True)

    @process_handler(priority=47, exit_codes=FleurCalculation.exit_codes.ERROR_TIME_LIMIT)
    def _handle_time_limits(self, calculation):
        """
        If calculation fails due to time limits, we simply resubmit it.
        """
        from aiida.common.exceptions import NotExistent

        # if previous calculation failed for the same reason, do not restart
        try:
            prev_calculation_remote = calculation.base.links.get_incoming().get_node_by_label('parent_folder')
            prev_calculation_status = prev_calculation_remote.creator.exit_status
            if prev_calculation_status in FleurCalculation.get_exit_statuses(['ERROR_TIME_LIMIT']):
                self.ctx.is_finished = True
                self.results()
                return ProcessHandlerReport(True)
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

        remote = calculation.base.links.get_outgoing().get_node_by_label('remote_folder')

        # resubmit providing inp.xml and cdn from the remote folder
        self.ctx.is_finished = False
        if _is_remote_reusable(self.ctx.inputs, calculation):
            if 'fleurinp' in self.ctx.inputs:
                del self.ctx.inputs.fleurinp
            self.ctx.inputs.parent_folder = remote

        return ProcessHandlerReport(True)


def _is_remote_reusable(inputs, calculation):
    """
    Check whether the remote folder of the given calculation
    can be resubmitted
    """
    can_use_remote = False
    #If no charge density file is available to restart from the calculation will except
    #with a not nice error message. So we can only reuse the charge density if these files are available
    retrieved_filenames = calculation.base.links.get_outgoing().get_node_by_label('retrieved').list_object_names()
    if any(file in retrieved_filenames for file in (
            'cdn_last.hdf',
            'cdn1',
    )):
        can_use_remote = True

    if 'fleurinp' in inputs:
        modes = inputs.fleurinp.get_fleur_modes()
        if modes['force_theorem'] or modes['dos'] or modes['band']:
            # in modes listed above it makes no sense copying cdn.hdf
            can_use_remote = False
    # without fleurinp it is harder to extract modes in this case
    # - simply try to reuse cdn.hdf and hope it works

    return can_use_remote
