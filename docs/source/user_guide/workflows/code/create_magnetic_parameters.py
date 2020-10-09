# -*- coding: utf-8 -*-
'lattice': 'fcc',                  # type of the substrate lattice: 'bcc' or 'fcc'
'miller': [[-1, 1, 0],             # miller indices to orient the lattice
           [0, 0, 1],
           [1, 1, 0]],
'host_symbol': 'Pt',               # chemical element of the substrate
'latticeconstant': 4.0,            # initial guess for the substrate lattice constant
'size': (1, 1, 5),                 # sets the size of the film unit cell for relax step
'replacements': {-2: 'Fe',         # sets the layer number to be replaced by another element
                 -1: 'Fe'},        # NOTE: negative number means that replacement will take place
                                   #       on layers on the other side from the held layers

'decimals': 10,                    # set the accuracy of writing atom positions
'pop_last_layers': 1,              # number of bottom layers to be removed before relaxation
'hold_n_first_layers': 5,          # number of bottom layers to be held during the relaxation
                                   # (relaxXYZ = 'FFF')

'total_number_layers': 4,          # use this total number of layers
'num_relaxed_layers': 2,           # use this number of relaxed interlayer distances
