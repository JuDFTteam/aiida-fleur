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
Common base for the three force-theorem workchains: MAE, SSDisp and DMI.

All three run the same shape -- optionally converge an SCF, modify ``inp.xml``, then submit one
FLEUR force-theorem calculation and collect its energies -- and their methods had been kept in
step by copy-paste. The four methods here were byte-identical across the three except for two
label strings and the name of the output node, so they are parametrised by the class attributes
below rather than duplicated.

The methods that genuinely differ per workchain -- ``start``, ``converge_scf``,
``get_inputs_scf``, ``change_fleurinp``, ``force_after_scf``, ``get_results`` and
``return_results`` -- stay in the subclasses. They carry the physics (which ``inp.xml`` changes
to apply, how to read the force-theorem output) and are not the same code with different names.
"""
from aiida.engine import WorkChain, ToContext, if_
from aiida.orm import Code, Dict, RemoteData

from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, validate_fleur_entry_points
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.workflows.scf import FleurScfWorkChain


class FleurForceTheoremWorkChain(WorkChain):
    """
    Shared skeleton of FleurMaeWorkChain, FleurSSDispWorkChain and FleurDMIWorkChain.

    A subclass must set the three class attributes below and implement the physics methods.
    """

    #: link label of the result Dict, e.g. 'output_mae_wc_para'
    _OUTPUT_NAME = None
    #: metadata label given to the force-theorem FLEUR calculation
    _FT_LABEL = None
    #: metadata description given to that calculation
    _FT_DESCRIPTION = None

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           },
                           namespace='scf')
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote_data', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('options', valid_type=Dict, required=False)
        #reject an illegal combination of starting points at submission instead of
        #creating a node that aborts in its first step
        spec.inputs.validator = validate_fleur_entry_points

        spec.outline(cls.start,
                     if_(cls.scf_needed)(
                         cls.converge_scf,
                         cls.force_after_scf,
                     ).else_(
                         cls.force_wo_scf,
                     ), cls.get_results, cls.return_results)

        spec.output(cls._OUTPUT_NAME, valid_type=Dict)

        # exit codes
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
        spec.exit_code(336, 'ERROR_FORCE_THEOREM_FAILED', message='Force theorem calculation failed.')

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails sometimes
        self.ctx.errors.append(errormsg)
        self.return_results()

    def force_wo_scf(self):
        """
        Submit FLEUR force theorem calculation using input remote
        """
        self.report('INFO: run Force theorem calculations')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder from the inputs
        remote = self.inputs.remote_data

        label = self._FT_LABEL
        description = self._FT_DESCRIPTION

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code,
                                          remote,
                                          fleurin,
                                          options,
                                          label,
                                          description,
                                          settings,
                                          add_comp_para=self.ctx.wf_dict['add_comp_para'])
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(f_t=future)

    def scf_needed(self):
        """
        Returns True if SCF WC is needed.
        """
        return self.ctx.scf_needed
