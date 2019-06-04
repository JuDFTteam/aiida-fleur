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
In this module you find the worklfow 'fleur_scf_wc' for the self-consistency
cylce management of a FLEUR calculation with AiiDA.
"""
# TODO: more info in output, log warnings
# TODO: make smarter, ggf delete broyd or restart with more or less iterations
# you can use the pattern of the density convergence for this
# TODO: test in each step if calculation before had a problem
# TODO: maybe write dict schema for wf_parameter inputs, how?
# TODO: clean up exit codes and its messages
from __future__ import absolute_import
from lxml import etree
from lxml.etree import XMLSyntaxError
import six
from six.moves import range

from aiida.plugins import DataFactory
from aiida.orm import Code
from aiida.engine import WorkChain, while_, if_, ToContext
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent

from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, optimize_calc_options
from aiida_fleur.tools.xml_util import eval_xpath2, get_xml_attribute

RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')


class FleurScfWorkChain(WorkChain):
    """
    Workchain for converging a FLEUR calculation (SCF).

    It converges the charge density.
    Two paths are possible:

    (1) Start from a structure and run the inpgen first optional with calc_parameters
    (2) Start from a Fleur calculation, with optional remoteData

    :param wf_parameters: (Dict), Workchain Spezifications
    :param structure: (StructureData), Crystal structure
    :param calc_parameters: (Dict), Inpgen Parameters
    :param fleurinp: (FleurinpData), to start with a Fleur calculation
    :param remote_data: (RemoteData), from a Fleur calculation
    :param inpgen: (Code)
    :param fleur: (Code)

    :return output_scf_wc_para: (Dict), Information of workflow results
        like Success, last result node, list with convergence behavior

    minimum input example:
    1. Code1, Code2, Structure, (Parameters), (wf_parameters)
    2. Code2, FleurinpData, (wf_parameters)

    maximum input example:
    1. Code1, Code2, Structure, Parameters
        wf_parameters: {'density_criterion' : Float,
                        'energy_criterion' : Float,
                        'converge_density' : True,
                        'converge_energy' : True}
    2. Code2, FleurinpData, (remote-data), wf_parameters as in 1.

    Hints:
    1. This workflow does not work with local codes!
    """

    _workflowversion = "0.3.2"
    _wf_default = {'fleur_runmax': 4,
                   'density_criterion': 0.00002,
                   'energy_criterion': 0.002,
                   'force_criterion': 0.002,
                   'mode': 'density',  # 'density', 'energy' or 'force'
                   'serial': False,
                   'itmax_per_run': 30,
                   'force_dict': {'qfix': 2,
                                  'forcealpha': 0.5,
                                  'forcemix': 2},
                   'inpxml_changes': [],
                  }

    _default_options = {
        'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        'max_wallclock_seconds': 6*60*60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}}

    @classmethod
    def define(cls, spec):
        super(FleurScfWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False,
                   default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("settings", valid_type=Dict, required=False)
        spec.input("options", valid_type=Dict, required=False,
                   default=Dict(dict=cls._default_options))
        spec.input("fleurinp", valid_type=FleurInpData, required=False)
        spec.input("remote_data", valid_type=RemoteData, required=False)
        spec.input("inpgen", valid_type=Code, required=False)
        spec.input("fleur", valid_type=Code, required=True)

        spec.outline(
            cls.start,
            cls.validate_input,
            if_(cls.fleurinpgen_needed)(
                cls.run_fleurinpgen),
            cls.run_fleur,
            cls.inspect_fleur,
            cls.get_res,
            while_(cls.condition)(
                cls.loop_count,  # loop_count is not in while_ to throw exit_code correctly
                cls.run_fleur,
                cls.inspect_fleur,
                cls.get_res),
            cls.return_results
        )

        spec.output('fleurinp', valid_type=FleurInpData)
        spec.output('output_scf_wc_para', valid_type=Dict)
        spec.output('last_fleur_calc_output', valid_type=Dict)

        # exit codes
        spec.exit_code(301, 'ERROR_INVALID_INPUT_RESOURCES',
                       message="Invalid input, plaese check input configuration.")
        spec.exit_code(302, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED',
                       message="Some required inputs are missing.")
        spec.exit_code(303, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")
        spec.exit_code(304, 'ERROR_INPGEN_CALCULATION_FAILED',
                       message="Inpgen calculation failed.")
        spec.exit_code(305, 'ERROR_CHANGING_FLEURINPUT_FAILED',
                       message="Input file modification failed.")
        spec.exit_code(306, 'ERROR_CALCULATION_INVALID_INPUT_FILE',
                       message="Input file is corrupted after user's modifications.")
        spec.exit_code(307, 'ERROR_FLEUR_CALCULATION_FALIED',
                       message="Fleur calculation failed.")
        spec.exit_code(308, 'ERROR_DID_NOT_CONVERGE',
                       message="SCF cycle did not lead to convergence.")
        spec.exit_code(333, 'ERROR_NOT_OPTIMAL_RESOURSES',
                       message="Computational resourses are not optimal.")

    def start(self):
        """
        init context and some parameters
        """
        self.report('INFO: started convergence workflow version {}\n'
                    ''.format(self._workflowversion))

        ####### init    #######

        # internal para /control para
        self.ctx.last_calc = None
        self.ctx.loop_count = 0
        self.ctx.relax_generated = False
        self.ctx.calcs = []
        self.ctx.abort = False

        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default


        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        self.ctx.serial = self.ctx.wf_dict.get('serial', False)

        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        self.ctx.max_number_runs = self.ctx.wf_dict.get('fleur_runmax', 4)
        self.ctx.description_wf = self.inputs.get(
            'description', '') + '|fleur_scf_wc|'
        self.ctx.label_wf = self.inputs.get('label', 'fleur_scf_wc')
        self.ctx.default_itmax = self.ctx.wf_dict.get('itmax_per_run', 30)

        # return para/vars
        self.ctx.successful = False
        self.ctx.parse_last = True
        self.ctx.distance = []
        self.ctx.all_forces = []
        self.ctx.total_energy = []
        self.ctx.energydiff = 10000
        self.ctx.forcediff = 10000
        self.ctx.last_charge_density = 10000
        self.ctx.warnings = []
        # "debug": {},
        self.ctx.errors = []
        self.ctx.info = []
        self.ctx.possible_info = [
            'Consider providing more resources',
            'Consider providing a lot more resources',
            'Consider changing the mixing scheme',
        ]
        self.ctx.fleurinp = None
        self.ctx.formula = ''
        self.ctx.total_wall_time = 0

    def validate_input(self):
        """
        # validate input and find out which path (1, or 2) to take
        # return True means run inpgen if false run fleur directly
        """

        self.ctx.run_inpgen = True
        inputs = self.inputs

        if 'fleurinp' in inputs:
            self.ctx.run_inpgen = False
            if 'structure' in inputs:
                warning = 'WARNING: Ignoring Structure input because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'inpgen' in inputs:
                warning = 'WARNING: Ignoring inpgen code input because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'remote_data' in inputs:
                warning = ('WARNING: Ignoring remote_data inp.xml because Fleurinp'
                           'is given that overrides inp.xml from remote calculation')
                self.ctx.warnings.append(warning)
                self.report(warning)
        elif 'structure' in inputs:
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES
        elif 'remote_data' in inputs:
            self.ctx.run_inpgen = False
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(
                    inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(
                    inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # check the mode in wf_dict
        mode = self.ctx.wf_dict.get('mode')
        if mode not in ['force', 'density', 'energy']:
            error = ("ERROR: Wrong mode of converfence"
                     ": one of 'force', 'density' or 'energy' was expected.")
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        max_iters = self.ctx.wf_dict.get('itmax_per_run')
        if max_iters <= 1:
            error = ("ERROR: 'itmax_per_run' should be equal at least 2")
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        # check format of inpxml_changes
        fchanges = self.ctx.wf_dict.get('inpxml_changes', [])
        if fchanges:
            for change in fchanges:
                # somehow the tuple type gets destroyed on the way and becomes a list
                if (not isinstance(change, tuple)) and (not isinstance(change, list)):
                    error = ('ERROR: Wrong Input inpxml_changes wrong format of'
                             ': {} should be tuple of 2. I abort'.format(change))
                    return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES
        return

    def fleurinpgen_needed(self):
        """
        Returns True if inpgen calculation has to be submitted
        before fleur calculations
        """
        return self.ctx.run_inpgen

    def run_fleurinpgen(self):
        """
        run the inpgen
        """
        structure = self.inputs.structure
        self.ctx.formula = structure.get_formula()
        label = 'scf: inpgen'
        description = '{} inpgen on {}'.format(
            self.ctx.description_wf, self.ctx.formula)

        inpgencode = self.inputs.inpgen
        if 'calc_parameters' in self.inputs:
            params = self.inputs.calc_parameters
        else:
            params = None

        options = {"max_wallclock_seconds": int(self.ctx.options.get('max_wallclock_seconds')),
                   "resources": self.ctx.options.get('resources'),
                   "queue_name": self.ctx.options.get('queue_name', '')}
        # TODO do not use the same option for inpgen as for FLEUR; so far we ignore the other
        # clean Idea might be to provide second inpgen options

        inputs_build = get_inputs_inpgen(
            structure, inpgencode, options, label, description, params=params)
        self.report('INFO: run inpgen')
        future = self.submit(inputs_build)

        return ToContext(inpgen=future, last_calc=future)

    def check_kpts(self, fleurinp):
        """
        This routine checks if the total number of requested cpus
        is a factor of kpts and makes small optimisation.
        """
        mach = int(self.ctx.options['resources']['num_machines'])
        procs = int(self.ctx.options['resources']['num_mpiprocs_per_machine'])
        adv_nodes, adv_cpu_nodes, message, exit_code = optimize_calc_options(fleurinp, mach, procs)

        if 'WARNING' in message:
            self.ctx.warnings.append(message)

        self.report(message)

        self.ctx.options['resources']['num_machines'] = adv_nodes
        self.ctx.options['resources']['num_mpiprocs_per_machine'] = adv_cpu_nodes

        return exit_code

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')
        if self.ctx.fleurinp:  # something was already changed
            return
        elif 'fleurinp' in self.inputs:
            fleurin = self.inputs.fleurinp
        elif 'structure' in self.inputs:
            try:
                fleurin = self.ctx['inpgen'].outputs.fleurinpData
            except NotExistent:
                error = 'No fleurinpData found, inpgen failed'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INPGEN_CALCULATION_FAILED
        elif 'remote_data' in self.inputs:
            # In this case only remote_data for input structure is given
            # fleurinp data has to be generated from the remote inp.xml file to use change_fleurinp
            remote_node = self.inputs.remote_data
            parent_calc_node = remote_node.get_incoming().get_node_by_label('remote_folder')
            retrieved_node = parent_calc_node.get_outgoing().get_node_by_label('retrieved')
            fleurin = FleurInpData(files=['inp.xml'], node=retrieved_node)

        wf_dict = self.ctx.wf_dict
        force_dict = wf_dict.get('force_dict')
        converge_mode = wf_dict.get('mode')
        fchanges = wf_dict.get('inpxml_changes', [])

        fleurmode = FleurinpModifier(fleurin)

        # set proper convergence parameters in inp.xml
        if converge_mode == 'density':
            dist = wf_dict.get('density_criterion')
            fleurmode.set_inpchanges(
                {'itmax': self.ctx.default_itmax, 'minDistance': dist})
        elif converge_mode == 'force':
            force_converged = wf_dict.get('force_criterion')
            dist = 0.0
            fleurmode.set_inpchanges({'itmax': self.ctx.default_itmax, 'minDistance': dist,
                                      'force_converged': force_converged, 'l_f': True,
                                      'qfix': force_dict.get('qfix'),
                                      'forcealpha': force_dict.get('forcealpha'),
                                      'forcemix': force_dict.get('forcemix')})
        elif converge_mode == 'energy':
            dist = 0.0
            fleurmode.set_inpchanges(
                {'itmax': self.ctx.default_itmax, 'minDistance': dist})

        avail_ac_dict = fleurmode.get_avail_actions()

        # apply further user dependend changes
        if fchanges:
            for change in fchanges:
                function = change[0]
                para = change[1]
                method = avail_ac_dict.get(function, None)
                if not method:
                    error = ("ERROR: Input 'inpxml_changes', function {} "
                             "is not known to fleurinpmodifier class, "
                             "plaese check/test your input. I abort..."
                             "".format(method))
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

                else:  # apply change
                    if function == u'set_inpchanges':
                        method(**para)
                    else:
                        method(*para)

        # validate?
        apply_c = True
        try:
            fleurmode.show(display=False, validate=True)
        except XMLSyntaxError:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            # fleurmode.show(display=True)#, validate=True)
            self.report(error)
            apply_c = False
            return self.exit_codes.ERROR_CALCULATION_INVALID_INPUT_FILE

        # apply
        if apply_c:
            out = fleurmode.freeze()
            self.ctx.fleurinp = out
        return

    def run_fleur(self):
        """
        run a FLEUR calculation
        """
        self.report('INFO: run FLEUR')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp
        if self.check_kpts(fleurin):
            self.control_end_wc('ERROR: Not optimal computational resourses.')
            return self.exit_codes.ERROR_NOT_OPTIMAL_RESOURSES

        if 'settings' in self.inputs:
            settings = self.inputs.settings
        else:
            settings = None

        if self.ctx['last_calc']:
            # will this fail if fleur before failed? try needed?
            remote = self.ctx['last_calc'].outputs.remote_folder
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        label = ' '
        description = ' '
        if self.ctx.formula:
            label = 'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = '{} fleur run {} on {}'.format(
                self.ctx.description_wf, self.ctx.loop_count+1, self.ctx.formula)
        else:
            label = 'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = '{} fleur run {}, fleurinp given'.format(
                self.ctx.description_wf, self.ctx.loop_count+1)

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(
            code, remote, fleurin, options, label, description, settings, serial=self.ctx.serial)
        future = self.submit(inputs_builder)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report('INFO: run FLEUR number: {}'.format(self.ctx.loop_count))
        self.ctx.calcs.append(future)

        return ToContext(last_calc=future)

    def inspect_fleur(self):
        """
        Analyse the results of the previous Calculation (Fleur or inpgen),
        checking whether it finished successfully or if not, troubleshoot the
        cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """

        self.report('INFO: inspect FLEUR')
        try:
            calculation = self.ctx.last_calc
        except AttributeError:
            self.ctx.parse_last = False
            error = 'ERROR: Something went wrong I do not have a last calculation'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FALIED

        exit_status = calculation.exit_status
        if not calculation.is_finished_ok:
            error = ('ERROR: Last Fleur calculation failed '
                     'with exit status {}'.format(exit_status))
            self.control_end_wc(error)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FALIED
        else:
            self.ctx.parse_last = True

        '''
        #TODO: these retries have to be fixed/implemented using fleur calculation exit_codes
        # Done: successful convergence of last calculation
        if calculation.has_finished_ok():
            self.report('converged successfully after {} iterations'.format(self.ctx.iteration))
            self.ctx.restart_calc = calculation
            self.ctx.is_finished = True

        # Abort: exceeded maximum number of retries
        elif self.ctx.iteration >= self.ctx.max_iterations:
            self.report('reached the max number of iterations {}'.format(self.ctx.max_iterations))
            self.abort_nowait('last ran PwCalculation<{}>'.format(calculation.pk))

        # Abort: unexpected state of last calculation
        elif calculation.get_state() not in expected_states:
            self.abort_nowait('unexpected state ({}) of PwCalculation<{}>'.format(
                calculation.get_state(), calculation.pk))

        # Retry: submission failed, try to restart or abort
        elif calculation.get_state() in [calc_states.SUBMISSIONFAILED]:
            self._handle_submission_failure(calculation)

        # Retry: calculation failed, try to salvage or abort
        elif calculation.get_state() in [calc_states.FAILED]:
            self._handle_calculation_failure(calculation)

        # Retry: try to convergence restarting from this calculation
        else:
            self.report('calculation did not converge after {} iterations, restarting'.format(self.ctx.iteration))
            self.ctx.restart_calc = calculation

        # ggf handle bad convergence behavior, delete broyd (do not copy)
        return
        '''

    def get_res(self):
        """
        Check how the last Fleur calculation went
        Parse some results.
        """
        # TODO maybe do this different
        # or if complexer output node exists take from there.

        self.report('INFO: get results FLEUR')

        xpath_energy = '/fleurOutput/scfLoop/iteration/totalEnergy/@value'
        xpath_iter = '/fleurOutput/scfLoop/iteration'
        xpath_force = 'totalForcesOnRepresentativeAtoms/forceTotal'
        # be aware of magnetism
        xpath_distance = '/fleurOutput/scfLoop/iteration/densityConvergence/chargeDensity/@distance'
        #densityconvergence_xpath = 'densityConvergence'
        #chargedensity_xpath = 'densityConvergence/chargeDensity'
        overallchargedensity_xpath = ('/fleurOutput/scfLoop/iteration/densityConvergence'
                                      '/overallchargeDensity/@distance')
        #spindensity_xpath = 'densityConvergence/spinDensity'
        if self.ctx.parse_last:
            last_calc = self.ctx.last_calc

            '''
            spin = get_xml_attribute(eval_xpath(root, magnetism_xpath), jspin_name)

                charge_densitys = eval_xpath(iteration_node, chargedensity_xpath)
                charge_density1 = get_xml_attribute(charge_densitys[0], distance_name)
                write_simple_outnode(
                    charge_density1, 'float', 'charge_density1', simple_data)

                charge_density2 = get_xml_attribute(charge_densitys[1], distance_name)
                write_simple_outnode(
                    charge_density2, 'float', 'charge_density2', simple_data)

                spin_density = get_xml_attribute(
                    eval_xpath(iteration_node, spindensity_xpath), distance_name)
                write_simple_outnode(
                    spin_density, 'float', 'spin_density', simple_data)

                overall_charge_density = get_xml_attribute(
                    eval_xpath(iteration_node, overallchargedensity_xpath), distance_name)
                write_simple_outnode(
                    overall_charge_density, 'float', 'overall_charge_density', simple_data)

            '''
            # TODO: dangerous, can fail, error catching
            # TODO: is there a way to use a standard parser?
            outxmlfile_opened = last_calc.get_retrieved_node().open(
                last_calc.get_attribute('outxml_file_name'), 'r')
            walltime = last_calc.outputs.output_parameters.dict.walltime
            if isinstance(walltime, int):
                self.ctx.total_wall_time = self.ctx.total_wall_time + walltime
            #outpara = last_calc.get('output_parameters', None)
            #outxmlfile = outpara.dict.outputfile_path
            tree = etree.parse(outxmlfile_opened)
            root = tree.getroot()
            energies = eval_xpath2(root, xpath_energy)
            for energy in energies:
                self.ctx.total_energy.append(float(energy))

            overall_distances = eval_xpath2(root, overallchargedensity_xpath)
            if overall_distances:
                distances = eval_xpath2(root, xpath_distance)
                for distance in distances:
                    self.ctx.distance.append(float(distance))
            else:
                for distance in overall_distances:
                    self.ctx.distance.append(float(distance))

            iter_all = eval_xpath2(root, xpath_iter)
            for iteration in iter_all:
                forces = eval_xpath2(iteration, xpath_force)
                forces_in_iter = []
                for force in forces:
                    # forces_unit = get_xml_attribute(
                    #    eval_xpath(iteration_node, forces_units_xpath), units_name)
                    force_x = float(get_xml_attribute(force, 'F_x'))
                    force_y = float(get_xml_attribute(force, 'F_y'))
                    force_z = float(get_xml_attribute(force, 'F_z'))

                    forces_in_iter.append(force_x)
                    forces_in_iter.append(force_y)
                    forces_in_iter.append(force_z)

                self.ctx.all_forces.append(forces_in_iter)
            outxmlfile_opened.close()
        else:
            errormsg = 'ERROR: scf wc was not successful, check log for details'
            self.control_end_wc(errormsg)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FALIED

        if self.ctx.distance:
            errormsg = 'ERROR: did not manage to extract charge density from the calculation'
            self.control_end_wc(errormsg)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FALIED
        else:
            self.ctx.last_charge_density = self.ctx.distance[-1]

    def condition(self):
        """
        check convergence condition
        """
        self.report('INFO: checking condition FLEUR')
        mode = self.ctx.wf_dict.get('mode')

        energy = self.ctx.total_energy
        if len(energy) >= 2:
            self.ctx.energydiff = abs(energy[-1]-energy[-2])

        forces = self.ctx.all_forces
        if len(forces) >= 2:
            self.ctx.forcediff = max(
                [abs(forces[-1][i] - forces[-2][i]) for i in range(len(forces[-1]))])

        if mode == 'density':
            if self.ctx.wf_dict.get('density_criterion') >= self.ctx.last_charge_density:
                return False
        elif mode == 'energy':
            if self.ctx.wf_dict.get('energy_criterion') >= self.ctx.energydiff:
                return False
        elif mode == 'force':
            try:
                _ = self.ctx.last_calc.relax_parameters
            except NotExistent:
                return False
            # self.ctx.last_calc
            # if self.ctx.wf_dict.get('force_criterion') >= self.ctx.forcediff:

        return True

    def loop_count(self):
        """
        Exits the workchain if the number of iterations is exceeded.

        This loop count is separated from self.condition function since
        it has to return ExitCode to interupt the workchain.
        However, if a function returns an ExitCode inside a while_ statement,
        the ouptut seem to be automatically converted to True
        which does not interupt the workchain when needed.
        """
        if self.ctx.loop_count >= self.ctx.max_number_runs:
            errormsg = 'ERROR: did not reach convergence in specified number of iterations'
            self.control_end_wc(errormsg)
            return self.exit_codes.ERROR_DID_NOT_CONVERGE
        return

    def return_results(self):
        """
        return the results of the calculations
        This shoudl run through and produce output nodes even if everything failed,
        therefore it only uses results from context.
        """
        try:
            last_calc_uuid = self.ctx.last_calc.uuid
        except AttributeError:
            last_calc_uuid = None
        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.last_calc.outputs['output_parameters']
            retrieved = self.ctx.last_calc.outputs['retrieved']
            last_calc_out_dict = last_calc_out.get_dict()
        except NotExistent:
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None

        outputnode_dict = {}
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['material'] = self.ctx.formula
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = last_calc_out_dict.get(
            'number_of_iterations_total', None)
        outputnode_dict['distance_charge'] = self.ctx.last_charge_density
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = last_calc_out_dict.get(
            'energy_hartree', None)
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['force_diff_last'] = self.ctx.forcediff
        outputnode_dict['force_largest'] = last_calc_out_dict.get(
            'force_largest', None)
        outputnode_dict['distance_charge_units'] = 'me/bohr^3'
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['last_calc_uuid'] = last_calc_uuid
        outputnode_dict['total_wall_time'] = self.ctx.total_wall_time
        outputnode_dict['total_wall_time_units'] = 'hours'
        outputnode_dict['info'] = self.ctx.info
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors

        if self.ctx.successful:
            if len(self.ctx.total_energy) <= 1:  # then len(self.ctx.all_forces) <= 1 too
                self.report('STATUS: Done, the convergence criteria are reached.\n'
                            'INFO: The charge density of the FLEUR calculation '
                            'converged after {} FLEUR runs, {} iterations and {} sec '
                            'walltime to {} "me/bohr^3" \n'
                            'INFO: Did not manage to get energy and largest force difference '
                            'between two last iterations, probably converged in a single iteration'
                            ''.format(self.ctx.loop_count,
                                      last_calc_out_dict.get('number_of_iterations_total', None),
                                      self.ctx.total_wall_time,
                                      outputnode_dict['distance_charge']))
            else:
                self.report('STATUS: Done, the convergence criteria are reached.\n'
                            'INFO: The charge density of the FLEUR calculation '
                            'converged after {} FLEUR runs, {} iterations and {} sec '
                            'walltime to {} "me/bohr^3" \n'
                            'INFO: The total energy difference of the last two iterations '
                            'is {} Htr and largest force difference is {} Htr/bohr'
                            ''.format(self.ctx.loop_count,
                                      last_calc_out_dict.get('number_of_iterations_total', None),
                                      self.ctx.total_wall_time,
                                      outputnode_dict['distance_charge'],
                                      self.ctx.energydiff,
                                      self.ctx.forcediff))
        else:  # Termination ok, but not converged yet...
            if self.ctx.abort:  # some error occured, donot use the output.
                self.report('STATUS/ERROR: I abort, see logs and '
                            'erros/warning/hints in output_scf_wc_para')
            else:
                if len(self.ctx.total_energy) <= 1:  # then len(self.ctx.all_forces) <= 1 too
                    self.report('STATUS/WARNING: Done, the maximum number of runs '
                                'was reached or something failed.\n INFO: The '
                                'charge density of the FLEUR calculation, '
                                'after {} FLEUR runs, {} iterations and {} sec '
                                'walltime is {} "me/bohr^3"\n'
                                'INFO: can not extract energy and largest force difference between'
                                ' two last iterations, probably converged in a single iteration'
                                ''.format(self.ctx.loop_count,
                                          last_calc_out_dict.get(
                                              'number_of_iterations_total', None),
                                          self.ctx.total_wall_time,
                                          outputnode_dict['distance_charge']))
                else:
                    self.report('STATUS/WARNING: Done, the maximum number of runs '
                                'was reached or something failed.\n INFO: The '
                                'charge density of the FLEUR calculation, '
                                'after {} FLEUR runs, {} iterations and {} sec '
                                'walltime is {} "me/bohr^3"\n'
                                'INFO: The total energy difference of the last two iterations '
                                'is {} Htr and largest force difference is {} Htr/bohr\n'
                                ''.format(self.ctx.loop_count,
                                          last_calc_out_dict.get(
                                              'number_of_iterations_total', None),
                                          self.ctx.total_wall_time,
                                          outputnode_dict['distance_charge'],
                                          self.ctx.energydiff,
                                          self.ctx.forcediff))

        outputnode_t = Dict(dict=outputnode_dict)
        # this is unsafe so far, because last_calc_out could not exist...
        if last_calc_out:
            outdict = create_scf_result_node(
                outpara=outputnode_t, last_calc_out=last_calc_out, last_calc_retrieved=retrieved)
        else:
            outdict = create_scf_result_node(outpara=outputnode_t)

        if 'fleurinp' in self.inputs:
            outdict['fleurinp'] = self.inputs.fleurinp
        elif not self.ctx.run_inpgen:
            # fleurinp node contain a fleurinp which was changed according to inpxml_changes
            outdict['fleurinp'] = self.ctx.fleurinp
        else:
            try:
                fleurinp = self.ctx['inpgen'].outputs.fleurinpData
            except NotExistent:
                self.report(
                    'ERROR: No fleurinp, something was wrong with the inpgen calc')
                fleurinp = None
            outdict['fleurinp'] = fleurinp
        if last_calc_out:
            outdict['last_fleur_calc_output'] = last_calc_out

        #outdict['output_scf_wc_para'] = outputnode
        for link_name, node in six.iteritems(outdict):
            self.out(link_name, node)

    def handle_fleur_failure(self):
        """
        handle a failure of a Fleur calculation
        """
        return
        # handle out of walltime (not one interation run) abort, tell user to specifi mor resources, or different cutoffs

        # handle fleur error fermi level convergence
        # restart fleur with more tempertature broad or other smearing type (gauss = T)

        # qfix needed, restart fleur with Qfix

        # differ errors, solving dirac equation
        # abort, or restart with different parameters

        # muffin tin radii overlap, restart with smaller MT

        # wrong command line switches
        # hdf, -h , ... restart with the right one, or abort

        # something about kpt grid
        # abort, or restart with increased number /different number of kpoints

        # wrong parallelisation
        # abort or restart with right parallelisation

        #

        '''
        #ALl FLEUR current (07.2017) ERROR hints: TODO

        1.nsh greater than dimensioned | increase nmax in jcoff2'
        2. Fermi-level determination did not converge| change temperature or set input = F
        3. Too low eigenvalue detected | If the lowest eigenvalue is more than 1Htr below the lowest energy parameter, you probably have picked up a ghoststate
        4. e >= vz0 | Vacuum energy-parameter too high
        5. kidx /= stars | something wrong with kmxxc_fft or nxc3_fft
        6 Wrong size of matrix | Your basis might be too large or the parallelization fail or ??
        If no LO's are set skiplo must be 0 in enpara
        You compiled without support for HDF5. Please use another mode
        Your HDF5 library does not support parallel IO
        Use -mpi or -hdf instead
        Consider setting 'autocomp = false' in apwefl.
        Film setup not centered" | The z = 0 plane is the center of the film
        setcore_bystr |
        expnadconfig |
        File not readable:"//filename | FLEUR wants to read a file that is not present
        Both inp & inp.xml given  | Please delete one of the input files or specify -xml to use inp.xml
        inp.xml not found | You gave the -xml option but provided no inp.xml file
        No input file found | To use FLEUR, you have to provide either an 'inp' or an 'inp.xml' file in the working directory
        Use a supercell or a different functional
        MPI parallelization failed | ou have to either compile FLEUR with a parallel diagonalization library (ELPA,SCALAPACK...) or you have to run such that the No of kpoints can be distributed on the PEs

        AiiDA related:
        1. Submissionfailed:
        SSHException: SSH session not active   -> wait and relaunch

        Scheduler/HPC related:

        1. scf scheduler needs other things than torque, try to provide both as default
        that they both work

        2. ran out of walltime with out a single interation done. (killed by scheduler)
        -> terminate, because the user should specify more recources or in the
        calculation something is fishy

        3. bumped by scheduler joblimit. reached
        -> think about something here and retry

        4. no space/files left on remote machine.
        -> also terminate, tell user to delete stuff

        5. not eneough memory, (killed by scheduler, or some fleur error)
        -> can we do something here
        '''

    def handle_inpgen_failure(self):
        """
        Handle a failure of inpgen
        """
        return

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()

@cf
def create_scf_result_node(**kwargs):
    """
    This is a pseudo wf, to create the rigth graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in six.iteritems(kwargs):
        if key == 'outpara':  # should be alwasys there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_scf_wc_para'
    outputnode.description = ('Contains self-consistency results and '
                              'information of an fleur_scf_wc run.')

    outdict['output_scf_wc_para'] = outputnode
    # copy, because we rather produce the same node twice then have a circle in the database for now
    #output_para = args[0]
    # return {'output_eos_wc_para'}
    return outdict
