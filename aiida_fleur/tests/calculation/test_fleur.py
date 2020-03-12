"""Tests for the `FleurCalculation` class."""


from __future__ import absolute_import
from aiida import orm
from aiida.common import datastructures
from aiida_fleur.calculation.fleur import FleurCalculation
import aiida_fleur
import os


def test_fleur_default_calcinfo(aiida_profile, fixture_sandbox, generate_calc_job,
                                fixture_code, create_fleurinp):
    """Test a default `FleurCalculation`."""

    entry_point_name = 'fleur.fleur'
    aiida_path = os.path.dirname(aiida_fleur.__file__)
    TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/W/files/inp.xml')

    parameters = {}
    fleurinp = create_fleurinp(TEST_INP_XML_PATH)
    inputs = {
        'code': fixture_code(entry_point_name),
        'fleurinpdata': fleurinp,
        # 'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {'resources': {'num_machines': 1},
                        'max_wallclock_seconds': int(60),
                        'withmpi': False}
        }
    }

    calc_info = generate_calc_job(fixture_sandbox, entry_point_name, inputs)
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
