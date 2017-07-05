# -*- coding: utf-8 -*-
"""
This file is just were to hardcode some schema file paths
"""
__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


import os

# any additional schema file add here, plugin will find them
schema_file_paths = ['./input/0.27/FleurInputSchema.xsd', './input/0.27/FleurInputSchema.xsd', '.']


package_directory = os.path.dirname(os.path.abspath(__file__))


def get_schema_paths():
    """
    returns all know hardcodes schemas as a list of abs paths
    """
    schema_paths = []
    for schema in schema_file_paths:
        path = os.path.abspath(os.path.join(package_directory, schema))
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
    schema_paths = [package_directory]
    return schema_paths