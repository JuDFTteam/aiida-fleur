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
    
    
    

def dict_merger(dict1, dict2):
    """
    Merges rekursively two similar python dictionaries
    if key is in both digionaries tries to add the entries in both dicts.
    (merges two subdicts, adds strings and numbers together)
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
    
    
# test
'''
n_atom_types_Be12Ti = {'Ti' : [1], 'Be' : [4,4,4]}
n_atom_types_Be17Ti2 = {'Ti' : [2], 'Be' : [2,3,6,6]}
coreleveldict_Be17Ti2 = {u'Be': {'1s' : [-0.4789944497390507, -1.033711196166693, 
                                         -0.8176212667771887, -0.9725706485778098]}, 
                      u'Ti': {#'1s': [0.1593478601692393], 
                              #'2s': [0.1489621122363048], 
                              '2p1/2' : [0.1500901275901426], 
                              '2p3/2' : [0.149911337899338]}}

dict_merger(n_atom_types_Be12Ti, n_atom_types_Be17Ti2)
->{'Be': [4, 4, 4, 2, 3, 6, 6], 'Ti': [1, 2]}

dict_merger(coreleveldict_Be17Ti2, coreleveldict_Be17Ti2)
->{u'Be': {'1s': [-0.4789944497390507,
   -1.033711196166693,
   -0.8176212667771887,
   -0.9725706485778098,
   -0.4789944497390507,
   -1.033711196166693,
   -0.8176212667771887,
   -0.9725706485778098]},
 u'Ti': {'2p1/2': [0.1500901275901426, 0.1500901275901426],
  '2p3/2': [0.149911337899338, 0.149911337899338]}}
  
dict1 = {'a' : 1}
dict2 = {'b' : 2}
dict_merger(dict1, dict2)
->{'a': 1, 'b': 2}
'''