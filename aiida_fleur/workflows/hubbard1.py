# -*- coding: utf-8 -*-
"""
This module contains the FleurHubbard1WorkChain, which is used to perform
a complete hubbard 1 calculation including calculating model parameters beforehand
"""
from collections import defaultdict

from aiida.common import AttributeDict
from aiida.engine import WorkChain, ToContext, if_
from aiida import orm

from aiida_fleur.workflows.scf import FleurScfWorkChain
from .cfcoeff import FleurCFCoeffWorkChain


class FleurHubbard1WorkChain(WorkChain):
    """
    WorkChain for performing Hubbard-1 calculations
    """

    _workflow_version = '0.0.1'

    _default_wf_para = {
        'ldahia_dict': None,
        'soc': 'auto',
        'exchange_constants': None,
        'cf_coefficients': None,
        'occupation_converged': 0.01,
        'matrix_elements_converged': 0.001,
        'itmax_hubbard1': 5,
        'energy_contours': {
            'shape': 'semircircle',
            'eb': -1.0,
            'n': 128
        },
        'energy_grid': {
            'ellow': -1.0,
            'elup': 1.0,
            'n': 5400
        },
        'inpxml_changes': [],
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurCFCoeffWorkChain,
                           namespace='cfcoeff',
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           })
        spec.expose_inputs(FleurScfWorkChain, namespace='hubbard1_scf', namespace_options={
            'required': True,
        })
        spec.input('wf_parameters', valid_type=orm.Dict, required=False)

        spec.outline(
            cls.start, cls.validate_inputs,
            if_(cls.preliminary_calcs_needed)(cls.run_preliminary_calculations, cls.inspect_preliminary_calculations),
            cls.run_hubbard1_calculation, cls.inspect_hubbard1_calculation, cls.return_results)

        spec.output('output_hubbard1_wc_para', valid_type=orm.Dict)
        spec.expose_outputs(FleurScfWorkChain, namespace='scf')

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(377, 'ERROR_CFCOEFF_CALCULATION_FAILED', message='Crystal field coefficient calculation failed')
        spec.exit_code(378, 'ERROR_HUBBARD1_CALCULATION_FAILED', message='Hubbard 1 calculation failed')

    def start(self):
        """
        init context and some parameters
        """
        self.report(f'INFO: started hubbard1 workflow version {self._workflowversion}')

        self.ctx.run_preliminary = False
        self.ctx.fleurinp_hubbard1 = None

        wf_default = self._default_wf_para
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

    def validate_inputs(self):
        """
        Validate the input configuration
        """

        extra_keys = {key for key in self.ctx.wf_dict if key not in self._default_wf_para}
        if extra_keys:
            error = f'ERROR: input wf_parameters for Orbcontrol contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        inputs = self.inputs
        if 'cfcoeff' in inputs:
            self.ctx.run_preliminary = True
            if self.ctx.wf_dict['cf_coefficients'] is not None:
                error = 'ERROR: you gave cfcoeff input + explicit cf_coefficients in wf_parameters'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

    def preliminary_calcs_needed(self):
        """
        Return whether calculations need to be run before the hubbard 1 calculation
        """
        return self.ctx.run_prelimiary

    def run_preliminary_calculations(self):
        """
        Run calculations needed before hubbard 1
        """

        self.report('INFO: Starting Preliminary calculations')

        calcs = {}
        if 'cfcoeff' in self.inputs:
            self.report('INFO: Starting Crystal field calculation')

            inputs = AttributeDict(self.exposed_inputs(FleurCFCoeffWorkChain, namespace='cfcoeff'))
            calcs['cfcoeff'] = self.submit(FleurCFCoeffWorkChain, **inputs)

        return ToContext(**calcs)

    def inspect_preliminary_calculations(self):
        """
        Check that the preliminary calculations finished sucessfully
        """
        if not self.ctx.cfcoeff.is_finished_ok:
            error = ('ERROR: CFCoeff workflow was not successful')
            self.report(error)
            return self.exit_codes.ERROR_CFCOEFF_CALCULATION_FAILED

        try:
            self.ctx.cfcoeff.outputs.output_cfcoeff_wc_para
        except KeyError:
            message = ('ERROR: CFCoeff workflow failed, no output node')
            self.ctx.errors.append(message)
            return self.exit_codes.ERROR_CFCOEFF_CALCULATION_FAILED

    def create_hubbard1_input(self):
        """
        Create the inpxml_changes input to create the hubbard 1 input
        """
        inputs_hubbard1 = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if 'wf_parameters' in inputs_hubbard1:
            scf_wf_para = inputs_hubbard1.wf_parameters.get_dict()
        else:
            scf_wf_para = {}

        fchanges = self.ctx.wf_dict.get('inpxml_changes', [])
        scf_wf_para.setdefault('inpxml_changes', []).extend(fchanges)

        scf_wf_para['inpxml_changes'].append(('set_inpchanges', {
            'change_dict': {
                'minoccdistance': self.ctx.wf_dict['occupation_converged'],
                'minmatdistance': self.ctx.wf_dict['matrix_elements_converged'],
                'itmaxhubbard1': self.ctx.wf_dict['itmax_hubbard1']
            }
        }))

        scf_wf_para['inpxml_changes'].append(('set_simple_tag', {
            'tag_name': 'realAxis',
            'changes': self.ctx.wf_dict['energy_grid'],
            'create_parents': True
        }))

        complex_contours = self.ctx.wf_dict['energy_contours']
        if not isinstance(complex_contours, list):
            complex_contours = [complex_contours]

        #Build the list of changes (we need to provide them in one go to not override each other)
        contour_tags = defaultdict(list)
        for contour in complex_contours:
            shape = contour.pop('shape')

            if shape.lower() == 'semircircle':
                contour_tags['contourSemicircle'].append(contour)
            elif shape.lower() == 'dos':
                contour_tags['contourDOS'].append(contour)
            elif shape.lower() == 'rectangle':
                contour_tags['contourRectangle'].append(contour)

        scf_wf_para['inpxml_changes'].append(('set_complex_tag', {
            'tag_name': 'greensFunction',
            'changes': dict(contour_tags)
        }))

        if 'cfcoeff' in self.ctx:
            #Take the output crystal field cofficients from the CFCoeffWorkchain
            #TODO: Select spin channel
            cf_coefficients = self.ctx.cfcoeff.outputs.output_cfcoeff_wc_para.dict.cf_coefficients_up
            #Drop coefficients with negative m
            cf_coefficients = {key: coeff for key, coeff in cf_coefficients.items() if '-' in key}
        else:
            cf_coefficients = self.ctx.wf_dict.get('cf_coefficients', {})

        coefficient_tags = []
        for key, coeff in cf_coefficients.items():
            l, m = key.split('/')
            coefficient_tags.append({'l': l, 'm': m, 'value': coeff})

        exc_constant_tags = []
        exc_constant = self.ctx.wf_dict.get('exchange_constant', {})
        for l, exc_dict in exc_constant.items():
            exc_constant_tags.append({'l': l, **exc_dict})

        for species_name, ldahia_dict in self.ctx.wf_dict['ldahia_dict'].items():
            if coefficient_tags:
                ldahia_dict = {**ldahia_dict, 'cfCoeff': coefficient_tags}

            if exc_constant_tags:
                ldahia_dict = {**ldahia_dict, 'exc': exc_constant_tags}

            if self.ctx.wf_dict['soc'] != 'auto':
                ldahia_dict = {**ldahia_dict, 'addarg': {'key': 'xiSOC', 'value': self.ctx.wf_dict['soc']}}

            scf_wf_para['inpxml_changes'].append(('set_species', {'species_name': species_name, 'ldahia': ldahia_dict}))

        inputs_hubbard1.wf_parameters = orm.Dict(dict=scf_wf_para)

        return inputs_hubbard1

    def run_hubbard1_calculation(self):
        """
        Start the Hubbard1 calculation by submitting the SCF workchain with the correct inputs
        """
        self.report('INFO: Starting Hubbard 1 calculation')

        inputs = self.create_hubbard1_input()
        result = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(hubbard1=result)

    def inspect_hubbard1_calculation(self):
        """
        Inspect the finished Hubbard 1 calculation
        """
        if not self.ctx.hubbard1.is_finished_ok:
            error = ('ERROR: Hubbard1 SCF workflow was not successful')
            self.report(error)
            return self.exit_codes.ERROR_HUBBARD1_CALCULATION_FAILED

        try:
            self.ctx.hubbard1.outputs.output_scf_wc_para
        except KeyError:
            message = ('ERROR: Hubbard1 SCF workflow failed, no output node')
            self.ctx.errors.append(message)
            return self.exit_codes.ERROR_HUBBARD1_CALCULATION_FAILED

    def return_results(self):
        pass
