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
"""Command line utilities to create and inspect `StructureData` nodes."""
import click
from aiida.cmdline.params import options
from aiida.cmdline.utils import decorators, echo

from . import cmd_data


@click.group('structure')
def cmd_structure():
    """Commands to create and inspect `StructureData` nodes."""


cmd_data.add_command(cmd_structure)
# import filename
# import -N pk_fleurinp


@cmd_structure.command('import')
@click.argument('filename', type=click.Path(exists=True))
@click.option('--fleurinp/--no-fleurinp',
              default=False,
              show_default=True,
              help='Store also the fleurinp and the extractor calcfunction in the db.')
@options.DRY_RUN()
@decorators.with_dbenv()
def cmd_import(filename, dry_run, fleurinp):
    """
    Import a `StructureData` from a Fleur input file.

    FILENAME is the name/path of the inp.xml file to use.

    If you want to import a structure from any file type you can use
    'verdi data structure import -ase <filename>' instead.
    """
    from aiida_fleur.data.fleurinp import FleurinpData

    if not filename.endswith('.xml'):
        echo.echo_critical('Error: Currently, only StructureData from a inp.xml file can be extracted.')
    fleurinpd = FleurinpData(files=[filename])
    if not fleurinp or dry_run:
        structure = fleurinpd.get_structuredata_ncf()
    else:
        structure = fleurinpd.get_structuredata()
    formula = structure.get_formula()

    if dry_run:
        echo.echo_success(f'parsed structure with formula {formula}')
    else:
        structure.store()
        echo.echo_success(
            f'parsed and stored StructureData<{structure.pk}> with formula {formula}, also stored FleurinpData<{fleurinpd.pk}>'
        )
