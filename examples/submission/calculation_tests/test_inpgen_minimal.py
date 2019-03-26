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



################################################################


ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')
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

queue = None
# queue = "th1_small"
settings = None
#####

code = test_and_get_code(codename, expected_code_type='fleur_inp.fleurinputgen')

# W bcc structure 
bohr_a_0= 0.52917721092 # A
a = 3.013812049196*bohr_a_0
cell = [[-a,a,a],[a,-a,a],[a,a,-a]]
s = StructureData(cell=cell)
s.append_atom(position=(0.,0.,0.), symbols='W')
    
#elements = list(s.get_symbols_set())    

## For remote codes, it is not necessary to manually set the computer,
## since it is set automatically by new_calc
#computer = code.get_remote_computer()
#calc = code.new_calc(computer=computer)

calc = code.new_calc()
calc.label = "Test Fleur inpgen minimal"
calc.description = "Test calculation of the Fleur input generator minimal"
calc.set_max_wallclock_seconds(5 * 60)  # 5 min
# Valid only for Slurm and PBS (using default values for the
# number_cpus_per_machine), change for SGE-like schedulers
calc.set_resources({"num_machines": 1})
calc.set_withmpi(False)
## Otherwise, to specify a given # of cpus per machine, uncomment the following:
# calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 8})

#calc.set_custom_scheduler_commands("#SBATCH --account=ch3")

if queue is not None:
    calc.set_queue_name(queue)

calc.use_structure(s)

if settings is not None:
    calc.use_settings(settings)


if submit_test:
    subfolder, script_filename = calc.submit_test()
    print("Test_submit for calculation (uuid='{}')".format(
        calc.uuid))
    print("Submit file in {}".format(os.path.join(
        os.path.relpath(subfolder.abspath),
        script_filename
    )))
else:
    calc.store_all()
    print("created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk))
    calc.submit()
    print("submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk))

