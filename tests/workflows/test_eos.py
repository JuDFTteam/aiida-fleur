#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv(profile='aiida_test')
from aiida.orm import Code, DataFactory
from aiida.orm import load_node
from aiida.tools.codespecific.fleur.eos import fleur_eos_wc
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
FleurinpData = DataFactory('fleurinp')

###############################
# Set your values here
codename = 'inpgen_iff@local_iff'#'inpgen_mac_30_11_2016@local_mac'
codename2 = 'fleur_MPI_iff003_v0_27@iff003'
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)

from pprint import pprint
s = load_node(5937)#Ti
s = load_node(5955)#W
#s = load_node(5898) #Be2W
s = load_node(120) # Si

f = s.get_formula()
#print s.get_formula()
parameters = load_node(139)
parameters = load_node(121) # Si
wf_para = ParameterData(dict={'fleur_runmax': 4, 
                                       'points' : 3, 
                                       'step' : 0.002, 
                                       'guess' : 1.00,
                                       'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 12},
                                       'walltime_sec':  60*60,
                                       'queue_name' : 'th123_node'})

print("structure = {}".format(f))
print("wf-para =")#.format(wf_para.get_dict()))
pprint(wf_para.get_dict())
print("parameterdata = ")#{}".format(parameters.get_dict()))
pprint(parameters.get_dict())

res = fleur_eos_wc.run(wf_parameters=wf_para, structure=s, 
                            calc_parameters=parameters, 
                            inpgen = code, fleur=code2)#, settings=settings)# 