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
In this module you find the workchain 'FleurScfWorkChain' for the self-consistency
cycle management of a FLEUR calculation with AiiDA.
"""
# TODO: more info in output, log warnings
# TODO: make smarter, ggf delete broyd or restart with more or less iterations
# you can use the pattern of the density convergence for this
# TODO: maybe write dict schema for wf_parameter inputs, how?
# TODO: clean up exit codes and its messages
from __future__ import absolute_import
from lxml import etree
from lxml.etree import XMLSyntaxError
import six
from six.moves import range

from aiida.plugins import DataFactory
from aiida.orm import Code, load_node, CalcJobNode
from aiida.engine import WorkChain, while_, if_, ToContext
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent

from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import cleanup_inputs
from aiida_fleur.tools.xml_util import eval_xpath2, get_xml_attribute
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain

# pylint: disable=invalid-name
RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurScfWorkChain(WorkChain):
    """
    Workchain for converging a FLEUR calculation (SCF).

    It converges the charge density.
    Two paths are possible:

    (1) Start from a structure and run the inpgen first optional with calc_parameters
    (2) Start from a Fleur calculation, with optional remoteData

    :params wf_parameters: (Dict), Workchain Specifications
    :params structure: (StructureData), Crystal structure
    :params calc_parameters: (Dict), Inpgen Parameters
    :params fleurinp: (FleurinpData), to start with a Fleur calculation
    :params remote_data: (RemoteData), from a Fleur calculation
    :params inpgen: (Code)
    :params fleur: (Code)

    :returns output_scf_wc_para: (Dict), Information of workflow results
        like Success, last result node, list with convergence behavior
    """

    _workflowversion = "0.4.0"
    _wf_default = {'fleur_runmax': 4,
                   'density_converged': 0.00002,
                   'energy_converged': 0.002,
                   'force_converged': 0.002,
                   'mode': 'density',  # 'density', 'energy' or 'force'
                   'serial': False,
                   'itmax_per_run': 30,
                   'force_dict': {'qfix': 2,
                                  'forcealpha': 0.5,
                                  'forcemix': 'BFGS'},
                   'inpxml_changes': [],
                  }

    _default_options = {
        'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        'max_wallclock_seconds': 6*60*60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}}

    @classmethod
    def define(cls, spec):
        super(FleurScfWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False,
                   default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("settings", valid_type=Dict, required=False)
        spec.input("options", valid_type=Dict, required=False,
                   default=Dict(dict=cls._default_options))
        spec.input("fleurinp", valid_type=FleurInpData, required=False)
        spec.input("remote_data", valid_type=RemoteData, required=False)
        spec.input("inpgen", valid_type=Code, required=False)
        spec.input("fleur", valid_type=Code, required=True)

        spec.outline(
            cls.start,
            cls.validate_input,
            if_(cls.fleurinpgen_needed)(
                cls.run_fleurinpgen),
            cls.run_fleur,
            cls.inspect_fleur,
            cls.get_res,
            while_(cls.condition)(
                cls.run_fleur,
                cls.inspect_fleur,
                cls.get_res),
            cls.return_results
        )

        spec.output('fleurinp', valid_type=FleurInpData)
        spec.output('output_scf_wc_para', valid_type=Dict)
        spec.output('last_fleur_calc_output', valid_type=Dict)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_RESOURCES',
                       message="Invalid input, please check input configuration.")
        spec.exit_code(231, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")
        spec.exit_code(232, 'ERROR_CHANGING_FLEURINPUT_FAILED',
                       message="Input file modification failed.")
        spec.exit_code(233, 'ERROR_INVALID_INPUT_FILE',
                       message="Input file is corrupted after user's modifications.")
        spec.exit_code(360, 'ERROR_INPGEN_CALCULATION_FAILED',
                       message="Inpgen calculation failed.")
        spec.exit_code(361, 'ERROR_FLEUR_CALCULATION_FAILED',
                       message="Fleur calculation failed.")
        spec.exit_code(362, 'ERROR_DID_NOT_CONVERGE',
                       message="SCF cycle did not lead to convergence.")

    def start(self):
        """
        init context and some parameters
        """
        self.report('INFO: started convergence workflow version {}'
                    ''.format(self._workflowversion))

        ####### init    #######

        # internal para /control para
        self.ctx.last_calc = None
        self.ctx.loop_count = 0
        self.ctx.relax_generated = False
        self.ctx.calcs = []
        self.ctx.abort = False
        self.ctx.reached_conv = True

        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        self.ctx.serial = self.ctx.wf_dict.get('serial', False)

        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        self.ctx.max_number_runs = self.ctx.wf_dict.get('fleur_runmax', 4)
        self.ctx.description_wf = self.inputs.get(
            'description', '') + '|fleur_scf_wc|'
        self.ctx.label_wf = self.inputs.get('label', 'fleur_scf_wc')
        self.ctx.default_itmax = self.ctx.wf_dict.get('itmax_per_run', 30)

        # return para/vars
        self.ctx.successful = True
        self.ctx.parse_last = True
        self.ctx.distance = []
        self.ctx.all_forces = []
        self.ctx.total_energy = []
        self.ctx.energydiff = 10000
        self.ctx.forcediff = 10000
        self.ctx.last_charge_density = 10000
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
        inputs = cleanup_inputs(self.inputs)

        if 'fleurinp' in inputs:
            self.ctx.run_inpgen = False
            if 'structure' in inputs:
                warning = 'WARNING: Ignoring Structure input because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'inpgen' in inputs:
                warning = 'WARNING: Ignoring inpgen code input because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input because Fleurinp was given'
                self.ctx.warnings.append(warning)
                self.report(warning)
            if 'remote_data' in inputs:
                warning = ('WARNING: Only initial charge density will be copied from the'
                           'given remote folder because fleurinp is given.')
                self.report(warning)
        elif 'remote_data' in inputs:
            self.ctx.run_inpgen = False
        elif 'structure' in inputs:
            self.ctx.run_inpgen = True
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES
        else:
            error = 'ERROR: No StructureData nor FleurinpData nor RemoteData was provided'
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(
                    inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(
                    inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # check the mode in wf_dict
        mode = self.ctx.wf_dict.get('mode')
        if mode not in ['force', 'density', 'energy']:
            error = ("ERROR: Wrong mode of convergence"
                     ": one of 'force', 'density' or 'energy' was expected.")
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        max_iters = self.ctx.wf_dict.get('itmax_per_run')
        if max_iters <= 1:
            error = ("ERROR: 'itmax_per_run' should be equal at least 2")
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        # check format of inpxml_changes
        fchanges = self.ctx.wf_dict.get('inpxml_changes', [])
        if fchanges:
            for change in fchanges:
                # somehow the tuple type gets destroyed on the way and becomes a list
                if (not isinstance(change, tuple)) and (not isinstance(change, list)):
                    error = ('ERROR: Wrong Input inpxml_changes wrong format of'
                             ': {} should be tuple of 2. I abort'.format(change))
                    return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES
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
        structure = self.inputs.structure
        self.ctx.formula = structure.get_formula()
        label = 'scf: inpgen'
        description = '{} inpgen on {}'.format(
            self.ctx.description_wf, self.ctx.formula)

        inpgencode = self.inputs.inpgen
        if 'calc_parameters' in self.inputs:
            params = self.inputs.calc_parameters
        else:
            params = None

        options = {"max_wallclock_seconds": int(self.ctx.options.get('max_wallclock_seconds')),
                   "resources": self.ctx.options.get('resources'),
                   "queue_name": self.ctx.options.get('queue_name', '')}
        # TODO do not use the same option for inpgen as for FLEUR; so far we ignore the other
        # clean Idea might be to provide second inpgen options

        inputs_build = get_inputs_inpgen(
            structure, inpgencode, options, label, description, params=params)
        self.report('INFO: run inpgen')
        future = self.submit(inputs_build)

        return ToContext(inpgen=future)

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')

        inputs = cleanup_inputs(self.inputs)

        # Has to never crash because corresponding check was done in validate function
        if self.ctx.fleurinp:  # something was already changed
            return
        elif 'fleurinp' in inputs:
            fleurin = self.inputs.fleurinp
        elif 'remote_data' in inputs:
            # In this case only remote_data for input structure is given
            # fleurinp data has to be generated from the remote inp.xml file to use change_fleurinp
            remote_node = self.inputs.remote_data
            for link in remote_node.get_incoming().all():
                if isinstance(link.node, CalcJobNode):
                    parent_calc_node = link.node
            retrieved_node = parent_calc_node.get_outgoing().get_node_by_label('retrieved')
            try:
                fleurin = FleurInpData(files=['inp.xml', 'relax.xml'], node=retrieved_node)
                self.report('INFO: generated FleurinpData from inp.xml and relax.xml')
            except ValueError:
                fleurin = FleurInpData(files=['inp.xml'], node=retrieved_node)
                self.report('INFO: generated FleurinpData from inp.xml')
            fleurin.store()
        elif 'structure' in inputs:
            # only structure is given, no remote nor fleurinp
            if not self.ctx['inpgen'].is_finished_ok:
                error = 'Inpgen calculation failed'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INPGEN_CALCULATION_FAILED
            fleurin = self.ctx['inpgen'].outputs.fleurinpData

        wf_dict = self.ctx.wf_dict
        force_dict = wf_dict.get('force_dict')
        converge_mode = wf_dict.get('mode')
        fchanges = wf_dict.get('inpxml_changes', [])

        fleurmode = FleurinpModifier(fleurin)

        # set proper convergence parameters in inp.xml
        if converge_mode == 'density':
            dist = wf_dict.get('density_converged')
            fleurmode.set_inpchanges(
                {'itmax': self.ctx.default_itmax, 'minDistance': dist})
        elif converge_mode == 'force':
            force_converged = wf_dict.get('force_converged')
            dist = 0.0
            fleurmode.set_inpchanges({'itmax': self.ctx.default_itmax, 'minDistance': dist,
                                      'force_converged': force_converged, 'l_f': True,
                                      'qfix': force_dict.get('qfix'),
                                      'forcealpha': force_dict.get('forcealpha'),
                                      'forcemix': force_dict.get('forcemix')})
        elif converge_mode == 'energy':
            dist = 0.0
            fleurmode.set_inpchanges(
                {'itmax': self.ctx.default_itmax, 'minDistance': dist})

        avail_ac_dict = fleurmode.get_avail_actions()

        # apply further user dependend changes
        if fchanges:
            for change in fchanges:
                function = change[0]
                para = change[1]
                method = avail_ac_dict.get(function, None)
                if not method:
                    error = ("ERROR: Input 'inpxml_changes', function {} "
                             "is not known to fleurinpmodifier class, "
                             "please check/test your input. I abort..."
                             "".format(method))
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

                else:  # apply change
                    method(**para)

        # validate?
        apply_c = True
        try:
            fleurmode.show(display=False, validate=True)
        except XMLSyntaxError:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            # fleurmode.show(display=True)#, validate=True)
            self.report(error)
            apply_c = False
            return self.exit_codes.ERROR_INVALID_INPUT_FILE

        # apply
        if apply_c:
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

        fleurin = self.ctx.fleurinp

        if 'settings' in self.inputs:
            settings = self.inputs.settings
        else:
            settings = None

        if self.ctx['last_calc']:
            # will this fail if fleur before failed? try needed?
            remote = self.ctx['last_calc'].outputs.remote_folder
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        label = ' '
        description = ' '
        if self.ctx.formula:
            label = 'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = '{} fleur run {} on {}'.format(
                self.ctx.description_wf, self.ctx.loop_count+1, self.ctx.formula)
        else:
            label = 'scf: fleur run {}'.format(self.ctx.loop_count+1)
            description = '{} fleur run {}, fleurinp given'.format(
                self.ctx.description_wf, self.ctx.loop_count+1)

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(
            code, remote, fleurin, options, label, description, settings, serial=self.ctx.serial)
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report('INFO: run FLEUR number: {}'.format(self.ctx.loop_count))
        self.ctx.calcs.append(future)

        return ToContext(last_calc=future)

    def inspect_fleur(self):
        """
        Analyse the results of the previous Calculation (Fleur or inpgen),
        checking whether it finished successfully or if not, troubleshoot the
        cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """

        self.report('INFO: inspect FLEUR')
        try:
            calculation = self.ctx.last_calc
        except AttributeError:
            self.ctx.parse_last = False
            error = 'ERROR: Something went wrong I do not have a last calculation'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED

        exit_status = calculation.exit_status
        if not calculation.is_finished_ok:
            error = ('ERROR: Last Fleur calculation failed '
                     'with exit status {}'.format(exit_status))
            self.control_end_wc(error)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED
        else:
            self.ctx.parse_last = True

    def get_res(self):
        """
        Check how the last Fleur calculation went
        Parse some results.
        """
        self.report('INFO: get results FLEUR')

        xpath_energy = '/fleurOutput/scfLoop/iteration/totalEnergy/@value'
        xpath_iter = '/fleurOutput/scfLoop/iteration'
        xpath_force = 'totalForcesOnRepresentativeAtoms/forceTotal'

        # be aware of magnetism
        xpath_distance = '/fleurOutput/scfLoop/iteration/densityConvergence/chargeDensity/@distance'
        overallchargedensity_xpath = ('/fleurOutput/scfLoop/iteration/densityConvergence/'
                                      'overallChargeDensity/@distance')

        mode = self.ctx.wf_dict.get('mode')
        if self.ctx.parse_last:
            last_calc = self.ctx.last_calc

            # TODO: dangerous, can fail, error catching
            # TODO: is there a way to use a standard parser?
            out_para = last_calc.outputs.output_parameters
            fleur_calcjob = load_node(out_para.get_dict()['CalcJob_uuid'])
            outxmlfile_opened = last_calc.outputs.retrieved.open(
                fleur_calcjob.process_class._OUTXML_FILE_NAME, 'r')

            walltime = last_calc.outputs.output_parameters.dict.walltime
            if isinstance(walltime, int):
                self.ctx.total_wall_time = self.ctx.total_wall_time + walltime

            tree = etree.parse(outxmlfile_opened)
            root = tree.getroot()

            energies = eval_xpath2(root, xpath_energy)
            for energy in energies:
                self.ctx.total_energy.append(float(energy))

            overall_distances = eval_xpath2(root, overallchargedensity_xpath)
            if not overall_distances:
                distances = eval_xpath2(root, xpath_distance)
                for distance in distances:
                    self.ctx.distance.append(float(distance))
            else:
                for distance in overall_distances:
                    self.ctx.distance.append(float(distance))

            if mode == 'force':
                iter_all = eval_xpath2(root, xpath_iter)
                for iteration in iter_all:
                    forces = eval_xpath2(iteration, xpath_force)
                    forces_in_iter = []
                    for force in forces:
                        force_x = float(get_xml_attribute(force, 'F_x'))
                        force_y = float(get_xml_attribute(force, 'F_y'))
                        force_z = float(get_xml_attribute(force, 'F_z'))

                        forces_in_iter.append(force_x)
                        forces_in_iter.append(force_y)
                        forces_in_iter.append(force_z)

                    self.ctx.all_forces.append(forces_in_iter)
            outxmlfile_opened.close()
        else:
            errormsg = 'ERROR: scf wc was not successful, check log for details'
            self.control_end_wc(errormsg)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED

        if not self.ctx.distance:
            errormsg = 'ERROR: did not manage to extract charge density from the calculation'
            self.control_end_wc(errormsg)
            return self.exit_codes.ERROR_FLEUR_CALCULATION_FAILED
        else:
            self.ctx.last_charge_density = self.ctx.distance[-1]

    def condition(self):
        """
        check convergence condition
        """
        self.report('INFO: checking condition FLEUR')
        mode = self.ctx.wf_dict.get('mode')

        energy = self.ctx.total_energy
        if len(energy) >= 2:
            self.ctx.energydiff = abs(energy[-1]-energy[-2])

        if mode == 'force':
            forces = self.ctx.all_forces
            if len(forces) >= 2:
                self.ctx.forcediff = max(
                    [abs(forces[-1][i] - forces[-2][i]) for i in range(len(forces[-1]))])
        else:
            self.ctx.forcediff = 'can not be determined'

        if mode == 'density':
            if self.ctx.wf_dict.get('density_converged') >= self.ctx.last_charge_density:
                return False
        elif mode == 'energy':
            if self.ctx.wf_dict.get('energy_converged') >= self.ctx.energydiff:
                return False
        elif mode == 'force':
            try:
                _ = self.ctx.last_calc.outputs.relax_parameters
            except NotExistent:
                pass
            else:
                return False

        if self.ctx.loop_count >= self.ctx.max_number_runs:
            self.ctx.reached_conv = False
            return False

        return True

    def return_results(self):
        """
        return the results of the calculations
        This should run through and produce output nodes even if everything failed,
        therefore it only uses results from context.
        """
        try:
            out_param = self.ctx.last_calc.outputs.output_parameters
            last_calc_uuid = out_param.get_dict()['CalcJob_uuid']
        except NotExistent:
            last_calc_uuid = None

        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.last_calc.outputs.output_parameters
            retrieved = self.ctx.last_calc.outputs.retrieved
            last_calc_out_dict = last_calc_out.get_dict()
        except (NotExistent, AttributeError):
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None

        outputnode_dict = {}
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['material'] = self.ctx.formula
        outputnode_dict['conv_mode'] = self.ctx.wf_dict.get('mode')
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['iterations_total'] = last_calc_out_dict.get(
            'number_of_iterations_total', None)
        outputnode_dict['distance_charge'] = self.ctx.last_charge_density
        outputnode_dict['distance_charge_all'] = self.ctx.distance
        outputnode_dict['total_energy'] = last_calc_out_dict.get('energy_hartree', None)
        outputnode_dict['total_energy_all'] = self.ctx.total_energy
        outputnode_dict['force_diff_last'] = self.ctx.forcediff
        outputnode_dict['force_largest'] = last_calc_out_dict.get('force_largest', None)
        outputnode_dict['distance_charge_units'] = 'me/bohr^3'
        outputnode_dict['total_energy_units'] = 'Htr'
        outputnode_dict['last_calc_uuid'] = last_calc_uuid
        outputnode_dict['total_wall_time'] = self.ctx.total_wall_time
        outputnode_dict['total_wall_time_units'] = 's'
        outputnode_dict['info'] = self.ctx.info
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors

        if self.ctx.successful and self.ctx.reached_conv:
            if len(self.ctx.total_energy) <= 1:  # then len(self.ctx.all_forces) <= 1 too
                self.report('STATUS: Done, the convergence criteria are reached.\n'
                            'INFO: The charge density of the FLEUR calculation '
                            'converged after {} FLEUR runs, {} iterations and {} sec '
                            'walltime to {} "me/bohr^3" \n'
                            'INFO: Did not manage to get energy and largest force difference '
                            'between two last iterations, probably converged in a single iteration'
                            ''.format(self.ctx.loop_count,
                                      last_calc_out_dict.get('number_of_iterations_total', None),
                                      self.ctx.total_wall_time,
                                      outputnode_dict['distance_charge']))
            else:
                self.report('STATUS: Done, the convergence criteria are reached.\n'
                            'INFO: The charge density of the FLEUR calculation '
                            'converged after {} FLEUR runs, {} iterations and {} sec '
                            'walltime to {} "me/bohr^3" \n'
                            'INFO: The total energy difference of the last two iterations '
                            'is {} Htr and largest force difference is {} Htr/bohr'
                            ''.format(self.ctx.loop_count,
                                      last_calc_out_dict.get('number_of_iterations_total', None),
                                      self.ctx.total_wall_time,
                                      outputnode_dict['distance_charge'],
                                      self.ctx.energydiff,
                                      self.ctx.forcediff))
        elif self.ctx.successful and not self.ctx.reached_conv:
            if len(self.ctx.total_energy) <= 1:  # then len(self.ctx.all_forces) <= 1 too
                self.report('STATUS/WARNING: Done, the maximum number of runs '
                            'was reached.\n INFO: The '
                            'charge density of the FLEUR calculation, '
                            'after {} FLEUR runs, {} iterations and {} sec '
                            'walltime is {} "me/bohr^3"\n'
                            'INFO: can not extract energy and largest force difference between'
                            ' two last iterations, probably converged in a single iteration'
                            ''.format(self.ctx.loop_count,
                                      last_calc_out_dict.get(
                                          'number_of_iterations_total', None),
                                      self.ctx.total_wall_time,
                                      outputnode_dict['distance_charge']))
            else:
                self.report('STATUS/WARNING: Done, the maximum number of runs '
                            'was reached.\n INFO: The '
                            'charge density of the FLEUR calculation, '
                            'after {} FLEUR runs, {} iterations and {} sec '
                            'walltime is {} "me/bohr^3"\n'
                            'INFO: The total energy difference of the last two iterations '
                            'is {} Htr and largest force difference is {} Htr/bohr\n'
                            ''.format(self.ctx.loop_count,
                                      last_calc_out_dict.get(
                                          'number_of_iterations_total', None),
                                      self.ctx.total_wall_time,
                                      outputnode_dict['distance_charge'],
                                      self.ctx.energydiff,
                                      self.ctx.forcediff))
        else:  # Termination ok, but not converged yet...
            if self.ctx.abort:  # some error occurred, do not use the output.
                self.report('STATUS/ERROR: I abort, see logs and '
                            'errors/warning/hints in output_scf_wc_para')

        outputnode_t = Dict(dict=outputnode_dict)
        # this is unsafe so far, because last_calc_out could not exist...
        if last_calc_out:
            outdict = create_scf_result_node(
                outpara=outputnode_t, last_calc_out=last_calc_out, last_calc_retrieved=retrieved)
        else:
            outdict = create_scf_result_node(outpara=outputnode_t)

        # Now it always returns changed fleurinp that was actually used in the calculation
        if self.ctx.fleurinp is not None:
            outdict['fleurinp'] = self.ctx.fleurinp

        if last_calc_out:
            outdict['last_fleur_calc_output'] = last_calc_out

        #outdict['output_scf_wc_para'] = outputnode
        for link_name, node in six.iteritems(outdict):
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
    for key, val in six.iteritems(kwargs):
        if key == 'outpara':  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_scf_wc_para'
    outputnode.description = ('Contains self-consistency results and '
                              'information of an fleur_scf_wc run.')

    outdict['output_scf_wc_para'] = outputnode
    # copy, because we rather produce the same node twice then have a circle in the database for now
    #output_para = args[0]
    # return {'output_eos_wc_para'}
    return outdict
