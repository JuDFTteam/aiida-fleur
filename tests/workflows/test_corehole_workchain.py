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
'''Contains tests for the FleurCoreholeWorkChain'''

import pytest
import aiida_fleur
import os
from aiida.orm import Code, load_node, Dict, StructureData
from aiida_fleur.workflows.corehole import FleurCoreholeWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.workflows.scf import FleurScfWorkChain


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurCoreholeWorkChain():
    """
    Regression tests for the FleurCoreholeWorkChain
    """

    @pytest.mark.regression_test
    @pytest.mark.timeout(5000, method='thread')
    def test_fleur_corehole_W(self, with_export_cache, inpgen_local_code, fleur_local_code, generate_structure_W,
                              show_workchain_summary):
        """
        full example using FleurCoreholeWorkChain on W.
        Several fleur runs needed, calculation of all only certain coreholes
        """
        from aiida.engine import run_get_node
        options = Dict(
            {
                'resources': {
                    'num_machines': 1,
                    'num_mpiprocs_per_machine': 1
                },
                'max_wallclock_seconds': 60 * 60,
                'queue_name': '',
                'withmpi': False,
            })
        #'withmpi': False, 'custom_scheduler_commands': ''}
        options.store()

        parameters = Dict(
            {
                'atom': {
                    'element': 'W',
                    'jri': 833,
                    'rmt': 2.3,
                    'dx': 0.015,
                    'lmax': 8,
                    'lo': '5p',
                    'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
                },
                'comp': {
                    'kmax': 3.0,
                },
                'kpt': {
                    'nkpt': 100,
                }
            })
        parameters.store()

        #structure = generate_structure_W()
        # W bcc structure
        bohr_a_0 = 0.52917721092  # A
        a = 3.013812049196 * bohr_a_0
        cell = [[-a, a, a], [a, -a, a], [a, a, -a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='W')

        structure.store()
        wf_para = Dict(
            {
                'method': 'valence',
                'hole_charge': 0.5,
                'atoms': ['all'],
                'corelevel': ['W,4f', 'W,4p'],  #['W,all'],#
                'supercell_size': [2, 1, 1],
                'magnetic': True
            })

        FleurCode = fleur_local_code
        InpgenCode = inpgen_local_code

        # create process builder to set parameters
        inputs = {
            #'metadata' : {
            #    'description' : 'Simple FleurCoreholeWorkChain test with W bulk',
            #    'label' : 'FleurCoreholeWorkChain_test_W_bulk'},
            'options': options,
            'fleur': FleurCode,
            'inpgen': InpgenCode,
            'wf_parameters': wf_para,
            'calc_parameters': parameters,
            'structure': structure
        }

        # now run calculation
        #out, node = run_with_cache(inputs, process_class=FleurCoreholeWorkChain)
        with with_export_cache('fleur_corehole_W.tar.gz'):
            out, node = run_get_node(FleurCoreholeWorkChain, **inputs)

        # check general run
        if not node.is_finished_ok:
            show_workchain_summary(node)
        assert node.is_finished_ok

        # check output
        # corelevel shift should be zero
        outn = out.get('output_corehole_wc_para', None)
        assert outn is not None
        outd = outn.get_dict()
        from pprint import pprint
        pprint(outd)

        assert outd.get('successful')
        assert outd.get('warnings') == []

        #Note Henning: The values were replaced when updating to MaX6 previous
        #[470.54883993999, 402.52235778002, 32.112260220107, 29.829247920075]
        assert outd.get('weighted_binding_energy') == [
            470.54492447991, 402.51844969997, 32.108438199852, 29.825437580002
        ]

        #previous: [235.27441997, 201.26117889001, 16.056130110053, 14.914623960038]
        assert outd.get('binding_energy') == [235.27246223995, 201.25922484999, 16.054219099926, 14.912718790001]

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_corehole_structure_Si_one(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurCoreholeWorkChain starting with a crystal structure and parameters,
        one corehole
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_corehole_structure_Si_all(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurCoreholeWorkChain starting from a structure, calculating all possible
        coreholes
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_corehole_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of FleurCoreholeWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
