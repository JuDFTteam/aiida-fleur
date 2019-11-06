from aiida_fleur.workflows.create_magnetic_film import FleurCreateMagneticWorkChain
from aiida.orm import Dict, load_node

wf_para = {
        'lattice': 'fcc',
        'miller': [[-1, 1, 0],
                   [0, 0, 1],
                   [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,
        'size': (1, 1, 5),
        'replacements': {0: 'Fe', -1: 'Fe'},
        'decimals': 10,
        'pop_last_layers': 1,

        'total_number_layers': 4,
        'num_relaxed_layers': 2,

        'eos_needed': False,
        'relax_needed': True
    }

wf_eos = {
        'fleur_runmax': 4,
        'density_converged': 0.0002,
        'serial': False,
        'itmax_per_run': 50,
        'inpxml_changes': [],
        'points': 15,
        'step': 0.015,
        'guess': 1.00
        }

calc_eos = {
    'comp': {
        'kmax': 3.8,
        },
    'kpt': {
        'div1': 4,
        'div2' : 4,
        'div3' : 4
        }
}

options_eos = {'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 4, "num_cores_per_mpiproc" : 6},
               'queue_name' : 'devel',
               'environment_variables' : {'OMP_NUM_THREADS' : '6'},
               'custom_scheduler_commands' : '',
               'max_wallclock_seconds':  1*60*60}

wf_relax = {
        'fleur_runmax': 5,
        'serial': False,
        'itmax_per_run': 50,
        'alpha_mix': 0.015,
        'relax_iter': 15,
        'force_converged': 0.0001,
        'force_dict': {'qfix': 2,
                       'forcealpha': 0.5,
                       'forcemix': 'straight'},
        'film_distance_relaxation' : False,
        'force_criterion': 0.001,
        'use_relax_xml': True,
        'inpxml_changes': [],
    }

calc_relax = {
    'comp': {
        'kmax': 4.0,
        },
    'kpt': {
        'div1': 24,
        'div2' : 20,
        'div3' : 1
        },
    'atom':{
        'element' : 'Pt',
        'rmt' : 2.2,
        'lmax' : 10,
        'lnonsph' : 6,
        'econfig': '[Kr] 5s2 4d10 4f14 5p6| 5d9 6s1',
        },
    'atom2':{
        'element' : 'Fe',
        'rmt' : 2.2,
        'lmax' : 10,
        'lnonsph' : 6,
        'econfig': '[Ne] 3s2 3p6| 3d6 4s2',
        },
}

options_relax = {'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 4, "num_cores_per_mpiproc" : 6},
                     'queue_name' : 'devel',
                     'environment_variables' : {'OMP_NUM_THREADS' : '6'},
                     'custom_scheduler_commands' : '',
                     'max_wallclock_seconds':  1*60*60}

wf_para = Dict(dict=wf_para)
wf_eos = Dict(dict=wf_eos)
calc_eos = Dict(dict=calc_eos)
options_eos = Dict(dict=options_eos)
wf_relax = Dict(dict=wf_relax)
calc_relax = Dict(dict=calc_relax)
options_relax = Dict(dict=options_relax)
settings = Dict(dict={})

inputs = {
    'eos': {
        'wf_parameters' : wf_eos,
        'calc_parameters' : calc_eos,
        'inpgen' : inpgen_code,
        'fleur' : fleur_code,
        'options' : options_eos,
        'settings' : settings
    },
    'relax': {
        'wf_parameters' : wf_relax,
        'calc_parameters' : calc_relax,
        'inpgen' : inpgen_code,
        'fleur' : fleur_code,
        'options' : options_relax,
        'label': 'relaxation',
        'description' : 'describtion'
    },
    'wf_parameters': wf_para,
    'eos_output': load_node(14405)
}


#inputs.eos_output = load_node(9226)

res = submit(FleurCreateMagneticWorkChain, **inputs)
