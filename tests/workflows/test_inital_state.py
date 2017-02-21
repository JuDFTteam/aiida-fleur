#!/usr/bin/env python
"""
This test runs the initial stae CLS workflow 
"""
#TODO: overall tests, should create the nodes they use in the db.
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv(profile='aiida_test')
from aiida.orm import Code, DataFactory
from aiida.orm import load_node
from aiida.tools.codespecific.fleur.initial_state_CLS import initial_state_CLS

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
#FleurinpData = DataFactory('fleurinp.fleurinp')
FleurinpData = DataFactory('fleurinp')

###############################
# Set your values here
codename = 'inpgen_iff@local_iff'#'inpgen_mac_30_11_2016@local_mac'
codename2 = 'fleur_iff@local_iff'#'fleur_mac_v0_27@local_mac'
#codename = 'fleur_inpgen_iff003@iff003'#'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff003_v0_27@iff003'#fleur_iff@iff003'#'fleur_mac_v0_27@local_mac'
#codename2 = 'fleur_MPI_iff003_v0_27@iff003'
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)

resources = {"num_machines": 1}#, "num_mpiprocs_per_machine" : 12}
s = load_node(3100) # Be

parameters = ParameterData(dict={})

wf_para = ParameterData(dict={'fleur_runmax' : 4, 
                              'density_criterion' : 0.000002,#})
                              'queue_name' : 'th123_node',
                              'resources' : resources,
                              'walltime_sec':  10*60})

res = initial_state_CLS.run(structure=s, inpgen = code, fleur=code2)# 
#wf_parameters=wf_para, 
'''
    _default_wf_para = {'references' : {'calculate' : 'all'}, 
                        'calculate_doses' : False,
                        'relax' : True,
                        'relax_mode': 'QE Fleur',
                        'relax_para' : 'default',
                        'scf_para' : 'default',
                        'dos_para' : 'default',
                        'same_para' : True,
                        'resources' : {"num_machines": 1},
                        'walltime_sec' : 10*30,
                        'queue' : None,
                        'serial' : False}    
    
           spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict=self._default_wf_para))#get_defaut_wf_para()))#
        spec.input("fleurinp", valid_type=FleurinpData, required=False)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("inpgen", valid_type=Code, required=False)        
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False) 
'''