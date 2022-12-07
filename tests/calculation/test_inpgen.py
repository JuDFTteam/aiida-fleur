"""Tests for the `FleurinputgenCalculation` class."""

import pytest
from aiida import orm
from aiida.common import datastructures
from aiida.cmdline.utils.common import get_calcjob_report
from aiida.engine import run_get_node
from aiida.plugins import CalculationFactory

import logging


def test_fleurinpgen_default_calcinfo(fixture_sandbox, generate_calc_job, fixture_code,
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
       0.000000000        5.130606429        5.130606429
       5.130606429        0.000000000        5.130606429
       5.130606429        5.130606429        0.000000000
      1.0000000000
       1.000000000        1.000000000        1.000000000

      2\n         14       0.0000000000       0.0000000000       0.0000000000
         14       0.2500000000       0.2500000000       0.2500000000\n"""
    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['JUDFT_WARN_ONLY', 'aiida.in'])
    assert input_written == aiida_in_text
    # file_regression.check(input_written, encoding='utf-8', extension='.in')


def test_fleurinpgen_with_parameters(fixture_sandbox, generate_calc_job, fixture_code,
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
       0.000000000        5.130606429        5.130606429
       5.130606429        0.000000000        5.130606429
       5.130606429        5.130606429        0.000000000
      1.0000000000
       1.000000000        1.000000000        1.000000000

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
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['JUDFT_WARN_ONLY', 'aiida.in'])
    assert input_written == aiida_in_text
    # file_regression.check(input_written, encoding='utf-8', extension='.in')


def test_fleurinpgen_with_profile_and_parameters(fixture_sandbox, generate_calc_job, fixture_code, generate_structure,
                                                 aiida_caplog):  # file_regression
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
        'settings': orm.Dict(dict={'profile': 'default'}),
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

    logs = orm.Log.objects.get_logs_for(orm.load_node(calc_info.uuid))

    assert len(logs) == 1
    assert 'Inpgen profile specified but atom/LAPW basis specific parameters are provided' in logs[0].message


def test_fleurinpgen_profile(fixture_sandbox, generate_calc_job, fixture_code, generate_structure):  # file_regression
    """Test a default `FleurinputgenCalculation` with a profile setting."""
    entry_point_name = 'fleur.inpgen'

    #Should not raise a warning for conflicting with the profile
    parameters = {'soc': {'theta': 0.0, 'phi': 0.0}}

    inputs = {
        'code': fixture_code(entry_point_name),
        'structure': generate_structure(),
        'parameters': orm.Dict(dict=parameters),
        'settings': orm.Dict(dict={'profile': 'precise'}),
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
       0.000000000        5.130606429        5.130606429
       5.130606429        0.000000000        5.130606429
       5.130606429        5.130606429        0.000000000
      1.0000000000
       1.000000000        1.000000000        1.000000000

      2\n         14       0.0000000000       0.0000000000       0.0000000000
         14       0.2500000000       0.2500000000       0.2500000000\n&soc\n 0.0  0.0 /\n"""
    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['JUDFT_WARN_ONLY', 'aiida.in'])
    assert input_written == aiida_in_text

    assert calc_info.codes_info[0].cmdline_params[-2:] == ['-profile', 'precise']

    logs = orm.Log.objects.get_logs_for(orm.load_node(calc_info.uuid))
    assert len(logs) == 0


def test_fleurinpgen_magnetic_structure(fixture_sandbox, generate_calc_job, fixture_code,
                                        generate_magnetic_structure):  # file_regression
    """Test a default `FleurinputgenCalculation` with a FleurMagneticStructureData input."""
    entry_point_name = 'fleur.inpgen'

    inputs = {
        'code': fixture_code(entry_point_name),
        'structure': generate_magnetic_structure(),
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
       9.387970416        0.000000000        0.000000000
      -4.693985208        8.130220871        0.000000000
       0.000000000        0.000000000        7.488795661
      1.0000000000
       1.000000000        1.000000000        1.000000000

      6\n         62       0.0000000000       0.0000000000       0.0000000000 : up
         27       0.3333333333       0.6666666667       0.0000000000 : down
         27       0.6666666667       0.3333333333       0.0000000000 : down
         27       0.0000000000       0.5000000000       0.5000000000 : down
         27       0.5000000000       0.0000000000       0.5000000000 : down
         27       0.5000000000       0.5000000000       0.5000000000 : down\n"""

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(['JUDFT_WARN_ONLY', 'aiida.in'])
    assert input_written == aiida_in_text

    logs = orm.Log.objects.get_logs_for(orm.load_node(calc_info.uuid))
    assert len(logs) == 0


@pytest.mark.regression_test
def test_FleurinpgenJobCalc_full_mock(inpgen_local_code, generate_structure_W):  # pylint: disable=redefined-outer-name
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
    res, node = run_get_node(CalculationFactory(CALC_ENTRY_POINT), code=inpgen_local_code, **inputs)
    print(node)
    print(get_calcjob_report(node))
    print(res['remote_folder'].list_object_names())
    print(res['retrieved'].list_object_names())
    assert node.is_finished_ok


def test_x_and_bunchatom_input(
    fixture_sandbox,
    generate_calc_job,
    fixture_code,
):
    """Test that plugin can deal (ignores) with other StructureData features

    Currently we assume atoms, deal with vacancies, i.e we leave them out
    ignore the x element. This is important for interoperability with kkr

    # TODO often we do natoms= len(n.sites), which would be false in the case of vacancies.
    """
    from aiida.orm import StructureData

    struc_Fe7Nb = StructureData()
    struc_Fe7Nb.cell = [[3.3168796764431, 0.0, 0.0], [1.6584398382215, 2.3453881115923, 0.0],
                        [0.0, 0.0, 13.349076054836]]
    struc_Fe7Nb.pbc = (True, True, False)
    elements = ['X', 'X', 'X', 'Fe', 'Nb', 'Nb']
    positions = [[0.0, 0.0, 1.1726940557829], [1.6584398382215, 0.0, 3.5180821673487], [0.0, 0.0, 5.8634702789145],
                 [1.6584398382215, 0.0, 8.2088583904803], [0.0, 0.0, 10.096376717551],
                 [1.6584398382215, 0.0, 12.46832205832]]
    for el, pos in zip(elements, positions):
        struc_Fe7Nb.append_atom(symbols=[el], position=pos)

    entry_point_name = 'fleur.inpgen'

    parameters = {}

    inputs = {
        'code': fixture_code(entry_point_name),
        'structure': struc_Fe7Nb,
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
    cmdline_params = ['+all', '-explicit', '-f', 'aiida.in']
    local_copy_list = []
    retrieve_list = ['inp.xml', 'out', 'shell.out', 'out.error', 'struct.xsf', 'aiida.in']
    retrieve_temporary_list = []

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)

    with fixture_sandbox.open('aiida.in') as handle:
        input_written = handle.read()

    print(input_written)
    assert '   3\n' in input_written  # test for natoms

    # Test not none of the vacany elements was written into the input file
    for line in input_written.split('\n'):
        assert 'X' not in line
        assert ' 0 ' not in line

    # todo weights, an molecules on site
