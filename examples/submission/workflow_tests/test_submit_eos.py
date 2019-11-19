# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
Here we run the FleurSSDispWorkChain
"""
from __future__ import absolute_import
from __future__ import print_function

import argparse
from pprint import pprint

from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.engine import submit, run

from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode
from aiida_fleur.workflows.eos import FleurEosWorkChain

# pylint: disable=invalid-name
Dict = DataFactory('dict')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')

parser = argparse.ArgumentParser(description=('Relax with FLEUR. workflow to optimize '
                                              'the structure. All arguments are pks, or uuids, '
                                              'codes can be names'))
parser.add_argument('--wf_para', type=int, dest='wf_parameters',
                    help='Some workflow parameters', required=False)
parser.add_argument('--structure', type=int, dest='structure',
                    help='The crystal structure node', required=False)
parser.add_argument('--calc_para', type=int, dest='calc_parameters',
                    help='Parameters for the FLEUR calculation', required=False)
parser.add_argument('--inpgen', type=int, dest='inpgen',
                    help='The inpgen code node to use', required=False)
parser.add_argument('--fleur', type=int, dest='fleur',
                    help='The FLEUR code node to use', required=True)
parser.add_argument('--submit', type=bool, dest='submit',
                    help='should the workflow be submited or run', required=False)
parser.add_argument('--options', type=int, dest='options',
                    help='options of the workflow', required=False)
args = parser.parse_args()

print(args)

### Defaults ###
wf_para = Dict(dict={'fleur_runmax': 2,
                     'density_converged': 0.02,
                     'serial': False,
                     'itmax_per_run': 60,
                     'inpxml_changes': [],
                     'points': 9,
                     'step': 0.002,
                     'guess': 1.00
                    })

# Fe fcc structure
bohr_a_0 = 0.52917721092 # A
a = 3.4100000000*2**(0.5)
cell = [[a, 0, 0],
        [0, a, 0],
        [0, 0, a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(0., 0., 0.), symbols='Fe', name='Fe1')
structure.append_atom(position=(0.5*a, 0.5*a, 0.0*a), symbols='Fe', name='Fe2')
structure.append_atom(position=(0.5*a, 0.0*a, 0.5*a), symbols='Fe', name='Fe31')
structure.append_atom(position=(0.0*a, 0.5*a, 0.5*a), symbols='Fe', name='Fe43')
parameters = Dict(dict={
    'comp': {
        'kmax': 3.4,
        },
    'atom' : {
        'element' : 'Fe',
        'bmu' : 2.5,
        'rmt' : 2.15
        },
    'kpt': {
        'div1': 4,
        'div2' : 4,
        'div3' : 4
        }})

wf_para_scf = {'fleur_runmax' : 2,
               'itmax_per_run' : 120,
               'density_converged' : 0.2,
               'serial' : False,
               'mode' : 'density'
}

wf_para_scf = Dict(dict=wf_para_scf)

options_scf = Dict(dict={'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 8},
                         'queue_name' : 'devel',
                         'custom_scheduler_commands' : '',
                         'max_wallclock_seconds':  60*60})

####


fleur_code = is_code(args.fleur)
fleur_inp = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

inpgen_code = is_code(args.inpgen)
inpgen_inp = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')

inputs = {'scf': {
                  'wf_parameters' : wf_para_scf,
                  'calc_parameters' : parameters,
                  'options' : options_scf,
                  'inpgen' : inpgen_inp,
                  'fleur' : fleur_inp
                 },
          'wf_parameters' : wf_para,
          'structure' : structure
}



submit_wc = False
if args.submit is not None:
    submit_wc = submit
pprint(inputs)

submit_wc = False
if args.submit is not None:
    submit_wc = submit
pprint(inputs)

print("##################### TEST FleurEosWorkChain #####################")

if submit_wc:
    res = submit(FleurEosWorkChain, **inputs)
    print("##################### Submited FleurEosWorkChain #####################")
    print(("Runtime info: {}".format(res)))
    print((res.pk))
    print("##################### Finished submiting FleurEosWorkChain #####################")

else:
    print("##################### Running FleurEosWorkChain #####################")
    res = run(FleurEosWorkChain, **inputs)
    print("##################### Finished running FleurEosWorkChain #####################")
