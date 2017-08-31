#!/usr/bin/env python
"""
In this module you find methods to parse/extract corelevel shifts from an 
out.xml file of FLEUR. 
"""
# TODO clean up
# TODO together with xml_util, parser info handling, has to be also a return value of everything
# or rather throw exception on lowest level and catch at higher levels? 
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys#,os
from lxml import etree#, objectify
from lxml.etree import XMLSyntaxError, XPathEvalError
from pprint import pprint
from aiida.orm import DataFactory, CalculationFactory
#from aiida.orm import Computer
from aiida.orm import load_node
from aiida_fleur.tools.xml_util import get_xml_attribute, eval_xpath, eval_xpath2
#convert_to_float

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')

FleurInpCalc = CalculationFactory('fleur.inpgen')
FleurCalc = CalculationFactory('fleur.fleur')


#import time
#start_time = time.time()

##
#calculation to extract from:
# either from list given here or system argument

#calcs_pks = []
#calcs_pks = [1464, 1462, 1399, 1403]#, 1059]#, 1414
####
#if not calcs_pks:
#    try:
#        for arg in sys.argv[1:]:
#            calc_t = arg
#            calcs_pks.append(int(calc_t))
#    except:
#        pass
#####

'''
# check if calculation pks belong to successful fleur calculations
for pk in calcs_pks:
    calc = load_node(pk)
    if (not isinstance(calc, FleurCalc)):
        raise ValueError("Calculation with pk {} must be a FleurCalculation".format(pk))
    if calc.get_state() != 'FINISHED':
        raise ValueError("Calculation with pk {} must be in state FINISHED".format(pk))
'''
def extract_lo_energies(outxmlfile, options=None):
    pass
    #TODO: how? out of DOS?



def extract_corelevels(outxmlfile, options=None):
    """ 
    Extras corelevels out of out.xml files
    
    param: outxmlfile path to out.xml file
    
    param: options, dict: 'iteration' : X/'all'
    return: corelevels, list of the form
             [atomtypes][spin][dict={atomtype : '', corestates : list_of_corestates}] 
             [atomtypeNumber][spin]['corestates'][corestate number][attribute]
    get corelevel energy of first atomtype, spin1, corelevels[0][0]['corestates'][i]['energy']                                  
    example::
    
    [[{'atomtype': '     1',
   'corestates': [{'energy': -3.6489930627,
                   'j': ' 0.5',
                   'l': ' 0',
                   'n': ' 1',
                   'weight': 2.0}],
   'eigenvalue_sum': '     -7.2979861254',
   'kin_energy': '     13.4757066163',
   'spin': '1'}],
 [{'atomtype': '     2',
   'corestates': [{'energy': -3.6489930627,
                   'j': ' 0.5',
                   'l': ' 0',
                   'n': ' 1',
                   'weight': 2.0}],
   'eigenvalue_sum': '     -7.2979861254',
   'kin_energy': '     13.4757066163',
   'spin': '1'}]]
    
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
    ########################
    #XPATHS to maintain
    
    species_xpath = '/fleurOutput/inputData/atomSpecies'
    iteration_xpath = '/fleurOutput/scfLoop/iteration'
    atomgroup_xpath = '/fleurOutput/inputData/atomGroups'
    relcoreStates_xpath = 'coreStates'
    
    #TODO all the attribute names...
    ######################
    
    
    #1. read out.xml in etree
    # TODO this should be common, moved somewhere else and importet
    parsed_data = {}
    outfile_broken = False
    parse_xml = True
    parser = etree.XMLParser(recover=False)#, remove_blank_text=True)
    parser_info = {'parser_warnings': [], 'unparsed' : []}
    
    try:
        tree = etree.parse(outxmlfile, parser)
    except XMLSyntaxError:
        outfile_broken = True
    #print 'broken xml'
        parser_info['parser_warnings'].append('The out.xml file is broken I try to repair it.')

    if outfile_broken:
        #repair xmlfile and try to parse what is possible.
        parser = etree.XMLParser(recover=True)#, remove_blank_text=True)
        try:
            tree = etree.parse(outxmlfile, parser)
        except XMLSyntaxError:
            #print 'here'
            parser_info['parser_warnings'].append('Skipping the parsing of the xml file. Repairing was not possible.')
            parse_xml = False

    #if parse_xml:
    root = tree.getroot()


    # 2. get all species from input
    # get element, name, coreStates
    # TODO why can this not be eval_xpath2?
    species_nodes = eval_xpath(root, species_xpath, parser_info)#/fleurinp/
    #print species_nodes
    species_atts = {}
    species_names = []
    for species in species_nodes:
        species_name = species.get('name')
        species_corestates = species.get('coreStates')
        species_element = species.get('element')
        species_atomicnumber = species.get('atomicNumber')
        species_magMom = species.get('magMom')
        species_atts[species_name] = {'name' : species_name, 
                                      'corestates' : species_corestates, 
                                      'element': species_element, 
                                      'atomgroups' : [], 
                                      'mag_mom' : species_magMom, 
                                      'atomic_number' : species_atomicnumber}
        species_names.append(species_name)
    #nspecies = len(species_nodes)
    #print(species_atts)
    #3. get number of atom types and their species from input
    atomtypes = []
    atomgroup_nodes = eval_xpath(root, atomgroup_xpath, parser_info)#/fleurinp/
    #print atomgroup_nodes
    #print parser_info
    for atomgroup in atomgroup_nodes:
        types_dict = {}
        group_species = atomgroup.get('species')
        if group_species in species_names:
            species_atts[group_species]['atomgroups'].append(atomgroup)
            element = species_atts[group_species]['element']
            atomicnumber = int(species_atts[group_species]['atomic_number'])
            #TODO get coreconfig,..., usually not in inp.xml...
            types_dict = {'species' : group_species, 'element' : element, 
                          'atomic_number' : atomicnumber, 'coreconfig': '', 
                          'valenceconfig' : '',
                          'stateOccupation' : []}
        atomtypes.append(types_dict)
    
    #print atomtypes
    natomgroup = len(atomgroup_nodes)
    #print natomgroup#, nspecies
    #print species_names
    corelevels = []

    #4 get corelevel dimension from atoms types.
    #5 init saving arrays:
    #6 parse corelevels:
    
    iteration_nodes = eval_xpath2(root, iteration_xpath, parser_info)
    #print iteration_nodes
    nIteration = len(iteration_nodes)
    if nIteration >= 1:
        iteration_to_parse = iteration_nodes[-1]#TODO:Optional all or other
        #print iteration_to_parse
        corestatescards = eval_xpath2(iteration_to_parse, relcoreStates_xpath, parser_info)
        # maybe does not return a list...
        #print(corestatescards)
        for type in atomtypes: # spin=2 is already in there
            corelevels.append([])
            
        for corestatescard in corestatescards:
            #print('here')
            #print(etree.tostring(corestatescard, pretty_print=True))
            #print(corestatescard, iteration_to_parse, parser_info)
            corelv = parse_state_card(corestatescard, iteration_to_parse, parser_info)
            #print(corelv['atomtype'])
            #print corelv
            #print(corelv['atomtype'])
            corelevels[int(corelv['atomtype'])-1].append(corelv)# is corelv['atomtype'] always an integer
            #corelevels.append(corelv)
                     
    #print parser_info
    #pprint(corelevels[0][1]['corestates'][2]['energy'])
    #corelevels[atomtypeNumber][spin]['corestates'][corestate number][attribute]
    return corelevels, atomtypes

def parse_state_card(corestateNode, iteration_node, parser_info={'parser_warnings' : []}):
    """
    Parses the ONE core state card

    :param corestateNode: an etree element (node), of a fleur output corestate card
    :param iteration_node: an etree element, iteration node
    :param jspin : integer 1 or 2
    
    :return a pythondict, {'eigenvalue_sum' : eigenvalueSum, 'corestates': states, 'spin' : spin, 'kin_energy' : kinEnergy, 'atomtype' : atomtype}
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
    eigenvalueSum_name = 'eigValSum'
    lostElectrons_name = 'lostElectrons'
    atomtype_name = 'atomType'
    #######
    
    atomtype = get_xml_attribute(corestateNode, atomtype_name, parser_info)

    kinEnergy = get_xml_attribute(corestateNode, kinEnergy_name, parser_info)
    vE2, suc = convert_to_float(kinEnergy, parser_info)
    #print('kinEnergy {}'.format(kinEnergy))
    eigenvalueSum = get_xml_attribute(corestateNode, eigenvalueSum_name, parser_info)
    vE2, suc = convert_to_float(eigenvalueSum, parser_info)

    spin = get_xml_attribute(corestateNode, spin_name, parser_info)
    #print('spin {}'.format(spin))
    #states = corestateNode.xpath(
    #for state in states:

    # get all corestate tags, (atomtypes * spin)
    #corestateNodes = eval_xpath(iteration_node, coreStates_xpath, parser_info)
    # for every corestate tag parse the attributes
    
    # some only the first interation, then get all state tags of the corestate tag (atom depended)
    # parse each core state #Attention to spin
    states = []
    corestates = eval_xpath2(corestateNode, state_xpath)#, parser_info)
    #print('corestates {}'.format(corestates))
    for corestate in corestates:# be careful that corestates is a list
        state_dict = {}
        n_state = get_xml_attribute(corestate, n_name, parser_info)
        l_state = get_xml_attribute(corestate, l_name, parser_info)
        j_state = get_xml_attribute(corestate, j_name, parser_info)
        energy, suc = convert_to_float(get_xml_attribute(corestate, energy_name, parser_info), parser_info)
        weight, suc = convert_to_float(get_xml_attribute(corestate, weight_name, parser_info), parser_info)
        state_dict = {'n' : n_state, 'l' : l_state, 'j' : j_state, 'energy' : energy, 'weight' : weight}
        states.append(state_dict)
    
    #print(states)

    core_states = {'eigenvalue_sum' : eigenvalueSum, 'corestates': states, 'spin' : spin, 'kin_energy' : kinEnergy, 'atomtype' : atomtype}
    #pprint(core_states)
    return core_states
'''
def eval_xpath(node, xpath):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.
    
    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns either nodes, or attributes, or text
    """
    try:
        return_value = node.xpath(xpath)
    except XPathEvalError:
        parser_info['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n'
            'Either it does not exist, or something is wrong with the expression.'.format(xpath))
        # TODO maybe raise an error again to catch in upper routine, to know where exactly
        return []
    if len(return_value) == 1:
        return return_value[0]
    else:
        return return_value
'''
def convert_to_float(value_string, parser_info={'parser_warnings':[]}):
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
        parser_info['parser_warnings'].append('Could not convert: "{}" to float, TypeError'.format(value_string))
        return value_string, False
    except ValueError:
        parser_info['parser_warnings'].append('Could not convert: "{}" to float, ValueError'.format(value_string))
        return value_string, False
    return value, True
'''
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
            parser_info['parser_warnings'].append('Tried to get attribute: "{}" from element {}.\n '
                   'I recieved "{}", maybe the attribute does not exist'.format(attributename, node, attrib_value))
            return None
    else: # something doesn't work here some nodes get through here
        parser_info['parser_warnings'].append('Can not get attributename: "{}" from node "{}", because node is not an element of etree.'.format(attributename,node))
        return None
'''

'''
### call
test_outxmlfiles = ['./out.xml', './test_outxml/outCuF.xml', './test_outxml/outFe.xml', './test_outxml/outHg.xml',  './test_outxml/outO.xml']
outxmlfile = test_outxmlfiles[2]

corelevels = extract_corelevels(outxmlfile)
for i in range(0,len(corelevels[0][1]['corestates'])):
    print corelevels[0][1]['corestates'][i]['energy']


for calc in calcs_pks:
    pass
    # get out.xml file of calculation
    outxml = load_node(pk).out.retrieved.folder.get_abs_path('out.xml')
    extract_corelevels(outxml)


print("--- %s seconds ---" % (time.time() - start_time))
'''
