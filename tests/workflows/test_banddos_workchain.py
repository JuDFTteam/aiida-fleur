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
import pytest
import aiida_fleur
from aiida_fleur.workflows.banddos import FleurBandDosWorkChain
from aiida import orm
from aiida.engine import run_get_node
from aiida.cmdline.utils.common import get_workchain_report, get_calcjob_report
import os
from ..conftest import run_regression_tests

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


@pytest.mark.skipif(not run_regression_tests, reason='Aiida-testing not there or not wanted.')
@pytest.mark.timeout(500, method='thread')
def test_fleur_band_fleurinp_Si(with_export_cache, fleur_local_code, create_fleurinp, clear_database, clear_spec):
    """
    Full example using the band dos workchain with just a fleurinp data as input.
    Calls scf, Several fleur runs needed till convergence
    """
    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    FleurCode = fleur_local_code

    # create process builder to set parameters
    builder = FleurBandDosWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Banddos test for Si bulk with fleurinp data given'
    builder.metadata.label = 'FleurBanddos_test_Si_bulk'
    builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.options = orm.Dict(dict=options).store()
    builder.fleur = FleurCode
    #print(builder)

    # now run calculation
    #run_with_cache(builder)
    data_dir_path = os.path.join(aiida_path, '../tests/workflows/caches/fleur_band_fleurinp_Si.tar.gz')
    with with_export_cache(data_dir_abspath=data_dir_path):
        out, node = run_get_node(builder)
    #print(out)
    #print(node)

    print(get_workchain_report(node, 'REPORT'))

    #assert node.is_finished_ok
    # check output
    n = out['output_banddos_wc_para']
    n = n.get_dict()

    print(get_calcjob_report(orm.load_node(n['last_calc_uuid'])))

    #print(n)
    efermi = 0.2034799610
    bandgap = 0.8556165891
    assert abs(n.get('fermi_energy_scf') - efermi) < 2.0e-6
    assert abs(n.get('bandgap_scf') - bandgap) < 2.0e-6
    assert 'output_banddos_wc_bands' in out
    assert 'last_calc_retrieved' in out
    res_files = out['last_calc_retrieved'].list_object_names()
    assert any(
        file in res_files for file in ('banddos.hdf', 'bands.1', 'bands.2')), f'No bands file retrieved: {res_files}'


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
