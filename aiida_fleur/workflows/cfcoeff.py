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
    In this module you find the workflow 'FleurCFCoeffWorkChain' for calculating
    the 4f crystal field coefficients
"""
from aiida.engine import WorkChain, ToContext
from aiida.engine import calcfunction as cf
from aiida.common import AttributeDict
from aiida.orm import Dict, load_node, Bool
from aiida.common.constants import elements as PeriodicTableElements

from aiida_fleur.tools.StructureData_util import replace_element
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain

from masci_tools.tools.cf_calculation import CFCalculation
import h5py


class FleurCFCoeffWorkChain(WorkChain):
    """
    Workflow for calculating rare-earth crystal field coefficients
    """
    _workflowversion = '0.1.0'

    _wf_default = {
        'element': '',
        'yttrium_analogue': False,
        'replace_all': True,
        'soc_off': True,
        'convert_to_stevens': True,
    }

    _yttrium_default_params = {'element': 'Y', 'lo': '4s 4p', 'lmax': 15, 'lnonsph': 15}

    @classmethod
    def define(cls, spec):
        super(FleurCFCoeffWorkChain, cls).define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace='scf_yttrium_analogue',
                           exclude=('structure', 'fleurinp'),
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           })
        spec.expose_inputs(FleurScfWorkChain,
                           namespace='scf',
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           })
        spec.expose_inputs(FleurOrbControlWorkChain,
                           namespace='orbcontrol',
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           })
        spec.input('wf_parameters', valid_type=Dict, required=False)

        spec.outline(cls.start, cls.validate_input, cls.run_scfcalculations, cls.run_cfcalculation, cls.return_results)

        spec.output('output_cfcoeff_wc_para', valid_type=Dict)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(345, 'ERROR_SCF_FAILED', message='Convergence scf workflow failed.')
        spec.exit_code(451, 'ERROR_ORBCONTROL_FAILED', message='Convergence orbcontrol workflow failed.')
        spec.exit_code(452, 'ERROR_CFCALC_FAILED', message='CF calculation failed.')

    def start(self):
        """
        init context and some parameters
        """
        self.report(f'INFO: started crystal field coefficient workflow version {self._workflowversion}')

        ####### init    #######

        # internal para /control para
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

    def validate_input(self):
        """
        validate input
        """
        extra_keys = []
        for key in self.ctx.wf_dict.keys():
            if key not in self._wf_default.keys():
                extra_keys.append(key)
        if extra_keys:
            error = f'ERROR: input wf_parameters for CFCoeff contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        inputs = self.inputs
        if 'scf' not in inputs and 'orbcontrol' not in inputs:
            error = 'ERROR: Missing input. Provide one of the scf or orbcontrol inputs.'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'scf' in inputs and 'orbcontrol' in inputs:
            error = 'ERROR: Invalid Input. Provide only one of the scf or orbcontrol inputs.'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        element = self.ctx.wf_dict['element']
        atomic_numbers = {data['symbol']: num for num, data in PeriodicTableElements.items()}
        if element not in atomic_numbers:
            error = f'ERROR: Invalid Input. Element not a valid element: {element}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        else:
            if atomic_numbers[element] < 57 and atomic_numbers[element] > 70:
                error = 'ERROR: Invalid Input. CF coefficient workflow only implemented for 4f rare-earths'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if not self.ctx.wf_dict['replace_all']:
            error = 'ERROR: Invalid Input. replace_all False not implemented yet'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def run_scfcalculations(self):

        self.report('INFO: Starting SCF calculations')
        inputs = {}
        calcs = {}
        if self.ctx.wf_dict['yttrium_analogue']:
            self.report('INFO: Creating Yttrium Analogue')
            inputs = self.get_inputs_yttrium_analogue()
            result_yttrium = self.submit(FleurScfWorkChain, **inputs)
            calcs['yttrium_analogue_scf'] = result_yttrium

        if 'scf' in self.inputs:
            inputs = self.get_inputs_scf()
            result_scf = self.submit(FleurScfWorkChain, **inputs)
            calcs['rare_earth_scf'] = result_scf
        elif 'orbcontrol' in self.inputs:
            inputs = self.get_inputs_orbcontrol()
            result_orbcontrol = self.submit(FleurOrbControlWorkChain, **inputs)
            calcs['rare_earth_orbcontrol'] = result_orbcontrol

        return ToContext(**calcs)

    def get_inputs_yttrium_analogue(self):

        inputs = self.inputs
        if 'scf' in inputs:
            input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        elif 'orbcontrol' in self.inputs:
            input_scf = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))
            input_scf = input_scf['scf_no_ldau']

        if 'structure' in input_scf:
            orig_structure = input_scf['structure']
        elif 'fleurinp' in input_scf:
            orig_structure = input_scf['fleurinp'].get_structuredata()

        if 'calc_parameters' in input_scf:
            rare_earth_params = input_scf['calc_parameters'].get_dict()
        else:
            rare_earth_params = {}

        replace_dict = {}
        replace_dict[self.ctx.wf_dict['element']] = 'Y'

        new_structures = replace_element(orig_structure, Dict(dict=replace_dict), replace_all=Bool(True))

        structure = new_structures['replaced_all']
        inputs_yttrium_analogue = AttributeDict(self.exposed_inputs(FleurScfWorkChain,
                                                                    namespace='scf_yttrium_analogue'))
        inputs_yttrium_analogue.structure = structure

        if 'calc_parameters' not in inputs_yttrium_analogue:

            #Reuse parameters from rare earth calculation
            new_params = rare_earth_params.copy()
            for key, value in rare_earth_params.items():
                if 'atom' in key:
                    if 'element' in value:
                        if value['element'] == self.ctx.wf_dict['element']:
                            new_params.pop(key)
                            new_params[key] = self._yttrium_default_params
            inputs_yttrium_analogue.calc_parameters = Dict(dict=new_params)

        if self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in inputs_yttrium_analogue:
                scf_wf_dict = {}
            else:
                scf_wf_dict = inputs_yttrium_analogue.wf_parameters.get_dict()

            if 'inpxml_changes' not in scf_wf_dict:
                scf_wf_dict['inpxml_changes'] = []

            scf_wf_dict['inpxml_changes'].append(('set_species', {
                'species_name': 'all-Y',
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            inputs_yttrium_analogue.wf_parameters = Dict(dict=scf_wf_dict)

        return inputs_yttrium_analogue

    def get_inputs_scf(self):

        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in input_scf:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_scf.wf_parameters.get_dict()

            if 'inpxml_changes' not in scf_wf_dict:
                scf_wf_dict['inpxml_changes'] = []

            scf_wf_dict['inpxml_changes'].append(('set_species', {
                'species_name': f"all-{self.ctx.wf_dict['element']}",
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        return input_scf

    def get_inputs_orbcontrol(self):

        input_orbcontrol = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))

        if self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in input_orbcontrol['scf_no_ldau']:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_orbcontrol['scf_no_ldau'].wf_parameters.get_dict()

            if 'inpxml_changes' not in scf_wf_dict:
                scf_wf_dict['inpxml_changes'] = []

            scf_wf_dict['inpxml_changes'].append(('set_species', {
                'species_name': f"all-{self.ctx.wf_dict['element']}",
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            input_orbcontrol.scf_no_ldau.wf_parameters = Dict(dict=scf_wf_dict)

        return input_orbcontrol

    def run_cfcalculation(self):

        if 'scf' in self.inputs:
            if not self.ctx.rare_earth_scf.is_finished_ok:
                error = ('ERROR: SCF workflow (rare-earth) was not successful')
                self.report(error)
                return self.exit_codes.ERROR_SCF_FAILED

            try:
                outdict = self.ctx.rare_earth_scf.outputs.output_scf_wc_para
            except KeyError:
                message = ('ERROR: SCF workflow (rare-earth) failed, no scf output node')
                self.ctx.errors.append(message)
                return self.exit_codes.ERROR_SCF_FAILED
        else:
            if not self.ctx.rare_earth_orbcontrol.is_finished_ok:
                if self.ctx.rare_earth_orbcontrol.exit_status not in FleurOrbControlWorkChain.get_exit_statuses(
                    ['ERROR_SOME_CONFIGS_FAILED']):
                    error = ('ERROR: Orbcontrol workflow (rare-earth) was not successful')
                    self.report(error)
                    return self.exit_codes.ERROR_ORBCONTROL_FAILED

            try:
                outdict = self.ctx.rare_earth_orbcontrol.outputs.output_orbcontrol_wc_para
            except KeyError:
                message = ('ERROR: Orbcontrol workflow (rare-earth) failed, no orbcontrol output node')
                self.ctx.errors.append(message)
                return self.exit_codes.ERROR_ORBCONTROL_FAILED

            try:
                outdict = self.ctx.rare_earth_orbcontrol.outputs.output_orbcontrol_wc_gs_scf
            except KeyError:
                message = ('ERROR: Orbcontrol workflow (rare-earth) failed, no groundstate scf output node')
                self.ctx.errors.append(message)
                return self.exit_codes.ERROR_ORBCONTROL_FAILED

        if self.ctx.wf_dict['yttrium_analogue']:
            if not self.ctx.yttrium_analogue_scf.is_finished_ok:
                error = ('ERROR: SCF workflow (yttrium-analogue) was not successful')
                self.report(error)
                return self.exit_codes.ERROR_SCF_FAILED

            try:
                outdict = self.ctx.yttrium_analogue_scf.outputs.output_scf_wc_para
            except KeyError:
                message = ('ERROR: SCF workflow (yttrium-analogue) failed, no scf output node')
                self.ctx.errors.append(message)
                return self.exit_codes.ERROR_SCF_FAILED

        self.report('INFO: Running Crystal Field Calculations')
        calcs = {}
        if self.ctx.wf_dict['yttrium_analogue']:
            inputs = self.get_inputs_cfyttrium_calculation()
            result_yttrium = self.submit(FleurBaseWorkChain, **inputs)
            calcs['yttrium_analogue_cf'] = result_yttrium

        inputs = self.get_inputs_cfrareearth_calculation()
        result_rareearth = self.submit(FleurBaseWorkChain, **inputs)
        calcs['rare_earth_cf'] = result_rareearth

        return ToContext(**calcs)

    def get_inputs_cfyttrium_calculation(self):

        inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_yttrium_analogue'))

        fleurinp_scf = self.ctx.yttrium_analogue.outputs.fleurinp
        remote_data = load_node(
            self.ctx.yttrium_analogue.outputs.output_scf_wc_para['last_calc_uuid']).outputs.remote_folder

        if 'settings' in inputs:
            settings = inputs.settings.get_dict()
        else:
            settings = {}

        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = {}

        fm = FleurinpModifier(fleurinp_scf)

        fm.set_atomgroup(attributedict={'cFCoeffs': {'chargeDensity': False, 'potential': True}}, species='all-Y')

        fleurinp_cf = fm.freeze()

        label = 'Yttrium Analogue Potential'
        description = 'Calculation of crystal field potential with Yttrium Analogue Method'

        inputs_yttrium = get_inputs_fleur(inputs.fleur,
                                          remote_data,
                                          fleurinp_cf,
                                          options,
                                          label,
                                          description,
                                          settings=settings)
        return inputs_yttrium

    def get_inputs_cfrareearth_calculation(self):

        if 'scf' in self.inputs:
            inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

            fleurinp_scf = self.ctx.rare_earth_scf.outputs.fleurinp
            remote_data = load_node(
                self.ctx.rare_earth_scf.outputs.output_scf_wc_para['last_calc_uuid']).outputs.remote_folder
        elif 'orbcontrol' in self.inputs:
            inputs = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))

            fleurinp_scf = self.ctx.rare_earth_orbcontrol.outputs.output_orbcontrol_wc_gs_fleurinp
            gs_scf_para = self.ctx.rare_earth_orbcontrol.outputs.output_orbcontrol_wc_gs_scf
            remote_data = load_node(gs_scf_para['last_calc_uuid']).outputs.remote_folder

        if 'settings' in inputs:
            settings = inputs.settings.get_dict()
        else:
            settings = {}

        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = {}

        label = 'CF calculation'
        if self.ctx.wf_dict['yttrium_analogue']:
            description = 'Calculation of crystal field charge density'
        else:
            description = 'Calculation of crystal field potential/charge density'

        fm = FleurinpModifier(fleurinp_scf)
        element = self.ctx.wf_dict['element']
        if self.ctx.wf_dict['yttrium_analogue']:
            #Only charge density
            fm.set_atomgroup(attributedict={'cFCoeffs': {
                'chargeDensity': True,
                'potential': False
            }},
                             species=f'all-{element}')
        else:
            #Both potential and charge density
            fm.set_atomgroup(attributedict={'cFCoeffs': {
                'chargeDensity': True,
                'potential': True,
                'remove4f': True
            }},
                             species=f'all-{element}')
        fleurinp_cf = fm.freeze()

        inputs_rareearth = get_inputs_fleur(inputs.fleur,
                                            remote_data,
                                            fleurinp_cf,
                                            options,
                                            label,
                                            description,
                                            settings=settings)
        return inputs_rareearth

    def return_results(self):
        """
        Return results fo cf calculation
        """

        if self.ctx.wf_dict['yttrium_analogue']:
            calculations = ['rare_earth_cf', 'yttrium_analogue_cf']
        else:
            calculations = ['rare_earth_cf']

        skip_calculation = False
        retrieved_nodes = {}
        outnodedict = {}
        for calc_name in calculations:
            if calc_name in self.ctx:
                calc = self.ctx[calc_name]
            else:
                message = f'One CF calculation was not run because the scf workflow failed: {calc_name}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                skip_calculation = True
                continue

            if not calc.is_finished_ok:
                message = f'One CF calculation was not successful: {calc_name}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                skip_calculation = True
                continue

            try:
                outputnode_calc = calc.outputs.output_parameters
            except KeyError:
                message = f'One CF calculation failed, no output node: {calc_name}. I skip this one.'
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue

            if 'CFdata.hdf' not in calc.outputs.retrieved.list_object_names():
                message = f'One CF calculation did not produce a CFdata.hdf file: {calc_name}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                skip_calculation = True
                continue

            if calc_name == 'rare_earth_cf':
                retrieved_nodes['cdn'] = calc.outputs.retrieved
                if not self.ctx.wf_dict['yttrium_analogue']:
                    retrieved_nodes['pot'] = calc.outputs.retrieved
            elif calc_name == 'yttrium_analogue_cf':
                retrieved_nodes['pot'] = calc.outputs.retrieved

            link_label = calc_name
            outnodedict[link_label] = outputnode_calc

        cf_calc_out = {}
        if not skip_calculation:
            cf_calc_out = calculate_cf_coefficients(retrieved_nodes['cdn'],
                                                    retrieved_nodes['pot'],
                                                    convert=self.ctx.wf_dict['convert_to_stevens'])

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'cf_coefficients': {},
            'angle_a_to_x_axis': None,
            'angle_c_to_z_axis': None,
            'density_normalization': None,
            'cf_coefficients_units': 'K',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        if self.ctx.wf_dict['convert_to_stevens']:
            out['cf_coefficients_convention'] = 'Stevens'
        else:
            out['cf_coefficients_convention'] = 'Wybourne'

        for key, value in cf_calc_out.items():
            out[key] = value

        if self.ctx.successful:
            self.report('Done, Crystal Field coefficients calculation complete')
        else:
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance.')

        outnode = Dict(dict=out)
        outnodedict['results_node'] = outnode

        # create links between all these nodes...
        outputnode_dict = create_cfcoeff_results_node(**outnodedict)
        outputnode = outputnode_dict.get('output_cfcoeff_wc_para')
        outputnode.label = 'output_cfcoeff_wc_para'
        outputnode.description = (
            'Contains crystal field occupation results and information of an FleurCFCoeffWorkChain run.')

        returndict = {}
        returndict['output_cfcoeff_wc_para'] = outputnode

        # create link to workchain node
        for link_name, node in returndict.items():
            self.out(link_name, node)

        if not self.ctx.successful:
            return self.exit_codes.ERROR_CFCALC_FAILED

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. It will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_cfcoeff_results_node(**kwargs):
    """
    This is a pseudo cf, to create the right graph structure of AiiDA.
    This calcfunction will create the output nodes in the database.
    It also connects the output_nodes to all nodes the information comes from.
    This includes the output_parameter node for the orbcontrol, connections to run scfs,
    and returning of the gs_calculation (best initial density matrix)
    So far it is just parsed in as kwargs argument, because we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_cfcoeff_wc_para'] = outpara.clone()

    return outdict


def calculate_cf_coefficients(cf_cdn_folder, cf_pot_folder, convert=True):
    """
    Calculate the crystal filed coefficients using the tool from the
    masci-tools package

    :param cf_cdn_folder: FolderData for the retrieved files for the charge density data
    :param cf_pot_folder: FolderData for the retrieved files for the potential data
    """

    out_dict = {}

    cfcalc = CFCalculation(quiet=True)

    #Reading in the HDF files
    with cf_cdn_folder.open('CFdata.hdf', 'rb') as f:
        with h5py.File(f, 'r') as cffile:
            cfcalc.readCDN(cffile)

    with cf_pot_folder.open('CFdata.hdf', 'rb') as f:
        with h5py.File(f, 'r') as cffile:
            cfcalc.readPot(cffile)

    out_dict['cf_coefficients'] = cfcalc.performIntegration(convert=convert)
    #Output more information about the performed calculation
    out_dict['angle_a_to_x_axis'] = cfcalc.phi
    out_dict['angle_c_to_z_axis'] = cfcalc.theta
    out_dict['density_normalization'] = cfcalc.denNorm

    return out_dict
