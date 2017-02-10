#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In here we put all things (methods) that are common to workflows 
"""
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import Code, DataFactory
from aiida.tools.codespecific.fleur.queue_defaults import queue_defaults
from aiida.work.workchain import WorkChain
from aiida.work.workchain import while_, if_
from aiida.work.run import submit
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


def is_code(code):
    """
    Test if the given input is a Code node, by object, id, uuid, or pk
    if yes returns a Code node in all cases
    if no returns None
    """
    StructureData = DataFactory('structure')

    #Test if StructureData
    if isinstance(structure, StructureData):
        return structure
    #Test if pk, if yes, is the corresponding node StructureData
    pk = None
    try:
        pk=int(structure)
    except:
        pass
    if pk:
        structure = load_node(pk)
        if isinstance(structure, StructureData):
            return structure
        else:
            return None
    #Test if uuid, if yes, is the corresponding node StructureData
    # TODO: test for uuids not for string (guess is ok for now)
    uuid = None
    try:
        uuid = str(structure)
    except:
        pass
    if uuid:
        structure = load_node(uuid)
        if isinstance(structure, StructureData):
            return structure
        else:
            return None
    #Else throw error? or rather return None

    return None

def get_inputs_fleur():
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
    
    if self.ctx.queue:
        inputs._options.queue_name = self.ctx.queue
        print self.ctx.queue
    # if code local use
    #if self.inputs.fleur.is_local():
    #    inputs._options.computer = computer
    #    #else use computer from code.
    #else:
    #    inputs._options.queue_name = 'th1'
    
    if self.ctx.serial:
        inputs._options.withmpi = False # for now
        inputs._options.resources = {"num_machines": 1}
    
    return inputs


def get_inputs_inpgen(structure, params=None, inpgencode, options):
    """
    get the input for a inpgen calc
    """
    inputs = FleurinpProcess.get_inputs_template()
    inputs.structure = structure
    inputs.code = inpgen
    if params:
        inputs.parameters = self.inputs.calc_parameters
    inputs._options.resources = {"num_machines": 1}
    inputs._options.max_wallclock_seconds = 360
    inputs._options.withmpi = False
    if self.ctx.queue:
        inputs._options.queue_name = self.ctx.queue
        print self.ctx.queue
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