#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collection of utility routines dealing with StructureData objects
"""
#TODO move imports to workfuncitons namespace?

from ase import *
from ase.lattice.surface import *
from ase.io import *
from aiida.orm import DataFactory
from aiida.orm import load_node
from aiida.orm.data.structure import Site, Kind
from aiida.work.workfunction import workfunction as wf
import numpy as np
from pymatgen.core.surface import generate_all_slabs, get_symmetrically_distinct_miller_indices, SlabGenerator

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')


def is_structure(structure):
    """
    Test if the given input is a StructureData node, by obejct, id, or pk
    if yes returns a StructureData node in all cases
    if no returns None
    """
    StructureData = DataFactory('structure')

    #Test if StructureData
    if isinstance(structure, StructureData):
        return structure
    #Test if pk, if yes, is the corresponding node StructureData
    pk = None
    try:
        pk=int(structure)
    except:
        pass
    if pk:
        structure = load_node(pk)
        if isinstance(structure, StructureData):
            return structure
        else:
            return None
    #Test if uuid, if yes, is the corresponding node StructureData
    # TODO: test for uuids not for string (guess is ok for now)
    uuid = None
    try:
        uuid = str(structure)
    except:
        pass
    if uuid:
        structure = load_node(uuid)
        if isinstance(structure, StructureData):
            return structure
        else:
            return None
    #Else throw error? or rather return None

    return None

@wf
def rescale(inp_structure, scale):
    """
    Rescales a crystal structure. Keeps the provanance in the database.

    :param inp_structure, a StructureData node (pk, or uuid)
    :param scale, float scaling factor for the cell

    :returns: New StrcutureData node with rescalled structure, which is linked to input Structure
              and None if inp_structure was not a StructureData
    """

    return rescale_nowf(inp_structure, scale)

def rescale_nowf(inp_structure, scale):#, _label='rescale_wf', _description='WF, Rescales a crystal structure (Volume), by a given float.'):
    """
    Rescales a crystal structure. DOES NOT keep the provanence in the database.

    :param inp_structure, a StructureData node (pk, or uuid)
    :param scale, float scaling factor for the cell

    :returns: New StrcutureData node with rescalled structure, which is linked to input Structure
              and None if inp_structure was not a StructureData
    """

    #test if structure:
    structure = is_structure(inp_structure)
    if not structure:
        #TODO: log something
        return None

    the_ase = structure.get_ase()
    new_ase = the_ase.copy()
    new_ase.set_cell(the_ase.get_cell()*float(scale), scale_atoms=True)
    rescaled_structure = DataFactory('structure')(ase=new_ase)

    return rescaled_structure

#@wf
def rescale_xyz(inp_structure, scalevec):
    """
    rescales a structure a certain way...
    """
    pass


@wf
def supercell(inp_structure, n_a1, n_a2, n_a3):
    """
    Creates a super cell from a StructureData node.
    Keeps the provanance in the database.

    :param StructureData, a StructureData node (pk, or uuid)
    :param scale: tuple of 3 AiiDA integers, number of cells in a1, a2, a3, or if cart =True in x,y,z

    :returns StructureData, Node with supercell
    """
    superc = supercell_nwf(inp_structure, n_a1, n_a2, n_a3)

    formula = inp_structure.get_formula()
    return superc


def supercell_nwf(inp_structure, n_a1, n_a2, n_a3):#, _label=u'supercell_wf', _description=u'WF, Creates a supercell of a crystal structure x(n1,n2,n3).'):# be carefull you have to use AiiDA datatypes...
    """
    Creates a super cell from a StructureData node.
    Does NOT keeps the provanance in the database.

    :param StructureData, a StructureData node (pk, or uuid)
    :param scale: tuple of 3 AiiDA integers, number of cells in a1, a2, a3, or if cart =True in x,y,z

    :returns StructureData, Node with supercell
    """
    #print('in create supercell')
    #test if structure:
    structure = is_structure(inp_structure)
    if not structure:
        #TODO: log something
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

    #new cell
    new_a1 = [i*na1 for i in old_a1]
    new_a2 = [i*na2 for i in old_a2]
    new_a3 = [i*na3 for i in old_a3]
    new_cell = [new_a1, new_a2, new_a3]
    new_structure = DataFactory('structure')(cell=new_cell, pbc=old_pbc)

    #insert atoms
    # first create all kinds
    old_kinds = structure.kinds
    for kind in old_kinds:
        new_structure.append_kind(kind)

    #scale n_a1
    for site in old_sites:
        # get atom position
        kn = site.kind_name
        pos_o = site.position
        for j in range(na1):
            pos = [pos_o[i] + j * old_a1[i] for i in range(0,len(old_a1))]
            new_structure.append_site(Site(kind_name=kn, position=pos))

    #scale n_a2
    o_sites = new_structure.sites
    for site in o_sites:
        # get atom position
        kn = site.kind_name
        pos_o = site.position
        for j in range(1,na2): # j=0 these sites/atoms are already added
            pos = [pos_o[i] + j * old_a2[i] for i in range(0,len(old_a2))]
            new_structure.append_site(Site(kind_name=kn, position=pos))

    #scale n_a3
    o_sites = new_structure.sites
    for site in o_sites:
        # get atom position
        kn = site.kind_name
        pos_o = site.position
        for j in range(1,na3): # these sites/atoms are already added
            pos = [pos_o[i] + j * old_a3[i] for i in range(0,len(old_a3))]
            new_structure.append_site(Site(kind_name=kn, position=pos))

    new_structure.label = 'supercell of {}'.format(formula)
    new_structure.description = '{}x{}x{} supercell of {}'.format(n_a1, n_a2, n_a3, inp_structure.get_formula())
    return new_structure


#wf
#prob don't make this a workfuntion, because rescale is already one and scalelist would has to be a ParameterData Node, since AiiDA has no list-datatype


#### Structure util
# after ths is in plugin code import these in fleurinp.
def abs_to_rel(vector, cell):
    """
    Converts a position vector in absolut coordinates to relative coordinates.
    """

    if len(vector) == 3:
        cell_np = np.array(cell)
        inv_cell_np = np.linalg.inv(cell_np)
        postionR =  np.array(vector)
        new_rel_post = np.matmul(postionR, inv_cell_np)#np.matmul(inv_cell_np, postionR)#
        new_rel_pos = [i for i in new_rel_post]
        return new_rel_pos
    else:
        return False

def abs_to_rel_f(vector, cell, pbc):
    """
    Converts a position vector in absolut coordinates to relative coordinates
    for a film system.
    """
    # TODO this currently only works if the z-coordinate is the one with no pbc
    # Therefore if a structure with x non pbc is given this should also work.
    # maybe write a 'tranform film to fleur_film routine'?
    if len(vector) == 3:
        if pbc[2] == False:
            # leave z coordinate absolut
            # convert only x and y.
            postionR =  np.array(vector)
            postionR_f =  np.array(postionR[:2])
            cell_np = np.array(cell)
            cell_np = np.array(cell_np[0:2, 0:2])
            inv_cell_np = np.linalg.inv(cell_np)
            new_xy = [i for i in np.matmul(postionR_f, inv_cell_np)]#np.matmul(inv_cell_np, postionR_f)]
            new_rel_pos_f = [new_xy[0], new_xy[1], postionR[2]]
            return new_rel_pos_f
        else:
            print 'FLEUR can not handle this type of film coordinate'
    else:
        return False

def rel_to_abs(vector, cell):
    """
    Converts a position vector in interal coordinates to absolut coordinates
    in Angstroem.
    """
    if len(vector) == 3:
        cell_np = np.array(cell)
        postionR =  np.array(vector)
        new_abs_post = np.matmul(postionR, cell_np)#
        new_abs_pos = [i for i in new_abs_post]

        return new_abs_pos

    else:
        return False

def rel_to_abs_f(vector, cell):
    """
    Converts a position vector in interal coordinates to absolut coordinates
    in Angstroem for a film structure (2D).
    """
    # TODO this currently only works if the z-coordinate is the one with no pbc
    # Therefore if a structure with x non pbc is given this should also work.
    # maybe write a 'tranform film to fleur_film routine'?
    if len(vector) == 3:
        postionR =  np.array(vector)
        postionR_f =  np.array(postionR[:2])
        #print postionR_f
        cell_np = np.array(cell)
        cell_np = np.array(cell_np[0:2, 0:2])
        #print cell_np
        new_xy = [i for i in np.matmul(postionR_f, cell_np)]
        new_abs_pos_f = [new_xy[0], new_xy[1], postionR[2]]
        return new_abs_pos_f
    else:
        return False

@wf
def break_symmetry_wf(structure, wf_para, parameterData = ParameterData(dict={})):#, _label='break_symmetry_wf', _description='WF, Introduces certain kind objects in a crystal structure, and adapts the parameter node for inpgen accordingly. All kinds of the structure will become there own species.'):
    """
    This is the workfunction of the routine break_symmetry, which
    introduces different 'kind objects' in a structure
    and names them that inpgen will make different species/atomgroups out of them.
    If nothing specified breaks ALL symmetry (i.e. every atom gets their own kind)

    params: StructureData
    params: wf_para: ParameterData which contains the keys atoms, sites, pos (see below)

    {
    params: atoms: python list of symbols, exp: ['W', 'Be']. This would make for
                   all Be and W atoms their own kinds.
    params: site: python list of integers, exp: [1, 4, 8]. This would create for
                  atom 1, 4 and 8 their own kinds.
    params: pos: python list of tuples of 3, exp [(0.0, 0.0, -1.837927), ...].
                 This will create a new kind for the atom at that position.
                 Be carefull the number given has to match EXACTLY the position
                 in the structure.
    }

    params: parameterData: AiiDa ParameterData
    return: StructureData, a AiiDA crystal structure with new kind specification.
    """
    wf_dict = wf_para.get_dict()
    atoms = wf_dict.get('atoms', ['all'])
    sites = wf_dict.get('site', [])
    pos = wf_dict.get('pos', [])
    new_kinds_names = wf_dict.get('new_kinds_names', {})
    new_structure, para_new = break_symmetry(structure, atoms=atoms, site=sites, pos=pos, new_kinds_names=new_kinds_names, parameterData = parameterData)

    return new_structure, para_new


# TODO: Bug: parameter data production not right...to many atoms list if break sym of everything
def break_symmetry(structure, atoms=['all'], site=[], pos=[], new_kinds_names={}, parameterData = None):
    """
    This routine introduces different 'kind objects' in a structure
    and names them that inpgen will make different species/atomgroups out of them.
    If nothing specified breaks ALL symmetry (i.e. every atom gets their own kind)

    params: StructureData
    params: atoms: python list of symbols, exp: ['W', 'Be']. This would make for
                   all Be and W atoms their own kinds.
    params: site: python list of integers, exp: [1, 4, 8]. This would create for
                  atom 1, 4 and 8 their own kinds.
    params: pos: python list of tuples of 3, exp [(0.0, 0.0, -1.837927), ...].
                 This will create a new kind for the atom at that position.
                 Be carefull the number given has to match EXACTLY the position
                 in the structure.

    return: StructureData, a AiiDA crystal structure with new kind specification.
    """
    # TODO proper input checks?
    from aiida.common.constants import elements as PeriodicTableElements

    _atomic_numbers = {data['symbol']: num for num,
                           data in PeriodicTableElements.iteritems()}

    #get all atoms, get the symbol of the atom
    #if wanted make individual kind for that atom
    #kind names will be atomsymbol+number
    #create new structure with new kinds and atoms
    #Param = DataFactory('parameter')
    symbol_count = {} # Counts the atom symbol occurence to set id's and kind names right
    replace = []  # all atoms symbols ('W') to be replaced
    replace_siteN = [] # all site integers to be replaced
    replace_pos = [] #all the atom positions to be replaced
    new_parameterd = None
    struc = is_structure(structure)
    if not struc:
        print 'Error, no structure given'
        # throw error?

    cell = struc.cell
    pbc = struc.pbc
    sites = struc.sites
    #natoms = len(sites)
    new_structure = DataFactory('structure')(cell=cell, pbc=pbc)

    for sym in atoms:
        replace.append(sym)
    for position in pos:
        replace_pos.append(position)
    for atom in site:
        replace_siteN.append(atom)

    if parameterData:
        para = parameterData.get_dict()
        new_parameterd = dict(para)
    else:
        new_parameterd = {}

    for i, site in enumerate(sites):
        kind_name = site.kind_name
        pos = site.position
        kind = struc.get_kind(kind_name)
        symbol = kind.symbol
        replace_kind = False

        if symbol in replace or 'all' in replace:
            replace_kind = True
        if pos in replace_pos:
            replace_kind = True
        if i in replace_siteN:
            replace_kind = True

        if replace_kind:
            if symbol in symbol_count:
                symbol_count[symbol] =  symbol_count[symbol] + 1
                symbol_new_kinds_names = new_kinds_names.get(symbol, [])
                print(symbol_new_kinds_names)
                if symbol_new_kinds_names and ((len(symbol_new_kinds_names))== symbol_count[symbol]):
                    newkindname = symbol_new_kinds_names[symbol_count[symbol]-1]
                else:
                    newkindname = '{}{}'.format(symbol, symbol_count[symbol])
            else:
                symbol_count[symbol] = 1
                symbol_new_kinds_names = new_kinds_names.get(symbol, [])
                #print(symbol_new_kinds_names)
                if symbol_new_kinds_names and ((len(symbol_new_kinds_names))== symbol_count[symbol]):
                    newkindname = symbol_new_kinds_names[symbol_count[symbol]-1]
                else:
                    newkindname = '{}{}'.format(symbol, symbol_count[symbol])
            #print(newkindname)
            new_kind = Kind(name=newkindname, symbols=symbol)
            new_structure.append_kind(new_kind)

            # now we have to add an atom list to parameterData with the corresponding id.
            if parameterData:
                id_a =  symbol_count[symbol]#'{}.{}'.format(charge, symbol_count[symbol])
                #print 'id: {}'.format(id)
                for key, val in para.iteritems():
                    if 'atom' in key:
                        if val.get('element', None) == symbol:
                            if id_a and id_a == val.get('id', None):
                                break # we assume the user is smart and provides a para node,
                                # which incooperates the symmetry breaking already
                            elif id_a:# != 1: # copy parameter of symbol and add id
                                val_new = dict(val)
                                # getting the charge over element might be risky
                                charge = _atomic_numbers.get((val.get('element')))
                                idp = '{}.{}'.format(charge, symbol_count[symbol])
                                idp = float("{0:.2f}".format(float(idp)))
                                # dot cannot be stored in AiiDA dict...
                                val_new.update({u'id' : idp})
                                atomlistname = 'atom{}'.format(id_a)
                                i = 0
                                while new_parameterd.get(atomlistname, {}):
                                    i = i+1
                                    atomlistname = 'atom{}'.format(id_a+i)

                                symbol_new_kinds_names = new_kinds_names.get(symbol, [])
                                #print(symbol_new_kinds_names)
                                if symbol_new_kinds_names and ((len(symbol_new_kinds_names))== symbol_count[symbol]):
                                     species_name = symbol_new_kinds_names[symbol_count[symbol]-1]
                                val_new.update({u'name' : species_name})

                                new_parameterd[atomlistname] = val_new
            else:
                pass
                #TODO write basic parameter data node
        else:
            newkindname = kind_name
            if not kind_name in new_structure.get_kind_names():
                new_structure.append_kind(kind)
        new_structure.append_site(Site(kind_name=newkindname, position=pos))

    #print 'natoms: {}, nkinds: {}'.format(natoms, len(new_structure.get_kind_names()))

    if parameterData:
        para_new = ParameterData(dict=new_parameterd)
    else:
        para_new = None

    new_structure.label = structure.label
    new_structure.description =  structure.description + 'more kinds, less sym'

    return new_structure, para_new



def find_equi_atoms(structure):#, sitenumber=0, position=None):
    """
    This routine uses spqlib and ASE to provide informations of all equivivalent
    atoms in the cell.

    params: AiiDA StructureData

    returns: equi_info_symbol : list of lists ['element': site_indexlist, ...]
    len(equi_info_symbol) = number of symmetryatomtypes
    returns: n_equi_info_symbol: dict {'element': numberequiatomstypes}
    """
    import spglib

    equi_info = []
    equi_info_symbol = []
    n_equi_info_symbol = {}
    k_symbols = {}

    s_ase = structure.get_ase()
    sym = spglib.get_symmetry(s_ase, symprec=1e-5)
    equi = sym['equivalent_atoms']
    unique = np.unique(equi)

    for uni in unique:
        equi_info.append(np.where(equi==uni)[0])

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
    returns the spacegorup of a given AiiDA structure
    """
    import spglib
    s_ase = structure.get_ase()
    spacegroup = spglib.get_spacegroup(s_ase, symprec=1e-5)
    return spacegroup

@wf
def move_atoms_incell_wf(structure, wf_para):#, _label='move_atoms_in_unitcell_wf', _description='WF, that moves all atoms in a unit cell by a given vector'):#Float1, Float2, Float3, test=None):
    """
    moves all atoms in a unit cell by a given vector

    para: AiiDA structure
    para: vector: tuple of 3, or array
    (currently 3 AiiDA Floats to make it a wf,
    In the future maybe a list or vector if AiiDa basetype exists)

    returns: AiiDA stucture
    """
    wf_para_dict = wf_para.get_dict()
    vector = wf_para_dict.get('vector' , [0.0, 0.0, 0.0])
    new_structure = move_atoms_incell(structure, vector)#[Float1, Float2, Float3])


    return {'moved_struc' : new_structure}

def move_atoms_incell(structure, vector):
    """
    moves all atoms in a unit cell by a given vector

    para: AiiDA structure
    para: vector: tuple of 3, or array

    returns: AiiDA stucture
    """

    StructureData = DataFactory('structure')
    new_structure = StructureData(cell=structure.cell)
    new_structure.pbc = structure.pbc
    sites = structure.sites
    for kind in structure.kinds:
        new_structure.append_kind(kind)

    for site in sites:
        pos = site.position
        new_pos = np.array(pos) + np.array(vector)
        new_site = Site(kind_name=site.kind_name, position=new_pos)
        new_structure.append_site(new_site)
        new_structure.label = structure.label

    new_structure.label = structure.label
    new_structure.description =  structure.description + 'moved'
    return new_structure


def find_primitive_cell(structure):
    """
    uses spglib find_primitive to find the primitive cell
    params: AiiDa structure data

    returns: list of new AiiDa structure data
    """
    # TODO: if refinced structure is the same as given structure
    # return the given structure (Is this good practise for prov?)
    from spglib import find_primitive
    from ase.atoms import Atoms
    symprec = 1e-7
    #print('old {}'.format(len(structure.sites)))
    ase_structure = structure.get_ase()
    lattice, scaled_positions, numbers = find_primitive(ase_structure, symprec=symprec)
    new_structure_ase = Atoms(numbers, scaled_positions=scaled_positions, cell=lattice, pbc=True)
    new_structure = StructureData(ase=new_structure_ase)
    #print('new {}'.format(len(new_structure.sites)))


    new_structure.label = structure.label + ' primitive'
    new_structure.description =  structure.description + ' primitive cell'
    return new_structure

@wf
def find_primitive_cell_wf(structure):
    """
    uses spglib find_primitive to find the primitive cell
    params: AiiDa structure data

    returns: list of new AiiDa structure data
    """

    return {'primitive_cell' : find_primitive_cell(structure)}


def find_primitive_cells(uuid_list):
    """
    uses spglib find_primitive to find the primitive cell
    params: list of structureData uuids, or pks

    returns: list of new AiiDa structure datas
    """

    new_structures = []
    for uuid in uuid_list:
        structure = load_node(uuid)
        new_structure = find_primitive_cell(structure)
        new_structures.append(new_structure)
    return new_structures

#test
#strucs = find_primitive_cells(all_be_ti_structures_uuid)

def get_all_miller_indices(structure, highestindex):
    """
    wraps the pymatgen function get_symmetrically_distinct_miller_indices for an AiiDa structure
    """
    return get_symmetrically_distinct_miller_indices(structure.get_pymatgen_structure(), highestindex)

def create_all_slabs_buggy(initial_structure, miller_index, min_slab_size_ang, min_vacuum_size=0,
                       bonds=None, tol=1e-3, max_broken_bonds=0,
                       lll_reduce=False, center_slab=False, primitive=False,
                       max_normal_search=None, symmetrize=False):#, reorient_lattice=True):
    """
    wraps the pymatgen function generate_all_slabs with some useful extras
    returns a dictionary of structures
    """
    aiida_strucs = {}
    pymat_struc = initial_structure.get_pymatgen_structure()
    # currently the pymatgen method is buggy... no coordinates in x,y....
    all_slabs = generate_all_slabs(pymat_struc, miller_index, min_slab_size_ang, min_vacuum_size,
                       bonds=bonds, tol=tol, max_broken_bonds=max_broken_bonds,
                       lll_reduce=lll_reduce, center_slab=center_slab, primitive=primitive,
                       max_normal_search=max_normal_search, symmetrize=symmetrize)#, reorient_lattice=reorient_lattice)
    for slab in all_slabs:
        print slab
        #slab2 = #slab.get_orthogonal_c_slab()
        film_struc = StructureData(pymatgen_structure=slab2)
        film_struc.pbc = (True, True, False)
        aiida_strucs[slab.miller_index] = film_struc
    return aiida_strucs

def create_all_slabs(initial_structure, miller_index, min_slab_size_ang, min_vacuum_size=0,
                       bonds=None, tol=1e-3, max_broken_bonds=0,
                       lll_reduce=False, center_slab=False, primitive=False,
                       max_normal_search=1, symmetrize=False):#, reorient_lattice=True):
    """
    returns a dictionary of structures
    """
    aiida_strucs = {}
    #pymat_struc = initial_structure.get_pymatgen_structure()
    indices = get_all_miller_indices(initial_structure, miller_index)
    for index in indices:
        slab = create_slap(initial_structure, index, min_slab_size, min_vacuum_size, min_slab_size_ang)
        film_struc = StructureData(pymatgen_structure=slab)
        film_struc.pbc = (True, True, False)
        aiida_strucs[slab.miller_index] = film_struc

    return aiida_strucs


def create_slap(initial_structure, miller_index, min_slab_size, min_vacuum_size=0, lll_reduce=False, center_slab=False, primitive=False, max_normal_search=1, reorient_lattice=True):
    """
    wraps the pymatgen slab generator
    """
    # minimum slab size is in Angstroem!!!
    pymat_struc = initial_structure.get_pymatgen_structure()
    slabg = SlabGenerator(pymat_struc, miller_index, min_slab_size, min_vacuum_size,
                          lll_reduce=lll_reduce, center_slab=center_slab, primitive=primitive,
                          max_normal_search=max_normal_search)
    slab = slabg.get_slab()
    #slab2 = slab.get_orthogonal_c_slab()
    film_struc = StructureData(pymatgen_structure=slab)
    film_struc.pbc = (True, True, False)

    # TODO: sort atoms after z-coordinate value,
    # TODO: Move all atoms that the middle atom is at [x,y,0]
    # film_struc2 = move_atoms_incell(film_struc, [0,0, z_of_middle atom])

    return film_struc

@wf
def center_film_wf(structure):
    """
    Centers a film at z=0, keeps the provenance in the database

    Args:
       structure: AiiDA structure

       returns: AiiDA structure
    """
    return center_film(structure)

def center_film(structure):
    """
    Centers a film at z=0

    Args:
       structure: AiiDA structure

       returns: AiiDA structure
    """
    # get highest and lowest z value, therefore the whole coordinate range,
    # then check if number of atoms is odd or even
    # if even move all atoms that 0 lies in the middle of the atoms in the middle
    # if odd, set the middle atom to 0.0

    sorted_struc = sort_atoms_z_value(structure)
    sites = sorted_struc.sites
    #natoms = len(sites)
    #if natoms%2: # odd
    #    shift = [0,0,-sites[natoms/2].position[2]]
    #else: #even
    #    middle = (sites[natoms/2].position[2] + sites[natoms/2 + 1].position[2])/2.0
    #    shift = [0,0, -middle]
    shift = [0,0, (sites[0].position[2]-sites[-1].position[2])/2.0]

    #print shift
    return move_atoms_incell(sorted_struc, shift)


def sort_atoms_z_value(structure):
    """
    Resorts the atoms in a structure by there Z-value

    Args:
       structure: AiiDA structure

       returns: AiiDA structure
    """
    new_structure = StructureData(cell=structure.cell)
    for kind in structure.kinds:
        new_structure.append_kind(kind)

    sites = structure.sites
    new_site_list = []
    for site in sites:
        new_site_list.append([site, site.position[2]])
    #pprint(new_site_list)
    sorted_sites = sorted(new_site_list, key=lambda position: position[1])
    #pprint(sorted_sites)
    for site in sorted_sites:
        new_structure.append_site(site[0])

    return new_structure


def estimate_mt_radii(structure, stepsize=0.05):
    """
    #TODO implement
    This method returns for every atom type (group/kind) in the structure a range of
    possible muffin tin radii (min, max).
    Or maybe just the maximal muffin tin radi (or sets of maximal muffin tin radii)

    example return for some Be-W compound
    [[{Be: 1.6, W:2.4}, {Be:1.8, W:2.2}]

    """


    # get symmetry equivalent atoms,
    # for each atom extimate muffin tin
    # check what algo fleur uses here
    # Max radius easy increase all spheres until they touch.
    # How to get the minimal muffin tin radii?
    pass

def common_mt(max_muffin_tins):
    """
    #TODO implement
    From a list of dictionary given return smallest common set.


    [[{Be: 1.7, W:2.4}, {Be:1.8, W:2.3}], [{Be : 1.75}], [{W:2.5}]
    should return [{Be:1.7, W:2.4}]
    """
    pass


def find_common_mt(structures):
    """
    #TODO implement
    From a given list of structures, estimate the muffin tin radii and return
    the smallest common set. (therefore a choice for rmt that would work for every structure given)

    """
    pass
