# -*- coding: utf-8 -*-
"""
This module contains the parser for a inpgen run (calculation) and methods for
parsing different files produced by inpgen, which from the input for the FLEUR
code.

Please implement file parsing routines that they can be executed from outside
the parser. Makes testing and portability easier.
"""
#TODO: maybe something from the out files should be saved in the db

import os
from aiida.parsers.parser import Parser
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.parsers import FleurOutputParsingError


__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


class Fleur_inputgenParser(Parser):
    """
    This class is the implementation of the Parser class for the FLEUR inpgen.
    It takes the files recieved from an inpgen calculation and creates AiiDA
    nodes for the Database. From the inp.xml file a FleurinpData object is
    created, also some information from the out file is stored in a
    ParameterData node.
    """

    _setting_key = 'parser_options'

    def __init__(self, calc):
        """
        Initialize the instance of Fleur_inputgenParser
        """
        # check for valid input
        if not isinstance(calc, FleurinputgenCalculation):
            raise FleurOutputParsingError(
                "Input calc must be a FleurInpgenCalculation")

        # these files should be at least present after success of inpgen
        self._default_files = {calc._OUTPUT_FILE_NAME, calc._INPXML_FILE_NAME}
        self._other_files = {calc._SHELLOUT_FILE_NAME}
        #"enpara","inp","sym.out", "fort.93","struct.xsf"}
        #plus other special files? corelevels.xx, ... get from calc object
        super(Fleur_inputgenParser, self).__init__(calc)

    def parse_with_retrieved(self, retrieved):
        """
        Receives as input a dictionary of the retrieved nodes from an inpgen run.
        Does all the logic here.

        :return: a dictionary of AiiDA nodes for storing in the database.
        """

        successful = True
        has_xml_inpfile = False
        #has_error = False

        # select the folder object
        # Check that the retrieved folder is there
        try:
            out_folder = retrieved[self._calc._get_linkname_retrieved()]
        except KeyError:
            self.logger.error("No retrieved folder found")
            return False, ()

        # check what is inside the folder
        list_of_files = out_folder.get_folder_list()
        self.logger.info("file list {}".format(list_of_files))

        if self._calc._INPXML_FILE_NAME not in list_of_files:
            successful = False
            self.logger.error(
                "XML inp not found '{}'".format(self._calc._INPXML_FILE_NAME))
        else:
            has_xml_inpfile = True

        for file1 in self._default_files:
            if file1 not in list_of_files:
                successful = False
                self.logger.warning(
                    "'{}' file not found in retrived folder, it was probable "
                    "not created by inpgen".format(file1))
        # TODO what about other files?

        # TODO parse out file of inpgen
        #output_data = ParameterData(dict=out_dict)
        #link_name = self.get_linkname_outparams()
        #new_nodes_list = [(link_name, output_data)]
        #return successful,new_nodes_list

        new_nodes_list = []
        if self._calc._ERROR_FILE_NAME in list_of_files:
            errorfile = os.path.join(out_folder.get_abs_path('.'),
                                     self._calc._ERROR_FILE_NAME)
            # read
            error_file_lines = ''
            try:
                with open(errorfile, 'r') as efile:
                    error_file_lines = efile.read()# Note: read(),not readlines()
            except IOError:
                self.logger.error(
                    "Failed to open error file: {}.".format(errorfile))
            # if not empty, has_error equals True, parse error.
            if error_file_lines:
                self.logger.error(
                    "The following was written to the error file {} : \n '{}'"
                    "".format(self._calc._ERROR_FILE_NAME, error_file_lines))
                #has_error = True
                successful = False
                return successful, ()

        if has_xml_inpfile:
            # read xmlinp file into an etree
            inpxmlfile = os.path.join(out_folder.get_abs_path('.'),
                                      self._calc._INPXML_FILE_NAME)
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
            fleurinp_data = FleurinpData(files=[inpxmlfile])
            # if kpoints
            # fleurinp_data.set_kpoints
            #, symoutfile, enparafile])
            self.logger.info('FleurinpData initialized')
            #self.logger.info
            link_name_fleurinp = 'fleurinpData'
            # return it to the execmanager
            new_nodes_list.append((link_name_fleurinp, fleurinp_data))

        return successful, new_nodes_list

