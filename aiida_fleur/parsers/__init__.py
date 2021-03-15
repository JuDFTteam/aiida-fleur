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
FLEUR plug-in
'''

from __future__ import absolute_import
from aiida.common.exceptions import OutputParsingError


#mainly created this Outputparsing error, that the user sees, that it comes from parsing a fleur calculation.
class FleurOutputParsingError(OutputParsingError):
    pass
    # if you want to do something special here do it
