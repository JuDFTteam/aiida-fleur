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
Here we run the FleurBandWorkChain for W or some other material
"""
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import argparse

from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode
from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.engine import submit, run
from aiida_fleur.workflows.band import FleurBandWorkChain
from pprint import pprint
################################################################
ParameterData = DataFactory('dict')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')

parser = argparse.ArgumentParser(
    description=(
        'Bandstructure with FLEUR. workflow to'
        ' calculate a band structure. all arguments are pks, or uuids, codes can be names'
    )
)
parser.add_argument(
    '--wf_para', type=int, dest='wf_parameters', help='Some workflow parameters', required=False
)

parser.add_argument(
    '--calc_para',
    type=int,
    dest='calc_parameters',
    help='Parameters for the FLEUR calculation',
    required=False
)
parser.add_argument(
    '--fleurinp',
    type=int,
    dest='fleurinp',
    help='FleurinpData from which to run the FLEUR calculation',
    required=False
)
parser.add_argument(
    '--remote',
    type=int,
    dest='remote_data',
    help=(
        'Remote Data of older FLEUR calculation, '
        'from which files will be copied (mixing_history ...)'
    ),
    required=False
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
args = parser.parse_args()

print(args)

# load_the nodes if arguments are there, or use default.
#nodes_dict = {}
#for key, val in vars(args).iteritems():
#    print(key, val)
#    if val is not None:
#        val_new = load_node(val)
#    else:
#        val_new = val# default[key]
#    nodes_dict[key] = val_new

### Defaults ###
wf_para = Dict(
    dict={
        'fleur_runmax': 4,
        'kpath': 'auto',
        'nkpts': 800,
        'sigma': 0.005,
        'emin': -0.30,
        'emax': 0.80
    }
)

options = Dict(
    dict={
        'resources': {
            'num_machines': 1
        },
        'queue_name': 'th1',  #23_node',
        'max_wallclock_seconds': 60 * 60
    }
)

# W bcc structure
file_path = '../../inp_xml_files/W/inp.xml'

filefolder = os.path.dirname(os.path.abspath(__file__))
inputfile = os.path.abspath(os.path.join(filefolder, file_path))

fleurinp = FleurinpData(files=[inputfile])

default = {
    'fleurinp': fleurinp,
    'wf_parameters': wf_para,
    'options': options,
}

####

inputs = {}

if args.wf_parameters is not None:
    inputs['wf_parameters'] = load_node(args.wf_parameters)
else:
    inputs['wf_parameters'] = default['wf_parameters']

if args.fleurinp is not None:
    inputs['fleurinp'] = load_node(args.fleurinp)
else:
    inputs['fleurinp'] = default['fleurinp']

if args.remote_data is not None:
    inputs['remote_data'] = load_node(args.remote_data)

if args.options is not None:
    inputs['options'] = load_node(args.options)
else:
    inputs['options'] = default['options']

fleur_code = is_code(args.fleur)
inputs['fleur'] = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

submit_wc = False
if args.submit is not None:
    submit_wc = submit
pprint(inputs)

print('##################### TEST FleurBandWorkChain #####################')

if submit_wc:
    res = submit(FleurBandWorkChain, **inputs)
    print('##################### Submited FleurBandWorkChain #####################')
    print(('Runtime info: {}'.format(res)))
    print('##################### Finished submiting FleurBandWorkChain #####################')
else:
    print('##################### Running fleur_dos_wc #####################')
    res = run(FleurBandWorkChain, **inputs)
    print('##################### Finished running FleurBandWorkChain #####################')
