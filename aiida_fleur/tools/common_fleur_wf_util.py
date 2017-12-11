#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In here we put all things (methods) that are common to workflows AND DO NOT
depend on AiiDA classes, therefore can be used without loading the dbenv.
Util that does depend on AiiDA classes should go somewhere else. 
"""

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


def get_natoms_element(formula):
    """
    Converts 'Be24W2' to {'Be': 24, 'W' : 2}, also BeW to {'Be' : 1, 'W' : 1}
    """

    import re
    elem_count_dict = {}
    elements = re.findall('[A-Z][^A-Z]*', formula)
    #re.split('(\D+)', formula)

    for i, elm in enumerate(elements):
        elem_count = re.findall('\d+|\D+', elm)
        #print(elem_count)
        if len(elem_count) == 1:
            elem_count_dict[elem_count[0]] = 1
        else:
            elem_count_dict[elem_count[0]] = float(elem_count[1])


    return elem_count_dict

# test
#get_natoms_element('BeW')
#get_natoms_element('Be2W')

def get_atomprocent(formula):
    """
    This converts a formula to a dictionary with elemnt : atomprocent
    example converts 'Be24W2' to {'Be': 24/26, 'W' : 2/26}, also BeW to {'Be' : 0.5, 'W' : 0.5}
    :params: formula: string
    :returns: a dict, element : atomprocent

    # Todo alternative with structuredata
    """
    form_dict_new = {}
    form_dict = get_natoms_element(formula)
    ntotal = sum(form_dict.values())
    for key, val in form_dict.iteritems():
        val_new = float(val)/ntotal
        form_dict_new[key] = val_new
    return form_dict_new

# test

def get_weight_procent(formula):
    """
    This converts a formula to a dictionary with elemnt : weightprocent
    example converts 'Be24W2' to {'Be': , 'W' : }, also BeW to {'Be' : , 'W' : }
    :params: formula: string
    :returns: a dict, element : weightprocent

    # Todo alternative with structuredata
    """

    pass


def determine_formation_energy(struc_te_dict, ref_struc_te_dict):
    """
    This method determines the formation energy.
    E_form =  E(A_xB_y) - x*E(A) - y*E(B)

    :inputs: struc_te_dict: python dictionary in the form of {'formula' : total_energy} for the compound(s)
    :inputs: ref_struc_te_dict: python dictionary in the form of {'formula' : total_energy per atom} for the elements
    (if the formula of the elements contains a number the total energy is devided by that number)
    :returns: list of floats, dict {formula : eform, ..} units energy/per atom, energies have some unit as energies given
    """
    eform_list = []
    eform_dict = {}
    #ref_el = ref_struc_te_dict.keys()
    ref_struc_te_dict_norm = {}
    # normalize reference
    for key, val in ref_struc_te_dict.iteritems():
        elem_n = get_natoms_element(key)
        ref_struc_te_dict_norm[elem_n.keys()[0]] = val / elem_n.values()[0]
    ref_el_norm = ref_struc_te_dict_norm.keys()

    for formula, tE in struc_te_dict.iteritems():
        elements_count = get_natoms_element(formula)
        ntotal = float(sum(elements_count.values()))
        eform = tE#abs(tE)
        for elem, count in elements_count.iteritems():
            if elem in ref_el_norm:
                eform = eform - count * ref_struc_te_dict_norm.get(elem)#abs(ref_struc_te_dict.get(elem))
            else:
                print('Reference energy missing for element {}. '
                      'You need to provide reference energies for all elements in you compound.'
                       ''.format(elem))
        eform_dict[formula] = eform/ntotal
        eform_list.append(eform/ntotal)
    return eform_list, eform_dict

# test
#determine_formation_energy({'BeW' : 2, 'Be2W' : 2.5}, {'Be' : 1, 'W' : 1})

def determine_convex_hull(formation_en_grid):
    """
    Wraps the scipy.spatial ConvexHull algo for our purposes.
    For now only for 2D phase diagrams
    Adds the points [1.0, 0.0] and [0.0, 1.0], because in material science these
    are always there.

    :params: formation_en_grid: list of points in phase space [[x, formation_energy]]
    :returns: a hul datatype
    """
    import numpy as np
    from scipy.spatial import ConvexHull

    # TODO multi d
    # check if endpoints are in
    if [1.0, 0.0] not in formation_en_grid:
        formation_en_grid.append([1.0, 0.0])
    if [0.0, 0.0] not in formation_en_grid:
        formation_en_grid.append([0.0, 0.0])

    points = np.array(formation_en_grid)
    hull = ConvexHull(points)

    return hull


def inpgen_dict_set_mesh(inpgendict, mesh):
    """
    params: python dict, used for inpgen parameterdata node
    params: mesh either as returned by kpointsdata or tuple of 3 integers

    returns: python dict, used for inpgen parameterdata node
    """
    if len(mesh) == 2:
        kmesh = mesh[0]
    elif len(mesh) == 3:
        kmesh = mesh
    kpt_dict = inpgendict.get('kpt', {})
    kpt_dict['div1'] = kmesh[0]
    kpt_dict['div2'] = kmesh[1]
    kpt_dict['div3'] = kmesh[2]

    inpgendict_new = inpgendict
    inpgendict_new['kpt'] = kpt_dict

    return inpgendict_new

# test
#inpgen_dict_set_mesh(Be_para.get_dict(), mesh)
