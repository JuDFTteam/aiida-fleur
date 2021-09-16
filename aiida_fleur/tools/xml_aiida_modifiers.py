# -*- coding: utf-8 -*-
"""
This module defines XML modifying functions, that require an aiida node as input
"""


def set_kpointsdata_f(xmltree, schema_dict, kpointsdata_uuid, name=None, switch=False):
    """This calc function writes all kpoints from a :class:`~aiida.orm.KpointsData` node
    in the ``inp.xml`` file as a kpointslist. It replaces kpoints written in the
    ``inp.xml`` file. Currently it is the users responsibility to provide a full
    :class:`~aiida.orm.KpointsData` node with weights.

    :param fleurinp_tree_copy: fleurinp_tree_copy
    :param kpointsdata_uuid: node identifier or :class:`~aiida.orm.KpointsData` node to be written into ``inp.xml``
    :return: modified xml tree
    """
    # TODO: check on weights,
    # also fleur allows for several kpoint sets, lists, paths and meshes,
    # support this.
    import numpy as np
    from aiida.orm import KpointsData, load_node
    from aiida.common.exceptions import InputValidationError
    from masci_tools.util.xml.xml_setters_names import set_kpointlist

    if not isinstance(kpointsdata_uuid, KpointsData):
        KpointsDataNode = load_node(kpointsdata_uuid)
    else:
        KpointsDataNode = kpointsdata_uuid

    if not isinstance(KpointsDataNode, KpointsData):
        raise InputValidationError('The node given is not a valid KpointsData node.')

    try:
        kpoints, weights = KpointsDataNode.get_kpoints(also_weights=True, cartesian=False)
    except AttributeError:
        kpoints = KpointsDataNode.get_kpoints(cartesian=False)
        weights = np.ones(len(kpoints)) / len(kpoints)

    labels = KpointsDataNode.labels

    labels_dict = None
    if labels is not None:
        labels_dict = dict(labels)

    try:
        KpointsDataNode.get_kpoints_mesh()
        kpoint_type = 'mesh'
    except AttributeError:
        kpoint_type = 'path'

    if schema_dict.inp_version <= (0, 31):
        xmltree = set_kpointlist(xmltree, schema_dict, kpoints, weights)
    else:
        xmltree = set_kpointlist(xmltree,
                                 schema_dict,
                                 kpoints,
                                 weights,
                                 special_labels=labels_dict,
                                 kpoint_type=kpoint_type,
                                 name=name,
                                 switch=switch)

    return xmltree


FLEURINPMODIFIER_EXTRA_FUNCS = {'schema_dict': {'set_kpointsdata': set_kpointsdata_f}}
