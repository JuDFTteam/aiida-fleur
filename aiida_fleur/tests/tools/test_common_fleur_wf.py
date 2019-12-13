from __future__ import absolute_import
import pytest


# is_code
def test_is_code_interface():
    from aiida import load_profile
    from aiida.orm import Code, load_node
    import os
    from aiida_fleur.tools.common_fleur_wf import is_code

    load_profile()

    assert is_code('random_string') is None
    assert is_code('fleur.inpGUT') is None

    f = open("1.txt", "w")
    f.close()

    code = Code(input_plugin_name='fleur.inpgen', local_executable='1.txt', files=['1.txt'])
    code.store()

    code_uuid = code.uuid
    code_pk = code.pk
    code_name = ''

    assert is_code(code_uuid)
    assert is_code(code_pk)
    assert is_code(code_name)

    os.remove("1.txt")



'''uncommented these 2 tests because the process builder input None is not currently not == None...
# get_inputs_fleur
def test_get_inputs_fleur_interface():
    from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
    from aiida.orm import Code, DataFactory


    code = Code()#'code'
    fleurinp = DataFactory('fleur.fleurinp')()
    remote = DataFactory('remote')()
    options = {}
    label = 'test'
    description = 'test des'
    inputs = {'code' : code, 'fleurinp' :  fleurinp, 'remote' : remote, 'options' : options, 'label' : label, 'description' : description}
    returns = {'description' : 'test des', 'label' : 'test', 'options' : None, 'store_provenance' : True,
                'code' : code, 'fleurinpdata' : fleurinp, 'parent_folder' : remote, 'settings' : None}
    assert get_inputs_fleur(**inputs) == returns


# get_inputs_inpgen
def test_get_inputs_inpgen_interface():
    from aiida_fleur.tools.common_fleur_wf import get_inputs_inpgen
    from aiida.orm import Code, DataFactory

    structure = DataFactory('structure')()#'structure'
    code = Code()#'inpgencode'
    options = {}
    label = 'test'
    description = 'test des'
    inputs = {'structure' : structure, 'inpgencode' : code, 'options' : options, 'label' : label, 'description' : description}
    returns = {'description' : 'test des', 'label' : 'test', 'options' : {'withmpi': False, 'resources': {'num_machines': 1}},
               'store_provenance' : True, 'code' : code, 'parameters' : None, 'settings' : None, 'structure' : structure}
    assert get_inputs_inpgen(**inputs) == returns


'''
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
