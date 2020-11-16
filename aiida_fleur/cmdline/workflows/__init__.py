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
Module with CLI commands to launch and inspect various aiida-fleur workchains.
"""
import click
from .. import cmd_root
from aiida.cmdline.params.types import ProcessParamType
from aiida.cmdline.params import arguments, options
from aiida.cmdline.utils import decorators, echo


@cmd_root.group('workflow')
def cmd_workflow():
    """Commands to inspect aiida-fleur workchains."""


# Import the sub commands to register them with the CLI
#from .scf import cmd_scf
#from .relax import cmd_relax
#from .banddos import cmd_banddos
#from .eos import cmd_eos
#from .corehole import cmd_corehole
#from .initial_cls import cmd_initial_cls

#from .dmi import cmd_dmi
#from .mae import cmd_mae
#from .ssdisp import cmd_ssdisp

# general further commands for fleur workchains


@cmd_workflow.command('res')
@arguments.PROCESS('process', type=ProcessParamType()
                   )  #, type=WorkflowParamType(sub_classes=('aiida.node:process.workflow.workchain',)))
@click.option('--info/--no-info', default=False, help='Print an info header above each node.')
@click.option('-l', '--label', 'label', type=str, help='Print only output dicts with a certain link_label.')
@options.DICT_KEYS()
@options.DICT_FORMAT()
@decorators.with_dbenv()
def workchain_res(process, fmt, keys, label, info):
    """Print data from Dict nodes returned or created by any fleur process."""
    #from aiida.cmdline.utils.echo import echo_dictionary
    from aiida.orm import Dict

    returned_dicts_info = []
    returned_dicts = []
    try:
        results = process.get_outgoing().all()
    except ValueError as exception:
        echo.echo_critical(str(exception))
    for result in results:
        if isinstance(result.node, Dict):
            if label is not None:
                if label == result.link_label:
                    returned_dicts.append(result.node.get_dict())
                    returned_dicts_info.append(result)
            else:
                returned_dicts.append(result.node.get_dict())
                returned_dicts_info.append(result)

    for i, re_dict in enumerate(returned_dicts):
        if keys is not None:
            try:
                result = {k: re_dict[k] for k in keys}
            except KeyError as exc:
                echo.echo_critical("key '{}' was not found in the results dictionary".format(exc.args[0]))
        else:
            result = re_dict
        if info:
            echo.echo('# Info: {} {} dict:'.format(returned_dicts_info[i].link_label, returned_dicts_info[i].node))
        echo.echo_dictionary(result, fmt=fmt)


@cmd_workflow.command('inputdict')
@arguments.PROCESS('process', type=ProcessParamType()
                   )  #, type=WorkflowParamType(sub_classes=('aiida.node:process.workflow.workchain',)))
@click.option('--info/--no-info', default=False, help='Print an info header above each node.')
@click.option('-l', '--label', 'label', type=str, help='Print only output dicts with a certain link_label.')
@options.DICT_KEYS()
@options.DICT_FORMAT()
@decorators.with_dbenv()
def workchain_inputdict(process, fmt, keys, label, info):
    """Print data from Dict nodes inputed into any fleur process."""
    #from aiida.cmdline.utils.echo import echo_dictionary
    from aiida.orm import Dict

    returned_dicts_info = []
    returned_dicts = []
    try:
        results = process.get_incoming().all()
    except ValueError as exception:
        echo.echo_critical(str(exception))
    for result in results:
        if isinstance(result.node, Dict):
            if label is not None:
                if label == result.link_label:
                    returned_dicts.append(result.node.get_dict())
                    returned_dicts_info.append(result)
            else:
                returned_dicts.append(result.node.get_dict())
                returned_dicts_info.append(result)

    for i, re_dict in enumerate(returned_dicts):
        if keys is not None:
            try:
                result = {k: re_dict[k] for k in keys}
            except KeyError as exc:
                echo.echo_critical("key '{}' was not found in the results dictionary".format(exc.args[0]))
        else:
            result = re_dict
        if info:
            echo.echo('# Info: {} {} dict:'.format(returned_dicts_info[i].link_label, returned_dicts_info[i].node))
        echo.echo_dictionary(result, fmt=fmt)


'''
@cmd_workflow.command('inputls')
def inputls_wc():
    """
    Prints verdi node show for all workchain inputs.
    """
    click.echo('verdi aiida-fleur scf res')

@cmd_workflow.command('show')
def show_wc():
    """
    Shows the node ans structure of a workchain.
    Similar to verdi node show
    """
    click.echo('verdi aiida-fleur scf show')


@cmd_workflow.command('list')
def list_wc():
    """
    Similar to the verdi process list command, but this has preset filters and
    displays also some specific information about fleur workchains
    """
    click.echo('verdi aiida-fleur scf list')
'''
