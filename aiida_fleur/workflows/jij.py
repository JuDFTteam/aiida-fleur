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
from lxml.etree import XMLSyntaxError

from aiida.engine import WorkChain, ToContext
from aiida.engine import submit
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, optimize_calc_options
from aiida_fleur.workflows.spst import fleur_spst_wc
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

import six
from six.moves import range
from six.moves import map

StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')

class fleur_jij_wc(WorkChain):
    """
    This workflow calculates Heisenberg exchange interaction parameters of a structure.
    """
    
    _workflowversion = "0.1.0a"

    _default_options = {
                        'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 1},
                        'max_wallclock_seconds' : 2*60*60,
                        'queue_name' : '',
                        'custom_scheduler_commands' : '',
                        'import_sys_environment' : False,
                        'environment_variables' : {}}
    
    _wf_default = {
                   'fleur_runmax': 10,              # Maximum number of fleur jobs/starts (defauld 30 iterations per start)
                   'density_criterion' : 0.00005,  # Stop if charge denisty is converged below this value
                   'serial' : False,                # execute fleur with mpi or without
                   'itmax_per_run' : 30,
                   'beta' : 0.000,
                   'alpha_mix' : 0.015,              #mixing parameter alpha
                   'q_mesh' : (2,2,1),
                   'inpxml_changes' : [],      # (expert) List of further changes applied after the inpgen run
                   }
    
    _jij_keys = ['fleur_runmax', 'density_criterion', 'serial', 'itmax_per_run', 'inpxml_changes',
    'beta', 'alpha_mix'] #a list of wf_params needed for scf workflow

    @classmethod
    def define(cls, spec):
        super(fleur_spst_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False, default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False, default=Dict(dict=cls._default_options))
        #spec.input("settings", valid_type=Dict, required=False)
                                                                              
        spec.outline(
            cls.start,
            cls.analyze_structure,
            cls.spsp_energies,
            cls.jij_comp,
            cls.get_results,
            cls.return_results
        )

        spec.output('out', valid_type=Dict)
    
        #exit codes
        spec.exit_code(301, 'ERROR_INVALID_INPUT_RESOURCES', message="Invalid input, plaese check input configuration.")
        spec.exit_code(302, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED', message="Some required inputs are missing.")
        spec.exit_code(303, 'ERROR_INVALID_CODE_PROVIDED', message="Invalid code node specified, please check inpgen and fleur code nodes.")
        spec.exit_code(304, 'ERROR_INPGEN_CALCULATION_FAILED', message="Inpgen calculation failed.")
        spec.exit_code(305, 'ERROR_CHANGING_FLEURINPUT_FAILED', message="Input file modification failed.")
        spec.exit_code(306, 'ERROR_CALCULATION_INVALID_INPUT_FILE', message="Input file is corrupted after user's modifications.")
        spec.exit_code(307, 'ERROR_FLEUR_CALCULATION_FALIED', message="Fleur calculation failed.")
        spec.exit_code(308, 'ERROR_CONVERGENCE_NOT_ARCHIVED', message="SCF cycle did not lead to convergence.")
        spec.exit_code(309, 'ERROR_REFERENCE_CALCULATION_FAILED', message="Reference calculation failed.")
        spec.exit_code(310, 'ERROR_REFERENCE_CALCULATION_NOREMOTE', message="Found no reference calculation remote repository.")
        spec.exit_code(316, 'ERROR_SPST_FAILED', message="Spin spiral dispersion workchain failed.")
        spec.exit_code(333, 'ERROR_NOT_OPTIMAL_RESOURSES', message="Computational resourses are not optimal.")
    
    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Jij calculation workflow version {}\n'
                    ''.format(self._workflowversion))
                    
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []

        #initialize the dictionary using defaults if no wf paramters are given by user
        wf_default = self._wf_default
        
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default
        
        #extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict
        
        #set up mixing parameter alpha
        self.ctx.wf_dict['inpxml_changes'].append((u'set_inpchanges', {u'change_dict' : {u'alpha' : self.ctx.wf_dict['alpha_mix']}}))
        
        #initialize the dictionary using defaults if no options are given by user
        defaultoptions = self._default_options
        
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions
        
        #extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        #Check if user gave valid inpgen and fleur execulatbles
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
        This function analyses structure:
        Checks if it is a bulk or film
        Checks symmetries
        """
        from ase.dft.kpoints import monkhorst_pack
        import ase.spacegroup
        ase_struct = self.inputs.structure.get_ase()
    
        spacegroup = ase.spacegroup.get_spacegroup(ase_struct)
        sym_op, _ = spacegroup.get_op()
        
        #represent sym_op in the basis of the reciprocal lattice
        sym_op2 = np.array([np.dot(np.dot(ase_struct.cell, i.T), np.linalg.inv(ase_struct.cell)) for i in sym_op])
        qus = monkhorst_pack(self.ctx.wf_dict['q_mesh'])
        calc_qus = qus
        storage = []
        
        #create a list of independent q_vectors and provide storage of unused ones
        for vec in qus:
            if not ((calc_qus==vec).all(1)).any():
                #if vec is already deleted from calc_qus
                continue
            for tmp_vec in qus:
                #if np.allclose(calc_qus, vec):
                    #if vec == tmp_vec do nothing
                #    continue
                for sym in sym_op2:
                    #check all available symmetries
                    if np.allclose(np.dot(vec, sym), tmp_vec):
                        ind_del = np.nonzero((calc_qus==tmp_vec).all(1))[0][0]
                        calc_qus = np.delete(calc_qus, ind_del, 0)
                        storage.append((vec, sym, tmp_vec))
                        #stop searching for a symmetry that connects vec and tmp_vec
                        break
    
        self.ctx.storage = storage
        self.ctx.calc_qus = calc_qus

    def spsp_energies(self):
        """
        Calculate spin spiral energy dispersion.
        """
        inputs = {}
        inputs = self.get_inputs_jij()
        res = self.submit(fleur_spst_wc, **inputs)
        return ToContext(spst_wc=res)
    
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
        #break all symmetries in spst workchain
        spst_wf_param['prop_dir'] = [0.23, 0.56, 0.52]
        
        #constuct and pass q_mesh
        spst_wf_param['q_vectors'] = [' '.join(map(str, i)) for i in self.ctx.calc_qus]
        
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
        t_energydict = []
        q_vectors = []
        try:
            calculation = self.ctx.spst_wc
            if not calculation.is_finished_ok:
                message = ('ERROR: Spin spiral dispersion calculation failed somehow it has '
                        'exit status {}'.format(calculation.exit_status))
                self.control_end_wc(message)
                return self.exit_codes.ERROR_SPST_FAILED
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have a spin spiral dispersion calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SPST_FAILED
    
        try:
            t_energydict = calculation.outputs.out.dict.energies
            q_vec_done = calculation.outputs.out.dict.q_vectors
            q_vec_done = np.array([np.array([float(a) for a in i.split()]) for i in q_vec_done])
        except AttributeError:
            message = ('Did not manage to read energies or q vectors from spst workchain.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SPST_FAILED

        self.ctx.all_res = []
        for i in len(t_energydict):
            for qpt in self.ctx.storage:
                if np.allclose(qpt[0], q_vec_done[i]):
                    res = (qpt[2], t_energydict[i])
                    self.ctx.all_res.append(res)
            
    def get_real_jij(self):
        pass

    def return_results(self):
    
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'is_it_force_theorem' : True,
               'energies' : self.ctx.energy_dict,
               'q_vectors' : self.ctx.wf_dict['q_vectors'],
               'energy_units' : 'eV',
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors
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

