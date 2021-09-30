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

import pytest
import os
from aiida.engine import run_get_node
from aiida import orm

import aiida_fleur
from aiida_fleur.workflows.eos import FleurEosWorkChain

from ..conftest import run_regression_tests

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


@pytest.mark.skipif(not run_regression_tests, reason='Aiida-testing not there or not wanted.')
@pytest.mark.timeout(500, method='thread')
def test_fleur_eos_structure_Si(with_export_cache, fleur_local_code, inpgen_local_code, generate_structure, clear_spec,
                                clear_database_after_test):
    """
    full example using scf workflow with just a fleurinp data as input.
    Several fleur runs needed till convergence
    """

    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 10 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }
    wf_param = {'points': 3, 'step': 0.02, 'guess': 1.03}

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

    FleurCode = fleur_local_code
    InpgenCode = inpgen_local_code

    # create process builder to set parameters
    builder = FleurEosWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur FleurEosWorkChain test for Si bulk'
    builder.metadata.label = 'FleurEosWorkChain_test_Si_bulk'
    builder.structure = generate_structure().store()  #generate_structure2().store()
    builder.wf_parameters = orm.Dict(dict=wf_param).store()
    builder.scf = {
        'fleur': FleurCode,
        'inpgen': InpgenCode,
        'options': orm.Dict(dict=options).store(),
        'calc_parameters': orm.Dict(dict=calc_parameters).store()
    }
    print(builder)
    # now run calculation
    data_dir_path = os.path.join(aiida_path, '../tests/workflows/caches/fleur_eos_si_structure.tar.gz')
    with with_export_cache(data_dir_abspath=data_dir_path):
        out, node = run_get_node(builder)

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
    assert abs(outpara.get('scaling_gs') - 1.0260318638379) < 1e-5
    # assert outpara.get('warnings') == ['Groundstate volume was not in the scaling range.']
    # assert outpara.get('info') == ['Consider rerunning around point 0.9926854655857787']


# tests
#@pytest.mark.skip
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurEosWorkChain:
    """
    Regression tests for the FleurEosWorkChain
    """

    @pytest.mark.skip
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

    @pytest.mark.skipif(not run_regression_tests, reason='Aiida-testing not there or not wanted.')
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


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
def test_birch_murnaghan_fit():
    """Test the birch murnaghan fit in of the eos workchain

    """
    import numpy as np
    from aiida_fleur.workflows.eos import birch_murnaghan_fit

    # ignore numerical differences
    dezi = 8
    should_vol = round(50.15185277312836, dezi)
    should_bulk_mod = round(30.630869193205523, dezi)
    should_bulk_deriv = round(-6.120875695109946, dezi)
    should_residuals = [round(0.05862235697619352, dezi)]
    energies = np.array([-1, -2, -3, -4, -3.2, -2.1, -1])
    base = 50.0
    scales = np.array([0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06])
    volumes = scales * base
    volume, bulk_modulus, bulk_deriv, residuals = birch_murnaghan_fit(energies, volumes)

    # print(volume, bulk_modulus, bulk_deriv, residuals)
    assert round(volume, dezi) == should_vol
    assert round(bulk_modulus, dezi) == should_bulk_mod
    assert round(bulk_deriv, dezi) == should_bulk_deriv
    assert [round(res, dezi) for res in residuals] == should_residuals


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
def test_birch_murnaghan():
    """Test the eval birch_murnaghan

    """
    import numpy as np
    from aiida_fleur.workflows.eos import birch_murnaghan

    should_ev = [
        0.00034115814926603393, 4.2469082027066444e-05, 1.2542478545309484e-06, 0.0, -1.1198946045507376e-06,
        -3.386445023825032e-05, -0.00024303823850147386
    ]
    should_vp = [
        3.169784634427714, 2.0773219926762585, 1.019704802686063, 0.0, -0.9797734383823876, -1.9184258091168582,
        -2.8154206900859817
    ]

    energies = np.array([-1, -2, -3, -4, -3.2, -2.1, -1])
    base = 50.00
    scales = np.array([0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06])
    volumes = base * scales
    bulk_modulus0 = 50
    bulk_deriv0 = 1
    ev, vp = birch_murnaghan(volumes, base, bulk_modulus0, bulk_deriv0)

    assert ev == should_ev
    assert vp == should_vp
