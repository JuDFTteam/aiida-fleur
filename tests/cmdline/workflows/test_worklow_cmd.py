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
Module to test all CLI workflow commands.
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
def test_workchain_res(run_cli_command, import_with_migrate):
    """Test invoking the workchain res command in all variants."""
    from aiida_fleur.cmdline.workflows import workchain_res

    EXPECTED1 = '"total_energy": -580.0719869963,'
    EXPECTED2 = '"energy_core_electrons": -316.7867593796,'
    # import an an aiida export, this does not migrate
    #import_data(EXPORTFILE_FILE, group=None)
    import_with_migrate(EXPORTFILE_FILE)
    process_uuid = 'f44623bf-d8a3-41f0-b4ee-6562b5f9b027'

    options = [process_uuid]
    result = run_cli_command(workchain_res, options=options)
    assert EXPECTED1 in result.output_lines
    assert EXPECTED2 in result.output_lines

    # only one node
    options = [process_uuid, '-l', 'output_scf_wc_para', '--info', '--keys', 'total_energy', 'total_wall_time']
    result = run_cli_command(workchain_res, options=options)
    assert EXPECTED1 in result.output_lines
    assert EXPECTED2 not in result.output_lines
    assert 'Info:' in result.output_lines[0]

    options = [process_uuid, '--keys', 'nothere']
    run_cli_command(workchain_res, options=options, raises=KeyError)


@pytest.mark.skipif(version.parse(aiida.__version__) < version.parse('1.5.0'),
                    reason='archive import and migration works only with aiida-core > 1.5.0')
def test_workchain_inputdict(run_cli_command, import_with_migrate):
    """Test invoking the workchain inputdict command in all variants."""
    from aiida_fleur.cmdline.workflows import workchain_inputdict

    # import an an aiida export, this does not migrate
    #import_data(EXPORTFILE_FILE, group=None)
    import_with_migrate(EXPORTFILE_FILE)
    EXPECTED = '"max_wallclock_seconds": 300,'
    EXPECTED2 = '"num_machines": 1,'
    process_uuid = 'f44623bf-d8a3-41f0-b4ee-6562b5f9b027'

    options = [process_uuid]
    result = run_cli_command(workchain_inputdict, options=options)
    assert EXPECTED in result.output_lines
    assert EXPECTED2 in result.output_lines

    options = [process_uuid, '--info', '-l', 'options', '--keys', 'max_wallclock_seconds', 'withmpi']
    result = run_cli_command(workchain_inputdict, options=options)
    assert EXPECTED in result.output_lines
    assert EXPECTED2 not in result.output_lines
    assert 'Info:' in result.output_lines[0]

    options = [process_uuid, '--keys', 'nothere']
    run_cli_command(workchain_inputdict, options=options, raises=KeyError)
