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
This module contains useful function to extract data from nodes,
specific to aiida-fleur. Any useful code snipets for handling large number of
nodes, or data-mine go in here
"""

#import time
from __future__ import absolute_import
from aiida.plugins import DataFactory
from aiida.orm.querybuilder import QueryBuilder as QB


def extract_structure_info(keys, structures=None):
    """
    A method that collects a bunch of information (specified in keys) from
    structures (default whole db, or provided node list) in the database and
    returns that information as a dict, which could be used for further evalation
    #keys = ['uuid', 'formula', 'pk', 'symmetry', 'pbc', 'volume', 'total_energy',
    'child_nodes', 'natoms', 'group', extras', 'label', 'description', 'cif_file',
    'cif_number', 'cif_uuid', 'cif_ref', 'calcfunctions', 'band', 'dos', 'eos',
    'init_cls', 'corehole', primitive]

    """
    StructureData = DataFactory('structure')
    structure_list = []

    from aiida_fleur.tools.StructureData_util import get_spacegroup, is_structure
    from aiida_fleur.tools.StructureData_util import is_primitive

    if not structures:
        StructureData = DataFactory('structure')
        #t = time.time()
        qb = QB()
        qb.append(StructureData)
        structures = qb.all()
        #elapsed = time.time() - t
        # print "Total number of structures: {} (retrieved in {} s.)".format(len(structures), elapsed)
        #t = time.time()

    # for structure in structures:
    #    structure_dict = {}
    #    struc = structure[0]
    #    for key in keys:
    #        structure_dict[key] = get_methods(key)(struc)

    # get information
    for structure in structures:
        structure_dict = {}

        if isinstance(structure, list):
            struc = structure[0]
        else:
            struc = is_structure(structure)

        if 'formula' in keys:
            structure_dict['formula'] = struc.get_formula()
        if 'pk' in keys:
            structure_dict['pk'] = struc.pk
        if 'uuid' in keys:
            structure_dict['uuid'] = str(struc.uuid)
        if 'natoms' in keys:
            structure_dict['natoms'] = len(struc.sites)
        if 'cell' in keys:
            structure_dict['cell'] = str(struc.cell)
        if 'pbc' in keys:
            structure_dict['pbc'] = str(struc.pbc)
        if 'label' in keys:
            structure_dict['label'] = struc.label
        if 'description' in keys:
            structure_dict['description'] = struc.description
        if 'extras' in keys:
            extras = struc.extras
            structure_dict['extras'] = str(extras)
        if 'symmetry' in keys:
            symmetry = get_spacegroup(struc)
            structure_dict['symmetry'] = str(symmetry)
        if 'volume' in keys:
            volume = struc.get_cell_volume()
            structure_dict['volume'] = volume
        if 'child_nodes' in keys:
            child_nodes = len(struc.get_outgoing().all())
            structure_dict['child_nodes'] = child_nodes
        if 'primitive' in keys:
            prim = is_primitive(struc)
            structure_dict['primitive'] = prim

        if 'cif_file' in keys:
            cif_file = get_cif_file(struc)
            structure_dict['cif_file'] = cif_file
        '''
        if 'cif_number' in keys:
            cif_number = get_cif_number(struc)
            structure_dict['cif_number'] = cif_number
        if 'cif_uuid' in keys:
            cif_uuid = get_cif_uuid(struc)
            structure_dict['cif_uuid'] = cif_uuid
        if 'cif_ref' in keys:
            cif_ref = get_cif_ref(struc)
            structure_dict['cif_ref'] = cif_ref
        if 'total_energy' in keys:
            total_energy = get_total_energy(struc)
            structure_dict['total_energy'] = total_energy
        '''
        if 'group' in keys:
            group = group_member(struc)
            structure_dict['group'] = group
        if 'scf' in keys:
            scf = input_of_workcal('fleur_scf_wc', struc)
            structure_dict['scf'] = scf
        if 'band' in keys:
            band = input_of_workcal('fleur_band_wc', struc)
            structure_dict['band'] = band
        if 'dos' in keys:
            dos = input_of_workcal('fleur_dos_wc', struc)
            structure_dict['dos'] = dos
        if 'eos' in keys:
            eos = input_of_workcal('fleur_eos_wc', struc)
            structure_dict['eos'] = eos
        if 'init_cls' in keys:
            init_cls = input_of_workcal('fleur_initial_cls_wc', struc)
            structure_dict['init_cls'] = init_cls
        if 'corehole' in keys:
            corehole = input_of_workcal('fleur_corehole_wc', struc)
            structure_dict['corehole'] = corehole
        if 'calcfunctions' in keys:
            calcfunctions_uuid, calcfunctions_name = input_of_calcfunctions(struc)
            structure_dict['calcfunctions'] = [calcfunctions_uuid, calcfunctions_name]

        structure_list.append(structure_dict)

    #elapsed = time.time() - t
    # print "(needed {} s.!!!)".format(elapsed)

    return structure_list


def group_member(node):
    """
    Find to what groups a node belongs to.

    Comment: currently very greedy!
    """
    from aiida.orm import Group
    member_in = []
    # get all groups in db
    # for each group check if node is member of group
    # append group name to member_in

    res = Group.objects.all()
    for group in res:
        name = group.label
        for gnode in group.nodes:  # TODO: easier/better way?
            if gnode.uuid == node.uuid:
                member_in.append(name)
    return member_in


def input_of_workcal(name, node):
    """
    checks if a given node was input into a certain WorkChain
    and returns a list of workcalculation uuids of workcalculations with the given name
    """
    from aiida.orm import WorkChainNode
    process_uuids = []
    for out in node.get_outgoing().all_nodes():
        if isinstance(out, WorkChainNode):
            label = out.get_attribute('process_label')
            if label == name:
                process_uuids.append(out.uuid)
    return process_uuids


def input_of_calcfunctions(node, name=''):
    """
    checks if a given node was input into a certain calcfunction
    and returns a list of calcfunction uuids of calcfunction with the given name
    """
    from aiida.orm import CalcFunctionNode
    process_uuids = []
    process_names = []
    outputs = node.get_outgoing().all_nodes()
    for out in outputs:
        if isinstance(out, CalcFunctionNode):
            try:  # TODO: is there a better way
                label = out.get_attribute('process_label')
            except AttributeError:
                label = None
                continue
            if label == name:
                process_uuids.append(out.uuid)
                process_names.append(label)
            if not name:
                process_uuids.append(out.uuid)
                process_names.append(label)
    return process_uuids, process_names


def get_cif_file(node):
    """
    Finds out if (a structure) given as input was created from a cif file
    currently with the method wf_struc_from_cif

    params: node: structureData node
    returns [cif_filename, cif_uuid]
    """
    from aiida.orm import CifData, CalcFunctionNode
    inputs = node.get_incoming().all_nodes()
    name = 'wf_struc_from_cif'  # TODO: Bad solution, not general for me currently enough
    cif_uuid, cif_filename = '', ''
    for inp in inputs:
        if isinstance(inp, CalcFunctionNode):
            try:  # TODO: is there a better way
                label = inp.get_attribute('process_label')
            except AttributeError:
                label = None
                continue
            if label == name:
                inp_wc = inp.get_incoming().all_nodes()
                for iwc in inp_wc:
                    if isinstance(iwc, CifData):
                        cif_uuid = iwc.uuid
                        cif_filename = iwc.filename
                        break

    return [cif_filename, cif_uuid]


# wf_struc_from_cif process_label
# cif.filename
# cif.uuid
# cif.folder.abspath
# wc.get_incoming().all()
