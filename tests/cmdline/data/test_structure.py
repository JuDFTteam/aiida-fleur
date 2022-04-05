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
'''
Module to test all CLI data structure commands.
'''
import os
from aiida.orm import Dict

file_path1 = '../../files/inpxml/FePt/inp.xml'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
FEPT_INPXML_FILE = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))


def test_import_structure(run_cli_command):
    """Test invoking the import structure command in all variants."""
    from shutil import copyfile
    from aiida_fleur.cmdline.data.structure import cmd_import

    options = [FEPT_INPXML_FILE, '--fleurinp']
    run_cli_command(cmd_import, options=options)

    options = [FEPT_INPXML_FILE, '--fleurinp', '--dry-run']
    run_cli_command(cmd_import, options=options)

    dest_path = FEPT_INPXML_FILE.strip('.xml')
    copyfile(FEPT_INPXML_FILE, dest_path)
    options = [dest_path, '--fleurinp', '--dry-run']
    result = run_cli_command(cmd_import, options=options, raises=True)
    os.remove(dest_path)
    assert 'Critical: Error: Currently, only StructureData from a inp.xml file can be '\
           'extracted.' in result.output_lines
