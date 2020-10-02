# -*- coding: utf-8 -*-
'''Contains tests for functions in common_aiida'''

from __future__ import absolute_import

import os
import json
import pytest


def test_create_group(capsys):
    'Test group creation'
    from aiida_fleur.tools.common_aiida import create_group
    from aiida.orm import Group, Dict

    para = Dict(dict={})
    para.store()
    group = create_group(name='test_group', nodes=[para.pk, 'not-existent-uuid'], description='test_description')

    captured = capsys.readouterr()

    assert captured.out == ('Group created with PK=1 and name test_group\n'
                            'Skipping not-existent-uuid, it does not exist in the DB\n'
                            'added nodes: [{}] to group test_group 1\n'.format(para.pk))

    para2 = para.clone()
    para2.store()
    group = create_group(name='test_group', nodes=[para2], add_if_exist=False)

    captured = capsys.readouterr()
    assert captured.out == ('Group with name test_group and pk 1 already exists.\n'
                            'Nodes were not added to the existing group test_group\n')

    group = create_group(name='test_group', nodes=[para2], add_if_exist=True)

    captured = capsys.readouterr()

    assert captured.out == ('Group with name test_group and pk 1 already exists.\n'
                            'Adding nodes to the existing group test_group\n'
                            'added nodes: [{}] to group test_group 1\n'.format(para2.pk))

    assert isinstance(group, Group)

    list_uuid = [x.uuid for x in group.nodes]
    assert para2.uuid in list_uuid
    assert para.uuid in list_uuid
    assert len(list_uuid) == 2


def test_export_extras(temp_dir):
    """Test exporting extras to json file"""
    from aiida_fleur.tools.common_aiida import export_extras
    from aiida.orm import Dict

    test_pk = []
    for i in range(3):
        test_dict = Dict(dict={})
        test_dict.store()
        test_dict.set_extra('test_extra', i)
        test_pk.append(test_dict.pk)

    extra_filename = os.path.join(temp_dir, 'node_extras.txt')
    export_extras(test_pk, extra_filename)

    with open(extra_filename) as json_file:
        data = json.load(json_file)

    test_extras = [x['test_extra'] for x in data.values()]

    assert len(data) == 3
    assert all(x in test_extras for x in [0, 1, 2])


def test_import_extras(temp_dir, capsys):
    """Test importing extras from json file"""
    from aiida_fleur.tools.common_aiida import export_extras, import_extras
    from aiida.orm import Dict

    test_dict = Dict(dict={})
    test_dict.store()

    extra_filename = os.path.join(temp_dir, 'node_extras.txt')
    export_extras([test_dict.pk], extra_filename)

    with open(extra_filename) as json_file:
        data = json.load(json_file)

    existent_uuid = list(data.keys())[0]
    data[existent_uuid]['test_extra'] = 'test data'
    data['not_existent_uuid'] = {}
    data['not_existent_uuid']['test_extra'] = 'data to be not written'

    with open(extra_filename, 'w') as json_file:
        json.dump(data, json_file)

    import_extras(extra_filename)

    assert test_dict.get_extra('test_extra') == 'test data'

    captured = capsys.readouterr()
    assert captured.out == 'node with uuid not_existent_uuid does not exist in DB\n'

    empty_file = os.path.join(temp_dir, 'empty_file')
    open(empty_file, 'w').close()
    import_extras(empty_file)

    captured = capsys.readouterr()
    assert captured.out == ('The file has to be loadable by json. i.e json format' ' (which it is not).\n')


'''
# FIXME
def test_delete_trash(monkeypatch):
    """Test removing trash nodes from the DB. Also covers delete_nodes."""
    from aiida_fleur.tools.common_aiida import delete_trash
    from aiida.orm import Dict, load_node
    from aiida.common.exceptions import NotExistent

    test_dict = Dict(dict={})
    test_dict.store()
    uuid_test = test_dict.uuid

    test_dict.set_extra('trash', True)

    monkeypatch.setattr('aiida_fleur.tools.common_aiida.input', lambda: 'y')
    delete_trash()

    try:
        load_node(uuid_test)
    except NotExistent:
        pass
    else:
        assert 0
'''


def test_get_nodes_from_group():
    """Test retrieving nodes from a given group."""
    from aiida_fleur.tools.common_aiida import get_nodes_from_group
    from aiida_fleur.tools.common_aiida import create_group

    from aiida.orm import Dict

    test_pk = []
    for i in range(3):
        test_dict = Dict(dict={})
        test_dict.store()
        test_pk.append(test_dict.pk)

    group = create_group(name='test_group', nodes=test_pk, description='test_description')

    w = get_nodes_from_group(group, return_format='uuid')
    assert len(w) == 3
    assert all([isinstance(x, str) for x in w])

    w = get_nodes_from_group(group, return_format='pk')
    assert len(w) == 3
    assert all(x in test_pk for x in w)

    with pytest.raises(ValueError) as excinfo:
        w = get_nodes_from_group(group, return_format='will_raise_a_ValueError')

    assert str(excinfo.value) == "return_format should be 'uuid' or 'pk'."
