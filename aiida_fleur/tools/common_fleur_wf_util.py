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
"""
In here we put all things (methods) that are common to workflows AND DO NOT
depend on AiiDA classes, therefore can be used without loading the dbenv.
Util that does depend on AiiDA classes should go somewhere else.
"""

from __future__ import absolute_import
from __future__ import print_function
from math import gcd
import six

from sympy import Symbol


def convert_formula_to_formula_unit(formula):
    """
    Converts a formula to the smallest chemical formula unit
    'Be4W2' -> 'Be2W'
    """

    # get formula dict
    # find greatest common divider of values
    # form formula unit string
    element_count_dict = get_natoms_element(formula)
    nelements = list(element_count_dict.values())
    g = int(nelements[0])
    for a2 in nelements:
        a2 = int(a2)
        g = gcd(g, a2)

    formula_unit_string = ''
    for key, val in six.iteritems(element_count_dict):
        new_val = int(val / g)
        if new_val == 1:
            new_val = ''
        formula_unit_string = formula_unit_string + '{}{}'.format(key, new_val)

    return formula_unit_string


def get_natoms_element(formula):
    """
    Converts 'Be24W2' to {'Be': 24, 'W' : 2}, also BeW to {'Be' : 1, 'W' : 1}
    """

    import re
    elem_count_dict = {}
    elements = re.findall('[A-Z][^A-Z]*', formula)
    #re.split('(\D+)', formula)

    for i, elm in enumerate(elements):
        elem_count = re.findall(r'\D+|\d+\.\d+|\d+', elm)
        #print(elem_count)
        if len(elem_count) == 1:
            elem_count_dict[elem_count[0]] = 1
        else:
            elem_count_dict[elem_count[0]] = float(elem_count[1])

    return elem_count_dict


# test
#get_natoms_element('BeW')
#get_natoms_element('Be2W')


def convert_frac_formula(formula, max_digits=3):
    """
    Converts a formula with fractions to a formula with integer factors only

    Be0.5W0.5 -> BeW

    :param formula: str, crystal formula i.e. Be2W, Be0.2W0.7
    :param max_digits: int default=3, number of digits after which fractions will be cut off
    :returns: string
    """
    form_dict = get_natoms_element(formula)
    formula_int = ''
    for key, val in form_dict.items():
        formula_int = formula_int + key + str(int(val * 10**max_digits))

    return convert_formula_to_formula_unit(formula_int)


#test
#convert_frac_formula('Be0.3W0.7') -> Be3W7
#convert_frac_formula('Be0.5W0.5') -> BeW
#convert_frac_formula('Be3W7') -> Be3W7


def ucell_to_atompr(ratio, formulas, element, error_ratio=None):
    """
    Converts unit cell ratios into atom ratios.

    len(ratio) == len(formulas) (== len(error_ratio))
    ucell_to_atompr([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'], element='Be', [0.1, 0.1, 0.1])
    """
    import numpy as np

    if error_ratio is None:
        error_ratio = []

    atompro = []
    atompro_err = []
    if len(ratio) != len(formulas):
        return

    n_atoms_formula = []
    for formula in formulas:
        res = get_natoms_element(formula)
        n_atoms_formula.append(res.get(element, 0))

    atompro = np.array(ratio) * np.array(n_atoms_formula)
    total = sum(atompro)
    atompro = atompro / total

    if len(error_ratio):
        atompro_err_t = np.array(error_ratio) * np.array(n_atoms_formula)
        e_sum = np.sqrt(sum(atompro_err_t**2))
        atompro_err = 1 / total * (np.sqrt(atompro_err_t**2 + (atompro * e_sum)**2))

    return atompro, atompro_err


def calc_stoi(unitcellratios, formulas, error_ratio=None):
    """
    Calculate the Stoichiometry with errors from a given unit cell ratio, formulas.

    Example:
    calc_stoi([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'], [0.1, 0.01, 0.1])
    ({'Be': 12.583333333333334, 'Ti': 1.0}, {'Be': 0.12621369924887876, 'Ti': 0.0012256517540566825})
    calc_stoi([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'])
    ({'Be': 12.583333333333334, 'Ti': 1.0}, {})
    """
    import numpy as np

    if error_ratio is None:
        error_ratio = []

    stoi = {}
    if len(unitcellratios) != len(formulas):
        return

    errors_stoi = {}
    for i, formula in enumerate(formulas):
        res = get_natoms_element(formula)
        for element, val in six.iteritems(res):
            stoi_elm = stoi.get(element, 0)
            stoi[element] = stoi_elm + val * unitcellratios[i]
            if len(error_ratio):
                errors = errors_stoi.get(element, 0)
                errors_stoi[element] = errors + val * val * error_ratio[i] * error_ratio[i]

    # make smallest number always one.
    vals = list(stoi.values())
    minv = min(vals)
    keymin = list(stoi.keys())[vals.index(minv)]
    norm_stoi = {}
    for key, val in six.iteritems(stoi):
        norm_stoi[key] = stoi[key] / minv
        if len(error_ratio):
            errors_stoi[key] = 1 / stoi[keymin] * np.sqrt(
                (errors_stoi[key]**2 + (stoi[key] / stoi[keymin] * errors_stoi[keymin])**2))
    return norm_stoi, errors_stoi


def get_atomprocent(formula):
    """
    This converts a formula to a dictionary with element : atomprocent
    example converts 'Be24W2' to {'Be': 24/26, 'W' : 2/26}, also BeW to {'Be' : 0.5, 'W' : 0.5}
    :params: formula: string
    :returns: a dict, element : atomprocent

    # Todo alternative with structuredata
    """
    form_dict_new = {}
    form_dict = get_natoms_element(formula)
    ntotal = sum(form_dict.values())
    for key, val in six.iteritems(form_dict):
        val_new = float(val) / ntotal
        form_dict_new[key] = val_new
    return form_dict_new


# test
'''
def get_weight_procent(formula):
    """
    This converts a formula to a dictionary with element : weightprocent
    example converts 'Be24W2' to {'Be': , 'W' : }, also BeW to {'Be' : , 'W' : }
    :params: formula: string
    :returns: a dict, element : weightprocent

    # Todo alternative with structuredata
    """

    pass
'''

#def norm_total_energy_peratom(totalenergy, formula)
#def norm_total_energy_perunitcell(totalenergy, )


def determine_formation_energy(struc_te_dict, ref_struc_te_dict):
    """
    This method determines the formation energy.
    E_form =  E(A_xB_y) - x*E(A) - y*E(B)

    :params struc_te_dict: python dictionary in the form of {'formula' : total_energy} for the compound(s)
    :params ref_struc_te_dict: python dictionary in the form of {'formula' : total_energy per atom, or per unit cell} for the elements
                               (if the formula of the elements contains a number the total energy is divided by that number)
    :returns: list of floats, dict {formula : eform, ..} units energy/per atom, energies have some unit as energies given
    """
    #eform_list = []
    eform_dict = {}
    #ref_el = ref_struc_te_dict.keys()
    ref_struc_te_dict_norm = ref_struc_te_dict  #{}
    # assume reference to be normalized

    # normalize reference
    #for key, val in ref_struc_te_dict.iteritems():
    ##    elem_n = get_natoms_element(key)
    #    ref_struc_te_dict_norm[elem_n.keys()[0]] = val / elem_n.values()[0]
    ref_el_norm = list(ref_struc_te_dict_norm.keys())

    for formula, tE in six.iteritems(struc_te_dict):
        elements_count = get_natoms_element(formula)
        ntotal = float(sum(elements_count.values()))
        print(ntotal)
        eform = tE  #abs(tE)
        for elem, count in six.iteritems(elements_count):
            if elem in ref_el_norm:
                eform = eform - count * ref_struc_te_dict_norm.get(elem)  #abs(ref_struc_te_dict.get(elem))
            else:
                print(('Reference energy missing for element {}. '
                       'You need to provide reference energies for all elements in you compound.'
                       ''.format(elem)))
        eform_dict[formula] = eform / ntotal
        #eform_list.append(eform/ntotal)
    return list(eform_dict.values()), eform_dict


# test
#determine_formation_energy({'BeW' : 2, 'Be2W' : 2.5}, {'Be' : 1, 'W' : 1})


def determine_convex_hull(formation_en_grid):
    """
    Wraps the pyhull packge implementing the qhull algo for our purposes.
    For now only for 2D phase diagrams
    Adds the points [1.0, 0.0] and [0.0, 1.0], because in material science these
    are always there.

    :params: formation_en_grid: list of points in phase space [[x, formation_energy]]
    :returns: a hul datatype
    """
    import numpy as np
    #from scipy.spatial import ConvexHull # Buggy in python 3... some ugly segfault
    from pyhull.convex_hull import ConvexHull

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


def powerset(L):
    """
    Constructs the power set, 'potenz Menge' of a given list.

    return list: of all possible subsets
    """
    import itertools
    pset = []
    for n in range(len(L) + 1):
        for sset in itertools.combinations(L, n):
            pset.append(sset)
    return pset


#a = powerset([1, 2, 3, 4])
#a = powerset(['Be', 'Be2W', 'Be12W', 'Be22W', 'W'])
#print(a)
#print(len(a))


def determine_reactions(formula, available_data):
    """
    Determines and balances theoretical possible reaction.
    Stoichiometry 'Be12W', [Be12W, Be2W, Be, W, Be22W] -> [[Be22W+Be2W], [Be12W], [Be12+W],...]

    :params formula: string, given educts (left side of equation)
    :params available_data: list of strings of compounds (products),
                            from which all possibilities will be constructed
    """

    # 1. for each compound try to balance equation
    # 2. for each compound with any other compound in list, try to balance equation
    # 3. for each compound with each two other compounds ... till other compounds
    reactions = []
    constructed_products = []
    pset_available_data = powerset(available_data)  # if len available_data to large cut off?
    for i, dataset in enumerate(pset_available_data):
        productstring = ''
        if len(dataset) < 1:
            continue
        for entry in dataset:
            productstring = productstring + '{}+'.format(entry)

        productstring = productstring[:-1]
        constructed_products.append(productstring)
        pos_reaction = '{}->{}'.format(formula, productstring)
        bal_reaction = balance_equation(pos_reaction, allow_negativ=False, allow_zero=False, eval_linear=True)
        # We do not allow zero coefficients of products, because the resulting equation should already be in our list.
        if bal_reaction:
            # TODO post process (i.e are remove 0 compounds)
            reactions.append(bal_reaction)
        else:
            continue
    return reactions


# test
# reac = determine_reactions('Be12W', ['Be12W', 'Be2W', 'Be', 'W', 'Be22W'])
#print(reac ['1*Be12W->1*Be12W', '1*Be12W->1*Be2W+10*Be', '2*Be12W->1*Be2W+1*Be22W',
#             '1*Be12W->12*Be+1*W', '11*Be12W->5*W+6*Be22W'])
#reac = determine_reactions('Be12Ti', ['Be12Ti', 'Be17Ti2', 'BeTi', 'Ti', 'Be', 'Be2Ti', 'Be8Ti4'])
#print(reac ['1*Be12Ti->1*Be12Ti', '2*Be12Ti->1*Be17Ti2+7*Be', '1*Be12Ti->1*BeTi+11*Be',
#             '1*Be12Ti->1*Ti+12*Be', '1*Be12Ti->10*Be+1*Be2Ti', '4*Be12Ti->40*Be+1*Be8Ti4'])


def convert_eq_to_dict(equationstring):
    """
    Converts an equation string to a dictionary
    convert_eq_to_dict('1*Be12Ti->10*Be+1*Be2Ti+5*Be') ->
    {'products': {'Be': 15, 'Be2Ti': 1}, 'educts': {'Be12Ti': 1}}
    """
    eq_dict = {'products': {}, 'educts': {}}
    product_dict = {}
    educt_dict = {}

    eq_split = equationstring.split('->')
    products = eq_split[1].split('+')
    educts = eq_split[0].split('+')

    for product in products:
        p_list = product.split('*')
        product_dict[p_list[-1]] = int(p_list[0]) + product_dict.get(p_list[-1], 0)
    for educt in educts:
        e_list = educt.split('*')
        educt_dict[e_list[-1]] = int(e_list[0]) + educt_dict.get(e_list[-1], 0)

    eq_dict['products'] = product_dict
    eq_dict['educts'] = educt_dict
    return eq_dict


# test convert_eq_to_dict('1*Be12Ti->10*Be+1*Be2Ti+5*Be')
# {'products': {'Be': 15, 'Be2Ti': 1}, 'educts': {'Be12Ti': 1}}


def get_enhalpy_of_equation(reaction, formenergydict):
    """
    calculate the enthalpy per atom of a given reaction from the given data.

    param reaction: string
    param fromenergydict: dictionary that contains the {compound: formationenergy per atom}

    # TODO check if physics is right
    """
    reac_dict = convert_eq_to_dict(reaction)
    educt_energy = 0
    product_energy = 0

    for compound, factor in six.iteritems(reac_dict.get('educts', {})):
        compound_e = 0
        try:
            compound_e = formenergydict.get(compound, 0)
        except KeyError:
            print(('Formation energy of compound {} not given in {}.' 'I abort...'.format(compound, formenergydict)))
            compound_e = 0
            # can be that educt side is not a real 'compound' but just a stoichiometry
            # so we give it 0
            #return None
        educt_energy = educt_energy + factor * compound_e

    for compound, factor in six.iteritems(reac_dict.get('products', {})):
        try:
            compound_e = formenergydict.get(compound)
        except KeyError:
            print(('Formation energy of compound {} not given in {}.' 'I abort...'.format(compound, formenergydict)))
            compound_e = 0
            return None
        product_energy = product_energy + factor * compound_e

    return educt_energy - product_energy


def balance_equation(equation_string, allow_negativ=False, allow_zero=False, eval_linear=True):
    """
    Method that balances a chemical equation.

    param equation_string: string (with '->')
    param allow_negativ: bool, default False, allows for negative coefficients for the products.

    return string: balanced equation

    balance_equation("C7H16+O2 -> CO2+H2O"))
    balance_equation("Be12W->Be22W+Be12W")
    balance_equation("Be12W->Be12W")

    have to be intergers everywhere in the equation, factors and formulas

    1*C7H16+11*O2 ->7* CO2+8*H2O
    None
    1*Be12W->1*Be12W
    #TODO The solver better then what we need. Currently if system is over
    #"Be12W->Be2W+W+Be" solves to {a: 24, b: -d/2 + 144, c: d/2 - 120}-> FAIL-> None
    # The code fails in the later stage, but this solution should maybe be used.

    code adapted from stack exchange (the messy part):
    https://codegolf.stackexchange.com/questions/8728/balance-chemical-equations
    """
    import sys
    import re
    from sympy.solvers import solve
    from sympy.core.numbers import Rational, Integer
    from collections import defaultdict
    letters = 'abcdefghijklmnopqrstuvwxyz'
    Ls = list(letters)
    eq = equation_string
    Ss, Os, Es, a, i = defaultdict(list), Ls[:], [], 1, 1
    for p in eq.split('->'):
        for k in p.split('+'):
            c = [Ls.pop(0), 1]
            for e, m in re.findall('([A-Z][a-z]?)([0-9]*)', k):
                m = 1 if m == '' else int(m)
                a *= m
                d = [c[0], c[1] * m * i]
                Ss[e][:0], Es[:0] = [d], [[e, d]]
        i = -1
    Ys = {}  # dict((s, eval('Symbol("' + s + '")')) for s in Os if s not in Ls)
    for s in Os:
        if s not in Ls:
            Ys[s] = Symbol(str(s))
    #a = '+'.join('%d*%s' % (c[1], c[0]) for c in Ss[s])
    #print(a)
    Qs = [
        eval(  # pylint: disable=eval-used
            '+'.join('%d*%s' % (c[1], c[0]) for c in Ss[s]), {}, Ys) for s in Ss
    ] + [Ys['a'] - a]
    # FIXME
    #Qs = []
    #for s in Ss:
    #   res1 = ''
    #   for c in s:
    #       prod = '%d*%s' % (c[1], c[0])
    #       res1 = res1 + '+' + prod
    #   Qs.append(res1)
    #Qs + [Ys['a'] - a]

    k = solve(Qs, *Ys)
    if k:  # if a solution is found multiply by gcd
        # TODO? check if solution has linear dependence: and evaluate
        #for c in k.values():
        #    for char in list(letters):
        #        if char in str(c):
        #             pass
        N = []  #[k[Ys[s]]for s in sorted(Ys)]
        rescale_N = False
        denom_list = []
        for s in sorted(Ys):
            n = k[Ys[s]]
            # idea: check if char in n, then linear depended, then
            try:  # since solver gives also a linear depended solution if correct, but code fails then
                if n < 0 and not allow_negativ:  # We allow for 0 but might be an other case to think about
                    return None
            except TypeError:
                return None  # TODO Maybe other return value... maybe list of some values for
                # linear dependencies, d,e,....? also choose them that the value is positive...?
            if n == 0 and not allow_zero:
                return None
            N.append(n)

            # Rationals are a problem in gcd, so we have to get rid of them
            if isinstance(n, Rational):
                rescale_N = True
                denom_list.append(n.as_numer_denom()[1])
        if rescale_N:
            multiplier = 1
            for denom in denom_list:
                multiplier = multiplier * int(denom)
            N = [int(n * multiplier) for n in N]
        g = N[0]
        for a1, a2 in zip(N[0::2], N[0::2]):
            g = gcd(g, a2)
        N = [int(i / g) for i in N]
        pM = lambda c: str(c) + '*'  # if c!=1 else ''
        res = '->'.join('+'.join(pM(N.pop(0)) + str(t) for t in p.split('+')) for p in eq.split('->'))
        return res
    else:
        return None


def check_eos_energies(energylist):
    """
    Checks if there is an abnormality in the total energies from the Equation of states.
    i.e. if one point has a larger energy then its two neighbors

    :param energylist: list of floats
    :returns nnormalies: integer
    """
    # TODO: possible improvements look at all differences, and introduce a threshold
    # Also look at several points...
    abnormalityindexlist = []
    abnormality = False
    i = 0
    for x, y, z in zip(energylist, energylist[1:], energylist[2:]):
        i = i + 1
        if x < y > z:
            abnormality = True
            abnormalityindexlist.append(i)
            print((x, y, z))
            print('annormly detected')

    return abnormality, abnormalityindexlist
