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
    In this module you find the workflow 'FleurOrbControlWorkChain' for finding the groundstate
    in a DFT+U calculation.
"""
from aiida import orm
from aiida.engine import WorkChain, ToContext, if_, ExitCode
from aiida.engine import calcfunction as cf
from aiida.orm import Dict, Code, StructureData, RemoteData
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen

from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier, inpxml_changes
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data

import numpy as np
from lxml import etree
import re


def generate_density_matrix_configurations(occupations=None, configurations=None):
    """
    Generate all the necessary density matrix configurations from either the occupations or
    the explicitly given configurations for each species/orbital

    Both arguments are expected as dictionaries in the form ``d[species][orbital]``, with the
    orbital key holding the specification for the current LDA+U procedure

    :param occupations: specifying the occupations for each procedure
    :param configurations: specifying a explicit list of configurations that should be calculated


    :returns: list of dictionaries with all the possible starting configurations for the whole system
    """
    from more_itertools import distinct_permutations
    from itertools import product

    if occupations is not None and configurations is not None:
        raise ValueError('Please provide either occupations or configurations not both')

    config_dict = {}  #This dictionary will contain all distinct permutations for each
    #species/orbital. They are recombined after
    if occupations is not None:
        #The initial occupations were given

        for species, occ_species in occupations.items():
            for orbital, fixed_occ in occ_species.items():
                ind = f'{species}-{orbital}'
                l = int(orbital)
                config_dict[ind] = []

                if not isinstance(fixed_occ, list):
                    spin_occupation = fixed_occ // 2
                    if fixed_occ % 2 == 0:
                        fixed_occ = [spin_occupation, spin_occupation]
                    else:
                        fixed_occ = [spin_occupation + 1, spin_occupation]  #not ideal but for fine for now

                if any(x > 2 * l + 1 for x in fixed_occ):
                    raise ValueError(f'Invalid occupation {species} {orbital}: {fixed_occ}')

                for occ in fixed_occ:
                    spin_configs = []
                    start = [0 for _ in range(2 * l + 1)]
                    #Fill up the occupations until it matches the wanted one
                    i = 0
                    while sum(start) < occ:
                        start[i] = 1
                        i += 1
                    for config in distinct_permutations(start):
                        spin_configs.append(config)

                    if len(config_dict[ind]) != 0:
                        spin_configs = product(config_dict[ind], spin_configs)

                    combined_config = []
                    for config in spin_configs:
                        combined_config.append(config)
                    config_dict[ind] = combined_config

    elif configurations is not None:
        #The configurations were given explicitely

        for species, configs_species in configurations.items():
            for orbital, configs in configs_species.items():
                ind = f'{species}-{orbital}'
                if not isinstance(configs[0], list):
                    configs = [configs]
                config_dict[ind] = configs

    #Now combine them
    all_atom_configs = []
    for configs in product(*config_dict.values()):

        current_config = {}
        for index, key in enumerate(config_dict.keys()):
            current_config[key] = configs[index]
        all_atom_configs.append(current_config)

    return all_atom_configs


class FleurOrbControlWorkChain(WorkChain):
    """
    Workchain for determining the groundstate density matrix in an DFT+U
    calculation. This is done in 2 or 3 steps:

        1. Converge the system without DFT+U (a converged calculation can be
           provided to skip this step)
        2. A fixed number of iterations is run with fixed density matrices
           either generated as all distinct permutations for the given occupations
           or the explicitly given configurations
        3. The system and density matrix is relaxed

    :param wf_parameters: (Dict), Workchain Specifications
    :param scf_no_ldau: (Dict), Inputs to a FleurScfWorkChain providing the initial system
                                either converged or staring from a structure
    :param scf_with_ldau: (Dict), Inputs to a FleurScfWorkChain. Only the wf_parameters are valid
    :param fleurinp: (FleurinpData) FleurinpData to start from if no SCF should be done
    :param remote: (RemoteData) RemoteData to start from if no SCF should be done
    :param structure: (StructureData) Structure to start from if no SCF should be done
    :param calc_parameters: (Dict), Inpgen Parameters
    :param settings: (Dict), additional settings for e.g retrieving files
    :param options: (Dict), Options for the submission of the jobs
    :param inpgen: (Code)
    :param fleur: (Code)
    """
    _workflowversion = '0.6.0'

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 2 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }

    _wf_default = {
        'iterations_fixed': 30,
        'distance_cutoff_relaxed': 5,
        'ldau_dict': None,
        'use_orbital_occupation': False,
        'fixed_occupations': None,
        'fixed_configurations': None,
        'inpxml_changes': [],
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False,
                               'help': 'Inputs for SCF Workchain before adding LDA+U'
                           },
                           namespace='scf_no_ldau')
        spec.input('remote', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('structure', valid_type=StructureData, required=False)
        spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False,
                               'help': 'Inputs for SCF Workchain after the LDA+U matrix was fixed'
                           },
                           exclude=('structure', 'fleurinp', 'remote_data'),
                           namespace='scf_with_ldau')
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('inpgen', valid_type=Code, required=False)
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('options', valid_type=Dict, required=False)
        spec.input('options_inpgen', valid_type=Dict, required=False)
        spec.input('settings', valid_type=Dict, required=False)
        spec.input('settings_inpgen', valid_type=Dict, required=False)

        spec.input_namespace('fixed_remotes', valid_type=orm.RemoteData, dynamic=True, required=False)
        spec.input_namespace('relaxed_remotes', valid_type=orm.RemoteData, dynamic=True, required=False)

        spec.outline(cls.start, cls.validate_input,
                     if_(cls.scf_no_ldau_needed)(cls.converge_scf_no_ldau).elif_(cls.inpgen_needed)(cls.run_inpgen),
                     cls.create_configurations,
                     if_(cls.run_fixed_calculations)(cls.run_fleur_fixed), cls.converge_scf, cls.return_results)

        spec.output('output_orbcontrol_wc_para', valid_type=Dict)
        spec.output('groundstate_denmat', valid_type=orm.SinglefileData, required=False)
        spec.expose_outputs(FleurScfWorkChain, namespace='groundstate_scf')

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Input codes do not correspond to fleur or inpgen respectively.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(342,
                       'ERROR_SOME_CONFIGS_FAILED',
                       message='Convergence LDA+U calculation failed for some Initial configurations.')
        spec.exit_code(343,
                       'ERROR_ALL_CONFIGS_FAILED',
                       message='Convergence LDA+U calculation failed for all Initial configurations.')
        spec.exit_code(360, 'ERROR_INPGEN_CALCULATION_FAILED', message='Inpgen calculation failed.')
        spec.exit_code(450, 'ERROR_SCF_NOLDAU_FAILED', message='Convergence workflow without LDA+U failed.')

    @classmethod
    def get_builder_continue_fixed(cls, node):
        """
        Get a Builder prepared with inputs to continue from the charge densities of
        a already finished MagRotateWorkChain

        :param node: Instance, from which the calculation should be continued
        """
        builder = node.get_builder_restart()
        scf_nodes = node.get_outgoing(node_class=FleurBaseWorkChain).all()
        for link in scf_nodes:
            if not link.node.is_finished_ok:
                continue
            if not re.fullmatch(r'Fixed\_[0-9]+', link.link_label):
                continue
            builder.fixed_remotes[link.link_label] = link.node.outputs.remote_folder

        return builder

    @classmethod
    def get_builder_continue_relaxed(cls, node, allow_nonconverged=True):
        """
        Get a Builder prepared with inputs to continue from the charge densities of
        a already finished MagRotateWorkChain

        :param node: Instance, from which the calculation should be continued
        """
        builder = node.get_builder_restart()
        scf_nodes = node.get_outgoing(node_class=FleurScfWorkChain).all()
        for link in scf_nodes:
            if not link.node.is_finished_ok:
                if allow_nonconverged:
                    if link.node.exit_status not in FleurScfWorkChain.get_exit_statuses(['ERROR_DID_NOT_CONVERGE']):
                        continue
                else:
                    continue
            if not re.fullmatch(r'Relaxed\_[0-9]+', link.link_label):
                continue
            builder.relaxed_remotes[link.link_label] = link.node.outputs.remote_folder

        return builder

    def start(self):
        """
        init context and some parameters
        """
        self.report(f'INFO: started orbital occupation control workflow version {self._workflowversion}')

        ####### init    #######

        # internal para /control para
        self.ctx.scf_no_ldau = None
        self.ctx.scf_no_ldau_needed = False
        self.ctx.skip_fixed_calculations = False
        self.ctx.inpgen_needed = False
        self.ctx.fixed_configurations = []
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.description_wf = self.inputs.get('description', '') + '|fleur_orbcontrol_wc|'
        self.ctx.label_wf = self.inputs.get('label', 'fleur_orbcontrol_wc')

        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # initialize the dictionary using defaults if no options are given
        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

    def validate_input(self):
        """
        validate input
        """
        extra_keys = []
        for key in self.ctx.wf_dict:
            if key not in self._wf_default:
                extra_keys.append(key)
        if extra_keys:
            error = f'ERROR: input wf_parameters for Orbcontrol contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        ldau_dict = self.ctx.wf_dict.get('ldau_dict')
        ldau_keys_required = ['l', 'U', 'J', 'l_amf']
        if ldau_dict is not None:
            missing = []
            for species, current in ldau_dict.items():
                for key in ldau_keys_required:
                    if key not in current:
                        missing.append(key)
                if missing:
                    error = 'ERROR: Missing input: The following required keys are missing from ldau_dict' \
                            f' for species {species}: {missing}'
                    self.report(error)
                    return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        else:
            error = 'ERROR: Missing input: ldau_dict was not speciified'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        max_iters = self.ctx.wf_dict.get('iterations_fixed')
        if max_iters <= 1:
            error = "ERROR: 'iterations_fixed' should be equal at least 2"
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        occupations_dict = self.ctx.wf_dict.get('fixed_occupations')
        configurations_dict = self.ctx.wf_dict.get('fixed_configurations')
        #TODO:check occupations or configurations
        if occupations_dict is not None:
            if configurations_dict is not None:
                error = 'ERROR: Invalid input: Only provide one of fixed_occupations and fixed_configurations'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

            for species, occ_species in occupations_dict.items():
                for orbital, occ in occ_species.items():
                    if species not in ldau_dict:
                        error = f'ERROR: Invalid input: {species} defined in fixed_occupations but not in ldau_dict'
                        self.report(error)
                        return self.exit_codes.ERROR_INVALID_INPUT_PARAM
                    missing = False
                    if isinstance(ldau_dict[species], dict):
                        if int(orbital) != ldau_dict[species]['l']:
                            missing = True
                    else:
                        for index, current_dict in enumerate(ldau_dict[species]):
                            if int(orbital) == current_dict['l']:
                                break
                            if index == len(ldau_dict) - 1:
                                missing = True
                    if missing:
                        error = f'ERROR: Invalid input: Orbital {orbital} is given in fixed_occupations for {species}, ' \
                                    ' but it is not defined in ldau_dict'
                        self.report(error)
                        return self.exit_codes.ERROR_INVALID_INPUT_PARAM

                    if not isinstance(occ, list):
                        error = f'ERROR: Invalid input: {species} defined in fixed_occupations invalid type'
                        self.report(error)
                        return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        else:
            if configurations_dict is not None:

                for species, occ_species in occupations_dict.items():
                    for orbital, occ in occ_species.items():

                        if species not in ldau_dict:
                            error = f'ERROR: Invalid input: {species} defined in fixed_configurations but not in ldau_dict'
                            self.report(error)
                            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

                        missing = False
                        if isinstance(ldau_dict[species], dict):
                            if int(orbital) != ldau_dict[species]['l']:
                                missing = True
                        else:
                            for index, current_dict in enumerate(ldau_dict[species]):
                                if int(orbital) == current_dict['l']:
                                    break
                                if index == len(ldau_dict) - 1:
                                    missing = True
                        if missing:
                            error = f'ERROR: Invalid input: Orbital {orbital} is given in fixed_configurations for {species}, ' \
                                        ' but it is not defined in ldau_dict'
                            self.report(error)
                            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

                        if not isinstance(occ, list):
                            error = f'ERROR: Invalid input: {species} defined in fixed_configurations invalid type'
                            self.report(error)
                            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

            else:
                error = 'ERROR: Missing input: Provide one of fixed_occupations or fixed_configurations'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        inputs = self.inputs
        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur')
            except ValueError:
                error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen')
            except ValueError:
                error = 'The code you provided for INPGEN does not use the plugin fleur.inpgen'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        fleurinp = None
        remote = None
        if 'scf_no_ldau' in inputs:
            input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_no_ldau'))
            self.ctx.scf_no_ldau_needed = True
            if 'fleurinp' in input_scf:
                fleurinp = input_scf.fleurinp
            if 'remote_data' in input_scf:
                remote = input_scf.remote_data
            if 'remote' in inputs:
                error = 'ERROR: you gave SCF input + remote for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in inputs:
                error = 'ERROR: you gave SCF input + fleurinp for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'structure' in inputs:
                error = 'ERROR: you gave SCF input + structure for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'calc_parameters' in inputs:
                error = 'ERROR: you gave SCF input + calc_parameters for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'inpgen' in inputs:
                error = 'ERROR: you gave SCF input + inpgen for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'relaxed_remotes' in inputs:
                error = 'ERROR: you gave SCF input + Charge densities for relaxation to start from'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'structure' in inputs:
            self.ctx.inpgen_needed = True
            if 'inpgen' not in inputs:
                error = 'ERROR: you gave structure input but no inpgen code Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'relaxed_remotes' in inputs:
                error = 'ERROR: you gave structure input + Charge densities for relaxation to start from'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote' not in inputs and 'fleurinp' not in inputs and 'relaxed_remotes' not in inputs:
            error = 'ERROR: you gave neither SCF input nor remote or fleurinp'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            if 'calc_parameters' in inputs:
                error = 'ERROR: you gave remote(s)/fleurinp input + calc_parameters for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'structure' in inputs:
                error = 'ERROR: you gave remote(s)/fleurinp input + structure for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'inpgen' in inputs:
                error = 'ERROR: you gave remote(s)/fleurinp input + inpgen for the Orbcontrol calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'relaxed_remotes' in inputs:
                if 'fixed_remotes' in inputs:
                    error = 'ERROR: you gave fixed and relaxed remotes for the Orbcontrol calculation'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
                if 'remote' in inputs:
                    error = 'ERROR: you gave relaxed remotes + remote for the Orbcontrol calculation'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
                if 'fleurinp' in inputs:
                    error = 'ERROR: you gave relaxed remotes + fleurinp for the Orbcontrol calculation'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
                self.ctx.skip_fixed_calculations = True
            if 'remote' in inputs:
                remote = inputs.remote
            if 'fleurinp' in inputs:
                fleurinp = inputs.fleurinp

        if fleurinp is not None:
            modes = fleurinp.get_fleur_modes()
            if modes['ldau']:
                error = f"ERROR: Wrong input: fleurinp {'in scf_no_ldau' if 'scf_no_ldau' in inputs else ''} already contains LDA+U"
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if remote is not None:
            retrieved_filenames = remote.creator.outputs.retrieved.list_object_names()
            if FleurCalculation._NMMPMAT_FILE_NAME in retrieved_filenames or \
               FleurCalculation._NMMPMAT_HDF5_FILE_NAME in retrieved_filenames:
                error = f"ERROR: Wrong input: remote_data {'in scf_no_ldau' if 'scf_no_ldau' in inputs else ''} already contains LDA+U"
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def scf_no_ldau_needed(self):
        """
        Returns whether to run an additional scf workchain before adding LDA+U
        """
        return self.ctx.scf_no_ldau_needed

    def run_fixed_calculations(self):
        """
        Returns whether to run frozen density matrix calculations
        """
        return not self.ctx.skip_fixed_calculations

    def converge_scf_no_ldau(self):
        """
        Launch fleur.scf for the system without LDA+U
        """
        inputs = self.get_inputs_scf_no_ldau()

        self.report('Info: Run SCF without LDA+U')
        future = self.submit(FleurScfWorkChain, **inputs)
        future.label = 'scf_no_ldau'
        future.description = 'SCF Calculation for orbital occupation control before adding DFT+U'
        return ToContext(scf_no_ldau=future)

    def get_inputs_scf_no_ldau(self):
        """
        Get the inputs for the scf workchain without LDA+U
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_no_ldau'))

        if 'fleur' not in input_scf:
            input_scf.fleur = self.inputs.fleur

        if 'options' not in input_scf:
            input_scf.options = self.inputs.options

        input_scf.metadata.call_link_label = 'scf_no_ldau'
        return input_scf

    def inpgen_needed(self):
        """
        Returns whether the inpgen should be run directly by this workchain
        """
        return self.ctx.inpgen_needed

    def run_inpgen(self):
        """
        Run the input generator
        """
        ## prepare inputs for inpgen
        structure = self.inputs.structure
        self.ctx.formula = structure.get_formula()
        label = 'scf: inpgen'
        description = f'{self.ctx.description_wf} inpgen on {self.ctx.formula}'

        inpgencode = self.inputs.inpgen

        if 'calc_parameters' in self.inputs:
            params = self.inputs.calc_parameters
        else:
            params = None

        if 'settings_inpgen' in self.inputs:
            settings = self.inputs.settings_inpgen
        else:
            settings = None

        if 'options_inpgen' in self.inputs:
            options = self.inputs.options_inpgen
        else:
            #Only take the parts that could be relevant (resources is overwritten anyway)
            options = {'queue_name': self.inputs.options.get_dict().get('queue_name', '')}
            if 'max_wallclock_seconds' in options:
                options['max_wallclock_seconds'] = int(self.inputs.options['max_wallclock_seconds'])

        inputs_build = get_inputs_inpgen(structure,
                                         inpgencode,
                                         options,
                                         label,
                                         description,
                                         settings=settings,
                                         params=params)

        inputs_build.metadata.call_link_label = 'inpgen'
        # Launch inpgen
        self.report('INFO: run inpgen')
        future = self.submit(inputs_build)
        future.label = 'inpgen'
        future.description = 'Inpgen calculation for Orbital occupation control workflow'

        return ToContext(inpgen=future)

    def create_configurations(self):
        """
        Creates the configurations for the initial density matrices

        If fixed_occupations was provided the density matrices are constructed
        as having the given occupations and constructing all distinct permutations

        If fixed_configurations was provided only the given configurations are taken
        """
        all_atom_configs = generate_density_matrix_configurations(
            occupations=self.ctx.wf_dict['fixed_occupations'], configurations=self.ctx.wf_dict['fixed_configurations'])

        self.report(f'INFO: Generated {len(all_atom_configs)} distinct fixed starting configurations')
        self.ctx.fixed_configurations = all_atom_configs

    def run_fleur_fixed(self):
        """
        Launches fleur.base with l_linMix=T and mixParam=0.0, i.e. with a fixed density matrix
        for all configurations.
        """

        if self.ctx.scf_no_ldau_needed:

            if not self.ctx.scf_no_ldau.is_finished_ok:
                error = ('ERROR: SCF workflow without LDA+U was not successful')
                self.report(error)
                return self.exit_codes.ERROR_SCF_NOLDAU_FAILED

            try:
                self.ctx.scf_no_ldau.outputs.output_scf_wc_para
            except NotExistent:
                message = ('ERROR: SCF workflow without LDA+U failed, no scf output node')
                self.ctx.errors.append(message)
                return self.exit_codes.ERROR_SCF_NOLDAU_FAILED

        self.report('INFO: Run fixed density matrix calculations')

        for index, config in enumerate(self.ctx.fixed_configurations):

            inputs, status = self.get_inputs_fixed_configurations(index, config)
            if status:
                return status
            label = f'Fixed_{index}'

            inputs.setdefault('metadata', {})['call_link_label'] = label
            res = self.submit(FleurBaseWorkChain, **inputs)
            res.label = label
            res.description = f'DFT+U calculation with fixed configuration number {index}'
            self.to_context(**{label: res})

    def get_inputs_fixed_configurations(self, index, config):
        """
        Sets up the input for the fixed density matrix calculation.
        """

        remote_data = None
        if self.ctx.scf_no_ldau_needed:
            try:
                fleurinp = self.ctx.scf_no_ldau.outputs.fleurinp
                remote_data = self.ctx.scf_no_ldau.outputs.last_calc.remote_folder
            except NotExistent:
                error = 'Fleurinp generated in the SCF calculation is not found.'
                self.control_end_wc(error)
                return {}, self.exit_codes.ERROR_SCF_NOLDAU_FAILED
        elif self.ctx.inpgen_needed:
            if not self.ctx.inpgen.is_finished_ok:
                error = 'Inpgen calculation failed'
                self.control_end_wc(error)
                return {}, self.exit_codes.ERROR_INPGEN_CALCULATION_FAILED
            try:
                fleurinp = self.ctx.inpgen.outputs.fleurinp
            except (AttributeError, NotExistent):
                return {}, self.exit_codes.ERROR_INPGEN_CALCULATION_FAILED
        else:
            if 'remote' in self.inputs:
                remote_data = self.inputs.remote
            if 'fixed_remotes' in self.inputs and \
                f'Fixed_{index}' in self.inputs.fixed_remotes:
                self.report(f'INFO: overwriting remote folder with given fixed remote for configuration {index}')
                remote_data = self.inputs.fixed_remotes[f'Fixed_{index}']

            if 'fleurinp' not in self.inputs:
                fleurinp = get_fleurinp_from_remote_data(remote_data, store=True)
                self.report(
                    f'INFO: generated FleurinpData from {fleurinp.files} from remote folder pk={remote_data.pk}')
            else:
                fleurinp = self.inputs.fleurinp

        inputs = self.inputs

        label = f'Fixed_{index}'
        description = f'LDA+U with fixed nmmpmat for config {index}'

        settings = {}
        if 'settings' in inputs:
            settings = inputs.settings.get_dict()
        settings.setdefault('remove_from_remotecopy_list', []).append('mixing_history*')

        self.report(f'INFO: create fleurinp for config {index}')
        fm = FleurinpModifier(fleurinp)
        modes = fleurinp.get_fleur_modes()

        fm.set_inpchanges({'itmax': self.ctx.wf_dict['iterations_fixed'], 'l_linMix': True, 'mixParam': 0.0})

        fchanges = self.ctx.wf_dict['inpxml_changes']
        if fchanges:
            try:
                fm.add_task_list(fchanges)
            except (ValueError, TypeError) as exc:
                error = ('ERROR: Changing the inp.xml file failed. Tried to apply inpxml_changes'
                         f', which failed with {exc}. I abort, good luck next time!')
                self.control_end_wc(error)
                return {}, self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        for atom_species, ldau_dict in self.ctx.wf_dict['ldau_dict'].items():
            fm.set_species(atom_species, {'ldaU': ldau_dict})

        for config_index, config_species in config.items():
            orbital = config_index.split('-')[-1]
            atom_species = '-'.join(config_index.split('-')[:-1])

            if len(config_species) == 2 and modes['jspin'] == 1:
                self.report(f'Configuration for species {atom_species} is given spin-polarized, '
                            'but the calculation is non-spinpolarized. Summing up configurations.')
                config_species = [sum(np.array(config) for config in config_species).tolist()]

            for spin, config_spin in enumerate(config_species):
                if self.ctx.wf_dict['use_orbital_occupation']:
                    fm.set_nmmpmat(species_name=atom_species,
                                   orbital=int(orbital),
                                   spin=spin + 1,
                                   orbital_occupations=config_spin)
                else:
                    fm.set_nmmpmat(species_name=atom_species,
                                   orbital=int(orbital),
                                   spin=spin + 1,
                                   state_occupations=config_spin)

        try:
            fm.show(display=False, validate=True)
        except etree.DocumentInvalid:
            self.control_end_wc('ERROR: input, inp.xml changes did not validate')
            return {}, self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, inp.xml changes could not be applied.'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return {}, self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        fleurinp_fixed = fm.freeze()

        input_fixed = get_inputs_fleur(inputs.fleur,
                                       remote_data,
                                       fleurinp_fixed,
                                       self.ctx.options,
                                       label,
                                       description,
                                       settings=settings,
                                       add_comp_para=self.ctx.wf_dict['add_comp_para'])

        return input_fixed, None

    def converge_scf(self):
        """
        Launch fleur.scf after the fixed density matrix calculations to relax the density matrix
        """
        self.report('INFO: Relax density matrices')
        for index, config in enumerate(self.ctx.fixed_configurations):

            inputs = self.get_inputs_scf()

            if self.ctx.skip_fixed_calculations:
                if f'Relaxed_{index}' not in self.inputs.relaxed_remotes:
                    self.report(f'INFO: Skipping configuration {index}')
                    continue
                inputs.remote_data = self.inputs.relaxed_remotes[f'Relaxed_{index}']
            else:

                fixed_calc = self.ctx[f'Fixed_{index}']

                if not fixed_calc.is_finished_ok:
                    message = f'One Base workflow (fixed nmmpmat) failed: {index}'
                    self.ctx.warnings.append(message)
                    continue

                try:
                    fixed_calc.outputs.output_parameters
                except NotExistent:
                    message = f'One Base workflow (fixed nmmpmat) failed, no output node: {index}. I skip this one.'
                    self.ctx.errors.append(message)
                    continue

                inputs.fleurinp = fixed_calc.inputs.fleurinp
                inputs.remote_data = fixed_calc.outputs.remote_folder

            label = f'Relaxed_{index}'
            inputs.setdefault('metadata', {})['call_link_label'] = label
            res = self.submit(FleurScfWorkChain, **inputs)
            res.label = label
            res.description = f'DFT+U calculation for configuration number {index} converging the density matrix'
            self.to_context(**{label: res})

    def get_inputs_scf(self):
        """
        Get the input for the scf workchain after the fixed density matrix calculations
        to relax the density matrix
        """
        if 'scf_with_ldau' in self.inputs:
            input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_with_ldau'))
        else:
            input_scf = AttributeDict({})

        if 'fleur' not in input_scf:
            input_scf.fleur = self.inputs.fleur

        if 'options' not in input_scf:
            input_scf.options = self.inputs.options

        if 'settings' not in input_scf:
            settings = {}
        else:
            settings = input_scf.settings.get_dict()
        settings.setdefault('remove_from_remotecopy_list', []).append('mixing_history*')
        input_scf.settings = Dict(settings)

        scf_wf_parameters = {}
        if 'wf_parameters' in input_scf:
            scf_wf_parameters = input_scf.wf_parameters.get_dict()
        scf_wf_parameters['stop_if_last_distance_exceeds'] = self.ctx.wf_dict['distance_cutoff_relaxed']

        with inpxml_changes(scf_wf_parameters) as fm:
            fm.set_inpchanges({'l_linmix': False})

        input_scf.wf_parameters = Dict(scf_wf_parameters)
        input_scf.settings = Dict(settings)

        return input_scf

    def return_results(self):
        """
        return the results of the relaxed DFT+U calculations (scf workchains)
        """
        distancelist = []
        t_energylist = []
        failed_configs = []
        skipped_configs = []
        non_converged_configs = []
        configs_list = []
        outnodedict = {}
        e_u = 'htr'
        dis_u = 'me/bohr^3'
        for index, config in enumerate(self.ctx.fixed_configurations):
            if f'Relaxed_{index}' in self.ctx:
                calc = self.ctx[f'Relaxed_{index}']
            elif not self.ctx.skip_fixed_calculations:
                message = (f'One SCF workflow was not run because the fixed calculation failed: Relaxed_{index}')
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                failed_configs.append(index)
                t_energylist.append(None)
                distancelist.append(None)
                continue
            elif f'Relaxed_{index}' in self.inputs.relaxed_remotes:
                message = (f'One SCF workflow was not run for unknown reasons: Relaxed_{index}')
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                failed_configs.append(index)
                t_energylist.append(None)
                distancelist.append(None)
                continue
            else:
                skipped_configs.append(index)
                t_energylist.append(None)
                distancelist.append(None)
                continue

            if not calc.is_finished_ok:
                message = f'One SCF workflow was not successful: Relaxed_{index}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                #We dont skip simply non-converged calculations
                #because we want to try to exctract the total_energy
                if calc.exit_status not in FleurScfWorkChain.get_exit_statuses(['ERROR_DID_NOT_CONVERGE']):
                    failed_configs.append(index)
                    t_energylist.append(None)
                    distancelist.append(None)
                    continue
                non_converged_configs.append(index)

            try:
                outputnode_scf = calc.outputs.output_scf_wc_para
            except NotExistent:
                message = f'One SCF workflow failed, no scf output node: Relaxed_{index}. I skip this one.'
                self.ctx.errors.append(message)
                self.ctx.successful = False
                failed_configs.append(index)
                t_energylist.append(None)
                distancelist.append(None)
                continue

            try:
                fleurinp_scf = calc.outputs.fleurinp
            except NotExistent:
                message = f'One SCF workflow failed, no fleurinp output node: Relaxed_{index}. I skip this one.'
                self.ctx.errors.append(message)
                self.ctx.successful = False
                failed_configs.append(index)
                t_energylist.append(None)
                distancelist.append(None)
                continue

            # we loose the connection of the failed scf here.
            # link labels cannot contain '.'
            link_label = f'configuration_{index}'
            fleurinp_label = f'fleurinp_{index}'
            outnodedict[link_label] = outputnode_scf
            outnodedict[fleurinp_label] = fleurinp_scf

            outpara = outputnode_scf.get_dict()

            t_e = outpara.get('total_energy', None)
            e_u = outpara.get('total_energy_units', 'htr')
            dis = outpara.get('distance_charge', None)
            dis_u = outpara.get('distance_charge_units', 'me/bohr^3')
            t_energylist.append(t_e)
            distancelist.append(dis)
            configs_list.append(index)
        converged_configs = [index for index in configs_list if index not in non_converged_configs]

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'configurations': self.ctx.fixed_configurations,
            'total_energy': t_energylist,
            'total_energy_units': e_u,
            'distance_charge': distancelist,
            'distance_charge_units': dis_u,
            'successful_configs': configs_list,
            'converged_configs': converged_configs,
            'non_converged_configs': non_converged_configs,
            'failed_configs': failed_configs,
            'skipped_configs': skipped_configs,
            'groundstate_configuration': None,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        if self.ctx.successful:
            self.report('Done, Orbital occupation control calculation complete')
        elif any(e is not None for e in t_energylist):
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance.')
        else:
            self.report('Done, but something went wrong.... All Calculations failed. Probably something is'
                        ' wrong in your setup')

        #Find the minimal total energy in the list
        if any(e is not None for e in t_energylist):
            energy = np.array(t_energylist, dtype=float)

            converged_mask = np.ones(energy.size, dtype=bool)
            converged_mask[non_converged_configs] = False
            converged_mask[failed_configs] = False
            converged_mask[skipped_configs] = False

            non_converged_mask = np.ones(energy.size, dtype=bool)
            non_converged_mask[converged_configs] = False
            non_converged_mask[failed_configs] = False
            non_converged_mask[skipped_configs] = False

            if len(energy[converged_mask]) != 0:
                converged_minimum_energy = np.nanmin(energy[converged_mask])
                if len(energy[non_converged_mask]) != 0:
                    if np.nanmin(energy[non_converged_mask]) < converged_minimum_energy:
                        lower_non_converged = np.array(non_converged_configs)[energy[non_converged_mask] <
                                                                              converged_minimum_energy]
                        out['warnings'].extend(f"Configuration 'Relaxed_{index}' did not converge "
                                               'but is lower in energy than the lowest converged configuration'
                                               for index in lower_non_converged)

                #Replace the non-converged calculations with NaN
                #If we were to simply do np.nanargmin(energy[converged_mask])
                #The index will no longer match up with the complete list
                energy[~converged_mask] = np.nan
                groundstate_index = np.nanargmin(energy)
                out['groundstate_configuration'] = groundstate_index

                if f'Relaxed_{groundstate_index}' in self.ctx:
                    groundstate_scf = self.ctx[f'Relaxed_{groundstate_index}']
                    self.out_many(self.exposed_outputs(groundstate_scf, FleurScfWorkChain, namespace='groundstate_scf'))

                    #Retrieve the nmmpmat file and provide it as an singlefiledata output
                    retrieved = groundstate_scf.outputs.last_calc.retrieved
                    nmmp_node = extract_nmmp_file(retrieved)
                    if not isinstance(nmmp_node, ExitCode):
                        self.out('groundstate_denmat', nmmp_node)
                    else:
                        self.report(
                            'Something went wrong. The groundstate SCF calculation contains no density matrix file')

        outnode = Dict(out)
        outnodedict['results_node'] = outnode

        # create links between all these nodes...
        outputnode_dict = create_orbcontrol_result_node(**outnodedict)

        outputnode = outputnode_dict.get('output_orbcontrol_wc_para')
        outputnode.label = 'output_orbcontrol_wc_para'
        outputnode.description = (
            'Contains orbital occupation control results and information of an FleurOrbControlWorkChain run.')

        self.out('output_orbcontrol_wc_para', outputnode)

        outputscf = outputnode_dict.get('output_orbcontrol_wc_gs_scf', None)
        if outputscf:
            outputscf.label = 'output_orbcontrol_wc_gs_scf'
            outputscf.description = ('SCF output from the run with the lowest total '
                                     'energy extracted from FleurOrbControlWorkChain')

        if all(e is None for e in t_energylist) or out.get('groundstate_configuration') is None:
            return self.exit_codes.ERROR_ALL_CONFIGS_FAILED
        if not self.ctx.successful:
            return self.exit_codes.ERROR_SOME_CONFIGS_FAILED

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. It will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_orbcontrol_result_node(**kwargs):
    """
    This is a pseudo cf, to create the right graph structure of AiiDA.
    This calcfunction will create the output nodes in the database.
    It also connects the output_nodes to all nodes the information comes from.
    This includes the output_parameter node for the orbcontrol, connections to run scfs,
    and returning of the gs_calculation (best initial density matrix)
    So far it is just parsed in as kwargs argument, because we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_orbcontrol_wc_para'] = outpara.clone()
    # copy, because we rather produce the same node twice
    # then have a circle in the database for now...
    outputdict = outpara.get_dict()
    groundstate_index = outputdict.get('groundstate_configuration')
    if groundstate_index is None:
        return outdict

    if f'configuration_{groundstate_index}' in kwargs:
        outdict['output_orbcontrol_wc_gs_scf'] = kwargs[f'configuration_{groundstate_index}'].clone()
    if f'fleurinp_{groundstate_index}' in kwargs:
        outdict['output_orbcontrol_wc_gs_fleurinp'] = kwargs[f'fleurinp_{groundstate_index}'].clone()

    return outdict


@cf
def extract_nmmp_file(folder):
    """
    Extract the density matrix file from the given folder data

    :raises: ExitCode 300, No density matrix file found
    """
    filenames = folder.list_object_names()

    nmmp_filename = None
    if FleurCalculation._NMMPMAT_FILE_NAME in filenames:
        nmmp_filename = FleurCalculation._NMMPMAT_FILE_NAME
    elif FleurCalculation._NMMPMAT_HDF5_FILE_NAME in filenames:
        nmmp_filename = FleurCalculation._NMMPMAT_HDF5_FILE_NAME

    if nmmp_filename is None:
        return ExitCode(300, message='FolderData has no density matrix file')

    with folder.open(nmmp_filename, 'rb') as nmmp_file:
        nmmp_node = orm.SinglefileData(nmmp_file, filename=FleurCalculation._NMMPMAT_FILE_NAME)

    nmmp_node.label = 'groundstate_denmat'
    nmmp_node.description = 'Converged density matrix file calculated in the orbcontrol workchain'
    return nmmp_node
