''' Contains tests for the fleur parser and its routines. '''

import os
import pytest
import math
from aiida.common import AttributeDict
from aiida import orm
import aiida_fleur
#TODO use pytest-regression for full dict tests, easier to update if parser changes.

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/Si/inp.xml')
# for relaxation path
TEST_INP_XML_PATH1 = os.path.join(aiida_path, '../tests/parsers/fixtures/fleur/relax/inp.xml')


def test_fleurparse_relax_file(test_file):
    """Test if parsing of a given relax.xml file is successfull"""
    from aiida_fleur.parsers.fleur import parse_relax_file
    from masci_tools.io.parsers.fleur_schema import InputSchemaDict
    from aiida.orm import Dict

    schema_dict = InputSchemaDict.fromVersion('0.34')
    with open(test_file('relaxxml/Fe_relax.xml')) as relaxfile:
        result = parse_relax_file(relaxfile, schema_dict)
    assert isinstance(result, Dict)
    assert result.get_dict() != {}


# test the full parser itself. on all kinds of different output files.

# test if the right aiida datastructures are produced for different output
# also check if errors are working...
# if an empty and broken file works, broken before and after first iteration


def test_fleur_parser_default_full(fixture_localhost, generate_parser, generate_calc_job_node, create_fleurinp,
                                   data_regression):
    """
    Default inpgen parser test of a successful inpgen calculation.
    Checks via data regression if attributes of outputparamters are the same
    """

    name = 'default'
    entry_point_calc_job = 'fleur.fleur'
    entry_point_parser = 'fleur.fleurparser'

    inputs = AttributeDict({'fleurinp': create_fleurinp(TEST_INP_XML_PATH), 'metadata': {}})

    #change retrieve list to save space
    retrieve_list = [
        'out.xml', 'inp.xml', 'shell.out', 'out.error', 'cdn1', '_scheduler-stdout.txt', '_scheduler-stderr.txt'
    ]
    node = generate_calc_job_node(entry_point_calc_job,
                                  fixture_localhost,
                                  name,
                                  inputs,
                                  store=True,
                                  retrieve_list=retrieve_list)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node), [log.message for log in orm.Log.objects.get_logs_for(node)]
    assert 'output_parameters' in results
    assert 'output_params_complex' not in results
    assert 'relax_parameters' not in results
    assert 'error_params' not in results

    data_regression.check({
        'output_parameters': clean_outdict_for_reg_dump(results['output_parameters'].get_dict()),
    })


'''
def test_fleur_parser_band_dos(fixture_localhost, generate_parser, generate_calc_job_node, create_fleurinp, data_regression):
    """
    Default inpgen parser test of a successful inpgen calculation.
    Checks via data regression if attributes of fleurinp are the same
    """

    name = 'band_dos'
    entry_point_calc_job = 'fleur.fleur'
    entry_point_parser = 'fleur.fleurparser'

    inputs = AttributeDict({'fleurinp': create_fleurinp(TEST_INP_XML_PATH),
                             'metadata' : {}})

    #change retrieve list to save space
    retrieve_list = ['out.xml', 'inp.xml', 'shell.out', 'out.error','cdn1','_scheduler-stdout.txt','_scheduler-stderr.txt']
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True, retrieve_list=retrieve_list)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node), [log.message for log in orm.Log.objects.get_logs_for(node)]
    assert 'output_parameters' in results
    assert 'output_params_complex' not in results
    assert 'relax_parameters' not in results
    assert 'error_params' not in results

    data_regression.check({
        'output_parameters': results['output_parameters'].attributes,
       })
'''


def test_fleur_parser_relax(fixture_localhost, generate_parser, generate_calc_job_node, create_fleurinp,
                            data_regression):
    """
    Default inpgen parser test of a successful inpgen calculation.
    Checks via data regression if attributes of fleurinp are the same
    """

    name = 'relax'
    entry_point_calc_job = 'fleur.fleur'
    entry_point_parser = 'fleur.fleurparser'

    inputs = AttributeDict({'fleurinp': create_fleurinp(TEST_INP_XML_PATH1), 'metadata': {}})

    #change retrieve list to save space
    retrieve_list = ['out.xml', 'out.error', 'relax.xml']
    node = generate_calc_job_node(entry_point_calc_job,
                                  fixture_localhost,
                                  name,
                                  inputs,
                                  store=True,
                                  retrieve_list=retrieve_list)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node), [log.message for log in orm.Log.objects.get_logs_for(node)]
    assert 'output_parameters' in results
    assert 'output_params_complex' not in results
    assert 'relax_parameters' in results
    assert 'error_params' not in results

    data_regression.check({
        'output_parameters': clean_outdict_for_reg_dump(results['output_parameters'].get_dict()),
        'relax_parameters': results['relax_parameters'].get_dict()
    })


def test_fleur_parser_MT_overlap_erroroutput(fixture_localhost, generate_parser, generate_calc_job_node,
                                             create_fleurinp, data_regression):
    """
    Default inpgen parser test of a failed fleur calculation.
    """

    name = 'mt_overlap_errorout'
    entry_point_calc_job = 'fleur.fleur'
    entry_point_parser = 'fleur.fleurparser'

    inputs = AttributeDict({'fleurinp': create_fleurinp(TEST_INP_XML_PATH1), 'metadata': {}})

    #change retrieve list to save space
    retrieve_list = ['out.xml', 'out.error', 'relax.xml']
    node = generate_calc_job_node(entry_point_calc_job,
                                  fixture_localhost,
                                  name,
                                  inputs,
                                  store=True,
                                  retrieve_list=retrieve_list)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_MT_RADII_RELAX.status
    assert 'output_parameters' not in results
    assert 'output_params_complex' not in results
    assert 'relax_parameters' not in results
    assert 'error_params' in results
    data_regression.check({'error_params': results['error_params'].get_dict()})


def test_fleur_parser_complex_erroroutput(fixture_localhost, generate_parser, generate_calc_job_node, create_fleurinp,
                                          data_regression):
    """
    Default inpgen parser test of a successful inpgen calculation.
    Checks via data regression if attributes of fleurinp are the same
    """

    name = 'complex_errorout'
    entry_point_calc_job = 'fleur.fleur'
    entry_point_parser = 'fleur.fleurparser'

    inputs = AttributeDict({'fleurinp': create_fleurinp(TEST_INP_XML_PATH), 'metadata': {}})

    #change retrieve list to save space
    retrieve_list = ['out.xml', 'out.error', 'usage.json']
    node = generate_calc_job_node(entry_point_calc_job,
                                  fixture_localhost,
                                  name,
                                  inputs,
                                  store=True,
                                  retrieve_list=retrieve_list)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_FLEUR_CALC_FAILED.status

    assert 'output_parameters' not in results
    assert 'output_params_complex' not in results
    assert 'relax_parameters' not in results
    assert 'error_params' not in results


def clean_outdict_for_reg_dump(outdict):
    """
    Apparently the regression dumper has problems with
    '  ', '0.33', 'fleur 31', dates
    we remove these keys.
    """
    outdict.pop('creator_target_structure', None)
    outdict.pop('creator_name', None)
    outdict.pop('creator_target_architecture', None)
    outdict.pop('title', None)
    outdict.pop('output_file_version', None)
    outdict.pop('start_date', None)
    outdict.pop('end_date', None)
    outdict.pop('relax_atomtype_info', None)

    return outdict
