# -*- coding: utf-8 -*-
"""Tests for the `FleurinputgenCalculation` class."""

from __future__ import absolute_import
from __future__ import print_function
import os
import pytest
from aiida import orm
from aiida.common import datastructures
from aiida.engine import run_get_node
from aiida.plugins import CalculationFactory, DataFactory
from aiida_fleur.calculation.fleur import FleurCalculation


def test_fleurinpgen_default_calcinfo(aiida_profile, fixture_sandbox, generate_calc_job, fixture_code,
                                      generate_structure):  # file_regression
    """Test a default `FleurinputgenCalculation`."""
    entry_point_name = 'fleur.inpgen'

    parameters = {}

    inputs = {
        'code': fixture_code(entry_point_name),
        'structure': generate_structure(),
        # 'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'resources': {
                    'num_machines': 1
                },
                'max_wallclock_seconds': int(100),
                'withmpi': False
            }
        }
    }

    calc_info = generate_calc_job(fixture_sandbox, entry_point_name, inputs)
    codes_info = calc_info.codes_info
    cmdline_params = ['-explicit']  # for inpgen2 ['+all', '-explicit', 'aiida.in']
    local_copy_list = []
    retrieve_list = ['inp.xml', 'out', 'shell.out', 'out.error', 'struct.xsf', 'aiida.in']
    retrieve_temporary_list = []

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    #assert sorted(codes_info[0].cmdline_params) == sorted(cmdline_params)
    assert sorted(calc_info.local_copy_list) == sorted(local_copy_list)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)
    # assert sorted(calc_info.retrieve_temporary_list) == sorted(retrieve_temporary_list)
    assert sorted(calc_info.remote_symlink_list) == sorted([])

    with fixture_sandbox.open('aiida.in') as handle:
        input_written = handle.read()

    aiida_in_text = """A Fleur input generator calculation with aiida\n&input  cartesian=F /
      0.0000000000       5.1306064465       5.1306064465
      5.1306064465       0.0000000000       5.1306064465
      5.1306064465       5.1306064465       0.0000000000
      1.0000000000
      1.0000000000       1.0000000000       1.0000000000

      2\n         14       0.0000000000       0.0000000000       0.0000000000
         14       0.2500000000       0.2500000000       0.2500000000\n"""
    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['aiida.in'])
    assert input_written == aiida_in_text
    # file_regression.check(input_written, encoding='utf-8', extension='.in')


def test_fleurinpgen_with_parameters(aiida_profile, fixture_sandbox, generate_calc_job, fixture_code,
                                     generate_structure):  # file_regression
    """Test a default `FleurinputgenCalculation`."""

    # Todo add (more) tests with full parameter possibilities, i.e econfig, los, ....

    entry_point_name = 'fleur.inpgen'

    parameters = {
        'atom': {
            'element': 'Si',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },  #'econfig': '[He] 2s2 2p6 | 3s2 3p2', 'lo': ''},
        'comp': {
            'kmax': 5.0,
            'gmaxxc': 12.5,
            'gmax': 15.0
        },
        'kpt': {
            'div1': 17,
            'div2': 17,
            'div3': 17,
            'tkb': 0.0005
        }
    }

    inputs = {
        'code': fixture_code(entry_point_name),
        'structure': generate_structure(),
        'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'resources': {
                    'num_machines': 1
                },
                'max_wallclock_seconds': int(100),
                'withmpi': False
            }
        }
    }
    calc_info = generate_calc_job(fixture_sandbox, entry_point_name, inputs)

    with fixture_sandbox.open('aiida.in') as handle:
        input_written = handle.read()

    aiida_in_text = """A Fleur input generator calculation with aiida\n&input  cartesian=F /
      0.0000000000       5.1306064465       5.1306064465
      5.1306064465       0.0000000000       5.1306064465
      5.1306064465       5.1306064465       0.0000000000
      1.0000000000
      1.0000000000       1.0000000000       1.0000000000

      2\n         14       0.0000000000       0.0000000000       0.0000000000
         14       0.2500000000       0.2500000000       0.2500000000
&atom
  element="Si"   jri=981   lmax=12   lnonsph=6   rmt=2.1 /
&comp
  gmax=15.0   gmaxxc=12.5   kmax=5.0 /
&kpt
  div1=17   div2=17   div3=17   tkb=0.0005 /
"""
    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['aiida.in'])
    assert input_written == aiida_in_text
    # file_regression.check(input_written, encoding='utf-8', extension='.in')


@pytest.mark.skip(reason='mock code buggy, todo has to be checked')
def test_FleurinpgenJobCalc_full_mock(aiida_profile, mock_code_factory, generate_structure_W):  # pylint: disable=redefined-outer-name
    """
    Tests the fleur inputgenerate with a mock executable if the datafiles are their,
    otherwise runs inpgen itself if a executable was specified

    """
    CALC_ENTRY_POINT = 'fleur.inpgen'

    parameters = {
        'atom': {
            'element': 'W',
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6,
            'econfig': '[Kr] 4d10 4f14 | 5s2 5p6 6s2 5d4',
            'lo': '5s 5p'
        },
        'comp': {
            'kmax': 5.0,
            'gmaxxc': 12.5,
            'gmax': 15.0
        },
        'kpt': {
            'div1': 3,
            'div2': 3,
            'div3': 3,
            'tkb': 0.0005
        }
    }

    mock_code = mock_code_factory(label='inpgen',
                                  data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                'data_dir/'),
                                  entry_point=CALC_ENTRY_POINT,
                                  ignore_files=['_aiidasubmit.sh'])
    print(mock_code)
    inputs = {
        'structure': generate_structure_W(),
        'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'resources': {
                    'num_machines': 1,
                    'tot_num_mpiprocs': 1
                },
                'max_wallclock_seconds': int(100),
                'withmpi': False
            }
        }
    }
    calc = CalculationFactory(CALC_ENTRY_POINT)  # (code=mock_code, **inputs)
    print(calc)
    res, node = run_get_node(CalculationFactory(CALC_ENTRY_POINT), code=mock_code, **inputs)

    print((res['remote_folder'].list_objects()))
    print((res['retrieved'].list_objects()))
    assert node.is_finished_ok
