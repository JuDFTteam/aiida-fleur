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
from aiida.engine import run_get_node

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'
CALC2_ENTRY_POINT = 'fleur.inpgen'


# tests
#@pytest.mark.skip(reason='fleur executable fails here, test prob works')
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_fleurinp_Si(
    #run_with_cache,
    with_export_cache,
    mock_code_factory,
    create_fleurinp, clear_database
):
    """
    full example using scf workflow with just a fleurinp data as input.
    Several fleur runs needed till convergence
    """

    options = {
        'resources': {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    FleurCode = mock_code = mock_code_factory(
        label='fleur',
        data_dir_abspath=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'
        ),
        entry_point=CALC_ENTRY_POINT,
        ignore_files=[
            '_aiidasubmit.sh', 'cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json',
            'cdn??'
        ]
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
    #run_with_cache(builder)
    data_dir_path = os.path.join(
        aiida_path, 'tests/workflows/caches/fleur_scf_fleurinp_Si.tar.gz'
    )
    with with_export_cache(data_dir_abspath=data_dir_path):
        out, node = run_get_node(builder)
    #print(out)
    #print(node)

    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    #print(n)
    assert abs(n.get('distance_charge') - 9.8993e-06) < 10**-14
    assert n.get('errors') == []
    #assert abs(n.get('starting_fermi_energy') - 0.409241) < 10**-14

@pytest.mark.skip(reason='fleur executable fails here, test prob works')
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_structure_W(run_with_cache, mock_code_factory, generate_structure2):
    """
    Full regression test of FleurScfWorkchain starting with a crystal structure and parameters
    Check if calc parameters are given through, check if wf default parameters are updated
    """

    # prepare input nodes and dicts
    options = {
        'resources': {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    FleurCode = mock_code_factory(
        label='fleur',
        data_dir_abspath=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'
        ),
        entry_point=CALC_ENTRY_POINT,
        ignore_files=['cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??']
    )
    InpgenCode = mock_code_factory(
        label='inpgen',
        data_dir_abspath=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'
        ),
        entry_point=CALC2_ENTRY_POINT,
        ignore_files=['_aiidasubmit.sh', 'FleurInputSchema.xsd']
    )

    wf_parameters = {'serial': True, 'itmax_per_run': 10}

    calc_parameters = {
        'atom': {
            'element': "Si",
            'rmt': 2.1,
            'jri': 981,
            'lmax': 12,
            'lnonsph': 6
        },
        'comp': {
            'kmax': 3.2
        },
        'kpt': {
            'div1': 10,
            'div2': 10,
            'div3': 10,
            'tkb': 0.0005
        }
    }

    #calc_parameters = {'atom': {'element': "W", 'rmt': 2.3, 'jri': 981, 'lmax': 10,
    #                   'lnonsph': 6, 'econfig': '[Kr] 4d10 4f14 | 5s2 5p6 6s2 5d4', 'lo': '5s 5p'},
    #                   'comp': {'kmax': 3.5},
    #                    'kpt': {'div1': 15, 'div2': 15, 'div3': 15, 'tkb': 0.0005}}

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for W bulk with structure, calc para and wf para given'
    builder.metadata.label = 'FleurSCF_test_W_bulk'
    builder.structure = generate_structure2().store()
    builder.options = Dict(dict=options).store()
    builder.calc_parameters = Dict(dict=calc_parameters).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.fleur = FleurCode.store()
    builder.inpgen = InpgenCode.store()
    print(builder)

    # now run scf with cache fixture
    run_with_cache(builder)
    out, node = run_get_node(builder)
    print(out)
    print(node)

    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    print(n)
    assert abs(n.get('distance_charge') - 9.8993e-06) < 10**-14
    assert n.get('errors') == []
    assert False

@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_fleurinp_Si_modifications(
    #run_with_cache,
    with_export_cache,
    mock_code_factory,
    create_fleurinp, clear_database
):
    """
    Full regression test of FleurScfWorkchain starting with a fleurinp data,
    but adjusting the Fleur input file before the fleur run.
    """

    wf_parameters = {
        'fleur_runmax': 4,
        'density_converged': 0.0002,
        'energy_converged': 0.002,
        'force_converged': 0.002,
        'mode': 'density',  # 'density', 'energy' or 'force'
        'serial': True,
        'itmax_per_run': 30,
        'force_dict': {
            'qfix': 2,
            'forcealpha': 0.5,
            'forcemix': 'BFGS'
        },
        'inpxml_changes': [('set_inpchanges', {
            'change_dict': {
                'Kmax': 3.6
            }
        })],
    }

    options = {
        'resources': {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    FleurCode = mock_code = mock_code_factory(
        label='fleur',
        data_dir_abspath=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'
        ),
        entry_point=CALC_ENTRY_POINT,
        ignore_files=[
            '_aiidasubmit.sh', 'cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json',
            'cdn??'
        ]
    )
    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given and mod request'
    builder.metadata.label = 'FleurSCF_test_Si_bulk_mod'
    builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.options = Dict(dict=options).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.fleur = FleurCode
    #print(builder)

    # now run calculation
    #run_with_cache(builder)
    data_dir_path = os.path.join(
        aiida_path, 'tests/workflows/caches/fleur_scf_fleurinp_Si_mod.tar.gz'
    )

    with with_export_cache(data_dir_abspath=data_dir_path):
        out, node = run_get_node(builder)
    print(out)
    #print(node)

    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    lasto = out['last_fleur_calc_output']
    calc = lasto.get_incoming().all()[0].node
    print(calc)
    print(calc.get_cache_source())
    lasto = lasto.get_dict()

    print(n)
    #get kmax and minDistance
    assert abs(n.get('distance_charge') - 9.8993e-06) < 10**-14
    assert n.get('errors') == []
    assert lasto['kmax'] == 3.6

@pytest.mark.skip(reason="Test is not implemented")
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_continue_converged(run_with_cache, mock_code_factory):
    """
    Full regression test of FleurScfWorkchain starting from an already converged fleur calculation,
    remote data
    """
    assert False

@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_validation_wrong_inputs(
    run_with_cache, mock_code_factory, create_fleurinp, generate_structure2
):
    """
    Test the validation behavior of FleurScfWorkchain if wrong input is provided it should throw
    an exitcode and not start a Fleur run or crash
    """
    from aiida.engine import run_get_node

    # prepare input nodes and dicts
    options = {
        'resources': {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }
    options = Dict(dict=options).store()

    FleurCode = mock_code_factory(
        label='fleur',
        data_dir_abspath=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'
        ),
        entry_point=CALC_ENTRY_POINT,
        ignore_files=['cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??']
    )
    InpgenCode = mock_code_factory(
        label='inpgen',
        data_dir_abspath=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'calc_data_dir/'
        ),
        entry_point=CALC2_ENTRY_POINT,
        ignore_files=['_aiidasubmit.sh', 'FleurInputSchema.xsd']
    )

    calc_parameters = Dict(dict={})
    calc_parameters.store()
    structure = generate_structure2()
    structure.store()
    fleurinp = create_fleurinp(TEST_INP_XML_PATH)
    fleurinp.store()

    ################
    # Create builders

    # 1. create builder structure and fleurinp
    builder_struc_fleurinp = FleurScfWorkChain.get_builder()
    builder_struc_fleurinp.structure = structure
    builder_struc_fleurinp.fleurinp = fleurinp
    builder_struc_fleurinp.options = options
    builder_struc_fleurinp.fleur = FleurCode
    builder_struc_fleurinp.inpgen = InpgenCode

    # 2. create builder structure no inpgen given
    builder_no_inpgen = FleurScfWorkChain.get_builder()
    builder_no_inpgen.structure = structure
    builder_no_inpgen.options = options
    builder_no_inpgen.fleur = FleurCode

    # 3. create builder no fleurcode given
    builder_no_fleur = FleurScfWorkChain.get_builder()
    builder_no_fleur.structure = structure
    builder_no_fleur.options = options
    builder_no_fleur.inpgen = InpgenCode

    # 4. wrong code given (here we swap)
    builder_wrong_code = FleurScfWorkChain.get_builder()
    builder_wrong_code.structure = structure
    builder_wrong_code.options = options
    builder_wrong_code.inpgen = FleurCode
    builder_wrong_code.fleur = InpgenCode

    # 5. create builder fleurinp and calc_parameter given

    builder_calc_para_fleurinp = FleurScfWorkChain.get_builder()
    builder_calc_para_fleurinp.calc_parameters = calc_parameters
    builder_calc_para_fleurinp.fleurinp = fleurinp
    builder_calc_para_fleurinp.options = options
    builder_calc_para_fleurinp.fleur = FleurCode
    builder_calc_para_fleurinp.inpgen = InpgenCode

    ###################
    # now run the buidlers all should fail early with exit codes

    # 1. structure and fleurinp given
    out, node = run_get_node(builder_struc_fleurinp)
    assert out == {}
    assert node.is_finished == True
    assert node.is_finished_ok == False
    assert node.exit_status == 231

    # 2. structure and no inpgen given
    out, node = run_get_node(builder_no_inpgen)
    assert out == {}
    assert node.is_finished == True
    assert node.is_finished_ok == False
    assert node.exit_status == 231

    # 3. no fleur code given, since not optional input,
    # caught by aiida during creation
    with pytest.raises(ValueError) as e_info:
        out, node = run_get_node(builder_no_fleur)

    # 4. wrong code type given
    out, node = run_get_node(builder_wrong_code)
    assert out == {}
    assert node.is_finished == True
    assert node.is_finished_ok == False
    assert node.exit_status == 233

    # 5. calc_parameter and fleurinp given
    out, node = run_get_node(builder_calc_para_fleurinp)
    assert out == {}
    assert node.is_finished == True
    assert node.is_finished_ok == False
    assert node.exit_status == 231
