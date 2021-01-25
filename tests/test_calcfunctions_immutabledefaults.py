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
'''
Tests if all calcfunctions we use have immutable defaultvalues,
otherwise the test for the corresponding calcfunction will fail.
If defaults are not immutable strange things can happen in aiida.

Also calcfunctions should not be inside a class, because that makes them not cacheable
'''

import inspect


def get_default_args(func):
    """
    Helpers to return the default kwargs of a given function
    """
    signature = inspect.signature(func)
    defaults = {}
    for key, val in signature.parameters.items():
        if val.default is not inspect.Parameter.empty:
            defaults[key] = val.default
    return defaults


def test_check_immutable_defaults():
    """Test if defaults of calcfunctions are immutable

    Is there a way to automatically collect all calcfunctions, without adding other
    register decorrators or so? Parsing source code? or integrate this in a git/precommit hook
    """

    from aiida_fleur.tools.merge_parameter import merge_parameter_cf
    from aiida_fleur.tools.create_kpoints_from_distance import create_kpoints_from_distance_parameter
    from aiida_fleur.tools.StructureData_util import center_film_wf, find_primitive_cell_wf, break_symmetry_wf, supercell, rescale
    from aiida_fleur.tools.read_cif_folder import wf_struc_from_cif

    from aiida_fleur.workflows.eos import eos_structures
    from aiida_fleur.workflows.create_magnetic_film import create_film_to_relax, create_substrate_bulk, magnetic_slab_from_relaxed_cf
    from aiida_fleur.workflows.corehole import prepare_struc_corehole_wf

    immutable = (str, type(None), tuple)

    calcfunction_list = [
        merge_parameter_cf, create_kpoints_from_distance_parameter, center_film_wf, find_primitive_cell_wf,
        break_symmetry_wf, supercell, rescale, wf_struc_from_cif, eos_structures, create_film_to_relax,
        create_substrate_bulk, magnetic_slab_from_relaxed_cf, prepare_struc_corehole_wf
    ]

    for calcf in calcfunction_list:
        defaults = get_default_args(calcf)
        for key, val in defaults.items():
            if not isinstance(val, immutable):
                message = ('Default value of calcfunction not immutable: \n'
                           'function: {}\n'
                           'kwarg: {} : {}'.format(calcf, key, val))
                # Add reason explaination, https://github.com/JuDFTteam/aiida-fleur/issues/85
                assert False, message
