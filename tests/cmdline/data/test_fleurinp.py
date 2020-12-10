# -*- coding: utf-8 -*-
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
Module to test all CLI data fleurinp commands.
'''
import os
from aiida.orm import Dict
file_path1 = '../../files/inpxml/FePt/inp.xml'
file_path2 = '../../files/inpxml/Si/inp.xml'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
FEPT_INPXML_FILE = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))
SI_INPXML_FILE = os.path.abspath(os.path.join(inpxmlfilefolder, file_path2))


def test_cmd_fleurinp_list(run_cli_command, create_fleurinp):
    """Test invoking the data fleurinp list command."""
    from aiida_fleur.cmdline.data.fleurinp import list_fleurinp

    fleurinp = create_fleurinp(FEPT_INPXML_FILE)
    fleurinp.store()
    options = ['--uuid', '--ctime', '--strucinfo']
    results = run_cli_command(list_fleurinp, options=options)
    print(results.output_lines)
    assert fleurinp.uuid in results.output

    fleurinp2 = create_fleurinp(SI_INPXML_FILE)
    fleurinp2.store()
    options = ['--uuid', '--ctime', '--strucinfo', '--raw']
    results = run_cli_command(list_fleurinp, options=options)
    assert fleurinp.uuid in results.output
    assert fleurinp2.uuid in results.output


def test_cmd_fleurinp_cat(run_cli_command, create_fleurinp):
    """Test invoking the data fleurinp cat command."""
    from aiida_fleur.cmdline.data.fleurinp import cat_file

    fleurinp = create_fleurinp(FEPT_INPXML_FILE)
    fleurinp.store()
    options = [fleurinp.uuid]
    result = run_cli_command(cat_file, options=options)
    # printed contents will also put in line breaks \n which makes comparisson hard.
