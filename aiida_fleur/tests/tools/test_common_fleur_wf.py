from __future__ import absolute_import
import pytest
import os


# is_code
def test_is_code_interface(aiida_profile, fixture_code):
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

    inputs = {'code': 'code', 'remote': 'remote', 'fleurinp': 'fleurinp',
              'options': {'custom_scheduler_commands' : 'test_command'}, 'label': 'label',
              'description': 'description', 'settings': {'test' : 1}, 'serial': False}

    results = get_inputs_fleur(**inputs)

    out_options = results['options'].get_dict()
    out_settings = results['settings'].get_dict()

    assert results['code'] == 'code'
    assert results['fleurinpdata'] == 'fleurinp'
    assert results['parent_folder'] == 'remote'
    assert results['description'] == 'description'
    assert results['label'] == 'label'
    assert out_options == {'custom_scheduler_commands': 'test_command\ncat /proc/meminfo > memory_avail.txt',
                           'withmpi' : True}
    assert out_settings == {'test' : 1}

    inputs = {'code': 'code', 'remote': 'remote', 'fleurinp': 'fleurinp',
              'options': {'custom_scheduler_commands' : 'test_command'}, 'serial': True}

    results = get_inputs_fleur(**inputs)

    out_options = results['options'].get_dict()

    assert results['description'] == ''
    assert results['label'] == ''
    assert out_options == {'custom_scheduler_commands' : 'test_command\ncat /proc/meminfo > memory_avail.txt',
                           'withmpi' : False, 'resources' : {"num_machines": 1}}

def test_get_inputs_inpgen(aiida_profile, fixture_code, generate_structure):
    '''
    Tests if get_inputs_fleur assembles inputs correctly.
    Note it is the work of FleurinputgenCalculation
    to check if input types are correct i.e. 'code' is a Fleur code etc.
    '''
    from aiida_fleur.tools.common_fleur_wf import get_inputs_inpgen
    from aiida.orm import Dict

    code = fixture_code('fleur.inpgen')
    structure = generate_structure()

    params = Dict(dict={'test' : 1})

    inputs = {'structure' : structure, 'inpgencode' : code, 'options' : {},
              'label' : 'label', 'description' : 'description',
              'params': params}
    returns = {'metadata' : {
                    'options' : {'withmpi': False, 'resources': {'num_machines': 1}},
                    'description' : 'description', 'label' : 'label'},
               'code' : code, 'parameters' : params, 'structure' : structure}

    assert get_inputs_inpgen(**inputs) == returns

    # repeat without a label and description
    inputs = {'structure' : structure, 'inpgencode' : code, 'options' : {},
              'params': params}
    returns = {'metadata' : {
                    'options' : {'withmpi': False, 'resources': {'num_machines': 1}},
                    'description' : '', 'label' : ''},
               'code' : code, 'parameters' : params, 'structure' : structure}

    assert get_inputs_inpgen(**inputs) == returns

@pytest.mark.skip(reason="Test not implemented")
def test_get_scheduler_extras():
    from aiida_fleur.tools.common_fleur_wf import get_scheduler_extras

# test_and_get_codenode
def test_test_and_get_codenode_inpgen(aiida_profile, clear_database, fixture_code):
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
    assert str(msg.value) == ("Given Code node is not of expected code type.\n"
                              "Valid labels for a fleur.fleur executable are:\n"
                              "* fleur_test@localhost-test")
    
    with pytest.raises(ValueError) as msg:
        test_and_get_codenode(code, not_existing, use_exceptions=True)
    assert str(msg.value) == ("Code not valid, and no valid codes for fleur.not_existing.\n"
                              "Configure at least one first using\n"
                              "    verdi code setup")

def test_get_kpoints_mesh_from_kdensity(aiida_profile, generate_structure):
    from aiida_fleur.tools.common_fleur_wf import get_kpoints_mesh_from_kdensity
    from aiida.orm import KpointsData

    a, b = get_kpoints_mesh_from_kdensity(generate_structure(), 0.1)
    assert a == ([21, 21, 21], [0.0, 0.0, 0.0])
    assert isinstance(b, KpointsData)

@pytest.mark.skip(reason="Test not implemented")
def test_determine_favorable_reaction():
    from aiida_fleur.tools.common_fleur_wf import determine_favorable_reaction

@pytest.mark.skip(reason="There seems to be now way to add outputs to CalcJobNode")
def test_performance_extract_calcs(aiida_profile, clear_database, fixture_localhost,
                                   generate_calc_job_node):
    from aiida_fleur.tools.common_fleur_wf import performance_extract_calcs
    from aiida.orm import Dict
    out = Dict(dict={})

    computer = fixture_localhost
    calc_job = generate_calc_job_node('fleur.fleur', computer, inputs={'test' : out})

    print(calc_job.get_outgoing().all())
    print(calc_job.get_incoming().all())

@pytest.mark.skip(reason="The optimize_calc_options function will be refactored soon")
def test_optimize_calc_options():
    from aiida_fleur.tools.common_fleur_wf import optimize_calc_options


@pytest.mark.skip(reason="There seems to be now way to add outputs to CalcJobNode")
def test_find_last_in_restart():
    from aiida_fleur.tools.common_fleur_wf import find_last_in_restart
