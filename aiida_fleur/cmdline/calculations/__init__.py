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
Module with CLI commands for calcjob types of aiida-fleur.
'''
from .. import cmd_root


@cmd_root.group('calcjob')
def cmd_calcjob():
    """Commands to launch and inspect calcjobs of aiida-fleur."""


# Import the sub commands to register them with the CLI
from .fleur import cmd_fleur
from .inpgen import cmd_inpgen
