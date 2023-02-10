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
In this module you find the workchain 'FleurScfWorkChain' for the self-consistency
cycle management of a FLEUR calculation with AiiDA.
"""
# TODO: more info in output, log warnings
# TODO: make smarter, ggf delete mixing_history or restart with more or less iterations
# you can use the pattern of the density convergence for this
# TODO: maybe write dict schema for wf_parameter inputs, how?
from lxml import etree
from copy import deepcopy

from aiida.orm import Code, load_node
from aiida.orm import StructureData, RemoteData, Dict, Bool, Float
from aiida.engine import WorkChain, while_, if_, ToContext
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent

from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.create_kpoints_from_distance import create_kpoints_from_distance_parameter
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.calculation.fleur import FleurCalculation

from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data_cf

from masci_tools.io.parsers.fleur import outxml_parser


class FleurScfWorkChain(WorkChain):
    """
    Workchain for converging a FLEUR calculation (SCF).

    It converges the charge density, total energy or the largest force.
    Two paths are possible:

    (1) Start from a structure and run the inpgen first optional with calc_parameters
    (2) Start from a Fleur calculation, with optional remoteData

    :param wf_parameters: (Dict), Workchain Specifications
    :param structure: (StructureData), Crystal structure
    :param calc_parameters: (Dict), Inpgen Parameters
    :param fleurinp: (FleurinpData), to start with a Fleur calculation
    :param remote_data: (RemoteData), from a Fleur calculation
    :param inpgen: (Code)
    :param fleur: (Code)

    :return: output_scf_wc_para (Dict), Information of workflow results
        like Success, last result node, list with convergence behavior
    """

    _workflowversion = '0.6.3'
    _default_wf_para = {
        'fleur_runmax': 4,
        'density_converged': 0.00002,
        'stop_if_last_distance_exceeds': None,
        'energy_converged': 0.002,
        'force_converged': 0.002,
        'torque_converged': 0.0002,
        'kpoints_distance': None,  # in 1/A, usually 0.1
        'kpoints_force_parity': False,
        'kpoints_force_odd': False,
        'kpoints_force_even': False,
        'kpoints_force_gamma': False,
        'nmmp_converged': 0.002,
        'mode': 'density',  # 'density', 'energy', 'force' or 'gw'
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'itmax_per_run': 30,
        'force_dict': {
            'qfix': 2,
            'forcealpha': 1.0,
            'forcemix': 'straight'
        },
        'use_relax_xml': False,
        'inpxml_changes': [],
        'drop_mixing_first_iteration': True,
        'straight_iterations': None,
        'initial_straight_mixing': False,
        'initial_ldau_straight_mixing': False,
        'initial_ldau_straight_mix_param': 0.0,  #Density matrix frozen by default, since it is the most stable option
    }

    _default_options = {
        'optimize_resources': True,
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 6 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('inpgen', valid_type=Code, required=False)
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('structure', valid_type=StructureData, required=False)
        spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('remote_data', valid_type=RemoteData, required=False)
        spec.input('options', valid_type=Dict, required=False)
        spec.input('settings', valid_type=Dict, required=False)
        spec.input('settings_inpgen', valid_type=Dict, required=False)
        spec.outline(cls.start, cls.validate_input,
                     if_(cls.fleurinpgen_needed)(cls.run_fleurinpgen), cls.run_fleur, cls.inspect_fleur, cls.get_res,
                     while_(cls.condition)(cls.run_fleur, cls.inspect_fleur, cls.get_res), cls.return_results)

        spec.output('fleurinp', valid_type=FleurinpData)
        spec.output('output_scf_wc_para', valid_type=Dict)
        spec.expose_outputs(FleurBaseWorkChain, namespace='last_calc')

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Input codes do not correspond to fleur or inpgen respectively.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(360, 'ERROR_INPGEN_CALCULATION_FAILED', message='Inpgen calculation failed.')
        spec.exit_code(361, 'ERROR_FLEUR_CALCULATION_FAILED', message='Fleur calculation failed.')
        spec.exit_code(362, 'ERROR_DID_NOT_CONVERGE', message='SCF cycle did not lead to convergence.')

    def start(self):
        """
        init context and some parameters
        """
        self.report(f'INFO: started convergence workflow version {self._workflowversion}')

        ####### init    #######

        # internal para /control para
        self.ctx.last_base_wc = None
        self.ctx.loop_count = 0
        self.ctx.relax_generated = False
        self.ctx.calcs = []
        self.ctx.abort = False
        self.ctx.reached_conv = True
        self.ctx.run_straight_mixing = False

        wf_default = self._default_wf_para
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            if isinstance(val, dict):
                wf_dict[key] = {**val, **wf_dict.get(key, {})}
            else:
                wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # fleur = self.inputs.fleur
        # fleur_extras = fleur.extras
        # inpgen_extras = None
        # if 'inpgen' in self.inputs:
        #     inpgen = self.inputs.inpgen
        #     inpgen_extras = inpgen.extras

        defaultoptions = self._default_options.copy()
        user_options = {}
        if 'options' in self.inputs:
            user_options = self.inputs.options.get_dict()
        '''
        # extend options by code defaults given in code extras
        # Maybe do full recursive merge
        if 'queue_defaults' in fleur_extras:
            qd = fleur_extras['queue_defaults']
            queue = user_options.get('queue', 'default')
            defaults_queue = qd.get(queue, {})
            for key, val in defaultoptions.items():
                defaultoptions[key] = defaults_queue.get(key, val)
        '''
        if 'options' in self.inputs:
            options = user_options
        else:
            options = defaultoptions
        # we use the same options for both codes, inpgen resources get overridden
        # and queue does not matter in case of direct scheduler

        # extend options given by user using defaults
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        self.ctx.max_number_runs = self.ctx.wf_dict['fleur_runmax']
        self.ctx.description_wf = self.inputs.get('description', '') + '|fleur_scf_wc|'
        self.ctx.label_wf = self.inputs.get('label', 'fleur_scf_wc')
        self.ctx.default_itmax = self.ctx.wf_dict['itmax_per_run']
        self.ctx.straight_mixing_iters = self.ctx.wf_dict['straight_iterations']
        if self.ctx.straight_mixing_iters is None:
            self.ctx.straight_mixing_iters = self.ctx.default_itmax

        # return para/vars
        self.ctx.successful = True
        self.ctx.parse_last = True
        self.ctx.distance = []
        self.ctx.all_forces = []
        self.ctx.total_energy = []
        self.ctx.nmmp_distance = []
        self.ctx.x_torques = []
        self.ctx.y_torques = []
        self.ctx.alpha_angles = []
        self.ctx.beta_angles = []
        self.ctx.energydiff = 10000
        self.ctx.forcediff = 10000
        self.ctx.torquediff = None
        self.ctx.last_charge_density = 10000
        self.ctx.last_nmmp_distance = -10000
        self.ctx.warnings = []
        # "debug": {},
        self.ctx.errors = []
        self.ctx.info = []
        self.ctx.possible_info = [
            'Consider providing more resources',
            'Consider providing a lot more resources',
            'Consider changing the mixing scheme',
        ]
        self.ctx.fleurinp = None
        self.ctx.formula = ''
        self.ctx.total_wall_time = 0

    def validate_input(self):
        """
        # validate input and find out which path (1, or 2) to take
        # return True means run inpgen if false run fleur directly
        """
        extra_keys = []
        for key in self.ctx.wf_dict:
            if key not in self._default_wf_para:
                extra_keys.append(key)
        if extra_keys:
            error = f'ERROR: input wf_parameters for SCF contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        inputs = self.inputs
        if 'fleurinp' in inputs:
            self.ctx.run_inpgen = False
            if 'structure' in inputs:
                error = 'ERROR: structure input is not needed because Fleurinp was given'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'inpgen' in inputs:
                error = 'ERROR: inpgen code is not needed input because Fleurinp was given'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'calc_parameters' in inputs:
                error = 'ERROR: calc_parameters input is not needed because Fleurinp was given'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'remote_data' in inputs:
                warning = ('WARNING: Only initial charge density will be copied from the'
                           'given remote folder because fleurinp is given.')
                self.report(warning)
        elif 'structure' in inputs:
            self.ctx.run_inpgen = True
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'remote_data' in inputs:
                warning = ('WARNING: Only initial charge density will be copied from the'
                           'given remote folder because fleurinp is given.')
                self.report(warning)
        elif 'remote_data' in inputs:
            self.ctx.run_inpgen = False
        else:
            error = 'ERROR: No StructureData nor FleurinpData nor RemoteData was provided'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen')
            except ValueError:
                error = 'The code you provided for inpgen of FLEUR does not use the plugin fleur.inpgen'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur')
            except ValueError:
                error = ('The code you provided for FLEUR does not use the plugin fleur.fleur')
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # check the mode in wf_dict
        mode = self.ctx.wf_dict['mode']
        if mode not in ['force', 'density', 'energy', 'spex', 'torque']:
            error = "ERROR: Wrong mode of convergence: one of 'force', 'density', 'energy' or 'gw' was expected."
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        max_iters = self.ctx.wf_dict['itmax_per_run']
        if max_iters <= 1:
            error = "ERROR: 'itmax_per_run' should be equal at least 2"
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        straight_iterations = self.ctx.wf_dict['straight_iterations']
        if straight_iterations is not None and straight_iterations <= 1:
            error = "ERROR: 'straight_iterations' should be atleast 2 if given"
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        self.ctx.run_straight_mixing = self.ctx.wf_dict['initial_straight_mixing'] or \
                                       self.ctx.wf_dict['initial_ldau_straight_mixing']

        if straight_iterations is not None:
            if not self.ctx.run_straight_mixing:
                error = "ERROR: 'initial_straight_mixing' or 'initial_ldau_straight_mixing' should be True if 'straight_iterations' is given"
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # check format of inpxml_changes
        fchanges = self.ctx.wf_dict['inpxml_changes']
        if fchanges:
            for change in fchanges:
                # somehow the tuple type gets destroyed on the way and becomes a list
                if not isinstance(change, (tuple, list)):
                    error = f'ERROR: Wrong Input inpxml_changes wrong format of: {change} should be tuple of 2. I abort'
                    self.report(error)
                    return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        return

    def fleurinpgen_needed(self):
        """
        Returns True if inpgen calculation has to be submitted
        before fleur calculations
        """
        return self.ctx.run_inpgen

    def run_fleurinpgen(self):
        """
        run the inpgen
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

        # If given kpt_dist has prio over given calc_parameters
        kpt_dist = self.ctx.wf_dict['kpoints_distance']
        if kpt_dist is not None:
            cf_para_kpt = Dict({
                'distance': kpt_dist,
                'force_parity': self.ctx.wf_dict['kpoints_force_parity'],
                'force_even': self.ctx.wf_dict['kpoints_force_even'],
                'force_odd': self.ctx.wf_dict['kpoints_force_odd'],
                'include_gamma': self.ctx.wf_dict['kpoints_force_gamma']
            })
            inputs = {
                'structure': structure,
                'calc_parameters': params,
                'cf_para': cf_para_kpt,
                'metadata': {
                    'call_link_label': 'create_kpoints_from_distance'
                }
            }
            params = create_kpoints_from_distance_parameter(**inputs)

        options = {
            'max_wallclock_seconds': int(self.ctx.options.get('max_wallclock_seconds')),
            'resources': self.ctx.options.get('resources'),
            'queue_name': self.ctx.options.get('queue_name', '')
        }

        inputs_build = get_inputs_inpgen(structure,
                                         inpgencode,
                                         options,
                                         label,
                                         description,
                                         settings=settings,
                                         params=params)

        # Launch inpgen
        self.report('INFO: run inpgen')
        future = self.submit(inputs_build)

        return ToContext(inpgen=future)

    def reset_straight_mixing(self):
        """
        Turn off the straight mixing features again
        """
        if not self.ctx.fleurinp:
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        wf_dict = self.ctx.wf_dict

        fleurmode = FleurinpModifier(self.ctx.fleurinp)

        fleurmode.set_inpchanges({'itmax': self.ctx.default_itmax})
        #Take out straight mixing
        if wf_dict['initial_straight_mixing']:
            fleurmode.set_inpchanges({'imix': 'Anderson'})  #TODO: should take the actual value from before
        if wf_dict['initial_ldau_straight_mixing']:
            fleurmode.set_inpchanges({'l_linmix': False})

        # validate?
        try:
            fleurmode.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, user wanted inp.xml changes could not be applied.'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # apply
        out = fleurmode.freeze()
        self.ctx.fleurinp = out
        return

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')

        inputs = self.inputs

        # Has to never crash because corresponding check was done in validate function
        if self.ctx.fleurinp:  # something was already changed
            return

        if 'fleurinp' in inputs:
            fleurin = self.inputs.fleurinp
        elif 'structure' in inputs:
            if not self.ctx['inpgen'].is_finished_ok:
                error = 'Inpgen calculation failed'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INPGEN_CALCULATION_FAILED
            fleurin = self.ctx['inpgen'].outputs.fleurinp
        elif 'remote_data' in inputs:
            # In this case only remote_data for input structure is given
            # fleurinp data has to be generated from the remote inp.xml file to use change_fleurinp
            fleurin = get_fleurinp_from_remote_data_cf(self.inputs.remote_data)
            self.report(
                f'INFO: generated FleurinpData from files {fleurin.files} from remote folder pk={self.inputs.remote_data.pk}'
            )

        wf_dict = self.ctx.wf_dict
        force_dict = wf_dict['force_dict']
        converge_mode = wf_dict['mode']
        fchanges = wf_dict['inpxml_changes']

        fleurmode = FleurinpModifier(fleurin)

        itmax = self.ctx.default_itmax
        if self.ctx.run_straight_mixing:
            if self.ctx.loop_count == 0:
                #Set up straight mixing
                itmax = self.ctx.straight_mixing_iters  #Is set further below
                if wf_dict['initial_straight_mixing']:
                    fleurmode.set_inpchanges({'imix': 'straight'})
                if wf_dict['initial_ldau_straight_mixing']:
                    fleurmode.set_inpchanges({'l_linmix': True, 'mixParam': wf_dict['initial_ldau_straight_mix_param']})

        # set proper convergence parameters in inp.xml
        if converge_mode == 'density':
            fleurmode.set_inpchanges({'itmax': itmax, 'minDistance': wf_dict['density_converged']})
        elif converge_mode == 'force':
            fleurmode.set_inpchanges({
                'itmax': itmax,
                'minDistance': wf_dict['density_converged'],
                'force_converged': wf_dict['force_converged'],
                'l_f': True,
                'qfix': force_dict['qfix'],
                'forcealpha': force_dict['forcealpha'],
                'forcemix': force_dict['forcemix']
            })
        elif converge_mode == 'energy':
            fleurmode.set_inpchanges({'itmax': itmax, 'minDistance': 0.0})

        elif converge_mode == 'spex':
            if fleurin.inp_version >= (0, 34):
                fleurmode.set_inpchanges({'itmax': itmax, 'minDistance': 0.0, 'spex': 1})
            else:
                fleurmode.set_inpchanges({'itmax': itmax, 'minDistance': 0.0, 'gw': 1})
        elif converge_mode == 'torque':
            #TODO: Allow to select orbitals
            dist = wf_dict.get('density_converged')
            fleurmode.set_inpchanges({
                'itmax': self.ctx.default_itmax,
                'minDistance': dist,
                'l_noco': True,
                # 'numbands': 'all',
                'ctail': False
            })
            fleurmode.set_complex_tag('greensFunction',
                                      changes={
                                          'realAxis': {
                                              'ne': 5400,
                                              'ellow': -1,
                                              'elup': 1.0
                                          },
                                          'contourSemicircle': {
                                              'n': 128,
                                              'eb': -1.0,
                                              'et': 0.0,
                                              'alpha': 1.0
                                          }
                                      },
                                      create=True)
            fleurmode.set_species('all', {
                'torqueCalculation': {
                    'kkintgrCutoff': 'd',
                    'greensfElements': {
                        's': ['F', 'F', 'F', 'F'],
                        'p': ['F', 'T', 'T', 'F'],
                        'd': ['F', 'T', 'T', 'F'],
                        'f': ['F', 'F', 'F', 'F']
                    }
                }
            },
                                  create=True)
            fleurmode.set_attrib_value('l_mperp', True, tag_name='mtNocoParams')
            fleurmode.set_attrib_value('l_mperp', True, tag_name='greensFunction')

        # apply further user dependend changes
        if fchanges:
            try:
                fleurmode.add_task_list(fchanges)
            except (ValueError, TypeError) as exc:
                error = ('ERROR: Changing the inp.xml file failed. Tried to apply inpxml_changes'
                         f', which failed with {exc}. I abort, good luck next time!')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # validate?
        try:
            fleurmode.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        except (ValueError, TypeError) as exc:
            error = ('ERROR: input, user wanted inp.xml changes could not be applied.'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # apply
        out = fleurmode.freeze()
        self.ctx.fleurinp = out
        return

    def run_fleur(self):
        """
        run a FLEUR calculation
        """
        self.report('INFO: run FLEUR')

        status = self.change_fleurinp()
        if status:
            return status

        if 'settings' in self.inputs:
            settings = deepcopy(self.inputs.settings.get_dict())
        else:
            settings = None

        if self.ctx.wf_dict['drop_mixing_first_iteration'] and self.ctx.loop_count == 0:
            if settings is None:
                settings = {}
            remotecopy_list = settings.get('remove_from_remotecopy_list', [])
            if 'mixing_history*' not in remotecopy_list:
                remotecopy_list.append('mixing_history*')
            settings['remove_from_remotecopy_list'] = remotecopy_list

        if self.ctx.run_straight_mixing and self.ctx.loop_count == 1:
            status = self.reset_straight_mixing()
            if status:
                return status

            if settings is None:
                settings = {}
            else:
                settings = settings.get_dict()

            settings.setdefault('remove_from_remotecopy_list', []).append('mixing_history*')

        fleurin = self.ctx.fleurinp

        if self.ctx['last_base_wc']:
            # will this fail if fleur before failed? try needed?
            remote = self.ctx['last_base_wc'].outputs.remote_folder
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        label = ' '
        description = ' '
        if self.ctx.formula:
            label = f'scf: fleur run {self.ctx.loop_count + 1}'
            description = f'{self.ctx.description_wf} fleur run {self.ctx.loop_count + 1} on {self.ctx.formula}'
        else:
            label = f'scf: fleur run {self.ctx.loop_count + 1}'
            description = f'{self.ctx.description_wf} fleur run {self.ctx.loop_count + 1}, fleurinp given'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code,
                                          remote,
                                          fleurin,
                                          options,
                                          label,
                                          description,
                                          settings,
                                          add_comp_para=self.ctx.wf_dict['add_comp_para'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report(f'INFO: run FLEUR number: {self.ctx.loop_count}')
        self.ctx.calcs.append(future)

        return ToContext(last_base_wc=future)

    def inspect_fleur(self):
        """
        Analyse the results of the previous Calculation (Fleur or inpgen),
        checking whether it finished successfully or if not, troubleshoot the
        cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """

        self.report('INFO: inspect FLEUR')
        try:
            base_wc = self.ctx.last_base_wc
        except AttributeError:
            self.ctx.parse_last = False
            error = 'ERROR: Something went wrong I do not have a last calculation'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED

        exit_status = base_wc.exit_status
        if not base_wc.is_finished_ok:
            error = f'ERROR: Last Fleur calculation failed with exit status {exit_status}'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED

        self.ctx.parse_last = True

    def get_res(self):
        """
        Check how the last Fleur calculation went
        Parse some results.
        """
        self.report('INFO: get results FLEUR')

        mode = self.ctx.wf_dict.get('mode')
        if self.ctx.parse_last:
            last_base_wc = self.ctx.last_base_wc

            walltime = last_base_wc.outputs.output_parameters['walltime']
            if isinstance(walltime, int):
                self.ctx.total_wall_time = self.ctx.total_wall_time + walltime

            with last_base_wc.outputs.retrieved.open(FleurCalculation._OUTXML_FILE_NAME, 'rb') as outxmlfile:
                output_dict = outxml_parser(outxmlfile,
                                            minimal_mode=True,
                                            list_return=True,
                                            iteration_to_parse='all',
                                            ignore_validation=True)

            energies = output_dict.get('energy_hartree', [])
            if energies is not None:
                self.ctx.total_energy.extend(energies)

            if 'overall_density_convergence' in output_dict:
                distances = output_dict['overall_density_convergence']
            else:
                distances = output_dict.get('density_convergence', [])

            if distances is not None:
                self.ctx.distance.extend(distances)

            if 'ldau_info' in output_dict:
                nmmp_distances = output_dict['ldau_info'].get('density_matrix_distance', [])

                if nmmp_distances is not None:
                    self.ctx.nmmp_distance.extend(nmmp_distances)

            if mode == 'force':
                forces = output_dict.get('force_atoms', [])
                if forces is not None:
                    for force_iter in forces:
                        self.ctx.all_forces.append([force for atom, force in force_iter])

            if mode == 'torque':

                with last_base_wc.outputs.retrieved.open(FleurCalculation._OUTXML_FILE_NAME, 'rb') as outxmlfile:
                    output_dict_torque = outxml_parser(outxmlfile,
                                                       iteration_to_parse='all',
                                                       optional_tasks=['torques', 'noco_angles'],
                                                       ignore_validation=True)

                    x_torques = output_dict_torque.get('torque_x', [])
                    y_torques = output_dict_torque.get('torque_y', [])
                    if not isinstance(x_torques[0], list):  # only 1 iterations was done
                        x_torques = [x_torques]
                        y_torques = [y_torques]

                    # extract angles from inp.xml because out.xml causes alpha and beta to jump
                    # alpha_angles = output_dict_torque.get('noco_alpha', [])
                    # beta_angles = output_dict_torque.get('noco_beta', [])
                    alpha_angles = [x['nocoParams']['alpha'] for x in self.ctx.fleurinp.inp_dict['atomGroups']]
                    beta_angles = [x['nocoParams']['beta'] for x in self.ctx.fleurinp.inp_dict['atomGroups']]

                    self.ctx.x_torques.extend(x_torques)
                    self.ctx.y_torques.extend(y_torques)
                    self.ctx.alpha_angles = alpha_angles
                    self.ctx.beta_angles = beta_angles
        else:
            errormsg = 'ERROR: scf wc was not successful, check log for details'
            self.control_end_wc(errormsg)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED

        if not self.ctx.distance:
            # if fleur relaxes an already converged crystal it stops directly
            if mode == 'force':
                self.report('INFO: System already force converged, could not extract distance.')
                self.ctx.last_charge_density = None
            else:
                errormsg = 'ERROR: did not manage to extract charge density from the calculation'
                self.control_end_wc(errormsg)
                return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED
        else:
            self.ctx.last_charge_density = self.ctx.distance[-1]

        if self.ctx.nmmp_distance:
            if isinstance(self.ctx.nmmp_distance[-1], list):
                self.ctx.last_nmmp_distance = max(self.ctx.nmmp_distance[-1])
            else:
                self.ctx.last_nmmp_distance = self.ctx.nmmp_distance[-1]
            if self.ctx.last_nmmp_distance is None:
                self.report('No LDA+U distance found but only one iteration performed\n'
                            'Assuming that the calculatin should be continued')
                self.ctx.last_nmmp_distance = self.ctx.wf_dict['nmmp_converged'] + 1

    def condition(self):
        """
        check convergence condition
        """
        self.report('INFO: checking condition FLEUR')
        mode = self.ctx.wf_dict['mode']
        ldau_notconverged = False

        energy = self.ctx.total_energy
        if len(energy) >= 2:
            self.ctx.energydiff = abs(energy[-1] - energy[-2])

        if mode == 'force':
            forces = self.ctx.all_forces
            if len(forces) >= 2:
                self.ctx.forcediff = max(
                    abs(forces[-1][i][k] - forces[-2][i][k]) for i in range(len(forces[-1])) for k in range(3))
        else:
            self.ctx.forcediff = 'can not be determined'

        if mode == 'torque':
            x_torques = self.ctx.x_torques
            y_torques = self.ctx.y_torques
            if len(x_torques) > 1 and len(y_torques) > 1:
                max_x_torque_diff = max(abs(x_torques[-1][i] - x_torques[-2][i]) for i in range(len(x_torques[0])))
                max_y_torque_diff = max(abs(y_torques[-1][i] - y_torques[-2][i]) for i in range(len(y_torques[0])))
                self.ctx.torquediff = max(max_x_torque_diff, max_y_torque_diff)
            else:
                self.ctx.torquediff = 'can not be determined'

        if self.ctx.last_nmmp_distance > 0.0 and \
           self.ctx.last_nmmp_distance >= self.ctx.wf_dict['nmmp_converged']:
            ldau_notconverged = True

        if mode == 'density':
            if self.ctx.wf_dict['density_converged'] >= self.ctx.last_charge_density:
                if not ldau_notconverged:
                    return False
        elif mode in ('energy', 'spex'):
            if self.ctx.wf_dict['energy_converged'] >= self.ctx.energydiff:
                if not ldau_notconverged:
                    return False
        elif mode == 'force':
            if self.ctx.last_charge_density is None:
                try:
                    _ = self.ctx.last_base_wc.outputs.relax_parameters
                except NotExistent:
                    pass
                else:
                    if not ldau_notconverged:
                        return False

            elif self.ctx.wf_dict['density_converged'] >= self.ctx.last_charge_density:
                try:
                    _ = self.ctx.last_base_wc.outputs.relax_parameters
                except NotExistent:
                    pass
                else:
                    if not ldau_notconverged:
                        return False
        elif mode == 'torque':
            if self.ctx.torquediff == 'can not be determined' and self.ctx.wf_dict.get(
                    'density_converged') >= self.ctx.last_charge_density:
                if not ldau_notconverged:
                    return False
            elif self.ctx.wf_dict.get('torque_converged') >= self.ctx.torquediff:
                if not ldau_notconverged:
                    return False

        if self.ctx.loop_count >= self.ctx.max_number_runs:
            self.ctx.reached_conv = False
            return False

        if self.ctx.wf_dict['stop_if_last_distance_exceeds'] is not None:
            if mode == 'density' and \
               self.ctx.last_charge_density >= self.ctx.wf_dict['stop_if_last_distance_exceeds']:

                self.report(
                    f'Stopping because last charge density distance {self.ctx.last_charge_density} me/bohr^3'
                    f' of the last calculation exceeded the given limit of {self.ctx.wf_dict["stop_if_last_distance_exceeds"]} me/bohr^3'
                )
                self.ctx.reached_conv = False
                return False
            if mode in ('energy', 'spex') and \
               self.ctx.energydiff >= self.ctx.wf_dict['stop_if_last_distance_exceeds']:

                self.report(
                    f'Stopping because last energy difference {self.ctx.energydiff} htr'
                    f' of the last calculation exceeded the given limit of {self.ctx.wf_dict["stop_if_last_distance_exceeds"]} htr'
                )
                self.ctx.reached_conv = False
                return False

        return True

    def return_results(self):
        """
        return the results of the calculations
        This should run through and produce output nodes even if everything failed,
        therefore it only uses results from context.
        """

        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.last_base_wc.outputs.output_parameters
            retrieved = self.ctx.last_base_wc.outputs.retrieved
            last_calc_out_dict = last_calc_out.get_dict()
        except (NotExistent, AttributeError):
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None

        last_nmmp_distance = None
        if self.ctx.last_nmmp_distance > 0.0:
            last_nmmp_distance = self.ctx.last_nmmp_distance

        outputnode_dict = {}
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['material'] = self.ctx.formula
        outputnode_dict['conv_mode'] = self.ctx.wf_dict['mode']
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = last_calc_out_dict.get('number_of_iterations_total', None)
        outputnode_dict['distance_charge'] = self.ctx.last_charge_density
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = last_calc_out_dict.get('energy_hartree', None)
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['force_diff_last'] = self.ctx.forcediff
        outputnode_dict['force_largest'] = last_calc_out_dict.get('force_largest', None)
        outputnode_dict['distance_charge_units'] = 'me/bohr^3'
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['nmmp_distance'] = last_nmmp_distance
        outputnode_dict['nmmp_distance_all'] = self.ctx.nmmp_distance
        outputnode_dict['total_wall_time'] = self.ctx.total_wall_time
        outputnode_dict['total_wall_time_units'] = 's'
        outputnode_dict['info'] = self.ctx.info
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors

        if self.ctx.x_torques:
            outputnode_dict['last_x_torques'] = self.ctx.x_torques[-1]
            outputnode_dict['last_y_torques'] = self.ctx.y_torques[-1]
            outputnode_dict['alphas'] = self.ctx.alpha_angles
            outputnode_dict['betas'] = self.ctx.beta_angles

        num_iterations = last_calc_out_dict.get('number_of_iterations_total', None)
        if self.ctx.successful and self.ctx.reached_conv:
            if len(self.ctx.total_energy) <= 1:  # then len(self.ctx.all_forces) <= 1 too
                self.report('STATUS: Done, the convergence criteria are reached.\n'
                            'INFO: The charge density of the FLEUR calculation '
                            f'converged after {self.ctx.loop_count} FLEUR runs, {num_iterations} '
                            f'iterations and {self.ctx.total_wall_time} sec '
                            f'walltime to {outputnode_dict["distance_charge"]} "me/bohr^3" \n'
                            'INFO: Did not manage to get energy and largest force difference '
                            'between two last iterations, probably converged in a single iteration')
            else:
                self.report('STATUS: Done, the convergence criteria are reached.\n'
                            'INFO: The charge density of the FLEUR calculation '
                            f'converged after {self.ctx.loop_count} FLEUR runs, {num_iterations} '
                            f'iterations and {self.ctx.total_wall_time} sec '
                            f'walltime to {outputnode_dict["distance_charge"]} "me/bohr^3" \n'
                            'INFO: The total energy difference of the last two iterations '
                            f'is {self.ctx.energydiff} Htr and largest force difference is '
                            f'{self.ctx.forcediff} Htr/bohr')
        elif self.ctx.successful and not self.ctx.reached_conv:
            if len(self.ctx.total_energy) <= 1:  # then len(self.ctx.all_forces) <= 1 too
                self.report('STATUS/WARNING: Done, the maximum number of runs '
                            'was reached.\n INFO: The '
                            'charge density of the FLEUR calculation, '
                            f'after {self.ctx.loop_count} FLEUR runs, {num_iterations} '
                            f' iterations and {self.ctx.total_wall_time} sec '
                            f'walltime is {outputnode_dict["distance_charge"]} "me/bohr^3"\n'
                            'INFO: can not extract energy and largest force difference between'
                            ' two last iterations, probably converged in a single iteration')
            else:
                self.report('STATUS/WARNING: Done, the maximum number of runs '
                            'was reached.\n INFO: The '
                            'charge density of the FLEUR calculation, '
                            f'after {self.ctx.loop_count} FLEUR runs, {num_iterations} '
                            f' iterations and {self.ctx.total_wall_time} sec '
                            f'walltime is {outputnode_dict["distance_charge"]} "me/bohr^3"\n'
                            'INFO: The total energy difference of the last two iterations '
                            f'is {self.ctx.energydiff} Htr and largest force difference is'
                            f'{self.ctx.forcediff} Htr/bohr\n')
        else:  # Termination ok, but not converged yet...
            if self.ctx.abort:  # some error occurred, do not use the output.
                self.report('STATUS/ERROR: I abort, see logs and errors/warning/hints in output_scf_wc_para')

        if self.ctx.torquediff is None:
            self.ctx.torquediff = 9999
        self.report(f'Torque diff {self.ctx.torquediff}')
        outputnode_t = Dict(dict=outputnode_dict)
        if self.ctx.last_nmmp_distance > 0.0:
            self.report(f'INFO: The LDA+U density matrix is converged to {self.ctx.last_nmmp_distance} change '
                        'of all matrix elements')

        outputnode_t = Dict(outputnode_dict)
        # this is unsafe so far, because last_calc_out could not exist...
        if last_calc_out:
            outdict = create_scf_result_node(outpara=outputnode_t,
                                             last_calc_out=last_calc_out,
                                             last_calc_retrieved=retrieved)
        else:
            outdict = create_scf_result_node(outpara=outputnode_t)

        # Now it always returns changed fleurinp that was actually used in the calculation
        if self.ctx.fleurinp is not None:
            outdict['fleurinp'] = self.ctx.fleurinp

        if self.ctx.last_base_wc:
            self.out_many(self.exposed_outputs(self.ctx.last_base_wc, FleurBaseWorkChain, namespace='last_calc'))

        #outdict['output_scf_wc_para'] = outputnode
        for link_name, node in outdict.items():
            self.out(link_name, node)

        if not self.ctx.reached_conv:
            return self.exit_codes.ERROR_DID_NOT_CONVERGE

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_scf_result_node(**kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in kwargs.items():
        if key == 'outpara':  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_scf_wc_para'
    outputnode.description = ('Contains self-consistency results and information of an fleur_scf_wc run.')

    outdict['output_scf_wc_para'] = outputnode
    # copy, because we rather produce the same node twice then have a circle in the database for now
    #output_para = args[0]
    # return {'output_eos_wc_para'}
    return outdict
