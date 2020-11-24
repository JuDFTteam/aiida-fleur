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
"""Command line utilities to create and inspect `Dict` nodes with FLAPW parameters."""
import click

from aiida.cmdline.params import options
from aiida.cmdline.utils import decorators, echo

from . import cmd_data


@cmd_data.group('parameter')
def cmd_parameter():
    """Commands to create and inspect `Dict` nodes containing FLAPW parameters ('calc_parameters')."""


@cmd_parameter.command('import')
@click.argument('filename', type=click.Path(exists=True))
@click.option('--fleurinp/--no-fleurinp',
              default=False,
              show_default=True,
              help='Store also the fleurinp and the extractor calcfunction in the db.')
@click.option('--show/--no-show', default=True, show_default=True, help='Print the contents from the extracted dict.')
@options.DRY_RUN()
@decorators.with_dbenv()
def cmd_param_import(filename, dry_run, fleurinp, show):
    """
    Extract FLAPW parameters from a Fleur input file and store as Dict in the db.

    FILENAME is the name/path of the inp.xml file to use.
    """
    from aiida_fleur.data.fleurinp import FleurinpData

    if not filename.endswith('.xml'):
        echo.echo_critical('Error: Currently, we can only extract information from an inp.xml file.')
    fleurinpd = FleurinpData(files=[filename])
    if not fleurinp or dry_run:
        parameters = fleurinpd.get_parameterdata_ncf()
    else:
        parameters = fleurinpd.get_parameterdata(fleurinpd)

    if dry_run:
        echo.echo_success('parsed FLAPW parameters')
    else:
        parameters.store()
        echo.echo_success(f'parsed and stored FLAPW parameters<{parameters.pk}>  <{parameters.uuid}>')

    if show:
        echo.echo_dictionary(parameters.get_dict())


# further ideas:
# query for certain FLAPW parameter nodes.
# Example show me all for Si
# query for options nodes
# command to split and merge parameters nodes together based on elements.
