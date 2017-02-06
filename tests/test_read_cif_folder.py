#!/usr/bin/env python

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.tools.codespecific.fleur.read_cif_folder import read_cif_folder

read_cif_folder(log=True, store=False, extras={'type' : 'Fusion relevant', 'project': 'Fusion', 'test' : 'read_cif_test'})
