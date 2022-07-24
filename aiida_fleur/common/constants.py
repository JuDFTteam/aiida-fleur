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
import warnings

warnings.warn('aiida_fleur.common.constants is deprecated'
              'Use masci_tools.util.constants instead', DeprecationWarning)
from masci_tools.util.constants import HTR_TO_EV, BOHR_A
