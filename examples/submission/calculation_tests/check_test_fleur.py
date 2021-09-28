# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
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
    raise ValueError('Pass a valid PK of a completed calculation')

calc = load_node(pk)
if calc.get_state() == calc_states.SUBMISSIONFAILED:
    raise ValueError('The calculation could not be submitted (failed)')
elif calc.get_state() == calc_states.FAILED:
    raise ValueError('The calculation did fail')
elif calc.get_state() != calc_states.FINISHED:
    raise ValueError('The calculation did not complete')
res = calc.res
print(f'Test: {calc.label}')
print(f'Description: {calc.description}')
print(f'Code name in db: {calc.get_code()}')
#print "Input structure (chemical formula): {}".format(calc.inp.structure.get_formula())
print(f'Code name/version: {res.creator_name}')
print(f'The following files were retrieved: {calc.out.retrieved.get_folder_list()}')

#print "Wall time: {} s".format(calc.res.wall_time_seconds)
#print "Input wavefunction cutoff: {} Ry".format(calc.inp.parameters.dict.SYSTEM['ecutwfc'])
print(f'The total energy of the system is {res.energy} eV')
print(f'The fermi energy of the system is {res.fermi_energy} htr')

if res.number_of_spin_components == 1:
    print('Non magnetic calculation, 1 spin component')
    print(f'Charge distance of the system is: {res.charge_density} me/bohr^3')
else:
    print('Magnetic calculation, 2 spin components')
    print(f'Charge distance spin 1 of the system is: {res.charge_density1} me/bohr^3')
    print(f'Charge distance spin 2 of the system is: {res.charge_density2} me/bohr^3')
    print(f'Spin density distance of the system is: {res.spin_density} me/bohr^3')

#if calc.res.warnings:
#    print "List of warnings:"
#    for warning in calc.res.warnings:
#        print "- {}".format(warning)
#if 'res
print(f'Log messages: {get_log_messages(calc)}')
