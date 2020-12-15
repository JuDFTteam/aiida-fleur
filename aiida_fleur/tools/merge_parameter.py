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
This module, contains a method to merge Dict nodes used by the FLEUR inpgen.
This might also be of interest for other all-electron codes
"""
# Shall we allow for a python dictionary also instead of forcing paramteraData?
# but then we can not keep the provenace...

from __future__ import absolute_import
from __future__ import print_function

from aiida.plugins import DataFactory
from aiida.orm import Bool, Dict
from aiida.engine import calcfunction as cf
#Dict = DataFactory('dict')


def merge_parameter(Dict1, Dict2, overwrite=True, merge=True):
    """
    Merges two Dict nodes.
    Additive: uses all namelists of both.
    If they have a namelist in common. Dict2 will overwrite the namelist
    of Dict. If this is not wanted. set overwrite = False.
    Then attributes of both will be added, but attributes from Dict1 won't
    be overwritten.


    :param Dict1: AiiDA Dict Node
    :param Dict2: AiiDA Dict Node
    :param overwrite: bool, default True
    :param merge: bool, default True

    returns: AiiDA Dict Node

    #TODO be more carefull how to merge ids in atom namelists, i.e species labels
    """

    from aiida.common.exceptions import InputValidationError
    from aiida_fleur.tools.dict_util import recursive_merge
    #Dict = DataFactory('dict')

    # layout:
    # check input
    # get dictionaries
    # merge dictionaries into new dictionary
    # create a new Dict node

    new_dict = {}
    atoms_dict = {}
    atomlist = []
    if not isinstance(Dict1, Dict):
        raise InputValidationError('Dict1, must be of ' 'type Dict')
    if not isinstance(Dict2, Dict):
        raise InputValidationError('Dict2, must be of ' 'type Dict')
    dict1 = Dict1.get_dict()
    dict2 = Dict2.get_dict()

    if dict1 == dict2:
        return Dict(dict=dict1)

    for key in list(dict1.keys()):
        if 'atom' in key:
            val = dict1.pop(key)
            atomlist.append(val)

    for key in list(dict2.keys()):
        if 'atom' in key:
            val = dict2.pop(key)
            atomlist.append(val)

    # TODO do something on atom list,
    # we do not want doubles, check element and Id? Keep first ones?

    for i, atom in enumerate(atomlist):
        # TODO check for duplicates? what about
        key = 'atom{}'.format(i)
        atoms_dict[key] = atom

    # merge all namelists except atoms
    if overwrite:
        new_dict = dict1.copy()
        new_dict.update(dict2)
    else:
        # add second one later?
        new_dict = dict2.copy()
        if merge:
            new_dict = recursive_merge(new_dict, dict1)
        else:
            new_dict.update(dict1)
        # TODO mergeing does not make sense for all namelist keys.
        # be more specific here.
    new_dict.update(atoms_dict)

    # be carefull with atom namelist

    return Dict(dict=new_dict)


def merge_parameters(DictList, overwrite=True):
    """
    Merge together all parameter nodes in the given list.
    """
    #Dict = DataFactory('dict')
    paremeter_data_new = Dict(dict={})

    for i, parameter in enumerate(DictList):
        if isinstance(parameter, Dict):
            # merge
            paremeter_data_new = merge_parameter(paremeter_data_new, parameter, overwrite=overwrite)
        else:
            print(('WARNING: Entry : {} {} is not of type Dict, I skip it.'.format(i, parameter)))

    return paremeter_data_new


@cf
def merge_parameter_cf(Dict1, Dict2, overwrite=None):
    """
    calcfunction of merge_parameters
    """
    if overwrite is None:
        overwrite = Bool(True)
    paremeter_data_new = merge_parameter(Dict1, Dict2, overwrite=overwrite)

    return paremeter_data_new


'''
# TODO how to deal with a list? *args, prob is not the best, also it is not working here.
# makeing a methods m(self, *args, **kwargs) and setting some fallbacks, does not work, because self, cannot be parsed
# I guess...
@cf
def merge_parameters_wf(*Dicts, overwrite=Bool(True)):
    """
    calcfunction of merge_parameters
    """
    DictList = []
    for parameter in Dicts:
        DictList.append(parameter)
    paremeter_data_new = merge_parameters(DictList, overwrite=overwrite)

    return paremeter_data_new
'''
'''
#TODO this has to moved into cmdline
if __name__ == '__main__':
    import argparse
    #Dict = DataFactory('dict')

    parser = argparse.ArgumentParser(description='Merge a Dict node.')
    parser.add_argument('--para1', type=Dict, dest='para1', help='The first Dict node', required=True)
    parser.add_argument('--para2', type=Dict, dest='para2', help='The second Dict node', required=True)
    parser.add_argument('--overwrite',
                        type=bool,
                        dest='overwrite',
                        help='Shall values given in Dict2 overwrite the values from the first Dict?',
                        required=False)
    args = parser.parse_args()
    merge_parameter(Dict1=args.para1, Dict2=args.para1, overwrite=args.overwrite)
    '''
