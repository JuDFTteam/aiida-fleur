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
'''Contains tests for the functions in create_kpoints_from_distance'''
import pytest
from aiida_fleur.tools.create_kpoints_from_distance import create_kpoints_from_distance_parameter
from aiida.orm import Dict


def test_create_kpoints_from_distance_no_para(generate_structure):
    """Test mesh generation of create_kpoints_from_distance_parameter without calc_parameter input"""

    wanted_result = {'kpt': {'div1': 22, 'div2': 22, 'div3': 22}}
    structure = generate_structure()
    cf_para = Dict({'distance': 0.1, 'force_parity': True, 'force_even': True})
    result_para = create_kpoints_from_distance_parameter(structure, cf_para, calc_parameters=None)

    assert result_para.get_dict() == wanted_result


def test_create_kpoints_from_distance_gamma(generate_structure):
    """Test mesh generation of create_kpoints_from_distance_parameter without calc_parameter input"""

    wanted_result = {'kpt': {'div1': 23, 'div2': 23, 'div3': 23, 'gamma': True}}
    structure = generate_structure()
    cf_para = Dict({'distance': 0.1, 'force_parity': True, 'force_odd': True, 'include_gamma': True})
    result_para = create_kpoints_from_distance_parameter(structure, cf_para, calc_parameters=None)

    assert result_para.get_dict() == wanted_result


def test_create_kpoints_from_distance_with_para(generate_structure):
    """Test mesh generation of create_kpoints_from_distance_parameter with calc_parameter input"""

    wanted_result = {
        'atom0': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
            'gmaxxc': 12.5,
            'gmax': 15.0
        },
        'kpt': {
            'div1': 23,
            'div2': 23,
            'div3': 23,
            'tkb': 0.0005
        }
    }
    structure = generate_structure()

    cf_para = Dict({'distance': 0.1, 'force_parity': True, 'force_odd': True})

    parameters = Dict({
        'atom': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0,
            'gmaxxc': 12.5,
            'gmax': 15.0
        },
        'kpt': {
            'div1': 17,
            'div2': 17,
            'div3': 17,
            'tkb': 0.0005
        }
    })

    result_para = create_kpoints_from_distance_parameter(structure, cf_para, calc_parameters=parameters)
    assert result_para.get_dict() == wanted_result
