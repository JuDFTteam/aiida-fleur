#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test runs the initial stae CLS workflow
"""
#TODO: overall tests, should create the nodes they use in the db.
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
    #load_dbenv(profile='aiida_test')
from aiida.plugins import Code, DataFactory
from aiida.orm import load_node
from aiida_fleur.workflows.initial_cls import fleur_initial_cls_wc

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')
#FleurinpData = DataFactory('fleurinp.fleurinp')
FleurinpData = DataFactory('fleur.fleurinp')

###############################
# Set your values here
codename = 'inpgen_iff@local_iff'  #'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff@local_iff'#'fleur_mac_v0_27@local_mac'
#codename = 'fleur_inpgen_iff003@iff003'#'inpgen_mac_30_11_2016@local_mac'
#codename2 = 'fleur_iff003_v0_27@iff003'#fleur_iff@iff003'#'fleur_mac_v0_27@local_mac'
codename2 = 'fleur_MPI_iff003_v0_27@iff003'
###############################

code = Code.get_from_string(codename)
code2 = Code.get_from_string(codename2)

resources = {'num_machines': 1, 'num_mpiprocs_per_machine': 12}

s = load_node(5898)  # Be2W

s1 = load_node(5955)  #W
s2 = load_node(3100)  #Be

references = {'use': {'Be': s2.uuid, 'W': s1.uuid}}
print(references)
parameters = Dict(dict={})
parameters = Dict(dict={})

wf_para = Dict(
    dict={
        'fleur_runmax': 4,
        'density_criterion': 0.000002,  #})
        'queue_name': 'th123_node',
        'resources': resources,
        'walltime_sec': 10 * 60,
        'serial': False,
        'references': references
    }
)

res = fleur_initial_cls_wc.run(structure=s, wf_parameters=wf_para, inpgen=code, fleur=code2)  #
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
