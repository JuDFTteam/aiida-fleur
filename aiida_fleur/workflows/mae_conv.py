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
    In this module you find the workflow 'FleurMAEWorkChain' for the calculation of
    Magnetic Anisotropy Energy converging all the directions.
"""

from __future__ import absolute_import

import six

from aiida.engine import WorkChain
from aiida.engine import calcfunction as cf
from aiida.plugins import DataFactory
from aiida.orm import Code

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.workflows.scf import FleurScfWorkChain

# pylint: disable=invalid-name
StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurMaeConvWorkChain(WorkChain):
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
        'sqas': {'label' : [0.0, 0.0]},
        'alpha_mix': 0.05,
        'density_converged': 0.00005,
        'serial': False,
        'itmax_per_run': 30,
        'soc_off': [],
        'inpxml_changes': [],
    }

    _scf_keys = ['fleur_runmax', 'density_converged', 'serial', 'itmax_per_run', 'inpxml_changes']

    @classmethod
    def define(cls, spec):
        super(FleurMaeConvWorkChain, cls).define(spec)
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
        spec.exit_code(301, 'ERROR_INVALID_INPUT_RESOURCES',
                       message="Invalid input, plaese check input configuration.")
        spec.exit_code(302, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED',
                       message="Some required inputs are missing.")
        spec.exit_code(303, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")
        spec.exit_code(304, 'ERROR_INPGEN_CALCULATION_FAILED',
                       message="Inpgen calculation failed.")
        spec.exit_code(305, 'ERROR_CHANGING_FLEURINPUT_FAILED',
                       message="Input file modification failed.")
        spec.exit_code(306, 'ERROR_CALCULATION_INVALID_INPUT_FILE',
                       message="Input file is corrupted after user's modifications.")
        spec.exit_code(307, 'ERROR_FLEUR_CALCULATION_FALIED',
                       message="Fleur calculation failed.")
        spec.exit_code(308, 'ERROR_CONVERGENCE_NOT_ARCHIVED',
                       message="SCF cycle did not lead to convergence.")
        spec.exit_code(309, 'ERROR_REFERENCE_CALCULATION_FAILED',
                       message="Reference calculation failed.")
        spec.exit_code(310, 'ERROR_REFERENCE_CALCULATION_NOREMOTE',
                       message="Found no reference calculation remote repository.")
        spec.exit_code(311, 'ERROR_FORCE_THEOREM_FAILED',
                       message="Force theorem calculation failed.")
        spec.exit_code(312, 'ERROR_ALL_SQAS_FAILED',
                       message="Convergence MAE calculation failed for all SQAs.")
        spec.exit_code(313, 'ERROR_SOME_SQAS_FAILED',
                       message="Convergence MAE calculation failed for some SQAs.")

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Magnetic Anisotropy Energy calculation workflow version {}\n'
                    ''.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        # defaults that will be written into the output node in case of failure
        # note: convergence branch always generates defaults inside get_results
        self.ctx.t_energydict = []
        self.ctx.mae_thetas = []
        self.ctx.mae_phis = []

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

        # switch off SOC on an atom specie
        for atom_label in self.ctx.wf_dict['soc_off']:
            self.ctx.wf_dict['inpxml_changes'].append(
                ('set_species_label',
                 {'at_label': atom_label,
                  'attributedict': {'special': {'socscale': 0.0}},
                  'create': True
                 }))

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

    def converge_scf(self):
        """
        Converge charge density with or without SOC.
        Depending on a branch of MAE calculation, submit a single Fleur calculation to obtain
        a reference for further force theorem calculations or
        submit a set of Fleur calculations to converge charge density for all given SQAs.
        """
        inputs = {}
        for key, socs in six.iteritems(self.ctx.wf_dict['sqas']):
            inputs[key] = self.get_inputs_scf()
            inputs[key]['calc_parameters']['soc'] = {'theta': socs[0], 'phi': socs[1]}
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

        inputs['options'] = self.ctx.options

        # Try to retrieve calculaion parameters from inputs
        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        # Initialize codes
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur
        # Initialize the strucutre
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
        htr_to_ev = 27.21138602

        for label in six.iterkeys(self.ctx.wf_dict['sqas']):
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
                    'SCF worflow: {}'.format(label))
                self.ctx.warnings.append(message)
                continue
            e_u = outpara.get('total_energy_units', 'Htr')
            if e_u == 'Htr' or 'htr':
                t_e = t_e * htr_to_ev
            t_energydict[label] = t_e

        if t_energydict:
            # Find a minimal value of MAE and count it as 0
            minenergy = min(t_energydict.values())

            for key in six.iterkeys(t_energydict):
                t_energydict[key] = t_energydict[key] - minenergy

        self.ctx.energydict = t_energydict

    def return_results(self):
        """
        Retrieve results of converge calculations
        """

        failed_labels = []

        for label in six.iterkeys(self.ctx.wf_dict['sqas']):
            if label not in six.iterkeys(self.ctx.energydict):
                failed_labels.append(label)

        out = {'workflow_name': self.__class__.__name__,
               'workflow_version': self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'maes': self.ctx.energydict,
               'sqas': self.ctx.wf_dict['sqas'],
               'failed_labels': failed_labels,
               'mae_units': 'eV',
               'info': self.ctx.info,
               'warnings': self.ctx.warnings,
               'errors': self.ctx.errors}

        # create link to workchain node
        out = save_output_node(Dict(dict=out))
        self.out('out', out)

        if not self.ctx.energydict:
            return self.exit_codes.ERROR_ALL_SQAS_FAILED
        elif failed_labels:
            return self.exit_codes.ERROR_SOME_SQAS_FAILED

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
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
