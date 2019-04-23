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
Input plug-in for a FLEUR ciculation. fleur.x
"""
# TODO:
# polishing
# think about exception. warning policy.
# TODO maybe allow only single file names not *
# TODO maybe check the settings key values, make a list of all fleur files?
from __future__ import absolute_import
from __future__ import print_function
import os
import six
#from lxml import etree
#from lxml.etree import XMLSyntaxError

from aiida.engine import CalcJob
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.orm import Dict
from aiida.orm import RemoteData
from aiida_fleur.data.fleurinp import FleurinpData
from aiida.common.utils import classproperty
from aiida.common.exceptions import InputValidationError, ValidationError
from aiida.common.exceptions import UniquenessError



class FleurCalculation(CalcJob):
    """
    Main DFT code of the FLEUR code
    For more information about the FLEUR-code family, go to http://www.flapw.de/
    """

    ######### Only this should be to be maintained! #########

    # should a kpt node be used or fleur generate the mesh?
    _DEFAULT_use_kpoints = False
    _DEFAULT_INPXML_FILE_NAME = 'inp.xml'

    # Default input and output files
    _DEFAULT_INPUT_FILE = 'inp.xml'#_DEFAULT_set_INPXML_FILE_PATH()
    #_DEFAULT_FLEURINPDATA_FOLDER
    #fleurinp.get_file_abs_path(_DEFAULT_INPXML_FILE_NAME)
    #'inp.xml' # this has to change the file is under FleurinpData
    _DEFAULT_OUTPUT_FILE = 'out.xml'

    # Name of all files in FLEUR
    # TODO think also to oursource this in a FleurCalc structure, and add
    # as info when what file has to be copied

    # these will be shown in AiiDA
    _DEFAULT_OUTPUT_FILE_NAME = 'aiida.out' # Shell output
    _DEFAULT_INPUT_FILE_NAME = 'inp.xml'
    #fleur file names:

    # needed for calc

    _DEFAULT_OUTXML_FILE_NAME = 'out.xml'
    _DEFAULT_INP_FILE_NAME = 'inp'
    _DEFAULT_ENPARA_FILE_NAME = 'enpara'
    _DEFAULT_SYMOUT_FILE_NAME = 'sym.out'
    _DEFAULT_CDN1_FILE_NAME = 'cdn1'
    _DEFAULT_SHELLOUTPUT_FILE_NAME = 'shell.out'
    _DEFAULT_ERROR_FILE_NAME = 'out.error'
     # other
    _DEFAULT_OUT_FILE_NAME = 'out'
    _DEFAULT_CDNC_FILE_NAME = 'cdnc' # core charge density
    _DEFAULT_TIME_INFO_FILE_NAME = 'time.info'
    _DEFAULT_KPTS_FILE_NAME = 'kpts'
    _DEFAULT_QPTS_FILE_NAME = 'qpts'
    _DEFAULT_PLOT_INP_FILE_NAME = 'plot_inp'
    _DEFAULT_BROYD_FILE_NAME = 'broyd*'
    _DEFAULT_POT_FILE_NAME = 'pot*'
    _DEFAULT_POT1_FILE_NAME = 'pottot'
    _DEFAULT_POT2_FILE_NAME = 'potcoul'
    _DEFAULT_STRUCTURE_FILE_NAME = 'struct.xcf'
    _DEFAULT_STARS_FILE_NAME = 'stars'
    _DEFAULT_WKF2_FILE_NAME = 'wkf2'
    _DEFAULT_CDN_HDF5_FILE_NAME = 'cdn.hdf'
    _DEFAULT_CDN_LAST_HDF5_FILE_NAME = 'cdn_last.hdf'


    # special out files
    _DEFAULT_DOS_FILE_NAME = 'DOS.*'
    _DEFAULT_DOSINP_FILE_NAME = 'dosinp'
    _DEFAULT_BAND_GNU_FILE_NAME = 'band.gnu'
    _DEFAULT_BAND_FILE_NAME = 'bands.*'
    _DEFAULT_NEW_XMlINP_FILE_NAME = 'inp_new.xml'

    # helper files
    _DEFAULT_FLEUR_WARN_ONLY_INFO_FILE_NAME = 'FLEUR_WARN_ONLY'
    _DEFAULT_JUDFT_WARN_ONLY_INFO_FILE_NAME = 'JUDFT_WARN_ONLY'
    _DEFAULT_QFIX_FILE_NAME = 'qfix'


    # forces and relaxation files
    _DEFAULT_FORCE_FILE_NAME = 'forces.dat'

    # jij files
    _DEFAULT_JENERG_FILE_NAME = 'jenerg'
    _DEFAULT_MCINP_FILE_NAME = 'MCinp'
    _DEFAULT_QPTSINFO_FILE_NAME = 'qptsinfo'
    _DEFAULT_SHELL_FILE_NAME = 'shells'
    _DEFAULT_JCONST_FILE_NAME = 'jconst'

    # files for lda+U
    _DEFAULT_NMMPMAT_FILE_NAME = 'n_mmp_mat'

    # files for hybrid functionals
    _DEFAULT_COULOMB1_FILE_NAME = 'coulomb1'
    _DEFAULT_MIXBAS_FILE_NAME = 'mixbas'
    _DEFAULT_CMT_FIlE_NAME = 'cmt'
    _DEFAULT_CZ_FILE_NAME = 'cz'
    _DEFAULT_OLAP_FILE_NAME = 'olap'
    _DEFAULT_VR0_FILE_NAME = 'vr0'

    # files non-collinear calculation
    _DEFAULT_RHOMAT_INP_FILE_NAME = 'rhomat_inp'
    _DEFAULT_RHOMAT_OUT_FILE_NAME = 'rhomat_out'
    _DEFAULT_CDN_FILE_NAME = 'cdn'
    _DEFAULT_DIROFMAG_FILE_NAME = 'dirofmag'

    # files for Wannier 90
    _DEFAULT_W90KPTS_FILE_NAME = 'w90kpts'
    _DEFAULT_PROJ_FILE_NAME = 'proj'
    _DEFAULT_WANN_INP_FILE_NAME = 'wann_inp'
    _DEFAULT_BKPTS_FILE_NAME = 'bkpts'
    _DEFAULT_WFMMN_FILE_NAME = 'WF*.mmn'
    _DEFAULT_WFAMN_FILE_NAME = 'WF*.amn'
    _DEFAULT_WFWIN_FILE_NAME = 'WF*.win'
    _DEFAULT_WFWOUT_FILE_NAME = 'WF*.wout'
    _DEFAULT_UNK_FILE_NAME = 'UNK*'
    _DEFAULT_KPTSMAP_FILE_NAME = 'kptsmap'
    _DEFAULT_PROJGEN_INP_FILE_NAME = 'projgen_inp'
    _DEFAULT_IONS_FILE_NAME = 'IONS'
    _DEFAULT_POLARIZATION_OUT_FILE_NAME = 'polarization_out'
    _DEFAULT_HOPPING_FILE_NAME = 'hopping.*'
    _DEFAULT_WF1HSOMTX_FILE_NAME = 'WF1.hsomtx'
    _DEFAULT_RSSOCMAT_FILE_NAME = 'rssocmat.1'
    _DEFAULT_RSNABLA_FILE_NAME = 'rsnabla.*'
    _DEFAULT_WFNABL_FILE_NAME = 'WF*.nabl'

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
    _DEFAULT_copy_filelist1 = [_DEFAULT_INP_FILE_NAME,
                            _DEFAULT_ENPARA_FILE_NAME,
                            _DEFAULT_SYMOUT_FILE_NAME,
                            _DEFAULT_CDN1_FILE_NAME,
                            _DEFAULT_KPTS_FILE_NAME,
                            _DEFAULT_STARS_FILE_NAME,
                            _DEFAULT_WKF2_FILE_NAME]

    #after inpgen, before first chargedensity
    _DEFAULT_copy_filelist_inpgen = [_DEFAULT_INPXML_FILE_NAME]

    #for after fleur SCF [name, detination_name]
    _DEFAULT_copy_filelist_scf1 = [[_DEFAULT_CDN1_FILE_NAME, _DEFAULT_CDN1_FILE_NAME]]
    _DEFAULT_copy_filelist_scf2 = [[_DEFAULT_CDN_LAST_HDF5_FILE_NAME, _DEFAULT_CDN_HDF5_FILE_NAME]]
    #_DEFAULT_INPXML_FILE_NAME, comes from fleurinpdata
    _DEFAULT_copy_filelist_scf = [[_DEFAULT_CDN1_FILE_NAME, _DEFAULT_CDN1_FILE_NAME],
                               [_DEFAULT_INPXML_FILE_NAME, _DEFAULT_INPXML_FILE_NAME]]
    _DEFAULT_copy_filelist_scf2_1 = [[_DEFAULT_CDN_LAST_HDF5_FILE_NAME, _DEFAULT_CDN_HDF5_FILE_NAME],
                               [_DEFAULT_INPXML_FILE_NAME, _DEFAULT_INPXML_FILE_NAME]]
    _DEFAULT_copy_filelist_scf_remote = [_DEFAULT_BROYD_FILE_NAME]
    _DEFAULT_copy_filelist3 = [_DEFAULT_INP_FILE_NAME,
                            _DEFAULT_ENPARA_FILE_NAME,
                            _DEFAULT_SYMOUT_FILE_NAME,
                            _DEFAULT_CDN1_FILE_NAME,
                            _DEFAULT_KPTS_FILE_NAME,
                            _DEFAULT_STARS_FILE_NAME,
                            _DEFAULT_WKF2_FILE_NAME,
                            _DEFAULT_BROYD_FILE_NAME,
                            _DEFAULT_OUT_FILE_NAME,
                            _DEFAULT_POT_FILE_NAME]

    #files need for rerun
    _DEFAULT_copy_filelist_dos = [_DEFAULT_INPXML_FILE_NAME,
                               _DEFAULT_CDN1_FILE_NAME]
    _DEFAULT_copy_filelist_band = [_DEFAULT_INPXML_FILE_NAME,
                                _DEFAULT_POT_FILE_NAME,
                                _DEFAULT_CDN1_FILE_NAME]


    _DEFAULT_copy_filelist_hybrid = []
    _DEFAULT_copy_filelist_jij = []

    #possible settings_dict keys
    _DEFAULT_settings_keys = ['additional_retrieve_list', 'remove_from_retrieve_list',
                           'additional_remotecopy_list', 'remove_from_remotecopy_list'
                           'cmdline']
    #possible modes?
    _DEFAULT_fleur_modes = ['band', 'dos', 'forces', 'chargeDen',
                         'latticeCo', 'scf']
#_DEFAULT_INPUT_FILE = 'inp.xml'
    
    @classmethod
    def define(cls, spec):
        super(FleurCalculation, cls).define(spec)
        
        spec.input('metadata.options.use_kpoints', valid_type=type(True), default=cls._DEFAULT_use_kpoints)
        spec.input('metadata.options.inpxml_file_name', valid_type=six.string_types, default=cls._DEFAULT_INPXML_FILE_NAME)
        
        #default input and output files
        spec.input('metadata.options.default_input_file', valid_type=six.string_types, default=cls._DEFAULT_INPUT_FILE)
        spec.input('metadata.options.output_file', valid_type=six.string_types, default=cls._DEFAULT_OUTPUT_FILE)
        
        #these will be shown in AiiDA
        spec.input('metadata.options.output_file_name', valid_type=six.string_types, default=cls._DEFAULT_OUTPUT_FILE_NAME)
        spec.input('metadata.options.input_file_name', valid_type=six.string_types, default=cls._DEFAULT_INPUT_FILE_NAME)
        
        #needed for calc
        spec.input('metadata.options.outxml_file_name', valid_type=six.string_types, default=cls._DEFAULT_OUTXML_FILE_NAME)
        spec.input('metadata.options.inp_file_name', valid_type=six.string_types, default=cls._DEFAULT_INP_FILE_NAME)
        spec.input('metadata.options.enpara_file_name', valid_type=six.string_types, default=cls._DEFAULT_ENPARA_FILE_NAME)
        spec.input('metadata.options.symout_file_name', valid_type=six.string_types, default=cls._DEFAULT_SYMOUT_FILE_NAME)
        spec.input('metadata.options.cdn1_file_name', valid_type=six.string_types, default=cls._DEFAULT_CDN1_FILE_NAME)
        spec.input('metadata.options.shelloutput_file_name', valid_type=six.string_types, default=cls._DEFAULT_SHELLOUTPUT_FILE_NAME)
        spec.input('metadata.options.error_file_name', valid_type=six.string_types, default=cls._DEFAULT_ERROR_FILE_NAME)
        #other
        spec.input('metadata.options.out_file_name', valid_type=six.string_types, default=cls._DEFAULT_OUT_FILE_NAME)
        spec.input('metadata.options.cdnc_file_name', valid_type=six.string_types, default=cls._DEFAULT_CDNC_FILE_NAME)
        spec.input('metadata.options.time_info_file_name', valid_type=six.string_types, default=cls._DEFAULT_TIME_INFO_FILE_NAME)
        spec.input('metadata.options.kpts_file_name', valid_type=six.string_types, default=cls._DEFAULT_KPTS_FILE_NAME)
        spec.input('metadata.options.qpts_file_name', valid_type=six.string_types, default=cls._DEFAULT_QPTS_FILE_NAME)
        spec.input('metadata.options.plot_inp_file_name', valid_type=six.string_types, default=cls._DEFAULT_PLOT_INP_FILE_NAME)
        spec.input('metadata.options.broyd_file_name', valid_type=six.string_types, default=cls._DEFAULT_BROYD_FILE_NAME)
        spec.input('metadata.options.pot_file_name', valid_type=six.string_types, default=cls._DEFAULT_POT_FILE_NAME)
        spec.input('metadata.options.pot1_file_name', valid_type=six.string_types, default=cls._DEFAULT_POT1_FILE_NAME)
        spec.input('metadata.options.pot2_file_name', valid_type=six.string_types, default=cls._DEFAULT_POT2_FILE_NAME)
        spec.input('metadata.options.structure_file_name', valid_type=six.string_types, default=cls._DEFAULT_STRUCTURE_FILE_NAME)
        spec.input('metadata.options.stars_file_name', valid_type=six.string_types, default=cls._DEFAULT_STARS_FILE_NAME)
        spec.input('metadata.options.wkf2_file_name', valid_type=six.string_types, default=cls._DEFAULT_WKF2_FILE_NAME)
        spec.input('metadata.options.cdn_hdf5_file_name', valid_type=six.string_types, default=cls._DEFAULT_CDN_HDF5_FILE_NAME)
        spec.input('metadata.options.cdn_last_hdf5_file_name', valid_type=six.string_types, default=cls._DEFAULT_CDN_LAST_HDF5_FILE_NAME)
        
        #special out files
        spec.input('metadata.options.dos_file_name', valid_type=six.string_types, default=cls._DEFAULT_DOS_FILE_NAME)
        spec.input('metadata.options.dosinp_file_name', valid_type=six.string_types, default=cls._DEFAULT_DOSINP_FILE_NAME)
        spec.input('metadata.options.band_gnu_file_name', valid_type=six.string_types, default=cls._DEFAULT_BAND_GNU_FILE_NAME)
        spec.input('metadata.options.band_file_name', valid_type=six.string_types, default=cls._DEFAULT_BAND_FILE_NAME)
        spec.input('metadata.options.new_xmlinp_file_name', valid_type=six.string_types, default=cls._DEFAULT_NEW_XMlINP_FILE_NAME)
        
        #helper files
        spec.input('metadata.options.fleur_warn_only_info_file_name', valid_type=six.string_types, default=cls._DEFAULT_FLEUR_WARN_ONLY_INFO_FILE_NAME)
        spec.input('metadata.options.judft_warn_only_info_file_name', valid_type=six.string_types, default=cls._DEFAULT_JUDFT_WARN_ONLY_INFO_FILE_NAME)
        spec.input('metadata.options.qfix_file_name', valid_type=six.string_types, default=cls._DEFAULT_QFIX_FILE_NAME)
        
        #forces and relaxation forces
        spec.input('metadata.options.force_file_name', valid_type=six.string_types, default=cls._DEFAULT_FORCE_FILE_NAME)
        
        #jij files
        spec.input('metadata.options.default_jenerg_file_name', valid_type=six.string_types, default=cls._DEFAULT_JENERG_FILE_NAME)
        spec.input('metadata.options.mcinp_file_name', valid_type=six.string_types, default=cls._DEFAULT_MCINP_FILE_NAME)
        spec.input('metadata.options.qptsinfo_file_name', valid_type=six.string_types, default=cls._DEFAULT_QPTSINFO_FILE_NAME)
        spec.input('metadata.options.shell_file_name', valid_type=six.string_types, default=cls._DEFAULT_SHELL_FILE_NAME)
        spec.input('metadata.options.jconst_file_name', valid_type=six.string_types, default=cls._DEFAULT_JCONST_FILE_NAME)
        
        #files for LDA+U
        spec.input('metadata.options.nmmpmat_file_name', valid_type=six.string_types, default=cls._DEFAULT_NMMPMAT_FILE_NAME)
        
        #files for hybrid functionals
        spec.input('metadata.options.coulomb1_file_name', valid_type=six.string_types, default=cls._DEFAULT_COULOMB1_FILE_NAME)
        spec.input('metadata.options.mixbas_file_name', valid_type=six.string_types, default=cls._DEFAULT_MIXBAS_FILE_NAME)
        spec.input('metadata.options.cmt_file_name', valid_type=six.string_types, default=cls._DEFAULT_CMT_FIlE_NAME)
        spec.input('metadata.options.cz_file_name', valid_type=six.string_types, default=cls._DEFAULT_CZ_FILE_NAME)
        spec.input('metadata.options.olap_file_name', valid_type=six.string_types, default=cls._DEFAULT_OLAP_FILE_NAME)
        spec.input('metadata.options.vr0_file_name', valid_type=six.string_types, default=cls._DEFAULT_VR0_FILE_NAME)
        
        #files non-collinear calculation
        spec.input('metadata.options.rhomat_inp_file_name', valid_type=six.string_types, default=cls._DEFAULT_RHOMAT_INP_FILE_NAME)
        spec.input('metadata.options.rhomat_out_file_name', valid_type=six.string_types, default=cls._DEFAULT_RHOMAT_OUT_FILE_NAME)
        spec.input('metadata.options.cdn_file_name', valid_type=six.string_types, default=cls._DEFAULT_CDN_FILE_NAME)
        spec.input('metadata.options.dirofmag_file_name', valid_type=six.string_types, default=cls._DEFAULT_DIROFMAG_FILE_NAME)
        
        #files for Wannier 90
        spec.input('metadata.options.w90kpts_file_name', valid_type=six.string_types, default=cls._DEFAULT_W90KPTS_FILE_NAME)
        spec.input('metadata.options.proj_file_name', valid_type=six.string_types, default=cls._DEFAULT_PROJ_FILE_NAME)
        spec.input('metadata.options.wann_inp_file_name', valid_type=six.string_types, default=cls._DEFAULT_WANN_INP_FILE_NAME)
        spec.input('metadata.options.bkpts_file_name', valid_type=six.string_types, default=cls._DEFAULT_BKPTS_FILE_NAME)
        spec.input('metadata.options.wfmmn_file_name', valid_type=six.string_types, default=cls._DEFAULT_WFMMN_FILE_NAME)
        spec.input('metadata.options.wfamn_file_name', valid_type=six.string_types, default=cls._DEFAULT_WFAMN_FILE_NAME)
        spec.input('metadata.options.wfwin_file_name', valid_type=six.string_types, default=cls._DEFAULT_WFWIN_FILE_NAME)
        spec.input('metadata.options.wfwout_file_name', valid_type=six.string_types, default=cls._DEFAULT_WFWOUT_FILE_NAME)
        spec.input('metadata.options.unk_file_name', valid_type=six.string_types, default=cls._DEFAULT_UNK_FILE_NAME)
        spec.input('metadata.options.kptsmap_file_name', valid_type=six.string_types, default=cls._DEFAULT_KPTSMAP_FILE_NAME)
        spec.input('metadata.options.projgen_inp_file_name', valid_type=six.string_types, default=cls._DEFAULT_PROJGEN_INP_FILE_NAME)
        spec.input('metadata.options.ions_file_name', valid_type=six.string_types, default=cls._DEFAULT_IONS_FILE_NAME)
        spec.input('metadata.options.polarization_out_file_name', valid_type=six.string_types, default=cls._DEFAULT_POLARIZATION_OUT_FILE_NAME)
        spec.input('metadata.options.hopping_file_name', valid_type=six.string_types, default=cls._DEFAULT_HOPPING_FILE_NAME)
        spec.input('metadata.options.wf1hsomtx_file_name', valid_type=six.string_types, default=cls._DEFAULT_WF1HSOMTX_FILE_NAME)
        spec.input('metadata.options.rssocmat_file_name', valid_type=six.string_types, default=cls._DEFAULT_RSSOCMAT_FILE_NAME)
        spec.input('metadata.options.rsnabla_file_name', valid_type=six.string_types, default=cls._DEFAULT_RSNABLA_FILE_NAME)
        spec.input('metadata.options.wfnabl_file_name', valid_type=six.string_types, default=cls._DEFAULT_WFNABL_FILE_NAME)
        
        #filelists
        spec.input('metadata.options.copy_filelist1', valid_type=list, default=cls._DEFAULT_copy_filelist1)
        spec.input('metadata.options.copy_filelist_inpgen', valid_type=list, default=cls._DEFAULT_copy_filelist_inpgen)
        
        spec.input('metadata.options.copy_filelist_scf1', valid_type=list, default=cls._DEFAULT_copy_filelist_scf1)
        spec.input('metadata.options.copy_filelist_scf2', valid_type=list, default=cls._DEFAULT_copy_filelist_scf2)
        spec.input('metadata.options.copy_filelist_scf', valid_type=list, default=cls._DEFAULT_copy_filelist_scf)
        spec.input('metadata.options.copy_filelist_scf2_1', valid_type=list, default=cls._DEFAULT_copy_filelist_scf2_1)
        spec.input('metadata.options.copy_filelist_scf_remote', valid_type=list, default=cls._DEFAULT_copy_filelist_scf_remote)
        spec.input('metadata.options.copy_filelist3', valid_type=list, default=cls._DEFAULT_copy_filelist3)
        spec.input('metadata.options.copy_filelist_dos', valid_type=list, default=cls._DEFAULT_copy_filelist_dos)
        spec.input('metadata.options.copy_filelist_band', valid_type=list, default=cls._DEFAULT_copy_filelist_band)
        spec.input('metadata.options.copy_filelist_hybrid', valid_type=list, default=cls._DEFAULT_copy_filelist_hybrid)
        spec.input('metadata.options.copy_filelist_jij', valid_type=list, default=cls._DEFAULT_copy_filelist_jij)
        spec.input('metadata.options.setting_keys', valid_type=list, default=cls._DEFAULT_settings_keys)
        spec.input('metadata.options.fleur_modes', valid_type=list, default=cls._DEFAULT_fleur_modes)
        
        #inputs transfered from _use_methods (pre 1.0.0b1)
        spec.input('fleurinpdata', valid_type=FleurinpData, required = False,
            help="Use a FleruinpData node that specifies the input parameters"
                    "usually copy from the parent calculation, basicly makes"
                    "the inp.xml file visible in the db and makes sure it has "
                    "the files needed.")
        spec.input('parent_folder', valid_type=RemoteData, required = False,
            help="Use a remote or local repository folder as parent folder "
                    "(also for restarts and similar). It should contain all the "
                    "needed files for a Fleur calc, only edited files should be "
                    "uploaded from the repository.")
        spec.input('settings', valid_type=Dict, required = False,
            help="This parameter data node is used to specify for some "
                    "advanced features how the plugin behaves. You can add files"
                    "the retrieve list, or add command line switches, "
                    "for all available features here check the documentation.")
        
        #parser
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default='fleur.fleurparser')
    
        # declare outputs of the calculation
        spec.output('output_parameters', valid_type=Dict, required=False)
        spec.output('output_params_complex', valid_type=Dict, required=False)
        spec.output('fleurinpData', valid_type=FleurinpData, required=False)
        
        #exit codes
        spec.exit_code(
            104, 'ERROR_WRONG_PARSER_INPUT', message='Parser class accepts FleurCalculation only.')
        spec.exit_code(
            105, 'ERROR_OPENING_OUTPUTS', message='One of output files can not be opened.')
        spec.exit_code(
            106, 'ERROR_NO_RETRIEVED_FOLDER', message='No retrieved folder found.')
        spec.exit_code(
            107, 'ERROR_FLEUR_CALC_FAILED', message='FLEUR calculation failed.')
        spec.exit_code(
            108, 'ERROR_NO_OUTXML', message='XML output file was not found.')
        spec.exit_code(
            109, 'ERROR_MISSING_RETRIEVED_FILES', message='Some required files were not retrieved.')
        spec.exit_code(
            110, 'ERROR_XMLOUT_PARSING_FAILED', message='Parsing of XML output file was not successfull.')
    

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
    def prepare_for_submission(self, tempfolder):
        """
        This is the routine to be called when you make a fleur calculation
        Here should be checked if all the files are there to run fleur.
        And input files (inp.xml) can be modified.

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """

        # TODO how to check if code compiled with HDF5?
        # Idea: in description of code can be written wirh what libs the code was compiled,
        # and we check in the description for certain keywords... if we have the code node...
        # also ggf, to be back comportable, the plugin should know the version number...

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
        with_hdf5 = False

        #since 1.0.0b inputs are checked automatically
        code = self.inputs.code

        codesdesc = code.description
        # TODO ggf also check settings
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
        #(then no parent is needed) all files are in the repo, but usually it is
        # a child of a inpgen calc or an other fleur calc (some or all files are
        # in a remote source). if the User has not changed something, the
        #calculation does not need theoretical a new FleurinpData it could use
        #the one from the parent, but the plug-in desgin is in a way that it has
        # to be there and it just copies files if changes occured..
        
        if 'fleurinpdata' in self.inputs:
            fleurinp = self.inputs.fleurinpdata
        else:
            fleurinp = None

        if fleurinp is None:
            #xml_inp_dict = {}
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
                raise InputValidationError(
                    "No parent calculation found and no fleurinp data "
                    "given, need either one or both for a "
                    "'fleurcalculation'.")
        else:
            # extract parent calculation
            #assume that RemoteFolder has a single parent
            parent_calcs = parent_calc_folder.get_incoming(node_class=CalcJob).all()
            n_parents = len(parent_calcs)
            if n_parents != 1:
                raise UniquenessError("Input RemoteData is child of {} "
                    "calculation{}, while it should have a single parent"
                    "".format(n_parents, "" if n_parents == 0 else "s"))
            parent_calc = parent_calcs[0].node
            parent_calc_class = parent_calc.process_class
            has_parent = True

            # check that it is a valid parent
            #self._check_valid_parent(parent_calc)


            # if inpgen calc do
            # check if folder from db given, or get folder from rep.
            # Parent calc does not has to be on the same computer.

            if parent_calc_class is FleurCalculation:
                new_comp = self.node.computer
                old_comp = parent_calc.computer
                if new_comp.uuid != old_comp.uuid:
                    #dont copy files, copy files localy
                    copy_remotely = False
                    #raise InputValidationError(
                    #    "FleurCalculation must be launched on the same computer"
                    #    " of the parent: {}".format(old_comp.get_name()))
            elif parent_calc_class is FleurinputgenCalculation:
                fleurinpgen = True
                new_comp = self.node.computer
                old_comp = parent_calc.computer
                if new_comp.uuid != old_comp.uuid:
                    #dont copy files, copy files localy
                    copy_remotely = False
            else:
                raise InputValidationError(
                    "parent_calc, must be either an 'inpgen calculation' or"
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

        #check for for allowed keys, ignor unknown keys but warn.
        for key in settings_dict.keys():
            if key not in self.inputs.metadata.options.setting_keys:
                #TODO warrning
                self.logger.info("settings dict key {} for Fleur calculation"
                                 "not reconized, only {} are allowed."
                                 "".format(key, self.inputs.metadata.options.setting_keys))

        #TODO: Detailed check of FleurinpData
        # if certain files are there in fleurinpData.
        # from where to copy

        # file copy stuff TODO check in fleur input
        if has_fleurinp:
            #add files belonging to fleurinp into local_copy_list
            allfiles = fleurinp.files
            for file1 in allfiles:
                local_copy_list.append((
                    fleurinp.uuid, file1,
                    file1))
            modes = fleurinp.get_fleur_modes()

            # add files to mode_retrieved_filelist
            if modes['band']:
                mode_retrieved_filelist.append(self.inputs.metadata.options.band_file_name)
                mode_retrieved_filelist.append(self.inputs.metadata.options.band_gnu_file_name)
            if modes['dos']:
                mode_retrieved_filelist.append(self.inputs.metadata.options.dos_file_name)
            if modes['forces']:
                print('FORCES!!!')
                mode_retrieved_filelist.append(self.inputs.metadata.options.new_xmlinp_file_name)
                mode_retrieved_filelist.append(self.inputs.metadata.options.force_file_name)
            if modes['ldau']:
                mode_retrieved_filelist.append(self.inputs.metadata.options.nmmpmat_file_name)
            #if noco, ldau, gw...
            # TODO: check from where it was copied, and copy files of its parent
            # if needed
        #self.logger.info("@@@@@@@@@@@@@@@@@@@@@@@@has_parent {}".format(has_parent))

        if has_parent:
            # copy the right files #TODO check first if file, exist and throw
            # warning, now this will throw an error
            outfolder_uuid = parent_calc.outputs.retrieved.uuid
            self.logger.info("out folder path {}".format(outfolder_uuid))

            if fleurinpgen and (not has_fleurinp):
                for file1 in self.inputs.metadata.options.copy_filelist_inpgen:
                    local_copy_list.append((
                        outfolder_uuid,
                        os.path.join(file1),
                        os.path.join(file1)))
            elif not fleurinpgen and (not has_fleurinp): # fleurCalc
                if with_hdf5:
                    copylist = self.inputs.metadata.options.copy_filelist_scf2_1
                else:
                    copylist = self.inputs.metadata.options.copy_filelist_scf
                #for file1 in copylist:
                    #local_copy_list.append((
                    #    outfolder_uuid,
                    #    file1[0],
                    #   file1[1]))
                #until 2725 aiida_core not solved, copy remotely:
                filelist_tocopy_remote = filelist_tocopy_remote# + self._copy_filelist_scf_remote
                #TODO get inp.xml from parent fleurinpdata, since otherwise it will be doubled in repo
            elif fleurinpgen and has_fleurinp:
                # everything is taken care of
                pass
            elif not fleurinpgen and has_fleurinp:
                # input file is already taken care of
                if with_hdf5:
                    copylist = self.inputs.metadata.options.copy_filelist_scf2
                else:
                    copylist = self.inputs.metadata.options.copy_filelist_scf1
                #for file1 in copylist:
                #    local_copy_list.append((
                #        outfolder_uuid,
                #        file1[0],
                #        file1[1]))
                #until 2725 aiida_core not solved, copy remotely:
                filelist_tocopy_remote = filelist_tocopy_remote# + self._copy_filelist_scf_remote

            # TODO not on same computer -> copy needed files from repository,
            # if they are not there, throw error
            if copy_remotely: # on same computer.
                #print('copy files remotely')

                # from fleurmodes
                if modes['dos']:
                    pass
                elif modes['band']:
                    pass
                else:
                    filelist_tocopy_remote = filelist_tocopy_remote + self.inputs.metadata.options.copy_filelist_scf_remote
                # from settings, user specified
                #TODO check if list?
                for file1 in settings_dict.get('additional_remotecopy_list', []):
                    filelist_tocopy_remote.append(file1)

                for file1 in settings_dict.get('remove_from_remotecopy_list', []):
                    if file1 in filelist_tocopy_remote:
                        filelist_tocopy_remote.remove(file1)
            
                for file1 in copylist:
                    remote_copy_list.append((
                        parent_calc_folder.computer.uuid,
                        os.path.join(parent_calc_folder.get_remote_path(), file1[0]),
                        file1[1]))
            
                for file1 in filelist_tocopy_remote:
                    remote_copy_list.append((
                        parent_calc_folder.computer.uuid,
                        os.path.join(parent_calc_folder.get_remote_path(), file1),
                        self._OUTPUT_FOLDER))

                #self.logger.info("remote copy file list {}".format(remote_copy_list))
        
        #  Prepare self._JUDFT_WARN_ONLY_INFO_FILE_NAME and upload
        # local_copy_list.append
        #_JUDFT_WARN_ONLY_INFO_FILE_NAME depricated for now.
        #warn_only_filename = tempfolder.get_abs_path(self.inputs.metadata.options.judft_warn_only_info_file_name)
        #with open(warn_only_filename, 'w') as infile:
        #    infile.write("\n")


        ########## MAKE CALCINFO ###########

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid
        # Empty command line by default
        #cmdline_params = settings_dict.pop('CMDLINE', [])
        #calcinfo.cmdline_params = (list(cmdline_params)
        #                           + ["-in", self._INPUT_FILE_NAME])

        self.logger.info("local copy file list {}".format(local_copy_list))

        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        #(remotemachinename, remoteabspath, relativedestpath)
        calcinfo.remote_symlink_list = remote_symlink_list
        #calcinfo.stdout_name = self._OUTPUT_FILE_NAME

        # Retrieve by default the output file and the xml file
        retrieve_list = []
        retrieve_list.append(self.inputs.metadata.options.outxml_file_name)
        retrieve_list.append(self.inputs.metadata.options.inpxml_file_name)
        #calcinfo.retrieve_list.append(self._OUTPUT_FILE_NAME)
        retrieve_list.append(self.inputs.metadata.options.shelloutput_file_name)
        retrieve_list.append(self.inputs.metadata.options.error_file_name)
        #calcinfo.retrieve_list.append(self._TIME_INFO_FILE_NAME)
        retrieve_list.append(self.inputs.metadata.options.out_file_name)
        if with_hdf5:
            retrieve_list.append(self.inputs.metadata.options.cdn_last_hdf5_file_name)
            retrieve_list.append(self.inputs.metadata.options.cdn1_file_name) # only for now because somthing is buggy
        else:
            retrieve_list.append(self.inputs.metadata.options.cdn1_file_name)
        #calcinfo.retrieve_list.append(self._INP_FILE_NAME)
        #calcinfo.retrieve_list.append(self._ENPARA_FILE_NAME)
        #calcinfo.retrieve_list.append(self._SYMOUT_FILE_NAME)
        #calcinfo.retrieve_list.append(self._KPTS_FILE_NAME)

        # if certain things are modefied, flags set,
        #other files should be retrieved, example DOS.x...

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
        walltime_sec = self.node.get_attribute('max_wallclock_seconds')
        #self.logger.info("!!!!!!!!!!!!!!!!!!! walltime_sec : {}"
        #                         "".format(walltime_sec))
        cmdline_params = []#, "-wtime", "{}".format(walltime_sec)]"-xml"
        #print('walltime: {}'.format(walltime_sec))
        if with_hdf5:
            cmdline_params.append("-last_extra")

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
        codeinfo.withmpi = self.node.get_attribute('max_wallclock_seconds')
        codeinfo.stdin_name = None#self._INPUT_FILE_NAME
        codeinfo.stdout_name = self.inputs.metadata.options.shelloutput_file_name
        #codeinfo.join_files = True
        codeinfo.stderr_name = self.inputs.metadata.options.error_file_name

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

'''
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

        self._DEFAULT_INPUT_FILE = fleurinp.get_file_abs_path(self._INPXML_FILE_NAME)
        # somehow this is not working...
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
'''
