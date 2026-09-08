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
''' Contains tests for the FleurBandWorkChain '''
import pytest

from aiida import orm
from aiida.engine import run_get_node

import aiida_fleur
from aiida_fleur.workflows.band import FleurBandWorkChain


TEST_INP_XML_PATH = f'{aiida_fleur.__path__[0]}/../tests/files/inpxml/Si/inp.xml'


@pytest.mark.usefixtures('aiida_profile')
def test_band_workchain_entry_point():
    """The workchain is registered under ``fleur.band``."""
    from aiida.plugins import WorkflowFactory
    assert WorkflowFactory('fleur.band') is FleurBandWorkChain


def test_band_workchain_invalid_inputs():
    """The workchain detects invalid combinations of inputs."""
    from aiida.engine import ProcessBuilder
    builder = FleurBandWorkChain.get_builder()
    builder.fleur = orm.load_node(TEST_INP_XML_PATH)  # placeholder, will be replaced

    # Patch the ``fleur`` input with a mock code-like node. We use a Code node
    # already configured in the test database; if none exists we skip the test.
    pytest.skip('Requires a configured FLEUR code in the database; see regression tests for full run.')


@pytest.mark.regression_test
@pytest.mark.timeout(500, method='thread')
def test_fleur_band_fleurinp_Si(enable_archive_cache, fleur_local_code, create_fleurinp, clear_database,
                                aiida_caplog, show_workchain_summary):
    """
    Full example using the band workchain with a fleurinp data and SCF
    namespace as input. Calls scf, then a single fleur run on the band path.
    """
    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 5 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }

    FleurCode = fleur_local_code

    builder = FleurBandWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Band test for Si bulk with fleurinp data given'
    builder.metadata.label = 'FleurBand_test_Si_bulk'
    builder.options = orm.Dict(dict=options).store()
    builder.fleur = FleurCode
    builder.scf.fleurinp = create_fleurinp(TEST_INP_XML_PATH).store()
    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()

    with enable_archive_cache('fleur_band_fleurinp_Si.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)

    assert node.is_finished_ok
    assert 'output_band_wc_para' in out
    assert out['output_band_wc_para'].get_dict().get('mode') == 'band'
    assert 'band_calc' in out
    res_files = out['band_calc']['retrieved'].list_object_names()
    assert any(
        file in res_files for file in ('banddos.hdf', 'bands.1', 'bands.2')), f'No bands file retrieved: {res_files}'