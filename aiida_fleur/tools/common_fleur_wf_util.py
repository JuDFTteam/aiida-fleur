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

def powerset(L):
    """
    Constructs the power set, 'potenz Menge' of a given list.
    
    return list: of all possible subsets
    """
    import itertools
    pset = []
    for n in xrange(len(L) + 1):
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
    
    Stoichiometry
    'Be12W', [Be12W, Be2W, Be, W, Be22W] -> [[Be22W+Be2W], [Be12W], [Be12+W],...]
    """
    
    # 1. for each compound try to balance equation
    # 2. for each compound with any other compound in list, try to balance equation
    # 3. for each compound with each two other compounds ... till other compounds
    reactions = []
    constructed_products = []
    pset_available_data = powerset(available_data) # if len available_data to large cut off?
    for i,dataset in enumerate(pset_available_data):
        productstring = ''
        if len(dataset) <1:
            continue
        for entry in dataset:
            productstring = productstring + '{}+'.format(entry)
        
        productstring = productstring[:-1]
        #print productstring
        constructed_products.append(productstring)
        pos_reaction = '{}->{}'.format(formula, productstring)
        bal_reaction = balance_equation(pos_reaction, allow_negativ=False, allow_zero=False, eval_linear=True)
        # We do not allow zero coefficents of products, because the resulting equation should already be in our list.
        if bal_reaction:
            # TODO post process (i.e are remove 0 compounds)
            reactions.append(bal_reaction)
        else:
            continue
    return reactions
    
# test reac = determine_reactions('Be12W', ['Be12W', 'Be2W', 'Be', 'W', 'Be22W'])
#print reac ['1*Be12W->1*Be12W', '1*Be12W->1*Be2W+10*Be', '2*Be12W->1*Be2W+1*Be22W', '1*Be12W->12*Be+1*W', '11*Be12W->5*W+6*Be22W']
    
#reac = determine_reactions('Be12Ti', ['Be12Ti', 'Be17Ti2', 'BeTi', 'Ti', 'Be', 'Be2Ti', 'Be8Ti4'])
#print reac ['1*Be12Ti->1*Be12Ti', '2*Be12Ti->1*Be17Ti2+7*Be', '1*Be12Ti->1*BeTi+11*Be', '1*Be12Ti->1*Ti+12*Be', '1*Be12Ti->10*Be+1*Be2Ti', '4*Be12Ti->40*Be+1*Be8Ti4']
    
    
def convert_eq_to_dict(equationstring):
    """
    Converts an equation string to a dictionary
    convert_eq_to_dict('1*Be12Ti->10*Be+1*Be2Ti+5*Be') -> {'products': {'Be': 15, 'Be2Ti': 1}, 'educts': {'Be12Ti': 1}}
    """
    eq_dict = {'products': {}, 'educts' : {}}
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
    #print eq_dict
    return eq_dict
    
# test convert_eq_to_dict('1*Be12Ti->10*Be+1*Be2Ti+5*Be')
 # {'products': {'Be': 15, 'Be2Ti': 1}, 'educts': {'Be12Ti': 1}}   
    
    
def get_enhalpy_of_equation(reaction, formenergydict):
    """
    calculate the enhalpy per atom of a given reaction from the given data.
    
    param reaction: string
    param fromenergydict: dictionary that contains the {compound: formationenergy per atom}
    
    # TODO check if physics is right
    """
    reac_dict = convert_eq_to_dict(reaction)
    educt_energy = 0
    product_energy = 0
    
    for compound, factor in reac_dict.get('educts', {}).iteritems():
        compound_e = 0
        try:
            compound_e = formenergydict.get(compound)
        except KeyError:
            print('Formation energy of compound {} not given in {}.'
                  'I abort...'.format(compound, formenergydict))
            compound_e = 0            
            return None
        educt_energy = educt_energy + factor*compound_e

    for compound, factor in reac_dict.get('products', {}).iteritems():
        try:
            compound_e = formenergydict.get(compound)
        except KeyError:
            print('Formation energy of compound {} not given in {}.'
                  'I abort...'.format(compound, formenergydict))
            compound_e = 0            
            return None
        product_energy = product_energy + factor*compound_e        
        
    
    return educt_energy - product_energy
    
from sympy import Symbol #somehow, otherwise it in not found in balance equation...

def balance_equation(equation_string, allow_negativ=False, allow_zero=False, eval_linear=True):
    """
    Method that balances a chemical equation.
    
    param equation_string: string (with '->')
    param allow_negativ: bool, default False, allows for negative coefficents for the products.
    
    return string: balanced equation 
    
    balance_equation("C7H16+O2 -> CO2+H2O"))
    balance_equation("Be12W->Be22W+Be12W")
    balance_equation("Be12W->Be12W")
    
    1*C7H16+11*O2 ->7* CO2+8*H2O
    None
    1*Be12W->1*Be12W
    #TODO The solver better then what we need. Currently if system is over 
    #"Be12W->Be2W+W+Be" solves to {a: 24, b: -d/2 + 144, c: d/2 - 120}-> FAIL-> None
    # The code fails in the later stage, but this solution should maybe be used.
    
    code adapted from stack exchange (the messy part): 
    https://codegolf.stackexchange.com/questions/8728/balance-chemical-equations
    """

    import sys,re
    from sympy.solvers import solve
    from fractions import gcd
    from collections import defaultdict
    letters = 'abcdefghijklmnopqrstuvwxyz'
    Ls=list(letters)
    eq=equation_string
    Ss,Os,Es,a,i = defaultdict(list),Ls[:],[],1,1
    for p in eq.split('->'):
        for k in p.split('+'):
            c = [Ls.pop(0), 1]
            for e,m in re.findall('([A-Z][a-z]?)([0-9]*)',k):
                m=1 if m=='' else int(m)
                a*=m
                d=[c[0],c[1]*m*i]
                Ss[e][:0],Es[:0]=[d],[[e,d]]
        i=-1
    Ys=dict((s,eval('Symbol("'+s+'")')) for s in Os if s not in Ls)
    Qs=[eval('+'.join('%d*%s'%(c[1],c[0]) for c in Ss[s]),{},Ys) for s in Ss]+[Ys['a']-a]
    k=solve(Qs,*Ys)
    if k:# if a solution is found multiply by gcd
        # TODO? check if solution has linear dependence: and evaluate
        #for c in k.values():
        #    print str(c)
        #    for char in list(letters):
        #        if char in str(c):
        #            print 'here'
        N=[]#[k[Ys[s]]for s in sorted(Ys)]
        for s in sorted(Ys):
            n = k[Ys[s]]
            #print n
            # idea: check if char in n, then linear depended, then 
            try: # since solver gives also a linear depended solution if correct, but code fails then
                if n<0 and not allow_negativ: # We allow for 0 but might be an other case to think about
                    return None    
            except TypeError:
                return None # TODO Maybe other return value... maybe list of some values for 
                # linear dependencies, d,e,....? also choose them that the value is positive...?
            if n==0 and not allow_zero:
                return None
            N.append(n)
        #print N
        g=N[0]
        for a1, a2 in zip(N[0::2],N[0::2]):
            g=gcd(g,a2)
        N=[i/g for i in N]
        pM=lambda c: str(c)+'*'# if c!=1 else ''
        return '->'.join('+'.join(pM(N.pop(0))+str(t) for t in p.split('+')) for p in eq.split('->'))
    else:
        return None
        
        
# test
#print(balance_equation("C7H16+O2 -> CO2+H2O"))
#print balance_equation("Be12W->Be2W+W+Be")#+Be12W+Be+Be22W")
#print balance_equation("Be12WO->Be2WO+W+Be+O2")#+Be12W+Be+Be22W")
#print balance_equation("Be12W->Be22W+Be12W")
#print balance_equation("Be12W->Be12W")

#1*C7H16+11*O2 ->7* CO2+8*H2O
#None
#None
#None
#1*Be12W->1*Be12W