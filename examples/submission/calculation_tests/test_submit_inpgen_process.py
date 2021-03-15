# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from aiida import load_profile
load_profile()

import sys
import os

from aiida.orm import load_node, Code
from aiida.plugins import DataFactory, CalculationFactory
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation  # as calc
from aiida.engine import submit, run
from aiida.common.exceptions import NotExistent

################################################################

Dict = DataFactory('dict')
StructureData = DataFactory('structure')
try:
    dontsend = sys.argv[1]
    if dontsend == '--dont-send':
        submit_test = True
    elif dontsend == '--send':
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print(('The first parameter can only be either ' '--send or --dont-send'), file=sys.stderr)
    sys.exit(1)

try:
    codename = sys.argv[2]
except IndexError:
    codename = None

queue = None
# queue = "th1_small"
settings = None
#####

expected_code_type = 'fleur.inpgen'

try:
    if codename is None:
        raise ValueError(message='codename is None')
    code = Code.get_from_string(codename)
    if code.get_input_plugin_name() != expected_code_type:
        raise ValueError
except (NotExistent, ValueError):
    print('codename {} does not exist or is not of the expected type : {}'.format(codename, expected_code_type))

# W bcc structure
bohr_a_0 = 0.52917721092  # A
a = 3.013812049196 * bohr_a_0
cell = [[-a, a, a], [a, -a, a], [a, a, -a]]
s = StructureData(cell=cell)
s.append_atom(position=(0., 0., 0.), symbols='W')
parameters = Dict(
    dict={
        'atom': {
            'element': 'W',
            'jri': 833,
            'rmt': 2.3,
            'dx': 0.015,
            'lmax': 8,
            'lo': '5p',
            'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
        },
        'comp': {
            'kmax': 3.5,
            'gmax': 2.9,
        },
        'kpt': {
            'nkpt': 200,
        }
    })
JobCalc = FleurinputgenCalculation
label = 'Test inpgen run'
description = 'Test inpgen run on W'
label = 'fleur_scf_wc inpgen on W'
description = '|fleur_scf_wc| inpgen on W, pbc(True, True, True)'

attrs = {'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 1}, 'withmpi': False}  # ,

inp = {
    'structure': s,
    'parameters': parameters,
    'code': code,
    'metadata': {
        'options': {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            },
            'withmpi': False
        }
    }
}

inputs = {
    'structure': s,
    'parameters': parameters,
    'metadata': {
        'options': {
            'withmpi': False,
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            }
        }
    }
}
# 'label': label, 'description': description}}

if submit_test:
    # subfolder, script_filename = calc.submit_test()
    # print "Test_submit for calculation (uuid='{}')".format(
    #    calc.uuid)
    # print "Submit file in {}".format(os.path.join(
    #    os.path.relpath(subfolder.abspath),
    #    script_filename
    # ))
    #JobCalc.
    pass
else:
    # future = submit(JobCalc, _options=attrs, _label=label, _description=description, **inp)
    future = submit(JobCalc, code=code, **inputs)
    # calc.store_all()
    print('submited')
    print(future)
