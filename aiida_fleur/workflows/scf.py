#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the worklfow 'fleur_convergence' for a self-consistency
cylce of a FLEUR calculation with AiiDA.
"""
#TODO: more info in output, log warnings
#TODO: make smarter, ggf delete broyd or restart with more or less iterations
# you can use the pattern of the density convergence for this
#TODO: other error handling, where is known what to do
#TODO: test in each step if calculation before had a problem
#TODO: maybe write dict schema for wf_parameter inputs, how?
from lxml import etree
from lxml.etree import XMLSyntaxError

from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain, while_, if_, ToContext
from aiida.work.run import submit, run
from aiida.work import workfunction as wf
from aiida.work.process_registry import ProcessRegistry
from aiida.common.datastructures import calc_states
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.tools.xml_util import eval_xpath2
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


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
                        'converge_energy' : True,
                        'queue' : String,
                        'resources' : dict({"num_machines": int, "num_mpiprocs_per_machine" : int})
                        'walltime' : int}
    2. Code2, FleurinpData, (remote-data), wf_parameters as in 1.

    Hints:
    1. This workflow does not work with local codes!
    """

    _workflowversion = "0.1.0"
    _wf_default = {'fleur_runmax': 4,              # Maximum number of fleur jobs/starts (defauld 30 iterations per start)
                   'density_criterion' : 0.00002,  # Stop if charge denisty is converged below this value
                   'energy_criterion' : 0.002,     # if converge energy run also this total energy convergered below this value
                   'converge_density' : True,      # converge the charge density
                   'converge_energy' : False,      # converge the total energy (usually converged before density)
                   'resue' : True,                 # AiiDA fastforwarding (currently not there yet)
                   'queue_name' : '',              # Queue name to submit jobs too
                   'resources': {"num_machines": 1},# resources to allowcate for the job
                   'walltime_sec' : 60*60,          # walltime after which the job gets killed (gets parsed to fleur)
                   'serial' : False,                # execute fleur with mpi or without
                   #'label' : 'fleur_scf_wc',        # label for the workchain node and all sporned calculations by the wc
                   #'description' : 'Fleur self consistensy cycle workchain', # description (see label)
                   'inpxml_changes' : [],      # (expert) List of further changes applied after the inpgen run
                   'custom_scheduler_commands' : ''}                                 # tuples (function_name, [parameters]), the ones from fleurinpmodifier
                                                    # example: ('set_nkpts' , {'nkpts': 500,'gamma': False}) ! no checks made, there know what you are doing
    #_default_wc_label = u'fleur_scf_wc'
    #_default_wc_description = u'fleur_scf_wc: Fleur self consistensy cycle workchain, converges the total energy.'


    @classmethod
    def define(cls, spec):
        super(fleur_scf_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={'fleur_runmax': 4,
                                               'density_criterion' : 0.00002,
                                               'energy_criterion' : 0.002,
                                               'converge_density' : True,
                                               'converge_energy' : False,
                                               'reuse' : True,
                                               'resources': {"num_machines": 1},
                                               'walltime_sec': 60*60,
                                               'queue_name': '',
                                               'serial' : False,
                                               'inpxml_changes' : [],
                                               'custom_scheduler_commands' : ''}))
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.input("settings", valid_type=ParameterData, required=False)
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
        #spec.dynamic_output()

    def start(self):
        """
        init context and some parameters
        """
        self.report('INFO: started convergence workflow version {}\n'
                    'INFO: Workchain node identifiers: {}'
                    ''.format(self._workflowversion, ProcessRegistry().current_calc_node))

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
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        self.ctx.resources = wf_dict.get('resources', {"num_machines": 1})
        self.ctx.walltime_sec = wf_dict.get('walltime_sec', 60*60)
        self.ctx.queue = wf_dict.get('queue_name', '')
        self.ctx.custom_scheduler_commands = wf_dict.get('custom_scheduler_commands', '')
        self.ctx.description_wf = self.inputs.get('_description', '') + '|fleur_scf_wc|'
        self.ctx.label_wf = self.inputs.get('_label', 'fleur_scf_wc')

        # return para/vars
        self.ctx.successful = True
        self.ctx.distance = []
        self.ctx.total_energy = []
        self.ctx.energydiff = 10000
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.fleurinp = None
        self.ctx.formula = ''

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
                self.ctx.errors.append(error)
                self.control_end_wc(error)
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            self.ctx.errors.append(error)
            self.control_end_wc(error)

        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                self.control_end_wc(error)

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)

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

        return run_inpgen


    def run_fleurinpgen(self):
        """
        run the inpgen
        """
        structure = self.inputs.structure
        self.ctx.formula = structure.get_formula()
        label = 'scf: inpgen'
        description = '{} inpgen on {}'.format(self.ctx.description_wf, self.ctx.formula)

        inpgencode = self.inputs.inpgen
        if 'calc_parameters' in self.inputs:
            params = self.inputs.calc_parameters
        else:
            params = None

        options = {"max_wallclock_seconds": self.ctx.walltime_sec,
                   "resources": self.ctx.resources,
                   "queue_name" : self.ctx.queue}

        inputs = get_inputs_inpgen(structure, inpgencode, options, label, description, params=params)
        self.report('INFO: run inpgen')
        future = submit(FleurinpProcess, **inputs)

        return ToContext(inpgen=future, last_calc=future)

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """

        # TODO recongize inpgen fail, then no fleurin exists...

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


        wf_dict = self.inputs.wf_parameters.get_dict()
        converge_te = wf_dict.get('converge_energy', False)
        fchanges = wf_dict.get('inpxml_changes', [])

        if not converge_te or fchanges:# change inp.xml file
            fleurmode = FleurinpModifier(fleurin)
            if not converge_te:
                dist = wf_dict.get('density_criterion', 0.00002)
                fleurmode.set_inpchanges({'itmax': 30, 'minDistance' : dist})
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

                    else:# apply change
                        method(**para)

            # validate?
            apply_c = True
            try:
                fleurmode.show(display=False, validate=True)
            except XMLSyntaxError:
                error = ('ERROR: input, user wanted inp.xml changes did not validate')
                #fleurmode.show(display=True)#, validate=True)
                self.control_end_wc(error)

                apply_c = False

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

        self.change_fleurinp()
        fleurin = self.ctx.fleurinp
        '''
        if 'settings' in self.inputs:
            settings = self.input.settings
        else:
            settings = ParameterData(dict={'files_to_retrieve' : [],
                                           'files_not_to_retrieve': [],
                                           'files_copy_remotely': [],
                                           'files_not_copy_remotely': [],
                                           'commandline_options': ["-wtime", "{}".format(self.ctx.walltime_sec)],
                                           'blaha' : ['bla']})
        '''
        if self.ctx['last_calc']:
            # will this fail if fleur before failed? try needed?
            remote = self.ctx['last_calc'].out.remote_folder
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        label = ' '
        description = ' '
        if self.ctx.formula:
            label = 'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = '{} fleur run {} on {}'.format(self.ctx.description_wf, self.ctx.loop_count+1, self.ctx.formula)
        else:
            label = 'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = '{} fleur run {}, fleurinp given'.format(self.ctx.description_wf, self.ctx.loop_count+1)

        code = self.inputs.fleur
        options = {"max_wallclock_seconds": self.ctx.walltime_sec,
                   "resources": self.ctx.resources,
                   "queue_name" : self.ctx.queue}#,
        if self.ctx.custom_scheduler_commands:
            options["custom_scheduler_commands"] = self.ctx.custom_scheduler_commands
        inputs = get_inputs_fleur(code, remote, fleurin, options, label, description, serial=self.ctx.serial)


        future = submit(FleurProcess, **inputs)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report('INFO: run FLEUR number: {}'.format(self.ctx.loop_count))
        self.ctx.calcs.append(future)

        return ToContext(last_calc=future)

    def inspect_fleur(self):
        """
        Analyse the results of the previous Calculation (Fleur or inpgen),
        checking whether it finished successfully or if not troubleshoot the
        cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """
        #expected_states = [calc_states.FINISHED, calc_states.FAILED, 
        #                   calc_states.SUBMISSIONFAILED]
        #print(self.ctx['last_calc'])
        #self.report('I am in inspect_fleur')
        try:
            calculation = self.ctx.last_calc
        except AttributeError:
            self.ctx.successful = False
            error = 'ERROR: Something went wrong I do not have a last calculation'
            self.control_end_wc(error)
            return
        calc_state = calculation.get_state()
        #self.report('the state of the last calculation is: {}'.format(calc_state))

        if calc_state != calc_states.FINISHED:
            #TODO kill workflow in a controled way, call return results, or write a end_routine
            self.ctx.successful = False
            self.ctx.abort = True
            error = ('ERROR: Last Fleur calculation failed somehow it is '
                    'in state {}'.format(calc_state))
            self.control_end_wc(error)
            return
        elif calc_state == calc_states.FINISHED:
            pass

        '''
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

        xpath_energy = '/fleurOutput/scfLoop/iteration/totalEnergy/@value'
        xpath_distance = '/fleurOutput/scfLoop/iteration/densityConvergence/chargeDensity/@distance' # be aware of magnetism
        #densityconvergence_xpath = 'densityConvergence'
        #chargedensity_xpath = 'densityConvergence/chargeDensity'
        #overallchargedensity_xpath = 'densityConvergence/overallChargeDensity'
        #spindensity_xpath = 'densityConvergence/spinDensity'
        if self.ctx.successful:
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
            outxmlfile = last_calc.out.output_parameters.dict.outputfile_path
            #outpara = last_calc.get('output_parameters', None)
            #outxmlfile = outpara.dict.outputfile_path
            tree = etree.parse(outxmlfile)
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
            return # otherwise this will lead to erros further down

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
        if inpwfp_dict.get('converge_density', True):
            if inpwfp_dict.get('density_criterion', 0.00002) >= last_charge_density:
                density_converged = True
        else:
            density_converged = True

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
            last_calc_out_dict = last_calc_out.get_dict()
        except AttributeError:
            last_calc_out = None
            last_calc_out_dict = {}



        outputnode_dict = {}
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['material'] = self.ctx.formula
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = last_calc_out_dict.get('number_of_iterations_total', None)
        outputnode_dict['distance_charge'] = last_calc_out_dict.get('charge_density', None)
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = last_calc_out_dict.get('energy_hartree', None)
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['distance_charge_units'] = 'me/bohr^3'
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['last_calc_uuid'] = last_calc_uuid
        # maybe also store some information about the formula
        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids),
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.

        if self.ctx.successful:
            self.report('STATUS: Done, the convergence criteria are reached.\n'
                        'INFO: The charge density of the FLEUR calculation pk= '
                        'converged after {} FLEUR runs and {} iterations to {} '
                        '"me/bohr^3" \n'
                        'INFO: The total energy difference of the last two iterations '
                        'is {} htr \n'.format(self.ctx.loop_count,
                                       last_calc_out_dict.get('number_of_iterations_total', None),
                                       last_calc_out_dict.get('charge_density', None), self.ctx.energydiff))

        else: # Termination ok, but not converged yet...
            if self.ctx.abort: # some error occured, donot use the output.
                self.report('STATUS/ERROR: I abort, see logs and '
                            'erros/warning/hints in output_scf_wc_para')
            else:
                self.report('STATUS/WARNING: Done, the maximum number of runs '
                            'was reached or something failed.\n INFO: The '
                            'charge density of the FLEUR calculation pk= '
                            'after {} FLEUR runs and {} iterations is {} "me/bohr^3"\n'
                            'INFO: The total energy difference of the last '
                            'two interations is {} htr'
                            ''.format(self.ctx.loop_count,
                            last_calc_out_dict.get('number_of_iterations_total', None),
                            last_calc_out_dict.get('charge_density', None), self.ctx.energydiff))

        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids),
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.


        outputnode_t = ParameterData(dict=outputnode_dict)
         # this is unsafe so far, because last_calc_out could not exist...
        if last_calc_out:
            outdict = create_scf_result_node(outpara=outputnode_t, last_calc_out=last_calc_out)
        else:
            outdict = create_scf_result_node(outpara=outputnode_t)

        if 'fleurinp' in self.inputs:
            outdict['fleurinp'] = self.inputs.fleurinp
        else:
            try:
                fleurinp = self.ctx['inpgen'].out.fleurinpData
            except AttributeError:
                self.report('ERROR: No fleurinp, something was wrong with the inpgen calc')
                fleurinp = None
            outdict['fleurinp'] = fleurinp
        if last_calc_out:
            outdict['last_fleur_calc_output'] = last_calc_out

        #outdict['output_scf_wc_para'] = outputnode
        for link_name, node in outdict.iteritems():
            self.out(link_name, node)


    def bad_ending(self):
        """
        controled shutdown
        """
        return

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
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg) # because return_results still fails somewhen
        self.return_results()
        #self.abort_nowait(errormsg)
        self.abort(errormsg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=('SCF with FLEUR. workflow to'
                 ' converge the chargedensity and optional the total energy.'))
    parser.add_argument('--wf_para', type=ParameterData, dest='wf_parameters',
                        help='The pseudopotential family', required=False)
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
    res = run(fleur_scf_wc, 
              wf_parameters=args.wf_parameters,
              structure=args.structure,
              calc_parameters=args.calc_parameters,
              fleurinp=args.fleurinp,
              remote_data=args.remote_data,
              inpgen = args.inpgen,
              fleur=args.fleur)



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
    outputnode = outpara.copy()
    outputnode.label = 'output_scf_wc_para'
    outputnode.description = ('Contains self-consistency results and '
                             'information of an fleur_scf_wc run.')

    outdict['output_scf_wc_para'] = outputnode
    # copy, because we rather produce the same node twice then have a circle in the database for now...
    #output_para = args[0]
    #return {'output_eos_wc_para'}
    return outdict
