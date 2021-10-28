# -*- coding: utf-8 -*-
'beta': {'all': 1.57079},               # see description below
'sqas_theta': [0.0, 1.57079, 1.57079],  # a list of theta values for the FT
'sqas_phi': [0.0, 0.0, 1.57079],        # a list of phi values for the FT
'soc_off': [],                          # a list of atom labels to switch off SOC term
'q_vectors': [[0.0, 0.0, 0.0],          # set a set of q-vectors to calculate DMI dispersion
              [0.1, 0.1, 0.0]]
'add_comp_para': {
    'only_even_MPI': False,             # True if suppress parallelisation having odd number of MPI
    'max_queue_nodes': 20,              # Max number of nodes allowed (used by automatic error fix)
    'max_queue_wallclock_sec': 86400    # Max number of walltime allowed (used by automatic error fix)
    },
'ref_qss': [0.0, 0.0, 0.0],             # sets a q-vector for the reference calculation
'inpxml_changes': [],                   # additional changes before the FT step
