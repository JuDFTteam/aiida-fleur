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
Contains verdi commands for the scf workchain
in general these should become options of verdi aiida-fleur workchains
"""

from __future__ import absolute_import
import click

from . import cmd_workflow


@cmd_workflow.group('scf')
def cmd_scf():
    """Commands to launch and inspect scf workchains."""


@cmd_scf.command('launch')
def launch_scf():
    """
    Prints the result node to screen
    """
    click.echo('Not implemented yet, sorry. Please implement me!')
