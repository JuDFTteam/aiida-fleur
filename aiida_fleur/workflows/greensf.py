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
from __future__ import annotations

import copy
import math
from collections import defaultdict

from lxml import etree
import pandas as pd

from aiida.engine import WorkChain, ToContext, if_, ExitCode
from aiida.engine import calcfunction as cf
from aiida import orm
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode, get_inputs_fleur
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data

from aiida_dataframe.data import PandasFrameData

import numpy as np


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
        'orbitals': None,
        'integration_cutoff': 'calc',
        'jij_shells': 0,
        'jij_shells_per_calc': None,
        'jij_shell_element': None,
        'species': None,
        'torque': False,
        'calculate_spinoffdiagonal': False,
        'contour_label': 'default',
        'jij_postprocess': True,
        'jij_full_tensor': False,
        'jij_onsite_exchange_splitting': 'bxc',  #or band-method
        'calculations_explicit': {},
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
        spec.expose_inputs(
            FleurScfWorkChain,
            namespace='scf',
            namespace_options={
                'required':
                False,
                'populate_defaults':
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
                'populate_defaults':
                False,
                'help':
                "Inputs for an Orbital occupation control workchain to run before calculating Green's functions. If not specified the Orbcontrol workchain is not run"
            })
        spec.input('remote',
                   valid_type=orm.RemoteData,
                   required=False,
                   help='Remote Folder data to start the calculation from')
        spec.input('fleurinp',
                   valid_type=FleurinpData,
                   required=False,
                   help='Fleurinpdata to start the calculation from')
        spec.input('fleur',
                   valid_type=orm.Code,
                   required=True,
                   help="Fleur code to use for the Green's function calculation")
        spec.input('wf_parameters',
                   valid_type=orm.Dict,
                   required=False,
                   help="Parameters to control the calculation of Green's functions")
        spec.input('options',
                   valid_type=orm.Dict,
                   required=False,
                   help="Submission options for the Green's function calculation")
        spec.input('settings',
                   valid_type=orm.Dict,
                   required=False,
                   help="Additional settings for the Green's function calculation")

        spec.outline(cls.start,
                     if_(cls.scf_needed)(cls.converge_scf,),
                     if_(cls.split_up_jij_calculations)(cls.run_blocked_jij_calcs).else_(cls.run_greensf_calc),
                     cls.return_results)

        spec.output('output_greensf_wc_para', valid_type=orm.Dict)
        spec.expose_outputs(FleurBaseWorkChain, namespace='greensf_calc')
        spec.output_namespace('jijs', valid_type=PandasFrameData, required=False, dynamic=True)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Input codes do not correspond to fleur or inpgen respectively.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(342, 'ERROR_GREENSF_CALC_FAILED', message="Green's function calculation failed.")
        spec.exit_code(345,
                       'ERROR_JIJ_POSTPROCESSING_FAILED',
                       message="Post processing of intersite Green's functions failed.")
        spec.exit_code(450, 'ERROR_SCF_FAILED', message='SCF Convergence workflow failed.')
        spec.exit_code(451, 'ERROR_ORBCONTROL_FAILED', message='Orbital occupation control workflow failed.')

    def start(self):
        """
        Intitialize context and defaults
        """
        self.ctx.scf_needed = False
        self.ctx.fleurinp_greensf = None
        self.ctx.num_jij_blocks = 0

        inputs = self.inputs

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in inputs:
            wf_dict = inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            if isinstance(val, dict):
                wf_dict[key] = {**val, **wf_dict.get(key, {})}
            else:
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

    def get_inputs_greensf_calc(self, jij_block=None):
        """
        Get inputs for the Green's function calculation workchain
        """

        status = self.change_fleurinp(jij_block=jij_block)
        if status:
            return status

        fleurin = self.ctx.fleurinp_greensf
        if fleurin is None:
            error = ("ERROR: Creating Green's function Fleurinp failed for an unknown reason")
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        if self.ctx.scf_needed:
            if 'scf' in self.inputs:
                try:
                    remote_data = self.ctx.scf.outputs.last_calc.remote_folder
                except NotExistent:
                    error = 'Remote generated in the SCF calculation is not found.'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_SCF_FAILED
            else:
                try:
                    remote_data = self.ctx.orbcontrol.outputs.groundstate_scf.last_calc.remote_folder
                except NotExistent:
                    error = 'Remote generated in the Orbcontrol calculation is not found.'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_ORBCONTROL_FAILED
        else:
            inputs = self.inputs
            if 'remote' in inputs:
                remote_data = inputs.remote
            else:
                remote_data = None

        inputs = self.inputs
        if 'settings' in inputs:
            settings = inputs.settings
        else:
            settings = None

        label = 'greensf_calc'
        description = f"Fleur Green's function calculation with{'out' if not self.ctx.scf_needed else ''} previous SCF calculation"

        input_greensf = get_inputs_fleur(inputs.fleur,
                                         remote_data,
                                         fleurin,
                                         self.ctx.options,
                                         label,
                                         description,
                                         settings=settings)

        return input_greensf

    def run_greensf_calc(self):
        """
        Submit greens function calculation without previous scf
        """
        self.report(f"INFO: run Green's function calculations{' after SCF/OrbControl' if self.ctx.scf_needed else ''}")
        inputs = self.get_inputs_greensf_calc()
        result_greensf = self.submit(FleurBaseWorkChain, **inputs)
        return ToContext(greensf=result_greensf)

    def split_up_jij_calculations(self):
        """
        Return whether the Jij calculations are to be done in multiple steps
        """
        return self.ctx.wf_dict['jij_shells'] != 0 and self.ctx.wf_dict['jij_shells_per_calc'] is not None

    def run_blocked_jij_calcs(self):
        """
        Run multiple Jij calculations with jij_shells_per_calc each
        """
        self.report(
            f"INFO: run Jij Green's function calculations{' after SCF/OrbControl' if self.ctx.scf_needed else ''}")

        self.ctx.num_jij_blocks = math.ceil(self.ctx.wf_dict['jij_shells'] / self.ctx.wf_dict['jij_shells_per_calc'])
        self.report(f"INFO: Submitting {self.ctx.num_jij_blocks} calculations for Intersite Green's functions")
        calculations = {}
        for jij_block in range(self.ctx.num_jij_blocks):
            inputs = self.get_inputs_greensf_calc(jij_block=jij_block)
            label = f'greensf_jij_block_{jij_block}'

            inputs.setdefault('metadata', {})['call_link_label'] = label
            self.report(f"INFO: Submitting  Green's functions calculation: block {jij_block}")
            res = self.submit(FleurBaseWorkChain, **inputs)
            res.label = label
            calculations[label] = self.submit(FleurBaseWorkChain, **inputs)
        return ToContext(**calculations)

    def change_fleurinp(self, jij_block=None):
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
                    return self.exit_codes.ERROR_SCF_FAILED
            else:
                try:
                    fleurin = self.ctx.orbcontrol.outputs.output_orbcontrol_wc_gs_fleurinp
                except NotExistent:
                    error = 'Fleurinp generated in the Orbcontrol calculation is not found.'
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_ORBCONTROL_FAILED
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

        if self.ctx.wf_dict['torque'] or self.ctx.wf_dict['calculate_spinoffdiagonal']:
            fleurmode.set_inpchanges({
                'ctail': False,
                'l_noco': True,
                'l_mperp': True
            },
                                     path_spec={'l_mperp': {
                                         'contains': 'magnetism'
                                     }})
            contour_tags['l_mperp'] = True

        fleurmode.set_complex_tag('greensFunction', dict(contour_tags))

        calculations = wf_dict['calculations_explicit'].copy()

        if self.ctx.wf_dict['species'] is not None:

            orbitals = self.ctx.wf_dict['orbitals']
            if not isinstance(orbitals, list):
                orbitals = [orbitals]

            if all(len(o) == 1 for o in orbitals):
                orbital_tag = {'diagelements': {orb: True for orb in orbitals}}
            else:
                orbital_tag = {}
                for orb in orbitals:
                    if len(orb) == 2:
                        l, lp = orb[0], orb[1]
                    elif len(orb) == 1:
                        l, lp = orb

                    orbital_tag.setdefault(l, np.zeros((4,), dtype=bool))['spdf'.index(lp)] = True
                orbital_tag = {'matrixelements': orbital_tag}

            calculation = {
                'kkintgrCutoff': self.ctx.wf_dict['integration_cutoff'],
                'label': self.ctx.wf_dict['contour_label'],
                **orbital_tag
            }
            if self.ctx.wf_dict['torque']:
                calculation['torque'] = True
            else:
                if jij_block is not None:
                    shells_per_calc = self.ctx.wf_dict['jij_shells_per_calc']
                    start = jij_block * shells_per_calc + 1
                    end = min((jij_block + 1) * shells_per_calc, self.ctx.wf_dict['jij_shells'])
                    calculation['startFromShell'] = start
                    calculation['nshells'] = end
                else:
                    calculation['nshells'] = self.ctx.wf_dict['jij_shells']
                if self.ctx.wf_dict['jij_shell_element'] is not None:
                    calculation['shellElement'] = self.ctx.wf_dict['jij_shell_element']

            calculations.append(calculation)

        calc_tags = defaultdict(defaultdict(list))
        for species_name, calc in calculations.items():

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
        """
        Return the results of the workchain
        """
        self.report("Green's function calculation done")

        outnodedict = {}
        retrieved_nodes = {}
        if self.split_up_jij_calculations():
            for block in range(self.ctx.num_jij_blocks):
                label = f'greensf_jij_block_{block}'
                if label in self.ctx:
                    calc = self.ctx[label]
                else:
                    message = (
                        f"Green's function calculation was not run because the previous calculation failed: {label}")
                    self.ctx.warnings.append(message)
                    self.ctx.successful = False
                    continue

                if not calc.is_finished_ok:
                    message = f"One Green's function calculation was not successful: {label}"
                    self.ctx.warnings.append(message)
                    self.ctx.successful = False
                    continue

                try:
                    para = calc.outputs.output_parameters
                except NotExistent:
                    message = f"One Green's function calculation failed, no output node: {label}. I skip this one."
                    self.ctx.errors.append(message)
                    self.ctx.successful = False
                    continue

                try:
                    retrieved = calc.outputs.retrieved
                except NotExistent:
                    message = f"One Green's function calculation failed, no retrieved output node: {label}. I skip this one."
                    self.ctx.errors.append(message)
                    self.ctx.successful = False
                    continue

                if 'greensf.hdf' not in retrieved.list_object_names():
                    message = f"One Green's function calculation failed, no greensf.hdf file: {label}. I skip this one."
                    self.ctx.errors.append(message)
                    self.ctx.successful = False
                    continue

                # we loose the connection of the failed calcs here.
                # link labels cannot contain '.'
                link_label = f'parameters_{label}'
                retrieved_label = f'retrieved_{label}'
                outnodedict[link_label] = para
                outnodedict[retrieved_label] = retrieved
                retrieved_nodes[retrieved_label] = retrieved

        else:
            if self.ctx.greensf:
                self.report(
                    f"Green's functions were calculated. The calculation is found under pk={self.ctx.greensf.pk}, "
                    f'calculation {self.ctx.greensf}')

            try:  # if something failed, we still might be able to retrieve something
                last_calc_out = self.ctx.greensf.outputs.output_parameters
                retrieved = self.ctx.greensf.outputs.retrieved
            except (NotExistent, AttributeError):
                last_calc_out = None
                retrieved = None

            if last_calc_out is not None:
                outnodedict['para_greensf'] = last_calc_out
            if retrieved is not None:
                outnodedict['retrieved_greensf'] = retrieved
                retrieved_nodes['retrieved_greensf'] = retrieved

            greensf_files = []
            if retrieved:
                greensf_files = retrieved.list_object_names()

            if 'greensf.hdf' in greensf_files:
                self.ctx.successful = True

            if not self.ctx.successful:
                self.report("!NO Green's function file was found, something went wrong!")

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['errors'] = self.ctx.errors
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful

        jij_calculation_failed = False
        if self.ctx.successful and self.ctx.wf_dict['jij_shells'] > 0 and self.ctx.wf_dict['jij_postprocess']:
            self.report(f"Calculating Jij constants for atom species '{self.ctx.wf_dict['species']}'")

            result = calculate_jij(species=orm.Str(self.ctx.wf_dict['species']),
                                   onsite_exchange_splitting_mode=orm.Str(
                                       self.ctx.wf_dict['jij_onsite_exchange_splitting']),
                                   calculate_full_tensor=orm.Bool(self.ctx.wf_dict['jij_full_tensor']),
                                   **retrieved_nodes)

            if isinstance(result, ExitCode):
                jij_calculation_failed = True
            else:
                self.out_many(result, namespace='jijs')

        outputnode_t = orm.Dict(dict=outputnode_dict)
        outdict = {}
        if last_calc_out:
            outdict = create_greensf_result_node(outpara=outputnode_t, **outnodedict)

        for link_name, node in outdict.items():
            self.out(link_name, node)

        if self.split_up_jij_calculations() and 'greensf_jij_block_0' in self.ctx:
            self.out_many(
                self.exposed_outputs(self.ctx.greensf_jij_block_0, FleurBaseWorkChain, namespace='greensf_calc'))
        elif self.ctx.greensf:
            self.out_many(self.exposed_outputs(self.ctx.greensf, FleurBaseWorkChain, namespace='greensf_calc'))

        if jij_calculation_failed:
            return self.exit_codes.ERROR_JIJ_POSTPROCESSING_FAILED

        if not self.ctx.successful:
            return self.exit_codes.ERROR_GREENSF_CALC_FAILED

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_greensf_result_node(**kwargs):
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
    outputnode.label = 'output_greensf_wc_para'
    outputnode.description = ('Contains results and information of an FleurGreensfWorkChain run.')

    outdict['output_greensf_wc_para'] = outputnode
    return outdict


@cf
def calculate_jij(
    species: orm.Str,
    onsite_exchange_splitting_mode: orm.Str | None = None,
    calculate_full_tensor: orm.Bool | None = None,
    **retrieved: orm.FolderData,
) -> dict[str, PandasFrameData]:
    """
    Calculate the Heisenberg Jij calculations for the given
    Calculation results (multiple possible)

    If multiple are given they are assumed to calculate different shells
    and the results are concatenated
    ATM no checks are done that multiple calculations actually come from the same system

    :param retrieved: FolderData of the Calculation containing a greensf.hdf file
    :param onsite_exchange_splitting: Str What method to use for the onsite exhcnage splitting
                                      either 'bxc' or 'band-delta'

    :returns: dictionary with Jij constants
    """

    result = defaultdict(list)
    for node in retrieved.values():
        single_result = calculate_jij_single_calc(node,
                                                  species=species,
                                                  onsite_exchange_splitting_mode=onsite_exchange_splitting_mode,
                                                  calculate_full_tensor=calculate_full_tensor)

        if isinstance(single_result, ExitCode):
            return single_result

        for key, value in single_result.items():
            result[key].append(value)

    for key, jij_list in result.items():
        result[key] = pd.concat(jij_list, ignore_index=True)
        #Sort by R first to get the shells separate
        #The order inside shells is determined with the vectors
        result[key] = result[key].sort_values(by=['R', 'R_ij_x', 'R_ij_y', 'R_ij_z'])
        result[key] = PandasFrameData(result[key])

    return dict(result)


def calculate_jij_single_calc(retrieved: orm.FolderData,
                              species: orm.Str,
                              onsite_exchange_splitting_mode: orm.Str | None = None,
                              calculate_full_tensor: orm.Bool | None = None) -> dict[str, pd.DataFrame]:
    """
    Calculate the Heisenberg Jij calculations for the given
    Calculation results

    :param retrieved: FolderData of the Calculation containing a greensf.hdf file
    :param onsite_exchange_splitting: Str What method to use for the onsite exhcnage splitting
                                      either 'bxc' or 'band-delta'

    :returns: Jij constant array
    """
    from masci_tools.io.fleur_xml import load_outxml, FleurXMLContext
    from masci_tools.tools.greensf_calculations import calculate_heisenberg_jij, calculate_heisenberg_tensor
    from masci_tools.util.constants import ATOMIC_NUMBERS

    if 'greensf.hdf' not in retrieved.list_object_names():
        return ExitCode(100, message="Given retrieved folder does not contain a 'greensf.hdf' file")

    if 'out.xml' not in retrieved.list_object_names():
        return ExitCode(100, message="Given retrieved folder does not contain a 'out.xml' file")

    if onsite_exchange_splitting_mode is None:
        onsite_exchange_splitting_mode = orm.Str('bxc')
    if calculate_full_tensor is None:
        calculate_full_tensor = orm.Bool(False)

    if onsite_exchange_splitting_mode.value not in ['bxc', 'band-delta']:
        return ExitCode(100, message="Invalid input for onsite_exchange_splitting_mode. Either 'bxc' or 'band-method'")

    with retrieved.open('out.xml', 'rb') as file:
        xmltree, schema_dict = load_outxml(file)

    with FleurXMLContext(xmltree, schema_dict) as root:

        n_atomgroups = root.number_nodes('atomgroup')

        species_to_element = {}
        for species_node in root.iter('species'):
            nz = species_node.attribute('atomicNumber')
            species_to_element[species_node.attribute('name')] = ATOMIC_NUMBERS[nz]

        atomtypes_to_calculate = []
        species_names = root.attribute('species', contains='atomGroup', list_return=True)
        for index, species_name in enumerate(species_names):
            if species.value == 'all':
                atomtypes_to_calculate.append(index)
            elif species.value[:4] == 'all-' and species.value[4:] in species_name:
                atomtypes_to_calculate.append(index)
            elif species.value == species_name:
                atomtypes_to_calculate.append(index)

        if onsite_exchange_splitting_mode.value == 'bxc':
            delta = root.all_attributes('bxcIntegral', filters={'iteration': {'index': -1}}, iteration_path=True)
            delta_atomtypes = [
                delta['Delta'][delta['atomType'].index(index + 1)] if index + 1 in delta['atomType'] else None
                for index in range(n_atomgroups)
            ]
            delta_arr = np.array([[d] * 4 for d in delta_atomtypes])
        else:
            return ExitCode(999, message='Not implemented')
            #delta = evaluate_tag(xmltree, schema_dict, 'bxcIntegral', filters={'iteration': {'index': -1}}, iteration_path=True)

    result = {}
    with retrieved.open('greensf.hdf', 'rb') as file:
        for reference_atom in atomtypes_to_calculate:
            if calculate_full_tensor:
                jij_df = calculate_heisenberg_tensor(file, reference_atom, delta_arr)
            else:
                jij_df = calculate_heisenberg_jij(file, reference_atom, delta_arr)

            name = f'{species_to_element[species_names[reference_atom]]}_{reference_atom}'
            result[name] = jij_df

    return result
