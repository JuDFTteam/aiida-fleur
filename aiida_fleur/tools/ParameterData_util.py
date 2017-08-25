#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This contains code snippets and utility useful for dealing with parameter data nodes
commonly used by the fleur plugin and workflows
"""

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

#from aiida.orm import DataFactory
#from aiida.orm import load_node


#ParameterData = DataFactory('parameter')

def extract_elementpara(parameter_dict, element):
    """
    params: parameter_dict: python dict, parameter node for inpgen
    params: element: string, i.e 'W'
    
    returns: python dictionary, parameter node which contains only 
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