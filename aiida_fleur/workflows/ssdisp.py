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
    In this module you find the workflow 'FleurSSDispWorkChain' for the calculation of
    spin spiral dispersion using scalar-relatevistic Hamiltonian.
"""

import copy

from ase.dft.kpoints import monkhorst_pack

from aiida.engine import ToContext
from aiida.engine import calcfunction as cf
from aiida.orm import load_node
from aiida.orm import Dict, KpointsData
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from pyfleur.util.constants import HTR_TO_EV

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows._force_theorem import FleurForceTheoremWorkChain
from aiida_fleur.data.fleurinpmodifier import inpxml_changes
from aiida_fleur.workflows._base import merge_parameter_dicts, unknown_parameter_keys
from aiida_fleur.workflows._base import apply_inpxml_changes
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinp import get_fleurinp_from_remote_data


class FleurSSDispWorkChain(FleurForceTheoremWorkChain):
    """
    This workflow calculates spin spiral dispersion of a structure.
    """

    _workflowversion = '0.4.0'

    _OUTPUT_NAME = 'output_ssdisp_wc_para'
    _FT_LABEL = 'SSDisp_force_theorem'
    _FT_DESCRIPTION = ('This is the force theorem calculation for Spin Spiral Dispersion.')

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

    _default_wf_para = {
        'beta': {
            'all': 1.57079
        },
        'prop_dir': [1.0, 0.0, 0.0],
        'q_vectors': [[0.0, 0.0, 0.0], [0.125, 0.0, 0.0], [0.250, 0.0, 0.0], [0.375, 0.0, 0.0]],
        'ref_qss': [0.0, 0.0, 0.0],
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'kmesh_force_theorem': None,
        'inpxml_changes': []
    }


    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report(f'INFO: started Spin Stiffness calculation workflow version {self._workflowversion}\n')
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []

        # initialize the dictionary using defaults if no wf paramters are given
        wf_dict = self.inputs.wf_parameters.get_dict() if 'wf_parameters' in self.inputs else {}
        extra_keys = unknown_parameter_keys(wf_dict, self._default_wf_para)
        if extra_keys:
            self.report(f'ERROR: input wf_parameters for SSDisp contains extra keys: {extra_keys}')
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        self.ctx.wf_dict = merge_parameter_dicts(wf_dict, self._default_wf_para,
                                                 nested=False)

        if self.ctx.wf_dict['ref_qss'] != self.ctx.wf_dict['q_vectors'][0]:
            error = ('The first q_vector of the forceTheorem step has to be equal to'
                     'the q vector of the reference calculation.')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

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

        # Check if user gave valid fleur executable
        inputs = self.inputs
        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur')
            except ValueError:
                error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # Check if user gave an input setup making any sense
        if 'scf' in inputs:
            self.ctx.scf_needed = True
            if 'remote_data' in inputs:
                error = 'ERROR: you gave SCF input + remote_data for the FT'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in inputs:
                error = 'ERROR: you gave SCF input + fleurinp for the FT'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote_data' not in inputs:
            error = 'ERROR: you gave neither SCF input nor remote_data for the FT'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            self.ctx.scf_needed = False


    def converge_scf(self):
        """
        Converge charge density for collinear case which is a reference for futher
        spin spiral calculations.
        """
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(reference=res)

    def get_inputs_scf(self):
        """
        Initialize inputs for the scf cycle
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        input_scf.metadata.label = 'reference_scf_SSDisp'
        input_scf.metadata.description = ('The SCF workchain converging reference charge'
                                          ' density for Spin Spiral Dispersion')

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()

        with inpxml_changes(scf_wf_dict) as fm:

            if [x for x in self.ctx.wf_dict['ref_qss'] if x != 0]:
                fm.set_inpchanges({'qss': self.ctx.wf_dict['ref_qss'], 'l_noco': True, 'ctail': False, 'l_ss': True})
            else:
                fm.set_inpchanges({'qss': ' 0.0 0.0 0.0 ', 'l_noco': False, 'ctail': True, 'l_ss': False})

            # change beta parameter
            for key, val in self.ctx.wf_dict['beta'].items():
                fm.set_atomgroup_label(key, {'nocoParams': {'beta': val}})

        input_scf.wf_parameters = Dict(scf_wf_dict)

        if 'structure' in input_scf:  # add info about spin spiral propagation
            if 'calc_parameters' in input_scf:
                calc_parameters = input_scf.calc_parameters.get_dict()
            else:
                calc_parameters = {}
            calc_parameters['qss'] = {
                'x': self.ctx.wf_dict['prop_dir'][0],
                'y': self.ctx.wf_dict['prop_dir'][1],
                'z': self.ctx.wf_dict['prop_dir'][2]
            }
            input_scf.calc_parameters = Dict(calc_parameters)

        return input_scf

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')

        if self.ctx.scf_needed:  # use fleurinp from scf wc
            try:
                fleurin = self.ctx.reference.outputs.fleurinp
            except NotExistent:
                error = 'Fleurinp generated in the reference calculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED
        else:
            if 'fleurinp' in self.inputs:  # use the given fleurinp
                fleurin = self.inputs.fleurinp
            else:  # or generate a new one from inp.xml located in the remote folder
                fleurin = get_fleurinp_from_remote_data(self.inputs.remote_data)

        # copy inpchanges from wf parameters
        with inpxml_changes(self.ctx.wf_dict) as fm:
            fm.set_complex_tag('spinSpiralDispersion', {'q': self.ctx.wf_dict['q_vectors']}, create=True)
            fm.set_inpchanges({'itmax': 1, 'l_noco': True, 'ctail': False, 'l_ss': True})

            if self.ctx.wf_dict['kmesh_force_theorem'] is not None:
                kmesh = KpointsData()
                kmesh.set_kpoints(monkhorst_pack(self.ctx.wf_dict['kmesh_force_theorem']))
                kmesh.store()
                fm.set_kpointsdata(kmesh.uuid, switch=True, kpoint_type='mesh')

            # change beta parameter
            for label, beta in self.ctx.wf_dict['beta'].items():
                fm.set_atomgroup_label(label, {'nocoParams': {'beta': beta}})

        modified, failure = apply_inpxml_changes(fleurin, self.ctx.wf_dict['inpxml_changes'], self.report)
        if failure == 'invalid':
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        if failure is not None:
            self.control_end_wc('Applying the requested inp.xml changes failed.')
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        self.ctx.fleurinp = modified

    def force_after_scf(self):
        '''
        This routine uses the force theorem to calculate energies dispersion of
        spin spirals. The force theorem calculations implemented into the FLEUR
        code. Hence a single iteration FLEUR input file having <forceTheorem> tag
        has to be created and submitted.
        '''
        calc = self.ctx.reference

        if not calc.is_finished_ok:
            message = ('The reference SCF calculation was not successful.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        try:
            outpara_node = calc.outputs.output_scf_wc_para
        except NotExistent:
            message = ('The reference SCF calculation failed, no scf output node.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        outpara = outpara_node.get_dict()

        if 'total_energy' not in outpara:
            message = ('Did not manage to extract float total energy from the reference SCF calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        self.report('INFO: run Force theorem calculations')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder of the reference calculation
        pk_last = 0
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.node_type == 'process.workflow.workchain.WorkChainNode.':
                if i.process_class is FleurBaseWorkChain:
                    if pk_last < i.pk:
                        pk_last = i.pk
        try:
            remote = load_node(pk_last).outputs.remote_folder
        except AttributeError:
            message = ('Found no remote folder of the reference scf calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_NOREMOTE

        label = 'Force_theorem_calculation'
        description = 'This is a force theorem calculation for all SQA'

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
        return ToContext(f_t=future)


    def get_results(self):
        """
        Generates results of the workchain.
        """
        t_energydict = []
        try:
            calculation = self.ctx.f_t
            if not calculation.is_finished_ok:
                message = f'ERROR: Force theorem Fleur calculation failed somehow it has exit status {calculation.exit_status}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_FORCE_THEOREM_FAILED
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have a force theorem Fleur calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        try:
            out_dict = calculation.outputs.output_parameters.dict
            t_energydict = out_dict.spst_force_evsum
            e_u = out_dict.spst_force_units

            # Find a minimal value of SpSp and count it as 0
            minenergy = min(t_energydict)

            if e_u in ['Htr', 'htr']:
                t_energydict = [HTR_TO_EV * (x - minenergy) for x in t_energydict]
            else:
                t_energydict = [(x - minenergy) for x in t_energydict]

            self.ctx.energy_dict = t_energydict

        except AttributeError:
            message = ('Did not manage to read evSum or energy units after FT calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

    def return_results(self):
        """
        This function outputs results of the wc
        """
        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            # 'initial_structure': self.inputs.structure.uuid, # parse from fleurinp or remove
            'is_it_force_theorem': True,
            'energies': self.ctx.energy_dict,
            'q_vectors': self.ctx.wf_dict['q_vectors'],
            'energy_units': 'eV',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        out = save_output_node(Dict(dict=out))
        self.out('output_ssdisp_wc_para', out)



@cf
def save_output_node(out):
    """
    This calcfunction saves the out dict in the db
    """
    out_wc = out.clone()
    return out_wc
