#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the workflow 'fleur_optimize_parameter_wc', which finds
working/(in the future, optiomal) flapw parameters for a given Structure
"""

#import numpy as np
from aiida.orm import Code, DataFactory#, load_node
#from aiida.orm.data.base import Float
from aiida.work.process_registry import ProcessRegistry
from aiida.work.workchain import WorkChain, ToContext#,Outputs
#from aiida.work import workfunction as wf
from aiida.work.run import submit
#from aiida_fleur.tools.StructureData_util import rescale, is_structure
#from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
#from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
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
#FleurProcess = FleurCalculation.process()
FleurinpProcess = FleurinputgenCalculation.process()


__copyright__ = (u"Copyright (c), 2017, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


class fleur_optimize_parameters_wc(WorkChain):
    """
    This workflow finds out working/(in the future optimal) flapw parameters
    from a structure. For now, it runs inpgen on the structure and uses 
    the Fleur defaults.

    :param wf_parameters: ParameterData node, optional, protocol specification will be parsed like this to fleur_eos_wc
    :param structure: StructureData node, bulk crystal structure
    :param inpgen: Code node,
    :param fleur: Code node,

    :return output_optimized_wc_para: ParameterData node, contains relevant output information 
                                      about general succces.
    :return optimized_para: ParameterData node usable by inpgen
    :return optimized_fleurinp: FleurinpData with optimized 

    """

    _workflowversion = "0.1.0"

    def __init__(self, *args, **kwargs):
        super(fleur_optimize_parameters_wc, self).__init__(*args, **kwargs)

    @classmethod
    def define(cls, spec):
        super(fleur_optimize_parameters_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={
                       'resources' : {"num_machines": 1},#, "num_mpiprocs_per_machine" : 12},
                       'walltime_sec':  60*60,
                       'queue_name' : '',
                       'custom_scheduler_commands' : ''}))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=False)
        spec.outline(
            cls.start,
            cls.run_inpgen,
            cls.determine_parameters,
            cls.return_results
        )
        #spec.dynamic_output()
        
        
    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        self.report('started fleur_optimize_parameter workflow version {}'.format(self._workflowversion))
        self.report("Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node))

        ### input check ### 

        # initialize contexts 

        self.ctx.successful = True
        # Check on inputnodes        
        
        inputs = self.inputs
        
        # wf_parameters:
        wf_dict = inputs.wf_parameters.get_dict()
        
        # set values, or DEFAULTS 
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

        
    def run_inpgen(self):
        """
        So far run inpgen and see what you get
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


    def determine_parameters(self):
        """
        Determine_parameters, so far extract them from FleurinpData
        """
        
        try:
            fleurin = self.ctx['inpgen'].out.fleurinpData
        except AttributeError:
            error = 'No fleurinpData found, inpgen failed'
            self.control_end_wc(error)
        
        # TODO this has to be implemented
        self.ctx.optimal_parameters = fleurin.get_parameter_data()
        
        
    def return_results(self):
        """
        Prepare and return the result nodes
        """
        
        if self.ctx.optimal_parameters:
            optimal_parameters_uuid = self.ctx.optimal_parameters.uuid
        else:
            optimal_parameters_uuid = None
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'structure': self.inputs.structure.uuid,
               'optimal_para' : optimal_parameters_uuid,
               'successful' : self.ctx.successful}        
        
        outnode = ParameterData(dict=out)
        
        returndict = {}

        if self.ctx.successful:
            self.report('Done, fleur_optimize_parameter_wc calculation complete')

            returndict['output_optimized_wc_para'] = outnode
            returndict['optimized_para'] = self.ctx.optimal_parameters
            #optimized_fleurinp
        else:
            self.report('Done, but something failed in fleur_optimize_parameter_wc.')
 

        # create link to workchain node
        for link_name, node in returndict.iteritems():
            self.out(link_name, node)   
    
    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. Can initalize the output nodes,
        or set things in the contents
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg) # because return_results still fails somewhen
        self.return_results()
        #self.abort_nowait(errormsg)
        self.abort(errormsg)