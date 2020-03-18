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
    In this module you find the workflow 'FleurRelaxWorkChain' for geometry optimization.
"""
from __future__ import absolute_import
from __future__ import print_function
import copy
import numpy as np

import six

from aiida.engine import WorkChain, ToContext, while_
from aiida.engine import calcfunction as cf
from aiida.orm import load_node
from aiida.orm import StructureData, Dict
from aiida.common import AttributeDict
from aiida.common.exceptions import NotExistent

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.calculation.fleur import FleurCalculation as FleurCalc


class FleurRelaxWorkChain(WorkChain):
    """
    This workflow performs structure optimization.
    """

    _workflowversion = "0.1.3"

    _wf_default = {'relax_iter': 5, 'film_distance_relaxation': False, 'force_criterion': 0.001}

    @classmethod
    def define(cls, spec):
        super(FleurRelaxWorkChain, cls).define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.input("wf_parameters", valid_type=Dict, required=False)

        spec.outline(
            cls.start,
            cls.converge_scf,
            cls.check_failure,
            while_(cls.condition)(
                cls.generate_new_fleurinp,
                cls.converge_scf,
                cls.check_failure,
            ),
            cls.get_results,
            cls.return_results,
        )

        spec.output('out', valid_type=Dict)
        spec.output('optimized_structure', valid_type=StructureData)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message="Invalid workchain parameters.")
        spec.exit_code(
            350,
            'ERROR_DID_NOT_RELAX',
            message="Optimization cycle did not lead to convergence of forces."
        )
        spec.exit_code(351, 'ERROR_SCF_FAILED', message="SCF Workchains failed for some reason.")
        spec.exit_code(
            352,
            'ERROR_NO_RELAX_OUTPUT',
            message="Found no relaxed structure info in the output of SCF"
        )
        spec.exit_code(352, 'ERROR_NO_SCF_OUTPUT', message="Found no SCF output")
        spec.exit_code(
            311,
            'ERROR_VACUUM_SPILL_RELAX',
            message='FLEUR calculation failed because an atom spilled to the'
            'vacuum during relaxation'
        )
        spec.exit_code(
            313, 'ERROR_MT_RADII_RELAX', message='Overlapping MT-spheres during relaxation.'
        )

    def start(self):
        """
        Retrieve and initialize paramters of the WorkChain
        """
        self.report(
            'INFO: started structure relaxation workflow version {}\n'
            ''.format(self._workflowversion)
        )

        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        # Pre-initialization of some variables
        self.ctx.loop_count = 0
        self.ctx.forces = []
        self.ctx.final_cell = None
        self.ctx.final_atom_positions = None
        self.ctx.pbc = None
        self.ctx.reached_relax = True
        self.ctx.scf_res = None

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
            error = 'ERROR: input wf_parameters for Relax contains extra keys: {}'.format(
                extra_keys
            )
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

    def converge_scf(self):
        """
        Submits :class:`aiida_fleur.workflows.scf.FleurScfWorkChain`.
        """
        inputs = {}
        if self.ctx.loop_count:
            inputs = self.get_inputs_scf()
        else:
            inputs = self.get_inputs_first_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(scf_res=res)

    def get_inputs_first_scf(self):
        """
        Initialize inputs for the first iteration.
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        input_scf.metadata.label = 'SCF_forces'
        input_scf.metadata.description = 'The SCF workchain converging forces, part of the Relax'

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()

        if 'inpxml_changes' not in scf_wf_dict:
            scf_wf_dict['inpxml_changes'] = []

        scf_wf_dict['mode'] = 'force'

        if self.ctx.wf_dict['film_distance_relaxation']:
            scf_wf_dict['inpxml_changes'].append((
                'set_atomgr_att', {
                    'attributedict': {
                        'force': [('relaxXYZ', 'FFT')]
                    },
                    'species': 'all'
                }
            ))

        input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        return input_scf

    def get_inputs_scf(self):
        """
        Initializes inputs for further iterations.
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        if 'structure' in input_scf:
            del input_scf.structure
            del input_scf.inpgen
            del input_scf.calc_parameters

        if 'wf_parameters' not in input_scf:
            scf_wf_dict = {}
        else:
            scf_wf_dict = input_scf.wf_parameters.get_dict()

        scf_wf_dict['mode'] = 'force'
        input_scf.wf_parameters = Dict(dict=scf_wf_dict)

        scf_wc = self.ctx.scf_res
        last_calc = load_node(scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])

        input_scf.remote_data = last_calc.outputs.remote_folder
        if self.ctx.new_fleurinp:
            input_scf.fleurinp = self.ctx.new_fleurinp

        return input_scf

    def check_failure(self):
        """
        Throws an exit code if scf failed
        """
        try:
            scf_wc = self.ctx.scf_res
        except AttributeError:
            message = 'ERROR: Something went wrong I do not have new atom positions calculation'
            self.control_end_wc(message)
            return self.exit_codes.ERROR_NO_SCF_OUTPUT

        if not scf_wc.is_finished_ok:
            exit_statuses = FleurScfWorkChain.get_exit_statuses(['ERROR_FLEUR_CALCULATION_FAILED'])
            if scf_wc.exit_status == exit_statuses[0]:
                fleur_calc = load_node(
                    scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid']
                )
                if fleur_calc.exit_status == FleurCalc.get_exit_statuses([
                    'ERROR_VACUUM_SPILL_RELAX'
                ])[0]:
                    self.control_end_wc('Failed due to atom and vacuum overlap')
                    return self.exit_codes.ERROR_VACUUM_SPILL_RELAX
                elif fleur_calc.exit_status == FleurCalc.get_exit_statuses(['ERROR_MT_RADII_RELAX']
                                                                           )[0]:
                    self.control_end_wc('Failed due to MT overlap')
                    return self.exit_codes.ERROR_MT_RADII_RELAX
            return self.exit_codes.ERROR_SCF_FAILED

    def condition(self):
        """
        Checks if relaxation criteria is achieved.

        :return: True if structure is optimised and False otherwise
        """
        scf_wc = self.ctx.scf_res

        try:
            self.ctx.forces.append(scf_wc.outputs.output_scf_wc_para.dict.force_largest)
        except AttributeError:
            # message = 'ERROR: Did not manage to read the largest force'
            # self.control_end_wc(message)
            # return self.exit_codes.ERROR_RELAX_FAILED
            return False

        largest_now = abs(self.ctx.forces[-1])

        if largest_now < self.ctx.wf_dict['force_criterion']:
            self.report(
                'Structure is converged to the largest force'
                '{}'.format(self.ctx.forces[-1])
            )
            return False

        self.ctx.loop_count = self.ctx.loop_count + 1
        if self.ctx.loop_count == self.ctx.wf_dict['relax_iter']:
            self.ctx.reached_relax = False
            self.report(
                'INFO: Reached optimization iteration number {}. Largest force is {}, '
                'force criterion is {}'.format(
                    self.ctx.loop_count + 1, largest_now, self.ctx.wf_dict['force_criterion']
                )
            )
            return False

        self.report(
            'INFO: submit optimization iteration number {}. Largest force is {}, '
            'force criterion is {}'.format(
                self.ctx.loop_count + 1, largest_now, self.ctx.wf_dict['force_criterion']
            )
        )

        return True

    def generate_new_fleurinp(self):
        """
        This function fetches relax.xml from the previous iteration and calls
        :meth:`~aiida_fleur.workflows.relax.FleurRelaxWorkChain.analyse_relax()`.
        New FleurinpData is stored in the context.
        """
        # TODO do we loose provenance here, which we like to keep?
        scf_wc = self.ctx.scf_res
        last_calc = load_node(scf_wc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid'])
        try:
            relax_parsed = last_calc.outputs.relax_parameters
        except NotExistent:
            return self.exit_codes.ERROR_NO_SCF_OUTPUT

        new_fleurinp = self.analyse_relax(relax_parsed)

        self.ctx.new_fleurinp = new_fleurinp

    @staticmethod
    def analyse_relax(relax_dict):
        """
        This function generates a new fleurinp analysing parsed relax.xml from the previous
        calculation.

        **NOT IMPLEMENTED YET**

        :param relax_dict: parsed relax.xml from the previous calculation
        :return new_fleurinp: new FleurinpData object that will be used for next relax iteration
        """
        # TODO: implement this function, now always use relax.xml generated in FLEUR
        if False:
            return 1

        return None

    def get_results(self):
        """
        Generates results of the workchain.
        Creates a new structure data node which is an
        optimized structure.
        """
        try:
            relax_out = self.ctx.scf_res.outputs.last_fleur_calc_output
        except NotExistent:
            return self.exit_codes.ERROR_NO_SCF_OUTPUT

        relax_out = relax_out.get_dict()

        try:
            cell = relax_out['relax_brav_vectors']
            atom_positions = relax_out['relax_atom_positions']
            film = relax_out['film']
        except KeyError:
            return self.exit_codes.ERROR_NO_RELAX_OUTPUT

        self.ctx.final_cell = cell
        self.ctx.final_atom_positions = atom_positions

        if film == 'True':
            self.ctx.pbc = (True, True, False)
        else:
            self.ctx.pbc = (True, True, True)

    def return_results(self):
        """
        This function stores results of the workchain into the output nodes.
        """
        #TODO maybe we want to have a more detailed array output node with the force and
        # position history of all atoms?
        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors,
            'force': self.ctx.forces,
            'force_iter_done': self.ctx.loop_count,
            'last_scf_wc_uuid': self.ctx.scf_res.uuid
        }

        if self.ctx.final_cell:
            structure = StructureData(cell=self.ctx.final_cell)
            bohr_a = 0.52917721092

            for atom in self.ctx.final_atom_positions:
                np_cell = np.array(self.ctx.final_cell)
                np_pos = np.array(atom[1:]) * bohr_a
                pos_abs = list(np.dot(np_cell, np_pos))
                if self.ctx.pbc == (True, True, True):
                    structure.append_atom(
                        position=(pos_abs[0], pos_abs[1], pos_abs[2]), symbols=atom[0]
                    )
                else:  # assume z-direction is orthogonal to xy
                    structure.append_atom(
                        position=(pos_abs[0], pos_abs[1], atom[3] * bohr_a), symbols=atom[0]
                    )

            structure.pbc = self.ctx.pbc
            structure = save_structure(structure)
            self.out('optimized_structure', structure)

        out = save_output_node(Dict(dict=out))
        self.out('out', out)
        if not self.ctx.reached_relax:
            return self.exit_codes.ERROR_DID_NOT_RELAX

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. It will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards.
        """
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def save_structure(structure):
    """
    Save a structure data node to provide correct provenance.
    """
    structure_return = structure.clone()
    return structure_return


@cf
def save_output_node(out):
    """
    Save the out dict in the db to provide correct provenance.
    """
    out_wc = out.clone()
    return out_wc
