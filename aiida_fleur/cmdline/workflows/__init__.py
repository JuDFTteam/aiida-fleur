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
from aiida.cmdline.params.types import ProcessParamType
from aiida.cmdline.params import arguments, options
from aiida.cmdline.utils import decorators, echo
from aiida import orm
from aiida_fleur.cmdline.util import options as options_fl


@click.group('workflow')
def cmd_workflow():
    """Commands to inspect aiida-fleur workchains."""


# general further commands for fleur workchains


@cmd_workflow.command('res')
@arguments.PROCESS('process', type=ProcessParamType()
                   )  #, type=WorkflowParamType(sub_classes=('aiida.node:process.workflow.workchain',)))
@click.option('--info/--no-info', default=False, help='Print an info header above each node.')
@click.option('-l', '--label', 'label', type=str, help='Print only output dicts with a certain link_label.')
@options_fl.SHOW()
@options.DICT_KEYS()
@options.DICT_FORMAT()
@decorators.with_dbenv()
def workchain_res(process, info, label, show, keys, fmt):
    """Print data from Dict nodes returned or created by any fleur process."""

    returned_dicts_info = []
    returned_dicts = []
    try:
        results = process.get_outgoing().all()
    except ValueError as exception:
        echo.echo_critical(str(exception))
    for result in results:
        if isinstance(result.node, orm.Dict):
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
@options_fl.SHOW()
@options.DICT_KEYS()
@options.DICT_FORMAT()
@decorators.with_dbenv()
def workchain_inputdict(process, info, label, show, keys, fmt):
    """Print data from Dict nodes input into any fleur process."""
    from aiida.orm import Dict

    returned_dicts_info = []
    returned_dicts = []
    try:
        results = process.get_incoming().all()
    except ValueError as exception:
        echo.echo_critical(str(exception))
    for result in results:
        if isinstance(result.node, orm.Dict):
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
        if show:
            echo.echo_dictionary(result, fmt=fmt)


'''
@cmd_workflow.command('gen_wf_para')
@arguments.ENTRYPOINTSTR('entrypoint', default='fleur.scf')
@options.SHOW()
@options.STORE()
@options.CHECK_EXISTENCE()
@options.KWARGS()
@decorators.with_dbenv()
def gen_wf_para_cmd(entrypoint, show, store, check_existence, kwargs):
    """
    Generates a default parameter wf parameter node for given entrypoint.
    """
    from aiida_fleur.tools.node_generators import generate_wf_para_node
    from aiida.plugins import entry_point
    try:
        wf = entry_point.load_entry_point('aiida.workflows', prefix)
    except ValueError:
        echo.echo('here1')
    try:
        wf = entry_point.load_entry_point('aiida.calculations', prefix)
    except ValueError:
        echo.echo('here1')

    wf_para = generate_wf_para_node(entrypoint=entrypoint, **kwargs)
    if store:
        wf_para.store()
        echo.echo('Created wf para node')
    else:
        echo.echo('Created wf para node')
    if show:
        echo.echo_dictionary(wf.para.get_dict())



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
