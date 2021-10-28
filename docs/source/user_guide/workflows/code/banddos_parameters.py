# -*- coding: utf-8 -*-
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
