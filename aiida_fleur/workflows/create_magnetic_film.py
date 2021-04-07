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
    In this module you find the workflow 'FleurCreateMagneticWorkChain' for creation of relaxed
    film deposited on a cubic substrate.
"""

from __future__ import absolute_import
import copy
import six

from aiida.engine import WorkChain, if_
from aiida.engine import calcfunction as cf
from aiida.orm import StructureData, Dict, Float, load_node, Str
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.workflows.eos import FleurEosWorkChain
from aiida_fleur.workflows.base_relax import FleurBaseRelaxWorkChain


class FleurCreateMagneticWorkChain(WorkChain):
    """
        This workflow creates relaxed magnetic film on a substrate.
    """
    _workflowversion = '0.1.2'

    _default_wf_para = {
        'lattice': 'fcc',
        'miller': [[-1, 1, 0], [0, 0, 1], [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,  # if equals to 0, use distance_suggestion
        'size': (1, 1, 5),
        'replacements': {
            0: 'Fe',
            -1: 'Fe'
        },
        'hold_n_first_layers': 3,
        'decimals': 10,
        'pop_last_layers': 1,
        'total_number_layers': 4,
        'num_relaxed_layers': 2
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurEosWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           },
                           namespace='eos',
                           exclude=('structure',))
        spec.expose_inputs(FleurBaseRelaxWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           },
                           namespace='relax',
                           exclude=('structure',))
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('eos_output', valid_type=Dict, required=False)
        spec.input('optimized_structure', valid_type=StructureData, required=False)
        spec.input('distance_suggestion', valid_type=Dict, required=False)

        spec.outline(cls.start,
                     if_(cls.eos_needed)(cls.run_eos,),
                     if_(cls.relax_needed)(cls.run_relax,), cls.make_magnetic)

        spec.output('magnetic_structure', valid_type=StructureData)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(380, 'ERROR_NOT_SUPPORTED_LATTICE', message='Specified substrate has to be bcc or fcc.')
        spec.exit_code(382, 'ERROR_RELAX_FAILED', message='Relaxation calculation failed.')
        spec.exit_code(383, 'ERROR_EOS_FAILED', message='EOS WorkChain failed.')

    def eos_needed(self):
        """
        Returns True if EOS WorkChain should be submitted
        """
        return self.ctx.eos_needed

    def prepare_eos(self):
        """
        Initialize inputs for eos workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        inputs = AttributeDict(self.exposed_inputs(FleurEosWorkChain, namespace='eos'))
        inputs.metadata.label = 'EOS_substrate'
        inputs.metadata.description = 'The EOS workchain finding equilibrium substrate'
        # Here wf_dict nodes appears out of nowwhere.
        inputs.structure = create_substrate_bulk(Dict(dict=self.ctx.wf_dict))

        if not isinstance(inputs.structure, StructureData):
            return inputs, inputs.structure  # exit code thrown in create_substrate_bulk

        return inputs, None

    def run_eos(self):
        """
        Optimize lattice parameter for substrate bulk structure.
        """
        self.report('INFO: submit EOS WorkChain')
        inputs = {}
        inputs, error = self.prepare_eos()
        if error:
            return error
        res = self.submit(FleurEosWorkChain, **inputs)
        self.to_context(eos_wc=res)

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Create Magnetic Film' ' workflow version {}\n'.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []
        self.ctx.substrate = None

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = []
        for key in wf_dict.keys():
            if key not in list(wf_default.keys()):
                extra_keys.append(key)
        if extra_keys:
            error = 'ERROR: input wf_parameters for Create Magnetic contains extra keys: {}'.format(extra_keys)
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        inputs = self.inputs
        if 'eos' in inputs:
            self.report('INFO: EOS workchain will be submitted')
            self.ctx.eos_needed = True
            self.ctx.relax_needed = True
            if 'eos_output' in inputs:
                self.report('ERROR: you specified both eos_output and eos wc inputs.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'relax' not in inputs:
                self.report('ERROR: no relax wc input was given despite EOS is needed.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'optimized_structure' in inputs:
                self.report('ERROR: optimized structure was given despite EOS is needed.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            if 'eos_output' in inputs:
                self.report('INFO: Outputs of the given EOS workchain will be used for relaxation')
                self.ctx.eos_needed = False
                self.ctx.relax_needed = True
                if 'relax' not in inputs:
                    self.report('ERROR: no relax wc input was given despite EOS is needed.')
                    return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
                if 'optimized_structure' in inputs:
                    self.report('ERROR: optimized structure was given despite relax is needed.')
                    return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            else:
                if 'optimized_structure' in inputs:
                    self.report('INFO: given relaxed structure will be used, no EOS or relax WC')
                    self.ctx.eos_needed = False
                    self.ctx.relax_needed = False
                    if 'relax' in inputs:
                        self.report('ERROR: relax wc input was given but relax is not needed.')
                        return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
                else:
                    self.ctx.eos_needed = False
                    self.ctx.relax_needed = True
                    self.report('INFO: relaxation will be continued; no EOS')
                    if 'relax' not in inputs:
                        self.report('ERROR: relax wc input was not given but relax is needed.')
                        return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        if 'relax' in inputs and 'distance_suggestion' not in inputs:
            if 'eos' in inputs or 'eos_output' in inputs:
                self.report('ERROR: relax wc input was given but distance_suggestion was not.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        if self.ctx.wf_dict['latticeconstant'] == 0 and 'distance_suggestion' not in inputs:
            self.report('ERROR: latticeconstant equals to 0 but distance_suggestion was not given.')
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

        if not self.ctx.wf_dict['latticeconstant']:
            from numpy import sqrt
            host_symbol = self.ctx.wf_dict['host_symbol']
            dict_suggestion = self.inputs.distance_suggestion.get_dict()
            lattice = self.ctx.wf_dict['lattice']

            if lattice == 'fcc':
                suggestion_factor = sqrt(2)
            elif lattice == 'bcc':
                suggestion_factor = 2 / sqrt(3)
            else:
                return self.exit_codes.ERROR_NOT_SUPPORTED_LATTICE

            suggestion = dict_suggestion.get(lattice, dict_suggestion[host_symbol]).get(host_symbol, 4.0)

            self.ctx.wf_dict['latticeconstant'] = float(suggestion_factor * suggestion)

    def relax_needed(self):
        """
        Returns true if interlayer relaxation should be performed.
        """
        if self.ctx.eos_needed or 'eos_output' in self.inputs:
            if not self.ctx.eos_needed:
                eos_output = self.inputs.eos_output
            else:
                try:
                    eos_output = self.ctx.eos_wc.outputs.output_eos_wc_para
                except NotExistent:
                    return self.ctx.ERROR_EOS_FAILED

            self.ctx.scaling_param = eos_output.get_dict()['scaling_gs']

        return self.ctx.relax_needed

    def run_relax(self):
        """
        Optimize interlayer distance.
        """
        self.report('INFO: submit Relaxation WorkChain')
        inputs = {}
        inputs, error = self.prepare_relax()
        if error:
            return error
        res = self.submit(FleurBaseRelaxWorkChain, **inputs)
        self.to_context(relax_wc=res)

    def prepare_relax(self):
        """
        Initialise inputs for Relax workchain
        """
        inputs = AttributeDict(self.exposed_inputs(FleurBaseRelaxWorkChain, namespace='relax'))
        inputs.metadata.label = 'Relax_symmetric_film'
        inputs.metadata.description = 'The Relax workchain relaxing film structure'

        if self.ctx.eos_needed or 'eos_output' in self.inputs:
            if not self.ctx.eos_needed:
                eos_output = self.inputs.eos_output
            else:
                try:
                    eos_output = self.ctx.eos_wc.outputs.output_eos_wc_para
                except NotExistent:
                    return self.ctx.ERROR_EOS_FAILED
            # print(eos_output.get_dict())
            scaling_param = eos_output.get_dict()['scaling_gs']

            out_create_structure = create_film_to_relax(wf_dict_node=Dict(dict=self.ctx.wf_dict),
                                                        scaling_parameter=Float(scaling_param),
                                                        suggestion_node=self.inputs.distance_suggestion)
            inputs.scf.structure = out_create_structure['structure']
            substrate = out_create_structure['substrate']
            # TODO: error handling might be needed
            self.ctx.substrate = substrate.uuid  # can not store aiida data nodes directly in ctx.

            if not isinstance(inputs.scf.structure, StructureData):
                return inputs, inputs.scf.structure

        return inputs, None

    def make_magnetic(self):
        """
        Analuses outputs of previous steps and generated the final
        structure suitable for magnetic film calculations.
        """

        if 'optimized_structure' not in self.inputs:
            if not self.ctx.relax_wc.is_finished_ok:
                return self.exit_codes.ERROR_RELAX_FAILED

        if self.ctx.relax_needed:
            optimized_structure = self.ctx.relax_wc.outputs.optimized_structure
        else:
            optimized_structure = self.inputs.optimized_structure

        para_dict = {
            'total_number_layers': self.ctx.wf_dict['total_number_layers'],
            'num_relaxed_layers': self.ctx.wf_dict['num_relaxed_layers']
        }

        if not self.ctx.substrate:  # workchain was stated from remote->Relax or optimized_structure
            if 'optimized_structure' in self.inputs:
                self.ctx.substrate = find_substrate(structure=self.inputs['optimized_structure'])
            else:
                self.ctx.substrate = find_substrate(remote=self.inputs.relax.scf.remote_data)

        # to track the provenance from which structures it was created
        magnetic = magnetic_slab_from_relaxed_cf(optimized_structure, load_node(self.ctx.substrate),
                                                 Dict(dict=para_dict))
        magnetic.label = 'magnetic_structure'
        magnetic.description = ('Magnetic structure slab created within FleurCreateMagneticWorkChain, '
                                'created from : {} and {}'.format(optimized_structure.uuid, self.ctx.substrate))

        self.out('magnetic_structure', magnetic)


'''
@cf
def save_structure(structure):
    """
    Save a structure data node to provide correct provenance.
    """
    structure_return = structure.clone()
    return structure_return
'''


@cf
def magnetic_slab_from_relaxed_cf(optimized_structure, substrate, para_dict):
    """ calcfunction which wraps magnetic_slab_from_relaxed to keep provenance """
    from aiida_fleur.tools.StructureData_util import magnetic_slab_from_relaxed

    magnetic = magnetic_slab_from_relaxed(optimized_structure, substrate, **para_dict.get_dict())

    return magnetic


@cf
def create_substrate_bulk(wf_dict_node):
    """
    Calcfunction to create a bulk structure of a substrate.

    :params wf_dict: AiiDA dict node with at least keys lattice, host_symbol and latticeconstant
    (If they are not there, raises KeyError)
    Lattice key supports only fcc and bcc

    raises ExitCode 380, ERROR_NOT_SUPPORTED_LATTICE
    """

    from aiida.engine import ExitCode
    from ase.lattice.cubic import FaceCenteredCubic
    from ase.lattice.cubic import BodyCenteredCubic

    wf_dict = wf_dict_node.get_dict()
    lattice = wf_dict['lattice']
    if lattice == 'fcc':
        structure_factory = FaceCenteredCubic
    elif lattice == 'bcc':
        structure_factory = BodyCenteredCubic
    else:
        return ExitCode(380, 'ERROR_NOT_SUPPORTED_LATTICE', message='Specified substrate has to be bcc or fcc.')

    miller = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    host_symbol = str(wf_dict['host_symbol'])
    latticeconstant = float(wf_dict['latticeconstant'])
    size = (1, 1, 1)
    structure = structure_factory(miller=miller,
                                  symbol=host_symbol,
                                  pbc=(1, 1, 1),
                                  latticeconstant=latticeconstant,
                                  size=size)

    return StructureData(ase=structure)


@cf
def create_film_to_relax(wf_dict_node, scaling_parameter, suggestion_node):
    """
    Create a film structure those interlayers will be relaxed.
    """
    from aiida_fleur.tools.StructureData_util import create_manual_slab_ase, center_film, adjust_film_relaxation

    # scaling_parameter = eos_output.get_dict()['scaling_gs']
    wf_dict = wf_dict_node.get_dict()
    scaling_parameter = float(scaling_parameter)

    miller = wf_dict['miller']
    host_symbol = wf_dict['host_symbol']
    latticeconstant = float(wf_dict['latticeconstant'] * scaling_parameter**(1 / 3.0))
    size = wf_dict['size']
    replacements = wf_dict['replacements']
    pop_last_layers = wf_dict['pop_last_layers']
    decimals = wf_dict['decimals']
    lattice = wf_dict['lattice']
    hold_layers = wf_dict['hold_n_first_layers']

    structure = create_manual_slab_ase(lattice=lattice,
                                       miller=miller,
                                       host_symbol=host_symbol,
                                       latticeconstant=latticeconstant,
                                       size=size,
                                       replacements=replacements,
                                       decimals=decimals,
                                       pop_last_layers=pop_last_layers)

    structure = StructureData(ase=structure)

    # substrate needs to be reversed
    substrate = create_manual_slab_ase(lattice=lattice,
                                       miller=miller,
                                       host_symbol=host_symbol,
                                       latticeconstant=latticeconstant,
                                       size=(1, 1, 1),
                                       replacements=None,
                                       decimals=decimals,
                                       inverse=True)

    tmp_substrate = create_manual_slab_ase(lattice=lattice,
                                           miller=miller,
                                           host_symbol=host_symbol,
                                           latticeconstant=latticeconstant,
                                           size=(2, 2, 2),
                                           replacements=None,
                                           decimals=decimals)

    bond_length = find_min_distance_unary_struct(tmp_substrate)

    suggestion = suggestion_node.get_dict()

    # structure will be reversed here
    structure = adjust_film_relaxation(structure, suggestion, host_symbol, bond_length, hold_layers)

    centered_structure = center_film(structure)

    return {'structure': centered_structure, 'substrate': StructureData(ase=substrate)}


def find_min_distance_unary_struct(tmp_substrate):
    """
    Finds a minimal distance beteween atoms in a unary structure.

    ..warning:

        Make sure tmp_substrate to have a non-primitive unit cell!

    """
    import numpy as np
    distance = tmp_substrate.get_all_distances()
    di = np.diag_indices(len(distance))
    distance[di] = 100
    bond_length = np.amin(distance)
    return bond_length


def find_substrate(remote=None, structure=None):
    """
    Finds the stored substrate structure.
    If remote is given, goes up and tri
    """
    from aiida_fleur.workflows.base_relax import find_inputs_relax
    from aiida.plugins import DataFactory

    FleurinpData = DataFactory('fleur.fleurinp')

    if remote:
        inputs = find_inputs_relax(remote)
    elif structure:
        from aiida.orm import WorkChainNode
        inc_nodes = structure.get_incoming().all()
        for link in inc_nodes:
            if isinstance(link.node, WorkChainNode):
                relax_wc = link.node
                break

        if 'scf__remote_data' in relax_wc.inputs:
            inputs = find_inputs_relax(relax_wc.inputs.scf__remote_data)
        else:
            return relax_wc.inputs.scf__structure.get_incoming().all()[0].node.get_outgoing().get_node_by_label(
                'substrate').uuid

    if isinstance(inputs, FleurinpData):
        raise ValueError('Did not expect to find Relax WC started from FleurinpData')
    else:
        orig_structure = inputs[0]
        return orig_structure.get_incoming().all()[0].node.get_outgoing().get_node_by_label('substrate').uuid
