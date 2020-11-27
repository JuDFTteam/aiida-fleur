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
Module to test all CLI workflow commands.
'''

import os
from aiida.tools.importexport import import_data

file_path = '../../files/exports/fleur_scf_fleurinp_Si.tar.gz'
thisfilefolder = os.path.dirname(os.path.abspath(__file__))
EXPORTFILE_FILE = os.path.abspath(os.path.join(thisfilefolder, file_path))


def test_workchain_res(run_cli_command):
    """Test invoking the workchain res command in all variants."""
    from aiida_fleur.cmdline.workflows import workchain_res

    EXPECTED1 = '"total_energy": -580.0719889044,'
    EXPECTED2 = '"energy_core_electrons": -316.8117066016,'
    # import an an aiida export, this does not migrate
    import_data(EXPORTFILE_FILE, group=None)
    process_uuid = '7f9f4cfb-4170-48ea-801d-4269f88792e0'

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


def test_workchain_inputdict(run_cli_command):
    """Test invoking the workchain inputdict command in all variants."""
    from aiida_fleur.cmdline.workflows import workchain_inputdict

    # import an an aiida export, this does not migrate
    import_data(EXPORTFILE_FILE, group=None)

    EXPECTED = '"max_wallclock_seconds": 300,'
    EXPECTED2 = '"num_machines": 1,'
    process_uuid = '7f9f4cfb-4170-48ea-801d-4269f88792e0'

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
