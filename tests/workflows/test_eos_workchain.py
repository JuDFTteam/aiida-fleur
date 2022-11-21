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

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_eos_structure_Si(with_export_cache, fleur_local_code, inpgen_local_code, generate_structure,
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

    with with_export_cache('fleur_eos_si_structure.tar.gz'):
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


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_eos_validation_wrong_inputs(fleur_local_code, inpgen_local_code, generate_structure2):
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

    FleurCode = fleur_local_code
    InpgenCode = inpgen_local_code

    wf_parameters = Dict({'points': 9, 'step': 0.002, 'guess': 1.00, 'wrong_key': None})
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
