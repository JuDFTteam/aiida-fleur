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
''' Contains various tests for the scf workchain '''
import pytest
import os
from aiida.orm import load_node, Dict
from aiida.engine import run_get_node
from aiida.cmdline.utils.common import get_calcjob_report
import aiida_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml')


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_fleurinp_Si(with_export_cache, fleur_local_code, create_fleurinp, clear_database,
                               show_workchain_summary):
    """
    full example using scf workflow with just a fleurinp data as input.
    Several fleur runs needed till convergence
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

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given'
    builder.metadata.label = 'FleurSCF_test_Si_bulk'
    builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.options = Dict(dict=options).store()
    builder.fleur = fleur_local_code
    #print(builder)

    with with_export_cache('fleur_scf_fleurinp_Si.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)
    assert node.is_finished_ok

    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()

    #print(n)
    assert abs(n.get('distance_charge') - 9.8993e-06) < 2.0e-6
    assert n.get('errors') == []
    #assert abs(n.get('starting_fermi_energy') - 0.409241) < 10**-14


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_structure_Si(with_export_cache, clear_database, fleur_local_code, inpgen_local_code,
                                generate_structure2, show_workchain_summary):
    """
    Full regression test of FleurScfWorkchain starting with a crystal structure and parameters
    Check if calc parameters are given through, check if wf default parameters are updated
    """
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

    wf_parameters = {'itmax_per_run': 30}

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

    #calc_parameters = {'atom': {'element': "W", 'rmt': 2.3, 'jri': 981, 'lmax': 10,
    #                   'lnonsph': 6, 'econfig': '[Kr] 4d10 4f14 | 5s2 5p6 6s2 5d4', 'lo': '5s 5p'},
    #                   'comp': {'kmax': 3.5},
    #                    'kpt': {'div1': 15, 'div2': 15, 'div3': 15, 'tkb': 0.0005}}

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk with structure, calc para and wf para given'
    builder.metadata.label = 'FleurSCF_test_Si_bulk'
    builder.structure = generate_structure2().store()
    builder.options = Dict(dict=options).store()
    builder.calc_parameters = Dict(dict=calc_parameters).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.fleur = fleur_local_code
    builder.inpgen = inpgen_local_code
    print(builder)

    with with_export_cache('fleur_scf_structure_Si.tar.gz'):
        out, node = run_get_node(builder)
    show_workchain_summary(node)
    assert node.is_finished_ok

    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    print(n)
    #The two distances correspond to the scenario where
    # 1. The inpgen ignores the set Muffin-tin radius and uses it's default
    #assert abs(n.get('distance_charge') - 8.0987e-06) < 2.0e-6
    # 2. The set muffin-tin radius is respected
    assert abs(n.get('distance_charge') - 1.67641e-05) < 2.0e-6
    assert n.get('errors') == []


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_non_convergence(with_export_cache, clear_database, fleur_local_code, inpgen_local_code,
                                   generate_structure2, show_workchain_summary):
    """
    Full regression test of FleurScfWorkchain starting with a crystal structure and parameters
    Check if calc parameters are given through, check if wf default parameters are updated
    """
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

    wf_parameters = {'itmax_per_run': 3}

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

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk which does not converge'
    builder.metadata.label = 'FleurSCF_test_Si_bulk_non_converged'
    builder.structure = generate_structure2().store()
    builder.options = Dict(dict=options).store()
    builder.calc_parameters = Dict(dict=calc_parameters).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.fleur = fleur_local_code
    builder.inpgen = inpgen_local_code
    print(builder)

    # now run scf with cache fixture
    with with_export_cache('fleur_scf_structure_Si_non_converged.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)
    assert not node.is_finished_ok
    assert node.exit_status == 362


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_fleurinp_Si_modifications(with_export_cache, fleur_local_code, create_fleurinp, clear_database,
                                             show_workchain_summary):
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
        'itmax_per_run': 30,
        'force_dict': {
            'qfix': 2,
            'forcealpha': 0.5,
            'forcemix': 'BFGS'
        },
        'inpxml_changes': [('set_inpchanges', {
            'changes': {
                'Kmax': 3.8
            }
        })],
    }

    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given and mod request'
    builder.metadata.label = 'FleurSCF_test_Si_bulk_mod'
    builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.options = Dict(dict=options).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.fleur = fleur_local_code
    #print(builder)

    with with_export_cache('fleur_scf_fleurinp_Si_mod.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)
    assert node.is_finished_ok
    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    lasto = out['last_calc']['output_parameters']
    calc = lasto.get_incoming().all()[0].node
    print(calc)
    print(calc.get_cache_source())
    lasto = lasto.get_dict()

    print(n)
    #get kmax and minDistance
    assert abs(n.get('distance_charge') - 0.0001671267) < 2.0e-6
    assert n.get('errors') == []
    assert lasto['kmax'] == 3.8


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_structure_kpoint_distance(with_export_cache, fleur_local_code, inpgen_local_code, clear_database,
                                             generate_structure2, show_workchain_summary):
    """
    Full regression test of FleurScfWorkchain starting with a fleurinp data,
    but adjusting the Fleur input file before the fleur run.
    """

    wf_parameters = {
        'fleur_runmax': 4,
        'density_converged': 0.0002,
        'energy_converged': 0.002,
        'force_converged': 0.002,
        'kpoints_distance': 0.15,
        'kpoints_force_gamma': True,
        'mode': 'density',  # 'density', 'energy' or 'force'
        'itmax_per_run': 30,
        'force_dict': {
            'qfix': 2,
            'forcealpha': 0.5,
            'forcemix': 'BFGS'
        },
    }
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
    }

    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk with structure given and kpoint distance specified'
    builder.metadata.label = 'FleurSCF_test_Si_bulk_kpoint_distance'
    builder.options = Dict(dict=options).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.calc_parameters = Dict(dict=calc_parameters).store()
    builder.structure = generate_structure2().store()
    builder.fleur = fleur_local_code
    builder.inpgen = inpgen_local_code
    #print(builder)

    with with_export_cache('fleur_scf_structure_Si_kpoints_distance.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)
    assert node.is_finished_ok
    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    lasto = out['last_calc']['output_parameters']
    calc = lasto.get_incoming().all()[0].node
    print(calc)
    print(calc.get_cache_source())
    lasto = lasto.get_dict()

    print(n)
    #get kmax and minDistance
    assert abs(n.get('distance_charge') - 0.0001500536) < 2.0e-6
    assert n.get('errors') == []

    parameter = node.outputs.fleurinp.get_parameterdata_ncf()
    assert parameter['kpt'] == {'div1': 14, 'div2': 14, 'div3': 14, 'gamma': True}
    assert lasto['kmax'] == 3.4


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_continue_converged(with_export_cache, fleur_local_code, clear_database, get_remote_data_si,
                                      show_workchain_summary):
    """
    Full regression test of FleurScfWorkchain starting from an already converged fleur calculation,
    remote data
    """
    wf_parameters = {
        'fleur_runmax': 4,
        'density_converged': 0.0002,
        'energy_converged': 0.002,
        'force_converged': 0.002,
        'mode': 'density',  # 'density', 'energy' or 'force'
        'itmax_per_run': 30,
        'force_dict': {
            'qfix': 2,
            'forcealpha': 0.5,
            'forcemix': 'BFGS'
        },
    }

    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    # create process builder to set parameters
    builder = FleurScfWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur SCF test for Si bulk with remote data given which is already converged'
    builder.metadata.label = 'FleurSCF_test_Si_remote_converged'
    builder.remote_data = get_remote_data_si()
    builder.options = Dict(dict=options).store()
    builder.wf_parameters = Dict(dict=wf_parameters).store()
    builder.fleur = fleur_local_code
    #print(builder)

    with with_export_cache('fleur_scf_remote_Si_converged.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)
    assert node.is_finished_ok
    # check output
    n = out['output_scf_wc_para']
    n = n.get_dict()
    lasto = out['last_calc']['output_parameters']
    calc = lasto.get_incoming().all()[0].node
    print(calc)
    print(calc.get_cache_source())
    lasto = lasto.get_dict()

    print(n)
    #get kmax and minDistance
    assert abs(n.get('distance_charge') - 4.122e-07) < 2.0e-7
    assert n.get('errors') == []
    assert len(n['distance_charge_all']) == 1

    #Test that the provenance is being kept for the fleurinp output
    assert 'fleurinp' in out
    #This should be the calcfunction that creates the fleurinp from the remote data
    assert out['fleurinp'].creator.inputs.original.creator is not None
    assert out['fleurinp'].creator.inputs.original.creator.inputs.remote_node.uuid == builder.remote_data.uuid


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_scf_validation_wrong_inputs(fleur_local_code, inpgen_local_code, create_fleurinp, generate_structure2,
                                           clear_database):
    """
    Test the validation behavior of FleurScfWorkchain if wrong input is provided it should throw
    an exitcode and not start a Fleur run or crash
    """

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

    calc_parameters = Dict({})
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
    builder_struc_fleurinp.fleur = fleur_local_code
    builder_struc_fleurinp.inpgen = inpgen_local_code

    # 2. create builder structure no inpgen given
    builder_no_inpgen = FleurScfWorkChain.get_builder()
    builder_no_inpgen.structure = structure
    builder_no_inpgen.options = options
    builder_no_inpgen.fleur = fleur_local_code

    # 3. create builder no fleur code given
    builder_no_fleur = FleurScfWorkChain.get_builder()
    builder_no_fleur.structure = structure
    builder_no_fleur.options = options
    builder_no_fleur.inpgen = inpgen_local_code

    # 4. wrong code given (here we swap)
    builder_wrong_code = FleurScfWorkChain.get_builder()
    builder_wrong_code.structure = structure
    builder_wrong_code.options = options
    builder_wrong_code.inpgen = fleur_local_code
    builder_wrong_code.fleur = inpgen_local_code

    # 5. create builder fleurinp and calc_parameter given

    builder_calc_para_fleurinp = FleurScfWorkChain.get_builder()
    builder_calc_para_fleurinp.calc_parameters = calc_parameters
    builder_calc_para_fleurinp.fleurinp = fleurinp
    builder_calc_para_fleurinp.options = options
    builder_calc_para_fleurinp.fleur = fleur_local_code
    builder_calc_para_fleurinp.inpgen = inpgen_local_code

    ###################
    # now run the buidlers all should fail early with exit codes

    # 1. structure and fleurinp given
    out, node = run_get_node(builder_struc_fleurinp)
    assert out == {}
    assert node.is_finished
    assert not node.is_finished_ok
    assert node.exit_status == 231

    # 2. structure and no inpgen given
    out, node = run_get_node(builder_no_inpgen)
    assert out == {}
    assert node.is_finished
    assert not node.is_finished_ok
    assert node.exit_status == 231

    # 3. no fleur code given, since not optional input,
    # caught by aiida during creation
    with pytest.raises(ValueError) as e_info:
        out, node = run_get_node(builder_no_fleur)

    # 4. wrong code type given
    out, node = run_get_node(builder_wrong_code)
    assert out == {}
    assert node.is_finished
    assert not node.is_finished_ok
    assert node.exit_status == 233

    # 5. calc_parameter and fleurinp given
    out, node = run_get_node(builder_calc_para_fleurinp)
    assert out == {}
    assert node.is_finished
    assert not node.is_finished_ok
    assert node.exit_status == 231
