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
'''
Contains extensive tests for the FleurinpData structure of AiiDA-Fleur
'''
from __future__ import absolute_import
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


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_valid_inpxml(create_fleurinp, inpxmlfilepath):
    """
    test if valid inp.xml files are recognized by fleur
    """
    fleurinp_tmp = create_fleurinp(inpxmlfilepath)

    assert fleurinp_tmp._has_schema
    assert fleurinp_tmp._schema_file_path is not None
    assert fleurinp_tmp.inp_dict != {}
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
    kptsd = fleurinp_tmp.get_kpointsdata_ncf()

    if kptsd is not None:
        assert isinstance(kptsd, KpointsData)
    else:
        pass
        # What todo here, may test inpxml are with latnam definded, which does not work here.
        # or without a kpoint list. Therefore this test might let two much through


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
    struc = fleurinp_tmp.get_structuredata_ncf()

    if struc is not None:
        assert isinstance(struc, StructureData)
    else:
        pass
        # What todo here, may test inpxml are with latnam definded,
        # which does not work here.
        # But if something else fails also None return. T
        # Therefore this test might let two much through


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


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_fleurinp_first_species_modification(create_fleurinp, inpxmlfilepath):
    """
    Decrease the rmt of the first species by 10%, check if rmt was set
    """
    return
