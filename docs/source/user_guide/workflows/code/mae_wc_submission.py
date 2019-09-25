from aiida_fleur.workflows.mae import FleurMaeWorkChain
from aiida.orm import Dict, load_node

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)
structure = load_node(STRUCTURE_PK)

wf_para = Dict(dict={'sqa_ref': [0.7, 0.7],                
                     'use_soc_ref': False,                 
                     'sqas_theta': [0.0, 1.57079, 1.57079],
                     'sqas_phi': [0.0, 0.0, 1.57079],      
                     'fleur_runmax': 10,                   
                     'density_converged': 0.02,            
                     'serial': False,                      
                     'itmax_per_run': 30,                  
                     'inpxml_changes': []                  
                    })

options = Dict(dict={'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 2},
                     'withmpi' : True,
                     'max_wallclock_seconds' : 600})

calc_parameters = Dict(dict={'kpt': {'div1': 2,
                                     'div2' : 2,
                                     'div3' : 2
                                    }})

SCF_workchain = submit(FleurMaeWorkChain,
                       fleur=fleur_code,
                       inpgen=inpgen_code,
                       calc_parameters=calc_parameters,
                       structure=structure,
                       wf_parameters=wf_para,
                       options=options)
