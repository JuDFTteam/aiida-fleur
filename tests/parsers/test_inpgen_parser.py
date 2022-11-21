''' Contains tests for the inpgen parser and its routines. '''
# TODO: implement all

# test the full parser itself.

from aiida.common import AttributeDict
from aiida import orm


def test_inpgen_parser_default(fixture_localhost, generate_parser, generate_calc_job_node, generate_structure,
                               data_regression):
    """
    Default inpgen parser test of a successful inpgen calculation.
    Checks via data regression if attributes of fleurinp are the same
    """

    name = 'default'
    entry_point_calc_job = 'fleur.inpgen'
    entry_point_parser = 'fleur.fleurinpgenparser'

    inputs = AttributeDict({'structure': generate_structure(), 'metadata': {}})
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node), [log.message for log in orm.Log.objects.get_logs_for(node)]
    assert 'fleurinp' in results

    data_regression.check({
        'fleurinp': results['fleurinp'].inp_dict,
    })


def test_inpgen_parser_no_inpxml(fixture_localhost, generate_parser, generate_calc_job_node, generate_structure):
    """
    Default inpgen parser test of a failed inpgen calculation, inp.xml file missing.
    """

    name = 'no_inpxml'
    entry_point_calc_job = 'fleur.inpgen'
    entry_point_parser = 'fleur.fleurinpgenparser'

    inputs = AttributeDict({'structure': generate_structure(), 'metadata': {}})
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_NO_INPXML.status
    assert 'fleurinp' not in results


def test_inpgen_parser_no_other_files(fixture_localhost, generate_parser, generate_calc_job_node, generate_structure):
    """
    Default inpgen parser test of a failed inpgen calculation, where files are missing.
    """

    name = 'no_otherfiles'
    entry_point_calc_job = 'fleur.inpgen'
    entry_point_parser = 'fleur.fleurinpgenparser'

    inputs = AttributeDict({'structure': generate_structure(), 'metadata': {}})
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_MISSING_RETRIEVED_FILES.status
    assert 'fleurinp' not in results


def test_inpgen_parser_broken_inpxml(fixture_localhost, generate_parser, generate_calc_job_node, generate_structure):
    """
    Default inpgen parser test of a failed inpgen calculation with broken xml.
    """

    name = 'broken_inpxml'
    entry_point_calc_job = 'fleur.inpgen'
    entry_point_parser = 'fleur.fleurinpgenparser'

    inputs = AttributeDict({'structure': generate_structure(), 'metadata': {}})
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_FLEURINPDATA_INPUT_NOT_VALID.status
    assert 'fleurinp' not in results


def test_inpgen_parser_nonvalid_inpxml(fixture_localhost, generate_parser, generate_calc_job_node, generate_structure):
    """
    Default inpgen parser test of a failed inpgen calculation with non valid inpmxl.
    """

    name = 'novalid_inpxml'
    entry_point_calc_job = 'fleur.inpgen'
    entry_point_parser = 'fleur.fleurinpgenparser'

    inputs = AttributeDict({'structure': generate_structure(), 'metadata': {}})
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_FLEURINPDATA_INPUT_NOT_VALID.status
    assert 'fleurinp' not in results


def test_inpgen_parser_unknown_profile(fixture_localhost, generate_parser, generate_calc_job_node, generate_structure):
    """
    Default inpgen parser test of a failed inpgen calculation with a unknown profile.
    """

    name = 'unknown_profile'
    entry_point_calc_job = 'fleur.inpgen'
    entry_point_parser = 'fleur.fleurinpgenparser'

    inputs = AttributeDict({'structure': generate_structure(), 'metadata': {}})
    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, inputs, store=True)
    parser = generate_parser(entry_point_parser)
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_failed, calcfunction.exit_status
    assert calcfunction.exit_status == node.process_class.exit_codes.ERROR_UNKNOWN_PROFILE.status
    assert 'non_existent' in calcfunction.exit_message
    assert 'fleurinp' not in results


# TODO test multi files, enpara, kpts, relax.xml nnmpmat ...
