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
Options commonly used throughout the aiida-fleur command line interface.
To standardize at least of the options, they are kept as close as possible to
aiida-core and aiida-quantumespresso
"""
import click
from aiida.cmdline.params import types
from aiida.cmdline.params.options import OverridableOption

STRUCTURE = OverridableOption('-s',
                              '--structure',
                              type=types.DataParamType(sub_classes=('aiida.data:structure',)),
                              help='StructureData node.')

MAX_NUM_MACHINES = OverridableOption('-m',
                                     '--max-num-machines',
                                     type=click.INT,
                                     default=1,
                                     show_default=True,
                                     help='The maximum number of machines (nodes) to use for the calculations.')

MAX_WALLCLOCK_SECONDS = OverridableOption('-w',
                                          '--max-wallclock-seconds',
                                          type=click.INT,
                                          default=1800,
                                          show_default=True,
                                          help='the maximum wallclock time in seconds to set for the calculations.')

WITH_MPI = OverridableOption('-i',
                             '--with-mpi',
                             is_flag=True,
                             default=False,
                             show_default=True,
                             help='Run the calculations with MPI enabled.')

PARENT_FOLDER = OverridableOption('-P',
                                  '--parent-folder',
                                  'parent_folder',
                                  type=types.DataParamType(sub_classes=('aiida.data:remote',)),
                                  show_default=True,
                                  required=False,
                                  help='The PK of a parent remote folder (for restarts).')

DAEMON = OverridableOption('-d',
                           '--daemon',
                           is_flag=True,
                           default=False,
                           show_default=True,
                           help='Submit the process to the daemon instead of running it locally.')

CLEAN_WORKDIR = OverridableOption(
    '-x',
    '--clean-workdir',
    is_flag=True,
    default=False,
    show_default=True,
    help='Clean the remote folder of all the launched calculations after completion of the workchain.')
