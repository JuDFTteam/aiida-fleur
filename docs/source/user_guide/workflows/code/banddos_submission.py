# -*- coding: utf-8 -*-
from aiida_fleur.workflows.banddos import FleurBandDosWorkChain
from aiida.orm import Dict, load_node
from aiida.engine import submit

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)
structure = load_node(STRUCTURE_PK)

wf_para = Dict(
    dict={
        'mode': 'band',
        'kpath': 'auto',  #seek (aiida), fleur (only Max4) or string to pass to ase
        'klistname': 'path-3',
        'kpoints_number': None,
        'kpoints_distance': None,
        'kpoints_explicit': None,  #dictionary containing a list of kpoints, weights
        #and additional arguments to pass to set_kpointlist
        'sigma': 0.005,
        'emin': -0.50,
        'emax': 0.90,
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'inpxml_changes': [],
    })

wf_para_scf = Dict(
    dict={
        'fleur_runmax': 3,
        'density_converged': 0.001,
        'mode': 'density',
        'itmax_per_run': 30,
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        }
    })

options = Dict(dict={
    'resources': {
        'num_machines': 1,
        'num_mpiprocs_per_machine': 2
    },
    'withmpi': True,
    'max_wallclock_seconds': 600
})

options_scf = Dict(dict={
    'resources': {
        'num_machines': 1,
        'num_mpiprocs_per_machine': 2
    },
    'withmpi': True,
    'max_wallclock_seconds': 600
})

calc_parameters = Dict(dict={'kpt': {'nkpts': 500, 'path': 'default'}})

inputs = {
    'scf': {
        'wf_parameters': wf_para_scf,
        'structure': structure,
        'calc_parameters': calc_parameters,
        'options': options_scf,
        'inpgen': inpgen_code,
        'fleur': fleur_code
    },
    'wf_parameters': wf_para,
    'fleur': fleur_code,
    'options': options
}

banddos_workchain = submit(FleurBandDosWorkChain, **inputs)
