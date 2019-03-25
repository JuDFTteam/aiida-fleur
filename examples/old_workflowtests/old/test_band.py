#!/usr/bin/env python
"""
This test runs the Fleur band workflow
"""
from __future__ import absolute_import
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv(profile='aiida_test')
from aiida.orm import Code, DataFactory
from aiida.orm import load_node
#from aiida.work.run import run
from aiida_fleur.workflows.band import fleur_band_wc

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
# Set your values here
codename2 = 'fleur_iff@local_iff'#'fleur_iff003_v0_27@iff003'
codename2 = 'fleur_iff003_v0_27@iff003'
###############################

code2 = Code.get_from_string(codename2)

fleurinp = load_node(1684)
fleur_calc = load_node(1693)
remote = fleur_calc.out.remote_folder
wf_para = ParameterData(dict={'queue' : 'th123_node'})


#res = band.run(fleurinp=fleurinp, remote=remote, fleur=code2)
res = fleur_band_wc.run(wf_parameters=wf_para, fleurinp=fleurinp, remote=remote, fleur=code2)
