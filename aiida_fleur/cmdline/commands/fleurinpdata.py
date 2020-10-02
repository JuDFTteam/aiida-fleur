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
Contains verdi commands for fleurinpdata
"""
from __future__ import absolute_import
import click


# this will get replaced by data_plug.group
#@data_plug.group('fleur.fleurinp')
@click.group()
def fleurinp():
    pass


@fleurinp.command()
def list_fleurinp():
    """
    list all Fleurinp data in the database and displays some information
    """
    click.echo('verdi data fleurinp list')
    #do a query and list all reuse AiiDA code


@fleurinp.command()
def show():
    """
    Shows some basic information about the fleurinp datastructure and dumbs the
    inp.xml
    """
    click.echo('verdi data fleurinp list')


@fleurinp.command()
def open_inp():
    """
    opens the inp.xml in some editor, readonly.
    inp.xml
    """
    click.echo('verdi data fleurinp list')


# this is a maybe
@fleurinp.command()
def get_structure():
    """
    Prints some basic information about the structure data and return a structure uuid/pk
    """
    click.echo('verdi data fleurinp list')


@fleurinp.command()
def get_kpoints():
    """
    Prints some basic information about the kpoints data and returns a kpoints uuid/pk
    """
    click.echo('verdi data fleurinp kpoints')


@fleurinp.command()
def get_parameters():
    """
    Prints some basic information about the parameter data and returns a
    parameter data uuid/pk
    """
    click.echo('verdi data fleurinp parameter')
