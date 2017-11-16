
# export_extras
#def test_export_extras():
#    pass

# import_extras

# create_group
def test_create_group():
   from aiida_fleur.tools.common_aiida import create_group
   from aiida.orm import DataFactory, Group
   ParameterData = DataFactory('parameter')

   para = ParameterData(dict={})
   # para.store()
   group = create_group([para.pk], 'test_group')
    
   assert isinstance(group, Group)
   # assert 


# get_nodes_from_group
#def test_get_nodes_from_group_uuidlist():
#    pass

