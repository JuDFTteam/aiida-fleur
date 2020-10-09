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
''' Contains tests for the FleurRelaxWorkChain. '''
from __future__ import absolute_import
from __future__ import print_function

import pytest
import aiida_fleur
import os
from aiida.engine import run_get_node
from aiida_fleur.workflows.relax import FleurRelaxWorkChain

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurRelaxWorkChain():
    """
    Regression tests for the FleurRelaxWorkChain
    """

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_relax_fleurinp_Si_bulk(self, run_with_cache, mock_code_factory, create_fleurinp):
        """
        full example using FleurRelaxWorkChain with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        from aiida.orm import Code, load_node, Dict, StructureData
        from numpy import array

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
        builder = FleurRelaxWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur relax test for Si bulk with fleurinp data given'
        builder.metadata.label = 'Fleurrelax_test_Si_bulk'
        builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH)
        builder.options = Dict(dict=options)
        builder.fleur = FleurCode

        # now run calculation
        out, node = run_with_cache(builder)

        # check output

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_relax_structure_Si(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurRelaxWorkChain starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_relax_structure_Si_film(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurRelaxWorkChain starting with a fleurinp data of a film structure
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_relax_continue_converged(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurRelaxWorkChain starting from an already converged relaxed structure
        """
        assert False

    @pytest.mark.timeout(500, method='thread')
    def test_fleur_relax_validation_wrong_inputs(self, run_with_cache, mock_code_factory, generate_structure2):
        """
        Test the validation behavior of FleurRelaxWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        from aiida.orm import Dict

        # prepare input nodes and dicts
        options = {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            },
            'max_wallclock_seconds': 5 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }
        options = Dict(dict=options).store()

        FleurCode = mock_code_factory(
            label='fleur',
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'),
            entry_point=CALC_ENTRY_POINT,
            ignore_files=['cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??'])
        InpgenCode = mock_code_factory(label='inpgen',
                                       data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                     'calc_data_dir/'),
                                       entry_point=CALC2_ENTRY_POINT,
                                       ignore_files=['_aiidasubmit.sh', 'FleurInputSchema.xsd'])

        wf_parameters = Dict(dict={
            'relax_iter': 5,
            'film_distance_relaxation': False,
            'force_criterion': 0.001,
            'wrong_key': None
        })
        wf_parameters.store()
        structure = generate_structure2()
        structure.store()

        ################
        # Create builders
        # interface of exposed scf is tested elsewhere

        # 1. create builder with wrong wf parameters
        builder_additionalkeys = FleurRelaxWorkChain.get_builder()
        builder_additionalkeys.scf.structure = structure
        builder_additionalkeys.wf_parameters = wf_parameters
        builder_additionalkeys.scf.fleur = FleurCode
        builder_additionalkeys.scf.inpgen = InpgenCode

        ###################
        # now run the builders all should fail early with exit codes

        # 1. structure and fleurinp given
        out, node = run_get_node(builder_additionalkeys)
        assert out == {}
        assert node.is_finished
        assert not node.is_finished_ok
        assert node.exit_status == 230


# maybe validate common interface of code acknostic worklfows and builders, to make sure it can take
# the protocol.
