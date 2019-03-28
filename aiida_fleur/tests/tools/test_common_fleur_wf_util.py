from __future__ import absolute_import
import pytest

# get_natoms_element
def test_get_natoms_element_Be2W():
    from aiida_fleur.tools.common_fleur_wf_util import get_natoms_element
    
    assert get_natoms_element('Be2W') == {'Be' : 2, 'W' : 1}

# get_atomprocent
def test_get_atomprocent_Be24W2():
    from aiida_fleur.tools.common_fleur_wf_util import get_atomprocent
    assert get_atomprocent('Be24W2') == {'Be': 24./26., 'W' : 2./26.}


#TODO
# get_weight_procent
def test_get_weight_procent():
    from aiida_fleur.tools.common_fleur_wf_util import get_weight_procent
    pass

# determine_formation_energy
def test_determine_formation_energy():
    from aiida_fleur.tools.common_fleur_wf_util import determine_formation_energy
    
    # form energy is per atom here...
    form_en_exp = [-0.16666666666666666, 0.0]
    form_en_dict_exp = {'BeW' : 0.0, 'Be2W': -0.16666666666666666}
    form_en, form_en_dict = determine_formation_energy({'Be2W' : 2.5, 'BeW' : 2}, {'Be' : 1, 'W' : 1})
    assert form_en == form_en_exp
    assert form_en_dict == form_en_dict_exp


# inpgen_dict_set_mesh
def test_inpgen_dict_set_mesh():
    from aiida_fleur.tools.common_fleur_wf_util import inpgen_dict_set_mesh
    pass

#inpgen_dict_set_mesh(Be_para.get_dict(), mesh)

# powerset
def test_powerset():
    from aiida_fleur.tools.common_fleur_wf_util import powerset
    
    res = [(), ('Be',), ('W',), ('Be2W',), ('Be', 'W'), ('Be', 'Be2W'), ('W', 'Be2W'), ('Be', 'W', 'Be2W')]
    length = len(res)
    assert powerset([1, 2, 3]) == [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]
    assert powerset(['Be', 'W', 'Be2W']) == res
    assert length == 8

# determine_reactions
def test_determine_reactions():
    from aiida_fleur.tools.common_fleur_wf_util import determine_reactions

    res = ['1*Be12W->1*Be12W', '1*Be12W->1*Be2W+10*Be',
           '2*Be12W->1*Be2W+1*Be22W', '1*Be12W->12*Be+1*W',
           '11*Be12W->5*W+6*Be22W']
    n_equations = len(res)

    assert determine_reactions('Be12W', ['Be12W', 'Be2W', 'Be', 'W', 'Be22W']) == res
    assert n_equations == 5

# convert_eq_to_dict
def test_convert_eq_to_dict():
    from aiida_fleur.tools.common_fleur_wf_util import convert_eq_to_dict
    
    res_dict = {'products': {'Be': 15, 'Be2Ti': 1}, 'educts': {'Be12Ti': 1}}
    assert convert_eq_to_dict('1*Be12Ti->10*Be+1*Be2Ti+5*Be') == res_dict


# get_enhalpy_of_equation
def test_get_enhalpy_of_equation():
    from aiida_fleur.tools.common_fleur_wf_util import get_enhalpy_of_equation
    pass    

# balance_equation
def test_balance_equation():
    from aiida_fleur.tools.common_fleur_wf_util import balance_equation
    pass

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


