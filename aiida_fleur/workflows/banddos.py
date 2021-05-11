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
This is the worklfow 'band' for the Fleur code, which calculates a
electron bandstructure.
"""
# TODO alow certain kpoint path, or kpoint node, so far auto
import copy
from lxml import etree

from aiida.orm import Code, Dict, RemoteData
from aiida.orm import load_node, CalcJobNode, FolderData
from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent
from aiida.common import AttributeDict

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data


class FleurBandDosWorkChain(WorkChain):
    '''
    This workflow calculated a bandstructure from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior
    '''
    # wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    # defaults : tria = True, nkpts = 800, sigma=0.005, emin= , emax =

    _workflowversion = '0.4.0'

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }
    _default_wf_para = {
        'kpath': 'auto',
        'klistname': 'path-2',
        'mode': 'band',
        'nkpts': 800,
        'sigma': 0.005,
        'emin': -0.50,
        'emax': 0.90,
        'add_comp_para': {
            'serial': False,
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'inpxml_changes': [],
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           },
                           namespace='scf')
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('options', valid_type=Dict, required=False)

        spec.outline(cls.start,
                     if_(cls.scf_needed)(
                         cls.converge_scf,
                         cls.banddos_after_scf,
                     ).else_(
                         cls.banddos_wo_scf,
                     ), cls.return_results)

        spec.output('output_banddos_wc_para', valid_type=Dict)
        spec.output('last_calc_retrieved', valid_type=FolderData)

        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(337, 'ERROR_SCF_CALCULATION_FAILED', message='SCF calculation failed.')
        spec.exit_code(335, 'ERROR_SCF_CALCULATION_NOREMOTE', message='Found no SCF calculation remote repository.')

    def start(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        self.report('started bandsdos workflow version {}'.format(self._workflowversion))
        #print("Workchain node identifiers: ")#'{}'
        #"".format(ProcessRegistry().current_calc_node))

        self.ctx.scf_needed = False
        self.ctx.banddos_calc = None
        self.ctx.successful = False
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        inputs = self.inputs

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in inputs:
            wf_dict = inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        defaultoptions = self._default_options
        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'scf' in inputs:
            self.ctx.scf_needed = True
            if 'remote' in inputs:
                error = 'ERROR: you gave SCF input + remote for the BandDOS calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in inputs:
                error = 'ERROR: you gave SCF input + fleurinp for the BandDOS calculation'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote' not in inputs:
            error = 'ERROR: you gave neither SCF input nor remote'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            self.ctx.scf_needed = False

    def change_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.ctx.wf_dict

        if self.ctx.scf_needed:
            try:
                fleurin = self.ctx.scf.outputs.fleurinp
            except NotExistent:
                error = 'Fleurinp generated in the SCF calculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_SCF_CALCULATION_FAILED
        else:
            if 'fleurinp' not in self.inputs:
                fleurin = get_fleurinp_from_remote_data(self.inputs.remote)
            else:
                fleurin = self.inputs.fleurinp

        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        fleurmode = FleurinpModifier(fleurin)

        fleurmode.add_task_list(wf_dict.get('inpxml_changes', []))

        sigma = wf_dict.get('sigma', 0.005)
        emin = wf_dict.get('emin', -0.30)
        emax = wf_dict.get('emax', 0.80)
        nkpts = wf_dict.get('nkpts', 500)

        if fleurin.inp_version < '0.32':
            if wf_dict.get('mode') == 'dos':
                fleurmode.set_inpchanges({'ndir': -1})

            if wf_dict.get('kpath') != 'auto':
                fleurmode.set_kpath(wf_dict.get('kpath'), nkpts)
        else:
            fleurmode.switch_kpointset(wf_dict.get('klistname', 'path-2'))

        if wf_dict.get('mode') == 'dos':
            change_dict = {'dos': True, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}
        else:
            change_dict = {'band': True, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}
        fleurmode.set_inpchanges(change_dict)

        try:
            fleurmode.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_FILE

        fleurinp_new = fleurmode.freeze()
        self.ctx.fleurinp_banddos = fleurinp_new

    def scf_needed(self):
        """
        Returns True if SCF WC is needed.
        """
        return self.ctx.scf_needed

    def converge_scf(self):
        """
        Converge charge density.
        """
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(scf=res)

    def banddos_after_scf(self):
        """
        This method submits the BandDOS calculation after the initial SCF calculation
        """
        calc = self.ctx.scf

        if not calc.is_finished_ok:
            message = ('The SCF calculation was not successful.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        try:
            outpara_node = calc.outputs.output_scf_wc_para
        except NotExistent:
            message = ('The SCF calculation failed, no scf output node.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        outpara = outpara_node.get_dict()

        if 'total_energy' not in outpara:
            message = ('Did not manage to extract float total energy from the SCF calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        self.report('INFO: run BandDOS calculation')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp_banddos

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder of the reference calculation
        pk_last = 0
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.node_type == 'process.workflow.workchain.WorkChainNode.':
                if i.process_class is FleurBaseWorkChain:
                    if pk_last < i.pk:
                        pk_last = i.pk
        try:
            remote = load_node(pk_last).outputs.remote_folder
        except AttributeError:
            message = ('Found no remote folder of the reference scf calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_NOREMOTE

        label = 'bansddos_calculation'
        description = 'Bandstructure or DOS is calculated for the given structure'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code,
                                          remote,
                                          fleurin,
                                          options,
                                          label,
                                          description,
                                          settings,
                                          add_comp_para=self.ctx.wf_dict['add_comp_para'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(banddos_calc=future)

    def banddos_wo_scf(self):
        """
        This method submits the BandDOS calculation without a previous SCF calculation
        """
        self.report('INFO: run BandDOS calculation')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp_banddos

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder from the inputs
        remote = self.inputs.remote

        label = 'bansddos_calculation'
        description = 'Bandstructure or DOS is calculated for the given structure'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code,
                                          remote,
                                          fleurin,
                                          options,
                                          label,
                                          description,
                                          settings,
                                          add_comp_para=self.ctx.wf_dict['add_comp_para'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(banddos_calc=future)

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        return input_scf

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        self.report('BandDOS workflow Done')
        self.report(f'A bandstructure was calculated and is found under pk={self.ctx.banddos_calc.pk}, '
                    f'calculation {self.ctx.banddos_calc}')

        from aiida_fleur.tools.common_fleur_wf import find_last_submitted_calcjob
        if self.ctx.banddos_calc:
            try:
                last_calc_uuid = find_last_submitted_calcjob(self.ctx.banddos_calc)
            except NotExistent:
                last_calc_uuid = None
        else:
            last_calc_uuid = None

        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.banddos_calc.outputs.output_parameters
            retrieved = self.ctx.banddos_calc.outputs.retrieved
            last_calc_out_dict = last_calc_out.get_dict()
        except (NotExistent, AttributeError):
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None

        #check if band file exists: if not succesful = False
        #TODO be careful with general bands.X
        bandfiles = ['bands.1', 'bands.2', 'banddos.hdf']

        bandfile_res = []
        if retrieved:
            bandfile_res = retrieved.list_object_names()

        for name in bandfiles:
            if name in bandfile_res:
                self.ctx.successful = True
        if not self.ctx.successful:
            self.report('!NO bandstructure file was found, something went wrong!')

        # # get efermi from last calculation
        scf_results = None
        efermi_scf = 0
        bandgap_scf = 0
        if 'remote' in self.inputs:
            for w in self.inputs.remote.get_incoming().all():
                if isinstance(w.node, CalcJobNode):
                    scf_results = load_node(w.node.pk).res
                    efermi_scf = scf_results.fermi_energy
                    bandgap_scf = scf_results.bandgap

        efermi_band = last_calc_out_dict.get('fermi_energy', None)
        bandgap_band = last_calc_out_dict.get('bandgap', None)

        diff_efermi = None
        if efermi_band is not None:
            diff_efermi = efermi_scf - efermi_band

        diff_bandgap = None
        if bandgap_band is not None:
            diff_bandgap = bandgap_scf - bandgap_band

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['Warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['last_calc_uuid'] = last_calc_uuid
        outputnode_dict['last_calc_pk'] = self.ctx.banddos_calc.pk
        outputnode_dict['fermi_energy_band'] = efermi_band
        outputnode_dict['bandgap_band'] = bandgap_band
        outputnode_dict['fermi_energy_scf'] = efermi_scf
        outputnode_dict['bandgap_scf'] = bandgap_scf
        outputnode_dict['diff_efermi'] = diff_efermi
        outputnode_dict['diff_bandgap'] = diff_bandgap
        outputnode_dict['bandgap_units'] = 'eV'
        outputnode_dict['fermi_energy_units'] = 'Htr'

        outputnode_t = Dict(dict=outputnode_dict)
        if last_calc_out:
            outdict = create_band_result_node(outpara=outputnode_t,
                                              last_calc_out=last_calc_out,
                                              last_calc_retrieved=retrieved)
        else:
            outdict = create_band_result_node(outpara=outputnode_t)

        if retrieved:
            outdict['last_calc_retrieved'] = retrieved

        #TODO parse Bandstructure
        for link_name, node in outdict.items():
            self.out(link_name, node)

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_band_result_node(**kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in kwargs.items():
        if key == 'outpara':  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_banddos_wc_para'
    outputnode.description = ('Contains band calculation results')

    outdict['output_banddos_wc_para'] = outputnode

    return outdict
