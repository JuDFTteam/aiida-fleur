# -*- coding: utf-8 -*-

import os
#import numpy
from pprint import pprint
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.parsers.plugins.fleur_inp.fleur import parse_xmlout_file



outxmlfile = '/usr/users/iff_th1/broeder/aiida/github/aiida_fleur_plugin/tests/parsers/outxmlfiles/out1.xml'

a = parse_xmlout_file(outxmlfile)

pprint(a)