# -*- coding: utf-8 -*-
from lxml import etree


def set_kpointsdata_f(fleurinp_tree_copy, kpointsdata_uuid):
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
    from aiida.orm import KpointsData, load_node
    from aiida.common.exceptions import InputValidationError
    from aiida_fleur.tools.xml_util import replace_tag

    # all hardcoded xpaths used and attributes names:
    kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList'

    # replace the kpoints tag.(delete old write new)
    # <kPointList posScale="36.00000000" weightScale="324.00000000" count="324">
    #    <kPoint weight="    1.000000">   17.000000     0.000000     0.000000</kPoint>
    # add new inp.xml to fleurinpdata
    if not isinstance(kpointsdata_uuid, KpointsData):
        KpointsDataNode = load_node(kpointsdata_uuid)
    else:
        KpointsDataNode = kpointsdata_uuid

    if not isinstance(KpointsDataNode, KpointsData):
        raise InputValidationError('The node given is not a valid KpointsData node.')

    kpoint_list = KpointsDataNode.get_kpoints(also_weights=True, cartesian=False)
    nkpts = len(kpoint_list[0])
    totalw = 0
    for weight in kpoint_list[1]:
        totalw = totalw + weight
    #weightscale = totalw
    # fleur will re weight? renormalize?
    new_kpo = etree.Element('kPointList', posScale='1.000', weightScale='1.0', count='{}'.format(nkpts))
    for i, kpos in enumerate(kpoint_list[0]):
        new_k = etree.Element('kPoint', weight='{}'.format(kpoint_list[1][i]))
        new_k.text = '{} {} {}'.format(kpos[0], kpos[1], kpos[2])
        new_kpo.append(new_k)
    new_tree = replace_tag(fleurinp_tree_copy, kpointlist_xpath, new_kpo)
    return new_tree


FLEURINPMODIFIER_EXTRA_FUNCS = {'basic': {'set_kpointsdata': set_kpointsdata_f}}
