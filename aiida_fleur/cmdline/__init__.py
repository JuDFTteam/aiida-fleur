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
Module for the command line interface of AiiDA-FLEUR
'''
import click
import click_completion
import difflib

from aiida_fleur import __version__
from aiida.cmdline.params import options, types
from .launch import cmd_launch
from .data import cmd_data
from .workflows import cmd_workflow
from .visualization import cmd_plot
from .util import options as options_af

# Activate the completion of parameter types provided by the click_completion package
# for bash: eval "$(_AIIDA_FLEUR_COMPLETE=source aiida-fleur)"
click_completion.init()

# Instead of using entrypoints and directly injecting verdi commands into aiida-core
# we created our own separete CLI because verdi will prob change and become
# less material science specific


class MostSimilarCommandGroup(click.Group):
    """
    Overloads the get_command to display a list of possible command
    candidates if the command could not be found with an exact match.
    """

    def get_command(self, ctx, cmd_name):
        """
        Override the default click.Group get_command with one giving the user
        a selection of possible commands if the exact command name could not be found.
        """
        cmd = click.Group.get_command(self, ctx, cmd_name)

        # return the exact match
        if cmd is not None:
            return cmd

        matches = difflib.get_close_matches(cmd_name, self.list_commands(ctx), cutoff=0.5)

        if not matches:
            # single letters are sometimes not matched, try with a simple startswith
            matches = [c for c in sorted(self.list_commands(ctx)) if c.startswith(cmd_name)][:3]

        if matches:
            ctx.fail("'{cmd}' is not a aiida-fleur command.\n\n"
                     'The most similar commands are: \n'
                     '{matches}'.format(cmd=cmd_name, matches='\n'.join(f'\t{m}' for m in sorted(matches))))
        else:
            ctx.fail(f"'{cmd_name}' is not a aiida-fleur command.\n\nNo similar commands found.")

        return None


# Uncomment this for now, has problems with sphinx-click
#@click.command('aiida-fleur', cls=MostSimilarCommandGroup, context_settings={'help_option_names': ['-h', '--help']})
@click.group('aiida-fleur', context_settings={'help_option_names': ['-h', '--help']})
@options.PROFILE(type=types.ProfileParamType(load_profile=True))
# Note, __version__ should always be passed explicitly here,
# because click does not retrieve a dynamic version when installed in editable mode
@click.version_option(__version__, '-v', '--version', message='AiiDA-FLEUR version %(version)s')
def cmd_root(profile):  # pylint: disable=unused-argument
    """CLI for the `aiida-fleur` plugin."""


# To avoid circular imports all commands are not yet connected to the root
# but they have to be here because of bash completion on the other hand, this
# makes them not work with the difflib...
# see how aiida-core does it.

cmd_root.add_command(cmd_launch)
cmd_root.add_command(cmd_data)
cmd_root.add_command(cmd_workflow)
cmd_root.add_command(cmd_plot)
