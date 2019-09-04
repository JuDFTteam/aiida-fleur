#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test tries to create a fleurinpdata and to modefy it
"""
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.plugins import DataFactory
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from pprint import pprint
from lxml import etree
from lxml.etree import XMLSyntaxError
import os

import time
start_time = time.time()

ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')

#schemanameQq


path = os.getcwd()#path.realpath(__file__)
print(path)
filepath = path + '/inp.xml'  
#'/Users/broeder/aiida/scratch/broeder/aiida_run2/ff/4c/c14d-8a1b-40b3-af95-400e23002bcb/inp.xml'

new_fleurinpData = FleurInpData(files= [filepath])
#print(new_fleurinpData.get_file_abs_path('inp.xml'))
#new_fleurinpData.store()

#new_fleurinpData= load_node(6)

fleurmode = FleurinpModifier(new_fleurinpData)


#fleurmode.set_switch({'dos': True})

fleurmode.set_inpchanges({})
fleurmode.set_inpchanges({'dos': True})
tria = True
nkpts = 800

change_dict = {'dos': True, 'ndir' : -1, 'minEnergy' : -0.8,
               'maxEnergy' : 0.8, 'sigma' : 0.005}

fleurmode.set_inpchanges(change_dict)
if tria:
    change_dict = {'mode': 'tria'}
    fleurmode.set_inpchanges(change_dict)
if nkpts:
    fleurmode.set_nkpts(count=nkpts)

'''
fleurmode.set_species('W-1', {'radius' : 3.5})
fleurmode.change_atom('forces', True, position=(0.0, 0.0, 0.0))
fleurmode.set_xpath('/fleurinput/@dos', True)
'''
'''
name = 'Na-1'
xpathn = '/fleurInput/atomSpecies/species[@name = "{}"]/mtSphere'.format(name)# 'radius':
attributename = 'radius'
attribv = 0.0000
fleurmode.xml_set_all_attribv(xpathn, attributename, attribv)

xpathn = '/fleurInput/atomSpecies/species/mtSphere'
xpathn = '/fleurInput'
#attribv = [0.0000, '1.2', 3.4]
#fleurmode.xml_set_all_attribv(xpathn, attributename, attribv)


#fleurmode.xml_set_attribv_occ(xmltree, xpathn, attributename, attribv, occ=[0])
#fleurmode.xml_set_first_attribv(xmltree, xpathn, attributename, attribv)
xpathn = '/fleurInput/atomSpecies/species[@name = "{}"]/mtSphere/@radius'.format(name)# 'radius':

attribv = 1.1111
#set_xpath(xmltree, xpathn, attribv)# does not work


xpathn =  '/fleurInput/atomGroups/atomGroup/relPos'
text =  '1.20000 PI/3 5.1-MYCrazyCostant'
#fleurmode.xml_set_all_text(xpathn, text)


fleurmode.set_species('Na-1', { 'mtSphere' : {'radius' : 3.5}})
fleurmode.set_species('W-2', {'atomicCutoffs' : {'lmax' : 9, 'lnonsphr': 7}, 'energyParameters': {'d' : 6}, 'mtSphere' : {'radius' : 2.6, 'gridPoints' : 925, 'logIncrement' : .01800000}})
print 'here1'
#
fleurmode.set_species('W-2', {'electronConfig' : {'coreConfig' : '[Xe] (4f5/2) (4f7/2)', 'valenceConfig' : '(6s1/2) (5d3/2) (5d5/2) (6p1/2) (6p3/2)'}}, create=True)#, 'stateOccupation' : [{'state' : "(6p3/2)", 'spinUp' : "1.00000000", 'spinDown' : "1.00000000"}, {'state' : "(6p1/2)", 'spinUp' : "1.00000000", 'spinDown' : "1.00000000"}]}}, create=True)


xpathn = '/fleurInput/atomSpecies/species[@name = "{}"]'.format(name)# 'radius':
xpathn2 = '/fleurInput/atomSpecies/species[@name = "{}"]/electronConfig3/e/d/g/f/yeah'.format(name)

new_e = etree.Element('lo')
new_e.set('type', "SCLO")

#fleurmode.create_tag(xpathn, new_e, True)
#fleurmode.create_tag(xpathn,'electronConfig2', True)

#eval_xpath3(root, xpathn2, create=True)
#fleurmode.set_species('W-2', {'lo': {'type':"SCLO", 'l' : 1, 'n' : 5, 'eDeriv'  : 1}}, True)

#fleurmode.set_species('W-2', {'lo': [{'type':"SCLO", 'l' : 1, 'n' : 5, 'eDeriv'  : 2}]}, True)
#fleurmode.set_species('W-2', {'lo': [{'type':"SCLO", 'l' : 1, 'n' : 5, 'eDeriv'  : 3}, {'type':"SCLO", 'l' : 1, 'n' : 5, 'eDeriv'  : 4}, {'type':"SCLO", 'l' : 1, 'n' : 5, 'eDeriv'  : 5}, {'type':"SCLO", 'l' : 1, 'n' : 5, 'eDeriv'  : 6}]}, True)
'''

#fleurmode.changes()
fleurmode.show(validate=True)#, display=False)

print(fleurmode._original)
print(fleurmode._tasks)
out=''#fleurmode.freeze()

print('out: {}'.format(out))
print('in: {}'.format(new_fleurinpData))

