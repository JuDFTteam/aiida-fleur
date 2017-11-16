#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This contains code snippets and utility useful for dealing with parameter data nodes
commonly used by the fleur plugin and workflows
"""

#from aiida.orm import DataFactory
#from aiida.orm import load_node

#ParameterData = DataFactory('parameter')

def extract_elementpara(parameter_dict, element):
    """
    :param parameter_dict: python dict, parameter node for inpgen
    :param element: string, i.e 'W'

    :return: python dictionary, parameter node which contains only
                                the atom parameters for the given element
    """
    element_para_dict = {}
    for key, val in parameter_dict.iteritems():
        if 'atom' in key:
            if val.get('element', '') == element:
                element_para_dict[key] = val
        else:
            element_para_dict[key] = val
    return element_para_dict


def dict_merger(dict1, dict2):
    """
    Merge rekursively two nested python dictionaries.
    
    If key is in both digionaries tries to add the entries in both dicts.
    (merges two subdicts, adds strings and numbers together)    
    
    :return: dict
    """
    new_dict = dict1.copy()

    if not dict1:
        return dict2
    if not dict2:
        return dict1

    keys1 = dict1.keys()
    keys2 = dict2.keys()

    # add uncommon
    for key in keys2:
        if key not in keys1:
            new_dict[key] = dict2[key]

    # merge common
    for key, val in dict1.iteritems():
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
            print("don't know what to do with element : {}".format(key))
    return new_dict
