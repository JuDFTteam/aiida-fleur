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
In this module you find methods to parse/extract corelevel shifts from an
out.xml file of FLEUR.
"""
# TODO clean up
# TODO together with xml_util, parser info handling, has to be also a return value of everything
# or rather throw exception on lowest level and catch at higher levels?
from lxml import etree  #, objectify
import warnings

from masci_tools.util.xml.common_functions import eval_xpath, get_xml_attribute
#convert_to_float

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
    Extracts corelevels out of out.xml files

    :params outxmlfile: path to out.xml file

    :param options: A dict: 'iteration' : X/'all'
    :returns corelevels: A list of the form:

    .. code-block:: python

            [atomtypes][spin][dict={atomtype : '', corestates : list_of_corestates}]
            [atomtypeNumber][spin]['corestates'][corestate number][attribute]
            get corelevel energy of first atomtype, spin1, corelevels[0][0]['corestates'][i]['energy']

    :example of output:

    .. code-block:: python

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
    warnings.warn(
        'extract_corelevels is deprecated. You can use the outxml_parser\n'
        "in masci_tools.io.parsers.fleur instead with outxml_parser(outxmlfile, optional_tasks=('corelevels'))\n"
        'To get this information', DeprecationWarning)

    species_xpath = '/fleurOutput/inputData/atomSpecies'
    iteration_xpath = '/fleurOutput/scfLoop/iteration'
    atomgroup_xpath = '/fleurOutput/inputData/atomGroups'
    coreconfig_xpath = 'electronConfig/coreConfig/text()'
    valenceconfig_xpath = 'electronConfig/valenceConfig/text()'
    state_occ_xpath = 'electronConfig/stateOccupation'

    new_species_xpath = '/fleurOutput/fleurInput/atomSpecies'
    new_atomgroup_xpath = '/fleurOutput/fleurInput/atomGroups'

    relcoreStates_xpath = 'coreStates'
    relpos_xpath = 'relPos'
    abspos_xpath = 'absPos'
    filmpos_xpath = 'filmPos'
    #TODO all the attribute names...
    ######################

    #1. read out.xml in etree
    # TODO this should be common, moved somewhere else and importet
    parsed_data = {}
    outfile_broken = False
    parse_xml = True
    parser = etree.XMLParser(recover=False)  #, remove_blank_text=True)
    parser_info = {'parser_warnings': [], 'unparsed': []}

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
            parser_info['parser_warnings'].append('Skipping the parsing of the xml file. Repairing was not possible.')
            parse_xml = False

    #if parse_xml:
    root = tree.getroot()

    # 2. get all species from input
    # get element, name, coreStates
    # TODO why can this not be eval_xpath2?
    species_nodes = eval_xpath(root, species_xpath)
    if not species_nodes:
        species_nodes = eval_xpath(root, new_species_xpath)
    species_atts = {}
    species_names = []
    for species in species_nodes:
        species_name = species.get('name')
        species_corestates = species.get('coreStates')
        species_element = species.get('element')
        species_atomicnumber = species.get('atomicNumber')
        species_magMom = species.get('magMom')
        #TODO sometimes not in inp.xml... what if it is not there
        coreconfig = eval_xpath(species, coreconfig_xpath)
        valenceconfig = eval_xpath(species, valenceconfig_xpath)
        state_occ = eval_xpath(species, state_occ_xpath, list_return=True)

        #parse state occ
        state_results = []
        for tag in state_occ:  #always a list?
            state = tag.get('state')
            spinUp = tag.get('spinUp')
            spinDown = tag.get('spinDown')
            state_results.append({state: [spinUp, spinDown]})

        species_atts[species_name] = {
            'name': species_name,
            'corestates': species_corestates,
            'element': species_element,
            'atomgroups': [],
            'mag_mom': species_magMom,
            'atomic_number': species_atomicnumber,
            'coreconfig': coreconfig,
            'valenceconfig': valenceconfig,
            'stateOccupation': state_results
        }
        species_names.append(species_name)

    #3. get number of atom types and their species from input
    atomtypes = []
    atomgroup_nodes = eval_xpath(root, atomgroup_xpath)  #/fleurinp/
    if not atomgroup_nodes:
        atomgroup_nodes = eval_xpath(root, new_atomgroup_xpath)
    # always a list?
    for atomgroup in atomgroup_nodes:
        types_dict = {}
        group_species = atomgroup.get('species')
        if group_species in species_names:
            species_atts[group_species]['atomgroups'].append(atomgroup)
            element = species_atts[group_species]['element']
            atomicnumber = int(species_atts[group_species]['atomic_number'])
            coreconf = species_atts[group_species]['coreconfig']
            valenceconf = species_atts[group_species]['valenceconfig']
            stateocc = species_atts[group_species]['stateOccupation']
            a =   eval_xpath(atomgroup, relpos_xpath, list_return=True) \
                + eval_xpath(atomgroup, abspos_xpath, list_return=True) \
                + eval_xpath(atomgroup, filmpos_xpath, list_return=True)  # always list
            natoms = len(a)
            types_dict = {
                'species': group_species,
                'element': element,
                'atomic_number': atomicnumber,
                'coreconfig': coreconf,
                'valenceconfig': valenceconf,
                'stateOccupation': stateocc,
                'natoms': natoms
            }
        atomtypes.append(types_dict)

    #natomgroup = len(atomgroup_nodes)
    #print(natomgroup)
    corelevels = []

    #4 get corelevel dimension from atoms types.
    #5 init saving arrays:
    #6 parse corelevels:

    iteration_nodes = eval_xpath(root, iteration_xpath, list_return=True)
    nIteration = len(iteration_nodes)
    if nIteration >= 1:
        iteration_to_parse = iteration_nodes[-1]  #TODO:Optional all or other
        #print iteration_to_parse
        corestatescards = eval_xpath(iteration_to_parse, relcoreStates_xpath, list_return=True)
        # maybe does not return a list...
        for atype in atomtypes:  # spin=2 is already in there
            corelevels.append([])

        for corestatescard in corestatescards:
            corelv = parse_state_card(corestatescard, iteration_to_parse, parser_info)
            corelevels[int(corelv['atomtype']) - 1].append(corelv)  # is corelv['atomtype'] always an integer?

    #print parser_info
    #pprint(corelevels[0][1]['corestates'][2]['energy'])
    #corelevels[atomtypeNumber][spin]['corestates'][corestate number][attribute]
    return corelevels, atomtypes


def parse_state_card(corestateNode, iteration_node, parser_info=None):
    """
    Parses the ONE core state card

    :params corestateNode: an etree element (node), of a fleur output corestate card
    :params iteration_node: an etree element, iteration node
    :params jspin: integer 1 or 2

    :returns: a pythondict of type:

    .. code-block:: python

            {'eigenvalue_sum' : eigenvalueSum,
             'corestates': states,
             'spin' : spin,
             'kin_energy' : kinEnergy,
             'atomtype' : atomtype}

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
    if parser_info is None:
        parser_info = {'parser_warnings': []}

    atomtype = get_xml_attribute(corestateNode, atomtype_name)

    kinEnergy = get_xml_attribute(corestateNode, kinEnergy_name)
    vE2, suc = convert_to_float(kinEnergy)
    eigenvalueSum = get_xml_attribute(corestateNode, eigenvalueSum_name)
    vE2, suc = convert_to_float(eigenvalueSum)

    spin = get_xml_attribute(corestateNode, spin_name)
    #print('spin {}'.format(spin))
    #states = corestateNode.xpath(
    #for state in states:

    # get all corestate tags, (atomtypes * spin)
    #corestateNodes = eval_xpath(iteration_node, coreStates_xpath, parser_info)
    # for every corestate tag parse the attributes

    # some only the first interation, then get all state tags of the corestate tag (atom depended)
    # parse each core state #Attention to spin
    states = []
    corestates = eval_xpath(corestateNode, state_xpath, list_return=True)  #, parser_info)

    for corestate in corestates:  # be careful that corestates is a list
        state_dict = {}
        n_state = get_xml_attribute(corestate, n_name)
        l_state = get_xml_attribute(corestate, l_name)
        j_state = get_xml_attribute(corestate, j_name)
        energy, suc = convert_to_float(get_xml_attribute(corestate, energy_name))
        weight, suc = convert_to_float(get_xml_attribute(corestate, weight_name))
        state_dict = {'n': n_state, 'l': l_state, 'j': j_state, 'energy': energy, 'weight': weight}
        states.append(state_dict)

    core_states = {
        'eigenvalue_sum': eigenvalueSum,
        'corestates': states,
        'spin': spin,
        'kin_energy': kinEnergy,
        'atomtype': atomtype
    }
    return core_states


# TODO should be used from somewhere else, probably double
def convert_to_float(value_string, parser_info=None):
    """
    Tries to make a float out of a string. If it can't it logs a warning
    and returns True or False if convertion worked or not.

    :param value_string: a string
    :returns value: the new float or value_string: the string given
    :retruns: True or False
    """
    if parser_info is None:
        parser_info = {'parser_warnings': []}

    try:
        value = float(value_string)
    except TypeError:
        parser_info['parser_warnings'].append(f'Could not convert: "{value_string}" to float, TypeError')
        return value_string, False
    except ValueError:
        parser_info['parser_warnings'].append(f'Could not convert: "{value_string}" to float, ValueError')
        return value_string, False
    return value, True


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


# TODO this is prob doubled is also in init_cls wc
def clshifts_to_be(coreleveldict, reference_dict, warn=False):
    """
    This methods converts corelevel shifts to binding energies, if a reference is given.
    These can than be used for plotting.

    :params reference_dict: An example:

    .. code-block:: python

           reference_dict = {'W' : {'4f7/2' : [124],
                                    '4f5/2' : [102]},
                             'Be' : {'1s': [117]}}

    :params coreleveldict: An example:

    .. code-block:: python

           coreleveldict = {'W' : {'4f7/2' : [0.4, 0.3, 0.4 ,0.1],
                                   '4f5/2' : [0, 0.3, 0.4, 0.1]},
                            'Be' : {'1s': [0, 0.2, 0.4, 0.1, 0.3]}

    """
    # this block of comments was extracted from the docstring
    # I did not understand where it belongs
    # {'Be': {'1s': [117, 117.2, 117.4, 117.1, 117.3]},
    #  'W': {'4f5/2': [102, 102.3, 102.4, 102.1],
    #        '4f7/2': [124.4, 124.3, 124.4, 124.1]}}

    return_corelevel_dict = {}

    for elem, corelevel_dict in coreleveldict.items():
        ref_el = reference_dict.get(elem, {})

        if not ref_el:  # no refernce for that element given
            if warn:
                print(f"WARNING: Reference for element: '{elem}' not given. I ignore these.")
            continue

        return_corelevel_dict[elem] = {}
        for corelevel_name, corelevel_list in corelevel_dict.items():
            ref_cl = ref_el.get(corelevel_name, [])
            if not ref_cl:  # no reference corelevel given for that element
                if warn:
                    print("WARNING: Reference corelevel '{}' for element: '{}' "
                          'not given. I ignore these.'.format(corelevel_name, elem))
                continue
            be_all = []
            nref = len(ref_cl)
            ncl = len(corelevel_list)
            if nref == ncl:
                for i, corelevel in enumerate(corelevel_list):
                    be = corelevel + ref_cl[i]
                    be_all.append(be)
            else:
                for corelevel in corelevel_list:
                    be = corelevel + ref_cl[0]
                    be_all.append(be)
            return_corelevel_dict[elem][corelevel_name] = be_all

    return return_corelevel_dict
