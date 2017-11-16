 #!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import DataFactory


# TODO maybe merge these methods into fleurinp or structure util? or create a parameterData utils
ParameterData = DataFactory('parameter')
#355

def create_corehole_para(structure, kind, econfig, species_name='corehole', parameterData=None):
    """
    This methods sets of electron configurations for a kind
    or position given, make sure to break the symmetry for this position/kind
    beforehand, otherwise you will create several coreholes.

    param: structure: StructureData
    param: kind, a string with the kind_name (TODO: alternative the kind object)
    param: econfig, string, e.g. econfig = "[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2"
    ! THis is the new econfig therefore

    returns a parameterData node
    """

    from aiida.common.constants import elements as PeriodicTableElements

    _atomic_numbers = {data['symbol']: num for num,
                           data in PeriodicTableElements.iteritems()}
    #from aiida_fleur.tools.merge_parameter import merge_parameter

    kindo = structure.get_kind(kind)
    symbol = kindo.symbol
    head = kindo.name.rstrip('01223456789')
    #print(kindo)
    charge = _atomic_numbers[kindo.symbol]
    id = float("{}.{}".format(charge, kindo.name[len(head):]))
    #print('id {}'.format(id))

    # get kind symbol, get kind name,
    #&atom element="W" jri=921 lmax=8 rmt=2.52 dx=0.014 lo="5p" econfig="[Kr] 5s2 4d10 4f13 | 5p6 5d4 6s2" /
    #count = 0
    if parameterData:
        new_parameterd = parameterData.get_dict() # dict()otherwise parameterData is changed
        for key, val in new_parameterd.iteritems():
            if 'atom' in key:
                if val.get('element', None) == symbol:
                    # remember id is atomic number.some int
                    if (id and float(id) == float(val.get('id', -1))):
                        val.update({'econfig' : econfig})
                        #print 'here1'
                        break
                    elif not id:
                        #print 'here2'
                        val.update({'econfig' : econfig})
                    else:
                        pass
    else:
        if id:
            if species_name:
                new_parameterd = {'atom': {'element' : symbol, 'econfig' : econfig, 'id' : id, 'name' : species_name}}
            else:
                new_parameterd = {'atom': {'element' : symbol, 'econfig' : econfig, 'id' : id}}
        else:
            new_parameterd = {'atom': {'element' : symbol, 'econfig' : econfig}}

    new_parameter= ParameterData(dict=new_parameterd)
    #if parameterData:
    #    new_parameter = merge_parameter(parameterData, new_parameter)
    return new_parameter#structure


# Move to fleurinpmod? fleurinp->self
# This method is fully implemented yet since it turned out to better go over inpgen
def create_corehole_fleurinp(fleurinp, species, stateocc, pos=[], coreconfig='same', valenceconfig='same'):
    """
    Removes an electron from the core and adds it to the valence band of the kind
    given econfig as in inp.xml [Kr] (5s1/2) (4d3/2) (4d5/2) (4f5/2) (4f7/2)
    if position(pos) is given the electronConfig for the specifed position will be set.
    (or todo? econfig, either [Kr] 5s2 4d10 4f13 | 5p6 5d4 6s2 or
    [Kr] 2(5s1/2) 4(4d3/2) 6(4d5/2) 6(4f5/2) 8(4f7/2) |2(5p1/2) 4(5p3/2) 2(6s1/2) 2(5d3/2) 2(5d5/2))
    occ tags already there will be untouched, unless the state is the same as given

    :param fleurinp:, an unstored! changes are done on this fleurinp fleurinpdata object # TODO alternatively stored?
    :param species:, string with species name
    :param stateocc: dict state tuples (spinup, spindown), exp: {'(5d3/2)' : (2.5, 0.0), '(4f7/2)' : (3.5 , 4.0)}
    :param pos: list of tuples of 3, pos=[(0.0, 0.0, 0.0), ...]
    :param coreconfig: string, e.g: [Kr] (5s1/2) (4d3/2) (4d5/2) (4f5/2) (4f7/2), default='same' (same as current in inp.xml)
    :param valenceconfig, string, e.g.: (5p1/2) (5p3/2) (6s1/2) (5d3/2) (5d5/2)

    :return: the changes fleurinpData object
    """
    '''
         <electronConfig>
            <coreConfig>[Kr] (5s1/2) (4d3/2) (4d5/2) (4f5/2) (4f7/2)</coreConfig>
            <valenceConfig>(5p1/2) (5p3/2) (6s1/2) (5d3/2) (5d5/2)</valenceConfig>
            <stateOccupation state="(5d3/2)" spinUp="2.00000000" spinDown=".00000000"/>
            <stateOccupation state="(5d5/2)" spinUp="2.00000000" spinDown=".00000000"/>
         </electronConfig>
    '''
    from aiida_fleur.tools.xml_util import eval_xpath2, get_xml_attribute
    #from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
    # or from fleurinp?

    FleurinpData = DataFactory('fleur.fleurinp')
    ########### all xpath maintain ########### ? needed?
    electronConfig_xpath =  '/fleurInput/atomSpecies/species/electronConfig'
    species_xpath = '/fleurInput/atomSpecies/species'
    #####################

    # test input, if something wrong return/ throw error
    # get electronConfig tag from fleurinp
    # create new tag from old tag and method input
    # return new fleurinp data
    # Best use fleurinp functions
    # Do it with xml or rather

    new_core = False
    new_valence = False

    # test input.
    if not isinstance(fleurinp, FleurinpData):
        print 'No fleurinp Data given to "create_valence_corehole"'
        return None # TODO throw error?

    if coreconfig != 'same':
        new_core = True

    if valenceconfig != 'same':
        new_valence = True
    #print stateocc

    species_tags = fleurinp.get_tag(species_xpath)
    #print species_tags
    for speci in species_tags:
        if get_xml_attribute(speci, 'name') == species:
            # change
            econfig = eval_xpath2(speci, 'electronConfig')[0]
            coreconfig = eval_xpath2(econfig, 'coreConfig')
            valenceconfig = eval_xpath2(econfig, 'valenceConfig')
            occupations = eval_xpath2(econfig, 'stateOccupation')

            for key, val in stateocc.iteritems():
                #print key
                added = False
                for occ in occupations:
                    name = get_xml_attribute(occ, 'state')
                    #print name
                    if name == key:
                        added = True
                        # override and break (can occur only once)
                        occ.set('spinUp', str(val[0]))
                        occ.set('spinDown', str(val[0]))
                        break
                if not added:
                    pass


    #st_inpchanges(change_dict)


    #alternative
    change_dict = {'coreConfig' : '', 'valenceConfig': ''}
    change_dict2 = {'state' : '', 'spinUp' : '', 'spinDown' : ''}
    change_dict3 = {'valenceElectrons' : ''}




    return fleurinp



def write_change(xmltree, changelist_xpath):


    xmltree_new = xmltree
    for element in changelist_xpath:
        xpath = element[0]
        value = element[1]
        #print element
    return xmltree_new


