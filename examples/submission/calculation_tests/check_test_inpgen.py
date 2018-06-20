from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

import sys

from aiida.orm import load_node
from aiida.common.datastructures import calc_states
from aiida.backends.utils import get_log_messages
from pprint import pprint
try:
    pk = int(sys.argv[1])
except (KeyError, IndexError):
    raise ValueError("Pass a valid PK of a completed calculation")

calc = load_node(pk)
if calc.get_state() == calc_states.SUBMISSIONFAILED:
    raise ValueError("The calculation could not be submitted (failed)") 
elif calc.get_state() == calc_states.FAILED:
    raise ValueError("The calculation did fail")
elif calc.get_state() != calc_states.FINISHED:
    raise ValueError("The calculation did not complete")   

print "Test: {}".format(calc.label)
print "Description: {}".format(calc.description)
print "Code name in db: {}".format(calc.get_code())
print "Input structure (chemical formula): {}".format(calc.inp.structure.get_formula())
inp = calc.get_inputs_dict()
if 'parameters' in inp:
    print "Input parameter dictionary:"
    pprint(calc.inp.parameters.get_dict())
else:
    print "no parameters were specified for inpgen input"
print "The following files were retrieved: {}".format(calc.out.retrieved.get_folder_list())
print "Output nodes produced: {}".format(calc.get_outputs())
#print "Wall time: {} s".format(calc.res.wall_time_seconds)

#if calc.res.warnings:
#    print "List of warnings:"
#    for warning in calc.res.warnings:
#        print "- {}".format(warning)
#if 'res
print "Log messages: {}".format(get_log_messages(calc))        
  



