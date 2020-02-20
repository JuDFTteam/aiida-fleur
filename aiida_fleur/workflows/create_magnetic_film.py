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
from aiida.plugins import DataFactory
from aiida.orm import StructureData, Dict
from aiida.common import AttributeDict

from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.workflows.eos import FleurEosWorkChain
from aiida_fleur.workflows.base_relax import FleurBaseRelaxWorkChain

from aiida_fleur.data.fleurinp import FleurinpData


class FleurCreateMagneticWorkChain(WorkChain):
    """
        This workflow creates relaxed magnetic film on a substrate.
    """

    _workflowversion = "0.1.1"

    _wf_default = {
        'lattice': 'fcc',
        'miller': [[-1, 1, 0],
                   [0, 0, 1],
                   [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,
        'size': (1, 1, 5),
        'replacements': {0: 'Fe', -1: 'Fe'},
        'decimals': 10,
        'pop_last_layers': 1,

        'total_number_layers': 4,
        'num_relaxed_layers': 2
    }

    @classmethod
    def define(cls, spec):
        super(FleurCreateMagneticWorkChain, cls).define(spec)
        spec.expose_inputs(FleurEosWorkChain, namespace='eos', exclude=('structure', ))
        spec.expose_inputs(FleurBaseRelaxWorkChain, namespace='relax', exclude=('structure', ))
        spec.input("wf_parameters", valid_type=Dict, required=False)
        spec.input("eos_output", valid_type=Dict, required=False)
        spec.input("optimized_structure", valid_type=StructureData, required=False)

        spec.outline(
            cls.start,
            if_(cls.eos_needed)(
                cls.run_eos,
            ),
            if_(cls.relax_needed)(
                cls.run_relax,
            ),
            cls.make_magnetic
        )

        spec.output('magnetic_structure', valid_type=StructureData)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM',
                       message="Invalid workchain parameters.")
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG',
                       message="Invalid input configuration.")
        spec.exit_code(380, 'ERROR_NOT_SUPPORTED_LATTICE',
                       message="Specified substrate has to be bcc or fcc.")
        spec.exit_code(382, 'ERROR_RELAX_FAILED',
                       message="Relaxation calculation failed.")

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
        inputs.structure = self.create_substrate_bulk()

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

    def create_substrate_bulk(self):
        """
        Create a bulk structure of a substrate.
        """
        lattice = self.ctx.wf_dict['lattice']
        if lattice == 'fcc':
            from ase.lattice.cubic import FaceCenteredCubic
            structure_factory = FaceCenteredCubic
        elif lattice == 'bcc':
            from ase.lattice.cubic import BodyCenteredCubic
            structure_factory = BodyCenteredCubic
        else:
            return self.exit_codes.ERROR_NOT_SUPPORTED_LATTICE

        miller = [[1, 0, 0],
                  [0, 1, 0],
                  [0, 0, 1]]
        host_symbol = self.ctx.wf_dict['host_symbol']
        latticeconstant = self.ctx.wf_dict['latticeconstant']
        size = (1, 1, 1)
        structure = structure_factory(miller=miller, symbol=host_symbol, pbc=(1, 1, 1),
                                      latticeconstant=latticeconstant, size=size)

        return StructureData(ase=structure)

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report('INFO: started Create Magnetic Film'
                    ' workflow version {}\n'.format(self._workflowversion))

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.energy_dict = []

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = copy.deepcopy(self._wf_default)
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = []
        for key in wf_dict.keys():
            if key not in wf_default.keys():
                extra_keys.append(key)
        if extra_keys:
            error = 'ERROR: input wf_parameters for Create Magnetic contains extra keys: {}'.format(
                extra_keys)
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        inputs = self.inputs
        if inputs.eos:
            self.report('INFO: EOS workchain will be submitted')
            self.ctx.eos_needed = True
            self.ctx.relax_needed = True
            if 'eos_output' in inputs:
                self.report('ERROR: you specified both eos_output and eos wc inputs.')
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if not inputs.relax:
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
                if not inputs.relax:
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
                    if inputs.relax:
                        if inputs.relax:
                            self.report('ERROR: relax wc input was given but relax is not needed.')
                            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
                else:
                    self.ctx.eos_needed = False
                    self.ctx.relax_needed = True
                    self.report('INFO: relaxation will be continued; no EOS')
                    if inputs.relax:
                        if not inputs.relax:
                            self.report('ERROR: relax wc input was not given but relax is needed.')
                            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG

    def relax_needed(self):
        """
        Returns true if interlayer relaxation should be performed.
        """
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
            inputs.scf.structure = self.create_film_to_relax()

            if not isinstance(inputs.scf.structure, StructureData):
                return inputs, inputs.scf.structure

        return inputs, None

    def create_film_to_relax(self):
        """
        Create a film structure those interlayers will be relaxed.
        """
        from aiida_fleur.tools.StructureData_util import create_manual_slab_ase, center_film

        miller = self.ctx.wf_dict['miller']
        host_symbol = self.ctx.wf_dict['host_symbol']
        if not self.ctx.eos_needed:
            eos_output = self.inputs.eos_output
        else:
            eos_output = self.ctx.eos_wc.outputs.output_eos_wc_para
        scaling_parameter = eos_output.get_dict()['scaling_gs']
        latticeconstant = self.ctx.wf_dict['latticeconstant'] * scaling_parameter
        size = self.ctx.wf_dict['size']
        replacements = self.ctx.wf_dict['replacements']
        pop_last_layers = self.ctx.wf_dict['pop_last_layers']
        decimals = self.ctx.wf_dict['decimals']
        structure = create_manual_slab_ase(miller=miller, host_symbol=host_symbol,
                                           latticeconstant=latticeconstant, size=size,
                                           replacements=replacements, decimals=decimals,
                                           pop_last_layers=pop_last_layers)

        self.ctx.substrate = create_manual_slab_ase(miller=miller, host_symbol=host_symbol,
                                                    latticeconstant=latticeconstant, size=(1, 1, 1),
                                                    replacements=None, decimals=decimals)

        centered_structure = center_film(StructureData(ase=structure))

        return centered_structure

    def make_magnetic(self):
        """
        Analuses outputs of previous steps and generated the final
        structure suitable for magnetic film calculations.
        """
        from aiida_fleur.tools.StructureData_util import magnetic_slab_from_relaxed

        if not self.ctx.relax_wc.is_finished_ok:
            return self.exit_codes.ERROR_RELAX_FAILED

        if self.ctx.relax_needed:
            optimized_structure = self.ctx.relax_wc.outputs.optimized_structure
        else:
            optimized_structure = self.inputs.optimized_structure

        magnetic = magnetic_slab_from_relaxed(optimized_structure, self.ctx.substrate,
                                              self.ctx.wf_dict['total_number_layers'],
                                              self.ctx.wf_dict['num_relaxed_layers'])

        magnetic = save_structure(magnetic)

        self.out('magnetic_structure', magnetic)


@cf
def save_structure(structure):
    """
    Save a structure data node to provide correct provenance.
    """
    structure_return = structure.clone()
    return structure_return
