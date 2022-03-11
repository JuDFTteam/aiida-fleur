###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
'''Contains tests for create_corehole functions.'''
import pytest
from aiida import orm

# create_corehole_para
# test interface of corehole para, that the parameter dict that comes out is right
PARAMETERS2 = {
    'atom1': {
        'element': 'Si',
        'id': 14.1,
        'rmt': 2.1,
        'jri': 981,
        'lmax': 12,
        'lnonsph': 6
    },  #'econfig': '[He] 2s2 2p6 | 3s2 3p2', 'lo': ''},
    'atom2': {
        'element': 'Si',
        'z': 14,
        'id': 14.2,
        'rmt': 2.1,
        'jri': 981,
        'lmax': 12,
        'lnonsph': 6
    },
    'comp': {
        'kmax': 5.0,
    }
}


def test_create_corehole_para(generate_structure, data_regression):
    """Test if the create corehole para function has thr right interface and returns
    the correct things
    """
    from aiida_fleur.tools.create_corehole import create_corehole_para
    from aiida_fleur.tools.StructureData_util import break_symmetry

    dict2 = orm.Dict(dict=PARAMETERS2)
    struc = generate_structure()  #Si
    struc2, para_new = break_symmetry(struc, parameterdata=dict2)
    parameters1 = create_corehole_para(struc2, kind='Si1', econfig='[He] 2s1 2p6 | 3s2 3p3', parameterdata=para_new)
    assert isinstance(parameters1, orm.Dict)

    # with no parameterdata to modify
    parameters2 = create_corehole_para(struc2, kind='Si1', econfig='[He] 2s1 2p6 | 3s2 3p3')
    assert isinstance(parameters2, orm.Dict)

    data_regression.check({
        'parameters1': parameters1.get_dict(),
        'parameters2': parameters2.get_dict(),
    })


'''
# from old, test idea for create_corehole_fleurinp
ids = []  #13924]#, 13925]#, 13926, 13927, 13928, 13929, 13930, 13931, 13932, 13933, 13934, 13935]
#ids = [479, 480, 481, 482, 537]#	O12W4, O12W4, O6W2, O6W2, O36W3Y18

kind = 'W1'
econfig = '[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2'
para1 = Dict(
    dict={
        'title': 'A test calculation of Tungsten',
        'input': {
            'film': False,
            'cartesian': True,
        },
        'atom': {
            'element': 'W',
            'jri': 833,
            'rmt': 2.3,
            'dx': 0.015,
            'lmax': 8,
            'lo': '5p',
            'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
        },
        'soc': {
            'theta': 0.0,
            'phi': 0.0
        },
        'comp': {
            'kmax': 3.5,
            'gmax': 2.9,
        },
        'kpt': {
            'nkpt': 200,
        }
    })
#para1.store()
#pprint(para1.get_dict())

for id in ids:
    s = load_node(id)
    new_s, para = bs(s, atoms=[], site=[0, 1], pos=[(0.0, 0.0, 0, 0)], parameterData=para1)
    #print new_s.sites
    #pprint(para.get_dict())
    res = create_corehole(new_s, kind, econfig, para)
    #print res
    #pprint(para.get_dict())
    #pprint(res.get_dict())

# test create_corehole_fleurinp
#fleurinp = load_node(14039) # W film

inpxmlfile1 = '../inp_xml_files/W/inp.xml'
inpxmlfile = os.path.abspath(inpxmlfile1)
fleurinp = FleurinpData(files=[inpxmlfile])
species = 'W-1'
stateocc = {'(5d3/2)': (2.5, 0.0), '(4f7/2)': (3.5, 4.0)}
pos = []
coreconfig = 'same'
valenceconfig = 'same'
#pprint(fleurinp.inp_dict)

new_inp = create_corehole_fleurinp(fleurinp, species, stateocc)
print(new_inp)

etree = ''
change = [(1, 2)]
res = write_change(etree, change)
#res.write('.outtree')
print(res)
'''
