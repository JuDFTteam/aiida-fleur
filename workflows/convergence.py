#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the worklfow 'fleur_convergence' for a self-consistency 
cylce of a FLEUR calculation with AiiDA.
"""

#TODO: more info in output, log warnings
#TODO: make smarter, ggf delete broyd or restart with more or less iterations
#TODO: other error handling, where is known what to do
#TODO: test in each step if calculation before had a problem
#TODO: maybe write dict schema for wf_parameter inputs

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import Code, DataFactory
from aiida.tools.codespecific.fleur.queue_defaults import queue_defaults
from aiida.work.workchain import WorkChain
from aiida.work.workchain import while_, if_
#from aiida.work.run import run, submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry
from aiida.tools.codespecific.fleur.decide_ncore import decide_ncore
from aiida.orm.calculation.job.fleur_inp.fleurinputgen import FleurinputgenCalculation
from aiida.orm.calculation.job.fleur_inp.fleur import FleurCalculation

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
#FleurInpData = DataFactory('fleurinp.fleurinp')
FleurInpData = DataFactory('fleurinp')
FleurProcess = FleurCalculation.process()
FleurinpProcess = FleurinputgenCalculation.process()

class fleur_convergence(WorkChain):
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
     
    @classmethod
    def define(cls, spec):
        super(fleur_convergence, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False, 
                   default=ParameterData(dict={'fleur_runmax': 4, 
                                               'density_criterion' : 0.00002, 
                                               'energy_criterion' : 0.002, 
                                               'converge_density' : True, 
                                               'converge_energy' : True}))
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
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
                cls.get_res),
            cls.return_results
        )
        #spec.dynamic_output()

    def start(self):
        """
        init context and some parameters
        """
        
        print 'started convergence workflow version {}'.format(self._workflowversion)
        print "Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node)
        
        # init
        self.ctx.last_calc = None
        self.ctx.loop_count = 0
        self.ctx.calcs = []
        self.ctx.successful = False
        self.ctx.distance = []
        self.ctx.total_energy = []
        self.energydiff = 1000
        self.ctx.warnings = []
        self.ctx.errors = []
        wf_dict = self.inputs.wf_parameters.get_dict()
        
        # if MPI in code name, execute parallel
        self.ctx.serial = True

        # set values, or defaults
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        #queue = wf_dict.get('queue', '')
        self.ctx.resources = ''
        self.ctx.walltime_sec = ''
        queue = wf_dict.get('queue', None)

        computer = self.inputs.fleur.get_computer()
        
        if queue:
            qres = queue_defaults(queue, computer)

        res = wf_dict.get('resources', {"num_machines": 1})
        
        if res:
            self.ctx.resources = res
        wt = wf_dict.get('walltime_sec', 10*30)
        if wt:
            self.ctx.walltime_sec = wt
        #print wt, res


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
                print(warning)
                self.ctx.warnings.append(warning)
            if 'inpgen' in inputs:
                warning = 'WARNING: Ignoring inpgen code input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
        elif 'structure' in inputs:
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                print(error)
                self.ctx.errors.append(error)
                #kill workflow
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            print(error)
            self.ctx.errors.append(error)
            #kill workflow        
        
        return run_inpgen


    def run_fleurinpgen(self):
        """
        run the inpgen
        """        
        inputs = {}        
        inputs = self.get_inputs_inpgen()
        print 'run inpgen'
        future = submit(FleurinpProcess, **inputs)

        return ToContext(inpgen=future, last_calc=future)


    def get_inputs_inpgen(self):
        """
        get the input for a inpgen calc
        """
        inputs = FleurinpProcess.get_inputs_template()
        inputs.structure = self.inputs.structure
        inputs.code = self.inputs.inpgen
        if 'calc_parameters' in self.inputs:
            inputs.parameters = self.inputs.calc_parameters
        inputs._options.resources = {"num_machines": 1}
        inputs._options.max_wallclock_seconds = 360
        inputs._options.withmpi = False
        #inputs._options.computer = computer
        '''
                "max_wallclock_seconds": int,
                "resources": dict,
                "custom_scheduler_commands": unicode,
                "queue_name": basestring,
                "computer": Computer,
                "withmpi": bool,
                "mpirun_extra_params": Any(list, tuple),
                "import_sys_environment": bool,
                "environment_variables": dict,
                "priority": unicode,
                "max_memory_kb": int,
                "prepend_text": unicode,
                "append_text": unicode,
        '''
        return inputs

    def get_inputs_fleur(self):
        """
        get the input for a FLEUR calc
        """

        inputs = FleurProcess.get_inputs_template()
        if 'fleurinp' in self.inputs:
            fleurin = self.inputs.fleurinp
        else:
            fleurin = self.ctx['inpgen'].out.fleurinpData
        
        if self.ctx['last_calc']:
            remote = self.ctx['last_calc'].out.remote_folder
            inputs.parent_folder = remote
        elif 'remote_data' in self.inputs:
            inputs.parent_folder = self.inputs.remote_data
        inputs.code = self.inputs.fleur
        inputs.fleurinpdata = fleurin
        
        core=12 # get from computer nodes per machine
                
        # this should be done by fleur in my opinion
        nkpoints = fleurin.inp_dict.get(
                       'calculationSetup', {}).get(
                       'bzIntegration', {}).get(
                       'kPointList', {}).get(
                       'count', None)
        
        if not nkpoints:
            pass # get KpointCount, KpointMesh
            nkpoints = fleurin.inp_dict.get(
                            'calculationSetup', {}).get(
                            'bzIntegration', {}).get(
                            'kPointCount', {}).get(
                            'count', None)     
             
                                               
        if nkpoints:
            core = decide_ncore(nkpoints, core)
            print('using {} cores'.format(core))
        else:
            warning = 'WARNING: nkpoints not know, parallelisation might be wrong'
            print(warning)
            self.ctx.warnings.append(warning)
        inputs._options.resources = {"num_machines": 1, "num_mpiprocs_per_machine" : core}
        inputs._options.max_wallclock_seconds = 30 * 60
        # if code local use
        #if self.inputs.fleur.is_local():
        #    inputs._options.computer = computer
        #    #else use computer from code.
        #else:
        #    inputs._options.queue_name = 'th1'
        
        if self.ctx.serial:
            inputs._options.withmpi = False # for now
            inputs._options.resources = {"num_machines": 1}
        #inputs._label = 'Fleur'
        
        return inputs

    def run_fleur(self):
        """
        run a FLEUR calculation
        """
        #print 'run fleur'


        inputs = {}
        inputs = self.get_inputs_fleur()
        #print inputs
        future = submit(FleurProcess, **inputs)
        self.ctx.loop_count = self.ctx.loop_count + 1
        print 'run FLEUR number: {}'.format(self.ctx.loop_count)
        self.ctx.calcs.append(future)

        return ToContext(last_calc=future) #calcs.append(future),

    def get_res(self):
        """
        Check how the last Fleur calculation went
        Parse some results.
        """
        # TODO maybe do this different 
        # or if complexer output node exists take from there.
        from aiida.tools.codespecific.fleur.xml_util import eval_xpath2
        from lxml import etree
        #from lxml.etree import XMLSyntaxError
        
        xpath_energy = '/fleurOutput/scfLoop/iteration/totalEnergy/@value'
        xpath_distance = '/fleurOutput/scfLoop/iteration/densityConvergence/chargeDensity/@distance' # be aware of magnetism
        
        last_calc = self.ctx.last_calc
        outxmlfile = last_calc.out.output_parameters.dict.outputfile_path
        tree = etree.parse(outxmlfile)
        root = tree.getroot()
        energies = eval_xpath2(root, xpath_energy)
        for energy in energies:
            self.ctx.total_energy.append(float(energy))
        
        distances = eval_xpath2(root, xpath_distance)
        for distance in distances:        
            self.ctx.distance.append(float(distance))
        
    def condition(self):
        """
        check convergence condition
        """
        density_converged = False
        energy_converged = False
        # TODO do a test first if last_calculation was successful, otherwise,
        # 'output_parameters' wont exist.
        inpwfp_dict = self.inputs.wf_parameters.get_dict()
        last_charge_density = self.ctx.last_calc.out.output_parameters.dict.charge_density
        print last_charge_density
        if inpwfp_dict.get('converge_density', True):
            if inpwfp_dict.get('density_criterion', 0.00002) >= last_charge_density:
                density_converged = True
        else:
            density_converged = True
            
        energy = self.ctx.total_energy
        
        if len(energy) >=2:
            self.energydiff = abs(energy[-1]-energy[-2])
        print self.energydiff 
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
        outputnode_dict ={}
        if self.ctx.successful:
            print('Done, the convergence criteria are reached.')
            print('The charge density of the FLEUR calculation pk= converged after {} FLEUR runs and {} iterations to {} '
                  '"me/bohr^3"'.format(self.ctx.loop_count, self.ctx.last_calc.out.output_parameters.dict.number_of_iterations_total,
                                       self.ctx.last_calc.out.output_parameters.dict.charge_density))
            print('The total energy difference of the last two interations is {} htr'.format(self.energydiff))
        else:
            print('Done, the maximum number of runs was reached or something failed.')
            print('The charge density of the FLEUR calculation pk= after {} FLEUR runs and {} iterations is {} "me/bohr^3"'
                  ''.format(self.ctx.loop_count, self.ctx.last_calc.out.output_parameters.dict.number_of_iterations_total,
                            self.ctx.last_calc.out.output_parameters.dict.charge_density))
            print('The total energy difference of the last two interations is {} htr'.format(self.energydiff))

        outputnode_dict['workflow_name'] = self.__class__.__name__# fleur_convergence
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = self.ctx.last_calc.out.output_parameters.dict.number_of_iterations_total
        outputnode_dict['distance_charge'] = self.ctx.last_calc.out.output_parameters.dict.charge_density
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = self.ctx.last_calc.out.output_parameters.dict.energy_hartree
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['distance_charge_units'] = ''
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['Warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        #also lognotes, which then can be parsed from subworkflow too workflow, list of calculations involved (pks, and uuids), 
        #This node should contain everything you wish to plot, here iteration versus, total energy and distance.

        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        if 'fleurinp' in self.inputs:
            outdict['fleurinp'] = self.inputs.fleurinp
        else:
            outdict['fleurinp'] = self.ctx['inpgen'].out.fleurinpData
        outdict['outputnode'] = outputnode
        print outdict
        for k, v in outdict.iteritems():
            self.out(k, v)

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
    res = fleur_convergence.run(wf_parameters=args.wf_parameters, 
                                structure=args.structure, 
                                calc_parameters=args.calc_parameters,
                                fleurinp=args.fleurinp,
                                remote_data=args.remote_data,
                                inpgen = args.inpgen, 
                                fleur=args.fleur)