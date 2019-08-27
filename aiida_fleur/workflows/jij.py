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
    In this module you find the workflow 'fleur_jij_wc' for the calculation of
    Heisenberg exchange interaction parameters.
"""

from __future__ import absolute_import
import numpy as np

import six

from aiida.engine import WorkChain, ToContext
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.orm import StructureData, Dict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain

# pylint: disable=invalid-name
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name


class FleurJijWorkChain(WorkChain):
    """
    This workflow calculates Heisenberg exchange interaction parameters of a structure.
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
        'density_criterion': 0.00005,
        'serial': False,
        'itmax_per_run': 30,
        'beta': 0.000,
        'alpha_mix': 0.015,
        'q_mesh': (2, 2, 1),
        'inpxml_changes': [],
    }

    _ssdisp_keys = ['fleur_runmax', 'density_criterion', 'serial', 'itmax_per_run',
                    'inpxml_changes', 'beta', 'alpha_mix']

    @classmethod
    def define(cls, spec):
        super(FleurJijWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False,
                   default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False,
                   default=Dict(dict=cls._default_options))
        #spec.input("settings", valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            cls.analyze_structure,
            cls.collect_exsiting,
            cls.submit_ssdisp,
            cls.fourier_tr,
            cls.get_results,
            cls.return_results
        )

        spec.output('out', valid_type=Dict)

        #exit codes


    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Spin Stiffness calculation workflow version {}\n'
                    ''.format(self._workflowversion))
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

        if wf_dict['input_converged']:
            if not 'remote' in self.inputs:
                error = ("Remote calculation was not specified. However, 'input_converged was set"
                         " to True.")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

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

    def analyze_structure(self):
        """
        This method performs strucutre analysis and generates a list of q-vectors to be calculated.
        It analyses structure symmetry and get rids of 
        """
        from ase.dft.kpoints import monkhorst_pack
        import ase.spacegroup

        ase_struct = self.inputs.structure.get_ase()

        spacegroup = ase.spacegroup.get_spacegroup(ase_struct)
        sym_op, _ = spacegroup.get_op()

        #represent sym_op in the basis of the reciprocal lattice
        sym_op2 = np.array([np.dot(np.dot(ase_struct.cell, i.T),
                                   np.linalg.inv(ase_struct.cell)) for i in sym_op])
        qus = monkhorst_pack(self.ctx.wf_dict['q_mesh'])
        calc_qus = qus
        storage = []

        #create a list of independent q_vectors and provide storage of unused ones
        for vec in qus:
            if not ((calc_qus == vec).all(1)).any():
                #if vec is already deleted from calc_qus
                continue
            for tmp_vec in qus:
                if np.allclose(tmp_vec, vec):
                    #if vec == tmp_vec do nothing
                    continue
                for sym in sym_op2:
                    #check all available symmetries
                    if np.allclose(np.dot(vec, sym), tmp_vec):
                        ind_del = np.nonzero(
                            (calc_qus == tmp_vec).all(1))[0][0]
                        calc_qus = np.delete(calc_qus, ind_del, 0)
                        storage.append((vec, sym, tmp_vec))
                        #stop searching for a symmetry that connects vec and tmp_vec
                        break

        self.ctx.storage = storage
        self.ctx.calc_qus = calc_qus

    def collect_exsiting(self):
        """
        Searches through given WorkChain node for results of SSDisp.
        Checks if nodes correspond to :class:`aiida_fleur.workflows.ssdisp.FleurSSDispWorkChain`
        or to :class:`aiida_fleur.workflows.ssdisp_conv.FleurSSDispConvWorkChain`, strucutre used
        and fetches ready results. Afterwards, it updates the list of q-vector that will be
        submited.
        """

        existing_q_vectors = []
        existing_energies = []

        for prev_workchain in self.ctx.wf_dict['list_prev_ssdisp']:
            prev_node = load_node(prev_workchain)
            if prev_node is not FleurSSDispWorkChain:
                self.report('WARNING: drop node {} from the list of previous SSDisp workchains'
                            'because it is not FleurSSDispWorkChain.'.format(prev_workchain))
                continue

            if not prev_node.is_finished_ok:
                self.report('WARNING: drop node {} from the list of previous SSDisp workchains'
                            'because if is not finished ok.'.format(prev_workchain))
                continue

            try:
                out_dict = prev_node.outputs.out.get_dict()
            except NotExistent:
                self.report('WARNING: drop node {} from the list of previous SSDisp workchains'
                            'because I could not load output dictionary.'.format(prev_workchain))
                continue

            for i, q_vector in enumerate(out_dict['q_vectors']):
                energy = out_dict['energies'][i]
                if q_vector in existing_q_vectors:
                    if abs((existing_energies[existing_q_vectors.index(q_vector)] -
                            energy) / energy) > 0.03:
                        return self.exit_codes.ERROR_INCONSISTENT_INPUT_SSDISP
                else:
                    existing_q_vectors.append(q_vector)
                    existing_energies.append(energy)

        done_storage = []
        done_energies = []
        calc_qus = self.ctx.calc_qus.deepcopy()
        # refine existing q_vectors, throw that are not needed
        for i, q_check in enumerate(existing_q_vectors):
            q_check = np.array(q_check)
            if ((calc_qus == q_check).all(1)).any():
                # if there is q_check in calc_qus
                ind_del = np.nonzero((calc_qus == q_check).all(1))[0][0]
                calc_qus = np.delete(calc_qus, ind_del, 0)
                done_storage.append(q_check)
                done_energies.append(existing_energies[i])

        self.ctx.done_storage = done_storage
        self.ctx.done_energies = done_energies
        self.ctx.calc_qus_submit = calc_qus


    def spsp_energies(self):
        """
        Calculate spin spiral energy dispersion.
        """
        inputs = {}
        inputs = self.get_inputs_jij()
        res = self.submit(FleurSSDispWorkChain, **inputs)
        return ToContext(ssdisp_wc=res)

    def get_inputs_jij(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = {}

        # Retrieve spst wf parameters and options from inputs
        spst_wf_param = {}
        for key in self._spst_keys:
            spst_wf_param[key] = self.ctx.wf_dict.get(key)
       

        # constuct and pass q_mesh

        spst_wf_param['q_vectors'] = [list(i) for i in self.ctx.calc_qus_submit]

        inputs['wf_parameters'] = spst_wf_param

        inputs['options'] = self.ctx.options

        #Try to retrieve calculaion parameters from inputs
        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        #Initialize codes
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur
        #Initialize the strucutre
        inputs['structure'] = self.inputs.structure

        inputs['wf_parameters'] = Dict(dict=inputs['wf_parameters'])
        inputs['calc_parameters'] = Dict(dict=inputs['calc_parameters'])
        inputs['options'] = Dict(dict=inputs['options'])

        return inputs

    def get_results(self):
        """
        Generates results of the workchain.
        """

        ssdisp_workchain = self.ctx.ssdisp_wc

        if not ssdisp_workchain.is_finished_ok:
            message = ('ERROR: Spin spiral dispersion calculation failed somehow it has '
                        'exit status {}'.format(ssdisp_workchain.exit_status))
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SPST_FAILED

        try:
            energies = ssdisp_workchain.outputs.out.dict.energies
            q_vectors = ssdisp_workchain.outputs.out.dict.q_vectors
        except NotExistent:
            message = 'Did not manage to read energies or q vectors from SSDisp workchain.'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SPST_FAILED

        result = []
        # assemble input and ssdisp results
        for q_vector in self.ctx.calc_qus:
            q_vector = list(q_vector)
            if q_vector in q_vectors:
                result.append((q_vector, energies[q_vectors.index(q_vector)]))
            elif q_vector in self.ctx.done_storage:
                result.append((q_vector, self.ctx.done_energies[q_vectors.index(q_vector)]))
            else:
                return self.ctx.exit_codes.ERROR_MISSING_Q_VECTOR

        self.ctx.result = result


    def get_real_jij(self):
        pass

    def return_results(self):

        out = {'workflow_name': self.__class__.__name__,
               'workflow_version': self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'is_it_force_theorem': True,
               'energies': self.ctx.energy_dict,
               'q_vectors': self.ctx.wf_dict['q_vectors'],
               'energy_units': 'eV',
               'info': self.ctx.info,
               'warnings': self.ctx.warnings,
               'errors': self.ctx.errors
               }

        self.out('out', Dict(dict=out))

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()
