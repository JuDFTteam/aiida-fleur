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
def test_fleur_band_fleurinp_Si(with_export_cache, fleur_local_code, create_fleurinp, clear_database, clear_spec,
                                aiida_caplog):
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
    desc = FleurCode.description
    with_hdf5 = False
    if desc is not None:
        if 'hdf5' in desc:
            with_hdf5 = True
        elif 'Hdf5' in desc:
            with_hdf5 = True
        elif 'HDF5' in desc:
            with_hdf5 = True
        else:
            with_hdf5 = False

    # create process builder to set parameters
    builder = FleurBandDosWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Banddos test for Si bulk with fleurinp data given'
    builder.metadata.label = 'FleurBanddos_test_Si_bulk'
    builder.options = orm.Dict(dict=options).store()
    builder.fleur = FleurCode
    builder.scf.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()
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
    assert n.get('mode') == 'band'
    if with_hdf5:
        assert 'output_banddos_wc_bands' in out
    assert 'last_calc_retrieved' in out
    res_files = out['last_calc_retrieved'].list_object_names()
    assert any(
        file in res_files for file in ('banddos.hdf', 'bands.1', 'bands.2')), f'No bands file retrieved: {res_files}'


@pytest.mark.skipif(not run_regression_tests, reason='Aiida-testing not there or not wanted.')
@pytest.mark.timeout(500, method='thread')
def test_fleur_dos_fleurinp_Si(with_export_cache, fleur_local_code, create_fleurinp, clear_database, clear_spec,
                               aiida_caplog):
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

    wf_parameters = {'mode': 'dos'}

    FleurCode = fleur_local_code
    desc = FleurCode.description
    with_hdf5 = False
    if desc is not None:
        if 'hdf5' in desc:
            with_hdf5 = True
        elif 'Hdf5' in desc:
            with_hdf5 = True
        elif 'HDF5' in desc:
            with_hdf5 = True
        else:
            with_hdf5 = False

    # create process builder to set parameters
    builder = FleurBandDosWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Banddos test for DOS of  Si bulk with fleurinp data given'
    builder.metadata.label = 'FleurBanddos_test_Si_bulk_dos'
    builder.options = orm.Dict(dict=options).store()
    builder.fleur = FleurCode
    builder.wf_parameters = orm.Dict(dict=wf_parameters).store()
    builder.scf.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()
    #print(builder)

    # now run calculation
    #run_with_cache(builder)
    data_dir_path = os.path.join(aiida_path, '../tests/workflows/caches/fleur_dos_fleurinp_Si.tar.gz')
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
    assert n.get('mode') == 'dos'
    if with_hdf5:
        assert 'output_banddos_wc_dos' in out
    assert 'last_calc_retrieved' in out
    res_files = out['last_calc_retrieved'].list_object_names()
    assert any(
        file in res_files for file in ('banddos.hdf', 'bands.1', 'bands.2')), f'No bands file retrieved: {res_files}'


@pytest.mark.skipif(not run_regression_tests, reason='Aiida-testing not there or not wanted.')
@pytest.mark.timeout(500, method='thread')
def test_fleur_band_fleurinp_Si_seekpath(with_export_cache, fleur_local_code, create_fleurinp, clear_database,
                                         clear_spec, aiida_caplog):
    """
    Full example using the band dos workchain with just a fleurinp data as input.
    Uses seekpath to determine the path for the bandstructure
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

    wf_parameters = {'kpath': 'seek'}

    FleurCode = fleur_local_code
    desc = FleurCode.description
    with_hdf5 = False
    if desc is not None:
        if 'hdf5' in desc:
            with_hdf5 = True
        elif 'Hdf5' in desc:
            with_hdf5 = True
        elif 'HDF5' in desc:
            with_hdf5 = True
        else:
            with_hdf5 = False

    # create process builder to set parameters
    builder = FleurBandDosWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Banddos test for Si bulk with fleurinp data given and kpoint path from seekpath'
    builder.metadata.label = 'FleurBanddos_test_Si_bulk'
    builder.options = orm.Dict(dict=options).store()
    builder.fleur = FleurCode
    builder.wf_parameters = orm.Dict(dict=wf_parameters).store()
    builder.scf.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()
    #print(builder)

    # now run calculation
    #run_with_cache(builder)
    data_dir_path = os.path.join(aiida_path, '../tests/workflows/caches/fleur_band_fleurinp_Si_seek.tar.gz')
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
    assert n.get('mode') == 'band'
    if with_hdf5:
        assert 'output_banddos_wc_bands' in out
    assert 'last_calc_retrieved' in out
    res_files = out['last_calc_retrieved'].list_object_names()
    assert any(
        file in res_files for file in ('banddos.hdf', 'bands.1', 'bands.2')), f'No bands file retrieved: {res_files}'


@pytest.mark.skipif(not run_regression_tests, reason='Aiida-testing not there or not wanted.')
@pytest.mark.timeout(500, method='thread')
def test_fleur_band_fleurinp_Si_ase(with_export_cache, fleur_local_code, create_fleurinp, clear_database, clear_spec,
                                    aiida_caplog):
    """
    Full example using the band dos workchain with just a fleurinp data as input.
    Uses ase bandpath to determine the path through the briloouin zone
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

    wf_parameters = {'kpath': 'XKGLWWXG', 'kpoints_number': 200}

    FleurCode = fleur_local_code
    desc = FleurCode.description
    with_hdf5 = False
    if desc is not None:
        if 'hdf5' in desc:
            with_hdf5 = True
        elif 'Hdf5' in desc:
            with_hdf5 = True
        elif 'HDF5' in desc:
            with_hdf5 = True
        else:
            with_hdf5 = False

    # create process builder to set parameters
    builder = FleurBandDosWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Banddos test for Si bulk with fleurinp data given and kpoint path from ase'
    builder.metadata.label = 'FleurBanddos_test_Si_bulk'
    builder.options = orm.Dict(dict=options).store()
    builder.fleur = FleurCode
    builder.wf_parameters = orm.Dict(dict=wf_parameters).store()
    builder.scf.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()
    #print(builder)

    # now run calculation
    #run_with_cache(builder)
    data_dir_path = os.path.join(aiida_path, '../tests/workflows/caches/fleur_band_fleurinp_Si_ase.tar.gz')
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
    assert n.get('mode') == 'band'
    if with_hdf5:
        assert 'output_banddos_wc_bands' in out
    assert 'last_calc_retrieved' in out
    res_files = out['last_calc_retrieved'].list_object_names()
    assert any(
        file in res_files for file in ('banddos.hdf', 'bands.1', 'bands.2')), f'No bands file retrieved: {res_files}'


@pytest.mark.skip(reason='Test is not implemented')
@pytest.mark.timeout(500, method='thread')
def test_fleur_band_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
    """
    Test the validation behavior of band dos workchain if wrong input is provided it should throw
    an exitcode and not start a Fleur run or crash
    """
    assert False
