# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
In this module you find the worklfow 'fleur_scf_wc' for the self-consistency
cylce management of a FLEUR calculation with AiiDA.
"""
#TODO: more info in output, log warnings
#TODO: make smarter, ggf delete broyd or restart with more or less iterations
# you can use the pattern of the density convergence for this
#TODO: other error handling, where is known what to do
#TODO: test in each step if calculation before had a problem
#TODO: maybe write dict schema for wf_parameter inputs, how?
import re
from lxml import etree
from lxml.etree import XMLSyntaxError

from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain, while_, if_, ToContext
from aiida.work.run import submit
from aiida.work import workfunction as wf
from aiida.common.datastructures import calc_states
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, choose_resources_fleur
from aiida_fleur.tools.xml_util import eval_xpath2

RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')
FleurProcess = FleurCalculation.process()
FleurinpProcess = FleurinputgenCalculation.process()

class fleur_scf_wc(WorkChain):
    """
    Workchain for converging a FLEUR calculation (SCF).

    It converges the charge density.
    Two paths are possible:

    (1) Start from a structure and run the inpgen first optional with calc_parameters
    (2) Start from a Fleur calculation, with optional remoteData

    :param wf_parameters: (ParameterData), Workchain Spezifications
    :param structure: (StructureData), Crystal structure
    :param calc_parameters: (ParameterData), Inpgen Parameters
    :param fleurinp: (FleurinpData), to start with a Fleur calculation
    :param remote_data: (RemoteData), from a Fleur calculation
    :param inpgen: (Code)
    :param fleur: (Code)

    :return output_scf_wc_para: (ParameterData), Information of workflow results
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

    _workflowversion = "0.4.0"
    _wf_default = {'fleur_runmax': 4,              # Maximum number of fleur jobs/starts (defauld 80 iterations per start)
                   'density_criterion' : 0.00002,  # Stop if charge denisty is converged below this value
                   'energy_criterion' : 0.002,     # if converge energy run also this total energy convergered below this value
                   'converge_density' : True,      # converge the charge density
                   'converge_energy' : False,      # converge the total energy (usually converged before density)
                   'refine_resources' : True,      # Tries to choose an optimal parallelisation call for a fleur calculation within the resources provieded, from the input, if set to True. 
                                                   # If False, force to use given resources and parallelisation.
                   #'resue' : True,                 # AiiDA fastforwarding (currently not there yet
                   'serial' : False,                # execute fleur with mpi or without
                   #'label' : 'fleur_scf_wc',        # label for the workchain node and all sporned calculations by the wc
                   #'description' : 'Fleur self consistensy cycle workchain', # description (see label)
                   'itmax_per_run' : 80,
                   'maxiterbroyd' : 8,
                   'inpxml_changes' : [],      # (expert) List of further changes applied after the inpgen run
                   }                                 # tuples (function_name, [parameters]), the ones from fleurinpmodifier
                                                    # example: ('set_nkpts' , {'nkpts': 500,'gamma': False}) ! no checks made, there know what you are doing
    #_default_wc_label = u'fleur_scf_wc'
    #_default_wc_description = u'fleur_scf_wc: Fleur self consistensy cycle workchain, converges the total energy.'
    _default_options = {
                        u'resources' : {"num_machines": 1},
                        u'max_wallclock_seconds' : 6*60*60,
                        u'queue_name' : u'',
                        u'custom_scheduler_commands' : u'',
                        u'import_sys_environment' : False,
                        u'environment_variables' : {}}
    
    # 0 is the usual return status of each step and the workchain
    ERROR_INVALID_INPUT_RESOURCES = 1
    ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED = 2
    ERROR_INVALID_CODE_PROVIDED = 3
    ERROR_INPGEN_CALCULATION_FAILED = 4
    ERROR_CHANGING_FLEURINPUT_FAILED = 5
    ERROR_CALCULATION_INVALID_INPUT_FILE = 6
    ERROR_FLEUR_CALCULATION_FALIED = 7
    ERROR_CONVERGENCE_NOT_ARCHIVED = 8
    # loop count, not enough resources provided

    @classmethod
    def define(cls, spec):
        super(fleur_scf_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict=cls._wf_default))
                                              #'fleur_runmax': 4,
                                               #'density_criterion' : 0.00002,
                                               #'energy_criterion' : 0.002,
                                               #'converge_density' : True,
                                               #'converge_energy' : False,
                                               #'reuse' : True,
                                               #'options' : {
                                               #    'resources': {"num_machines": 1},
                                               #    'max_wallclock_seconds': 60*60,
                                               #    'queue_name': '',
                                               #    'custom_scheduler_commands' : '',
                                               #    #'max_memory_kb' : None,
                                               #    'import_sys_environment' : False,
                                               #    'environment_variables' : {}},
                                               #'serial' : False,
                                               #'itmax_per_run' : 30,
                                               #'inpxml_changes' : [],
                                               #}))
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.input("settings", valid_type=ParameterData, required=False)
        spec.input("options", valid_type=ParameterData, required=False, 
                   default=ParameterData(dict=cls._default_options))#{
                            #'resources': {"num_machines": 1},
                            #'max_wallclock_seconds': 60*60,
                            #'queue_name': '',
                            #'custom_scheduler_commands' : '',
                            #'max_memory_kb' : None,
                            #'import_sys_environment' : False,
                            #'environment_variables' : {}}))
        spec.input("fleurinp", valid_type=FleurInpData, required=False)
        spec.input("remote_data", valid_type=RemoteData, required=False)
        spec.input("inpgen", valid_type=Code, required=False)
        spec.input("fleur", valid_type=Code, required=True)

        spec.outline(
            cls.start,
            if_(cls.validate_input)(
                cls.run_fleurinpgen),
            cls.run_fleur, # are these first runs needed TODO
            cls.inspect_fleur, # are these first runs needed
            cls.get_res, # are these first runs needed
            while_(cls.condition)(
                cls.run_fleur,
                cls.inspect_fleur,
                cls.get_res),
            cls.return_results
        )

        spec.output('fleurinp', valid_type=FleurInpData)
        spec.output('output_scf_wc_para', valid_type=ParameterData)
        spec.output('last_fleur_calc_output', valid_type=ParameterData)


        
    def start(self):
        """
        init context and some parameters
        """
        self.report(u'INFO: started convergence workflow version {}\n'
                    ''.format(self._workflowversion))

        ####### init    #######

        # internal para /control para
        self.ctx.last_calc = None
        self.ctx.loop_count = 0
        self.ctx.calcs = []
        self.ctx.abort = False


        # input para
        wf_dict = self.inputs.wf_parameters.get_dict()

        if wf_dict == {}:
            wf_dict = self._wf_default

        self.ctx.serial = wf_dict.get('serial', False)

        # set values, or defaults
        defaultoptions = self._default_options
        #options = wf_dict.get('options', defaultoptions)

        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions
            
        for key, val in defaultoptions.iteritems():
            options[key] = options.get(key, val)
        self.ctx.options = options
        
        
        self.report(u'options: {}'.format(self.ctx.options))
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        self.ctx.description_wf = self.inputs.get('description', '') + '|fleur_scf_wc|'
        self.ctx.label_wf = self.inputs.get('label', 'fleur_scf_wc')
        self.ctx.default_itmax = wf_dict.get('itmax_per_run', 80)
        self.ctx.refine_resources = wf_dict.get('refine_resources', True)

        # return para/vars
        self.ctx.successful = False
        self.ctx.parse_last = True
        self.ctx.distance = []
        self.ctx.total_energy = []
        self.ctx.energydiff = 10000
        self.ctx.warnings = []#
        #"warnings": {
        #"debug": {},
        #"error": {},
        #"info": {},
        #"warning": {}
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
        self.ctx.last_charge_density = None
        
    def validate_input(self):
        """
        # validate input and find out which path (1, or 2) to take
        # return True means run inpgen if false run fleur directly
        """

        run_inpgen = True
        inputs = self.inputs

        if 'fleurinp' in inputs:
            run_inpgen = False
            if 'structure' in inputs:
                warning = 'WARNING: Ignoring Structure input, because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'inpgen' in inputs:
                warning = 'WARNING: Ignoring inpgen code input, because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input, because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
        elif 'structure' in inputs:
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                self.report(error)
                return self.ERROR_INVALID_INPUT_RESOURCES
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            self.control_end_wc(error)
            return self.ERROR_INVALID_INPUT_RESOURCES
            
        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                self.control_end_wc(error)
                return self.ERROR_INVALID_CODE_PROVIDED
                
        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                return self.ERROR_INVALID_CODE_PROVIDED

        # maybe ckeck here is unessesary...
        wf_dict = self.inputs.wf_parameters.get_dict()

        if wf_dict == {}:
            wf_dict = self._wf_default

        # check format of inpxml_changes
        fchanges = wf_dict.get('inpxml_changes', [])
        if fchanges:
            for change in fchanges:
                # somehow the tuple type gets destroyed on the way and becomes a list
                if (not isinstance(change, tuple)) and (not isinstance(change, list)):
                    error = ('ERROR: Wrong Input inpxml_changes wrong format of'
                             ': {} should be tuple of 2. I abort'.format(change))
                    self.control_end_wc(error)
                    self.ERROR_INVALID_INPUT_RESOURCES

        return run_inpgen


    def run_fleurinpgen(self):
        """
        run the inpgen
        """
        structure = self.inputs.structure
        self.ctx.formula = structure.get_formula()
        self.ctx.natoms = len(structure.sites)
        label = 'scf: inpgen'
        description = '{} inpgen on {}'.format(self.ctx.description_wf, self.ctx.formula)

        inpgencode = self.inputs.inpgen
        if 'calc_parameters' in self.inputs:
            params = self.inputs.calc_parameters
        else:
            params = None
        
        options = {"max_wallclock_seconds" : int(self.ctx.options.get('max_wallclock_seconds')),
                   "resources" : self.ctx.options.get('resources', {"num_machines": 1}),
                   "queue_name" : self.ctx.options.get('queue_name', '')}
        # TODO do not use the same option for inpgen as for FLEUR... so far we ignore the others...
        # clean Idea might be to provide second inpgen options, currenly for our purposes not nessesary...
        self.report(options)
        inputs_build = get_inputs_inpgen(structure, inpgencode, options, label, description, params=params)
        self.report('INFO: run inpgen')
        future = submit(FleurinpProcess, **inputs_build)

        return ToContext(inpgen=future, last_calc=future)

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report(u'INFO: run change_fleurinp')
        if self.ctx.fleurinp: #something was already changed
            #print('Fleurinp already exists')
            return 
        elif 'fleurinp' in self.inputs:
            fleurin = self.inputs.fleurinp
        else:
            try:
                fleurin = self.ctx['inpgen'].out.fleurinpData
            except AttributeError:
                error = 'No fleurinpData found, inpgen failed'
                self.control_end_wc(error)
                return self.ERROR_INPGEN_CALCULATION_FAILED

        wf_dict = self.inputs.wf_parameters.get_dict()
        converge_te = wf_dict.get('converge_energy', False)
        fchanges = wf_dict.get('inpxml_changes', [])

        if not converge_te or fchanges:# change inp.xml file
            fleurmode = FleurinpModifier(fleurin)
            if not converge_te:
                dist = wf_dict.get('density_criterion', 0.00002)
                maxbroyd = wf_dict.get('maxiterbroyd', 8)
                fleurmode.set_inpchanges({'itmax': self.ctx.default_itmax, 'minDistance' : dist, 'maxIterBroyd' : maxbroyd})
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
                        return self.ERROR_CHANGING_FLEURINPUT_FAILED

                    else:# apply change
                        method(**para)

            # validate?
            apply_c = True
            try:
                fleurmode.show(display=False, validate=True)
            except XMLSyntaxError:
                error = ('ERROR: input, user wanted inp.xml changes did not validate')
                #fleurmode.show(display=True)#, validate=True)
                self.report(error)
                apply_c = False
                return self.ERROR_CALCULATION_INVALID_INPUT_FILE
            
            # apply
            if apply_c:
                out = fleurmode.freeze()
                self.ctx.fleurinp = out
            return
        else: # otherwise do not change the inp.xml
            self.ctx.fleurinp = fleurin
            return


    def run_fleur(self):
        """
        run a FLEUR calculation
        """
        self.report(u'INFO: run FLEUR')

        self.change_fleurinp()
        fleurin = self.ctx.fleurinp
        
        # TODO: ggf move the resource refinement somewhere else should be done only once, and maybe again if some parameters were changed in fleurinp
        if self.ctx.refine_resources:
            options = self.ctx.options.copy()
            # get_kpts # TODO: try to do this more efficient... also this can fail...
            kpt = fleurin.get_kpointsdata_nwf(fleurin)
            kpt_shape = kpt.get_shape('kpoints')
            nkpt = kpt_shape[0]
            # TODO; get computer memmory and ncores per node from computer and scheduler
            if not self.ctx.natoms:
                structure = fleurin.get_structuredata_nwf(fleurin)
                self.ctx.natoms = len(structure.sites)
            resources = options.get(u'resources', {u"num_machines": 1})
            ncores_per_node = 24 # TODO
            memmory_gb = 120 # TODO
            optimal_res = choose_resources_fleur(nkpt=nkpt, natm=self.ctx.natoms, max_resources=resources, ncores_per_node=ncores_per_node, memmory_gb=memmory_gb)
            #optimal_res: nodes, mpi_per node, openmp_num_thread, warnings
            
            option_keys = options.keys()
            res_keys = resources.keys()
            if 'tot_num_mpiprocs' in res_keys:
                new_resources = {'tot_num_mpiprocs' : optimal_res[0]*optimal_res[1]}
                if 'num_mpiprocs_per_machine' in res_keys:
                    new_resources['num_mpiprocs_per_machine'] = optimal_res[1]
                options['resources'] = new_resources
            elif 'num_machines' in res_keys:
                new_resources = {'num_machines' : optimal_res[0]}
                options[u'resources'] = new_resources
            
            if u'custom_scheduler_commands' in option_keys:
                sched_comd = options[u'custom_scheduler_commands']
                if 'span[ptile=' in sched_comd:
                    sched_comd = re.sub(u'ptile=\d?\d', u'ptile={}'.format(optimal_res[1]), sched_comd)
                options[u'custom_scheduler_commands'] = sched_comd
                
            if u'environment_variables' in option_keys:
                environment_variables = options[u'environment_variables']
                environment_variables[u'OMP_NUM_THREADS'] = u'{}'.format(optimal_res[2])
                options[u'environment_variables'] = environment_variables
            
            if u'max_memory_kb' in option_keys:
                max_memory_kb = int(memmory_gb*1000/optimal_res[1])
                options[u'max_memory_kb'] = max_memory_kb
            
            self.ctx.options = options
            self.report(u'changed options to {}'.format(options))
        else:
            options = self.ctx.options.copy()
        
        '''
        if 'settings' in self.inputs:
            settings = self.input.settings
        else:
            settings = ParameterData(dict={'files_to_retrieve' : [],
                                           'files_not_to_retrieve': [],
                                           'files_copy_remotely': [],
                                           'files_not_copy_remotely': [],
                                           'commandline_options': ["-wtime", "{}".format(self.ctx.options['max_wallclock_seconds'])],
                                           'blaha' : ['bla']})
        '''
        if self.ctx['last_calc']:
            # will this fail if fleur before failed? try needed?
            remote = self.ctx['last_calc'].out.remote_folder
        elif u'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        label = ' '
        description = ' '
        if self.ctx.formula:
            label = u'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = u'{} fleur run {} on {}'.format(self.ctx.description_wf, self.ctx.loop_count+1, self.ctx.formula)
        else:
            label = u'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = u'{} fleur run {}, fleurinp given'.format(self.ctx.description_wf, self.ctx.loop_count+1)

        code = self.inputs.fleur


        
        inputs_builder = get_inputs_fleur(code, remote, fleurin, options, label, description, serial=self.ctx.serial)
        future = submit(FleurProcess, **inputs_builder)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report(u'INFO: run FLEUR number: {}'.format(self.ctx.loop_count))
        self.ctx.calcs.append(future)

        return ToContext(last_calc=future)

    def inspect_fleur(self):
        """
        Analyse the results of the previous Calculation (Fleur or inpgen),
        checking whether it finished successfully or if not, troubleshoot the
        cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """
        #expected_states = [calc_states.FINISHED, calc_states.FAILED,
        #                   calc_states.SUBMISSIONFAILED]
        #print(self.ctx['last_calc'])
        #self.report(u'I am in inspect_fleur')
        try:
            calculation = self.ctx.last_calc
        except AttributeError:
            self.ctx.parse_last = False
            error = 'ERROR: Something went wrong I do not have a last calculation'
            self.control_end_wc(error)
            return self.ERROR_FLEUR_CALCULATION_FALIED
        calc_state = calculation.get_state()
        #self.report(u'the state of the last calculation is: {}'.format(calc_state))

        if calc_state != calc_states.FINISHED:
            error = ('ERROR: Last Fleur calculation failed somehow it is '
                    'in state {}'.format(calc_state))
            self.control_end_wc(error)
            return self.ERROR_FLEUR_CALCULATION_FALIED
        elif calc_state == calc_states.FINISHED:
            self.ctx.parse_last = True

        '''
        # Done: successful convergence of last calculation
        if calculation.has_finished_ok():
            self.report(u'converged successfully after {} iterations'.format(self.ctx.iteration))
            self.ctx.restart_calc = calculation
            self.ctx.is_finished = True

        # Abort: exceeded maximum number of retries
        elif self.ctx.iteration >= self.ctx.max_iterations:
            self.report(u'reached the max number of iterations {}'.format(self.ctx.max_iterations))
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
            self.report(u'calculation did not converge after {} iterations, restarting'.format(self.ctx.iteration))
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

        xpath_energy = '/fleurOutput/scfLoop/iteration/totalEnergy/@value'
        xpath_distance = '/fleurOutput/scfLoop/iteration/densityConvergence/chargeDensity/@distance' # be aware of magnetism
        #densityconvergence_xpath = 'densityConvergence'
        #chargedensity_xpath = 'densityConvergence/chargeDensity'
        #overallchargedensity_xpath = 'densityConvergence/overallChargeDensity'
        #spindensity_xpath = 'densityConvergence/spinDensity'
        if self.ctx.parse_last:#self.ctx.successful:
            #self.report('last calc successful = {}'.format(self.ctx.successful))
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
            #TODO: dangerous, can fail, error catching
            # TODO: is there a way to use a standard parser?
            outxmlfile = last_calc.out.output_parameters.dict.outputfile_path
            walltime = last_calc.out.output_parameters.dict.walltime
            if isinstance(walltime, int):
                self.ctx.total_wall_time = self.ctx.total_wall_time + walltime
            #outpara = last_calc.get('output_parameters', None)
            #outxmlfile = outpara.dict.outputfile_path
            parser = etree.XMLParser(recover=False)#, remove_blank_text=True)
            outfile_whole = True
            try:
                tree = etree.parse(outxmlfile, parser)
            except etree.XMLSyntaxError:
                outfile_whole = False
                errormsg = ('ERROR: SCF wc was not successful. The out.xml file of the last Fleur calculation is broken.'
                           ' FLEUR calc failed, through it was marked as FINISHED... I abort.')
                self.control_end_wc(errormsg)
                return self.ERROR_FLEUR_CALCULATION_FALIED
            
            if outfile_whole:
                root = tree.getroot()
                energies = eval_xpath2(root, xpath_energy)
                for energy in energies:
                    self.ctx.total_energy.append(float(energy))

                distances = eval_xpath2(root, xpath_distance)
                for distance in distances:
                    self.ctx.distance.append(float(distance))
        else:
            errormsg = 'ERROR: scf wc was not successful, check log for details'
            self.control_end_wc(errormsg)
            return self.ERROR_FLEUR_CALCULATION_FALIED
            # otherwise this will lead to erros further down

    def condition(self):
        """
        check convergence condition
        """

        density_converged = False
        energy_converged = False
        # TODO do a test first if last_calculation was successful, otherwise,
        # 'output_parameters' wont exist.
        inpwfp_dict = self.inputs.wf_parameters.get_dict()
        #last_charge_density = self.ctx.last_calc['output_parameters'].dict.charge_density
        # not a good fix for magnetic stuff, but for now, we want to test if the rest works.
        try:
            last_charge_density = self.ctx.last_calc.out.output_parameters.dict.charge_density
        except AttributeError:
            # magnetic system
            last_charge_density = self.ctx.last_calc.out.output_parameters.dict.overall_charge_density
            # divide by 2?
        self.ctx.last_charge_density = last_charge_density
        if inpwfp_dict.get('converge_density', True):
            if inpwfp_dict.get('density_criterion', 0.00002) >= last_charge_density:
                density_converged = True
        else:
            density_converged = True #since density convergence is not wanted

        energy = self.ctx.total_energy

        if len(energy) >= 2:
            self.ctx.energydiff = abs(energy[-1]-energy[-2])
        if inpwfp_dict.get('converge_energy', True):
            if inpwfp_dict.get('energy_criterion', 0.002) >= self.ctx.energydiff:
                energy_converged = True
        else:
            energy_converged = True #since energy convergence is not wanted

        if density_converged and energy_converged:
            self.ctx.successful = True
            return False
        elif self.ctx.loop_count >= self.ctx.max_number_runs:
            self.ctx.successful = False
            return False
        else:
            return True


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
        try: # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.last_calc.out['output_parameters']
            retrieved = self.ctx.last_calc.out['retrieved']
            last_calc_out_dict = last_calc_out.get_dict()
        except KeyError:
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None



        outputnode_dict = {}
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['material'] = self.ctx.formula
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = last_calc_out_dict.get('number_of_iterations_total', None)
        outputnode_dict['distance_charge'] = self.ctx.last_charge_density #last_calc_out_dict.get('charge_density', None)
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = last_calc_out_dict.get('energy_hartree', None)
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['distance_charge_units'] = 'me/bohr^3'
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['last_difference_total_energy'] = self.ctx.energydiff
        outputnode_dict['last_difference_total_energy_units'] = 'Htr'
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['last_calc_uuid'] = last_calc_uuid
        outputnode_dict['total_wall_time'] = self.ctx.total_wall_time
        outputnode_dict['total_wall_time_units'] = 'seconds'
        outputnode_dict['info'] = self.ctx.info
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors

        # maybe also store some information about the formula
        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids),
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.

        if self.ctx.successful:
            self.report(u'STATUS: Done, the convergence criteria are reached.\n'
                        'INFO: The charge density of the FLEUR calculation '
                        'converged after {} FLEUR runs, {} iterations and {} sec '
                        'walltime to {} "me/bohr^3" \n'
                        'INFO: The total energy difference of the last two iterations '
                        'is {} htr \n'.format(self.ctx.loop_count,
                                       last_calc_out_dict.get('number_of_iterations_total', None),
                                       self.ctx.total_wall_time,
                                       last_calc_out_dict.get('charge_density', None), 
                                       self.ctx.energydiff))

        else: # Termination ok, but not converged yet...
            if self.ctx.abort: # some error occured, donot use the output.
                self.report(u'STATUS/ERROR: I abort, see logs and '
                            'erros/warning/hints in output_scf_wc_para')
            else:
                self.report(u'STATUS/WARNING: Done, the maximum number of runs '
                            'was reached or something failed.\n INFO: The '
                            'charge density of the FLEUR calculation, '
                            'after {} FLEUR runs, {} iterations and {} sec '
                            'walltime is {} "me/bohr^3"\n'
                            'INFO: The total energy difference of the last '
                            'two interations is {} htr'
                            ''.format(self.ctx.loop_count,
                            last_calc_out_dict.get('number_of_iterations_total', None),
                            self.ctx.total_wall_time,
                            last_calc_out_dict.get('charge_density', None), self.ctx.energydiff))

        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids),
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.


        outputnode_t = ParameterData(dict=outputnode_dict)
         # this is unsafe so far, because last_calc_out could not exist...
        if last_calc_out:
            outdict = create_scf_result_node(outpara=outputnode_t, last_calc_out=last_calc_out, last_calc_retrieved=retrieved)
        else:
            outdict = create_scf_result_node(outpara=outputnode_t)

        if 'fleurinp' in self.inputs:
            outdict['fleurinp'] = self.inputs.fleurinp
        else:
            try:
                fleurinp = self.ctx['inpgen'].out.fleurinpData
            except AttributeError:
                self.report(u'ERROR: No fleurinp, something was wrong with the inpgen calc')
                fleurinp = None
                self.control_end_wc(u'ERROR: No fleurinp, something was wrong with the inpgen calc') # in the aiida 0.12 version
            outdict['fleurinp'] = fleurinp
        if last_calc_out:
            outdict[u'last_fleur_calc_output'] = last_calc_out

        #outdict['output_scf_wc_para'] = outputnode
        for link_name, node in outdict.iteritems():
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
        self.report(errormsg) # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()
        
        return
'''
if __name__ == "__main__":
    import argparse
    from aiida.orm import load_node
    from aiida_fleur.tools.common_fleur_wf import is_code
    
    parser = argparse.ArgumentParser(description=('SCF with FLEUR. workflow to'
                 ' converge the chargedensity and optional the total energy. all arguments are pks, or uuids, codes can be names'))
    parser.add_argument('--wf_para', type=ParameterData, dest='wf_parameters',
                        help='Some workflow parameters', required=False)
    parser.add_argument('--structure', type=StructureData, dest='structure',
                        help='The crystal structure node', required=False)
    parser.add_argument('--calc_para', type=ParameterData, dest='calc_parameters',
                        help='Parameters for the FLEUR calculation', required=False)
    parser.add_argument('--fleurinp', type=FleurInpData, dest='fleurinp',
                        help='FleurinpData from which to run the FLEUR calculation', required=False)
    parser.add_argument('--remote', type=RemoteData, dest='remote_data',
                        help=('Remote Data of older FLEUR calculation, '
                        'from which files will be copied (broyd ...)'), required=False)
    parser.add_argument('--inpgen', type=Code, dest='inpgen',
                        help='The inpgen code node to use', required=False)
    parser.add_argument('--fleur', type=Code, dest='fleur',
                        help='The FLEUR code node to use', required=True)

    args = parser.parse_args()
    
    # load_the nodes
    #if args.wf_parameters:
    wf_parameters = load_node(args.wf_parameters)
    
    structure = load_node(args.structure)
    
    #if args.calc_parameters:
    calc_parameters = load_node(args.calc_parameters)
    
    fleurinp = load_node(args.fleurinp)
    remote_data = load_node(args.remote_data)
    
    inpgen = is_code(args.inpgen)       
    fleur = is_code(args.fleur)    
    
    # TODO input logic....
    
    # submit fleur_scf_wc with different inputs.
    
    #res = submit(fleur_scf_wc,
    #          wf_parameters=wf_parameters,
    #          structure=structure,
    #          calc_parameters=args.calc_parameters,
    #          fleurinp=args.fleurinp,
    #          remote_data=args.remote_data,
    #          inpgen = args.inpgen,
    #          fleur=args.fleur)
'''


@wf
def create_scf_result_node(**kwargs):
    """
    This is a pseudo wf, to create the rigth graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in kwargs.iteritems():
        if key == 'outpara': #  should be alwasys there
            outpara = val
    outdict = {}
    outputnode = outpara.copy()#clone()
    outputnode.label = 'output_scf_wc_para'
    outputnode.description = ('Contains self-consistency results and '
                             'information of an fleur_scf_wc run.')

    outdict['output_scf_wc_para'] = outputnode
    # copy, because we rather produce the same node twice then have a circle in the database for now...
    #output_para = args[0]
    #return {'output_eos_wc_para'}
    return outdict
