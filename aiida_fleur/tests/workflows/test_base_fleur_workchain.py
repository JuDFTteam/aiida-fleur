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
'''Contains tests for the FleurBaseWorkChain'''
# Here we test if the interfaces of the workflows are still the same
from __future__ import absolute_import
from __future__ import print_function

import pytest
import aiida_fleur
import os

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurBaseWorkChain():
    """
    Regression tests for the FleurBaseWorkChain
    """

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_fleurinp_Si(self, run_with_cache, mock_code_factory, create_fleurinp):
        """
        full example using FleurBaseWorkChain with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        from aiida.orm import Code, load_node, Dict, StructureData
        from numpy import array
        from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain

        options = {
            'resources': {
                'num_machines': 1
            },
            'max_wallclock_seconds': 5 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }

        FleurCode = mock_code = mock_code_factory(
            label='fleur',
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir/'),
            entry_point=CALC_ENTRY_POINT,
            ignore_files=['_aiidasubmit.sh', 'cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??'])
        # create process builder to set parameters
        builder = FleurBaseWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given'
        builder.metadata.label = 'FleurSCF_test_Si_bulk'
        builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH)
        builder.options = Dict(dict=options)
        builder.fleur = FleurCode

        # now run calculation
        out, node = run_with_cache(builder)

        # check output

        #assert abs(n.get('starting_fermi_energy') - 0.409241) < 10**-14

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_structure_Si(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurBaseWorkChain starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_continue_from_x(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurBaseWorkChain while encountering x, handling it and restart
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of FleurBaseWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
