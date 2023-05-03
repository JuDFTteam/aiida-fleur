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
'''
Contains extensive tests for the FleurinpData structure of AiiDA-Fleur
'''
import os
import pytest

# Collect the input files
file_path1 = '../files/inpxml/'
file_path2 = '../files/nonvalid_inpxml'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
inpxmlfilefolder_valid = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))
inpxmlfilefolder_non_valid = os.path.abspath(os.path.join(inpxmlfilefolder, file_path2))

inpxmlfilelist = []
for subdir, dirs, files in os.walk(inpxmlfilefolder_valid):
    for file in files:
        if file.endswith('.xml'):
            inpxmlfilelist.append(os.path.join(subdir, file))

inpxmlfilelist2 = []
for subdir, dirs, files in os.walk(inpxmlfilefolder_non_valid):
    for file in files:
        if file.endswith('.xml'):
            inpxmlfilelist2.append(os.path.join(subdir, file))

INPXML_LATNAM_DEFINITION = [
    'Fe_bct_SOCXML', 'CuBulkXML', 'CuBandXML', 'Bi2Te3XML', 'PTO-SOCXML', 'Fe_bctXML', 'Fe_1lXML', 'Fe_1l_SOCXML',
    'Fe_bct_LOXML', 'NiO_ldauXML', 'CuDOSXML', 'PTOXML'
]
INPXML_NO_KPOINTLISTS = ['GaAsMultiForceXML']


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_valid_inpxml(create_fleurinp, inpxmlfilepath):
    """
    test if valid inp.xml files are recognized by fleur
    """
    fleurinp_tmp = create_fleurinp(inpxmlfilepath)

    assert fleurinp_tmp.inp_dict != {}

    parser_warnings = fleurinp_tmp.parser_info['parser_warnings'].copy()

    if any('Schema available for version' in warning for warning in parser_warnings):
        for warning in parser_warnings.copy():
            if 'Input file does not validate against the schema' in warning:
                parser_warnings.remove(warning)
            if 'Schema available for version' in warning:
                parser_warnings.remove(warning)

    assert parser_warnings == []
    assert fleurinp_tmp._validate() is None  # if fails, _validate throws an error


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist2)
def test_fleurinp_non_valid_inpxml(create_fleurinp, inpxmlfilepath):
    """
    Test what happens if inp.xml file is not valid
    either an InputValidationError should be thrown by fleurinpData or an
    XMLSyntaxError error if the inp.xml does not correspond to the xml schema.
    """
    from aiida.common.exceptions import InputValidationError
    from lxml import etree

    with pytest.raises((InputValidationError, etree.XMLSyntaxError)):
        create_fleurinp(inpxmlfilepath)


# test kpoints and structure and parameter data extraction


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_kpointsdata_extraction(create_fleurinp, inpxmlfilepath):
    """
    Extract a kpointsData from the fleurinp data, i.e inp.xml and check if
    the resulting node is a valid kpoints data
    """
    from aiida.orm import KpointsData

    fleurinp_tmp = create_fleurinp(inpxmlfilepath)

    if any(folder in inpxmlfilepath for folder in INPXML_LATNAM_DEFINITION):
        with pytest.raises(ValueError, match='Could not extract Bravais matrix out of inp.xml.'):
            fleurinp_tmp.get_kpointsdata_ncf()
    elif any(folder in inpxmlfilepath for folder in INPXML_NO_KPOINTLISTS):
        with pytest.raises(ValueError, match='No Kpoint lists found in the given inp.xml'):
            fleurinp_tmp.get_kpointsdata_ncf()
    else:
        kptsd = fleurinp_tmp.get_kpointsdata_ncf()

        assert isinstance(kptsd, (KpointsData, dict))

        if isinstance(kptsd, dict):
            assert all(isinstance(val, KpointsData) for val in kptsd.values())


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_parameterdata_extraction(create_fleurinp, inpxmlfilepath):
    """
    Extract a ParameterData from the fleurinp data, i.e inp.xml and check if
    the resulting node is a valid ParameterData. ggf if it can be used by inpgen
    """
    from aiida.orm import Dict

    fleurinp_tmp = create_fleurinp(inpxmlfilepath)
    param = fleurinp_tmp.get_parameterdata_ncf()

    assert isinstance(param, Dict)

    # ToDo check if it is also right for inpgen...


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_structuredata_extraction(create_fleurinp, inpxmlfilepath):
    """
    Extract a ParameterData from the fleurinp data, i.e inp.xml and check if
    the resulting node is a valid ParameterData.
    """
    from aiida.orm import StructureData

    fleurinp_tmp = create_fleurinp(inpxmlfilepath)
    if any(folder in inpxmlfilepath for folder in INPXML_LATNAM_DEFINITION):
        with pytest.raises(ValueError, match='Could not extract Bravais matrix out of inp.xml.'):
            fleurinp_tmp.get_structuredata_ncf()
    else:
        struc = fleurinp_tmp.get_structuredata_ncf()

        assert isinstance(struc, StructureData)

    #    # What todo here, may test inpxml are with latnam definded,
    #    # which does not work here.
    #    # But if something else fails also None return. T
    #    # Therefore this test might let two much through


# Input Modification tests
@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_single_value_modification(create_fleurinp, inpxmlfilepath):
    """
    set kmax, itmax, minDistance in inp.xml input file of fleurinpdata to
    10.2, 99, 0.000001, then check if it everything set
    """
    from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

    fleurinp_tmp = create_fleurinp(inpxmlfilepath)
    fleurinpmode = FleurinpModifier(fleurinp_tmp)

    fleurinpmode.set_inpchanges({'itmax': 99, 'minDistance': 0.01, 'Kmax': 10.2})

    fleurinpmode.show(display=False, validate=True)
    out = fleurinpmode.freeze()

    assert isinstance(out, type(fleurinp_tmp))
    # TODO check if set right


def test_fleurinp_convert_inpxml(create_fleurinp):
    """
    Test that the convert_inpxml method works correctly
    """
    inpxmlfilepath = os.path.abspath(os.path.join(inpxmlfilefolder, '../files/inpxml/FePt/31/inp.xml'))

    fleurinp = create_fleurinp(inpxmlfilepath)

    fleurinp_converted = fleurinp.convert_inpxml_ncf('0.34')

    assert fleurinp_converted.files == ['inp.xml']
    assert fleurinp_converted.inp_version == '0.34'

    #Random check that the bzintegration tag has moved
    assert 'bzIntegration' in fleurinp_converted.inp_dict['cell']


folderlist = [
    os.path.abspath(os.path.join(inpxmlfilefolder, '../files/inpxml/Fe_1l_SOCXML/files')),
    os.path.abspath(os.path.join(inpxmlfilefolder, '../files/inpxml/FePt')),
    os.path.abspath(os.path.join(inpxmlfilefolder, '../files/included_xml_files')),
    os.path.abspath(os.path.join(inpxmlfilefolder, '../parsers/fixtures/fleur/default')),
    os.path.abspath(os.path.join(inpxmlfilefolder, '../parsers/fixtures/fleur/relax'))
]

expected_files_list = [{'inp.xml'}, {'inp.xml'}, {'inp.xml', 'kpts.xml', 'sym.xml'}, {'inp.xml'},
                       {'inp.xml', 'relax.xml'}]


@pytest.mark.parametrize('folderpath,expected_files', zip(folderlist, expected_files_list))
def test_get_fleurinp_from_folder_data(folderpath, expected_files):
    from aiida import orm
    from aiida_fleur.data.fleurinp import get_fleurinp_from_folder_data

    folder = orm.FolderData()
    folder.put_object_from_tree(folderpath)

    fleurinp = get_fleurinp_from_folder_data(folder)

    assert set(fleurinp.files) == expected_files


test_names = ['default', 'relax']
fleur_expected_files = [{'inp.xml'}, {'inp.xml', 'relax.xml'}]


@pytest.mark.parametrize('parser_test_name,expected_files', zip(test_names, fleur_expected_files))
def test_get_fleurinp_from_remote_data_fleur(fixture_localhost, generate_calc_job_node, parser_test_name,
                                             expected_files):
    from aiida_fleur.data.fleurinp import get_fleurinp_from_remote_data

    entry_point_calc_job = 'fleur.fleur'

    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, parser_test_name, store=True)

    fleurinp = get_fleurinp_from_remote_data(node.outputs.remote_folder)

    assert set(fleurinp.files) == expected_files


def test_get_fleurinp_from_remote_data_inpgen(fixture_localhost, generate_calc_job_node):
    from aiida_fleur.data.fleurinp import get_fleurinp_from_remote_data

    name = 'default'
    entry_point_calc_job = 'fleur.inpgen'

    node = generate_calc_job_node(entry_point_calc_job, fixture_localhost, name, store=True)

    fleurinp = get_fleurinp_from_remote_data(node.outputs.remote_folder)

    assert set(fleurinp.files) == {'inp.xml'}
