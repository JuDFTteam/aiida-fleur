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
''' Contains tests for StructureData util '''
import pytest
import numpy as np


def test_is_structure(generate_structure):
    """Test if is structure can differentiate between structures, identifiers and else"""
    from aiida_fleur.tools.StructureData_util import is_structure
    from aiida.orm import Dict

    dict_test = Dict({})
    dict_test.store()

    structure = generate_structure()
    structure.store()

    assert is_structure(structure)
    assert is_structure(structure.pk)
    assert is_structure(structure.uuid)
    assert is_structure('asfasfas') is None
    assert is_structure(555212) is None
    assert is_structure(dict_test.pk) is None


def test_is_primitive(generate_structure):
    """Test if is_primitive test can distinguish between a primitive and non primitive structure"""
    from aiida_fleur.tools.StructureData_util import is_primitive
    structure = generate_structure()
    structure.store()

    assert is_primitive(structure)

    structure = generate_structure()
    structure.clear_sites()
    param = 5.43
    structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
    structure.append_atom(position=(param / 2., param / 2., param / 2.), symbols='Si', name='Si')
    structure.store()

    assert not is_primitive(structure)


def test_rescale_nowf(generate_structure):
    """Test to rescale some structure """
    from aiida_fleur.tools.StructureData_util import rescale_nowf
    from aiida_fleur.tools.StructureData_util import rescale
    from aiida.orm import Dict, Float

    structure = generate_structure()
    old_cell = np.array(structure.cell)

    rescaled = rescale_nowf(structure, 1.05)
    rescaled2 = rescale(structure, Float(1.05))
    rescaled_cell = np.array(rescaled.cell)
    rescaled_cell2 = np.array(rescaled2.cell)

    assert (rescaled_cell == 1.05**(1 / 3.) * old_cell).all()
    #assert (np.round(rescaled_cell2, 13) == 1.05**(1 / 3.) * old_cell).all()
    # This does not work, seems to check if it is the same object, not if values are the same
    # The precision between these functions is strangely different
    assert list(np.round(rescaled_cell[0], 13)) == list(rescaled_cell2[0])
    assert list(np.round(rescaled_cell[1], 13)) == list(rescaled_cell2[1])
    assert list(np.round(rescaled_cell[2], 13)) == list(rescaled_cell2[2])

    positions_old = [x.position for x in structure.sites]
    positions_rescaled = [x.position for x in rescaled.sites]
    for position in positions_old:
        assert tuple(pos * 1.05**(1 / 3.) for pos in position) in positions_rescaled

    no_struc = Dict({})
    no_rescaled = rescale_nowf(no_struc, 1.05)
    assert no_rescaled is None


def test_supercell(generate_structure):
    """Test to create a super cell"""
    from aiida_fleur.tools.StructureData_util import supercell
    from aiida_fleur.tools.StructureData_util import supercell_ncf
    from aiida.orm import Int
    from itertools import product

    structure = generate_structure()

    supercell = supercell(structure, Int(2), Int(3), Int(4))

    assert (supercell.cell[0] == np.array(structure.cell[0]) * 2).all()
    assert (supercell.cell[1] == np.array(structure.cell[1]) * 3).all()
    assert (supercell.cell[2] == np.array(structure.cell[2]) * 4).all()
    assert len(supercell.sites) == 2 * 3 * 4 * len(structure.sites)

    positions_old = [x.position for x in structure.sites]
    positions_rescaled = [x.position for x in supercell.sites]
    for position in positions_old:
        for x, y, z in product(range(2), range(3), range(4)):
            test_pos = tuple(
                np.array(position) + x * np.array(structure.cell[0]) + y * np.array(structure.cell[1]) +
                z * np.array(structure.cell[2]))
            assert test_pos in positions_rescaled

    no_struc = Int(1)
    no_supercell = supercell_ncf(no_struc, 2, 3, 4)
    assert no_supercell is None


def test_break_symmetry_wf_film_structure_only(generate_film_structure):
    """Check if it does not crash and able to destroy all symmetries"""
    from aiida_fleur.tools.StructureData_util import break_symmetry_wf, supercell_ncf
    from aiida_fleur.tools.StructureData_util import break_symmetry
    from aiida.orm import Dict

    structure = generate_film_structure()
    structure = supercell_ncf(structure, 2, 2, 1)

    out = break_symmetry_wf(
        structure,
        wf_para=Dict(dict={}),
    )
    structure_broken = out['new_structure']
    kind_names = [x.kind_name for x in structure_broken.sites]
    kind_names_should = ['Fe1', 'Fe2', 'Fe3', 'Fe4', 'Pt1', 'Pt2', 'Pt3', 'Pt4', 'Pt5', 'Pt6', 'Pt7', 'Pt8']
    for kind_name in kind_names_should:
        assert kind_name in kind_names
    assert len(set(kind_names)) == len(kind_names_should)

    struc_b_fe, para_new_fe = break_symmetry(structure, atoms=['Fe'])
    kind_names = [x.kind_name for x in struc_b_fe.sites]
    kind_names_should = ['Fe1', 'Fe2', 'Fe3', 'Fe4', 'Pt']
    for kind_name in kind_names_should:
        assert kind_name in kind_names
    assert len(set(kind_names)) == len(kind_names_should)

    struc_b_pt, para_new_pt = break_symmetry(structure, atoms=['Pt'])
    kind_names = [x.kind_name for x in struc_b_pt.sites]
    kind_names_should = ['Fe', 'Pt1', 'Pt2', 'Pt3', 'Pt4', 'Pt5', 'Pt6', 'Pt7', 'Pt8']
    for kind_name in kind_names_should:
        assert kind_name in kind_names
    assert len(set(kind_names)) == len(kind_names_should)

    struc_b_site, para_new_site = break_symmetry(structure, atoms=[], site=[0, 1])
    kind_names = [x.kind_name for x in struc_b_site.sites]
    kind_names_should = ['Fe', 'Fe1', 'Fe2', 'Pt']
    for kind_name in kind_names_should:
        assert kind_name in kind_names
    assert len(set(kind_names)) == len(kind_names_should)

    pos = [structure.sites[0].position, structure.sites[1].position]

    struc_b_pos, para_new_pos = break_symmetry(structure, atoms=[], pos=pos)
    kind_names = [x.kind_name for x in struc_b_pos.sites]
    kind_names_should = ['Fe', 'Fe1', 'Fe2', 'Pt']
    for kind_name in kind_names_should:
        assert kind_name in kind_names
    assert len(set(kind_names)) == len(kind_names_should)


def test_break_symmetry_corhole(generate_structure):
    """Test if what the corehole workflow does works"""
    from aiida_fleur.tools.StructureData_util import break_symmetry
    from aiida import orm

    structure = generate_structure()
    sites = structure.sites
    pos = sites[0].position
    kind_name = sites[0].kind_name
    para = orm.Dict(dict={
        'atom': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }
    })
    new_kinds_names = {'Si': [kind_name + '_corehole1']}
    inputs = {
        'structure': structure,
        'atoms': [],
        'site': [],
        'pos': [(pos[0], pos[1], pos[2])],
        'new_kinds_names': new_kinds_names
    }
    if para is not None:
        inputs['parameterdata'] = para
    new_struc, new_para = break_symmetry(**inputs)

    #print(new_para.get_dict())
    kind_names = ['Si_corehole1', 'Si']
    for i, site in enumerate(new_struc.sites):
        assert site.kind_name == kind_names[i]

    # Test if the kind name was set to the atom lists
    should = {
        'atom1': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0
        },
        'atom2': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6,
            'id': '14.1',
            'name': 'Si_corehole1'
        }
    }
    assert new_para.get_dict() == should


def test_break_symmetry_film_parameters_only_simple(generate_film_structure):
    """Test if these break symmetry operation adjusted the parameter data right.
    This basicly tests
    from aiida_fleur.tools.StructureData_util import adjust_calc_para_to_structure
    for a separate test we would have to generate these structures again
    """
    from aiida_fleur.tools.StructureData_util import break_symmetry
    from aiida.orm import Dict

    structure = generate_film_structure()
    para = Dict({
        'atom': {
            'element': 'Fe',
            'z': 26,
            'rmt': 2.1,
            'bmu': -1
        },
        'atom1': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1
        },
        'comp': {
            'kmax': 5.0,
        }
    })

    structure_broken, para_out = break_symmetry(structure, parameterdata=para)
    should1 = {
        'atom1': {
            'element': 'Fe',
            'z': 26,
            'rmt': 2.1,
            'bmu': -1
        },
        'atom2': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1
        },
        'comp': {
            'kmax': 5.0
        },
        'atom3': {
            'element': 'Fe',
            'z': 26,
            'rmt': 2.1,
            'bmu': -1,
            'id': '26.1'
        },
        'atom4': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1,
            'id': '78.1'
        },
        'atom5': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1,
            'id': '78.2'
        }
    }
    assert para_out.get_dict() == should1

    # breaking again should not change something
    structure_broken, para_out = break_symmetry(structure_broken, parameterdata=para_out)
    assert para_out.get_dict() == should1

    should2 = {
        'comp': {
            'kmax': 5.0
        },
        'atom1': {
            'element': 'Fe',
            'z': 26,
            'rmt': 2.1,
            'bmu': -1,
            'id': '26.1'
        },
        'atom2': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1,
            'id': '78.1'
        },
        'atom3': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1,
            'id': '78.2'
        }
    }
    structure_broken, para_out = break_symmetry(structure_broken, parameterdata=para_out, add_atom_base_lists=False)
    print(para_out.get_dict())
    assert para_out.get_dict() == should2

    struc_b_fe, para_new_fe = break_symmetry(structure, atoms=['Fe'], parameterdata=para)

    should3 = {
        'atom1': {
            'element': 'Fe',
            'z': 26,
            'rmt': 2.1,
            'bmu': -1
        },
        'atom2': {
            'element': 'Pt',
            'rmt': 2.2,
            'bmu': 1
        },
        'comp': {
            'kmax': 5.0
        },
        'atom3': {
            'element': 'Fe',
            'z': 26,
            'rmt': 2.1,
            'bmu': -1,
            'id': '26.1'
        }
    }
    assert para_new_fe.get_dict() == should3


def test_break_symmetry_film_parameters_only_complex(generate_film_structure):
    """Test if these break symmetry operation adjusted the complex parameter data right.
    This basicly tests
    from aiida_fleur.tools.StructureData_util import adjust_calc_para_to_structure
    for a separate test we would have to generate these structures again
    """
    from aiida_fleur.tools.StructureData_util import break_symmetry
    from aiida.orm import Dict

    structure = generate_film_structure()
    para = Dict({
        'atom': {
            'element': 'Fe',
            'id': 26.1,
            'rmt': 2.1,
            'bmu': -1
        },
        'atom1': {
            'element': 'Pt',
            'id': 78.1,
            'rmt': 2.2,
            'bmu': 1
        },
        'comp': {
            'kmax': 5.0,
        }
    })

    structure_broken, para_out = break_symmetry(structure, parameterdata=para)
    struc_b_fe, para_new_fe = break_symmetry(structure, atoms=['Fe'], parameterdata=para)

    should1 = {
        'atom1': {
            'element': 'Fe',
            'id': '26.1',
            'rmt': 2.1,
            'bmu': -1
        },
        'atom2': {
            'element': 'Pt',
            'id': '78.1',
            'rmt': 2.2,
            'bmu': 1
        },
        'atom3': {
            'element': 'Pt',
            'id': '78.2',
            'rmt': 2.2,
            'bmu': 1
        },
        'comp': {
            'kmax': 5.0,
        }
    }

    assert para_out.get_dict() == should1

    should2 = {'atom1': {'bmu': -1, 'element': 'Fe', 'id': '26.1', 'rmt': 2.1}, 'comp': {'kmax': 5.0}}
    assert para_new_fe.get_dict() == should2
    # Deletes the other Ids because Pt had an id


'''


    # old should dict
    should_out_dict = {
        'atom': {
            'id': 26,
            'rmt': 2.1,
            'bmu': -1
        },
        'atom1': {
            'id': 78.1,
            'rmt': 2.1,
            'bmu': -1
        },
        'atom2': {
            'id': 78.2,
            'rmt': 2.2,
            'bmu': 1
        }
    }

    should_out_dict = {'atom1': {'z': 26, 'rmt': 2.1, 'bmu': -1},
    'atom2': {'z': 26, 'rmt': 2.1, 'bmu': -1, 'id': '26.1'},
    'atom3': {'z': 26, 'rmt': 2.1, 'bmu': -1, 'id': '26.2'},
    'atom4': {'z': 26, 'rmt': 2.1, 'bmu': -1, 'id': '26.3'},
    'atom5': {'z': 26, 'rmt': 2.1, 'bmu': -1, 'id': '26.4'}}
    parameter_data = Dict(
        dict={
            'atom': {
                'z': 26,
                'rmt': 2.1,
                'bmu': -1
            },
            'atom1': {
                'id': 78.1,
                'rmt': 2.1,
                'bmu': -1
            },
            'atom2': {
                'id': 78.2,
                'rmt': 2.2,
                'bmu': 1
            }
        })
    out, parameterdata_new = break_symmetry(structure, parameterdata=parameter_data)
    out_dict = parameterdata_new.get_dict()
    print(out_dict)
    assert out_dict == should_out_dict
'''
'''
def test_break_symmetry_bulk(generate_structure):
    """Check if it does not crash and able to destroy all symmetries"""
    from aiida_fleur.tools.StructureData_util import break_symmetry, supercell_ncf
    from aiida.orm import Dict

    structure = generate_structure()

    # Test if break symmetry adjusts parameters right with simple parameters

    parameter_data = Dict(
        dict={
        'atom': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }})
    structure_broken, parameters1  = break_symmetry(structure, parameterdata=parameter_data)

    print('para1', parameters1.get_dict())
    should_para1 = {
        'atom0': {
            'element': 'Si',
            'id': 14.1,
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'atom1': {
            'element': 'Si',
            'id': 14.2,
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }}
    assert parameters1.get_dict() == should_para1
    # Now test if it also adjusts for complex parameters right
    parameter_data2 = Dict(dict={
        'atom1': {
            'element': 'Si',
            'id': 14.1,
            'rmt': 2.2,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'atom2': {
            'element': 'Si',
            'z' : 14,
            'id': 14.2,
            'rmt': 2.1,
            'jri': 981,
            'lmax': 11,
            'lnonsph': 6
        },
        'atom': {
            'element': 'Si',
            'rmt': 2.0,
            'jri': 981,
            'lmax': 10,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }
    })
    structure = supercell_ncf(structure, 2, 1, 1)
    # Test if break symmetry adjusts the parameter data right.
    structure_broken, parameters2 = break_symmetry(structure, parameterdata=parameter_data2)
    kind_names = [x.kind_name for x in structure_broken.sites]
    for kind_name in ['Si1', 'Si2', 'Si3', 'Si4']:
        assert kind_name in kind_names
    print('para2', parameters2.get_dict())
    para2_should = {
        'atom1': {
            'element': 'Si',
            'id': 14.1,
            'rmt': 2.2,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'atom2': {
            'element': 'Si',
            'z' : 14,
            'id': 14.2,
            'rmt': 2.1,
            'jri': 981,
            'lmax': 11,
            'lnonsph': 6
        },
        'atom0': {
            'element': 'Si',
            'id': 14.3,
            'rmt': 2.0,
            'jri': 981,
            'lmax': 10,
            'lnonsph': 6
        },
        'atom3': {
            'element': 'Si',
            'id': 14.4,
            'rmt': 2.0,
            'jri': 981,
            'lmax': 10,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }
    }

    assert para2_should == parameters2.get_dict()
    #TODO test break_symmetry with several different elements in parameter and structure
'''


def test_adjust_calc_para_to_structure(generate_structure):
    """Test intergace of check_structure_para_consistent"""
    from aiida_fleur.tools.StructureData_util import adjust_calc_para_to_structure
    from aiida_fleur.tools.StructureData_util import break_symmetry
    from aiida import orm

    structure = generate_structure()

    parameter_data = orm.Dict(dict={
        'atom1': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }
    })
    new_para = adjust_calc_para_to_structure(parameter_data, structure)
    # The parameter data should not be changed
    assert new_para.get_dict() == parameter_data.get_dict()

    structure_broken, parameters1 = break_symmetry(structure, parameterdata=parameter_data)
    new_para = adjust_calc_para_to_structure(parameter_data, structure_broken)
    # The parameter data should be changed and should be the same.
    assert new_para.get_dict() == parameters1.get_dict()


def test_check_structure_para_consistent(generate_structure):
    """Test intergace of check_structure_para_consistent"""
    from aiida_fleur.tools.StructureData_util import check_structure_para_consistent
    from aiida_fleur.tools.StructureData_util import break_symmetry
    from aiida import orm

    structure = generate_structure()

    parameter_data = orm.Dict(dict={
        'atom': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }
    })
    assert check_structure_para_consistent(parameter_data, structure)

    structure_broken, parameters1 = break_symmetry(structure, parameterdata=parameter_data)
    assert check_structure_para_consistent(parameters1, structure_broken)
    assert check_structure_para_consistent(parameter_data, structure_broken)

    wrong_parameter_data = orm.Dict(dict={
        'atom': {
            'element': 'P',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
        }
    })
    assert not check_structure_para_consistent(wrong_parameter_data, structure)


def test_find_equi_atoms(generate_film_structure):
    """Test if find_equi_atoms functions returns equidistant atoms"""
    from aiida_fleur.tools.StructureData_util import find_equi_atoms, supercell_ncf
    from numpy import array

    structure = generate_film_structure()
    structure = supercell_ncf(structure, 2, 2, 1)
    equi_info_symbol, n_equi_info_symbol = find_equi_atoms(structure)

    assert equi_info_symbol[0][0] == 'Fe'
    assert (equi_info_symbol[0][1] == array([0, 1, 6, 7])).all()
    assert equi_info_symbol[1][0] == 'Pt'
    assert (equi_info_symbol[1][1] == array([2, 3, 8, 9])).all()
    assert equi_info_symbol[2][0] == 'Pt'
    assert (equi_info_symbol[2][1] == array([4, 5, 10, 11])).all()

    assert n_equi_info_symbol == {'Fe': 1, 'Pt': 2}


def test_get_spacegroup(generate_film_structure):
    """Test if get_spacegroup function returns the right spacegroup"""
    from aiida_fleur.tools.StructureData_util import get_spacegroup

    structure = generate_film_structure()
    assert get_spacegroup(structure) == 'Pmm2 (25)'


def test_move_atoms_incell_wf(generate_structure):
    """Test if move atoms incell functions moves atoms correctly"""
    from aiida_fleur.tools.StructureData_util import move_atoms_incell_wf
    from aiida.orm import Dict

    structure = generate_structure()

    result = move_atoms_incell_wf(structure, Dict(dict={'vector': [0.1, 0.2, 0.3]}))
    result = result['moved_struc']

    positions_old = [x.position for x in structure.sites]
    positions_shifted = np.array([x.position for x in result.sites])
    for position in positions_old:
        test_pos = np.array(position) + np.array([0.1, 0.2, 0.3])
        assert np.isclose(test_pos, positions_shifted).all(axis=1).any()


def test_find_primitive_cell_wf(generate_structure):
    from aiida_fleur.tools.StructureData_util import find_primitive_cell_wf, supercell_ncf
    from aiida_fleur.tools.StructureData_util import find_primitive_cells

    structure_primitive = generate_structure()
    structure = supercell_ncf(structure_primitive, 2, 2, 22)

    result = find_primitive_cell_wf(structure)
    result = result['primitive_cell']

    assert all(x in structure_primitive.cell for x in result.cell)

    resultlist = find_primitive_cells([structure.uuid, structure.uuid])
    for struc in resultlist:
        assert all(x in structure_primitive.cell for x in result.cell)


def test_center_film_wf(generate_film_structure, generate_structure):
    from aiida_fleur.tools.StructureData_util import center_film_wf, move_atoms_incell, center_film

    structure_film = generate_film_structure()
    structure_bulk = generate_structure()

    structure_film = move_atoms_incell(structure_film, [0.0, 0.0, 1.1242])

    centered_film = center_film_wf(structure_film)
    assert [x.position for x in centered_film.sites] == [(0.0, 0.0, -1.22860131), (1.40263174, 1.98362077, -0.17403051),
                                                         (0.0, 0.0, 1.22860131)]

    with pytest.raises(TypeError):
        center_film(structure_bulk)


def test_get_layers(generate_film_structure):
    from aiida_fleur.tools.StructureData_util import get_layers
    from masci_tools.util.constants import BOHR_A
    structure = generate_film_structure()

    assert get_layers(structure) == ([[([0.0, 0.0, -1.05457080454278], 'Fe')],
                                      [([1.402631738400183, 1.9836207746838, 0.0], 'Pt')],
                                      [([0.0, 0.0, 1.402631823174372], 'Pt')]], [-1.0545708, 0.0,
                                                                                 1.40263182], [1, 1, 1])

    structure.append_atom(position=(1.0, 0., -1.99285 * BOHR_A), symbols='Fe')
    assert get_layers(structure) == ([[([0.0, 0.0, -1.05457080454278], 'Fe'), ([1.0, 0.0, -1.05457080454278], 'Fe')],
                                      [([1.402631738400183, 1.9836207746838, 0.0], 'Pt')],
                                      [([0.0, 0.0, 1.402631823174372], 'Pt')]], [-1.0545708, 0.0,
                                                                                 1.40263182], [2, 1, 1])


create_slab_inputs = [{
    'lattice': 'fcc',
    'miller': None,
    'host_symbol': 'Fe',
    'latticeconstant': 4.0,
    'size': (1, 1, 3),
    'replacements': {
        -1: 'Pt',
        2: 'U'
    },
    'decimals': 10,
    'pop_last_layers': 0
}, {
    'lattice': 'fcc',
    'miller': [[-1, 1, 0], [0, 0, 1], [1, 1, 0]],
    'host_symbol': 'Fe',
    'latticeconstant': 4.0,
    'size': (1, 1, 3),
    'replacements': {
        1: 'Pt'
    },
    'decimals': 10,
    'pop_last_layers': 1
}, {
    'lattice': 'fcc',
    'directions': [[-1, 1, 0], [0, 0, 1], [1, 1, 0]],
    'host_symbol': 'Fe',
    'latticeconstant': 4.0,
    'size': (1, 1, 3),
    'replacements': {
        1: 'Pt'
    },
    'decimals': 10,
    'pop_last_layers': 1
}, {
    'lattice': 'bcc',
    'miller': None,
    'host_symbol': 'Fe',
    'latticeconstant': 4.0,
    'size': (1, 1, 3),
    'replacements': {
        -3: 'Pt'
    },
    'decimals': 10,
    'pop_last_layers': 0
}, {
    'lattice': 'bcc',
    'miller': [[0, 0, 1], [1, 1, 0], [-1, 1, 0]],
    'host_symbol': 'Nb',
    'latticeconstant': 4.0,
    'size': (1, 1, 2),
    'replacements': {
        -1: 'Fe'
    },
    'decimals': 10,
    'pop_last_layers': 0
}]

create_slab_chem_elements = [['Fe', 'Fe', 'U', 'U', 'Fe', 'Fe', 'Fe', 'Fe', 'Fe', 'Fe', 'Pt', 'Pt'],
                             ['Pt', 'Fe', 'Fe', 'Fe', 'Fe'], ['Pt', 'Fe', 'Fe', 'Fe', 'Fe'],
                             ['Fe', 'Fe', 'Fe', 'Pt', 'Fe', 'Fe'], ['Nb', 'Nb', 'Nb', 'Nb', 'Nb', 'Nb', 'Fe', 'Fe']]

create_slab_positions = [
    np.array([[0., 0., 0.], [2., 2., 0.], [2., 0., 2.], [0., 2., 2.], [0., 0., 4.], [2., 2., 4.], [2., 0., 6.],
              [0., 2., 6.], [0., 0., 8.], [2., 2., 8.], [2., 0., 10.], [0., 2., 10.]]),
    np.array([[0.00000000, 0., 0.00000000], [1.41421356, 2., 1.41421356], [-0.0000000, 0., 2.82842712],
              [1.41421356, 2., 4.24264069], [-0.0000000, 0., 5.65685425]]),
    np.array([[0.00000000, 0., 0.00000000], [1.41421356, 2., 1.41421356], [-0.0000000, 0., 2.82842712],
              [1.41421356, 2., 4.24264069], [-0.0000000, 0., 5.65685425]]),
    np.array([[0., 0., 0.], [2., 2., 2.], [0., 0., 4.], [2., 2., 6.], [0., 0., 8.], [2., 2., 10.]]),
    np.array([[0., 0., -0.], [2., 2.82842712, 0], [2., 0, 2.82842712], [0, 2.82842712, 2.82842712], [-0, 0, 5.65685425],
              [2., 2.82842712, 5.65685425], [2., 0, 8.48528137], [-0., 2.82842712, 8.48528137]])
]


@pytest.mark.parametrize('inputs,symbols,positions',
                         zip(create_slab_inputs, create_slab_chem_elements, create_slab_positions))
def test_create_manual_slab_ase(inputs, symbols, positions):
    from aiida_fleur.tools.StructureData_util import create_manual_slab_ase

    structure = create_manual_slab_ase(**inputs)

    assert structure.get_chemical_symbols() == symbols

    assert np.isclose(structure.positions, positions).all()


def test_magnetic_slab_from_relaxed(generate_film_structure):
    from aiida_fleur.tools.StructureData_util import magnetic_slab_from_relaxed, rescale_nowf
    from aiida_fleur.tools.StructureData_util import create_manual_slab_ase
    import math

    inp = {
        'lattice': 'fcc',
        'miller': [[-1, 1, 0], [0, 0, 1], [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,
        'size': (1, 1, 1),
        'decimals': 10,
        'pop_last_layers': 0
    }

    structure2 = create_manual_slab_ase(**inp)

    relaxed_structure = generate_film_structure()

    result = magnetic_slab_from_relaxed(relaxed_structure, structure2, 5, 2)

    names = ['Fe', 'Pt', 'Pt', 'Pt', 'Pt']
    z_positions = [-2.64860575, -1.59403494, -0.17982138, 1.23439218, 2.64860575]
    for site, correct_name, correct_position in zip(result.sites, names, z_positions):
        assert site.kind_name == correct_name
        assert math.isclose(site.position[2], correct_position)


def test_request_average_bond_length(generate_film_structure):
    """Test interface of request average bond length from mp, requires mp_api_key"""
    # Todo mock the mp query, since result could change overtime, also that the CI can run this
    import os
    from aiida_fleur.tools.StructureData_util import request_average_bond_length

    user_api_key = os.getenv('USER_API_KEY')
    if not user_api_key:
        pytest.skip('No USER_API_KEY given, skip the test')

    structure = generate_film_structure()
    result = request_average_bond_length(['Fe', 'Pt'], ['Fe', 'Pt'], user_api_key=user_api_key).get_dict()
    assert result == {
        'Fe': {
            'Fe': 2.4651768430600254,
            'Pt': 2.633878591723135
        },
        'Pt': {
            'Fe': 2.633878591723135,
            'Pt': 2.8120017054377606
        }
    }


def test_adjust_film_relaxation(generate_film_structure):
    """Test interface of adjust film relaxation, requires mp_api_key"""
    # Todo mock the mp query, since result could change overtime, also that the CI can run this
    import os
    from aiida_fleur.tools.StructureData_util import adjust_film_relaxation

    suggestion = {
        'Fe': {
            'Fe': 2.4651768430600254,
            'Pt': 2.633878591723135
        },
        'Pt': {
            'Fe': 2.633878591723135,
            'Pt': 2.8120017054377606
        }
    }

    structure = generate_film_structure()
    result = adjust_film_relaxation(structure, suggestion, last_layer_factor=0.85, first_layer_factor=1.0)

    assert result.sites[0].position[2] == -1.22560291
    assert result.sites[1].position[2] == -0.19045726
    assert result.sites[2].position[2] == 1.22560291

    result = adjust_film_relaxation(structure, suggestion, 'Pt', 2.77)
    assert result.sites[0].position[2] == -1.18751078
    assert result.sites[1].position[2] == 0.05641248
    assert result.sites[2].position[2] == 1.18751078


def test_adjust_sym_film_relaxation(generate_sym_film_structure):
    """Test interface of adjust film relaxation, requires mp_api_key"""
    # Todo mock the mp query, since result could change overtime, also that the CI can run this
    import os
    from aiida_fleur.tools.StructureData_util import adjust_sym_film_relaxation

    suggestion = {
        'Fe': {
            'Fe': 2.4651768430600254,
            'Pt': 2.633878591723135
        },
        'Pt': {
            'Fe': 2.633878591723135,
            'Pt': 2.8120017054377606
        }
    }

    structure = generate_sym_film_structure()
    result = adjust_sym_film_relaxation(structure, suggestion, last_layer_factor=0.85)
    print(result.sites)

    assert result.sites[0].position[2] == -1.04770016
    assert result.sites[1].position[2] == 0.0
    assert result.sites[2].position[2] == 1.04770016

    result = adjust_sym_film_relaxation(structure, suggestion, 'Pt', 2.77)
    assert result.sites[0].position[2] == -1.03205109
    assert result.sites[1].position[2] == 0.0
    assert result.sites[2].position[2] == 1.03205109


def test_has_z_reflection(generate_sym_film_structure, generate_film_structure):
    """Tests has_z_reflection"""
    from aiida_fleur.tools.StructureData_util import has_z_reflection

    structure = generate_film_structure()
    structure_sym = generate_sym_film_structure()

    assert has_z_reflection(structure_sym)
    assert not has_z_reflection(structure)


def test_mark_fixed_atoms(generate_film_structure):
    """Tests has_z_reflection"""
    from aiida_fleur.tools.StructureData_util import mark_fixed_atoms

    structure = generate_film_structure()

    structure_res = mark_fixed_atoms(structure, [1, 3])

    assert structure_res.sites[0].kind_name[-5:] == '49999'
    assert structure_res.sites[2].kind_name[-5:] == '49999'

    structure_res = mark_fixed_atoms(structure, [-1, -2])

    assert structure_res.sites[1].kind_name[-5:] == '49999'
    assert structure_res.sites[2].kind_name[-5:] == '49999'


def test_create_slap(generate_structure):
    """Test if create_slap"""
    from aiida_fleur.tools.StructureData_util import create_slap

    structure = generate_structure()
    film_struc = create_slap(structure, [1, 1, 1], 2)
    cell_should = [[3.839589821842953, 0.0, 2.351070692679364e-16],
                   [1.9197949109214756, 3.3251823258281643, 2.351070692679364e-16], [0.0, 0.0, 9.405035885099004]]
    sites_should = [(0.0, 0.0, 0.0), (1.9197949109214758, 1.1083941086093878, 3.135011961699669),
                    (3.8395898218429525, 2.216788217218776, 6.270023923399337)]
    # since this depends on pymatgen we round here the last digits.
    assert (np.round(film_struc.cell, 8) == np.round(cell_should, 8)).all()
    assert (np.round(film_struc.sites[0].position, 8) == np.round(sites_should[0], 8)).all()
    assert (np.round(film_struc.sites[1].position, 8) == np.round(sites_should[1], 8)).all()
    assert (np.round(film_struc.sites[2].position, 8) == np.round(sites_should[2], 8)).all()


def test_create_all_slabs(generate_structure):
    """Test if create_all_slabs"""
    from aiida_fleur.tools.StructureData_util import create_all_slabs
    from aiida.orm import StructureData

    structure = generate_structure()
    film_strucs = create_all_slabs(structure, 2, 5)

    assert len(film_strucs.keys()) == 9
    assert list(film_strucs.keys()) == [(1, 1, 1), (2, 2, 1), (1, 1, 0), (2, 2, -1), (2, 1, 1), (2, 1, -1), (2, 1, -2),
                                        (2, 0, -1), (2, -1, -1)]
    for key, film_struc in film_strucs.items():
        assert isinstance(film_struc, StructureData)


def test_replace_element(generate_structure):
    from aiida_fleur.tools.StructureData_util import replace_element
    from aiida.orm import Bool, Dict

    structure = generate_structure()

    result = replace_element(structure, Dict(dict={'Si': 'Y'}))

    assert result['replaced_all'].kinds[0].symbols[0] == 'Y'

    result = replace_element(structure, Dict(dict={'Si': 'Y'}), replace_all=Bool(False))

    assert result['replaced_Si_Y_site_0'].kinds[0].symbols[0] == 'Y'
    assert result['replaced_Si_Y_site_0'].kinds[1].symbols[0] == 'Si'
    assert result['replaced_Si_Y_site_1'].kinds[0].symbols[0] == 'Si'
    assert result['replaced_Si_Y_site_1'].kinds[1].symbols[0] == 'Y'


def test_get_atomtype_site_symmetry(generate_structure):
    from aiida_fleur.tools.StructureData_util import get_atomtype_site_symmetry

    structure = generate_structure()
    result = get_atomtype_site_symmetry(structure)

    assert result == ['-43m']
