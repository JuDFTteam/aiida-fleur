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
AiiDA-FLEUR
'''
import click
import json

from .defaults import get_code_interactive, get_default_dict
from aiida.cmdline.utils import decorators


# general further commands for fleur workchains
@click.command('config')
@decorators.with_dbenv()
def cmd_defaults():
    """Interactively create/modify the default settings for aiida-fleur CLI."""

    dict = get_default_dict()

    #default codes
    dict['fleur'] = get_code_interactive('fleur.fleur', dict['fleur'])
    dict['inpgen'] = get_code_interactive('fleur.inpgen', dict['inpgen'])

    import os
    HOME = os.getenv('HOME')
    try:
        os.mkdir(f"{HOME}/.aiida-fleur")
    except:
        pass  #dir might exist already
    with open(f"{HOME}/.aiida-fleur/cli.json", 'w') as f:
        json.dump(dict, f)
