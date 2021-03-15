# -*- coding: utf-8 -*-
''' Contains tests for the fleur parser and its routines. '''

from __future__ import absolute_import
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


# parse_xmlout_file
def test_parse_xmlout_file():
    """
    tests if the routine that parsers the outputfile, produces the right output, no aiida datastructures,
    with the right content
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file

    filename = os.path.abspath('./files/outxml/BeTi_out.xml')

    simple_out, complex_out, parser_info_out, successful = parse_xmlout_file(filename)

    expected_simple_out_dict = {
        'bandgap': 0.0052350388,
        'bandgap_units': 'eV',
        'charge_den_xc_den_integral': -45.0947551412,
        'charge_density': 8.7984e-06,
        'creator_name': 'fleur 27',
        'creator_target_architecture': 'GEN',
        'creator_target_structure': ' ',
        'density_convergence_units': 'me/bohr^3',
        'energy': -23635.691961010132,
        'energy_core_electrons': -496.172547773,
        'energy_hartree': -868.5956587197,
        'energy_hartree_units': 'Htr',
        'energy_units': 'eV',
        'energy_valence_electrons': -7.1055909396,
        'fermi_energy': 0.3451127139,
        'fermi_energy_units': 'Htr',
        'force_largest': -0.0,
        'kmax': 4.5,
        'number_of_atom_types': 2,
        'number_of_atoms': 2,
        'number_of_iterations': 19,
        'number_of_iterations_total': 19,
        'number_of_kpoints': 56,
        'number_of_species': 1,
        'number_of_spin_components': 1,
        'number_of_symmetries': 48,
        'output_file_version': '0.27',
        'start_date': {
            'date': '2017/09/10',
            'time': '07:58:10'
        },
        'end_date': {
            'date': '2017/09/10',
            'time': '07:58:34'
        },
        'sum_of_eigenvalues': -503.2781387127,
        'title': 'Be-Ti, bulk compounds',
        'walltime': 24,
        'walltime_units': 'seconds',
        'warnings': {
            'debug': {},
            'error': {},
            'info': {},
            'warning': {}
        }
    }

    expected_parser_info_out = {'parser_info': 'AiiDA Fleur Parser v0.3.2', 'parser_warnings': [], 'unparsed': []}
    simple_out.pop('outputfile_path', None)  # otherwise test will fail on different installations
    # also this should go away any way...

    assert successful
    assert expected_simple_out_dict == simple_out
    assert expected_parser_info_out == parser_info_out


# test special cases parser behavior
def test_parse_xmlout_file_broken_xmlout_file():
    """
    tests the behavior of the parse_xmlout_file routine in the case of an broken out.xml file.
    Here broken after serveral iteration, should parse all iteration except last.
    (which can happen in the case of some kill, or Non regular termination of FLEUR)
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file

    filename = os.path.abspath('./files/outxml/special/broken_BeTi_out.xml')

    simple_out, complex_out, parser_info_out, successful = parse_xmlout_file(filename)

    expected_parser_info_out = {
        'last_iteration_parsed':
        15,
        'parser_info':
        'AiiDA Fleur Parser v0.3.2',
        'parser_warnings': [
            'The out.xml file is broken I try to repair it.',
            'Endtime was unparsed, inp.xml prob not complete, do not believe the walltime!'
        ],
        'unparsed': []
    }

    assert successful
    assert parser_info_out['last_iteration_parsed'] == 15
    assert expected_parser_info_out['unparsed'] == parser_info_out['unparsed']
    assert expected_parser_info_out['parser_warnings'] == parser_info_out['parser_warnings']


def test_parse_xmlout_file_broken_first_xmlout_file():
    """
    tests the behavior of the parse_xmlout_file routine in the case of an broken out.xml file.
    Here broken in first iteration, should parse nothing.
    (which can happen in the case of some kill, or Non regular termination of FLEUR)
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file

    filename = os.path.abspath('./files/outxml/special/broken_first_BeTi_out.xml')

    simple_out, complex_out, parser_info_out, successful = parse_xmlout_file(filename)

    expected_parser_info_out = {
        'last_iteration_parsed':
        1,
        'parser_info':
        'AiiDA Fleur Parser v0.3.2',
        'parser_warnings': [
            'The out.xml file is broken I try to repair it.',
            'Can not get attributename: "units" from node "[]", because node is not an element of etree.',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError', 'Could not convert: "None" to float, TypeError',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "units" from node "[]", because node is not an element of etree.',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "value" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Can not get attributename: "units" from node "[]", because node is not an element of etree.',
            'Can not get attributename: "units" from node "[]", because node is not an element of etree.',
            'Can not get attributename: "distance" from node "[]", because node is not an element of etree.',
            'Could not convert: "None" to float, TypeError',
            'Endtime was unparsed, inp.xml prob not complete, do not believe the walltime!'
        ],
        'unparsed': [{
            'energy_hartree': None,
            'iteration': '    1'
        }, {
            'energy': None,
            'iteration': '    1'
        }, {
            'iteration': '    1',
            'sum_of_eigenvalues': None
        }, {
            'energy_core_electrons': None,
            'iteration': '    1'
        }, {
            'energy_valence_electrons': None,
            'iteration': '    1'
        }, {
            'charge_den_xc_den_integral': None,
            'iteration': '    1'
        }, {
            'bandgap': None,
            'iteration': '    1'
        }, {
            'fermi_energy': None,
            'iteration': '    1'
        }, {
            'charge_density': None,
            'iteration': '    1'
        }]
    }

    assert successful
    assert parser_info_out['last_iteration_parsed'] == 1
    assert expected_parser_info_out['unparsed'] == parser_info_out['unparsed']
    assert expected_parser_info_out['parser_warnings'] == parser_info_out['parser_warnings']


def test_parse_xmlout_file_fortran_garbage_in_xmlout_file():
    """
    tests the behavior of the parse_xmlout_file routine in the case of an individual 'garbage' in the out.xml file.
    Fortran NANs and INFs will be parsed fine, ** will not be parsed.
    (which can happen in the case of some kill, or Non regular termination of FLEUR)
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file

    filename = os.path.abspath('./files/outxml/special/Fortran_garbage_BeTi_out.xml')

    simple_out, complex_out, parser_info_out, successful = parse_xmlout_file(filename)

    exp_partial_simple_out_dict = {
        'bandgap_units': 'eV',
        'energy': float('Inf'),
        'energy_hartree': float('Inf'),
        'fermi_energy': float('NaN'),
        'warnings': {
            'debug': {},
            'error': {},
            'info': {},
            'warning': {}
        }
    }

    expected_parser_info_out = {
        'parser_info':
        'AiiDA Fleur Parser v0.3.2',
        'parser_warnings': [
            'Could not convert: "**" to float, ValueError',
            'Could not convert: "        !#@)!(U$*(Y" to float, ValueError'
        ],
        'unparsed': [{
            'bandgap': '**',
            'iteration': '   19'
        }, {
            'charge_density': '        !#@)!(U$*(Y',
            'iteration': '   19'
        }]
    }

    #TODO maybe in the case on unpared, things should be initialized, here they are missing...
    def isNaN(num):
        return math.isnan(num)  #num != num

    assert successful
    assert exp_partial_simple_out_dict['energy'] == simple_out['energy']
    assert exp_partial_simple_out_dict['energy_hartree'] == simple_out['energy_hartree']
    assert isNaN(exp_partial_simple_out_dict['fermi_energy']) == isNaN(simple_out['fermi_energy'])
    assert 'bandgap' not in list(simple_out.keys())

    assert expected_parser_info_out['unparsed'] == parser_info_out['unparsed']
    assert expected_parser_info_out['parser_warnings'] == parser_info_out['parser_warnings']


def test_parse_xmlout_file_empty_file():
    """
    tests the behavior of the parse_xmlout_file routine in the case of an empty file
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file

    filename = os.path.abspath('./files/outxml/special/empty_out.xml')

    simple_out, complex_out, parser_info_out, successful = parse_xmlout_file(filename)

    expected_parser_info_out = {
        'parser_info':
        'AiiDA Fleur Parser v0.3.2',
        'parser_warnings': [
            'The out.xml file is broken I try to repair it.',
            'Skipping the parsing of the xml file. Repairing was not possible.'
        ],
        'unparsed': []
    }

    assert not successful
    assert expected_parser_info_out == parser_info_out


# test parser success for all out files in folder
file_path1 = '../files/outxml/all_test/'
outxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
outxmlfilefolder_valid = os.path.abspath(os.path.join(outxmlfilefolder, file_path1))

outxmlfilelist = []
for subdir, dirs, files in os.walk(outxmlfilefolder_valid):
    for file in files:
        if file.endswith('.xml'):
            outxmlfilelist.append(os.path.join(subdir, file))


@pytest.mark.parametrize('xmloutfile', outxmlfilelist)
def test_fleurparse_all_xmlout_file(xmloutfile):
    """
    tests if the routine that parsers the outputfile, succeeds for all out files
    """
    from aiida_fleur.parsers.fleur import parse_xmlout_file

    simple_out, complex_out, parser_info_out, successful = parse_xmlout_file(xmloutfile)

    assert successful


def test_fleurparse_relax_file():
    """Test if parsing of a given relax.xml file is successfull"""
    from aiida_fleur.parsers.fleur import parse_relax_file
    from aiida.orm import Dict

    filename = os.path.abspath('./files/relaxxml/Fe_relax.xml')
    with open(filename, 'r') as relaxfile:
        result = parse_relax_file(relaxfile)
    assert isinstance(result, Dict)
    assert result.get_dict() != {}


# parse_dos_file, test for different dos files with spin and without
@pytest.mark.skip(reason='Test is not implemented')
def test_parse_dos_file():
    """
    test for the fleur dos file parser. test if right output, datastructures are produced without error
    """
    from aiida_fleur.parsers.fleur import parse_dos_file
    # test if array data is prodcued without error
    assert False


# parse_bands_file
@pytest.mark.skip(reason='Test is not implemented')
def test_parse_bands_file():
    """
    test for band file parse routine.
    """

    from aiida_fleur.parsers.fleur import parse_bands_file

    # test if a bandsdata object is produced
    assert False


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
