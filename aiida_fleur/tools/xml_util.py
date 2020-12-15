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
In this module contains useful methods for handling xml trees and files which are used
by the Fleur code and the fleur plugin.
"""
# TODO FEHLER meldungen, currently if a xpath expression is valid, but does not exists
# xpath returns []. Do we want this behavior?
# TODO finish implementation of create=False
# TODO: no aiida imports

from __future__ import absolute_import
from __future__ import print_function
from lxml import etree
import six

from aiida.common.exceptions import InputValidationError


def is_sequence(arg):
    """
    Checks if arg is a sequence
    """
    if isinstance(arg, str):
        return False
    elif hasattr(arg, '__iter__'):
        return True
    elif not hasattr(arg, 'strip') and hasattr(arg, '__getitem__'):
        return True
    else:
        return False


##### CONVERTERS ############


def convert_to_float(value_string, parser_info_out=None, suc_return=True):
    """
    Tries to make a float out of a string. If it can't it logs a warning
    and returns True or False if convertion worked or not.

    :param value_string: a string
    :returns value: the new float or value_string: the string given
    :returns: True or False
    """
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}
    try:
        value = float(value_string)
    except TypeError:
        parser_info_out['parser_warnings'].append('Could not convert: "{}" to float, TypeError' ''.format(value_string))
        if suc_return:
            return value_string, False
        else:
            return value_string
    except ValueError:
        parser_info_out['parser_warnings'].append('Could not convert: "{}" to float, ValueError'
                                                  ''.format(value_string))
        if suc_return:
            return value_string, False
        else:
            return value_string
    if suc_return:
        return value, True
    else:
        return value


def convert_to_int(value_string, parser_info_out=None, suc_return=True):
    """
    Tries to make a int out of a string. If it can't it logs a warning
    and returns True or False if convertion worked or not.

    :param value_string: a string
    :returns value: the new int or value_string: the string given
    :returns: True or False, if suc_return=True
    """
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}
    try:
        value = int(value_string)
    except TypeError:
        parser_info_out['parser_warnings'].append('Could not convert: "{}" to int, TypeError' ''.format(value_string))
        if suc_return:
            return value_string, False
        else:
            return value_string
    except ValueError:
        parser_info_out['parser_warnings'].append('Could not convert: "{}" to int, ValueError' ''.format(value_string))
        if suc_return:
            return value_string, False
        else:
            return value_string
    if suc_return:
        return value, True
    else:
        return value


def convert_htr_to_ev(value, parser_info_out=None):
    """
    Multiplies the value given with the Hartree factor (converts htr to eV)
    """
    from aiida_fleur.common.constants import HTR_TO_EV
    # htr = 27.21138602
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}

    suc = False
    value_to_save, suc = convert_to_float(value, parser_info_out=parser_info_out)
    if suc:
        return value_to_save * HTR_TO_EV
    else:
        return value


def convert_ev_to_htr(value, parser_info_out=None):
    """
    Divides the value given with the Hartree factor (converts htr to eV)
    """
    from aiida_fleur.common.constants import HTR_TO_EV
    # htr = 27.21138602
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}
    suc = False
    value_to_save, suc = convert_to_float(value, parser_info_out=parser_info_out)
    if suc:
        return value_to_save / HTR_TO_EV
    else:
        return value


def convert_from_fortran_bool(stringbool):
    """
    Converts a string in this case ('T', 'F', or 't', 'f') to True or False

    :param stringbool: a string ('t', 'f', 'F', 'T')

    :return: boolean  (either True or False)
    """
    true_items = ['True', 't', 'T']
    false_items = ['False', 'f', 'F']
    if isinstance(stringbool, str):
        if stringbool in false_items:
            return False
        if stringbool in true_items:
            return True
        else:
            raise InputValidationError("A string: {} for a boolean was given, which is not 'True',"
                                       " 'False', 't', 'T', 'F' or 'f'".format(stringbool))
    elif isinstance(stringbool, bool):
        return stringbool  # no convertion needed...
    else:
        raise TypeError('convert_to_fortran_bool accepts only a string or ' 'bool as argument')


def convert_to_fortran_bool(boolean):
    """
    Converts a Boolean as string to the format defined in the input

    :param boolean: either a boolean or a string ('True', 'False', 'F', 'T')

    :return: a string (either 't' or 'f')
    """

    if isinstance(boolean, bool):
        if boolean:
            new_string = 'T'
            return new_string
        else:
            new_string = 'F'
            return new_string
    elif isinstance(boolean, str):  # basestring):
        if boolean in ('True', 't', 'T'):
            new_string = 'T'
            return new_string
        elif boolean in ('False', 'f', 'F'):
            new_string = 'F'
            return new_string
        else:
            raise InputValidationError("A string: {} for a boolean was given, which is not 'True',"
                                       "'False', 't', 'T', 'F' or 'f'".format(boolean))
    else:
        raise TypeError('convert_to_fortran_bool accepts only a string or '
                        'bool as argument, given {} '.format(boolean))


def convert_to_fortran_string(string):
    """
    converts some parameter strings to the format for the inpgen
    :param string: some string
    :returns: string in right format (extra "")
    """
    new_string = '"' + string + '"'
    return new_string


def convert_fleur_lo(loelements):
    """
    Converts lo xml elements from the inp.xml file into a lo string for the inpgen
    """
    # Developer hint: Be careful with using '' and "", basestring and str are not the same...
    # therefore other conversion methods might fail, or the wrong format could be written.
    from aiida_fleur.tools.element_econfig_list import shell_map

    lo_string = ''
    for element in loelements:
        lo_type = get_xml_attribute(element, 'type')
        if lo_type != 'SCLO':  # non standard los not supported for now
            continue
        l_num = get_xml_attribute(element, 'l')
        n_num = get_xml_attribute(element, 'n')
        l_char = shell_map.get(int(l_num), '')
        lostr = '{}{}'.format(n_num, l_char)
        lo_string = lo_string + ' ' + lostr
    return lo_string.strip()


def set_dict_or_not(para_dict, key, value):
    """
    setter method for a dictionary that will not set the key, value pair.
    if the key is [] or None.
    """
    if value == [] or value is None:
        return para_dict
    else:
        para_dict[key] = value
        return para_dict


####### XML SETTERS GENERAL ##############


def xml_set_attribv_occ(xmltree, xpathn, attributename, attribv, occ=None, create=False):
    """
    Routine sets the value of an attribute in the xml file on only the places
    specified in occ

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute
    :param attributename: an attribute name
    :param attribv: an attribute value which will be set
    :param occ: a list of integers specifying number of occurrence to be set
    :param create: if True and there is no given xpath in the FleurinpData, creates it

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'band', 'T')
             xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'dos', 'F')
    """
    if occ is None:
        occ = [0]

    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpathn, create=create)

    if not isinstance(attribv, type('')):
        attribv = str(attribv)
    for i, node in enumerate(nodes):
        if i in occ:
            node.set(attributename, attribv)
        if -1 in occ:  # 'all'
            node.set(attributename, attribv)


def xml_set_first_attribv(xmltree, xpathn, attributename, attribv, create=False):
    """
    Routine sets the value of the first found attribute in the xml file

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute
    :param attributename: an attribute name
    :param attribv: an attribute value which will be set
    :param create: if True and there is no given xpath in the FleurinpData, creates it

    :return: None, or an etree

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'band', 'T')
             xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'dos', 'F')
    """

    root = xmltree.getroot()
    if isinstance(attribv, type('')):
        eval_xpath3(root, xpathn, create=create)[0].set(attributename, attribv)
    else:
        eval_xpath3(root, xpathn, create=create)[0].set(attributename, str(attribv))
    # return xmltree
    # ToDO check if worked. else exception,


def xml_set_all_attribv(xmltree, xpathn, attributename, attribv, create=False):
    """
    Routine sets the value of an attribute in the xml file on all places it occurs

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute
    :param attributename: an attribute name
    :param attribv: an attribute value which will be set
    :param create: if True and there is no given xpath in the FleurinpData, creates it

    :return: None, or an etree

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: xml_set_first_attribv(tree, '/fleurInput/atomGroups/atomGroup/force', 'relaxXYZ', 'TTF')
             xml_set_first_attribv(tree, '/fleurInput/atomGroups/atomGroup/force', 'calculate', 'F')
    """

    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpathn, create=create)
    if is_sequence(attribv):
        for i, node in enumerate(nodes):
            node.set(attributename, str(attribv[i]))
    else:
        if not isinstance(attribv, str):  # type(attribv) != type(''):
            attribv = str(attribv)
        for node in nodes:
            node.set(attributename, attribv)


def xml_set_text(xmltree, xpathn, text, create=False, place_index=None, tag_order=None):
    """
    Routine sets the text of a tag in the xml file

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute
    :param text: text to be set
    :param create: if True and there is no given xpath in the FleurinpData, creates it
    :param place_index: if create=True, defines the place where to put a created tag
    :param tag_order: if create=True, defines a tag order

    example:

        xml_set_text(tree, '/fleurInput/comment', 'Test Fleur calculation for AiiDA plug-in')

    but also coordinates and Bravais Matrix!:

        xml_set_text(tree, '/fleurInput/atomGroups/atomGroup/relPos','1.20000 PI/3 5.1-MYCrazyCostant')
    """

    root = xmltree.getroot()
    node = eval_xpath3(root, xpathn, create=create, place_index=place_index, tag_order=tag_order)
    if node:
        node[0].text = text
    # return xmltree


def xml_set_text_occ(xmltree, xpathn, text, create=False, occ=0, place_index=None, tag_order=None):
    """
    Routine sets the text of a tag in the xml file

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute
    :param text: text to be set
    :param create: if True and there is no given xpath in the FleurinpData, creates it
    :param occ: an integer that sets occurrence number to be set
    :param place_index: if create=True, defines the place where to put a created tag
    :param tag_order: if create=True, defines a tag order
    """

    root = xmltree.getroot()
    node = eval_xpath3(root, xpathn, create=create, place_index=place_index, tag_order=tag_order)
    if node:
        node[occ].text = text


def xml_set_all_text(xmltree, xpathn, text, create=False, tag_order=None):
    """
    Routine sets the text of a tag in the xml file

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute
    :param text: text to be set
    :param create: if True and there is no given xpath in the FleurinpData, creates it
    :param place_index: if create=True, defines the place where to put a created tag
    :param tag_order: if create=True, defines a tag order
    """
    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpathn, create=create, tag_order=tag_order)
    if is_sequence(text):
        for i, node in enumerate(nodes):
            node.text = text[i]
    else:
        for node in nodes:
            node.text = text


def create_tag(xmlnode, xpath, newelement, create=False, place_index=None, tag_order=None):
    """
    This method evaluates an xpath expresion and creates tag in an xmltree under the
    returned nodes. If the path does exist things will be overwritten, or created.
    Per default the new element is appended to the elements, but it can also be
    inserted in a certain position or after certain other tags.

    :param xmlnode: an xmltree that represents inp.xml
    :param xpathn: a path where to place a new tag
    :param newelement: a tag name to be created
    :param create: if True and there is no given xpath in the FleurinpData, creates it
    :param place_index: defines the place where to put a created tag
    :param tag_order: defines a tag order
    """
    import copy
    newelement_name = newelement
    if not etree.iselement(newelement):
        try:
            newelement = etree.Element(newelement)
        except ValueError as v:
            raise ValueError('{}. If this is a species, are you sure this species exists '
                             'in your inp.xml?'.format(v)) from v
    nodes = eval_xpath3(xmlnode, xpath, create=create)
    if nodes:
        for node_1 in nodes:
            element_to_write = copy.deepcopy(newelement)
            if place_index:
                if tag_order:
                    # behind what shall I place it
                    try:
                        place_index = tag_order.index(newelement_name)
                    except ValueError as exc:
                        raise ValueError('Did not find element name in the tag_order list') from exc
                    behind_tags = tag_order[:place_index]
                    # check if children are in the same sequence as given in tag_order
                    tags = []
                    for child in node_1.iterchildren():
                        if child.tag not in tags:
                            tags.append(child.tag)
                    prev = -1
                    for name in tags:
                        try:
                            current = tag_order.index(name)
                        except ValueError as exc:
                            raise ValueError('Did not find existing tag name in the tag_order list'
                                             ': {}'.format(name)) from exc
                        if current > prev:
                            prev = current
                        else:
                            raise ValueError('Existing order does not correspond to tag_order list')
                    # get all names of tag existing tags
                    was_set = False
                    for tag in reversed(behind_tags):
                        for child in node_1.iterchildren(tag=tag, reversed=False):
                            # if tagname of elements==tag:
                            tag_index = node_1.index(child)
                            try:
                                node_1.insert(tag_index + 1, element_to_write)
                            except ValueError as exc:
                                raise ValueError('{}. If this is a species, are'
                                                 'you sure this species exists in your inp.xml?'
                                                 ''.format(exc)) from exc
                            was_set = True
                            break
                        if was_set:
                            break
                    if not was_set:  # just append
                        try:
                            node_1.insert(0, element_to_write)
                        except ValueError as exc:
                            raise ValueError('{}. If this is a species, are you'
                                             ' sure this species exists in your inp.xml?'
                                             ''.format(exc)) from exc
                    # (or remove all and write them again in right order?)
                else:
                    try:
                        node_1.insert(place_index, element_to_write)
                    except ValueError as exc:
                        raise ValueError('{}. If this is a species, are you sure this species '
                                         'exists in your inp.xml?'.format(exc)) from exc
            else:
                try:
                    node_1.append(element_to_write)
                except ValueError as exc:
                    raise ValueError('{}. If this is a species, are you sure this species exists'
                                     'in your inp.xml?'.format(exc)) from exc
    return xmlnode


def delete_att(xmltree, xpath, attrib):
    """
    Deletes an xml tag in an xmletree.

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the attribute to be deleted
    :param attrib: the name of an attribute
    """
    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpath)
    if nodes:
        for node in nodes:
            try:
                del node.attrib[attrib]
            except BaseException:
                pass
    return xmltree


def delete_tag(xmltree, xpath):
    """
    Deletes an xml tag in an xmletree.

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the tag to be deleted
    """
    root = xmltree.getroot()
    if root is None:  # eval will fail in this case
        return xmltree

    nodes = eval_xpath3(root, xpath)
    if nodes:
        for node in nodes:
            parent = node.getparent()
            parent.remove(node)
    return xmltree


def replace_tag(xmltree, xpath, newelement):
    """
    replaces a xml tag by another tag on an xmletree in place

    :param xmltree: an xmltree that represents inp.xml
    :param xpathn: a path to the tag to be replaced
    :param newelement: a new tag
    """
    root = xmltree.getroot()

    nodes = eval_xpath3(root, xpath)
    if nodes:
        for node in nodes:
            parent = node.getparent()
            index = parent.index(node)
            parent.remove(node)
            parent.insert(index, newelement)

    return xmltree


def get_inpgen_paranode_from_xml(inpxmlfile):
    """
    This routine returns an AiiDA Parameter Data type produced from the inp.xml
    file, which can be used by inpgen.

    :return: ParameterData node
    """
    from aiida.orm import Dict
    para_dict = get_inpgen_para_from_xml(inpxmlfile)
    return Dict(dict=para_dict)


def get_inpgen_para_from_xml(inpxmlfile, inpgen_ready=True):
    """
    This routine returns an python dictionary produced from the inp.xml
    file, which can be used as a calc_parameters node by inpgen.
    Be aware that inpgen does not take all information that is contained in an inp.xml file

    :param inpxmlfile: and xml etree of a inp.xml file
    :param inpgen_ready: Bool, return a dict which can be inputed into inpgen while setting atoms
    :return new_parameters: A Dict, which will lead to the same inp.xml (in case if other defaults,
                            which can not be controlled by input for inpgen, were changed)

    """

    # TODO: convert econfig
    # TODO: parse kpoints, somehow count is bad (if symmetry changes), mesh is not known, path cannot be specified

    # Disclaimer: this routine needs some xpath expressions. these are hardcoded here,
    # therefore maintainance might be needed, if you want to circumvent this, you have
    # to get all the paths from somewhere.

    #######
    # all hardcoded xpaths used and attributes names:
    # input
    film_xpath = '/fleurInput/atomGroups/atomGroup/filmPos/'  # check for film pos

    # atom, for each species\
    species_xpath = '/fleurInput/atomSpecies/species'
    atom_id_xpath = ''  # is reconstruction possible at all now?
    atom_z_xpath = '@atomicNumber'
    atom_rmt_xpath = 'mtSphere/@radius'
    atom_dx_xpath = 'mtSphere/@logIncrement'
    atom_jri_xpath = 'mtSphere/@gridPoints'
    atom_lmax_xpath = 'atomicCutoffs/@lmax'
    atom_lnosph_xpath = 'atomicCutoffs/@lnonsphr'
    #atom_ncst_xpath = '@coreStates'
    atom_econfig_xpath = 'electronConfig'  # converting todo
    atom_bmu_xpath = '@magMom'
    atom_lo_xpath = 'lo'  # converting todo
    atom_element_xpath = '@element'
    atom_name_xpath = '@name'

    # comp
    jspins_xpath = 'calculationSetup/magnetism/@jspins'
    frcor_xpath = 'calculationSetup/coreElectrons/@frcor'
    ctail_xpath = 'calculationSetup/coreElectrons/@ctail'
    kcrel_xpath = 'calculationSetup/coreElectrons/@kcrel'
    gmax_xpath = 'calculationSetup/cutoffs/@Gmax'
    gmaxxc_xpath = 'calculationSetup/cutoffs/@GmaxXC'
    kmax_xpath = 'calculationSetup/cutoffs/@Kmax'

    # exco
    exco_xpath = 'xcFunctional/@name'
    # film

    # soc
    l_soc_xpath = '//calculationSetup/soc/@l_soc'
    theta_xpath = '//calculationSetup/soc/@theta'
    phi_xpath = '//calculationSetup/soc/@phi'
    # qss

    # kpt

    title_xpath = '/fleurInput/comment/text()'  # text

    ########
    new_parameters = {}

    #print('parsing inp.xml without XMLSchema')
    #tree = etree.parse(inpxmlfile)
    tree = inpxmlfile
    root = tree.getroot()

    # Create the cards

    # &input # most things are not needed for AiiDA here. or we ignor them for now.
    # film is set by the plugin depended on the structure
    # symor per default = False? to avoid input which fleur can't take

    # &comp
    # attrib = get_xml_attribute(
    comp_dict = {}
    comp_dict = set_dict_or_not(comp_dict, 'jspins', convert_to_int(eval_xpath(root, jspins_xpath), suc_return=False))
    comp_dict = set_dict_or_not(comp_dict, 'frcor', convert_from_fortran_bool(eval_xpath(root, frcor_xpath)))
    comp_dict = set_dict_or_not(comp_dict, 'ctail', convert_from_fortran_bool(eval_xpath(root, ctail_xpath)))
    comp_dict = set_dict_or_not(comp_dict, 'kcrel', eval_xpath(root, kcrel_xpath))
    comp_dict = set_dict_or_not(comp_dict, 'gmax', convert_to_float(eval_xpath(root, gmax_xpath), suc_return=False))
    comp_dict = set_dict_or_not(comp_dict, 'gmaxxc', convert_to_float(eval_xpath(root, gmaxxc_xpath), suc_return=False))
    comp_dict = set_dict_or_not(comp_dict, 'kmax', convert_to_float(eval_xpath(root, kmax_xpath), suc_return=False))
    new_parameters['comp'] = comp_dict

    # &atoms
    species_list = eval_xpath2(root, species_xpath)

    for i, species in enumerate(species_list):
        atom_dict = {}
        atoms_name = 'atom{}'.format(i)
        atom_z = convert_to_int(eval_xpath(species, atom_z_xpath), suc_return=False)
        atom_rmt = convert_to_float(eval_xpath(species, atom_rmt_xpath), suc_return=False)
        atom_dx = convert_to_float(eval_xpath(species, atom_dx_xpath), suc_return=False)
        atom_jri = convert_to_int(eval_xpath(species, atom_jri_xpath), suc_return=False)
        atom_lmax = convert_to_int(eval_xpath(species, atom_lmax_xpath), suc_return=False)
        atom_lnosph = convert_to_int(eval_xpath(species, atom_lnosph_xpath), suc_return=False)
        #atom_ncst = convert_to_int(eval_xpath(species, atom_ncst_xpath), suc_return=False)
        atom_econfig = eval_xpath(species, atom_econfig_xpath)
        atom_bmu = convert_to_float(eval_xpath(species, atom_bmu_xpath), suc_return=False)
        atom_lo = eval_xpath(species, atom_lo_xpath)
        atom_element = eval_xpath(species, atom_element_xpath)
        atom_name_2 = eval_xpath(species, atom_name_xpath)

        if not inpgen_ready:
            atom_dict = set_dict_or_not(atom_dict, 'z', atom_z)
            #atom_dict = set_dict_or_not(atom_dict, 'name', atom_name_2)
            #atom_dict = set_dict_or_not(atom_dict, 'ncst', atom_ncst) (deprecated)
        atom_dict = set_dict_or_not(atom_dict, 'rmt', atom_rmt)
        atom_dict = set_dict_or_not(atom_dict, 'dx', atom_dx)
        atom_dict = set_dict_or_not(atom_dict, 'jri', atom_jri)
        atom_dict = set_dict_or_not(atom_dict, 'lmax', atom_lmax)
        atom_dict = set_dict_or_not(atom_dict, 'lnonsph', atom_lnosph)

        atom_dict = set_dict_or_not(atom_dict, 'econfig', atom_econfig)
        atom_dict = set_dict_or_not(atom_dict, 'bmu', atom_bmu)
        if atom_lo is not None:
            atom_dict = set_dict_or_not(atom_dict, 'lo', convert_fleur_lo(atom_lo))
        atom_dict = set_dict_or_not(atom_dict, 'element', '{}'.format(atom_element))

        new_parameters[atoms_name] = atom_dict

    # &soc
    attrib = convert_from_fortran_bool(eval_xpath(root, l_soc_xpath))
    theta = convert_to_float(eval_xpath(root, theta_xpath), suc_return=False)
    phi = convert_to_float(eval_xpath(root, phi_xpath), suc_return=False)
    if attrib:
        new_parameters['soc'] = {'theta': theta, 'phi': phi}

    # &kpt
    #attrib = convert_from_fortran_bool(eval_xpath(root, l_soc_xpath))
    #theta = eval_xpath(root, theta_xpath)
    #phi = eval_xpath(root, phi_xpath)
    # if kpt:
    #    new_parameters['kpt'] = {'theta' : theta, 'phi' : phi}
    #    # ['nkpt', 'kpts', 'div1', 'div2', 'div3',                         'tkb', 'tria'],

    # title
    title = eval_xpath(root, title_xpath)  # text
    if title:
        new_parameters['title'] = title.replace('\n', '').strip()

    # &exco
    #TODO, easy
    exco_dict = {}
    exco_dict = set_dict_or_not(exco_dict, 'xctyp', eval_xpath(root, exco_xpath))
    # 'exco' : ['xctyp', 'relxc'],
    new_parameters['exco'] = exco_dict
    # &film
    # TODO

    # &qss
    # TODO

    # lattice, not supported?

    return new_parameters


####### XML SETTERS SPECIAL ########


def set_species_label(fleurinp_tree_copy, at_label, attributedict, create=False):
    """
    This method calls :func:`~aiida_fleur.tools.xml_util.set_species()`
    method for a certain atom specie that corresponds to an atom with a given label

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param at_label: string, a label of the atom which specie will be changed. 'all' to change all the species
    :param attributedict: a python dict specifying what you want to change.
    :param create: bool, if species does not exist create it and all subtags?
    """

    if at_label == 'all':
        fleurinp_tree_copy = set_species(fleurinp_tree_copy, 'all', attributedict, create)
        return fleurinp_tree_copy

    specie = ''
    at_label = '{: >20}'.format(at_label)
    all_groups = eval_xpath2(fleurinp_tree_copy, '/fleurInput/atomGroups/atomGroup')

    species_to_set = []

    # set all species, where given label is present
    for group in all_groups:
        positions = eval_xpath2(group, 'filmPos')
        if not positions:
            positions = eval_xpath2(group, 'relPos')
        for atom in positions:
            atom_label = get_xml_attribute(atom, 'label')
            if atom_label == at_label:
                species_to_set.append(get_xml_attribute(group, 'species'))

    species_to_set = list(set(species_to_set))

    for specie in species_to_set:
        fleurinp_tree_copy = set_species(fleurinp_tree_copy, specie, attributedict, create)

    return fleurinp_tree_copy


def set_species(fleurinp_tree_copy, species_name, attributedict, create=False):
    """
    Method to set parameters of a species tag of the fleur inp.xml file.

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param species_name: string, name of the specie you want to change
    :param attributedict: a python dict specifying what you want to change.
    :param create: bool, if species does not exist create it and all subtags?

    :raises ValueError: if species name is non existent in inp.xml and should not be created.
                        also if other given tags are garbage. (errors from eval_xpath() methods)

    :return fleurinp_tree_copy: xml etree of the new inp.xml

    **attributedict** is a python dictionary containing dictionaries that specify attributes
    to be set inside the certain specie. For example, if one wants to set a MT radius it
    can be done via::

        attributedict = {'mtSphere' : {'radius' : 2.2}}

    Another example::

        'attributedict': {'special': {'socscale': 0.0}}

    that switches SOC terms on a sertain specie. ``mtSphere``, ``atomicCutoffs``,
    ``energyParameters``, ``lo``, ``electronConfig``, ``nocoParams``, ``ldaU`` and
    ``special`` keys are supported. To find possible
    keys of the inner dictionary please refer to the FLEUR documentation flapw.de
    """
    # TODO lowercase everything
    # TODO make a general specifier for species, not only the name i.e. also
    # number, other parameters
    if species_name == 'all':
        xpath_species = '/fleurInput/atomSpecies/species'
    elif species_name[:4] == 'all-':  #format all-<string>
        xpath_species = '/fleurInput/atomSpecies/species[contains(@name,"{}")]'.format(species_name[4:])
    else:
        xpath_species = '/fleurInput/atomSpecies/species[@name = "{}"]'.format(species_name)

    xpath_mt = '{}/mtSphere'.format(xpath_species)
    xpath_atomic_cutoffs = '{}/atomicCutoffs'.format(xpath_species)
    xpath_energy_parameters = '{}/energyParameters'.format(xpath_species)
    xpath_lo = '{}/lo'.format(xpath_species)
    xpath_electron_config = '{}/electronConfig'.format(xpath_species)
    xpath_core_occ = '{}/electronConfig/stateOccupation'.format(xpath_species)
    xpath_lda_u = '{}/ldaU'.format(xpath_species)
    xpath_soc_scale = '{}/special'.format(xpath_species)

    # can we get this out of schema file?
    species_seq = [
        'mtSphere', 'atomicCutoffs', 'energyParameters', 'prodBasis', 'special', 'force', 'electronConfig',
        'nocoParams', 'ldaU', 'lo'
    ]

    for key, val in six.iteritems(attributedict):
        if key == 'mtSphere':  # always in inp.xml
            for attrib, value in six.iteritems(val):
                xml_set_all_attribv(fleurinp_tree_copy, xpath_mt, attrib, value)
        elif key == 'atomicCutoffs':  # always in inp.xml
            for attrib, value in six.iteritems(val):
                xml_set_all_attribv(fleurinp_tree_copy, xpath_atomic_cutoffs, attrib, value)
        elif key == 'energyParameters':  # always in inp.xml
            for attrib, value in six.iteritems(val):
                xml_set_all_attribv(fleurinp_tree_copy, xpath_energy_parameters, attrib, value)
        elif key == 'lo':  # optional in inp.xml
            # policy: we DELETE all LOs, and create new ones from the given parameters.
            existinglos = eval_xpath3(fleurinp_tree_copy, xpath_lo)
            for los in existinglos:
                parent = los.getparent()
                parent.remove(los)

            # there can be multible LO tags, so I expect either one or a list
            if isinstance(val, dict):
                create_tag(fleurinp_tree_copy,
                           xpath_species,
                           'lo',
                           place_index=species_seq.index('lo'),
                           tag_order=species_seq)
                for attrib, value in six.iteritems(val):
                    xml_set_all_attribv(fleurinp_tree_copy, xpath_lo, attrib, value, create=True)
            else:  # I expect a list of dicts
                # lonodes = eval_xpath3(root, xpathlo)#, create=True, place_index=species_seq.index('lo'), tag_order=species_seq)
                #nlonodes = len(lonodes)
                # ggf create more lo tags of needed
                los_need = len(val)  # - nlonodes
                for j in range(0, los_need):
                    create_tag(fleurinp_tree_copy,
                               xpath_species,
                               'lo',
                               place_index=species_seq.index('lo'),
                               tag_order=species_seq)
                for i, lodict in enumerate(val):
                    for attrib, value in six.iteritems(lodict):
                        sets = []
                        for k in range(len(eval_xpath2(fleurinp_tree_copy, xpath_species + '/lo')) // los_need):
                            sets.append(k * los_need + i)
                        xml_set_attribv_occ(fleurinp_tree_copy, xpath_lo, attrib, value, occ=sets)

        elif key == 'electronConfig':
            # eval electronConfig and ggf create tag at right place.
            eval_xpath3(fleurinp_tree_copy,
                        xpath_electron_config,
                        create=True,
                        place_index=species_seq.index('electronConfig'),
                        tag_order=species_seq)

            for tag in ['coreConfig', 'valenceConfig', 'stateOccupation']:
                for etag, edictlist in six.iteritems(val):
                    if not etag == tag:
                        continue
                    if etag == 'stateOccupation':  # there can be multiple times stateOccupation
                        # policy: default we DELETE all existing occs and create new ones for the
                        # given input!
                        existingocc = eval_xpath3(fleurinp_tree_copy, xpath_core_occ)
                        for occ in existingocc:
                            parent = occ.getparent()
                            parent.remove(occ)
                        if isinstance(edictlist, dict):
                            for attrib, value in six.iteritems(edictlist):
                                xml_set_all_attribv(fleurinp_tree_copy, xpath_core_occ, attrib, value, create=True)
                        else:  # I expect a list of dicts
                            nodes_need = len(edictlist)
                            for j in range(0, nodes_need):
                                create_tag(fleurinp_tree_copy, xpath_electron_config, 'stateOccupation', create=True)
                            for i, occdict in enumerate(edictlist):
                                # override them one after one
                                sets = []
                                for k in range(len(eval_xpath2(fleurinp_tree_copy, xpath_core_occ)) // nodes_need):
                                    sets.append(k * nodes_need + i)
                                for attrib, value in six.iteritems(occdict):
                                    xml_set_attribv_occ(fleurinp_tree_copy, xpath_core_occ, attrib, value, occ=sets)

                    else:
                        xpathconfig = xpath_electron_config + '/{}'.format(etag)
                        xml_set_all_text(fleurinp_tree_copy,
                                         xpathconfig,
                                         edictlist,
                                         create=create,
                                         tag_order=['coreConfig', 'valenceConfig', 'stateOccupation'])
        elif key == 'ldaU':
            #Same policy as los: delete existing ldaU and add the ldaU specified
            existingldaus = eval_xpath3(fleurinp_tree_copy, xpath_lda_u)
            for ldau in existingldaus:
                parent = ldau.getparent()
                parent.remove(ldau)

            if isinstance(val, dict):
                create_tag(fleurinp_tree_copy,
                           xpath_species,
                           'ldaU',
                           place_index=species_seq.index('ldaU'),
                           tag_order=species_seq)
                for attrib, value in six.iteritems(val):
                    xml_set_all_attribv(fleurinp_tree_copy, xpath_lda_u, attrib, value, create=True)
            else:  #list of dicts

                ldaus_needed = len(val)
                for j in range(0, ldaus_needed):
                    create_tag(fleurinp_tree_copy,
                               xpath_species,
                               'ldaU',
                               place_index=species_seq.index('ldaU'),
                               tag_order=species_seq)
                for i, ldaudict in enumerate(val):
                    for attrib, value in six.iteritems(ldaudict):
                        sets = []
                        for k in range(len(eval_xpath2(fleurinp_tree_copy, xpath_species + '/ldaU')) // ldaus_needed):
                            sets.append(k * ldaus_needed + i)
                        xml_set_attribv_occ(fleurinp_tree_copy, xpath_lda_u, attrib, value, occ=sets)

        elif key == 'special':
            eval_xpath3(fleurinp_tree_copy,
                        xpath_soc_scale,
                        create=True,
                        place_index=species_seq.index('special'),
                        tag_order=species_seq)
            for attrib, value in six.iteritems(val):
                xml_set_all_attribv(fleurinp_tree_copy, xpath_soc_scale, attrib, value, create=create)
        else:
            xml_set_all_attribv(fleurinp_tree_copy, xpath_species, key, val)

    return fleurinp_tree_copy


def shift_value_species_label(fleurinp_tree_copy, at_label, attr_name, value_given, mode='abs'):
    """
    Shifts value of a specie by label
    if at_label contains 'all' then applies to all species

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param at_label: string, a label of the atom which specie will be changed. 'all' if set up all species
    :param attr_name: name of the attribute to change
    :param value_given: value to add or to multiply by
    :param mode: 'rel' for multiplication or 'abs' for addition
    """
    import numpy as np
    specie = ''
    if at_label != 'all':
        at_label = '{: >20}'.format(at_label)
    all_groups = eval_xpath2(fleurinp_tree_copy, '/fleurInput/atomGroups/atomGroup')

    species_to_set = []

    for group in all_groups:
        positions = eval_xpath2(group, 'filmPos')
        if not positions:
            positions = eval_xpath2(group, 'relPos')
        for atom in positions:
            atom_label = get_xml_attribute(atom, 'label')
            if at_label in ['all', atom_label]:
                species_to_set.append(get_xml_attribute(group, 'species'))

    species_to_set = list(set(species_to_set))

    for specie in species_to_set:

        xpath_species = '/fleurInput/atomSpecies/species[@name = "{}"]'.format(specie)

        xpath_mt = '{}/mtSphere'.format(xpath_species)
        xpath_atomic_cutoffs = '{}/atomicCutoffs'.format(xpath_species)
        xpath_energy_parameters = '{}/energyParameters'.format(xpath_species)
        xpath_final = 'initialise'

        if attr_name in ['radius', 'gridPoints', 'logIncrement']:
            xpath_final = xpath_mt
        elif attr_name in ['lmax', 'lnonsphr']:
            xpath_final = xpath_atomic_cutoffs
        elif attr_name in ['s', 'p', 'd', 'f']:
            xpath_final = xpath_energy_parameters

        old_val = np.array(eval_xpath2(fleurinp_tree_copy, '/@'.join([xpath_final, attr_name])))

        if old_val.size == 0:
            print('Can not find {} attribute in the inp.xml, skip it'.format(attr_name))
        else:
            old_val = old_val.astype('float')

        if mode == 'rel':
            value = value_given * old_val
        elif mode == 'abs':
            value = value_given + old_val
        else:
            raise ValueError("Mode should be 'res' or 'abs' only")

        if attr_name in ['radius', 'logIncrement']:
            value_to_write = value
        else:
            if not np.all(value == value.astype('int')):
                raise ValueError('You are trying to write a float to an integer attribute')
            value_to_write = value.astype('int')

        xml_set_all_attribv(fleurinp_tree_copy, xpath_final, attr_name, value_to_write)

    return fleurinp_tree_copy


def change_atomgr_att_label(fleurinp_tree_copy, attributedict, at_label):
    """
    This method calls :func:`~aiida_fleur.tools.xml_util.change_atomgr_att()`
    method for a certain atom specie that corresponds to an atom with a given label.

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param at_label: string, a label of the atom which specie will be changed. 'all' to change all the species
    :param attributedict: a python dict specifying what you want to change.

    :return fleurinp_tree_copy: xml etree of the new inp.xml

    **attributedict** is a python dictionary containing dictionaries that specify attributes
    to be set inside the certain specie. For example, if one wants to set a beta noco parameter it
    can be done via::

        'attributedict': {'nocoParams': [('beta', val)]}

    ``force`` and ``nocoParams`` keys are supported.
    To find possible keys of the inner dictionary please refer to the FLEUR documentation flapw.de
    """

    if at_label == 'all':
        fleurinp_tree_copy = change_atomgr_att(fleurinp_tree_copy, attributedict, position=None, species='all')
        return fleurinp_tree_copy

    specie = ''
    at_label = '{: >20}'.format(at_label)
    all_groups = eval_xpath2(fleurinp_tree_copy, '/fleurInput/atomGroups/atomGroup')

    species_to_set = []

    for group in all_groups:
        positions = eval_xpath2(group, 'filmPos')
        if not positions:
            positions = eval_xpath2(group, 'relPos')
        for atom in positions:
            atom_label = get_xml_attribute(atom, 'label')
            if atom_label == at_label:
                species_to_set.append(get_xml_attribute(group, 'species'))

    species_to_set = list(set(species_to_set))

    for specie in species_to_set:
        fleurinp_tree_copy = change_atomgr_att(fleurinp_tree_copy, attributedict, position=None, species=specie)

    return fleurinp_tree_copy


def change_atomgr_att(fleurinp_tree_copy, attributedict, position=None, species=None):
    """
    Method to set parameters of an atom group of the fleur inp.xml file.

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param attributedict: a python dict specifying what you want to change.
    :param position: position of an atom group to be changed. If equals to 'all', all species will be changed
    :param species: atom groups, corresponding to the given specie will be changed
    :param create: bool, if species does not exist create it and all subtags?

    :return fleurinp_tree_copy: xml etree of the new inp.xml

    **attributedict** is a python dictionary containing dictionaries that specify attributes
    to be set inside the certain specie. For example, if one wants to set a beta noco parameter it
    can be done via::

        'attributedict': {'nocoParams': [('beta', val)]}

    ``force`` and ``nocoParams`` keys are supported.
    To find possible keys of the inner dictionary please refer to the FLEUR documentation flapw.de
    """
    xpathatmgroup = '/fleurInput/atomGroups/atomGroup'
    xpathforce = '{}/force'.format(xpathatmgroup)
    xpathnocoParams = '{}/nocoParams'.format(xpathatmgroup)

    if not position and not species:  # not specfied what to change
        return fleurinp_tree_copy

    if position:
        if not position == 'all':
            xpathatmgroup = '/fleurInput/atomGroups/atomGroup[{}]'.format(position)
            xpathforce = '{}/force'.format(xpathatmgroup)
            xpathnocoParams = '{}/nocoParams'.format(xpathatmgroup)
    if species:
        if not species == 'all':
            xpathatmgroup = '/fleurInput/atomGroups/atomGroup[@species = "{}"]'.format(species)
            xpathforce = '{}/force'.format(xpathatmgroup)
            xpathnocoParams = '{}/nocoParams'.format(xpathatmgroup)

    for key, val in six.iteritems(attributedict):
        if key == 'force':
            for attrib, value in val:
                xml_set_all_attribv(fleurinp_tree_copy, xpathforce, attrib, value)
        elif key == 'nocoParams':
            for attrib, value in val:
                xml_set_all_attribv(fleurinp_tree_copy, xpathnocoParams, attrib, value)
        else:
            xml_set_all_attribv(fleurinp_tree_copy, xpathatmgroup, attrib, value)

    return fleurinp_tree_copy


def set_inpchanges(fleurinp_tree_copy, change_dict):
    """
    Makes given changes directly in the inp.xml file. Afterwards
    updates the inp.xml file representation and the current inp_userchanges
    dictionary with the keys provided in the 'change_dict' dictionary.

    :param fleurinp_tree_copy: a lxml tree that represents inp.xml
    :param change_dict: a python dictionary with the keys to substitute.
                        It works like dict.update(), adding new keys and
                        overwriting existing keys.

    :returns new_tree: a lxml tree with applied changes

    An example of change_dict::

            change_dict = {'itmax' : 1,
                           'l_noco': True,
                           'ctail': False,
                           'l_ss': True}

    A full list of supported keys in the change_dict can be found in
    :py:func:`~aiida_fleur.tools.xml_util.get_inpxml_file_structure()`::

            'comment': '/fleurInput/comment',
            'relPos': '/fleurInput/atomGroups/atomGroup/relPos',
            'filmPos': '/fleurInput/atomGroups/atomGroup/filmPos',
            'absPos': '/fleurInput/atomGroups/atomGroup/absPos',
            'qss': '/fleurInput/calculationSetup/nocoParams/qss',
            'l_ss': '/fleurInput/calculationSetup/nocoParams',
            'row-1': '/fleurInput/cell/bulkLattice/bravaisMatrix',
            'row-2': '/fleurInput/cell/bulkLattice/bravaisMatrix',
            'row-3': '/fleurInput/cell/bulkLattice/bravaisMatrix',
            'a1': '/fleurInput/cell/filmLattice/a1',  # switches once
            'dos': '/fleurInput/output',
            'band': '/fleurInput/output',
            'secvar': '/fleurInput/calculationSetup/expertModes',
            'ctail': '/fleurInput/calculationSetup/coreElectrons',
            'frcor': '/fleurInput/calculationSetup/coreElectrons',
            'l_noco': '/fleurInput/calculationSetup/magnetism',
            'l_J': '/fleurInput/calculationSetup/magnetism',
            'swsp': '/fleurInput/calculationSetup/magnetism',
            'lflip': '/fleurInput/calculationSetup/magnetism',
            'off': '/fleurInput/calculationSetup/soc',
            'spav': '/fleurInput/calculationSetup/soc',
            'l_soc': '/fleurInput/calculationSetup/soc',
            'soc66': '/fleurInput/calculationSetup/soc',
            'pot8': '/fleurInput/calculationSetup/expertModes',
            'eig66': '/fleurInput/calculationSetup/expertModes',
            'l_f': '/fleurInput/calculationSetup/geometryOptimization',
            'gamma': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
            'gauss': '',
            'tria': '',
            'invs': '',
            'zrfs': '',
            'vchk': '/fleurInput/output/checks',
            'cdinf': '/fleurInput/output/checks',
            'disp': '/fleurInput/output/checks',
            'vacdos': '/fleurInput/output',
            'integ': '/fleurInput/output/vacuumDOS',
            'star': '/fleurInput/output/vacuumDOS',
            'iplot': '/fleurInput/output/plotting',
            'score': '/fleurInput/output/plotting',
            'plplot': '/fleurInput/output/plotting',
            'slice': '/fleurInput/output',
            'pallst': '/fleurInput/output/chargeDensitySlicing',
            'form66': '/fleurInput/output/specialOutput',
            'eonly': '/fleurInput/output/specialOutput',
            'bmt': '/fleurInput/output/specialOutput',
            'relativisticCorrections': '/fleurInput/xcFunctional',
            'calculate': '/fleurInput/atomGroups/atomGroup/force',
            'flipSpin': '/fleurInput/atomSpecies/species',
            'Kmax': '/fleurInput/calculationSetup/cutoffs',
            'Gmax': '/fleurInput/calculationSetup/cutoffs',
            'GmaxXC': '/fleurInput/calculationSetup/cutoffs',
            'numbands': '/fleurInput/calculationSetup/cutoffs',
            'itmax': '/fleurInput/calculationSetup/scfLoop',
            'minDistance': '/fleurInput/calculationSetup/scfLoop',
            'maxIterBroyd': '/fleurInput/calculationSetup/scfLoop',
            'imix': '/fleurInput/calculationSetup/scfLoop',
            'alpha': '/fleurInput/calculationSetup/scfLoop',
            'spinf': '/fleurInput/calculationSetup/scfLoop',
            'kcrel': '/fleurInput/calculationSetup/coreElectrons',
            'jspins': '/fleurInput/calculationSetup/magnetism',
            'theta': '/fleurInput/calculationSetup/soc',
            'phi': '/fleurInput/calculationSetup/soc',
            'gw': '/fleurInput/calculationSetup/expertModes',
            'lpr': '/fleurInput/calculationSetup/expertModes',
            'isec1': '/fleurInput/calculationSetup/expertModes',
            'forcemix': '/fleurInput/calculationSetup/geometryOptimization',
            'forcealpha': '/fleurInput/calculationSetup/geometryOptimization',
            'force_converged': '/fleurInput/calculationSetup/geometryOptimization',
            'qfix': '/fleurInput/calculationSetup/geometryOptimization',
            'epsdisp': '/fleurInput/calculationSetup/geometryOptimization',
            'epsforce': '/fleurInput/calculationSetup/geometryOptimization',
            'valenceElectrons': '/fleurInput/calculationSetup/bzIntegration',
            'mode': '/fleurInput/calculationSetup/bzIntegration',
            'fermiSmearingEnergy': '/fleurInput/calculationSetup/bzIntegration',
            'nx': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
            'ny': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
            'nz': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
            'count': '/fleurInput/calculationSetup/kPointCount',
            'ellow': '/fleurInput/calculationSetup/energyParameterLimits',
            'elup': '/fleurInput/calculationSetup',
            'filename': '/fleurInput/cell/symmetryFile',
            'scale': '/fleurInput/cell/bulkLattice',
            'ndir': '/fleurInput/output/densityOfStates',
            'minEnergy': '/fleurInput/output/densityOfStates',
            'maxEnergy': '/fleurInput/output/densityOfStates',
            'sigma': ' /fleurInput/output/densityOfStates',
            'layers': '/fleurInput/output/vacuumDOS',
            'nstars': '/fleurInput/output/vacuumDOS',
            'locx1': '/fleurInput/output/vacuumDOS',
            'locy1': '/fleurInput/output/vacuumDOS',
            'locx2': '/fleurInput/output/vacuumDOS',
            'locy2': '/fleurInput/output/vacuumDOS',
            'nstm': '/fleurInput/output/vacuumDOS',
            'tworkf': '/fleurInput/output/vacuumDOS',
            'numkpt': '/fleurInput/output/chargeDensitySlicing',
            'minEigenval': '/fleurInput/output/chargeDensitySlicing',
            'maxEigenval': '/fleurInput/output/chargeDensitySlicing',
            'nnne': '/fleurInput/output/chargeDensitySlicing',
            'dVac': '/fleurInput/cell/filmLattice',
            'dTilda': '/fleurInput/cell/filmLattice',
            'xcFunctional': '/fleurInput/xcFunctional/name',  # other_attributes_more
            'name': {'/fleurInput/constantDefinitions', '/fleurInput/xcFunctional',
                    '/fleurInput/atomSpecies/species'},
            'value': '/fleurInput/constantDefinitions',
            'element': '/fleurInput/atomSpecies/species',
            'atomicNumber': '/fleurInput/atomSpecies/species',
            'coreStates': '/fleurInput/atomSpecies/species',
            'magMom': '/fleurInput/atomSpecies/species',
            'radius': '/fleurInput/atomSpecies/species/mtSphere',
            'gridPoints': '/fleurInput/atomSpecies/species/mtSphere',
            'logIncrement': '/fleurInput/atomSpecies/species/mtSphere',
            'lmax': '/fleurInput/atomSpecies/species/atomicCutoffs',
            'lnonsphr': '/fleurInput/atomSpecies/species/atomicCutoffs',
            's': '/fleurInput/atomSpecies/species/energyParameters',
            'p': '/fleurInput/atomSpecies/species/energyParameters',
            'd': '/fleurInput/atomSpecies/species/energyParameters',
            'f': '/fleurInput/atomSpecies/species/energyParameters',
            'type': '/fleurInput/atomSpecies/species/lo',
            'l': '/fleurInput/atomSpecies/species/lo',
            'n': '/fleurInput/atomSpecies/species/lo',
            'eDeriv': '/fleurInput/atomSpecies/species/lo',
            'species': '/fleurInput/atomGroups/atomGroup',
            'relaxXYZ': '/fleurInput/atomGroups/atomGroup/force'

    """
    tree = fleurinp_tree_copy
    # apply changes to etree
    xmlinpstructure = get_inpxml_file_structure()
    new_tree = write_new_fleur_xmlinp_file(tree, change_dict, xmlinpstructure)

    return new_tree


def shift_value(fleurinp_tree_copy, change_dict, mode='abs'):
    """
    Shifts numertical values of some tags directly in the inp.xml file.

    :param fleurinp_tree_copy: a lxml tree that represents inp.xml
    :param change_dict: a python dictionary with the keys to shift.
    :param mode: 'abs' if change given is absolute, 'rel' if relative

    :returns new_tree: a lxml tree with shifted values

    An example of change_dict::

            change_dict = {'itmax' : 1, 'dVac': -0.123}
    """
    xmlinpstructure = get_inpxml_file_structure()
    all_attrib_xpath = xmlinpstructure[12]
    float_attributes_once = xmlinpstructure[4]
    int_attributes_once = xmlinpstructure[3]

    change_to_write = {}

    for key, value_given in six.iteritems(change_dict):
        if key not in float_attributes_once and key not in int_attributes_once:
            raise ValueError('Given attribute name either does not exist or is not floar or int')

        key_path = all_attrib_xpath[key]

        old_val = eval_xpath2(fleurinp_tree_copy, '/@'.join([key_path, key]))

        if not old_val:
            print('Can not find {} attribute in the inp.xml, skip it'.format(key))
            continue

        old_val = float(old_val[0])

        if mode == 'rel':
            value = value_given * old_val
        elif mode == 'abs':
            value = value_given + old_val
        else:
            raise ValueError("Mode should be 'res' or 'abs' only")

        if key in float_attributes_once:
            change_to_write[key] = value
        elif key in int_attributes_once:
            if not value.is_integer():
                raise ValueError('You are trying to write a float to an integer attribute')
            change_to_write[key] = int(value)

    new_tree = set_inpchanges(fleurinp_tree_copy, change_to_write)
    return new_tree


def add_num_to_att(xmltree, xpathn, attributename, set_val, mode='abs', occ=None):
    """
    Routine adds something to the value of an attribute in the xml file (should be a number here)
    This is a lower-level version of :func:`~aiida_fleur.tools.xml_util.shift_value()` which
    allows one to specife an arbitrary xml path.

    :param: an etree a xpath from root to the attribute and the attribute value
    :param xpathn: an xml path to the attribute to change
    :param attributename: a name of the attribute to change
    :param set_val: a value to be added/multiplied to the previous value
    :param mode: 'abs' if to add set_val, 'rel' if multiply
    :param occ: a list of integers specifying number of occurrence to be set

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: add_num_to_add(tree, '/fleurInput/bzIntegration', 'valenceElectrons', '1')
             add_num_to_add(tree, '/fleurInput/bzIntegration', 'valenceElectrons', '1.1', mode='rel')
    """

    if occ is None:
        occ = [0]

    # get attribute, add or multiply
    # set attribute
    attribval_node = eval_xpath(xmltree, xpathn)
    # do some checks..
    attribval = get_xml_attribute(attribval_node, attributename)
    print(attribval)
    if attribval:
        if mode == 'abs':
            newattribv = float(attribval) + float(set_val)
        elif mode == 'rel':
            newattribv = float(attribval) * float(set_val)
        else:
            pass
            # unknown mode

        xml_set_attribv_occ(xmltree, xpathn, attributename, newattribv, occ=[0], create=False)
    else:
        pass
        # something was wrong, ...
    return xmltree


def set_nkpts(fleurinp_tree_copy, count, gamma):
    """
    Sets a k-point mesh directly into inp.xml

    :param fleurinp_tree_copy: a lxml tree that represents inp.xml
    :param count: number of k-points
    :param gamma: a fortran-type boolean that controls if the gamma-point should be included
                    in the k-point mesh

    :returns new_tree: a lxml tree with applied changes
    """

    kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList'
    #kpoint_xpath = '/fleurInput/calculationSetup/bzIntegration/kPoint*'

    tree = fleurinp_tree_copy
    new_kpo = etree.Element('kPointCount', count='{}'.format(count), gamma='{}'.format(gamma))
    new_tree = replace_tag(tree, kpointlist_xpath, new_kpo)

    return new_tree


def set_kpath(fleurinp_tree_copy, kpath, count, gamma):
    """
    Sets a k-path directly into inp.xml

    :param fleurinp_tree_copy: a lxml tree that represents inp.xml
    :param kpath: a dictionary with kpoint name as key and k point coordinate as value
    :param count: number of k-points
    :param gamma: a fortran-type boolean that controls if the gamma-point should be included
                    in the k-point mesh

    :returns new_tree: a lxml tree with applied changes
    """

    kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/altKPointSet/kPointCount'
    #kpoint_xpath = '/fleurInput/calculationSetup/bzIntegration/kPoint*'

    tree = fleurinp_tree_copy
    new_kpo = etree.Element('kPointCount', count='{}'.format(count), gamma='{}'.format(gamma))
    for key in kpath:
        new_k = etree.Element('specialPoint', name='{}'.format(key))
        new_k.text = '{} {} {}'.format(kpath[key][0], kpath[key][1], kpath[key][2])
        new_kpo.append(new_k)

    new_tree = replace_tag(tree, kpointlist_xpath, new_kpo)

    return new_tree


####### XML GETTERS #########
# TODO parser infos do not really work, might need to be returned, here


def eval_xpath(node, xpath, parser_info=None):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.
    If seferal paths are found, return a list. If only one - returns the value.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns either nodes, or attributes, or text
    """
    if parser_info is None:
        parser_info = {'parser_warnings': []}
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        parser_info['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n'
                                              'Either it does not exist, or something is wrong'
                                              ' with the expression.'.format(xpath))
        # TODO maybe raise an error again to catch in upper routine, to know where exactly
        return []
    if len(return_value) == 1:
        return return_value[0]
    else:
        return return_value


def eval_xpath2(node, xpath, parser_info=None):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.
    Always return a list.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns a node list
    """
    if parser_info is None:
        parser_info = {'parser_warnings': []}
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        parser_info['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n'
                                              'Either it does not exist, or something is wrong'
                                              'with the expression.'.format(xpath))
        # TODO maybe raise an error again to catch in upper routine, to know where exactly
        return []
    return return_value


def eval_xpath3(node, xpath, create=False, place_index=None, tag_order=None):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.
    If create == True, creates a tag

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns always a node list
    """
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError as exc:
        message = ('There was a XpathEvalError on the xpath: {} \n Either it does '
                   'not exist, or something is wrong with the expression.'
                   ''.format(xpath))
        raise etree.XPathEvalError(message) from exc

    if return_value == []:
        if create:
            x_pieces = [e for e in xpath.split('/') if e != '']
            #x_pieces = xpath.split('/')
            xpathn = ''
            for piece in x_pieces[:-1]:
                xpathn = xpathn + '/' + piece
            # this is REKURSIV! since create tag calls eval_xpath3
            create_tag(node, xpathn, x_pieces[-1], create=create, place_index=place_index, tag_order=tag_order)
            return_value = node.xpath(xpath)
            return return_value
        else:
            return return_value
    else:
        return return_value


def get_xml_attribute(node, attributename, parser_info_out=None):
    """
    Get an attribute value from a node.

    :params node: a node from etree
    :params attributename: a string with the attribute name.
    :returns: either attributevalue, or None
    """
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}

    if etree.iselement(node):
        attrib_value = node.get(attributename)
        if attrib_value:
            return attrib_value
        else:
            if parser_info_out:
                parser_info_out['parser_warnings'].append('Tried to get attribute: "{}" from element {}.\n '
                                                          'I recieved "{}", maybe the attribute does not exist'
                                                          ''.format(attributename, node, attrib_value))
            else:
                print(('Can not get attributename: "{}" from node "{}", '
                       'because node is not an element of etree.'
                       ''.format(attributename, node)))
            return None
    else:  # something doesn't work here, some nodes get through here
        if parser_info_out:
            parser_info_out['parser_warnings'].append('Can not get attributename: "{}" from node "{}", '
                                                      'because node is not an element of etree.'
                                                      ''.format(attributename, node))
        else:
            print(('Can not get attributename: "{}" from node "{}", '
                   'because node is not an element of etree.'
                   ''.format(attributename, node)))
        return None


# TODO this has to be done better. be able to write tags and
# certain attributes of attributes that occur possible more then once.
# HINT: This is not really used anymore. use fleurinpmodifier
def write_new_fleur_xmlinp_file(inp_file_xmltree, fleur_change_dic, xmlinpstructure):
    """
    This modifies the xml-inp file. Makes all the changes wanted by
    the user or sets some default values for certain modes

    :params inp_file_xmltree: xml-tree of the xml-inp file
    :params fleur_change_dic: dictionary {attrib_name : value} with all the wanted changes.

    :returns: an etree of the xml-inp file with changes.
    """
    # TODO rename, name is misleaded just changes the tree.
    xmltree_new = inp_file_xmltree

    pos_switch_once = xmlinpstructure[0]
    pos_switch_several = xmlinpstructure[1]
    pos_attrib_once = xmlinpstructure[2]
    pos_float_attributes_once = xmlinpstructure[4]
    pos_attrib_several = xmlinpstructure[6]
    pos_int_attributes_several = xmlinpstructure[7]
    pos_text = xmlinpstructure[11]
    pos_xpaths = xmlinpstructure[12]
    expertkey = xmlinpstructure[13]

    for key in fleur_change_dic:
        if key in pos_switch_once:
            # TODO: a test here if path is plausible and if exist
            # ggf. create tags and key.value is 'T' or 'F' if not convert,
            # if garbage, exception
            # convert user input into 'fleurbool'
            fleur_bool = convert_to_fortran_bool(fleur_change_dic[key])

            xpath_set = pos_xpaths[key]
            # TODO: check if something in setup is inconsitent?
            xml_set_first_attribv(xmltree_new, xpath_set, key, fleur_bool)

        elif key in pos_attrib_once:
            # TODO: same here, check existance and plausiblility of xpath
            xpath_set = pos_xpaths[key]
            if key in pos_float_attributes_once:
                newfloat = '{:.10f}'.format(fleur_change_dic[key])
                xml_set_first_attribv(xmltree_new, xpath_set, key, newfloat)
            elif key == 'xcFunctional':
                xml_set_first_attribv(xmltree_new, xpath_set, 'name', fleur_change_dic[key])
            else:
                xml_set_first_attribv(xmltree_new, xpath_set, key, fleur_change_dic[key])
        elif key in pos_text:
            # can be several times, therefore check
            xpath_set = pos_xpaths[key]
            xml_set_text(xmltree_new, xpath_set, fleur_change_dic[key])
        else:
            raise InputValidationError("You try to set the key:'{}' to : '{}', but the key is unknown"
                                       ' to the fleur plug-in'.format(key, fleur_change_dic[key]))
    return xmltree_new


# TODO: maybe it is possible to use the xml, schema to dict libary of the QE people.
# So far it does not seem to do what we need.
def inpxml_todict(parent, xmlstr):
    """
    Recursive operation which transforms an xml etree to
    python nested dictionaries and lists.
    Decision to add a list is if the tag name is in the given list tag_several

    :param parent: some xmltree, or xml element
    :param xmlstr: structure/layout of the xml file in xmlstr is tags_several:
                   a list of the tags, which should be converted to a list, not
                   a dictionary(because they are known to occur more often, and
                   want to be accessed in a list later.

    :return: a python dictionary
    """

    xmlstructure = xmlstr
    pos_switch_once1 = xmlstructure[0]
    pos_switch_several1 = xmlstructure[1]
    int_attributes_once1 = xmlstructure[3]
    float_attributes_once1 = xmlstructure[4]
    string_attributes_once1 = xmlstructure[5]
    int_attributes_several1 = xmlstructure[7]
    float_attributes_several1 = xmlstructure[8]
    string_attributes_several1 = xmlstructure[9]
    tags_several1 = xmlstructure[10]
    pos_text1 = xmlstructure[11]

    return_dict = {}
    if list(parent.items()):
        return_dict = dict(list(parent.items()))
        # Now we have to convert lazy fortan style into pretty things for the Database
        for key in return_dict:
            if key in pos_switch_once1 or (key in pos_switch_several1):
                return_dict[key] = convert_from_fortran_bool(return_dict[key])
            elif key in int_attributes_once1 or (key in int_attributes_several1):
                # TODO int several
                try:
                    return_dict[key] = int(return_dict[key])
                except ValueError:
                    pass
            elif key in float_attributes_once1 or (key in float_attributes_several1):
                # TODO pressision?
                try:
                    return_dict[key] = float(return_dict[key])
                except ValueError:
                    pass
            elif key in string_attributes_once1 or (key in string_attributes_several1):
                # TODO What attribute shall be set? all, one or several specific onces?
                return_dict[key] = str(return_dict[key])
            elif key in pos_text1:
                # Text is done by below check (parent.text)
                pass
            else:
                pass
                # this key is not know to plug-in TODO maybe make this a method
                # of the parser and log this as warning, or add here make a log
                # list, to which you always append messages, pass them back to
                # the parser, who locks it then
                # raise TypeError("Parser wanted to convert the key:'{}' with
                # value '{}', from the inpxml file but the key is unknown to the
                # fleur plug-in".format(key, return_dict[key]))

    if parent.text:  # TODO more detal, exp: relPos
        # has text, but we don't want all the '\n' s and empty stings in the database
        if parent.text.strip() != '':  # might not be the best solution
            # set text
            return_dict = parent.text.strip()

    for element in parent:
        if element.tag in tags_several1:
            # make a list, otherwise the tag will be overwritten in the dict
            if element.tag not in return_dict:  # is this the first occurence?
                # create a list
                return_dict[element.tag] = []
                return_dict[element.tag].append(inpxml_todict(element, xmlstructure))
            else:  # occured before, a list already exists, therefore just add
                return_dict[element.tag].append(inpxml_todict(element, xmlstructure))
        else:
            # make dict
            return_dict[element.tag] = inpxml_todict(element, xmlstructure)

    return return_dict


# This is probably only used to represent the whole inp.xml in the database for the fleurinpData attributes
# TODO this should be replaced by something else, maybe a class. that has a method to return certain
# list of possible xpaths from a schema file, or to validate a certain xpath expression and
# to allow to get SINGLE xpaths for certain attrbiutes.
#  akk: tell me where 'DOS' is
# This might not be back compatible... i.e a certain plugin version will by this design only work
#  with certain schema version
def get_inpxml_file_structure():
    """
    This routine returns the structure/layout of the 'inp.xml' file.

    Basicly the plug-in should know from this routine, what things are allowed
    to be set and where, i.e all attributes and their xpaths.
    As a developer make sure to use this routine always of you need information
    about the inp.xml file structure.
    Therefore, this plug-in should be easy to adjust to other codes with xml
    files as input files. Just rewrite this routine.

    For now the structure of the xmlinp file for fleur is hardcoded.
    If big changes are in the 'inp.xml' file, maintain this routine.
    TODO: Maybe this is better done, by reading the xml schema datei instead.
    And maybe it should also work without the schema file, do we want this?

    :param Nothing: TODO xml schema

    :return all_switches_once: list of all switches ('T' or 'F') which are allowed to be set
    :return all_switches_several: list of all switches ('T' or 'F') which are allowed to be set
    :return other_attributes_once: list of all attributes, which occur just once (can be tested)
    :return other_attributes_several: list of all attributes, which can occur more then once
    :return all_text: list of all text of tags, which can be set
    :return all_attrib_xpath:
                              dictonary (attrib, xpath), of all possible attributes
                              with their xpath expression for the xmp inp

    :return expertkey:
                       keyname (should not be in any other list), which can be
                       used to set anything in the file, by hand,
                       (for experts, and that plug-in does not need to be directly maintained if
                       xmlinp gets a new switch)
    """

    # All attributes (allowed to change?)

    # switches can be 'T' ot 'F' # TODO: alphabetical sorting
    all_switches_once = ('dos', 'band', 'secvar', 'ctail', 'frcor', 'l_noco', 'ctail', 'swsp', 'lflip', 'off', 'spav',
                         'l_soc', 'soc66', 'pot8', 'eig66', 'gamma', 'gauss', 'tria', 'invs', 'invs2', 'zrfs', 'vchk',
                         'cdinf', 'disp', 'vacdos', 'integ', 'star', 'score', 'plplot', 'slice', 'pallst', 'form66',
                         'eonly', 'bmt', 'relativisticCorrections', 'l_J', 'l_f', 'l_ss', 'l_linMix')

    all_switches_several = ('calculate', 'flipSpin', 'l_amf')

    int_attributes_once = ('numbands', 'itmax', 'maxIterBroyd', 'kcrel', 'jspins', 'gw', 'isec1', 'nx', 'ny', 'nz',
                           'ndir', 'layers', 'nstars', 'nstm', 'iplot', 'numkpt', 'nnne', 'lpr', 'count', 'qfix')

    float_attributes_once = ('Kmax', 'Gmax', 'GmaxXC', 'alpha', 'spinf', 'minDistance', 'theta', 'phi', 'epsdisp',
                             'epsforce', 'valenceElectrons', 'fermiSmearingEnergy', 'ellow', 'elup', 'scale', 'dTilda',
                             'dVac', 'minEnergy', 'maxEnergy', 'sigma', 'locx1', 'locy1', 'locx2', 'locy2', 'tworkf',
                             'minEigenval', 'maxEigenval', 'forcealpha', 'force_converged', 'mixParam')

    string_attributes_once = ('imix', 'mode', 'filename', 'latnam', 'spgrp', 'xcFunctional', 'fleurInputVersion',
                              'species', 'forcemix')

    other_attributes_once = tuple(
        list(int_attributes_once) + list(float_attributes_once) + list(string_attributes_once))
    other_attributes_once1 = ('isec1', 'Kmax', 'Gmax', 'GmaxXC', 'numbands', 'itmax', 'maxIterBroyd', 'imix', 'alpha',
                              'spinf', 'minDistance', 'kcrel', 'jspins', 'theta', 'phi', 'gw', 'lpr', 'epsdisp',
                              'epsforce', 'valenceElectrons', 'mode', 'gauss', 'fermiSmearingEnergy', 'nx', 'ny', 'nz',
                              'ellow', 'elup', 'filename', 'scale', 'dTilda', 'dVac', 'ndir', 'minEnergy', 'maxEnergy',
                              'sigma', 'layers', 'nstars', 'locx1', 'locy1', 'locx2', 'locy2', 'nstm', 'tworkf',
                              'numkpt', 'minEigenval', 'maxEigenval', 'nnne')

    int_attributes_several = ('atomicNumber', 'gridPoints', 'lmax', 'lnonsphr', 's', 'p', 'd', 'f', 'l', 'n', 'eDeriv',
                              'coreStates')
    float_attributes_several = ('value', 'magMom', 'radius', 'logIncrement', 'U', 'J')
    string_attributes_several = ('name', 'element', 'coreStates', 'type', 'relaxXYZ')
    other_attributes_several = ('name', 'value', 'element', 'atomicNumber', 'coreStates', 'magMom', 'radius',
                                'gridPoints', 'logIncrement', 'lmax', 'lnonsphr', 's', 'p', 'd', 'f', 'species', 'type',
                                'coreStates', 'l', 'n', 'eDeriv', 'relaxXYZ')

    # when parsing the xml file to a dict, these tags should become
    # list(sets, or tuples) instead of dictionaries.
    tags_several = ('atomGroup', 'relPos', 'absPos', 'filmPos', 'species', 'symOp', 'kPoint', 'ldaU', 'lo',
                    'stateOccupation')

    all_text = {
        'comment': 1,
        'relPos': 3,
        'filmPos': 3,
        'absPos': 3,
        'row-1': 3,
        'row-2': 3,
        'row-3': 3,
        'a1': 1,
        'qss': 3
    }
    # TODO all these (without comment) are floats, or float tuples.
    # Should be converted to this in the databas
    # changing the Bravais matrix should rather not be allowed I guess

    # all attribute xpaths

    # text xpaths(coordinates, bravaisMatrix)
    # all switches once, several, all attributes once, several
    all_attrib_xpath = {  # text
        'comment': '/fleurInput/comment',
        'relPos': '/fleurInput/atomGroups/atomGroup/relPos',
        'filmPos': '/fleurInput/atomGroups/atomGroup/filmPos',
        'absPos': '/fleurInput/atomGroups/atomGroup/absPos',
        'qss': '/fleurInput/calculationSetup/nocoParams/qss',
        'l_ss': '/fleurInput/calculationSetup/nocoParams',
        'row-1': '/fleurInput/cell/bulkLattice/bravaisMatrix',
        'row-2': '/fleurInput/cell/bulkLattice/bravaisMatrix',
        'row-3': '/fleurInput/cell/bulkLattice/bravaisMatrix',
        'a1': '/fleurInput/cell/filmLattice/a1',  # switches once
        'dos': '/fleurInput/output',
        'band': '/fleurInput/output',
        'secvar': '/fleurInput/calculationSetup/expertModes',
        'ctail': '/fleurInput/calculationSetup/coreElectrons',
        'frcor': '/fleurInput/calculationSetup/coreElectrons',
        'l_noco': '/fleurInput/calculationSetup/magnetism',
        'l_J': '/fleurInput/calculationSetup/magnetism',
        'swsp': '/fleurInput/calculationSetup/magnetism',
        'lflip': '/fleurInput/calculationSetup/magnetism',
        'off': '/fleurInput/calculationSetup/soc',
        'spav': '/fleurInput/calculationSetup/soc',
        'l_soc': '/fleurInput/calculationSetup/soc',
        'soc66': '/fleurInput/calculationSetup/soc',
        'pot8': '/fleurInput/calculationSetup/expertModes',
        'eig66': '/fleurInput/calculationSetup/expertModes',
        'l_f': '/fleurInput/calculationSetup/geometryOptimization',
        'gamma': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'l_linMix': '/fleurInput/calculationSetup/ldaU',
        'mixParam': '/fleurInput/calculationSetup/ldaU',
        # 'invs': '',
        # 'zrfs': '',
        'vchk': '/fleurInput/output/checks',
        'cdinf': '/fleurInput/output/checks',
        'disp': '/fleurInput/output/checks',
        'vacdos': '/fleurInput/output',
        'integ': '/fleurInput/output/vacuumDOS',
        'star': '/fleurInput/output/vacuumDOS',
        'iplot': '/fleurInput/output/plotting',
        'score': '/fleurInput/output/plotting',
        'plplot': '/fleurInput/output/plotting',
        'slice': '/fleurInput/output',
        'pallst': '/fleurInput/output/chargeDensitySlicing',
        'form66': '/fleurInput/output/specialOutput',
        'eonly': '/fleurInput/output/specialOutput',
        'bmt': '/fleurInput/output/specialOutput',
        'relativisticCorrections': '/fleurInput/xcFunctional',  # ALL_Switches_several
        'calculate': '/fleurInput/atomGroups/atomGroup/force',
        'flipSpin': '/fleurInput/atomSpecies/species',  # other_attributes_once
        'Kmax': '/fleurInput/calculationSetup/cutoffs',
        'Gmax': '/fleurInput/calculationSetup/cutoffs',
        'GmaxXC': '/fleurInput/calculationSetup/cutoffs',
        'numbands': '/fleurInput/calculationSetup/cutoffs',
        'itmax': '/fleurInput/calculationSetup/scfLoop',
        'minDistance': '/fleurInput/calculationSetup/scfLoop',
        'maxIterBroyd': '/fleurInput/calculationSetup/scfLoop',
        'imix': '/fleurInput/calculationSetup/scfLoop',
        'alpha': '/fleurInput/calculationSetup/scfLoop',
        'spinf': '/fleurInput/calculationSetup/scfLoop',
        'kcrel': '/fleurInput/calculationSetup/coreElectrons',
        'jspins': '/fleurInput/calculationSetup/magnetism',
        'theta': '/fleurInput/calculationSetup/soc',
        'phi': '/fleurInput/calculationSetup/soc',
        'gw': '/fleurInput/calculationSetup/expertModes',
        'lpr': '/fleurInput/calculationSetup/expertModes',
        'isec1': '/fleurInput/calculationSetup/expertModes',
        'forcemix': '/fleurInput/calculationSetup/geometryOptimization',
        'forcealpha': '/fleurInput/calculationSetup/geometryOptimization',
        'force_converged': '/fleurInput/calculationSetup/geometryOptimization',
        'qfix': '/fleurInput/calculationSetup/geometryOptimization',
        'epsdisp': '/fleurInput/calculationSetup/geometryOptimization',
        'epsforce': '/fleurInput/calculationSetup/geometryOptimization',
        'valenceElectrons': '/fleurInput/calculationSetup/bzIntegration',
        'mode': '/fleurInput/calculationSetup/bzIntegration',
        'fermiSmearingEnergy': '/fleurInput/calculationSetup/bzIntegration',
        'nx': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'ny': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'nz': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'count': '/ fleurInput/calculationSetup/bzIntegration/kPointList',
        'ellow': '/fleurInput/calculationSetup/energyParameterLimits',
        'elup': '/fleurInput/calculationSetup/energyParameterLimits',
        #'filename': '/fleurInput/cell/symmetryFile',
        'scale': '/fleurInput/cell/bulkLattice',
        # 'film_scale': '/fleurInput/cell/filmLattice',
        'ndir': '/fleurInput/output/densityOfStates',
        'minEnergy': '/fleurInput/output/densityOfStates',
        'maxEnergy': '/fleurInput/output/densityOfStates',
        'sigma': ' /fleurInput/output/densityOfStates',
        'layers': '/fleurInput/output/vacuumDOS',
        'nstars': '/fleurInput/output/vacuumDOS',
        'locx1': '/fleurInput/output/vacuumDOS',
        'locy1': '/fleurInput/output/vacuumDOS',
        'locx2': '/fleurInput/output/vacuumDOS',
        'locy2': '/fleurInput/output/vacuumDOS',
        'nstm': '/fleurInput/output/vacuumDOS',
        'tworkf': '/fleurInput/output/vacuumDOS',
        'numkpt': '/fleurInput/output/chargeDensitySlicing',
        'minEigenval': '/fleurInput/output/chargeDensitySlicing',
        'maxEigenval': '/fleurInput/output/chargeDensitySlicing',
        'nnne': '/fleurInput/output/chargeDensitySlicing',
        'dVac': '/fleurInput/cell/filmLattice',
        'dTilda': '/fleurInput/cell/filmLattice',
        'xcFunctional': '/fleurInput/xcFunctional',  # other_attributes_more
        # 'name': {'/fleurInput/constantDefinitions', '/fleurInput/xcFunctional',
        #          '/fleurInput/atomSpecies/species'},
        # 'value': '/fleurInput/constantDefinitions',
        'element': '/fleurInput/atomSpecies/species',
        'atomicNumber': '/fleurInput/atomSpecies/species',
        'coreStates': '/fleurInput/atomSpecies/species',
        'magMom': '/fleurInput/atomSpecies/species',
        'radius': '/fleurInput/atomSpecies/species/mtSphere',
        'gridPoints': '/fleurInput/atomSpecies/species/mtSphere',
        'logIncrement': '/fleurInput/atomSpecies/species/mtSphere',
        'lmax': '/fleurInput/atomSpecies/species/atomicCutoffs',
        'lnonsphr': '/fleurInput/atomSpecies/species/atomicCutoffs',
        's': '/fleurInput/atomSpecies/species/energyParameters',
        'p': '/fleurInput/atomSpecies/species/energyParameters',
        'd': '/fleurInput/atomSpecies/species/energyParameters',
        'f': '/fleurInput/atomSpecies/species/energyParameters',
        'type': '/fleurInput/atomSpecies/species/lo',
        'l': '/fleurInput/atomSpecies/species/lo',
        'n': '/fleurInput/atomSpecies/species/lo',
        'eDeriv': '/fleurInput/atomSpecies/species/lo',
        'species': '/fleurInput/atomGroups/atomGroup',
        'relaxXYZ': '/fleurInput/atomGroups/atomGroup/force'
    }

    all_tag_xpaths = ('/fleurInput/constantDefinitions', '/fleurInput/calculationSetup',
                      '/fleurInput/calculationSetup/cutoffs', '/fleurInput/calculationSetup/scfLoop',
                      '/fleurInput/calculationSetup/coreElectrons', '/fleurInput/calculationSetup/magnetism',
                      '/fleurInput/calculationSetup/soc', '/fleurInput/calculationSetup/expertModes',
                      '/fleurInput/calculationSetup/geometryOptimization', '/fleurInput/calculationSetup/bzIntegration',
                      '/fleurInput/calculationSetup/kPointMesh', '/fleurInput/cell/symmetry',
                      '/fleurInput/cell/bravaisMatrix', '/fleurInput/calculationSetup/nocoParams',
                      '/fleurInput/xcFunctional', '/fleurInput/xcFunctional/xcParams',
                      '/fleurInput/atomSpecies/species', '/fleurInput/atomSpecies/species/mtSphere',
                      '/fleurInput/atomSpecies/species/atomicCutoffs',
                      '/fleurInput/atomSpecies/species/energyParameters', '/fleurInput/atomSpecies/species/coreConfig',
                      '/fleurInput/atomSpecies/species/coreOccupation', '/fleurInput/atomGroups/atomGroup',
                      '/fleurInput/atomGroups/atomGroup/relPos', '/fleurInput/atomGroups/atomGroup/absPos',
                      '/fleurInput/atomGroups/atomGroup/filmPos', '/fleurInput/output/checks',
                      '/fleurInput/output/densityOfStates', '/fleurInput/output/vacuumDOS',
                      '/fleurInput/output/plotting', '/fleurInput/output/chargeDensitySlicing',
                      '/fleurInput/output/specialOutput')

    expertkey = 'other'
    returnlist = (all_switches_once, all_switches_several, other_attributes_once, int_attributes_once,
                  float_attributes_once, string_attributes_once, other_attributes_several, int_attributes_several,
                  float_attributes_several, string_attributes_several, tags_several, all_text, all_attrib_xpath,
                  expertkey)
    return returnlist


def clear_xml(tree):
    """
    Removes comments and executes xinclude tags of an
    xml tree.

    :param tree: an xml-tree which will be processes
    :return cleared_tree: an xml-tree without comments and with replaced xinclude tags
    """
    import copy

    cleared_tree = copy.deepcopy(tree)

    # replace XInclude parts to validate against schema
    cleared_tree.xinclude()

    # get rid of xml:base attribute in the relaxation part
    relax = eval_xpath(cleared_tree, '/fleurInput/relaxation')
    if relax != []:
        for attribute in relax.keys():
            if 'base' in attribute:
                cleared_tree = delete_att(cleared_tree, '/fleurInput/relaxation', attribute)

    # remove comments from inp.xml
    comments = cleared_tree.xpath('//comment()')
    for comment in comments:
        com_parent = comment.getparent()
        com_parent.remove(comment)

    return cleared_tree
