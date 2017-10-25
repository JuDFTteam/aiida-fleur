#!/usr/bin/env python
# -*- coding: utf-8 -*-


#    aiida_profile.reset_db()
#    
#def test_my_stuff(test_data):
#   # run a test
#   print('test_my_stuf works')

#class TestAiida_fleur_entrypoints:
#    """
#    tests all the entry points of the Fleur plugin. Therefore if the plugin is reconized by AiiDA 
#    and installed right. 
#    """
#    #@pytest.mark.usefixtures(aiida_profile)
def test_inpgen_calculation_entry_point(aiida_profile):
   from aiida.orm import CalculationFactory
   inpgen_calculation = CalculationFactory('fleur.inpgen')
   assert inpgen_calculation is not None

def test_fleur_calculation_entry_point(aiida_profile):
    from aiida.orm import CalculationFactory
    fleur_calculation = CalculationFactory('fleur.fleur')
    assert fleur_calculation is not None

def test_fleur_fleurinpdata_entry_point(aiida_profile):
    from aiida.orm import DataFactory
    fleurinp = DataFactory('fleur.fleurinp')
    assert fleurinp is not None

