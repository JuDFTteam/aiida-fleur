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
''' Various tests for the FleurMaeWorkChain. '''
from __future__ import absolute_import
from __future__ import print_function

import pytest
import aiida_fleur
import os
from aiida.engine import run_get_node
from aiida_fleur.workflows.mae import FleurMaeWorkChain


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurMaeWorkChain:
    """
    Regression tests for the FleurEosWorkChain
    """

    @pytest.mark.skip(reason='aiida-testing buggy, todo check, aiida-fleur fixture')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_mae_FePt_film(self, run_with_cache, fleur_local_code, inpgen_local_code):
        """
        full example using mae workflow with FePt film structure as input.
        """
        from aiida.orm import Code, load_node, Dict, StructureData

        options = Dict(
            dict={
                'resources': {
                    'num_machines': 1,
                    'num_mpiprocs_per_machine': 1
                },
                'max_wallclock_seconds': 60 * 60,
                'queue_name': '',
                'custom_scheduler_commands': ''
            })

        wf_para_scf = {
            'fleur_runmax': 2,
            'itmax_per_run': 120,
            'density_converged': 0.4,
            'serial': False,
            'mode': 'density'
        }

        wf_para_scf = Dict(dict=wf_para_scf)

        wf_para = Dict(
            dict={
                'sqa_ref': [0.7, 0.7],
                'use_soc_ref': False,
                'sqas_theta': [0.0, 1.57079, 1.57079],
                'sqas_phi': [0.0, 0.0, 1.57079],
                'serial': False,
                'soc_off': [],
                'inpxml_changes': [],
            })

        bohr_a_0 = 0.52917721092  # A
        a = 7.497 * bohr_a_0
        cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0.0, 0.0, -1.99285 * bohr_a_0), symbols='Fe', name='Fe123')
        structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
        structure.append_atom(position=(0., 0., 2.65059 * bohr_a_0), symbols='Pt')
        structure.pbc = (True, True, False)

        parameters = Dict(
            dict={
                'atom': {
                    'element': 'Pt',
                    'lmax': 6
                },
                'atom2': {
                    'element': 'Fe',
                    'lmax': 6,
                },
                'comp': {
                    'kmax': 3.2,
                },
                'kpt': {
                    'div1': 8,  #20,
                    'div2': 12,  #24,
                    'div3': 1
                }
            })

        FleurCode = fleur_local_code
        InpgenCode = inpgen_local_code

        inputs = {
            'scf': {
                'wf_parameters': wf_para_scf,
                'structure': structure,
                'calc_parameters': parameters,
                'options': options,
                'inpgen': InpgenCode,
                'fleur': FleurCode
            },
            'wf_parameters': wf_para,
            'fleur': FleurCode,
            'options': options
        }

        # now run calculation
        out, node = run_with_cache(inputs, process_class=FleurMaeWorkChain)

        print(out)
        print(node)

        assert node.is_finished_ok

        outpara = out.get('out', None)
        assert outpara is not None
        outpara = outpara.get_dict()
        print(outpara)

        # check output
        assert outpara.get('warnings') == []
        assert outpara.get('phi') == [0.0, 0.0, 1.57079]
        assert outpara.get('theta') == [0.1, 1.57079, 1.57079]
        assert outpara.get('is_it_force_theorem')
        assert outpara.get('maes') == [0.0039456509729923, 0.0026014085035566, 0.0]

    @pytest.mark.skip
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_mae_validation_wrong_inputs(self, fleur_local_code, inpgen_local_code):
        """
        Test the validation behavior of FleurMaeWorkChain if wrong input is provided it should throw
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
            'custom_scheduler_commands': ''
        }
        options = Dict(dict=options).store()

        FleurCode = fleur_local_code
        InpgenCode = inpgen_local_code

        ################
        # Create builders
        # interface of exposed scf is tested elsewhere

        #spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM',
        #               message="Invalid workchain parameters.")
        #spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG',
        #               message="Invalid input configuration.")
        #spec.exit_code(233, 'ERROR_INVALID_CODE_PROVIDED',
        #               message="Invalid code node specified, check inpgen and fleur code nodes.")

        # 1. create inputs with wrong wf parameters
        inputs1 = {}

        # 2. create inputs with wrong code
        # 3. create inputs with invalid input config

        ###################
        # now run the builders all should fail early with exit codes

        # 1. structure and fleurinp given
        out, node = run_get_node(FleurMaeWorkChain, **inputs1)
        assert out == {}
        assert node.is_finished
        assert not node.is_finished_ok
        assert node.exit_status == 230
