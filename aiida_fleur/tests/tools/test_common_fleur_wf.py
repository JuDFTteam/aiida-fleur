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
'''Contains tests for workfunction helpers in common_fleur_wf.py'''
from __future__ import absolute_import
import pytest
import os


# is_code
def test_is_code_interface(fixture_code):
    from aiida_fleur.tools.common_fleur_wf import is_code

    assert is_code('random_string') is None
    assert is_code('fleur.inpGUT') is None
    assert is_code(99999) is None

    code = fixture_code('fleur.inpgen')
    code.store()

    assert is_code(code.uuid)
    assert is_code(code.pk)
    assert is_code('@'.join([code.label, code.get_computer_name()]))
    assert is_code(code)


def test_get_inputs_fleur():
    '''
    Tests if get_inputs_fleur assembles inputs correctly.
    Note it is the work of FleurCalculation
    to check if input types are correct i.e. 'code' is a Fleur code etc.
    '''
    from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
    from aiida.orm import Dict

    inputs = {
        'code': 'code',
        'remote': 'remote',
        'fleurinp': 'fleurinp',
        'options': {
            'custom_scheduler_commands': 'test_command'
        },
        'label': 'label',
        'description': 'description',
        'settings': {
            'test': 1
        },
        'serial': False
    }

    results = get_inputs_fleur(**inputs)

    out_options = results['options'].get_dict()
    out_settings = results['settings'].get_dict()

    assert results['code'] == 'code'
    assert results['fleurinpdata'] == 'fleurinp'
    assert results['parent_folder'] == 'remote'
    assert results['description'] == 'description'
    assert results['label'] == 'label'
    assert out_options == {'custom_scheduler_commands': 'test_command', 'withmpi': True}
    assert out_settings == {'test': 1}

    inputs = {
        'code': 'code',
        'remote': 'remote',
        'fleurinp': 'fleurinp',
        'options': {
            'custom_scheduler_commands': 'test_command'
        },
        'serial': True
    }

    results = get_inputs_fleur(**inputs)

    out_options = results['options'].get_dict()

    assert results['description'] == ''
    assert results['label'] == ''
    assert out_options == {
        'custom_scheduler_commands': 'test_command',
        'withmpi': False,
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        }
    }


def test_get_inputs_inpgen(fixture_code, generate_structure):
    '''
    Tests if get_inputs_fleur assembles inputs correctly.
    Note it is the work of FleurinputgenCalculation
    to check if input types are correct i.e. 'code' is a Fleur code etc.
    '''
    from aiida_fleur.tools.common_fleur_wf import get_inputs_inpgen
    from aiida.orm import Dict

    code = fixture_code('fleur.inpgen')
    structure = generate_structure()

    params = Dict(dict={'test': 1})

    inputs = {
        'structure': structure,
        'inpgencode': code,
        'options': {},
        'label': 'label',
        'description': 'description',
        'params': params
    }
    returns = {
        'metadata': {
            'options': {
                'withmpi': False,
                'resources': {
                    'num_machines': 1,
                    'num_mpiprocs_per_machine': 1
                }
            },
            'description': 'description',
            'label': 'label'
        },
        'code': code,
        'parameters': params,
        'structure': structure
    }

    assert get_inputs_inpgen(**inputs) == returns

    # repeat without a label and description
    inputs = {'structure': structure, 'inpgencode': code, 'options': {}, 'params': params}
    returns = {
        'metadata': {
            'options': {
                'withmpi': False,
                'resources': {
                    'num_machines': 1,
                    'num_mpiprocs_per_machine': 1
                }
            },
            'description': '',
            'label': ''
        },
        'code': code,
        'parameters': params,
        'structure': structure
    }

    assert get_inputs_inpgen(**inputs) == returns


@pytest.mark.skip(reason='Test is not implemented')
def test_get_scheduler_extras():
    from aiida_fleur.tools.common_fleur_wf import get_scheduler_extras


# test_and_get_codenode


def test_test_and_get_codenode_inpgen(fixture_code):
    from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
    from aiida.orm import Code
    from aiida.common.exceptions import NotExistent

    # install code setup code
    code = fixture_code('fleur.inpgen')
    code_fleur = fixture_code('fleur.fleur')
    code_fleur.label = 'fleur_test'
    code_fleur.store()

    expected = 'fleur.inpgen'
    nonexpected = 'fleur.fleur'
    not_existing = 'fleur.not_existing'

    assert isinstance(test_and_get_codenode(code, expected), Code)
    with pytest.raises(ValueError) as msg:
        test_and_get_codenode(code, nonexpected, use_exceptions=True)
    assert str(msg.value) == ('Given Code node is not of expected code type.\n'
                              'Valid labels for a fleur.fleur executable are:\n'
                              '* fleur_test@localhost-test')

    with pytest.raises(ValueError) as msg:
        test_and_get_codenode(code, not_existing, use_exceptions=True)
    assert str(msg.value) == ('Code not valid, and no valid codes for fleur.not_existing.\n'
                              'Configure at least one first using\n'
                              '    verdi code setup')


def test_get_kpoints_mesh_from_kdensity(generate_structure):
    from aiida_fleur.tools.common_fleur_wf import get_kpoints_mesh_from_kdensity
    from aiida.orm import KpointsData

    a, b = get_kpoints_mesh_from_kdensity(generate_structure(), 0.1)
    assert a == ([21, 21, 21], [0.0, 0.0, 0.0])
    assert isinstance(b, KpointsData)


@pytest.mark.skip(reason='Test is not implemented')
def test_determine_favorable_reaction():
    from aiida_fleur.tools.common_fleur_wf import determine_favorable_reaction


# @pytest.mark.skip(reason="There seems to be now way to add outputs to CalcJobNode")


def test_performance_extract_calcs(fixture_localhost, generate_calc_job_node):
    from aiida_fleur.tools.common_fleur_wf import performance_extract_calcs
    from aiida.common.links import LinkType
    from aiida.orm import Dict
    out = Dict(
        dict={
            'title': 'A Fleur input generator calculation with aiida',
            'energy': -138529.7052157,
            'bandgap': 6.0662e-06,
            'end_date': {
                'date': '2019/11/12',
                'time': '16:12:08'
            },
            'unparsed': [],
            'walltime': 43,
            'warnings': {
                'info': {},
                'debug': {},
                'error': {},
                'warning': {}
            },
            'start_date': {
                'date': '2019/11/12',
                'time': '16:11:25'
            },
            'parser_info': 'AiiDA Fleur Parser v0.2beta',
            'CalcJob_uuid': '3dc62d43-b607-4415-920f-e0d34e805711',
            'creator_name': 'fleur 30',
            'energy_units': 'eV',
            'kmax': 4.2,
            'fermi_energy': 0.0605833326,
            'spin_density': 0.0792504665,
            'bandgap_units': 'eV',
            'force_largest': 0.0,
            'energy_hartree': -5090.8728101494,
            'walltime_units': 'seconds',
            'charge_density1': 0.0577674505,
            'charge_density2': 0.0461840944,
            'number_of_atoms': 4,
            'parser_warnings': [],
            'magnetic_moments': [3.3720063737, 3.3719345944, 3.3719329177, 3.3719329162],
            'number_of_kpoints': 8,
            'number_of_species': 1,
            'fermi_energy_units': 'Htr',
            'sum_of_eigenvalues': -2973.4129786677,
            'output_file_version': '0.27',
            'energy_hartree_units': 'Htr',
            'number_of_atom_types': 4,
            'number_of_iterations': 11,
            'number_of_symmetries': 8,
            'energy_core_electrons': -2901.8120489845,
            'magnetic_moment_units': 'muBohr',
            'overall_charge_density': 0.0682602474,
            'creator_target_structure': ' ',
            'energy_valence_electrons': -71.6009296831,
            'magnetic_spin_up_charges': [9.1494766577, 9.1494806151, 9.1494806833, 9.1494806834],
            'orbital_magnetic_moments': [],
            'density_convergence_units': 'me/bohr^3',
            'number_of_spin_components': 2,
            'charge_den_xc_den_integral': -223.295208608,
            'magnetic_spin_down_charges': [5.777470284, 5.7775460208, 5.7775477657, 5.7775477672],
            'number_of_iterations_total': 11,
            'creator_target_architecture': 'GEN',
            'orbital_magnetic_moment_units': 'muBohr',
            'orbital_magnetic_spin_up_charges': [],
            'orbital_magnetic_spin_down_charges': []
        })
    out.store()

    node = generate_calc_job_node('fleur.fleur', fixture_localhost)
    node.store()

    out.add_incoming(node, link_type=LinkType.CREATE, link_label='output_parameters')

    result = performance_extract_calcs([node.pk])

    assert result == {
        'n_symmetries': [8],
        'n_spin_components': [2],
        'n_kpoints': [8],
        'n_iterations': [11],
        'walltime_sec': [43],
        'walltime_sec_per_it': [3.909090909090909],
        'n_iterations_total': [11],
        'density_distance': [0.0682602474],
        'computer': ['localhost-test'],
        'n_atoms': [4],
        'kmax': [4.2],
        'cost': [75866.11200000001],
        'costkonstant': [147.02734883720933],
        'walltime_sec_cor': [43],
        'total_cost': [834527.2320000001],
        'fermi_energy': [0.0605833326],
        'bandgap': [6.0662e-06],
        'energy': [-138529.7052157],
        'force_largest': [0.0],
        'ncores': [12],
        'pk': [node.pk],
        'uuid': [node.uuid],
        'serial': [False],
        'resources': [{
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        }]
    }


inputs_optimize = [(4, 8, 3, True, 0.5, None, 720), (4, 8, 3, True, 2, None, 720), (4, 8, 3, True, 100, None, 720),
                   (4, 8, 3, True, 100, None, 720, 0.5), (4, 8, 3, False, 0.5, None, 720)]

results_optimize = [
    (4, 4, 6, 'Computational setup is perfect! Nodes: 4, MPIs per node 4, OMP per MPI 6. Number of k-points is 720'),
    (4, 6, 4, 'Computational setup is perfect! Nodes: 4, MPIs per node 6, OMP per MPI 4. Number of k-points is 720'),
    (4, 12, 2, 'Computational setup is perfect! Nodes: 4, MPIs per node 12, OMP per MPI 2. Number of k-points is 720'),
    (3, 24, 1, 'WARNING: Changed the number of nodes from 4 to 3'),
    (4, 20, 1,
     'WARNING: Changed the number of MPIs per node from 8 to 20 and OMP from 3 to 1. Changed the number of nodes from 4 to 4. Number of k-points is 720.'
     )
]


@pytest.mark.parametrize('inputs,result_correct', zip(inputs_optimize, results_optimize))
def test_optimize_calc_options(inputs, result_correct):
    from aiida_fleur.tools.common_fleur_wf import optimize_calc_options

    result = optimize_calc_options(*inputs)
    assert result == result_correct


def test_find_last_submitted_calcjob(fixture_localhost, generate_calc_job_node, generate_work_chain_node):
    from aiida_fleur.tools.common_fleur_wf import find_last_submitted_calcjob
    from aiida.common.links import LinkType
    from aiida.common.exceptions import NotExistent

    node1 = generate_calc_job_node('fleur.fleur', fixture_localhost)
    node2 = generate_calc_job_node('fleur.fleur', fixture_localhost)
    node3 = generate_calc_job_node('fleur.fleur', fixture_localhost)

    node_main = generate_work_chain_node('fleur.base_relax', fixture_localhost)
    node_main.store()

    with pytest.raises(NotExistent):
        result = find_last_submitted_calcjob(node_main)

    node1.add_incoming(node_main, link_type=LinkType.CALL_CALC, link_label='CALL')
    node2.add_incoming(node_main, link_type=LinkType.CALL_CALC, link_label='CALL')
    node3.add_incoming(node_main, link_type=LinkType.CALL_CALC, link_label='CALL')

    node1.store()
    node2.store()
    node3.store()

    result = find_last_submitted_calcjob(node_main)

    assert result == node3.uuid


def test_find_last_submitted_workchain(fixture_localhost, generate_work_chain_node):
    from aiida_fleur.tools.common_fleur_wf import find_last_submitted_workchain
    from aiida.common.links import LinkType
    from aiida.common.exceptions import NotExistent

    node1 = generate_work_chain_node('fleur.base_relax', fixture_localhost)
    node2 = generate_work_chain_node('fleur.base_relax', fixture_localhost)
    node3 = generate_work_chain_node('fleur.base_relax', fixture_localhost)

    node_main = generate_work_chain_node('fleur.base_relax', fixture_localhost)

    node1.add_incoming(node_main, link_type=LinkType.CALL_WORK, link_label='CALL')
    node2.add_incoming(node_main, link_type=LinkType.CALL_WORK, link_label='CALL')
    node3.add_incoming(node_main, link_type=LinkType.CALL_WORK, link_label='CALL')

    node_main.store()
    node1.store()
    node2.store()
    node3.store()

    result = find_last_submitted_workchain(node_main)

    assert result == node3.uuid
