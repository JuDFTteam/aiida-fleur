# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
contains verdi commands for the scf workchain
in general these should become options of verdi aiida-fleur workchains 
"""

from __future__ import absolute_import
import click


@click.group()
def scf_wc():
    pass

@scf_wc.command()
def res():
    """
    Prints the result node to screen
    """
    click.echo('verdi aiida-fleur scf res')

@scf_wc.command()
def show():
    """
    plots the results of a 
    """
    click.echo('verdi aiida-fleur scf show')

@scf_wc.command()
def list():
    """
    similar to the verdi work list command, but this displays also some 
    specific information about the scfs
    """
    click.echo('verdi aiida-fleur scf list')