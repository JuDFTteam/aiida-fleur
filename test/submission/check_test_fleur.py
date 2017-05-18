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
if calc.get_state() == calc_states.SUBMISSIONFAILED:
    raise ValueError("The calculation could not be submitted (failed)") 
elif calc.get_state() == calc_states.FAILED:
    raise ValueError("The calculation did fail")
elif calc.get_state() != calc_states.FINISHED:
    raise ValueError("The calculation did not complete")   
res = calc.res
print "Test: {}".format(calc.label)
print "Description: {}".format(calc.description)
print "Code name in db: {}".format(calc.get_code())
#print "Input structure (chemical formula): {}".format(calc.inp.structure.get_formula())
print "Code name/version: {}".format(res.creator_name)
print "The following files were retrieved: {}".format(calc.out.retrieved.get_folder_list())   

#print "Wall time: {} s".format(calc.res.wall_time_seconds)
#print "Input wavefunction cutoff: {} Ry".format(calc.inp.parameters.dict.SYSTEM['ecutwfc'])
print "The total energy of the system is {} eV".format(res.energy)
print "The fermi energy of the system is {} htr".format(res.fermi_energy)

if res.number_of_spin_components == 1:
    print "Non magnetic calculation, 1 spin component"
    print "Charge distance of the system is: {} me/bohr^3".format(res.charge_density)
else:
    print "Magnetic calculation, 2 spin components"
    print "Charge distance spin 1 of the system is: {} me/bohr^3".format(res.charge_density1)
    print "Charge distance spin 2 of the system is: {} me/bohr^3".format(res.charge_density2)
    print "Spin density distance of the system is: {} me/bohr^3".format(res.spin_density)
    
#if calc.res.warnings:
#    print "List of warnings:"
#    for warning in calc.res.warnings:
#        print "- {}".format(warning)
#if 'res
print "Log messages: {}".format(get_log_messages(calc))        
  



