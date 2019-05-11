# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
Here we run the fleur_eos_wc for @ or some other material

Layout:

1. Database env load, Import, create base classes
2. Creation of  input nodes
3. Lauch workchain
"""

#######################
# 1. Load the database environment. Imports and base class creation

from __future__ import absolute_import
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.engine.launch import submit, run
from aiida_fleur.workflows.eos import fleur_eos_wc

ParameterData = DataFactory('parameter')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')


#######################    
# 2. Creation/loding of input nodes

# Load the codes, thwy have to be setup in your database.
fleur_label = 'fleur@localhost'
inpgen_label = 'inpgen@localhost'
fleur_code =  Code.get_from_string(fleur_label)
inpgen_code = Code.get_from_string(inpgen_label)

### Create wf_parameters (optional) and options
wf_para = Dict(dict={'fleur_runmax' : 4, 
                              'points' : 4,
                              'guess' : 1.0})

options = Dict(dict={'resources' : {"num_machines": 1},
                              'queue_name' : '',
                              'max_wallclock_seconds':  60*60})

# Create W bcc crystal structure 
bohr_a_0= 0.52917721092 # A
a = 3.013812049196*bohr_a_0
cell = [[-a,a,a],[a,-a,a],[a,a,-a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(0.,0.,0.), symbols='W')

# (optional) We specifi some FLAPW parameters for W
parameters = Dict(dict={
                  'atom':{
                        'element' : 'W',
                        'jri' : 833,
                        'rmt' : 2.3,
                        'dx' : 0.015,
                        'lmax' : 8,
                        'lo' : '5p',
                        'econfig': '[Kr] 5s2 4d10 4f14| 5p6 5d4 6s2',
                        },
                  'comp': {
                        'kmax': 3.0,
                        },
                  'kpt': {
                        'nkpt': 100,
                        }})


################################
# 3. submit the workchain with its inputs.

inputs = {}
inputs['wf_parameters'] = wf_para
inputs['structure'] = structure
inputs['calc_parameters'] = parameters
inputs['fleur'] = fleur_code
inputs['inpgen'] = inpgen_code
inputs['description'] = 'test fleur_eos_wc run on W'
inputs['label'] = 'eos test on W'
inputs['options'] = options

# submit workchain to the daemon
# Noice that the nodes we created before are not yet stored in the database, 
# but AiiDA will do so automaticly when we launch the workchain. 
# To reuse nodes it might be a good idea, to save them before by hand and then load them 
res = submit(fleur_eos_wc, **inputs)

# You can also run the workflow in the python interpreter as blocking
#res = run(fleur_eos_wc, **inputs)
