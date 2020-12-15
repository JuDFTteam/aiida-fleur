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
'''Contains tests merge_parameters.'''
import pytest
from aiida import orm

PARAMETERS1 = {
    'atom': {
        'element': 'Si',
        'rmt': 2.1,
        'jri': 981,
        'lmax': 12,
        'lnonsph': 6
    },  #'econfig': '[He] 2s2 2p6 | 3s2 3p2', 'lo': ''},
    'comp': {
        'kmax': 5.0,
    },
    'kpt': {
        'div1': 17,
        'tkb': 0.0005
    }
}
PARAMETERS2 = {
    'atom1': {
        'element': 'Si',
        'id': 16.1,
        'rmt': 2.1,
        'jri': 981,
        'lmax': 12,
        'lnonsph': 6
    },  #'econfig': '[He] 2s2 2p6 | 3s2 3p2', 'lo': ''},
    'atom2': {
        'element': 'Si',
        'z': 16,
        'id': 16.4,
        'rmt': 2.1,
        'jri': 981,
        'lmax': 12,
        'lnonsph': 6
    },
    'comp': {
        'kmax': 5.0,
    }
}
PARAMETERS3 = PARAMETERS1.copy()
PARAMETERS3['atom']['element'] = 'Fe'


def test_merge_parameter():
    """Test if merge_parameter merges atom keys in dicts right
    """
    from aiida_fleur.tools.merge_parameter import merge_parameter
    from aiida.common.exceptions import InputValidationError

    dict1 = orm.Dict(dict=PARAMETERS1).store()
    dict2 = orm.Dict(dict=PARAMETERS2).store()
    dict3 = orm.Dict(dict=PARAMETERS3).store()
    # otherwise we we can still change the dicts and therefore the PARAMETERS

    result = merge_parameter(dict2, dict2)
    assert isinstance(result, orm.Dict)
    assert result.get_dict() == PARAMETERS2

    res_exp = {
        'kpt': {
            'tkb': 0.0005,
            'div1': 17
        },
        'comp': {
            'kmax': 5.0
        },
        'atom0': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        },
        'atom1': {
            'id': 16.1,
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Si',
            'lnonsph': 6
        },
        'atom2': {
            'z': 16,
            'id': 16.4,
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Si',
            'lnonsph': 6
        }
    }

    result1 = merge_parameter(dict1, dict2)
    assert isinstance(result1, orm.Dict)
    assert result1.get_dict() == res_exp

    res_exp = {
        'kpt': {
            'tkb': 0.0005,
            'div1': 17
        },
        'atom': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        },
        'comp': {
            'kmax': 5.0
        }
    }
    result2 = merge_parameter(dict1, dict3)
    assert isinstance(result2, orm.Dict)
    assert result2.get_dict() == res_exp

    # wrong input
    with pytest.raises(InputValidationError):
        merge_parameter(dict2, 'string')
    with pytest.raises(InputValidationError):
        merge_parameter(123123, dict2)


def test_merge_parameters():
    """Test if merge_parameters works for a given set
    """
    from aiida_fleur.tools.merge_parameter import merge_parameters

    dict1 = orm.Dict(dict=PARAMETERS1).store()
    dict2 = orm.Dict(dict=PARAMETERS2).store()
    dict3 = orm.Dict(dict=PARAMETERS3).store()

    # overwrite seems broken...
    res_exp = {
        'kpt': {
            'tkb': 0.0005,
            'div1': 17
        },
        'comp': {
            'kmax': 5.0
        },
        'atom0': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        },
        'atom1': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        }
    }
    result1 = merge_parameters([dict1, dict1], overwrite=False)
    assert isinstance(result1, orm.Dict)
    assert result1.get_dict() == res_exp

    res_exp = {
        'kpt': {
            'tkb': 0.0005,
            'div1': 17
        },
        'comp': {
            'kmax': 5.0
        },
        'atom0': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        },
        'atom1': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        }
    }
    result2 = merge_parameters([dict1, dict1], overwrite=True)
    assert isinstance(result2, orm.Dict)
    assert result2.get_dict() == res_exp

    res_exp = {
        'kpt': {
            'tkb': 0.0005,
            'div1': 17
        },
        'comp': {
            'kmax': 5.0
        },
        'atom0': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        },
        'atom1': {
            'id': 16.1,
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Si',
            'lnonsph': 6
        },
        'atom2': {
            'z': 16,
            'id': 16.4,
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Si',
            'lnonsph': 6
        },
        'atom3': {
            'jri': 981,
            'rmt': 2.1,
            'lmax': 12,
            'element': 'Fe',
            'lnonsph': 6
        }
    }
    result3 = merge_parameters([dict1, dict2, dict3])
    assert isinstance(result3, orm.Dict)
    assert result3.get_dict() == res_exp


def test_merge_parameter_cf():
    """Test calcfunction of merge_parameter
    """
    from aiida_fleur.tools.merge_parameter import merge_parameter_cf

    dict1 = orm.Dict(dict=PARAMETERS1)

    result = merge_parameter_cf(dict1, dict1)
    assert isinstance(result, orm.Dict)
    assert result.get_dict() == PARAMETERS1
    assert result.is_stored
