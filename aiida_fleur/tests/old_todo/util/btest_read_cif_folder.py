#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida_fleur.tools.read_cif_folder import read_cif_folder

read_cif_folder(
    log=True,
    store=True,
    recursive=True,
    extras={
        'type': 'bulk',
        'project': 'Fusion',
        'specification': 'aiida_work',
        'comment': 'Materials for Fusion'
    }
)
