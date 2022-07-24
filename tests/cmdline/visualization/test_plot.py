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
import pytest
import aiida
from packaging import version

file_path = '../../files/exports/fleur_scf_fleurinp_Si.tar.gz'
thisfilefolder = os.path.dirname(os.path.abspath(__file__))
EXPORTFILE_FILE = os.path.abspath(os.path.join(thisfilefolder, file_path))


@pytest.mark.skipif(version.parse(aiida.__version__) < version.parse('1.5.0'),
                    reason='archive import and migration works only with aiida-core > 1.5.0')
def test_cmd_plot(run_cli_command, temp_dir, import_with_migrate):
    """Test invoking the plot command in all variants.

    If this test hangs, --no-show is not working
    """
    from aiida_fleur.cmdline.visualization import cmd_plot

    # import an an aiida export, this does not migrate
    import_with_migrate(EXPORTFILE_FILE)
    process_uuid = 'f44623bf-d8a3-41f0-b4ee-6562b5f9b027'

    options = [process_uuid, '--no-show']
    result = run_cli_command(cmd_plot, options=options)

    # provide a file with ids
    tempfile_name = os.path.join(temp_dir, 'test_uuids.txt')
    with open(tempfile_name, 'w', encoding='utf-8') as file1:
        file1.write(f'{process_uuid}\n{process_uuid}')
    options = [process_uuid, '--no-show', '-f', tempfile_name]
    result = run_cli_command(cmd_plot, options=options)
    os.remove(tempfile_name)
