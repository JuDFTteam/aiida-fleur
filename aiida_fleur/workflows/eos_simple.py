#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the workflow 'fleur_eos_wc_simple' for the calculation of
of an equation of state, with only the structure and optional wc parameters as input
"""

import numpy as np
from aiida.orm import Code, DataFactory, load_node
from aiida.orm.data.base import Float
from aiida.work.process_registry import ProcessRegistry
from aiida.work.workchain import WorkChain, ToContext#,Outputs
#from aiida.work import workfunction as wf
from aiida.work.run import submit
#from aiida_fleur.tools.StructureData_util import rescale, is_structure
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida_fleur.workflows.optimize_para import fleur_optimize_parameters_wc
from aiida_fleur.workflows.eos import fleur_eos_wc, eos_structures
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode


StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')

__copyright__ = (u"Copyright (c), 2017, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

class fleur_eos_wc_simple(WorkChain):
    """
    This workflow prepares the input parameters for an fleur_eos_wc and
    calls it for the calculation of the equation of states of a structure.


    :param wf_parameters: ParameterData node, optional, protocol specification will be parsed like this to fleur_eos_wc
    :param structure: StructureData node, bulk crystal structure
    :param inpgen: Code node,
    :param fleur: Code node,


    :return output_eos_wc_para: ParameterData node of fleur_eos_wc, contains relevant output information.
    about general succces, fit results and so on.

    """

    _workflowversion = "0.1.0"

    def __init__(self, *args, **kwargs):
        super(fleur_eos_wc_simple, self).__init__(*args, **kwargs)

    @classmethod
    def define(cls, spec):
        super(fleur_eos_wc_simple, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={
                       'fleur_runmax': 4,
                       'points' : 9,
                       'step' : 0.002,
                       'guess' : 1.00,
                       'resources' : {"num_machines": 1},#, "num_mpiprocs_per_machine" : 12},
                       'walltime_sec':  60*60,
                       'queue_name' : '',
                       'custom_scheduler_commands' : ''}))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.outline(
            cls.start,
            cls.determine_parameters,
            cls.run_eos_wc,
            cls.inspect_eos_wc,# or maybe merge with last step?
            cls.return_results
        )
        #spec.dynamic_output()

    # first we initialize everything,
    # get structure with lowest volume
    # find out the optiomal parameter for these structures.
    # then make as modular as possible


    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        self.report('started simple eos workflow version {}'.format(self._workflowversion))
        self.report("Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node))

        ### input check ### 

        # initialize contexts 

        self.ctx.last_calc2 = None
        self.ctx.calcs = []
        self.ctx.calcs_future = []
        self.ctx.structures = []
        self.ctx.temp_calc = None
        self.ctx.structurs_uuids = []
        self.ctx.scalelist = []
        self.ctx.volume = []
        self.ctx.volume_peratom = []
        self.ctx.org_volume = -1# avoid div 0
        self.ctx.labels = []
        self.ctx.successful = True
         
        
        # Check on inputnodes        
        
        inputs = self.inputs
        
        
        # wf_parameters:
        
        wf_dict = inputs.wf_parameters.get_dict()
        
        # set values, or DEFAULTS 
        self.ctx.points = wf_dict.get('points', 9)
        self.ctx.step = wf_dict.get('step', 0.002)
        self.ctx.guess = wf_dict.get('guess', 1.00)
        self.ctx.serial = wf_dict.get('serial', False)
        self.ctx.custom_scheduler_commands = wf_dict.get('custom_scheduler_commands', '')
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
            
        
        # codes
        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                self.control_end_wc(error)
                self.abort(error)

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                self.abort(error)
                
    def determine_parameters(self):
        """
        determine the optimal input parameters for the given structure
        """

        points = self.ctx.points
        step = self.ctx.step
        guess = self.ctx.guess
        startscale = guess-(points-1)/2*step

        for point in range(points):
            self.ctx.scalelist.append(startscale + point*step)
       
        smallest_structure = eos_structures(self.inputs.structure, self.ctx.scalelist[0])[0]
        

        optimize_res = submit(fleur_optimize_parameters_wc, 
                                    structure=smallest_structure, 
                                    inpgen=self.inputs.inpgen, 
                                    fleur=self.inputs.fleur)
        #wf_parameters
        
        return ToContext(optimize_res=optimize_res)

    def run_eos_wc(self):
        """
        Run the fleur_eos_wc
        """

        structure = self.inputs.structure
        eos_wc_para = self.inputs.wf_parameters
        optimize_res = self.ctx.optimize_res
        calc_parameters = optimize_res.get('optimized_para')
        fleur = self.inputs.fleur
        inpgen = self.inputs.inpgen
        
        form = structure.get_formula()
        label = 'fleur_eos_wc on {}'.format(form)
        description = 'Fleur eos of {}'.format(form)

        eos_res = submit(fleur_eos_wc, wf_parameters=eos_wc_para, fleur=fleur, inpgen=inpgen, 
                structure=structure, calc_parameters=calc_parameters, 
                _label=label, _description=description)    
 
        return ToContext(**eos_res)

   
    def inspect_eos_wc(self):
        """
        Check the results of the fleur_eos_wc        
        """
        # TODO: check on the returns of fleur_eos_wc
        pass



    def return_results(self):
        """
        Return the result node of fleur_eos_wc
        """
        
        returndict = {}

        if self.ctx.successful:
            self.report('Done, Simple equation of states calculation complete')

            returndict['output_eos_wc_para'] = self.ctx.eos_res['output_eos_wc_para']
            returndict['output_eos_wc_structure'] = self.ctx.eos_res['output_eos_wc_structure']         
        else:
            self.report('Done, but something failed in fleur_eos_wc.')
 

        # create link to workchain node
        for link_name, node in returndict.iteritems():
            self.out(link_name, node)    