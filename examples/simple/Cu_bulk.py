#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys, os
from aiida.plugins import Code, DataFactory, Computer, load_node
from aiida.engine.run import async, run
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
codename = 'inpgen_iff@local_iff'
#computer_name = 'local_mac'
codename2 = 'fleur_iff@local_iff'
###############################
bohr_a_0 = 0.52917721092  # A

# first create a structure, or get it from somewhere
#s = load_node(601)
#parameters =load_node(602)

# Cu_delta_inp
a = 3.436364432671 * bohr_a_0
cell = [[0.0, a, a], [a, 0., a], [a, a, 0.]]
s = StructureData(cell=cell)
s.append_atom(position=(0., 0., 0.), symbols='Cu')

# A structure would be enough, then the input generator will choose default values,
# if you want to set parameters you have to provide a ParameterData node with some namelists of the inpgen:
parameters = Dict(
    dict={
        'title': 'Cu, fcc copper, bulk, delta project',
        'atom': {
            'element': 'Cu',
            'rmt': 2.28,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
            'gmaxxc': 12.5,
            'gmax': 15.0
        },
        'kpt': {
            'div1': 25,
            'div2': 25,
            'div3': 25,
            'tkb': 0.0005
        }
    })

# now run the inputgenerator:
code = Code.get_from_string(codename)
#computer = Computer.get(computer_name)
JobCalc = FleurinputgenCalculation.process()

attrs = {
    'max_wallclock_seconds': 180,
    'resources': {
        'num_machines': 1
    },
    'withmpi': False,
    #'computer': computer
}
inp = {'structure': s, 'parameters': parameters, 'code': code}

print('running inpgen')
f = run(JobCalc, _options=attrs, **inp)
fleurinp = f['fleurinpData']
fleurinpd = load_node(fleurinp.pk)

# now run a Fleur calculation ontop of an inputgen calculation
code = Code.get_from_string(codename2)
JobCalc = FleurCalculation.process()

attrs = {'max_wallclock_seconds': 180, 'resources': {'num_machines': 1}}
inp1 = {'code': code, 'fleurinpdata': fleurinpd}  #'parent' : parent_calc,
print('running Fleur')
f1 = run(JobCalc, _options=attrs, **inp1)

print('copper example run was succcesful, check the results in your DB')
print('Hint: Fleur did run for just 9 iterations, check if convergence already reached (No)')
'''
# You can also run Fleur from a Fleur calculation and apply some changes to the input file.
# you should also specify the remote parent folder
#parentcalc = FleurCalculation.get_subclass_from_pk(parent_id)
fleurinp = f1['fleurinpData']
fleurinpd = load_node(fleurinp.pk).copy()
fleurinpd.set_changes({'dos' : T})

inp2 = {'code' : code, 'fleurinpdata' : fleurinpd}#'parent' : parent_calc,
f2 = run(JobCalc, _options=attrs, **inp2)
'''
