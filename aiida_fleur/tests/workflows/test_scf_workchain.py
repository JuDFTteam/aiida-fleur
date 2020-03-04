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

# Here we test if the interfaces of the workflows are still the same
from __future__ import absolute_import
from __future__ import print_function

import pytest
import os
import aiida_fleur
from aiida.orm import Code, load_node, Dict, StructureData
from aiida_fleur.workflows.scf import FleurScfWorkChain

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


# tests
@pytest.mark.usefixtures("aiida_profile", "clear_database")
class Test_FleurScfWorkChain():
    """
    Regression tests for the FleurScfWorkChain
    """

    @pytest.mark.timeout(500, method='thread')
    def test_fleur_scf_fleurinp_Si(self, run_with_cache, mock_code_factory, create_fleurinp):
        """
        full example using scf workflow with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        #from aiida.orm import Code, load_node, Dict, StructureData
        #from aiida_fleur.workflows.scf import FleurScfWorkChain

        options = {'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
                   'max_wallclock_seconds': 5 * 60,
                   'withmpi': False, 'custom_scheduler_commands': ''}

        FleurCode = mock_code = mock_code_factory(
            label='fleur',
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir/'),
            entry_point=CALC_ENTRY_POINT,
            ignore_files=['_aiidasubmit.sh', 'cdnc', 'out',
                          'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??']
        )
        # create process builder to set parameters
        builder = FleurScfWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given'
        builder.metadata.label = 'FleurSCF_test_Si_bulk'
        builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
        builder.options = Dict(dict=options).store()
        builder.fleur = FleurCode
        #print(builder)

        # now run calculation
        out, node = run_with_cache(builder)
        #print(out)
        #print(node)

        # check output
        n = out['output_scf_wc_para']
        n = n.get_dict()
        #print(n)
        assert abs(n.get('distance_charge') - 9.8993e-06) < 10**-14
        assert n.get('errors') == []
        #assert abs(n.get('starting_fermi_energy') - 0.409241) < 10**-14


    @pytest.mark.timeout(500, method='thread')
    def test_fleur_scf_structure_Si(self, run_with_cache, mock_code_factory, generate_structure):
        """
        Full regression test of FleurScfWorkchain starting with a crystal structure and parameters
        Check if calc parameters are given through, check if wf default parameters are updated
        """
        
        # prepare input nodes and dicts
        options = {'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
                   'max_wallclock_seconds': 5 * 60,
                   'withmpi': False, 'custom_scheduler_commands': ''}

        FleurCode = mock_code_factory(
            label='fleur',
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir/'),
            entry_point=CALC_ENTRY_POINT,
            ignore_files=['_aiidasubmit.sh', 'cdnc', 'out',
                          'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??'])
        InpgenCode = mock_code_factory(
            label='inpgen',
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir/'),
            entry_point=CALC2_ENTRY_POINT,
            ignore_files=['_aiidasubmit.sh', 'out', 'FleurInputSchema.xsd'])


        wf_parameters = {'serial': True,
                         'itmax_per_run': 10}

        calc_parameters = {'atom': 
                              {'element': "Si", 'rmt': 2.1, 'jri': 981, 'lmax': 12, 'lnonsph': 6},
                           'comp': {'kmax': 3.2},
                           'kpt': {'div1': 10, 'div2': 10, 'div3': 10, 'tkb': 0.0005}}

        

        # create process builder to set parameters
        builder = FleurScfWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur SCF test for Si bulk with structure, calc para and wf para given'
        builder.metadata.label = 'FleurSCF_test_Si_bulk_2'
        builder.structure = generate_structure().store()
        builder.options = Dict(dict=options).store()
        builder.calc_parameters = Dict(dict=calc_parameters).store()
        builder.wf_parameters = Dict(dict=wf_parameters).store()
        builder.fleur = FleurCode
        builder.inpgen = InpgenCode
        print(builder)

        # now run scf with cache fixture
        out, node = run_with_cache(builder)
        print(out)
        print(node)

        # check output
        n = out['output_scf_wc_para']
        n = n.get_dict()
        print(n)
        assert abs(n.get('distance_charge') - 9.8993e-06) < 10**-14
        assert n.get('errors') == []
        assert False

    @pytest.mark.skip(reason="Test is not implemented")
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_scf_structure_Si_modifications(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurScfWorkchain starting with a fleurinp data,
        but adjusting the Fleur input file before the fleur run.
        """
        assert False
        wf_parameters = {'fleur_runmax': 4,
                   'density_converged': 0.00002,
                   'energy_converged': 0.002,
                   'force_converged': 0.002,
                   'mode': 'density',  # 'density', 'energy' or 'force'
                   'serial': False,
                   'itmax_per_run': 30,
                   'force_dict': {'qfix': 2,
                                  'forcealpha': 0.5,
                                  'forcemix': 'BFGS'},
                   'use_relax_xml': True,
                   'inpxml_changes': [],
                   }

    @pytest.mark.skip(reason="Test is not implemented")
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_scf_continue_converged(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurScfWorkchain starting from an already converged fleur calculation,
        remote data
        """
        assert False

    @pytest.mark.skip(reason="Test is not implemented")
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_scf_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of FleurScfWorkchain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
