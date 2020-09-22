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
''' Contains tests for the fleur_initial_cls_wc. '''

from __future__ import absolute_import
from __future__ import print_function

import pytest
import aiida_fleur
import os
from aiida.orm import load_node
from aiida.engine import run_get_node
from aiida_fleur.workflows.initial_cls import fleur_initial_cls_wc


# tests
@pytest.mark.skip
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_fleur_initial_cls_wc():
    """
    Regression tests for the fleur_initial_cls_wc
    """

    @pytest.mark.timeout(500, method='thread')
    def test_fleur_initial_cls_W(self, run_with_cache, inpgen_local_code, fleur_local_code, generate_structure_W,
                                 export_cache, load_cache, clear_spec):
        """
        full example using fleur_initial_cls_wc with just elemental W as input
        (W, onw atoms per unit cell)
        uses the same structure as reference.
        """
        from aiida.orm import Code, Dict, StructureData

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
        load_cache('data_dir/W_structure_para.tar.gz')

        #print(structure.uuid, structure.pk)
        #print(parameters.uuid, parameters.pk)
        structure = load_node('6c7addb7-f688-4afd-8492-7c64861efd70')
        parameters = load_node('b5275b1a-bff7-4cdc-8efc-36c5ddd67f28')

        wf_para = Dict(dict={'references': {'W': [structure.uuid, parameters.uuid]}})

        FleurCode = fleur_local_code
        InpgenCode = inpgen_local_code

        # create process builder to set parameters
        inputs = {
            'metadata': {
                'description': 'Simple fleur_initial_cls_wc test with W bulk',
                'label': 'fleur_initial_cls_wc_test_W_bulk'
            },
            'options': Dict(dict=options),
            'fleur': FleurCode,
            'inpgen': InpgenCode,
            'wf_parameters': wf_para,
            'calc_parameters': parameters,
            'structure': structure
        }

        # now run calculation
        out, node = run_with_cache(inputs, process_class=fleur_initial_cls_wc)

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
        Full regression test of fleur_initial_cls_wc starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_initial_cls_wc_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of fleur_initial_cls_wc if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
