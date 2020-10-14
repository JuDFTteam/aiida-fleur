# -*- coding: utf-8 -*-
from aiida.orm import load_node, Dict
from aiida.engine import submit
from aiida.plugins import WorkflowFactory


fleur_init_cls_wc = WorkflowFactory('fleur.initial_cls')
struc = load_node(STRUCTURE_PK)
flapw_para = load_node(PARAMETERS_PK)
fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)

options = Dict(dict={'resources': {'num_machines': 2, 'num_mpiprocs_per_machine': 24},
                         'queue_name': '',
                         'custom_scheduler_commands': '',
                         'max_wallclock_seconds':  60*60})

wf_para_initial = Dict(dict={
  'references': {'Be': '257d8ae8-32b3-4c95-8891-d5f527b80008',
                 'W': 'c12c999c-9a00-4866-b6ef-9bb5d28e7797'},
  'scf_para': {'density_criterion': 5e-06, 'fleur_runmax': 3, 'itmax_per_run': 80}})

# launch workflow
initial_res = submit(fleur_init_cls_wc, wf_parameters=wf_para_initial, structure=struc,
             calc_parameters=flapw_para, options=options, fleur=fleur, inpgen=inpgen,
             label='test initial cls', description='fleur_initial_cls test')
