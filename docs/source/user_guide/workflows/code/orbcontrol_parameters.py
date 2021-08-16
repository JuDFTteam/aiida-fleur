# -*- coding: utf-8 -*-
'iterations_fixed': 30,                         #Number of iterations to run with fixed density matrices
'ldau_dict': {'all-Nd': {'l': 3,                #Specifications of the LDA+U parameters to add
                         'U': 6.7,              #Note that the input has to be without LDA+U
                         'J': 0.7,              #for this wokchain to wotk consistently
                         'l_amf': False}},
'use_orbital_occupation': False,                #If True the obtained configurations are used for the
                                                #atomic orbitals and not the spherical harmonics
'fixed_occupations': {'all-Nd': {3: (4,0)}},    #Specifies the occupations for each LDA+U orbital
                                                #for each spin to generate all possible configurations from
'fixed_configurations': None,                   #Alternative way to specify density matrix configurations
                                                #specifies the explicit configurations to use
