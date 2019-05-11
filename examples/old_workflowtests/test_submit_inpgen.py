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
from aiida.plugins import DataFactory, CalculationFactory
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation as calc


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

code = test_and_get_code(codename, expected_code_type='fleur.inpgen')

# W bcc structure 
bohr_a_0= 0.52917721092 # A
a = 3.013812049196*bohr_a_0
cell = [[-a,a,a],[a,-a,a],[a,a,-a]]
s = StructureData(cell=cell)
s.append_atom(position=(0.,0.,0.), symbols='W')
parameters = Dict(dict={
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
                        'kmax': 3.5,
                        'gmax': 2.9,
                        },
                  'kpt': {
                        'nkpt': 200,
                        }})
    
#elements = list(s.get_symbols_set())    

## For remote codes, it is not necessary to manually set the computer,
## since it is set automatically by new_calc
#computer = code.get_remote_computer()
#calc = code.new_calc(computer=computer)

calc = code.new_calc()
#calc = CalculationFactory('fleur.inpgen')
print(calc, type(calc))
calc.label = "Test Fleur inpgen"
calc.description = "Test calculation of the Fleur input generator"
calc.set_max_wallclock_seconds(300)  # 5 min
# Valid only for Slurm and PBS (using default values for the
# number_cpus_per_machine), change for SGE-like schedulers
calc.set_resources({"num_machines": 1})
calc.set_withmpi(False)
calc.use_code(code)
## Otherwise, to specify a given # of cpus per machine, uncomment the following:
# calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 8})
calc.set_resources({"tot_num_mpiprocs" : 1})

#calc.set_custom_scheduler_commands("#SBATCH --account=ch3")
calc.set_custom_scheduler_commands("#BSUB -P jara0043 \n#BSUB -x")

if queue is not None:
    calc.set_queue_name(queue)

calc.use_structure(s)
calc.use_parameters(parameters)

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

