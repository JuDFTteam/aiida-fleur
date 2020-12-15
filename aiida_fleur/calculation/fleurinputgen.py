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
Input plug-in for the FLEUR input generator 'inpgen'.
The input generator for the Fleur code is a preprocessor
and should be run locally (with the direct scheduler) or inline,
because it does not take many resources.
"""
from __future__ import absolute_import
import six
from six.moves import zip as zip_six

from aiida.engine import CalcJob
from aiida.common.exceptions import InputValidationError
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.constants import elements as PeriodicTableElements
from aiida.orm import StructureData, Dict

from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.tools.StructureData_util import abs_to_rel_f, abs_to_rel
from aiida_fleur.tools.xml_util import convert_to_fortran_bool, convert_to_fortran_string
from aiida_fleur.common.constants import BOHR_A


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

    _settings_keys = [
        'additional_retrieve_list', 'remove_from_retrieve_list', 'cmdline', 'significant_figures_cell',
        'significant_figures_positions'
    ]
    # TODO switch all these to init_internal_params?
    _OUTPUT_SUBFOLDER = './fleur_inp_out/'
    _PREFIX = 'aiida'

    # Additional files that should always be retrieved for the specific plugin
    _internal_retrieve_list = []
    _automatic_namelists = {}

    # Specify here what namelist and parameters the inpgen takes
    _possible_namelists = [
        'title', 'input', 'lattice', 'gen', 'shift', 'factor', 'qss', 'soc', 'atom', 'comp', 'exco', 'film', 'kpt',
        'end'
    ]
    # this order is important!
    _possible_params = {
        'input': ['film', 'cartesian', 'cal_symm', 'checkinp', 'symor', 'oldfleur'],
        'lattice': ['latsys', 'a0', 'a', 'b', 'c', 'alpha', 'beta', 'gamma'],
        'atom': ['id', 'z', 'rmt', 'dx', 'jri', 'lmax', 'lnonsph', 'ncst', 'econfig', 'bmu', 'lo', 'element', 'name'],
        'comp': ['jspins', 'frcor', 'ctail', 'kcrel', 'gmax', 'gmaxxc', 'kmax'],
        'exco': ['xctyp', 'relxc'],
        'film': ['dvac', 'dtild'],
        'soc': ['theta', 'phi'],
        'qss': ['x', 'y', 'z'],
        'kpt': ['nkpt', 'kpts', 'div1', 'div2', 'div3', 'tkb', 'tria'],
        'title': {}
    }

    # Keywords that cannot be set
    # TODO: To specify what combinations are not allowed together,
    # or not at all (lattice ?, shift, scale)
    _blocked_keywords = []

    # TODO different kpt mods? (use kpointNode)? FleurinpdData can do it.
    _use_kpoints = False

    # If two lattices are given, via the input &lattice
    # and the aiida structure prefare the aiida structure?
    # currently is not allow the use of &lattice
    _use_aiida_structure = True

    # Default title
    _inp_title = 'A Fleur input generator calculation with aiida'

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.input('metadata.options.input_filename', valid_type=six.string_types, default=cls._INPUT_FILE)
        spec.input('metadata.options.output_filename', valid_type=six.string_types, default=cls._INPXML_FILE_NAME)
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
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default='fleur.fleurinpgenparser')

        # declaration of outputs of the calclation
        spec.output('fleurinpData', valid_type=FleurinpData, required=True)

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
                       message=('During parsing: FleurinpData could not be initialized, see log. '
                                'Maybe no Schemafile was found or the Fleurinput is not valid.'))
        spec.exit_code(309, 'ERROR_FLEURINPDATA_NOT_VALID', message='During parsing: FleurinpData failed validation.')

    def prepare_for_submission(self, folder):
        """
        This is the routine to be called when you want to create
        the input files for the inpgen with the plug-in.

        :param folder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """

        # Get the connection between coordination number and element symbol
        _atomic_numbers = {data['symbol']: num for num, data in six.iteritems(PeriodicTableElements)}

        possible_namelists = self._possible_namelists
        possible_params = self._possible_params
        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []
        bulk = True
        film = False

        # convert these 'booleans' to the inpgen format.
        replacer_values_bool = [True, False, 'True', 'False', 't', 'T', 'F', 'f']
        # some keywords require a string " around them in the input file.
        string_replace = ['econfig', 'lo', 'element', 'name', 'xctyp']

        # of some keys only the values are written to the file, specify them here.
        val_only_namelist = ['soc', 'qss']

        # Scaling comes from the Structure
        # but we have to convert from Angstrom to a.u (bohr radii)
        scaling_factors = [1.0, 1.0, 1.0]
        scaling_lat = 1.  # /bohr_to_ang = 0.52917720859
        scaling_pos = 1. / BOHR_A  # Angstrom to atomic
        own_lattice = False  # not self._use_aiida_structure

        ##########################################
        ############# INPUT CHECK ################
        ##########################################

        # first check existence of structure and if 1D, 2D, 3D
        structure = self.inputs.structure

        pbc = structure.pbc
        if False in pbc:
            bulk = False
            film = True

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

        # we write always out rel coordinates, because thats the way FLEUR uses
        # them best. we have to convert them from abs, because thats how they
        # are stored in a Structure node. cartesian=F is default
        if 'input' in parameters_dict:
            parameters_dict['input']['cartesian'] = False
            if film:
                parameters_dict['input']['film'] = True
        else:
            if bulk:
                parameters_dict['input'] = {'cartesian': False}
            elif film:
                parameters_dict['input'] = {'cartesian': False, 'film': True}

        namelists_toprint = possible_namelists

        input_params = parameters_dict

        if 'title' in list(input_params.keys()):
            self._inp_title = input_params.pop('title')
        # TODO validate type of values of the input parameter keys ?

        # check input_parameters
        for namelist, paramdic in six.iteritems(input_params):
            if 'atom' in namelist:  # this namelist can be specified more often
                # special atom namelist needs to be set for writing,
                #  but insert it in the right spot!
                index = namelists_toprint.index('atom') + 1
                namelists_toprint.insert(index, namelist)
                namelist = 'atom'
            if namelist not in possible_namelists:
                raise InputValidationError("The namelist '{0}' is not supported by the fleur"
                                           " inputgenerator. Check on the fleur website or add '{0}'"
                                           'to _possible_namelists.'.format(namelist))
            for para in paramdic.keys():
                if para not in possible_params[namelist]:
                    raise InputValidationError("The property '{}' is not supported by the "
                                               "namelist '{}'. "
                                               'Check the fleur website, or if it really is,'
                                               ' update _possible_params. '.format(para, namelist))
                if para in string_replace:
                    # TODO check if its in the parameter dict
                    paramdic[para] = convert_to_fortran_string(paramdic[para])
                # things that are in string replace can never be a bool
                # Otherwise input where someone given the title 'F' would fail...
                elif paramdic[para] in replacer_values_bool:
                    # because 1/1.0 == True, and 0/0.0 == False
                    # maybe change in convert_to_fortran that no error occurs
                    if isinstance(paramdic[para], (int, float)):
                        if isinstance(paramdic[para], bool):
                            paramdic[para] = convert_to_fortran_bool(paramdic[para])
                    else:
                        paramdic[para] = convert_to_fortran_bool(paramdic[para])

            # in fleur it is possible to give a lattice namelist
            if 'lattice' in list(input_params.keys()):
                own_lattice = True
                if structure in self.inputs:  # two structures given?
                    # which one should be prepared? TODO: log warning or even error
                    if self._use_aiida_structure:
                        input_params.pop('lattice', {})
                        own_lattice = False
        #TODO check if input parameter dict is consistent to given structure.
        # if not issue warnings.
        # TODO allow only usual kpt meshes and use therefore Aiida kpointData
        # if self._use_kpoints:
        #     try:
        #         kpoints = inputdict.pop(self.get_linkname('kpoints'))
        #     except KeyError:
        #         raise InputValidationError("No kpoints specified for this"
        #                                    " calculation")
        #     if not isinstance(kpoints, KpointsData):
        #         raise InputValidationError("kpoints is not of type KpointsData")

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

        ##############################
        # END OF INITIAL INPUT CHECK #
        ##############################

        #######################################################
        ######### PREPARE PARAMETERS FOR INPUT FILE ###########
        #######################################################

        #### STRUCTURE_PARAMETERS ####

        scaling_factor_card = ''
        cell_parameters_card = ''
        # We allow to set the significant figures format, because sometimes
        # inpgen has numerical problems which are not there with less precise formatting
        sf_c = str(settings_dict.get('significant_figures_cell', 9))
        sf_p = str(settings_dict.get('significant_figure_positions', 10))
        if not own_lattice:
            cell = structure.cell
            for vector in cell:
                scaled = [a * scaling_pos for a in vector]  # scaling_pos=1./bohr_to_ang
                reg_string = '{0:18.' + sf_c + 'f} {1:18.' + sf_c + 'f} {2:18.' + sf_c + 'f}\n'
                cell_parameters_card += (reg_string.format(scaled[0], scaled[1], scaled[2]))
            reg_string = '{0:18.' + sf_c + 'f} {1:18.' + sf_c + 'f} {2:18.' + sf_c + 'f}\n'
            scaling_factor_card += (reg_string.format(scaling_factors[0], scaling_factors[1], scaling_factors[2]))

        #### ATOMIC_POSITIONS ####

        # TODO: be careful with units
        atomic_positions_card_list = ['']
        atomic_positions_card_listtmp = ['']

        if not own_lattice:
            natoms = len(structure.sites)

            # for FLEUR true, general not, because you could put several
            # atoms on a site
            # TODO: test that only one atom at site?

            # TODO this feature might change in Fleur, do different. that in inpgen kind gets a name, which will also be the name in fleur inp.xml.
            # now user has to make kind_name = atom id.
            for site in structure.sites:
                kind_name = site.kind_name
                kind = structure.get_kind(kind_name)
                if kind.has_vacancies:
                    # then we do not at atoms with weights smaller one
                    if kind.weights[0] < 1.0:
                        natoms = natoms - 1
                        # Log message?
                        continue
                # TODO: list I assume atoms therefore I just get the first one...
                site_symbol = kind.symbols[0]
                atomic_number = _atomic_numbers[site_symbol]
                atomic_number_name = atomic_number

                # per default we use relative coordinates in Fleur
                # we have to scale back to atomic units from angstrom
                pos = site.position
                if bulk:
                    vector_rel = abs_to_rel(pos, cell)
                elif film:
                    vector_rel = abs_to_rel_f(pos, cell, structure.pbc)
                    vector_rel[2] = vector_rel[2] * scaling_pos

                if site_symbol != kind_name:  # This is an important fact, if user renames it becomes a new atomtype or species!
                    try:
                        # Kind names can be more then numbers now, this might need to be reworked
                        head = kind_name.rstrip('0123456789')
                        kind_namet = int(kind_name[len(head):])
                        #if int(kind_name[len(head)]) > 4:
                        #    raise InputValidationError('New specie name/label should start with a digit smaller than 4')
                    except ValueError:
                        self.report(
                            'Warning: Kind name {} will be ignored by the FleurinputgenCalculation and not set a charge number.'
                            .format(kind_name))
                    else:
                        atomic_number_name = '{}.{}'.format(atomic_number, kind_namet)
                    # append a label to the detached atom
                    reg_string = '    {0:7} {1:18.' + sf_p + 'f} {2:18.' + sf_p + 'f} {3:18.' + sf_p + 'f} {4}\n'
                    atomic_positions_card_listtmp.append(
                        reg_string.format(atomic_number_name, vector_rel[0], vector_rel[1], vector_rel[2], kind_namet))
                else:
                    reg_string = '    {0:7} {1:18.' + sf_p + 'f} {2:18.' + sf_p + 'f} {3:18.' + sf_p + 'f}\n'
                    atomic_positions_card_listtmp.append(
                        reg_string.format(atomic_number_name, vector_rel[0], vector_rel[1], vector_rel[2]))
            # TODO check format
            # we write it later, since we do not know what natoms is before the loop...
            atomic_positions_card_list.append('    {0:3}\n'.format(natoms))
            for card in atomic_positions_card_listtmp:
                atomic_positions_card_list.append(card)
        else:
            # TODO with own lattice atomic positions have to come from somewhere
            # else.... User input?
            raise InputValidationError('fleur lattice needs also the atom '
                                       ' position as input,'
                                       ' not implemented yet, sorry!')
        atomic_positions_card = ''.join(atomic_positions_card_list)
        del atomic_positions_card_list  # Free memory

        #### Kpts ####

        # TODO: kpts
        # kpoints_card = ""#.join(kpoints_card_list)
        #del kpoints_card_list

        #######################################
        #### WRITE ALL CARDS IN INPUT FILE ####

        input_filename = folder.get_abs_path(self._INPUT_FILE_NAME)

        with open(input_filename, 'w') as infile:

            # first write title
            infile.write('{0}\n'.format(self._inp_title))

            # then write &input namelist
            infile.write('&{0}'.format('input'))

            # namelist content; set to {} if not present, so that we leave an
            # empty namelist
            namelist = input_params.pop('input', {})
            for k, val in sorted(six.iteritems(namelist)):
                infile.write(get_input_data_text(k, val, False, mapping=None))
            infile.write('/\n')

            # Write lattice information now
            infile.write(cell_parameters_card)
            infile.write('{0:18.10f}\n'.format(scaling_lat))
            infile.write(scaling_factor_card)
            infile.write('\n')

            # Write Atomic positons
            infile.write(atomic_positions_card)

            # Write namelists after atomic positions
            for namels_name in namelists_toprint:
                namelist = input_params.pop(namels_name, {})
                if namelist:
                    if 'atom' in namels_name:
                        namels_name = 'atom'
                    infile.write('&{0}\n'.format(namels_name))
                    if namels_name in val_only_namelist:
                        make_reversed = False
                        if namels_name == 'soc':
                            make_reversed = True
                        for k, val in sorted(six.iteritems(namelist), reverse=make_reversed):
                            infile.write(get_input_data_text(k, val, True, mapping=None))
                    else:
                        for k, val in sorted(six.iteritems(namelist)):
                            infile.write(get_input_data_text(k, val, False, mapping=None))
                    infile.write('/\n')
            # infile.write(kpoints_card)

        if input_params:
            raise InputValidationError('input_params leftover: The following namelists are specified'
                                       ' in input_params, but are '
                                       'not valid namelists for the current type of calculation: '
                                       '{}'.format(','.join(list(input_params.keys()))))

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
        #cmdline_params = ['-explicit', '-inc', '+all', '-f', '{}'.format(self._INPUT_FILE_NAME)]
        cmdline_params = ['-explicit']

        # user specific commandline_options
        for command in settings_dict.get('cmdline', []):
            cmdline_params.append(command)
        codeinfo.cmdline_params = (list(cmdline_params))

        codeinfo.code_uuid = code.uuid
        codeinfo.stdin_name = self._INPUT_FILE_NAME
        codeinfo.stdout_name = self._SHELLOUT_FILE_NAME  # shell output will be piped in file
        codeinfo.stderr_name = self._ERROR_FILE_NAME  # std error too

        calcinfo.codes_info = [codeinfo]

        return calcinfo


def conv_to_fortran(val, quote_strings=True):
    """
    :param val: the value to be read and converted to a Fortran-friendly string.
    """
    # Note that bool should come before integer, because a boolean matches also
    # isinstance(...,int)
    import numpy
    import numbers

    if isinstance(val, (bool, numpy.bool_)):
        if val:
            val_str = '.true.'
        else:
            val_str = '.false.'
    elif isinstance(val, numbers.Integral):
        val_str = '{:d}'.format(val)
    elif isinstance(val, numbers.Real):
        val_str = ('{:18.10e}'.format(val)).replace('e', 'd')
    elif isinstance(val, six.string_types):
        if quote_strings:
            val_str = "'{!s}'".format(val)
        else:
            val_str = '{!s}'.format(val)
    else:
        raise ValueError("Invalid value '{}' of type '{}' passed, accepts only booleans, ints, "
                         'floats and strings'.format(val, type(val)))

    return val_str


# TODO rewrite for fleur/ delete unnecessary parts
def get_input_data_text(key, val, value_only, mapping=None):
    """
    Given a key and a value, return a string (possibly multiline for arrays)
    with the text to be added to the input file.

    :param key: the flag name
    :param val: the flag value. If it is an array, a line for each element
            is produced, with variable indexing starting from 1.
            Each value is formatted using the conv_to_fortran function.
    :param mapping: Optional parameter, must be provided if val is a dictionary.
            It maps each key of the 'val' dictionary to the corresponding
            list index. For instance, if ``key='magn'``,
            ``val = {'Fe': 0.1, 'O': 0.2}`` and ``mapping = {'Fe': 2, 'O': 1}``,
            this function will return the two lines ``magn(1) = 0.2`` and
            ``magn(2) = 0.1``. This parameter is ignored if 'val'
            is not a dictionary.
    """
    #from aiida.common.utils import conv_to_fortran
    # I don't try to do iterator=iter(val) and catch TypeError because
    # it would also match strings
    # I check first the dictionary, because it would also matc
    # hasattr(__iter__)
    if isinstance(val, dict):
        if mapping is None:
            raise ValueError("If 'val' is a dictionary, you must provide also " "the 'mapping' parameter")

        # At difference with the case of a list, at the beginning
        # list_of_strings
        # is a list of 2-tuples where the first element is the idx, and the
        # second is the actual line. This is used at the end to
        # resort everything.
        list_of_strings = []
        for elemk, itemval in six.iteritems(val):
            try:
                idx = mapping[elemk]
            except KeyError as exc:
                raise ValueError("Unable to find the key '{}' in the mapping " 'dictionary'.format(elemk)) from exc

            list_of_strings.append((idx, '  {0}({2})={1} '.format(key, conv_to_fortran(itemval), idx)))
            # changed {0}({2}) = {1}\n".format

        # I first have to resort, then to remove the index from the first
        # column, finally to join the strings
        list_of_strings = list(zip_six(*sorted(list_of_strings)))[1]
        return ''.join(list_of_strings)
    elif not isinstance(val, six.string_types) and hasattr(val, '__iter__'):
        if value_only:
            list_of_strings = [
                '  ({1}){0} '.format(conv_to_fortran(itemval), idx + 1) for idx, itemval in enumerate(val)
            ]
        else:
            # a list/array/tuple of values
            list_of_strings = [
                '  {0}({2})={1} '.format(key, conv_to_fortran(itemval), idx + 1) for idx, itemval in enumerate(val)
            ]
        return ''.join(list_of_strings)
    else:
        # single value
        # return "  {0}={1} ".format(key, conv_to_fortran(val))
        if value_only:
            return ' {0} '.format(val)
        else:
            return '  {0}={1} '.format(key, val)


def _lowercase_dict(dic, dict_name):
    """
    Converts every entry in a dictionary to lowercase

    :param dic: parameters dictionary
    :param dict_name: dictionary name
    """
    from collections import Counter

    if isinstance(dic, dict):
        new_dict = dict((str(k).lower(), val) for k, val in six.iteritems(dic))
        if len(new_dict) != len(dic):
            num_items = Counter(str(k).lower() for k in dic.keys())
            double_keys = ','.join([k for k, val in num_items if val > 1])
            raise InputValidationError("Inside the dictionary '{}' there are the following keys that "
                                       'are repeated more than once when compared case-insensitively:'
                                       '{}.This is not allowed.'.format(dict_name, double_keys))
        return new_dict
    else:
        raise TypeError('_lowercase_dict accepts only dictionaries as argument')
