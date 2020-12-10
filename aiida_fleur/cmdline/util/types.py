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
This module contains click option types specific to aiida-fleur
'''
import click
from aiida.cmdline.params import types
from aiida.cmdline.utils import echo
from aiida.common.exceptions import NotExistent
from aiida.plugins import DataFactory
from aiida.cmdline.utils.decorators import with_dbenv


class StructureNodeOrFileParamType(click.ParamType):
    """
    The ParamType for identifying a structure by node or to extract it from a given file

    Pro: It is convenient
    Con: If users only use other formats to launch their workflows it will create many
    more structures in the database.
    """

    name = 'StructureFile'

    @with_dbenv()
    def convert(self, value, param, ctx):
        is_path = False
        # Alternative one could check if int or uuid
        # aiida allows also for shorten uuids
        from aiida.orm import StructureData, QueryBuilder

        try:
            structure = types.DataParamType(sub_classes=('aiida.data:structure',)).convert(value, param, ctx)
        except (NotExistent, click.exceptions.BadParameter) as er:
            echo.echo(f'Tried to load node, could not fine one for {value}. '
                      'I will further check if it is a filepath.')
            is_path = True

        if is_path:
            # If it is a path to a file try to convert the structure
            pathtype = click.Path(exists=True, dir_okay=False, resolve_path=True)
            filename = pathtype.convert(value, param, ctx)
            try:
                import ase.io
            except ImportError:
                echo.echo_critical('You have not installed the package ase. \nYou can install it with: pip install ase')

            try:
                asecell = ase.io.read(filename)
                structure = StructureData(ase=asecell)
            except ValueError as err:
                echo.echo_critical(str(err))
            # do not store structure, since this option is for calculation and workflow
            # input, which will store the structure anyway.

        # do not store again if structure is already there.
        duplicate = QueryBuilder().append(StructureData, filters={'extras._aiida_hash': structure._get_hash()}).first()  # pylint: disable=protected-access

        if duplicate:
            return duplicate[0]
        return structure
