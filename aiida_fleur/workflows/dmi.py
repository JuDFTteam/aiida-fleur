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
    In this module you find the workflow 'FleurDMIWorkChain' for the calculation of
    DMI energy dispersion.
"""
import copy
import numpy as np

from ase.dft.kpoints import monkhorst_pack

from aiida.engine import ToContext
from aiida.engine import calcfunction as cf
from aiida.orm import load_node
from aiida.orm import Dict, KpointsData
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows._force_theorem import FleurForceTheoremWorkChain
from aiida_fleur.workflows._base import merge_parameter_dicts, unknown_parameter_keys
from aiida_fleur.workflows._base import apply_inpxml_changes
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinp import get_fleurinp_from_remote_data
from aiida_fleur.data.fleurinpmodifier import inpxml_changes

from pyfleur.util.constants import HTR_TO_EV


class FleurDMIWorkChain(FleurForceTheoremWorkChain):
    """
    This workflow calculates DMI energy dispersion of a structure.
    """

    _workflowversion = '0.4.0'

    _OUTPUT_NAME = 'output_dmi_wc_para'
    _FT_LABEL = 'DMI_force_theorem'
    _FT_DESCRIPTION = ('The is the force theorem calculation for DMI energy.')

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
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'beta': {
            'all': 1.57079
        },
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'soc_off': [],
        # 'prop_dir': [1.0, 0.0, 0.0],
        'q_vectors': [[0.0, 0.0, 0.0], [0.125, 0.0, 0.0], [0.250, 0.0, 0.0], [0.375, 0.0, 0.0]],
        'ref_qss': [0.0, 0.0, 0.0],
        'kmesh_force_theorem': None,
        'inpxml_changes': []
    }


    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report(f'INFO: started DMI calculation workflow version {self._workflowversion}\n')
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.qs = []
        self.ctx.mae_thetas = []
        self.ctx.mae_phis = []
        self.ctx.num_ang = 1
        self.ctx.h_so = []
        self.ctx.q_vectors = []

        # initialize the dictionary using defaults if no wf paramters are given
        wf_dict = self.inputs.wf_parameters.get_dict() if 'wf_parameters' in self.inputs else {}
        extra_keys = unknown_parameter_keys(wf_dict, self._default_wf_para)
        if extra_keys:
            self.report(f'ERROR: input wf_parameters for DMI contains extra keys: {extra_keys}')
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        self.ctx.wf_dict = merge_parameter_dicts(wf_dict, self._default_wf_para,
                                                 nested=False)

        if self.ctx.wf_dict['ref_qss'] != self.ctx.wf_dict['q_vectors'][0]:
            error = ('The first q_vector of the forceTheorem step has to be equal to'
                     'the q vector of the reference calculation.')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # Check if sqas_theta and sqas_phi have the same length
        if len(self.ctx.wf_dict.get('sqas_theta')) != len(self.ctx.wf_dict.get('sqas_phi')):
            error = ('Number of sqas_theta has to be equal to the number of sqas_phi')
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
                error = ('The code you provided for FLEUR does not use the plugin fleur.fleur')
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

        with inpxml_changes(input_scf) as fm:

            if [x for x in self.ctx.wf_dict['ref_qss'] if x != 0]:
                fm.set_inpchanges({
                    'qss': self.ctx.wf_dict['ref_qss'],
                    'l_noco': True,
                    'ctail': False,
                    'l_ss': True,
                    'l_soc': False
                })
            else:
                fm.set_inpchanges({
                    'qss': ' 0.0 0.0 0.0 ',
                    'l_noco': False,
                    'ctail': True,
                    'l_ss': False,
                    'l_soc': False
                })

            # change beta parameter
            for key, val in self.ctx.wf_dict['beta'].items():
                fm.set_atomgroup_label(key, {'nocoParams': {'beta': val}})

        if 'structure' in input_scf:  # add info about spin spiral propagation
            if 'calc_parameters' in input_scf:
                calc_parameters = input_scf.calc_parameters.get_dict()
            else:
                calc_parameters = {}
            sum_vec = np.array([np.pi / 4.0, np.e / 3.0, np.euler_gamma])
            calc_parameters['qss'] = {'x': sum_vec[0], 'y': sum_vec[1], 'z': sum_vec[2]}
            calc_parameters['soc'] = {'theta': 0.7, 'phi': 0.7}
            input_scf.calc_parameters = Dict(calc_parameters)
        return input_scf

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')

        if self.ctx.scf_needed:
            try:
                fleurin = self.ctx.reference.outputs.fleurinp
            except NotExistent:
                error = 'Fleurinp generated in the reference calculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED
        else:
            if 'fleurinp' in self.inputs:
                fleurin = self.inputs.fleurinp
            else:
                # In this case only remote is given
                # fleurinp data has to be generated from the remote inp.xml file
                fleurin = get_fleurinp_from_remote_data(self.inputs.remote_data)

        # copy inpchanges from wf parameters
        with inpxml_changes(self.ctx.wf_dict) as fm:
            fm.set_complex_tag('DMI', {
                'qVectors': {
                    'q': self.ctx.wf_dict['q_vectors']
                },
                'theta': self.ctx.wf_dict['sqas_theta'],
                'phi': self.ctx.wf_dict['sqas_phi']
            },
                               create=True)
            fm.set_inpchanges({
                'itmax': 1,
                'l_noco': True,
                'ctail': False,
                'spav': True,
                # 'l_soc': True,
                'l_ss': True
            })

            if self.ctx.wf_dict['kmesh_force_theorem'] is not None:
                kmesh = KpointsData()
                kmesh.set_kpoints(monkhorst_pack(self.ctx.wf_dict['kmesh_force_theorem']))
                kmesh.store()
                fm.set_kpointsdata(kmesh.uuid, switch=True, kpoint_type='mesh')

            # change beta parameter
            for key, val in self.ctx.wf_dict['beta'].items():
                fm.set_atomgroup_label(key, {'nocoParams': {'beta': val}})

            # switch off SOC on an atom specie
            for atom_label in self.ctx.wf_dict['soc_off']:
                fm.set_species_label(
                    atom_label,
                    {'special': {
                        'socscale': 0.0
                    }},
                )

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
        mae_thetas = []
        mae_phis = []
        num_ang = 0
        q_vectors = []

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
            h_so = out_dict.dmi_force_so_h_so
            mae_thetas = out_dict.dmi_force_theta
            mae_phis = out_dict.dmi_force_phi
            num_ang = out_dict.dmi_force_angles
            q_vectors = [self.ctx.wf_dict['q_vectors'][x - 1] for x in out_dict.dmi_force_so_q]
            e_u = out_dict.dmi_force_units
        except AttributeError:
            message = ('Did not manage to read evSum or energy units after FT calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        if not isinstance(h_so, list):
            message = ('Did not manage to read evSum or energy units after FT calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        if e_u in ['htr', 'Htr']:
            h_so = np.array(h_so) * HTR_TO_EV
            h_so = h_so.tolist()

        self.ctx.h_so = h_so
        self.ctx.q_vectors = q_vectors
        self.ctx.mae_thetas = mae_thetas
        self.ctx.mae_phis = mae_phis
        self.ctx.num_ang = num_ang

    def return_results(self):
        """
        This function outputs results of the wc
        """
        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            # 'initial_structure': self.inputs.structure.uuid,
            'is_it_force_theorem': True,
            'soc_energies': self.ctx.h_so,
            'q_vectors': self.ctx.q_vectors,
            'theta': self.ctx.mae_thetas,
            'phi': self.ctx.mae_phis,
            'angles': self.ctx.num_ang - 1,
            'energy_units': 'eV',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
        }

        out = save_output_node(Dict(dict=out))
        self.out('output_dmi_wc_para', out)



@cf
def save_output_node(out):
    """
    This calcfunction saves the out dict in the db
    """
    out_wc = out.clone()
    return out_wc
