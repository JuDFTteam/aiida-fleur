# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
'''
Here we collect physical constants which are used throughout the code
that way we ensure consitency
'''
# at some point one should import these from masci-tools, or better scipy or ase to ensure,
# that all judft plugins and tools take the same values, to make roundtrips consistent
# NIST https://physics.nist.gov/cgi-bin/cuu/Value?hrev
HTR_TO_EV = 27.211386245988  #(53)
BOHR_A = 0.5291772108
#Scipy bohr 5.29177210903e-11 m
#Scipy htr 27.211386245988 eV
# NIST BOHR 0.529177210903 #(80)
#https://physics.nist.gov/cgi-bin/cuu/Value?bohrrada0

#Fleur
#htr_eV   = 27.21138602
#bohr=0.5291772108
#bohrtocm=0.529177e-8
#pymatgen uses scipy.constants
#ase: Bohr 0.5291772105638411
#Hartree 27.211386024367243
#Rydberg 13.605693012183622
#1/Bohr
#1.8897261258369282
#aiida-core units:
#bohr_to_ang = 0.52917720859
