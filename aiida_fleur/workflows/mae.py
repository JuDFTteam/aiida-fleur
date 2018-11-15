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
    In this module you find the workflow 'fleur_mae_wc' for the calculation of
    Magnetic Anisotropy Energy.
"""

from aiida.work.workchain import WorkChain, ToContext, if_
from aiida.work.launch import submit
from aiida.orm.data.base import Float
from aiida.work.workfunctions import workfunction as wf
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida.orm import Code, DataFactory, load_node
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida.common.datastructures import calc_states

StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')

class fleur_mae_wc(WorkChain):
    """
        This workflow calculates the Magnetic Anisotropy Energy of a thin structure.
    """
    
    _workflowversion = "0.1.0a"

    _default_options = {
                        'resources' : {"num_machines": 1, "num_mpiprocs_per_machine" : 1},
                        'max_wallclock_seconds' : 6*60*60,
                        'queue_name' : '',
                        'custom_scheduler_commands' : '',
                        'import_sys_environment' : False,
                        'environment_variables' : {}}
    
    _wf_default = {
                   'sqa_ref' : 'x',                  # Spin Quantization Axis acting as a reference for force theorem calculations
                   'force_th' : True,               #Use the force theorem (True) or converge
                   'fleur_runmax': 10,              # Maximum number of fleur jobs/starts (defauld 30 iterations per start)
                   'density_criterion' : 0.00005,  # Stop if charge denisty is converged below this value
                   'serial' : False,                # execute fleur with mpi or without
                   'itmax_per_run' : 30,
    #do not allow an user to change inp-file manually
                   'inpxml_changes' : [],      # (expert) List of further changes applied after the inpgen run
                   }                                 # tuples (function_name, [parameters]), the ones from fleurinpmodifier
                                                    # example: ('set_nkpts' , {'nkpts': 500,'gamma': False}) ! no checks made, there know what you are doing
    #Specify the list of scf wf paramters to be trasfered into scf wf
    _scf_keys = ['fleur_runmax', 'density_criterion', 'serial', 'itmax_per_run', 'inpxml_changes']

    ERROR_INVALID_INPUT_RESOURCES = 1
    ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED = 2
    ERROR_INVALID_CODE_PROVIDED = 3
    ERROR_INPGEN_CALCULATION_FAILED = 4
    ERROR_CHANGING_FLEURINPUT_FAILED = 5
    ERROR_CALCULATION_INVALID_INPUT_FILE = 6
    ERROR_FLEUR_CALCULATION_FALIED = 7
    ERROR_CONVERGENCE_NOT_ARCHIVED = 8
    ERROR_WRONG_SQA_PROVIDED = 9

    @classmethod
    def define(cls, spec):
        super(fleur_mae_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False, default=ParameterData(dict=cls._wf_default))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=ParameterData, required=False, default=ParameterData(dict=cls._default_options))
        spec.input("settings", valid_type=ParameterData, required=False)
                                                                              
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

        spec.output('MAE_x', valid_type=Float)
        spec.output('MAE_y', valid_type=Float)
        spec.output('MAE_z', valid_type=Float)

    def start(self):
        """
        Retrieve and initialize paramters of the WorkFlow
        """
        self.report('INFO: started Magnetic Anisotropy Energy calculation workflow version {}\n'
                    ''.format(self._workflowversion))
                    
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        #Retrieve WorkFlow parameters,
        #initialize the directory using defaults if no wf paramters are given by user
        wf_default = self._wf_default
        a = ParameterData(dict = wf_default)
        
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default
        
        #extend options given by user using defaults
        for key, val in wf_default.iteritems():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        if self.ctx.wf_dict['sqa_ref'] == 'z':
            self.ctx.theta = 0.0
            self.ctx.phi = 0.0
        elif self.ctx.wf_dict['sqa_ref'] == 'x':
            self.ctx.theta = 1.57079
            self.ctx.phi = 0.0
        elif self.ctx.wf_dict['sqa_ref'] == 'y':
            self.ctx.theta = 1.57079
            self.ctx.phi = 1.57079
        else:
            error = ("sqa_ref has to be equal to x, y or z.")
            self.control_end_wc(error)
            return self.ERROR_WRONG_SQA_PROVIDED
        
        #Retrieve calculation options,
        #initialize the directory using defaults if no options are given by user
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

    def validate_input(self):
        """
        Choose the branch of MAE calculation: straightforward scf (return False)
        or force theorem (return True)
        Create the list of SQAs. If it is a force theorem calculation,
        symmetry has to be broken using SQA not patallel to high symmetry direction.
        The SQA will be changed before FLEUR execution.
        In case of converge, list of SQA corresponding to x y and z directions.
        """
        if self.ctx.wf_dict['force_th']:
            self.ctx.inpgen_soc = {'xyz' : ['0.1', '0.1']}
        else:
            self.ctx.inpgen_soc = {'z' : ['0.0', '0.0'], 'x' : ['1.57079', '0.0'], 'y' : ['1.57079', '1.57079']}
        return self.ctx.wf_dict['force_th']

    def converge_scf(self):
        """
        Converge magnetic structure with SOC to get
        a reference for force theorem calculations
        """
        self.ctx.labels = []
        inputs = {}
        for key, socs in self.ctx.inpgen_soc.iteritems():
            inputs[key] = self.get_inputs_scf()
            inputs[key]['calc_parameters']['soc'] = {'theta' : socs[0], 'phi' : socs[1]}
            if key == 'xyz':
                try:
                    inputs[key]['wf_parameters']['inpxml_changes'].append((u'set_inpchanges', {u'change_dict' : {u'alpha' : 0.015}}))
                except KeyError:
                    inputs[key]['wf_parameters']['inpxml_changes'] = [(u'set_inpchanges', {u'change_dict' : {u'alpha' : 0.015}})]
            else:
            #TODO in case of converge calculation in appends 3 times
                inputs[key]['wf_parameters']['inpxml_changes'].append((u'set_inpchanges', {u'change_dict' : {u'alpha' : 0.015}}))
            inputs[key]['wf_parameters'] = ParameterData(dict=inputs[key]['wf_parameters'])
            inputs[key]['calc_parameters'] = ParameterData(dict=inputs[key]['calc_parameters'])
            inputs[key]['options'] = ParameterData(dict=inputs[key]['options'])
            print "#############################################"
            print inputs[key]['options'].get_dict()
            print inputs[key]['calc_parameters'].get_dict()
            print inputs[key]['wf_parameters'].get_dict()
            print "#############################################"
            res = self.submit(fleur_scf_wc, **inputs[key])
            self.ctx.labels.append(key)
            self.to_context(**{key:res})
    
    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow: wf_param, options, calculation parameters, codes, struture
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
        inputs['structure'] = self.inputs.structure

        return inputs

    def change_fleurinp(self, SQA_direction):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        self.report('INFO: run change_fleurinp')
        try:
            fleurin = self.ctx['xyz'].out.fleurinp
            print "TOOOK FLEURINP FORM LAST CONVERGE"
        except AttributeError:
            error = 'No fleurinpData found, inpgen failed'
            self.control_end_wc(error)
            return self.ERROR_INPGEN_CALCULATION_FAILED

        if SQA_direction == 'x':
            fchanges = [(u'set_inpchanges', {u'change_dict' : {u'theta' : 1.57079, u'phi' : 0.0, u'itmax' : 1}})]
        elif SQA_direction == 'y':
            fchanges = [(u'set_inpchanges', {u'change_dict' : {u'theta' : 1.57079, u'phi' : 1.57079, u'itmax' : 1}})]
        elif SQA_direction == 'z':
            fchanges = [(u'set_inpchanges', {u'change_dict' : {u'theta' : 0.0, u'phi' : 0.0, u'itmax' : 1}})]

        if fchanges:# change inp.xml file
            fleurmode = FleurinpModifier(fleurin)
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
                    method(**para)

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

    def mae_force(self):
        """
        Calculate energy of a system with given SQA
        using the force theorem
        """
        self.report('INFO: run FORCE THEOREM CALCULATION')

        for SQA_direction in ['x', 'y', 'z']:
            self.change_fleurinp(SQA_direction)
            fleurin = self.ctx.fleurinp

            settings = ParameterData(dict={'remove_from_remotecopy_list': ['broyd*'],
                                           'commandline_options': ["-wtime", "{}".format(self.ctx.options['max_wallclock_seconds'])],
                                           })
        
            a = load_node(self.ctx['xyz'].pk)
            for i in a.called:
                if i.type == u'calculation.job.fleur.fleur.FleurCalculation.':
                    remote_old = i.out.remote_folder
            print '#################'
            print remote_old
            #remote_old=None
            
            label = 'FORCE'
            description = 'This is a force theorem calculation'

            code = self.inputs.fleur
            options = self.ctx.options.copy()

        
            inputs_builder = get_inputs_fleur(code, remote_old, fleurin, options, label, description, settings, serial=False)
            future = submit(inputs_builder)
            key = 'force_{}'.format(SQA_direction)
            self.to_context(**{key:future})

    def get_res_force(self):
        
        print "MAE XXXXX"
        print self.ctx['force_x'].out.output_parameters.dict.energy# - self.ctx['xyz'].get_outputs_dict()['output_scf_wc_para'].get_dict()['total_energy']
        print "MAE YYYYY"
        print self.ctx['force_y'].out.output_parameters.dict.energy# - self.ctx['xyz'].get_outputs_dict()['output_scf_wc_para'].get_dict()['total_energy']
        print "MAE ZZZZZ"
        print self.ctx['force_z'].out.output_parameters.dict.energy# - self.ctx['xyz'].get_outputs_dict()['output_scf_wc_para'].get_dict()['total_energy']
        
        natoms = len(self.inputs.structure.sites)
        t_energydict = {}
        t_energydict['MAE_x'] = self.ctx['force_x'].out.output_parameters.dict.energy
        t_energydict['MAE_y'] = self.ctx['force_y'].out.output_parameters.dict.energy
        t_energydict['MAE_z'] = self.ctx['force_z'].out.output_parameters.dict.energy
        
        labelmin = 'MAE_z'
        for labels in ['MAE_y', 'MAE_x']:
            if t_energydict[labels] < t_energydict[labels]:
                labelmin = labels
        minenergy = t_energydict[labelmin]

        for key, val in t_energydict.iteritems():
            t_energydict[key] = t_energydict[key] - minenergy
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'natoms' : natoms,
               'total_energy': t_energydict,
               'total_energy_units' : self.ctx['force_z'].out.output_parameters.dict.energy_units,
               'calculations' : [],#self.ctx.calcs1,
               'scf_wfs' : [],#self.converge_scf_uuids,
               'successful' : self.ctx.successful,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors}
        
        self.out('MAE_x', Float(out['total_energy']['MAE_x']))
        self.out('MAE_y', Float(out['total_energy']['MAE_y']))
        self.out('MAE_z', Float(out['total_energy']['MAE_z']))

    def get_results_converge(self):
        """
        Retrieve results of converge calculations
        """
        distancedict ={}
        t_energydict = {}
        outnodedict = {}
        natoms = len(self.inputs.structure.sites)
        htr2eV = 27.21138602
        
        for label in self.ctx.labels:
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
                self.ctx.warning.append(message)
                self.ctx.successful = False
            
            t_e = outpara.get('total_energy', float('nan'))
            e_u = outpara.get('total_energy_units', 'eV')
            if e_u == 'Htr' or 'htr':
                t_e = t_e * htr2eV
            dis = outpara.get('distance_charge', float('nan'))
            dis_u = outpara.get('distance_charge_units')
            t_energydict[label] = t_e
            distancedict[label] = dis
        
        labelmin = 'z'
        for labels in ['y', 'x']:
            try:
                if t_energydict[labels] < t_energydict[labels]:
                    labelmin = labels
            except KeyError:
                pass

        minenergy = t_energydict[labelmin]

        for key, val in t_energydict.iteritems():
            t_energydict[key] = t_energydict[key] - minenergy
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'natoms' : natoms,
               'total_energy': t_energydict,
               'total_energy_units' : e_u,
               'calculations' : [],#self.ctx.calcs1,
               'scf_wfs' : [],#self.converge_scf_uuids,
               'distance_charge' : distancedict,
               'distance_charge_units' : dis_u,
               'successful' : self.ctx.successful,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors}
   
        if self.ctx.successful:
            self.report('Done, Magnetic Anisotropy Energy calculation using convergence complete')
        else:
            self.report('Done, but something went wrong.... Properly some individual calculation failed or a scf-cylcle did not reach the desired distance.')

        # output must be aiida Data types.
        #outnode = ParameterData(dict=out)

        # create link to workchain node
        self.out('MAE_x', Float(out['total_energy']['x']))
        self.out('MAE_y', Float(out['total_energy']['y']))
        self.out('MAE_z', Float(out['total_energy']['z']))

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
