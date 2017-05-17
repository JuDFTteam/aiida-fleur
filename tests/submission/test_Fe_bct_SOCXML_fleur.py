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

# If set to True, will ask AiiDA to run in serial mode (i.e., AiiDA will not
# invoke the mpirun command in the submission script)
run_in_serial_mode = True#False

################################################################


ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')
FleurinpData = DataFactory('fleurinp')
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

queue = None
# queue = "th1_small"
settings = None
#####

code = test_and_get_code(codename, expected_code_type='fleur_inp.fleur')

#TODO: how to make smart path?
# get where tests folder is, then relative path
inpxmlfile = '/usr/users/iff_th1/broeder/aiida/github/aiida_fleur_plugin/tests/inp_xml_files/Fe_bct_SOCXML/files/inp.xml'
enpara = '/usr/users/iff_th1/broeder/aiida/github/aiida_fleur_plugin/tests/inp_xml_files/Fe_bct_SOCXML/files/enpara'
symout = '/usr/users/iff_th1/broeder/aiida/github/aiida_fleur_plugin/tests/inp_xml_files/Fe_bct_SOCXML/files/sym.out'

fleurinp = FleurinpData(files = [inpxmlfile, enpara, symout])
print fleurinp.files
## For remote codes, it is not necessary to manually set the computer,
## since it is set automatically by new_calc
#computer = code.get_remote_computer()
#calc = code.new_calc(computer=computer)

calc = code.new_calc()
calc.label = "Fe_bct_SOC Fleur test"
calc.description = ("Simple test of Fleur with two steps:"
                    "1.Generate a starting density"
                    "2.Run 20 iterations and compare convergence, fermi-energy & total energy")
calc.set_max_wallclock_seconds(5 * 60)  # 5 min
# Valid only for Slurm and PBS (using default values for the
# number_cpus_per_machine), change for SGE-like schedulers
calc.set_resources({"num_machines": 1})
if run_in_serial_mode:
    calc.set_withmpi(False)
## Otherwise, to specify a given # of cpus per machine, uncomment the following:
# calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 8})

#calc.set_custom_scheduler_commands("#SBATCH --account=ch3")

if queue is not None:
    calc.set_queue_name(queue)

calc.use_fleurinpdata(fleurinp)
#calc.use_code(code)

if settings is not None:
    calc.use_settings(settings)


if submit_test:
    subfolder, script_filename = calc.submit_test()
    print "Test_submit for calculation (uuid='{}')".format(
        calc.uuid)
    print "Submit file in {}".format(os.path.join(
        os.path.relpath(subfolder.abspath),
        script_filename
    ))
else:
    calc.store_all()
    print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)

