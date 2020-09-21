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
"""
contains verdi commands that are useful for fleur workchains
"""

from __future__ import absolute_import
import click


@click.group()
def workchains():
    pass


@workchains.command()
def res_wc():
    """
    Prints the result node to screen
    """
    click.echo('verdi aiida-fleur workchains res pk/uuid/list')


@workchains.command()
def show_wc():
    """
    plots the results of a workchain
    """
    click.echo('verdi aiida-fleur workchains show pk/uuid/list')


@workchains.command()
def list_wc():
    """
    similar to the verdi work list command, but this displays also some
    specific information about the fleur workchains, can be filtered for
    certain workchains...
    """
    click.echo('verdi aiida-fleur workchians list -scf -A -p')
