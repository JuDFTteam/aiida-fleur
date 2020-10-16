# -*- coding: utf-8 -*-
from aiida.orm import load_node, Dict
from aiida.engine import submit
from aiida.plugins import WorkflowFactory


fleur_corehole_wc = WorkflowFactory('fleur.corehole')
struc = load_node(STRUCTURE_PK)
flapw_para = load_node(PARAMETERS_PK)
fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)

options = Dict(dict={'resources': {'num_machines': 2, 'num_mpiprocs_per_machine': 24},
                         'queue_name': '',
                         'custom_scheduler_commands': '',
                         'max_wallclock_seconds':  60*60})

wf_para_corehole = Dict(dict={u'atoms': [u'Be'], #[u'all'],
  u'supercell_size': [2, 2, 2], u'corelevel': ['1s'], #[u'all'],
  u'hole_charge': 1.0, u'magnetic': True, u'method': u'valence', u'serial': False})

# launch workflow
dos = submit(fleur_corehole_wc, wf_parameters=wf_para_corehole, structure=struc,
             calc_parameters=flapw_para, options=options,
             fleur=fleur, inpgen=inpgen, label='test core hole wc',
             description='fleur_corehole test')
