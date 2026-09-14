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
    In this module you find the workflow 'FleurMaeWorkChain' for the calculation of
    Magnetic Anisotropy Energy via the force theorem.
"""

import copy

from ase.dft.kpoints import monkhorst_pack

from aiida.engine import ToContext
from aiida.engine import calcfunction as cf
from aiida.orm import load_node
from aiida.orm import Dict, KpointsData
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows._force_theorem import FleurForceTheoremWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import inpxml_changes
from aiida_fleur.workflows._base import merge_parameter_dicts, unknown_parameter_keys
from aiida_fleur.workflows._base import apply_inpxml_changes
from aiida_fleur.data.fleurinp import get_fleurinp_from_remote_data
from pyfleur.util.constants import HTR_TO_EV


class FleurMaeWorkChain(FleurForceTheoremWorkChain):
    """
        This workflow calculates the Magnetic Anisotropy Energy of a structure.
    """

    _workflowversion = '0.4.0'

    _OUTPUT_NAME = 'output_mae_wc_para'
    _FT_LABEL = 'Force_theorem_calculation'
    _FT_DESCRIPTION = ('This is a force theorem calculation for all SQA')

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
        'sqa_ref': [0.7, 0.7],
        'use_soc_ref': False,
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'kmesh_force_theorem': None,
        'use_symmetries_reference': False,
        'soc_off': [],
        'inpxml_changes': [],
    }


    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report(f'INFO: started Magnetic Anisotropy Energy calculation workflow version {self._workflowversion}\n')

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.t_energydict = []
        self.ctx.mae_thetas = []
        self.ctx.mae_phis = []
        self.ctx.fleuroutuuid = None

        # initialize the dictionary using defaults if no wf paramters are given
        wf_dict = self.inputs.wf_parameters.get_dict() if 'wf_parameters' in self.inputs else {}
        extra_keys = unknown_parameter_keys(wf_dict, self._default_wf_para)
        if extra_keys:
            self.report(f'ERROR: input wf_parameters for MAE contains extra keys: {extra_keys}')
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        self.ctx.wf_dict = merge_parameter_dicts(wf_dict, self._default_wf_para,
                                                 nested=False)

        # switch off SOC on an atom specie
        with inpxml_changes(self.ctx.wf_dict) as fm:
            for atom_label in self.ctx.wf_dict['soc_off']:
                fm.set_species(atom_label, {'special': {'socscale': 0}})

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
        Converge charge density with or without SOC.
        Submit a single Fleur calculation to obtain
        a reference for further force theorem calculations.
        """
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(reference=res)

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        soc = self.ctx.wf_dict.get('sqa_ref')
        with inpxml_changes(input_scf) as fm:
            if not self.ctx.wf_dict.get('use_soc_ref'):
                fm.set_inpchanges({'l_soc': False})
            else:
                fm.set_inpchanges({
                    'theta': soc[0],
                    'phi': soc[1],
                    'l_soc': True
                },
                                  path_spec={
                                      'phi': {
                                          'contains': 'soc'
                                      },
                                      'theta': {
                                          'contains': 'soc'
                                      }
                                  })

        if 'structure' in input_scf:
            if 'calc_parameters' in input_scf:
                calc_parameters = input_scf.calc_parameters.get_dict()
            else:
                calc_parameters = {}
            if not self.ctx.wf_dict.get('use_symmetries_reference'):
                # break symmetries, SOC will be removed if not set
                calc_parameters['soc'] = {'theta': soc[0], 'phi': soc[1]}
            input_scf.calc_parameters = Dict(calc_parameters)

        return input_scf

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
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

        with inpxml_changes(self.ctx.wf_dict) as fm:
            # add forceTheorem tag into inp.xml
            fm.set_complex_tag('MAE', {
                'theta': self.ctx.wf_dict['sqas_theta'],
                'phi': self.ctx.wf_dict['sqas_phi']
            },
                               create=True)

            fm.set_inpchanges({'itmax': 1, 'l_soc': True})

            if self.ctx.wf_dict['kmesh_force_theorem'] is not None:
                # set k-mesh for the full BZ
                kmesh = KpointsData()
                kmesh.set_kpoints(monkhorst_pack(self.ctx.wf_dict['kmesh_force_theorem']))
                kmesh.store()
                fm.set_kpointsdata(kmesh.uuid, switch=True, kpoint_type='mesh')

            # if self.ctx.wf_dict['use_symmetries_reference']:
            #     # remove symmetries from the inp.xml
            #     fchanges.append(('delete_tag', {
            #         'tag_name': 'symOp',
            #         'occurrences': range(1, len(fleurin.inp_dict['cell']['symmetryOperations']))
            #     }))

        modified, failure = apply_inpxml_changes(fleurin, self.ctx.wf_dict['inpxml_changes'], self.report)
        if failure == 'invalid':
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        if failure is not None:
            self.control_end_wc('Applying the requested inp.xml changes failed.')
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        self.ctx.fleurinp = modified

    def force_after_scf(self):
        """
        Calculate energy of a system for given SQAs
        using the force theorem. Converged reference is stored in self.ctx['xyz'].
        """
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

        t_e = outpara.get('total_energy', 'failed')
        if not isinstance(t_e, float):
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

        label = 'MAE_force_theorem'
        description = 'This is the force theorem calculation for MAE.'

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
        mae_thetas = []
        mae_phis = []
        fleur_output_uuid = None

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
            fleurout = calculation.outputs.output_parameters
            fleur_output_uuid = fleurout.uuid
            out_dict = fleurout.dict
            t_energydict = out_dict.mae_force_evsum
            mae_thetas = out_dict.mae_force_theta
            mae_phis = out_dict.mae_force_phi
            e_u = out_dict.mae_force_units

            minenergy = min(t_energydict)

            if e_u in ['Htr', 'htr']:
                t_energydict = [HTR_TO_EV * (x - minenergy) for x in t_energydict]
            else:
                t_energydict = [(x - minenergy) for x in t_energydict]

        except AttributeError as e_message:
            message = f'Did not manage to read evSum or energy units after FT calculation. {e_message}'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        self.ctx.t_energydict = t_energydict
        self.ctx.mae_thetas = mae_thetas
        self.ctx.mae_phis = mae_phis
        self.ctx.fleuroutuuid = fleur_output_uuid

    def return_results(self):
        """
        This function outputs results of the wc
        """

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            # 'initial_structure': self.inputs.structure.uuid,
            'is_it_force_theorem': True,
            'maes': self.ctx.t_energydict,
            'theta': self.ctx.mae_thetas,
            'phi': self.ctx.mae_phis,
            'mae_units': 'eV',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        # ensure provenance of output nodes

        out_dict = {'out': Dict(out)}
        if self.ctx.fleuroutuuid is not None:
            out_dict['last_fleur_out'] = load_node(self.ctx.fleuroutuuid)

        out_nodes = save_mae_output_node(**out_dict)
        out = out_nodes.get('output_mae_wc_para')

        # make wc return out node
        self.out('output_mae_wc_para', out)



@cf
def save_mae_output_node(**kwargs):
    """
    This is a pseudo cf, to create the right graph structure of AiiDA.
    This calcfunction will create the output node in the database.
    It also connects the output_node to all nodes the information comes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in kwargs.items():
        if key == 'out':  # should be always there
            outpara = val
    outdict = {}

    # clone, because we rather produce the same node twice then have a circle in the database for
    outputnode = outpara.clone()
    outputnode.label = 'output_mae_wc_para'
    outputnode.description = ('Contains magnetic anisotropy results and information of an FleurMaeWorkChain run.')

    outdict['output_mae_wc_para'] = outputnode

    return outdict
