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
''' Contains tests for the FleurBandDosWorkChain '''
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
class Test_BandDosWorkChain():
    """
    Regression tests for the FleurBandDosWorkChain
    """

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_band_converged_Si(self, run_with_cache, mock_code_factory, create_remote_fleur):
        """
        full example using the band dos workchain with just a fleurinp data as input.
        Calls scf, Several fleur runs needed till convergence
        """
        from aiida.orm import Code, load_node, Dict, StructureData
        from numpy import array
        from aiida_fleur.workflows.banddos import FleurBandDosWorkChain

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
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir_calcs/'),
            entry_point=CALC_ENTRY_POINT,
            ignore_files=['_aiidasubmit.sh', 'cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??'])
        # create process builder to set parameters
        builder = FleurBandDosWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur Band Dos calculation ontop converged fleur calc'
        builder.metadata.label = 'FleurBandDos_test'
        #builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH)
        builder.remote = create_remote_fleur()
        builder.options = Dict(dict=options)
        builder.fleur = FleurCode

        # now run calculation
        out, node = run_with_cache(builder)

        # check output
        # check if BandDos file was parsed. success and all output nodes there.

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_band_fleurinp_Si(self, run_with_cache, mock_code_factory, create_fleurinp):
        """
        full example using the band dos workchain with just a fleurinp data as input.
        Calls scf, Several fleur runs needed till convergence
        """

        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_band_structure_Si(self, run_with_cache, mock_code_factory):
        """
        Full regression test of the band dos workchain starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_band_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of band dos workchain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False

    # needed?

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_band_seekpath(self, run_with_cache, mock_code_factory):
        """
        Tests if the band dos workchain is capable of running without a specified path
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_band_no_seekpath(self, run_with_cache, mock_code_factory):
        """
        Tests if the band dos workchain is capable of running with a specified path
        """
        assert False
