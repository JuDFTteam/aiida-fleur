#!/usr/bin/env python
"""
You find the usual econfig for all elements in the periodic table.
"""
# TODO
# FLEUR econfig=[core states|valence states] 
# TODO add default los
econfiguration = {
    1: {'mass': 1.00794, 'name': 'Hydrogen', 'symbol': 'H', 'econfig': '1s1' },
    2: {'mass': 4.002602, 'name': 'Helium', 'symbol': 'He', 'econfig': '1s2'},
    3: {'mass': 6.941, 'name': 'Lithium', 'symbol': 'Li', 'econfig': '1s2 | 2s1'},
    4: {'mass': 9.012182, 'name': 'Beryllium', 'symbol': 'Be', 'econfig': '1s2 | 2s2'},
    5: {'mass': 10.811, 'name': 'Boron', 'symbol': 'B', 'econfig': '1s2 | 2s2 2p1'},
    6: {'mass': 12.0107, 'name': 'Carbon', 'symbol': 'C', 'econfig': '[He] 2s2 | 2p2'},
    7: {'mass': 14.0067, 'name': 'Nitrogen', 'symbol': 'N', 'econfig': '[He] 2s2 | 2p3'},
    8: {'mass': 15.9994, 'name': 'Oxygen', 'symbol': 'O', 'econfig': '[He] 2s2 | 2p4'},
    9: {'mass': 18.9984032, 'name': 'Fluorine', 'symbol': 'F', 'econfig': '[He] 2s2 | 2p5'},
    10: {'mass': 20.1797, 'name': 'Neon', 'symbol': 'Ne', 'econfig': '[He] 2s2 | 2p6'},
    11: {'mass': 22.98977, 'name': 'Sodium', 'symbol': 'Na', 'econfig': '[He] 2s2 | 2p6 3s1'},
    12: {'mass': 24.305, 'name': 'Magnesium', 'symbol': 'Mg', 'econfig': '[He] 2s2 | 2p6 3s2'},
    13: {'mass': 26.981538, 'name': 'Aluminium', 'symbol': 'Al', 'econfig': '[He] 2s2 2p6 | 3s2 3p1'},
    14: {'mass': 28.0855, 'name': 'Silicon', 'symbol': 'Si', 'econfig': '[He] 2s2 2p6 | 3s2 3p2'},
    15: {'mass': 30.973761, 'name': 'Phosphorus', 'symbol': 'P', 'econfig': '[He] 2s2 2p6 | 3s2 3p3'},
    16: {'mass': 32.065, 'name': 'Sulfur', 'symbol': 'S', 'econfig': '[He] 2s2 2p6 | 3s2 3p4'},
    17: {'mass': 35.453, 'name': 'Chlorine', 'symbol': 'Cl', 'econfig': '[He] 2s2 2p6 | 3s2 3p5'},
    18: {'mass': 39.948, 'name': 'Argon', 'symbol': 'Ar', 'econfig': '[He] 2s2 2p6 | 3s2 3p6'},
    19: {'mass': 39.0983, 'name': 'Potassium', 'symbol': 'K', 'econfig': '[Ne] 3s2 | 3p6 4s1 '},
    20: {'mass': 40.078, 'name': 'Calcium', 'symbol': 'Ca', 'econfig': '[Ne] 3s2 | 3p6 4s2 '},
    21: {'mass': 44.955912, 'name': 'Scandium', 'symbol': 'Sc', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d1'},
    22: {'mass': 47.867, 'name': 'Titanium', 'symbol': 'Ti', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d2'},
    23: {'mass': 50.9415, 'name': 'Vanadium', 'symbol': 'V', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d3'},
    24: {'mass': 51.9961, 'name': 'Chromium', 'symbol': 'Cr', 'econfig': '[Ne] 3s2 3p6 | 4s1 3d5'},
    25: {'mass': 54.938045, 'name': 'Manganese', 'symbol': 'Mn', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d5'},
    26: {'mass': 55.845, 'name': 'Iron', 'symbol': 'Fe', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d6'},
    27: {'mass': 58.933195, 'name': 'Cobalt', 'symbol': 'Co', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d7'},
    28: {'mass': 58.6934, 'name': 'Nickel', 'symbol': 'Ni', 'econfig': '[Ne] 3s2 3p6 | 4s2 3d8'},
    29: {'mass': 63.546, 'name': 'Copper', 'symbol': 'Cu', 'econfig': '[Ne] 3s2 3p6 |4s1 3d10'},
    30: {'mass': 65.38, 'name': 'Zinc', 'symbol': 'Zn', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2'},
    31: {'mass': 69.723, 'name': 'Gallium', 'symbol': 'Ga', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2 4p1'},
    32: {'mass': 72.64, 'name': 'Germanium', 'symbol': 'Ge', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2 4p2'},
    33: {'mass': 74.9216, 'name': 'Arsenic', 'symbol': 'As', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2 4p3'},
    34: {'mass': 78.96, 'name': 'Selenium', 'symbol': 'Se', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2 4p4'},
    35: {'mass': 79.904, 'name': 'Bromine', 'symbol': 'Br', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2 4p5'},
    36: {'mass': 83.798, 'name': 'Krypton', 'symbol': 'Kr', 'econfig': '[Ne] 3s2 3p6 | 3d10 4s2 4p6'},
    37: {'mass': 85.4678, 'name': 'Rubidium', 'symbol': 'Rb', 'econfig': '[Ar] 3d10 4s2 | 4p6 5s1'},
    38: {'mass': 87.62, 'name': 'Strontium', 'symbol': 'Sr', 'econfig': '[Ar] 3d10 4s2 | 4p6 5s2'},
    39: {'mass': 88.90585, 'name': 'Yttrium', 'symbol': 'Y', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s2 4d1'},
    40: {'mass': 91.224, 'name': 'Zirconium', 'symbol': 'Zr', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s2 4d2'},
    41: {'mass': 92.90638, 'name': 'Niobium', 'symbol': 'Nb', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s1 4d4'},
    42: {'mass': 95.96, 'name': 'Molybdenum', 'symbol': 'Mo', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s1 4d5'},
    43: {'mass': 98.0, 'name': 'Technetium', 'symbol': 'Tc', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s2 4d5'},
    44: {'mass': 101.07, 'name': 'Ruthenium', 'symbol': 'Ru', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s1 4d7'},
    45: {'mass': 102.9055, 'name': 'Rhodium', 'symbol': 'Rh', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s1 4d8'},
    46: {'mass': 106.42, 'name': 'Palladium', 'symbol': 'Pd', 'econfig': '[Ar] 4s2 3d10 4p6 | 4d10'},
    47: {'mass': 107.8682, 'name': 'Silver', 'symbol': 'Ag', 'econfig': '[Ar] 4s2 3d10 4p6 | 5s1 4d10'},
    48: {'mass': 112.411, 'name': 'Cadmium', 'symbol': 'Cd', 'econfig': '[Ar] 4s2 3d10 4p6 | 4d10 5s2'},
    49: {'mass': 114.818, 'name': 'Indium', 'symbol': 'In', 'econfig': '[Ar] 4s2 3d10 4p6 | 4d10 5s2 5p1'},
    50: {'mass': 118.71, 'name': 'Tin', 'symbol': 'Sn', 'econfig': '[Kr] 4d10 | 5s2 5p2'},
    51: {'mass': 121.76, 'name': 'Antimony', 'symbol': 'Sb', 'econfig': '[Kr] 4d10 | 5s2 5p3'},
    52: {'mass': 127.6, 'name': 'Tellurium', 'symbol': 'Te', 'econfig': '[Kr] 4d10 | 5s2 5p4'},
    53: {'mass': 126.90447, 'name': 'Iodine', 'symbol': 'I', 'econfig': '[Kr] 4d10 | 5s2 5p5'},
    54: {'mass': 131.293, 'name': 'Xenon', 'symbol': 'Xe', 'econfig': '[Kr] 4d10 | 5s2 5p6'},
    55: {'mass': 132.9054519, 'name': 'Caesium', 'symbol': 'Cs', 'econfig': '[Kr] 4d10 5s2 | 5p6 6s1'},
    56: {'mass': 137.327, 'name': 'Barium', 'symbol': 'Ba', 'econfig': '[Kr] 4d10 5s2 | 5p6 6s2'},
    57: {'mass': 138.90547, 'name': 'Lanthanum', 'symbol': 'La', 'econfig': '[Kr] 4d10 5s2 | 5p6 6s2 5d1'},
    58: {'mass': 140.116, 'name': 'Cerium', 'symbol': 'Ce', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f1 5d1'},
    59: {'mass': 140.90765, 'name': 'Praseodymium', 'symbol': 'Pr', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f3'},
    60: {'mass': 144.242, 'name': 'Neodymium', 'symbol': 'Nd', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f4'},
    61: {'mass': 145.0, 'name': 'Promethium', 'symbol': 'Pm', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f5'},
    62: {'mass': 150.36, 'name': 'Samarium', 'symbol': 'Sm', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f6'},
    63: {'mass': 151.964, 'name': 'Europium', 'symbol': 'Eu', 'econfig' : '[Kr] 4d10 | 4f7 5s2 5p6 6s2'},
    64: {'mass': 157.25, 'name': 'Gadolinium', 'symbol': 'Gd', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f7 5d1'},
    65: {'mass': 158.92535, 'name': 'Terbium', 'symbol': 'Tb', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f9'},
    66: {'mass': 162.5, 'name': 'Dysprosium', 'symbol': 'Dy', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f10'},
    67: {'mass': 164.93032, 'name': 'Holmium', 'symbol': 'Ho', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f11'},
    68: {'mass': 167.259, 'name': 'Erbium', 'symbol': 'Er', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f12'},
    69: {'mass': 168.93421, 'name': 'Thulium', 'symbol': 'Tm', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f13'},
    70: {'mass': 173.054, 'name': 'Ytterbium', 'symbol': 'Yb', 'econfig': '[Kr] 4d10 5s2 5p6 | 6s2 4f14'},
    71: {'mass': 174.9668, 'name': 'Lutetium', 'symbol': 'Lu', 'econfig': '[Kr] 4d10 | 4f14 5s2 5p6 5d1 6s2'},
    72: {'mass': 178.49, 'name': 'Hafnium', 'symbol': 'Hf', 'econfig': '[Kr] 4d10 | 4f14 5s2 5p6 5d2 6s2'},
    73: {'mass': 180.94788, 'name': 'Tantalum', 'symbol': 'Ta', 'econfig': '[Kr] 4d10 4f14 | 5s2 5p6 5d3 6s2'},
    74: {'mass': 183.84, 'name': 'Tungsten', 'symbol': 'W', 'econfig' : '[Kr] 4d10 4f14 5p6 | 5s2 6s2 5d4'},
    75: {'mass': 186.207, 'name': 'Rhenium', 'symbol': 'Re', 'econfig': ''},
    76: {'mass': 190.23, 'name': 'Osmium', 'symbol': 'Os', 'econfig': ''},
    77: {'mass': 192.217, 'name': 'Iridium', 'symbol': 'Ir', 'econfig': ''},
    78: {'mass': 195.084, 'name': 'Platinum', 'symbol': 'Pt', 'econfig': ''},
    79: {'mass': 196.966569, 'name': 'Gold', 'symbol': 'Au', 'econfig': ''},
    80: {'mass': 200.59, 'name': 'Mercury', 'symbol': 'Hg', 'econfig': '[Kr] 5s2 4d10 4f14 | 5p6 5d10 6s2'},
    81: {'mass': 204.3833, 'name': 'Thallium', 'symbol': 'Tl', 'econfig': ''},
    82: {'mass': 207.2, 'name': 'Lead', 'symbol': 'Pb', 'econfig': ''},
    83: {'mass': 208.9804, 'name': 'Bismuth', 'symbol': 'Bi', 'econfig': ''},
    84: {'mass': 209.0, 'name': 'Polonium', 'symbol': 'Po', 'econfig': '[Xe] 4f14 | 5d10 6s2 6p4'},
    85: {'mass': 210.0, 'name': 'Astatine', 'symbol': 'At', 'econfig': ''},
    86: {'mass': 222.0, 'name': 'Radon', 'symbol': 'Rn', 'econfig': ''},
    87: {'mass': 223.0, 'name': 'Francium', 'symbol': 'Fr', 'econfig': ''},
    88: {'mass': 226.0, 'name': 'Radium', 'symbol': 'Ra', 'econfig': ''},
    89: {'mass': 227.0, 'name': 'Actinium', 'symbol': 'Ac', 'econfig': ''},
    90: {'mass': 232.03806, 'name': 'Thorium', 'symbol': 'Th', 'econfig': ''},
    91: {'mass': 231.03588, 'name': 'Protactinium', 'symbol': 'Pa', 'econfig': ''},
    92: {'mass': 238.02891, 'name': 'Uranium', 'symbol': 'U', 'econfig': ''},
    93: {'mass': 237.0, 'name': 'Neptunium', 'symbol': 'Np', 'econfig': ''},
    94: {'mass': 244.0, 'name': 'Plutonium', 'symbol': 'Pu', 'econfig': ''},
    95: {'mass': 243.0, 'name': 'Americium', 'symbol': 'Am', 'econfig': ''},
    96: {'mass': 247.0, 'name': 'Curium', 'symbol': 'Cm', 'econfig': ''},
    97: {'mass': 247.0, 'name': 'Berkelium', 'symbol': 'Bk', 'econfig': ''},
    98: {'mass': 251.0, 'name': 'Californium', 'symbol': 'Cf', 'econfig': ''},
    99: {'mass': 252.0, 'name': 'Einsteinium', 'symbol': 'Es', 'econfig': ''},
    100: {'mass': 257.0, 'name': 'Fermium', 'symbol': 'Fm', 'econfig': ''},
    101: {'mass': 258.0, 'name': 'Mendelevium', 'symbol': 'Md', 'econfig': ''},
    102: {'mass': 259.0, 'name': 'Nobelium', 'symbol': 'No', 'econfig': ''},
    103: {'mass': 262.0, 'name': 'Lawrencium', 'symbol': 'Lr', 'econfig': ''},
    104: {'mass': 267.0, 'name': 'Rutherfordium', 'symbol': 'Rf', 'econfig': ''},
    105: {'mass': 268.0, 'name': 'Dubnium', 'symbol': 'Db', 'econfig': ''},
    106: {'mass': 271.0, 'name': 'Seaborgium', 'symbol': 'Sg', 'econfig': ''},
    107: {'mass': 272.0, 'name': 'Bohrium', 'symbol': 'Bh', 'econfig': ''},
    108: {'mass': 270.0, 'name': 'Hassium', 'symbol': 'Hs', 'econfig': ''},
    109: {'mass': 276.0, 'name': 'Meitnerium', 'symbol': 'Mt', 'econfig': ''},
    110: {'mass': 281.0, 'name': 'Darmstadtium', 'symbol': 'Ds', 'econfig': ''},
    111: {'mass': 280.0, 'name': 'Roentgenium', 'symbol': 'Rg', 'econfig': ''},
    112: {'mass': 285.0, 'name': 'Copernicium', 'symbol': 'Cn', 'econfig': ''},
    114: {'mass': 289.0, 'name': 'Flerovium', 'symbol': 'Fl', 'econfig': ''},
    116: {'mass': 293.0, 'name': 'Livermorium', 'symbol': 'Lv', 'econfig': ''},
}

all_econfig = ['1s2', '2s2', '2p6', '3s2', '3p6', '4s2', '3d10', '4p6', '5s2', '4d10', '5p6', '6s2', '4f14', '5d10', '6p6', '7s2', '5f14', '6d10', '7p6', '8s2', '6f14']
states_spin = {'s': ['1/2'], 'p' : ['1/2', '3/2'], 'd' : ['3/2', '5/2'], 'f' : ['5/2', '7/2']}
max_state_occ = {'s': 2., 'p' : 6., 'd' : 10., 'f' : 14.}
max_state_occ_spin = {'1/2' : 2., '3/2' : 4., '5/2' : 6., '7/2' : 8.}
element_delta_defaults = {} # for workflow purposes

element_max_para = {} # for workflow purposes


def get_econfig(element, full=False):
    """
    returns the econfiguration as a string of an element.
    
    :params: element string
    :params: full, bool (econfig without [He]...)
    returns string
    Be careful with base strings...
    """
    if isinstance(element, int):
        econ = econfiguration.get(element, {}).get('econfig', None)
        if full:
            econ = rek_econ(econ)
            return econ
        else:
            return econ
    elif isinstance(element, str):
        atomic_names = {data['symbol']: num for num,
                         data in econfiguration.iteritems()}
        element_num = atomic_names.get(element, None)
        econ = econfiguration.get(element_num, {}).get('econfig', None)
        if full:
            econ = rek_econ(econ)
            return econ
        else:
            return econ
    else:
        print('INPUTERROR: element has to be and int or string')
        return None

def get_coreconfig(element, full=False):
    """
    returns the econfiguration as a string of an element.
    
    :params: element string
    :params: full, bool (econfig without [He]...)
    returns string
    Be careful with base strings...
    """    
    if isinstance(element, int):
        econ = econfiguration.get(element, {}).get('econfig', None)
        if full:
            econ = rek_econ(econ)
            return econ.split('|')[0]
        else:
            return econ.split('|')[0]
    elif isinstance(element, str):
        atomic_names = {data['symbol']: num for num,
                         data in econfiguration.iteritems()}
        element_num = atomic_names.get(element, None)
        econ = econfiguration.get(element_num, {}).get('econfig', None)
        if full:
            econ = rek_econ(econ)
            return econ.split('|')[0]
        else:
            return econ.split('|')[0]
    else:
        print('INPUTERROR: element has to be and int or string')
        return None
        
def rek_econ(econfigstr):
    """
    rekursive routine to return a full econfig
    '[Xe] 4f14 | 5d10 6s2 6p4' -> '1s 2s ... 4f14 | 5d10 6s2 6p4'
    """
    split_econ = econfigstr.strip('[')
    split_econ = split_econ.split(']')
    if len(split_econ) == 1:
        return econfigstr
    else:
        rest = split_econ[1]
        elem = split_econ[0]
        econfig = get_econfig(elem)
        econ = econfig.replace(' |', '')
        econfigstr = rek_econ(econ + rest)
        return econfigstr# for now
        
def highest_unocc_valence(econfigstr):
    """
    returns the highest not full valence orbital. If all are full, it returns ''
    #maybe should be advanced to give back the next highest unocc
    """
    
    val_orb = ''
    econ = econfigstr.split('|')
    econ_val = econ[-1]
    econ_val_list = econ_val.split()
    for state in econ_val_list[::-1]:
        state_l = state[1]
        occ = int(state.split(state_l)[-1])
        max_occ = max_state_occ.get(state_l, 100)     
        if occ < max_occ:
            val_orb = state            
            return val_orb
    # everything was full return next empty orbital
    hightest_orb = econ_val_list[-1]
    #print hightest_orb
    index = all_econfig.index(hightest_orb)
    if index:    
        next_orb_full = all_econfig[all_econfig.index(hightest_orb)+1]
        next_orb_empty = next_orb_full[0:2] + '0'
        return next_orb_empty # ''  # everythin is full  
    else:
        return val_orb#None
        
def econfigstr_hole(econfigstr, corelevel, highesunoccp, htype='valence'):
    """
    # '1s2 | 2s2' , '1s2' , '2p0' -> '1s1 | 2s2 2p1'

    param: string
    param: string 
    param: string
    
    return: string
    """
    corestates = econfigstr.split()
    
    hoc = int(highesunoccp[2:])
    if htype=='valence':
        new_highocc = str(hoc + 1)
    else:# charged corehole, removed from system, keep occ
        if hoc == 0: # do not add orbital to econfig
            highesunoccp = ''
            new_highocc = ''
        else:
            new_highocc = str(hoc)
    new_econfig = ''
    added = False
    for state in corestates:
        if state == corelevel:
            occ = int(state[2:])
            new_occ = occ - 1
            state = state[:2] + str(new_occ)
        if state == highesunoccp:
            added = True
            state = highesunoccp[:2] + str(new_highocc)
        new_econfig = new_econfig + state + ' '
    if not added:
        new_econfig = new_econfig + highesunoccp[:2] + str(new_highocc)
    
    return new_econfig.rstrip(' ')
    


def get_state_occ(econfigstr, corehole = '', valence = '', ch_occ = 1.0):
    """
    finds out all not full occupied states and returns a dictionary of them
    return a dict
    i.e corehole '4f 5/2'
    ch_occ full or fractional corehole occupation?
    valence: orbital sting '5d', is to adjust the charges for fractional coreholes
    To that orbital occupation ch_occ - 1 will be added.


    """
    # get all not full occ states
    # get how are are filled spin up down
    state_occ_dict_list = []
    
    corehole1 = corehole.replace(" ", "")# get rid of spaces
    corehole_blank = corehole1[:2] + corehole1[-3:] # get rid of occupation    
    econ = econfigstr.replace("| ", "")
    econ_list = econ.split()
    for state in econ_list[::-1]:
        state_l = state[1]
        occ = int(state.split(state_l)[-1])
        max_occ = max_state_occ.get(state_l, 100)     
        if occ < max_occ:
            spinstates = states_spin.get(state_l, [])
            #print(spinstates)
            statename = state[:2]
            spinupocc = 0
            spindownocc = 0
            occ_spin = occ
            if statename==valence:
                is_valence = True
            else:
                is_valence = False            
            for i, spins in enumerate(spinstates):
                spin_mac_occ = max_state_occ_spin[spins]
                occ_spin = occ_spin - spin_mac_occ
                #print occ_spin
                name = statename + spins
                if name==corehole_blank:
                    # use this state
                    # assume it is without the corehole fully filled.
                    nelec = spin_mac_occ 
                    max_spin_up_occ = spin_mac_occ/2.
                    spinupocc = max_spin_up_occ
                    spindownocc = max_spin_up_occ - ch_occ
                    fleur_name = '(' + name + ')'
                    state_dict = {'state' : fleur_name, 'spinUp' : spinupocc, 'spinDown' : spindownocc}
                    state_occ_dict_list.append(state_dict)
                    occ_spin = occ_spin + 1 # because the electron left here and not in the other state
                    continue
                if occ_spin < 0: # this one state is not full
                    if is_valence:
                        #print('is_valence')
                        nelec = occ_spin + spin_mac_occ -1 + ch_occ
                    else:
                        nelec = occ_spin + spin_mac_occ
                    max_spin_up_occ = spin_mac_occ/2.
                    if 0<= nelec <= max_spin_up_occ:
                        spinupocc = nelec
                        spindownocc = 0.00000
                    elif 0<= nelec:
                        spinupocc = max_spin_up_occ
                        spindownocc = nelec - max_spin_up_occ 
                    else:# do not append
                        continue
                    fleur_name = '(' + name + ')'
                    state_dict = {'state' : fleur_name, 'spinUp' : spinupocc, 'spinDown' : spindownocc}
                    state_occ_dict_list.append(state_dict)                   


    return state_occ_dict_list