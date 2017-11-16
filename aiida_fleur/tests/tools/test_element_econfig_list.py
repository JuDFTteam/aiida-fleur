

# get_econfig
def test_get_econfig_W():
    from aiida_fleur.tools.element_econfig_list import get_econfig

    assert get_econfig('W', full=False) == '[Kr] 4d10 4f14 5p6 | 5s2 6s2 5d4'
    assert get_econfig('W', full=True) == '1s2 2s2 2p6 3s2 3p6 3d10 4s2 4p6 4d10 4f14 5p6 | 5s2 6s2 5d4'

# get_coreconfig
def test_get_coreconfig_W():
    from aiida_fleur.tools.element_econfig_list import get_coreconfig
    
    assert get_coreconfig('W', full=False) == '[Kr] 4d10 4f14 5p6'
    assert get_coreconfig('W', full=True) == '1s2 2s2 2p6 3s2 3p6 3d10 4s2 4p6 4d10 4f14 5p6'

# rek_econ
def test_rek_econ_interface_W():
    from aiida_fleur.tools.element_econfig_list import rek_econ

    assert rek_econ('[Kr] 4d10 4f14 5p6 | 5s2 6s2 5d4') == '1s2 2s2 2p6 3s2 3p6 3d10 4s2 4p6 4d10 4f14 5p6 | 5s2 6s2 5d4'


# highest_unocc_valence
def test_rek_econ_interface_W():
    from aiida_fleur.tools.element_econfig_list import highest_unocc_valence
    assert highest_unocc_valence('[Kr] 4d10 4f14 5p6 | 5s2 6s2 5d4') == '5d4'
    assert highest_unocc_valence('1s2 | 2s2') == '2p0' 

# econfig_str_hole
def test_econfig_str_hole_1s_Be():
    from aiida_fleur.tools.element_econfig_list import econfigstr_hole
    
    assert econfigstr_hole('1s2 | 2s2', '1s2', '2p0') == '1s1 | 2s2 2p1'


# get_state_occ

def test_get_state_occ_interface_half_valence_hole_W():
    from aiida_fleur.tools.element_econfig_list import get_state_occ
    econfig = '1s2 2s2 2p6 3s2 3p6 3d10 4s2 4p6 4d10 4f13 5p6 | 5s2 6s2 5d5'
    assert get_state_occ(econfig, corehole='4f 5/2', valence='5d', ch_occ=0.5)[1] == {'state' : '(4f5/2)', 'spinUp' : 3.0, 'spinDown' : 2.5}
    assert get_state_occ(econfig, corehole='4f 5/2', valence='5d', ch_occ=0.5)[0] == {'state' : '(5d5/2)', 'spinUp' : 0.5, 'spinDown' : 0.0}
