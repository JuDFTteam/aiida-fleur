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
from aiida.work.launch import submit
from aiida_fleur.workflows.scf import fleur_scf_wc

# If set to True, will ask AiiDA to run in serial mode (i.e., AiiDA will not
# invoke the mpirun command in the submission script)
run_in_serial_mode = True#False
queue = None
queue = 'th123_node'
################################################################
ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')

    
parser = argparse.ArgumentParser(description=('SCF with FLEUR. workflow to'
                 ' converge the chargedensity and optional the total energy. all arguments are pks, or uuids, codes can be names'))
parser.add_argument('--wf_para', type=int, dest='wf_parameters',
                        help='Some workflow parameters', required=False)
parser.add_argument('--structure', type=int, dest='structure',
                        help='The crystal structure node', required=False)
parser.add_argument('--calc_para', type=int, dest='calc_parameters',
                        help='Parameters for the FLEUR calculation', required=False)
parser.add_argument('--fleurinp', type=int, dest='fleurinp',
                        help='FleurinpData from which to run the FLEUR calculation', required=False)
parser.add_argument('--remote', type=int, dest='remote_data',
                        help=('Remote Data of older FLEUR calculation, '
                        'from which files will be copied (broyd ...)'), required=False)
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
nodes_dict = {}
for key, val in vars(args).iteritems():
    print(key, val)
    if val is not None:
        val_new = load_node(val)
    else:
        val_new = val# default[key]
    nodes_dict[key] = val_new


default = {
           }
           
if args.wf_parameters is not None:
    wf_parameters = load_node(args.wf_parameters)
else:
    # use default
    pass

if args.structure is not None:
    structure = load_node(args.structure)
else:
    # use default Si
    pass
    
#if args.calc_parameters:
#    calc_parameters = load_node(args.calc_parameters)
#if args.fleurinp:
#fleurinp = load_node(args.fleurinp)
#remote_data = load_node(args.remote_data)
    
#inpgen = test_and_get_code(args.inpgen, expected_code_type='fleur.fleur')      
fleur_code = is_code(args.fleur)
fleur = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')

if args.inpgen is not None:
    inpgen_code = is_code(args.inpgen)
    inpgen = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')
  
    

#if submit:
#    res = submit(fleur_scf_wc, wf_parameters=wf_para, fleurinp=fleurinp, fleur=code)
#                 #remote_data= remote, fleur=code)
#    print("Submited fleur_scf_wc")
#else:
#    print("Running fleur_scf_wc)
#    res = run(fleur_scf_wc, wf_parameters=wf_para, fleurinp=fleurinp, fleur=code)
#                 #remote_data= remote, fleur=code)
'''
try:
    submit = sys.argv[1]
    if submit == "--submit":
        submit_test = True
    else: # run
        submit_test = False
        raise IndexError
except IndexError:
    print >> sys.stderr, ("The first parameter can only be either "
                          "--send or --dont-send")
    sys.exit(1)

try:
    codename = sys.argv[2]
except IndexError:
    codename = None

try:
    queue = sys.argv[3]
except IndexError:
    queue = None

#####

code = test_and_get_code(codename, expected_code_type='fleur.fleur')

# get where tests folder is, then relative path
inpxmlfile = '/usr/users/iff_th1/broeder/aiida/github/aiida-fleur/tests/inp_xml_files/W/inp.xml'
fleurinp = FleurinpData(files = [inpxmlfile])
    
wf_para = ParameterData(dict={'fleur_runmax' : 4, 
                              'density_criterion' : 0.000001,#})
                              'queue_name' : 'th123_node',
                              'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 12},
                              'walltime_sec':  10*60, 'serial' : run_in_serial_mode})


if submit_test:
    print('workchain do not have so far a submit_test function')
else:
    res = submit(fleur_scf_wc, wf_parameters=wf_para, fleurinp=fleurinp, fleur=code)
                 #remote_data= remote, fleur=code)
    print("Submited fleur_scf_wc")
'''