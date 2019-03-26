#/usr/bin/env python
"""
This test runs the Fleur dos workflow
"""
from __future__ import absolute_import
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv(profile='aiida_test')
from aiida.plugins import Code, DataFactory
from aiida.orm import load_node
#from aiida.work.run import run
from aiidai_fleur.workflows.dos import fleur_dos_wc

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
# Set your values here
codename = 'inpgen_iff@local_iff'#'fleur_inpgen_mac'
codename2 = 'fleur_iff@local_iff'#'fleur_iff003_v0_27@iff003'
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)

fleurinp = load_node(1684)
fleur_calc = load_node(1693)
remote = fleur_calc.out.remote_folder
#wf_para = ParameterData(dict={})


res = fleur_dos_wc.run(fleurinp=fleurinp, remote=remote, fleur=code2)
#res = dos.run(wf_parameters=wf_para, fleurinp=fleurinp, fleur_calc=remote, fleur=code2)
