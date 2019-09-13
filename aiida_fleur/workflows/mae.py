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
    In this module you find the workflow 'FleurMaeWorkChain' for the calculation of
    Magnetic Anisotropy Energy via the force theorem.
"""

from __future__ import absolute_import
import copy

import six
from six.moves import range, map
from lxml.etree import XMLSyntaxError

from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node, CalcJobNode
from aiida.orm import StructureData, RemoteData, Dict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

# pylint: disable=invalid-name
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name

class FleurMaeWorkChain(WorkChain):
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
        'sqa_ref': [0.7, 0.7],
        'use_soc_ref': False,
        'input_converged' : False,
        'fleur_runmax': 10,
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
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
        super(FleurMaeWorkChain, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False)
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=Dict, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("remote", valid_type=RemoteData, required=False)
        spec.input("fleurinp", valid_type=FleurInpData, required=False)
        spec.input("options", valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            if_(cls.scf_needed)(
                cls.converge_scf,
                cls.force_after_scf,
            ).else_(
                cls.force_wo_scf,
            ),
            cls.get_results,
            cls.return_results
        )

        spec.output('out', valid_type=Dict)

        #exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_RESOURCES',
                       message="Invalid input, please check input configuration.")
        spec.exit_code(231, 'ERROR_INVALID_CODE_PROVIDED',
                       message="Invalid code node specified, check inpgen and fleur code nodes.")
        spec.exit_code(232, 'ERROR_CHANGING_FLEURINPUT_FAILED',
                       message="Input file modification failed.")
        spec.exit_code(233, 'ERROR_INVALID_INPUT_FILE',
                       message="Input file is corrupted after user's modifications.")
        spec.exit_code(334, 'ERROR_REFERENCE_CALCULATION_FAILED',
                       message="Reference calculation failed.")
        spec.exit_code(335, 'ERROR_REFERENCE_CALCULATION_NOREMOTE',
                       message="Found no reference calculation remote repository.")
        spec.exit_code(336, 'ERROR_FORCE_THEOREM_FAILED',
                       message="Force theorem calculation failed.")

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Magnetic Anisotropy Energy calculation workflow version {}\n'
                    ''.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.t_energydict = []
        self.ctx.mae_thetas = []
        self.ctx.mae_phis = []

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = copy.deepcopy(self._wf_default)
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

        # Check if sqas_theta and sqas_phi have the same length
        if len(self.ctx.wf_dict.get('sqas_theta')) != len(self.ctx.wf_dict.get('sqas_phi')):
            error = ("Number of sqas_theta has to be equal to the nmber of sqas_phi")
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

        if wf_dict['input_converged']:
            if not 'remote' in self.inputs:
                error = ("Remote calculation was not specified. However, 'input_converged was set"
                         " to True.")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_RESOURCES

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

    def scf_needed(self):
        """
        This function handles setting of required parameters
        for force theorem calculation depending on if scf is needed
        or not.
        """
        self.ctx.scf_needed = not self.ctx.wf_dict['input_converged']
        return self.ctx.scf_needed

    def converge_scf(self):
        """
        Converge charge density with or without SOC.
        Submit a single Fleur calculation to obtain
        a reference for further force theorem calculations.
        """
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        self.to_context(reference=res)

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = self.inputs
        input_scf = {}

        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)

        input_scf['wf_parameters'] = scf_wf_param
        input_scf['wf_parameters']['mode'] = 'density'

        if not self.ctx.wf_dict.get('use_soc_ref'):
            input_scf['wf_parameters']['inpxml_changes'].append(
                ('set_inpchanges', {'change_dict': {'l_soc': False}}))

        input_scf['wf_parameters'] = Dict(dict=input_scf['wf_parameters'])

        input_scf['options'] = self.ctx.options
        input_scf['options'] = Dict(dict=input_scf['options'])

        input_scf['fleur'] = self.inputs.fleur

        if 'fluerinp' in inputs:
            input_scf['fleurinp'] = inputs.fleurinp
            if 'remote' in inputs:
                input_scf['remote_data'] = inputs.remote
        elif 'remote' in inputs:
            input_scf['remote_data'] = inputs.remote
        elif 'structure' in inputs:
            input_scf['structure'] = inputs.structure
            input_scf['inpgen'] = inputs.inpgen
            if 'calc_parameters' in inputs:
                input_scf['calc_parameters'] = inputs.calc_parameters.get_dict()
            else:
                input_scf['calc_parameters'] = {}
            socs = self.ctx.wf_dict.get('sqa_ref')
            input_scf['calc_parameters']['soc'] = {'theta': socs[0], 'phi': socs[1]}
            input_scf['calc_parameters'] = Dict(dict=input_scf['calc_parameters'])
        return input_scf

    def change_fleurinp(self):
        """
        This routine sets somethings in the fleurinp file before running a fleur
        calculation.
        """
        if self.ctx.scf_needed:
            try:
                fleurin = self.ctx.reference.outputs.fleurinp
            except NotExistent:
                error = 'Fleurinp generated in the reference claculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED
        else:
            if 'fleurinp' in self.inputs:
                fleurin = self.inputs.fleurinp
            else:
                # In this case only remote is given
                # fleurinp data has to be generated from the remote inp.xml file
                remote_node = self.inputs.remote
                for link in remote_node.get_incoming().all():
                    if isinstance(link.node, CalcJobNode):
                        parent_calc_node = link.node
                retrieved_node = parent_calc_node.get_outgoing().get_node_by_label('retrieved')
                try:
                    fleurin = FleurInpData(files=['inp.xml', 'relax.xml'], node=retrieved_node)
                except ValueError:
                    fleurin = FleurInpData(files=['inp.xml'], node=retrieved_node)

        # copy default changes
        fchanges = self.ctx.wf_dict.get('inpxml_changes', [])

        # add forceTheorem tag into inp.xml
        fchanges.extend([('create_tag',
                          {'xpath': '/fleurInput',
                           'newelement': 'forceTheorem'
                          }),
                         ('create_tag',
                          {'xpath': '/fleurInput/forceTheorem',
                           'newelement': 'MAE'
                          }),
                         ('xml_set_attribv_occ',
                          {'xpathn': '/fleurInput/forceTheorem/MAE',
                           'attributename': 'theta',
                           'attribv': ' '.join(map(str, self.ctx.wf_dict.get('sqas_theta')))
                          }),
                         ('xml_set_attribv_occ',
                          {'xpathn': '/fleurInput/forceTheorem/MAE',
                           'attributename': 'phi',
                           'attribv': ' '.join(map(str, self.ctx.wf_dict.get('sqas_phi')))
                          }),
                         ('set_inpchanges', {'change_dict': {'itmax': 1}})
                        ])

        if fchanges:  # change inp.xml file
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
                             "please check/test your input. I abort..."
                             "".format(method))
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

                else:  # apply change
                    method(**para)

            # validate?
            apply_c = True
            try:
                fleurmode.show(display=False, validate=True)
            except XMLSyntaxError:
                error = ('ERROR: input, user wanted inp.xml changes did not validate')
                # fleurmode.show(display=True)#, validate=True)
                self.report(error)
                apply_c = False
                return self.exit_codes.ERROR_INVALID_INPUT_FILE

            # apply
            if apply_c:
                out = fleurmode.freeze()
                self.ctx.fleurinp = out
            return
        else:  # otherwise do not change the inp.xml
            self.ctx.fleurinp = fleurin
            return

    def force_after_scf(self):
        """
        Calculate energy of a system for given SQAs
        using the force theorem. Converged reference is stored in self.ctx['xyz'].
        """
        calc = self.ctx.reference

        if not calc.is_finished_ok:
            message = ('The reference SCF calculation was not successful.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        try:
            outpara_node = calc.outputs.output_scf_wc_para
        except NotExistent:
            message = ('The reference SCF calculation failed, no scf output node.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        outpara = outpara_node.get_dict()

        t_e = outpara.get('total_energy', 'failed')
        if not isinstance(t_e, float):
            message = ('Did not manage to extract float total energy from the reference '
                       'SCF calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        self.report('INFO: run Force theorem calculations')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp

        # Do not copy broyd* files from the parent
        settings = {'remove_from_remotecopy_list': ['broyd*']}

        #Retrieve remote folder of the reference calculation
        pk_last = 0
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.node_type == u'process.workflow.workchain.WorkChainNode.':
                if i.process_class is FleurBaseWorkChain:
                    if pk_last < i.pk:
                        pk_last = i.pk
        try:
            remote = load_node(pk_last).outputs.remote_folder
        except AttributeError:
            message = ('Found no remote folder of the reference scf calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_NOREMOTE

        label = 'Force_theorem_calculation'
        description = 'This is a force theorem calculation for all SQA'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code, remote,
                                          fleurin, options, label, description, settings,
                                          serial=self.ctx.wf_dict['serial'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(f_t=future)

    def force_wo_scf(self):
        """
        Submit FLEUR force theorem calculation using input remote
        """
        self.report('INFO: run Force theorem calculations')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp

        #Do not copy broyd* files from the parent
        settings = {'remove_from_remotecopy_list': ['broyd*']}

        #Retrieve remote folder from the inputs
        remote = self.inputs.remote

        label = 'Force_theorem_calculation'
        description = 'This is a force theorem calculation for all SQA'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code, remote,
                                          fleurin, options, label, description, settings,
                                          serial=self.ctx.wf_dict['serial'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(f_t=future)

    def get_results(self):
        """
        Generates results of the workchain.
        """
        t_energydict = []
        mae_thetas = []
        mae_phis = []
        htr_to_ev = 27.21138602

        try:
            calculation = self.ctx.f_t
            if not calculation.is_finished_ok:
                message = ('ERROR: Force theorem Fleur calculation failed somehow it has '
                           'exit status {}'.format(calculation.exit_status))
                self.control_end_wc(message)
                return self.exit_codes.ERROR_FORCE_THEOREM_FAILED
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have a force theorem Fleur calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        try:
            out_dict = calculation.outputs.output_parameters.dict
            t_energydict = out_dict.mae_force_evSum
            mae_thetas = out_dict.mae_force_theta
            mae_phis = out_dict.mae_force_phi
            e_u = out_dict.energy_units

            minenergy = min(t_energydict)

            if e_u == 'Htr' or 'htr':
                t_energydict = [htr_to_ev * (x-minenergy) for x in t_energydict]
            else:
                t_energydict = [(x-minenergy) for x in t_energydict]

        except AttributeError:
            message = ('Did not manage to read evSum or energy units after FT calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_FORCE_THEOREM_FAILED

        self.ctx.t_energydict = t_energydict
        self.ctx.mae_thetas = mae_thetas
        self.ctx.mae_phis = mae_phis

    def return_results(self):
        """
        This function outputs results of the wc
        """

        out = {'workflow_name': self.__class__.__name__,
               'workflow_version': self._workflowversion,
               'initial_structure': self.inputs.structure.uuid,
               'is_it_force_theorem': True,
               'maes': self.ctx.t_energydict,
               'theta': self.ctx.mae_thetas,
               'phi': self.ctx.mae_phis,
               'mae_units': 'eV',
               'info': self.ctx.info,
               'warnings': self.ctx.warnings,
               'errors': self.ctx.errors}

        out = save_output_node(Dict(dict=out))
        self.out('out', out)

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()

@cf
def save_output_node(out):
    """
    This calcfunction saves the out dict in the db
    """
    out_wc = out.clone()
    return out_wc
