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
Collection of utility routines dealing with StructureData objects
"""
# TODO move imports to workfuncitons namespace?
# TODO: MPrester has a new backwards incompatible version in pymatgen
#       Migrate and solve pylint warning deactivated below
#pylint: disable=not-context-manager

# from ase import *
# from ase.lattice.surface import *
# from ase.io import *

import warnings
from pymatgen.core.surface import generate_all_slabs  #, get_symmetrically_distinct_miller_indices
from pymatgen.core.surface import SlabGenerator

import numpy as np

from aiida.plugins import DataFactory
from aiida.orm import load_node, Bool
from aiida.orm.nodes.data.structure import Site, Kind
from aiida.engine.processes.functions import calcfunction as cf


def is_structure(structure):
    """
    Test if the given input is a StructureData node, by object, id, or pk
    :param structure: AiiDA StructureData
    :return: if yes returns a StructureData node in all cases, if no returns None
    """
    from aiida.common import NotExistent

    StructureData = DataFactory('core.structure')

    # Test if StructureData
    if isinstance(structure, StructureData):
        return structure

    try:
        structure = load_node(structure)
        if isinstance(structure, StructureData):
            return structure
        return None
    except NotExistent:
        return None


def is_primitive(structure):
    """
    Checks if a structure is primitive or not,
    :param structure: AiiDA StructureData
    :return: True if the structure can not be anymore refined.
    prints False if the structure can be futher refined.
    """
    refined_cell = find_primitive_cell(structure)

    prim = False
    if all(x in structure.cell for x in refined_cell.cell):
        prim = True
    return prim


@cf
def rescale(inp_structure, scale):
    """
    Rescales a crystal structures Volume, atoms stay at their same relative postions,
    therefore the absolute postions change.
    Keeps the provenance in the database.

    :param inp_structure: a StructureData node (pk, or uuid)
    :param scale: float scaling factor for the cell

    :return: New StructureData node with rescalled structure, which is linked to input Structure
              and None if inp_structure was not a StructureData
    """

    return rescale_nowf(inp_structure, scale)


def rescale_nowf(inp_structure, scale):
    """
    Rescales a crystal structures Volume, atoms stay at their same relative postions,
    therefore the absolute postions change.
    DOES NOT keep the provenance in the database.

    :param inp_structure: a StructureData node (pk, or uuid)
    :param scale: float scaling factor for the cell

    :return: New StructureData node with rescalled structure, which is linked to input Structure
              and None if inp_structure was not a StructureData
    """

    # test if structure:
    structure = is_structure(inp_structure)
    if not structure:
        # TODO: log something
        return None

    the_ase = structure.get_ase()
    new_ase = the_ase.copy()
    new_ase.set_cell(the_ase.get_cell() * np.power(float(scale), 1.0 / 3), scale_atoms=True)
    rescaled_structure = DataFactory('core.structure')(ase=new_ase)
    rescaled_structure.label = f'{scale}  rescaled'  #, structure.uuid)
    #uuids in node labels are bad for caching
    rescaled_structure.pbc = structure.pbc

    return rescaled_structure


@cf
def supercell(inp_structure, n_a1, n_a2, n_a3):
    """
    Creates a super cell from a StructureData node.
    Keeps the provenance in the database.

    :param StructureData: a StructureData node (pk, or uuid)
    :param scale: tuple of 3 AiiDA integers, number of cells in a1, a2, a3,
                  or if cart =True in x,y,z

    :return: StructureData Node with supercell
    """
    superc = supercell_ncf(inp_structure, n_a1, n_a2, n_a3)

    formula = inp_structure.get_formula()
    return superc


def supercell_ncf(inp_structure, n_a1, n_a2, n_a3):
    """
    Creates a super cell from a StructureData node.
    Does NOT keeps the provenance in the database.

    :param StructureData: a StructureData node (pk, or uuid)
    :param scale: tuple of 3 AiiDA integers, number of cells in a1, a2, a3, or if cart=True in x,y,z

    :return: StructureData Node with supercell
    """
    # print('in create supercell')
    # test if structure:
    structure = is_structure(inp_structure)
    if not structure:
        # TODO: log something
        return None
    old_cell = structure.cell
    old_a1 = old_cell[0]
    old_a2 = old_cell[1]
    old_a3 = old_cell[2]
    old_sites = structure.sites
    old_pbc = structure.pbc

    na1 = int(n_a1)
    na2 = int(n_a2)
    na3 = int(n_a3)

    # new cell
    new_a1 = [i * na1 for i in old_a1]
    new_a2 = [i * na2 for i in old_a2]
    new_a3 = [i * na3 for i in old_a3]
    new_cell = [new_a1, new_a2, new_a3]
    new_structure = DataFactory('core.structure')(cell=new_cell, pbc=old_pbc)

    # insert atoms
    # first create all kinds
    old_kinds = structure.kinds
    for kind in old_kinds:
        new_structure.append_kind(kind)

    # scale n_a1
    for site in old_sites:
        # get atom position
        kn = site.kind_name
        pos_o = site.position
        for j in range(na1):
            pos = [pos_o[i] + j * old_a1[i] for i in range(0, len(old_a1))]
            new_structure.append_site(Site(kind_name=kn, position=pos))

    # scale n_a2
    o_sites = new_structure.sites
    for site in o_sites:
        # get atom position
        kn = site.kind_name
        pos_o = site.position
        for j in range(1, na2):  # j=0 these sites/atoms are already added
            pos = [pos_o[i] + j * old_a2[i] for i in range(0, len(old_a2))]
            new_structure.append_site(Site(kind_name=kn, position=pos))

    # scale n_a3
    o_sites = new_structure.sites
    for site in o_sites:
        # get atom position
        kn = site.kind_name
        pos_o = site.position
        for j in range(1, na3):  # these sites/atoms are already added
            pos = [pos_o[i] + j * old_a3[i] for i in range(0, len(old_a3))]
            new_structure.append_site(Site(kind_name=kn, position=pos))

    formula = inp_structure.get_formula()
    new_structure.label = f'supercell of {formula}'
    new_structure.description = f'{n_a1}x{n_a2}x{n_a3} supercell of {formula}'
    return new_structure


# Structure util
# after ths is in plugin code import these in fleurinp.


@cf
def break_symmetry_wf(structure, wf_para, parameterdata=None):
    """
    This is the calcfunction of the routine break_symmetry, which
    introduces different 'kind objects' in a structure
    and names them that inpgen will make different species/atomgroups out of them.
    If nothing specified breaks ALL symmetry (i.e. every atom gets their own kind)

    :param structure: StructureData
    :param wf_para: ParameterData which contains the keys atoms, sites, pos (see below)

                     'atoms':
                            python list of symbols, exp: ['W', 'Be']. This would make for
                            all Be and W atoms their own kinds.

                     'site':
                           python list of integers, exp: [1, 4, 8]. This would create for
                           atom 1, 4 and 8 their own kinds.

                     'pos':
                          python list of tuples of 3, exp [(0.0, 0.0, -1.837927), ...].
                          This will create a new kind for the atom at that position.
                          Be carefull the number given has to match EXACTLY the position
                          in the structure.

    :param parameterdata: AiiDa ParameterData
    :return: StructureData, a AiiDA crystal structure with new kind specification.
    """
    Dict = DataFactory('core.dict')
    if parameterdata is None:
        parameterdata = Dict({})
    wf_dict = wf_para.get_dict()
    atoms = wf_dict.get('atoms', ['all'])
    sites = wf_dict.get('site', [])
    pos = wf_dict.get('pos', [])
    new_kinds_names = wf_dict.get('new_kinds_names', {})
    new_structure, para_new = break_symmetry(structure,
                                             atoms=atoms,
                                             site=sites,
                                             pos=pos,
                                             new_kinds_names=new_kinds_names,
                                             parameterdata=parameterdata)

    return {'new_structure': new_structure, 'new_parameters': para_new}


def break_symmetry(structure,
                   atoms=None,
                   site=None,
                   pos=None,
                   new_kinds_names=None,
                   add_atom_base_lists=True,
                   parameterdata=None):
    """
    This routine introduces different 'kind objects' in a structure
    and names them that inpgen will make different species/atomgroups out of them.
    If nothing specified breaks ALL symmetry (i.e. every atom gets their own kind)

    :param structure: StructureData
    :param atoms: python list of symbols, exp: ['W', 'Be']. This would make for
                all Be and W atoms their own kinds.
    :param site: python list of integers, exp: [1, 4, 8]. This would create for
                atom 1, 4 and 8 their own kinds.
    :param pos: python list of tuples of 3, exp [(0.0, 0.0, -1.837927), ...].
                This will create a new kind for the atom at that position.
                Be carefull the number given has to match EXACTLY the position
                in the structure.
    :param parameterdata: Dict node, containing calculation_parameters, however,
                this only works well if you prepare already a node for containing
                the atom lists from the symmetry breaking, or lists without ids.
    :param add_atom_base_lists: Bool (default True), if the atom base lists should be added or not
    :return: StructureData, a AiiDA crystal structure with new kind specification.
    :return: DictData, a AiiDA dict with new parameters for inpgen.
    """
    if atoms is None:
        atoms = ['all']

    if site is None:
        site = []

    if pos is None:
        pos = []

    if new_kinds_names is None:
        new_kinds_names = {}
        write_new_kind_names = False
    else:
        write_new_kind_names = True
    from aiida.common.constants import elements as PeriodicTableElements
    from aiida.orm import Dict

    _atomic_numbers = {data['symbol']: num for num, data in PeriodicTableElements.items()}

    # get all atoms, get the symbol of the atom
    # if wanted make individual kind for that atom
    # kind names will be atomsymbol+number
    # create new structure with new kinds and atoms
    symbol_count = {}  # Counts the atom symbol occurrence to set id's and kind names right
    replace = []  # all atoms symbols ('W') to be replaced
    replace_siteN = []  # all site integers to be replaced
    replace_pos = []  # all the atom positions to be replaced
    para_new = None
    kind_name_id_mapping = {}

    struc = is_structure(structure)
    if not struc:
        print('Error, no structure given')
        # throw error?
        return None, None

    cell = struc.cell
    pbc = struc.pbc
    sites = struc.sites
    new_structure = DataFactory('core.structure')(cell=cell, pbc=pbc)

    for sym in atoms:
        replace.append(sym)
    for position in pos:
        replace_pos.append(position)
    for atom in site:
        replace_siteN.append(atom)

    for i, site_c in enumerate(sites):
        # get site info
        kind_name = site_c.kind_name
        pos = site_c.position
        kind = struc.get_kind(kind_name)
        symbol = kind.symbol
        replace_kind = False

        # check if kind to replace is in inputs
        if symbol in replace or 'all' in replace:
            replace_kind = True
        if pos in replace_pos:
            replace_kind = True
        if i in replace_siteN:
            replace_kind = True

        if replace_kind:
            symbol_count[symbol] = symbol_count.get(symbol, 0) + 1
            symbol_new_kinds_names = new_kinds_names.get(symbol, [])
            if symbol_new_kinds_names and ((len(symbol_new_kinds_names)) == symbol_count[symbol]):
                newkindname = symbol_new_kinds_names[symbol_count[symbol] - 1]
                kind_name_id_mapping[newkindname] = symbol_count[symbol] - 1
            else:
                newkindname = f'{symbol}{symbol_count[symbol]}'
                kind_name_id_mapping[newkindname] = symbol_count[symbol]
            new_kind = Kind(name=newkindname, symbols=symbol)
            new_structure.append_kind(new_kind)

        else:
            newkindname = kind_name
            if not kind_name in new_structure.get_kind_names():
                new_structure.append_kind(kind)
        new_structure.append_site(Site(kind_name=newkindname, position=pos))

    # update parameter data
    if parameterdata is not None:
        # TODO This may not enough, since for magnetic systems one need a kind mapping
        # i.e if the parameters are for a partly 'pre symmetry broken system'
        # and we want to keep track from which 'old' kind which new kind spawn
        para_new = adjust_calc_para_to_structure(parameterdata,
                                                 new_structure,
                                                 add_atom_base_lists=add_atom_base_lists,
                                                 write_new_kind_names=write_new_kind_names)

    new_structure.label = structure.label
    new_structure.description = structure.description + 'more kinds, less sym'

    return new_structure, para_new


def adjust_calc_para_to_structure(parameter, structure, add_atom_base_lists=True, write_new_kind_names=False):
    """
    Adjust calculation parameters for inpgen to a given structure with several kinds

    Rules:
    1. Only atom lists are changed in the parameter node
    2. If at least one atomlist of a certain element is in parameter
    all kinds with this elements will have atomlists in the end
    3. For a certain kind which has no atom list yet and at least one list with such an element
    exists it gets the parameters from the atom list with the lowest number (while atom<atom0<atom1)
    4. Atom lists with ids are preserved

    :param parameter: aiida.orm.Dict node containing calc parameters
    :param structure: aiida.orm.StructureData node containing a crystal structure
    :param add_atom_base_lists: Bool (default True), if the atom base lists should be added or not
    :return: new aiida.orm.Dict with new calc_parameters
    """
    from aiida.common.constants import elements as PeriodicTableElements
    from aiida import orm
    atomic_numbers = {data['symbol']: num for num, data in PeriodicTableElements.items()}

    param_new_dict = {}
    para_dict = parameter.get_dict()
    atom_lists = []
    j = 1
    for key in sorted(para_dict):
        val = para_dict[key]
        if 'atom' in key:
            atom_lists.append(val)
            if add_atom_base_lists:
                if not 'id' in val:
                    atomlistname = f'atom{j}'
                    param_new_dict[atomlistname] = val
                    j = j + 1
        else:
            param_new_dict[key] = val

    for i, kind in enumerate(structure.kinds):
        symbol = kind.symbol
        atomic_number = atomic_numbers.get(symbol)
        kind_name = kind.name
        try:
            # Kind names can be more then numbers now, this might need to be reworked
            # Every string without a number excepts and will be ignored/assumed covered by base lists
            head = kind_name.rstrip('0123456789')
            kind_namet = int(kind_name[len(head):])
        except ValueError:
            # base lists are already added
            kind_namet = None
            should_id = None
            continue

        should_id = f'{atomic_number}.{kind_namet}'
        # check if atom list with id was given if yes use that one
        found_kind = False
        for atomlst in atom_lists:
            if atomlst.get('id', None) == should_id:
                #if atomlst.get('element', None) != symbol or atomlst.get('z', None) != atomic_number:
                #    continue # None id, but wrong element
                atomlistname = f'atom{j}'
                param_new_dict[atomlistname] = atomlst
                j = j + 1
                found_kind = True

        if found_kind:
            continue

        # we have to create a new list with right id
        # get first list which has element or charge in given list
        for atomlst in atom_lists:
            if atomlst.get('element', None) == symbol or atomlst.get('z', None) == atomic_number:
                new_alst = atomlst.copy()
                new_alst['id'] = should_id
                if write_new_kind_names:
                    new_alst['name'] = kind_name
                atomlistname = f'atom{j}'
                param_new_dict[atomlistname] = new_alst
                j = j + 1

    return orm.Dict(dict=param_new_dict)


def check_structure_para_consistent(parameter, structure, verbose=True):
    """
    Check if the given calculation parameters for inpgen match to a given structure

    If parameter contains atom lists which do not fit to any kind in the structure,
    false is returned
    This knows how the FleurinputgenCalculation prepares structures.

    :param parameter: aiida.orm.Dict node containing calc parameters
    :param structure: aiida.orm.StructureData node containing a crystal structure

    :return: Boolean, True if parameter is consistent to structure
    """
    from aiida.common.constants import elements as PeriodicTableElements
    atomic_numbers = {data['symbol']: num for num, data in PeriodicTableElements.items()}

    consistent = True
    para_dict = parameter.get_dict()
    kinds = structure.kinds
    kind_symbols = [kind.symbol for kind in kinds]
    kind_charges = [atomic_numbers[kind.symbol] for kind in kinds]
    kind_names = [kind.name for kind in kinds]
    possible_ids = []
    for i, kind_name in enumerate(kind_names):
        try:
            # Kind names can be more then numbers now, this might need to be reworked
            head = kind_name.rstrip('0123456789')
            kind_namet = int(kind_name[len(head):])
        except ValueError:
            pass
            #print('Warning: Kind name {} will be ignored by a FleurinputgenCalculation and not set a charge number. id'.
            #      format(kind_name))
        else:
            atomic_number_name = f'{kind_charges[i]}.{kind_namet}'
            possible_ids.append(atomic_number_name)
        # Id can also be integer number only?

    # Now perform the consitency check
    for key, val in para_dict.items():
        if 'atom' in key:
            if 'z' in val:
                if val['z'] not in kind_charges:
                    consistent = False
                    if not verbose:
                        print(f'Charge z in atomlist {key} is not consistent with structure.')
            if 'element' in val:
                if val['element'] not in kind_symbols:
                    consistent = False
                    if not verbose:
                        print(f'Element in atomlist {key} is not consistent with structure.')
            if 'id' in val:
                if str(val['id']) not in possible_ids:
                    consistent = False
                    if not verbose:
                        print(f'Id in atomlist {key} is not consistent with kinds in structure.')

    return consistent


'''
# TODO: Bug: parameter data production not right...to many atoms list if break sym of everything
def break_symmetry(structure, atoms=None, site=None, pos=None, new_kinds_names=None, add_atom_base_lists=False, parameterdata=None):
    """
    This routine introduces different 'kind objects' in a structure
    and names them that inpgen will make different species/atomgroups out of them.
    If nothing specified breaks ALL symmetry (i.e. every atom gets their own kind)

    :param structure: StructureData
    :param atoms: python list of symbols, exp: ['W', 'Be']. This would make for
                   all Be and W atoms their own kinds.
    :param site: python list of integers, exp: [1, 4, 8]. This would create for
                  atom 1, 4 and 8 their own kinds.
    :param pos: python list of tuples of 3, exp [(0.0, 0.0, -1.837927), ...].
                 This will create a new kind for the atom at that position.
                 Be carefull the number given has to match EXACTLY the position
                 in the structure.
    :param parameterdata: Dict node, containing calculation_parameters, however, this only works well
    if you prepare already a node for containing the atom lists from the symmetry breaking,
    or lists without ids.
    :return: StructureData, a AiiDA crystal structure with new kind specification.
    :return: DictData, a AiiDA dict with new parameters for inpgen.
    """
    if atoms is None:
        atoms = ['all']

    if site is None:
        site = []

    if pos is None:
        pos = []

    if new_kinds_names is None:
        new_kinds_names = {}

    from aiida.common.constants import elements as PeriodicTableElements
    from aiida.orm import Dict

    _atomic_numbers = {data['symbol']: num for num, data in PeriodicTableElements.items()}

    # get all atoms, get the symbol of the atom
    # if wanted make individual kind for that atom
    # kind names will be atomsymbol+number
    # create new structure with new kinds and atoms
    # Param = DataFactory('dict')
    symbol_count = {}  # Counts the atom symbol occurrence to set id's and kind names right
    replace = []  # all atoms symbols ('W') to be replaced
    replace_siteN = []  # all site integers to be replaced
    replace_pos = []  # all the atom positions to be replaced
    new_parameterd = None
    kind_name_id_mapping = {}

    struc = is_structure(structure)
    if not struc:
        print('Error, no structure given')
        # throw error?

    cell = struc.cell
    pbc = struc.pbc
    sites = struc.sites
    # natoms = len(sites)
    new_structure = DataFactory('structure')(cell=cell, pbc=pbc)

    for sym in atoms:
        replace.append(sym)
    for position in pos:
        replace_pos.append(position)
    for atom in site:
        replace_siteN.append(atom)

    for i, site_c in enumerate(sites):
        # get site info
        kind_name = site_c.kind_name
        pos = site_c.position
        kind = struc.get_kind(kind_name)
        symbol = kind.symbol
        replace_kind = False

        # check if kind to replace is in inputs
        if symbol in replace or 'all' in replace:
            replace_kind = True
        if pos in replace_pos:
            replace_kind = True
        if i in replace_siteN:
            replace_kind = True

        if replace_kind:
            symbol_count[symbol] = symbol_count.get(symbol, 0) + 1
            symbol_new_kinds_names = new_kinds_names.get(symbol, [])
            if symbol_new_kinds_names and ((len(symbol_new_kinds_names)) == symbol_count[symbol]):
                newkindname = symbol_new_kinds_names[symbol_count[symbol] - 1]
                kind_name_id_mapping[newkindname] = symbol_count[symbol]-1
            else:
                newkindname = '{}{}'.format(symbol, symbol_count[symbol])
                kind_name_id_mapping[newkindname] = symbol_count[symbol]
            new_kind = Kind(name=newkindname, symbols=symbol)
            new_structure.append_kind(new_kind)

        else:
            newkindname = kind_name
            if not kind_name in new_structure.get_kind_names():
                new_structure.append_kind(kind)
        new_structure.append_site(Site(kind_name=newkindname, position=pos))

    # now we have to add an atom list to parameterdata with the corresponding id.
    # generate possible IDs
    #symbol_count_added = {symbol: 0 for symbol in symbol_count.keys()}
    symbol_possible_ids = {}
    for key, val in symbol_count.items():
        symbol_possible_ids[key] = [i+1 for i in range(val)]
    new_parameterd = {}
    if parameterdata:
        para = parameterdata.get_dict()
'''
'''
        for i, kind in enumerate(new_structure.kinds):
            # for each kind in structure add an individual atom list to parameterdata with id
            # as long as there was some predefined atom list for such an element
            # use the first one you find as base for all new
            # if there is an atom list with such an id use that one
            atomlistname = 'atom{}'.format(i)
            symbol = kind.symbol
            kind_found = False
            for key in sorted(para):
                val = para[key]
                if 'atom' in key:
                    # ignore atom lists elements not to break sym for.
                    # we also only use the first one we find.
                    # therefore best to give only one atom list per element
                    if val.get('element', None) != symbol:
                        if val.get('z', None) != _atomic_numbers.get(symbol):
                            continue
                    # we have a list of a kind we did something for
                    el_id = str(val.get('id', '0.0'))
                    # 0.0 because if case where id is no specified
                    # cast str since sometimes people might give as float
                    # id has the form Int.Int
                    el_id = int(el_id.split('.')[1])
                    ids = symbol_possible_ids.get(symbol)
                    if el_id in ids: #id_a == el_id and el_id > 0:
                        new_parameterd[atomlistname] = val
                        ids.remove(el_id)
                        symbol_possible_ids[symbol] = ids
                        kind_found = True
                        break  # we assume the user is smart and provides a para node,
                        # which incorporates the symmetry breaking already
                        # but we need to see all atom lists to know if it is there...
            if kind_found:
                continue
            for key in sorted(para):
                val = para[key]
                if 'atom' in key:
                    if val.get('element', None) != symbol:
                        if val.get('z', None) != _atomic_numbers.get(symbol):
                            continue
                    el_id = str(val.get('id', '0.0'))
                    el_id = int(el_id.split('.')[1])
                    ids = symbol_possible_ids.get(symbol)
                    # copy parameter of symbol and add id
                    # this would be the lowest predefined atom list of an element
                    val_new = {}
                    val_new.update(val)
                    charge = _atomic_numbers.get((val.get('element', None)))
                    if charge is None:
                        charge = val.get('z', None)
                    idp = '{}.{}'.format(charge, ids[0])
                    ids.remove(el_id)
                    idp = float('{0:.2f}'.format(float(idp)))
                    # dot cannot be stored in AiiDA dict...
                    val_new.update({u'id': idp})
                    atomlistname = 'atom{}'.format(i)#id_a)
                    # Since there are other atoms list also find the next
                    # free atom key.
                    #j = 0
                    #while new_parameterd.get(atomlistname, {}):
                    #    j = j + 1
                    #    atomlistname = 'atom{}'.format(id_a + i)
                    #symbol_new_kinds_names = new_kinds_names.get(symbol, [])
                    # print(symbol_new_kinds_names)
                    #if symbol_new_kinds_names and ((len(symbol_new_kinds_names)) == symbol_count[symbol]):
                    #    species_name = symbol_new_kinds_names[symbol_count[symbol] - 1]
                    #    val_new.update({u'name': species_name})
                    new_parameterd[atomlistname] = val_new
                    break # max one new atom list per kind
'''
'''
        # add other non atom keys from original parameterdata
        for key, val in para.items():
            if 'atom' not in key:
                new_parameterd[key] = val
            elif add_atom_base_lists:
                if not 'id' in val:
                    new_parameterd[key] = val
        para_new = Dict(dict=new_parameterd)
    else:
        para_new = None

    print(new_parameterd)
    new_structure.label = structure.label
    new_structure.description = structure.description + 'more kinds, less sym'

    return new_structure, para_new
'''


def find_equi_atoms(structure):  # , sitenumber=0, position=None):
    """
    This routine uses spglib and ASE to provide informations of all equivivalent
    atoms in the cell.

    :param structure: AiiDA StructureData

    :return: equi_info_symbol, list of lists ['element': site_indexlist, ...]
        len(equi_info_symbol) = number of symmetryatomtypes
        and n_equi_info_symbol, dict {'element': numberequiatomstypes}
    """
    import spglib

    equi_info = []
    equi_info_symbol = []
    n_equi_info_symbol = {}
    k_symbols = {}

    s_ase = structure.get_ase()

    lattice = s_ase.get_cell()
    positions = s_ase.get_scaled_positions()
    numbers = s_ase.get_atomic_numbers()

    sym = spglib.get_symmetry((lattice, positions, numbers), symprec=1e-5)
    equi = sym['equivalent_atoms']
    unique = np.unique(equi)

    for uni in unique:
        equi_info.append(np.where(equi == uni)[0])

    sites = structure.sites
    kinds = structure.kinds

    for kind in kinds:
        k_symbols[kind.name] = kind.symbol

    for equi in equi_info:
        kind = sites[equi[0]].kind_name
        element = k_symbols[kind]
        n_equi_info_symbol[element] = n_equi_info_symbol.get(element, 0) + 1
        equi_info_symbol.append([element, equi])

    return equi_info_symbol, n_equi_info_symbol


def get_spacegroup(structure):
    """
    :param structure: AiiDA StructureData
    :return: the spacegroup (spglib class) of a given AiiDA structure
    """
    import spglib
    s_ase = structure.get_ase()
    lattice = s_ase.get_cell()
    positions = s_ase.get_scaled_positions()
    numbers = s_ase.get_atomic_numbers()
    spacegroup = spglib.get_spacegroup((lattice, positions, numbers), symprec=1e-5)
    return spacegroup


@cf
# , _label='move_atoms_in_unitcell_wf', _description='WF, that moves all atoms in a unit cell by a given vector'):#Float1, Float2, Float3, test=None):
def move_atoms_incell_wf(structure, wf_para):
    """
    moves all atoms in a unit cell by a given vector

    :param structure: AiiDA structure
    :param wf_para: AiiDA Dict node with vector: tuple of 3, or array
        (currently 3 AiiDA Floats to make it a wf,
        In the future maybe a list or vector if AiiDa basetype exists)
    :return: AiiDA stucture
    """
    wf_para_dict = wf_para.get_dict()
    vector = wf_para_dict.get('vector', [0.0, 0.0, 0.0])
    # [Float1, Float2, Float3])
    new_structure = move_atoms_incell(structure, vector)

    return {'moved_struc': new_structure}


def move_atoms_incell(structure, vector):
    """
    moves all atoms in a unit cell by a given vector

    :param structure: AiiDA structure
    :param vector: tuple of 3, or array
    :return: AiiDA structure
    """

    StructureData = DataFactory('core.structure')
    new_structure = StructureData(cell=structure.cell)
    new_structure.pbc = structure.pbc
    sites = structure.sites
    for kind in structure.kinds:
        new_structure.append_kind(kind)

    for site in sites:
        pos = site.position
        new_pos = np.around(np.array(pos) + np.array(vector), decimals=8)
        new_site = Site(kind_name=site.kind_name, position=new_pos)
        new_structure.append_site(new_site)
        new_structure.label = structure.label

    new_structure.label = structure.label
    new_structure.description = structure.description + 'moved'
    return new_structure


def find_primitive_cell(structure):
    """
    uses spglib find_primitive to find the primitive cell

    :param sructure: AiiDA structure data
    :return: list of new AiiDA structure data
    """
    # TODO: if refinced structure is the same as given structure
    # return the given structure (Is this good practise for prov?)
    from spglib import find_primitive
    from ase.atoms import Atoms
    StructureData = DataFactory('core.structure')

    symprec = 1e-7
    # print('old {}'.format(len(structure.sites)))
    ase_structure = structure.get_ase()
    lattice = ase_structure.get_cell()
    positions = ase_structure.get_scaled_positions()
    numbers = ase_structure.get_atomic_numbers()
    lattice, scaled_positions, numbers = find_primitive((lattice, positions, numbers), symprec=symprec)
    new_structure_ase = Atoms(numbers, scaled_positions=scaled_positions, cell=lattice, pbc=True)
    new_structure = StructureData(ase=new_structure_ase)
    # print('new {}'.format(len(new_structure.sites)))

    new_structure.label = structure.label + ' primitive'
    new_structure.description = structure.description + ' primitive cell'
    return new_structure


@cf
def find_primitive_cell_wf(structure):
    """
    uses spglib find_primitive to find the primitive cell
    :param structure: AiiDa structure data

    :return: list of new AiiDa structure data
    """

    return {'primitive_cell': find_primitive_cell(structure)}


def find_primitive_cells(uuid_list):
    """
    uses spglib find_primitive to find the primitive cell
    :param uuid_list: list of structureData uuids, or pks

    :return: list of new AiiDa structure datas
    """

    new_structures = []
    for uuid in uuid_list:
        structure = load_node(uuid)
        new_structure = find_primitive_cell(structure)
        new_structures.append(new_structure)
    return new_structures


def get_all_miller_indices(structure, highestindex):
    """
    wraps the pymatgen function get_symmetrically_distinct_miller_indices for an AiiDa structure
    """
    from pymatgen.core.surface import get_symmetrically_distinct_miller_indices
    return get_symmetrically_distinct_miller_indices(structure.get_pymatgen_structure(), highestindex)


'''
def create_all_slabs_buggy(initial_structure,
                           miller_index,
                           min_slab_size_ang,
                           min_vacuum_size=0,
                           bonds=None,
                           tol=1e-3,
                           max_broken_bonds=0,
                           lll_reduce=False,
                           center_slab=False,
                           primitive=False,
                           max_normal_search=None,
                           symmetrize=False):  # , reorient_lattice=True):
    """
    wraps the pymatgen function generate_all_slabs with some useful extras
    :return: a dictionary of structures
    """
    StructureData = DataFactory('structure')
    aiida_strucs = {}
    pymat_struc = initial_structure.get_pymatgen_structure()
    # currently the pymatgen method is buggy... no coordinates in x,y....
    all_slabs = generate_all_slabs(pymat_struc,
                                   miller_index,
                                   min_slab_size_ang,
                                   min_vacuum_size,
                                   bonds=bonds,
                                   tol=tol,
                                   max_broken_bonds=max_broken_bonds,
                                   lll_reduce=lll_reduce,
                                   center_slab=center_slab,
                                   primitive=primitive,
                                   max_normal_search=max_normal_search,
                                   symmetrize=symmetrize)  # , reorient_lattice=reorient_lattice)
    for slab in all_slabs:
        # print(slab)
        # slab2 = #slab.get_orthogonal_c_slab()
        film_struc = StructureData(pymatgen_structure=slab)
        film_struc.pbc = (True, True, False)
        aiida_strucs[slab.miller_index] = film_struc
    return aiida_strucs
'''


def create_all_slabs(initial_structure,
                     miller_index,
                     min_slab_size_ang,
                     min_vacuum_size=0,
                     bonds=None,
                     tol=1e-3,
                     max_broken_bonds=0,
                     lll_reduce=False,
                     center_slab=False,
                     primitive=False,
                     max_normal_search=1,
                     symmetrize=False):  # , reorient_lattice=True):
    """
    :return: a dictionary of structures
    """
    StructureData = DataFactory('core.structure')
    aiida_strucs = {}
    # pymat_struc = initial_structure.get_pymatgen_structure()
    indices = get_all_miller_indices(initial_structure, miller_index)
    for index in indices:
        slab = create_slap(initial_structure, index, min_slab_size_ang, min_vacuum_size, min_slab_size_ang)
        #film_struc = StructureData(pymatgen_structure=slab)
        #film_struc.pbc = (True, True, False)
        aiida_strucs[index] = slab

    return aiida_strucs


def create_slap(initial_structure,
                miller_index,
                min_slab_size,
                min_vacuum_size=0,
                lll_reduce=False,
                center_slab=False,
                primitive=False,
                max_normal_search=1,
                reorient_lattice=True):
    """
    wraps the pymatgen slab generator
    """
    # minimum slab size is in Angstrom!!!
    StructureData = DataFactory('core.structure')
    pymat_struc = initial_structure.get_pymatgen_structure()
    slabg = SlabGenerator(pymat_struc,
                          miller_index,
                          min_slab_size,
                          min_vacuum_size,
                          lll_reduce=lll_reduce,
                          center_slab=center_slab,
                          primitive=primitive,
                          max_normal_search=max_normal_search)
    slab = slabg.get_slab()
    # slab2 = slab.get_orthogonal_c_slab()
    film_struc = StructureData(pymatgen_structure=slab)
    film_struc.pbc = (True, True, False)

    # TODO: sort atoms after z-coordinate value,
    # TODO: Move all atoms that the middle atom is at [x,y,0]
    # film_struc2 = move_atoms_incell(film_struc, [0,0, z_of_middle atom])

    return film_struc


@cf
def center_film_wf(structure):
    """
    Centers a film at z=0, keeps the provenance in the database

    :param structure: AiiDA structure

    :return: AiiDA structure
    """
    return center_film(structure)


def center_film(structure):
    """
    Centers a film at z=0

    :param structure: AiiDA structure

    :return: AiiDA structure
    """
    if structure.pbc != (True, True, False):
        raise TypeError('Only film structures having surface normal to z are supported')
    sorted_struc = sort_atoms_z_value(structure)
    sites = sorted_struc.sites
    shift = [0, 0, -(sites[0].position[2] + sites[-1].position[2]) / 2.0]

    return move_atoms_incell(sorted_struc, shift)


def sort_atoms_z_value(structure):
    """
    Resorts the atoms in a structure by there Z-value

    :param structure: AiiDA structure
    :return: AiiDA structure
    """
    StructureData = DataFactory('core.structure')
    new_structure = StructureData(cell=structure.cell)
    new_structure.pbc = structure.pbc
    for kind in structure.kinds:
        new_structure.append_kind(kind)

    sites = structure.sites
    new_site_list = []
    for site in sites:
        new_site_list.append([site, site.position[2]])
    sorted_sites = sorted(new_site_list, key=lambda position: position[1])
    for site in sorted_sites:
        new_structure.append_site(site[0])

    return new_structure


def create_manual_slab_ase(lattice='fcc',
                           miller=None,
                           directions=None,
                           host_symbol='Fe',
                           latticeconstant=4.0,
                           size=(1, 1, 5),
                           replacements=None,
                           decimals=8,
                           pop_last_layers=0):
    """
    Wraps ase.lattice lattices generators to create a slab having given lattice vectors directions.

    :param lattice: 'fcc' and 'bcc' are supported. Set the host lattice of a slab.
    :param miller: a list of directions of planes forming the primitive unit cell
    :param directions: a list of directions of lattice vectors
    :param symbol: a string specifying the atom type
    :param latticeconstant: the lattice constant of a structure
    :param size: a 3-element tuple that sets supercell size. For instance, use (1,1,5) to set
                 5 layers of a slab.
    :param replacements: a dict of type {INT: STRING}, where INT is the layer number to be replaced
                         (counting from lowest z-coordinate layers, INT=1 for the first layer
                         INT=-1 for the last one) and STRING is the element name.
    :param decimals: sets the rounding of atom positions. See numpy.around.
    :param pop_last_layers: specifies how many layers to remove. Sometimes one does not want
                            to use the integer number of unit cells along z, extra layers can be
                            removed. Layers are removed in order from highest to lowest z-coordinate.
    :return structure: an ase-lattice representing a slab with replaced atoms

    """

    if miller is None:
        miller = [None, None, None]
    if directions is None:
        directions = [None, None, None]

    if lattice == 'fcc':
        from ase.lattice.cubic import FaceCenteredCubic
        structure_factory = FaceCenteredCubic
    elif lattice == 'bcc':
        from ase.lattice.cubic import BodyCenteredCubic
        structure_factory = BodyCenteredCubic
    else:
        raise ValueError(f'The given lattice {lattice} is not supported')

    structure = structure_factory(miller=miller,
                                  directions=directions,
                                  symbol=host_symbol,
                                  pbc=(1, 1, 0),
                                  latticeconstant=latticeconstant,
                                  size=size)

    # sort atoms according to z coordinate
    current_symbols = structure.get_chemical_symbols()
    positions = structure.positions

    zipped = zip(positions, current_symbols)
    zipped = sorted(zipped, key=lambda x: np.around(x[0][2], decimals=decimals))

    positions = [x[0] for x in zipped]
    current_symbols = [x[1] for x in zipped]
    structure.set_chemical_symbols(current_symbols)
    structure.set_positions(positions)

    # pop layers having the highest z coordinate
    layer_occupancies = get_layers(structure)[2]

    if replacements is not None and len(replacements) > 0:
        keys = list(replacements.keys())
        if max(abs(int(x)) for x in keys) >= len(layer_occupancies):
            raise ValueError('"replacements" has to contain numbers less than number of layers:'
                             ' {}'.format(len(layer_occupancies)))
    else:
        replacements = {}

    layer_occupancies.append(0)  # technical append
    atoms_to_pop = np.cumsum(np.array(layer_occupancies[-1::-1]))
    for i in range(atoms_to_pop[pop_last_layers]):
        structure.pop()

    # incorporate replacements
    current_symbols = structure.get_chemical_symbols()
    layer_occupancies = get_layers(structure)[2]
    layer_occupancies.insert(0, 0)
    for i, at_type in replacements.items():
        if isinstance(i, str):
            i = int(i)
        if i != 0:
            i = i - 1  # if i positive: makes layers count from 1; if negative: makes count from -1
        else:
            raise ValueError('replacement layer should not be equal to 0')
        atoms_to_skip = np.cumsum(np.array(layer_occupancies))[i]
        for k in range(layer_occupancies[i + 1]):
            current_symbols[k + atoms_to_skip] = at_type
    structure.set_chemical_symbols(current_symbols)

    return structure


def magnetic_slab_from_relaxed(relaxed_structure,
                               orig_structure,
                               total_number_layers,
                               num_relaxed_layers,
                               z_coordinate_window=3,
                               shift=(0, 0)):
    """
    Transforms a structure that was used for interlayer distance relaxation to
    a structure that can be further used for magnetic calculations.

    Usually one uses a slab having z-reflection symmetry e.g. A-B1-B2-B3-B2-B1-A where A is
    a magnetic element (Fe, Ni, Co, Cr) and B is a substrate. However, further magnetic
    calculations are done using assymetric slab A-B1-B2-B3-B4-B5-B6-B7-B8. The function uses
    A-B1, B1-B2 etc. iterlayer distances for constraction of assymetric relaxed film.

    The function works as follows: it constructs a new StructureData object taking x and y positions
    from the orig_structure and z positions from relax_structure for first num_relaxed_interlayers.
    Then it appends orig_structure slab to the bottom it a way the total number of layers is
    total_number_layers.

    :param relaxed_structure: Structure which is the output of Relax WorkChain. In thin function
                              it is assumed to have inversion or at least z-reflection symmetry.
    :param orig_structure: The host structure slab having the lattice perioud corresponding to
                           the bulk structure of the substrate.
    :param total_number_layers: the total number of layers to produce
    :param num_relaxed_layers: the number of top layers to adjust according to **relaxed_struct**
    :param tolerance_decimals: sets the rounding of atom positions. See numpy.around.
    :return magn_structure: Resulting assymetric structure with adjusted interlayer distances for
                            several top layers.

    """
    from aiida.orm import StructureData

    if relaxed_structure.pbc != (True, True, False):
        raise ValueError('Input structure has to be a film')

    sorted_struc = sort_atoms_z_value(relaxed_structure)
    sites = sorted_struc.sites

    layers = {np.around(atom.position[2], decimals=z_coordinate_window) for atom in sites}
    num_layers = len(layers)
    if has_z_reflection(sorted_struc):
        max_layers_to_extract = num_layers // 2 + num_layers % 2
    else:
        max_layers_to_extract = num_layers

    if isinstance(orig_structure, StructureData):
        positions = orig_structure.get_ase().positions
    else:
        positions = orig_structure.positions

    num_layers_org = len({np.around(x[2], decimals=z_coordinate_window) for x in positions})

    if num_layers_org > num_layers:
        raise ValueError('Your original structure contains more layers than given in relaxed '
                         'structure.\nCould you reduce the number of layers in the'
                         'original structure?\nIf not, I will not be able to guess '
                         'x-y displacements of some atoms')

    if num_relaxed_layers > max_layers_to_extract:
        print('You want to extract more layers than available, I am setting num_relaxed_layers to'
              ' {}'.format(max_layers_to_extract))
        num_relaxed_layers = max_layers_to_extract

    # take relaxed interlayers
    magn_structure = StructureData(cell=sorted_struc.cell)
    magn_structure.pbc = (True, True, False)
    for kind in relaxed_structure.kinds:
        kind_append = kind
        kind_append.name = simplify_kind_name(kind.name)
        try:
            magn_structure.append_kind(kind_append)
        except ValueError:
            pass

    done_layers = 0
    while True:
        if done_layers < num_relaxed_layers:
            layer = get_layers(sorted_struc, z_coordinate_window=z_coordinate_window)[0]
            for atom in layer[done_layers]:
                orig_pos = atom[0]
                pos_x = atom[0][0] + shift[0] * magn_structure.cell[0][0] + shift[1] * magn_structure.cell[1][0]
                pos_y = atom[0][1] + shift[0] * magn_structure.cell[0][1] + shift[1] * magn_structure.cell[1][1]
                a = Site(kind_name=atom[1], position=(pos_x, pos_y, atom[0][2]))
                magn_structure.append_site(a)
            done_layers = done_layers + 1
        elif done_layers < total_number_layers:
            k = done_layers % num_layers_org
            layer = get_layers(orig_structure, z_coordinate_window=z_coordinate_window)[0]
            prev_layer_z = magn_structure.sites[-1].position[2]
            for atom in layer[k]:
                if k == 0:
                    add_distance = abs(atom[0][2] + orig_structure.cell[2][2] - layer[k - 1][0][0][2])
                else:
                    add_distance = abs(atom[0][2] - layer[k - 1][0][0][2])
                atom[0][2] = prev_layer_z + add_distance
                a = Site(kind_name=atom[1], position=atom[0])
                magn_structure.append_site(a)
            done_layers = done_layers + 1
        else:
            break

    magn_structure = center_film(magn_structure)
    return magn_structure


def get_layers(structure, z_coordinate_window=8):
    """
    Extracts atom positions and their types belonging to the same layer
    Removes any information related to kind specie.

    :param structure: ase lattice or StructureData which represents a slab
    :param number: the layer number. Note, that layers will be sorted according to z-position
    :param z_coordinate_window: sets the maximal difference between 2 atoms that will be considered in the same layer.
                                it is an interger, which sets how z-coordinates will be rounded. For instance,
                                z_coordinate_window = 2 means that first z-coordinates will be rounded up to 2 digits
                                after the dot and than grouped.
    :return layer, layer_z_positions: layer is a list of tuples, the first element of which is
                                      atom positions and the second one is atom type.
                                      layer_z_position is a sorted list of all layer positions

    """
    from aiida.orm import StructureData
    from ase.lattice.bravais import Lattice
    from itertools import groupby
    import copy

    structure = copy.deepcopy(structure)

    if isinstance(structure, StructureData):
        reformat = [(list(x.position), simplify_kind_name(x.kind_name))
                    for x in sorted(structure.sites, key=lambda x: x.position[2])]
    elif isinstance(structure, Lattice):
        reformat = list(zip(structure.positions, structure.get_chemical_symbols()))
    else:
        raise ValueError('Structure has to be ase lattice or StructureData')

    layer_z_positions = []
    layer_occupancies = []
    layers = []
    for val, e in groupby(reformat, key=lambda x: np.around(x[0][2], decimals=z_coordinate_window)):
        layer_z_positions.append(val)
        layer_content = list(e)
        layers.append(layer_content)
        layer_occupancies.append(len(layer_content))

    return layers, layer_z_positions, layer_occupancies


def adjust_film_relaxation(structure,
                           suggestion,
                           scale_as=None,
                           bond_length=None,
                           last_layer_factor=0.85,
                           first_layer_factor=0.85):
    """
    Tries to optimize interlayer distances. Can be used before RelaxWC to improve its behaviour.
    Works only for films having no z-reflection symmetry, for other films check out the adjust_sym_film_relaxation

    .. warning:

        This should work ony for metallic bonding since bond length can drastically
        depend on the atom hybridisation.

    .. warning:

        The algorithm builds structure from the highest z-coordinates to the lowest
        z-coordinates. If your system is a film deposited on substrate, make sure that
        the substrate is located above magnetic elements i.e. the substrate has the most positive z-coordinates.
        If you use create_manual_slab_ase, it can be achieved by replacing substrate for magnetic elements from the
        bottom, using for example {1: 'Fe'} instead of {-1: 'Fe'}.

    :param structure: ase film structure which will be adjusted
    :param suggestion: dictionary containing average bond length between different elements,
                       is is basically the result of
                       :py:func:`~aiida_fleur.tools.StructureData_util.request_average_bond_length()`
    :param scale_as: an element name, for which the El-El bond length will be enforced. It is
                     can be helpful to enforce the same interlayer distance in the substrate,
                     i.e. adjust deposited film interlayer distances only.
    :param bond_length: a float that sets the bond length for scale_as element
    :param hold_layers: this parameters sets the number of layers that will be marked via the
                        certain label. The label is reserved for future use in the relaxation WC:
                        all the atoms marked with the label will not be relaxed.
    :param last_layer_factor: a float factor to which interlayer distance between last and second last layers
                              is multiplied
    :param first_layer_factor: a float factor to which interlayer distance between first and second layers
                              is multiplied
    """
    from aiida.orm import StructureData
    from copy import deepcopy
    from itertools import product

    if scale_as and not bond_length:
        raise ValueError('bond_length is required when scale_as was provided')

    structure = sort_atoms_z_value(structure)
    layers = get_layers(structure)[0][::-1]  # inverse the structure to start building from substrate

    suggestion = deepcopy(suggestion)
    if scale_as:
        norm = suggestion[scale_as][scale_as]
        for sym1, sym2 in product(suggestion.keys(), suggestion.keys()):
            try:
                suggestion[sym1][sym2] = suggestion[sym1][sym2] / norm
            except KeyError:
                pass  # do nothing, happens for magnetic-magnetic or substrate-substrate combinations

    layers_supercell = get_layers(supercell_ncf(structure, 2, 2, 1))[0][::-1]

    def calculate_distance_to_previous(num_layer, atom_prev, layers_supercell):
        pos_prev = np.array(atom_prev[0])[0:2]
        z_dist = [0]
        for atom_this in layers_supercell[num_layer]:
            pos_this = np.array(atom_this[0])[0:2]
            xy_dist_sq = np.linalg.norm(pos_prev - pos_this)**2
            if scale_as:
                bond_length_sq = suggestion[atom_prev[1]][atom_this[1]]**2 * bond_length**2
            else:
                bond_length_sq = suggestion[atom_prev[1]][atom_this[1]]**2
            if xy_dist_sq < bond_length_sq:
                z_dist.append((bond_length_sq - xy_dist_sq)**(0.5))
        return z_dist

    def suggest_distance_to_previous(num_layer):
        z_distances = []
        for atom_prev in layers_supercell[num_layer - 1]:
            z_distances.extend(calculate_distance_to_previous(num_layer, atom_prev, layers_supercell))

        # find suggestion for distance to 2nd layer
        z_distances2 = []
        if num_layer != 1:
            for atom_prev in layers_supercell[num_layer - 2]:
                z_distances2.extend(calculate_distance_to_previous(num_layer, atom_prev, layers_supercell))

        if not z_distances:
            z_distances = [0]

        if not z_distances2:
            z_distances2 = [0]

        return max(z_distances), max(z_distances2)

    # take relaxed interlayers
    rebuilt_structure = StructureData(cell=structure.cell)
    rebuilt_structure.pbc = (True, True, False)

    for atom in layers[0]:
        rebuilt_structure.append_atom(symbols=atom[1], position=(atom[0][0], atom[0][1], -atom[0][2]),
                                      name=atom[1])  # minus inverses back

    prev_distance = 0
    for i, layer in enumerate(layers[1:]):
        add_distance1, add_distance2 = suggest_distance_to_previous(i + 1)
        add_distance2 = add_distance2 - prev_distance
        if add_distance1 <= 0 and add_distance2 <= 0:
            raise ValueError('error not implemented')
        prev_distance = max(add_distance1, add_distance2)
        if i == len(layers) - 2 and last_layer_factor:
            prev_distance = prev_distance * last_layer_factor  # last layer should be closer
        elif i == 0 and first_layer_factor:
            prev_distance = prev_distance * first_layer_factor

        layer_copy = deepcopy(layer)
        prev_layer_z = -rebuilt_structure.sites[-1].position[2]  # minus to pretend that we built inverted structure
        for atom in layer_copy:
            atom[0][2] = -(prev_layer_z + prev_distance)  # minus inverses back
            rebuilt_structure.append_atom(position=atom[0], symbols=atom[1], name=atom[1])

    rebuilt_structure = center_film(rebuilt_structure)
    return rebuilt_structure


def adjust_sym_film_relaxation(structure,
                               suggestion,
                               scale_as=None,
                               bond_length=None,
                               last_layer_factor=0.85,
                               ILD=None):
    """
    Tries to optimize interlayer distances. Can be used before RelaxWC to improve its behaviour.
    Works only for films having z-reflection symmetry, for other films check out the adjust_film_relaxation

    .. warning:

        This should work ony for metallic bonding since bond length can drastically
        depend on the atom hybridisation.

    :param structure: ase film structure which will be adjusted
    :param suggestion: dictionary containing average bond length between different elements,
                       is is basically the result of
                       :py:func:`~aiida_fleur.tools.StructureData_util.request_average_bond_length()`
    :param scale_as: an element name, for which the El-El bond length will be enforced. It is
                     can be helpful to enforce the same interlayer distance in the substrate,
                     i.e. adjust deposited film interlayer distances only.
    :param bond_length: a float that sets the bond length for scale_as element
    :param hold_layers: this parameters sets the number of layers that will be marked via the
                        certain label. The label is reserved for future use in the relaxation WC:
                        all the atoms marked with the label will not be relaxed.
    :param last_layer_factor: a float factor to which interlayer distance between last and second last layers
                              is multiplied
    """
    from aiida.orm import StructureData
    from copy import deepcopy
    from itertools import product

    if scale_as and not bond_length:
        raise ValueError('bond_length is required when scale_as was provided')

    structure = center_film(structure)
    structure = sort_atoms_z_value(structure)

    suggestion = deepcopy(suggestion)
    if ILD is not None:
        ILD = deepcopy(ILD)
    if scale_as:
        norm = suggestion[scale_as][scale_as]
        for sym1, sym2 in product(suggestion.keys(), suggestion.keys()):
            try:
                suggestion[sym1][sym2] = suggestion[sym1][sym2] / norm
            except KeyError:
                pass  # do nothing, happens for magnetic-magnetic or substrate-substrate combinations

    # sort layers from central to surface atoms
    sorted_layers = sorted(get_layers(structure)[0], key=lambda x: abs(x[0][0][2]))
    sorted_layers = [x for x in sorted_layers if x[0][0][2] >= 0]

    layers_supercell = sorted(get_layers(supercell_ncf(structure, 2, 2, 1))[0], key=lambda x: abs(x[0][0][2]))
    layers_supercell = [x for x in layers_supercell if x[0][0][2] >= 0]

    def calculate_distance_to_previous(num_layer, atom_prev, layers_supercell):
        pos_prev = np.array(atom_prev[0])[0:2]
        z_dist = [0]
        for atom_this in layers_supercell[num_layer]:
            pos_this = np.array(atom_this[0])[0:2]
            xy_dist_sq = np.linalg.norm(pos_prev - pos_this)**2
            if scale_as:
                bond_length_sq = suggestion[atom_prev[1]][atom_this[1]]**2 * bond_length**2
            else:
                bond_length_sq = suggestion[atom_prev[1]][atom_this[1]]**2
            if xy_dist_sq < bond_length_sq:
                z_dist.append((bond_length_sq - xy_dist_sq)**(0.5))
        return z_dist

    def suggest_distance_to_previous(num_layer):
        z_distances = []
        for atom_prev in layers_supercell[num_layer - 1]:
            z_distances.extend(calculate_distance_to_previous(num_layer, atom_prev, layers_supercell))

        # find suggestion for distance to 2nd previous layer
        z_distances2 = []
        if num_layer != 1:
            for atom_prev in layers_supercell[num_layer - 2]:
                z_distances2.extend(calculate_distance_to_previous(num_layer, atom_prev, layers_supercell))
        elif layers_supercell[0][0][0][2] == 0:  # if it is the second layer and the first one is in the center
            for atom_prev in layers_supercell[num_layer]:  # we should consider the mirror image too
                z_distances2.extend(calculate_distance_to_previous(num_layer, atom_prev, layers_supercell))

        if not z_distances:
            z_distances = [0]

        if not z_distances2:
            z_distances2 = [0]

        return max(z_distances), max(z_distances2)

    rebuilt_structure = StructureData(cell=structure.cell)
    rebuilt_structure.pbc = (True, True, False)

    for atom in sorted_layers[0]:
        if atom[0][2] != 0:  # no layers in the center, calculate distance to the mirror image
            z_distances2 = []
            for atom_prev in layers_supercell[0]:
                z_distances2.extend(calculate_distance_to_previous(0, atom_prev, layers_supercell))
            z_first = max(z_distances2) / 2
            rebuilt_structure.append_atom(symbols=atom[1], position=(atom[0][0], atom[0][1], z_first), name=atom[1])
            rebuilt_structure.append_atom(symbols=atom[1], position=(atom[0][0], atom[0][1], -z_first), name=atom[1])
        else:  # if the first layer is in the center we can simply add it
            rebuilt_structure.append_atom(symbols=atom[1], position=(atom[0][0], atom[0][1], atom[0][2]), name=atom[1])

    prev_distance = 0
    if ILD is not None:
        if len(ILD.keys()) > 0:
            #Init Counting
            keyILD = list(ILD)  #List of keys
    else:
        keyILD = 0
    #Now iterate over all other layers
    for i, layer in enumerate(sorted_layers[1:]):
        layer_copy = deepcopy(layer)
        add_distance1, add_distance2 = suggest_distance_to_previous(i + 1)
        if i == 0:  # the 2nd distance is the distance to the mirror image in films with no central layer
            # for a film with central layer add_distance2 == 0
            add_distance2 = add_distance2 / 2
        else:
            add_distance2 = add_distance2 - prev_distance
        if add_distance1 <= 0 and add_distance2 <= 0:
            raise ValueError('error not implemented')
        prev_distance = max(add_distance1, add_distance2)

        if i == len(sorted_layers) - 2 and last_layer_factor:
            if ILD is None:
                prev_distance = prev_distance * last_layer_factor  # last layer should be closer

        prev_layer_z = max(x.position[2] for x in rebuilt_structure.sites)

        for atom in layer_copy:
            if ILD is None:
                atom[0][2] = prev_layer_z + prev_distance
            else:
                if ILD[keyILD[i]] == 0.0:
                    atom[0][2] = prev_layer_z + prev_distance
                else:
                    atom[0][2] = prev_layer_z + ILD[keyILD[i]]
                    print(atom)
            print("We're here")
            rebuilt_structure.append_atom(position=atom[0], symbols=atom[1], name=atom[1])
            rebuilt_structure.append_atom(
                position=(atom[0][0], atom[0][1], -atom[0][2]), symbols=atom[1],
                name=atom[1])  # minus at atom[0][2] because the film is built from bottom (inverse)
    rebuilt_structure = center_film(rebuilt_structure)
    return rebuilt_structure


def mark_fixed_atoms(structure, hold_layers=None):
    '''
    Marks atom in layers, that should be fixed in the relaxation. Uses reserved 49999 label
    '''
    from aiida.orm import StructureData

    if hold_layers is None or not hold_layers:
        return structure

    rebuilt_structure = StructureData(cell=structure.cell)
    rebuilt_structure.pbc = (True, True, False)

    layers = get_layers(structure)[0]

    for i, layer in enumerate(layers):
        if i + 1 in hold_layers or (-len(layers) + i) in hold_layers:
            addition = '49999'
        else:
            addition = ''
        for atom in layer:
            element = atom[1].rstrip('0123456789')
            old_addition = atom[1][len(element):]
            if old_addition != '' and addition == '':
                addition = old_addition
            rebuilt_structure.append_atom(position=atom[0], symbols=element, name=element + addition)

    return rebuilt_structure


def has_z_reflection(structure):
    '''
    Checks if a structure has z-reflection symmetry
    '''
    structure = center_film(structure)
    structure = sort_atoms_z_value(structure)
    layers = get_layers(structure)[0]

    for i, layer in enumerate(layers):
        for atom in layer:
            atom_symmetrical = list(layers[-1 - i])
            atom_check = ([atom[0][0], atom[0][1], -atom[0][2]], atom[1])

            if atom_check not in atom_symmetrical:
                return False
    return True


def request_average_bond_length_store(first_bin, second_bin, user_api_key, ignore_second_bin=False):
    """
    Requests MaterialsProject to estimate thermal average bond length between given elements.
    Also requests information about lattice constants of fcc and bcc structures.
    Stores the result in the Database. Notice that this is not a calcfunction!
    Therefore, the inputs are not stored and the result node is unconnected.

    :param first_bin: element list to calculate the average bond length
                      only combinations of AB, AA and BB are calculated, where
                      A belongs to first_bin, B belongs to second_bin.
    :param second_bin: element list, see main_elements
    :param user_api_key: user API key from materialsproject
    :param ignore_second_bin: if True, the second bin is ignored and all possible combinations from the first one are
                              constructed.
    :return: bond_data, a dict containing obtained lattice constants.
    """
    result = request_average_bond_length(first_bin, second_bin, user_api_key, ignore_second_bin)
    result.store()
    return result


def request_average_bond_length(first_bin, second_bin, user_api_key, ignore_second_bin=False):
    """
    Requests MaterialsProject to estimate thermal average bond length between given elements.
    Also requests information about lattice constants of fcc and bcc structures.

    :param first_bin: element list to calculate the average bond length
                      only combinations of AB are calculated, where
                      A belongs to first_bin, B belongs to second_bin.
    :param second_bin: element list, see main_elements
    :param user_api_key: user API key from materialsproject
    :param ignore_second_bin: if True, the second bin is ignored and all possible combinations from the first one are
                              constructed.
    :return: bond_data, a dict containing obtained lattice constants.
    """
    from itertools import product, combinations
    from math import exp  # pylint: disable=no-name-in-module
    from aiida.orm import Dict
    from pymatgen.ext.matproj import MPRester
    from collections import defaultdict
    from copy import deepcopy

    bond_data = defaultdict(lambda: defaultdict(lambda: 0.0))
    if ignore_second_bin:
        symbols = first_bin
        second_bin_calculate = first_bin
    else:
        symbols = first_bin + second_bin
        second_bin_calculate = second_bin

    for sym in symbols:
        distance = 0
        partition_function = 0
        with MPRester(user_api_key) as mat_project:  #pylint: disable=not-context-manager
            mp_entries = mat_project.get_entries_in_chemsys([sym])
        fcc_structure = None
        bcc_structure = None
        for entry in mp_entries:
            if sym != entry.name:
                continue
            with MPRester(user_api_key) as mat_project:  #pylint: disable=not-context-manager
                structure_analyse = mat_project.get_structure_by_material_id(entry.entry_id)
                en_per_atom = mat_project.query(entry.entry_id, ['energy_per_atom'])[0]['energy_per_atom']
                structure_analyse.make_supercell([2, 2, 2])
            factor = exp(-(en_per_atom / 0.0259))
            partition_function = partition_function + factor
            indices1 = structure_analyse.indices_from_symbol(sym)
            distances = (structure_analyse.get_distance(x, y) for x, y in combinations(indices1, 2))
            min_distance = min(distances)
            distance = distance + min_distance * factor
            # save distance for particular cases of fcc and bcc
            if structure_analyse.get_space_group_info()[1] == 225:  # fcc
                bond_data['fcc'][sym] = min_distance
            elif structure_analyse.get_space_group_info()[1] == 229:  # bcc
                bond_data['bcc'][sym] = min_distance

        distance = distance / partition_function
        bond_data[sym][sym] = distance
        print('Request completed for {symst} {symst} pair'.format(symst=sym))

    for sym1, sym2 in product(first_bin, second_bin_calculate):
        if sym1 == sym2:
            continue
        distance = 0
        partition_function = 0
        with MPRester(user_api_key) as mat_project:  #pylint: disable=not-context-manager
            mp_entries = mat_project.get_entries_in_chemsys([sym1, sym2])
        for entry in mp_entries:
            name = ''.join([i for i in entry.name if not i.isdigit()])
            if name not in (sym1 + sym2, sym2 + sym1):
                continue
            with MPRester(user_api_key) as mat_project:  #pylint: disable=not-context-manager
                structure_analyse = mat_project.get_structure_by_material_id(entry.entry_id)
                en_per_atom = mat_project.query(entry.entry_id, ['energy_per_atom'])[0]['energy_per_atom']
                structure_analyse.make_supercell([2, 2, 2])
            factor = exp(-(en_per_atom / 0.0259))
            partition_function = partition_function + factor
            indices1 = structure_analyse.indices_from_symbol(sym1)
            indices2 = structure_analyse.indices_from_symbol(sym2)
            distances = (structure_analyse.get_distance(x, y) for x, y in product(indices1, indices2))
            distance = distance + min(distances) * factor
        if partition_function == 0:
            distance = (bond_data[sym1][sym1] + bond_data[sym2][sym2]) / 2
        else:
            distance = distance / partition_function
        bond_data[sym1][sym2] = distance
        bond_data[sym2][sym1] = distance
        print(f'Request completed for {sym1} {sym2} pair')

    return Dict(bond_data)


@cf
def replace_element(inp_structure, replace_dict, replace_all=None):
    """
    Replaces the given element with the element_replacement, but keeps the structure the same.
    If there are more than one site they are either all replaced or a list with one replacement
    at a time is returned.
    Keeps the provenance in the database.

    :param inp_structure: a StructureData node (pk, or uuid)
    :param replace_dict: Dict of elements to replace. Replacement is done according to the symbols
    :param replace_all: bool determines wether to replace all occurrences of the element at once
                        Otherwise a list, with one occurence replaced at a time

    :return: Dict with new StructureData nodes with replaced elements,
             which is/are linked to input Structure
             and None if inp_structure was not a StructureData

    Example usage:
        This example replaces all Neodymium atoms with Yttrium
        replace_element(structure,Dict(dict={'Nd':'Y'}),replace_all=Bool(True))
    """

    return replace_elementf(inp_structure, replace_dict, replace_all)


def replace_elementf(inp_structure, replace_dict, replace_all):
    """
    Replaces the site according to replace_dict (symbols), but keeps the structure the same.
    If there are more than one site they are either all replaced or a list with one replacement
    at a time is returned.
    DOES NOT keep the provenance in the database.

    :param inp_structure: a StructureData node (pk, or uuid)
    :param replace_dict: Dict of elements to replace. Replacement is done according to the symbols
    :param replace_all: bool determines wether to replace all occurrences of the element at once
                        Otherwise a list, with one occurence replaced at a time

    :return: New StructureData node or list of new StructureData nodes with replaced elements,
             which is/are linked to input Structure
             and None if inp_structure was not a StructureData
    """

    if replace_all is None:
        replace_all = Bool(True)

    # test if structure:
    structure = is_structure(inp_structure)
    if not structure:
        # TODO: log something
        return None

    StructureData = DataFactory('core.structure')

    replace_dict = replace_dict.get_dict()

    new_structures = {}

    ase_struc = structure.get_ase()
    if replace_all:
        for replace_symbol, new_symbol in replace_dict.items():
            ase_struc.symbols[ase_struc.symbols == replace_symbol] = new_symbol
        new_structures['replaced_all'] = StructureData(ase=ase_struc)
    else:
        for replace_symbol, new_symbol in replace_dict.items():
            for index, symbol in enumerate(ase_struc.symbols):
                if symbol == replace_symbol:
                    struc = ase_struc.copy()
                    struc.symbols[index] = new_symbol
                    label = f'replaced_{replace_symbol}_{new_symbol}_site_{index}'
                    new_structures[label] = StructureData(ase=struc)

    for name, structure in new_structures.items():
        structure.label = name
        structure.description = f"Structure with {'all' if 'all' in name else ''} {replace_symbol} atoms replaced with {new_symbol}"

    return new_structures


def mark_atoms(structure, condition, kind_id='99999'):
    '''
    Marks atom where sites fullfill the given condition with a given id
    The resulting kind name for these atoms is element-kind_id

    condition is a callable taking the site and kind as arguments
    '''
    from aiida.orm import StructureData

    new_structure = StructureData(cell=structure.cell)
    new_structure.pbc = structure.pbc

    for site in structure.sites:
        kind = structure.get_kind(site.kind_name)
        element = kind.symbols[0]
        if condition(site, kind):
            new_structure.append_atom(position=site.position, symbols=element, name=f'{element}-{kind_id}')
        else:
            if site.kind_name not in {kind.name for kind in new_structure.kinds}:
                new_structure.append_kind(kind)
            new_structure.append_site(site)

    return new_structure


def simplify_kind_name(kind_name):
    '''
    Simplifies the kind name string. Example: "W-1" -> "W", "Iron (Fe)" -> "Fe"
    '''
    if '(' in kind_name:
        return kind_name[kind_name.find('(') + 1:kind_name.find(')')]
    return kind_name.split('-')[0]


def define_AFM_structures(structure,
                          lattice,
                          directions,
                          host_symbol,
                          replacements,
                          latticeconstant,
                          size,
                          decimals=8,
                          pop_last_layers=0,
                          AFM_name='FM',
                          magnetic_layers=1,
                          sym_film=False):
    """
    Create
    """
    from aiida.orm import StructureData
    if magnetic_layers not in [1, 2]:
        raise ValueError('magnetic_layers should be equal to 1 or 2, other options are not supported')

    size_z = size[2]

    if lattice == 'fcc':

        if directions == [[-1, 1, 0], [0, 0, 1], [1, 1, 0]]:
            if AFM_name == 'FM':
                output_structure = create_manual_slab_ase(lattice=lattice,
                                                          directions=directions,
                                                          host_symbol=host_symbol,
                                                          latticeconstant=latticeconstant,
                                                          size=(1, 1, size_z),
                                                          replacements=replacements,
                                                          decimals=decimals,
                                                          pop_last_layers=pop_last_layers)

                substrate = create_manual_slab_ase(lattice=lattice,
                                                   directions=directions,
                                                   host_symbol=host_symbol,
                                                   latticeconstant=latticeconstant,
                                                   size=(1, 1, 1),
                                                   replacements=None,
                                                   decimals=decimals)

                def spin_up(atom):
                    return True

            elif AFM_name == 'AFM_x':
                if magnetic_layers == 1:
                    output_structure = create_manual_slab_ase(lattice=lattice,
                                                              directions=directions,
                                                              host_symbol=host_symbol,
                                                              latticeconstant=latticeconstant,
                                                              size=(2, 1, size_z),
                                                              replacements=replacements,
                                                              decimals=decimals,
                                                              pop_last_layers=pop_last_layers)

                    substrate = create_manual_slab_ase(lattice=lattice,
                                                       directions=directions,
                                                       host_symbol=host_symbol,
                                                       latticeconstant=latticeconstant,
                                                       size=(2, 1, 1),
                                                       replacements=None,
                                                       decimals=decimals)

                else:
                    output_structure = create_manual_slab_ase(lattice=lattice,
                                                              directions=directions,
                                                              host_symbol=host_symbol,
                                                              latticeconstant=latticeconstant,
                                                              size=(1, 1, size_z),
                                                              replacements=replacements,
                                                              decimals=decimals,
                                                              pop_last_layers=pop_last_layers)

                    substrate = create_manual_slab_ase(lattice=lattice,
                                                       directions=directions,
                                                       host_symbol=host_symbol,
                                                       latticeconstant=latticeconstant,
                                                       size=(1, 1, 1),
                                                       replacements=None,
                                                       decimals=decimals)

                def spin_up(atom):
                    if round(atom[0][0], 10) != 0 or round(atom[0][1], 10) != 0:
                        return False
                    return True

            elif AFM_name == 'AFM_y':
                if magnetic_layers == 1:
                    output_structure = create_manual_slab_ase(lattice=lattice,
                                                              directions=directions,
                                                              host_symbol=host_symbol,
                                                              latticeconstant=latticeconstant,
                                                              size=(1, 2, size_z),
                                                              replacements=replacements,
                                                              decimals=decimals,
                                                              pop_last_layers=pop_last_layers)

                    substrate = create_manual_slab_ase(lattice=lattice,
                                                       directions=directions,
                                                       host_symbol=host_symbol,
                                                       latticeconstant=latticeconstant,
                                                       size=(1, 2, 1),
                                                       replacements=None,
                                                       decimals=decimals)
                else:
                    output_structure = create_manual_slab_ase(lattice=lattice,
                                                              directions=directions,
                                                              host_symbol=host_symbol,
                                                              latticeconstant=latticeconstant,
                                                              size=(1, 1, size_z),
                                                              replacements=replacements,
                                                              decimals=decimals,
                                                              pop_last_layers=pop_last_layers)

                    substrate = create_manual_slab_ase(lattice=lattice,
                                                       directions=directions,
                                                       host_symbol=host_symbol,
                                                       latticeconstant=latticeconstant,
                                                       size=(1, 1, 1),
                                                       replacements=None,
                                                       decimals=decimals)

                def spin_up(atom):
                    if round(atom[0][0], 10) != 0 or round(atom[0][1], 10) != 0:
                        return False
                    return True

            elif AFM_name == 'AFM_xy':
                output_structure = create_manual_slab_ase(lattice=lattice,
                                                          directions=[[-1, 1, 2], [1, -1, 2], [1, 1, 0]],
                                                          host_symbol=host_symbol,
                                                          latticeconstant=latticeconstant,
                                                          size=(1, 1, size_z),
                                                          replacements=replacements,
                                                          decimals=decimals,
                                                          pop_last_layers=pop_last_layers)

                substrate = create_manual_slab_ase(lattice=lattice,
                                                   directions=[[-1, 1, 2], [1, -1, 2], [1, 1, 0]],
                                                   host_symbol=host_symbol,
                                                   latticeconstant=latticeconstant,
                                                   size=(1, 1, 1),
                                                   replacements=None,
                                                   decimals=decimals)

                last_layer_z = get_layers(output_structure)[1][-1]

                def spin_up(atom):
                    if round(atom[0][2], 10) > 0 and round(atom[0][2],
                                                           decimals) != last_layer_z:  # 2nd first and last layers only
                        if round(atom[0][0], 10) == 0 and round(atom[0][1], 10) != 0 or round(
                                atom[0][0], 10) != 0 and round(atom[0][1], 10) == 0:
                            return False
                    else:  # first and last layers only
                        if round(atom[0][0], 10) != 0 and round(atom[0][1], 10) != 0:
                            return False
                    return True

    elif lattice == 'bcc':

        if directions == [[1, -1, 1], [1, -1, -1], [1, 1, 0]]:
            if AFM_name == 'FM':
                output_structure = create_manual_slab_ase(lattice=lattice,
                                                          directions=directions,
                                                          host_symbol=host_symbol,
                                                          latticeconstant=latticeconstant,
                                                          size=(1, 1, size_z),
                                                          replacements=replacements,
                                                          decimals=decimals,
                                                          pop_last_layers=pop_last_layers)

                substrate = create_manual_slab_ase(lattice=lattice,
                                                   directions=directions,
                                                   host_symbol=host_symbol,
                                                   latticeconstant=latticeconstant,
                                                   size=(1, 1, 1),
                                                   replacements=None,
                                                   decimals=decimals)

                def spin_up(atom):
                    return True

            elif AFM_name == 'AFM_x':
                output_structure = create_manual_slab_ase(lattice=lattice,
                                                          directions=[[0, 0, 1], [1, -1, 0], [1, 1, 0]],
                                                          host_symbol=host_symbol,
                                                          latticeconstant=latticeconstant,
                                                          size=(1, 1, size_z),
                                                          replacements=replacements,
                                                          decimals=decimals,
                                                          pop_last_layers=pop_last_layers)

                substrate = create_manual_slab_ase(lattice=lattice,
                                                   directions=[[0, 0, 1], [1, -1, 0], [1, 1, 0]],
                                                   host_symbol=host_symbol,
                                                   latticeconstant=latticeconstant,
                                                   size=(1, 1, 1),
                                                   replacements=None,
                                                   decimals=decimals)

                def spin_up(atom):
                    if round(atom[0][0], 10) != 0:
                        return False
                    return True

            elif AFM_name == 'AFM_y':
                output_structure = create_manual_slab_ase(lattice=lattice,
                                                          directions=[[0, 0, 1], [1, -1, 0], [1, 1, 0]],
                                                          host_symbol=host_symbol,
                                                          latticeconstant=latticeconstant,
                                                          size=(1, 1, size_z),
                                                          replacements=replacements,
                                                          decimals=decimals,
                                                          pop_last_layers=pop_last_layers)

                substrate = create_manual_slab_ase(lattice=lattice,
                                                   directions=[[0, 0, 1], [1, -1, 0], [1, 1, 0]],
                                                   host_symbol=host_symbol,
                                                   latticeconstant=latticeconstant,
                                                   size=(1, 1, 1),
                                                   replacements=None,
                                                   decimals=decimals)

                def spin_up(atom):
                    if round(atom[0][1], 10) != 0:
                        return False
                    return True

            elif AFM_name == 'AFM_xy':
                if magnetic_layers == 1:
                    output_structure = create_manual_slab_ase(lattice=lattice,
                                                              directions=directions,
                                                              host_symbol=host_symbol,
                                                              latticeconstant=latticeconstant,
                                                              size=(2, 1, size_z),
                                                              replacements=replacements,
                                                              decimals=decimals,
                                                              pop_last_layers=pop_last_layers)

                    substrate = create_manual_slab_ase(lattice=lattice,
                                                       directions=directions,
                                                       host_symbol=host_symbol,
                                                       latticeconstant=latticeconstant,
                                                       size=(2, 1, 1),
                                                       replacements=None,
                                                       decimals=decimals)

                else:
                    output_structure = create_manual_slab_ase(lattice=lattice,
                                                              directions=directions,
                                                              host_symbol=host_symbol,
                                                              latticeconstant=latticeconstant,
                                                              size=(1, 1, size_z),
                                                              replacements=replacements,
                                                              decimals=decimals,
                                                              pop_last_layers=pop_last_layers)

                    substrate = create_manual_slab_ase(lattice=lattice,
                                                       directions=directions,
                                                       host_symbol=host_symbol,
                                                       latticeconstant=latticeconstant,
                                                       size=(1, 1, 1),
                                                       replacements=None,
                                                       decimals=decimals)

                def spin_up(atom):
                    if round(atom[0][0], 10) != 0 or round(atom[0][1], 10) != 0:
                        return False
                    return True

    if isinstance(structure, StructureData):
        init_layers = get_layers(structure)[1]
    else:
        init_layers = structure

    try:
        rebuilt_structure = StructureData(cell=output_structure.cell)
        rebuilt_structure.pbc = (True, True, False)
    except UnboundLocalError as err:
        raise ValueError('Please check the lattice and directions input, I do now know given values') from err

    output_layers = get_layers(output_structure)[0]

    if len(init_layers) != len(output_layers):
        raise ValueError('input and output structure have different number of layers {} {}'.format(
            len(init_layers), len(output_layers)))

    for i, layer in enumerate(get_layers(output_structure)[0]):
        for atom in layer:
            if i < magnetic_layers or sym_film and i >= len(output_layers) - magnetic_layers:
                if spin_up(atom):
                    addition = '49990'
                else:
                    addition = '49991'
            else:
                addition = ''
            rebuilt_structure.append_atom(position=(atom[0][0], atom[0][1], init_layers[i]),
                                          symbols=atom[1],
                                          name=atom[1] + addition)

    return rebuilt_structure, substrate


def get_atomtype_site_symmetry(struc):
    """
    Get the local site symmetry symbols for each atomtype

    Uses pymatgen SpaceGroupAnalyzer

    :param struc: StructureData to analyse

    :returns: list of the site symmetry symbols for each atomtype
              (In the order they appear in the StructureData)
    """
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from more_itertools import unique_everseen

    pym_struc = struc.get_pymatgen()

    symmetry_analyzer = SpacegroupAnalyzer(pym_struc)
    sym_data = symmetry_analyzer.get_symmetry_dataset()

    site_symmetries = sym_data['site_symmetry_symbols']
    equivalent_atoms = sym_data['equivalent_atoms']

    #Get the representative atom for each atomtype
    representative_atoms = unique_everseen(equivalent_atoms)

    return [site_symmetries[repr_atom] for repr_atom in representative_atoms]


'''
def estimate_mt_radii(structure, stepsize=0.05):
    """
    # TODO implement
    This method returns for every atom type (group/kind) in the structure a range of
    possible muffin tin radii (min, max).
    Or maybe just the maximal muffin tin radii (or sets of maximal muffin tin radii)

    example return for some Be-W compound
    [[{Be: 1.6, W:2.4}, {Be:1.8, W:2.2}]

    """

    # get symmetry equivalent atoms,
    # for each atom estimate muffin tin
    # check what algo fleur uses here
    # Max radius easy increase all spheres until they touch.
    # How to get the minimal muffin tin radii?
    return None


def common_mt(max_muffin_tins):
    """
    # TODO implement
    From a list of dictionary given return smallest common set.
    Could be read from the econfig file within AiiDA fleur.

    [[{Be: 1.7, W:2.4}, {Be:1.8, W:2.3}], [{Be : 1.75}], [{W:2.5}]
    should return [{Be:1.7, W:2.4}]
    """
    return None


def find_common_mt(structures):
    """
    # TODO implement (in some phd notebook of Broeder this is implement)
    From a given list of structures, estimate the muffin tin radii and return
    the smallest common set. (therefore a choice for rmt that would work for every structure given)

    """
    return None
'''
