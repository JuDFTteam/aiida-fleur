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
''' Contains tests for the FleurCFWorkchain '''
import pytest
from aiida_fleur.workflows.cfcoeff import FleurCFCoeffWorkChain
from aiida import orm
from aiida.engine import run_get_node
from aiida.cmdline.utils.common import get_workchain_report, get_calcjob_report


@pytest.mark.regression_test
@pytest.mark.timeout(1000, method='thread')
def test_fleur_cfcoeff_structure_no_analogue(with_export_cache, fleur_local_code, inpgen_local_code,
                                             generate_smco5_structure, clear_database, aiida_caplog,
                                             show_workchain_summary):
    """
    Full example using the CFCoeff workchain with just a structure as input.
    Calls scf for analogue and rare-earth system
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
    desc = FleurCode.description
    with_hdf5 = False
    if desc is not None:
        if 'hdf5' in desc:
            with_hdf5 = True
        elif 'Hdf5' in desc:
            with_hdf5 = True
        elif 'HDF5' in desc:
            with_hdf5 = True
        else:
            with_hdf5 = False
    if not with_hdf5:
        pytest.skip('CFCoeff workchain only works with HDF5')

    # create process builder to set parameters
    builder = FleurCFCoeffWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur CFcoeff test for SmCo5 bulk with structure data given'
    builder.metadata.label = 'FleurCFCoeff_test_analogue'

    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()
    builder.scf.inpgen = inpgen_local_code
    builder.scf.structure = generate_smco5_structure()
    builder.scf.calc_parameters = orm.Dict(
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
    builder.wf_parameters = orm.Dict(dict={'element': 'Sm'})

    with with_export_cache('fleur_cfcoeff_smco5_structure_no_analogue.tar.gz'):
        out, node = run_get_node(builder)
    #print(out)
    #print(node)

    show_workchain_summary(node)

    #assert node.is_finished_ok
    # check output
    assert 'output_cfcoeff_wc_para' in out
    n = out['output_cfcoeff_wc_para']
    n = n.get_dict()
    assert 'output_cfcoeff_wc_potentials' in out
    assert 'output_cfcoeff_wc_charge_densities' in out

    from pprint import pprint
    pprint(n)

    assert n['cf_coefficients_convention'] == 'Stevens'
    assert n['cf_coefficients_site_symmetries'] == ['6/mmm']
    assert n['angle_a_to_x_axis'] == 0.0
    assert n['angle_c_to_z_axis'] == 0.0

    assert sorted(n['cf_coefficients_spin_up'].keys()) == ['2/0', '4/0', '6/-6', '6/0', '6/6']
    assert sorted(n['cf_coefficients_spin_down'].keys()) == ['2/0', '4/0', '6/-6', '6/0', '6/6']

    keys = sorted(n['cf_coefficients_spin_up'].keys())
    assert pytest.approx([n['cf_coefficients_spin_up'][key] for key in keys]) \
         == [-530.07676884271, -51.531259261553, 91.429428364653,3.9379215268871, 91.429428364653]
    assert pytest.approx([n['cf_coefficients_spin_down'][key] for key in keys]) \
         == [-585.50088518635, 107.57251558557, 66.240659350976,2.8694095323364, 66.240659350976]


@pytest.mark.regression_test
@pytest.mark.timeout(1000, method='thread')
def test_fleur_cfcoeff_structure_analogue(with_export_cache, fleur_local_code, inpgen_local_code,
                                          generate_smco5_structure, clear_database, aiida_caplog,
                                          show_workchain_summary):
    """
    Full example using the CFCoeff workchain with just a structure as input.
    Calls scf for analogue and rare-earth system
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
    desc = FleurCode.description
    with_hdf5 = False
    if desc is not None:
        if 'hdf5' in desc:
            with_hdf5 = True
        elif 'Hdf5' in desc:
            with_hdf5 = True
        elif 'HDF5' in desc:
            with_hdf5 = True
        else:
            with_hdf5 = False
    if not with_hdf5:
        pytest.skip('CFCoeff workchain only works with HDF5')

    # create process builder to set parameters
    builder = FleurCFCoeffWorkChain.get_builder()
    builder.metadata.description = 'Simple Fleur CFcoeff test for SmCo5 bulk with structure data given'
    builder.metadata.label = 'FleurCFCoeff_test_analogue'

    builder.scf.fleur = FleurCode
    builder.scf.options = orm.Dict(dict=options).store()
    builder.scf.inpgen = inpgen_local_code
    builder.scf.structure = generate_smco5_structure()
    builder.scf.calc_parameters = orm.Dict(
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
    builder.scf_rare_earth_analogue.fleur = FleurCode
    builder.scf_rare_earth_analogue.inpgen = inpgen_local_code
    builder.scf_rare_earth_analogue.options = orm.Dict(dict=options).store()
    builder.wf_parameters = orm.Dict(dict={'element': 'Sm', 'rare_earth_analogue': True})

    with with_export_cache('fleur_cfcoeff_smco5_structure_analogue.tar.gz'):
        out, node = run_get_node(builder)
    #print(out)
    #print(node)

    show_workchain_summary(node)

    #assert node.is_finished_ok
    # check output
    assert 'output_cfcoeff_wc_para' in out
    n = out['output_cfcoeff_wc_para']
    n = n.get_dict()
    assert 'output_cfcoeff_wc_potentials' in out
    assert 'output_cfcoeff_wc_charge_densities' in out

    from pprint import pprint
    pprint(n)

    assert n['cf_coefficients_convention'] == 'Stevens'
    assert n['cf_coefficients_site_symmetries'] == ['6/mmm']
    assert n['angle_a_to_x_axis'] == 0.0
    assert n['angle_c_to_z_axis'] == 0.0

    assert sorted(n['cf_coefficients_spin_up'].keys()) == ['2/0', '4/0', '6/-6', '6/0', '6/6']
    assert sorted(n['cf_coefficients_spin_down'].keys()) == ['2/0', '4/0', '6/-6', '6/0', '6/6']

    keys = sorted(n['cf_coefficients_spin_up'].keys())
    assert pytest.approx([n['cf_coefficients_spin_up'][key] for key in keys]) \
         == [-1326.3111439024, 29.816507610986, 80.111746599164, 3.1490421501724, 80.111746599164]
    assert pytest.approx([n['cf_coefficients_spin_down'][key] for key in keys]) \
         == [-1237.5714206598,
             20.016912116816,
             75.244818163538,
             2.6312426823951,
             75.244818163538]
