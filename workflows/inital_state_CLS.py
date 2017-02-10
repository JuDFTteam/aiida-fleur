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
    'references' : ['calculate', or 
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
    
    @classmethod
    def define(cls, spec):
        super(inital_state_CLS, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={
                                            'method' : 'initial',
                                            'atoms' : 'all',
                                            'references' : 'calculate', 
                                            'calculate_doses' : False,
                                            'relax' : True,
                                            'relax_mode': 'QE Fleur',
                                            'relax_para' : 'default',
                                            'scf_para' : 'default',
                                            'dos_para' : 'default'}))
        spec.input("fleurinp", valid_type=FleurinpData, required=True)
        spec.input("fleur", valid_type=Code, required=True)
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
            cls.collect_results,
            cls.return_results
        )
        #spec.dynamic_output()


    def check_iput(self):
        """
        check what input is given if it makes sence
        """
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        print('Started inital_state_CLS workflow version {}'.format(self._workflowversion))
        print("Workchain node identifiers: {}"
              "".format(ProcessRegistry().current_calc_node))
        '''
        outputnode_dict['Warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['Corelevelshifts'] = self.ctx.CLS   
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
        self.ctx.serial = wf_dict.get('serial', False)#True

        # set values, or defaults
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        self.ctx.resources = wf_dict.get('resources', {"num_machines": 1})
        self.ctx.walltime_sec = wf_dict.get('walltime_sec', 10*30)
        self.ctx.queue = wf_dict.get('queue', None)
        '''
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
        pass
    
    def relaxation_needed(self):
        """
        If the structures should be relaxed, check if their Forces are below a certain 
        threshold, otherwise throw them in the relaxation wf.
        """
        print('In relaxation inital_state_CLS workflow')
        pass
    
    def run_fleur_scfs(self):
        """
        Run SCF-cycles for all structures, calculations given in certain workflow arrays.
        """
        print('In run_fleur_scfs inital_state_CLS workflow')        
        pass

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