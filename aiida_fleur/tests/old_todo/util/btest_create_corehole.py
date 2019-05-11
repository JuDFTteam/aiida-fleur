#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys,os
from aiida.orm.querybuilder import QueryBuilder

from aiida_fleur_ad.util.create_corehole import create_corehole, create_corehole_fleurinp, write_change
from aiida.plugins import Code, CalculationFactory, DataFactory
from aiida.orm import load_node
from pprint import pprint
from aiida_fleur.tools.StructureData_util import break_symmetry as bs

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')
'''
ids = [13586, 13934, 12748]#, 12927]

for id in ids:
    s = load_node(id)
    new_s = bs(s, atoms=['Be'], site=[0, 1], pos=[(0.0, 0.0, -1.83792744752922), (0.0, 0.0, 0.918963723764612)])
    #new_s.store()
'''
#s = load_node(355)

ids = []#13924]#, 13925]#, 13926, 13927, 13928, 13929, 13930, 13931, 13932, 13933, 13934, 13935]
#ids = [479, 480, 481, 482, 537]#	O12W4, O12W4, O6W2, O6W2, O36W3Y18

kind ='W1'
econfig = "[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2"
para1 = Dict(dict={
                  'title': 'A test calculation of Tungsten',
                  'input': {
                       'film': False,
                       'cartesian' : True,
                        },
                  'atom':{
                        'element' : 'W',
                        'jri' : 833,
                        'rmt' : 2.3,
                        'dx' : 0.015,
                        'lmax' : 8,
                        'lo' : '5p',
                        'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
                        },
                  'soc': {'theta': 0.0, 'phi': 0.0},
                  'comp': {
                        'kmax': 3.5,
                        'gmax': 2.9,
                        },
                  'kpt': {
                        'nkpt': 200,
                        }})
#para1.store()
#pprint(para1.get_dict())

for id in ids:
    s = load_node(id)
    new_s, para = bs(s, atoms=[], site=[0,1], pos=[(0.0, 0.0, 0,0)], parameterData=para1)
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
fleurinp = FleurinpData(files = [inpxmlfile])
species = 'W-1'
stateocc = {'(5d3/2)' : (2.5, 0.0), '(4f7/2)' : (3.5 , 4.0)}
pos = []
coreconfig = 'same'
valenceconfig = 'same'
#pprint(fleurinp.inp_dict)

new_inp = create_corehole_fleurinp(fleurinp, species, stateocc)
print(new_inp)

etree = ''
change = [(1,2)]
res = write_change(etree, change)
#res.write('.outtree')
print(res)
