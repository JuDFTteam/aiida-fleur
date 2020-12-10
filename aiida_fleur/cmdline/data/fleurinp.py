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
from aiida.cmdline.commands.cmd_data.cmd_list import query, list_options
from aiida.cmdline.params import arguments, options, types
from aiida.cmdline.utils import decorators, echo
from aiida.cmdline.params.types import DataParamType
from aiida.plugins import DataFactory
#from aiida_fleur.data.fleurinp import FleurinpData
from . import cmd_data
FleurinpData = DataFactory('fleur.fleurinp')


@click.group('fleurinp')
def cmd_fleurinp():
    """Commands to handle `FleurinpData` nodes."""


cmd_data.add_command(cmd_fleurinp)


@cmd_fleurinp.command('list')
@list_options  # usual aiida list options
@click.option('--uuid/--no-uuid', default=False, show_default=True, help='Display uuid of nodes.')
@click.option('--ctime/--no-ctime', default=False, show_default=True, help='Display ctime of nodes.')
@click.option('--extras/--no-extras', default=True, show_default=True, help='Display extras of nodes.')
@click.option('--strucinfo/--no-strucinfo',
              default=False,
              show_default=True,
              help='Perpare additional information on the crystal structure to show. This slows down the query.')
@decorators.with_dbenv()
def list_fleurinp(raw, past_days, groups, all_users, strucinfo, uuid, ctime, extras):
    """
    List stored FleurinpData in the database with additional information
    """
    # do a query and list all reuse AiiDA code
    from tabulate import tabulate
    list_project_headers = ['Id', 'Label', 'Description', 'Files']  # these we always get
    # 'UUID', 'Ctime',
    columns_dict = {
        'ID': 'id',
        'Id': 'id',
        'UUID': 'uuid',
        'Ctime': 'ctime',
        'Label': 'label',
        'Description': 'description',
        'Files': 'attributes.files',
        'Extras': 'attributes.extras'
    }

    if uuid:
        list_project_headers.append('UUID')
    if ctime:
        list_project_headers.append('Ctime')
    if extras:
        list_project_headers.append('Extras')

    project = [columns_dict[k] for k in list_project_headers]
    group_pks = None
    if groups is not None:
        group_pks = [g.pk for g in groups]

    data_fleurinp = query(FleurinpData, project, past_days, group_pks, all_users)
    if strucinfo:  # second query
        # we get the whole node to get some extra information
        project2 = '*'
        fleurinps = query(FleurinpData, project2, past_days, group_pks, all_users)
        list_project_headers.append('Formula')
    counter = 0
    fleurinp_list_data = list()

    # , 'Formula', 'Symmetry'
    # It is fastest for list commands to only display content from a query
    if not raw:
        fleurinp_list_data.append(list_project_headers)
    for j, entry in enumerate(data_fleurinp):
        #print(entry)
        for i, value in enumerate(entry):
            if isinstance(value, list):
                new_entry = list()
                for elm in value:
                    if elm is None:
                        new_entry.append('')
                    else:
                        new_entry.append(elm)
                entry[i] = ','.join(new_entry)
        if strucinfo:
            structure = fleurinps[j][0].get_structuredata_ncf()
            formula = structure.get_formula()
            entry.append(formula)
        for i in range(len(entry), len(list_project_headers)):
            entry.append(None)
        counter += 1
    fleurinp_list_data.extend(data_fleurinp)
    if raw:
        echo.echo(tabulate(fleurinp_list_data, tablefmt='plain'))
    else:
        echo.echo(tabulate(fleurinp_list_data, headers='firstrow'))
        echo.echo('\nTotal results: {}\n'.format(counter))


@cmd_fleurinp.command('cat')
@arguments.NODE('node', type=DataParamType(sub_classes=('aiida.data:fleur.fleurinp',)))
@click.option('-f',
              '--filename',
              'filename',
              default='inp.xml',
              show_default=True,
              help='Disply the file content of the given filename.')
def cat_file(node, filename):
    """
    Dumb the content of a file contained in given fleurinpdata, per default dump
    inp.xml
    """
    echo.echo(node.get_content(filename=filename))


'''
@cmd_fleurinp.command('info')
def info():
    """
    Shows some basic information about the fleurinp datastructure and dumbs the
    inp.xml
    """
    click.echo('Not implemented yet, sorry. Please implement me!')


@cmd_fleurinp.command('show')
def cmd_show():
    """
    Shows the content of a certain file
    """
    click.echo('Not implemented yet, sorry. Please implement me!')


@cmd_fleurinp.command('open')
def open_inp():
    """
    opens the inp.xml in some editor, readonly.
    inp.xml this way looking at xml might be more convenient.
    """
    click.echo('Not implemented yet, sorry. Please implement me!')


# this is a maybe
@cmd_fleurinp.command()
def get_structure():
    """
    Prints some basic information about the structure data and return a structure uuid/pk
    """
    click.echo('Not implemented yet, sorry. Please implement me!')


@cmd_fleurinp.command()
def get_kpoints():
    """
    Prints some basic information about the kpoints data and returns a kpoints uuid/pk
    """
    click.echo('Not implemented yet, sorry. Please implement me!')


@cmd_fleurinp.command()
def get_parameters():
    """
    Prints some basic information about the parameter data and returns a
    parameter data uuid/pk
    """
    click.echo('Not implemented yet, sorry. Please implement me!')
'''
