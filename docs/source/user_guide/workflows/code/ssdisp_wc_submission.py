from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain
from aiida.orm import Dict, load_node

fleur_code = load_node(FLEUR_PK)
inpgen_code = load_node(INPGEN_PK)
structure = load_node(STRUCTURE_PK)

wf_para = Dict(dict={'fleur_runmax' : 3,                    
                     'itmax_per_run' : 30,                  
                     'density_converged' : 0.002,           
                     'serial' : False,                      
                     'beta' : {'all' : 1.57079},            
                     'q_vectors': [[0.0, 0.0, 0.0,          
                                   [0.125, 0.125, 0.0],     
                                   [0.250, 0.250, 0.0],     
                                   [0.375, 0.375, 0.0],     
                                   [0.500, 0.500, 0.0]],    
                     'ref_qss' : [0.0, 0.0, 0.0],            
                     'inpxml_changes': []
                    })

options = Dict(dict={'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 2},
                     'withmpi' : True,
                     'max_wallclock_seconds' : 600})

calc_parameters = Dict(dict={'kpt': {'div1': 2,
                                     'div2' : 2,
                                     'div3' : 2
                                    }})

SCF_workchain = submit(FleurSSDispWorkChain,
                       fleur=fleur_code,
                       inpgen=inpgen_code,
                       calc_parameters=calc_parameters,
                       structure=structure,
                       wf_parameters=wf_para,
                       options=options)
