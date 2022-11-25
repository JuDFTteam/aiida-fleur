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
''' Contains tests for the FleurRelaxTorqueWorkChain '''
import pytest
from aiida_fleur.workflows.relax_torque import FleurRelaxTorqueWorkChain
from aiida import orm
from aiida.engine import run_get_node
import os
import aiida_fleur

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/FeRelaxTorque/inp.xml')


@pytest.mark.regression_test
@pytest.mark.timeout(2000, method='thread')
def test_fleur_relax_torque_fleurinp(with_export_cache, fleur_local_code, create_fleurinp, clear_database, aiida_caplog,
                                     show_workchain_summary):
    """
    Full example using the Relax Torque workchain with just a fleurinp as input.
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

    # create process builder to set parameters
    builder = FleurRelaxTorqueWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur Relax Torque test for Fe bulk with fleurinp data given (initial angles perpendicular)'
    builder.metadata.label = 'FleurRelaxTorque_test_fleurinp'

    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(options).store()
    builder.scf.fleurinp = create_fleurinp(TEST_INP_XML_PATH)
    builder.wf_parameters = orm.Dict({
        'opt_scheme': 'bfgs',
    })

    with with_export_cache('fleur_relax_torque_fleurinp.tar.gz'):
        out, node = run_get_node(builder)
    #print(out)
    #print(node)

    show_workchain_summary(node)

    #assert node.is_finished_ok
    # check output
    assert 'output_relax_torque_wc_para' in out
    n = out['output_relax_torque_wc_para']
    n = n.get_dict()

    from pprint import pprint
    pprint(n)

    assert node.exit_status == 350
    assert pytest.approx(n['alphas']) == [0.0, 0.0]
    assert pytest.approx(n['betas'], rel=1e-5) == [0.4, 1.1708047268]
    assert pytest.approx(n['energy'], rel=1e-7) == -2541.3701388552
    assert pytest.approx(n['x_torques'], rel=1e-2) == [-619.93526449, 619.93526449]
    assert pytest.approx(n['y_torques']) == [0.0, 0.0]
