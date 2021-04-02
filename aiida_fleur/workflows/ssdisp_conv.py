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
    In this module you find the workflow 'FleurSSDispConvWorkChain' for the calculation of
    Spin Spiral energy Dispersion converging all the directions.
"""

from __future__ import absolute_import
import copy
import six

from aiida.engine import WorkChain
from aiida.engine import calcfunction as cf
from aiida.orm import Dict
from aiida.common import AttributeDict

from aiida_fleur.workflows.scf import FleurScfWorkChain


class FleurSSDispConvWorkChain(WorkChain):
    """
        This workflow calculates the Spin Spiral Dispersion of a structure.
    """

    _workflowversion = '0.2.0'

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

        spec.output('out', valid_type=Dict)

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
            error = 'ERROR: input wf_parameters for SSDisp Conv contains extra keys: {}'.format(extra_keys)
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

    def converge_scf(self):
        """
        Converge charge density with or without SOC.
        Depending on a branch of Spiral calculation, submit a single Fleur calculation to obtain
        a reference for further force theorem calculations or
        submit a set of Fleur calculations to converge charge density for all given SQAs.
        """
        inputs = {}
        for key, q_vector in six.iteritems(self.ctx.wf_dict['q_vectors']):
            inputs[key] = self.get_inputs_scf()
            if self.ctx.wf_dict['suppress_symmetries']:
                inputs[key].calc_parameters['qss'] = {'x': 1.221, 'y': 0.522, 'z': -0.5251}
                changes_dict = {'qss': ' '.join(map(str, q_vector))}
                wf_para = inputs[key].wf_parameters.get_dict()
                wf_para['inpxml_changes'].append(('set_inpchanges', {'change_dict': changes_dict}))
                inputs[key].wf_parameters = Dict(dict=wf_para)
            else:
                inputs[key].calc_parameters['qss'] = {'x': q_vector[0], 'y': q_vector[1], 'z': q_vector[2]}
            inputs[key].calc_parameters = Dict(dict=inputs[key]['calc_parameters'])
            res = self.submit(FleurScfWorkChain, **inputs[key])
            res.label = key
            self.to_context(**{key: res})

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()

        if 'inpxml_changes' not in scf_wf_dict:
            scf_wf_dict['inpxml_changes'] = []

        # change beta parameter
        for key, val in six.iteritems(self.ctx.wf_dict.get('beta')):
            scf_wf_dict['inpxml_changes'].append(('set_atomgr_att_label', {
                'attributedict': {
                    'nocoParams': [('beta', val)]
                },
                'atom_label': key
            }))

        input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        if 'calc_parameters' in input_scf:
            calc_parameters = input_scf.calc_parameters.get_dict()
        else:
            calc_parameters = {}
        input_scf.calc_parameters = calc_parameters

        return input_scf

    def get_results(self):
        """
        Retrieve results of converge calculations
        """
        t_energydict = {}
        original_t_energydict = {}
        outnodedict = {}
        htr_to_eV = 27.21138602

        for label in six.iterkeys(self.ctx.wf_dict['q_vectors']):
            calc = self.ctx[label]

            if not calc.is_finished_ok:
                message = ('One SCF workflow was not successful: {}'.format(label))
                self.ctx.warnings.append(message)
                continue

            try:
                outnodedict[label] = calc.outputs.output_scf_wc_para
            except KeyError:
                message = ('One SCF workflow failed, no scf output node: {}.' ' I skip this one.'.format(label))
                self.ctx.errors.append(message)
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()

            t_e = outpara.get('total_energy', 'failed')
            if not isinstance(t_e, float):
                message = ('Did not manage to extract float total energy from one ' 'SCF workflow: {}'.format(label))
                self.ctx.warnings.append(message)
                continue
            e_u = outpara.get('total_energy_units', 'Htr')
            if e_u in ['Htr', 'htr']:
                t_e = t_e * htr_to_eV
            t_energydict[label] = t_e

        if t_energydict:
            # Find a minimal value of Spiral and count it as 0
            minenergy = min(t_energydict.values())

            for key in six.iterkeys(t_energydict):
                original_t_energydict[key] = t_energydict[key]
                t_energydict[key] = t_energydict[key] - minenergy

        self.ctx.energydict = t_energydict
        self.ctx.original_energydict = original_t_energydict

    def return_results(self):
        """
        Retrieve results of converge calculations
        """

        failed_labels = []

        for label in six.iterkeys(self.ctx.wf_dict['q_vectors']):
            if label not in six.iterkeys(self.ctx.energydict):
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
        self.out('out', out)

        if not self.ctx.energydict:
            return self.exit_codes.ERROR_ALL_QVECTORS_FAILED
        elif failed_labels:
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
