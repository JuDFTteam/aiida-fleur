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
#from aiida.orm.calculation.job.fleur_inp.fleurinputgen import FleurinputgenCalculation
#from aiida.orm.calculation.job.fleur_inp.fleur import FleurCalculation

from aiida.tools.codespecific.fleur.common_fleur_wf import is_code, get_inputs_fleur, get_inputs_inpgen

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

# difference between local and remote codes?
codename = 'fleur_iff@local_iff'
codepk = 1
codeuuid = 'ba86d8f3-fd47-4776-ac75-bad7009dfa67'
codeNode = load_node(1)
nocode = load_node(2254)
print is_code(Code)
print is_code(codeNode)
print is_code(codename)
print is_code(codepk)
print is_code(codeuuid)
print is_code(nocode)

# test get_inputs_inpgen




# test get inputs_fleur