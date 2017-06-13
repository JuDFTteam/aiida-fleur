#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In here we put all things (methods) that are common to workflows 
"""
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import Code, DataFactory, load_node
#from aiida.tools.codespecific.fleur.queue_defaults import queue_defaults
#from aiida.work.workchain import WorkChain
#from aiida.work.workchain import while_, if_
#from aiida.work.run import submit
#from aiida.work.workchain import ToContext
#from aiida.work.process_registry import ProcessRegistry
#from aiida.tools.codespecific.fleur.decide_ncore import decide_ncore
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


RemoteData = DataFactory('remote')
ParameterData = DataFactory('parameter')
#FleurInpData = DataFactory('fleurinp.fleurinp')
FleurInpData = DataFactory('fleur.fleurinp')
FleurProcess = FleurCalculation.process()
FleurinpProcess = FleurinputgenCalculation.process()


def is_code(code):
    """
    Test if the given input is a Code node, by object, id, uuid, or pk
    if yes returns a Code node in all cases
    if no returns None
    """
    
    #Test if Code
    if isinstance(code, Code):
        return code
    #Test if pk, if yes, is the corresponding node Code
    pk = None
    try:
        pk=int(code)
    except:
        pass
    if pk:
        code = load_node(pk)
        if isinstance(code, Code):
            return code
        else:
            return None
    #given as string
    codestring = None
    try:
        codestring = str(code)
    except:
        pass
    if codestring:
        code = Code.get_from_string(codestring)
        return code      
    #Test if uuid, if yes, is the corresponding node Code
    # TODO: test for uuids not for string (guess is ok for now)
    '''
    uuid = None
    try:
        uuid = str(code)
    except:
        pass
    if uuid:
        code = load_node(uuid)
        if isinstance(code, Code):
            return code
        else:
            return None
    '''
    return None

def get_inputs_fleur(code, remote, fleurinp, options, settings=None, serial=False):
    '''
    get the input for a FLEUR calc
    '''
    inputs = FleurProcess.get_inputs_template()
    if remote:
        inputs.parent_folder = remote
    if code:
        inputs.code = code
    if fleurinp:
        inputs.fleurinpdata = fleurinp
    
    for key, val in options.iteritems():
        if val==None:
            continue
        else:
            inputs._options[key] = val
    
    #TODO check  if code is parallel version?
    if serial:
        inputs._options.withmpi = False # for now
        inputs._options.resources = {"num_machines": 1}
    
    if settings:
        inputs.settings = settings
        
    return inputs


def get_inputs_inpgen(structure, inpgencode, options, params=None):
    """
    get the input for a inpgen calc
    """
    inputs = FleurinpProcess.get_inputs_template()
    if structure:
        inputs.structure = structure
    if inpgencode:
        inputs.code = inpgencode
    if params:
        inputs.parameters = params
    for key, val in options.iteritems():
        if val==None:
            #leave them out, otherwise the dict schema won't validate
            continue
        else:
            inputs._options[key] = val
    
    
    #inpgen run always serial
    inputs._options.withmpi = False # for now
    inputs._options.resources = {"num_machines": 1}
                    
    return inputs
