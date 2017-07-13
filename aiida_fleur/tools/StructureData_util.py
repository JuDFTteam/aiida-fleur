#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collection of utility routines dealing with StructureData objects
"""
#TODO move imports to workfuncitons namespace?
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from ase import *
from ase.lattice.surface import *
from ase.io import *
from aiida.orm import DataFactory
from aiida.orm import load_node
from aiida.orm.data.structure import Site, Kind

from aiida.work.workfunction import workfunction as wf

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
def supercell(inp_structure, n_a1, n_a2, n_a3):# be carefull you have to use AiiDA datatypes...
    """
    Creates a super cell from a StructureData node.
    Keeps the provanance in the database.

    :param StructureData, a StructureData node (pk, or uuid)
    :param scale: tuple of 3 AiiDA integers, number of cells in a1, a2, a3, or if cart =True in x,y,z

    :returns StructureData, Node with supercell
    """
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
    return new_structure


#wf
#prob don't make this a workfuntion, because rescale is already one and scalelist would has to be a ParameterData Node, since AiiDA has no list-datatype


#### Structure util
# after ths is in plugin code import these in fleurinp.
def abs_to_rel(vector, cell):
    """
    Converts a position vector in absolut coordinates to relative coordinates.
    """
    import numpy as np

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
    import numpy as np
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
    import numpy as np
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
    import numpy as np
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



def break_symmetry(structure, atoms=['all'], site=[], pos=[], parameterData = None):
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

    #get all atoms, get the symbol of the atom
    #if wanted make individual kind for that atom
    #kind names will be atomsymbol+number
    #create new structure with new kinds and atoms

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
                newkindname = '{}{}'.format(symbol, symbol_count[symbol])
            else:
                symbol_count[symbol] = 1
                newkindname = '{}{}'.format(symbol, symbol_count[symbol])
            new_kind = Kind(name=newkindname, symbols=symbol)
            new_structure.append_kind(new_kind)

            # now we have to add an atom list to parameterData with the corresponding id.
            if parameterData:
                id = symbol_count[symbol]
                #print 'id: {}'.format(id)
                for key, val in para.iteritems():
                    if 'atom' in key:
                        if val.get('element', None) == symbol:
                            if id and id == val.get('id', None):
                                break # we assume the user is smart and provides a para node,
                                # which incooperates the symmetry breaking already
                            elif id:# != 1: # copy parameter of symbol and add id
                                val_new = dict(val)
                                val_new.update({u'id' : id})
                                atomlistname = 'atom{}'.format(id)
                                i = 0
                                while new_parameterd.get(atomlistname, {}):
                                    i = i+1
                                    atomlistname = 'atom{}'.format(id+i)
                                new_parameterd[atomlistname] = val_new
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
    import numpy as np
    
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