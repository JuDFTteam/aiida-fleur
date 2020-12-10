# -*- coding: utf-8 -*-
'relax': True,               # Not implemented, relax the structure
'relax_mode': 'Fleur',       # Not implemented, how to relax the structure
'relax_para': 'default',     # Not implemented, parameter for the relaxation
'scf_para': 'default',       # Use these parameters for the SCFs
'same_para': True,           # enforce the same parameters
'serial': False,             # Run everthing in serial
'references': {}             # Dict to provide the elemental references
                             # i.e { 'W': calc, outputnode of SCF workflow or fleurinp,
                             # or structure data or (structure data + Parameter),
                             # 'Be' : ...}
