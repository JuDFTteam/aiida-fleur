# -*- coding: utf-8 -*-
"""
Here we specify some defaults for cli commands
"""

# Structures


def get_si_bulk_structure():
    """Return a `StructureData` representing bulk silicon.

    The database will first be queried for the existence of a bulk silicon crystal. If this is not the case, one is
    created and stored. This function should be used as a default for CLI options that require a `StructureData` node.
    This way new users can launch the command without having to construct or import a structure first. This is the
    reason that we hardcode a bulk silicon crystal to be returned. More flexibility is not required for this purpose.

    :return: a `StructureData` representing bulk silicon
    """
    from ase.spacegroup import crystal
    from aiida.orm import QueryBuilder, StructureData

    # Filters that will match any elemental Silicon structure with 2 or less sites in total
    filters = {
        'attributes.sites': {
            'of_length': 2
        },
        'attributes.kinds': {
            'of_length': 1
        },
        'attributes.kinds.0.symbols.0': 'Si'
    }

    builder = QueryBuilder().append(StructureData, filters=filters)
    results = builder.first()

    if not results:
        alat = 5.43
        ase_structure = crystal(
            'Si',
            [(0, 0, 0)],
            spacegroup=227,
            cellpar=[alat, alat, alat, 90, 90, 90],
            primitive_cell=True,
        )
        structure = StructureData(ase=ase_structure)
        structure.store()
    else:
        structure = results[0]

    return structure.uuid


def get_fept_film_structure():
    """Return a `StructureData` representing FePt film.

    The database will first be queried for the existence of a FePt film. If this is not the case, one is
    created and stored. This function should be used as a default for CLI options that require a `StructureData` node.
    This way new users can launch the command without having to construct or import a structure first. This is the
    reason that we hardcode a FePt film to be returned. More flexibility is not required for this purpose.

    :return: the uuid of  `StructureData` representing a FePt film
    """
    from aiida.orm import StructureData, QueryBuilder

    bohr_a_0 = 0.52917721092  # A
    a = 7.497 * bohr_a_0
    cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
    structure = StructureData(cell=cell)
    structure.append_atom(position=(0.0, 0.0, -1.99285 * bohr_a_0), symbols='Fe', name='Fe123')
    structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
    structure.append_atom(position=(0., 0., 2.65059 * bohr_a_0), symbols='Pt')
    structure.pbc = (True, True, False)

    builder = QueryBuilder().append(StructureData, filters={'extras._aiida_hash': structure._get_hash()})
    results = builder.first()

    if not results:
        structure.store()
    else:
        structure = results[0]

    return structure.uuid


# Codes
def get_inpgen():
    """Return a `Code` node of the latest added inpgen executable in the database."""

    return get_last_code('fleur.inpgen')


def get_fleur():
    """Return a `Code` node of the latest added inpgen executable in the database."""

    return get_last_code('fleur.fleur')


def get_last_code(entry_point_name):
    """Return a `Code` node of the latest code executable of the given entry_point_name in the database.

    The database will be queried for the existence of a inpgen node.
    If this is not exists and NotExistent error is raised.


    :param entry_point_name: string
    :return: the uuid of a inpgen `Code` node
    :raise: aiida.common.exceptions.NotExistent
    """
    from aiida.orm import QueryBuilder, Code
    from aiida.common.exceptions import NotExistent

    filters = {'attributes.input_plugin': {'==': entry_point_name}}

    builder = QueryBuilder().append(Code, filters=filters)
    builder.order_by({Code: {'ctime': 'asc'}})
    results = builder.first()

    if not results:
        raise NotExistent(f'ERROR: Could not find any Code in the database with entry point: {entry_point_name}!')
    else:
        inpgen = results[0]

    return inpgen.uuid
