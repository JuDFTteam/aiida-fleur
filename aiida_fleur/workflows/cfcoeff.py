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

from aiida_fleur.tools.StructureData_util import replace_element, mark_atoms, get_atomtype_site_symmetry
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier, inpxml_changes
from aiida_fleur.calculation.fleur import FleurCalculation

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain

from masci_tools.tools.cf_calculation import CFCalculation, CFCoefficient
from masci_tools.util.schema_dict_util import eval_simple_xpath, tag_exists

import h5py
from lxml import etree
import numpy as np


def reconstruct_cfcoeffcients(output_dict, atomtype=None):
    """
    Reconstruct the CFCoefficient list from the output dictionary
    of the FleurCFCoeffWorkChain

    :param output_dict: output dictionary node or the corresponding
                        dictionary
    :param atomtype: int of the atomtype to reconstruct the coefficients for
    """
    if isinstance(output_dict, orm.Dict):
        output_dict = output_dict.get_dict()

    if atomtype is not None and not isinstance(atomtype, str):
        atomtype = str(atomtype)

    multiple_atomtypes = all('/' not in key for key in output_dict['cf_coefficients_spin_up'])

    if atomtype is None and multiple_atomtypes:
        raise ValueError('atomtype not specified')

    if multiple_atomtypes and atomtype not in output_dict['cf_coefficients_spin_up']:
        raise ValueError(f'Atomtype {atomtype} not available')

    spin_up = output_dict['cf_coefficients_spin_up']
    spin_down = output_dict['cf_coefficients_spin_down']
    spin_up_imag = output_dict.get('cf_coefficients_spin_up_imag', {})
    spin_down_imag = output_dict.get('cf_coefficients_spin_down_imag', {})

    convention = output_dict['cf_coefficients_convention']
    unit = output_dict['cf_coefficients_units']

    if multiple_atomtypes:
        spin_up = spin_up[atomtype]
        spin_down = spin_down[atomtype]
        spin_up_imag = spin_up_imag.get(atomtype, {})
        spin_down_imag = spin_down_imag.get(atomtype, {})

    coefficients = []
    for key in spin_up:
        l, m = key.split('/', maxsplit=1)
        up = spin_up[key]
        if key in spin_up_imag:
            up = up + 1j * spin_up_imag[key]
        down = spin_down[key]
        if key in spin_down_imag:
            down = down + 1j * spin_down_imag[key]

        coefficients.append(CFCoefficient(l=l, m=m, spin_up=up, spin_down=down, unit=unit, convention=convention))

    return coefficients


def reconstruct_cfcalculation(charge_densities, potentials, atomtype, **kwargs):
    """
    Reconstruct the CFCalculation instance from the outputs of the
    FleurCFCoeffWorkChain
    """

    radial_meshes = {'cdn': charge_densities.get_x()[1], 'pot': potentials.get_x()[1]}
    names, cdn_array, _ = zip(*charge_densities.get_y())
    if f'atomtype-{atomtype}' not in names:
        raise ValueError(f'Atomtype {atomtype} not available')
    density = cdn_array[names.index(f'atomtype-{atomtype}')]

    names, pot_array, _ = zip(*potentials.get_y())

    pot_dict = {}
    for l in range(0, 7):
        for m in range(-l, l + 1):
            if f'atomtype-{atomtype}-{l}/{m}-up' in names:
                p = [pot_array[names.index(f'atomtype-{atomtype}-{l}/{m}-up')]]
                if f'atomtype-{atomtype}-{l}/{m}-down' in names:
                    p.append(pot_array[names.index(f'atomtype-{atomtype}-{l}/{m}-down')])
                pot_dict[(l, m)] = np.array(p)

    cfcalc = CFCalculation.from_arrays(density, potentials=pot_dict, radial_mesh=radial_meshes, **kwargs)

    return cfcalc


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

    _CF_GROUP_LABEL = '89999'

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
        spec.output('output_cfcoeff_wc_charge_densities', valid_type=orm.XyData, required=False)
        spec.output('output_cfcoeff_wc_potentials', valid_type=orm.XyData, required=False)

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
        self.ctx.num_analogues = None
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

        if 'scf' in inputs and 'orbcontrol' in inputs:
            error = 'ERROR: Invalid Input. Provide only one of the scf or orbcontrol inputs.'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        element = self.ctx.wf_dict['element']
        atomic_numbers = {data['symbol']: num for num, data in PeriodicTableElements.items()}
        if element not in atomic_numbers:
            error = f'ERROR: Invalid Input. Element not a valid element: {element}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if atomic_numbers[element] < 57 and atomic_numbers[element] > 70:
            error = 'ERROR: Invalid Input. CF coefficient workflow only implemented for 4f rare-earths'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def run_scfcalculations(self):

        self.report('INFO: Starting SCF calculations')
        inputs = {}
        calcs = {}
        if self.ctx.wf_dict['rare_earth_analogue']:
            self.report(f"INFO: Creating Rare-Earth Analogue with {self.ctx.wf_dict['analogue_element']}")
            all_inputs = self.get_inputs_rare_earth_analogue()
            for name, inputs in all_inputs.items():
                calcs[name] = self.submit(FleurScfWorkChain, **inputs)
                calcs[name].label = name
                calcs[
                    name].description = f"SCF workflow for the rare-earth analogue ({self.ctx.wf_dict['analogue_element']}); number {name.split('_')[-1]}"

        if 'scf' in self.inputs:
            inputs = self.get_inputs_scf()
            result_scf = self.submit(FleurScfWorkChain, **inputs)
            calcs['rare_earth_scf'] = result_scf
            calcs['rare_earth_scf'].label = 'rare_earth_scf'
            calcs['rare_earth_scf'].description = 'SCF workflow for the rare-earth system for the CF calculation'
        elif 'orbcontrol' in self.inputs:
            inputs = self.get_inputs_orbcontrol()
            result_orbcontrol = self.submit(FleurOrbControlWorkChain, **inputs)
            calcs['rare_earth_orbcontrol'] = result_orbcontrol
            calcs['rare_earth_orbcontrol'].label = 'rare_earth_orbcontrol'
            calcs[
                'rare_earth_orbcontrol'].description = 'Orbcontrol workflow for the rare-earth system for the CF calculation'

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
        elif 'fleurinp' in input_scf:
            rare_earth_params = input_scf['fleurinp'].get_parameterdata_ncf(write_ids=False).get_dict()
        else:
            rare_earth_params = {}

        replace_dict = {}
        replace_dict[self.ctx.wf_dict['element']] = self.ctx.wf_dict['analogue_element']

        new_structures = replace_element(orig_structure,
                                         orm.Dict(dict=replace_dict),
                                         replace_all=orm.Bool(self.ctx.wf_dict['replace_all']))

        inputs = {}
        self.ctx.num_analogues = len(new_structures)
        for index, structure in enumerate(new_structures.values()):
            inputs_analogue = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_rare_earth_analogue'))
            inputs_analogue.structure = structure
            # inputs_analogue.structure = mark_atoms(structure,
            #                                        lambda _, kind: kind.symbols ==
            #                                        (self.ctx.wf_dict['analogue_element'],),
            #                                        kind_id=self._CF_GROUP_LABEL)

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

                with inpxml_changes(scf_wf_dict) as fm:
                    fm.set_species(f"all-{self.ctx.wf_dict['analogue_element']}", {'special': {'socscale': 0}})

            inputs_analogue.wf_parameters = orm.Dict(dict=scf_wf_dict)
            inputs_analogue.metadata.call_link_label = f'analogue_scf_{index}'
            inputs[f'analogue_scf_{index}'] = inputs_analogue

        return inputs

    def get_inputs_scf(self):

        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in input_scf:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_scf.wf_parameters.get_dict()
            with inpxml_changes(scf_wf_dict) as fm:
                fm.set_species(f"all-{self.ctx.wf_dict['element']}", {'special': {'socscale': 0}})

            input_scf.wf_parameters = orm.Dict(dict=scf_wf_dict)
        input_scf.metadata.call_link_label = 'rare_earth_scf'

        return input_scf

    def get_inputs_orbcontrol(self):

        input_orbcontrol = AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))

        if self.ctx.wf_dict['soc_off'] and 'scf_no_ldau' in input_orbcontrol:
            if 'wf_parameters' not in input_orbcontrol['scf_no_ldau']:
                scf_wf_dict = {}
            else:
                scf_wf_dict = input_orbcontrol['scf_no_ldau'].wf_parameters.get_dict()

            with inpxml_changes(scf_wf_dict) as fm:
                fm.set_species(f"all-{self.ctx.wf_dict['element']}", {'special': {'socscale': 0}})

            input_orbcontrol.scf_no_ldau.wf_parameters = orm.Dict(dict=scf_wf_dict)
        elif self.ctx.wf_dict['soc_off']:
            if 'wf_parameters' not in input_orbcontrol:
                orbcontrol_wf_dict = {}
            else:
                orbcontrol_wf_dict = input_orbcontrol.wf_parameters.get_dict()

            with inpxml_changes(orbcontrol_wf_dict) as fm:
                fm.set_species(f"all-{self.ctx.wf_dict['element']}", {'special': {'socscale': 0}})

            input_orbcontrol.wf_parameters = orm.Dict(dict=orbcontrol_wf_dict)
        input_orbcontrol.metadata.call_link_label = 'rare_earth_orbcontrol'

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
            if not all(self.ctx[f'analogue_scf_{index}'].is_finished_ok for index in range(self.ctx.num_analogues)):
                error = (
                    f"ERROR: One SCF workflow ({self.ctx.wf_dict['analogue_element']}-analogue) was not successful")
                self.report(error)
                return self.exit_codes.ERROR_SCF_FAILED

            try:
                for index in range(self.ctx.num_analogues):
                    _ = self.ctx[f'analogue_scf_{index}'].outputs.output_scf_wc_para
            except NotExistent:
                message = (
                    f"ERROR: SCF workflow ({self.ctx.wf_dict['analogue_element']}-analogue) failed, no scf output node")
                self.ctx.errors.append(message)
                self.report(message)
                return self.exit_codes.ERROR_SCF_FAILED

        self.report('INFO: Running Crystal Field Calculations')
        calcs = {}
        if self.ctx.wf_dict['rare_earth_analogue']:
            all_inputs = self.get_inputs_cfanalogue_calculation()
            for name, inputs in all_inputs.items():
                calcs[name] = self.submit(FleurBaseWorkChain, **inputs)
                calcs[name].label = name
                calcs[
                    name].description = f"Calculation of crystal field potential with {self.ctx.wf_dict['analogue_element']} Analogue Method"

        inputs = self.get_inputs_cfrareearth_calculation()
        result_rareearth = self.submit(FleurBaseWorkChain, **inputs)
        calcs['rare_earth_cf'] = result_rareearth
        calcs['rare_earth_cf'].label = 'rare_earth_cf'
        calcs['rare_earth_cf'].description = 'Crystal Field Calculation including the 4f element'

        return ToContext(**calcs)

    def get_inputs_cfanalogue_calculation(self):

        analogue_element = self.ctx.wf_dict['analogue_element']

        all_inputs = {}
        for index in range(self.ctx.num_analogues):
            inputs = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf_rare_earth_analogue'))

            fleurinp_scf = self.ctx[f'analogue_scf_{index}'].outputs.fleurinp
            remote_data = self.ctx[f'analogue_scf_{index}'].outputs.last_calc.remote_folder

            if 'settings' in inputs:
                settings = inputs.settings.get_dict()
            else:
                settings = {}

            if 'options' in inputs:
                options = inputs.options.get_dict()
            else:
                options = {}

            fm = FleurinpModifier(fleurinp_scf)

            fm.set_atomgroup({'cFCoeffs': {
                'chargeDensity': False,
                'potential': True
            }},
                             species=f"all-{self.ctx.wf_dict['analogue_element']}")

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

            label = f'analogue_cf_{index}'
            description = f'Calculation of crystal field potential with {analogue_element} Analogue Method'

            all_inputs[label] = get_inputs_fleur(inputs.fleur,
                                                 remote_data,
                                                 fleurinp_cf,
                                                 options,
                                                 label,
                                                 description,
                                                 settings=settings)
            all_inputs[label].setdefault('metadata', {})['call_link_label'] = label

        return all_inputs

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

        label = 'rare_earth_cf'
        if self.ctx.wf_dict['rare_earth_analogue']:
            description = 'Calculation of crystal field charge density'
        else:
            description = 'Calculation of crystal field potential/charge density'

        fm = FleurinpModifier(fleurinp_scf)
        element = self.ctx.wf_dict['element']
        if self.ctx.wf_dict['rare_earth_analogue']:
            #Only charge density
            fm.set_atomgroup({'cFCoeffs': {'chargeDensity': True, 'potential': False}}, species=f'all-{element}')
        else:
            #Both potential and charge density
            fm.set_atomgroup({'cFCoeffs': {
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
        inputs_rareearth.setdefault('metadata', {})['call_link_label'] = label

        return inputs_rareearth

    def check_cf_calculation(self, calc_name):
        """
        Check that the CFCalculation finished successfully
        """
        successful = True

        if calc_name in self.ctx:
            calc = self.ctx[calc_name]
        else:
            message = f'One CF calculation was not run because the scf workflow failed: {calc_name}'
            self.ctx.warnings.append(message)
            successful = False
            self.ctx.successful = self.ctx.successful and successful
            return successful

        if not calc.is_finished_ok:
            message = f'One CF calculation was not successful: {calc_name}'
            self.ctx.warnings.append(message)
            successful = False

        try:
            _ = calc.outputs.output_parameters
        except NotExistent:
            message = f'One CF calculation failed, no output node: {calc_name}. I skip this one.'
            self.ctx.errors.append(message)
            successful = False

        if FleurCalculation._CFDATA_HDF5_FILE_NAME not in calc.outputs.retrieved.list_object_names():
            message = f'One CF calculation did not produce a {FleurCalculation._CFDATA_HDF5_FILE_NAME} file: {calc_name}'
            self.ctx.warnings.append(message)
            successful = False

        self.ctx.successful = self.ctx.successful and successful
        return successful

    def return_results(self):
        """
        Return results fo cf calculation
        """

        outnodedict = {}
        cf_calcs_out = []  #All single nodes
        charge_densities = []
        potentials = []

        #This calculation is always there
        success = self.check_cf_calculation('rare_earth_cf')
        if success:
            link_label = 'rare_earth_cf'
            outnodedict[link_label] = self.ctx.rare_earth_cf.outputs.output_parameters
            cdn_retrieved = self.ctx.rare_earth_cf.outputs.retrieved
            xmltree, schema_dict = self.ctx.rare_earth_cf.inputs.fleurinp.load_inpxml()

            groups = eval_simple_xpath(xmltree, schema_dict, 'atomGroup', list_return=True)
            atomTypes = []
            for index, group in enumerate(groups):
                if tag_exists(group, schema_dict, 'cfcoeffs'):
                    atomTypes.append(index + 1)

            if not self.ctx.wf_dict['rare_earth_analogue']:
                pot_retrieved = self.ctx.rare_earth_cf.outputs.retrieved
                res = calculate_cf_coefficients(cdn_retrieved,
                                                pot_retrieved,
                                                convert=orm.Bool(self.ctx.wf_dict['convert_to_stevens']),
                                                atomTypes=orm.List(list=atomTypes))
                if isinstance(res, ExitCode):
                    self.report(f'Calculation of crystal field coefficients failed with {cf_calc_out!r}')
                    self.ctx.successful = False
                    success = False
                    cf_calc_out = {}
                else:
                    cf_calc_out = res['out']
                    cf_calcs_out = [cf_calc_out]
                    cf_calc_out = cf_calc_out.get_dict()
                    charge_densities = [res['charge_densities']]
                    potentials = [res['potentials']]
            else:
                cf_calc_out = {}
                for index in range(self.ctx.num_analogues):
                    calc_name = f'analogue_cf_{index}'
                    success = self.check_cf_calculation(calc_name)
                    if not success:
                        continue
                    pot_retrieved = self.ctx[calc_name].outputs.retrieved
                    outnodedict[link_label] = self.ctx[calc_name].outputs.output_parameters

                    xmltree, schema_dict = self.ctx[calc_name].inputs.fleurinp.load_inpxml()
                    groups = eval_simple_xpath(xmltree, schema_dict, 'atomGroup', list_return=True)
                    atomTypes = []
                    for group_index, group in enumerate(groups):
                        if tag_exists(group, schema_dict, 'cfcoeffs'):
                            atomTypes.append(group_index + 1)

                    cf_calc_out_analogue = calculate_cf_coefficients(cdn_retrieved,
                                                                     pot_retrieved,
                                                                     convert=orm.Bool(
                                                                         self.ctx.wf_dict['convert_to_stevens']),
                                                                     atomTypes=orm.List(list=atomTypes))
                    if isinstance(cf_calc_out_analogue, ExitCode):
                        self.report(
                            f'Calculation of crystal field coefficients failed: {calc_name} with {cf_calc_out!r}')
                        self.ctx.successful = False
                        continue

                    charge_densities.append(cf_calc_out_analogue['charge_densities'])
                    potentials.append(cf_calc_out_analogue['potentials'])
                    cf_calc_out_analogue = cf_calc_out_analogue['out']

                    cf_calcs_out.append(cf_calc_out_analogue)

                    if not cf_calc_out:
                        cf_calc_out = cf_calc_out_analogue.get_dict()
                    else:
                        cf_calc_out['cf_coefficients_atomtypes'] += atomTypes

                    cf_calc_out['cf_coefficients_spin_up'] = {
                        **cf_calc_out['cf_coefficients_spin_up'],
                        **cf_calc_out_analogue['cf_coefficients_spin_up']
                    }
                    cf_calc_out['cf_coefficients_spin_down'] = {
                        **cf_calc_out['cf_coefficients_spin_down'],
                        **cf_calc_out_analogue['cf_coefficients_spin_down']
                    }
                    if not self.ctx.wf_dict['convert_to_stevens']:
                        cf_calc_out['cf_coefficients_spin_up_imag'] = {
                            **cf_calc_out['cf_coefficients_spin_up_imag'],
                            **cf_calc_out_analogue['cf_coefficients_spin_up_imag']
                        }
                        cf_calc_out['cf_coefficients_spin_down_imag'] = {
                            **cf_calc_out['cf_coefficients_spin_down_imag'],
                            **cf_calc_out_analogue['cf_coefficients_spin_down_imag']
                        }

        #pop out output if only one atomtype is calculated
        if success and len(cf_calc_out['cf_coefficients_atomtypes']) == 1:
            _, cf_calc_out['cf_coefficients_spin_up'] = cf_calc_out['cf_coefficients_spin_up'].popitem()
            _, cf_calc_out['cf_coefficients_spin_down'] = cf_calc_out['cf_coefficients_spin_down'].popitem()
            if not self.ctx.wf_dict['convert_to_stevens']:
                _, cf_calc_out['cf_coefficients_spin_up_imag'] = cf_calc_out['cf_coefficients_spin_up_imag'].popitem()
                _, cf_calc_out['cf_coefficients_spin_down_imag'] = cf_calc_out[
                    'cf_coefficients_spin_down_imag'].popitem()

        rare_earth_site_symmetries = []
        if success and len(cf_calc_out['cf_coefficients_atomtypes']) > 0:
            #For this to work the order of the atomtype CANNOT change between the conversions
            struc = self.ctx.rare_earth_cf.inputs.fleurinp.get_structuredata_ncf()
            site_symmetries = get_atomtype_site_symmetry(struc)
            rare_earth_site_symmetries = [
                site_symmetries[atomtype - 1] for atomtype in cf_calc_out['cf_coefficients_atomtypes']
            ]

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
            'cf_coefficients_site_symmetries': rare_earth_site_symmetries,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        if cf_calc_out:
            for key, value in cf_calc_out.items():
                out[key] = value

        if self.ctx.successful:
            self.report('Done, Crystal Field coefficients calculation complete')
        else:
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance or the post-processing failed.')

        outnode = orm.Dict(dict=out)
        outnodedict = {f'crystal_field_coefficients_{index}': cf_coff for index, cf_coff in enumerate(cf_calcs_out)}
        outnodedict['results_node'] = outnode

        if charge_densities:
            #Merge the different calculations together
            cdn_output = orm.XyData()
            x_name, x_array, x_unit = charge_densities[0].get_x()
            cdn_output.set_x(x_array, x_name, x_unit)

            y_names, y_arrays, y_units = [], [], []
            for cdn in charge_densities:
                names, arrays, units = zip(*cdn.get_y())
                y_names.extend(names)
                y_arrays.extend(arrays)
                y_units.extend(units)
            cdn_output.set_y(y_arrays, y_names, y_units)

            cdn_output.label = 'output_cfcoeff_wc_charge_densities'
            cdn_output.description = 'Charge densities used in the Crystal Field calculation'
            outnodedict['charge_densities'] = cdn_output

            #Merge the different calculations together
            pot_output = orm.XyData()
            x_name, x_array, x_unit = potentials[0].get_x()
            pot_output.set_x(x_array, x_name, x_unit)

            y_names, y_arrays, y_units = [], [], []
            for pot in potentials:
                names, arrays, units = zip(*pot.get_y())
                y_names.extend(names)
                y_arrays.extend(arrays)
                y_units.extend(units)
            pot_output.set_y(y_arrays, y_names, y_units)

            pot_output.label = 'output_cfcoeff_wc_potentials'
            pot_output.description = 'Potentials used in the Crystal Field calculation'
            outnodedict['potentials'] = pot_output

        # create links between all these nodes...
        outputnode_dict = create_cfcoeff_results_node(**outnodedict)
        outputnode = outputnode_dict.get('output_cfcoeff_wc_para')
        outputnode.label = 'output_cfcoeff_wc_para'
        outputnode.description = (
            'Contains crystal field occupation results and information of an FleurCFCoeffWorkChain run.')

        returndict = {}
        returndict['output_cfcoeff_wc_para'] = outputnode
        if charge_densities:
            returndict['output_cfcoeff_wc_charge_densities'] = cdn_output
            returndict['output_cfcoeff_wc_potentials'] = pot_output

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

    charge_densities = {}
    charge_densities_rmesh = None
    potentials = {}
    potentials_rmesh = None

    if atomTypes is None:
        res = _calculate_single_atomtype(cf_cdn_folder, cf_pot_folder, convert)
        if isinstance(res, ExitCode):
            return res
        cfcalc, coefficients = res
        atomTypes = orm.List(list=[cfcalc.atom_type])
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
        norm = cfcalc.density_normalization

        atom_prefix = f'atomtype-{cfcalc.atom_type}'
        charge_densities_rmesh, charge_densities[atom_prefix] = cfcalc.get_charge_density(interpolated=False)

        potentials_rmesh, potentials_up = cfcalc.get_potentials('up', interpolated=False)
        potentials_down = {}
        if cfcalc.spin_polarized:
            _, potentials_down = cfcalc.get_potentials('down', interpolated=False)

        for (l, m), pot in potentials_up.items():
            prefix = f'{prefix}-{l}/{m}'
            potentials[f'{prefix}-up'] = pot
            if (l, m) in potentials_down:
                potentials[f'{prefix}-down'] = potentials_down[(l, m)]

    else:
        norm = {}
        for atom_type in atomTypes:
            res = _calculate_single_atomtype(cf_cdn_folder, cf_pot_folder, convert, atom_type=atom_type)
            if isinstance(res, ExitCode):
                return res
            cfcalc, coefficients = res

            atom_up = coefficients_dict_up.setdefault(atom_type, {})
            atom_dn = coefficients_dict_dn.setdefault(atom_type, {})
            atom_up_imag = coefficients_dict_up_imag.setdefault(atom_type, {})
            atom_dn_imag = coefficients_dict_dn_imag.setdefault(atom_type, {})
            norm[atom_type] = cfcalc.density_normalization
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

            atom_prefix = f'atomtype-{atom_type}'
            rmesh, charge_densities[atom_prefix] = cfcalc.get_charge_density(interpolated=False)
            if charge_densities_rmesh is None:
                charge_densities_rmesh = rmesh

            rmesh, potentials_up = cfcalc.get_potentials('up', interpolated=False)
            if potentials_rmesh is None:
                potentials_rmesh = rmesh
            potentials_down = {}
            if cfcalc.spin_polarized:
                _, potentials_down = cfcalc.get_potentials('down', interpolated=False)

            for (l, m), pot in potentials_up.items():
                prefix = f'{atom_prefix}-{l}/{m}'
                potentials[f'{prefix}-up'] = pot
                if (l, m) in potentials_down:
                    potentials[f'{prefix}-down'] = potentials_down[(l, m)]

    out_dict['cf_coefficients_atomtypes'] = atomTypes.get_list()
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

    cdn_data = orm.XyData()
    cdn_data.set_x(charge_densities_rmesh, 'rmesh', x_units='Bohr')

    y_names, y_arrays = zip(*charge_densities.items())
    y_units = ['density'] * len(y_names)
    cdn_data.set_y(y_arrays, y_names, y_units=y_units)

    cdn_data.label = 'cfcoeff_cdn_data'
    cdn_data.description = ('Contains XyData for the Charge density used in the crystal field calculation')

    pot_data = orm.XyData()
    pot_data.set_x(potentials_rmesh, 'rmesh', x_units='Bohr')

    y_names, y_arrays = zip(*potentials.items())
    y_units = ['htr'] * len(y_names)
    pot_data.set_y([d.real for d in y_arrays], y_names, y_units=y_units)

    pot_data.label = 'cfcoeff_pot_data'
    pot_data.description = ('Contains XyData for the Poteintials used in the crystal field calculation')

    return {'out': out_dict, 'charge_densities': cdn_data, 'potentials': pot_data}


def _calculate_single_atomtype(cf_cdn_folder, cf_pot_folder, convert, **kwargs):
    """
    Private method wrapping the calculation of coefficients
    """
    CRYSTAL_FIELD_FILE = FleurCalculation._CFDATA_HDF5_FILE_NAME

    cfcalc = CFCalculation()
    #Reading in the HDF files
    if CRYSTAL_FIELD_FILE in cf_cdn_folder.list_object_names():
        try:
            with cf_cdn_folder.open(CRYSTAL_FIELD_FILE, 'rb') as f:
                with h5py.File(f, 'r') as cffile:
                    cfcalc.read_charge_density(cffile, **kwargs)
        except ValueError as exc:
            return ExitCode(310, message=f'{CRYSTAL_FIELD_FILE} reading failed with: {exc}')
    else:
        return ExitCode(300, message=f'{CRYSTAL_FIELD_FILE} file not in the retrieved files')

    if CRYSTAL_FIELD_FILE in cf_pot_folder.list_object_names():
        try:
            with cf_pot_folder.open(CRYSTAL_FIELD_FILE, 'rb') as f:
                with h5py.File(f, 'r') as cffile:
                    cfcalc.read_potential(cffile, **kwargs)
        except ValueError as exc:
            return ExitCode(310, message=f'{CRYSTAL_FIELD_FILE} reading failed with: {exc}')
    else:
        return ExitCode(300, message=f'{CRYSTAL_FIELD_FILE} file not in the retrieved files')

    try:
        coefficients = cfcalc.get_coefficients(convention='Stevens' if convert else 'Wybourne')
    except ValueError as exc:
        return ExitCode(320, message=f'Crystal field calculation failed with: {exc}')
    if len(coefficients) == 0:
        return ExitCode(320, message='Crystal field calculation failed with: No Coefficients produced')

    return cfcalc, coefficients
