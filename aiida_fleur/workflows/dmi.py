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
    In this module you find the workflow 'FleurDMIWorkChain' for the calculation of
    DMI energy dispersion.
"""

from __future__ import absolute_import
import copy
import numpy as np

import six
#from six.moves import range
#from six.moves import map
from lxml import etree

from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida.orm import Code, load_node, CalcJobNode
from aiida.orm import RemoteData, Dict
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.common.constants import HTR_TO_EV
from aiida_fleur.data.fleurinp import FleurinpData


class FleurDMIWorkChain(WorkChain):
    """
    This workflow calculates DMI energy dispersion of a structure.
    """

    _workflowversion = '0.2.0'

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
        'serial': False,
        'only_even_MPI': False,
        'beta': {
            'all': 1.57079
        },
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'soc_off': [],
        # 'prop_dir': [1.0, 0.0, 0.0],
        'q_vectors': [[0.0, 0.0, 0.0], [0.125, 0.0, 0.0], [0.250, 0.0, 0.0], [0.375, 0.0, 0.0]],
        'ref_qss': [0.0, 0.0, 0.0],
        'inpxml_changes': []
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('options', valid_type=Dict, required=False)

        spec.outline(cls.start,
                     if_(cls.scf_needed)(
                         cls.converge_scf,
                         cls.force_after_scf,
                     ).else_(
                         cls.force_wo_scf,
                     ), cls.get_results, cls.return_results)

        spec.output('out', valid_type=Dict)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(334, 'ERROR_REFERENCE_CALCULATION_FAILED', message='Reference calculation failed.')
        spec.exit_code(335,
                       'ERROR_REFERENCE_CALCULATION_NOREMOTE',
                       message='Found no reference calculation remote repository.')
        spec.exit_code(336, 'ERROR_FORCE_THEOREM_FAILED', message='Force theorem calculation failed.')

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started DMI calculation workflow version {}\n' ''.format(self._workflowversion))
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []
        self.ctx.qs = []
        self.ctx.mae_thetas = []
        self.ctx.mae_phis = []
        self.ctx.num_ang = 1
        self.ctx.t_energydict = []
        self.ctx.q_vectors = []

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = []
        for key in wf_dict.keys():
            if key not in wf_default.keys():
                extra_keys.append(key)
        if extra_keys:
            error = 'ERROR: input wf_parameters for DMI contains extra keys: {}'.format(extra_keys)
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        if wf_dict['ref_qss'] != wf_dict['q_vectors'][0]:
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
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        # Check if user gave valid fleur executable
        inputs = self.inputs
        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ('The code you provided for FLEUR does not use the plugin fleur.fleur')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        # Check if user gave an input setup making any sense
        if inputs.scf:
            self.ctx.scf_needed = True
            if 'remote' in inputs:
                error = 'ERROR: you gave SCF input + remote for the FT'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in inputs:
                error = 'ERROR: you gave SCF input + fleurinp for the FT'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote' not in inputs:
            error = 'ERROR: you gave neither SCF input nor remote for the FT'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            self.ctx.scf_needed = False

    def scf_needed(self):
        """
        Returns True if SCF WC is needed.
        """
        return self.ctx.scf_needed

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

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()

        if 'inpxml_changes' not in scf_wf_dict:
            scf_wf_dict['inpxml_changes'] = []

        # set up q vector for the reference calculation
        list_ref_qss = self.ctx.wf_dict['ref_qss']
        if [x for x in list_ref_qss if x != 0]:
            changes_dict = {'qss': self.ctx.wf_dict['ref_qss'], 'l_noco': True, 'ctail': False, 'l_ss': True}
        else:
            changes_dict = {'qss': ' 0.0 0.0 0.0 ', 'l_noco': False, 'ctail': True, 'l_ss': False}

        scf_wf_dict['inpxml_changes'].append(('set_inpchanges', {'change_dict': changes_dict}))

        # change beta parameter
        for key, val in six.iteritems(self.ctx.wf_dict.get('beta')):
            scf_wf_dict['inpxml_changes'].append(('set_atomgr_att_label', {
                'attributedict': {
                    'nocoParams': [('beta', val)]
                },
                'atom_label': key
            }))

        input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        if 'structure' in input_scf:  # add info about spin spiral propagation
            if 'calc_parameters' in input_scf:
                calc_parameters = input_scf.calc_parameters.get_dict()
            else:
                calc_parameters = {}
            sum_vec = np.array([np.pi / 4.0, np.e / 3.0, np.euler_gamma])
            calc_parameters['qss'] = {'x': sum_vec[0], 'y': sum_vec[1], 'z': sum_vec[2]}
            input_scf.calc_parameters = Dict(dict=calc_parameters)
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
                remote_node = self.inputs.remote
                for link in remote_node.get_incoming().all():
                    if isinstance(link.node, CalcJobNode):
                        parent_calc_node = link.node
                retrieved_node = parent_calc_node.get_outgoing().get_node_by_label('retrieved')
                fleurin = FleurinpData(files=['inp.xml'], node=retrieved_node)

        # copy inpchanges from wf parameters
        fchanges = self.ctx.wf_dict.get('inpxml_changes', [])
        # create forceTheorem tags
        fchanges.extend([('create_tag', {
            'xpath': '/fleurInput',
            'newelement': 'forceTheorem'
        }), ('create_tag', {
            'xpath': '/fleurInput/forceTheorem',
            'newelement': 'DMI'
        }), ('create_tag', {
            'xpath': '/fleurInput/forceTheorem/DMI',
            'newelement': 'qVectors'
        }),
                         ('xml_set_attribv_occ', {
                             'xpathn': '/fleurInput/forceTheorem/DMI',
                             'attributename': 'theta',
                             'attribv': ' '.join(six.moves.map(str, self.ctx.wf_dict.get('sqas_theta')))
                         }),
                         ('xml_set_attribv_occ', {
                             'xpathn': '/fleurInput/forceTheorem/DMI',
                             'attributename': 'phi',
                             'attribv': ' '.join(six.moves.map(str, self.ctx.wf_dict.get('sqas_phi')))
                         })])

        for i, vectors in enumerate(self.ctx.wf_dict['q_vectors']):
            fchanges.append(('create_tag', {'xpath': '/fleurInput/forceTheorem/DMI/qVectors', 'newelement': 'q'}))
            fchanges.append(('xml_set_text_occ', {
                'xpathn': '/fleurInput/forceTheorem/DMI/qVectors/q',
                'text': ' '.join(six.moves.map(str, vectors)),
                'create': False,
                'occ': i
            }))

        changes_dict = {
            'itmax': 1,
            'l_noco': True,
            'ctail': False,
            # 'l_soc': True,
            'l_ss': True
        }
        fchanges.append(('set_inpchanges', {'change_dict': changes_dict}))

        # change beta parameter
        for key, val in six.iteritems(self.ctx.wf_dict.get('beta')):
            fchanges.append(('set_atomgr_att_label', {
                'attributedict': {
                    'nocoParams': [('beta', val)]
                },
                'atom_label': key
            }))

        # switch off SOC on an atom specie
        for atom_label in self.ctx.wf_dict['soc_off']:
            fchanges.append(('set_species_label', {
                'at_label': atom_label,
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                },
                'create': True
            }))

        if fchanges:  # change inp.xml file
            fleurmode = FleurinpModifier(fleurin)
            avail_ac_dict = fleurmode.get_avail_actions()

            # apply further user dependend changes
            for change in fchanges:
                function = change[0]
                para = change[1]
                method = avail_ac_dict.get(function, None)
                if not method:
                    error = ("ERROR: Input 'inpxml_changes', function {} "
                             'is not known to fleurinpmodifier class, '
                             'please check/test your input. I abort...'
                             ''.format(function))
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

                else:  # apply change
                    method(**para)

            # validate?
            try:
                fleurmode.show(display=False, validate=True)
            except etree.DocumentInvalid:
                error = ('ERROR: input, user wanted inp.xml changes did not validate')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_FILE

            # apply
            out = fleurmode.freeze()
            self.ctx.fleurinp = out
            return
        else:  # otherwise do not change the inp.xml
            self.ctx.fleurinp = fleurin
            return

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
                                          serial=self.ctx.wf_dict['serial'],
                                          only_even_MPI=self.ctx.wf_dict['only_even_MPI'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(f_t=future)

    def force_wo_scf(self):
        """
        Submit FLEUR force theorem calculation using input remote
        """
        self.report('INFO: run Force theorem calculations')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder from the inputs
        remote = self.inputs.remote

        label = 'DMI_force_theorem'
        description = 'The is the force theorem calculation for DMI energy.'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code,
                                          remote,
                                          fleurin,
                                          options,
                                          label,
                                          description,
                                          settings,
                                          serial=self.ctx.wf_dict['serial'],
                                          only_even_MPI=self.ctx.wf_dict['only_even_MPI'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(f_t=future)

    def get_results(self):
        """
        Generates results of the workchain.
        """
        t_energydict = []
        mae_thetas = []
        mae_phis = []
        num_ang = 0
        num_q_vectors = 0
        q_vectors = []

        try:
            calculation = self.ctx.f_t
            if not calculation.is_finished_ok:
                message = ('ERROR: Force theorem Fleur calculation failed somehow it has '
                           'exit status {}'.format(calculation.exit_status))
                self.control_end_wc(message)
                return self.exit_codes.ERROR_FORCE_THEOREM_FAILED
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have a force theorem Fleur calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        try:
            out_dict = calculation.outputs.output_parameters.dict
            t_energydict = out_dict.dmi_force_evSum
            mae_thetas = out_dict.dmi_force_theta
            mae_phis = out_dict.dmi_force_phi
            num_ang = out_dict.dmi_force_angles
            num_q_vectors = out_dict.dmi_force_qs
            q_vectors = [self.ctx.wf_dict['q_vectors'][x - 1] for x in out_dict.dmi_force_q]
            e_u = out_dict.energy_units

            for i in six.moves.range((num_q_vectors - 1) * (num_ang), -1, -num_ang):
                ref_enrg = t_energydict.pop(i)
                q_vectors.pop(i)
                for k in six.moves.range(i, i + num_ang - 1, 1):
                    t_energydict[k] -= ref_enrg

            if e_u in ['Htr', 'htr']:
                for labels, energies in t_energydict.items():
                    t_energydict[labels] = energies * HTR_TO_EV
        except AttributeError:
            message = ('Did not manage to read evSum or energy units after FT calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        self.ctx.t_energydict = t_energydict
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
            'energies': self.ctx.t_energydict,
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
        self.out('out', out)

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def save_output_node(out):
    """
    This calcfunction saves the out dict in the db
    """
    out_wc = out.clone()
    return out_wc
