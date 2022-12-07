"""
Tests of the FleurMagneticStructureData
"""

import pytest

from aiida.orm import load_node
from aiida.common.exceptions import ValidationError

from aiida_fleur.data.magnetic_structure import FleurMagneticStructureData


@pytest.mark.parametrize('magnetic_def',
                         [['up', 'down'], [1, 2.0], [[1, 2, 3], [4.0, 5.0, 6.0]], ['up', [4.0, 5.0, 6.0]]])
def test_valid(magnetic_def):
    """
    Test setting valid magnetic moments
    """

    param = 5.43
    cell = [[0, param / 2., param / 2.], [param / 2., 0, param / 2.], [param / 2., param / 2., 0]]
    structure = FleurMagneticStructureData(cell=cell, magnetic_moments=magnetic_def)
    structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
    structure.append_atom(position=(param / 4., param / 4., param / 4.), symbols='Si', name='Si')

    structure.store()

    assert structure.is_stored

    loaded = load_node(structure.pk)
    assert loaded is not structure
    assert structure.magnetic_moments == magnetic_def


@pytest.mark.parametrize('magnetic_def', [
    ['up', 'notadef'],
    [[1, 2, 3, 4], [4.0, 5.0, 6.0]],
])
def test_invalid(magnetic_def):
    """
    Test setting valid magnetic moments
    """

    param = 5.43
    cell = [[0, param / 2., param / 2.], [param / 2., 0, param / 2.], [param / 2., param / 2., 0]]

    with pytest.raises(ValueError):
        FleurMagneticStructureData(cell=cell, magnetic_moments=magnetic_def)


@pytest.mark.parametrize('magnetic_def', [
    ['up', 'down', 'up'],
    [
        1,
    ],
])
def test_wrong_number_of_moments(magnetic_def):
    """
    Test setting too many or too few magnetic moments
    """

    param = 5.43
    cell = [[0, param / 2., param / 2.], [param / 2., 0, param / 2.], [param / 2., param / 2., 0]]
    structure = FleurMagneticStructureData(cell=cell, magnetic_moments=magnetic_def)
    structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
    structure.append_atom(position=(param / 4., param / 4., param / 4.), symbols='Si', name='Si')

    with pytest.raises(ValidationError):
        structure.store()
