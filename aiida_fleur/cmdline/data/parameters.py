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

from aiida.cmdline.params import options as aiida_options
from aiida.cmdline.utils import decorators, echo
from ..util import options as fleur_options
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
@aiida_options.DRY_RUN()
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
        parameters = fleurinpd.get_parameterdata()

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
@cmd_data.group('options')
def cmd_options():
    """Commands to create and inspect `Dict` nodes containing options."""


@cmd_options.command('create')
@fleur_options.MAX_NUM_MACHINES()
@fleur_options.NUM_MPIPROCS_PER_MACHINE()
@fleur_options.MAX_WALLCLOCK_SECONDS()
@fleur_options.QUEUE_NAME()
@aiida_options.DRY_RUN()
@click.option('--show/--no-show', default=True, show_default=True, help='Print the contents from the options dict.')
@decorators.with_dbenv()
def cmd_option_create(max_num_machines, num_mpiprocs_per_machine, queue, max_wallclock_seconds, dry_run, show):
    """
    Command to create options dict nodes
    """
    from aiida_fleur.common.node_generators import generate_wf_option_node

    optiondict = {}
    optiondict = {
        'resources': {
            'num_machines': max_num_machines,
            'num_mpiprocs_per_machine': num_mpiprocs_per_machine
        },
        'max_wallclock_seconds': max_wallclock_seconds,
        'queue_name': queue
    }

    options = generate_wf_option_node(**optiondict)

    if dry_run:
        echo.echo_success('Created option node.')
    else:
        options.store()
        echo.echo_success(f'Created and stored Options node <{options.pk}>  <{options.uuid}>')

    if show:
        echo.echo_dictionary(options.get_dict())
