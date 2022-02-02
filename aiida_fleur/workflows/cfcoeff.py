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
from aiida.engine import WorkChain, ToContext, ExitCode
from aiida.engine import calcfunction as cf
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent
from aiida import orm
from aiida.common.constants import elements as PeriodicTableElements

from aiida_fleur.tools.StructureData_util import replace_element
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.calculation.fleur import FleurCalculation

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain

from masci_tools.tools.cf_calculation import CFCalculation
from masci_tools.util.schema_dict_util import eval_simple_xpath, tag_exists

import h5py
from lxml import etree


class FleurCFCoeffWorkChain(WorkChain):
    """
    Workflow for calculating rare-earth crystal field coefficients
    """
    _workflowversion = '0.2.0'

    _wf_default = {
        'element': '',
        'rare_earth_analogue': False,
        'analogue_element': 'Y',
        'replace_all': True,
        'soc_off': True,
        'convert_to_stevens': True,
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace='scf_rare_earth_analogue',
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
        spec.input('wf_parameters', valid_type=orm.Dict, required=False)

        spec.outline(cls.start, cls.validate_input, cls.run_scfcalculations, cls.run_cfcalculation, cls.return_results)

        spec.output('output_cfcoeff_wc_para', valid_type=orm.Dict)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
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
        extra_keys = {key for key in self.ctx.wf_dict if key not in self._wf_default}
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
        if self.ctx.wf_dict['rare_earth_analogue']:
            self.report(f"INFO: Creating Rare-Earth Analogue with {self.ctx.wf_dict['analogue_element']}")
            inputs = self.get_inputs_rare_earth_analogue()
            result_analogue = self.submit(FleurScfWorkChain, **inputs)
            calcs['analogue_scf'] = result_analogue

        if 'scf' in self.inputs:
            inputs = self.get_inputs_scf()
            result_scf = self.submit(FleurScfWorkChain, **inputs)
            calcs['rare_earth_scf'] = result_scf
        elif 'orbcontrol' in self.inputs:
            inputs = self.get_inputs_orbcontrol()
            result_orbcontrol = self.submit(FleurOrbControlWorkChain, **inputs)
            calcs['rare_earth_orbcontrol'] = result_orbcontrol

        return ToContext(**calcs)

    def get_inputs_rare_earth_analogue(self):

        inputs = self.inputs
        if 'scf' in inputs:
            input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        elif 'orbcontrol' in self.inputs:
            input_scf = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))
            input_scf_tmp = input_scf.get('scf_no_ldau')
            if input_scf_tmp is None:
                input_scf_tmp = {}
                input_scf_tmp['structure'] = input_scf['structure']
                input_scf_tmp['inpgen'] = input_scf['inpgen']
                input_scf_tmp['fleur'] = input_scf['fleur']
                input_scf_tmp['options'] = input_scf['options']
                if 'calc_parameters' in input_scf:
                    input_scf_tmp['calc_parameters'] = input_scf['calc_parameters']
            input_scf = input_scf_tmp

        if 'structure' in input_scf:
            orig_structure = input_scf['structure']
        elif 'fleurinp' in input_scf:
            orig_structure = input_scf['fleurinp'].get_structuredata_ncf()

        if 'calc_parameters' in input_scf:
            rare_earth_params = input_scf['calc_parameters'].get_dict()
        else:
            rare_earth_params = {}

        replace_dict = {}
        replace_dict[self.ctx.wf_dict['element']] = self.ctx.wf_dict['analogue_element']

        new_structures = replace_element(orig_structure,
                                         orm.Dict(dict=replace_dict),
                                         replace_all=orm.Bool(self.ctx.wf_dict['replace_all']))

        structure = new_structures['replaced_all']
        inputs_analogue = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_rare_earth_analogue'))
        inputs_analogue.structure = structure

        if 'calc_parameters' not in inputs_analogue:

            #Reuse parameters from rare earth calculation
            new_params = rare_earth_params.copy()
            for key, value in rare_earth_params.items():
                if 'atom' in key:
                    if 'element' in value:
                        if value['element'] == self.ctx.wf_dict['element']:
                            new_params.pop(key)
            inputs_analogue.calc_parameters = orm.Dict(dict=new_params)

        if self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in inputs_analogue:
                scf_wf_dict = {}
            else:
                scf_wf_dict = inputs_analogue.wf_parameters.get_dict()

            scf_wf_dict.setdefault('inpxml_changes', []).append(('set_species', {
                'species_name': f"all-{self.ctx.wf_dict['analogue_element']}",
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            inputs_analogue.wf_parameters = orm.Dict(dict=scf_wf_dict)

        return inputs_analogue

    def get_inputs_scf(self):

        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in input_scf:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_scf.wf_parameters.get_dict()

            scf_wf_dict.setdefault('inpxml_changes', []).append(('set_species', {
                'species_name': f"all-{self.ctx.wf_dict['element']}",
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            input_scf.wf_parameters = orm.Dict(dict=scf_wf_dict)

        return input_scf

    def get_inputs_orbcontrol(self):

        input_orbcontrol = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))

        if self.ctx.wf_dict['soc_off'] and 'scf_no_ldau' in input_orbcontrol:
            if 'wf_parameters' not in input_orbcontrol['scf_no_ldau']:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_orbcontrol['scf_no_ldau'].wf_parameters.get_dict()

            scf_wf_dict.setdefault('inpxml_changes', []).append(('set_species', {
                'species_name': f"all-{self.ctx.wf_dict['element']}",
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            input_orbcontrol.scf_no_ldau.wf_parameters = orm.Dict(dict=scf_wf_dict)
        elif self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in input_orbcontrol:
                orbcontrol_wf_dict = {}
            else:
                orbcontrol_wf_dict = input_orbcontrol.wf_parameters.get_dict()

            orbcontrol_wf_dict.setdefault('inpxml_changes', []).append(('set_species', {
                'species_name': f"all-{self.ctx.wf_dict['element']}",
                'attributedict': {
                    'special': {
                        'socscale': 0.0
                    }
                }
            }))

            input_orbcontrol.wf_parameters = orm.Dict(dict=orbcontrol_wf_dict)

        return input_orbcontrol

    def run_cfcalculation(self):

        if 'scf' in self.inputs:
            if not self.ctx.rare_earth_scf.is_finished_ok:
                error = ('ERROR: SCF workflow (rare-earth) was not successful')
                self.report(error)
                return self.exit_codes.ERROR_SCF_FAILED

            try:
                outdict = self.ctx.rare_earth_scf.outputs.output_scf_wc_para
            except NotExistent:
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
            except NotExistent:
                message = ('ERROR: Orbcontrol workflow (rare-earth) failed, no orbcontrol output node')
                self.ctx.errors.append(message)
                self.report(message)
                return self.exit_codes.ERROR_ORBCONTROL_FAILED

            try:
                outdict = self.ctx.rare_earth_orbcontrol.outputs.groundstate_scf.output_scf_wc_para
            except NotExistent:
                message = ('ERROR: Orbcontrol workflow (rare-earth) failed, no groundstate scf output node')
                self.ctx.errors.append(message)
                self.report(message)
                return self.exit_codes.ERROR_ORBCONTROL_FAILED

        if self.ctx.wf_dict['rare_earth_analogue']:
            if not self.ctx.analogue_scf.is_finished_ok:
                error = (f"ERROR: SCF workflow ({self.ctx.wf_dict['analogue_element']}-analogue) was not successful")
                self.report(error)
                return self.exit_codes.ERROR_SCF_FAILED

            try:
                outdict = self.ctx.analogue_scf.outputs.output_scf_wc_para
            except NotExistent:
                message = (
                    f"ERROR: SCF workflow ({self.ctx.wf_dict['analogue_element']}-analogue) failed, no scf output node")
                self.ctx.errors.append(message)
                self.report(message)
                return self.exit_codes.ERROR_SCF_FAILED

        self.report('INFO: Running Crystal Field Calculations')
        calcs = {}
        if self.ctx.wf_dict['rare_earth_analogue']:
            inputs = self.get_inputs_cfanalogue_calculation()
            result_analogue = self.submit(FleurBaseWorkChain, **inputs)
            calcs['analogue_cf'] = result_analogue

        inputs = self.get_inputs_cfrareearth_calculation()
        result_rareearth = self.submit(FleurBaseWorkChain, **inputs)
        calcs['rare_earth_cf'] = result_rareearth

        return ToContext(**calcs)

    def get_inputs_cfanalogue_calculation(self):

        inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_rare_earth_analogue'))

        fleurinp_scf = self.ctx.analogue_scf.outputs.fleurinp
        remote_data = self.ctx.analogue_scf.outputs.last_calc.remote_folder

        if 'settings' in inputs:
            settings = inputs.settings.get_dict()
        else:
            settings = {}

        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = {}

        fm = FleurinpModifier(fleurinp_scf)

        analogue_element = self.ctx.wf_dict['analogue_element']
        fm.set_atomgroup(attributedict={'cFCoeffs': {
            'chargeDensity': False,
            'potential': True
        }},
                         species=f'all-{analogue_element}')

        try:
            fm.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, inp.xml changes did not validate')
            self.control_end_wc(error)
            return {}, self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, inp.xml changes could not be applied.\n'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return {}, self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        fleurinp_cf = fm.freeze()

        label = f'Rare-Earth Analogue ({analogue_element}) CF Potential'
        description = f'Calculation of crystal field potential with {analogue_element} Analogue Method'

        inputs_analogue = get_inputs_fleur(inputs.fleur,
                                           remote_data,
                                           fleurinp_cf,
                                           options,
                                           label,
                                           description,
                                           settings=settings)
        return inputs_analogue

    def get_inputs_cfrareearth_calculation(self):

        if 'scf' in self.inputs:
            inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

            fleurinp_scf = self.ctx.rare_earth_scf.outputs.fleurinp
            remote_data = self.ctx.rare_earth_scf.outputs.last_calc.remote_folder
        elif 'orbcontrol' in self.inputs:
            inputs = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))

            fleurinp_scf = self.ctx.rare_earth_orbcontrol.outputs.groundstate_scf.fleurinp
            remote_data = self.ctx.rare_earth_orbcontrol.outputs.groundstate_scf.last_calc.remote_folder

        if 'settings' in inputs:
            settings = inputs.settings.get_dict()
        else:
            settings = {}

        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = {}

        label = 'CF calculation'
        if self.ctx.wf_dict['rare_earth_analogue']:
            description = 'Calculation of crystal field charge density'
        else:
            description = 'Calculation of crystal field potential/charge density'

        fm = FleurinpModifier(fleurinp_scf)
        element = self.ctx.wf_dict['element']
        if self.ctx.wf_dict['rare_earth_analogue']:
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

        try:
            fm.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, inp.xml changes did not validate')
            self.control_end_wc(error)
            return {}, self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, inp.xml changes could not be applied.\n'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return {}, self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

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

        if self.ctx.wf_dict['rare_earth_analogue']:
            calculations = ['rare_earth_cf', 'analogue_cf']
        else:
            calculations = ['rare_earth_cf']

        skip_calculation = False
        retrieved_nodes = {}
        outnodedict = {}
        atomTypes = []
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
            except NotExistent:
                message = f'One CF calculation failed, no output node: {calc_name}. I skip this one.'
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue

            if FleurCalculation._CFDATA_HDF5_FILE_NAME not in calc.outputs.retrieved.list_object_names():
                message = f'One CF calculation did not produce a {FleurCalculation._CFDATA_HDF5_FILE_NAME} file: {calc_name}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                skip_calculation = True
                continue

            if calc_name == 'rare_earth_cf':
                retrieved_nodes['cdn'] = calc.outputs.retrieved
                if not self.ctx.wf_dict['rare_earth_analogue']:
                    retrieved_nodes['pot'] = calc.outputs.retrieved
            elif calc_name == 'analogue_cf':
                retrieved_nodes['pot'] = calc.outputs.retrieved

            if not atomTypes:
                xmltree, schema_dict = calc.inputs.fleurinpdata.load_inpxml()

                groups = eval_simple_xpath(xmltree, schema_dict, 'atomGroup')
                for index, group in enumerate(groups):
                    if tag_exists(group, schema_dict, 'cfcoeffs'):
                        atomTypes.append(index + 1)

            link_label = calc_name
            outnodedict[link_label] = outputnode_calc

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'angle_a_to_x_axis': None,
            'angle_c_to_z_axis': None,
            'density_normalization': None,
            'cf_coefficients_spin_up': None,
            'cf_coefficients_spin_down': None,
            'cf_coefficients_convention': None,
            'cf_coefficients_units': 'K',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        if not skip_calculation:
            cf_calc_out = calculate_cf_coefficients(retrieved_nodes['cdn'],
                                                    retrieved_nodes['pot'],
                                                    convert=orm.Bool(self.ctx.wf_dict['convert_to_stevens']),
                                                    atomTypes=orm.List(list=atomTypes))
            if isinstance(cf_calc_out, orm.Dict):
                for key, value in cf_calc_out.get_dict().items():
                    out[key] = value
            else:
                self.report('Calculation of crystal field coefficients failed')
                self.ctx.successful = False

        if self.ctx.successful:
            self.report('Done, Crystal Field coefficients calculation complete')
        else:
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance or the post-processing failed.')

        outnode = orm.Dict(dict=out)
        outnodedict['results_node'] = outnode
        outnodedict['crystal_field_coefficients'] = cf_calc_out

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


@cf
def calculate_cf_coefficients(cf_cdn_folder: orm.FolderData,
                              cf_pot_folder: orm.FolderData,
                              convert: orm.Bool = None,
                              atomTypes: orm.List = None) -> orm.Dict:
    """
    Calculate the crystal filed coefficients using the tool from the
    masci-tools package

    :param cf_cdn_folder: FolderData for the retrieved files for the charge density data
    :param cf_pot_folder: FolderData for the retrieved files for the potential data

    :raises: ExitCode 300, CFData.hdf file is missing
    :raises: ExitCode 310, CFdata.hdf reading failed
    :raises: ExitCode 320, Crystal field calculation failed
    """

    if convert is None:
        convert = orm.Bool(True)

    out_dict = {}

    units = None
    convention = None
    phi = None
    theta = None
    norm = None
    coefficients_dict_up = {}
    coefficients_dict_dn = {}
    coefficients_dict_up_imag = {}
    coefficients_dict_dn_imag = {}
    if atomTypes is None:
        cfcalc, coefficients = _calculate_single_atomtype(cf_cdn_folder, cf_pot_folder, convert)
        for coeff in coefficients:
            if units is None:
                units = coeff.unit
                convention = coeff.convention
            key = f'{coeff.l}/{coeff.m}'
            coefficients_dict_up[key] = coeff.spin_up.real
            coefficients_dict_dn[key] = coeff.spin_down.real
            coefficients_dict_up_imag[key] = coeff.spin_up.imag
            coefficients_dict_dn_imag[key] = coeff.spin_down.imag
        phi = cfcalc.phi
        theta = cfcalc.theta
        norm = cfcalc.denNorm
    else:
        norm = {}
        for atomType in atomTypes:
            cfcalc, coefficients = _calculate_single_atomtype(cf_cdn_folder, cf_pot_folder, convert, atomType=atomType)

            atom_up = coefficients_dict_up.setdefault(atomType, {})
            atom_dn = coefficients_dict_dn.setdefault(atomType, {})
            atom_up_imag = coefficients_dict_up_imag.setdefault(atomType, {})
            atom_dn_imag = coefficients_dict_dn_imag.setdefault(atomType, {})
            norm[atomType] = cfcalc.denNorm
            phi = cfcalc.phi
            theta = cfcalc.theta

            for coeff in coefficients:
                if units is None:
                    units = coeff.unit
                    convention = coeff.convention
                key = f'{coeff.l}/{coeff.m}'
                atom_up[key] = coeff.spin_up.real
                atom_dn[key] = coeff.spin_down.real
                atom_up_imag[key] = coeff.spin_up.imag
                atom_dn_imag[key] = coeff.spin_down.imag

    out_dict['cf_coeffcients_atomtypes'] = atomTypes.get_list()
    out_dict['cf_coefficients_spin_up'] = coefficients_dict_up
    out_dict['cf_coefficients_spin_down'] = coefficients_dict_dn
    if not convert:
        out_dict['cf_coefficients_spin_up_imag'] = coefficients_dict_up_imag
        out_dict['cf_coefficients_spin_down_imag'] = coefficients_dict_dn_imag
    #Output more information about the performed calculation
    out_dict['angle_a_to_x_axis'] = phi
    out_dict['angle_c_to_z_axis'] = theta
    out_dict['density_normalization'] = norm
    out_dict['cf_coefficients_units'] = units
    out_dict['cf_coefficients_convention'] = convention

    out_dict = orm.Dict(dict=out_dict)
    out_dict.label = 'CFCoefficients'
    out_dict.description = 'Results of the post-processing tool for calculating Crystal field coefficients'

    return out_dict


def _calculate_single_atomtype(cf_cdn_folder, cf_pot_folder, convert, **kwargs):
    """
    Private method wrapping the calculation of coefficients
    """
    CRYSTAL_FIELD_FILE = FleurCalculation._CFDATA_HDF5_FILE_NAME

    cfcalc = CFCalculation(quiet=True)
    #Reading in the HDF files
    if CRYSTAL_FIELD_FILE in cf_cdn_folder.list_object_names():
        try:
            with cf_cdn_folder.open(CRYSTAL_FIELD_FILE, 'rb') as f:
                with h5py.File(f, 'r') as cffile:
                    cfcalc.readCDN(cffile, **kwargs)
        except ValueError as exc:
            return ExitCode(310, message=f'{CRYSTAL_FIELD_FILE} reading failed with: {exc}')
    else:
        return ExitCode(300, message=f'{CRYSTAL_FIELD_FILE} file not in the retrieved files')

    if CRYSTAL_FIELD_FILE in cf_pot_folder.list_object_names():
        try:
            with cf_pot_folder.open(CRYSTAL_FIELD_FILE, 'rb') as f:
                with h5py.File(f, 'r') as cffile:
                    cfcalc.readPot(cffile, **kwargs)
        except ValueError as exc:
            return ExitCode(310, message=f'{CRYSTAL_FIELD_FILE} reading failed with: {exc}')
    else:
        return ExitCode(300, message=f'{CRYSTAL_FIELD_FILE} file not in the retrieved files')

    try:
        coefficients = cfcalc.performIntegration(convert=convert)
    except ValueError as exc:
        return ExitCode(320, message=f'Crystal field calculation failed with: {exc}')
    if len(coefficients) == 0:
        return ExitCode(320, message='Crystal field calculation failed with: No Coefficients produced')

    return cfcalc, coefficients
