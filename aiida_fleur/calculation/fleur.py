# -*- coding: utf-8 -*-
"""
Input plug-in for a FLEUR ciculation. fleur.x
"""
# TODO:
# polishing
# think about exception. warning policy.
# TODO maybe allow only single file names not *
# TODO maybe check the settings key values, make a list of all fleur files?
import os
#from lxml import etree
#from lxml.etree import XMLSyntaxError

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm.calculation.job import JobCalculation
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida.common.datastructures import CalcInfo, CodeInfo
#from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.remote import RemoteData
#from aiida.orm.data.fleurinp.fleurinp import FleurinpData
from aiida_fleur.data.fleurinp import FleurinpData
#from aiida.orm.data.array.kpoints import KpointsData
from aiida.common.utils import classproperty
from aiida.common.exceptions import InputValidationError, ValidationError
from aiida.common.exceptions import UniquenessError

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


class FleurCalculation(JobCalculation):
    """
    Main DFT code of the FLEUR code
    For more information about the FLEUR-code family, go to http://www.flapw.de/
    """
    def _init_internal_params(self):
        super(FleurCalculation, self)._init_internal_params()

        ######### Only this should be to be maintained! #########

        # Default fleur output parser
        self._default_parser = 'fleur.fleurparser'
        #self._default_parser = 'fleur.fleur'

        # should a kpt node be used or fleur generate the mesh?
        self._use_kpoints = False
        self._INPXML_FILE_NAME = 'inp.xml'

        # Default input and output files
        self._DEFAULT_INPUT_FILE = 'inp.xml'#self._set_INPXML_FILE_PATH()
        #self._FLEURINPDATA_FOLDER
        #fleurinp.get_file_abs_path(self._INPXML_FILE_NAME)
        #'inp.xml' # this has to change the file is under FleurinpData
        self._DEFAULT_OUTPUT_FILE = 'out.xml'
        #print self._DEFAULT_INPUT_FILE

        # Name of all files in FLEUR
        # TODO think also to oursource this in a FleurCalc structure, and add
        # as info when what file has to be copied

        # these will be shown in AiiDA
        self._OUTPUT_FILE_NAME = 'aiida.out' # Shell output
        self._INPUT_FILE_NAME = 'inp.xml'
        #fleur file names:

        # needed for calc

        self._OUTXML_FILE_NAME = 'out.xml'
        self._INP_FILE_NAME = 'inp'
        self._ENPARA_FILE_NAME = 'enpara'
        self._SYMOUT_FILE_NAME = 'sym.out'
        self._CDN1_FILE_NAME = 'cdn1'
        self._SHELLOUTPUT_FILE_NAME = 'shell.out'
        self._ERROR_FILE_NAME = 'out.error'
         # other
        self._OUT_FILE_NAME = 'out'
        self._CDNC_FILE_NAME = 'cdnc' # core charge density
        self._TIME_INFO_FILE_NAME = 'time.info'
        self._KPTS_FILE_NAME = 'kpts'
        self._QPTS_FILE_NAME = 'qpts'
        self._PLOT_INP_FILE_NAME = 'plot_inp'
        self._BROYD_FILE_NAME = 'broyd*'
        self._POT_FILE_NAME = 'pot*'
        self._POT1_FILE_NAME = 'pottot'
        self._POT2_FILE_NAME = 'potcoul'
        self._STRUCTURE_FILE_NAME = 'struct.xcf'
        self._STARS_FILE_NAME = 'stars'
        self._WKF2_FILE_NAME = 'wkf2'

        # special out files
        self._DOS_FILE_NAME = 'DOS.*'
        self._DOSINP_FILE_NAME = 'dosinp'
        self._BAND_GNU_FILE_NAME = 'band.gnu'
        self._BAND_FILE_NAME = 'bands.*'
        self._NEW_XMlINP_FILE_NAME = 'inp_new.xml'

        # helper files
        self._FLEUR_WARN_ONLY_INFO_FILE_NAME = 'FLEUR_WARN_ONLY'
        self._JUDFT_WARN_ONLY_INFO_FILE_NAME = 'JUDFT_WARN_ONLY'
        self._QFIX_FILE_NAME = 'qfix'


        # forces and relaxation files
        self._FORCE_FILE_NAME = 'forces.dat'

        # jij files
        self._JENERG_FILE_NAME = 'jenerg'
        self._MCINP_FILE_NAME = 'MCinp'
        self._QPTSINFO_FILE_NAME = 'qptsinfo'
        self._SHELL_FILE_NAME = 'shells'
        self._JCONST_FILE_NAME = 'jconst'

        # files for lda+U
        self._NMMPMAT_FILE_NAME = 'n_mmp_mat'

        # files for hybrid functionals
        self._COULOMB1_FILE_NAME = 'coulomb1'
        self._MIXBAS_FILE_NAME = 'mixbas'
        self._CMT_FIlE_NAME = 'cmt'
        self._CZ_FILE_NAME = 'cz'
        self._OLAP_FILE_NAME = 'olap'
        self._VR0_FILE_NAME = 'vr0'

        # files non-collinear calculation
        self._RHOMAT_INP_FILE_NAME = 'rhomat_inp'
        self._RHOMAT_OUT_FILE_NAME = 'rhomat_out'
        self._CDN_FILE_NAME = 'cdn'
        self._DIROFMAG_FILE_NAME = 'dirofmag'

        # files for Wannier 90
        self._W90KPTS_FILE_NAME = 'w90kpts'
        self._PROJ_FILE_NAME = 'proj'
        self._WANN_INP_FILE_NAME = 'wann_inp'
        self._BKPTS_FILE_NAME = 'bkpts'
        self._WFMMN_FILE_NAME = 'WF*.mmn'
        self._WFAMN_FILE_NAME = 'WF*.amn'
        self._WFWIN_FILE_NAME = 'WF*.win'
        self._WFWOUT_FILE_NAME = 'WF*.wout'
        self._UNK_FILE_NAME = 'UNK*'
        self._KPTSMAP_FILE_NAME = 'kptsmap'
        self._PROJGEN_INP_FILE_NAME = 'projgen_inp'
        self._IONS_FILE_NAME = 'IONS'
        self._POLARIZATION_OUT_FILE_NAME = 'polarization_out'
        self._HOPPING_FILE_NAME = 'hopping.*'
        self._WF1HSOMTX_FILE_NAME = 'WF1.hsomtx'
        self._RSSOCMAT_FILE_NAME = 'rssocmat.1'
        self._RSNABLA_FILE_NAME = 'rsnabla.*'
        self._WFNABL_FILE_NAME = 'WF*.nabl'

        # copy file lists. I rather dont like this.
        # Might gives rise to a lot of possible erros, if files or not there,
        #or Fleur did not created same, or at some point they will not be
        # deleted remotely.

        ########## Policy
        # we store everything needed for a further run in the local repository
        #(inp.xml, cdn1), also all important results files.
        # these will ALWAYS be copied from the local repository to the maschine
        # If a parent calculation exists, other files will be copied remotely
        #######

        #all possible files first chargedensity
        self._copy_filelist1 = []
        self._copy_filelist1 = [self._INP_FILE_NAME,
                                self._ENPARA_FILE_NAME,
                                self._SYMOUT_FILE_NAME,
                                self._CDN1_FILE_NAME,
                                self._KPTS_FILE_NAME,
                                self._STARS_FILE_NAME,
                                self._WKF2_FILE_NAME]

        #after inpgen, before first chargedensity
        self._copy_filelist_inpgen = [self._INPXML_FILE_NAME]

        #for after fleur SCF
        self._copy_filelist_scf1 = [self._CDN1_FILE_NAME]
        #self._INPXML_FILE_NAME, comes from fleurinpdata
        self._copy_filelist_scf = [self._CDN1_FILE_NAME, self._INPXML_FILE_NAME]
        self._copy_filelist_scf_remote = [self._BROYD_FILE_NAME]
        self._copy_filelist3 = []
        self._copy_filelist3 = [self._INP_FILE_NAME,
                                self._ENPARA_FILE_NAME,
                                self._SYMOUT_FILE_NAME,
                                self._CDN1_FILE_NAME,
                                self._KPTS_FILE_NAME,
                                self._STARS_FILE_NAME,
                                self._WKF2_FILE_NAME,
                                self._BROYD_FILE_NAME,
                                self._OUT_FILE_NAME,
                                self._POT_FILE_NAME]

        #files need for rerun
        self._copy_filelist3 = []
        self._copy_filelist_dos = [self._INPXML_FILE_NAME,
                                   self._CDN1_FILE_NAME]
        self._copy_filelist_band = [self._INPXML_FILE_NAME,
                                    self._POT_FILE_NAME,
                                    self._CDN1_FILE_NAME]


        self._copy_filelist_hybrid = []
        self._copy_filelist_jij = []

        #possible settings_dict keys
        self._settings_keys = ['additional_retrieve_list', 'remove_from_retrieve_list',
                               'additional_remotecopy_list', 'remove_from_remotecopy_list'
                               'cmdline']
        #possible modes?
        self._fleur_modes = ['band', 'dos', 'forces', 'chargeDen',
                             'latticeCo', 'scf']
    #_DEFAULT_INPUT_FILE = 'inp.xml'
    @classproperty
    def _use_methods(cls):
        """
        Extend the parent _use_methods with further keys.
        """
        retdict = JobCalculation._use_methods
        retdict.update({
            "fleurinpdata": {
                'valid_types': FleurinpData,
                'additional_parameter': None,
                'linkname': 'fleurinpdata',
                'docstring': (
                    "Use a FleruinpData node that specifies the input parameters"
                    "usually copy from the parent calculation, basicly makes"
                    "the inp.xml file visible in the db and makes sure it has "
                    "the files needed."),
                },
            "parent_folder": {
                'valid_types': RemoteData,
                'additional_parameter': None,
                'linkname': 'parent_calc_folder',
                'docstring': (
                    "Use a remote or local repository folder as parent folder "
                    "(also for restarts and similar). It should contain all the "
                    "needed files for a Fleur calc, only edited files should be "
                    "uploaded from the repository."),
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
            #
            #"parent_calc":{
            #   'valid_types': (FleurinputgenCalculation, FleurCalculation),
            #   'additional_parameter': None,
            #   'linkname': 'parent_calc',
            #   'docstring': ("Use a parent calculation from which to copy"
            #                 "files, and so on."),
            #
            #  },
            #"kpoints" : {
            #   'valid_types': KpointsData,
            #   'additional_parameter': None,
            #   'linkname': 'kpoints',
            #   'docstring': "Connect to k-point node from inpgen or other calc.",
            #   }


        return retdict

    @classproperty
    def _OUTPUT_FOLDER(cls):
        return './'
    '''
    @classproperty
    def _set_INPXML_FILE_PATH(self, cls, fleurinp=None):
        if fleruinp:
            if not isinstance(fleurinp, FleurinpData):
                self._DEFAULT_INPUT_FILE = 'inp.xml'
            else:
                self._DEFAULT_INPUT_FILE(
                    fleurinp.get_file_abs_path(self._INPXML_FILE_NAME))
        else:
            self._DEFAULT_INPUT_FILE = 'inp.xml'

    @classproperty
    def _FLEURINPDATA_FOLDER(self, cls, inputdict):
        try:
            fleurinp = inputdict[self.get_linkname('fleurinpdata')]
        except:
            return None
        if fleurinp is None:
            xml_inp_dict = {}
        else:
            if not isinstance(fleurinp, FleurinpData):
                raise InputValidationError(
                    "The FleurinpData node given is not of type FleurinpData.")
        return fleurinp.get_file_abs_path(self._INPXML_FILE_NAME)

    def set_inppath(cls):
        self._DEFAULT_INPUT_FILE = fleurinp.get_file_abs_path(
                                                         self._INPXML_FILE_NAME)
    '''
    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        This is the routine to be called when you make a fleur calculation
        Here should be checked if all the files are there to run fleur.
        And input files (inp.xml) can be modified.

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """

        #   from aiida.common.utils import get_unique_filename, get_suggestion

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []
        mode_retrieved_filelist = []
        #filelocal_copy_list = []
        #filelist_tocopy = []
        filelist_tocopy_remote = []
        settings_dict = {}

        #fleur_calc = False
        #new_inp_file = False
        #ignore_mode = False
        has_fleurinp = False
        has_parent = False
        #restart_flag = False
        fleurinpgen = False
        copy_remotely = True

        ##########################################
        ############# INPUT CHECK ################
        ##########################################

        try:
            code = inputdict.pop(self.get_linkname('code'))
        except KeyError:
            raise InputValidationError("No code specified for this calculation")

        # a Fleur calc can be created from a fleurinpData alone
        #(then no parent is needed) all files are in the repo, but usually it is
        # a child of a inpgen calc or an other fleur calc (some or all files are
        # in a remote source). if the User has not changed something, the
        #calculation does not need theoretical a new FleurinpData it could use
        #the one from the parent, but the plug-in desgin is in a way that it has
        # to be there and it just copies files if changes occured..

        fleurinp = inputdict.pop(self.get_linkname('fleurinpdata'), None)
        if fleurinp is None:
            #xml_inp_dict = {}
            has_fleurinp = False
        else:
            if not isinstance(fleurinp, FleurinpData):
                raise InputValidationError(
                    "The FleurinpData node given is not of type FleurinpData.")
            has_fleurinp = True
        parent_calc_folder = inputdict.pop(self.get_linkname('parent_folder'),
                                           None)
        #print parent_calc_folder
        if parent_calc_folder is None:
            has_parent = False
            if not has_fleurinp:
                raise InputValidationError(
                    "No parent calculation found and no fleurinp data "
                    "given, need either one or both for a "
                    "'fleurcalculation'.")
        else: #
            if not isinstance(parent_calc_folder, RemoteData):
                raise InputValidationError("parent_calc_folder, if specified,"
                                           "must be of type RemoteData")

            # extract parent calculation
            parent_calcs = parent_calc_folder.get_inputs(node_type=JobCalculation)
            n_parents = len(parent_calcs)
            if n_parents != 1:
                raise UniquenessError(
                    "Input RemoteData is child of {} "
                    "calculation{}, while it should have a single parent"
                    "".format(n_parents, "" if n_parents == 0 else "s"))
            parent_calc = parent_calcs[0]
            has_parent = True
            #print parent_calc
            # check that it is a valid parent
            #self._check_valid_parent(parent_calc)


            # if inpgen calc do
            # check if folder from db given, or get folder from rep.
            # Parent calc does not has to be on the same computer.

            if isinstance(parent_calc, FleurCalculation):
                new_comp = self.get_computer()
                old_comp = parent_calc.get_computer()
                if new_comp.uuid != old_comp.uuid:
                    #dont copy files, copy files localy
                    copy_remotely = False
                    #raise InputValidationError(
                    #    "FleurCalculation must be launched on the same computer"
                    #    " of the parent: {}".format(old_comp.get_name()))
            elif isinstance(parent_calc, FleurinputgenCalculation):
                fleurinpgen = True
                new_comp = self.get_computer()
                old_comp = parent_calc.get_computer()
                if new_comp.uuid != old_comp.uuid:
                    #dont copy files, copy files localy
                    copy_remotely = False
            else:
                raise InputValidationError(
                    "parent_calc, must be either an 'inpgen calculation' or"
                    " a 'fleur calculation'.")

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
        #print settings_dict
        # Here, there should be no other inputs
        if inputdict:
            raise InputValidationError(
                "The following input data nodes are "
                "unrecognized: {}".format(inputdict.keys()))

        #TODO: Detailed check of FleurinpData
        # if certain files are there in fleurinpData.
        # from where to copy

        ##############################
        # END OF INITIAL INPUT CHECK #


        # file copy stuff TODO check in fleur input
        if has_fleurinp:
            self._DEFAULT_INPUT_FILE = fleurinp.get_file_abs_path(self._INPXML_FILE_NAME)

            #local_copy_list.append((
            #    fleurinp.get_file_abs_path(self._INPXML_FILE_NAME),
            #    self._INPXML_FILE_NAME))
            #copy ALL files from inp.xml
            allfiles = fleurinp.files
            for file1 in allfiles:
                local_copy_list.append((
                    fleurinp.get_file_abs_path(file1),
                    file1))
            modes = fleurinp.get_fleur_modes()

            # add files to mode_retrieved_filelist
            if modes['band']:
                mode_retrieved_filelist.append(self._BAND_FILE_NAME)
                mode_retrieved_filelist.append(self._BAND_GNU_FILE_NAME)
            if modes['dos']:
                mode_retrieved_filelist.append(self._DOS_FILE_NAME)
            if modes['forces']:
                print 'FORCES!!!'
                mode_retrieved_filelist.append(self._NEW_XMlINP_FILE_NAME)
                mode_retrieved_filelist.append(self._FORCE_FILE_NAME)
            if modes['ldau']:
                mode_retrieved_filelist.append(self._NMMPMAT_FILE_NAME)
            #if noco, ldau, gw...
            # TODO: check from where it was copied, and copy files of its parent
            # if needed
        #self.logger.info("@@@@@@@@@@@@@@@@@@@@@@@@has_parent {}".format(has_parent))

        if has_parent:
            # copy the right files #TODO check first if file, exist and throw
            # warning, now this will throw an error
            outfolderpath = parent_calc.out.retrieved.folder.abspath
            self.logger.info("out folder path {}".format(outfolderpath))

            #print outfolderpath
            if fleurinpgen and (not has_fleurinp):
                for file1 in self._copy_filelist_inpgen:
                    local_copy_list.append((
                        os.path.join(outfolderpath, 'path', file1),
                        os.path.join(file1)))
            elif not fleurinpgen and (not has_fleurinp): # fleurCalc
                for file1 in self._copy_filelist_scf:
                    local_copy_list.append((
                        os.path.join(outfolderpath, 'path', file1),
                        os.path.join(file1)))
                filelist_tocopy_remote = filelist_tocopy_remote# + self._copy_filelist_scf_remote
                #TODO get inp.xml from parent fleurinpdata, since otherwise it will be doubled in repo
            elif fleurinpgen and has_fleurinp:
                # everything is taken care of
                pass
            elif not fleurinpgen and has_fleurinp:
                # input file is already taken care of
                for file1 in self._copy_filelist_scf1:
                    local_copy_list.append((
                        os.path.join(outfolderpath, 'path', file1),
                        os.path.join(file1)))
                filelist_tocopy_remote = filelist_tocopy_remote# + self._copy_filelist_scf_remote

            # TODO not on same computer -> copy needed files from repository,
            # if they are not there, throw error
            if copy_remotely: # on same computer.
                #print('copy files remotely')

                # from fleurmodes
                if modes['pot8']:
                    filelist_tocopy_remote = filelist_tocopy_remote + self._copy_filelist_scf_remote
                    filelist_tocopy_remote.append(self._POT_FILE_NAME)
                #    #filelist_tocopy_remote.append(self._POT2_FILE_NAME)
                elif modes['dos']:
                    pass
                elif modes['band']:
                    pass
                else:
                    filelist_tocopy_remote = filelist_tocopy_remote + self._copy_filelist_scf_remote
                # from settings, user specified
                #TODO check if list?
                for file1 in settings_dict.get('additional_remotecopy_list', []):
                    filelist_tocopy_remote.append(file1)

                for file1 in settings_dict.get('remove_from_remotecopy_list', []):
                    if file1 in filelist_tocopy_remote:
                        filelist_tocopy_remote.remove(file1)

                for file1 in filelist_tocopy_remote:
                    remote_copy_list.append((
                        parent_calc_folder.get_computer().uuid,
                        os.path.join(parent_calc_folder.get_remote_path(), file1),
                        self._OUTPUT_FOLDER))
                #print remote_copy_list
                #self.logger.info("remote copy file list {}".format(remote_copy_list))


        ########## MAKE CALCINFO ###########

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid
        # Empty command line by default
        #cmdline_params = settings_dict.pop('CMDLINE', [])
        #calcinfo.cmdline_params = (list(cmdline_params)
        #                           + ["-in", self._INPUT_FILE_NAME])
        #print local_copy_list
        self.logger.info("local copy file list {}".format(local_copy_list))

        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        #(remotemachinename, remoteabspath, relativedestpath)
        calcinfo.remote_symlink_list = remote_symlink_list
        #calcinfo.stdout_name = self._OUTPUT_FILE_NAME

        # Retrieve by default the output file and the xml file
        retrieve_list = []
        retrieve_list.append(self._OUTXML_FILE_NAME)
        retrieve_list.append(self._INPXML_FILE_NAME)
        #calcinfo.retrieve_list.append(self._OUTPUT_FILE_NAME)
        retrieve_list.append(self._SHELLOUTPUT_FILE_NAME)
        retrieve_list.append(self._CDN1_FILE_NAME)
        retrieve_list.append(self._ERROR_FILE_NAME)
        #calcinfo.retrieve_list.append(self._TIME_INFO_FILE_NAME)
        retrieve_list.append(self._OUT_FILE_NAME)
        #calcinfo.retrieve_list.append(self._INP_FILE_NAME)
        #calcinfo.retrieve_list.append(self._ENPARA_FILE_NAME)
        #calcinfo.retrieve_list.append(self._SYMOUT_FILE_NAME)
        #calcinfo.retrieve_list.append(self._KPTS_FILE_NAME)

        # if certain things are modefied, flags set,
        #other files should be retrieved, example DOS.x...
        #print "mode_retrieved_filelist", repr(mode_retrieved_filelist)
        for mode_file in mode_retrieved_filelist:
            retrieve_list.append(mode_file)
        #print('retrieve_list: {}'.format(retrieve_list))

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
        # should look like: codepath -xmlInput < inp.xml > shell.out 2>&1
        walltime_sec = self.get_max_wallclock_seconds()
        #self.logger.info("!!!!!!!!!!!!!!!!!!! walltime_sec : {}"
        #                         "".format(walltime_sec))
        cmdline_params = ["-xml"]#, "-wtime", "{}".format(walltime_sec)]
        #walltime_sec = self.get_max_wallclock_seconds()
        #print('walltime: {}'.format(walltime_sec))
        if walltime_sec:
            walltime_min = max(1, walltime_sec/60)
            cmdline_params.append("-wtime")
            cmdline_params.append("{}".format(walltime_min))

        # user specific commandline_options
        for command in settings_dict.get('cmdline', []):
            cmdline_params.append(command)

        codeinfo.cmdline_params = list(cmdline_params)
        # + ["<", self._INPXML_FILE_NAME,
	    # ">", self._SHELLOUTPUT_FILE_NAME, "2>&1"]
        codeinfo.code_uuid = code.uuid
        codeinfo.withmpi = self.get_withmpi()
        codeinfo.stdin_name = self._INPUT_FILE_NAME
        codeinfo.stdout_name = self._SHELLOUTPUT_FILE_NAME
        #codeinfo.join_files = True
        codeinfo.stderr_name = self._ERROR_FILE_NAME

        calcinfo.codes_info = [codeinfo]
        '''
        # not needed in new version
        if fleurinpgen:# execute twice, as long start density stop
            codeinfo1 = CodeInfo()
            cmdline_params = ["-xmlInput"]
            codeinfo1.cmdline_params = list(cmdline_params)
            # + ["<", self._INPUT_FILE_NAME])#,
	        # ">",self._OUTPUT_FILE_NAME]
            codeinfo1.code_uuid = code.uuid
            codeinfo1.withmpi = self.get_withmpi()
            codeinfo1.stdin_name = self._INPUT_FILE_NAME
            codeinfo1.stdout_name = self._SHELLOUTPUT_FILE_NAME
            calcinfo.codes_info.append(codeinfo1)

        if settings_dict:
            raise InputValidationError("The following keys have been found in "
                "the settings input node, but were not understood: {}".format(
                ",".join(settings_dict.keys())))
        '''
        return calcinfo

    def _check_valid_parent(self, calc):
        """
        Check that calc is a valid parent for a FleurCalculation.
        It can be a FleurCalculation, InpgenCalculation, or (if the class exists) a
        CopyonlyCalculation
        :TODO: maybe assume that CopyonlyCalculation class always exists?
        """
        #from aiida.orm.calculation.job.simpleplugins.copyonly import CopyonlyCalculation

        try:
            if (((not isinstance(calc, FleurCalculation)))
                            and (not isinstance(calc, FleurinputgenCalculation))):
                            #and (not isinstance(calc, CopyonlyCalculation)) ):
                raise ValueError("Parent calculation must be a FleurCalculation, a "
                                 "FleurinputgenCalculation or a CopyonlyCalculation")
        except ImportError:
            if ((not isinstance(calc, FleurCalculation))
                            and (not isinstance(calc, FleurinputgenCalculation)) ):
                raise ValueError("Parent calculation must be a FleurCalculation or "
                                 "a FleurinputgenCalculation")


    def use_fleurinp(self, fleurinp):
        """
        set fleurinpdata and path to inp.xml file.
        """
        if not isinstance(fleurinp, FleurinpData):
            raise InputValidationError("The FleurinpData node given is not of type"
                                           " FleurinpData.")
        #print fleurinp.get_file_abs_path(self._INPXML_FILE_NAME)
        #print self._DEFAULT_INPUT_FILE
        self._DEFAULT_INPUT_FILE = fleurinp.get_file_abs_path(self._INPXML_FILE_NAME)
        # somehow this is not working...
        #print self._DEFAULT_INPUT_FILE
        self.use_fleurinpdata(fleurinp)


    def use_parent_calculation(self, calc):
        """
        Set the parent calculation of Fleur,
        from which it will inherit the outputsubfolder.
        The link will be created from parent RemoteData to FleurCalculation
        """
        from aiida.common.exceptions import NotExistent

        self._check_valid_parent(calc)

        remotedatas = calc.get_outputs(type=RemoteData)
        if not remotedatas:
            raise NotExistent("No output remotedata found in "
                                  "the parent")
        if len(remotedatas) != 1:
            raise UniquenessError("More than one output remotedata found in "
                                  "the parent")
        remotedata = remotedatas[0]

        self._set_parent_remotedata(remotedata)

    def _set_parent_remotedata(self,remotedata):
        """
        Used to set a parent remotefolder in the restart of fleur.
        """
        if not isinstance(remotedata,RemoteData):
            raise ValueError('remotedata must be a RemoteData')

        # complain if another remotedata is already found
        input_remote = self.get_inputs(node_type=RemoteData)
        if input_remote:
            raise ValidationError("Cannot set several parent calculation to a "
                                  "fleur calculation")

        self.use_parent_folder(remotedata)

    def _create_warnonly_file(self,calc):
        """
        Used to create a WARN_ONLY file in the calculation dir
        """
        pass
