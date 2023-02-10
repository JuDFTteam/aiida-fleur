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
Input plug-in for the FLEUR input generator 'inpgen'.
The input generator for the Fleur code is a preprocessor
and should be run locally (with the direct scheduler) or inline,
because it does not take many resources.
"""
from aiida.engine import CalcJob
from aiida.common.exceptions import InputValidationError
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.orm import StructureData, Dict

from aiida_fleur.data.fleurinp import FleurinpData
import io


class FleurinputgenCalculation(CalcJob):
    """
    JobCalculationClass for the inpgen, which is a preprocessor for a FLEUR calculation.
    For more information about produced files and the FLEUR-code family, go to http://www.flapw.de/.
    """

    __version__ = '1.2.2'

    # Default input and output files
    _INPUT_FILE = 'aiida.in'  # will be shown with inputcat
    _OUTPUT_FILE = 'out'  # 'shell.out' #will be shown with outputcat

    # created file names, some needed for Fleur calc
    _INPXML_FILE_NAME = 'inp.xml'
    _INPUT_FILE_NAME = 'aiida.in'
    _SHELLOUT_FILE_NAME = 'shell.out'
    _OUTPUT_FILE_NAME = 'out'
    _ERROR_FILE_NAME = 'out.error'
    _STRUCT_FILE_NAME = 'struct.xsf'
    _JUDFT_WARN_ONLY_INFO_FILE_NAME = 'JUDFT_WARN_ONLY'

    _settings_keys = [
        'additional_retrieve_list', 'remove_from_retrieve_list', 'cmdline', 'significant_figures_cell',
        'significant_figures_positions', 'profile'
    ]
    # TODO switch all these to init_internal_params?
    _OUTPUT_SUBFOLDER = './fleur_inp_out/'
    _PREFIX = 'aiida'

    # Additional files that should always be retrieved for the specific plugin
    _internal_retrieve_list = []
    _automatic_namelists = {}

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.input('metadata.options.input_filename', valid_type=str, default=cls._INPUT_FILE)
        spec.input('metadata.options.output_filename', valid_type=str, default=cls._INPXML_FILE_NAME)
        spec.input('structure', valid_type=StructureData, help='Choose the input structure to use')
        spec.input('parameters',
                   valid_type=Dict,
                   required=False,
                   help='Use a node that specifies the input parameters '
                   'for the namelists')
        spec.input('settings',
                   valid_type=Dict,
                   required=False,
                   help='This parameter data node is used to specify for some '
                   'advanced features how the plugin behaves. You can add files'
                   'the retrieve list, or add command line switches, '
                   'for all available features here check the documentation.')

        # parser
        spec.input('metadata.options.parser_name', valid_type=str, default='fleur.fleurinpgenparser')

        # declaration of outputs of the calclation
        spec.output('fleurinp', valid_type=FleurinpData, required=True)

        # exit codes
        # spec.exit_code(251, 'ERROR_WRONG_INPUT_PARAMS',
        #                message='Input parameters for inpgen contain unknown keys.')
        # spec.exit_code(253, 'ERROR_ATOM_POSITION_NEEDED',
        #                message='Fleur lattice needs atom positions as input.')
        # spec.exit_code(254, 'ERROR_INPUT_PARAMS_LEFTOVER',
        #                message='Excessive input parameters were specified.')
        spec.exit_code(300, 'ERROR_NO_RETRIEVED_FOLDER', message='No retrieved folder found.')
        spec.exit_code(301, 'ERROR_OPENING_OUTPUTS', message='One of the output files can not be opened.')
        spec.exit_code(306, 'ERROR_NO_INPXML', message='XML input file was not found.')
        spec.exit_code(307, 'ERROR_MISSING_RETRIEVED_FILES', message='Some required files were not retrieved.')
        spec.exit_code(308,
                       'ERROR_FLEURINPDATA_INPUT_NOT_VALID',
                       message=('During parsing: FleurinpData could not be initialized, see log. '))
        spec.exit_code(309, 'ERROR_FLEURINPDATA_NOT_VALID', message='During parsing: FleurinpData failed validation.')
        spec.exit_code(310,
                       'ERROR_UNKNOWN_PROFILE',
                       message='The profile {profile} is not known to the used inpgen code')

    def prepare_for_submission(self, folder):
        """
        This is the routine to be called when you want to create
        the input files for the inpgen with the plug-in.

        :param folder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []

        # first check existence of structure and if 1D, 2D, 3D
        structure = self.inputs.structure

        # check existence of parameters (optional)
        if 'parameters' in self.inputs:
            parameters = self.inputs.parameters
        else:
            parameters = None

        if parameters is None:
            # use default
            parameters_dict = {}
        else:
            parameters_dict = _lowercase_dict(parameters.get_dict(), dict_name='parameters')

        code = self.inputs.code

        # check existence of settings (optional)
        if 'settings' in self.inputs:
            settings = self.inputs.settings
        else:
            settings = None

        if settings is None:
            settings_dict = {}
        else:
            settings_dict = settings.get_dict()

        # check for for allowed keys, ignore unknown keys but warn.
        for key in settings_dict.keys():
            if key not in self._settings_keys:
                # TODO warning
                self.logger.info('settings dict key %s for Fleur calculation'
                                 'not recognized, only %s are allowed.', key, str(self._settings_keys))

        #Check that if a inpgen profile is given no additional parameters are provided
        #since this will overwrite the effects of the inpgen profile (For now we just issue a warning)
        if 'profile' in settings_dict:
            lapw_parameters_given = any('atom' in key for key in parameters_dict)
            comp = parameters_dict.get('comp', {})
            lapw_parameters_given = lapw_parameters_given or \
                                    'kmax' in comp or \
                                    'gmax' in comp or \
                                    'gmaxxc' in comp
            if lapw_parameters_given:
                self.logger.warning('Inpgen profile specified but atom/LAPW basis specific '
                                    'parameters are provided. These will conflict/override each other')

        #######################################
        #### WRITE ALL CARDS IN INPUT FILE ####

        with folder.open(self._INPUT_FILE_NAME, 'w') as input_file:
            write_inpgen_file_aiida_struct(structure, input_file, input_params=parameters_dict, settings=settings_dict)

        # create a JUDFT_WARN_ONLY file in the calculation folder
        with io.StringIO('/n') as handle:
            warn_only_filename = self._JUDFT_WARN_ONLY_INFO_FILE_NAME
            folder.create_file_from_filelike(handle, filename=warn_only_filename, mode='w')

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid

        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve per default only out file and inp.xml file?
        retrieve_list = []
        retrieve_list.append(self._INPXML_FILE_NAME)
        retrieve_list.append(self._OUTPUT_FILE_NAME)
        retrieve_list.append(self._SHELLOUT_FILE_NAME)
        retrieve_list.append(self._ERROR_FILE_NAME)
        retrieve_list.append(self._STRUCT_FILE_NAME)
        retrieve_list.append(self._INPUT_FILE_NAME)

        # user specific retrieve
        add_retrieve = settings_dict.get('additional_retrieve_list', [])
        for file1 in add_retrieve:
            retrieve_list.append(file1)

        remove_retrieve = settings_dict.get('remove_from_retrieve_list', [])
        for file1 in remove_retrieve:
            if file1 in retrieve_list:
                retrieve_list.remove(file1)

        calcinfo.retrieve_list = []
        for file1 in retrieve_list:
            calcinfo.retrieve_list.append(file1)

        codeinfo = CodeInfo()
        # , "-electronConfig"] # TODO? let the user decide -electronconfig?

        # We support different inpgen and fleur version via reading the version from the code node extras
        code_extras = code.extras
        code_version = code_extras.get('version', 32)
        if int(code_version) < 32:
            # run old inpgen
            cmdline_params = ['-explicit']
            codeinfo.stdin_name = self._INPUT_FILE_NAME
        else:
            cmdline_params = ['-explicit', '-inc', '+all', '-f', f'{self._INPUT_FILE_NAME}']

        if 'profile' in settings_dict:
            cmdline_params.extend(['-profile', settings_dict['profile']])

        # user specific commandline_options
        for command in settings_dict.get('cmdline', []):
            cmdline_params.append(command)
        codeinfo.cmdline_params = (list(cmdline_params))

        codeinfo.code_uuid = code.uuid
        codeinfo.stdout_name = self._SHELLOUT_FILE_NAME  # shell output will be piped in file
        codeinfo.stderr_name = self._ERROR_FILE_NAME  # std error too
        calcinfo.codes_info = [codeinfo]

        return calcinfo


def _lowercase_dict(dic, dict_name):
    """
    Converts every entry in a dictionary to lowercase

    :param dic: parameters dictionary
    :param dict_name: dictionary name
    """
    from collections import Counter

    if not isinstance(dic, dict):
        raise TypeError('_lowercase_dict accepts only dictionaries as argument')

    new_dict = {str(k).lower(): val for k, val in dic.items()}
    if len(new_dict) != len(dic):
        num_items = Counter(str(k).lower() for k in dic.keys())
        double_keys = ','.join([k for k, val in num_items if val > 1])
        raise InputValidationError("Inside the dictionary '{}' there are the following keys that "
                                   'are repeated more than once when compared case-insensitively:'
                                   '{}.This is not allowed.'.format(dict_name, double_keys))
    return new_dict


def write_inpgen_file_aiida_struct(structure, file, input_params=None, settings=None):
    """Wraps around masci_tools write inpgen_file, unpacks aiida structure"""
    from masci_tools.io.fleur_inpgen import write_inpgen_file

    atoms_dict_list = []
    kind_list = []

    for kind in structure.kinds:
        kind_list.append(kind.get_raw())

    for site in structure.sites:
        atoms_dict_list.append(site.get_raw())

    if settings is None:
        settings = {}

    write_settings = {}
    if 'significant_figures_cell' in settings:
        write_settings['significant_figures_cell'] = settings.get('significant_figures_cell')
    if 'significant_figures_positions' in settings:
        write_settings['significant_figures_positions'] = settings.get('significant_figures_positions')

    report = write_inpgen_file(structure.cell,
                               atoms_dict_list,
                               kind_list,
                               file=file,
                               pbc=structure.pbc,
                               input_params=input_params,
                               **write_settings)

    return report
