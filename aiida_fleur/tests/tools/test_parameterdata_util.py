

# dict_merger
def test_dict_merger_interface_dicts_lists_str_int():
    from aiida_fleur.tools.ParameterData_util import dict_merger

    dict1 = {'a1' : {'b1' : [1]}}
    dict2 = {'a1' : {'b1': [2,3]}}
    assert dict_merger(dict1, dict2) == {'a1' : {'b1' : [1,2,3]}}

    dict3 = {'a1' : {'b2' : 1}}
    dict4 = {'a1' : {'b2' : 1}}
    assert dict_merger(dict3, dict4) == {'a1' : {'b2' : 2}}
    
    dict5 = {'a1' : {'b3' : 'a'}}
    dict6 = {'a1' : {'b3' : 'b' }, 'a2': [1]}
    assert dict_merger(dict5, dict6) == {'a1' : {'b3' : 'ab'}, 'a2' : [1]}


# extract_elementpara
def test_extract_elementpara_interface_W():
    from aiida_fleur.tools.ParameterData_util import extract_elementpara

    para_dict = {'a' : 1, 'atom' : {'element' : 'H', 'rmt': 1}, 'atom1' : {'element' : 'W', 'rmt' : 4}}
    assert extract_elementpara(para_dict, 'W') == {'a' : 1, 'atom1' : {'element' : 'W', 'rmt' : 4}}

