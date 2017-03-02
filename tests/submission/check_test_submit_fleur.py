from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

import sys

from aiida.orm import load_node
from aiida.common.datastructures import calc_states
from aiida.backends.utils import get_log_messages

try:
    pk = int(sys.argv[1])
except (KeyError, IndexError):
    raise ValueError("Pass a valid PK of a completed calculation")

calc = load_node(pk)
if calc.get_state() != calc_states.FINISHED:
    raise ValueError("The calculation did not complete")

print "Test: {}".format(calc.label)
print "Description: {}".format(calc.description)
print "Code name in db: {}".format(calc.get_code())
#print "Input structure (chemical formula): {}".format(calc.inp.structure.get_formula())
print "Code name/version: {}".format(calc.res.creator_name)

#print "Wall time: {} s".format(calc.res.wall_time_seconds)
#print "Input wavefunction cutoff: {} Ry".format(calc.inp.parameters.dict.SYSTEM['ecutwfc'])
print "The total energy of the system is {} eV".format(calc.res.energy)
print "Charge distance of the system is: {} me/bohr^3".format(calc.res.charge_density)
print "The following files were retrieved: {}".format(calc.out.retrieved.get_folder_list())   
#if calc.res.warnings:
#    print "List of warnings:"
#    for warning in calc.res.warnings:
#        print "- {}".format(warning)
        
print "Log messages: {}".format(get_log_messages(calc))        
  



