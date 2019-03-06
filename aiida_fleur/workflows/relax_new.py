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

from aiida.work.workchain import WorkChain, ToContext, while_
from aiida.work.launch import submit
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, optimize_calc_options
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida.orm import Code, DataFactory, load_node
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida.common.datastructures import calc_states

StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
ParameterData = DataFactory('parameter')
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
                   'fleur_runmax': 10,              # Maximum number of fleur jobs/starts (defauld 30 iterations per start)
                   'density_criterion' : 0.00005,  # Stop if charge denisty is converged below this value
                   'serial' : False,                # execute fleur with mpi or without
                   'itmax_per_run' : 30,
                   'alpha_mix' : 0.015,              #mixing parameter alpha
                   'relax_iter' : 5,
                   'relax_specie' : {},
                   'force_criterion' : 0.00002,
                   'inpxml_changes' : [],      # (expert) List of further changes applied after the inpgen run
                   }
    
    _scf_keys = ['fleur_runmax', 'density_criterion', 'serial', 'itmax_per_run', 'inpxml_changes'] #a list of wf_params needed for scf workflow

    ERROR_INVALID_INPUT_RESOURCES = 1
    ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED = 2
    ERROR_INVALID_CODE_PROVIDED = 3
    ERROR_INPGEN_CALCULATION_FAILED = 4
    ERROR_CHANGING_FLEURINPUT_FAILED = 5
    ERROR_CALCULATION_INVALID_INPUT_FILE = 6
    ERROR_FLEUR_CALCULATION_FALIED = 7
    ERROR_CONVERGENCE_NOT_ARCHIVED = 8
    ERROR_REFERENCE_CALCULATION_FAILED = 9

    @classmethod
    def define(cls, spec):
        super(fleur_relax_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False, default=ParameterData(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=ParameterData, required=False, default=ParameterData(dict=cls._default_options))
        #spec.input("settings", valid_type=ParameterData, required=False)
                                                                              
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

        spec.output('out', valid_type=ParameterData)

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started relaxation of a structure workflow version {}\n'
                    ''.format(self._workflowversion))
                    
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        
        #Pre-initialization of some variables
        self.ctx.loop_count = 0
        self.ctx.make_fleurinp = True

        #Retrieve WorkFlow parameters,
        #initialize the dictionary using defaults if no wf paramters are given by user
        wf_default = self._wf_default
        
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default
        
        #extend wf parameters given by user using defaults
        for key, val in wf_default.iteritems():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict
        
        #set up mixing parameter alpha
        self.ctx.wf_dict['inpxml_changes'].append((u'set_inpchanges', {u'change_dict' : {u'alpha' : self.ctx.wf_dict['alpha_mix']}}))
        
        #Retrieve calculation options,
        #initialize the dictionary using defaults if no options are given by user
        defaultoptions = self._default_options
        
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions
        
        #extend options given by user using defaults
        for key, val in defaultoptions.iteritems():
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
                return self.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                return self.ERROR_INVALID_CODE_PROVIDED

    def converge_scf(self):
        """
        Converge charge density for collinear case.
        """
        inputs = {}
        inputs = self.get_inputs_scf().deepcopy()
        print inputs
        inputs['wf_parameters'] = ParameterData(dict=inputs['wf_parameters'])
        inputs['calc_parameters'] = ParameterData(dict=inputs['calc_parameters'])
        inputs['options'] = ParameterData(dict=inputs['options'])
        res = self.submit(fleur_scf_wc, **inputs)
        return ToContext(reference=res)
    
    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = {}

        # Retrieve scf wf parameters and options form inputs
        #Note that relax wf parameters contain more information than needed for scf
        #Note: by the time this function is executed, wf_dict is initialized by inputs or defaults
        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)
        inputs['wf_parameters'] = scf_wf_param
        
        inputs['options'] = self.ctx.options
        
        #Try to retrieve calculaion parameters from inputs
        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        #TODO
        #if not a first force calculation cycle, provide fleurinp and remote folder
        #remove stucture in this case

        if self.ctx.make_fleurinp:
            #generate inp.xml in scf workflow
            inputs['inpgen'] = self.inputs.inpgen
            inputs['structure'] = self.inputs.structure
            self.ctx.make_fleurinp = False
        else:
            #use inp.xml from previous iteration
            inputs['remote_data'] = self.ctx.forr.out.remote_folder
            inputs['settings'] = ParameterData(dict={'remove_from_remotecopy_list': ['broyd*']})#, 'remove_from_localcopy_list': ['cdn_last.hdf']})
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
            fleurin = self.ctx.reference.out.fleurinp
        except AttributeError:
            error = 'A force theorem calculation did not find fleur input generated be the reference claculation.'
            self.control_end_wc(error)
            return self.ERROR_REFERENCE_CALCULATION_FAILED

        #copy inpchanges from wf parameters
        fchanges = list(self.ctx.wf_dict['inpxml_changes'])
        
        for specie,relax_dir in self.ctx.wf_dict.get('relax_specie').iteritems():
            fchanges.append((u'set_atomgr_att', ({u'force' : [(u'relaxXYZ', relax_dir)]}, False, specie)))
        
        fchanges.append((u'set_inpchanges', {u'change_dict' : {u'l_f' : True, u'itmax' : 60}}))#, u'epsforce' : self.ctx.wf_dict.get('force_criterion')}}))
        
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
                    return self.ERROR_CHANGING_FLEURINPUT_FAILED

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
                return self.ERROR_CALCULATION_INVALID_INPUT_FILE
            
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

        if exit_code:
        #TODO: make an error exit
            pass

        if 'WARNING' in message:
            self.ctx.warnings.append(message)

        self.report(message)

        self.ctx.options['resources']['num_machines'] = adv_nodes
        self.ctx.options['resources']['num_mpiprocs_per_machine'] = adv_cpu_nodes

    def calculate_forces(self):
        '''
        This routine calculaties forces of a pre-converged structure
        '''
        calc = self.ctx.reference
        try:
            outpara_check = calc.get_outputs_dict()['output_scf_wc_para']
        except KeyError:
            message = ('The reference SCF calculation failed, no scf output node.')
            self.ctx.errors.append(message)
            self.ctx.successful = False
            return
        
        outpara = calc.get_outputs_dict()['output_scf_wc_para'].get_dict()
        
        if not outpara.get('successful', False):
            message = ('The reference SCF calculation was not successful.')
            self.ctx.errors.append(message)
            self.ctx.successful = False
            return
        
        t_e = outpara.get('total_energy', 'failed')
        if not (type(t_e) is float):
            self.ctx.successful = False
            message = ('Did not manage to extract float total energy from the reference SCF calculation.')
            self.ctx.errors.append(message)
            return

        self.report('INFO: run Force theorem calculations')

        self.change_fleurinp()
        fleurin = self.ctx.fleurinp
        self.check_kpts(fleurin)

        #Do not copy broyd* files from the parent
        settings = ParameterData(dict={'remove_from_remotecopy_list': ['broyd*']})
    
        #Retrieve remote folder of the reference calculation
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.type == u'calculation.job.fleur.fleur.FleurCalculation.':
                try:
                    remote_old = i.out.remote_folder
                except AttributeError:
                    message = ('Found no remote folder of the referece scf calculation.')
                    self.ctx.warnings.append(message)
                    #self.ctx.successful = False
                    remote_old = None
        
        label = 'Forces'
        description = 'This is a calculation of forces'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code, remote_old, fleurin, options, label, description, settings, serial=self.ctx.wf_dict['serial'])
        future = self.submit(inputs_builder)
        return ToContext(forr=future)

    def condition(self):
        #at this point self.ctx.successful == True if the reference calculation is OK
        #the force theorem calculation is checked inside if
        if self.ctx.successful:
            try:
                calculation = self.ctx.forr
                calc_state = calculation.get_state()
                if calc_state != calc_states.FINISHED or calculation.exit_status != 0:
                    self.ctx.successful = False
                    message = ('ERROR: Force theorem Fleur calculation failed somehow it is '
                            'in state {} with exit status {}'.format(calc_state, calculation.exit_status))
                    self.ctx.errors.append(message)
            except AttributeError:
                self.ctx.successful = False
                message = 'ERROR: Something went wrong I do not have a force theorem Fleur calculation'
                self.ctx.errors.append(message)
        
            #now self.ctx.successful == True if forceTheorem calculation is successful
            #TODO change back
            if self.ctx.successful:
                try:
                    self.ctx.forces = calculation.out.output_parameters.dict.force_largest
                except AttributeError:
                    self.ctx.successful = False
                    message = ('Did not manage to read largest force.')
                    self.ctx.errors.append(message)
    
        if abs(self.ctx.forces) < self.ctx.wf_dict['force_criterion']:
            return False

        self.ctx.loop_count += 1

        if (self.ctx.loop_count == self.ctx.wf_dict['relax_iter']):
            self.ctx.successful = False
            self.ctx.warnings.append('Did not manage to relax forces in given number of iterations')
            return False

        return True
        
    def return_results(self):
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'successful' : self.ctx.successful,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors,
               'force' : self.ctx.forces,
               'force_iter_made' : self.ctx.loop_count
               }
       
       #TODO create a fleurinp node
       
        self.out('out', ParameterData(dict=out))

