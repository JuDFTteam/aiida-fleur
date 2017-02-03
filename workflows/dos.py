#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the worklfow 'dos' for the Fleur code, which calculates a
density of states (DOS).
"""
#TODO:
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
    
import os.path
from aiida.orm import Code, DataFactory
#from aiida.tools.codespecific.fleur.queue_defaults import queue_defaults
from aiida.work.workchain import WorkChain
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry
#from aiida.tools.codespecific.fleur.decide_ncore import decide_ncore
#from aiida.orm.calculation.job.fleur_inp.fleurinputgen import FleurinputgenCalculation
from aiida.orm.calculation.job.fleur_inp.fleur import FleurCalculation
from aiida.orm.data.fleurinp.fleurinpmodifier import FleurinpModifier


StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleurinp')
FleurProcess = FleurCalculation.process()


class dos(WorkChain):
    '''
    This workflow calculated a DOS from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior
    '''
    # wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    # defaults : tria = True, nkpts = 800, sigma=0.005, emin= , emax =
    
    _workflowversion = "0.1.0"
    
    @classmethod
    def define(cls, spec):
        super(dos, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={
                                         'tria' : True, 
                                         'nkpts' : 800, 
                                         'sigma' : 0.005,
                                         'emin' : -0.30, 
                                         'emax' :  0.80}))
        spec.input("remote", valid_type=RemoteData, required=True)#TODO ggf run convergence first
        spec.input("fleurinp", valid_type=FleurinpData, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.outline(
            cls.start,
            cls.create_new_fleurinp,
            cls.run_fleur,
            cls.return_results
        )
        #spec.dynamic_output()


    def start(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        print('started dos workflow version {}'.format(self._workflowversion))
        print("Workchain node identifiers: {}"
              "".format(ProcessRegistry().current_calc_node))
        
        self.ctx.fleurinp1 = ""
        self.ctx.last_calc = None
        
        self.ctx.successful = False #TODO
        self.ctx.warnings = []
        # if MPI in code name, execute parallel
        self.ctx.serial = True
        
        wf_dict = self.inputs.wf_parameters.get_dict()
        
        
        
    def create_new_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.inputs.wf_parameters.get_dict()
        nkpts = wf_dict.get('nkpts', 800) 
        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        tria = wf_dict.get('tria', True)
        sigma = wf_dict.get('sigma', 0.005)
        emin = wf_dict.get('emin', -0.30)
        emax = wf_dict.get('emax', 0.80)
      
        fleurmode = FleurinpModifier(self.inputs.fleurinp)

        #change_dict = {'dos': True, 'ndir' : -1, 'minEnergy' : self.inputs.wf_parameters.get_dict().get('minEnergy', -0.30000000), 
        #'maxEnergy' :  self.inputs.wf_parameters.get_dict().get('manEnergy','0.80000000'), 
        #'sigma' :  self.inputs.wf_parameters.get_dict().get('sigma', '0.00500000')}
        change_dict = {'dos': True, 'ndir' : -1, 'minEnergy' : emin,
                       'maxEnergy' : emax, 'sigma' : sigma}
        
        fleurmode.set_inpchanges(change_dict)
        if tria:
            change_dict = {'mode': 'tria'}
            fleurmode.set_inpchanges(change_dict)
        if nkpts:
            fleurmode.set_nkpts(count=nkpts)
            #fleurinp_new.replace_tag()
        fleurmode.show(validate=True, display=False) # needed?
        fleurinp_new = fleurmode.freeze()
        self.ctx.fleurinp1 = fleurinp_new
        #print(fleurinp_new)
        #print(fleurinp_new.folder.get_subfolder('path').get_abs_path(''))

    def get_inputs_fleur(self):
        '''
        get the input for a FLEUR calc
        '''
        inputs = FleurProcess.get_inputs_template()

        fleurin = self.ctx.fleurinp1
        #print fleurin
        remote = self.inputs.remote
        inputs.parent_folder = remote
        inputs.code = self.inputs.fleur
        inputs.fleurinpdata = fleurin
        
        # TODO nkpoints decide n core

        core = 12 # get from computer nodes per machine
        inputs._options.resources = {"num_machines": 1, "num_mpiprocs_per_machine" : core}
        inputs._options.max_wallclock_seconds = 30 * 60
          
        if self.ctx.serial:
            inputs._options.withmpi = False # for now
            inputs._options.resources = {"num_machines": 1}
        
        return inputs
        
    def run_fleur(self):
        '''
        run a fleur calculation
        '''
        FleurProcess = FleurCalculation.process()
        inputs = {}
        inputs = self.get_inputs_fleur()
        #print inputs
        future = submit(FleurProcess, **inputs)
        print 'run Fleur in dos workflow'

        return ToContext(last_calc=future)

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        print('Dos workflow Done')
        print('A DOS was calculated for calculation {} and is found under pk=, '
              'calculation {}')#.format(self.ctx.last_calc, ctx['last_calc'] )
        
        #check if dos file exists: if not succesful = False
        #TODO be careful with general DOS.X
        dosfilename = 'DOS.1' # ['DOS.1', 'DOS.2', ...]
        # TODO this should be easier...
        dosfilepath = self.ctx.last_calc.get_outputs_dict()['retrieved'].folder.get_subfolder('path').get_abs_path(dosfilename)
        print dosfilepath
        #dosfilepath = "path to dosfile" # Array?
        if os.path.isfile(dosfilepath):
            self.ctx.successful = True
        else:
            dosfilepath = None
        
        outputnode_dict ={}
        
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['Warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        #outputnode_dict['last_calc_pk'] = self.ctx.last_calc.pk
        #outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid
        outputnode_dict['dosfile'] = dosfilepath
        
        #print outputnode_dict
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['dos_out'] = outputnode
        #print outdict
        for k, v in outdict.iteritems():
            self.out(k, v)
