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
# TODO alternative parse a structure and run scf
from __future__ import absolute_import
from __future__ import print_function
import os.path
import copy
import six

from aiida.plugins import DataFactory
from aiida.orm import Code, StructureData, Dict, RemoteData
from aiida.orm import load_node, CalcJobNode
from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent
from aiida.common import AttributeDict

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, is_code
from aiida_fleur.data.fleurinp import FleurinpData


class FleurBandDosWorkChain(WorkChain):
    '''
    This workflow calculated a bandstructure from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior
    '''
    # wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    # defaults : tria = True, nkpts = 800, sigma=0.005, emin= , emax =

    _workflowversion = '0.3.5'

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
        'fleur_runmax': 4,
        'kpath': 'auto',
        # 'nkpts' : 800,
        'sigma': 0.005,
        'emin': -0.50,
        'emax': 0.90
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        # spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote', valid_type=RemoteData, required=True)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('options', valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            if_(cls.scf_needed)(
                cls.converge_scf,
                cls.create_new_fleurinp,
                cls.run_fleur,
            ).else_(
                cls.create_new_fleurinp,
                cls.run_fleur,
            ), cls.return_results)

        spec.output('output_banddos_wc_para', valid_type=Dict)

        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')

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

        self.ctx.fleurinp_scf = None
        self.ctx.scf_needed = False
        self.ctx.fleurinp_banddos = None
        self.ctx.last_calc = None
        self.ctx.successful = False
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.calcs = []

        inputs = self.inputs

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in inputs:
            wf_dict = inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict
        # if MPI in code name, execute parallel
        self.ctx.serial = self.ctx.wf_dict.get('serial', False)

        defaultoptions = self._default_options
        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        # set values, or defaults
        self.ctx.max_number_runs = self.ctx.wf_dict.get('fleur_runmax', 4)

        # if 'scf' in self.inputs:
        #     self.ctx.scf_needed = True
        #     if 'remote' in self.inputs.scf:
        #       error = "ERROR: you gave SCF input + remote"
        #       self.control_end_wc(error)
        #       return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        #     if 'structure' and 'fleurinp' in self.inputs.scf:
        #       error = "ERROR: you gave SCF input structure and fleurinp"
        #       self.control_end_wc(error)
        #       return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        #     if 'structure' in self.inputs.scf:
        #       if 'inpgen' not in self.inputs:
        #         error = "ERROR: you gave SCF input structure and not inpgen"
        #         self.control_end_wc(error)
        #         return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        # elif 'remote' not in self.inputs:
        #     error = "ERROR: you gave neither SCF input nor remote"
        #     self.control_end_wc(error)
        #     return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        # else:
        #     self.ctx.scf_needed = False

    def create_new_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.ctx.wf_dict

        if 'fleurinp' not in self.inputs:
            for i in self.inputs.remote.get_incoming():
                if isinstance(i.node, CalcJobNode):
                    self.ctx.fleurinp_scf = load_node(i.node.pk).get_incoming().get_node_by_label('fleurinpdata')
        else:
            self.ctx.fleurinp_scf = self.inputs.fleurinp

        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        fleurmode = FleurinpModifier(self.ctx.fleurinp_scf)

        nkpts = wf_dict.get('nkpts', 500)
        sigma = wf_dict.get('sigma', 0.005)
        emin = wf_dict.get('emin', -0.30)
        emax = wf_dict.get('emax', 0.80)

        if wf_dict.get('mode') == 'dos':
            change_dict = {'dos': True, 'ndir': -1, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}
        else:
            change_dict = {'band': True, 'ndir': 0, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}

        fleurmode.set_inpchanges(change_dict)

        if wf_dict.get('kpath') != 'auto':
            fleurmode.set_kpath(wf_dict.get('kpath'), nkpts)

        # if nkpts:
        # fleurmode.set_nkpts(count=nkpts)
        #fleurinp_new.replace_tag()

        fleurmode.show(validate=True, display=False)  # needed?
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
        # TODO: implement
        return 0

    def run_fleur(self):
        """
        run a FLEUR calculation
        """
        self.report('INFO: run FLEUR')
        # inputs = self.get_inputs_scf()
        fleurin = self.ctx.fleurinp_banddos
        remote = self.inputs.remote
        code = self.inputs.fleur
        options = self.ctx.options.copy()

        label = 'bansddos_calculation'
        description = 'Bandstructure or DOS is calculated for the given structure'

        inputs = get_inputs_fleur(code, remote, fleurin, options, label, description, serial=self.ctx.serial)
        future = self.submit(FleurBaseWorkChain, **inputs)
        self.ctx.calcs.append(future)

        return ToContext(last_calc=future)

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        input_scf.fleurinp = self.ctx.fleurinp_banddos

        return input_scf

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        self.report('Band workflow Done')
        self.report('A bandstructure was calculated for fleurinpdata {} and is found under pk={}, '
                    'calculation {}'.format(self.ctx.fleurinp_scf, self.ctx.last_calc.pk, self.ctx.last_calc))

        from aiida_fleur.tools.common_fleur_wf import find_last_submitted_calcjob
        if self.ctx.last_calc:
            try:
                last_calc_uuid = find_last_submitted_calcjob(self.ctx.last_calc)
            except NotExistent:
                last_calc_uuid = None
        else:
            last_calc_uuid = None

        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.last_calc.outputs.output_parameters
            retrieved = self.ctx.last_calc.outputs.retrieved
            last_calc_out_dict = last_calc_out.get_dict()
        except (NotExistent, AttributeError):
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None

        #check if band file exists: if not succesful = False
        #TODO be careful with general bands.X
        # bandfilename = 'bands.1' # ['bands.1', 'bands.2', ...]

        # bandfile =retrieved.open(bandfilename).name

        # if os.path.isfile(bandfile):
        #     self.ctx.successful = True
        # else:
        #     bandfile = None
        #     self.report('!NO bandstructure file was found, something went wrong!')

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
        outputnode_dict['last_calc_pk'] = self.ctx.last_calc.pk
        outputnode_dict['fermi_energy_band'] = efermi_band
        outputnode_dict['bandgap_band'] = bandgap_band
        outputnode_dict['fermi_energy_scf'] = efermi_scf
        outputnode_dict['bandgap_scf'] = bandgap_scf
        outputnode_dict['diff_efermi'] = diff_efermi
        outputnode_dict['diff_bandgap'] = diff_bandgap
        outputnode_dict['bandgap_units'] = 'eV'
        outputnode_dict['fermi_energy_units'] = 'Htr'
        # outputnode_dict['bandfile']           = bandfile

        outputnode_t = Dict(dict=outputnode_dict)
        if last_calc_out:
            outdict = create_band_result_node(outpara=outputnode_t,
                                              last_calc_out=last_calc_out,
                                              last_calc_retrieved=retrieved)
        else:
            outdict = create_band_result_node(outpara=outputnode_t)

        #TODO parse Bandstructure
        for link_name, node in six.iteritems(outdict):
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
    for key, val in six.iteritems(kwargs):
        if key == 'outpara':  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_banddos_wc_para'
    outputnode.description = ('Contains band calculation results')

    outdict['output_banddos_wc_para'] = outputnode

    return outdict
