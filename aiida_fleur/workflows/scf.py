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
#TODO: maybe write dict schema for wf_parameter inputs
#TODO: Idea pass structure extras, save them in outputnode? no
#TODO: get density for magnetic structures
#TODO: set minDistance and higher iteration number, ggf change logic for total energy
#TODO: check if calculation already exists
# TODO test if code given if fleur and inpgen code, uses the right plugin.
#TODO write a routine that calls self.abort and produced there output nodes dict with errors all keys and
# successful false

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain
from aiida.work.workchain import while_, if_
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry
from aiida.common.datastructures import calc_states
from aiida.work.workchain import Outputs

from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.xml_util import eval_xpath2
from lxml import etree

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
    This workflow converges a FLEUR calculation (SCF).
    It converges the charge density and optional the total energy

    Two paths are possible: 

    (1) Start from a structure and run the inpgen first
    (2) Start from a Fleur calculation, with optional remoteData

    :Params: wf_parameters: parameterData node,
    :Params: structure : structureData node,
    :Params: calc_parameters: parameterData node,
    :Params: fleurinp:  fleurinpData node,
    :Params: remote_data: remoteData node,
    :Params: inpgen: Code node,
    :Params: fleur: Code node,

    :returns: Success, last result node, list with convergence behavior

    minimum input example: 
    1. Code1, Code2, Structure, (Parameters), (wf_parameters)
    2. Code2, FleurinpData, (wf_parameters)

    maximum input example: 
    1. Code1, Code2, Structure, Parameters 
                           wf_parameters: {
                           'density_criterion' : Float,
                           'energy_criterion' : Float,
                           'converge_density' : True,
                           'converge_energy' : True,
                           'queue' : String,
                           'resources' : dict(
                               {"num_machines": int, "num_mpiprocs_per_machine" : int})
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
                   'label' : 'fleur_scf_wc',        # label for the workchain node and all sporned calculations by the wc
                   'description' : 'Fleur self consistensy cycle workchain', # description (see label)
                   'inpxml_changes' : []}      # (expert) List of further changes applied after the inpgen run
                                                    # tuples (function_name, [parameters]), the ones from fleurinpmodifier
                                                    # example: ('set_nkpts' , {'nkpts': 500,'gamma': False}) ! no checks made, there know what you are doing
    
    def __init__(self, *args, **kwargs):
        super(fleur_scf_wc, self).__init__(*args, **kwargs)    
    
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
                                               'label' : 'fleur_scf_wc',
                                               'description' : 'Fleur self consistensy cycle workchain',
                                               'inpxml_changes' : []}))
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
            cls.run_fleur,
            cls.get_res,
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
        self.report('INFO: started convergence workflow version {}'.format(self._workflowversion))
        self.report('INFO: Workchain node identifiers: {}'.format(ProcessRegistry().current_calc_node))
        #print('started convergence workflow version {}'.format(self._workflowversion))
        #print('Workchain node identifiers: {}'.format(ProcessRegistry().current_calc_node))
        
        # init
        self.ctx.last_calc = None
        self.ctx.loop_count = 0
        self.ctx.calcs = []
        self.ctx.successful = True
        self.ctx.distance = []
        self.ctx.total_energy = []
        self.energydiff = 10000
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.fleurinp = None
        wf_dict = self.inputs.wf_parameters.get_dict()
        
        if wf_dict == {}:
            wf_dict = self._wf_default
        
        # if MPI in code name, execute parallel
        self.ctx.serial = wf_dict.get('serial', False)#True

        # set values, or defaults
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        self.ctx.resources = wf_dict.get('resources', {"num_machines": 1})
        self.ctx.walltime_sec = wf_dict.get('walltime_sec', 60*60)
        self.ctx.queue = wf_dict.get('queue_name', '')


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
                #print(warning)
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'inpgen' in inputs:
                warning = 'WARNING: Ignoring inpgen code input, because Fleurinp was given'
                #print(warning)
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input, because Fleurinp was given'
                #print(warning)
                self.ctx.warnings.append(warning)
                self.report(warning)
        elif 'structure' in inputs:
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                #print(error)
                self.ctx.errors.append(error)
                self.abort_nowait(error)
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            #print(error)
            self.ctx.errors.append(error)
            self.abort_nowait(error)
        
        # maybe ckeck here is unessesary...        
        wf_dict = self.inputs.wf_parameters.get_dict()
        
        if wf_dict == {}:
            wf_dict = self._wf_default
        
        # check format of inpxml_changes
        fchanges = wf_dict.get('inpxml_changes', [])
        if fchanges:
            for change in fchanges:
                print('change : {}'.format(change))
                # somehow the tuple type gets destroyed on the way and becomes a list
                if (not isinstance(change, tuple)) and (not isinstance(change, list)):
                    error = 'ERROR: Wrong Input inpxml_changes wrong format of : {} should be tuple of 2. I abort'.format(change)
                    self.abort_nowait(error)

        return run_inpgen


    def run_fleurinpgen(self):
        """
        run the inpgen
        """        
        structure = self.inputs.structure
        inpgencode = self.inputs.inpgen
        if 'calc_parameters' in self.inputs:
            params = self.inputs.calc_parameters
        else:
            params = None
        
        options = {"max_wallclock_seconds": self.ctx.walltime_sec,
                   "resources": self.ctx.resources,
                   "queue_name" : self.ctx.queue}
        
        inputs = get_inputs_inpgen(structure, inpgencode, options, params=params)        
        self.report('INFO: run inpgen')
        future = submit(FleurinpProcess, **inputs)

        return ToContext(inpgen=future, last_calc=future)
    
    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """

        #print('in change_fleurinp')
        # TODO recongize inpgen fail, then no fleurin exists...


        if self.ctx.fleurinp: #something was already changed
            #print('Fleurinp already exists')
            return
        elif 'fleurinp' in self.inputs:
            fleurin = self.inputs.fleurinp
        else:
            try:
                fleurin = self.ctx['inpgen'].out.fleurinpData
            except:
                error = 'No fleurinpData found, inpgen failed'
                self.abort_nowait(error)
        
        wf_dict = self.inputs.wf_parameters.get_dict()
        converge_te = wf_dict.get('converge_energy', False)
        fchanges = wf_dict.get('inpxml_changes', [])
        
        if not converge_te or fchanges:# change inp.xml file
            #if not energy convergence, set mindistance to criterium
            #itermax to 18 (less jobs needed)   
            
            fleurmode = FleurinpModifier(fleurin)
            if not converge_te:
                dc = wf_dict.get('density_criterion', 0.00002)
                fleurmode.set_inpchanges({'itmax': 30, 'minDistance' : dc})
            avail_ac_dict = fleurmode.get_avail_actions()
            # apply further user dependend changes
            if fchanges:
                for change in fchanges:
                    function = change[0]
                    para = change[1]
                    method = avail_ac_dict.get(function, None)
                    if not method:
                        error = ("ERROR: Input 'inpxml_changes', function {}"
                                 "is not known to fleurinpmodifier class, "
                                 "plaese check/test your input. I abort..."
                                 "".format(method))
                        self.abort(error)
                    else:# apply change
                        #method(para)
                        method(**para)
                        
            # validate?
            apply_c = True
            try:
                fleurmode.show(display=False, validate=True)
            except:
                error = ('ERROR: input, user wanted inp.xml changes did not validate')
                self.abort(error)
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
            settings = ParameterData(dict={'files_to_retrieve' : [], 'files_not_to_retrieve': [], 
                               'files_copy_remotely': [], 'files_not_copy_remotely': [],
                               'commandline_options': ["-wtime", "{}".format(self.ctx.walltime_sec)], 'blaha' : ['bla']})
        '''
        if self.ctx['last_calc']:
            # will this fail if fleur before failed? try needed?
            remote = self.ctx['last_calc'].out.remote_folder
            #print('found last calc remote folder')
            #print(remote)
            #print(self.ctx['last_calc'])
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
            #print('remote from input')#is this taken only once or all the time?
        else:
            remote = None
            #print('no remote')
        code = self.inputs.fleur
        options = {"max_wallclock_seconds": self.ctx.walltime_sec,
                   "resources": self.ctx.resources,
                   "queue_name" : self.ctx.queue}
        
        #inputs = get_inputs_fleur(code, remote, fleurin, options, settings=settings, serial=self.ctx.serial)
        inputs = get_inputs_fleur(code, remote, fleurin, options, serial=self.ctx.serial)
        #print inputs
        future = submit(FleurProcess, **inputs)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report('INFO: run FLEUR number: {}'.format(self.ctx.loop_count))
        #print 'run FLEUR number: {}'.format(self.ctx.loop_count)
        self.ctx.calcs.append(future)

        #return ToContext(last_calc=Outputs(future)) #calcs.append(future),
        return ToContext(last_calc=future)

    def inspect_fleur(self):
        """
        Analyse the results of the previous Calculation (Fleur or inpgen), checking whether it finished successfully
        or if not troubleshoot the cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """
        #expected_states = [calc_states.FINISHED, calc_states.FAILED, calc_states.SUBMISSIONFAILED]
        #print(self.ctx['last_calc'])
        
        try:
            calculation = self.ctx['last_calc']
        except Exception:
            self.ctx.successful = False
            self.abort_nowait('ERROR: Something went wrong I do not have a last calculation')
            #self.report('ERROR: Something went wrong I do not have a last calculation')
            return

        calc_state = calculation.get_state()
        print(calc_state)
        if calc_state != calc_states.FINISHED:
            #kill workflow in a controled way, call return results, or write a end_routine
            #TODO
            #TODO error handling here controled ending routine
            self.ctx.successful = False
            error = 'ERROR: Last Fleur calculation failed somehow it is in state {}'.format(calc_state)
            #self.report(error)
            self.abort_nowait(error)
            return


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

        return
        '''  
    def get_res(self):
        """
        Check how the last Fleur calculation went
        Parse some results.
        """
        #print('In get_res')
        # TODO maybe do this different 
        # or if complexer output node exists take from there.

        #from lxml.etree import XMLSyntaxError
        
        xpath_energy = '/fleurOutput/scfLoop/iteration/totalEnergy/@value'
        xpath_distance = '/fleurOutput/scfLoop/iteration/densityConvergence/chargeDensity/@distance' # be aware of magnetism
 
        #densityconvergence_xpath = 'densityConvergence'
        #chargedensity_xpath = 'densityConvergence/chargeDensity'
        #overallchargedensity_xpath = 'densityConvergence/overallChargeDensity'
        #spindensity_xpath = 'densityConvergence/spinDensity'
        if not self.ctx.successful:
            #print('not successful')
            return # otherwise this will lead to erros further down
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
        #print(last_calc)
        outxmlfile = last_calc.out.output_parameters.dict.outputfile_path
        #outpara = last_calc.get('output_parameters', None)
        #outxmlfile = outpara.dict.outputfile_path
        tree = etree.parse(outxmlfile)
        root = tree.getroot()
        energies = eval_xpath2(root, xpath_energy)
        #print(energies)
        for energy in energies:
            self.ctx.total_energy.append(float(energy))
        
        #print(self.ctx.total_energy)
        distances = eval_xpath2(root, xpath_distance)
        #print self.ctx.distance
        for distance in distances:
            self.ctx.distance.append(float(distance))
        
    def condition(self):
        """
        check convergence condition
        """
        #print('condition')
        
        density_converged = False
        energy_converged = False
        # TODO do a test first if last_calculation was successful, otherwise,
        # 'output_parameters' wont exist.
        inpwfp_dict = self.inputs.wf_parameters.get_dict()
        #last_charge_density = self.ctx.last_calc['output_parameters'].dict.charge_density
        last_charge_density = self.ctx.last_calc.out.output_parameters.dict.charge_density
        #print last_charge_density
        if inpwfp_dict.get('converge_density', True):
            if inpwfp_dict.get('density_criterion', 0.00002) >= last_charge_density:
                density_converged = True
        else:
            density_converged = True
            
        energy = self.ctx.total_energy
        #print(energy)
        if len(energy) >=2:
            self.energydiff = abs(energy[-1]-energy[-2])
        #print self.energydiff 
        if inpwfp_dict.get('converge_energy', True):
            if inpwfp_dict.get('energy_criterion', 0.002) >= self.energydiff:
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
        """
        #TODO report
        last_calc_out = self.ctx.last_calc.out.output_parameters.dict
        #last_calc_out = self.ctx.last_calc['output_parameters'].dict
        outputnode_dict ={}


        outputnode_dict['workflow_name'] = self.__class__.__name__# fleur_convergence
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = last_calc_out.number_of_iterations_total
        outputnode_dict['distance_charge'] = last_calc_out.charge_density
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = last_calc_out.energy_hartree
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['distance_charge_units'] = 'me/bohr^3'
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid            
        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids), 
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.

        if self.ctx.successful:
            self.report('STATUS: Done, the convergence criteria are reached.\n'
                        'INFO: The charge density of the FLEUR calculation pk= '
                        'converged after {} FLEUR runs and {} iterations to {} '
                        '"me/bohr^3"'.format(self.ctx.loop_count, 
                                       last_calc_out.number_of_iterations_total,
                                       last_calc_out.charge_density))
            self.report('INFO: The total energy difference of the last two iterations '
                        'is {} htr \n'.format(self.energydiff))
        else:
            self.report('STATUS/WARNING: Done, the maximum number of runs was reached or something failed.\n'
                        'INFO: The charge density of the FLEUR calculation pk= '
                        'after {} FLEUR runs and {} iterations is {} "me/bohr^3"'
                        ''.format(self.ctx.loop_count, 
                            last_calc_out.number_of_iterations_total,
                            last_calc_out.charge_density))
            self.report('INFO: The total energy difference of the last two interations'
                        'is {} htr'.format(self.energydiff))

        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids), 
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.

            
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        if 'fleurinp' in self.inputs:
            outdict['fleurinp'] = self.inputs.fleurinp
        else:
            outdict['fleurinp'] = self.ctx['inpgen'].out.fleurinpData
        outdict['output_scf_wc_para'] = outputnode
        #print outdict
        for link_name, node in outdict.iteritems():
            self.out(link_name, node)

    def bad_ending(self):
        pass
    
    def handle_fleur_failure(self):
        pass
    
    def handle_inpgen_failure(self):
        pass
    
    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        """
        outputnode_dict = {}
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        if 'fleurinp' in self.inputs:
            outdict['fleurinp'] = self.inputs.fleurinp
        else:
            outdict['fleurinp'] = self.ctx['inpgen'].out.fleurinpData
        outdict['output_scf_wc_para'] = outputnode
        #print outdict
        for link_name, node in outdict.iteritems():
            self.out(link_name, node)      
        
        self.abort_nowait(errormsg)
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SCF with FLEUR. workflow to'
                 ' converge the chargedensity and optional the total energy.')
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
    res = fleur_scf_wc.run(wf_parameters=args.wf_parameters, 
                                structure=args.structure, 
                                calc_parameters=args.calc_parameters,
                                fleurinp=args.fleurinp,
                                remote_data=args.remote_data,
                                inpgen = args.inpgen, 
                                fleur=args.fleur)


def test_and_get_codenode(codenode, expected_code_type, use_exceptions=False):
    """
    Pass a code node and an expected code (plugin) type. Check that the
    code exists, is unique, and return the Code object. 
    
    :param codenode: the name of the code to load (in the form label@machine)
    :param expected_code_type: a string with the plugin that is expected to
      be loaded. In case no plugins exist with the given name, show all existing
      plugins of that type
    :param use_exceptions: if True, raise a ValueError exception instead of
      calling sys.exit(1)
    :return: a Code object
    """
    import sys
    from aiida.common.exceptions import NotExistent
    from aiida.orm import Code

    try:
        if codenode is None:
            raise ValueError
        code = codenode
        if code.get_input_plugin_name() != expected_code_type:
            raise ValueError
    except (NotExistent, ValueError):
        from aiida.orm.querybuilder import QueryBuilder
        qb = QueryBuilder()
        qb.append(Code,
                  filters={'attributes.input_plugin':
                               {'==': expected_code_type}},
                  project='*')

        valid_code_labels = ["{}@{}".format(c.label, c.get_computer().name)
                             for [c] in qb.all()]

        if valid_code_labels:
            msg = ("Pass as further parameter a valid code label.\n"
                   "Valid labels with a {} executable are:\n".format(
                expected_code_type))
            msg += "\n".join("* {}".format(l) for l in valid_code_labels)

            if use_exceptions:
                raise ValueError(msg)
            else:
                print >> sys.stderr, msg
                sys.exit(1)
        else:
            msg = ("Code not valid, and no valid codes for {}.\n"
                   "Configure at least one first using\n"
                   "    verdi code setup".format(
                expected_code_type))
            if use_exceptions:
                raise ValueError(msg)
            else:
                print >> sys.stderr, msg
                sys.exit(1)

    return code
