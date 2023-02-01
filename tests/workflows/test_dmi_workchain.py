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
''' Various tests for the FleurDMIWorkChain, different groupping '''
# Here we test if the interfaces of the workflows are still the same
import pytest
import os
from aiida.engine import run_get_node
from aiida.cmdline.utils.common import get_workchain_report
from aiida_fleur.workflows.dmi import FleurDMIWorkChain


@pytest.mark.regression_test
@pytest.mark.timeout(2000, method='thread')
def test_fleur_dmi_FePt_film(clear_database, enable_archive_cache, fleur_local_code, inpgen_local_code):
    """
    full example using mae workflow with FePt film structure as input.
    """
    pytest.importorskip('masci_tools', minversion='0.7.3')
    from aiida.orm import Dict, StructureData

    options = Dict({
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'withmpi': False,
    })

    wf_para_scf = {'fleur_runmax': 2, 'itmax_per_run': 120, 'density_converged': 0.3, 'mode': 'density'}

    wf_para_scf = Dict(wf_para_scf)

    wf_para = Dict({
        'beta': {
            'all': 1.57079
        },
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'soc_off': [],
        # 'prop_dir': [1.0, 0.0, 0.0],
        'q_vectors': [[0.0, 0.0, 0.0], [0.125, 0.0, 0.0], [0.250, 0.0, 0.0], [0.375, 0.0, 0.0]],
        'ref_qss': [0.0, 0.0, 0.0],
        'inpxml_changes': [],
    })

    bohr_a_0 = 0.52917721092  # A
    a = 7.497 * bohr_a_0
    cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
    structure = StructureData(cell=cell)
    structure.append_atom(position=(0.0, 0.0, -1.99285 * bohr_a_0), symbols='Fe', name='Fe123')
    structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
    structure.append_atom(position=(0., 0., 2.65059 * bohr_a_0), symbols='Pt')
    structure.pbc = (True, True, False)

    parameters = Dict({
        'atom': {
            'element': 'Pt',
            'lmax': 6
        },
        'atom2': {
            'element': 'Fe',
            'lmax': 6,
        },
        'comp': {
            'kmax': 3.2,
        },
        'kpt': {
            'div1': 8,  #20,
            'div2': 12,  #24,
            'div3': 1
        }
    })

    FleurCode = fleur_local_code
    InpgenCode = inpgen_local_code

    inputs = {
        'scf': {
            'wf_parameters': wf_para_scf,
            'structure': structure,
            'calc_parameters': parameters,
            'options': options,
            'inpgen': InpgenCode,
            'fleur': FleurCode
        },
        'wf_parameters': wf_para,
        'fleur': FleurCode,
        'options': options
    }

    with enable_archive_cache('fleur_dmi_FePt.tar.gz'):
        out, node = run_get_node(FleurDMIWorkChain, **inputs)
    print(out)
    print(node)
    print(get_workchain_report(node, 'REPORT'))

    assert node.is_finished_ok

    outpara = out.get('output_dmi_wc_para', None)
    assert outpara is not None
    outpara = outpara.get_dict()
    print(outpara)

    # check output
    assert outpara.get('warnings') == []
    assert outpara.get('phi') == [
        3.14159265, 3.14159265, 4.71238265, 3.14159265, 3.14159265, 4.71238265, 3.14159265, 3.14159265, 4.71238265,
        3.14159265, 3.14159265, 4.71238265
    ]
    assert outpara.get('theta') == [
        0.0, -1.57079, -1.57079, 0.0, -1.57079, -1.57079, 0.0, -1.57079, -1.57079, 0.0, -1.57079, -1.57079
    ]
    assert outpara.get('q_vectors') == [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.125, 0.0, 0.0],
                                        [0.125, 0.0, 0.0], [0.125, 0.0, 0.0], [0.25, 0.0, 0.0], [0.25, 0.0, 0.0],
                                        [0.25, 0.0, 0.0], [0.375, 0.0, 0.0], [0.375, 0.0, 0.0], [0.375, 0.0, 0.0]]
    assert outpara.get('is_it_force_theorem')
    assert pytest.approx(outpara.get('soc_energies')) == [
        0.0, 0.0, 0.0, 3.2653663495186e-06, 0.0, 0.0068542760815019, 4.625935661818e-06, 0.0, 0.0065824343329045,
        6.5307326990371e-06, 0.0, -0.0020811268200932
    ]


@pytest.mark.skip(reason='not implemented')
@pytest.mark.timeout(5000, method='thread')
def test_fleur_dmi_validation_wrong_inputs(fleur_local_code, inpgen_local_code):
    """
    Test the validation behavior of FleurMaeWorkChain if wrong input is provided it should throw
    an exitcode and not start a Fleur run or crash
    """
    from aiida.orm import Dict

    # prepare input nodes and dicts
    options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 60 * 60,
        'custom_scheduler_commands': ''
    }
    options = Dict(dict=options).store()

    FleurCode = fleur_local_code
    InpgenCode = inpgen_local_code

    ################
    # Create builders
    # interface of exposed scf is tested elsewhere

    #spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM',
    #               message="Invalid workchain parameters.")
    #spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG',
    #               message="Invalid input configuration.")
    #spec.exit_code(233, 'ERROR_INVALID_CODE_PROVIDED',
    #               message="Invalid code node specified, check inpgen and fleur code nodes.")

    # 1. create inputs with wrong wf parameters
    inputs1 = {}

    # 2. create inputs with wrong code
    # 3. create inputs with invalid input config

    ###################
    # now run the builders all should fail early with exit codes

    # 1. structure and fleurinp given
    out, node = run_get_node(FleurDMIWorkChain, **inputs1)
    assert out == {}
    assert node.is_finished
    assert not node.is_finished_ok
    assert node.exit_status == 230
