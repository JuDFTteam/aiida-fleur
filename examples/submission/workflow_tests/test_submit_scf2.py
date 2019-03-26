#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

import sys
import os

from aiida.common.example_helpers import test_and_get_code
from aiida.plugins import DataFactory
from aiida.engine import submit
from aiida_fleur.workflows.scf import fleur_scf_wc

# If set to True, will ask AiiDA to run in serial mode (i.e., AiiDA will not
# invoke the mpirun command in the submission script)
run_in_serial_mode = False#True#False
queue = None

################################################################
ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')


try:
    dontsend = sys.argv[1]
    if dontsend == "--dont-send":
        submit_test = True
    elif dontsend == "--send":
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print(("The first parameter can only be either "
                          "--send or --dont-send"), file=sys.stderr)
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
    
wf_para = Dict(dict={'fleur_runmax' : 4, 
                              'density_criterion' : 0.000001,#})
                              'queue_name' : queue,
                              'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 7},
                              'walltime_sec':  10*60, 'serial' : run_in_serial_mode})


if submit_test:
    print('workchain do not have so far a submit_test function')
else:
    res = submit(fleur_scf_wc, wf_parameters=wf_para, fleurinp=fleurinp, fleur=code)
                 #remote_data= remote, fleur=code)
    print("Submited fleur_scf_wc")
