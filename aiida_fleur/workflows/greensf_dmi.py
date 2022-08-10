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
Workflow for calculating DMI from Green's functions
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict

from lxml import etree
import pandas as pd
import numpy as np

from aiida.engine import WorkChain, ToContext, if_, ExitCode
from aiida.engine import calcfunction as cf
from aiida import orm
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.workflows.greensf import FleurGreensfWorkChain
from aiida_fleur.data.fleurinpmodifier import inpxml_changes

from aiida_dataframe.data import PandasFrameData


class FleurGreensfDMIWorkChain(WorkChain):
    """
    Workflow for calculating DMI from Green's functions
    """

    _workflowversion = '0.1.0'

    _default_wf_para = {
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'sqas_moment_direction': ['z', 'x', 'y'],  #Do not change (yet)
        'noco': True,
        'soc_one_shot': False,
        'species': None,
        'orbitals': None,
        'integration_cutoff': 'calc',
        'jij_shells': 0,
        'jij_shells_per_calc': None,
        'jij_shell_element': None,
        'calculate_spinoffdiagonal': True,
        'contour_label': 'default',
        'jij_onsite_exchange_splitting': 'bxc',  #or band-method
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
            FleurGreensfWorkChain,
            namespace='greensf',
            namespace_options={
                'required':
                False,
                'populate_defaults':
                False,
                'help':
                "Inputs for an SCF workchain to run before calculating Green's functions. If not specified the SCF workchain is not run"
            })
        spec.input('wf_parameters',
                   valid_type=orm.Dict,
                   required=False,
                   help="Parameters to control the calculation of Green's functions")

        spec.outline(cls.start, cls.run_greensf_wc, cls.decompose_jijs, cls.return_results)

        spec.output('output_greensf_dmi_wc_para', valid_type=orm.Dict)
        spec.output_namespace('jij', valid_type=PandasFrameData, required=False, dynamic=True)
        spec.output_namespace('dij', valid_type=PandasFrameData, required=False, dynamic=True)
        spec.output_namespace('sij', valid_type=PandasFrameData, required=False, dynamic=True)
        spec.output_namespace('aij', valid_type=PandasFrameData, required=False, dynamic=True)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(342, 'ERROR_GREENSF_WC_FAILED', message="Green's function workchain failed.")
        spec.exit_code(345,
                       'ERROR_JIJ_DECOMPOSITION_FAILED',
                       message="Post processing of intersite Green's functions failed.")

    def start(self):
        """
        Initialize context
        """
        self.report(f"Started Green's function DMI workflow version {self._workflowversion}")
        self.ctx.successful = False
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.exit_code = None
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

        self.ctx.sqas = {
            label: (t, p) for label, t, p in zip(
                self.ctx.wf_dict['sqas_moment_direction'],
                self.ctx.wf_dict['sqas_theta'],
                self.ctx.wf_dict['sqas_phi'],
            )
        }

        if any(d not in ('x', 'y', 'z') for d in self.ctx.wf_dict['sqas_moment_direction']):
            error = 'ERROR: Provided invalid direction. Only x,y,z allowed'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def get_inputs_greensfunction(self, sqa):
        """
        Get the inputs for calculating Green's function workchain for the given SQA
        """
        inputs_greensf = self.exposed_inputs(FleurGreensfWorkChain, namespace='greensf')

        if self.ctx.wf_dict['soc_one_shot'] or ('scf' not in inputs_greensf and 'orbcontrol' not in inputs_greensf):
            parameters = inputs_greensf
        elif 'scf' in inputs_greensf:
            parameters = inputs_greensf.scf
        else:
            parameters = inputs_greensf.orbcontrol

        with inpxml_changes(parameters) as fm:
            if self.ctx.wf_dict['noco']:
                fm.set_inpchanges({
                    'ctail': False,
                    'l_noco': True,
                    'l_soc': True,
                })
                if self.ctx.wf_dict['calculate_spinoffdiagonal']:
                    fm.set_inpchanges({'l_mperp': True}, path_spec={'l_mperp': {'contains': 'magnetism'}})
                fm.set_atomgroup('all', {'nocoParams': {'beta': sqa[0], 'alpha': sqa[1]}})
            else:
                fm.set_inpchanges({
                    'theta': sqa[0],
                    'phi': sqa[1],
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

        if 'wf_parameters' in inputs_greensf:
            greensf_para = inputs_greensf.wf_parameters.get_dict()
        else:
            greensf_para = {}

        #Overwrite everything that needs to be overwritten
        greensf_para['species'] = self.ctx.wf_dict['species']
        greensf_para['orbitals'] = self.ctx.wf_dict['orbitals']
        greensf_para['jij_shells'] = self.ctx.wf_dict['jij_shells']
        greensf_para['jij_shells_per_calc'] = self.ctx.wf_dict['jij_shells_per_calc']
        greensf_para['integration_cutoff'] = self.ctx.wf_dict['integration_cutoff']
        greensf_para['jij_shell_element'] = self.ctx.wf_dict['jij_shell_element']
        greensf_para['calculate_spinoffdiagonal'] = self.ctx.wf_dict['calculate_spinoffdiagonal']
        greensf_para['contour_label'] = self.ctx.wf_dict['contour_label']
        greensf_para['jij_postprocess'] = True
        greensf_para['jij_full_tensor'] = True
        greensf_para['jij_onsite_exchange_splitting'] = self.ctx.wf_dict['jij_onsite_exchange_splitting']

        inputs_greensf.wf_parameters = orm.Dict(dict=greensf_para)

        return inputs_greensf

    def run_greensf_wc(self):
        """
        Run the Green's function
        """

        for direction, sqa in self.ctx.sqas.items():
            inputs = self.get_inputs_scf(sqa=sqa)
            res = self.submit(FleurGreensfWorkChain, **inputs)
            label = f'greensf_sqa_{direction}'
            res.label = label
            self.to_context(**{label: res})

    def decompose_jijs(self):
        """
        Get the results of the Green's function workchains and
        decompose the jij
        """

        jijs = defaultdict(dict)
        first_calc = True
        for direction in self.ctx.sqas:
            label = f'greensf_sqa_{direction}'
            if label in self.ctx:
                calc = self.ctx[label]
            else:
                message = (f"Green's function workchain was not run: {label}")
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                self.ctx.exit_code = self.exit_codes.ERROR_GREENSF_WC_FAILED
                continue

            if not calc.is_finished_ok:
                message = f"One Green's function workchain was not successful: {label}"
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                self.ctx.exit_code = self.exit_codes.ERROR_GREENSF_WC_FAILED
                continue

            try:
                jijs_direction = calc.outputs.jijs
            except NotExistent:
                message = f"One Green's function workchain failed, no jijs node: {label}. I skip this one."
                self.ctx.errors.append(message)
                self.ctx.successful = False
                self.ctx.exit_code = self.exit_codes.ERROR_GREENSF_WC_FAILED
                continue

            for atom_name, jij_df in jijs_direction.items():
                if not first_calc and atom_name not in jijs:
                    message = f"One Green's function workchain calculated jijs for different atomtypes: {label}. {atom_name}."
                    self.ctx.errors.append(message)
                    self.ctx.successful = False
                    self.ctx.exit_code = self.exit_codes.ERROR_GREENSF_WC_FAILED
                jijs[atom_name][direction] = jij_df

            first_calc = False

        if not self.ctx.successful:
            self.control_end_wc("Green's function DMI workflow failed, since atleast one SQA direction failed")

        for atom_name, all_directions in jijs.items():
            decomposed_dfs = decompose_jij_tensors(all_directions['x'], all_directions['y'], all_directions['z'])
            self.out_many({f'{namespace}__{atom_name}': node for namespace, node in decomposed_dfs.items()})

    def return_results(self):
        """
        Return results
        """
        self.report("Green's function DMI calculation done")

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['errors'] = self.ctx.errors
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful

        outputnode_t = orm.Dict(dict=outputnode_dict)
        outdict = {}
        outdict = create_greensf_dmi_result_node(outpara=outputnode_t)

        for link_name, node in outdict.items():
            self.out(link_name, node)

        if self.ctx.exit_code is not None:
            return self.ctx.exit_code

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_greensf_dmi_result_node(**kwargs):
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
    outputnode.label = 'output_greensf_dmi_wc_para'
    outputnode.description = ('Contains results and information of an FleurGreensfDMIWorkChain run.')

    outdict['output_greensf_dmi_wc_para'] = outputnode
    return outdict


@cf
def decompose_jij_tensors(jij_x: PandasFrameData, jij_y: PandasFrameData,
                          jij_z: PandasFrameData) -> dict[str, PandasFrameData]:
    """
    Combine the Jij tensors calculated for x,y and z SQA and decompose it into the
    isotropic and non-isotropic exchange.
    The resulting dataframes will contain the vectors for J_ij, D_ij, S_ij, A_ij
    """
    from masci_tools.tools.greensf_calculations import decompose_jij_tensor

    mom_direction = ('x', 'y', 'z')

    all_directions = []
    for jij_node, direction in zip((jij_x, jij_y, jij_z), mom_direction):
        all_directions.append(decompose_jij_tensor(jij_node.df, direction))

    results = {}
    for component in ('J_ij', 'D_ij', 'S_ij', 'A_ij'):

        output_label = component.replace('_', '').lower()

        #Get the columns that are common to all calculations from the first one
        series = [
            all_directions[0]['R'],
            all_directions[0]['R_ij_x'],
            all_directions[0]['R_ij_y'],
            all_directions[0]['R_ij_z'],
        ]
        if component == 'J_ij':
            series.append(all_directions[0][component])  #This is the isotropic part that is equal for all directions
        else:
            #rename the decomposed components to contain the direction
            for df, direction in zip(all_directions, mom_direction):
                series.append(df[component].rename(f'{component}_{direction}'))

        all_vectors = pd.concat(series, axis=1)
        if component not in ('D_ij', 'S_ij', 'A_ij'):
            results[output_label] = PandasFrameData(all_vectors)
            continue

        if component == 'D_ij':
            all_vectors['D_ij_x'] = -all_vectors['D_ij_x']  #See fleur noco issues
            all_vectors['D_ij_z'] = -all_vectors['D_ij_z']

        all_vectors[component] = np.sqrt(all_vectors[f'{component}_x']**2 + all_vectors[f'{component}_y']**2 +
                                         all_vectors[f'{component}_z']**2)

        all_vectors[f'cos_theta{component}'] = (all_vectors['R_ij_x']*all_vectors[f'{component}_x']+\
                                                all_vectors['R_ij_y']*all_vectors[f'{component}_y']+\
                                                all_vectors['R_ij_z']*all_vectors[f'{component}_z'])*\
                                                1/(all_vectors['R']*all_vectors[component])
        results[output_label] = PandasFrameData(all_vectors)

    return results
