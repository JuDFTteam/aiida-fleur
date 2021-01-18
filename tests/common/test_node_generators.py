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
'''
Module to test all common node_generators


import pytest
from aiida_fleur.common.node_generators import generate_option_dict, generate_option_node
from aiida_fleur.common.node_generators import generate_wf_para_dict, generate_wf_para_node

ALL_ENTRYPOINTS_CALCS = ['fleur.fleur', 'fleur.inpgen']
ALL_ENTRYPOINTS_WC = ['fleur.base', 'fleur.scf', 'fleur.relax', 'fleur.base_relax', 'fleur.eos',
    'fleur.corehole', 'fleur.init_cls', 'fleur.banddos', 'fleur.mae', 'fleur.dmi', 'fleur.ssdisp',
    'fleur.create_magnetic']

def test_generate_option_dict_defaults_wc(entrypoint):
    """Tests if the generate_option_dict function can get all the default options from the workchains

    i.e this also tests if all fleur workchains have defined some _default_option
    """
    default_dict = generate_option_dict(wf_entry_point=entrypoint)
    assert isinstance(default_dict, dict)

def test_generate_option_node_interface():
    """

    """
    pass

@pytest.mark.parametrize('entrypoint', ALL_ENTRYPOINTS_WC)
def test_generate_wf_para_dict_defaults_wc(entrypoint):
    """Tests if the generate_option_dict function can get all the default options from the workchains

    i.e this also tests if all fleur workchains have defined some _default_option
    """
    default_dict = generate_wf_para_dict(wf_entry_point=entrypoint)
    assert isinstance(default_dict, dict)
'''
