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
'''Contains tests for the FleurBaseWorkChain'''
import pytest
import aiida_fleur
import os
from aiida.orm import Dict
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.common.workchain.utils import ErrorHandlerReport

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, 'tests/files/inpxml/Si/inp.xml')
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

    result = process._handle_general_error(process.ctx.calculations[-1])
    assert isinstance(result, ErrorHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG

    result = process.inspect_calculation()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG


def test_handle_vacuum_spill_error(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_vacuum_spill_error`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_VACUUM_SPILL_RELAX)
    process.setup()

    result = process._handle_vacuum_spill_error(process.ctx.calculations[-1])
    assert isinstance(result, ErrorHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_VACUUM_SPILL_RELAX

    result = process.inspect_calculation()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_VACUUM_SPILL_RELAX


def test_handle_mt_relax_error(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_mt_relax_error`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_MT_RADII_RELAX)
    process.setup()

    result = process._handle_mt_relax_error(process.ctx.calculations[-1])
    assert isinstance(result, ErrorHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_MT_RADII_RELAX

    result = process.inspect_calculation()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_MT_RADII_RELAX


def test_handle_dirac_equation_no_parent_folder(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_mt_relax_error`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_DROP_CDN)
    process.setup()

    result = process._handle_dirac_equation(process.ctx.calculations[-1])
    assert isinstance(result, ErrorHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_SOMETHING_WENT_WRONG

    result = process.inspect_calculation()
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

    inputs = {'code': fleur, 'fleurinpdata': fleurinp, 'parent_folder': remote, 'options': Dict(dict=default_options)}

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_DROP_CDN, inputs=inputs)
    process.setup()
    process.validate_inputs()  #Needed so that the inputs are on the context of the workchain

    result = process._handle_dirac_equation(process.ctx.calculations[-1])
    assert isinstance(result, ErrorHandlerReport)
    assert not result.do_break
    assert 'parent_folder' not in process.ctx.inputs

    result = process.inspect_calculation()
    assert result is None


def test_handle_not_enough_memory_no_solution(generate_workchain_base):
    """Test `FleurBaseWorkChain._handle_not_enough_memory`."""

    process = generate_workchain_base(exit_code=FleurCalculation.exit_codes.ERROR_NOT_ENOUGH_MEMORY)
    process.setup()
    process.ctx.can_be_optimised = False

    result = process._handle_not_enough_memory(process.ctx.calculations[-1])
    assert isinstance(result, ErrorHandlerReport)
    assert result.do_break
    assert result.exit_code == FleurBaseWorkChain.exit_codes.ERROR_NOT_ENOUGH_MEMORY_NO_SOLUTION

    result = process.inspect_calculation()
    assert result == FleurBaseWorkChain.exit_codes.ERROR_NOT_ENOUGH_MEMORY_NO_SOLUTION


# tests
@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class Test_FleurBaseWorkChain():
    """
    Regression tests for the FleurBaseWorkChain
    """

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_fleurinp_Si(self, run_with_cache, mock_code_factory, create_fleurinp):
        """
        full example using FleurBaseWorkChain with just a fleurinp data as input.
        Several fleur runs needed till convergence
        """
        from aiida.orm import Code, load_node, StructureData
        from numpy import array

        options = {
            'resources': {
                'num_machines': 1
            },
            'max_wallclock_seconds': 5 * 60,
            'withmpi': False,
            'custom_scheduler_commands': ''
        }

        FleurCode = mock_code = mock_code_factory(
            label='fleur',
            data_dir_abspath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_dir/'),
            entry_point=CALC_ENTRY_POINT,
            ignore_files=['_aiidasubmit.sh', 'cdnc', 'out', 'FleurInputSchema.xsd', 'cdn.hdf', 'usage.json', 'cdn??'])
        # create process builder to set parameters
        builder = FleurBaseWorkChain.get_builder()
        builder.metadata.description = 'Simple Fleur SCF test for Si bulk with fleurinp data given'
        builder.metadata.label = 'FleurSCF_test_Si_bulk'
        builder.fleurinp = create_fleurinp(TEST_INP_XML_PATH)
        builder.options = Dict(dict=options)
        builder.fleur = FleurCode

        # now run calculation
        out, node = run_with_cache(builder)

        # check output

        #assert abs(n.get('starting_fermi_energy') - 0.409241) < 10**-14

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_structure_Si(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurBaseWorkChain starting with a crystal structure and parameters
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_continue_from_x(self, run_with_cache, mock_code_factory):
        """
        Full regression test of FleurBaseWorkChain while encountering x, handling it and restart
        """
        assert False

    @pytest.mark.skip(reason='Test is not implemented')
    @pytest.mark.timeout(500, method='thread')
    def test_fleur_base_validation_wrong_inputs(self, run_with_cache, mock_code_factory):
        """
        Test the validation behavior of FleurBaseWorkChain if wrong input is provided it should throw
        an exitcode and not start a Fleur run or crash
        """
        assert False
