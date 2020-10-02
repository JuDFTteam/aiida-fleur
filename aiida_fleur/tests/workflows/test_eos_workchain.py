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
''' Contains test for the eos workchain, short, interface and regression '''
from __future__ import absolute_import
from __future__ import print_function

import pytest
import aiida_fleur
import os
from aiida.engine import run_get_node
from aiida_fleur.workflows.eos import FleurEosWorkChain

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


# tests
@pytest.mark.skip
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurEosWorkChain:
    """
    Regression tests for the FleurEosWorkChain
    """

    @pytest.mark.timeout(500, method='thread')
    def test_fleur_eos_structure_Si(self, run_with_cache, fleur_local_code, inpgen_local_code, generate_structure2,
                                    clear_spec):
        """
        full example using scf workflow with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        from aiida.orm import Code, load_node, Dict, StructureData

        options = {
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            },
            'max_wallclock_seconds': 10 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }
        wf_param = {'points': 7, 'step': 0.002, 'guess': 1.00}

        calc_parameters = {
            'atom': {
                'element': 'Si',
                'rmt': 2.1,
                'jri': 981,
                'lmax': 8,
                'lnonsph': 6
            },
            'comp': {
                'kmax': 3.4
            },
            'kpt': {
                'div1': 10,
                'div2': 10,
                'div3': 10,
                'tkb': 0.0005
            }
        }

        # Fe fcc structure
        bohr_a_0 = 0.52917721092  # A
        a = 3.4100000000 * 2**(0.5)
        cell = [[a, 0, 0], [0, a, 0], [0, 0, a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='Fe', name='Fe1')
        structure.append_atom(position=(0.5 * a, 0.5 * a, 0.0 * a), symbols='Fe', name='Fe2')
        structure.append_atom(position=(0.5 * a, 0.0 * a, 0.5 * a), symbols='Fe', name='Fe31')
        structure.append_atom(position=(0.0 * a, 0.5 * a, 0.5 * a), symbols='Fe', name='Fe43')
        calc_parameters = {
            'comp': {
                'kmax': 3.4,
            },
            'atom': {
                'element': 'Fe',
                'bmu': 2.5,
                'rmt': 2.15
            },
            'kpt': {
                'div1': 4,
                'div2': 4,
                'div3': 4
            }
        }

        wf_para_scf = {
            'fleur_runmax': 2,
            'itmax_per_run': 120,
            'density_converged': 0.2,
            'serial': True,
            'mode': 'density'
        }

        FleurCode = fleur_local_code
        InpgenCode = inpgen_local_code

        # create process builder to set parameters
        builder = FleurEosWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur FleurEosWorkChain test for Si bulk'
        builder.metadata.label = 'FleurEosWorkChain_test_Si_bulk'
        builder.structure = structure.store()  #generate_structure2().store()
        builder.wf_parameters = Dict(dict=wf_param).store()
        builder.scf = {
            'fleur': FleurCode,
            'inpgen': InpgenCode,
            'options': Dict(dict=options).store(),
            'wf_parameters': Dict(dict=wf_para_scf).store(),
            'calc_parameters': Dict(dict=calc_parameters).store()
        }
        print(builder)
        # now run calculation
        out, node = run_with_cache(builder)

        print(out)
        print(node)

        outpara = out.get('output_eos_wc_para', None)
        assert outpara is not None
        outpara = outpara.get_dict()
        print(outpara)

        outstruc = out.get('output_eos_wc_structure', None)
        assert outstruc is not None

        assert node.is_finished_ok

        # check output
        #distance, bulk modulus, optimal structure, opt scaling
        assert abs(outpara.get('scaling_gs') - 0.99268546558578) < 10**14
        assert outpara.get('warnings') == ['Groundstate volume was not in the scaling range.']
        assert outpara.get('info') == ['Consider rerunning around point 0.9926854655857787']

    @pytest.mark.timeout(500, method='thread')
    def test_fleur_eos_validation_wrong_inputs(self, run_with_cache, mock_code_factory, generate_structure2):
        """
        Test the validation behavior of FleurEosWorkChain if wrong input is provided it should throw
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

        wf_parameters = Dict(dict={'points': 9, 'step': 0.002, 'guess': 1.00, 'wrong_key': None})
        wf_parameters.store()
        structure = generate_structure2()
        structure.store()

        ################
        # Create builders
        # interface of exposed scf is tested elsewhere

        # 1. create builder with wrong wf parameters
        builder_additionalkeys = FleurEosWorkChain.get_builder()
        builder_additionalkeys.structure = structure
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
