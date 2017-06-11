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
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain
from aiida.work.workchain import while_, if_
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry


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
    _wf_default = {'fleur_runmax': 4, 
                   'density_criterion' : 0.00002, 
                   'energy_criterion' : 0.002, 
                   'converge_density' : True, 
                   'converge_energy' : False,
                   'resue' : True,
                   'queue_name' : ''}
    @classmethod
    def define(cls, spec):
        super(fleur_scf_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False, 
                   default=ParameterData(dict={'fleur_runmax': 4, 
                                               'density_criterion' : 0.00002, 
                                               'energy_criterion' : 0.002, 
                                               'converge_density' : True, 
                                               'converge_energy' : False,
                                               'reuse' : True}))
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
                cls.get_res),
            cls.return_results
        )
        spec.dynamic_output()

    def start(self):
        """
        init context and some parameters
        """
        self.report('started convergence workflow version {}'.format(self._workflowversion))
        self.report('Workchain node identifiers: {}'.format(ProcessRegistry().current_calc_node))
        print('started convergence workflow version {}'.format(self._workflowversion))
        print('Workchain node identifiers: {}'.format(ProcessRegistry().current_calc_node))
        
        # init
        self.ctx.last_calc = None
        self.ctx.loop_count = 0
        self.ctx.calcs = []
        self.ctx.successful = False
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
                print(warning)
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'inpgen' in inputs:
                warning = 'WARNING: Ignoring inpgen code input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
                self.report(warning)
        elif 'structure' in inputs:
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                print(error)
                self.ctx.errors.append(error)
                self.abort_nowait(error)
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            print(error)
            self.ctx.errors.append(error)
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
        print 'run inpgen'
        future = submit(FleurinpProcess, **inputs)

        return ToContext(inpgen=future, last_calc=future)
    
    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """

        #print('in change_fleurinp')
        
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

        if not converge_te:
            #if not energy convergence, set mindistance to criterium
            #itermax to 18 (less jobs needed)   
            dc = wf_dict.get('density_criterion', 0.00002)
            fleurmode = FleurinpModifier(fleurin)
            fleurmode.set_inpchanges({'itmax': 30, 'minDistance' : dc})
            out = fleurmode.freeze()
            self.ctx.fleurinp = out
            return
        else:
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
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        code = self.inputs.fleur
        options = {"max_wallclock_seconds": self.ctx.walltime_sec,
                   "resources": self.ctx.resources,
                   "queue_name" : self.ctx.queue}
        
        #inputs = get_inputs_fleur(code, remote, fleurin, options, settings=settings, serial=self.ctx.serial)
        inputs = get_inputs_fleur(code, remote, fleurin, options, serial=self.ctx.serial)
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
       
        last_calc = self.ctx.last_calc
        # TODO check calculation state:
        calc_state = 'FINISHED'
        if calc_state != 'FINISHED':
            #kill workflow in a controled way, call return results, or write a end_routine
            #TODO
            #TODO error handling here controled ending routine
            self.ctx.successful
            error = 'Fleur calculation failed somehow'
            self.abort(error)
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
        tree = etree.parse(outxmlfile)
        root = tree.getroot()
        energies = eval_xpath2(root, xpath_energy)
        for energy in energies:
            self.ctx.total_energy.append(float(energy))
        
        distances = eval_xpath2(root, xpath_distance)
        #print distances
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
        last_charge_density = self.ctx.last_calc.out.output_parameters.dict.charge_density
        #print last_charge_density
        if inpwfp_dict.get('converge_density', True):
            if inpwfp_dict.get('density_criterion', 0.00002) >= last_charge_density:
                density_converged = True
        else:
            density_converged = True
            
        energy = self.ctx.total_energy
        
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
        outputnode_dict ={}
        if self.ctx.successful:
            print('Done, the convergence criteria are reached.')
            print('The charge density of the FLEUR calculation pk= converged after {} FLEUR runs and {} iterations to {} '
                  '"me/bohr^3"'.format(self.ctx.loop_count, self.ctx.last_calc.out.output_parameters.dict.number_of_iterations_total,
                                       self.ctx.last_calc.out.output_parameters.dict.charge_density))
            print('The total energy difference of the last two interations is {} htr \n'.format(self.energydiff))
        else:
            print('Done, the maximum number of runs was reached or something failed.')
            print('The charge density of the FLEUR calculation pk= after {} FLEUR runs and {} iterations is {} "me/bohr^3"'
                  ''.format(self.ctx.loop_count, self.ctx.last_calc.out.output_parameters.dict.number_of_iterations_total,
                            self.ctx.last_calc.out.output_parameters.dict.charge_density))
            print('The total energy difference of the last two interations is {} htr \n'.format(self.energydiff))

        outputnode_dict['workflow_name'] = self.__class__.__name__# fleur_convergence
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = self.ctx.last_calc.out.output_parameters.dict.number_of_iterations_total
        outputnode_dict['distance_charge'] = self.ctx.last_calc.out.output_parameters.dict.charge_density
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = self.ctx.last_calc.out.output_parameters.dict.energy_hartree
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['distance_charge_units'] = ''
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid            
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
