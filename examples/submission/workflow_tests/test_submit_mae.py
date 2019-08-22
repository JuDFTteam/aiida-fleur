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
# pylint: disable=invalid-name
from __future__ import absolute_import
from __future__ import print_function

import argparse
from pprint import pprint

from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.engine import submit, run

from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode
from aiida_fleur.workflows.mae import FleurMaeWorkChain

################################################################
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
parser.add_argument('--remote', type=int, dest='remote',
                    help='remote', required=False)
parser.add_argument('--fleurinp', type=int, dest='fleurinp',
                    help='fleurinp', required=False)
args = parser.parse_args()

print(args)

### Defaults ###
wf_para = Dict(dict={'sqa_ref': [0.7, 0.7],
                     'use_soc_ref': False,
                     'input_converged' : False,
                     'fleur_runmax': 10,
                     'sqas_theta': [0.0, 1.57079, 1.57079],
                     'sqas_phi': [0.0, 0.0, 1.57079],
                     'alpha_mix': 0.05,
                     'density_converged': 0.02,
                     'serial': False,
                     'itmax_per_run': 30,
                     'soc_off': [],
                     'inpxml_changes': [],
                    })

options = Dict(dict={'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 24},
                     'queue_name' : 'devel',
		             'custom_scheduler_commands' : '',
                     'max_wallclock_seconds':  60*60})

bohr_a_0 = 0.52917721092 # A
a = 7.497*bohr_a_0
cell = [[0.7071068*a, 0.0, 0.0],
        [0.0, 1.0*a, 0.0],
        [0.0, 0.0, 0.7071068*a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(0.0, 0.0, -1.99285*bohr_a_0), symbols='Fe')
structure.append_atom(position=(0.5*0.7071068*a, 0.5*a, 0.0), symbols='Pt')
structure.append_atom(position=(0., 0., 2.65059*bohr_a_0), symbols='Pt')
structure.pbc = (True, True, False)

parameters = Dict(dict={
    'atom':{
        'element' : 'Pt',
        #'jri' : 833,
        #'rmt' : 2.3,
        #'dx' : 0.015,
        'lmax' : 8,
        #'lo' : '5p',
        #'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
        },
    'atom2':{
        'element' : 'Fe',
        #'jri' : 833,
        #'rmt' : 2.3,
        #'dx' : 0.015,
        'lmax' : 8,
        #'lo' : '5p',
        #'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
        },
    'comp': {
        'kmax': 3.8,
        },
    'kpt': {
        'div1': 20,
        'div2' : 24,
        'div3' : 1
        }})

'''
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
'''
default = {'structure' : structure,
           'wf_parameters': wf_para,
           'options' : options,
           'calc_parameters' : parameters
          }

####

inputs = {}

if args.wf_parameters is not None:
    inputs['wf_parameters'] = load_node(args.wf_parameters)
else:
    inputs['wf_parameters'] = default['wf_parameters']

if args.structure is not None:
    inputs['structure'] = load_node(args.structure)
else:
    # use default W
    inputs['structure'] = default['structure']

if args.calc_parameters is not None:
    inputs['calc_parameters'] = load_node(args.calc_parameters)
else:
    inputs['calc_parameters'] = default['calc_parameters'] # bad if using other structures...

if args.remote is not None:
    inputs['remote'] = load_node(args.remote)

if args.fleurinp is not None:
    inputs['fleurinp'] = load_node(args.fleurinp)

if args.options is not None:
    inputs['options'] = load_node(args.options)
else:
    inputs['options'] = default['options']

fleur_code = is_code(args.fleur)
inputs['fleur'] = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

if args.inpgen is not None:
    inpgen_code = is_code(args.inpgen)
    inputs['inpgen'] = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')

submit_wc = False
if args.submit is not None:
    submit_wc = submit
pprint(inputs)

print("##################### TEST FleurMaeWorkChain #####################")

if submit_wc:
    res = submit(FleurMaeWorkChain, **inputs)
    print("##################### Submited FleurMaeWorkChain #####################")
    print(("Runtime info: {}".format(res)))
    print((res.pk))
    print("##################### Finished submiting FleurMaeWorkChain #####################")

else:
    print("##################### Running FleurMaeWorkChain #####################")
    res = run(FleurMaeWorkChain, **inputs)
    print("##################### Finished running FleurMaeWorkChain #####################")
