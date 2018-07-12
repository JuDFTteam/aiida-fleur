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
Here we run the fleur_scf_wc for Si or some other material
"""
import sys
import os
import argparse

from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode
from aiida.orm import DataFactory, load_node
from aiida.work.launch import submit, run
from aiida_fleur.workflows.eos import fleur_eos_wc
from pprint import pprint
################################################################
ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')
    
parser = argparse.ArgumentParser(description=('SCF with FLEUR. workflow to'
                 ' converge the chargedensity and optional the total energy. all arguments are pks, or uuids, codes can be names'))
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
wf_para = ParameterData(dict={'fleur_runmax' : 4, 
                              'points' : 4})

options = ParameterData(dict={'resources' : {"num_machines": 1},
                              'queue_name' : 'th1',#23_node',
                              'walltime_sec':  60*60})

# W bcc structure 
bohr_a_0= 0.52917721092 # A
a = 3.013812049196*bohr_a_0
cell = [[-a,a,a],[a,-a,a],[a,a,-a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(0.,0.,0.), symbols='W')
parameters = ParameterData(dict={
                  'atom':{
                        'element' : 'W',
                        'jri' : 833,
                        'rmt' : 2.3,
                        'dx' : 0.015,
                        'lmax' : 8,
                        'lo' : '5p',
                        'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
                        },
                  'comp': {
                        'kmax': 3.0,
                        },
                  'kpt': {
                        'nkpt': 100,
                        }})

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

#builder = fleur_scf_wc.get_builder()

print("##################### TEST fleur_eos_wc #####################")

if submit_wc:
    res = submit(fleur_eos_wc, **inputs)
    print("##################### Submited fleur_eos_wc #####################")
    print("Runtime info: {}".format(res))
    print("##################### Finished submiting fleur_eos_wc #####################")

else:
    print("##################### Running fleur_eos_wc #####################")
    res = run(fleur_eos_wc, **inputs)
    print("##################### Finished running fleur_eos_wc #####################")
