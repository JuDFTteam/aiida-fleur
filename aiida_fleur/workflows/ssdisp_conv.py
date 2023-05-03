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
    In this module you find the workflow 'FleurSSDispConvWorkChain' for the calculation of
    Spin Spiral energy Dispersion converging all the directions.
"""

import copy

from aiida.engine import WorkChain
from aiida.engine import calcfunction as cf
from aiida.orm import Dict
from aiida.common import AttributeDict

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.data.fleurinpmodifier import inpxml_changes

from masci_tools.util.constants import HTR_TO_EV


class FleurSSDispConvWorkChain(WorkChain):
    """
        This workflow calculates the Spin Spiral Dispersion of a structure.
    """

    _workflowversion = '0.3.0'

    _default_wf_para = {
        'beta': {
            'all': 1.57079
        },
        'q_vectors': {
            'label': [0.0, 0.0, 0.0],
            'label2': [0.125, 0.0, 0.0]
        },
        'suppress_symmetries': False
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.input('wf_parameters', valid_type=Dict, required=False)

        spec.outline(cls.start, cls.converge_scf, cls.get_results, cls.return_results)

        spec.output('output_ssdisp_conv_wc_para', valid_type=Dict)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(340,
                       'ERROR_ALL_QVECTORS_FAILED',
                       message='Convergence SSDisp calculation failed for all q-vectors.')
        spec.exit_code(341,
                       'ERROR_SOME_QVECTORS_FAILED',
                       message='Convergence SSDisp calculation failed for some q-vectors.')

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Spin Stiffness calculation'
                    ' convergence calculation workflow version {}\n'.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []

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
            error = f'ERROR: input wf_parameters for SSDisp Conv contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

    def get_inputs_scf(self, qss):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        with inpxml_changes(input_scf) as fm:
            for key, val in self.ctx.wf_dict['beta'].items():
                fm.set_atomgroup_label(key, {'nocoParams': {'beta': val}})
            if self.ctx.wf_dict['suppress_symmetries']:
                fm.set_inpchanges({'qss': qss})

        if 'calc_parameters' in input_scf:
            calc_parameters = input_scf.calc_parameters.get_dict()
        else:
            calc_parameters = {}
        if self.ctx.wf_dict['suppress_symmetries']:
            calc_parameters['qss'] = {'x': 1.221, 'y': 0.522, 'z': -0.5251}
        else:
            calc_parameters['qss'] = {'x': qss[0], 'y': qss[1], 'z': qss[2]}
        input_scf.calc_parameters = Dict(calc_parameters)

        return input_scf

    def converge_scf(self):
        """
        Converge charge density with or without SOC.
        Depending on a branch of Spiral calculation, submit a single Fleur calculation to obtain
        a reference for further force theorem calculations or
        submit a set of Fleur calculations to converge charge density for all given SQAs.
        """
        inputs = {}
        for key, q_vector in self.ctx.wf_dict['q_vectors'].items():
            inputs[key] = self.get_inputs_scf(q_vector)
            res = self.submit(FleurScfWorkChain, **inputs[key])
            res.label = key
            self.to_context(**{key: res})

    def get_results(self):
        """
        Retrieve results of converge calculations
        """
        t_energydict = {}
        original_t_energydict = {}
        outnodedict = {}

        for label in self.ctx.wf_dict['q_vectors'].keys():
            calc = self.ctx[label]

            if not calc.is_finished_ok:
                message = f'One SCF workflow was not successful: {label}'
                self.ctx.warnings.append(message)
                continue

            try:
                outnodedict[label] = calc.outputs.output_scf_wc_para
            except KeyError:
                message = f'One SCF workflow failed, no scf output node: {label}. I skip this one.'
                self.ctx.errors.append(message)
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()

            t_e = outpara.get('total_energy', 'failed')
            if not isinstance(t_e, float):
                message = f'Did not manage to extract float total energy from one SCF workflow: {label}'
                self.ctx.warnings.append(message)
                continue
            e_u = outpara.get('total_energy_units', 'Htr')
            if e_u in ['Htr', 'htr']:
                t_e = t_e * HTR_TO_EV
            t_energydict[label] = t_e

        if t_energydict:
            # Find a minimal value of Spiral and count it as 0
            minenergy = min(t_energydict.values())

            for key, energy in t_energydict.items():
                original_t_energydict[key] = energy
                t_energydict[key] = energy - minenergy

        self.ctx.energydict = t_energydict
        self.ctx.original_energydict = original_t_energydict

    def return_results(self):
        """
        Retrieve results of converge calculations
        """

        failed_labels = []

        for label in self.ctx.wf_dict['q_vectors'].keys():
            if label not in self.ctx.energydict.keys():
                failed_labels.append(label)

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            # 'initial_structure': self.inputs.structure.uuid,
            'energies': self.ctx.energydict,
            'original_energies': self.ctx.original_energydict,
            'q_vectors': self.ctx.wf_dict['q_vectors'],
            'failed_labels': failed_labels,
            'energy_units': 'eV',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        # create link to workchain node
        out = save_output_node(Dict(dict=out))
        self.out('output_ssdisp_conv_wc_para', out)

        if not self.ctx.energydict:
            return self.exit_codes.ERROR_ALL_QVECTORS_FAILED
        if failed_labels:
            return self.exit_codes.ERROR_SOME_QVECTORS_FAILED

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def save_output_node(out):
    """
    This calcfunction saves the out dict in the db
    """
    out_wc = out.clone()
    return out_wc
