# -*- coding: utf-8 -*-
'sqa_ref': [0.7, 0.7],                  # sets theta and phi for the reference calc
'use_soc_ref': False,                   # True if reference calc should use SOC terms
'sqas_theta': [0.0, 1.57079, 1.57079],  # a list of theta values for the FT
'sqas_phi': [0.0, 0.0, 1.57079],        # a list of phi values for the FT
'add_comp_para': {
    'only_even_MPI': False,             # True if suppress parallelisation having odd number of MPI
    'max_queue_nodes': 20,              # Max number of nodes allowed (used by automatic error fix)
    'max_queue_wallclock_sec': 86400    # Max number of walltime allowed (used by automatic error fix)
    },
'soc_off': [],                          # a list of atom labels to switch off SOC term
'inpxml_changes': []                    # additional changes before the FT step
