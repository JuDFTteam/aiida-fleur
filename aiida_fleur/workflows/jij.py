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
Workflow for the calculation of the Jij tensor from ``greensf.hdf`` files.
"""
from __future__ import annotations

import copy
import io
import json

from lxml import etree
import numpy as np
import pandas as pd

from aiida import orm
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent
from aiida.engine import ExitCode, WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf

from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, test_and_get_codenode
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.workflows.scf import FleurScfWorkChain

from masci_tools.tools.greensf_calculations import calculate_heisenberg_tensor, decompose_jij_tensor


class FleurJijWorkChain(WorkChain):
    """
    Calculate the full Jij tensor from three SOC Green's-function calculations
    with the magnetization along z, x and y.
    """

    _workflowversion = '0.1.0'
    _directions = ('z', 'x', 'y')

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
        'reference_atom': 1,
        'onsite_delta': [],
        'max_shells': None,
        'use_soc_reference': False,
        'sqa_ref': [0.0, 0.0],
        'soc_angles': [0.0, 0.0],
        'greensf_use_soc': False,
        'xc_functional': 'vwn',
        'sqas': {
            'z': [0.0, 0.0],
            'x': [1.57079, 0.0],
            'y': [1.57079, 1.57079],
        },
        'greensf_real_axis': {
            'ne': 5400,
            'ellow': -1.0,
            'elup': 1.0,
        },
        'greensf_contour': {
            'n': 128,
            'eb': -1.0,
            'et': 0.0,
            'alpha': 1.0,
        },
        'greensf_energy_parameters': None,
        'greensf_diag_elements': {
            's': 'F',
            'p': 'F',
            'd': 'T',
            'f': 'F'
        },
        'greensf_nshells': 2,
        'greensf_kkintgrCutoff': 'calc',
        'greensf_label': 'default',
        'soc_off': [],
        'add_comp_para': {
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
        spec.input('wf_parameters', valid_type=orm.Dict, required=False)
        spec.input('fleur', valid_type=orm.Code, required=False)
        spec.input('remote', valid_type=orm.RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('options', valid_type=orm.Dict, required=False)
        spec.input('greensf_z', valid_type=orm.SinglefileData, required=False)
        spec.input('greensf_x', valid_type=orm.SinglefileData, required=False)
        spec.input('greensf_y', valid_type=orm.SinglefileData, required=False)

        spec.outline(cls.start,
                     if_(cls.postprocess_only)(cls.collect_tensors_from_files).else_(
                         if_(cls.scf_needed)(cls.converge_scf, cls.submit_greens_calculations).else_(
                             cls.submit_greens_calculations), cls.collect_tensors), cls.return_results)

        spec.output('output_jij_wc_para', valid_type=orm.Dict)
        spec.output('jij_tensor_z', valid_type=orm.Dict)
        spec.output('jij_tensor_x', valid_type=orm.Dict)
        spec.output('jij_tensor_y', valid_type=orm.Dict)
        spec.output('jij_tensor_z_file', valid_type=orm.SinglefileData)
        spec.output('jij_tensor_x_file', valid_type=orm.SinglefileData)
        spec.output('jij_tensor_y_file', valid_type=orm.SinglefileData)
        spec.output('full_jij_tensor', valid_type=orm.Dict)
        spec.output('full_jij_tensor_file', valid_type=orm.SinglefileData)
        spec.output('jij_interactions', valid_type=orm.Dict)
        spec.output('jij_interactions_file', valid_type=orm.SinglefileData)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(334, 'ERROR_REFERENCE_CALCULATION_FAILED', message='Reference calculation failed.')
        spec.exit_code(335,
                       'ERROR_REFERENCE_CALCULATION_NOREMOTE',
                       message='Found no reference calculation remote repository.')
        spec.exit_code(336, 'ERROR_GREENSF_CALCULATION_FAILED', message='Green function calculation failed.')
        spec.exit_code(337, 'ERROR_POSTPROCESSING_FAILED', message='Postprocessing of greensf.hdf failed.')

    def start(self):
        """
        Retrieve and initialize the parameters of the workchain.
        """
        self.report(f'INFO: started Jij calculation workflow version {self._workflowversion}')

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.tensor_outputs = {}
        self.ctx.combined_outputs = {}
        self.ctx.postprocess_only = False

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = []
        for key in wf_dict.keys():
            if key not in wf_default.keys():
                extra_keys.append(key)
        if extra_keys:
            error = f'ERROR: input wf_parameters for Jij contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        for key, val in wf_default.items():
            if isinstance(val, dict):
                wf_dict[key] = {**val, **wf_dict.get(key, {})}
            else:
                wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        if not self.ctx.wf_dict['onsite_delta']:
            error = 'ERROR: wf_parameters.onsite_delta has to be provided for a meaningful Jij calculation.'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if sorted(self.ctx.wf_dict['sqas'].keys()) != ['x', 'y', 'z']:
            error = "ERROR: wf_parameters.sqas has to contain exactly the keys 'x', 'y' and 'z'."
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        greensf_inputs = [name for name in ('greensf_z', 'greensf_x', 'greensf_y') if name in self.inputs]
        if greensf_inputs:
            missing = [name for name in ('greensf_z', 'greensf_x', 'greensf_y') if name not in self.inputs]
            if missing:
                error = ('ERROR: postprocessing-only mode requires all three greensf inputs: '
                         "greensf_z, greensf_x and greensf_y.")
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

            self.ctx.postprocess_only = True

            for invalid in ('scf', 'remote', 'fleurinp'):
                if invalid in self.inputs:
                    error = f'ERROR: you gave {invalid} together with explicit greensf files for postprocessing only'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        if 'fleur' in self.inputs and not self.ctx.postprocess_only:
            try:
                test_and_get_codenode(self.inputs.fleur, 'fleur.fleur')
            except ValueError:
                error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED
        elif not self.ctx.postprocess_only:
            error = 'ERROR: no Fleur code was provided'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        if self.ctx.postprocess_only:
            self.ctx.scf_needed = False
        elif 'scf' in self.inputs:
            self.ctx.scf_needed = True
            if 'remote' in self.inputs:
                error = 'ERROR: you gave SCF input + remote for the Jij workflow'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in self.inputs:
                error = 'ERROR: you gave SCF input + fleurinp for the Jij workflow'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote' not in self.inputs:
            error = 'ERROR: you gave neither SCF input nor remote for the Jij workflow'
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            self.ctx.scf_needed = False

    def postprocess_only(self):
        """
        Returns True if only postprocessing of existing greensf files is requested.
        """
        return self.ctx.postprocess_only

    def scf_needed(self):
        """
        Returns True if SCF WC is needed.
        """
        return self.ctx.scf_needed

    def converge_scf(self):
        """
        Converge charge density for the reference system.
        """
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(reference=res)

    def get_inputs_scf(self):
        """
        Initialize inputs for the SCF cycle.
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        fleurmode = FleurinpModifier(input_scf.fleurinp) if 'fleurinp' in input_scf else None
        if self.ctx.wf_dict.get('use_soc_reference') and fleurmode is not None:
            soc = self.ctx.wf_dict.get('sqa_ref')
            fleurmode.set_xcfunctional(self.ctx.wf_dict['xc_functional'])
            fleurmode.set_inpchanges({
                'theta': soc[0],
                'phi': soc[1],
                'l_soc': True
            },
                                      path_spec={
                                          'phi': {
                                              'contains': 'soc'
                                          },
                                          'theta': {
                                              'contains': 'soc'
                                          }
                                      })
            input_scf.fleurinp = fleurmode.freeze()
        elif fleurmode is not None:
            fleurmode.set_xcfunctional(self.ctx.wf_dict['xc_functional'])
            fleurmode.set_inpchanges({'l_soc': False})
            input_scf.fleurinp = fleurmode.freeze()

        if 'structure' in input_scf:
            if 'calc_parameters' in input_scf:
                calc_parameters = input_scf.calc_parameters.get_dict()
            else:
                calc_parameters = {}
            if self.ctx.wf_dict.get('use_soc_reference'):
                soc = self.ctx.wf_dict.get('sqa_ref')
                calc_parameters['soc'] = {'theta': soc[0], 'phi': soc[1]}
            elif 'soc' in calc_parameters:
                del calc_parameters['soc']
            input_scf.calc_parameters = orm.Dict(calc_parameters)

        return input_scf

    def submit_greens_calculations(self):
        """
        Submit the three single-iteration Green's-function calculations.
        """
        if self.ctx.scf_needed:
            if not self.ctx.reference.is_finished_ok:
                message = 'The reference SCF calculation was not successful.'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

            try:
                self.ctx.reference.outputs.output_scf_wc_para
            except NotExistent:
                message = 'The reference SCF calculation failed, no scf output node.'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        try:
            remote = self.get_reference_remote()
        except NotExistent:
            message = 'Found no remote folder for the reference calculation.'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_NOREMOTE

        try:
            fleurin = self.get_reference_fleurinp()
        except NotExistent:
            message = 'Fleurinp for the reference calculation was not found.'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_REFERENCE_CALCULATION_FAILED

        settings = {'remove_from_remotecopy_list': ['mixing_history*']}
        futures = {}

        for direction in self._directions:
            modified_fleurinp = self.change_fleurinp(fleurin, direction)
            if isinstance(modified_fleurinp, ExitCode):
                return modified_fleurinp

            label = f'Jij_greensf_{direction}'
            description = f'Single-iteration Green function calculation for Jij with the moment along {direction}.'

            inputs_builder = get_inputs_fleur(self.inputs.fleur,
                                              remote,
                                              modified_fleurinp,
                                              self.ctx.options.copy(),
                                              label,
                                              description,
                                              settings,
                                              add_comp_para=self.ctx.wf_dict['add_comp_para'])
            futures[f'greens_{direction}'] = self.submit(FleurBaseWorkChain, **inputs_builder)

        return ToContext(**futures)

    def get_reference_fleurinp(self):
        """
        Return the fleurinp node used as the basis for the Green's-function calculations.
        """
        if self.ctx.scf_needed:
            return self.ctx.reference.outputs.fleurinp
        if 'fleurinp' in self.inputs:
            return self.inputs.fleurinp
        return get_fleurinp_from_remote_data(self.inputs.remote)

    def get_reference_remote(self):
        """
        Return the remote folder used as parent for the Green's-function calculations.
        """
        if self.ctx.scf_needed:
            return self.ctx.reference.outputs.last_calc.remote_folder
        return self.inputs.remote

    def change_fleurinp(self, fleurin, direction):
        """
        Create a modified fleurinp for the selected spin direction.
        """
        alpha, beta = self.ctx.wf_dict['sqas'][direction]
        soc_theta, soc_phi = self.ctx.wf_dict['soc_angles']
        fleurmode = FleurinpModifier(fleurin)

        fleurmode.set_xcfunctional(self.ctx.wf_dict['xc_functional'])

        # First define the global Green's-function contour block
        fleurmode.set_complex_tag('greensFunction',
                                  changes={
                                      'realAxis': self.ctx.wf_dict['greensf_real_axis'],
                                      'contourSemicircle': self.ctx.wf_dict['greensf_contour']
                                  },
                                  create=True)
        fleurmode.set_inpchanges({
            'itmax': 1,
            'l_noco': True,
            'l_ss': False,
            'l_soc': self.ctx.wf_dict['greensf_use_soc'],
            'ctail': False,
            'theta': soc_theta,
            'phi': soc_phi
        },
                                  path_spec={
                                      'phi': {
                                          'contains': 'soc'
                                      },
                                      'theta': {
                                          'contains': 'soc'
                                      }
                                  })

        # Then define the magnetic direction on the atom group
        fleurmode.set_atomgroup({
            'nocoParams': {
                'alpha': alpha,
                'beta': beta
            }
        },
                             species='all',
                             create=True)

        if self.ctx.wf_dict['greensf_energy_parameters'] is not None:
            fleurmode.set_species('all', {
                'energyParameters': self.ctx.wf_dict['greensf_energy_parameters']
            },
                                  create=True)

        # Finally request the actual Green's-function matrix elements on the species
        fleurmode.set_species('all', {
            'greensfCalculation': {
                'l_sphavg': True,
                'nshells': self.ctx.wf_dict['greensf_nshells'],
                'kkintgrCutoff': self.ctx.wf_dict['greensf_kkintgrCutoff'],
                'label': self.ctx.wf_dict['greensf_label'],
                'diagElements': self.ctx.wf_dict['greensf_diag_elements']
            }
        },
                              create=True)
        fleurmode.set_attrib_value('l_mperp', True, tag_name='mtNocoParams')
        fleurmode.set_attrib_value('l_mperp', True, tag_name='greensFunction')
        fleurmode.set_attrib_value('outputSphavg', True, tag_name='greensFunction')

        for atom_label in self.ctx.wf_dict['soc_off']:
            fleurmode.set_species(atom_label, {'special': {'socscale': 0}}, create=True)

        try:
            fleurmode.add_task_list(self.ctx.wf_dict['inpxml_changes'])
        except (ValueError, TypeError) as exc:
            error = ('ERROR: Changing the inp.xml file failed. Tried to apply inpxml_changes'
                     f', which failed with {exc}. I abort, good luck next time!')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        try:
            fleurmode.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = 'ERROR: input, user wanted inp.xml changes did not validate'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, user wanted inp.xml changes could not be applied.'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        return fleurmode.freeze()

    def collect_tensors(self):
        """
        Postprocess all ``greensf.hdf`` files into tensor output nodes.
        """
        for direction in self._directions:
            calculation = self.ctx[f'greens_{direction}']
            if not calculation.is_finished_ok:
                message = ('ERROR: Green function Fleur calculation '
                           f'for {direction} failed with exit status {calculation.exit_status}')
                self.control_end_wc(message)
                return self.exit_codes.ERROR_GREENSF_CALCULATION_FAILED

            try:
                tensor_outputs = extract_jij_tensor_data(
                    calculation.outputs.retrieved,
                    orm.Dict(
                        dict={
                            'reference_atom': self.ctx.wf_dict['reference_atom'],
                            'onsite_delta': self.ctx.wf_dict['onsite_delta'],
                            'moment_direction': direction,
                            'max_shells': self.ctx.wf_dict['max_shells'],
                        }))
            except Exception as exc:  #pylint: disable=broad-except
                message = f'ERROR: Postprocessing greensf.hdf for {direction} failed: {exc}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_POSTPROCESSING_FAILED
            if isinstance(tensor_outputs, ExitCode):
                message = f'ERROR: Postprocessing greensf.hdf for {direction} failed: {tensor_outputs.message}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_POSTPROCESSING_FAILED

            try:
                self.ctx.tensor_outputs[direction] = self._normalize_tensor_outputs(tensor_outputs)
            except KeyError as exc:
                message = f'ERROR: Could not normalize tensor outputs for {direction}: {exc}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_POSTPROCESSING_FAILED

        combine_outputs = combine_full_jij_tensor(
            self.ctx.tensor_outputs['x']['jij_tensor_data'], self.ctx.tensor_outputs['y']['jij_tensor_data'],
            self.ctx.tensor_outputs['z']['jij_tensor_data'])
        try:
            self.ctx.combined_outputs = self._normalize_combined_outputs(combine_outputs)
        except KeyError as exc:
            message = f'ERROR: Could not normalize combined tensor outputs: {exc}'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_POSTPROCESSING_FAILED

    def collect_tensors_from_files(self):
        """
        Postprocess explicitly provided greensf files into tensor output nodes.
        """
        for direction in self._directions:
            try:
                tensor_outputs = extract_jij_tensor_data_from_singlefile(
                    self.inputs[f'greensf_{direction}'],
                    orm.Dict(
                        dict={
                            'reference_atom': self.ctx.wf_dict['reference_atom'],
                            'onsite_delta': self.ctx.wf_dict['onsite_delta'],
                            'moment_direction': direction,
                            'max_shells': self.ctx.wf_dict['max_shells'],
                        }))
            except Exception as exc:  #pylint: disable=broad-except
                message = f'ERROR: Postprocessing provided greensf file for {direction} failed: {exc}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_POSTPROCESSING_FAILED
            if isinstance(tensor_outputs, ExitCode):
                message = f'ERROR: Postprocessing provided greensf file for {direction} failed: {tensor_outputs.message}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_POSTPROCESSING_FAILED

            try:
                self.ctx.tensor_outputs[direction] = self._normalize_tensor_outputs(tensor_outputs)
            except KeyError as exc:
                message = f'ERROR: Could not normalize provided tensor outputs for {direction}: {exc}'
                self.control_end_wc(message)
                return self.exit_codes.ERROR_POSTPROCESSING_FAILED

        combine_outputs = combine_full_jij_tensor(
            self.ctx.tensor_outputs['x']['jij_tensor_data'], self.ctx.tensor_outputs['y']['jij_tensor_data'],
            self.ctx.tensor_outputs['z']['jij_tensor_data'])
        try:
            self.ctx.combined_outputs = self._normalize_combined_outputs(combine_outputs)
        except KeyError as exc:
            message = f'ERROR: Could not normalize combined tensor outputs: {exc}'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_POSTPROCESSING_FAILED

    @staticmethod
    def _normalize_tensor_outputs(tensor_outputs):
        """
        Normalize calcfunction outputs into a stable mapping with the expected keys.
        """
        if isinstance(tensor_outputs, dict):
            data_node = tensor_outputs.get('jij_tensor_data')
            file_node = tensor_outputs.get('jij_tensor_file')
        else:
            try:
                data_node = tensor_outputs['jij_tensor_data']
                file_node = tensor_outputs['jij_tensor_file']
            except (TypeError, KeyError):
                data_node = getattr(tensor_outputs, 'jij_tensor_data', None)
                file_node = getattr(tensor_outputs, 'jij_tensor_file', None)

        if data_node is None or file_node is None:
            raise KeyError(f'expected jij_tensor_data/jij_tensor_file, got {tensor_outputs}')

        return {'jij_tensor_data': data_node, 'jij_tensor_file': file_node}

    @staticmethod
    def _normalize_combined_outputs(combined_outputs):
        """
        Normalize the merged full-tensor/interactions calcfunction outputs.
        """
        expected = ('full_jij_tensor', 'full_jij_tensor_file', 'jij_interactions', 'jij_interactions_file')
        if isinstance(combined_outputs, dict):
            normalized = {key: combined_outputs.get(key) for key in expected}
        else:
            normalized = {}
            for key in expected:
                try:
                    normalized[key] = combined_outputs[key]
                except (TypeError, KeyError):
                    normalized[key] = getattr(combined_outputs, key, None)

        missing = [key for key, val in normalized.items() if val is None]
        if missing:
            raise KeyError(f'missing keys in combined outputs: {missing}')

        return normalized

    def return_results(self):
        """
        Output results of the workchain.
        """
        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'reference_atom': self.ctx.wf_dict['reference_atom'],
            'max_shells': self.ctx.wf_dict['max_shells'],
            'is_scf_needed': self.ctx.scf_needed,
            'postprocess_only': self.ctx.postprocess_only,
            'directions': list(self._directions),
            'tensor_node_uuids': {
                direction: self.ctx.tensor_outputs[direction]['jij_tensor_data'].uuid
                for direction in self.ctx.tensor_outputs
            },
            'tensor_file_uuids': {
                direction: self.ctx.tensor_outputs[direction]['jij_tensor_file'].uuid
                for direction in self.ctx.tensor_outputs
            },
            'full_tensor_uuid': self.ctx.combined_outputs['full_jij_tensor'].uuid,
            'full_tensor_file_uuid': self.ctx.combined_outputs['full_jij_tensor_file'].uuid,
            'interactions_uuid': self.ctx.combined_outputs['jij_interactions'].uuid,
            'interactions_file_uuid': self.ctx.combined_outputs['jij_interactions_file'].uuid,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
        }
        if not self.ctx.postprocess_only:
            out['greensf_calculation_uuids'] = {
                direction: self.ctx[f'greens_{direction}'].uuid
                for direction in self._directions if f'greens_{direction}' in self.ctx
            }
        else:
            out['greensf_file_uuids'] = {
                direction: self.inputs[f'greensf_{direction}'].uuid
                for direction in self._directions
            }

        out_nodes = save_jij_output_node(out=orm.Dict(out))
        self.out('output_jij_wc_para', out_nodes['output_jij_wc_para'])

        for direction in self._directions:
            if direction not in self.ctx.tensor_outputs:
                continue
            self.out(f'jij_tensor_{direction}', self.ctx.tensor_outputs[direction]['jij_tensor_data'])
            self.out(f'jij_tensor_{direction}_file', self.ctx.tensor_outputs[direction]['jij_tensor_file'])
        self.out('full_jij_tensor', self.ctx.combined_outputs['full_jij_tensor'])
        self.out('full_jij_tensor_file', self.ctx.combined_outputs['full_jij_tensor_file'])
        self.out('jij_interactions', self.ctx.combined_outputs['jij_interactions'])
        self.out('jij_interactions_file', self.ctx.combined_outputs['jij_interactions_file'])

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain.
        """
        self.report(errormsg)
        self.ctx.errors.append(errormsg)


@cf
def extract_jij_tensor_data(retrieved: orm.FolderData, parameters: orm.Dict):
    """
    Extract a full Jij tensor from a retrieved ``greensf.hdf`` file and provide it
    both as a ``Dict`` node and a CSV ``SinglefileData`` node.
    """
    filenames = retrieved.list_object_names()
    if FleurCalculation._GREENSF_HDF5_FILE_NAME not in filenames:
        return ExitCode(300, message='Retrieved folder has no greensf.hdf file')

    parameter_dict = parameters.get_dict()
    onsite_delta = np.array(parameter_dict['onsite_delta'], dtype=float)

    with retrieved.open(FleurCalculation._GREENSF_HDF5_FILE_NAME, 'rb') as handle:
        dataframe = calculate_heisenberg_tensor(handle,
                                                reference_atom=parameter_dict['reference_atom'],
                                                onsite_delta=onsite_delta,
                                                max_shells=parameter_dict.get('max_shells'))
    if dataframe.empty:
        raise ValueError('No intersite Green-function pairs were found in greensf.hdf')
    dataframe = decompose_jij_tensor(dataframe, parameter_dict['moment_direction'])

    records = json.loads(dataframe.to_json(orient='records'))
    csv_content = dataframe.to_csv(index=False)
    csv_handle = io.BytesIO(csv_content.encode('utf-8'))

    tensor_data = orm.Dict(
        dict={
            'moment_direction': parameter_dict['moment_direction'],
            'reference_atom': parameter_dict['reference_atom'],
            'max_shells': parameter_dict.get('max_shells'),
            'columns': list(dataframe.columns),
            'data': records,
        })
    tensor_data.label = f'jij_tensor_{parameter_dict["moment_direction"]}'
    tensor_data.description = ('Full Jij tensor extracted from greensf.hdf '
                               f'for the moment along {parameter_dict["moment_direction"]}.')

    tensor_file = orm.SinglefileData(csv_handle, filename=f'jij_tensor_{parameter_dict["moment_direction"]}.csv')
    tensor_file.label = f'jij_tensor_{parameter_dict["moment_direction"]}_file'
    tensor_file.description = ('CSV export of the full Jij tensor extracted from greensf.hdf '
                               f'for the moment along {parameter_dict["moment_direction"]}.')

    return {'jij_tensor_data': tensor_data, 'jij_tensor_file': tensor_file}


@cf
def extract_jij_tensor_data_from_singlefile(greensf_file: orm.SinglefileData, parameters: orm.Dict):
    """
    Extract a full Jij tensor from a provided ``greensf.hdf`` SinglefileData node.
    """
    parameter_dict = parameters.get_dict()
    onsite_delta = np.array(parameter_dict['onsite_delta'], dtype=float)

    with greensf_file.open('rb') as handle:
        dataframe = calculate_heisenberg_tensor(handle,
                                                reference_atom=parameter_dict['reference_atom'],
                                                onsite_delta=onsite_delta,
                                                max_shells=parameter_dict.get('max_shells'))
    if dataframe.empty:
        raise ValueError('No intersite Green-function pairs were found in greensf.hdf')
    dataframe = decompose_jij_tensor(dataframe, parameter_dict['moment_direction'])

    records = json.loads(dataframe.to_json(orient='records'))
    csv_content = dataframe.to_csv(index=False)
    csv_handle = io.BytesIO(csv_content.encode('utf-8'))

    tensor_data = orm.Dict(
        dict={
            'moment_direction': parameter_dict['moment_direction'],
            'reference_atom': parameter_dict['reference_atom'],
            'max_shells': parameter_dict.get('max_shells'),
            'columns': list(dataframe.columns),
            'data': records,
        })
    tensor_data.label = f'jij_tensor_{parameter_dict["moment_direction"]}'
    tensor_data.description = ('Full Jij tensor extracted from provided greensf.hdf '
                               f'for the moment along {parameter_dict["moment_direction"]}.')

    tensor_file = orm.SinglefileData(csv_handle, filename=f'jij_tensor_{parameter_dict["moment_direction"]}.csv')
    tensor_file.label = f'jij_tensor_{parameter_dict["moment_direction"]}_file'
    tensor_file.description = ('CSV export of the full Jij tensor extracted from provided greensf.hdf '
                               f'for the moment along {parameter_dict["moment_direction"]}.')

    return {'jij_tensor_data': tensor_data, 'jij_tensor_file': tensor_file}


@cf
def save_jij_output_node(**kwargs):
    """
    Create the main output node for the Jij workflow.
    """
    outpara = kwargs['out']
    outputnode = outpara.clone()
    outputnode.label = 'output_jij_wc_para'
    outputnode.description = 'Contains Jij workflow results and bookkeeping information.'
    return {'output_jij_wc_para': outputnode}


@cf
def combine_full_jij_tensor(jij_tensor_x: orm.Dict, jij_tensor_y: orm.Dict, jij_tensor_z: orm.Dict):
    """
    Reconstruct the full Jij tensor from the accessible subblocks of the
    x/y/z-resolved calculations and derive a compact magnetic-interaction table.
    """
    directional_nodes = {
        'x': jij_tensor_x.get_dict(),
        'y': jij_tensor_y.get_dict(),
        'z': jij_tensor_z.get_dict(),
    }

    dataframes = {}
    for direction, node_dict in directional_nodes.items():
        dataframe = pd.DataFrame(node_dict['data'])
        if dataframe.empty:
            raise ValueError(f'No tensor data available for moment direction {direction}')
        dataframes[direction] = dataframe

    tensor_components = ('J_xx', 'J_xy', 'J_xz', 'J_yx', 'J_yy', 'J_yz', 'J_zx', 'J_zy', 'J_zz')
    accessible_components = {
        'x': ('J_yy', 'J_yz', 'J_zy', 'J_zz'),
        'y': ('J_xx', 'J_xz', 'J_zx', 'J_zz'),
        'z': ('J_xx', 'J_xy', 'J_yx', 'J_yy'),
    }
    component_sources = {
        'J_xx': ('y', 'z'),
        'J_xy': ('z',),
        'J_xz': ('y',),
        'J_yx': ('z',),
        'J_yy': ('x', 'z'),
        'J_yz': ('x',),
        'J_zx': ('y',),
        'J_zy': ('x',),
        'J_zz': ('x', 'y'),
    }

    key_columns = [column for column in dataframes['x'].columns if column not in tensor_components + ('J_ij', 'A_ij', 'S_ij', 'D_ij')]
    merge_columns = [column for column in key_columns if column in dataframes['y'].columns and column in dataframes['z'].columns]
    if not merge_columns:
        raise ValueError('Could not determine common pair identifiers across the x/y/z tensor tables')

    merged = None
    for direction, dataframe in dataframes.items():
        subset_columns = merge_columns + [component for component in accessible_components[direction] if component in dataframe.columns]
        subset = dataframe[subset_columns].copy()
        rename_map = {
            component: f'{component}_{direction}'
            for component in accessible_components[direction] if component in subset.columns
        }
        subset = subset.rename(columns=rename_map)
        merged = subset if merged is None else merged.merge(subset, on=merge_columns, how='inner', validate='one_to_one')

    if merged is None or merged.empty:
        raise ValueError('Could not combine the x/y/z Jij tensor tables')

    full_tensor = merged[merge_columns].copy()
    for component, sources in component_sources.items():
        source_columns = [f'{component}_{source}' for source in sources if f'{component}_{source}' in merged.columns]
        if not source_columns:
            raise ValueError(f'Missing source columns for tensor component {component}')
        full_tensor[component] = merged[source_columns].mean(axis=1)

    full_tensor['Jij'] = (full_tensor['J_xx'] + full_tensor['J_yy'] + full_tensor['J_zz']) / 3.0
    full_tensor['Dij_x'] = 0.5 * (full_tensor['J_yz'] - full_tensor['J_zy'])
    full_tensor['Dij_y'] = 0.5 * (full_tensor['J_zx'] - full_tensor['J_xz'])
    full_tensor['Dij_z'] = 0.5 * (full_tensor['J_xy'] - full_tensor['J_yx'])
    full_tensor['|D|'] = np.sqrt(full_tensor['Dij_x']**2 + full_tensor['Dij_y']**2 + full_tensor['Dij_z']**2)

    interaction_columns = merge_columns + ['Jij', 'Dij_x', 'Dij_y', 'Dij_z', '|D|']
    interactions = full_tensor[interaction_columns].copy()

    full_tensor_records = json.loads(full_tensor.to_json(orient='records'))
    full_tensor_csv = io.BytesIO(full_tensor.to_csv(index=False).encode('utf-8'))
    interactions_records = json.loads(interactions.to_json(orient='records'))
    interactions_csv = io.BytesIO(interactions.to_csv(index=False).encode('utf-8'))

    full_tensor_node = orm.Dict(
        dict={
            'columns': list(full_tensor.columns),
            'pair_identifier_columns': merge_columns,
            'data': full_tensor_records,
            'component_sources': {component: list(sources) for component, sources in component_sources.items()},
        })
    full_tensor_node.label = 'full_jij_tensor'
    full_tensor_node.description = ('Full Jij tensor reconstructed from the x/y/z directional calculations. '
                                    'Overlapping accessible tensor elements are averaged.')

    full_tensor_file = orm.SinglefileData(full_tensor_csv, filename='full_jij_tensor.csv')
    full_tensor_file.label = 'full_jij_tensor_file'
    full_tensor_file.description = 'CSV export of the reconstructed full Jij tensor for each pair.'

    interactions_node = orm.Dict(
        dict={
            'columns': list(interactions.columns),
            'pair_identifier_columns': merge_columns,
            'data': interactions_records,
        })
    interactions_node.label = 'jij_interactions'
    interactions_node.description = ('Pair-resolved isotropic exchange and DMI extracted from the reconstructed '
                                     'full Jij tensor.')

    interactions_file = orm.SinglefileData(interactions_csv, filename='jij_interactions.csv')
    interactions_file.label = 'jij_interactions_file'
    interactions_file.description = ('CSV export of the pair-resolved isotropic exchange Jij, DMI components '
                                     'and |D| extracted from the reconstructed full Jij tensor.')

    return {
        'full_jij_tensor': full_tensor_node,
        'full_jij_tensor_file': full_tensor_file,
        'jij_interactions': interactions_node,
        'jij_interactions_file': interactions_file
    }
