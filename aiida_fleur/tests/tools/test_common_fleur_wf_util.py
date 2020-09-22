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
'''Contains tests for various functions in common_fleur_wf_util.py'''
from __future__ import absolute_import
import pytest
import numpy as np


def test_convert_formula_to_formula_unit():
    from aiida_fleur.tools.common_fleur_wf_util import convert_formula_to_formula_unit

    assert convert_formula_to_formula_unit('Be4W2') == 'Be2W'


def test_get_natoms_element_Be2W():
    from aiida_fleur.tools.common_fleur_wf_util import get_natoms_element

    assert get_natoms_element('Be2W') == {'Be': 2, 'W': 1}


def test_ucell_to_atompr():
    from aiida_fleur.tools.common_fleur_wf_util import ucell_to_atompr

    correct_result = np.array([0.7947019867549668, 0.11258278145695365, 0.09271523178807947])
    correct_error = np.array([0.013571924638784224, 0.01136565320488641, 0.0018444037839109243])

    atompro, atompro_err = ucell_to_atompr([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'], element='Be')
    assert (atompro == correct_result).all()

    atompro, atompro_err = ucell_to_atompr([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'],
                                           element='Be',
                                           error_ratio=[0.1, 0.1, 0.1])
    assert (atompro == correct_result).all()
    assert (atompro_err == correct_error).all()


def test_calc_stoi():
    from aiida_fleur.tools.common_fleur_wf_util import calc_stoi

    norm_stoi, errors_stoi = calc_stoi([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'], [0.1, 0.01, 0.1])
    assert norm_stoi == {'Be': 12.583333333333334, 'Ti': 1.0}
    assert errors_stoi == {'Be': 0.12621369924887876, 'Ti': 0.0012256517540566825}

    norm_stoi, errors_stoi = calc_stoi([10, 1, 7], ['Be12Ti', 'Be17Ti2', 'Be2'])
    assert norm_stoi == {'Be': 12.583333333333334, 'Ti': 1.0}
    assert errors_stoi == {}


def test_get_atomprocent_Be24W2():
    from aiida_fleur.tools.common_fleur_wf_util import get_atomprocent
    assert get_atomprocent('Be24W2') == {'Be': 24. / 26., 'W': 2. / 26.}


#@pytest.mark.skip(reason='The function is not implemented')
#def test_get_weight_procent():
#    from aiida_fleur.tools.common_fleur_wf_util import get_weight_procent
#    pass


def test_determine_formation_energy():
    from aiida_fleur.tools.common_fleur_wf_util import determine_formation_energy

    # form energy is per atom here...
    form_en_exp = [-0.16666666666666666, 0.0]
    form_en_dict_exp = {'BeW': 0.0, 'Be2W': -0.16666666666666666}
    form_en, form_en_dict = determine_formation_energy({'Be2W': 2.5, 'BeW': 2}, {'Be': 1, 'W': 1})
    assert form_en == form_en_exp
    assert form_en_dict == form_en_dict_exp


@pytest.mark.skip(reason='Test is not implemented')
def test_determine_convex_hull():
    from aiida_fleur.tools.common_fleur_wf_util import determine_convex_hull


def test_inpgen_dict_set_mesh(generate_kpoints_mesh):
    from aiida_fleur.tools.common_fleur_wf_util import inpgen_dict_set_mesh

    inpgendict = {'test': 'test_data'}
    inpgendict_new = inpgen_dict_set_mesh(inpgendict, (1, 2, 3))
    expected_result = {'test': 'test_data', 'kpt': {'div1': 1, 'div2': 2, 'div3': 3}}
    assert inpgendict_new == expected_result

    inpgendict_new = inpgen_dict_set_mesh(inpgendict, generate_kpoints_mesh(3).get_kpoints_mesh())
    expected_result = {'test': 'test_data', 'kpt': {'div1': 3, 'div2': 3, 'div3': 3}}
    assert inpgendict_new == expected_result


def test_powerset():
    from aiida_fleur.tools.common_fleur_wf_util import powerset

    res = [(), ('Be',), ('W',), ('Be2W',), ('Be', 'W'), ('Be', 'Be2W'), ('W', 'Be2W'), ('Be', 'W', 'Be2W')]
    length = len(res)
    assert powerset([1, 2, 3]) == [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]
    assert powerset(['Be', 'W', 'Be2W']) == res
    assert length == 8


def test_determine_reactions():
    from aiida_fleur.tools.common_fleur_wf_util import determine_reactions

    res = [
        '1*Be12W->1*Be12W', '1*Be12W->1*Be2W+10*Be', '2*Be12W->1*Be2W+1*Be22W', '1*Be12W->12*Be+1*W',
        '11*Be12W->5*W+6*Be22W'
    ]
    n_equations = len(res)

    assert determine_reactions('Be12W', ['Be12W', 'Be2W', 'Be', 'W', 'Be22W']) == res
    assert n_equations == 5


def test_convert_eq_to_dict():
    from aiida_fleur.tools.common_fleur_wf_util import convert_eq_to_dict

    res_dict = {'products': {'Be': 15, 'Be2Ti': 1}, 'educts': {'Be12Ti': 1}}
    assert convert_eq_to_dict('1*Be12Ti->10*Be+1*Be2Ti+5*Be') == res_dict


@pytest.mark.skip(reason='Test is not implemented')
def test_get_enhalpy_of_equation():
    from aiida_fleur.tools.common_fleur_wf_util import get_enhalpy_of_equation


@pytest.mark.parametrize('test_input,expected', [('C7H16+O2 -> CO2+H2O', '1*C7H16+11*O2 ->7* CO2+8*H2O'),
                                                 ('Be12W->Be2W+W+Be', None), ('Be12WO->Be2WO+W+Be+O2', None),
                                                 ('Be12W->Be22W+Be12W', None), ('Be12W->Be12W', '1*Be12W->1*Be12W')])
def test_balance_equation(test_input, expected):
    from aiida_fleur.tools.common_fleur_wf_util import balance_equation
    assert balance_equation(test_input) == expected


@pytest.mark.skip(reason='Test is not implemented')
def test_check_eos_energies():
    from aiida_fleur.tools.common_fleur_wf_util import check_eos_energies
