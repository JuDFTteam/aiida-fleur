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
'''Contains tests for the FleurBaseWorkChain'''
#pylint: disable=no-self-use
import pytest
import os
from aiida.orm import Dict
from aiida.engine.processes.workchains.utils import ProcessHandlerReport

import aiida_fleur
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml')
CALC_ENTRY_POINT = 'fleur.fleur'


@pytest.mark.parametrize('exit_status', [
    'ERROR_FLEUR_CALC_FAILED', 'ERROR_MT_RADII', 'ERROR_NO_RETRIEVED_FOLDER', 'ERROR_OPENING_OUTPUTS',
    'ERROR_NO_OUTXML', 'ERROR_XMLOUT_PARSING_FAILED', 'ERROR_RELAX_PARSING_FAILED'
])
def test_handle_general_error(generate_workchain_base, exit_status):
    """Test `FleurBaseWorkChain._handle_general_error`."""
    exit_codes = FleurCalculation.exit_codes

    process = generate_workchain_base(exit_code=exit_codes(exit_status))
    process.setup()

    result = process._handle_general_error(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG

    result = process.inspect_process()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG


def test_handle_vacuum_spill_error(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_vacuum_spill_error`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_VACUUM_SPILL_RELAX)
    process.setup()

    result = process._handle_vacuum_spill_error(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_VACUUM_SPILL_RELAX

    result = process.inspect_process()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_VACUUM_SPILL_RELAX


def test_handle_mt_relax_error(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_mt_relax_error`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_MT_RADII_RELAX)
    process.setup()

    result = process._handle_mt_relax_error(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_MT_RADII_RELAX

    result = process.inspect_process()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_MT_RADII_RELAX


def test_handle_dirac_equation_no_parent_folder(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_mt_relax_error`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_DROP_CDN)
    process.setup()
    process.validate_inputs()  #Needed so that the inputs are on the context of the workchain

    result = process._handle_dirac_equation(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG

    result = process.inspect_process()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG


def test_handle_dirac_equation_fleurinp_with_relax(generate_workchain_base, create_fleurinp, fixture_code,
                                                   generate_remote_data):
    """Test `FleurBaseWorkChain._handle_mt_relax_error`."""
    from aiida_fleur.common.defaults import default_options
    import io

    INPXML_PATH = os.path.abspath(os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml'))
    relax_file = io.BytesIO(b'<relaxation/>')
    relax_file.name = 'relax.xml'
    fleurinp = create_fleurinp(INPXML_PATH, additional_files=[relax_file])

    fleur = fixture_code('fleur.fleur')
    path = os.path.abspath(os.path.join(aiida_path, '../tests/files/outxml/tmp'))
    remote = generate_remote_data(fleur.computer, path).store()

    inputs = {'code': fleur, 'fleurinp': fleurinp, 'parent_folder': remote, 'options': Dict(default_options)}

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_DROP_CDN, inputs=inputs)
    process.setup()
    process.validate_inputs()  #Needed so that the inputs are on the context of the workchain

    result = process._handle_dirac_equation(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert 'parent_folder' not in process.ctx.inputs

    #Reinsert parent_folder
    process.ctx.inputs.parent_folder = remote
    result = process.inspect_process()
    assert result.status == 0


def test_handle_not_enough_memory_no_solution(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_not_enough_memory`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_NOT_ENOUGH_MEMORY)
    process.setup()
    process.ctx.can_be_optimised = False

    result = process._handle_not_enough_memory(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_MEMORY_ISSUE_NO_SOLUTION

    result = process.inspect_process()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_MEMORY_ISSUE_NO_SOLUTION


def test_handle_not_enough_memory(generate_workchain_base, generate_remote_data, generate_retrieved_data):
    """Test `FleurBaseWorkChain._handle_not_enough_memory`."""
    from aiida.common import LinkType

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_NOT_ENOUGH_MEMORY)
    process.setup()
    process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    code = process.ctx.inputs.code

    #Add outgoing remote folder
    process.ctx.children[-1].store()
    remote = generate_remote_data(code.computer, '/tmp')
    remote.add_incoming(process.ctx.children[-1], link_type=LinkType.CREATE, link_label='remote_folder')
    remote.store()
    generate_retrieved_data(process.ctx.children[-1], 'default')

    result = process._handle_not_enough_memory(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert process.ctx.num_machines == 2
    assert abs(process.ctx.suggest_mpi_omp_ratio - 0.5) < 1e-12
    assert 'settings' in process.ctx.inputs
    assert process.ctx.inputs.settings['remove_from_remotecopy_list'] == ['mixing_history*']

    process.ctx.inputs.settings = Dict({})  #Test that already set inputs also work
    process.ctx.num_machines = 14  #doubling goes over the maximum specified
    result = process.inspect_process()
    assert result.status == 0
    assert process.ctx.num_machines == 20
    assert abs(process.ctx.suggest_mpi_omp_ratio - 0.25) < 1e-12
    assert 'settings' in process.ctx.inputs
    assert process.ctx.inputs.settings['remove_from_remotecopy_list'] == ['mixing_history*']
    assert 'parent_folder' in process.ctx.inputs
    assert process.ctx.inputs.parent_folder.uuid == remote.uuid
    assert 'fleurinp' not in process.ctx.inputs


def test_handle_time_limits(generate_workchain_base, generate_remote_data, generate_retrieved_data):
    """Test `FleurBaseWorkChain._handle_time_limits`."""
    from aiida.common import LinkType

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_TIME_LIMIT)
    process.setup()
    process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    code = process.ctx.inputs.code

    #Add outgoing remote folder
    process.ctx.children[-1].store()
    remote = generate_remote_data(code.computer, '/tmp')
    remote.add_incoming(process.ctx.children[-1], link_type=LinkType.CREATE, link_label='remote_folder')
    remote.store()
    generate_retrieved_data(process.ctx.children[-1], 'default')

    result = process._handle_time_limits(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 12 * 60 * 60
    assert process.ctx.num_machines == 2
    assert process.ctx.inputs.parent_folder.uuid == remote.uuid
    assert 'fleurinp' not in process.ctx.inputs

    process.ctx.inputs.metadata.options['max_wallclock_seconds'] = 80000  #doubling goes over the maximum specified
    process.ctx.num_machines = 14  #doubling goes over the maximum specified
    result = process.inspect_process()
    assert result.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 86400
    assert process.ctx.num_machines == 20
    assert process.ctx.inputs.parent_folder.uuid == remote.uuid
    assert 'fleurinp' not in process.ctx.inputs


def test_handle_time_limits_no_charge_density(generate_workchain_base, generate_remote_data, generate_retrieved_data):
    """Test `FleurBaseWorkChain._handle_time_limits` with remote folder without charge density.
       Expected result continue without charge density and doulbed resources"""
    from aiida.common import LinkType

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_TIME_LIMIT)
    process.setup()
    process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    code = process.ctx.inputs.code

    #Add outgoing remote folder
    process.ctx.children[-1].store()
    remote = generate_remote_data(code.computer, '/tmp')
    remote.add_incoming(process.ctx.children[-1], link_type=LinkType.CREATE, link_label='remote_folder')
    remote.store()
    generate_retrieved_data(process.ctx.children[-1], 'complex_errorout')

    result = process._handle_time_limits(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 12 * 60 * 60
    assert process.ctx.num_machines == 2
    assert 'parent_folder' not in process.ctx.inputs
    assert 'fleurinp' in process.ctx.inputs

    process.ctx.inputs.metadata.options['max_wallclock_seconds'] = 80000  #doubling goes over the maximum specified
    process.ctx.num_machines = 14  #doubling goes over the maximum specified
    result = process.inspect_process()
    assert result.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 86400
    assert process.ctx.num_machines == 20
    assert 'parent_folder' not in process.ctx.inputs
    assert 'fleurinp' in process.ctx.inputs


def test_handle_time_limits_incompatible_mode(generate_workchain_base, generate_remote_data, generate_retrieved_data,
                                              create_fleurinp, fixture_code):
    """Test `FleurBaseWorkChain._handle_time_limits`."""
    from aiida.common import LinkType
    from aiida_fleur.common.defaults import default_options

    INPXML_PATH = os.path.abspath(os.path.join(aiida_path, '../tests/files/inpxml/CuDOSXML/files/inp.xml'))
    fleurinp = create_fleurinp(INPXML_PATH)
    fleur = fixture_code('fleur.fleur')
    path = os.path.abspath(os.path.join(aiida_path, '../tests/files/outxml/tmp'))
    remote_before = generate_remote_data(fleur.computer, path).store()

    inputs = {
        'code': fleur,
        'fleurinp': fleurinp,
        'parent_folder': remote_before,
        'options': Dict(default_options)
    }

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_TIME_LIMIT, inputs=inputs)
    process.setup()
    process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    #Add outgoing remote folder
    process.ctx.children[-1].store()
    remote = generate_remote_data(fleur.computer, '/tmp')
    remote.add_incoming(process.ctx.children[-1], link_type=LinkType.CREATE, link_label='remote_folder')
    remote.store()
    generate_retrieved_data(process.ctx.children[-1], 'default')

    result = process._handle_time_limits(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 12 * 60 * 60
    assert process.ctx.inputs.parent_folder.uuid == remote_before.uuid


def test_handle_time_limits_no_fleurinp(generate_workchain_base, generate_remote_data, generate_retrieved_data,
                                        create_fleurinp, fixture_code):
    """Test `FleurBaseWorkChain._handle_time_limits`."""
    from aiida.common import LinkType
    from aiida_fleur.common.defaults import default_options

    INPXML_PATH = os.path.abspath(os.path.join(aiida_path, '../tests/files/inpxml/CuDOSXML/files/inp.xml'))
    fleurinp = create_fleurinp(INPXML_PATH)
    fleur = fixture_code('fleur.fleur')
    path = os.path.abspath(os.path.join(aiida_path, '../tests/files/outxml/tmp'))
    remote_before = generate_remote_data(fleur.computer, path).store()

    inputs = {
        'code': fleur,
        'fleurinp': fleurinp,
        'parent_folder': remote_before,
        'options': Dict(default_options)
    }

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_TIME_LIMIT, inputs=inputs)
    process.setup()
    process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    process.ctx.inputs.pop('fleurinp')  #Simulate the fact that some previous error handler dropped fleurinp

    #Add outgoing remote folder
    process.ctx.children[-1].store()
    remote = generate_remote_data(fleur.computer, '/tmp')
    remote.add_incoming(process.ctx.children[-1], link_type=LinkType.CREATE, link_label='remote_folder')
    remote.store()
    generate_retrieved_data(process.ctx.children[-1], 'default')

    result = process._handle_time_limits(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 12 * 60 * 60
    assert process.ctx.inputs.parent_folder.uuid == remote.uuid


def test_handle_time_limits_previous_calculation_error(generate_workchain_base, generate_remote_data, create_fleurinp,
                                                       fixture_code, generate_calc_job_node):
    """Test `FleurBaseWorkChain._handle_time_limits`."""
    from aiida.common import LinkType
    from plumpy import ProcessState
    from aiida_fleur.common.defaults import default_options

    INPXML_PATH = os.path.abspath(os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml'))
    fleurinp = create_fleurinp(INPXML_PATH)
    fleur = fixture_code('fleur.fleur')
    path = os.path.abspath(os.path.join(aiida_path, '../tests/files/outxml/tmp'))
    remote_before = generate_remote_data(fleur.computer, path)

    prev_calc = generate_calc_job_node('fleur.fleur', inputs={'parameters': Dict()})
    prev_calc.set_process_state(ProcessState.FINISHED)
    prev_calc.set_exit_status(FleurCalculation.exit_codes.ERROR_TIME_LIMIT.status)
    prev_calc.store()

    remote_before.add_incoming(prev_calc, link_type=LinkType.CREATE, link_label='remote_folder')
    remote_before.store()

    inputs = {
        'code': fleur,
        'fleurinp': fleurinp,
        'parent_folder': remote_before,
        'options': Dict(default_options)
    }

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_TIME_LIMIT, inputs=inputs)
    process.setup()
    process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    #Add outgoing remote folder
    process.ctx.children[-1].add_incoming(remote_before, link_type=LinkType.INPUT_CALC, link_label='parent_folder')
    process.ctx.children[-1].store()
    remote = generate_remote_data(fleur.computer, '/tmp')
    remote.add_incoming(process.ctx.children[-1], link_type=LinkType.CREATE, link_label='remote_folder')
    remote.store()

    result = process._handle_time_limits(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0
    assert process.ctx.inputs.metadata.options['max_wallclock_seconds'] == 6 * 60 * 60

    result = process.inspect_process()
    assert result.status == 0


def test_base_fleur_worlchain_forbid_single_mpi(generate_workchain_base, create_fleurinp, fixture_code):

    from aiida_fleur.common.defaults import default_options
    from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

    INPXML_PATH = os.path.abspath(os.path.join(aiida_path, '../tests/files/inpxml/CuDOSXML/files/inp.xml'))
    fleurinp = create_fleurinp(INPXML_PATH)
    fm = FleurinpModifier(fleurinp)
    fm.set_nkpts(1033)  #set to bad number to make the only parallelization 1 node 1 MPI
    fleurinp = fm.freeze()

    fleur = fixture_code('fleur.fleur')

    inputs = {
        'code':
        fleur,
        'fleurinp':
        fleurinp,
        'add_comp_para':
        Dict({
            'only_even_MPI': False,
            'forbid_single_mpi': True,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        }),
        'options':
        Dict(default_options)
    }

    process = generate_workchain_base(inputs=inputs)
    process.setup()
    status = process.validate_inputs()  #Sets up all the context in order for the memory error handler to work

    assert status == FleurBaseWorkChain.exit_codes.ERROR_NOT_OPTIMAL_RESOURCES


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurBaseWorkChain():
    """
    Regression tests for the FleurBaseWorkChain
    """

    @pytest.mark.skip
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_fleurinp_Si(self, with_export_cache, fleur_local_code, create_fleurinp):
        """
        full example using FleurBaseWorkChain with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        from aiida.engine import run_get_node

        options = {
            'resources': {
                'num_machines': 1
            },
            'max_wallclock_seconds': 5 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }

        # create process builder to set parameters
        builder = FleurBaseWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given'
        builder.metadata.label = 'FleurBase_test_Si_bulk'
        builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH)
        builder.options = Dict(options)
        builder.code = fleur_local_code

        # now run calculation
        with with_export_cache('fleur_base_fleurinp_Si.tar.gz'):
            out, node = run_get_node(builder)

        # check output

        #assert abs(n.get('starting_fermi_energy') - 0.409241) < 10**-14

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_structure_Si(self, run_with_cache, fleur_local_code):
        """
        Full regression test of FleurBaseWorkChain starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_continue_from_x(self, run_with_cache, fleur_local_code):
        """
        Full regression test of FleurBaseWorkChain while encountering x, handling it and restart
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_validation_wrong_inputs(self, run_with_cache, fleur_local_code):
        """
        Test the validation behavior of FleurBaseWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
