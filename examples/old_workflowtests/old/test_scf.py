#!/usr/bin/env python
"""
This test runs the fleur_convergence workflow for path 1
"""
#TODO: overall tests, should create the nodes they use in the db.
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv(profile='aiida_test')
from aiida.orm import Code, DataFactory
from aiida.orm import load_node
from aiida_fleur.workflows.scf import fleur_scf_wc

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
#FleurinpData = DataFactory('fleurinp.fleurinp')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
# Set your values here
codename = 'inpgen_iff_0.28@local_iff' #'inpgen_iff@local_iff'#'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff@local_iff'#'fleur_mac_v0_27@local_mac'
#codename = 'fleur_inpgen_iff003@iff003'#'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff003_v0_27@iff003'#fleur_iff@iff003'#'fleur_mac_v0_27@local_mac'
codename2 = 'fleur_iff_0.28@local_iff'#'fleur_MPI_iff003_v0_27@iff003'
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)

s = load_node(138)

parameters = ParameterData(dict={})

settings = ParameterData(dict={'files_to_retrieve' : [], 'files_not_to_retrieve': [], 
                               'files_copy_remotely': [], 'files_not_copy_remotely': [],
                               'commandline_options': ["-wtime", "30"], 'blaha' : ['bla']})
    
wf_para = ParameterData(dict={'fleur_runmax' : 4, 
                              'density_criterion' : 0.000001,#})
                              'queue_name' : 'th123_node',
                              'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 12},
                              'walltime_sec':  10*60})

res = fleur_scf_wc.run(wf_parameters=wf_para, structure=s, 
                            #calc_parameters=parameters, 
                            inpgen = code, fleur=code2)#, settings=settings)# 

'''
code = Code.get_from_string('inpgen_mac_25_10_2016')
code2 = Code.get_from_string('fleur_mac_v0_27')
computer = Computer.get('local_mac')
wf_para = ParameterData(dict={'fleur_runmax' : 4, 'density_criterion' : 0.0000001})#, 'queue' : 'th1'})
res = run(fleur_convergence, wf_parameters=wf_para, structure=load_node(24422),
          calc_parameters=load_node(24507), inpgen = code, fleur=code2)
'''
