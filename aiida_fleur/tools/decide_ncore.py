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
Contains helper functions to decide on the paralellization to use for a given system.
'''
from __future__ import absolute_import


def gcd(x, y):
    """
    greatest common divisor
    """
    while y != 0:
        (x, y) = (y, x % y)
    return x


def decide_ncore(nkpoints, ncore):
    """
    For kpoint para the number of cores used must be devidebale
    """
    ncore_new = gcd(nkpoints, ncore)
    ncore_list = list(range(ncore_new, ncore + 1))
    #print ncore_list
    for noc in ncore_list:
        remain = nkpoints % noc
        #print remain
        if not remain:
            ncore_new = noc
    return ncore_new
