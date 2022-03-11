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
This module contains the parser for a inpgen calculation and methods for
parsing different files produced by inpgen.
"""

from aiida.parsers import Parser
from aiida.common.exceptions import NotExistent, InputValidationError, ValidationError

from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation

import pprint


class Fleur_inputgenParser(Parser):
    """
    This class is the implementation of the Parser class for the FLEUR inpgen.
    It takes the files received from an inpgen calculation and creates AiiDA
    nodes for the Database. From the inp.xml file a FleurinpData object is
    created, also some information from the out file is stored in a
    ParameterData node.
    """

    _setting_key = 'parser_options'

    def __init__(self, node):
        """
        Initialize the instance of Fleur_inputgenParser
        """
        super().__init__(node)

        # these files should be at least present after success of inpgen
        self._default_files = {FleurinputgenCalculation._OUTPUT_FILE_NAME, FleurinputgenCalculation._INPXML_FILE_NAME}
        self._other_files = {FleurinputgenCalculation._SHELLOUT_FILE_NAME}

    def parse(self, **kwargs):
        """
        Takes inp.xml generated by inpgen calculation and created an FleurinpData node.

        :return: a dictionary of AiiDA nodes to be stored in the database.
        """

        try:
            output_folder = self.retrieved
        except NotExistent:
            self.logger.error('No retrieved folder found')
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # check what is inside the folder
        list_of_files = output_folder.list_object_names()
        self.logger.info(f'file list {list_of_files}')

        errorfile = FleurinputgenCalculation._ERROR_FILE_NAME
        if errorfile in list_of_files:
            try:
                with output_folder.open(errorfile, 'r') as error_file:
                    error_file_lines = error_file.read()
            except OSError:
                self.logger.error(f'Failed to open error file: {errorfile}.')
                return self.exit_codes.ERROR_OPENING_OUTPUTS
            # if not empty, has_error equals True, prior fleur 32
            if error_file_lines:
                if isinstance(error_file_lines, bytes):
                    error_file_lines = error_file_lines.replace(b'\x00', b' ')
                else:
                    error_file_lines = error_file_lines.replace('\x00', ' ')
                if 'Run finished successfully' not in error_file_lines:
                    self.logger.warning(
                        f'The following was written into std error and piped to {errorfile}: \n {error_file_lines}')
                    self.logger.error('Inpgen calculation did not finish successfully.')

        inpxml_file = FleurinputgenCalculation._INPXML_FILE_NAME
        if inpxml_file not in list_of_files:
            self.logger.error(f"XML inp not found '{inpxml_file}'")
            return self.exit_codes.ERROR_NO_INPXML

        for file1 in self._default_files:
            if file1 not in list_of_files:
                self.logger.error(f"Expected file '{file1}' not found in retrieved folder, it was probably "
                                  'not created by inpgen')
                return self.exit_codes.ERROR_MISSING_RETRIEVED_FILES

        try:
            fleurinp = FleurinpData(files=[])
            fleurinp.set_file(inpxml_file, node=output_folder)
        except InputValidationError as ex:
            self.logger.error(f'FleurinpData initialization failed: {str(ex)}')
            if fleurinp.parser_info == {}:
                self.logger.error('Parser output: No Output produced')
            else:
                self.logger.error(f'Parser output: {pprint.pformat(fleurinp.parser_info)}')
            return self.exit_codes.ERROR_FLEURINPDATA_INPUT_NOT_VALID
        except ValidationError as ex:
            self.logger.error(f'FleurinpData validation failed: {str(ex)}')
            return self.exit_codes.ERROR_FLEURINPDATA_NOT_VALID

        self.logger.info('FleurinpData initialized')
        self.out('fleurinpData', fleurinp)
