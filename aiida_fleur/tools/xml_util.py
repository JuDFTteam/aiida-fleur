# -*- coding: utf-8 -*-
"""
In this module contains useful methods for handling xml trees and files which are used
by the Fleur code and the fleur plugin.
"""
__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
         "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


# TODO FEHLER meldungen, currently if a xpath expression is valid, but does not exists
# xpath returns []. Do we want this behavior?
# TODO finish implementation of create=False
# TODO: no aiida imports
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from lxml import etree
from lxml.etree import XMLSyntaxError

from aiida.common.exceptions import InputValidationError

#from somewhere import ValidationError/InputValidationError
#some error, that does not depend on aiida

def is_sequence(arg):
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))

##### CONVERTERS ############

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
            raise InputValidationError(
            "A string: {} for a boolean was given, which is not 'True',"
            " 'False', 't', 'T', 'F' or 'f'".format(stringbool))
    else:
        raise TypeError("convert_to_fortran_bool accepts only a string or "
                     "bool as argument")


def convert_to_fortran_bool(boolean):
    """
    Converts a Boolean as string to the format definded in the input

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
    elif isinstance(boolean, str):
        if boolean == 'True' or boolean == 't' or boolean == 'T':
            new_string = 'T'
            return new_string
        elif boolean == 'False' or boolean == 'f' or boolean == 'F':
            new_string = 'F'
            return new_string
        else:
            raise InputValidationError(
                "A string: {} for a boolean was given, which is not 'True',"
                "'False', 't', 'T', 'F' or 'f'".format(boolean))
    else:
         raise TypeError("convert_to_fortran_bool accepts only a string or "
                         "bool as argument, given {} ".format(boolean))

def convert_to_fortran_string(string):
    """
    converts some parameter strings to the format for the inpgen
    :param string: some string
    :returns: string in right format (extra "")
    """
    new_string = '"' + string + '"'
    return new_string
    '''
    if isinstance(string, str):
        new_string = '"' + string + '"'
        print new_string
        return new_string
        #if '"' in string:
        #    return new_string
        #else:
        #    new_string = '"' + string + '"'
        #    return new_string
    else:
        print (string)
        #return string
        raise TypeError("_convert_to_fortran_string accepts only a"
              "string as argument, type {} given".format(type(string)))
    '''


####### XML SETTERS GENERAL ##############

'''
def xml_set_xpath(xmltree, xpathn, value):
    """
    """
    root = xmltree.getroot()
    nodes = root.xpath(xpathn)

    if type(attribv) != type(''):
        attribv = str(attribv)
    for node in nodes:
        node.set(attributename, attribv)
'''
'''
def set_xpath(xmltree, xpath, value, create=False):
    """
    method to set a general xpath in an xml file
    """
    # does not work
    # set text?

    # set attribute?
    #print xpath
    #print value
    nodes = eval_xpath3(xmltree, xpathn, create=create)
    print nodes
    for node in nodes:
        node = value
'''
def xml_set_attribv_occ(xmltree, xpathn, attributename, attribv, occ=[0], create=False):
    """
    Routine sets the value of an attribute in the xml file on only the places
    specified in occ

    :param: an etree a xpath from root to the attribute and the attribute value
    :param: occ, list of integers
    :return: None, or an etree

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'band', 'T')
             xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'dos', 'F')
    """

    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpathn, create=create)
    #print 'nodes from xml_set_attribv_occ: {}'.format(nodes)
    if type(attribv) != type(''):
        attribv = str(attribv)
    for i, node in enumerate(nodes):
        if i in occ:
            node.set(attributename, attribv)
        if -1 in occ:# 'all'
            node.set(attributename, attribv)

def xml_set_first_attribv(xmltree, xpathn, attributename, attribv, create=False):
    """
    Routine sets the value of an attribute in the xml file

    :param: an etree a xpath from root to the attribute and the attribute value

    :return: None, or an etree

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'band', 'T')
             xml_set_first_attribv(tree, '/fleurInput/calculationSetup', 'dos', 'F')
    """

    root = xmltree.getroot()
    if type(attribv) == type(''):
        eval_xpath3(root, xpathn, create=create)[0].set(attributename, attribv)
    else:
        eval_xpath3(root, xpathn, create=create)[0].set(attributename, str(attribv))
    #return xmltree
    #ToDO check if worked. else exception,

def xml_set_all_attribv(xmltree, xpathn, attributename, attribv, create=False):
    """
    Routine sets the value of an attribute in the xml file on all places it occurs

    :param: an etree a xpath from root to the attribute and the attribute value

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
            if not isinstance(attribv[i], str):#type(attribv) != type(''):
                attribv[i] = str(attribv[i])
            node.set(attributename, attribv[i])
    else:
        if not isinstance(attribv, str):#type(attribv) != type(''):
            attribv = str(attribv)
        for node in nodes:
            node.set(attributename, attribv)

def xml_set_text(xmltree, xpathn, text, create=False, place_index=None, tag_order=None):
    """
    Routine sets the text of a tag in the xml file
    Input: an etree a xpath from root to the tag and the text
    Output: none, an etree
    example:
    xml_set_text(tree, '/fleurInput/comment', 'Test Fleur calculation for AiiDA plug-in')
    but also cordinates and Bravais Matrix!:
    xml_set_text(tree, '/fleurInput/atomGroups/atomGroup/relPos', '1.20000 PI/3 5.1-MYCrazyCostant')
    """

    root = xmltree.getroot()
    node = eval_xpath3(root, xpathn, create=create, place_index=place_index, tag_order=tag_order)
    #print node
    if node:
        node[0].text = text
    #return xmltree

def xml_set_all_text(xmltree, xpathn, text, create=False):
    """
    Routine sets the text of a tag in the xml file
    Input: an etree a xpath from root to the tag and the text
    Output: none, an etree
    example:
    xml_set_text(tree, '/fleurInput/comment', 'Test Fleur calculation for AiiDA plug-in')
    but also cordinates and Bravais Matrix!:
    xml_set_text(tree, '/fleurInput/atomGroups/atomGroup/relPos', '1.20000 PI/3 5.1-MYCrazyCostant')
    """
    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpathn, create=create)
    if is_sequence(text):
        for i, node in enumerate(nodes):
            node.text = text[i]
    else:
        for node in nodes:
            node.text = text

def create_tag(xmlnode, xpath, newelement, create=False, place_index = None, tag_order = None):
    """
    This method evaluates an xpath expresion and creates tag in an xmltree under the
    returned nodes. If the path does exist things will be overriden, or created.
    Per default the new element is appended to the elements, but it can also be
    inserted in a certain position or after certain other tags.

    """
    #root = xmltree.getroot()
    #print 'create_tag {} {} {} {} {} {}'.format(xmlnode, xpath, newelement, create, place_index, tag_order)
    if not etree.iselement(newelement):
        #print 'newelement from create_tag: {}'.format(newelement)
        #print 'xpath from create_tag: {}'.format(xpath)
        try:
            newelement = etree.Element(newelement)
        except ValueError as v:
            raise ValueError('{}. If this is a species, are you sure this species exists in your inp.xml?'.format(v))
    nodes = eval_xpath3(xmlnode, xpath, create=create, place_index=place_index, tag_order=tag_order)
    #print 'nodes found from create_tag: {}'.format(nodes)
    if nodes:
        for node_1 in nodes:
            if place_index:
                if tag_order:
                    print 'in tag_order'
                    # behind what shall I place it
                    behind_tags = tag_order[:place_index]
                    #children = node_1.getchildren()
                    #print children
                    # get all names of tag exisiting tags
                    set = False
                    #print reversed(behind_tags)
                    for tag in reversed(behind_tags):
                        #print tag
                        for child in node_1.iterchildren(tag=tag, reversed=False):
                            # if tagname of elements==tag:
                            tag_index = node_1.index(child)
                            #print child
                            #print tag_index
                            try:
                                node_1.insert(tag_index, newelement)
                            except ValueError as v:
                                raise ValueError('{}. If this is a species, are you sure this species exists in your inp.xml?'.format(v))
                            set = True
                            break
                        if set:
                            break
                    if not set: # just append
                        try:
                            node_1.append(newelement)
                        except ValueError as v:
                            raise ValueError('{}. If this is a species, are you sure this species exists in your inp.xml?'.format(v))
                    # (or remove all and write them again in right order?)
                else:
                    try:
                        node_1.insert(place_index, newelement)
                    except ValueError as v:
                        raise ValueError('{}. If this is a species, are you sure this species exists in your inp.xml?'.format(v))
                    #print 'in place_index'

            else:
                #print 'normal append'
                try:
                    node_1.append(newelement)
                except ValueError as v:
                    raise ValueError('{}. If this is a species, are you sure this species exists in your inp.xml?'.format(v))
    return xmlnode

def delete_att(xmltree, xpath, attrib):
    """
    deletes an xml tag in an xmletree in place

    param: xmltree: xmltree (etree)
    param: xpath: xpathexpression
    """
    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpath)
    if nodes:
        for node in nodes:
            try:
                del node.attrib[attrib]
            except:
                pass
    return xmltree

def delete_tag(xmltree, xpath):
    """
    deletes an xml tag in an xmletree in place

    param: xmltree: xmltree (etree)
    param: xpath: xpathexpression
    """
    root = xmltree.getroot()
    nodes = eval_xpath3(root, xpath)
    if nodes:
        for node in nodes:
            parent = node.getparent()
            parent.remove(node)
    return xmltree

def replace_tag(xmltree, xpath, newelement):
    """
    replaces a xml tag by another tag on an xmletree in place

    param: xmltree: xmltree (etree)
    param: xpath: xpathexpression
    param: newelement: xmlElement
    """
    root = xmltree.getroot()

    nodes = eval_xpath3(root, xpath)
    if nodes:
        for node in nodes:
            parent = node.getparent()
            parent.remove(node)
            parent.append(newelement)

    return xmltree

####### XML SETTERS SPECIAL ########

def set_species(fleurinp_tree_copy, species_name, attributedict, create=False):
    """
    Method to set parameters of a species tag of the fleur inp.xml file.

    param: fleurinp_tree_copy, xml etree of the inp.xml
    param: species_name : string, name of the species you want to change
    param: attributedict: python dict: what you want to change
    param: create: bool, if species does not exist create it and all subtags?

    raises: ValueError, if species name is non existent in inp.xml and should not be created.
    also if other given tags are garbage. (errors from eval_xpath() methods)

    return: fleurinp_tree_copy: xml etree of the new inp.xml


    """
    # TODO lowercase everything
    # TODO make a general specifier for species, not only the name i.e. also number, other parameters
    xpathspecies ='/fleurInput/atomSpecies/species[@name = "{}"]'.format(species_name)
    xpathmt = '{}/mtSphere'.format(xpathspecies)
    xpathatomicCutoffs = '{}/atomicCutoffs'.format(xpathspecies)
    xpathenergyParameters = '{}/energyParameters'.format(xpathspecies)
    xpathlo = '{}/lo'.format(xpathspecies)
    xpathelectronConfig = '{}/electronConfig'.format(xpathspecies)
    xpathcoreocc = '{}/electronConfig/stateOccupation'.format(xpathspecies)
    xpathLDA_U = '{}/ldaU'.format(xpathspecies)
    xpathnocoParams = '{}/nocoParams'.format(xpathspecies)
    xpathnocoParamsqss = '{}/nocoParams/qss'.format(xpathspecies)

    # can we get this out of schema file?
    species_seq = ['mtSphere', 'atomicCutoffs', 'energyParameters', 'force', 'electronConfig', 'nocoParams', 'ldaU', 'lo']

    #root = fleurinp_tree_copy.getroot()
    for key,val in attributedict.iteritems():
        if key == 'mtSphere': # always in inp.xml
            for attrib, value in val.iteritems():
                xml_set_attribv_occ(fleurinp_tree_copy, xpathmt, attrib, value)
        elif key == 'atomicCutoffs': # always in inp.xml
            for attrib, value in val.iteritems():
                xml_set_attribv_occ(fleurinp_tree_copy, xpathatomicCutoffs, attrib, value)
        elif key == 'energyParameters': # always in inp.xml
            for attrib, value in val.iteritems():
                xml_set_attribv_occ(fleurinp_tree_copy, xpathenergyParameters, attrib, value)
        elif key == 'lo': # optional in inp.xml
            #policy: we DELETE all LOs, and create new ones from the given parameters.
            existinglos = eval_xpath3(fleurinp_tree_copy, xpathlo)
            for los in existinglos:
                parent = los.getparent()
                parent.remove(los)

            # there can be multible LO tags, so I expect either one or a list
            if isinstance(val,dict):
                for attrib, value in val.iteritems():
                    xml_set_attribv_occ(fleurinp_tree_copy, xpathlo, attrib, value, create=create)
            else:# I expect a list of dicts
                #lonodes = eval_xpath3(root, xpathlo)#, create=True, place_index=species_seq.index('lo'), tag_order=species_seq)
                #nlonodes = len(lonodes)
                #print 'nlonodes:{}'.format(nlonodes)
                #ggf create more lo tags of needed
                los_need = len(val)# - nlonodes
                for j in range(0,los_need):
                    create_tag(fleurinp_tree_copy, xpathspecies, 'lo')#, place_index=species_seq.index('lo'), tag_order=species_seq)
                for i, lodict in enumerate(val):
                    for attrib, value in lodict.iteritems():
                        xml_set_attribv_occ(fleurinp_tree_copy, xpathlo, attrib, value, occ=[i])

        elif key == 'electronConfig':
            # eval electronConfig and ggf create tag at right place.
            #print 'index {}'.format(species_seq.index('electronConfig'))
            eval_xpath3(fleurinp_tree_copy, xpathelectronConfig, create=True, place_index=species_seq.index('electronConfig'), tag_order=species_seq)

            for tag in ['coreConfig', 'valenceConfig', 'stateOccupation']:
                for etag, edictlist in val.iteritems():
                    if not etag == tag:
                        continue
                    if etag=='stateOccupation':# there can be multiple times stateOccupation
                        #policy: default we DELETE all existing occs and create new ones for the given input!
                        existingocc = eval_xpath3(fleurinp_tree_copy, xpathcoreocc)
                        for occ in existingocc:
                            parent = occ.getparent()
                            parent.remove(occ)
                        if isinstance(edictlist,dict):
                            #print('here')
                            for attrib, value in edictlist.iteritems():
                                xml_set_attribv_occ(fleurinp_tree_copy, xpathcoreocc, attrib, value, create=create)
                        else:# I expect a list of dicts
                            #occnodes = eval_xpath3(root, xpathcoreocc)
                            #noccnodes = len(occnodes)
                            #ggf create more lo tags of needed
                            nodes_need = len(edictlist)# - noccnodes
                            for j in range(0,nodes_need):
                                create_tag(fleurinp_tree_copy, xpathelectronConfig, 'stateOccupation', create=create)
                            for i, occdict in enumerate(edictlist):
                                #override them one after one
                                for attrib, value in occdict.iteritems():
                                    xml_set_attribv_occ(fleurinp_tree_copy, xpathcoreocc, attrib, value, occ=[i])

                    else:
                        #print edictlist
                        xpathconfig = xpathelectronConfig + '/{}'.format(etag)
                        xml_set_text(fleurinp_tree_copy, xpathconfig, edictlist, create=create, place_index=species_seq.index('electronConfig'), tag_order = species_seq)
        elif key == 'nocoParams':
            for attrib, value in val.iteritems():
                if attrib == 'qss':
                    xml_set_text(fleurinp_tree_copy, xpathnocoParamsqss, attrib, value)
                else:
                   xml_set_attribv_occ(fleurinp_tree_copy, xpathnocoParams, attrib, value)
        elif key == 'ldaU':
            for attrib, value in val.iteritems():
                xml_set_attribv_occ(fleurinp_tree_copy, xpathLDA_U, attrib, value, create=create)
        else:
            xml_set_all_attribv(fleurinp_tree_copy, xpathspecies, attrib, value)

    return fleurinp_tree_copy

def add_lo(fleurinp_tree_copy, species_name, attributedict):
    pass


def change_atomgr_att(fleurinp_tree_copy, attributedict, position=None, species=None,create=False):

    xpathatmgroup = '/fleurInput/atomGroups/atomGroup'
    xpathforce = '{}/force'.format(xpathatmgroup)
    xpathnocoParams = '{}/nocoParams'.format(xpathatmgroup)

    if not position and not species: # not specfied what to change
        return fleurinp_tree_copy

    if position:
        if not position == 'all':
            xpathatmgroup ='/fleurInput/atomGroups/atomGroup/[/*Pos = {}]'.format(position)
            xpathforce = '{}/force'.format(xpathatmgroup)
            xpathnocoParams = '{}/nocoParams'.format(xpathatmgroup)
    if species:
        if not species == 'all':
            xpathatmgroup ='/fleurInput/atomGroups/atomGroup[@species = {}]'.format(species)
            xpathforce = '{}/force'.format(xpathatmgroup)
            xpathnocoParams = '{}/nocoParams'.format(xpathatmgroup)


    for key, val in attributedict.iteritems():
        if key == 'force':
            for attrib, value in val:
                xml_set_attribv_occ(fleurinp_tree_copy, xpathforce, attrib, value)
        elif key == 'nocoParams':
            for attrib, value in val:
                xml_set_attribv_occ(fleurinp_tree_copy, xpathnocoParams, attrib, value)
        else:
            xml_set_all_attribv(fleurinp_tree_copy, xpathatmgroup, attrib, value)



    return fleurinp_tree_copy

def add_num_to_att(xmltree, xpathn, attributename, set_val, mode='abs', occ=[0], create=False):
    """
    Routine adds something to the value of an attribute in the xml file (should be a number here)

    :param: an etree a xpath from root to the attribute and the attribute value

    :param: mode: 'abs', 'rel', change by absolut or relative amount
    :return: None, or an etree

    Comment: Element.set will add the attribute if it does not exist,
             xpath expression has to exist
    example: add_num_to_add(tree, '/fleurInput/bzIntegration', 'valenceElectrons', '1')
             add_num_to_add(tree, '/fleurInput/bzIntegration', 'valenceElectrons', '1.1', mode='rel')
    """


    #get attribute, add or multiply
    #set attribute
    attribval_node = eval_xpath(xmltree, xpathn)
    # do some checks..
    attribval = get_xml_attribute(attribval_node, attributename)
    print(attribval)
    if attribval:
        if mode=='abs':
            newattribv = float(attribval) + float(set_val)
        elif mode == 'rel':
            newattribv = float(attribval) * float(set_val)
        else:
            pass
            #unknown mode

        xml_set_attribv_occ(xmltree, xpathn, attributename, newattribv, occ=[0], create=False)
    else:
        pass
        # something was wrong, ...
    return xmltree

####### XML GETTERS #########
# TODO parser infos do not really work, might need to be returned, here
def eval_xpath(node, xpath, parser_info={'parser_warnings':[]}):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns either nodes, or attributes, or text
    """
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        parser_info['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n'
            'Either it does not exist, or something is wrong with the expression.'.format(xpath))
        # TODO maybe raise an error again to catch in upper routine, to know where exactly
        return []
    if len(return_value) == 1:
        return return_value[0]
    else:
        return return_value


def eval_xpath2(node, xpath, parser_info={'parser_warnings':[]}):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns either nodes, or attributes, or text
    """
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        parser_info['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n'
            'Either it does not exist, or something is wrong with the expression.'.format(xpath))
        # TODO maybe raise an error again to catch in upper routine, to know where exactly
        return []
    return return_value


'''
def eval_xpath2(node, xpath):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns ALWAYS a node list
    """
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        print(
            'There was a XpathEvalError on the xpath: {} \n Either it does '
            'not exist, or something is wrong with the expression.'
            ''.format(xpath))
        return []
    return return_value
'''
def eval_xpath3(node, xpath, create=False, place_index=None, tag_order=None):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns ALWAYS a node list
    """
    #print('call eval_xpath3')
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        message = (
            'There was a XpathEvalError on the xpath: {} \n Either it does '
            'not exist, or something is wrong with the expression.'
            ''.format(xpath))
        raise etree.XPathEvalError(message)
        return []

    if return_value == []:
        if create:
            #print node, xpath, create
            x_pieces =  [e for e in xpath.split('/') if e != ""]
            #x_pieces = xpath.split('/')
            xpathn = ''
            #for piece in x_pieces[:-1]:
            #    piece = piece + '/'
            #    xpathn = xpathn + piece
            #print x_pieces
            for piece in x_pieces[:-1]:
                xpathn = xpathn + '/'+ piece
            #print 'xpathn: {}'.format(xpathn)
            #node_c = eval_xpath3(node, xpathn, create)
            # this is REKURSIV! since create tag calls eval_xpath3
            create_tag(node, xpathn, x_pieces[-1], create=create, place_index=place_index, tag_order=tag_order)
            return_value = node.xpath(xpath)
            #print 'return:{}'.format(return_value)
            return return_value
        else:
            return return_value
    else:
        return return_value


def get_xml_attribute(node, attributename, parser_info_out={}):
    """
    Get an attribute value from a node.

    :param node: a node from etree
    :param attributename: a string with the attribute name.
    :returns either attributevalue, or None
    """
    if etree.iselement(node):
        attrib_value = node.get(attributename)
        if attrib_value:
            return attrib_value
        else:
            if parser_info_out:
                parser_info_out['parser_warnings'].append(
                    'Tried to get attribute: "{}" from element {}.\n '
                    'I recieved "{}", maybe the attribute does not exist'
                    ''.format(attributename, node, attrib_value))
            else:
                print(
                    'Can not get attributename: "{}" from node "{}", '
                    'because node is not an element of etree.'
                    ''.format(attributename, node))
            return None
    else: # something doesn't work here, some nodes get through here
        if parser_info_out:
            parser_info_out['parser_warnings'].append(
                'Can not get attributename: "{}" from node "{}", '
                'because node is not an element of etree.'
                ''.format(attributename, node))
        else:
            print(
                'Can not get attributename: "{}" from node "{}", '
                'because node is not an element of etree.'
                ''.format(attributename, node))
        return None




# TODO this has to be done better. be able to write tags and
# certain attributes of attributes that occur possible more then once.
# HINT: This is not really used anymore. use fleurinpmodifier
def write_new_fleur_xmlinp_file(inp_file_xmltree, fleur_change_dic, xmlinpstructure):
    """
    This modifies the xml-inp file. Makes all the changes wanted by
    the user or sets some default values for certain modes

    :param inp_file_lines_o xml-tree of the xml-inp file
    :param fleur_change_dic dictionary {attrib_name : value} with all the
           wanted changes.

    return an etree of the xml-inp file with changes.
    """
    # TODO rename, name is misleaded just changes the tree.
    xmltree_new = inp_file_xmltree

    #get all attributes of a inpxml file
    #xmlinpstructure = get_inpxml_file_structure()

    pos_switch_once = xmlinpstructure[0]
    pos_switch_several = xmlinpstructure[1]
    pos_attrib_once = xmlinpstructure[2]
    #pos_int_attributes_once = xmlinpstructure[3]
    pos_float_attributes_once = xmlinpstructure[4]
    #pos_string_attributes_once = xmlinpstructure[5]
    pos_attrib_several = xmlinpstructure[6]
    pos_int_attributes_several = xmlinpstructure[7]
    #pos_float_attributes_several = xmlinpstructure[8]
    #pos_string_attributes_several = xmlinpstructure[9]
    #pos_tags_several = xmlinpstructure[10]
    pos_text = xmlinpstructure[11]
    pos_xpaths = xmlinpstructure[12]
    expertkey = xmlinpstructure[13]


    for key in fleur_change_dic:
        if key in pos_switch_once:
            # call routine set (key,value) in tree.
            # TODO: a test here if path is plausible and if exist
            # ggf. create tags and key.value is 'T' or 'F' if not convert,
            # if garbage, exception
            # convert user input into 'fleurbool'
            fleur_bool = convert_to_fortran_bool(fleur_change_dic[key])

            xpath_set = pos_xpaths[key]
            #TODO: check if something in setup is inconsitent?

            # apply change to tree
            #print xmltree_new, xpath_set, key, fleur_bool
            xml_set_first_attribv(xmltree_new, xpath_set, key, fleur_bool)

        elif key in pos_attrib_once:
            # TODO: same here, check existance and plausiblility of xpath
            xpath_set = pos_xpaths[key]
            #print xmltree_new, xpath_set, key, fleur_change_dic[key]
            if key in pos_float_attributes_once:
                newfloat = '{:.10f}'.format(fleur_change_dic[key])
                xml_set_first_attribv(xmltree_new, xpath_set, key, newfloat)
            else:
                xml_set_first_attribv(xmltree_new, xpath_set, key, fleur_change_dic[key])
        elif key in pos_attrib_several:
            # TODO What attribute shall be set? all, one or several specific onces?
            pass
        elif key in pos_switch_several:
            # TODO
            pass
        elif key in pos_text:
            # can be several times, therefore check
            xpath_set = pos_xpaths[key]
            xml_set_text(xmltree_new, xpath_set, fleur_change_dic[key])
        elif key == expertkey:
            # posibility for experts to set something, not suported by the plug-in directly
            pass
        else:
            # this key is not know to plug-in
            raise InputValidationError(
                "You try to set the key:'{}' to : '{}', but the key is unknown"
                " to the fleur plug-in".format(key, fleur_change_dic[key]))
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
    #pos_attrib_once1 = xmlstructure[2]
    int_attributes_once1 = xmlstructure[3]
    float_attributes_once1 = xmlstructure[4]
    string_attributes_once1 = xmlstructure[5]
    #pos_attrib_several1 = xmlstructure[6]
    int_attributes_several1 = xmlstructure[7]
    float_attributes_several1 = xmlstructure[8]
    string_attributes_several1 = xmlstructure[9]
    tags_several1 = xmlstructure[10]
    pos_text1 = xmlstructure[11]
    #pos_xpaths1 = xmlstructure[12]
    #expertkey1 = xmlstructure[13]

    return_dict = {}
    if parent.items():
        return_dict = dict(parent.items())
        # Now we have to convert lazy fortan style into pretty things for the Database
        for key in return_dict:
            if key in pos_switch_once1 or (key in pos_switch_several1):
                return_dict[key] = convert_from_fortran_bool(return_dict[key])

            elif key in int_attributes_once1 or (key in int_attributes_several1):
                # TODO int several
                return_dict[key] = int(return_dict[key])
            elif key in string_attributes_once1 or (key in string_attributes_several1):
                # TODO What attribute shall be set? all, one or several specific onces?
                return_dict[key] = str(return_dict[key])
            elif key in float_attributes_once1 or (key in float_attributes_several1):
                # TODO pressision?
                return_dict[key] = float(return_dict[key])
                #pass
            elif key in pos_text1:
                # TODO, prob not nessesary, since taken care of below check,
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


    if parent.text: # TODO more detal, exp: relPos
        # has text, but we don't want all the '\n' s and empty stings in the database
        if parent.text.strip() != '': # might not be the best solution
            # set text
            return_dict = parent.text.strip()

    firstocc = True
    for element in parent:
        if element.tag in tags_several1:
            #make a list, otherwise the tag will be overwritten in the dict
            if firstocc: # is this the first occurence?
                #create a list
                return_dict[element.tag] = []
                return_dict[element.tag].append(inpxml_todict(element, xmlstructure))
                firstocc = False
            else: # occured before, a list already exists, therefore just add
                return_dict[element.tag].append(inpxml_todict(element, xmlstructure))
        else:
            #make dict
            return_dict[element.tag] = inpxml_todict(element, xmlstructure)

    return return_dict



# TODO this should be replaced by something else, maybe a class. that has a method to return certain
# list of possible xpaths from a schema file, or to validate a certain xpath expression and
# to allow to get SINGLE xpaths for certain attrbiutes.
#  akk: tell me where 'DOS' is
# This might not be back compatible... i.e a certain plugin version will by this design only work with
#  certain schema version
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
    :return all_attrib_xpath: dictonary (attrib, xpath), of all possible attributes
                              with their xpath expression for the xmp inp
    :return expertkey: keyname (should not be in any other list), which can be
                       used to set anything in the file, by hand,
     (for experts, and that plug-in does not need to be directly maintained if
     xmlinp gets a new switch)
    """

    # All attributes (allowed to change?)

    #switches can be 'T' ot 'F' # TODO: alphabetical sorting
    all_switches_once = (
        'dos', 'band', 'secvar', 'ctail', 'frcor', 'l_noco',
        'ctail', 'swsp', 'lflip', 'off', 'spav', 'l_soc', 'soc66', 'pot8',
        'eig66', 'gamma', 'gauss', 'tria', 'invs', 'invs2', 'zrfs', 'vchk', 'cdinf',
        'disp', 'vacdos', 'integ', 'star', 'iplot', 'score', 'plplot', 'slice',
        'pallst', 'form66', 'eonly', 'bmt', 'relativisticCorrections', 'l_J', 'l_f')

    all_switches_several = ('calculate', 'flipSpin')

    int_attributes_once = ('numbands', 'itmax', 'maxIterBroyd', 'kcrel', 'jspins',
                           'gw', 'isec1', 'nx', 'ny', 'nz', 'ndir', 'layers',
                           'nstars', 'nstm', 'numkpt', 'nnne', 'lpr', 'count')
    float_attributes_once = ('Kmax', 'Gmax', 'GmaxXC', 'alpha', 'spinf', 'minDistance', 'theta',
                             'phi', 'xa', 'thetad', 'epsdisp', 'epsforce',
                             'valenceElectrons', 'fermiSmearingEnergy', 'ellow',
                             'elup', 'scale', 'dTilda', 'dVac', 'minEnergy',
                             'maxEnergy', 'sigma', 'locx1', 'locy1', 'locx2',
                             'locy2', 'tworkf', 'minEigenval', 'maxEigenval')
    string_attributes_once = ('imix', 'mode', 'filename', 'latnam', 'spgrp',
                              'xcFunctional', 'fleurInputVersion', 'species')



    other_attributes_once = tuple(list(int_attributes_once) + list(float_attributes_once) + list(string_attributes_once))
    #print other_attributes_once
    other_attributes_once1 = (
        'isec1', 'Kmax', 'Gmax', 'GmaxXC', 'numbands', 'itmax', 'maxIterBroyd',
        'imix', 'alpha', 'spinf', 'minDistance',
 'kcrel', 'jspins', 'theta', 'phi', 'gw', 'lpr',
        'xa', 'thetad', 'epsdisp', 'epsforce', 'valenceElectrons', 'mode',
        'gauss', 'fermiSmearingEnergy', 'nx', 'ny', 'nz', 'ellow', 'elup',
        'filename', 'scale', 'dTilda', 'dVac', 'ndir', 'minEnergy', 'maxEnergy',
        'sigma', 'layers', 'nstars', 'locx1', 'locy1', 'locx2', 'locy2', 'nstm',
        'tworkf', 'numkpt', 'minEigenval', 'maxEigenval', 'nnne')


    int_attributes_several = ('atomicNumber', 'gridPoints', 'lmax', 'lnonsphr',
                              's', 'p', 'd', 'f', 'l', 'n', 'eDeriv', 'coreStates')
    float_attributes_several = ('value', 'magMom', 'radius', 'logIncrement')
    string_attributes_several = ('name', 'element', 'coreStates', 'type', 'relaxXYZ')
    other_attributes_several = (
        'name', 'value', 'element', 'atomicNumber', 'coreStates', 'magMom',
        'radius', 'gridPoints', 'logIncrement', 'lmax', 'lnonsphr', 's', 'p',
        'd', 'f', 'species', 'type', 'coreStates', 'l', 'n', 'eDeriv', 'relaxXYZ')

    # when parsing the xml file to a dict, these tags should become
    # list(sets, or tuples) instead of dictionaries.
    tags_several = ('atomGroup', 'relPos', 'absPos', 'filmPos', 'species', 'kPoint')

    all_text = {'comment' : 1, 'relPos' : 3, 'filmPos' : 3, 'absPos' : 3,
                'row-1': 3, 'row-2':3, 'row-3' :3, 'a1': 1}
    #TODO all these (without comment) are floats, or float tuples.
    #Should be converted to this in the databas
    # changing the Bravais matrix should rather not be allowed I guess

    # all attribute xpaths

    #text xpaths(coordinates, bravaisMatrix)
    #all switches once, several, all attributes once, several
    all_attrib_xpath = {# text
        'comment': '/fleurInput/comment',
        'relPos': '/fleurInput/atomGroups/atomGroup/relPos',
        'filmPos': '/fleurInput/atomGroups/atomGroup/filmPos',
        'absPos': '/fleurInput/atomGroups/atomGroup/absPos',
        'row-1': '/fleurInput/cell/bulkLattice/bravaisMatrix',
        'row-2': '/fleurInput/cell/bulkLattice/bravaisMatrix',
        'row-3': '/fleurInput/cell/bulkLattice/bravaisMatrix',
        'a1': '/fleurInput/cell/filmLattice/a1', #switches once
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
        'relativisticCorrections': '/fleurInput/xcFunctional', #ALL_Switches_several
        'calculate': '/fleurInput/atomGroups/atomGroup/force',
        'flipSpin' : '/fleurInput/atomSpecies/species', #other_attributes_once
        'Kmax' : '/fleurInput/calculationSetup/cutoffs',
        'Gmax' : '/fleurInput/calculationSetup/cutoffs',
        'GmaxXC': '/fleurInput/calculationSetup/cutoffs',
        'numbands': '/fleurInput/calculationSetup/cutoffs',
        'itmax' : '/fleurInput/calculationSetup/scfLoop',
        'minDistance' : '/fleurInput/calculationSetup/scfLoop',
        'maxIterBroyd': '/fleurInput/calculationSetup/scfLoop',
        'imix': '/fleurInput/calculationSetup/scfLoop',
        'alpha': '/fleurInput/calculationSetup/scfLoop',
        'spinf': '/fleurInput/calculationSetup/scfLoop',
        'kcrel': '/fleurInput/calculationSetup/coreElectrons',
        'jspins': '/fleurInput/calculationSetup/magnetism',
        'theta': '/fleurInput/calculationSetup/soc',
        'phi' : '/fleurInput/calculationSetup/soc',
        'gw': '/fleurInput/calculationSetup/expertModes',
        'lpr': '/fleurInput/calculationSetup/expertModes',
        'isec1': '/fleurInput/calculationSetup/expertModes',
        'xa': '/fleurInput/calculationSetup/geometryOptimization',
        'thetad': '/fleurInput/calculationSetup/geometryOptimization',
        'epsdisp': '/fleurInput/calculationSetup/geometryOptimization',
        'epsforce': '/fleurInput/calculationSetup/geometryOptimization',
        'valenceElectrons':'/fleurInput/calculationSetup/bzIntegration',
        'mode': '/fleurInput/calculationSetup/bzIntegration',
        'fermiSmearingEnergy': '/fleurInput/calculationSetup/bzIntegration',
        'nx': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'ny': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'nz': '/fleurInput/calculationSetup/bzIntegration/kPointMesh',
        'count': '/fleurInput/calculationSetup/kPointCount',
        'ellow' : '/fleurInput/calculationSetup/energyParameterLimits',
        'elup': '/fleurInput/calculationSetup',
        'filename': '/fleurInput/cell/symmetryFile',
        'scale': '/fleurInput/cell/bulkLattice',
        'ndir': '/fleurInput/output/densityOfStates',
        'minEnergy': '/fleurInput/output/densityOfStates',
        'maxEnergy': '/fleurInput/output/densityOfStates',
        'sigma':' /fleurInput/output/densityOfStates',
        'layers': '/fleurInput/output/vacuumDOS',
        'nstars': '/fleurInput/output/vacuumDOS',
        'locx1': '/fleurInput/output/vacuumDOS',
        'locy1': '/fleurInput/output/vacuumDOS',
        'locx2': '/fleurInput/output/vacuumDOS',
        'locy2': '/fleurInput/output/vacuumDOS',
        'nstm': '/fleurInput/output/vacuumDOS',
        'tworkf': '/fleurInput/output/vacuumDOS',
        'numkpts': '/fleurInput/output/chargeDensitySlicing',
        'minEigenval': '/fleurInput/output/chargeDensitySlicing',
        'maxEigenval': '/fleurInput/output/chargeDensitySlicing',
        'nnne': '/fleurInput/output/chargeDensitySlicing',
        'dVac': '/fleurInput/cell/filmLattice',
        'dTilda': '/fleurInput/cell/filmLattice',
        'xcFunctional': '/fleurInput/xcFunctional/@name',#other_attributes_more
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
        'relaxXYX': '/fleurInput/atomGroups/atomGroup/force'
    }
    #'constant': (name, value)
    #'xcFunctional' : name
    #'species' : (old_name, set_name)
    #'radius': (spcies_name, value), (species_id, value), (species_element, value)
    # all tags paths, make this a dict?

    all_tag_xpaths = (
        '/fleurInput/constantDefinitions',
        '/fleurInput/calculationSetup',
        '/fleurInput/calculationSetup/cutoffs',
        '/fleurInput/calculationSetup/scfLoop',
        '/fleurInput/calculationSetup/coreElectrons',
        '/fleurInput/calculationSetup/magnetism',
        '/fleurInput/calculationSetup/soc',
        '/fleurInput/calculationSetup/expertModes',
        '/fleurInput/calculationSetup/geometryOptimization',
        '/fleurInput/calculationSetup/bzIntegration',
        '/fleurInput/calculationSetup/kPointMesh',
        '/fleurInput/cell/symmetry',
        '/fleurInput/cell/bravaisMatrix',
        '/fleurInput/xcFunctional',
        '/fleurInput/xcFunctional/xcParams',
        '/fleurInput/atomSpecies/species',
        '/fleurInput/atomSpecies/species/mtSphere',
        '/fleurInput/atomSpecies/species/atomicCutoffs',
        '/fleurInput/atomSpecies/species/energyParameters',
        '/fleurInput/atomSpecies/species/coreConfig',
        '/fleurInput/atomSpecies/species/coreOccupation',
        '/fleurInput/atomGroups/atomGroup',
        '/fleurInput/atomGroups/atomGroup/relPos',
        '/fleurInput/atomGroups/atomGroup/absPos',
        '/fleurInput/atomGroups/atomGroup/filmPos',
        '/fleurInput/output/checks',
        '/fleurInput/output/densityOfStates',
        '/fleurInput/output/vacuumDOS',
        '/fleurInput/output/plotting',
        '/fleurInput/output/chargeDensitySlicing',
        '/fleurInput/output/specialOutput'
    )

    expertkey = 'other'
    returnlist = (all_switches_once,
                  all_switches_several,
                  other_attributes_once,
                  int_attributes_once,
                  float_attributes_once,
                  string_attributes_once,
                  other_attributes_several,
                  int_attributes_several,
                  float_attributes_several,
                  string_attributes_several,
                  tags_several,
                  all_text,
                  all_attrib_xpath,
                  expertkey)
    return returnlist


