#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

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
from aiida.orm import DataFactory
from aiida_fleur.workflows.scf import fleur_scf_wc

# If set to True, will ask AiiDA to run in serial mode (i.e., AiiDA will not
# invoke the mpirun command in the submission script)
run_in_serial_mode = True#False
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
    print("Running fleur_scf_wc")
    res = fleur_scf_wc.run(wf_parameters=wf_para, fleurinp=fleurinp, fleur=code)
                 #remote_data= remote, fleur=code)
