# -*- coding: utf-8 -*-
from aiida.orm import load_node, Dict
from aiida.engine import submit

from aiida_fleur.workflows.relax import FleurRelaxWorkChain

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)


wf_relax = {'film_distance_relaxation': False,
            'force_criterion': 0.049,
            'relax_iter': 5
            }

wf_relax_scf = {'fleur_runmax': 5,
                'serial': False,
                'itmax_per_run': 50,
                'alpha_mix': 0.015,
                'relax_iter': 25,
                'force_converged': 0.001,
                'force_dict': {'qfix': 2,
                               'forcealpha': 0.75,
                               'forcemix': 'straight'},
                'inpxml_changes': []
                }

wf_relax = Dict(dict=wf_relax)
wf_relax_scf = Dict(dict=wf_relax_scf)

calc_relax = {'comp': {'kmax': 4.0,
                       },
              'kpt': {'div1': 24,
                      'div2': 20,
                      'div3': 1
                      },
              'atom': {'element': 'Pt',
                       'rmt': 2.2,
                       'lmax': 10,
                       'lnonsph': 6,
                       'econfig': '[Kr] 5s2 4d10 4f14 5p6| 5d9 6s1',
                       },
              'atom2': {'element': 'Fe',
                        'rmt': 2.1,
                        'lmax': 10,
                        'lnonsph': 6,
                        'econfig': '[Ne] 3s2 3p6| 3d6 4s2',
                        },
              }

calc_relax = Dict(dict=calc_relax)

options_relax = {'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4, 'num_cores_per_mpiproc': 6},
                 'queue_name': 'devel',
                 'custom_scheduler_commands': '',
                 'max_wallclock_seconds':  1*60*60}

inputs = {
    'scf': {
        'wf_parameters': wf_relax_scf,
        'calc_parameters': calc_relax,
        'options': options_relax,
        'inpgen': inpgen_code,
        'fleur': fleur_code
    },
    'wf_parameters': wf_relax
}

res = submit(FleurRelaxWorkChain, **inputs)
