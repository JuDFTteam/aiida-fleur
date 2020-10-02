# -*- coding: utf-8 -*-
from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain
from aiida.orm import Dict, load_node

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)
structure = load_node(STRUCTURE_PK)

wf_para = Dict(dict={'points': 9,
                     'step': 0.002,
                     'guess': 1.00
                     })


wf_para_scf = Dict(dict={'fleur_runmax': 2,
                        'itmax_per_run': 120,
                        'density_converged': 0.2,
                        'serial': False,
                        'mode': 'density'
               })


options_scf = Dict(dict={'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 8},
                         'queue_name': 'devel',
                         'custom_scheduler_commands': '',
                         'max_wallclock_seconds':  60*60})

inputs = {'scf': {
                  'wf_parameters': wf_para_scf,
                  'calc_parameters': parameters,
                  'options': options_scf,
                  'inpgen': inpgen_code,
                  'fleur': fleur_code
                 },
          'wf_parameters': wf_para,
          'structure': structure
}

SCF_workchain = submit(FleurSSDispWorkChain,
                       fleur=fleur_code,
                       inpgen=inpgen_code,
                       calc_parameters=calc_parameters,
                       structure=structure,
                       wf_parameters=wf_para,
                       options=options)
