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
''' Contains tests for StructureData util '''
from __future__ import absolute_import
import pytest
import numpy as np


def test_is_structure(generate_structure):
    """Test if is structure can differentiate between structures, identifiers and else"""
    from aiida_fleur.tools.StructureData_util import is_structure
    from aiida.orm import Dict

    dict_test = Dict(dict={})
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

    no_struc = Dict(dict={})
    no_rescaled = rescale_nowf(no_struc, 1.05)
    assert no_rescaled is None


def test_supercell(generate_structure):
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


def test_abs_to_rel(generate_structure):
    from aiida_fleur.tools.StructureData_util import abs_to_rel

    structure = generate_structure()
    cell = structure.cell

    vector = [1.3575, 1.3575, 1.3575]
    assert np.isclose(abs_to_rel(vector, cell), np.array([0.25, 0.25, 0.25])).all()
    assert not abs_to_rel([1], cell)


def test_abs_to_rel_f(generate_film_structure):
    from aiida_fleur.tools.StructureData_util import abs_to_rel_f

    structure = generate_film_structure()
    cell = structure.cell

    vector = [1.4026317387183, 1.9836207751336, 0.25]
    assert np.isclose(abs_to_rel_f(vector, cell, pbc=structure.pbc), np.array([0.5, 0.5, 0.25])).all()
    assert not abs_to_rel_f([1], cell, pbc=structure.pbc)


def test_rel_to_abs(generate_structure):
    """Test if rel_to_abs for bulk function scales coordinates right"""
    from aiida_fleur.tools.StructureData_util import rel_to_abs

    structure = generate_structure()
    cell = structure.cell

    vector = [0.25, 0.25, 0.25]
    assert np.isclose(rel_to_abs(vector, cell), np.array([1.3575, 1.3575, 1.3575])).all()
    assert not rel_to_abs([1], cell)


def test_rel_to_abs_f(generate_film_structure):
    """Test if rel_to_abs film function scales coordinates right"""
    from aiida_fleur.tools.StructureData_util import rel_to_abs_f

    structure = generate_film_structure()
    cell = structure.cell

    vector = [0.5, 0.5, 0.25]
    assert np.isclose(rel_to_abs_f(vector, cell), np.array([1.4026317387183, 1.9836207751336, 0.25])).all()
    assert not rel_to_abs_f([1], cell)


def test_break_symmetry_wf(generate_film_structure):
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

    for kind_name in ['Fe1', 'Fe1', 'Fe1', 'Fe1', 'Pt1', 'Pt2', 'Pt3', 'Pt4', 'Pt5', 'Pt6', 'Pt7', 'Pt8']:
        assert kind_name in kind_names

    # Test if break symmetry adjusts the parameter data right.
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
    parameter_data = Dict(
        dict={
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
        })
    out, parameterdata_new = break_symmetry(structure, parameterdata=parameter_data)
    out_dict = parameterdata_new.get_dict()
    assert out_dict == should_out_dict


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
    assert [x.position for x in centered_film.sites] == [(0.0, 0.0, -1.2286013139),
                                                         (1.4026317384, 1.9836207747, -0.1740305094),
                                                         (0.0, 0.0, 1.2286013138)]

    with pytest.raises(TypeError):
        center_film(structure_bulk)


def test_get_layers(generate_film_structure):
    from aiida_fleur.tools.StructureData_util import get_layers
    from aiida_fleur.common.constants import BOHR_A
    structure = generate_film_structure()

    assert get_layers(structure) == ([[([0.0, 0.0, -1.05457080454278], 'Fe')],
                                      [([1.402631738400183, 1.9836207746838, 0.0], 'Pt')],
                                      [([0.0, 0.0, 1.402631823174372], 'Pt')]], [-1.0545708045, 0.0,
                                                                                 1.4026318232], [1, 1, 1])

    structure.append_atom(position=(1.0, 0., -1.99285 * BOHR_A), symbols='Fe')
    assert get_layers(structure) == ([[([0.0, 0.0, -1.05457080454278], 'Fe'), ([1.0, 0.0, -1.05457080454278], 'Fe')],
                                      [([1.402631738400183, 1.9836207746838, 0.0], 'Pt')],
                                      [([0.0, 0.0, 1.402631823174372], 'Pt')]], [-1.0545708045, 0.0,
                                                                                 1.4026318232], [2, 1, 1])


create_slab_inputs = [{
    'lattice': 'fcc',
    'miller': None,
    'host_symbol': 'Fe',
    'latticeconstant': 4.0,
    'size': (1, 1, 3),
    'replacements': {
        -1: 'Pt',
        1: 'U'
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
        0: 'Pt'
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
                             ['Pt', 'Fe', 'Fe', 'Fe', 'Fe'], ['Fe', 'Fe', 'Fe', 'Pt', 'Fe', 'Fe'],
                             ['Nb', 'Nb', 'Nb', 'Nb', 'Nb', 'Nb', 'Fe', 'Fe']]

create_slab_positions = [
    np.array([[0., 0., 0.], [2., 2., 0.], [2., 0., 2.], [0., 2., 2.], [0., 0., 4.], [2., 2., 4.], [2., 0., 6.],
              [0., 2., 6.], [0., 0., 8.], [2., 2., 8.], [2., 0., 10.], [0., 2., 10.]]),
    np.array([[0.00000000, 0., 0.00000000], [1.41421356, 2., 1.41421356], [-0.0000000, 0., 2.82842712],
              [1.41421356, 2., 4.24264069], [-0.0000000, 0., 5.65685425]]),
    np.array([[0., 0., 0.], [2., 2., 2.], [0., 0., 4.], [2., 2., 6.], [0., 0., 8.], [2., 2., 10.]]),
    np.array([[2., 2.82842712, 0], [0., 0., -0.], [2., 0, 2.82842712], [0, 2.82842712, 2.82842712], [-0, 0, 5.65685425],
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
    z_positions = [-2.648605745990961, -1.5940349412090389, -0.1798213788090388, 1.2343921835909613, 2.648605745990961]
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

    user_api_key = os.getenv('USER_API_KEY')
    if not user_api_key:
        pytest.skip('No USER_API_KEY given, skip the test')

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
    result = adjust_film_relaxation(structure, suggestion, hold_layers=0)
    print(structure.sites)
    print(result.sites)
    assert result.sites[0].position[2] == -1.1957065898
    assert result.sites[1].position[2] == 0.1782640794
    assert result.sites[2].position[2] == 1.1957065898

    result = adjust_film_relaxation(structure, suggestion, 'Pt', 2.77)
    assert result.sites[0].position[2] == -1.1709859694
    assert result.sites[1].position[2] == 0.2602185234
    assert result.sites[2].position[2] == 1.1709859694


def test_create_slap(generate_structure):
    """Test if create_slap"""
    from aiida_fleur.tools.StructureData_util import create_slap

    structure = generate_structure()
    film_struc = create_slap(structure, [1, 1, 1], 2)
    cell_should = [[3.839589821842953, 0.0, 2.351070692679364e-16],
                   [1.9197949109214756, 3.3251823258281643, 2.351070692679364e-16], [0.0, 0.0, 9.405035885099004]]
    sites_should = [(3.839589821842953, 2.216788217218776, 3.135011961699669), (0.0, 0.0, 0.0),
                    (1.9197949109214758, 1.1083941086093878, 6.270023923399337)]

    assert film_struc.cell == cell_should
    assert film_struc.sites[0].position == sites_should[0]
    assert film_struc.sites[1].position == sites_should[1]
    assert film_struc.sites[2].position == sites_should[2]


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
