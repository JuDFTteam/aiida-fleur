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
This module contains the parser for a inpgen run (calculation) and methods for
parsing different files produced by inpgen, which form the input for the FLEUR
code.

Please implement file parsing routines that they can be executed from outside
the parser. Makes testing and portability easier. Also without using aiida_classes,
that they might be useful to external tools
"""
#TODO: maybe something from the out files should be saved in the db

from __future__ import absolute_import
import os
from aiida.parsers import Parser
from aiida.engine import ExitCode
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.parsers import FleurOutputParsingError


class Fleur_inputgenParser(Parser):
    """
    This class is the implementation of the Parser class for the FLEUR inpgen.
    It takes the files recieved from an inpgen calculation and creates AiiDA
    nodes for the Database. From the inp.xml file a FleurinpData object is
    created, also some information from the out file is stored in a
    ParameterData node.
    """

    _setting_key = 'parser_options'


    def __init__(self, node):
        """
        Initialize the instance of Fleur_inputgenParser
        """
        super(Fleur_inputgenParser, self).__init__(node)
        
        # these files should be at least present after success of inpgen
        self._default_files = {self.node.get_option('output_file_name'), self.node.get_option('inpxml_file_name')}
        self._other_files = {self.node.get_option('shellout_file_name')}
    
        #"enpara","inp","sym.out", "fort.93","struct.xsf"}
        #plus other special files? corelevels.xx, ... get from calc object

    def parse(self, retrieved_temporary_folder, **kwargs):
        """
        Receives as input a dictionary of the retrieved nodes from an inpgen run.
        Does all the logic here.

        :return: a dictionary of AiiDA nodes for storing in the database.
        """

        has_xml_inpfile = False
        
        # select the folder object
        # Check that the retrieved folder is there
        try:
            output_folder = self.retrieved
        except exceptions.NotExistent:
            self.logger.error("No retrieved folder found")
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # check what is inside the folder
        list_of_files = output_folder.list_object_names()
        self.logger.info("file list {}".format(list_of_files))

        if self.node.get_option('inpxml_file_name') not in list_of_files:
            self.logger.error(
                "XML inp not found '{}'".format(self.node.get_option('inpxml_file_name')))
            return self.exit_codes.ERROR_NO_INPXML
        else:
            has_xml_inpfile = True

        for file1 in self._default_files:
            if file1 not in list_of_files:
                self.logger.error(
                    "'{}' file not found in retrived folder, it was probable "
                    "not created by inpgen".format(file1))
                return self.exit_codes.ERROR_MISSING_RETRIEVED_FILES
        # TODO what about other files?

        # TODO parse out file of inpgen
        #output_data = ParameterData(dict=out_dict)
        #link_name = self.get_linkname_outparams()
        #new_nodes_list = [(link_name, output_data)]
        #return successful,new_nodes_list

        if self.node.get_option('error_file_name') in list_of_files:
            try:
                with output_folder.open(self.node.get_option('error_file_name'), 'r') as efile:
                    error_file_lines = efile.read()# Note: read(),not readlines()
            except IOError:
                self.logger.error(
                    "Failed to open error file: {}.".format(errorfile))
            # if not empty, has_error equals True, parse error.
            if error_file_lines:
                self.logger.error(
                    "The following was written to the error file {} : \n '{}'"
                    "".format(self.node.get_option('error_file_name'), error_file_lines))

        if has_xml_inpfile:
            # read xmlinp file into an etree
            inpxmlfile = self.node.get_option('inpxml_file_name')
           
            #tree = etree.parse(inpxmlfile)
            #root = tree.getroot()

            # convert etree into python dictionary
            #inpxml_params_dict = inpxml_todict(tree.getroot(), inpxmlstructure)
            #self.inpxmlstructure)#tags_several)#.xpath('/fleurInput')[0])

            # convert the dictionary into an AiiDA object
            #Some values, errors and co?
            #inpxml_params = ParameterData(dict=inpxml_params_dict)
            #link_name = self.get_linkname_outparams()
            # this will be accesible with res
            #new_nodes_list.append((link_name, inpxml_params))

            #check if inpgen was invokes with other options
            # if kpoints
            # fleurinp_data.set_kpoints
            #, symoutfile, enparafile])
            
            self.logger.info('FleurinpData initialized')
            self.out('fleurinpData', FleurinpData(files=[inpxmlfile], node=output_folder))

