#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys,os 
from aiida.plugins import Code, DataFactory
from aiida.orm import Computer
from aiida.orm import load_node
from aiida.engine import async, run
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.workflows.relax import fleur_relax_wc

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
# Set your values here
codename = 'fleur_inpgen_mac'
computer_name = 'local_mac'
#computer_name = 'iff003'
#codename2 = 'fleur_v0.27@iff003'
codename2 = 'fleur_iff003_v0_27@iff003'

#codename2 = 'fleur_mac'

###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)
#JobCalc = FleurinputgenCalculation.process()
computer = Computer.objects.get(computer_name)

s = load_node(14204)#13586)#137)# Be13586, W 137
print(s.sites)
#print s.cell
parameters = load_node(13496)# Be 13496, W 13161
wf_para = Dict(dict={'relax_runmax' : 5, 'density_criterion' : 0.0000001, 'max_force_cycle' : 9})


res = fleur_relax_wc.run(wf_parameters=wf_para, structure=s, calc_parameters=parameters, inpgen = code, fleur=code2)#, computer=computer)
