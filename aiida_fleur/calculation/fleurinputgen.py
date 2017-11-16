# -*- coding: utf-8 -*-
"""
Input plug-in for the FLEUR input generator 'inpgen'.
The input generator for the Fleur code is a preprocessor
and should be run localy (with the direct scheduler) or inline,
because it does not take many resources.
"""
from aiida.orm.calculation.job import JobCalculation
from aiida.orm import DataFactory
from aiida.common.exceptions import InputValidationError
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.constants import elements as PeriodicTableElements 
from aiida.common.utils import classproperty
from aiida_fleur.tools.StructureData_util import abs_to_rel_f, abs_to_rel
from aiida_fleur.tools.xml_util import convert_to_fortran_bool, convert_to_fortran_string

__copyright__ = u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany. All rights reserved."
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

bohr_a = 0.52917721092#A # TODO import from somewhere
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')

class FleurinputgenCalculation(JobCalculation):
    """
    JobCalculationClass for the Inputgenerator, which is a preprocessor for a FLEUR calculation. Here is implemented how an input file for 'inpgen' is written from AiiDA data objects.
    For more information about produced files and the FLEUR-code family, go to http://www.flapw.de/.
    """
    #### (Maintain) if inputgen keys change ####

    def _init_internal_params(self):
        super(FleurinputgenCalculation, self)._init_internal_params()

        # Default fleur output parser
        self._default_parser = 'fleur.fleurinpgenparser'

        # Default input and output files
        self._DEFAULT_INPUT_FILE = 'aiida.in' # will be shown with inputcat
        self._DEFAULT_OUTPUT_FILE = 'out' #'shell.out' #will be shown with outputcat

        # created file names, some needed for Fleur calc
        self._INPXML_FILE_NAME = 'inp.xml'
        self._INPUT_FILE_NAME = 'aiida.in'
        self._SHELLOUT_FILE_NAME = 'shell.out'
        self._OUTPUT_FILE_NAME = 'out'
        self._ERROR_FILE_NAME = 'out.error'
        self._STRUCT_FILE_NAME = 'struct.xsf'
        '''
        self._INP_FILE_NAME = 'inp'
        self._ENPARA_FILE_NAME = 'enpara'
        self._SYMOUT_FILE_NAME = 'sym.out'
        self._FORT_FILE_NAME = 'fort93'
        self._CORELEVEL_FILE_NAME = 'corelevels.' # Add coordination number
        '''
        self._settings_keys = ['additional_retrieve_list', 'remove_from_retrieve_list',
                               'cmdline']
    # TODO switch all these to init_interal_params?
    _OUTPUT_SUBFOLDER = './fleur_inp_out/'
    _PREFIX = 'aiida'

    # Additional files that should always be retrieved for the specific plugin
    _internal_retrieve_list = []
    _automatic_namelists = {}
    # Specify here what namelist and parameters the inpgen takes
    #TODO: complete?
    _possible_namelists = ['title', 'input', 'lattice', 'gen', 'shift', 'factor', 'qss',
                           'soc', 'atom', 'comp', 'exco', 'film', 'kpt', 'end']
                           # this order is important!
    _possible_params = {'input':['film', 'cartesian', 'cal_symm', 'checkinp',
                                 'symor', 'oldfleur'],
                        'lattice':['latsys', 'a0', 'a', 'b', 'c', 'alpha',
                                   'beta', 'gamma'],
                        'atom':['id', 'z', 'rmt', 'dx', 'jri', 'lmax',
                                'lnonsph', 'ncst', 'econfig', 'bmu', 'lo',
                                'element', 'name'],
                        'comp' : ['jspins', 'frcor', 'ctail', 'kcrel', 'gmax',
                                  'gmaxxc', 'kmax'],
                        'exco' : ['xctyp', 'relxc'],
                        'film' : ['dvac', 'dtild'],
                        'soc' : ['theta', 'phi'],
                        'qss' : ['x', 'y', 'z'],
                        'kpt' : ['nkpt', 'kpts', 'div1', 'div2', 'div3',
                                 'tkb', 'tria'],
                        'title' : {}
                       }

    # Keywords that cannot be set
    # TODO: To specify what combinations are not allowed together,
    # or not at all (lattice ?, shift, scale)
    _blocked_keywords = []

    # TODO different kpt mody? (use kpointNode)? FleurinpdData can do it.
    _use_kpoints = False

    # If two lattices are given, via the input &lattice
    # and the aiida structure prefare the aiida structure?
    # currently is not allow the use of &lattice
    _use_aiida_structure = False

    # Default title
    _inp_title = 'A Fleur input generator calulation with aiida'


    @classproperty
    def _use_methods(cls):
        """
        Extend the parent _use_methods with further keys.
        specifies what nodes have to be in calculation TODO: decide what is
        settings and what is parameters, sturcture might not be needed
        if &lattice is defined in inp
        """
        retdict = JobCalculation._use_methods
        retdict.update({
            "structure": {
                'valid_types': StructureData,
                'additional_parameter': None,
                'linkname': 'structure',
                'docstring': "Choose the input structure to use",
                },
            "parameters": {
                'valid_types': ParameterData,
                'additional_parameter': None,
                'linkname': 'parameters',
                'docstring': ("Use a node that specifies the input parameters "
                              "for the namelists"),
                },
            "settings": {
                'valid_types': ParameterData,
                'additional_parameter': None,
                'linkname': 'settings',
                'docstring': (
                    "This parameter data node is used to specify for some "
                    "advanced features how the plugin behaves. You can add files"
                    "the retrieve list, or add command line switches, "
                    "for all available features here check the documentation."),
            }})
        return retdict


    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        This is the routine to be called when you want to create
        the input files for the inpgen with the plug-in.

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """

        #from aiida.common.utils import get_unique_filename, get_suggestion
        #import re

        # Get the connection between coordination number and element symbol
        # maybe do in a differnt way
        _atomic_numbers = {data['symbol']: num for num,
                           data in PeriodicTableElements.iteritems()}

        possible_namelists = self._possible_namelists
        possible_params = self._possible_params
        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []
        bulk = True
        film = False

        # convert these 'booleans' to the inpgen format.
        replacer_values_bool = [True, False, 'True', 'False', 't', 'T',
                                'F', 'f']
        # some keywords require a string " around them in the input file.
        string_replace = ['econfig', 'lo', 'element', 'name']

        # of some keys only the values are writen to the file, specify them here.
        val_only_namelist = ['soc', 'qss']

        # Scaling comes from the Structure
        # but we have to convert from Angstroem to a.u (bohr radii)
        scaling_factors = [1.0, 1.0, 1.0] #
        scaling_lat = 1.#/bohr_a
        scaling_pos = 1./bohr_a # Angstrom to atomic
        own_lattice = False #not self._use_aiida_structure

        # The inpfile gen is run in serial TODO: How to do this by default?
        #self.set_withmpi(False)

        ##########################################
        ############# INPUT CHECK ################
        ##########################################

        # first check existence of structure and if 1D, 2D, 3D
        try:
            structure = inputdict.pop(self.get_linkname('structure'))
        except KeyError:
            raise InputValidationError("No structure specified for this"
                                       " calculation")
        if not isinstance(structure, StructureData):
            raise InputValidationError(
                       "structure is not of type StructureData")

        pbc = structure.pbc
        if False in pbc:
            bulk = False
            film = True

        # check existence of parameters (optional)
        parameters = inputdict.pop(self.get_linkname('parameters'), None)
        if parameters is None:
            # use default
            parameters_dict = {}
        else:
            if not isinstance(parameters, ParameterData):
                raise InputValidationError("parameters, if specified, must be of "
                                           "type ParameterData")
            parameters_dict = _lowercase_dict(parameters.get_dict(),
                                              dict_name='parameters')

        # we write always out rel coordinates, because thats the way FLEUR uses
        # them best. we have to convert them from abs, becauses thats how they
        #are stored in a Structure node. cartesian=F is default
        if 'input' in parameters_dict:
            parameters_dict['input']['cartesian'] = False
            if film:
                parameters_dict['input']['film'] = True
        else:
            if bulk:
                parameters_dict['input'] = {'cartesian' : False}
            elif film:
                parameters_dict['input'] = {'cartesian' : False, 'film' : True}

        namelists_toprint = possible_namelists

        # check parameters keys TODO: values needed, or keep plug-in as stupid as possible?
        #if parameters_dict:# TODO remove, unnesseary now?
        input_params = parameters_dict
        #TODO:?make everything lowercase in the database, and change it to inpgen format?
        #_lowercase_dict(parameters.get_dict(),
                                         #dict_name='parameters')
        #input_params = {k: _lowercase_dict(val, dict_name=k)
        #                   for k, val in input_params.iteritems()}
        #input_params_keys = input_params.keys()

        if 'title' in input_params.keys():
            self._inp_title = input_params.pop('title')
        #TODO validate type of values of the input parameter keys ?

        #check input_parameters
        for namelist, paramdic in input_params.iteritems():
            if 'atom' in namelist: # this namelist can be specified more often
                # special atom namelist needs to be set for writing,
                #  but insert it in the right spot!
                index = namelists_toprint.index('atom') + 1
                namelists_toprint.insert(index, namelist)
                namelist = 'atom'
            if namelist not in possible_namelists:
                raise InputValidationError(
                    "The namelist '{}' is not supported by the fleur"
                    " inputgenerator. Check on the fleur website or add '{}'"
                    "to _possible_namelists.".format(namelist, namelist))
            for para in paramdic.keys():
                if para not in possible_params[namelist]:
                    raise InputValidationError(
                        "The property '{}' is not supported by the "
                        "namelist '{}'. "
                        "Check the fleur website, or if it really is,"
                        " update _possible_params. ".format(para, namelist))
                if paramdic[para] in replacer_values_bool:
                    # because 1/1.0 == True, and 0/0.0 == False
                    # maybe change in convert_to_fortran that no error occurs
                    if isinstance(paramdic[para], (int, float)):
                        if isinstance(paramdic[para], bool):
                            paramdic[para] = convert_to_fortran_bool(paramdic[para])
                    else:
                        paramdic[para] = convert_to_fortran_bool(paramdic[para])

                if para in string_replace:
                    #TODO check if its in the parameter dict
                    #print para
                    paramdic[para] = convert_to_fortran_string(paramdic[para])
                    #print "{}".format(paramdic[para])
            #in fleur it is possible to give a lattice namelist
            if 'lattice' in input_params.keys():
                own_lattice = True
                structure = inputdict.pop(self.get_linkname('structure'), None)
                if structure is not None: #two structures given?
                    #which one should be prepared? TODO: print warning or even error
                    if self._use_aiida_structure:
                        if not isinstance(structure, StructureData):
                            raise InputValidationError("structure is not of type"
                                                       " StructureData")
                        input_params.pop('lattice', {})
                        own_lattice = False




        '''
        # TODO allow only usual kpt meshes and use therefore Aiida kpointData
        if self._use_kpoints:
            try:
                kpoints = inputdict.pop(self.get_linkname('kpoints'))
            except KeyError:
                raise InputValidationError("No kpoints specified for this"
                                           " calculation")
            if not isinstance(kpoints, KpointsData):
                raise InputValidationError("kpoints is not of type KpointsData")
        '''

        #TODO I think the code should not be in the input dict. check local,
        # verus remote, codeinfos, one several codes..
        try:
            code = inputdict.pop(self.get_linkname('code'))
        except KeyError:
            raise InputValidationError("No code specified for this "
                                       "calculation")

        # check existence of settings (optional)
        settings = inputdict.pop(self.get_linkname('settings'), None)
        #print('settings: {}'.format(settings))
        if settings is None:
            settings_dict = {}
        else:
            if not isinstance(settings, ParameterData):
                raise InputValidationError("settings, if specified, must be of "
                                           "type ParameterData")
            else:
                settings_dict = settings.get_dict()
        #check for for allowed keys, ignor unknown keys but warn.
        for key in settings_dict.keys():
            if key not in self._settings_keys:
                #TODO warrning
                self.logger.info("settings dict key {} for Fleur calculation"
                                 "not reconized, only {} are allowed."
                                 "".format(key, self._settings_keys))

        # Here, there should be no more parameters...
        if inputdict:
            raise InputValidationError(
                "The following input data nodes are "
                "unrecognized: {}".format(inputdict.keys()))

        ##############################
        # END OF INITIAL INPUT CHECK #

        #######################################################
        ######### PREPARE PARAMETERS FOR INPUT FILE ###########

        #### STRUCTURE_PARAMETERS ####

        scaling_factor_card = ""
        cell_parameters_card = ""

        if not own_lattice:
            cell = structure.cell
            for vector in cell:
                scaled = [a*scaling_pos for a  in vector]#scaling_pos=1./bohr_a
                cell_parameters_card += ("{0:18.10f} {1:18.10f} {2:18.10f}"
                                         "\n".format(scaled[0], scaled[1], scaled[2]))
            scaling_factor_card += ("{0:18.10f} {1:18.10f} {2:18.10f}"
                                    "\n".format(scaling_factors[0],
                                                scaling_factors[1],
                                                scaling_factors[2]))


        #### ATOMIC_POSITIONS ####

        # TODO: be careful with units
        atomic_positions_card_list = [""]
        # Fleur does not have any keyword before the atomic species.
        # first the number of atoms then the form nuclear charge, postion
        # Fleur hast the option of nuclear charge as floats,
        # allows the user to distinguish two atoms and break the symmetry.
        if not own_lattice:
            natoms = len(structure.sites)
            #for FLEUR true, general not, because you could put several
            # atoms on a site
            # TODO: test that only one atom at site?
            atomic_positions_card_list.append("    {0:3}\n".format(natoms))

            # TODO this feature might change in Fleur, do different. that in inpgen kind gets a name, which will also be the name in fleur inp.xml.
            # now user has to make kind_name = atom id.
            for site in structure.sites:
                kind_name = site.kind_name
                site_symbol = structure.get_kind(kind_name).symbols[0] # TODO: list I assume atoms therefore I just get the first one...
                atomic_number = _atomic_numbers[site_symbol]
                atomic_number_name = atomic_number
                if site_symbol != kind_name: # This is an important fact, if usere renames it becomes a new species!
                    suc = True
                    try:
                        head = kind_name.rstrip('0123456789')
                        kind_namet = int(kind_name[len(head):])
                    except ValueError:
                        suc = False
                    if suc:
                        atomic_number_name = '{}.{}'.format(atomic_number, kind_namet)
                # per default we use relative coordinates in Fleur
                # we have to scale back to atomic units from angstrom
                pos = site.position
                #print 'pos {}'.format(pos)
                if bulk:
                    vector_rel = abs_to_rel(pos, cell)
                elif film:
                    vector_rel = abs_to_rel_f(pos, cell, structure.pbc)
                    vector_rel[2] = vector_rel[2]*scaling_pos
                atomic_positions_card_list.append(
                    "    {0:3} {1:18.10f} {2:18.10f} {3:18.10f}"
                    "\n".format(atomic_number_name,
                                vector_rel[0], vector_rel[1],
                                vector_rel[2]))
                #print atomic_positions_card_list
                #TODO check format

        else:
            # TODO with own lattice atomic positions have to come from somewhere
            # else.... User input?
            raise InputValidationError("fleur lattice needs also the atom "
                                       " position as input,"
                                       " not implemented yet, sorry!")
        atomic_positions_card = "".join(atomic_positions_card_list)
        del atomic_positions_card_list # Free memory

        #### Kpts ####

        # TODO: kpts
        #kpoints_card = ""#.join(kpoints_card_list)
        #del kpoints_card_list

        #######################################
        #### WRITE ALL CARDS IN INPUT FILE ####

        input_filename = tempfolder.get_abs_path(self._INPUT_FILE_NAME)

        with open(input_filename, 'w') as infile:

            #first write title
            infile.write("{0}\n".format(self._inp_title))

            #then write &input namelist
            infile.write("&{0}".format('input'))

            # namelist content; set to {} if not present, so that we leave an
            # empty namelist
            namelist = input_params.pop('input', {})
            for k, val in sorted(namelist.iteritems()):
                infile.write(get_input_data_text(k, val, False, mapping=None))
            infile.write("/\n")

            # Write lattice information now
            infile.write(cell_parameters_card)
            infile.write("{0:18.10f}\n".format(scaling_lat))
            infile.write(scaling_factor_card)
            infile.write("\n")

            # Write Atomic positons
            infile.write(atomic_positions_card)

            # Write namelists after atomic positions
            for namels_name in namelists_toprint:
                namelist = input_params.pop(namels_name, {})
                if namelist:
                    if 'atom' in namels_name:
                        namels_name = 'atom'
                    infile.write("&{0}\n".format(namels_name))
                    if namels_name in val_only_namelist:
                        for k, val in sorted(namelist.iteritems()):
                            infile.write(get_input_data_text(k, val, True, mapping=None))
                    else:
                        for k, val in sorted(namelist.iteritems()):
                            infile.write(get_input_data_text(k, val, False, mapping=None))
                    infile.write("/\n")
            #infile.write(kpoints_card)

        if input_params:
            raise InputValidationError(
                "input_params leftover: The following namelists are specified"
                " in input_params, but are "
                "not valid namelists for the current type of calculation: "
                "{}".format(",".join(input_params.keys())))


        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid

        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve per default only out file and inp.xml file?
        retrieve_list = []

        # TODO: let the user specify?
        #settings_retrieve_list = settings_dict.pop(
        #                             'ADDITIONAL_RETRIEVE_LIST', [])
        retrieve_list.append(self._INPXML_FILE_NAME)
        retrieve_list.append(self._OUTPUT_FILE_NAME)
        retrieve_list.append(self._SHELLOUT_FILE_NAME)
        retrieve_list.append(self._ERROR_FILE_NAME)
        retrieve_list.append(self._STRUCT_FILE_NAME)
        retrieve_list.append(self._INPUT_FILE_NAME)
        #calcinfo.retrieve_list += settings_retrieve_list
        #calcinfo.retrieve_list += self._internal_retrieve_list

        # user specific retrieve
        add_retrieve = settings_dict.get('additional_retrieve_list', [])
        #print('add_retrieve: {}'.format(add_retrieve))
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
        cmdline_params = ["-explicit"] # TODO? let the user decide -econfig?

        # user specific commandline_options
        for command in settings_dict.get('cmdline', []):
            cmdline_params.append(command)
        codeinfo.cmdline_params = (list(cmdline_params))

        codeinfo.code_uuid = code.uuid
        codeinfo.stdin_name = self._INPUT_FILE_NAME
        codeinfo.stdout_name = self._SHELLOUT_FILE_NAME # shell output will be piped in file
        codeinfo.stderr_name = self._ERROR_FILE_NAME # std error too

        calcinfo.codes_info = [codeinfo]

        '''
        if settings_dict:
            try:
                Parserclass = self.get_parserclass()
                parser = Parserclass(self)
                parser_opts = parser.get_parser_settings_key()
                settings_dict.pop(parser_opts)
            except (KeyError, AttributeError): # the key parser_opts isn't
                                              # inside the dictionary
                raise InputValidationError(
                    "The following keys have been found in the settings "
                    "input node, but were not understood: {}"
                    "".format(",".join(settings_dict.keys())))
        '''
        return calcinfo

def get_input_data_text(key, val, value_only, mapping=None):#TODO rewrite for fleur/ delete unnessesariy parts
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
    from aiida.common.utils import conv_to_fortran
    # I don't try to do iterator=iter(val) and catch TypeError because
    # it would also match strings
    # I check first the dictionary, because it would also matc
    # hasattr(__iter__)
    if isinstance(val, dict):
        if mapping is None:
            raise ValueError("If 'val' is a dictionary, you must provide also "
                             "the 'mapping' parameter")

        # At difference with the case of a list, at the beginning
        # list_of_strings
        # is a list of 2-tuples where the first element is the idx, and the
        # second is the actual line. This is used at the end to
        # resort everything.
        list_of_strings = []
        for elemk, itemval in val.iteritems():
            try:
                idx = mapping[elemk]
            except KeyError:
                raise ValueError("Unable to find the key '{}' in the mapping "
                                 "dictionary".format(elemk))

            list_of_strings.append((
                idx, "  {0}({2})={1} ".format(key, conv_to_fortran(itemval), idx)))
                #changed {0}({2}) = {1}\n".format

        # I first have to resort, then to remove the index from the first
        # column, finally to join the strings
        list_of_strings = zip(*sorted(list_of_strings))[1]
        return "".join(list_of_strings)
    elif hasattr(val, '__iter__'):
        if value_only:
            list_of_strings = [
                "  ({1}){0} ".format(conv_to_fortran(itemval), idx+1)
                for idx, itemval in enumerate(val)]
        else:
            # a list/array/tuple of values
            list_of_strings = [
                "  {0}({2})={1} ".format(key, conv_to_fortran(itemval),
                                         idx+1)
                for idx, itemval in enumerate(val)]
        return "".join(list_of_strings)
    else:
        # single value
        #return "  {0}={1} ".format(key, conv_to_fortran(val))
        if value_only:
            return " {0} ".format(val)
        else:
            return "  {0}={1} ".format(key, val)

# TODO import from QE?
def _lowercase_dict(dic, dict_name):
    """
    converts every entry in a dictionary to lowercase
    :param dic: parameters dictionary
    :param dict_name: dictionary name
    """
    from collections import Counter

    if isinstance(dic, dict):
        new_dict = dict((str(k).lower(), val) for k, val in dic.iteritems())
        if len(new_dict) != len(dic):
            num_items = Counter(str(k).lower() for k in dic.keys())
            double_keys = ",".join([k for k, val in num_items if val > 1])
            raise InputValidationError(
                "Inside the dictionary '{}' there are the following keys that "
                "are repeated more than once when compared case-insensitively:"
                "{}.This is not allowed.".format(dict_name, double_keys))
        return new_dict
    else:
        raise TypeError("_lowercase_dict accepts only dictionaries as argument")
