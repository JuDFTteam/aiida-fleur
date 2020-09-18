#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In here we put all things (methods) that are common to workflows
"""
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
#from aiida.tools.codespecific.fleur.queue_defaults import queue_defaults
#from aiida.work.workchain import WorkChain
#from aiida.work.workchain import while_, if_
from aiida.engine.run import submit
#from aiida.work.workchain import ToContext
#from aiida.work.process_registry import ProcessRegistry
#from aiida.tools.codespecific.fleur.decide_ncore import decide_ncore
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation

from aiida_fleur.tools.common_fleur_wf import is_code, get_inputs_fleur, get_inputs_inpgen

__copyright__ = (u'Copyright (c), 2016, Forschungszentrum Jülich GmbH, ' 'IAS-1/PGI-1, Germany. All rights reserved.')
__license__ = 'MIT license, see LICENSE.txt file'
__version__ = '0.27'
__contributors__ = 'Jens Broeder'

FleurProcess = FleurCalculation.process()
InpgenProcess = FleurinputgenCalculation.process()
# difference between local and remote codes?
codename = 'fleur_iff@local_iff'
codepk = 1
codeuuid = 'ba86d8f3-fd47-4776-ac75-bad7009dfa67'
codeNode = load_node(1)
nocode = load_node(2254)

print(is_code(codeNode))
print(is_code(codename))
print(is_code(codepk))
#print is_code(codeuuid)
print(is_code(nocode))
#print is_code(Code)

# test get_inputs_inpgen

remote = load_node(2357)
fleurinp = load_node(2351)
options = {
    'max_wallclock_seconds': 360,
    'resources': {
        'num_machines': 1
    },
    'custom_scheduler_commands': 'bla',
    'queue_name': 'th1',
    #"computer": Computer,
    'withmpi': True,
    #"mpirun_extra_params": Any(list, tuple),
    'import_sys_environment': False,
    'environment_variables': {},
    'priority': 'High',
    'max_memory_kb': 62,
    'prepend_text': 'this is a test',
    'append_text': 'this was a test'
}
inp = get_inputs_fleur(codeNode, remote, fleurinp, options, serial=False)
print(inp)

inputs = {}
options2 = {'max_wallclock_seconds': 360, 'resources': {'num_machines': 1}}
inputs = get_inputs_fleur(codeNode, remote, fleurinp, options2, serial=True)
#print inputs
#future = submit(FleurProcess, **inputs)
print('run Fleur')

# test get inputs_fleur
inputs = {}
structure = load_node(2469)
inpgencode = is_code(2)
options2 = {'max_wallclock_seconds': 360, 'resources': {'num_machines': 1}}
inputs = get_inputs_inpgen(structure, inpgencode, options2, params=None)
future = submit(InpgenProcess, **inputs)
print('run inpgen')
