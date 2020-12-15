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
This file contains a CalcJob that represents FLEUR calculation.
"""
from __future__ import absolute_import
import os
import io
import six

from aiida.engine import CalcJob
from aiida.orm import Dict
from aiida.orm import RemoteData
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.utils import classproperty
from aiida.common.exceptions import InputValidationError
from aiida.common.exceptions import UniquenessError
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation


class FleurCalculation(CalcJob):
    """
    A CalcJob class that represents FLEUR DFT calculation.
    For more information about the FLEUR-code family go to http://www.flapw.de/
    """

    ######### Only this should be to be maintained! #########

    # should a kpt node be used or fleur generate the mesh?
    _use_kpoints = False
    _INPXML_FILE_NAME = 'inp.xml'

    # Default input and output files
    _INPUT_FILE = 'inp.xml'
    _OUTPUT_FILE = 'out.xml'

    # these will be shown in AiiDA
    _OUTPUT_FILE_NAME = 'aiida.out'  # Shell output
    _INPUT_FILE_NAME = 'inp.xml'

    # needed for calc
    _OUTXML_FILE_NAME = 'out.xml'
    _INP_FILE_NAME = 'inp'
    _ENPARA_FILE_NAME = 'enpara'
    _SYMOUT_FILE_NAME = 'sym.out'
    _CDN1_FILE_NAME = 'cdn1'
    _SHELLOUTPUT_FILE_NAME = 'shell.out'
    _ERROR_FILE_NAME = 'out.error'
    # other
    _OUT_FILE_NAME = 'out'
    _CDNC_FILE_NAME = 'cdnc'  # core charge density
    _TIME_INFO_FILE_NAME = 'time.info'
    _KPTS_FILE_NAME = 'kpts'
    _QPTS_FILE_NAME = 'qpts'
    _PLOT_INP_FILE_NAME = 'plot_inp'
    _MIX_HISTORY_FILE_NAME = 'mixing_history*'
    _POT_FILE_NAME = 'pot*'
    _POT1_FILE_NAME = 'pottot'
    _POT2_FILE_NAME = 'potcoul'
    _STRUCTURE_FILE_NAME = 'struct.xcf'
    _STARS_FILE_NAME = 'stars'
    _WKF2_FILE_NAME = 'wkf2'
    _CDN_HDF5_FILE_NAME = 'cdn.hdf'
    _CDN_LAST_HDF5_FILE_NAME = 'cdn_last.hdf'

    # special out files
    _DOS_FILE_NAME = 'DOS.*'
    _DOSINP_FILE_NAME = 'dosinp'
    _BAND_GNU_FILE_NAME = 'band.gnu'
    _BAND_FILE_NAME = 'bands.*'

    # helper files
    _FLEUR_WARN_ONLY_INFO_FILE_NAME = 'FLEUR_WARN_ONLY'
    _JUDFT_WARN_ONLY_INFO_FILE_NAME = 'JUDFT_WARN_ONLY'
    _QFIX_FILE_NAME = 'qfix'
    _USAGE_FILE_NAME = 'usage.json'

    # relax (geometry optimization) files
    _RELAX_FILE_NAME = 'relax.xml'

    # jij files
    _JENERG_FILE_NAME = 'jenerg'
    _MCINP_FILE_NAME = 'MCinp'
    _QPTSINFO_FILE_NAME = 'qptsinfo'
    _SHELL_FILE_NAME = 'shells'
    _JCONST_FILE_NAME = 'jconst'

    # files for lda+U
    _NMMPMAT_FILE_NAME = 'n_mmp_mat'
    _NMMPMAT_HDF5_FILE_NAME = 'n_mmp_mat_out'

    # files for hybrid functionals
    _COULOMB1_FILE_NAME = 'coulomb1'
    _MIXBAS_FILE_NAME = 'mixbas'
    _CMT_FIlE_NAME = 'cmt'
    _CZ_FILE_NAME = 'cz'
    _OLAP_FILE_NAME = 'olap'
    _VR0_FILE_NAME = 'vr0'

    # files non-collinear calculation
    _RHOMAT_INP_FILE_NAME = 'rhomat_inp'
    _RHOMAT_OUT_FILE_NAME = 'rhomat_out'
    _CDN_FILE_NAME = 'cdn'
    _DIROFMAG_FILE_NAME = 'dirofmag'

    # files for Wannier 90
    _W90KPTS_FILE_NAME = 'w90kpts'
    _PROJ_FILE_NAME = 'proj'
    _WANN_INP_FILE_NAME = 'wann_inp'
    _BKPTS_FILE_NAME = 'bkpts'
    _WFMMN_FILE_NAME = 'WF*.mmn'
    _WFAMN_FILE_NAME = 'WF*.amn'
    _WFWIN_FILE_NAME = 'WF*.win'
    _WFWOUT_FILE_NAME = 'WF*.wout'
    _UNK_FILE_NAME = 'UNK*'
    _KPTSMAP_FILE_NAME = 'kptsmap'
    _PROJGEN_INP_FILE_NAME = 'projgen_inp'
    _IONS_FILE_NAME = 'IONS'
    _POLARIZATION_OUT_FILE_NAME = 'polarization_out'
    _HOPPING_FILE_NAME = 'hopping.*'
    _WF1HSOMTX_FILE_NAME = 'WF1.hsomtx'
    _RSSOCMAT_FILE_NAME = 'rssocmat.1'
    _RSNABLA_FILE_NAME = 'rsnabla.*'
    _WFNABL_FILE_NAME = 'WF*.nabl'

    # copy file lists. I rather don not like this.
    # Might gives rise to a lot of possible errors, if files or not there,
    # or Fleur did not created same, or at some point they will not be
    # deleted remotely.

    # Policy
    # we store everything needed for a further run in the local repository
    # (inp.xml, cdn1), also all important results files.
    # these will ALWAYS be copied from the local repository to the maschine
    # If a parent calculation exists, other files will be copied remotely
    #######

    # all possible files first chargedensity
    _copy_filelist1 = [
        _INP_FILE_NAME, _ENPARA_FILE_NAME, _SYMOUT_FILE_NAME, _CDN1_FILE_NAME, _KPTS_FILE_NAME, _STARS_FILE_NAME,
        _WKF2_FILE_NAME
    ]

    # after inpgen, before first chargedensity
    _copy_filelist_inpgen = [_INPXML_FILE_NAME]

    # for after fleur SCF [name, destination_name]
    _copy_scf_noinp = [[_CDN1_FILE_NAME, _CDN1_FILE_NAME]]

    _copy_scf_noinp_hdf = [[_CDN_LAST_HDF5_FILE_NAME, _CDN_HDF5_FILE_NAME]]

    _copy_scf = [[_CDN1_FILE_NAME, _CDN1_FILE_NAME], [_INPXML_FILE_NAME, _INPXML_FILE_NAME]]

    _copy_scf_hdf = [[_CDN_LAST_HDF5_FILE_NAME, _CDN_HDF5_FILE_NAME], [_INPXML_FILE_NAME, _INPXML_FILE_NAME]]

    _copy_filelist_scf_remote = [_MIX_HISTORY_FILE_NAME]

    _copy_filelist3 = [
        _INP_FILE_NAME, _ENPARA_FILE_NAME, _SYMOUT_FILE_NAME, _CDN1_FILE_NAME, _KPTS_FILE_NAME, _STARS_FILE_NAME,
        _WKF2_FILE_NAME, _MIX_HISTORY_FILE_NAME, _OUT_FILE_NAME, _POT_FILE_NAME
    ]

    _copy_scf_ldau_nohdf = [[_CDN1_FILE_NAME, _CDN1_FILE_NAME], [_INPXML_FILE_NAME, _INPXML_FILE_NAME],
                            [_NMMPMAT_FILE_NAME, _NMMPMAT_FILE_NAME]]

    _copy_scf_ldau_noinp_nohdf = [[_CDN1_FILE_NAME, _CDN1_FILE_NAME], [_NMMPMAT_FILE_NAME, _NMMPMAT_FILE_NAME]]

    # files need for rerun
    _copy_filelist_dos = [_INPXML_FILE_NAME, _CDN1_FILE_NAME]

    _copy_filelist_band = [_INPXML_FILE_NAME, _POT_FILE_NAME, _CDN1_FILE_NAME]

    _copy_filelist_hybrid = []
    _copy_filelist_jij = []

    # possible settings_dict keys
    _settings_keys = [
        'additional_retrieve_list', 'remove_from_retrieve_list', 'additional_remotecopy_list',
        'remove_from_remotecopy_list', 'cmdline'
    ]
    # possible modes?
    _fleur_modes = ['band', 'dos', 'forces', 'chargeDen', 'latticeCo', 'scf', 'force_theorem', 'gw', 'ldau']

    @classmethod
    def define(cls, spec):
        super().define(spec)

        # spec.input('metadata.options.input_filename', valid_type=six.string_types,
        #            default=cls._INPXML_FILE_NAME)
        spec.input('metadata.options.output_filename', valid_type=six.string_types, default=cls._OUTXML_FILE_NAME)
        spec.input('metadata.options.use_kpoints', valid_type=type(True), default=cls._use_kpoints)

        # inputs
        spec.input('fleurinpdata',
                   valid_type=FleurinpData,
                   required=False,
                   help='Use a FleruinpData node that specifies the input parameters'
                   'usually copy from the parent calculation, basically makes'
                   'the inp.xml file visible in the db and makes sure it has '
                   'the files needed.')
        spec.input('parent_folder',
                   valid_type=RemoteData,
                   required=False,
                   help='Use a remote or local repository folder as parent folder '
                   '(also for restarts and similar). It should contain all the '
                   'needed files for a Fleur calc, only edited files should be '
                   'uploaded from the repository.')
        spec.input('settings',
                   valid_type=Dict,
                   required=False,
                   help='This parameter data node is used to specify for some '
                   'advanced features how the plugin behaves. You can add files'
                   'the retrieve list, or add command line switches, '
                   'for all available features here check the documentation.')

        # parser
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default='fleur.fleurparser')

        # declare outputs of the calculation
        spec.output('output_parameters', valid_type=Dict, required=False)
        spec.output('output_params_complex', valid_type=Dict, required=False)
        spec.output('relax_parameters', valid_type=Dict, required=False)
        spec.output('error_params', valid_type=Dict, required=False)
        spec.default_output_node = 'output_parameters'

        # exit codes
        spec.exit_code(300, 'ERROR_NO_RETRIEVED_FOLDER', message='No retrieved folder found.')
        spec.exit_code(301, 'ERROR_OPENING_OUTPUTS', message='One of the output files can not be opened.')
        spec.exit_code(302, 'ERROR_FLEUR_CALC_FAILED', message='FLEUR calculation failed for unknown reason.')
        spec.exit_code(303, 'ERROR_NO_OUTXML', message='XML output file was not found.')
        spec.exit_code(304, 'ERROR_XMLOUT_PARSING_FAILED', message='Parsing of XML output file failed.')
        spec.exit_code(305, 'ERROR_RELAX_PARSING_FAILED', message='Parsing of relax XML output file failed.')
        spec.exit_code(310, 'ERROR_NOT_ENOUGH_MEMORY', message='FLEUR calculation failed due to lack of memory.')
        spec.exit_code(311,
                       'ERROR_VACUUM_SPILL_RELAX',
                       message='FLEUR calculation failed because an atom spilled to the'
                       'vacuum during relaxation')
        spec.exit_code(312, 'ERROR_MT_RADII', message='FLEUR calculation failed due to MT overlap.')
        spec.exit_code(313, 'ERROR_MT_RADII_RELAX', message='Overlapping MT-spheres during relaxation.')
        spec.exit_code(314, 'ERROR_DROP_CDN', message='Problem with cdn is suspected. Consider removing cdn')
        spec.exit_code(315,
                       'ERROR_INVALID_ELEMENTS_MMPMAT',
                       message='The LDA+U density matrix contains invalid elements.')
        spec.exit_code(316, 'ERROR_TIME_LIMIT', message='Calculation failed due to time limits.')

    @classproperty
    def _get_output_folder(self):
        return './'

    def prepare_for_submission(self, folder):
        """
        This is the routine to be called when you make a FLEUR calculation.
        This routine checks the inputs and modifies copy lists accordingly.
        The standard files to be copied are given here.

        :param folder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []
        mode_retrieved_filelist = []
        filelist_tocopy_remote = []
        settings_dict = {}

        has_fleurinp = False
        has_parent = False
        fleurinpgen = False
        copy_remotely = True
        with_hdf5 = False

        code = self.inputs.code

        codesdesc = code.description
        # TODO: ggf also check settings
        # In code description we write with what libs the code was compiled
        # we look for certain keywords in the description
        # also ggf, to be back comportable, the plugin should know the version number
        if codesdesc is not None:
            if 'hdf5' in codesdesc:
                with_hdf5 = True
            elif 'Hdf5' in codesdesc:
                with_hdf5 = True
            elif 'HDF5' in codesdesc:
                with_hdf5 = True
            else:
                with_hdf5 = False
        # a Fleur calc can be created from a fleurinpData alone
        # (then no parent is needed) all files are in the repo, but usually it is
        # a child of a inpgen calc or an other fleur calc (some or all files are
        # in a remote source). if the User has not changed something, the
        # calculation does not need theoretical a new FleurinpData it could use
        # the one from the parent, but the plug-in desgin is in a way that it has
        # to be there and it just copies files if changes occurred..

        if 'fleurinpdata' in self.inputs:
            fleurinp = self.inputs.fleurinpdata
        else:
            fleurinp = None

        if fleurinp is None:
            has_fleurinp = False
        else:
            has_fleurinp = True

        if 'parent_folder' in self.inputs:
            parent_calc_folder = self.inputs.parent_folder
        else:
            parent_calc_folder = None

        if parent_calc_folder is None:
            has_parent = False
            if not has_fleurinp:
                raise InputValidationError('No parent calculation found and no fleurinp data '
                                           'given, need either one or both for a '
                                           "'fleurcalculation'.")
        else:
            # extract parent calculation
            parent_calcs = parent_calc_folder.get_incoming(node_class=CalcJob).all()
            n_parents = len(parent_calcs)
            if n_parents != 1:
                raise UniquenessError('Input RemoteData is child of {} '
                                      'calculation{}, while it should have a single parent'
                                      ''.format(n_parents, '' if n_parents == 0 else 's'))
            parent_calc = parent_calcs[0].node
            parent_calc_class = parent_calc.process_class
            has_parent = True

            # check that it is a valid parent
            # self._check_valid_parent(parent_calc)

            # if inpgen calc do
            # check if folder from db given, or get folder from rep.
            # Parent calc does not has to be on the same computer.

            if parent_calc_class is FleurCalculation:
                new_comp = self.node.computer
                old_comp = parent_calc.computer
                if new_comp.uuid != old_comp.uuid:
                    # don't copy files, copy files locally
                    copy_remotely = False
            elif parent_calc_class is FleurinputgenCalculation:
                fleurinpgen = True
                new_comp = self.node.computer
                old_comp = parent_calc.computer
                if new_comp.uuid != old_comp.uuid:
                    # don't copy files, copy files locally
                    copy_remotely = False
            else:
                raise InputValidationError("parent_calc, must be either an 'inpgen calculation' or"
                                           " a 'fleur calculation'.")

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
                self.logger.warning(
                    'settings dict key %s for Fleur calculation'
                    'not recognized, only %s are allowed.'
                    '', key, str(self._settings_keys))

        # TODO: Detailed check of FleurinpData
        # if certain files are there in fleurinpData
        # from where to copy

        # file copy stuff TODO check in fleur input
        if has_fleurinp:
            # add files belonging to fleurinp into local_copy_list
            allfiles = fleurinp.files
            for file1 in allfiles:
                local_copy_list.append((fleurinp.uuid, file1, file1))
            modes = fleurinp.get_fleur_modes()

            # add files to mode_retrieved_filelist
            if modes['band']:
                mode_retrieved_filelist.append(self._BAND_FILE_NAME)
                mode_retrieved_filelist.append(self._BAND_GNU_FILE_NAME)
            if modes['dos']:
                mode_retrieved_filelist.append(self._DOS_FILE_NAME)
            if modes['forces']:
                # if l_f="T" retrieve relax.xml
                mode_retrieved_filelist.append(self._RELAX_FILE_NAME)
            if modes['ldau']:
                if with_hdf5:
                    mode_retrieved_filelist.append(self._NMMPMAT_HDF5_FILE_NAME)
                else:
                    mode_retrieved_filelist.append(self._NMMPMAT_FILE_NAME)
            if modes['force_theorem']:
                if 'remove_from_retrieve_list' not in settings_dict:
                    settings_dict['remove_from_retrieve_list'] = []
                if with_hdf5:
                    settings_dict['remove_from_retrieve_list'].append(self._CDN_LAST_HDF5_FILE_NAME)
                else:
                    settings_dict['remove_from_retrieve_list'].append(self._CDN1_FILE_NAME)

            # if noco, ldau, gw...
            # TODO: check from where it was copied, and copy files of its parent
            # if needed

        if has_parent:
            # copy necessary files
            # TODO: check first if file exist and throw a warning if not
            outfolder_uuid = parent_calc.outputs.retrieved.uuid
            self.logger.info('out folder path %s', outfolder_uuid)

            outfolder_filenames = [x.name for x in parent_calc.outputs.retrieved.list_objects()]
            has_nmmpmat_file = self._NMMPMAT_FILE_NAME in outfolder_filenames
            if (self._NMMPMAT_FILE_NAME in outfolder_filenames or \
                self._NMMPMAT_HDF5_FILE_NAME in outfolder_filenames):
                if has_fleurinp:
                    if 'n_mmp_mat' in fleurinp.files:
                        self.logger.warning('Ingnoring n_mmp_mat from fleurinp. '
                                            'There is already an n_mmp_mat file '
                                            'for the parent calculation')
                        local_copy_list.remove((fleurinp.uuid, 'n_mmp_mat', 'n_mmp_mat'))

            if fleurinpgen and (not has_fleurinp):
                for file1 in self._copy_filelist_inpgen:
                    local_copy_list.append((outfolder_uuid, os.path.join(file1), os.path.join(file1)))
            elif not fleurinpgen and (not has_fleurinp):  # fleurCalc
                # need to copy inp.xml from the parent calc
                if with_hdf5:
                    copylist = self._copy_scf_hdf
                elif has_nmmpmat_file:
                    copylist = self._copy_scf_ldau_nohdf
                else:
                    copylist = self._copy_scf
                for file1 in copylist:
                    local_copy_list.append((outfolder_uuid, file1[0], file1[1]))
                # TODO: get inp.xml from parent fleurinpdata; otherwise it will be doubled in rep
            elif fleurinpgen and has_fleurinp:
                # everything is taken care of
                pass
            elif not fleurinpgen and has_fleurinp:
                # inp.xml will be copied from fleurinp
                if with_hdf5:
                    copylist = self._copy_scf_noinp_hdf
                elif has_nmmpmat_file:
                    copylist = self._copy_scf_ldau_noinp_nohdf
                else:
                    copylist = self._copy_scf_noinp
                for file1 in copylist:
                    local_copy_list.append((outfolder_uuid, file1[0], file1[1]))

            # TODO: not on same computer -> copy needed files from repository
            # if they are not there throw an error
            if copy_remotely:  # on same computer.
                # from fleurmodes
                if modes['dos']:
                    pass
                elif modes['band']:
                    pass
                else:
                    filelist_tocopy_remote = filelist_tocopy_remote + \
                        self._copy_filelist_scf_remote
                # from settings, user specified
                # TODO: check if list?
                for file1 in settings_dict.get('additional_remotecopy_list', []):
                    filelist_tocopy_remote.append(file1)

                for file1 in settings_dict.get('remove_from_remotecopy_list', []):
                    if file1 in filelist_tocopy_remote:
                        filelist_tocopy_remote.remove(file1)

                for file1 in filelist_tocopy_remote:
                    remote_copy_list.append(
                        (parent_calc_folder.computer.uuid, os.path.join(parent_calc_folder.get_remote_path(),
                                                                        file1), self._get_output_folder))

                self.logger.info('remote copy file list %s', str(remote_copy_list))

        # create a JUDFT_WARN_ONLY file in the calculation folder
        with io.StringIO(u'/n') as handle:
            warn_only_filename = self._JUDFT_WARN_ONLY_INFO_FILE_NAME
            folder.create_file_from_filelike(handle, filename=warn_only_filename, mode='w')

        ########## MAKE CALCINFO ###########

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid
        # Empty command line by default
        #cmdline_params = settings_dict.pop('CMDLINE', [])
        # calcinfo.cmdline_params = (list(cmdline_params)
        #                           + ["-in", self._INPUT_FILE_NAME])

        self.logger.info('local copy file list %s', str(local_copy_list))

        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve by default the output file and the xml file
        retrieve_list = []
        retrieve_list.append(self._OUTXML_FILE_NAME)
        retrieve_list.append(self._INPXML_FILE_NAME)
        retrieve_list.append(self._SHELLOUTPUT_FILE_NAME)
        retrieve_list.append(self._ERROR_FILE_NAME)
        retrieve_list.append(self._USAGE_FILE_NAME)
        # retrieve_list.append(self._TIME_INFO_FILE_NAME)
        # retrieve_list.append(self._OUT_FILE_NAME)
        if with_hdf5:
            retrieve_list.append(self._CDN_LAST_HDF5_FILE_NAME)
        else:
            retrieve_list.append(self._CDN1_FILE_NAME)

        for mode_file in mode_retrieved_filelist:
            retrieve_list.append(mode_file)
        self.logger.info('retrieve_list: %s', str(retrieve_list))

        # user specific retrieve
        add_retrieve = settings_dict.get('additional_retrieve_list', [])
        self.logger.info('add_retrieve: %s', str(add_retrieve))
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
        walltime_sec = self.node.get_attribute('max_wallclock_seconds')
        cmdline_params = []  # , "-wtime", "{}".format(walltime_sec)]"-xml"

        cmdline_params.append('-minimalOutput')

        if with_hdf5:
            cmdline_params.append('-last_extra')
            cmdline_params.append('-no_send')

        if walltime_sec:
            walltime_min = int(max(1, walltime_sec / 60))
            cmdline_params.append('-wtime')
            cmdline_params.append('{}'.format(int(walltime_min)))

        # user specific commandline_options
        for command in settings_dict.get('cmdline', []):
            cmdline_params.append(command)

        codeinfo.cmdline_params = list(cmdline_params)
        # + ["<", self._INPXML_FILE_NAME,
        # ">", self._SHELLOUTPUT_FILE_NAME, "2>&1"]
        codeinfo.code_uuid = code.uuid
        codeinfo.withmpi = self.node.get_attribute('max_wallclock_seconds')
        codeinfo.stdin_name = None  # self._INPUT_FILE_NAME
        codeinfo.stdout_name = self._SHELLOUTPUT_FILE_NAME
        #codeinfo.join_files = True
        codeinfo.stderr_name = self._ERROR_FILE_NAME

        calcinfo.codes_info = [codeinfo]

        return calcinfo
