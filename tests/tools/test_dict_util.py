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
''' Contains tests for routines in dict_util '''
from __future__ import absolute_import
import pytest

inputs = [({
    'a1': {
        'b1': [1]
    }
}, {
    'a1': {
        'b1': [2, 3]
    }
}), ({
    'a1': {
        'b2': 1.0
    }
}, {
    'a1': {
        'b2': 1
    }
}), ({
    'a1': {
        'b3': 'a'
    }
}, {
    'a1': {
        'b3': 'b'
    },
    'a2': [1]
}), ({
    'a1': {
        'b3': 'b'
    },
    'a2': [1]
}, {}), ({}, {
    'a1': {
        'b3': 'b'
    },
    'a2': [1]
})]

outputs = [{
    'a1': {
        'b1': [1, 2, 3]
    }
}, {
    'a1': {
        'b2': 2
    }
}, {
    'a1': {
        'b3': 'ab'
    },
    'a2': [1]
}, {
    'a1': {
        'b3': 'b'
    },
    'a2': [1]
}, {
    'a1': {
        'b3': 'b'
    },
    'a2': [1]
}]


@pytest.mark.parametrize('test_input,expected', zip(inputs, outputs))
def test_dict_merger_interface_dicts_lists_str_int(test_input, expected):
    from aiida_fleur.tools.dict_util import dict_merger
    assert dict_merger(*test_input) == expected


# extract_elementpara
def test_extract_elementpara_interface_W():
    from aiida_fleur.tools.dict_util import extract_elementpara

    para_dict = {'a': 1, 'atom': {'element': 'H', 'rmt': 1}, 'atom1': {'element': 'W', 'rmt': 4}}
    assert extract_elementpara(para_dict, 'W') == {'a': 1, 'atom1': {'element': 'W', 'rmt': 4}}
