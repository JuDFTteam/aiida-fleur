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
This contains functions to generate certain node content, mostly dictionaries
with defaults.
These functions are usefull to expose one the commandline and to have defaults in one place
'''
# Todo: some of these can be moved to aiida-jutools
# since for kkr they might be the same
#todo, we allow kwargs for the nodes, maybe they should be validated
from aiida import orm
from aiida.plugins import WorkflowFactory
from aiida.orm import QueryBuilder


def generate_wf_option_node(computer=None, check_existence=True, **kwargs):
    """Create a option node for a certain workflow or calculation entry point.

    :param wf_entry_point: string the entry point to create the node for, default='fleur.scf'
    :param computer: dict {computername, queue} to provide computer dependend defaults
    :param kwargs: dict, further key word argument by which the node content will be updated

    :returns: AiiDA Dict node
    """
    option_node_dict = generate_wf_option_dict(computer=computer, **kwargs)
    option_node = orm.Dict(dict=option_node_dict)
    if check_existence:
        duplicate = QueryBuilder().append(orm.Dict, filters={'extras._aiida_hash': option_node._get_hash()}).first()  # pylint: disable=protected-access
    if duplicate:
        option_node = duplicate[0]

    return option_node


def generate_wf_option_dict(computer=None, protocol_file=None, **kwargs):
    """Create a option dict for a certain workflow or calculation entry point.

    :param computer: dict {computername, queue} to provide computer dependend defaults
    :param kwargs: dict, further key word argument by which the node content will be updated
    :param protocol_file: str, path to json file containing a set of default options

    :returns: python dict
    """
    # options usually do not differe between workflows, but depend on system size and machine.
    # Also per project, therefore it would be nice to allow to provide a file and with a set of defaults.
    # and this function should read them
    from aiida_fleur.common.defaults import default_options

    default_wf_dict = default_options.deepcopy()
    #todo better rekursive merge?
    default_wf_dict.update(kwargs)

    return default_wf_dict


def generate_wf_para_dict(wf_entry_point='fleur.scf', **kwargs):
    """Create a wf parameter dict for a certain workflow or calculation entry point.

    :param wf_entry_point: string the entry point to create the node for, default='fleur.scf'
    :param kwargs: dict, further key word argument by which the node content will be updated

    :returns: python dict
    """

    wf = WorkflowFactory(wf_entry_point)
    default_wf_dict = wf._default_wf_para
    #todo better rekursive merge?
    default_wf_dict.update(kwargs)

    return default_wf_dict


def generate_wf_para_node(wf_entry_point='fleur.scf', check_existence=True, **kwargs):
    """Create a wf parameter node for a certain workflow or calculation entry point.

    :param wf_entry_point: string the entry point to create the node for, default='fleur.scf'
    :param kwargs: dict, further key word argument by which the node content will be updated

    :returns: AiiDA Dict node
    """
    wf_para_node_dict = generate_wf_para_dict(wf_entry_point=wf_entry_point, check_existence=check_existence, **kwargs)
    wf_para_node = orm.Dict(dict=wf_para_node_dict)
    if check_existence:
        duplicate = QueryBuilder().append(orm.Dict, filters={'extras._aiida_hash': wf_para_node._get_hash()}).first()  # pylint: disable=protected-access
    if duplicate:
        wf_para_node = duplicate[0]

    return wf_para_node
