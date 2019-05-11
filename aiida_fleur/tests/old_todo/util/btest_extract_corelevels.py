#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
from aiida import load_dbenv, is_dbenv_loaded
from six.moves import range
if not is_dbenv_loaded():
    load_dbenv()
import sys,os
from lxml import etree, objectify
from lxml.etree import XMLSyntaxError, XPathEvalError
from pprint import pprint
from aiida.plugins import Code, DataFactory, CalculationFactory
from aiida.orm import Computer
from aiida.orm import load_node
from pprint import pprint
from aiida_fleur_ad.util.extract_corelevels import extract_corelevels
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
KpointsData = DataFactory('array.kpoints')

FleurInpCalc = CalculationFactory('fleur.inpgen')
FleurCalc = CalculationFactory('fleur.fleur')


import time
start_time = time.time()

##
#calculation to extract from:
# either from list given here or system argument

calcs_pks = [4743]#4436]
#calcs_pks = [1464, 1462, 1399, 1403]#, 1059]#, 1414
####
'''
if not calcs_pks:
    try:
        for arg in sys.argv[1:]:
            calc_t = arg
            calcs_pks.append(int(calc_t))
    except:
        pass
#####
'''

# check if calculation pks belong to successful fleur calculations
for pk in calcs_pks:
    calc = load_node(pk)
    if (not isinstance(calc, FleurCalc)):
        raise ValueError("Calculation with pk {} must be a FleurCalculation".format(pk))
    if calc.get_state() != 'FINISHED':
        raise ValueError("Calculation with pk {} must be in state FINISHED".format(pk))


parser_info = {'parser_warnings': [], 'unparsed' : []}


### call
test_outxmlfiles = ['./test_outxml/outBeCr.xml','./test_outxml/out.xml', './test_outxml/outCuF.xml', './test_outxml/outFe.xml', './test_outxml/outHg.xml',  './test_outxml/outO.xml']
outxmlfile = test_outxmlfiles[0]

corelevels, atomtypes = extract_corelevels(outxmlfile)
#print corelevels
for i in range(0,len(corelevels[0][1]['corestates'])):
    print(corelevels[0][1]['corestates'][i]['energy'])

print(calcs_pks)
for calc in calcs_pks:
    # get out.xml file of calculation
    outxml = load_node(pk).out.retrieved.folder.get_abs_path('path/out.xml')
    corelevels, atypes = extract_corelevels(outxmlfile)
    #print('corelevels {}'.format(corelevels))
    pprint(corelevels)
    pprint(atypes)
    for i in range(0,len(corelevels[1][0]['corestates'])):
        #print corelevels[3][1]['corestates'][i]['energy']
        print(corelevels[1][0]['corestates'][i]['energy'])
print(("--- %s seconds ---" % (time.time() - start_time)))
