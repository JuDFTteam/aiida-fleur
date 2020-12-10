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
# pylint: disable=cyclic-import
# ,reimported,unused-import,wrong-import-position
"""
Module with CLI commands for various data types.
"""
import click


@click.group('data')
def cmd_data():
    """Commands to create and inspect data nodes."""


#cmd_root.add_command(cmd_data)

# Import the sub commands to register them with the CLI
from .structure import cmd_structure
from .parameters import cmd_parameter
from .fleurinp import cmd_fleurinp
