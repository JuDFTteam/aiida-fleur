#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module, contains a method to merge parameterData nodes used by the FLEUR inpgen.
This might also be of interest for other all-ellectron codes
"""
# TODO this should be made an inline calculation or workfunction to
# keep the proverance!
# Shall we allow for a python dictionary also instead of forcing paramteraData?
# but then we can not keep the provenace...

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys,os

from aiida.orm import Code, CalculationFactory, DataFactory
from aiida.orm import load_node
from aiida.orm.data.base import Bool
from aiida.work import workfunction as wf

ParameterData = DataFactory('parameter')

def merge_parameter(ParameterData1, ParameterData2, overwrite=True):
    """
    Merges two parameterData nodes.
    Additive: uses all namelists of both.
    If they have a namelist in common. ParameterData2 will overwrite the namelist
    of parameterData. If this is not wanted. set overwrite = False.
    Then attributes of both will be added, but attributes from ParameterData1 won't
    be oeverwritten.


    param: AiiDA ParamterData Node
    param: AiiDA ParamterData Node

    returns: AiiDA ParamterData Node
    """

    # layout:
    # check input
    # get dictionaries
    # merge dictionaries into new dictionary
    # create a new parameterData node

    new_dict = {}
    atoms_dict = {}
    atomlist = []
    if not isinstance(ParameterData1, ParameterData):
        raise InputValidationError("ParameterData1, must be of "
                                           "type ParameterData")
    if not isinstance(ParameterData2, ParameterData):
        raise InputValidationError("ParameterData2, must be of "
                                           "type ParameterData")
    dict1 = ParameterData1.get_dict()
    dict2 = ParameterData2.get_dict()

    print dict1.keys()
    for key in dict1.keys():
        if 'atom' in key:
            val = dict1.pop(key)
            atomlist.append(val)

    for key in dict2.keys():
        if 'atom' in key:
            val = dict2.pop(key)
            atomlist.append(val)


    # TODO do something on atom list,
    # we dont want doubles, check element and Id? Keep first ones?

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
        new_dict.update(dict1)
        # TODO or do we want to merge the value dicts? usually does not make sense
        # for all keys...
    new_dict.update(atoms_dict)

    # be carefull with atom namelist


    return ParameterData(dict=new_dict)


def merge_parameters(ParameterDataList, overwrite=True):
    """
    Merge together all parameter nodes in the given list.
    """
    paremeter_data_new = ParameterData(dict= {})

    for i, parameter in enumerate(ParameterDataList):
        if isinstance(parameter, ParameterData):
            # merge
            paremeter_data_new = merge_parameter(paremeter_data_new, parameter, overwrite=overwrite)
        else:
            print 'Entry : {} {} is not of type ParameterData, I skip it.'.format(i, parameter)

    return paremeter_data_new

@wf
def merge_parameter_wf(ParameterData1, ParameterData2, overwrite=Bool(True)):
    """
    workfunction of merge_parameters
    """
    paremeter_data_new = merge_parameter(ParameterData1, ParameterData2, overwrite=overwrite)

    return paremeter_data_new

'''
# TODO how to deal with a list? *args, prob is not the best, also it is not working here.
# makeing a methds m(self, *args, **kwargs) and setting some fallbacks, does not work, because self, cannot be parsed
# I guess...
@wf
def merge_parameters_wf(*ParameterDatas, overwrite=Bool(True)):
    """
    workfunction of merge_parameters
    """
    ParameterDataList = []
    for parameter in ParameterDatas:
        ParameterDataList.append(parameter)
    paremeter_data_new = merge_parameters(ParameterDataList, overwrite=overwrite)

    return paremeter_data_new
'''
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Merge a parameterData node.')
    parser.add_argument('--para1', type=ParameterData, dest='para1',
                        help='The first ParameterData node', required=True)
    parser.add_argument('--para2', type=ParameterData, dest='para2',
                        help='The second ParameterData node', required=True)
    parser.add_argument('--overwrite', type=bool, dest='overwrite',
                        help='Shall values given in ParameterData2 overwrite the values from the first ParameterData?', required=False)
    args = parser.parse_args()
    merge_parameter(paremeter_data_new=args.para1, parameter=args.para1, overwrite=args.overwrite)
