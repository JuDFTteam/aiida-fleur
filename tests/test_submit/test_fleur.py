#!/usr/bin/env python
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys,os 

from aiida.orm import Calculation, Code, Computer, Data, Node, load_node
from aiida.orm import CalculationFactory, DataFactory

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')

###############################
# Set your values here
codename1 = 'inpgen_iff@local_iff'#'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff@local_iff'#'fleur_mac_v0_27@local_mac'
codename = 'fleur_iff003_v0_27@iff003'
###############################

fleurinppk = 4968#Si
code = Code.get_from_string(codename)
#s = load_node()
fleurinpd = load_node(fleurinppk)
calc = code.new_calc(max_wallclock_seconds=180,
                resources={"num_machines": 1})
calc.label = "Fleur input test "
calc.description = "Si fleur input test. A much longer description1"

calc.use_fleurinpdata(fleurinpd)
calc.use_code(code)
calc.set_withmpi(False)
calc.set_queue_name('th123_node')
calc.submit_test()
#calc.store_all()
#calc.submit()
print "created calculation,{} with PK={}".format(calc.label,calc.pk)
pkid_parent = calc.pk