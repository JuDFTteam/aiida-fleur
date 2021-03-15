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
Module to test all CLI types of the package.
'''
import pytest
import os
import click
from aiida.orm import StructureData

file_path1 = '../files/cif/AlB.cif'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
CIF_FILE = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))


class TestStructureNodeOrFileParamType:
    """Test the ``StructureNodeOrFileParamType``"""

    def test_not_existent_structure(self, struct_file_type):
        """Test failure if identifier given but NotExistent"""
        with pytest.raises(click.BadParameter):
            struct_file_type.convert('7000', None, None)

    def test_path_give(self, struct_file_type):
        """Test if it can take a cif file"""
        result = struct_file_type.convert(CIF_FILE, None, None)
        assert isinstance(result, StructureData)

    def test_parse_duplicate(self, struct_file_type):
        """Test if duplicates are not stored again"""
        result = struct_file_type.convert(CIF_FILE, None, None)
        structure = result.store()

        result = struct_file_type.convert(CIF_FILE, None, None)
        assert result.uuid == structure.uuid
