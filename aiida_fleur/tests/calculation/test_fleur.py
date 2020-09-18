# -*- coding: utf-8 -*-
"""Tests for the `FleurCalculation` class."""

from __future__ import absolute_import
import os
import pytest
from aiida import orm
from aiida.plugins import CalculationFactory
from aiida.engine import run_get_node
from aiida.common import datastructures

from aiida_fleur.calculation.fleur import FleurCalculation

import aiida_fleur

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')  #W/files/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'


def test_fleur_default_calcinfo(aiida_profile, fixture_sandbox, generate_calc_job, fixture_code, create_fleurinp):
    """Test a default `FleurCalculation`."""

    parameters = {}
    fleurinp = create_fleurinp(TEST_INP_XML_PATH)
    inputs = {
        'code': fixture_code(CALC_ENTRY_POINT),
        'fleurinpdata': fleurinp,
        # 'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'resources': {
                    'num_machines': 1
                },
                'max_wallclock_seconds': int(60),
                'withmpi': False
            }
        }
    }

    calc_info = generate_calc_job(fixture_sandbox, CALC_ENTRY_POINT, inputs)
    codes_info = calc_info.codes_info

    cmdline_params = ['-minimalOutput', '-wtime', '1']
    local_copy_list = [(fleurinp.uuid, 'inp.xml', 'inp.xml')]
    retrieve_list = ['cdn1', 'inp.xml', 'out.error', 'out.xml', 'shell.out', 'usage.json']
    retrieve_temporary_list = []

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    assert sorted(codes_info[0].cmdline_params) == sorted(cmdline_params)
    assert sorted(calc_info.local_copy_list) == sorted(local_copy_list)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)
    #assert sorted(calc_info.retrieve_temporary_list) == sorted(retrieve_temporary_list)
    assert sorted(calc_info.remote_symlink_list) == sorted([])

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['JUDFT_WARN_ONLY'])
    # file_regression.check(input_written, encoding='utf-8', extension='.in')


@pytest.mark.skip(reason='mock code buggy, todo: check, ggf own fixture')
def test_FleurJobCalc_full_mock(aiida_profile, mock_code_factory, create_fleurinp, clear_database,
                                hash_code_by_entrypoint):  # pylint: disable=redefined-outer-name
    """
    Tests the fleur inputgenerate with a mock executable if the datafiles are their,
    otherwise runs inpgen itself if a executable was specified

    """

    mock_code = mock_code_factory(
        label='fleur',
        data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir/'),
        entry_point=CALC_ENTRY_POINT,
        ignore_files=[
            '_aiidasubmit.sh',
            'cdnc',
            'out',
            'FleurInputSchema.xsd',
            'cdn.hdf',
            'usage.json',  # 'cdn??']
            'cdn00',
            'cdn01',
            'cdn02',
            'cdn03',
            'cdn04',
            'cdn05',
            'cdn06',
            'cdn07',
            'cdn08',
            'cdn09',
            'cdn10',
            'cdn11'
        ])
    #mock_code.append_text = 'rm cdn?? broyd* wkf2 inf cdnc stars pot* FleurInputSchema* cdn.hdf'

    inputs = {
        'fleurinpdata': create_fleurinp(TEST_INP_XML_PATH),
        #'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'resources': {
                    'num_machines': 1,
                    'tot_num_mpiprocs': 1
                },
                'max_wallclock_seconds': int(600),
                'withmpi': True
            }
        }
    }
    #calc = CalculationFactory(CALC_ENTRY_POINT, code=mock_code, **inputs)

    res, node = run_get_node(CalculationFactory(CALC_ENTRY_POINT), code=mock_code, **inputs)

    print((res['remote_folder'].list_objects()))
    print((res['retrieved'].list_objects()))
    assert node.is_finished_ok
    #assert False
