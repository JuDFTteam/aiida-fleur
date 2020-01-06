from __future__ import absolute_import
import os
import aiida_fleur
import pytest

path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(path, 'tests/files/inpxml/FePt/FePt.xml')

def test_xml_set_attribv_occ(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_attribv_occ, eval_xpath
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_attribv_occ(etree, '/fleurInput/calculationSetup/cutoffs', 'Gmax', 11.00)
    assert float(eval_xpath(etree, '/fleurInput/calculationSetup/cutoffs/@Gmax')) == 11

    xml_set_attribv_occ(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-1', [1])
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['Fe-1', 'TEST-1']

    xml_set_attribv_occ(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-2', [-1])
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-2', 'TEST-2']

# xml_set_first_attribv
def test_xml_set_first_attribv(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_first_attribv, eval_xpath
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_first_attribv(etree, '/fleurInput/calculationSetup/cutoffs', 'Gmax', 11.00)
    assert float(eval_xpath(etree, '/fleurInput/calculationSetup/cutoffs/@Gmax')) == 11

    xml_set_first_attribv(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-1')
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-1', 'Pt-1']

# xml_set_all_attribv
def test_xml_set_all_attribv(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_all_attribv, eval_xpath
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_all_attribv(etree, '/fleurInput/calculationSetup/cutoffs', 'Gmax', 11.00)
    assert float(eval_xpath(etree, '/fleurInput/calculationSetup/cutoffs/@Gmax')) == 11

    xml_set_all_attribv(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-1')
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-1', 'TEST-1']

    xml_set_all_attribv(etree, '/fleurInput/atomGroups/atomGroup', 'species', ['TEST-1', 23])
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-1', '23']

# xml_set_text
def test_xml_set_text(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_text, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    second_text = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text

    xml_set_text(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'test_text')
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == second_text

# xml_set_all_text
def test_xml_set_text_occ(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_text_occ, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    first_text = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text
    second_text = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text

    xml_set_text_occ(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'test_text', occ=0)
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == second_text

    etree = inpxml_etree(TEST_INP_XML_PATH)
    xml_set_text_occ(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'test_text', occ=1)
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == first_text
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == 'test_text'

 # xml_set_all_text
def test_xml_set_all_text(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_all_text, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_all_text(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'test_text')
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == 'test_text'   

    xml_set_all_text(etree, '/fleurInput/atomGroups/atomGroup/filmPos', ['test_text2', 'test_ext3'])
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text2'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == 'test_ext3'   

# create_tag
def test_create_tag(inpxml_etree):
    from aiida_fleur.tools.xml_util import create_tag, eval_xpath3
    etree = inpxml_etree(TEST_INP_XML_PATH)

    create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG', create=False)
    assert eval_xpath3(etree, '/fleurInput/cell/filmLattice/bravaisMatrix')[0][3].tag == 'TEST_TAG'

    create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG2', create=False,
               place_index=1)
    tag_names = [x.tag for x in eval_xpath3(etree, '/fleurInput/cell/filmLattice/bravaisMatrix')[0]]
    assert tag_names == ['row-1', 'TEST_TAG2', 'row-2', 'row-3', 'TEST_TAG']

    create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG3', create=False,
               place_index=True, tag_order=['row-1', 'TEST_TAG2', 'TEST_TAG3', 'row-2',
                                            'row-3', 'TEST_TAG'])
    tag_names = [x.tag for x in eval_xpath3(etree, '/fleurInput/cell/filmLattice/bravaisMatrix')[0]]
    assert tag_names == ['row-1', 'TEST_TAG2', 'TEST_TAG3', 'row-2', 'row-3', 'TEST_TAG']

    create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG4', create=False,
               place_index=True, tag_order=['row-1', 'TEST_TAG2', 'TEST_TAG3', 'row-2',
                                            'TEST_TAG4', 'row-3', 'TEST_TAG'])
    tag_names = [x.tag for x in eval_xpath3(etree, '/fleurInput/cell/filmLattice/bravaisMatrix')[0]]
    assert tag_names == ['row-1', 'TEST_TAG2', 'TEST_TAG3', 'row-2', 'TEST_TAG4', 'row-3', 'TEST_TAG']

    create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG0', create=False,
               place_index=True, tag_order=['TEST_TAG0', 'row-1', 'TEST_TAG2', 'TEST_TAG3', 'row-2',
                                            'TEST_TAG4', 'row-3', 'TEST_TAG'])
    tag_names = [x.tag for x in eval_xpath3(etree, '/fleurInput/cell/filmLattice/bravaisMatrix')[0]]
    assert tag_names == ['TEST_TAG0', 'row-1', 'TEST_TAG2', 'TEST_TAG3',
                         'row-2', 'TEST_TAG4', 'row-3', 'TEST_TAG']

    with pytest.raises(ValueError) as excinfo:
        create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG5', create=False,
               place_index=True, tag_order=['TEST_TAG0', 'row-1', 'TEST_TAG3', 'TEST_TAG2',
                                            'TEST_TAG5', 'row-2', 'TEST_TAG4', 'row-3', 'TEST_TAG'])
    assert str(excinfo.value) == "Existing order does not correspond to tag_order list"

    with pytest.raises(ValueError) as excinfo:
        create_tag(etree, '/fleurInput/cell/filmLattice/bravaisMatrix', 'TEST_TAG5', create=False,
               place_index=True, tag_order=['TEST_TAG0', 'row-1', 'TEST_TAG3', 'TEST_TAG2',
                                            'row-2', 'TEST_TAG4', 'row-3', 'TEST_TAG'])
    assert str(excinfo.value) == "Did not find element name in the tag_order list"


# delete_att
def test_delete_att(inpxml_etree):
    from aiida_fleur.tools.xml_util import delete_att
    pass

# delete_tag
def test_delete_tag(inpxml_etree):
    from aiida_fleur.tools.xml_util import delete_tag
    pass

# replace_tag
def test_replace_tag(inpxml_etree):
    from aiida_fleur.tools.xml_util import replace_tag
    pass

# set_species
def test_set_species(inpxml_etree):
    from aiida_fleur.tools.xml_util import set_species
    pass

# change_atomgr_att
def test_change_atomgr_att(inpxml_etree):
    from aiida_fleur.tools.xml_util import change_atomgr_att
    pass

# add_num_to_att
def test_add_num_to_att(inpxml_etree):
    from aiida_fleur.tools.xml_util import add_num_to_att
    pass

# eval_xpath
def test_eval_xpath(inpxml_etree):
    from aiida_fleur.tools.xml_util import eval_xpath
    pass

# eval_xpath2
def test_eval_xpath2(inpxml_etree):
    from aiida_fleur.tools.xml_util import eval_xpath2
    pass

# eval_xpath3
def test_eval_xpath3(inpxml_etree):
    from aiida_fleur.tools.xml_util import eval_xpath3
    pass

# get_xml_attribute
def test_get_xml_attribute(inpxml_etree):
    from aiida_fleur.tools.xml_util import get_xml_attribute
    pass

# get_inpxml_file_structure
# IMPORTANT: Here we need thats that tell us when the plugin has to be maintained, i.e Know thing in the inp schema where changed
# Is there a way to test for not yet know attributes? i.e if the plugin is complete? Back compatible?
# I.e make for each Fleur schema file, complete inp.xml file version a test if the attributes exists.

# make a test_class

    
