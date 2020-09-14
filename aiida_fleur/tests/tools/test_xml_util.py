from __future__ import absolute_import
import os
import pytest
import aiida_fleur

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/FePt/inp.xml')


def test_xml_set_attribv_occ(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_attribv_occ, eval_xpath
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_attribv_occ(etree, '/fleurInput/calculationSetup/cutoffs', 'Gmax', 11.00)
    assert float(eval_xpath(etree, '/fleurInput/calculationSetup/cutoffs/@Gmax')) == 11

    xml_set_attribv_occ(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-1', [1])
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['Fe-1', 'TEST-1']

    xml_set_attribv_occ(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-2', [-1])
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-2', 'TEST-2']


def test_xml_set_first_attribv(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_first_attribv, eval_xpath
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_first_attribv(etree, '/fleurInput/calculationSetup/cutoffs', 'Gmax', 11.00)
    assert float(eval_xpath(etree, '/fleurInput/calculationSetup/cutoffs/@Gmax')) == 11

    xml_set_first_attribv(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-1')
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-1', 'Pt-1']


def test_xml_set_all_attribv(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_all_attribv, eval_xpath
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_all_attribv(etree, '/fleurInput/calculationSetup/cutoffs', 'Gmax', 11.00)
    assert float(eval_xpath(etree, '/fleurInput/calculationSetup/cutoffs/@Gmax')) == 11

    xml_set_all_attribv(etree, '/fleurInput/atomGroups/atomGroup', 'species', 'TEST-1')
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-1', 'TEST-1']

    xml_set_all_attribv(etree, '/fleurInput/atomGroups/atomGroup', 'species', ['TEST-1', 23])
    assert eval_xpath(etree, '/fleurInput/atomGroups/atomGroup/@species') == ['TEST-1', '23']


def test_xml_set_text(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_text, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    second_text = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text

    xml_set_text(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'test_text')
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == second_text


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


def test_xml_set_all_text(inpxml_etree):
    from aiida_fleur.tools.xml_util import xml_set_all_text, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    xml_set_all_text(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'test_text')
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == 'test_text'

    xml_set_all_text(etree, '/fleurInput/atomGroups/atomGroup/filmPos', ['test_text2', 'test_ext3'])
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[0].text == 'test_text2'
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos')[1].text == 'test_ext3'


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
    assert tag_names == ['row-1', 'TEST_TAG2', 'TEST_TAG3',
                         'row-2', 'TEST_TAG4', 'row-3', 'TEST_TAG']

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


def test_delete_att(inpxml_etree):
    from aiida_fleur.tools.xml_util import delete_att, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    assert eval_xpath2(
        etree, '/fleurInput/atomGroups/atomGroup/filmPos/@label')[0] == "                 222"

    delete_att(etree, '/fleurInput/atomGroups/atomGroup/filmPos', 'label')
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos/@label') == []


def test_delete_tag(inpxml_etree):
    from aiida_fleur.tools.xml_util import delete_tag, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos') != []

    delete_tag(etree, '/fleurInput/atomGroups/atomGroup/filmPos')
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos') == []


def test_replace_tag(inpxml_etree):
    from aiida_fleur.tools.xml_util import replace_tag, eval_xpath2
    etree = inpxml_etree(TEST_INP_XML_PATH)

    to_insert = eval_xpath2(etree, '/fleurInput/calculationSetup/cutoffs')[0]
    print(to_insert)
    print(eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos'))

    replace_tag(etree, '/fleurInput/atomGroups/atomGroup/filmPos', to_insert)

    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/filmPos') == []
    assert eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/cutoffs')[0] == to_insert


@pytest.mark.skip(reason='econfig extraction is not implemented')
def test_get_inpgen_para_from_xml(inpxml_etree):
    from aiida_fleur.tools.xml_util import get_inpgen_para_from_xml
    etree = inpxml_etree(TEST_INP_XML_PATH)

    result = {'comp': {'jspins': 2.0,
                       'frcor': False,
                       'ctail': True,
                       'kcrel': '0',
                       'gmax': 10.0,
                       'gmaxxc': 8.7,
                       'kmax': 4.0},
              'atom0': {'z': 26,
                        'rmt': 2.2,
                        'dx': 0.016,
                        'jri': 787,
                        'lmax': 10,
                        'lnonsph': 6,
                        # 'econfig': <Element electronConfig at 0x1105d66e0>,
                        'lo': '',
                        'element': 'Fe'},
              'atom1': {'z': 78,
                        'rmt': 2.2,
                        'dx': 0.017,
                        'jri': 787,
                        'lmax': 10,
                        'lnonsph': 6,
                        # 'econfig': <Element electronConfig at 0x110516d20>,
                        'lo': '',
                        'element': 'Pt'},
              'title': 'A Fleur input generator calculation with aiida',
              'exco': {'xctyp': 'vwn'}}

    dict_result = get_inpgen_para_from_xml(etree)
    assert dict_result == result


class TestSetSpecies:
    """Tests for set_species"""

    paths = ['mtSphere/@radius',
             'atomicCutoffs/@lmax',
             'energyParameters/@s',
             'electronConfig/coreConfig',
             'electronConfig/stateOccupation/@state',
             'electronConfig/stateOccupation/@state',
             'special/@socscale',
             'ldaU/@test_att',
             'lo/@test_att',
             'lo/@test_att'
             ]

    attdicts = [{'mtSphere': {'radius': 3.333}},
                {'atomicCutoffs': {'lmax': 7.0}},
                {'energyParameters': {'s': 3.0}},
                {'electronConfig': {'coreConfig': 'test'}},
                {'electronConfig': {'stateOccupation': {'state': 'state'}}},
                {'electronConfig': {'stateOccupation': [{'state': 'state'},
                                                        {'state': 'state2'}]}},
                {'special': {'socscale': 1.0}},
                {'ldaU': {'test_att': 2.0}},
                {'lo': {'test_att': 2.0}},
                {'lo': [{'test_att': 2.0}, {'test_att': 33.0}]}
                #  'nocoParams': {'test_att' : 2, 'qss' : '123 123 123'},
                ]

    results = ['3.333', '7.0', '3.0', 'test', 'state', [
        'state', 'state2'], '1.0', '2.0', '2.0', ['2.0', '33.0']]

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results, paths))
    def test_set_species(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import set_species, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        set_species(etree, 'Fe-1', attributedict=attr_dict)

        result = eval_xpath2(etree, '/fleurInput/atomSpecies/species[@name="Fe-1"]/' + path)

        if isinstance(correct_result, str):
            if 'coreConfig' in path:
                assert result[0].text == correct_result
            else:
                assert result[0] == correct_result
        elif isinstance(correct_result, (float, int)):
            assert result[0] == correct_result
        else:
            assert correct_result == result

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results, paths))
    def test_set_species_label(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import set_species_label, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        set_species_label(etree, "                 222", attributedict=attr_dict)

        result = eval_xpath2(etree, '/fleurInput/atomSpecies/species[@name="Fe-1"]/' + path)

        if isinstance(correct_result, str):
            if 'coreConfig' in path:
                assert result[0].text == correct_result
            else:
                assert result[0] == correct_result
        elif isinstance(correct_result, (float, int)):
            assert result[0] == correct_result
        else:
            assert correct_result == result

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results, paths))
    def test_set_species_all_string(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import set_species, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        set_species(etree, 'all-Fe', attributedict=attr_dict)

        result = eval_xpath2(etree, '/fleurInput/atomSpecies/species[@name="Fe-1"]/' + path)

        if isinstance(correct_result, str):
            if 'coreConfig' in path:
                assert result[0].text == correct_result
            else:
                assert result[0] == correct_result
        elif isinstance(correct_result, (float, int)):
            assert result[0] == correct_result
        else:
            assert correct_result == result

    results_all = [[x, x] if not isinstance(x, list) else [x[0], x[1], x[0], x[1]] for x in results]
    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results_all, paths))
    def test_set_species_all(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import set_species, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        set_species(etree, 'all', attributedict=attr_dict)

        result = eval_xpath2(etree, '/fleurInput/atomSpecies/species/' + path)

        import lxml
        print(lxml.etree.tostring(etree))

        if 'coreConfig' in path:
            assert [x.text for x in result] == correct_result
        else:
            assert result == correct_result

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results_all, paths))
    def test_set_species_label_all(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import set_species_label, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        set_species_label(etree, 'all', attributedict=attr_dict)

        result = eval_xpath2(etree, '/fleurInput/atomSpecies/species/' + path)

        if 'coreConfig' in path:
            assert [x.text for x in result] == correct_result
        else:
            assert result == correct_result


class TestChangeAtomgrAtt:
    """Tests for change_atomgr_att"""

    paths = ['force/@relaxXYZ',
             'nocoParams/@beta'
             ]

    attdicts = [{'force': [('relaxXYZ', 'FFF')]},
                {'nocoParams': [('beta', 7.0)]}
                ]

    results = ['FFF', '7.0']

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results, paths))
    def test_change_atomgr_att(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import change_atomgr_att, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        change_atomgr_att(etree, attributedict=attr_dict, species='Fe-1')

        result = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup[@species="Fe-1"]/' + path)

        assert result[0] == correct_result

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results, paths))
    def test_change_atomgr_att_position(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import change_atomgr_att, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        change_atomgr_att(etree, attributedict=attr_dict, position=1)

        result = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/' + path)

        assert result[0] == correct_result

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results, paths))
    def test_change_atomgr_att_label(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import change_atomgr_att_label, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        change_atomgr_att_label(etree, attributedict=attr_dict, at_label="                 222")

        result = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup[@species="Fe-1"]/' + path)

        assert result[0] == correct_result

    results_all = [[x, x] for x in results]
    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results_all, paths))
    def test_change_atomgr_att_all(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import change_atomgr_att, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        change_atomgr_att(etree, attributedict=attr_dict, species='all')

        result = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/' + path)

        assert result == correct_result

    @staticmethod
    @pytest.mark.parametrize('attr_dict,correct_result,path', zip(attdicts, results_all, paths))
    def test_change_atomgr_att_label_all(inpxml_etree, attr_dict, correct_result, path):
        from aiida_fleur.tools.xml_util import change_atomgr_att_label, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        change_atomgr_att_label(etree, attributedict=attr_dict, at_label="all")

        result = eval_xpath2(etree, '/fleurInput/atomGroups/atomGroup/' + path)

        assert result == correct_result

    def test_change_atomgr_att_fail(self, inpxml_etree):
        from aiida_fleur.tools.xml_util import change_atomgr_att, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        change_atomgr_att(etree, attributedict=self.attdicts[0])

        result = eval_xpath2(
            etree, '/fleurInput/atomGroups/atomGroup[@species="Fe-1"]/' + self.paths[0])

        assert result[0] == 'TTT'


class TestSetInpchanges:
    from aiida_fleur.tools.xml_util import get_inpxml_file_structure

    xml_structure = get_inpxml_file_structure()

    paths = xml_structure[12]

    @pytest.mark.parametrize('name,path', paths.items())
    def test_set_inpchanges(self, inpxml_etree, name, path):
        from aiida_fleur.tools.xml_util import set_inpchanges, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        skip_paths = ['atomSpecies', 'atomGroups', 'bzIntegration', 'kPointCount', 'bulkLattice',
                      'bravaisMatrix', 'a1']

        if any(x in path for x in skip_paths):
            pytest.skip("This attribute is not tested for FePt/inp.xml")
        elif name in self.xml_structure[11].keys():
            set_inpchanges(etree, change_dict={name: 'test'})
            if name not in ['relPos', 'absPos']:
                result = eval_xpath2(etree, path)[0]
                assert result.text == 'test'
        elif name in self.xml_structure[0]:
            set_inpchanges(etree, change_dict={name: 'T'})
            result = eval_xpath2(etree, path + '/@{}'.format(name))
            assert result[0] == 'T'
        elif name in self.xml_structure[4] or name in self.xml_structure[3]:
            set_inpchanges(etree, change_dict={name: 33})
            result = eval_xpath2(etree, path + '/@{}'.format(name))
            assert float(result[0]) == 33
        elif name in self.xml_structure[5]:
            set_inpchanges(etree, change_dict={name: 'test'})
            if name == 'xcFunctional':
                result = eval_xpath2(etree, path + '/@{}'.format('name'))
            else:
                result = eval_xpath2(etree, path + '/@{}'.format(name))
            assert result[0] == 'test'
        else:
            raise BaseException('A switch that you want to set is not one of the supported types.'
                                'Or you made a mistake during new switch registration')

    def test_set_inpchanges_fail(self, inpxml_etree):
        from aiida_fleur.tools.xml_util import set_inpchanges, eval_xpath2
        from aiida.common.exceptions import InputValidationError

        etree = inpxml_etree(TEST_INP_XML_PATH)
        with pytest.raises(InputValidationError):
            set_inpchanges(etree, change_dict={'not_existing': 'test'})


def test_inpxml_to_dict(inpxml_etree):
    from aiida_fleur.tools.xml_util import inpxml_todict, get_inpxml_file_structure, clear_xml

    correct = {
        'fleurInputVersion': '0.31',
        'comment': 'A Fleur input generator calculation with aiida',
        'calculationSetup': {
            'cutoffs': {
                'Kmax': 4.4,
                'Gmax': 10.9,
                'GmaxXC': 9.1,
                'numbands': 0,
            },
            'scfLoop': {
                'itmax': 60,
                'minDistance': 2e-05,
                'maxIterBroyd': 99,
                'imix': 'Anderson',
                'alpha': 0.05,
                'precondParam': '0.0',
                'spinf': 2.0,
            },
            'coreElectrons': {
                'ctail': False,
                'frcor': False,
                'kcrel': 0,
                'coretail_lmax': '0',
            },
            'magnetism': {
                'jspins': 2,
                'l_noco': True,
                'swsp': False,
                'lflip': False,
            },
            'soc': {
                'theta': 0.0,
                'phi': 0.0,
                'l_soc': False,
                'spav': False,
            },
            'prodBasis': {
                'gcutm': '2.90000000',
                'tolerance': '.00010000',
                'ewaldlambda': '3',
                'lexp': '16',
                'bands': '0',
            },
            'nocoParams': {
                'l_ss': True,
                'l_mperp': 'F',
                'l_constr': 'F',
                'mix_b': '.00000000',
                'qss': '0.0 0.0 0.0',
            },
            'expertModes': {'eig66': False,
                            'gw': 0,
                            'isec1': 99,
                            'lpr': 0,
                            'pot8': False,
                            'secvar': False},
            'geometryOptimization': {
                'l_f': False,
                'forcealpha': 1.0,
                'forcemix': 'BFGS',
                'force_converged': 1e-05,
                'qfix': 0,
                'epsdisp': 1e-05,
                'epsforce': 1e-05,
            },
            'ldaU': {'l_linMix': 'F', 'mixParam': '.050000', 'spinf': 1.0},
            'bzIntegration': {
                'altKPointSet': {'kPointCount': {'count': 240,
                                                 'gamma': False},
                                 'purpose': 'bands'},
                'valenceElectrons': 18.0,
                'mode': 'hist',
                'fermiSmearingEnergy': 0.001,
                'kPointList': {'posScale': '1.00000000', 'weightScale': '1.00000000', 'count': 1,
                               'kPoint': ['0.000000     0.000000     0.000000']},
            },
            'energyParameterLimits': {'ellow': -0.8, 'elup': 0.5},
        },
        'cell': {
            'symmetryOperations': {'symOp': {'row-1': '1 0 0 .0000000000',
                                             'row-2': '0 -1 0 .0000000000',
                                             'row-3': '0 0 1 .0000000000'}},
            'filmLattice': {
                'scale': 1.0,
                'dVac': 7.35,
                'latnam': 'any',
                'dTilda': 10.91,
                'bravaisMatrix': {'row-1': '5.301179702900000 .000000000000000 .000000000000000',
                                  'row-2': '.000000000000000 7.497000033000000 .000000000000000',
                                  'row-3': '.000000000000000 .000000000000000 7.992850008800000'},
                'vacuumEnergyParameters': {'vacuum': '2',
                                           'spinUp': '-.25000000',
                                           'spinDown': '-.25000000'},
            }},
        'xcFunctional': {'name': 'vwn', 'relativisticCorrections': False},
        'atomSpecies': {'species': [{
            'name': 'Fe-1',
            'element': 'Fe',
            'atomicNumber': 26,
            'coreStates': 7,
            'mtSphere': {'radius': 2.2, 'gridPoints': 787,
                         'logIncrement': 0.016},
            'atomicCutoffs': {'lmax': 10, 'lnonsphr': 6},
            'energyParameters': {
                's': 4,
                'p': 4,
                'd': 3,
                'f': 4,
            },
            'flipSpin': True,
            'magMom': 2.2,
            'prodBasis': {'lcutm': '4',
                          'lcutwf': '9',
                          'select': '4 0 4 2'},
            'electronConfig': {'coreConfig': '[Ar]',
                               'valenceConfig': '(4s1/2) (3d3/2) (3d5/2)',
                               'stateOccupation': [{'state': '(3d3/2)',
                                                    'spinUp': '2.00000000',
                                                    'spinDown': '1.00000000'},
                                                   {'state': '(3d5/2)',
                                                    'spinUp': '3.00000000',
                                                    'spinDown': '.00000000'}]},
        }, {
            'name': 'Pt-1',
            'element': 'Pt',
            'atomicNumber': 78,
            'coreStates': 19,
            'mtSphere': {'radius': 2.3, 'gridPoints': 787,
                         'logIncrement': 0.017},
            'atomicCutoffs': {'lmax': 10, 'lnonsphr': 6},
            'energyParameters': {
                's': 6,
                'p': 6,
                'd': 5,
                'f': 5,
            },
            'flipSpin': True,
            'magMom': 0.0,
            'prodBasis': {'lcutm': '4',
                          'lcutwf': '9',
                          'select': '4 0 4 2'},
            'electronConfig': {'coreConfig': '[Xe] (4f5/2) (4f7/2)',
                               'valenceConfig': '(6s1/2) (5d3/2) (5d5/2)',
                               'stateOccupation': [{'state': '(6s1/2)',
                                                    'spinUp': '.50000000',
                                                    'spinDown': '.50000000'},
                                                   {'state': '(5d5/2)',
                                                    'spinUp': '3.00000000',
                                                    'spinDown': '2.00000000'}]},
        }]},
        'atomGroups': {'atomGroup': [{
            'species': 'Fe-1',
            'filmPos': ['.0000000000 .0000000000 -.9964250044'],
            'force': {'calculate': True, 'relaxXYZ': 'TTT'},
            'nocoParams': {
                'l_relax': 'F',
                'alpha': 0.0,
                'beta': '1.570796326',
                'b_cons_x': '.00000000',
                'b_cons_y': '.00000000',
            },
        }, {
            'species': 'Pt-1',
            'filmPos': ['1.000/2.000 1.000/2.000 .9964250044'],
            'force': {'calculate': True, 'relaxXYZ': 'TTT'},
            'nocoParams': {
                'l_relax': 'F',
                'alpha': 0.0,
                'beta': '1.570796326',
                'b_cons_x': '.00000000',
                'b_cons_y': '.00000000',
            },
        }]},
        'output': {
            'dos': False,
            'band': False,
            'vacdos': False,
            'slice': False,
            'mcd': 'F',
            'checks': {'vchk': False, 'cdinf': False},
            'densityOfStates': {
                'ndir': 0,
                'minEnergy': -0.5,
                'maxEnergy': 0.5,
                'sigma': 0.015,
            },
            'vacuumDOS': {
                'layers': 0,
                'integ': False,
                'star': False,
                'nstars': 0,
                'locx1': 0.0,
                'locy1': 0.0,
                'locx2': 0.0,
                'locy2': 0.0,
                'nstm': 0,
                'tworkf': 0.0,
            },
            'unfoldingBand': {
                'unfoldBand': 'F',
                'supercellX': '1',
                'supercellY': '1',
                'supercellZ': '1',
            },
            'plotting':  {'iplot': 0,
                          'plplot': False,
                          'score': False},
            'chargeDensitySlicing': {
                'numkpt': 0,
                'minEigenval': 0.0,
                'maxEigenval': 0.0,
                'nnne': 0,
                'pallst': False,
            },
            'specialOutput': {'eonly': False, 'bmt': False},
            'magneticCircularDichroism': {'energyLo': '-10.00000000',
                                          'energyUp': '.00000000'},
        },
    }

    xml_structure = get_inpxml_file_structure()
    etree = inpxml_etree(TEST_INP_XML_PATH)
    inpxml_dict = inpxml_todict(clear_xml(etree).getroot(), xml_structure)

    assert inpxml_dict == correct


class TestShiftValue:
    from aiida_fleur.tools.xml_util import get_inpxml_file_structure
    xml_structure = get_inpxml_file_structure()

    attr_to_test = list(xml_structure[3])
    attr_to_test.extend(xml_structure[4])

    @pytest.mark.parametrize('attr_name', attr_to_test)
    def test_shift_value(self, inpxml_etree, attr_name):
        from aiida_fleur.tools.xml_util import shift_value, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        path = self.xml_structure[12][attr_name]
        result_before = eval_xpath2(etree, path + '/@{}'.format(attr_name))

        if not result_before:
            if attr_name in ['nx', 'ny', 'nz', 'scale']:
                pytest.skip("This attribute is not tested for FePt/inp.xml")
            raise BaseException('Can not find attribute that should exist in FePt/inp.xml')
        else:
            result_before = result_before[0]
            shift_value(etree, {attr_name: 333})
            result = eval_xpath2(etree, path + '/@{}'.format(attr_name))[0]

            assert float(result) - float(result_before) == 333

            shift_value(etree, {attr_name: 333})
            result = eval_xpath2(etree, path + '/@{}'.format(attr_name))[0]
            assert float(result) - float(result_before) == 666

    attr_to_test_float = list(xml_structure[4])
    @pytest.mark.parametrize('attr_name', attr_to_test_float)
    def test_shift_value_rel(self, inpxml_etree, attr_name):
        import math
        from aiida_fleur.tools.xml_util import shift_value, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        path = self.xml_structure[12][attr_name]
        result_before = eval_xpath2(etree, path + '/@{}'.format(attr_name))

        if not result_before:
            if attr_name in ['scale']:
                pytest.skip("This attribute is not tested for FePt/inp.xml")
            raise BaseException('Can not find attribute that should exist in FePt/inp.xml')
        else:
            result_before = result_before[0]
            shift_value(etree, {attr_name: 1.2442}, mode='rel')
            result = eval_xpath2(etree, path + '/@{}'.format(attr_name))[0]

            if float(result_before) != 0:
                assert math.isclose(float(result) / float(result_before), 1.2442, rel_tol=1e-6)
            else:
                assert float(result) == 0

    def test_shift_value_errors(self, inpxml_etree, capsys):
        from aiida_fleur.tools.xml_util import shift_value
        etree = inpxml_etree(TEST_INP_XML_PATH)

        with pytest.raises(ValueError) as excinfo:
            shift_value(etree, {'does_not_exist': 1.2442})
        assert "Given attribute name either does not ex" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            shift_value(etree, {'jspins': 3.3})
        assert "You are trying to write a float" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            shift_value(etree, {'l_noco': 33})
        assert "Given attribute name either does not ex" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            shift_value(etree, {'jspins': 33}, mode='not_a_mode')
        assert "Mode should be 'res' " in str(excinfo.value)

        shift_value(etree, {'nz': 333})
        captured = capsys.readouterr()
        assert captured.out == 'Can not find nz attribute in the inp.xml, skip it\n'

class TestShiftSpeciesLabel:
    attr_names = ['radius', 'gridPoints', 'logIncrement', 'lmax', 'lnonsphr', 's', 'p', 'd', 'f']
    tags = ['mtSphere', 'mtSphere', 'mtSphere', 'atomicCutoffs', 'atomicCutoffs',
            'energyParameters','energyParameters', 'energyParameters', 'energyParameters']

    @pytest.mark.parametrize('att_name,tag', zip(attr_names, tags))
    def test_shift_species_label(self, inpxml_etree, att_name, tag):
        from aiida_fleur.tools.xml_util import shift_value_species_label, eval_xpath2
        import math
        etree = inpxml_etree(TEST_INP_XML_PATH)
        path = '/fleurInput/atomSpecies/species[@name = "Fe-1"]/' + tag + '/@' + att_name
        old_result = eval_xpath2(etree, path)[0]

        shift_value_species_label(etree, '                 222', att_name, 3, mode='abs')
        result = eval_xpath2(etree, path)[0]

        assert math.isclose(float(result) - float(old_result), 3)

    attr_names_float = ['radius', 'logIncrement']
    tags_float = ['mtSphere', 'mtSphere']

    @pytest.mark.parametrize('att_name,tag', zip(attr_names_float, tags_float))
    def test_shift_species_label_rel(self, inpxml_etree, att_name, tag):
        from aiida_fleur.tools.xml_util import shift_value_species_label, eval_xpath2
        import math
        etree = inpxml_etree(TEST_INP_XML_PATH)
        path = '/fleurInput/atomSpecies/species[@name = "Fe-1"]/' + tag + '/@' + att_name
        untouched = '/fleurInput/atomSpecies/species[@name = "Pt-1"]/' + tag + '/@' + att_name
        old_result = eval_xpath2(etree, path)[0]
        untouched_result = eval_xpath2(etree, untouched)[0]

        shift_value_species_label(etree, '                 222', att_name, 3.2, mode='rel')
        result = eval_xpath2(etree, path)[0]
        untouched_result_new = eval_xpath2(etree, untouched)[0]

        assert math.isclose(float(result) / float(old_result), 3.2)
        assert math.isclose(float(untouched_result_new) / float(untouched_result), 1.0)

    @pytest.mark.parametrize('att_name,tag', zip(attr_names, tags))
    def test_shift_species_label_all(self, inpxml_etree, att_name, tag):
        from aiida_fleur.tools.xml_util import shift_value_species_label, eval_xpath2
        import numpy as np
        etree = inpxml_etree(TEST_INP_XML_PATH)
        path = '/fleurInput/atomSpecies/species/' + tag + '/@' + att_name
        old_result = np.array(eval_xpath2(etree, path)).astype('float')

        shift_value_species_label(etree, 'all', att_name, 3, mode='abs')
        result = np.array(eval_xpath2(etree, path)).astype('float')

        assert np.all(np.isclose(old_result + 3, result))

    @pytest.mark.parametrize('att_name,tag', zip(attr_names, tags))
    def test_shift_species_label_all_rel(self, inpxml_etree, att_name, tag):
        from aiida_fleur.tools.xml_util import shift_value_species_label, eval_xpath2
        import numpy as np
        etree = inpxml_etree(TEST_INP_XML_PATH)
        path = '/fleurInput/atomSpecies/species/' + tag + '/@' + att_name
        old_result = np.array(eval_xpath2(etree, path)).astype('float')

        shift_value_species_label(etree, 'all', att_name, 2, mode='rel')
        result = np.array(eval_xpath2(etree, path)).astype('float')

        assert np.all(np.isclose(old_result*2, result))
class TestAddNumToAtt:
    from aiida_fleur.tools.xml_util import get_inpxml_file_structure
    xml_structure = get_inpxml_file_structure()

    attr_to_test = list(xml_structure[3])
    attr_to_test.extend(xml_structure[4])

    @pytest.mark.parametrize('attr_name', attr_to_test)
    def test_add_num_to_att(self, inpxml_etree, attr_name):
        from aiida_fleur.tools.xml_util import add_num_to_att, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        path = self.xml_structure[12][attr_name]
        result_before = eval_xpath2(etree, path + '/@{}'.format(attr_name))

        if not result_before:
            if attr_name in ['nx', 'ny', 'nz', 'scale']:
                pytest.skip("This attribute is not tested for FePt/inp.xml")
            raise BaseException('Can not find attribute that should exist in FePt/inp.xml')
        else:
            result_before = result_before[0]
            add_num_to_att(etree, path, attr_name, 333)
            result = eval_xpath2(etree, path + '/@{}'.format(attr_name))[0]

            assert float(result) - float(result_before) == 333

    attr_to_test_float = list(xml_structure[4])
    @pytest.mark.parametrize('attr_name', attr_to_test_float)
    def test_ad_num_to_att_rel(self, inpxml_etree, attr_name):
        import math
        from aiida_fleur.tools.xml_util import add_num_to_att, eval_xpath2
        etree = inpxml_etree(TEST_INP_XML_PATH)

        path = self.xml_structure[12][attr_name]
        result_before = eval_xpath2(etree, path + '/@{}'.format(attr_name))

        if not result_before:
            if attr_name in ['scale']:
                pytest.skip("This attribute is not tested for FePt/inp.xml")
            raise BaseException('Can not find attribute that should exist in FePt/inp.xml')
        else:
            result_before = result_before[0]
            add_num_to_att(etree, path, attr_name, 1.2442, mode='rel')
            result = eval_xpath2(etree, path + '/@{}'.format(attr_name))[0]


            if float(result_before) != 0:
                assert math.isclose(float(result) / float(result_before), 1.2442, rel_tol=1e-6)
            else:
                assert float(result) == 0


# get_xml_attribute
def test_get_xml_attribute(inpxml_etree):
    from aiida_fleur.tools.xml_util import get_xml_attribute
    pass

# get_inpxml_file_structure
# IMPORTANT: Here we need thats that tell us when the plugin has to be maintained, i.e Know thing in the inp schema where changed
# Is there a way to test for not yet know attributes? i.e if the plugin is complete? Back compatible?
# I.e make for each Fleur schema file, complete inp.xml file version a test if the attributes exists.
