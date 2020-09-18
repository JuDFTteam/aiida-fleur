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
from aiida_fleur.workflows.mae_conv import FleurMaeConvWorkChain

################################################################
Dict = DataFactory('dict')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')

parser = argparse.ArgumentParser(
    description=(
        'Relax with FLEUR. workflow to optimize '
        'the structure. All arguments are pks, or uuids, '
        'codes can be names'
    )
)
parser.add_argument(
    '--wf_para', type=int, dest='wf_parameters', help='Some workflow parameters', required=False
)
parser.add_argument(
    '--structure', type=int, dest='structure', help='The crystal structure node', required=False
)
parser.add_argument(
    '--calc_para',
    type=int,
    dest='calc_parameters',
    help='Parameters for the FLEUR calculation',
    required=False
)
parser.add_argument(
    '--inpgen', type=int, dest='inpgen', help='The inpgen code node to use', required=False
)
parser.add_argument(
    '--fleur', type=int, dest='fleur', help='The FLEUR code node to use', required=True
)
parser.add_argument(
    '--submit',
    type=bool,
    dest='submit',
    help='should the workflow be submited or run',
    required=False
)
parser.add_argument(
    '--options', type=int, dest='options', help='options of the workflow', required=False
)
parser.add_argument('--remote', type=int, dest='remote', help='remote', required=False)
parser.add_argument('--fleurinp', type=int, dest='fleurinp', help='fleurinp', required=False)
args = parser.parse_args()

print(args)

### Defaults ###
wf_para = Dict(
    dict={
        'sqas': {
            'label': [0.0, 0.0],
            'label2': [1.57079, 1.57079]
        },
        'soc_off': ['124']
    }
)

bohr_a_0 = 0.52917721092  # A
a = 7.497 * bohr_a_0
cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(0.0, 0.0, -1.99285 * bohr_a_0), symbols='Fe', name='Fe123')
structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
structure.append_atom(position=(0., 0., 2.65059 * bohr_a_0), symbols='Pt', name='Fe124')
structure.pbc = (True, True, False)

parameters = Dict(
    dict={
        'atom': {
            'element': 'Pt',
            'lmax': 8
        },
        'atom2': {
            'element': 'Fe',
            'lmax': 8,
        },
        'comp': {
            'kmax': 3.8,
        },
        'kpt': {
            'div1': 20,
            'div2': 24,
            'div3': 1
        }
    }
)

wf_para_scf = {
    'fleur_runmax': 2,
    'itmax_per_run': 120,
    'density_converged': 0.2,
    'serial': False,
    'mode': 'density'
}

wf_para_scf = Dict(dict=wf_para_scf)

options_scf = Dict(
    dict={
        'resources': {
            'num_machines': 2,
            'num_mpiprocs_per_machine': 24
        },
        'queue_name': 'devel',
        'custom_scheduler_commands': '',
        'max_wallclock_seconds': 60 * 60
    }
)

####

fleur_code = is_code(args.fleur)
fleur_inp = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

inpgen_code = is_code(args.inpgen)
inpgen_inp = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')

inputs = {
    'scf': {
        'wf_parameters': wf_para_scf,
        'structure': structure,
        'calc_parameters': parameters,
        'options': options_scf,
        'inpgen': inpgen_inp,
        'fleur': fleur_inp
    },
    'wf_parameters': wf_para
}

submit_wc = False
if args.submit is not None:
    submit_wc = submit
pprint(inputs)

print('##################### TEST FleurMaeConvWorkChain #####################')

if submit_wc:
    res = submit(FleurMaeConvWorkChain, **inputs)
    print('##################### Submited FleurMaeConvWorkChain #####################')
    print(('Runtime info: {}'.format(res)))
    print((res.pk))
    print('##################### Finished submiting FleurMaeConvWorkChain #####################')

else:
    print('##################### Running FleurMaeConvWorkChain #####################')
    res = run(FleurMaeConvWorkChain, **inputs)
    print('##################### Finished running FleurMaeConvWorkChain #####################')
