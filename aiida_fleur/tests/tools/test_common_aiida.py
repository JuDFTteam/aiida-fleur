from __future__ import absolute_import


def test_create_group(aiida_profile, clear_database, capsys):
    "Test group creation"
    from aiida_fleur.tools.common_aiida import create_group
    from aiida.orm import Group, Dict

    para = Dict(dict={})
    para.store()
    group = create_group(name='test_group', nodes=[para.pk, 'not-existent-uuid'],
                         description='test_description')

    captured = capsys.readouterr()

    assert captured.out == ('Group created with PK=1 and name test_group\n'
                            'Skipping not-existent-uuid, it does not exist in the DB\n'
                            'added nodes: [1] to group test_group 1\n')

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
                            'added nodes: [2] to group test_group 1\n')

    assert isinstance(group, Group)

    list_uuid = [x.uuid for x in group.nodes]
    assert para2.uuid in list_uuid
    assert para.uuid in list_uuid
    assert len(list_uuid) == 2


def test_export_extras(aiida_profile, clear_database, fixture_sandbox):
    """Test exporting extras to json file"""
    from aiida_fleur.tools.common_aiida import export_extras
    from aiida.orm import Dict

    test_dict = Dict(dict={})
    test_dict.store()

    test_dict2 = Dict(dict={})
    test_dict2.store()

    test_dict3 = Dict(dict={})
    test_dict3.store()

    

# get_nodes_from_group
#def test_get_nodes_from_group_uuidlist():
#    pass

