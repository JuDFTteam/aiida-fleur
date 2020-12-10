# -*- coding: utf-8 -*-
'method' : 'valence',      # what method to use, default for valence to highest open shell
'hole_charge' : 1.0,       # what is the charge of the corehole? 0<1.0
'atoms' : ['all'],         # coreholes on what atoms, positions or index for list,
                           # or element ['Be', (0.0, 0.5, 0.334), 3]
'corelevel': ['all'],      # coreholes on which corelevels [ 'Be1s', 'W4f', 'Oall'...]
'supercell_size' : [2,1,1],# size of the supercell [nx,ny,nz]
'para_group' : None,       # use parameter nodes from a parameter group
'relax' : False,           # relax the unit cell first?
'relax_mode': 'Fleur',     # what releaxation do you want
'relax_para' : 'default',  # parameter dict for the relaxation
'scf_para' : 'default',    # wf parameter dict for the scfs
'same_para' : True,        # enforce the same atom parameter/cutoffs on the corehole calc and ref
'serial' : True,           # run fleur in serial, or parallel?
'magnetic' : True          # jspins=2, makes a difference for coreholes
