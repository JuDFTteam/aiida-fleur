#!/usr/bin/env python

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.tools.codespecific.fleur.read_cif_folder import read_cif_folder


read_cif_folder(log=True, store=False, rekursive=True, extras={'type' : 'bulk', 'project': 'Fusion', 'specification' : 'aiida_work', 'comment' : 'Materials for Fusion'})
