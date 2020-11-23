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
Module with CLI commands for calcjob types of aiida-fleur.
'''
import click
from .launch import launch_inpgen
from .launch import launch_fleur
from .launch import launch_scf
from .launch import launch_banddos
from .launch import launch_relax
from .launch import launch_eos
from .launch import launch_corehole
from .launch import launch_init_cls
from .launch import launch_mae
from .launch import launch_create_magnetic
from .launch import launch_dmi
from .launch import launch_ssdisp


@click.group('launch')
def cmd_launch():
    """Commands to launch workflows and calcjobs of aiida-fleur."""


# we do it like this and not in short from to avoid cyclic imports
# and get the full bash completion working
cmd_launch.add_command(launch_inpgen)
cmd_launch.add_command(launch_fleur)
cmd_launch.add_command(launch_scf)
cmd_launch.add_command(launch_banddos)
cmd_launch.add_command(launch_relax)
cmd_launch.add_command(launch_eos)
cmd_launch.add_command(launch_corehole)
cmd_launch.add_command(launch_init_cls)
cmd_launch.add_command(launch_mae)
cmd_launch.add_command(launch_create_magnetic)
cmd_launch.add_command(launch_dmi)
cmd_launch.add_command(launch_ssdisp)
