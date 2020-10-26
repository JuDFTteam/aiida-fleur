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
Module with CLI commands for inpgen calc.
'''
import click

from . import cmd_calcjob


@cmd_calcjob.group('inpgen')
def cmd_inpgen():
    """Commands to handle `inpgen` calcs."""


@cmd_inpgen.command('list')
def list_inpgen():
    """
    List FleurinpData in the database with information
    """
    click.echo('Not implemented yet, sorry. Please implement me!')
    # do a query and list all reuse AiiDA code


@cmd_inpgen.command('launch')
def launch_inpgen():
    """
    Launch an inpgen process
    """
    click.echo('Not implemented yet, sorry. Please implement me!')
