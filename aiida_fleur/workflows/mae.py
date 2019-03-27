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
    In this module you find the workflow 'fleur_mae_wc' for the calculation of
    Magnetic Anisotropy Energy.
    This workflow consists of modifyed parts of scf and eos workflows.
"""

from __future__ import absolute_import
from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import submit
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, optimize_calc_options
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida.common import CalcJobState
import six
from six.moves import range

StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
Dict = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')

class fleur_mae_wc(WorkChain):
    """
        This workflow calculates the Magnetic Anisotropy Energy of a structure.
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
                   'sqa_ref' : [0.7, 0.7],         # SQA for a reference calculation for the FT branch
                   'use_soc_ref' : False,           #True, if use SOC in reference calculation for the FT branch
                   'force_th' : True,               #Use the force theorem (True) or converge
                   'fleur_runmax': 10,              # Maximum number of fleur jobs/starts
                   'sqas_theta' : '0.0 1.57079 1.57079',
                   'sqas_phi' : '0.0 0.0 1.57079',
                   'alpha_mix' : 0.05,              #mixing parameter alpha
                   'density_criterion' : 0.00005,  # Stop if charge denisty is converged below this value
                   'serial' : False,                # execute fleur with mpi or without
                   'itmax_per_run' : 30,
                   'soc_off' : [],
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
        super(fleur_mae_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False, default=Dict(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False, default=Dict(dict=cls._default_options))
        #spec.input("settings", valid_type=Dict, required=False)
                                                                              
        spec.outline(
            cls.start,
            if_(cls.validate_input)(
                cls.converge_scf,
                cls.mae_force,
                cls.get_res_force,
            ).else_(
                cls.converge_scf,
                cls.get_results_converge,
            ),
        )

        spec.output('out', valid_type=Dict)

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Magnetic Anisotropy Energy calculation workflow version {}\n'
                    ''.format(self._workflowversion))
                    
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        #Retrieve WorkFlow parameters,
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
        #switch off SOC on an atom specie
        for specie in self.ctx.wf_dict['soc_off']:
                self.ctx.wf_dict['inpxml_changes'].append((u'set_species', (specie, {u'special' : {u'socscale' : 0.0}}, True)))
        
        #Check if sqas_theta and sqas_phi have the same length
        if (len(self.ctx.wf_dict.get('sqas_theta').split()) != len(self.ctx.wf_dict.get('sqas_phi').split())):
            error = ("Number of sqas_theta has to be equal to the nmber of sqas_phi")
            self.control_end_wc(error)
            return self.ERROR_INVALID_INPUT_RESOURCES
        
        #Retrieve calculation options,
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
                return self.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                return self.ERROR_INVALID_CODE_PROVIDED

    def validate_input(self):
        """
        Choose the branch of MAE calculation:
            a) converge charge density for all given SQAs
            b) 1) converge charge density for reference SQA given in wf_params
               2) use the force theorem to find energies for all given SQAs
        SQA = x: theta = pi/2, phi = 0
        SQA = y: theta = pi/2, phi = pi/2
        SQA = z: theta = 0,    phi = 0
        """
        if self.ctx.wf_dict['force_th']:
            #only a reference for force theorem calculations will be converged
            self.ctx.inpgen_soc = {'xyz' : self.ctx.wf_dict.get('sqa_ref')}
        else:
            #all given SQAs will be converged
            sqa_theta = self.ctx.wf_dict.get('sqas_theta').split()
            sqa_phi = self.ctx.wf_dict.get('sqas_phi').split()
            self.ctx.inpgen_soc = {}
            for i in range(len(sqa_theta)):
                self.ctx.inpgen_soc['theta_{}_phi_{}'.format(sqa_theta[i], sqa_phi[i])] = [sqa_theta[i], sqa_phi[i]]
        return self.ctx.wf_dict['force_th']

    def converge_scf(self):
        """
        Converge charge density with or without SOC.
        Depending on a branch of MAE calculation, submit a single Fleur calculation to obtain
        a reference for further force theorem calculations or
        submit a set of Fleur calculations to converge charge density for all given SQAs.
        """
        inputs = {}
        for key, socs in six.iteritems(self.ctx.inpgen_soc):
            inputs[key] = self.get_inputs_scf()
            inputs[key]['calc_parameters']['soc'] = {'theta' : socs[0], 'phi' : socs[1]}
            if (key == 'xyz') and not (self.ctx.wf_dict.get('use_soc_ref')):
                inputs[key]['wf_parameters']['inpxml_changes'].append((u'set_inpchanges', {u'change_dict' : {u'l_soc' : False}}))
            inputs[key]['wf_parameters'] = Dict(dict=inputs[key]['wf_parameters'])
            inputs[key]['calc_parameters'] = Dict(dict=inputs[key]['calc_parameters'])
            inputs[key]['options'] = Dict(dict=inputs[key]['options'])
            res = self.submit(fleur_scf_wc, **inputs[key])
            self.to_context(**{key:res})
    
    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = {}

        # Retrieve scf wf parameters and options form inputs
        #Note that MAE wf parameters contain more information than needed for scf
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

        #Initialize codes
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur
        #Initialize the strucutre
        inputs['structure'] = self.inputs.structure

        return inputs

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')
        try:
            fleurin = self.ctx['xyz'].outputs.fleurinp
        except AttributeError:
            error = 'A force theorem calculation did not find fleur input generated be the reference claculation.'
            self.control_end_wc(error)
            return self.ERROR_REFERENCE_CALCULATION_FAILED

        #copy default changes
        fchanges = self.ctx.wf_dict.get('inpxml_changes', [])
        #add forceTheorem tag into inp.xml
        fchanges.extend([(u'create_tag', (u'/fleurInput', u'forceTheorem')), (u'create_tag', (u'/fleurInput/forceTheorem', u'MAE')), (u'xml_set_attribv_occ', (u'/fleurInput/forceTheorem/MAE', u'theta', self.ctx.wf_dict.get('sqas_theta'))), (u'xml_set_attribv_occ', (u'/fleurInput/forceTheorem/MAE', u'phi', self.ctx.wf_dict.get('sqas_phi'))), (u'set_inpchanges', {u'change_dict' : {u'itmax' : 1}})])

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

    def mae_force(self):
        """
        Calculate energy of a system for given SQAs
        using the force theorem. Converged reference is stored in self.ctx['xyz'].
        """
        calc = self.ctx['xyz']
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
        settings = Dict(dict={'remove_from_remotecopy_list': ['broyd*']})
    
        #Retrieve remote folder of the reference calculation
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.type == u'calculation.job.fleur.fleur.FleurCalculation.':
                try:
                    remote_old = i.outputs.remote_folder
                except AttributeError:
                    message = ('Found no remote folder of the referece scf calculation.')
                    self.ctx.warnings.append(message)
                    #TODO error handle
                    #self.ctx.successful = False
                    remote_old = None
        
        label = 'Force_theorem_calculation'
        description = 'This is a force theorem calculation for all SQA'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code, remote_old, fleurin, options, label, description, settings, serial=self.ctx.wf_dict['serial'])
        future = self.submit(inputs_builder)
        return ToContext(forr=future)

    def get_res_force(self):
        t_energydict = []
        mae_thetas = []
        mae_phis = []
        htr2eV = 27.21138602
        #at this point self.ctx.successful == True if the reference calculation is OK
        #the force theorem calculation is checked inside if clause
        if self.ctx.successful:
            try:
                calculation = self.ctx.forr
                calc_state = calculation.get_state()
                if calc_state != CalcJobState.FINISHED or calculation.exit_status != 0:
                    self.ctx.successful = False
                    message = ('ERROR: Force theorem Fleur calculation failed somehow it is '
                            'in state {} with exit status {}'.format(calc_state, calculation.exit_status))
                    self.ctx.errors.append(message)
            except AttributeError:
                self.ctx.successful = False
                message = 'ERROR: Something went wrong I do not have a force theorem Fleur calculation'
                self.ctx.errors.append(message)

            if self.ctx.successful:
                try:
                    t_energydict = calculation.outputs.output_parameters.dict.mae_force_evSum
                    mae_thetas = calculation.outputs.output_parameters.dict.mae_force_theta
                    mae_phis = calculation.outputs.output_parameters.dict.mae_force_phi
                    e_u = calculation.outputs.output_parameters.dict.energy_units
                    
                    #Find a minimal value of MAE and count it as 0
                    labelmin = 0
                    for labels in range(1, len(t_energydict)):
                        if t_energydict[labels] < t_energydict[labelmin]:
                            labelmin = labels
                    minenergy = t_energydict[labelmin]

                    for labels in range(len(t_energydict)):
                        t_energydict[labels] = t_energydict[labels] - minenergy
                        if e_u == 'Htr' or 'htr':
                            t_energydict[labels] = t_energydict[labels] * htr2eV
            
                except AttributeError:
                    self.ctx.successful = False
                    message = ('Did not manage to read evSum, thetas or phis after FT calculation.')
                    self.ctx.errors.append(message)
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'is_it_force_theorem' : True,
               'maes' : t_energydict,
               'theta' : mae_thetas,
               'phi' : mae_phis,
               'mae_units' : 'eV',
               'successful' : self.ctx.successful,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors}
        
        self.out('out', Dict(dict=out))

    def get_results_converge(self):
        """
        Retrieve results of converge calculations
        """
        distancedict ={}
        t_energydict = {}
        outnodedict = {}
        htr2eV = 27.21138602
        
        for label, cont in six.iteritems(self.ctx.inpgen_soc):
            calc = self.ctx[label]
            try:
                outnodedict[label] = calc.get_outputs_dict()['output_scf_wc_para']
            except KeyError:
                message = ('One SCF workflow failed, no scf output node: {}. I skip this one.'.format(label))
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue
            
            outpara = calc.get_outputs_dict()['output_scf_wc_para'].get_dict()
            
            if not outpara.get('successful', False):
                #TODO: maybe do something else here
                # (exclude point and write a warning or so, or error treatment)
                # bzw implement and scf_handler,
                #TODO also if not perfect converged, results might be good
                message = ('One SCF workflow was not successful: {}'.format(label))
                self.ctx.warnings.append(message)
                self.ctx.successful = False
            
            t_e = outpara.get('total_energy', 'failed')
            if not (type(t_e) is float):
                self.ctx.successful = False
                message = ('Did not manage to extract float total energy from one SCF worflow: {}'.format(label))
                self.ctx.warnings.append(message)
                continue
            e_u = outpara.get('total_energy_units', 'Htr')
            if e_u == 'Htr' or 'htr':
                t_e = t_e * htr2eV
            t_energydict[label] = t_e
        
        if len(t_energydict):
            #Find a minimal value of MAE and count it as 0
            labelmin = list(t_energydict.keys())[0]
            for labels in t_energydict.keys():
                try:
                    if t_energydict[labels] < t_energydict[labelmin]:
                        labelmin = labels
                except KeyError:
                    pass
            minenergy = t_energydict[labelmin]

            for key in t_energydict.keys():
                t_energydict[key] = t_energydict[key] - minenergy
        
        #Make sure that meas are in right order that correspont to the order of thetas and phis
        maes_ordered_list = []
        theta_ordered_list = []
        phi_ordered_list = []
        failed_theta = []
        failed_phi = []
        sqa_theta = self.ctx.wf_dict.get('sqas_theta').split()
        sqa_phi = self.ctx.wf_dict.get('sqas_phi').split()
        for i in range(len(sqa_theta)):
            if 'theta_{}_phi_{}'.format(sqa_theta[i], sqa_phi[i]) in t_energydict:
                maes_ordered_list.append(t_energydict['theta_{}_phi_{}'.format(sqa_theta[i], sqa_phi[i])])
                theta_ordered_list.append(sqa_theta[i])
                phi_ordered_list.append(sqa_phi[i])
            else:
                failed_theta.append(sqa_theta[i])
                failed_phi.append(sqa_phi[i])
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'is_it_force_theorem' : False,
               'maes' : maes_ordered_list,
               'theta' : theta_ordered_list,
               'phi' : phi_ordered_list,
               'failed_theta' : failed_theta,
               'failed_phi' : failed_phi,
               'mae_units' : 'eV',
               'successful' : self.ctx.successful,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors}
   
        if self.ctx.successful:
            self.report('Done, Magnetic Anisotropy Energy calculation using convergence complete')
        else:
            self.report('Done, but something went wrong.... Properly some individual calculation failed or a scf-cylcle did not reach the desired distance.')

        # create link to workchain node
        self.out('out', Dict(dict=out))

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg) # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()
        
        return

'''
@wf
def create_mae_result_node(**kwargs):
    """
    This is a pseudo wf, to create the rigth graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_eos_wc_para'] = outpara.clone()
    # copy, because we rather produce the same node twice
    # then have a circle in the database for now...
    outputdict = outpara.get_dict()
    structure = load_node(outputdict.get('initial_structure'))
    #gs_scaling = outputdict.get('scaling_gs', 0)
    #if gs_scaling:
    #    gs_structure = rescale(structure, Float(gs_scaling))
    #    outdict['gs_structure'] = gs_structure

    return outdict
'''
