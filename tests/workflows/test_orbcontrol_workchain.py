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
''' Contains tests for the FleurOrbControlWorkChain '''
import pytest
from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain
from aiida import orm
from aiida.engine import run_get_node
from aiida.cmdline.utils.common import get_workchain_report, get_calcjob_report
import os


@pytest.mark.regression_test
@pytest.mark.timeout(2000, method='thread')
def test_fleur_orbcontrol_structure(with_export_cache, fleur_local_code, inpgen_local_code, generate_smco5_structure,
                                    clear_database, aiida_caplog, show_workchain_summary):
    """
    Full example using the OrbControl workchain with just a structure as input.
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
    builder = FleurOrbControlWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur OrbControl test for SmCo5 bulk with structure data given'
    builder.metadata.label = 'FleurOrbControl_test_structure'

    builder.scf_no_ldau.fleur = FleurCode
    builder.scf_no_ldau.options = orm.Dict(dict=options).store()
    builder.scf_no_ldau.inpgen = inpgen_local_code
    builder.scf_no_ldau.structure = generate_smco5_structure()
    builder.scf_no_ldau.calc_parameters = orm.Dict(
        dict={
            'comp': {
                'kmax': 3.0,
                'gmax': 7.0,
                'gmaxxc': 7.0
            },
            'exco': {
                'xctyp': 'vwn'
            },
            'kpt': {
                'div1': 1,
                'div2': 1,
                'div3': 1
            }
        })
    builder.fleur = FleurCode
    builder.options = orm.Dict(dict=options).store()
    builder.scf_with_ldau.fleur = FleurCode
    builder.scf_with_ldau.options = orm.Dict(dict=options).store()
    builder.wf_parameters = orm.Dict(
        dict={
            'iterations_fixed': 30,
            'ldau_dict': {
                'all-Sm': {
                    'l': 3,
                    'U': 6.7,
                    'J': 0.7,
                    'l_amf': False
                }
            },
            'fixed_occupations': {
                'all-Sm': {
                    3: (6, 0)
                }
            },
        })

    with with_export_cache('fleur_orbcontrol_structure.tar.gz'):
        out, node = run_get_node(builder)
    #print(out)
    #print(node)

    show_workchain_summary(node)

    #assert node.is_finished_ok
    # check output
    assert 'output_orbcontrol_wc_para' in out
    n = out['output_orbcontrol_wc_para']
    n = n.get_dict()
    assert 'groundstate_scf' in out

    from pprint import pprint
    pprint(n)

    assert n['failed_configs'] == []
    assert n['successful_configs'] == [0, 1, 2, 3, 4, 5, 6]
    assert n['non_converged_configs'] == []
    assert n['groundstate_configuration'] == 3
    assert pytest.approx(n['total_energy']) == [
        -17383.131898459, -17383.106547481, -17383.105996931, -17383.141450442, -17383.105996931, -17383.106547481,
        -17383.131898459
    ]
    assert n['configurations'] == [{
        'all-Sm-3': [[0, 1, 1, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0]]
    }, {
        'all-Sm-3': [[1, 0, 1, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0]]
    }, {
        'all-Sm-3': [[1, 1, 0, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0]]
    }, {
        'all-Sm-3': [[1, 1, 1, 0, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0]]
    }, {
        'all-Sm-3': [[1, 1, 1, 1, 0, 1, 1], [0, 0, 0, 0, 0, 0, 0]]
    }, {
        'all-Sm-3': [[1, 1, 1, 1, 1, 0, 1], [0, 0, 0, 0, 0, 0, 0]]
    }, {
        'all-Sm-3': [[1, 1, 1, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0]]
    }]
