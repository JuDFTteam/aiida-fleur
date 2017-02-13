#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the worklfow 'corelevel' using the Fleur code, which calculates Binding
energies and corelevel shifts with different methods.
'divide and conquer'
"""
# TODO alow certain kpoint path, or kpoint node, so far auto
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
    
import os.path
from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry
#from aiida.orm.calculation.job.fleur_inp.fleurinputgen import FleurinputgenCalculation
from aiida.orm.calculation.job.fleur_inp.fleur import FleurCalculation
from aiida.orm.data.fleurinp.fleurinpmodifier import FleurinpModifier
from aiida.work.workchain import while_, if_
from aiida.tools.codespecific.fleur import create_corehole

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleurinp')
FleurProcess = FleurCalculation.process()


class inital_state_CLS(WorkChain):
    '''
    Turn key solution for the calculation of core level shift and Binding energies
    

    '''
    # wf_Parameters: ParameterData, 
    '''
    'method' : ['initial', 'full_valence ch', 'half_valence_ch', 'ch', ...]
    'Bes' : [W4f, Be1s]
    'CLS' : [W4f, Be1s]
    'atoms' : ['all', 'postions' : []]
    'references' : ['calculate', and use # calculate : 'all' , or 'calculate' : ['W', 'Be']
    'scf_para' : {...}, 'default' 
    'relax' : True
    'relax_mode': ['Fleur', 'QE Fleur', 'QE']
    'relax_para' : {...}, 'default' 
    'calculate_doses' : False
    'dos_para' : {...}, 'default' 
    '''
    '''
    # defaults 
    default wf_Parameters::
    'method' : 'initial'
    'atoms' : 'all
    'references' : 'calculate' 
    'scf_para' : 'default' 
    'relax' : True
    'relax_mode': 'QE Fleur'
    'relax_para' : 'default' 
    'calculate_doses' : False
    'dos_para' : 'default'
    '''
    
    _workflowversion = "0.0.1"
    _default_wf_para = {'references' : {'calculate' : 'all'}, 
                        'calculate_doses' : False,
                        'relax' : True,
                        'relax_mode': 'QE Fleur',
                        'relax_para' : 'default',
                        'scf_para' : 'default',
                        'dos_para' : 'default',
                        'same_para' : True,
                        'resources' : {"num_machines": 1},
                        'walltime_sec' : 10*30,
                        'queue' : None,
                        'serial' : False}

    @classmethod
    def define(cls, spec):
        super(inital_state_CLS, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict=self._default_wf_para))
        spec.input("fleurinp", valid_type=FleurinpData, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("inpgen", valid_type=Code, required=False)        
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.outline(
            cls.check_input,
            cls.get_refernces,
            cls.run_fleur_scfs,
            if_(cls.relaxation_needed)(
                cls.relax),
            cls.find_parameters,
            cls.run_fleur_scfs,
            if_(cls.calculate_dos)(
                cls.dos),
            cls.collect_results,
            cls.return_results
        )
        #spec.dynamic_output()


    def check_iput(self):
        """
        check what input is given if it makes sence
        """
        ### input check ### ? or done automaticly, how optional?
        print('Started inital_state_CLS workflow version {}'.format(self._workflowversion))
        print("Workchain node identifiers: {}"
              "".format(ProcessRegistry().current_calc_node))
        
        # init
        self.ctx.last_calc = None
        self.ctx.eximated_jobs = 0
        self.ctx.run_jobs = 0
        self.ctx.calcs = []
        self.ctx.calcs_torun = []
        self.ctx.dos_to_calc = []
        self.ctx.struc_to_relax = []
        self.ctx.successful = False
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.CLS = {}
        
        # set values, or defaults
        wf_dict = self.inputs.wf_parameters.get_dict()
        default = self._default_wf_para

        self.ctx.serial = wf_dict.get('serial', default.get('serial'))
        self.ctx.same_para = wf_dict.get('same_para', default.get('same_para'))
        self.ctx.dos = wf_dict.get('calculate_doses', default.get('calculate_doses'))
        self.ctx.dos_para = wf_dict.get('dos_para', default.get('dos_para'))
        self.ctx.relax = wf_dict.get('relax', default.get('relax'))
        self.ctx.relax_mode = wf_dict.get('relax_mode', default.get('relax_mode'))
        self.ctx.relax_para = wf_dict.get('relax_para', default.get('dos_para'))
        self.ctx.resources = wf_dict.get('resources', default.get('resources'))
        self.ctx.walltime_sec = wf_dict.get('walltime_sec', default.get('walltime_sec'))
        self.ctx.queue = wf_dict.get('queue', default.get('queue'))
        
        
        inputs = self.inputs        
        if 'fleurinp' in inputs:
            structure = inputs.fleurinp.get_structuredata(inputs.fleurinp)
            self.ctx.elements = list(structure.get_composition().keys())
            self.calcs_torun.append(inputs.get('fleurinp'))
            if 'structure' in inputs:
                warning = 'WARNING: Ignoring Structure input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
        elif 'structure' in inputs:
            self.ctx.elements = list(inputs.structure.get_composition().keys())
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                print(error)
                self.ctx.errors.append(error)
                #kill workflow
            if 'calc_parameters' in inputs:
                self.calcs_torun.append((inputs.get('calc_parameters'), inputs.get('structure')))
            else:
                self.calcs_torun.append(inputs.get('structure'))
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            print(error)
            self.ctx.errors.append(error)
            #kill workflow          
        print('elements in structure: {}'.format(self.ctx.elements))
        
        
    def get_refernces(self):
        """
        To calculate a CLS in inital state approx, we need reference calculations
        to the Elemental crystals. First it is checked if the user has provided them
        Second the database is checked, if there are structures with certain extras.
        Third the COD database is searched for the elemental Cystal structures.
        If some referneces are not found stop here.
        Are there already calculation of these 'references'.
        Put these calculation in the queue
        """
        print('In Get_references inital_state_CLS workflow')   
        references = self.inputs.wf_parameters.get_dict().get('references', {'calculate' : 'all'})
        
        to_calc = {}
        results_ref = {}
        calculate = references.get('calculate', 'all')
        
        for elem in self.ctx.elements:
            to_calc[elem] = 'find' 
        if calculate != 'all':
            pass
            # remove some calcs from to_calc and check if 
            
        if references.get('use', {}): # if reference results are given in some form
            #as {'element' : float, or 'element': FleurCalculation} don't calculate them anew
            for elm, source in references.get('use').iteritems():
                re = to_calc.pop('elm') # no calc needed
                # convert results into {'W' : [float]} # TODO: be careful about atom types
                #if source float add
                #elif source int, load and check if calculation, if yes get correlevel from results.
                #elif source calc, as above
                results_ref[elem] = source
        '''                  
        for key, val in references.iteritems():
            if key == 'calculate':
                if val == 'all':
                    pass
                    # for element in self.ctx.elements:
                    # look in 'given'    
                    # querry db for structures, cif files
                    # if not found querry online?
                else:
                    for element, pk in val.iteritems():
                        pass
                        # if element not in self elements, ignore, print,log warning?
            elif key == 'use':
                
            else:
                print('This key: {} with value: {} is not supported'.format(key, val))
                #TODO warning
        '''
    '''        
    def find_references(search_dict):
        """
        This methods finds
        """
        #TODO write this routine
        from aiida.orm import QueryBuilder
        results = []
        structures_pks = []
        structures_formulae = []

        #query db
        structures_pks = []
        q = QueryBuilder()
        q.append(StructureData,
            #filters = {'extras.specification.project' : {'==' : 'Fusion'}}
            filters = {'extras.type' : {'==' : 'simple bulk'}}
            #or filters = {'extras.type' : {'==' : 'element'}}
            )
        structures = q.all()
        
        
        return results         
    '''        
    def relaxation_needed(self):
        """
        If the structures should be relaxed, check if their Forces are below a certain 
        threshold, otherwise throw them in the relaxation wf.
        """
        print('In relaxation inital_state_CLS workflow')
        if self.ctx.relax:
            # TODO check all forces of calculations
            forces_fine = True
            if forces_fine:
                return True
            else:
                return False
        else:
            return False
    
    
    def relax(self):
        """
        Do structural relaxation for certain structures.
        """
        print('In relax inital_state_CLS workflow')        
        for calc in self.ctx.dos_to_calc:
            pass 
            # TODO run relax workflow
        

    
    def calculate_dos(self):
        """
        Run SCF-cycles for all structures, calculations given in certain workflow arrays.
        """
        print('In calculate_dos? inital_state_CLS workflow')        
        if self.ctx.dos:
            return True
        else:
            return False   

    def dos(self):
        """
        Calculate a density of states for certain calculations.
        """
        print('In dos inital_state_CLS workflow')        
        for calc in self.ctx.dos_to_calc:
            pass 
            # TODO run dos workflow
        
    
    def run_fleur_scfs(self):
        """
        Run SCF-cycles for all structures, calculations given in certain workflow arrays.
        """
        print('In run_fleur_scfs inital_state_CLS workflow')        
        #from aiida.work import run, async, 
        from aiida.tools.codespecific.fleur.convergence import fleur_convergence
        res_all = []
        # for each calulation in self.ctx.calcs_torun
        for node in calcs_torun:
            if isinstance(node, structureData):
                res = fleur_convergence.submit(structure=node, 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, fleurinpData):
                res = fleur_convergence.submit(structure=node, 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, (StructureData, ParameterData)):
                res = fleur_convergence.submit(wf_parameters=node(1), structure=node(0), 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            res_all.append(res)
         return ToContext(last_calc=future) #calcs.append(future)
        '''    
        inputs = get_inputs_fleur(code, remote, fleurin, options)
        future = submit(FleurProcess, **inputs)
        self.ctx.loop_count = self.ctx.loop_count + 1
        print 'run FLEUR number: {}'.format(self.ctx.loop_count)
        self.ctx.calcs.append(future)
        '''
        return ToContext(last_calc=future) #calcs.append(future),            
    def collect_results(self):
        """
        Collect results from certain calculation, check if everything is fine, 
        calculate the wanted quantities.
        """
        print('Collecting results of inital_state_CLS workflow')        
        pass


    def return_results(self):
        """
        return the results of the calculations
        """
        # TODO more here
        print('Inital_state_CLS workflow Done')
        #print corelevel shifts were calculated bla bla
        
        outputnode_dict ={}
        
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['Warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['Corelevelshifts'] = self.ctx.CLS               

        #print outputnode_dict
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['Inital_state_CLS_out'] = outputnode
        #print outdict
        for k, v in outdict.iteritems():
            self.out(k, v)


    def create_new_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.inputs.wf_parameters.get_dict()
        nkpts = wf_dict.get('nkpts', 500) 
        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        sigma = wf_dict.get('sigma', 0.005)
        emin = wf_dict.get('emin', -0.30)
        emax = wf_dict.get('emax', 0.80)
      
        fleurmode = FleurinpModifier(self.inputs.fleurinp)

        #change_dict = {'band': True, 'ndir' : -1, 'minEnergy' : self.inputs.wf_parameters.get_dict().get('minEnergy', -0.30000000), 
        #'maxEnergy' :  self.inputs.wf_parameters.get_dict().get('manEnergy','0.80000000'), 
        #'sigma' :  self.inputs.wf_parameters.get_dict().get('sigma', '0.00500000')}
        change_dict = {'band': True, 'ndir' : 0, 'minEnergy' : emin,
                       'maxEnergy' : emax, 'sigma' : sigma} #'ndir' : 1, 'pot8' : True
        
        fleurmode.set_inpchanges(change_dict)

        if nkpts:
            fleurmode.set_nkpts(count=nkpts)
            #fleurinp_new.replace_tag()
        
        fleurmode.show(validate=True, display=False) # needed?
        fleurinp_new = fleurmode.freeze()
        self.ctx.fleurinp1 = fleurinp_new
        print(fleurinp_new)
        #print(fleurinp_new.folder.get_subfolder('path').get_abs_path(''))

        
    def run_fleur(self):
        '''
        run a fleur calculation
        '''
        FleurProcess = FleurCalculation.process()
        inputs = {}
        inputs = self.get_inputs_fleur()
        #print inputs
        future = submit(FleurProcess, **inputs)
        print 'run Fleur in band workflow'

        return ToContext(last_calc=future)