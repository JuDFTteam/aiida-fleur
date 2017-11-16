import pytest


# is_code
def test_is_code_interface():
    from aiida.orm import Code, load_node
    from aiida_fleur.tools.common_fleur_wf import is_code
    from aiida.common.exceptions import NotExistent
    
    with pytest.raises(NotExistent):
        is_code(Code)
    
    #inpgen has to be stored in db
    # maybe do a verdi code setup
    #code_uuid = load_node(1).uuid
    #code_pk = 1
    #code_name = 'inpgen'
    
    #assert is_code(code_uuid)
    #assert is_code(code_pk)
    #assert is_code(code_name)


# get_inputs_fleur
def test_get_inputs_fleur_interface():
    from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
    
    code = 'code'
    fleurinp = 'fleurinp'
    remote = 'remote'
    options = {}
    label = 'test'
    description = 'test des'
    inputs = {'code' : code, 'fleurinp' :  fleurinp, 'remote' : remote, 'options' : options, 'label' : label, 'description' : description}
    returns = {'_description' : 'test des', '_label' : 'test', '_options' : {}, '_store_provenance' : True,
                'code' : 'code', 'dynamic' : None, 'fleurinpdata' : 'fleurinp', 'parent_folder' : 'remote', 'settings' : None}
    assert get_inputs_fleur(**inputs) == returns


# get_inputs_inpgen
def test_get_inputs_inpgen_interface():
    from aiida_fleur.tools.common_fleur_wf import get_inputs_inpgen

    structure = 'structure'
    code = 'inpgencode'
    options = {}
    label = 'test'
    description = 'test des'
    inputs = {'structure' : structure, 'inpgencode' : code, 'options' : options, 'label' : label, 'description' : description}
    returns = {'_description' : 'test des', '_label' : 'test', '_options' : {'withmpi': False, 'resources': {'num_machines': 1}},
               '_store_provenance' : True, 'code' : 'inpgencode', 'dynamic' : None, 'parameters' : None, 'settings' : None, 'structure' : 'structure'}
    assert get_inputs_inpgen(**inputs) == returns


# get_natoms_element
def test_get_natoms_element_Be2W():
    from aiida_fleur.tools.common_fleur_wf import get_natoms_element
    
    assert get_natoms_element('Be2W') == {'Be' : 2, 'W' : 1}

# get_atomprocent
def test_get_atomprocent_Be24W2():
    from aiida_fleur.tools.common_fleur_wf import get_atomprocent
    assert get_atomprocent('Be24W2') == {'Be': 24./26., 'W' : 2./26.}



# get_weight_procent

# determine_formation_energy

# get_scheduler_extras

# test_and_get_codenode
def test_test_and_get_codenode_inpgen():
    from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
    from aiida.orm import Code
    from aiida.common.exceptions import NotExistent

    # install code setup code
    code = Code(input_plugin_name='fleur.inpgen')
    code.label = 'inpgen'
    #code = Code.get_from_string('inpgen@localhost')
    expected = 'fleur.inpgen'
    nonexpected = 'fleur.fleur'
    
    assert isinstance(test_and_get_codenode(code, expected), Code)
    with pytest.raises(ValueError) as msg:
        test_and_get_codenode(code, nonexpected, use_exceptions=True)
    assert 'Code not valid' in str(msg)
