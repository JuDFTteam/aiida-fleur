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
''' Contains tests for the FleurInitialCLSWorkChain. '''

import pytest
import aiida_fleur
from pathlib import Path
import os
from aiida.orm import load_node
from aiida.engine import run_get_node
from aiida_fleur.workflows.initial_cls import FleurInitialCLSWorkChain

# tests


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurInitialCLSWorkChain():
    """
    Regression tests for the FleurInitialCLSWorkChain
    """

    @pytest.mark.regression_test
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_initial_cls_W(self, with_export_cache, inpgen_local_code, fleur_local_code, generate_structure_W,
                                 load_cache):
        """
        full example using FleurInitialCLSWorkChain with just elemental W as input
        (W, onw atoms per unit cell)
        uses the same structure as reference.
        """
        from aiida.orm import Dict

        options = {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            },
            'max_wallclock_seconds': 5 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }

        # Since we parse uuid in input caching does not work if we recreate the nodes so we have to
        # import them
        '''
        parameters = Dict(dict={
                  'atom':{
                        'element' : 'W',
                        'jri' : 833,
                        'rmt' : 2.3,
                        'dx' : 0.015,
                        'lmax' : 8,
                        'lo' : '5p',
                        'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
                        },
                  'comp': {
                        'kmax': 3.0,
                        },
                  'kpt': {
                        'nkpt': 100,
                        }}).store()

        structure = generate_structure_W().store()
        export_cache([structure, parameters], 'W_structure_para.tar.gz')
        '''
        basepath = Path(aiida_fleur.__file__).parent
        load_cache(basepath / '../tests/data_dir/W_structure_para.tar.gz')

        #print(structure.uuid, structure.pk)
        #print(parameters.uuid, parameters.pk)
        structure = load_node('6c7addb7-f688-4afd-8492-7c64861efd70')
        parameters = load_node('b5275b1a-bff7-4cdc-8efc-36c5ddd67f28')

        wf_para = Dict({'references': {'W': [structure.uuid, parameters.uuid]}})

        FleurCode = fleur_local_code
        InpgenCode = inpgen_local_code

        # create process builder to set parameters
        inputs = {
            'metadata': {
                'description': 'Simple FleurInitialCLSWorkChain test with W bulk',
                'label': 'FleurInitialCLSWorkChain test_W_bulk'
            },
            'options': Dict(options),
            'fleur': FleurCode,
            'inpgen': InpgenCode,
            'wf_parameters': wf_para,
            'calc_parameters': parameters,
            'structure': structure
        }

        with with_export_cache('fleur_initial_cls_W.tar.gz'):
            # now run calculation
            out, node = run_get_node(FleurInitialCLSWorkChain, **inputs)

        # check general run
        assert node.is_finished_ok

        # check output
        # corelevel shift should be zero
        outn = out.get('output_initial_cls_wc_para', None)
        assert outn is not None
        outd = outn.get_dict()

        assert outd.get('successful')
        assert outd.get('warnings') == []
        assert outd.get('corelevelshifts') == {
            'W': [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
        }

        assert outd.get('formation_energy') == [0.0]

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_initial_cls_wc_binary_with_given_ref(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurInitialCLSWorkChain starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_initial_cls_wc_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of FleurInitialCLSWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
