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
Here we run the fleur_dos_wc for a Fleur calculation which has been converged before
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
from aiida_fleur.workflows.dos import fleur_dos_wc

ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')

#######################
# 2. Creation/loding of input nodes

# Load the codes, thwy have to be setup in your database.
fleur_label = 'fleur@localhost'
fleur_code = Code.get_from_string(fleur_label)

### Create wf_parameters (optional) and options
wf_para = Dict(dict={'fleur_runmax': 4, 'density_criterion': 0.000001, 'serial': False})

options = Dict(dict={'resources': {'num_machines': 1}, 'queue_name': '', 'max_wallclock_seconds': 60 * 60})

# load a fleurino data object from a scf_wc before
################################
# 3. submit the workchain with its inputs.

inputs = {}
inputs['wf_parameters'] = wf_para
inputs['fleurinp'] = fleurinp
inputs['fleur'] = fleur_code
inputs['description'] = 'test fleur_dos_wc run on W'
inputs['label'] = 'dos test '
inputs['options'] = options

# submit workchain to the daemon
# Noice that the nodes we created before are not yet stored in the database,
# but AiiDA will do so automaticly when we launch the workchain.
# To reuse nodes it might be a good idea, to save them before by hand and then load them
res = submit(fleur_dos_wc, **inputs)

# You can also run the workflow in the python interpreter as blocking
#res = run(fleur_dos_wc, **inputs)
