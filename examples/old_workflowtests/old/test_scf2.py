#!/usr/bin/env python
"""
This test runs the fleur_convergence workflow for path 2
"""
#TODO: overall tests, should create the nodes they use in the db.

from __future__ import absolute_import
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.plugins import Code, DataFactory
from aiida.orm import load_node
#from aiida.work.run import async, run
from aiida_fleur.workflows.scf import FleurScfWorkChain

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
#FleurinpData = DataFactory('fleurinp.fleurinp')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
# Set your values here
codename = 'inpgen_iff@local_iff'#'inpgen_mac_30_11_2016@local_mac'
codename2 = 'fleur_iff@local_iff'#'fleur_mac_v0_27@local_mac'
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)

wf_para = Dict(dict={'relax_runmax' : 4, 
                              'density_criterion' : 0.0000002,
                              'energy_criterion' : 0.0005,
                              'converge_energy' : True, 
                              'converge_density' : True})
fleurinp = load_node(1339)
remote = load_node(1353)
wf_para = load_node(1333)

res = FleurScfWorkChain.run(wf_parameters=wf_para, fleurinp=fleurinp,
                            remote_data= remote, fleur=code2)
