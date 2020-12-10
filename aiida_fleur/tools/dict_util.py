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
This contains code snippets and utility useful for dealing with parameter data nodes
commonly used by the fleur plugin and workflows
"""
from __future__ import print_function
from __future__ import absolute_import
import six
import typing as typ
import collections


def extract_elementpara(parameter_dict, element):
    """
    :param parameter_dict: python dict, parameter node for inpgen
    :param element: string, i.e 'W'

    :return: python dictionary, parameter node which contains only
                                the atom parameters for the given element
    """
    element_para_dict = {}
    for key, val in six.iteritems(parameter_dict):
        if 'atom' in key:
            if val.get('element', '') == element:
                element_para_dict[key] = val
        else:
            element_para_dict[key] = val
    return element_para_dict


def dict_merger(dict1, dict2):
    """
    Merge recursively two nested python dictionaries and
    if key is in both digionaries tries to add the entries in both dicts.
    (merges two subdicts, adds lists, strings, floats and numbers together!)

    :param dict1: dict
    :param dict2: dict

    :return dict: Merged dict
    """
    new_dict = dict1.copy()

    if not dict1:
        return dict2
    if not dict2:
        return dict1

    keys1 = list(dict1.keys())
    keys2 = list(dict2.keys())

    # add uncommon
    for key in keys2:
        if key not in keys1:
            new_dict[key] = dict2[key]

    # merge common
    for key, val in six.iteritems(dict1):
        if isinstance(val, dict):
            new_dict[key] = dict_merger(val, dict2.get(key, {}))
        elif isinstance(val, list):
            new_dict[key] = val + dict2.get(key, [])
        elif isinstance(val, str):
            new_dict[key] = val + dict2.get(key, '')
        elif isinstance(val, int):
            new_dict[key] = val + dict2.get(key, 0)
        elif isinstance(val, float):
            new_dict[key] = val + dict2.get(key, 0.0)
        else:
            print(("don't know what to do with element : {}".format(key)))
    return new_dict


def clean_nones(dict_to_clean):
    """Recursively remove all keys which values are None from a nested dictionary
    return the cleaned dictionary

    :param dict_to_clean: (dict): python dictionary to remove keys with None as value
    :return: dict, cleaned dictionary
    """
    new_dict = {}
    for key, val in dict_to_clean.items():
        if isinstance(val, dict):
            new_val = clean_nones(val)
        else:
            new_val = val
        if new_val is not None:  # currently we keep empty dicts
            new_dict[key] = new_val

    return new_dict


def recursive_merge(left: typ.Dict[str, typ.Any], right: typ.Dict[str, typ.Any]) -> typ.Dict[str, typ.Any]:
    """
    Recursively merge two dictionaries into a single dictionary.

    keys in right override keys in left!


    :param left: first dictionary.
    :param right: second dictionary.
    :return: the recursively merged dictionary.
    """
    for key, value in left.items():
        if key in right:
            if isinstance(value, collections.Mapping) and isinstance(right[key], collections.Mapping):
                right[key] = recursive_merge(value, right[key])

    merged = left.copy()
    merged.update(right)

    return merged
