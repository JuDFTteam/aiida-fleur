# -*- coding: utf-8 -*-
'beta': {'all': 1.57079},           # see description below
'prop_dir': [1.0, 0.0, 0.0],        # sets a propagation direction of a q-vector
'q_vectors': [[0.0, 0.0, 0.0],      # set a set of q-vectors to calculate SSDispersion
              [0.125, 0.0, 0.0],
              [0.250, 0.0, 0.0],
              [0.375, 0.0, 0.0]],
'ref_qss': [0.0, 0.0, 0.0],         # sets a q-vector for the reference calculation
'inpxml_changes': []                # additional changes before the FT step
'serial': False                     # False if use MPI version for the FT calc
'only_even_MPI': False,             # True if suppress parallelisation having odd number of MPI
