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
    Magnetic Anisotropy Energy converging all the directions.
"""

from __future__ import absolute_import

import six

from aiida.engine import WorkChain
from aiida.engine import calcfunction as cf
from aiida.plugins import DataFactory
from aiida.orm import Code
from aiida.rom import StructureData, RemoteData, Dict

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.workflows.scf import FleurScfWorkChain

# pylint: disable=invalid-name
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurSSDispConvWorkChain(WorkChain):
    """
        This workflow calculates the Magnetic Anisotropy Energy of a structure.
    """

    _workflowversion = "0.1.0"

    _default_options = {
        'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        'max_wallclock_seconds': 2 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}}

    _wf_default = {
        'fleur_runmax': 10,
        'beta': {'all' : 1.57079},
        'q_vectors': {'label': [0.0, 0.0, 0.0],
                      'label2': [0.125, 0.0, 0.0]
                     },
        'alpha_mix': 0.05,
        'density_converged': 0.005,
        'serial': False,
        'itmax_per_run': 30,
        'soc_off': [],
        'inpxml_changes': [],
    }

    _scf_keys = ['fleur_runmax', 'density_converged', 'serial', 'itmax_per_run', 'inpxml_changes']

    @classmethod
    def define(cls, spec):
        super(FleurSSDispConvWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False)
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            cls.converge_scf,
            cls.get_results,
            cls.return_results
        )

        spec.output('out', valid_type=Dict)

        # exit codes
        spec.exit_code(331, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")
        spec.exit_code(340, 'ERROR_ALL_QVECTORS_FAILED',
                       message="Convergence SSDisp calculation failed for all q-vectors.")
        spec.exit_code(341, 'ERROR_SOME_QVECTORS_FAILED',
                       message="Convergence SSDisp calculation failed for some q-vectors.")

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

        # Check if user gave valid inpgen and fleur executables
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

    def converge_scf(self):
        """
        Converge charge density with or without SOC.
        Depending on a branch of Spiral calculation, submit a single Fleur calculation to obtain
        a reference for further force theorem calculations or
        submit a set of Fleur calculations to converge charge density for all given SQAs.
        """
        inputs = {}
        for key, vect in six.iteritems(self.ctx.wf_dict['q_vectors']):
            inputs[key] = self.get_inputs_scf()
            inputs[key]['calc_parameters']['qss'] = {'x': vect[0], 'y': vect[1], 'z': vect[2]}
            inputs[key]['calc_parameters'] = Dict(dict=inputs[key]['calc_parameters'])
            res = self.submit(FleurScfWorkChain, **inputs[key])
            self.to_context(**{key: res})

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = {}

        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)
        inputs['wf_parameters'] = scf_wf_param

        #change beta parameter
        for key, val in six.iteritems(self.ctx.wf_dict.get('beta')):
            inputs['wf_parameters']['inpxml_changes'].append(
                ('set_atomgr_att_label',
                 {'attributedict': {'nocoParams': [('beta', val)]},
                  'atom_label': key
                 }))

        inputs['options'] = self.ctx.options

        # Try to retrieve calculation parameters from inputs
        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        # Initialize codes
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur
        # Initialize the structure
        inputs['structure'] = self.inputs.structure

        inputs['options'] = Dict(dict=inputs['options'])
        inputs['wf_parameters'] = Dict(dict=inputs['wf_parameters'])

        return inputs

    def get_results(self):
        """
        Retrieve results of converge calculations
        """
        t_energydict = {}
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
                message = (
                    'One SCF workflow failed, no scf output node: {}.'
                    ' I skip this one.'.format(label))
                self.ctx.errors.append(message)
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()

            t_e = outpara.get('total_energy', 'failed')
            if not isinstance(t_e, float):
                message = (
                    'Did not manage to extract float total energy from one '
                    'SCF workflow: {}'.format(label))
                self.ctx.warnings.append(message)
                continue
            e_u = outpara.get('total_energy_units', 'Htr')
            if e_u == 'Htr' or 'htr':
                t_e = t_e * htr_to_eV
            t_energydict[label] = t_e

        if t_energydict:
            # Find a minimal value of Spiral and count it as 0
            minenergy = min(t_energydict.values())

            for key in six.iterkeys(t_energydict):
                t_energydict[key] = t_energydict[key] - minenergy

        self.ctx.energydict = t_energydict

    def return_results(self):
        """
        Retrieve results of converge calculations
        """

        failed_labels = []

        for label in six.iterkeys(self.ctx.wf_dict['q_vectors']):
            if label not in six.iterkeys(self.ctx.energydict):
                failed_labels.append(label)

        out = {'workflow_name': self.__class__.__name__,
               'workflow_version': self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'energies': self.ctx.energydict,
               'q_vectors': self.ctx.wf_dict['q_vectors'],
               'failed_labels': failed_labels,
               'energy_units': 'eV',
               'info': self.ctx.info,
               'warnings': self.ctx.warnings,
               'errors': self.ctx.errors}

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
