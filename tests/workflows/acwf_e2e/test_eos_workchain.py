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
''' Contains test for the eos workchain, short, interface and regression '''

import pytest
from aiida.engine import run_get_node
from aiida import orm

try:
    import aiida_common_workflows
    from aiida_common_workflows.workflows.eos import EquationOfStateWorkChain
except ImportError:
    aiida_common_workflows = None



@pytest.mark.regression_test
@pytest.mark.skipif(not aiida_common_workflows, reason='aiida-common-workflows is not installed')
@pytest.mark.timeout(500, method='thread')
def test_fleur_eos_structure_Si(with_export_cache, fleur_local_code, inpgen_local_code, generate_structure, show_workchain_summary):
    """
    full example using scf workflow with just a fleurinp data as input.
    Several fleur runs needed till convergence
    """

    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 10 * 60,
        'withmpi': False,
        'custom_scheduler_commands': ''
    }
    wf_param = {'points': 3, 'step': 0.02, 'guess': 1.03}

    builder = EquationOfStateWorkChain.get_builder()
    builder.structure = generate_structure().store()
    builder.scale_factors = orm.List([1.01,1.03,1.05])
    builder.generator_inputs = {
        'engines': {
            'inpgen': {
                'code': inpgen_local_code
            },
            'relax': {
                'code': fleur_local_code,
                'options': options
            },
            'protocol': 'fast',
        }
    }
    builder.sub_process_class = 'common_workflows.relax.fleur'

    builder.metadata.description = 'Fleur common workflows EquationOfStateWorkChain test for Si bulk'
    builder.metadata.label = 'acwf_EquationOfStateWorkChain_test_Si_bulk'

    with with_export_cache('fleur_acwf_eos_si_structure.tar.gz'):
        out, node = run_get_node(builder)

    show_workchain_summary(node)

    assert node.is_finished_ok

    assert False