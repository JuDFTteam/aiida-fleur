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
Workflow for calculating Green's functions
"""

import copy
from collections import defaultdict

from lxml import etree

from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida import orm
from aiida.orm import Code, load_node, CalcJobNode
from aiida.orm import RemoteData, Dict, FolderData
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data


class FleurGreensfWorkChain(WorkChain):
    """
    Workflow for calculating Green's functions
    """

    _workflowversion = '0.1.0'

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 2 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }

    _default_wf_para = {
        'contours': {
            'shape': 'semircircle',
            'eb': -1.0,
            'n': 128
        },
        'grid': {
            'ellow': -1.0,
            'elup': 1.0,
            'n': 5400
        },
        'calculations': None,
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'inpxml_changes': [],
    }

    @classmethod
    def define(cls, spec):

        spec.expose_inputs(
            FleurScfWorkChain,
            namespace='scf',
            namespace_options={
                'required':
                False,
                'popuplate_defaults':
                False,
                'help':
                "Inputs for an SCF workchain to run before calculating Green's functions. If not specified the SCF workchain is not run"
            })
        spec.expose_inputs(
            FleurOrbControlWorkChain,
            namespace='orbcontrol',
            namespace_options={
                'required':
                False,
                'popuplate_defaults':
                False,
                'help':
                "Inputs for an Orbital occupation control workchain to run before calculating Green's functions. If not specified the Orbcontrol workchain is not run"
            })
        spec.input('remote',
                   valid_type=RemoteData,
                   required=False,
                   help='Remote Folder data to start the calculation from')
        spec.input('fleurinp',
                   valid_type=FleurinpData,
                   required=False,
                   help='Fleurinpdata to start the calculation from')
        spec.input('fleur',
                   valid_type=Code,
                   required=True,
                   help="Fleur code to use for the Green's function calculation")
        spec.input('wf_parameters',
                   valid_type=Dict,
                   required=False,
                   help="Parameters to control the calculation of Green's functions")
        spec.input('options',
                   valid_type=Dict,
                   required=False,
                   help="Submission options for the Green's function calculation")
        spec.input('settings',
                   valid_type=Dict,
                   required=False,
                   help="Additional settings for the Green's function calculation")

        spec.outline(cls.start,
                     if_(cls.scf_needed)(
                         cls.converge_scf,
                         cls.greensf_after_scf,
                     ).else_(
                         cls.greensf_wo_scf,
                     ), cls.return_results)

        spec.output('output_greensf_wc_para', valid_type=Dict)
        spec.output('last_calc_retrieved', valid_type=FolderData)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Input codes do not correspond to fleur or inpgen respectively.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(342, 'ERROR_GREENSF_CALC_FAILED', message="Green's function calculation failed.")
        spec.exit_code(450, 'ERROR_SCF_FAILED', message='SCF Convergence workflow failed.')
        spec.exit_code(451, 'ERROR_ORBCONTROL_FAILED', message='Orbital occupation control workflow failed.')

    def start(self):
        """
        Intitialize context and defaults
        """
        self.ctx.scf_needed = False
        self.ctx.fleurinp_greensf = None

        inputs = self.inputs

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in inputs:
            wf_dict = inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # initialize the dictionary using defaults if no options are given
        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        complex_contours = wf_dict['contour']
        if isinstance(complex_contours, list):
            if any('label' not in contour for contour in complex_contours):
                error = ('ERROR: Provided multiple contours without labels. Please provide labels for these contours')
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM
        else:
            complex_contours = [complex_contours]

        for contour in complex_contours:
            if 'shape' not in contour:
                error = ('ERROR: Provided contours without specifying shape')
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

            if contour['shape'].lower() not in (
                    'semircircle',
                    'dos',
                    'rectangle',
            ):
                error = (f"ERROR: Provided invalid shape for contour: {contour['shape'].lower()}",
                         "Valid are: 'semircircle', 'dos' and 'rectangle' (case-insensitive)")
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        try:
            test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
        except ValueError:
            error = ('The code you provided for FLEUR does not use the plugin fleur.fleur')
            return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

    def scf_needed(self):
        """
        Return whether a SCF or Orbcontrol workchain needs to be run beforehand
        """
        return self.ctx.scf_needed

    def converge_scf(self):
        """
        Run either the specified SCF or orbcontrol Workchain
        """
        self.report('INFO: Starting SCF calculations')
        calcs = {}
        if 'scf' in self.inputs:
            inputs = self.get_inputs_scf()
            result_scf = self.submit(FleurScfWorkChain, **inputs)
            calcs['scf'] = result_scf
        elif 'orbcontrol' in self.inputs:
            inputs = self.get_inputs_orbcontrol()
            result_orbcontrol = self.submit(FleurOrbControlWorkChain, **inputs)
            calcs['orbcontrol'] = result_orbcontrol

        return ToContext(**calcs)

    def get_inputs_scf(self):
        """
        Get inputs for the SCF workchain
        """
        return AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

    def get_inputs_orbcontrol(self):
        """
        Get inputs for the OrbControl workchain
        """
        return AttributeDict(self.exposed_inputs(FleurOrbControlWorkChain, namespace='orbcontrol'))

    def greensf_after_scf(self):
        """
        Submit greens function calculation without previous scf
        """

        self.report("INFO: run Green's function calculations after SCF/OrbControl")

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp_greensf
        if fleurin is None:
            error = ('ERROR: Creating BandDOS Fleurinp failed for an unknown reason')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        inputs = self.inputs
        if 'remote' in inputs:
            remote_data = inputs.remote
        else:
            remote_data = None

        if 'settings' in inputs:
            settings = inputs.settings
        else:
            settings = None

        label = "Green's function calculation"
        description = "Fleur Green's function calculation without previous SCF calculation"

        input_fixed = get_inputs_fleur(inputs.fleur,
                                       remote_data,
                                       fleurin,
                                       self.ctx.options,
                                       label,
                                       description,
                                       settings=settings)

        result_greensf = self.submit(FleurBaseWorkChain, **input_fixed)
        return ToContext(greensf=result_greensf)

    def greensf_wo_scf(self):
        """
        Submit greens function calculation without previous scf
        """

        self.report("INFO: run Green's function calculations")

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp_greensf
        if fleurin is None:
            error = ('ERROR: Creating BandDOS Fleurinp failed for an unknown reason')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        if 'scf' in self.inputs:
            try:
                remote_data = orm.load_node(
                    self.ctx.scf.outputs.output_scf_wc_para['last_calc_uuid']).outputs.remote_folder
            except NotExistent:
                error = 'Remote generated in the SCF calculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_SCF_CALCULATION_FAILED
        else:
            try:
                gs_scf_para = self.ctx.rare_earth_orbcontrol.outputs.output_orbcontrol_wc_gs_scf
                remote_data = orm.load_node(gs_scf_para['last_calc_uuid']).outputs.remote_folder
            except NotExistent:
                error = 'Fleurinp generated in the Orbcontrol calculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_ORBCONTROL_CALCULATION_FAILED

        inputs = self.inputs
        if 'settings' in inputs:
            settings = inputs.settings
        else:
            settings = None

        label = "Green's function calculation"
        description = "Fleur Green's function calculation without previous SCF calculation"

        input_fixed = get_inputs_fleur(inputs.fleur,
                                       remote_data,
                                       fleurin,
                                       self.ctx.options,
                                       label,
                                       description,
                                       settings=settings)

        result_greensf = self.submit(FleurBaseWorkChain, **input_fixed)
        return ToContext(greensf=result_greensf)

    def change_fleurinp(self):
        """
        Create FleurinpData for the Green's function calculation
        """

        wf_dict = self.ctx.wf_dict

        if self.ctx.scf_needed:
            if 'scf' in self.inputs:
                try:
                    fleurin = self.ctx.scf.outputs.fleurinp
                except NotExistent:
                    error = 'Fleurinp generated in the SCF calculation is not found.'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_SCF_CALCULATION_FAILED
            else:
                try:
                    fleurin = self.ctx.orbcontrol.outputs.output_orbcontrol_wc_gs_fleurinp
                except NotExistent:
                    error = 'Fleurinp generated in the Orbcontrol calculation is not found.'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_ORBCONTROL_CALCULATION_FAILED
        else:
            if 'fleurinp' not in self.inputs:
                fleurin = get_fleurinp_from_remote_data(self.inputs.remote)
            else:
                fleurin = self.inputs.fleurinp

        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        fleurmode = FleurinpModifier(fleurin)

        fleurmode.set_inpchanges({'itmax': 1})
        fleurmode.set_simple_tag('realAxis', wf_dict['grid'], create_parents=True)

        complex_contours = wf_dict['contour']
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

        fleurmode.set_complex_tag('greensFunction', dict(contour_tags))

        calc_tags = defaultdict(defaultdict(list))
        for species_name, calc in wf_dict['calculations'].items():

            torque_calc = calc.pop('torque', False)

            if torque_calc:
                if tuple(fleurin.inp_version.split('.')) >= (0, 35):
                    calc_tags[species_name]['torqueCalculation'].append(calc)
                else:
                    calc_tags[species_name]['torgueCalculation'].append(calc)
            else:
                calc_tags[species_name]['greensfCalculation'].append(calc)

        calc_tags = dict(calc_tags)
        for species_name, species_tags in calc_tags.items():
            if 'torqueCalculation' in species_tags:
                species_tags['torqueCalculation'] = species_tags['torqueCalculation'][0]
            if 'torgueCalculation' in species_tags:
                species_tags['torgueCalculation'] = species_tags['torgueCalculation'][0]

            fleurmode.set_species(species_name, species_tags)

        fchanges = wf_dict.get('inpxml_changes', [])
        # apply further user dependend changes
        if fchanges:
            try:
                fleurmode.add_task_list(fchanges)
            except (ValueError, TypeError) as exc:
                error = ('ERROR: Changing the inp.xml file failed. Tried to apply inpxml_changes'
                         f', which failed with {exc}. I abort, good luck next time!')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        try:
            fleurmode.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, user wanted inp.xml changes could not be applied.'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        self.ctx.fleurinp_greensf = fleurmode.freeze()

    def return_results(self):
        pass

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()
