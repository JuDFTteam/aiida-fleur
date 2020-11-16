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
from .defaults import get_inpgen, get_fleur, get_si_bulk_structure
from .types import StructureNodeOrFileParamType

#ANYSOURCE_STRUCTURE = OverridableOption(
#    '-as', '--anysource_structure',
#    type=click.Path(exists=True),
#    help=('A path to a file which contains structural information which will '
#        'be parsed with ase or pymatgen extracting a StructureData node.'))

STRUCTURE_OR_FILE = OverridableOption(
    '-s',
    '--structure',
    type=StructureNodeOrFileParamType(),
    help='StructureData node, given by pk or uuid or file in any for mat which will be converted.')

STRUCTURE = OverridableOption('-s',
                              '--structure',
                              type=types.DataParamType(sub_classes=('aiida.data:structure',)),
                              help='StructureData node, given by pk or uuid.')

FULL_PROVENANCE = OverridableOption('-fp',
                                    '--full-provenance',
                                    is_flag=True,
                                    default=False,
                                    show_default=True,
                                    help=('Store the full or reduced provenance. Example with the "-as" '
                                          'also the given file will be stored in the database together with a '
                                          'calcfunction extracting the structure.'))

INPGEN = OverridableOption('-inpgen',
                           '--inpgen',
                           type=types.CodeParamType(entry_point='fleur.inpgen'),
                           default=get_inpgen,
                           show_default=True,
                           help='A code node or label for an inpgen executable.')

FLEUR = OverridableOption('-fleur',
                          '--fleur',
                          type=types.CodeParamType(entry_point='fleur.fleur'),
                          default=get_fleur,
                          show_default=True,
                          help='A code node or label for a fleur executable.')

FLEURINP = OverridableOption('-inp',
                             '--fleurinp',
                             type=types.DataParamType(sub_classes=('aiida.data:fleur.fleurinp',)),
                             help='FleurinpData node for the fleur calculation.')

CALC_PARAMETERS = OverridableOption(
    '-cp',
    '--calc-parameters',
    type=types.DataParamType(sub_classes=('aiida.data:dict',)),
    help='Dict with calculation (FLAPW) parameters to build, which will be given to inpgen.')

SETTINGS = OverridableOption('-se',
                             '--settings',
                             type=types.DataParamType(sub_classes=('aiida.data:dict',)),
                             help='Settings node for the calcjob.')

WF_PARAMETERS = OverridableOption('-wp',
                                  '--wf-parameters',
                                  type=types.DataParamType(sub_classes=('aiida.data:dict',)),
                                  help='Dict containing parameters given to the workchain.')

SCF_PARAMETERS = OverridableOption('-sp',
                                   '--scf-parameters',
                                   type=types.DataParamType(sub_classes=('aiida.data:dict',)),
                                   help='Dict containing parameters given to the sub SCF workchains.')

OPTION_NODE = OverridableOption('-on',
                                '--option-node',
                                type=types.DataParamType(sub_classes=('aiida.data:dict',)),
                                help='Dict, an option node for the workchain.')

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
                                          help='The maximum wallclock time in seconds to set for the calculations.')

NUM_MPIPROCS_PER_MACHINE = OverridableOption('-n',
                                             '--num-mpiprocs-per-machine',
                                             type=click.INT,
                                             default=12,
                                             show_default=True,
                                             help='Run the simulation with so many num-mpi-procs-per-machine.')

WITH_MPI = OverridableOption('-i',
                             '--with-mpi',
                             is_flag=True,
                             default=False,
                             show_default=True,
                             help='Run the calculations with MPI enabled.')

REMOTE = OverridableOption('-P',
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
