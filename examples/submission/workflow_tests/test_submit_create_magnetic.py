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
# pylint: disable=invalid-name
from __future__ import absolute_import
from __future__ import print_function

import argparse

from aiida.plugins import DataFactory
from aiida.orm import load_node, Int
from aiida.engine import submit, run

from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode
from aiida_fleur.workflows.create_magnetic_film import FleurCreateMagneticWorkChain

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
                    help='should the workflow be submitted or run', required=False)
parser.add_argument('--options', type=int, dest='options',
                    help='options of the workflow', required=False)
args = parser.parse_args()

print(args)



fleur_code = is_code(args.fleur)
fleur_code = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

if args.inpgen is not None:
    inpgen_code = is_code(args.inpgen)
    inpgen_code = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')

####
wf_para = {
        'lattice': 'fcc',
        'miller': [[-1, 1, 0],
                   [0, 0, 1],
                   [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,
        'size': (1, 1, 5),
        'replacements': {0: 'Fe', -1: 'Fe'},
        'decimals': 10,
        'pop_last_layers': 1,

        'total_number_layers': 8,
        'num_relaxed_layers': 3,

        'eos_needed': True,
        'relax_needed': True
    }

wf_para = Dict(dict=wf_para)

wf_eos = {
        'points': 15,
        'step': 0.015,
        'guess': 1.00
        }

wf_eos_scf = {
        'fleur_runmax': 4,
        'density_converged': 0.0002,
        'serial': False,
        'itmax_per_run': 50,
        'inpxml_changes': []
        }

wf_eos_scf = Dict(dict=wf_eos_scf)

wf_eos = Dict(dict=wf_eos)

calc_eos = {
    'comp': {
        'kmax': 3.8,
        },
    'kpt': {
        'div1': 4,
        'div2' : 4,
        'div3' : 4
        }
}

calc_eos = Dict(dict=calc_eos)

options_eos = {'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 4, "num_cores_per_mpiproc" : 6},
               'queue_name' : 'devel',
               'environment_variables' : {'OMP_NUM_THREADS' : '6'},
               'custom_scheduler_commands' : '',
               'max_wallclock_seconds':  1*60*60}

options_eos = Dict(dict=options_eos)

wf_relax = {
        'film_distance_relaxation' : False,
        'force_criterion': 0.049,
        'use_relax_xml': True
    }

wf_relax_scf = {
        'fleur_runmax': 5,
        'serial': False,
        'itmax_per_run': 50,
        'alpha_mix': 0.015,
        'relax_iter': 25,
        'force_converged': 0.001,
        'force_dict': {'qfix': 2,
                       'forcealpha': 0.75,
                       'forcemix': 'straight'},
        'inpxml_changes': []
        }

wf_relax = Dict(dict=wf_relax)
wf_relax_scf = Dict(dict=wf_relax_scf)

calc_relax = {
    'comp': {
        'kmax': 4.0,
        },
    'kpt': {
        'div1': 24,
        'div2' : 20,
        'div3' : 1
        },
    'atom':{
        'element' : 'Pt',
        'rmt' : 2.2,
        'lmax' : 10,
        'lnonsph' : 6,
        'econfig': '[Kr] 5s2 4d10 4f14 5p6| 5d9 6s1',
        },
    'atom2':{
        'element' : 'Fe',
        'rmt' : 2.1,
        'lmax' : 10,
        'lnonsph' : 6,
        'econfig': '[Ne] 3s2 3p6| 3d6 4s2',
        },
}

calc_relax = Dict(dict=calc_relax)

options_relax = {'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 4, "num_cores_per_mpiproc" : 6},
                     'queue_name' : 'devel',
                     'environment_variables' : {'OMP_NUM_THREADS' : '6'},
                     'custom_scheduler_commands' : '',
                     'max_wallclock_seconds':  1*60*60}

options_relax = Dict(dict=options_relax)

settings = Dict(dict={})

fleur_code = is_code(args.fleur)
fleur_inp = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

inpgen_code = is_code(args.inpgen)
inpgen_inp = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')

inputs = {
    'eos': {
        'scf': {
                  'wf_parameters' : wf_eos_scf,
                  'calc_parameters' : calc_eos,
                  'options' : options_eos,
                  'inpgen' : inpgen_inp,
                  'fleur' : fleur_inp
        },
        'wf_parameters' : wf_eos
    },
    'relax': {
        'scf' : {
                  'wf_parameters' : wf_relax_scf,
                  'calc_parameters' : calc_relax,
                  'options' : options_relax,
                  'inpgen' : inpgen_inp,
                  'fleur' : fleur_inp
        },
        'wf_parameters' : wf_relax,
        'label': 'relaxation',
        'description' : 'describtion',
        'max_iterations' : Int(5)
    },
    'wf_parameters': wf_para
    #'eos_output': load_node(14405)
}


submit_wc = False
if args.submit is not None:
    submit_wc = submit

print("##################### TEST fleur_relax_wc #####################")

if submit_wc:
    res = submit(FleurCreateMagneticWorkChain, **inputs)
    print("##################### Submitted fleur_relax_wc #####################")
    print(("Runtime info: {}".format(res)))
    print((res.pk))
    print("##################### Finished submiting fleur_relax_wc #####################")

else:
    print("##################### Running fleur_relax_wc #####################")
    res = run(FleurCreateMagneticWorkChain, **inputs)
    print("##################### Finished running fleur_relax_wc #####################")
