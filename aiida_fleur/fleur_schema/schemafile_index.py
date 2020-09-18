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
"""
This file is just were to hardcode some schema file paths
"""

from __future__ import absolute_import
import os

# any additional schema file add here, plugin will find them
SCHEMA_FILE_PATHS = [
    './input/0.27/FleurInputSchema.xsd', './input/0.28/FleurInputSchema.xsd', './input/0.29/FleurInputSchema.xsd',
    './input/0.30/FleurInputSchema.xsd', './input/0.31/FleurInputSchema.xsd', './input/0.32/FleurInputSchema.xsd',
    './input/0.33/FleurInputSchema.xsd', '.'
]

PACKAGE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


def get_schema_paths():
    """
    returns all know hardcodes schemas as a list of abs paths
    """
    schema_paths = []
    for schema in SCHEMA_FILE_PATHS:
        path = os.path.abspath(os.path.join(PACKAGE_DIRECTORY, schema))
        if os.path.isfile(path):
            schema_paths.append(path)
    return schema_paths


def get_internal_search_paths():
    """
    returns all abs paths to dirs where schema files might be
    """
    #schema_paths = []
    #for schema in schema_file_paths:
    #    path = os.path.abspath(os.path.join(package_directory, schema))
    #    if os.path.isdir(path):
    #       schema_paths.append(path)
    schema_paths = [PACKAGE_DIRECTORY]
    return schema_paths
