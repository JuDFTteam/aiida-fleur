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
''' Contains tests for modifing FleurinpData with Fleurinpmodifier '''

import os
import copy
import pytest
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier, inpxml_changes
from aiida import orm

# Collect the input files
file_path1 = '../files/inpxml/FePt/inp.xml'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
inpxmlfilefolder = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))


def test_fleurinp_modifier1(create_fleurinp):
    """Tests if fleurinp_modifier with various modifations on species"""
    from masci_tools.io.fleurxmlmodifier import ModifierTask
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
    fm.shift_value({'Kmax': 0.1}, 'rel')
    fm.shift_value_species_label('                 222', 'radius', 3, mode='abs')
    fm.set_species('all', {'mtSphere': {'radius': 3.333}})
    fm.undo()
    changes = fm.changes()

    assert changes == [
        ModifierTask(name='set_inpchanges', args=({
            'dos': True,
            'Kmax': 3.9
        },), kwargs={}),
        ModifierTask(name='shift_value', args=({
            'Kmax': 0.1
        }, 'rel'), kwargs={}),
        ModifierTask(name='shift_value_species_label',
                     args=('                 222', 'radius', 3),
                     kwargs={'mode': 'abs'})
    ]

    fm.show(validate=True)
    fm.freeze()

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
    fm.undo(revert_all=True)
    changes = fm.changes()
    assert len(changes) == 0


def test_fleurinp_modifier_regression(create_fleurinp, file_regression):
    """Tests if fleurinp_modifier with various other modifations methods,
    the detailed tests for method functionality is tested elsewhere."""
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
    fm.shift_value({'Kmax': 0.1}, 'rel')
    fm.shift_value_species_label('                 222', 'radius', 3, mode='abs')
    fm.set_species('all', {'mtSphere': {'radius': 3.333}})
    fm.add_number_to_attrib('minDistance', 4)

    fm.show()

    new_fleurinp = fm.freeze()

    file_regression.check(new_fleurinp.get_content('inp.xml'), extension='.xml')


def test_fleurinp_modifier_included_files(create_fleurinp, inpxml_etree, file_regression):
    """Tests if fleurinp_modifier with various other modifations methods,
    the detailed tests for method functionality is tested elsewhere."""

    TEST_FOLDER = os.path.dirname(os.path.abspath(__file__))
    TEST_FOLDER = os.path.abspath(os.path.join(TEST_FOLDER, '../files/included_xml_files'))

    INPXML_FILE = os.path.join(TEST_FOLDER, 'inp.xml')
    KPTSXML_FILE = os.path.join(TEST_FOLDER, 'kpts.xml')
    SYMXML_FILE = os.path.join(TEST_FOLDER, 'sym.xml')

    fleurinp_tmp = create_fleurinp(INPXML_FILE, additional_files=[KPTSXML_FILE, SYMXML_FILE])

    fm = FleurinpModifier(fleurinp_tmp)
    #Modify main inp.xml file
    fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
    fm.shift_value({'Kmax': 0.1}, 'rel')

    #Modify included xml files
    fm.delete_tag('symmetryOperations')
    fm.create_tag('symmetryOperations')
    fm.create_tag('kPointList')
    fm.create_tag('kPoint', occurrences=0)
    fm.set_attrib_value('name', 'TEST', contains='kPointList', occurrences=0)
    fm.set_text('kPoint', [0.0, 0.0, 0.0],
                complex_xpath="/fleurInput/cell/bzIntegration/kPointLists/kPointList[@name='TEST']/kPoint")

    fm.show()

    new_fleurinp = fm.freeze()

    assert new_fleurinp.files == ['kpts.xml', 'sym.xml', 'inp.xml']

    file_content = [
        new_fleurinp.get_content('inp.xml'),
        new_fleurinp.get_content('kpts.xml'),
        new_fleurinp.get_content('sym.xml')
    ]

    file_regression.check('\n'.join(file_content), extension='.xml')


#For this test we need a input file with defined LDA+U procedures
file_path2 = '../files/inpxml/GaAsMultiForceXML/inp.xml'

inpxmlfilefolder2 = os.path.dirname(os.path.abspath(__file__))
inpxmlfilefolder2 = os.path.abspath(os.path.join(inpxmlfilefolder2, file_path2))


def test_fleurinp_modifier_set_nmmpmat(create_fleurinp):
    """Tests if set_nmmpmat works on fleurinp modifier works, with right interface"""
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder2)

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_nmmpmat('Ga-1', orbital=2, spin=1, state_occupations=[1, 2, 3, 4, 5])
    fm.set_nmmpmat('As-2', orbital=1, spin=1, denmat=[[1, -2, 3], [4, -5, 6], [7, -8, 9]])

    # Does not validate
    # Found invalid diagonal element for species Ga-1, spin 1 and l=2
    with pytest.raises(ValueError):
        fm.show(validate=True, display=False)
    new_fleurinp = fm.freeze()
    assert 'n_mmp_mat' in new_fleurinp.files


def test_fleurinp_modifier_instance_modifications(create_fleurinp):
    """Tests if set_nmmpmat works on fleurinp modifier works, with right interface"""
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder2)

    n_mmp_mat_file = os.path.dirname(os.path.abspath(__file__))
    n_mmp_mat_file = os.path.abspath(os.path.join(n_mmp_mat_file, '../files/n_mmp_mat/n_mmp_mat_GaAsMultiForceXML'))

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_file(n_mmp_mat_file, dst_filename='n_mmp_mat')

    tasks_before = copy.deepcopy(fm._tasks)
    fm.show()
    assert fm._tasks == tasks_before

    fm.validate()
    assert fm._tasks == tasks_before

    new_fleurinp = fm.freeze()
    assert 'n_mmp_mat' in new_fleurinp.files

    fm = FleurinpModifier(new_fleurinp)
    fm.del_file('n_mmp_mat')
    new_fleurinp = fm.freeze()
    assert 'n_mmp_mat' not in new_fleurinp.files


def test_fleurinp_modifier_instance_modifications_node(create_fleurinp):
    """Tests if set_nmmpmat works on fleurinp modifier works, with right interface"""
    from aiida.orm import FolderData
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder2)

    n_mmp_mat_folder = os.path.dirname(os.path.abspath(__file__))
    n_mmp_mat_folder = os.path.abspath(os.path.join(n_mmp_mat_folder, '../files/n_mmp_mat'))

    n_mmp_mat_folder = FolderData(tree=n_mmp_mat_folder)
    n_mmp_mat_folder.store()

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_file('n_mmp_mat_GaAsMultiForceXML', dst_filename='n_mmp_mat', node=n_mmp_mat_folder)

    new_fleurinp = fm.freeze()
    assert 'n_mmp_mat' in new_fleurinp.files

    fm = FleurinpModifier(new_fleurinp)
    fm.del_file('n_mmp_mat')
    deleted_file = fm.freeze()
    assert 'n_mmp_mat' not in deleted_file.files

    fm = FleurinpModifier(new_fleurinp)
    fm.del_file('n_mmp_mat')
    fm.set_file('n_mmp_mat_GaAsMultiForceXML', dst_filename='n_mmp_mat', node=n_mmp_mat_folder.uuid)
    new_fleurinp = fm.freeze()
    assert 'n_mmp_mat' in new_fleurinp.files


def test_fleurinp_modifier_set_kpointsdata(create_fleurinp):
    """Test if setting a kpoints list to a fleurinp data node works"""
    from aiida.orm import KpointsData

    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)
    fleurinp_tmp.store()  # needed?
    struc = fleurinp_tmp.get_structuredata_ncf()

    kps = KpointsData()
    kps.set_cell(struc.cell)
    kps.pbc = struc.pbc
    kpoints_pos = [[0.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.5, 0.0, 0.0], [0.5, 0.0, 0.5], [0.5, 0.5, 0.5], [1.0, 1.0, 1.0]]
    kpoints_weight = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    # Fleur renormalizes
    kps.set_kpoints(kpoints_pos, cartesian=False, weights=kpoints_weight)

    kps.store()  # needed, because node has to be loaded...
    #print(fleurinp_tmp)
    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_kpointsdata(kps)

    fm.show(validate=True, display=False)
    fm.freeze()

    # check if kpoint node is input into modification
    # uuid of node show also work
    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_kpointsdata(kps.uuid)
    fm.freeze()


def test_fleurinpmodifier_error_messages(create_fleurinp):
    """Test error interface of fleurinpmodifier"""
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)

    fm = FleurinpModifier(fleurinp_tmp)
    fm._tasks.append(('not_existent', [1, 2, 3], {'Random_arg': 'Does not make sense'}))  # task does not exists.
    with pytest.raises(ValueError):
        fm.freeze()

    fm = FleurinpModifier(fleurinp_tmp)


def test_fleurinpmodifier_element_serialization(create_fleurinp):
    """Tests of fleurinpmodifier registration methods accepting etree.Elements as arguments
    If any of these don't serialize the elements correctly you will see an error that etree.fromstring
    is passed an empty list (This is a weird side effect for etree._Element of the automatic serialization done in aiida-core)
    """
    from lxml import etree
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)

    fm = FleurinpModifier(fleurinp_tmp)
    fm.create_tag(etree.Element('expertModes'))
    fm.delete_tag('expertModes')
    fm.create_tag(tag=etree.Element('expertModes'))
    fm.delete_tag('expertModes')
    fm.create_tag(etree.Element('expertModes'), '/fleurInput/calculationSetup')
    fm.delete_tag('expertModes')
    fm.xml_create_tag('/fleurInput/calculationSetup', etree.Element('expertModes'))
    fm.delete_tag('expertModes')
    fm.xml_create_tag('/fleurInput/calculationSetup', element=etree.Element('expertModes'))
    fm.delete_tag('expertModes')
    fm.xml_create_tag('/fleurInput/calculationSetup', etree.Element('expertModes'), 0)

    fm.replace_tag('expertModes', etree.Element('expertModes'))
    fm.replace_tag('expertModes', element=etree.Element('expertModes'))
    fm.replace_tag('expertModes', etree.Element('expertModes'), '/fleurInput/calculationSetup/expertModes')
    fm.xml_replace_tag('/fleurInput/calculationSetup/expertModes', etree.Element('expertModes'))
    fm.xml_replace_tag('/fleurInput/calculationSetup/expertModes', element=etree.Element('expertModes'))
    fm.xml_replace_tag('/fleurInput/calculationSetup/expertModes', etree.Element('expertModes'), 0)

    fm.show()
    fm.freeze()


def test_inpxml_changes():
    """
    Test of the inpxml_changes contextmanager
    """
    from aiida_fleur.workflows.banddos import FleurBandDosWorkChain
    d = {}
    with inpxml_changes(d) as fm:
        fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
        fm.shift_value({'Kmax': 0.1}, 'rel')
        fm.shift_value_species_label('                 222', 'radius', 3, mode='abs')
        fm.set_species('all', {'mtSphere': {'radius': 3.333}})
        fm.set_file('test', dst_filename='/test/path')

    assert d == {
        'inpxml_changes': [('set_inpchanges', {
            'changes': {
                'Kmax': 3.9,
                'dos': True
            }
        }), ('shift_value', {
            'changes': {
                'Kmax': 0.1
            },
            'mode': 'rel'
        }),
                           ('shift_value_species_label', {
                               'atom_label': '                 222',
                               'attribute_name': 'radius',
                               'mode': 'abs',
                               'number_to_add': 3
                           }), ('set_species', {
                               'changes': {
                                   'mtSphere': {
                                       'radius': 3.333
                                   }
                               },
                               'species_name': 'all'
                           }), ('set_file', {
                               'dst_filename': '/test/path',
                               'filename': 'test',
                               'node': None
                           })]
    }

    d['test'] = 'A'
    d = orm.Dict(dict=d)
    with inpxml_changes(d, append=False) as fm:
        fm.delete_tag('symmetryOperations')
        fm.create_tag('symmetryOperations')

    assert d.get_dict() == {
        'test':
        'A',
        'inpxml_changes': [('delete_tag', {
            'tag_name': 'symmetryOperations'
        }), ('create_tag', {
            'tag': 'symmetryOperations'
        }), ('set_inpchanges', {
            'changes': {
                'Kmax': 3.9,
                'dos': True
            }
        }), ('shift_value', {
            'changes': {
                'Kmax': 0.1
            },
            'mode': 'rel'
        }),
                           ('shift_value_species_label', {
                               'atom_label': '                 222',
                               'attribute_name': 'radius',
                               'mode': 'abs',
                               'number_to_add': 3
                           }), ('set_species', {
                               'changes': {
                                   'mtSphere': {
                                       'radius': 3.333
                                   }
                               },
                               'species_name': 'all'
                           }), ('set_file', {
                               'dst_filename': '/test/path',
                               'filename': 'test',
                               'node': None
                           })]
    }

    d = FleurBandDosWorkChain.get_builder()
    with inpxml_changes(d) as fm:
        fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
        fm.shift_value({'Kmax': 0.1}, 'rel')
        fm.shift_value_species_label('                 222', 'radius', 3, mode='abs')
        fm.set_species('all', {'mtSphere': {'radius': 3.333}})

    with inpxml_changes(d.scf) as fm:
        fm.delete_tag('symmetryOperations')
        fm.create_tag('symmetryOperations')

    assert d.wf_parameters.get_dict() == {
        'inpxml_changes': [('set_inpchanges', {
            'changes': {
                'Kmax': 3.9,
                'dos': True
            }
        }), ('shift_value', {
            'changes': {
                'Kmax': 0.1
            },
            'mode': 'rel'
        }),
                           ('shift_value_species_label', {
                               'atom_label': '                 222',
                               'attribute_name': 'radius',
                               'mode': 'abs',
                               'number_to_add': 3
                           }), ('set_species', {
                               'changes': {
                                   'mtSphere': {
                                       'radius': 3.333
                                   }
                               },
                               'species_name': 'all'
                           })]
    }
    assert d.scf.wf_parameters.get_dict() == {
        'inpxml_changes': [('delete_tag', {
            'tag_name': 'symmetryOperations'
        }), ('create_tag', {
            'tag': 'symmetryOperations'
        })]
    }

    d = FleurBandDosWorkChain.get_builder()
    d.wf_parameters = orm.Dict(
        dict={
            'test':
            'A',
            'inpxml_changes': [('delete_tag', {
                'tag_name': 'symmetryOperations'
            }), ('create_tag', {
                'tag': 'symmetryOperations'
            })]
        }).store()
    with pytest.raises(ValueError):
        with inpxml_changes(d, builder_replace_stored=False) as fm:
            fm.set_inpchanges({'dos': True, 'Kmax': 3.9})

    with inpxml_changes(d) as fm:
        fm.set_inpchanges({'dos': True, 'Kmax': 3.9})

    assert d.wf_parameters.get_dict() == {
        'inpxml_changes': [['delete_tag', {
            'tag_name': 'symmetryOperations'
        }], ['create_tag', {
            'tag': 'symmetryOperations'
        }], ('set_inpchanges', {
            'changes': {
                'Kmax': 3.9,
                'dos': True
            }
        })],
        'test':
        'A'
    }

    d = orm.Dict(dict={}).store()
    with pytest.raises(ValueError):
        with inpxml_changes(d) as fm:
            pass

    d = orm.Dict(dict={})
    with inpxml_changes(d) as fm:
        with pytest.raises(ValueError):
            fm.show()
        with pytest.raises(ValueError):
            fm.validate()
        with pytest.raises(ValueError):
            fm.freeze()
