# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
    In this module you find the workflow 'fleur_relax_wc' for geometry optimization.
"""
from __future__ import absolute_import
from __future__ import print_function
import copy

from aiida.engine import WorkChain, ToContext, while_
from aiida.engine import submit
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.common.exceptions import NotExistent

from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, optimize_calc_options
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida_fleur.calculation.fleur import FleurCalculation

import six
from six.moves import range

StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')

class fleur_relax_wc(WorkChain):
    """
    This workflow calculates spin spiral dispersion of a structure.
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
                   'fleur_runmax': 10,              # Maximum number of fleur jobs/starts
                   'density_criterion' : 0.00005,  # Stop if charge denisty is converged below this value
                   'serial' : False,                # execute fleur with mpi or without
                   'itmax_per_run' : 30,
                   'alpha_mix' : 0.015,              #mixing parameter alpha
                   'relax_iter' : 5,
                   'relax_specie' : {},
                   'force_converged' : 0.0002,
                   'qfix' : 2,
                   'forcealpha' : 0.5,
                   'forcemix' : 2,
                   'force_criterion' : 0.001,
                   'inpxml_changes' : [],      # (expert) List of further changes applied after the inpgen run
                   }
    
    _scf_keys = ['fleur_runmax', 'density_criterion', 'serial', 'itmax_per_run', 'inpxml_changes'] #a list of wf_params needed for scf workflow

    @classmethod
    def define(cls, spec):
        super(fleur_relax_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False, default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False, default=Dict(dict=cls._default_options))
        #spec.input("settings", valid_type=Dict, required=False)
                                                                              
        spec.outline(
            cls.start,
            cls.converge_scf,
            cls.calculate_forces,
            while_(cls.condition)(
                cls.converge_scf,
                cls.calculate_forces
                ),
            cls.return_results,
        )

        spec.output('out', valid_type=Dict)

        #exit codes
        spec.exit_code(301, 'ERROR_INVALID_INPUT_RESOURCES', message="Invalid input, plaese check input configuration.")
        spec.exit_code(302, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED', message="Some required inputs are missing.")
        spec.exit_code(303, 'ERROR_INVALID_CODE_PROVIDED', message="Invalid code node specified, please check inpgen and fleur code nodes.")
        spec.exit_code(305, 'ERROR_CHANGING_FLEURINPUT_FAILED', message="Input file modification failed.")
        spec.exit_code(306, 'ERROR_CALCULATION_INVALID_INPUT_FILE', message="Input file is corrupted after user's modifications.")
        spec.exit_code(307, 'ERROR_FLEUR_CALCULATION_FALIED', message="Fleur calculation failed.")
        spec.exit_code(308, 'ERROR_DID_NOT_CONVERGE', message="Optimization cycle did not lead to convergence of forces.")
        spec.exit_code(309, 'ERROR_REFERENCE_CALCULATION_FAILED', message="Reference scf calculation failed.")
        spec.exit_code(310, 'ERROR_REFERENCE_CALCULATION_NOREMOTE', message="Found no reference calculation remote repository.")
        spec.exit_code(314, 'ERROR_RELAX_FAILED', message="New positions calculation failed.")
        spec.exit_code(333, 'ERROR_NOT_OPTIMAL_RESOURSES', message="Computational resourses are not optimal.")

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started relaxation of a structure workflow version {}\n'
                    ''.format(self._workflowversion))
                    
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        
        #Pre-initialization of some variables
        self.ctx.loop_count = 0
        self.ctx.make_fleurinp = True

        #initialize the dictionary using defaults if no wf paramters are given
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
        
        #initialize the dictionary using defaults if no options are given
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

    def converge_scf(self):
        """
        Converge charge density for collinear case.
        """
        inputs = {}
        inputs = self.get_inputs_scf().copy()
        inputs['wf_parameters'] = Dict(dict=inputs['wf_parameters'])
        inputs['calc_parameters'] = Dict(dict=inputs['calc_parameters'])
        inputs['options'] = Dict(dict=inputs['options'])
        res = self.submit(fleur_scf_wc, **inputs)
        return ToContext(reference=res)
    
    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = {}

        #Note that relax wf parameters contain more information than needed for scf
        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)
        
        #deepcopy to protect wf params
        inputs['wf_parameters'] = copy.deepcopy(scf_wf_param)
        
        inputs['options'] = self.ctx.options
        
        #Try to retrieve calculaion parameters from inputs
        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        if self.ctx.make_fleurinp:
            #generate inp.xml in scf workflow
            inputs['inpgen'] = self.inputs.inpgen
            inputs['structure'] = self.inputs.structure
            self.ctx.make_fleurinp = False
        else:
            #use inp.xml from previous iteration
            inputs['remote_data'] = self.ctx.forr.outputs.remote_folder
            #do not forget about relax.xml file
            inputs['settings'] = Dict(dict={'remove_from_remotecopy_list': ['broyd*'], 'additional_remotecopy_list': ['relax.xml']})
            #switch l_f off for scf calculation
            inputs['wf_parameters']['inpxml_changes'].append((u'set_inpchanges', {u'change_dict' : {u'l_f' : False}}))

        #Initialize codes
        inputs['fleur'] = self.inputs.fleur

        return inputs
    
   
    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')
        try:
            fleurin = self.ctx.reference.outputs.fleurinp
        except NotExistent:
            error = 'Fleurinp generated in previous scf calculation is not found.'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        #deepcopy inpchanges to protect wf params
        fchanges = copy.deepcopy(self.ctx.wf_dict['inpxml_changes'])
        
        for specie,relax_dir in six.iteritems(self.ctx.wf_dict.get('relax_specie')):
            fchanges.append((u'set_atomgr_att', ({u'force' : [(u'relaxXYZ', relax_dir)]}, False, specie)))
        
        #give 60 more iterations to generate new positions
        if self.ctx.loop_count == 0:
            fchanges.append((u'set_inpchanges', {u'change_dict' : {u'l_f' : True, u'itmax' : 60, u'epsforce' : self.ctx.wf_dict.get('force_criterion'), u'force_converged' : self.ctx.wf_dict.get('force_converged'), u'qfix' : self.ctx.wf_dict.get('qfix'), u'forcealpha' : self.ctx.wf_dict.get('forcealpha'), u'forcemix' : self.ctx.wf_dict.get('forcemix')}}))
        else:
            fchanges.append((u'set_inpchanges', {u'change_dict' : {u'l_f' : True, u'itmax' : 60}}))
        
        if fchanges:# change inp.xml file
            fleurmode = FleurinpModifier(fleurin)
            avail_ac_dict = fleurmode.get_avail_actions()

            # apply further user dependend changes
            for change in fchanges:
                function = change[0]
                para = change[1]
                method = avail_ac_dict.get(function, None)
                if not method:
                    error = ("ERROR: Input 'inpxml_changes', function {} "
                                "is not known to fleurinpmodifier class, "
                                "plaese check/test your input. I abort..."
                                "".format(method))
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

                else:# apply change
                    if function==u'set_inpchanges':
                        method(**para)
                    else:
                        method(*para)

            # validate?
            apply_c = True
            try:
                fleurmode.show(display=False, validate=True)
            except XMLSyntaxError:
                error = ('ERROR: input, user wanted inp.xml changes did not validate')
                #fleurmode.show(display=True)#, validate=True)
                self.report(error)
                apply_c = False
                return self.exit_codes.ERROR_CALCULATION_INVALID_INPUT_FILE
            
            # apply
            if apply_c:
                out = fleurmode.freeze()
                self.ctx.fleurinp = out
            return
        else: # otherwise do not change the inp.xml
            self.ctx.fleurinp = fleurin
            return
            
    def check_kpts(self, fleurinp):
        """
        This routine checks if the total number of requested cpus
        is a factor of kpts and makes small optimisation.
        """
        adv_nodes, adv_cpu_nodes, message, exit_code = optimize_calc_options(fleurinp,
                      int(self.ctx.options['resources']['num_machines']),
                      int(self.ctx.options['resources']['num_mpiprocs_per_machine']))

        if 'WARNING' in message:
            self.ctx.warnings.append(message)

        self.report(message)

        self.ctx.options['resources']['num_machines'] = adv_nodes
        self.ctx.options['resources']['num_mpiprocs_per_machine'] = adv_cpu_nodes
        
        return exit_code

    def calculate_forces(self):
        '''
        This routine calculaties forces of a pre-converged structure
        '''
        calc = self.ctx.reference
        
        if not calc.is_finished_ok:
            message = ('The SCF calculation is not finished OK.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED
        
        try:
            outpara_node = calc.outputs.output_scf_wc_para
        except NotExistent:
            message = ('The SCF calculation failed, no scf output node.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED
        
        outpara = outpara_node.get_dict()
        
        t_e = outpara.get('total_energy', 'failed')
        if not (type(t_e) is float):
            message = ('Did not manage to extract float total energy from the SCF calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        self.report('INFO: run new positions calculations')

        status = self.change_fleurinp()
        if not (status is None):
            return status

        fleurin = self.ctx.fleurinp
        if self.check_kpts(fleurin):
            self.control_end_wc('ERROR: Not optimal computational resourses.')
            return self.exit_codes.ERROR_NOT_OPTIMAL_RESOURSES

        #Do not copy broyd* files from the parent but copy relax.xml
        if self.ctx.loop_count == 0:
            settings = Dict(dict={'remove_from_remotecopy_list': ['broyd*'], 'additional_retrieve_list': ['relax.xml']})
        else:
            settings = Dict(dict={'remove_from_remotecopy_list': ['broyd*'], 'additional_retrieve_list': ['relax.xml'],
                'additional_remotecopy_list': ['relax.xml']})

        #Retrieve remote folder of the reference calculation
        pk_last = 0
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.node_type == u'process.calculation.calcjob.CalcJobNode.':
                if i.process_class is FleurCalculation:
                    if pk_last < i.pk:
                        pk_last = i.pk
        try:
            remote_old = load_node(pk_last).outputs.remote_folder
        except AttributeError:
            message = ('Found no remote folder of the referece scf calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_NOREMOTE
        
        label = 'New positions calculation'
        description = 'This calculation computes new atom positions using one of the existing algorithms in FLEUR'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code, remote_old, fleurin, options, label, description, settings, serial=self.ctx.wf_dict['serial'])
        future = self.submit(inputs_builder)
        return ToContext(forr=future)

    def condition(self):
        try:
            calculation = self.ctx.forr
            if not calculation.is_finished_ok:
                message = ('ERROR: New atom positions calculation failed somehow it has '
                        'exit status {}'.format(calculation.exit_status))
                self.control_end_wc(message)
                return self.exit_codes.ERROR_RELAX_FAILED
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have new atom positions calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_RELAX_FAILED

        try:
            self.ctx.forces = calculation.outputs.output_parameters.dict.force_largest
        except AttributeError:
            message = 'ERROR: Did not manage to read the largest force'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_RELAX_FAILED
    
        if abs(self.ctx.forces) < self.ctx.wf_dict['force_criterion']:
            return False

        self.ctx.loop_count += 1

        return True
        
    def loop_count(self):
        """
        Exits the workchain and throws an exit_code
        """
        if (self.ctx.loop_count == self.ctx.wf_dict['relax_iter']):
            message = ('Did not reach structure optimization in a given number of scf iterations.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_DID_NOT_CONVERGE
        
    def return_results(self):
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors,
               'force' : self.ctx.forces,
               'force_iter_done' : self.ctx.loop_count
               }
       
        self.out('out', Dict(dict=out))

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg) # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()
