"""
This module defines XML modifying functions, that require an aiida node as input
"""


def set_kpointsdata_f(xmltree, schema_dict, kpointsdata_uuid, name=None, switch=False, kpoint_type='path'):
    """This function creates a kpoint list in the inp.xml from a :py:class:`~aiida.orm.KpointsData` Node
    If no weights are given the weight is distibuted equally along the kpoints

    :param xmltree: an xmltree that represents inp.xml
    :param schema_dict: InputSchemaDict containing all information about the structure of the input
    :param kpointsdata_uuid: node identifier or :class:`~aiida.orm.KpointsData` node to be written into ``inp.xml``
    :param name: str name to give the newly entered kpoint list (only MaX5 or later)
    :param switch: bool if True the entered kpoint list will be used directly (only Max5 or later)
    :param kpoint_type: str of the type of kpoint list given (mesh, path, etc.) only Max5 or later

    :return: xmltree with entered kpoint list
    """
    # TODO: check on weights,
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

    # try:
    #     KpointsDataNode.get_kpoints_mesh()
    #     kpoint_type = 'mesh'
    # except AttributeError:
    #     kpoint_type = 'path'

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
