# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

from __future__ import absolute_import
import pytest
import os

## Collect the input files
file_path1 = '../files/inpxml/'
file_path2 = '../files/nonvalid_inpxml'


inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
inpxmlfilefolder_valid =  os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))
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
##

### Tests

# Testing of the Fleurinp data type


# Test if valid fleurinp datas can be created for all inp.xml files in a given test folder
        
@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_valid_inpxml(inpxmlfilepath, aiida_env):
    """
    test if inp.xml file is reconnized as valid by fleur
    """
    from aiida.orm import DataFactory
    
    fleurinp = DataFactory('fleur.fleurinp')
    fleurinp_tmp = fleurinp(files=[inpxmlfilepath])
    
    assert fleurinp_tmp._has_schema == True
    assert fleurinp._schema_file_path is not None
    assert fleurinp_tmp.inp_dict != {}
    fleurinp_tmp._validate # will throw validation error if not validating

    
@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist2)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_non_valid_inpxml(inpxmlfilepath):
    """
    test what happens if inp.xml file is not valid
    either an inputvalidationError should be thrown by fleurinpData or an 
    XMLSyntaxError error if the inp.xml does not correspond to the xml schema.
    """
    from aiida.common.exceptions import InputValidationError
    from lxml.etree import XMLSyntaxError
    from aiida.orm import DataFactory
    
    fleurinp = DataFactory('fleur.fleurinp')
    
    with pytest.raises((InputValidationError, XMLSyntaxError)) as error:
        fleurinp_tmp = fleurinp(files=[inpxmlfilepath])

        
# test kpoints and structure and parameter data extraction

@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_kpointsdata_extraction(inpxmlfilepath):
    """
    Extract a kpointsData from the fleurinp data, i.e inp.xml and check if 
    the resulting node is a valid kpoints data
    """
    from aiida.orm import DataFactory
    
    KpointsData = DataFactory('array.kpoints')
    fleurinp = DataFactory('fleur.fleurinp')

    
    fleurinp_tmp = fleurinp(files=[inpxmlfilepath])
    kptsd = fleurinp_tmp.get_kpointsdata_nwf(fleurinp_tmp)
    
    if kptsd is not None:
        assert isinstance(kptsd, KpointsData)
    else:
        pass
        # What todo here, may test inpxml are with latnam definded, which does not work here.
        # or without a kpoint list. Therefore this test might let two much through


@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_parameterdata_extraction(inpxmlfilepath):
    """
    Extract a ParameterData from the fleurinp data, i.e inp.xml and check if 
    the resulting node is a valid ParameterData. ggf if it can be used by inpgen  
    """
    from aiida.orm import DataFactory
    
    ParameterData = DataFactory('parameter')
    fleurinp = DataFactory('fleur.fleurinp')
    
    fleurinp_tmp = fleurinp(files=[inpxmlfilepath])
    param = fleurinp_tmp.get_parameterdata_nwf()
    
    assert isinstance(param, ParameterData)
    
    # ToDo check if it is also right for inpgen...


@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_structuredata_extraction(inpxmlfilepath):
    """
    Extract a ParameterData from the fleurinp data, i.e inp.xml and check if 
    the resulting node is a valid ParameterData.
    """
    from aiida.orm import DataFactory
    
    StructureData = DataFactory('structure')
    fleurinp = DataFactory('fleur.fleurinp')
    
    fleurinp_tmp = fleurinp(files=[inpxmlfilepath])
    struc = fleurinp_tmp.get_structuredata_nwf()

    if struc is not None:
        assert isinstance(struc, StructureData)
    else:
        pass
        # What todo here, may test inpxml are with latnam definded, 
        # which does not work here.
        # But if something else fails also None return. T
        # Therefore this test might let two much through    

       
# Input Modification tests
@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_single_value_modification(inpxmlfilepath):
    """
    set kmax, itmax, minDistance in inp.xml input file of fleurinpdata to 
    10.2, 99, 0.000001, then check if it everything set
    """
    from aiida.orm import DataFactory
    from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

    
    fleurinp = DataFactory('fleur.fleurinp')
    
    fleurinp_tmp = fleurinp(files=[inpxmlfilepath])
    fleurinpmode = FleurinpModifier(fleurinp_tmp)
    # caps matters here!
    fleurinpmode.set_inpchanges({'itmax': 99, 'minDistance' : 0.01, 'Kmax' : 10.2})
    
    
    fleurinpmode.show(display=False, validate=True)
    out = fleurinpmode.freeze()
    
    assert isinstance(out, fleurinp)
    
    # TODO check if set right
    
@pytest.mark.parametrize("inpxmlfilepath", inpxmlfilelist)
@pytest.mark.usefixtures("aiida_env")
def test_fleurinp_first_species_modification(inpxmlfilepath):
    """
    Decrease the rmt of the first species by 10%, check if rmt was set
    """
    pass

