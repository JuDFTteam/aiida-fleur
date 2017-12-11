import pytest

# get_natoms_element
def test_get_natoms_element_Be2W():
    from aiida_fleur.tools.common_fleur_wf_util import get_natoms_element
    
    assert get_natoms_element('Be2W') == {'Be' : 2, 'W' : 1}

# get_atomprocent
def test_get_atomprocent_Be24W2():
    from aiida_fleur.tools.common_fleur_wf_util import get_atomprocent
    assert get_atomprocent('Be24W2') == {'Be': 24./26., 'W' : 2./26.}



# get_weight_procent

# determine_formation_energy

# get_scheduler_extras

