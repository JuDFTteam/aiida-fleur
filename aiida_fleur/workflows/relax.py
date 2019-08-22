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
    In this module you find the workflow 'FleurRelaxWorkChain' for geometry optimization.
"""
from __future__ import absolute_import
from __future__ import print_function
import copy

import six

from aiida.engine import WorkChain, ToContext, while_
from aiida.engine import calcfunction as cf
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import cleanup_inputs
from aiida_fleur.workflows.scf import FleurScfWorkChain

# pylint: disable=invalid-name
StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurRelaxWorkChain(WorkChain):
    """
    This workflow performs structure optimization.
    """

    _workflowversion = "0.1.0"

    _default_options = {
        'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        'max_wallclock_seconds': 2*60*60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}}

    _wf_default = {
        'fleur_runmax': 10,
        'serial': False,
        'itmax_per_run': 30,
        'alpha_mix': 0.015,
        'relax_iter': 5,
        'force_converged': 0.0002,
        'force_dict': {'qfix': 2,
                       'forcealpha': 0.5,
                       'forcemix': 2},
        'force_criterion': 0.001,
        'inpxml_changes': [],
    }

    _scf_keys = ['fleur_runmax', 'density_criterion', 'serial', 'itmax_per_run',
                 'inpxml_changes', 'force_dict', 'force_converged']  #  scf workflow

    @classmethod
    def define(cls, spec):
        super(FleurRelaxWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False,
                   default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=False)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("remote", valid_type=RemoteData, required=False)
        spec.input("fleurinp", valid_type=FleurInpData, required=False)
        spec.input("options", valid_type=Dict, required=False,
                   default=Dict(dict=cls._default_options))

        spec.outline(
            cls.start,
            cls.validate,
            cls.converge_scf,
            while_(cls.condition)(
                cls.generate_new_fleurinp,
                cls.converge_scf,
            ),
            cls.get_results,
            cls.return_results,
        )

        spec.output('out', valid_type=Dict)
        spec.output('optimized_structure', valid_type=StructureData)

        # exit codes
        spec.exit_code(301, 'ERROR_INVALID_INPUT_RESOURCES',
                       message="Invalid input, please check input configuration.")
        spec.exit_code(302, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED',
                       message="Some required inputs are missing.")
        spec.exit_code(303, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")
        spec.exit_code(305, 'ERROR_CHANGING_FLEURINPUT_FAILED',
                       message="Input file modification failed.")
        spec.exit_code(306, 'ERROR_CALCULATION_INVALID_INPUT_FILE',
                       message="Input file is corrupted after user's modifications.")
        spec.exit_code(307, 'ERROR_FLEUR_CALCULATION_FALIED',
                       message="Fleur calculation failed.")
        spec.exit_code(308, 'ERROR_DID_NOT_CONVERGE',
                       message="Optimization cycle did not lead to convergence of forces.")
        spec.exit_code(309, 'ERROR_REFERENCE_CALCULATION_FAILED',
                       message="Reference scf calculation failed.")
        spec.exit_code(310, 'ERROR_REFERENCE_CALCULATION_NOREMOTE',
                       message="Found no reference calculation remote repository.")
        spec.exit_code(314, 'ERROR_RELAX_FAILED',
                       message="New positions calculation failed.")
        spec.exit_code(315, 'ERROR_NO_RELAX_OUTPUT',
                       message="Found no relax.xml file in retrieved folder")

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started relaxation of a structure workflow version {}\n'
                    ''.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        # Pre-initialization of some variables
        self.ctx.loop_count = 0
        self.ctx.forces = []
        self.ctx.final_cell = None
        self.ctx.final_atom_positions = None
        self.ctx.pbc = None
        self.ctx.reached_relax = True

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # set up mixing parameter alpha
        self.ctx.wf_dict['inpxml_changes'].append(
            ('set_inpchanges', {'change_dict': {'alpha': self.ctx.wf_dict['alpha_mix']}}))

        # initialize the dictionary using defaults if no options are given
        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        # Check if user gave valid inpgen and fleur execulatbles
        inputs = self.inputs
        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

    def validate(self):
        """
        This function analyses inputs nodes and decides what
        is the input mode:

        1. Fleurinp is given -> converge, cycle
        2. Fleurinp and remote are given -> take cdn1 from remote, converge, cycle
        3. Remote is given -> take inp.xml and cdn1 from remote, converge, cycle
        4. Structure is given -> run inpgen, converge, cycle
        
        """
        inputs = cleanup_inputs(self.inputs)

        if 'fluerinp' in inputs:
            self.ctx.run_inpgen = False
            if 'structure' in inputs:
                self.report('Structure data node will be ignored because fleurinp is given')
            if 'remote' in inputs:
                self.report('Initial charge density will be taken from given remote folder')
        elif 'remote' in inputs:
            self.ctx.run_inpgen = False
            if 'structure' in inputs:
                self.report('Structure data node will be ignored because fleurinp is given')
        elif 'structure' in inputs:
            self.ctx.run_inpgen = True
            if 'inpgen' not in inputs:
                return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES
        else:
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

    def converge_scf(self):
        """
        Converge charge density for collinear case.
        """
        inputs = {}
        if self.ctx.loop_count:
            inputs = self.get_inputs_scf()
        else:
            inputs = self.get_inputs_first_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(scf_res=res)

    def get_inputs_first_scf(self):
        """
        Initialize inputs for the first scf cycle
        """
        inputs = cleanup_inputs(self.inputs)

        input_scf = {}

        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)

        input_scf['wf_parameters'] = copy.deepcopy(scf_wf_param)
        input_scf['wf_parameters']['mode'] = 'force'
        input_scf['wf_parameters'] = Dict(dict=input_scf['wf_parameters'])

        input_scf['options'] = self.ctx.options
        input_scf['options'] = Dict(dict=input_scf['options'])

        input_scf['fleur'] = self.inputs.fleur

        if 'fluerinp' in inputs:
            input_scf['fleurinp'] = inputs.fleurinp
            if 'remote' in inputs:
                input_scf['remote_data'] = inputs.remote
        elif 'remote' in inputs:
            input_scf['remote_data'] = inputs.remote
        elif 'structure' in inputs:
            input_scf['structure'] = inputs.structure
            input_scf['inpgen'] = inputs.inpgen
            if 'calc_parameters' in inputs:
                input_scf['calc_parameters'] = inputs.calc_parameters
        return input_scf

    def get_inputs_scf(self):
        """
        Initialize inputs for the first scf cycle
        """
        input_scf = {}

        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)

        input_scf['wf_parameters'] = copy.deepcopy(scf_wf_param)
        input_scf['wf_parameters']['mode'] = 'force'
        input_scf['wf_parameters'] = Dict(dict=input_scf['wf_parameters'])

        input_scf['options'] = self.ctx.options
        input_scf['options'] = Dict(dict=input_scf['options'])

        input_scf['fleur'] = self.inputs.fleur

        scf_wc = self.ctx.scf_res
        last_calc = load_node(scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])

        # take cdn_last; take inp.xml and relax.xml if fleurinp in None
        input_scf['remote_data'] = last_calc.outputs.remote_folder
        if self.ctx.new_fleurinp:
            input_scf['fleurinp'] = self.ctx.new_fleurinp

        return input_scf

    def condition(self):
        """
        Returns True if structure is optimised
        and False otherwise
        """
        try:
            scf_wc = self.ctx.scf_res
            if not scf_wc.is_finished_ok:
                # message = ('ERROR: scf cycle failed, it has an '
                #            'exit status {}'.format(scf_wc.exit_status))
                # self.control_end_wc(message)
                # return self.exit_codes.ERROR_RELAX_FAILED
                return False
        except AttributeError:
            # message = 'ERROR: Something went wrong I do not have new atom positions calculation'
            # self.control_end_wc(message)
            # return self.exit_codes.ERROR_RELAX_FAILED
            return False

        try:
            self.ctx.forces.append(scf_wc.outputs.output_scf_wc_para.dict.force_largest)
        except AttributeError:
            message = 'ERROR: Did not manage to read the largest force'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_RELAX_FAILED

        largest_now = abs(self.ctx.forces[-1])

        if largest_now < self.ctx.wf_dict['force_criterion']:
            self.report('Structure is converged to the largest force'
                        '{}'.format(self.ctx.forces[-1]))
            return False

        if self.ctx.loop_count == self.ctx.wf_dict['relax_iter']:
            self.ctx.reached_relax = False
            return False

        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report('INFO: submit optimization iteration number {}. Largest force is {}, '
                    'force criterion is {}'.format(self.ctx.loop_count, largest_now,
                                                   self.ctx.wf_dict['force_criterion']))

        return True

    def generate_new_fleurinp(self):
        """
        This fuction generates a new fleurinp if needed
        """
        scf_wc = self.ctx.scf_res
        last_calc = load_node(scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])
        try:
            relax_parsed = last_calc.outputs.relax_parameters
        except NotExistent:
            return self.exit_codes.ERROR_NO_RELAX_OUTPUT

        new_fleurinp = self.analyse_relax(relax_parsed)

        self.ctx.new_fleurinp = new_fleurinp

    @staticmethod
    def analyse_relax(relax_dict):
        """
        This fuction generates a new fleurinp if needed
        """
        # TODO: implement this function, now always use relax.xml gemerated in FLEUR
        if False:
            return 1

        return None

    def get_results(self):
        """
        Generates results of the workchain.
        Creates a new structure data node which is an
        optimized structure
        """
        try:
            relax_out = self.ctx.scf_res.outputs.last_fleur_calc_output
        except NotExistent:
            return self.exit_codes.ERROR_NO_RELAX_OUTPUT

        relax_out = relax_out.get_dict()

        try:
            cell = relax_out['relax_brav_vectors']
            atom_positions = relax_out['relax_atom_positions']
            film = relax_out['film']
        except KeyError:
            return self.exit_codes.ERROR_NO_RELAX_OUTPUT

        self.ctx.final_cell = cell
        self.ctx.final_atom_positions = atom_positions

        if film == 'True':
            self.ctx.pbc = (True, True, False)
        else:
            self.ctx.pbc = (True, True, True)

    def return_results(self):
        """
        This function outputs results of the wc
        """

        out = {'workflow_name': self.__class__.__name__,
               'workflow_version': self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'info': self.ctx.info,
               'warnings': self.ctx.warnings,
               'errors': self.ctx.errors,
               'force': self.ctx.forces,
               'force_iter_done': self.ctx.loop_count
              }

        if self.ctx.final_cell:
            structure = StructureData(cell=self.ctx.final_cell)

            for atom in self.ctx.final_atom_positions:
                structure.append_atom(position=(atom[1], atom[2], atom[3]), symbols=atom[0])

            structure.pbc = self.ctx.pbc
            structure = save_structure(structure)
            self.out('optimized_structure', structure)

        out = save_output_node(Dict(dict=out))
        self.out('out', out)
        if not self.ctx.reached_relax:
            return self.exit_codes.ERROR_DID_NOT_CONVERGE

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()

@cf
def save_structure(structure):
    """
    Save a structure data node
    """
    structure_return = structure.clone()
    return structure_return

@cf
def save_output_node(out):
    """
    This calcfunction saves the out dict in the db
    """
    out_wc = out.clone()
    return out_wc
