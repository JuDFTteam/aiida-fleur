# -*- coding: utf-8 -*-
from aiida.orm import load_node, Dict
from aiida.engine import submit

from aiida_fleur.workflows.ssdisp_conv import FleurSSDispConvWorkChain

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)
structure = load_node(STRUCTURE_PK)

wf_para = Dict(dict={'beta': {'all': 1.57079},
                     'q_vectors': {'label': [0.0, 0.0, 0.0],
                                   'label2': [0.125, 0.0, 0.0]
                                   }
                     })


options = Dict(dict={'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 24},
                     'queue_name': 'devel',
                     'custom_scheduler_commands': '',
                     'max_wallclock_seconds':  60*60})


parameters = Dict(dict={'atom': {'element': 'Pt',
                                 'lmax': 8
                                 },
                        'atom2': {'element': 'Fe',
                                  'lmax': 8,
                                  },
                        'comp': {'kmax': 3.8,
                                 },
                        'kpt': {'div1': 20,
                                'div2': 24,
                                'div3': 1
                                }})

wf_para_scf = {'fleur_runmax': 2,
               'itmax_per_run': 120,
               'density_converged': 0.2,
               'serial': False,
               'mode': 'density'
               }

wf_para_scf = Dict(dict=wf_para_scf)

options_scf = Dict(dict={'resources': {'num_machines': 2, 'num_mpiprocs_per_machine': 24},
                         'queue_name': 'devel',
                         'custom_scheduler_commands': '',
                         'max_wallclock_seconds':  60*60})

inputs = {'scf': {'wf_parameters': wf_para_scf,
                  'structure': structure,
                  'calc_parameters': parameters,
                  'options': options_scf,
                  'inpgen': inpgen_code,
                  'fleur': fleur_code
                  },
          'wf_parameters': wf_para,
          }


res = submit(FleurSSDispConvWorkChain, **inputs)
