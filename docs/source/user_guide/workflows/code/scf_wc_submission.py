# -*- coding: utf-8 -*-
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida.orm import Dict, load_node

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)
structure = load_node(STRUCTURE_PK)

wf_para = Dict(dict={'fleur_runmax': 3,
                     'density_converged': 0.001,
                     'mode': 'density',
                     'itmax_per_run': 30,
                     'serial': False,
                     'only_even_MPI': False})

options = Dict(dict={'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 2},
                     'withmpi': True,
                     'max_wallclock_seconds': 600})

calc_parameters = Dict(dict={'kpt': {'div1': 2,
                                     'div2': 2,
                                     'div3': 2
                                     }})

SCF_workchain = submit(FleurScfWorkChain,
                       fleur=fleur_code,
                       inpgen=inpgen_code,
                       calc_parameters=calc_parameters,
                       structure=structure,
                       wf_parameters=wf_para,
                       options=options)
