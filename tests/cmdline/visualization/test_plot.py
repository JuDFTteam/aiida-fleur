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
Module to test the plot cmd from the commandline
'''

import os
from aiida.tools.importexport import import_data

file_path = '../../files/exports/fleur_scf_fleurinp_Si.tar.gz'
thisfilefolder = os.path.dirname(os.path.abspath(__file__))
EXPORTFILE_FILE = os.path.abspath(os.path.join(thisfilefolder, file_path))


def test_cmd_plot(run_cli_command, temp_dir):
    """Test invoking the plot command in all variants.

    If this test hangs, --no-show is not working
    """
    from aiida_fleur.cmdline.visualization import cmd_plot

    # import an an aiida export, this does not migrate
    import_data(EXPORTFILE_FILE, group=None)
    process_uuid = '7f9f4cfb-4170-48ea-801d-4269f88792e0'

    options = [process_uuid, '--no-show']
    result = run_cli_command(cmd_plot, options=options)

    # provide a file with ids
    tempfile_name = os.path.join(temp_dir, 'test_uuids.txt')
    with open(tempfile_name, 'w') as file1:
        file1.write('7f9f4cfb-4170-48ea-801d-4269f88792e0\n7f9f4cfb-4170-48ea-801d-4269f88792e0')
    options = [process_uuid, '--no-show', '-f', tempfile_name]
    result = run_cli_command(cmd_plot, options=options)
    os.remove(tempfile_name)
