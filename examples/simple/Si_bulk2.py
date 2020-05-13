#!/usr/bin/env python
from __future__ import absolute_import
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
#codename = 'fleur_inpgen_xml_mac_v0.27@local_mac'
#computer_name = 'local_mac'
#codename2 = 'Fleur_mac@local_mac'
codename = 'inpgen_iff@local_iff'  #'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff@local_iff'#'fleur_mac_v0_27@local_mac'
codename2 = 'fleur_iff003_v0_27@iff003'
###############################
bohr_a_0 = 0.52917721092  # A


def rel_to_abs(vector, cell):
    """
    converts interal coordinates to absolut coordinates in Angstroem.
    """
    if len(vector) == 3:
        postionR = vector
        row1 = cell[0]
        row2 = cell[1]
        row3 = cell[2]
        new_abs_pos = [
            postionR[0] * row1[0] + postionR[1] * row2[0] + postionR[2] * row3[0],
            postionR[0] * row1[1] + postionR[1] * row2[1] + postionR[2] * row3[1],
            postionR[0] * row1[2] + postionR[1] * row2[2] + postionR[2] * row3[2]
        ]
        return new_abs_pos


# first create a structure, or get it from somewhere

#s = load_node(601)
#parameters =load_node(602)

# Si_delta_inp

a = 5.167355275190 * bohr_a_0
cell = [[0.0, a, a], [a, 0.0, a], [a, a, 0.0]]
s = StructureData(cell=cell)
pos1 = rel_to_abs((1. / 8., 1. / 8., 1. / 8.), cell)
pos2 = rel_to_abs((-1. / 8., -1. / 8., -1. / 8.), cell)
s.append_atom(position=pos1, symbols='Si')
s.append_atom(position=pos2, symbols='Si')

# A structure would be enough, then the input generator will choose default values,
# if you want to set parameters you have to provide a ParameterData node with some namelists of the inpgen:
parameters = Dict(
    dict={
        'title': 'Si, alpha silicon, bulk, delta project',
        'atom': {
            'element': 'Si',
            'rmt': 2.1,
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
            'div1': 17,
            'div2': 17,
            'div3': 17,
            'tkb': 0.0005
        }
    }
)

# now run an inputgen calculation:

code = Code.get_from_string(codename)
#computer = Computer.get(computer_name)
JobCalc = FleurinputgenCalculation.process()

attrs = {
    'max_wallclock_seconds': 180,
    'resources': {
        "num_machines": 1
    },
    'withmpi': False,
    #'computer': computer
}
inp = {'structure': s, 'parameters': parameters, 'code': code}

f = run(JobCalc, _options=attrs, **inp)
fleurinp = f['fleurinpData']
fleurinpd = load_node(fleurinp.pk)

# now run a Fleur calculation ontop of an inputgen calculation
code = Code.get_from_string(codename2)
JobCalc = FleurCalculation.process()

attrs = {
    'max_wallclock_seconds': 180,
    'resources': {
        "num_machines": 1
    },
    'queue_name': 'th123_node',
    'withmpi': False
}
inp1 = {'_options': attrs, 'code': code, 'fleurinpdata': fleurinpd}  #'parent' : parent_calc,
#f1 = run(JobCalc, _options=attrs, **inp1)
f1 = run(JobCalc, **inp1)
'''
# You can also run Fleur from a Fleur calculation and apply some changes to the input file.
#parent_id = JobCalc.pk
#parentcalc = FleurCalculation.get_subclass_from_pk(parent_id)
fleurinp = f1['fleurinpData']
fleurinpd = load_node(fleurinp.pk).copy()
fleurinpd.set_changes({'dos' : T})

inp2 = {'code' : code, 'fleurinpdata' : fleurinpd}#'parent' : parent_calc,
f2 = run(JobCalc, _options=attrs, **inp2)
'''
