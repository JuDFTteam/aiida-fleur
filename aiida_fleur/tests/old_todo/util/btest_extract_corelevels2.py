#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
from six.moves import range
if not is_dbenv_loaded():
    load_dbenv()
import sys, os
from lxml import etree, objectify
from lxml.etree import XMLSyntaxError, XPathEvalError
from pprint import pprint
from aiida.plugins import Code, DataFactory, CalculationFactory
from aiida.orm import Computer
from aiida.orm import load_node
from aiida_fleur.calculation.fleur import FleurCalculation as FleurCalc
from pprint import pprint

StructureData = DataFactory('structure')
ParameterData = DataFactory('dict')
KpointsData = DataFactory('array.kpoints')

FleurInpCalc = CalculationFactory('fleur.inpgen')

import time
start_time = time.time()

##
#calculation to extract from:
# either from list given here or system argument

calcs_pks = []
#calcs_pks = [1464, 1462, 1399, 1403]#, 1059]#, 1414
####
if not calcs_pks:
    try:
        for arg in sys.argv[1:]:
            calc_t = arg
            calcs_pks.append(int(calc_t))
    except:
        pass
#####

# check if calculation pks belong to successful fleur calculations
for pk in calcs_pks:
    calc = load_node(pk)
    if (not isinstance(calc, FleurCalc)):
        raise ValueError('Calculation with pk {} must be a FleurCalculation'.format(pk))
    if calc.get_state() != 'FINISHED':
        raise ValueError('Calculation with pk {} must be in state FINISHED'.format(pk))

parser_info = {'parser_warnings': [], 'unparsed': []}


def extrac_corelevels(outxml):
    """
    main routine extras corelevels out of out.xml files
    """
    ##########################################
    #1. read out.xml in etree

    #2. get all species
    #3. get number of atom types and their species

    #4 get corelevel dimension from atoms types.

    #5 init saving arrays:
    #list length number of atom types, which contains dictionaries:
    # in the form { 'species' : species, 'coresetup' : '', 'atom' : W , 'corelevels' : []} lists of corelevels from last iteration (Do i want all iterations, optional?) Or do I even want a dictionaries of corelevels? (but coresetup is in atom type info

    #6 parse corelevels:
    # get last iteration
    # fill corelevel list
    #######################################

    #1. read out.xml in etree
    parsed_data = {}
    outfile_broken = False
    parse_xml = True
    parser = etree.XMLParser(recover=False)  #, remove_blank_text=True)

    try:
        tree = etree.parse(outxmlfile, parser)
    except etree.XMLSyntaxError:
        outfile_broken = True
        #print 'broken xml'
        parser_info['parser_warnings'].append('The out.xml file is broken I try to repair it.')

    if outfile_broken:
        #repair xmlfile and try to parse what is possible.
        parser = etree.XMLParser(recover=True)  #, remove_blank_text=True)
        try:
            tree = etree.parse(outxmlfile, parser)
        except etree.XMLSyntaxError:
            print('here')
            parser_info['parser_warnings'].append(
                'Skipping the parsing of the xml file. Repairing was not possible.'
            )
            parse_xml = False

    #if parse_xml:
    root = tree.getroot()

    # 2. get all species
    # get element, name, coreStates
    species_nodes = eval_xpath(root, '/fleurOutput/atomSpecies')  #/fleurinp/
    species_atts = {}
    species_names = []
    for species in species_nodes:
        print(species)
        species_name = species.get('name')
        species_corestates = species.get('coreStates')
        species_element = species.get('element')
        species_atomicnumber = species.get('atomicNumber')
        species_magMom = species.get('magMom')
        species_atts[species_name] = {
            'name': species_name,
            'corestates': species_corestates,
            'element': species_element,
            'atomgroups': [],
            'mag_mom': species_magMom,
            'atomic_number': species_atomicnumber
        }
        species_names.append(species_name)
        #species_atts.append(species_att)
    nspecies = len(species_nodes)

    #3. get number of atom types and their species
    atomtypes = []
    atomgroup_nodes = eval_xpath(root, '/fleurOutput/atomGroups')  #/fleurinp/
    for atomgroup in atomgroup_nodes:
        types_dict = {}
        group_species = atomgroup.get('species')
        if group_species in species_names:
            species_atts[group_species]['atomgroups'].append(atomgroup)
        types_dict = {'species': group_species, 'coresetup': '', 'corelevels': []}
        atomtypes.append(types_dict)

    natomgroup = len(atomgroup_nodes)
    #print natomgroup, nspecies
    #print species_names
    corelevels = []

    #4 get corelevel dimension from atoms types.
    #5 init saving arrays:

    #6 parse corelevels:
    #parse last iteration only
    coreStates_xpath = 'coreStates'
    iteration_nodes = eval_xpath(root, '/fleurOutput/scfLoop/iteration')
    nIteration = len(iteration_nodes)
    if nIteration >= 1:
        iteration_to_parse = iteration_nodes[-1]
        #print iteration_to_parse
        corestatescards = eval_xpath(iteration_to_parse, coreStates_xpath)
        #print corestatescards
        # what is the spin.
        #spin = 1
        for type in atomtypes:
            corelevels.append([])
            #if spin == 1:
            #    corelevels.append([])
            #if spin == 2:
            #    corelevels.append([[],[]])
        for corestatescard in corestatescards:
            #print 'here'
            #print corestatescard
            corelv = parse_state_card(corestatescard, iteration_to_parse)
            corelevels[int(corelv['atomtype']) - 1].append(corelv)
            #corelevels.append(corelv)
    print(parser_info)
    #pprint(corelevels)
    #pprint(corelevels[0][1]['corestates'][2]['energy'])
    #corelevels[atomtypeNumber][spin]['corestates'][corestate number][attribute]
    return corelevels


def parse_state_card(corestateNode, iteration_node):
    """
    Parses the ONE core state card

    :param iteration_node: an etree element, iteration node
    :param jspin : integer 1 or 2
    """
    ##### all xpath of density convergence card (maintain) ########
    coreStates_xpath = 'coreStates'
    state_xpath = 'state'

    units_name = 'units'
    value_name = 'value'
    distance_name = 'distance'

    n_name = 'n'
    j_name = 'j'
    l_name = 'l'
    energy_name = 'energy'
    weight_name = 'weight'
    spin_name = 'spin'
    kinEnergy_name = 'kinEnergy'
    eigenvalueSum_name = 'eigenvalueSum'
    lostElectrons_name = 'lostElectrons'
    atomtype_name = 'atomType'
    #######

    atomtype = get_xml_attribute(corestateNode, atomtype_name)

    kinEnergy = get_xml_attribute(corestateNode, kinEnergy_name)
    vE2, suc = convert_to_float(kinEnergy)

    eigenvalueSum = get_xml_attribute(corestateNode, eigenvalueSum_name)
    vE2, suc = convert_to_float(eigenvalueSum)

    spin = get_xml_attribute(corestateNode, spin_name)
    #states = corestateNode.xpath(
    #for state in states:

    # get all corestate tags, (atomtypes * spin)
    corestateNodes = eval_xpath(iteration_node, coreStates_xpath)
    # for every corestate tag parse the attributes

    # some only the first interation, then get all state tags of the corestate tag (atom depended)
    # parse each core state #Attention to spin
    states = []
    corestates = eval_xpath(corestateNode, state_xpath)
    for corestate in corestates:
        state_dict = {}
        n_state = get_xml_attribute(corestate, n_name)
        l_state = get_xml_attribute(corestate, l_name)
        j_state = get_xml_attribute(corestate, j_name)
        energy, suc = convert_to_float(get_xml_attribute(corestate, energy_name))
        weight, suc = convert_to_float(get_xml_attribute(corestate, weight_name))
        state_dict = {'n': n_state, 'l': l_state, 'j': j_state, 'energy': energy, 'weight': weight}
        states.append(state_dict)

    #pprint(states)

    core_states = {
        'eigenvalue_sum': eigenvalueSum,
        'corestates': states,
        'spin': spin,
        'kin_energy': kinEnergy,
        'atomtype': atomtype
    }
    #pprint(core_states)
    return core_states


def eval_xpath(node, xpath):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns either nodes, or attributes, or text
    """
    try:
        return_value = node.xpath(xpath)
    except XPathEvalError:
        parser_info['parser_warnings'].append(
            'There was a XpathEvalError on the xpath: {} \n'
            'Either it does not exist, or something is wrong with the expression.'.format(xpath)
        )
        # TODO maybe raise an error again to catch in upper routine, to know where exactly
        return []
    if len(return_value) == 1:
        return return_value[0]
    else:
        return return_value


def convert_to_float(value_string):
    """
    Tries to make a float out of a string. If it can't it logs a warning
    and returns True or False if convertion worked or not.

    :param value_string: a string
    :returns value: the new float or value_string: the string given
    :retruns True or False
    """
    try:
        value = float(value_string)
    except TypeError:
        parser_info['parser_warnings'].append(
            'Could not convert: "{}" to float, TypeError'.format(value_string)
        )
        return value_string, False
    except ValueError:
        parser_info['parser_warnings'].append(
            'Could not convert: "{}" to float, ValueError'.format(value_string)
        )
        return value_string, False
    return value, True


def get_xml_attribute(node, attributename):
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
            parser_info['parser_warnings'].append(
                'Tried to get attribute: "{}" from element {}.\n '
                'I recieved "{}", maybe the attribute does not exist'.format(
                    attributename, node, attrib_value
                )
            )
            return None
    else:  # something doesn't work here some nodes get through here
        parser_info['parser_warnings'].append(
            'Can not get attributename: "{}" from node "{}", because node is not an element of etree.'
            .format(attributename, node)
        )
        return None


### call
test_outxmlfiles = [
    './out.xml', './test_outxml/outCuF.xml', './test_outxml/outFe.xml', './test_outxml/outHg.xml',
    './test_outxml/outO.xml'
]
outxmlfile = test_outxmlfiles[2]

corelevels = extrac_corelevels(outxmlfile)
for i in range(0, len(corelevels[0][1]['corestates'])):
    print(corelevels[0][1]['corestates'][i]['energy'])

for calc in calcs_pks:
    pass
    # get out.xml file of calculation
    outxml = load_node(pk).out.retrieved.folder.get_abs_path('out.xml')
    extrac_corelevels(outxml)

print(('--- %s seconds ---' % (time.time() - start_time)))
