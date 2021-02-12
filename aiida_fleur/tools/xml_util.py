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


def get_inpgen_paranode_from_xml(inpxmlfile, schema_dict, inpgen_ready=True, write_ids=True):
    """
    This routine returns an AiiDA Parameter Data type produced from the inp.xml
    file, which can be used by inpgen.

    :return: ParameterData node
    """
    from aiida.orm import Dict
    para_dict = get_inpgen_para_from_xml(inpxmlfile, schema_dict, inpgen_ready=inpgen_ready, write_ids=write_ids)
    return Dict(dict=para_dict)


def get_inpgen_para_from_xml(inpxmlfile, schema_dict, inpgen_ready=True, write_ids=True):
    """
    This routine returns an python dictionary produced from the inp.xml
    file, which can be used as a calc_parameters node by inpgen.
    Be aware that inpgen does not take all information that is contained in an inp.xml file

    :param inpxmlfile: and xml etree of a inp.xml file
    :param inpgen_ready: Bool, return a dict which can be inputed into inpgen while setting atoms
    :return new_parameters: A Dict, which will lead to the same inp.xml (in case if other defaults,
                            which can not be controlled by input for inpgen, were changed)

    """
    from masci_tools.util.schema_dict_util import read_constants, eval_simple_xpath
    from masci_tools.util.schema_dict_util import evaluate_attribute, evaluate_text

    # TODO: convert econfig
    # TODO: parse kpoints, somehow count is bad (if symmetry changes), mesh is not known, path cannot be specified

    # Disclaimer: this routine needs some xpath expressions. these are hardcoded here,
    # therefore maintainance might be needed, if you want to circumvent this, you have
    # to get all the paths from somewhere.

    #######
    # all hardcoded xpaths used and attributes names:
    # input
    film_xpath = '/fleurInput/atomGroups/atomGroup/filmPos/'  # check for film pos

    # film

    # qss

    # kpt

    ########
    new_parameters = {}

    #print('parsing inp.xml without XMLSchema')
    #tree = etree.parse(inpxmlfile)
    tree = inpxmlfile
    root = tree.getroot()

    constants = read_constants(root, schema_dict)

    # Create the cards

    # &input # most things are not needed for AiiDA here. or we ignor them for now.
    # film is set by the plugin depended on the structure
    # symor per default = False? to avoid input which fleur can't take

    # &comp
    comp_dict = {}
    comp_dict = set_dict_or_not(comp_dict, 'jspins', evaluate_attribute(root, schema_dict, 'jspins', constants))
    comp_dict = set_dict_or_not(comp_dict, 'frcor', evaluate_attribute(root, schema_dict, 'frcor', constants))
    comp_dict = set_dict_or_not(comp_dict, 'ctail', evaluate_attribute(root, schema_dict, 'ctail', constants))
    comp_dict = set_dict_or_not(comp_dict, 'kcrel', evaluate_attribute(root, schema_dict, 'kcrel', constants))
    comp_dict = set_dict_or_not(comp_dict, 'gmax', evaluate_attribute(root, schema_dict, 'Gmax', constants))
    comp_dict = set_dict_or_not(comp_dict, 'gmaxxc', evaluate_attribute(root, schema_dict, 'GmaxXC', constants))
    comp_dict = set_dict_or_not(comp_dict, 'kmax', evaluate_attribute(root, schema_dict, 'Kmax', constants))
    new_parameters['comp'] = comp_dict

    # &atoms
    species_list = eval_simple_xpath(root, schema_dict, 'species', list_return=True)
    species_several = {}
    # first we see if there are several species with the same atomic number
    for i, species in enumerate(species_list):
        atom_z = evaluate_attribute(species, schema_dict, 'atomicNumber', constants)
        species_several[atom_z] = species_several.get(atom_z, 0) + 1

    species_count = {}
    for i, species in enumerate(species_list):
        atom_dict = {}
        atoms_name = 'atom{}'.format(i)
        atom_z = evaluate_attribute(species, schema_dict, 'atomicNumber', constants)
        species_count[atom_z] = species_count.get(atom_z, 0) + 1
        atom_id = '{}.{}'.format(atom_z, species_count[atom_z])
        atom_rmt = evaluate_attribute(species, schema_dict, 'radius', constants)
        atom_dx = evaluate_attribute(species, schema_dict, 'logIncrement', constants)
        atom_jri = evaluate_attribute(species, schema_dict, 'gridPoints', constants)
        atom_lmax = evaluate_attribute(species, schema_dict, 'lmax', constants)
        atom_lnosph = evaluate_attribute(species, schema_dict, 'lnonsphr', constants)
        #atom_ncst = convert_to_int(eval_xpath(species, atom_ncst_xpath), suc_return=False)
        atom_econfig = eval_simple_xpath(species, schema_dict, 'electronConfig')
        atom_bmu = evaluate_attribute(species, schema_dict, 'magMom', constants)
        atom_lo = eval_simple_xpath(species, schema_dict, 'lo', list_return=True)
        atom_element = evaluate_attribute(species, schema_dict, 'element', constants)
        atom_name_2 = evaluate_attribute(species, schema_dict, 'name', constants)

        if not inpgen_ready:
            atom_dict = set_dict_or_not(atom_dict, 'z', atom_z)
            #atom_dict = set_dict_or_not(atom_dict, 'name', atom_name_2)
            #atom_dict = set_dict_or_not(atom_dict, 'ncst', atom_ncst) (deprecated)
        atom_dict = set_dict_or_not(atom_dict, 'rmt', atom_rmt)
        atom_dict = set_dict_or_not(atom_dict, 'dx', atom_dx)
        atom_dict = set_dict_or_not(atom_dict, 'jri', atom_jri)
        atom_dict = set_dict_or_not(atom_dict, 'lmax', atom_lmax)
        atom_dict = set_dict_or_not(atom_dict, 'lnonsph', atom_lnosph)
        if write_ids:
            if species_several[atom_z] > 1:
                atom_dict = set_dict_or_not(atom_dict, 'id', atom_id)
        atom_dict = set_dict_or_not(atom_dict, 'econfig', atom_econfig)
        atom_dict = set_dict_or_not(atom_dict, 'bmu', atom_bmu)
        if atom_lo is not None:
            atom_dict = set_dict_or_not(atom_dict, 'lo', convert_fleur_lo(atom_lo))
        atom_dict = set_dict_or_not(atom_dict, 'element', '{}'.format(atom_element))

        new_parameters[atoms_name] = atom_dict

    # &soc
    soc = evaluate_attribute(root, schema_dict, 'l_soc', constants)
    theta = evaluate_attribute(root, schema_dict, 'theta', constants, contains='soc')
    phi = evaluate_attribute(root, schema_dict, 'phi', constants, contains='soc')
    if soc:
        new_parameters['soc'] = {'theta': theta, 'phi': phi}

    # &kpt
    #attrib = convert_from_fortran_bool(eval_xpath(root, l_soc_xpath))
    #theta = eval_xpath(root, theta_xpath)
    #phi = eval_xpath(root, phi_xpath)
    # if kpt:
    #    new_parameters['kpt'] = {'theta' : theta, 'phi' : phi}
    #    # ['nkpt', 'kpts', 'div1', 'div2', 'div3',                         'tkb', 'tria'],

    # title
    title = evaluate_text(root, schema_dict, 'comment', constants)
    if title:
        new_parameters['title'] = title.replace('\n', '').strip()

    # &exco
    #TODO, easy
    exco_dict = {}
    exco_dict = set_dict_or_not(exco_dict, 'xctyp',
                                evaluate_attribute(root, schema_dict, 'name', constants, contains='xcFunctional'))
    # 'exco' : ['xctyp', 'relxc'],
    new_parameters['exco'] = exco_dict
    # &film
    # TODO

    # &qss
    # TODO

    # lattice, not supported?

    return new_parameters


####### XML SETTERS SPECIAL ########


def set_species_label(fleurinp_tree_copy, schema_dict, at_label, attributedict, create=False):
    """
    This method calls :func:`~aiida_fleur.tools.xml_util.set_species()`
    method for a certain atom specie that corresponds to an atom with a given label

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param at_label: string, a label of the atom which specie will be changed. 'all' to change all the species
    :param attributedict: a python dict specifying what you want to change.
    :param create: bool, if species does not exist create it and all subtags?
    """
    from masci_tools.util.schema_dict_util import get_tag_xpath

    if at_label == 'all':
        fleurinp_tree_copy = set_species(fleurinp_tree_copy, schema_dict, 'all', attributedict, create)
        return fleurinp_tree_copy

    atomgroup_base_path = get_tag_xpath(schema_dict, 'atomGroup')

    specie = ''
    at_label = '{: >20}'.format(at_label)
    all_groups = eval_xpath2(fleurinp_tree_copy, atomgroup_base_path)

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
        fleurinp_tree_copy = set_species(fleurinp_tree_copy, schema_dict, specie, attributedict, create)

    return fleurinp_tree_copy


def set_species(fleurinp_tree_copy, schema_dict, species_name, attributedict, create=False):
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
    from masci_tools.util.schema_dict_util import get_tag_xpath

    base_xpath_species = get_tag_xpath(schema_dict, 'species')

    # TODO lowercase everything
    # TODO make a general specifier for species, not only the name i.e. also
    # number, other parameters
    if species_name == 'all':
        xpath_species = base_xpath_species
    elif species_name[:4] == 'all-':  #format all-<string>
        xpath_species = f'{base_xpath_species}[contains(@name,"{species_name[4:]}")]'
    else:
        xpath_species = f'{base_xpath_species}[@name = "{species_name}"]'

    fleurinp_tree_copy = set_complex_tag(fleurinp_tree_copy, schema_dict, base_xpath_species, xpath_species,
                                         attributedict)

    return fleurinp_tree_copy


def shift_value_species_label(fleurinp_tree_copy, schema_dict, at_label, attr_name, value_given, mode='abs', contains=None, not_contains=None, exclude=None):
    """
    Shifts value of a specie by label
    if at_label contains 'all' then applies to all species

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param at_label: string, a label of the atom which specie will be changed. 'all' if set up all species
    :param attr_name: name of the attribute to change
    :param value_given: value to add or to multiply by
    :param mode: 'rel' for multiplication or 'abs' for addition
    """
    from masci_tools.util.schema_dict_util import get_tag_xpath, get_attrib_xpath
    import numpy as np

    if contains is not None:
        if not isinstance(contains, list):
            contains = [contains]
        contains.append('species')
    else:
        contains = 'species'

    atomgroup_base_path = get_tag_xpath(schema_dict, 'atomGroup')
    species_base_path = get_tag_xpath(schema_dict, 'species')
    attr_base_path = get_attrib_xpath(schema_dict, attr_name, contains=contains, not_contains=not_contains, exclude=exclude)
    attr_base_path, attr_name = tuple(attr_base_path.split('/@'))

    possible_types = schema_dict['attrib_types'][attr_name]

    if 'float' not in possible_types and \
       'float_expression' not in possible_types and \
       'int' not in possible_types:
        raise ValueError('Given attribute name is not float or int')

    specie = ''
    if at_label != 'all':
        at_label = '{: >20}'.format(at_label)
    all_groups = eval_xpath2(fleurinp_tree_copy, atomgroup_base_path)

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

        xpath_species = f'{species_base_path}[@name = "{specie}"]'
        attr_xpath = attr_base_path.replace(species_base_path, xpath_species)

        old_val = np.array(eval_xpath2(fleurinp_tree_copy, '/@'.join([attr_xpath, attr_name])))

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

        if 'float' in possible_types or 'float_expression' in possible_types:
            value_to_write = value
        elif 'int' in possible_types:
            if not np.all(value == value.astype('int')):
                raise ValueError('You are trying to write a float to an integer attribute')
            value_to_write = value.astype('int')

        xml_set_all_attribv(fleurinp_tree_copy, attr_xpath, attr_name, value_to_write)

    return fleurinp_tree_copy


def change_atomgr_att_label(fleurinp_tree_copy, schema_dict, attributedict, at_label):
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
    from masci_tools.util.schema_dict_util import eval_simple_xpath

    if at_label == 'all':
        fleurinp_tree_copy = change_atomgr_att(fleurinp_tree_copy,
                                               schema_dict,
                                               attributedict,
                                               position=None,
                                               species='all')
        return fleurinp_tree_copy

    specie = ''
    at_label = '{: >20}'.format(at_label)
    all_groups = eval_simple_xpath(fleurinp_tree_copy, schema_dict, 'atomGroup', list_return=True)

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
        fleurinp_tree_copy = change_atomgr_att(fleurinp_tree_copy,
                                               schema_dict,
                                               attributedict,
                                               position=None,
                                               species=specie)

    return fleurinp_tree_copy


def change_atomgr_att(fleurinp_tree_copy, schema_dict, attributedict, position=None, species=None):
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

        'attributedict': {'nocoParams': {'beta': val]}

    ``force`` and ``nocoParams`` keys are supported.
    To find possible keys of the inner dictionary please refer to the FLEUR documentation flapw.de
    """
    from masci_tools.util.schema_dict_util import get_tag_xpath

    atomgroup_base_path = get_tag_xpath(schema_dict, 'atomGroup')
    atomgroup_xpath = atomgroup_base_path

    if not position and not species:  # not specfied what to change
        return fleurinp_tree_copy

    if position:
        if not position == 'all':
            atomgroup_xpath = f'{atomgroup_base_path}[{position}]'
    if species:
        if not species == 'all':
            atomgroup_xpath = f'{atomgroup_base_path}[@species = "{species}"]'

    fleurinp_tree_copy = set_complex_tag(fleurinp_tree_copy, schema_dict, atomgroup_base_path, atomgroup_xpath,
                                         attributedict)

    return fleurinp_tree_copy


def set_inpchanges(fleurinp_tree_copy, schema_dict, change_dict, path_spec=None):
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

    A full list of supported keys in the change_dict can be found in TODO

    """
    tree = fleurinp_tree_copy
    # apply changes to etree
    new_tree = update_fleurinput_xmltree(tree, schema_dict, change_dict, path_spec=path_spec)

    return new_tree


def shift_value(fleurinp_tree_copy, schema_dict, change_dict, mode='abs', path_spec=None):
    """
    Shifts numertical values of some tags directly in the inp.xml file.

    :param fleurinp_tree_copy: a lxml tree that represents inp.xml
    :param change_dict: a python dictionary with the keys to shift.
    :param mode: 'abs' if change given is absolute, 'rel' if relative

    :returns new_tree: a lxml tree with shifted values

    An example of change_dict::

            change_dict = {'itmax' : 1, 'dVac': -0.123}
    """
    from masci_tools.util.schema_dict_util import get_attrib_xpath

    change_to_write = {}

    if path_spec is None:
        path_spec = {}

    for key, value_given in six.iteritems(change_dict):

        if key not in schema_dict['attrib_types']:
            raise ValueError(f"You try to shift the attribute:'{key}' , but the key is unknown" ' to the fleur plug-in')

        possible_types = schema_dict['attrib_types'][key]

        if 'float' not in possible_types and \
           'float_expression' not in possible_types and \
           'int' not in possible_types:
            raise ValueError('Given attribute name is not float or int')

        key_spec = path_spec.get(key, {})
        #This method only support unique and unique_path attributes
        if 'exclude' not in key_spec:
            key_spec['exclude'] = ['other']
        elif 'other' not in key_spec['exclude']:
            key_spec['exclude'].append('other')

        key_xpath = get_attrib_xpath(schema_dict, key, **key_spec)
        key_xpath, key = tuple(key_xpath.split('/@'))

        old_val = eval_xpath2(fleurinp_tree_copy, '/@'.join([key_xpath, key]))

        if not old_val:
            print(f'Can not find {key} attribute in the inp.xml, skip it')
            continue

        old_val = float(old_val[0])

        if mode == 'rel':
            value = value_given * old_val
        elif mode == 'abs':
            value = value_given + old_val
        else:
            raise ValueError("Mode should be 'res' or 'abs' only")

        if 'float' in possible_types or 'float_expression' in possible_types:
            change_to_write[key] = value
        elif 'int' in possible_types:
            if not value.is_integer():
                raise ValueError('You are trying to write a float to an integer attribute')
            change_to_write[key] = int(value)

    new_tree = set_inpchanges(fleurinp_tree_copy, schema_dict, change_to_write, path_spec=path_spec)
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
def update_fleurinput_xmltree(inp_file_xmltree, schema_dict, fleur_change_dic, path_spec=None):
    """
    This modifies the xml-inp file. Makes all the changes wanted by
    the user or sets some default values for certain modes

    :params inp_file_xmltree: xml-tree of the xml-inp file
    :params fleur_change_dic: dictionary {attrib_name : value} with all the wanted changes.

    :returns: an etree of the xml-inp file with changes.
    """
    from masci_tools.util.schema_dict_util import get_attrib_xpath
    xmltree_new = inp_file_xmltree

    if path_spec is None:
        path_spec = {}

    for key, change_value in fleur_change_dic.items():

        #Special alias for xcFunctional since name is not a very telling attribute name
        if key == 'xcFunctional':
            key = 'name'

        if key not in schema_dict['attrib_types'] and key not in schema_dict['simple_elements']:
            raise InputValidationError(f"You try to set the key:'{key}' to : '{change_value}', but the key is unknown"
                                       ' to the fleur plug-in')

        text_attrib = False
        if key in schema_dict['attrib_types']:
            possible_types = schema_dict['attrib_types'][key]
        else:
            text_attrib = True

        key_spec = path_spec.get(key, {})
        #This method only support unique and unique_path attributes
        if 'exclude' not in key_spec:
            key_spec['exclude'] = ['other']
        elif 'other' not in key_spec['exclude']:
            key_spec['exclude'].append('other')

        try:
            key_xpath = get_attrib_xpath(schema_dict, key, **key_spec)
        except ValueError as exc:
            raise InputValidationError(exc) from exc

        if not text_attrib:
            #Split up path into tag path and attribute name (original name of key could have different cases)
            key_xpath, key = tuple(key_xpath.split('/@'))

        if text_attrib:
            xml_set_text(xmltree_new, key_xpath, change_value)
        else:
            if 'switch' in possible_types:
                # TODO: a test here if path is plausible and if exist
                # ggf. create tags and key.value is 'T' or 'F' if not convert,
                # if garbage, exception
                # convert user input into 'fleurbool'
                fleur_bool = convert_to_fortran_bool(change_value)

                # TODO: check if something in setup is inconsitent?
                xml_set_first_attribv(xmltree_new, key_xpath, key, fleur_bool)
            elif 'float' in possible_types:
                newfloat = '{:.10f}'.format(change_value)
                xml_set_first_attribv(xmltree_new, key_xpath, key, newfloat)
            elif 'float_expression' in possible_types:
                try:
                    newfloat = '{:.10f}'.format(change_value)
                except ValueError:
                    newfloat = change_value
                xml_set_first_attribv(xmltree_new, key_xpath, key, newfloat)
            else:
                xml_set_first_attribv(xmltree_new, key_xpath, key, change_value)

    return xmltree_new


def set_complex_tag(fleurinp_tree_copy, schema_dict, base_xpath, xpath, attributedict):
    """
    Recursive Function to correctly set tags/attributes for a given tag.
    Goes through the attributedict and decides based on the schema_dict, how the corresponding
    key has to be handled.
    Supports:
        attributes (no type checking)
        tags with text only
        simple tags, i.e. only attributes (can be optional single/multiple)
        complex tags, will recursively create/modify them

    :param fleurinp_tree_copy: xml etree of the inp.xml
    :param schema_dict: dict, represents the inputschema
    :param base_xpath: string, xpath of the tag to set without complex syntax (to get info from the schema_dict)
    :param xpath: string, actual xpath to use
    ;param attributedict: dict, changes to be made

    :return fleurinp_tree_copy: xml etree of the new inp.xml
    """
    #TODO create parameter
    tag_info = schema_dict['tag_info'][base_xpath]

    for key, val in attributedict.items():

        if key not in tag_info['complex'] | tag_info['simple'] | tag_info['attribs']:
            raise InputValidationError(
                f"The key '{key}' is not expected for this version of the input for the '{base_xpath.split('/')[-1]}' tag. "
                f"Allowed tags are: {sorted((tag_info['complex']|tag_info['simple']).original_case.values())}"
                f"Allowed attributes are: {sorted(tag_info['attribs'].original_case.values())}")

        key = (tag_info['complex'] | tag_info['simple'] | tag_info['attribs']).original_case[key]

        xpath_key = f'{xpath}/{key}'
        base_xpath_key = f'{base_xpath}/{key}'
        if key in tag_info['attribs']:
            xml_set_all_attribv(fleurinp_tree_copy, xpath, key, val)
        elif key in tag_info['text']:
            xml_set_all_text(fleurinp_tree_copy, xpath_key, val, create=True, tag_order=tag_info['order'])
        elif key in tag_info['simple'] and key not in tag_info['several']:  # only one tag with attributes
            if key in tag_info['optional']:  # This key might not be present
                eval_xpath3(fleurinp_tree_copy,
                            xpath_key,
                            create=True,
                            place_index=tag_info['order'].index(key),
                            tag_order=tag_info['order'])
            for attrib, value in val.items():
                if attrib not in schema_dict['tag_info'][base_xpath_key]['attribs']:
                    raise InputValidationError(
                        f"The key '{attrib}' is not expected for this version of the input for the '{key}' tag. "
                        f"Allowed attributes are: {sorted(schema_dict['tag_info'][base_xpath_key]['attribs'].original_case.values())}"
                    )
                attrib = schema_dict['tag_info'][base_xpath_key]['attribs'].original_case[attrib]
                xml_set_all_attribv(fleurinp_tree_copy, xpath_key, attrib, value)
        elif key in tag_info['simple'] and key in tag_info['several']:  #multiple tags but simple (i.e. only attributes)
            # policy: we DELETE all existing tags, and create new ones from the given parameters.
            existingtags = eval_xpath3(fleurinp_tree_copy, xpath_key)
            for tag in existingtags:
                parent = tag.getparent()
                parent.remove(tag)

            # there can be multiple tags, so I expect either one or a list
            if isinstance(val, dict):
                create_tag(fleurinp_tree_copy,
                           xpath,
                           key,
                           place_index=tag_info['order'].index(key),
                           tag_order=tag_info['order'])
                for attrib, value in val.items():
                    if attrib not in schema_dict['tag_info'][base_xpath_key]['attribs']:
                        raise InputValidationError(
                            f"The key '{attrib}' is not expected for this version of the input for the '{key}' tag. "
                            f"Allowed attributes are: {sorted(schema_dict['tag_info'][base_xpath_key]['attribs'].original_case.values())}"
                        )
                    attrib = schema_dict['tag_info'][base_xpath_key]['attribs'].original_case[attrib]
                    xml_set_all_attribv(fleurinp_tree_copy, xpath_key, attrib, value, create=True)
            else:  # I expect a list of dicts
                tags_need = len(val)
                for j in range(0, tags_need):
                    create_tag(fleurinp_tree_copy,
                               xpath,
                               key,
                               place_index=tag_info['order'].index(key),
                               tag_order=tag_info['order'])
                for i, tagdict in enumerate(val):
                    for attrib, value in tagdict.items():
                        if attrib not in schema_dict['tag_info'][base_xpath_key]['attribs']:
                            raise InputValidationError(
                                f"The key '{attrib}' is not expected for this version of the input for the '{key}' tag. "
                                f"Allowed attributes are: {sorted(schema_dict['tag_info'][base_xpath_key]['attribs'].original_case.values())}"
                            )
                        attrib = schema_dict['tag_info'][base_xpath_key]['attribs'].original_case[attrib]
                        sets = []
                        for k in range(len(eval_xpath2(fleurinp_tree_copy, xpath_key)) // tags_need):
                            sets.append(k * tags_need + i)
                        xml_set_attribv_occ(fleurinp_tree_copy, xpath_key, attrib, value, occ=sets)

        elif key not in tag_info['several']:  #Complex tag but only one (electronConfig)

            # eval and ggf create tag at right place.
            eval_xpath3(fleurinp_tree_copy,
                        xpath_key,
                        create=True,
                        place_index=tag_info['order'].index(key),
                        tag_order=tag_info['order'])

            fleurinp_tree_copy = set_complex_tag(fleurinp_tree_copy, schema_dict, base_xpath_key, xpath_key, val)

        else:

            # policy: we DELETE all existing tags, and create new ones from the given parameters.
            existingtags = eval_xpath3(fleurinp_tree_copy, xpath_key)
            for tag in existingtags:
                parent = tag.getparent()
                parent.remove(tag)
            if isinstance(val, dict):
                create_tag(fleurinp_tree_copy,
                           xpath,
                           key,
                           place_index=tag_info['order'].index(key),
                           tag_order=tag_info['order'])
                fleurinp_tree_copy = set_complex_tag(fleurinp_tree_copy, schema_dict, base_xpath_key, xpath_key, val)
            else:
                tags_need = len(val)
                for j in range(0, tags_need):
                    create_tag(fleurinp_tree_copy,
                               xpath,
                               key,
                               place_index=tag_info['order'].index(key),
                               tag_order=tag_info['order'])
                for i, tagdict in enumerate(val):
                    for k in range(len(eval_xpath2(fleurinp_tree_copy, xpath_key)) // tags_need):
                        fleurinp_tree_copy = set_complex_tag(fleurinp_tree_copy, schema_dict, base_xpath_key,
                                                             f'{xpath_key}[{k*tags_need+i}]', tagdict)
    return fleurinp_tree_copy
