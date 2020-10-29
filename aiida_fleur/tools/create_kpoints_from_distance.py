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
Calculation function to compute a k-point mesh for a structure with a
guaranteed minimum k-point distance.
"""
from aiida.engine import calcfunction
from .merge_parameter import merge_parameter


@calcfunction
def create_kpoints_from_distance_parameter(structure, distance, force_parity, calc_parameters=None):
    """
    Generate a uniformly spaced kpoint mesh for a given structure
    and merge it into a given calc_parameter node or create a new one

    The spacing between kpoints in reciprocal space is guaranteed to be at least the defined distance.
    :param structure: the StructureData to which the mesh should apply
    :param distance: a Float with the desired distance between kpoints in reciprocal space
    :param force_parity: a Bool to specify whether the generated mesh should maintain parity
    :param calc_parameters: a Dict which contains calc parameters for inpgen
    :returns: Dict node with the generated mesh, merged with given calc_parameters
    """

    new_calc_para = create_kpoints_from_distance_parameter_ncf(structure,
                                                               distance,
                                                               force_parity,
                                                               calc_parameters=calc_parameters)
    return new_calc_para


def create_kpoints_from_distance_parameter_ncf(structure, distance, force_parity, calc_parameters=None):
    """
    Generate a uniformly spaced kpoint mesh for a given structure
    and merge it into a given calc_parameter node or create a new one.
    Does not keep the provenance

    The spacing between kpoints in reciprocal space is guaranteed to be at least the defined distance.
    :param structure: the StructureData to which the mesh should apply
    :param distance: a Float with the desired distance between kpoints in reciprocal space
    :param force_parity: a Bool to specify whether the generated mesh should maintain parity
    :param calc_parameters: a Dict which contains calc parameters for inpgen
    :returns: Dict node with the generated mesh, merged with given calc_parameters
    :returns: Dict node with the generated mesh
    """
    import numpy
    from numpy import linalg
    from aiida.orm import Dict

    epsilon = 1E-5

    the_cell = structure.cell
    reciprocal_cell = 2. * numpy.pi * numpy.linalg.inv(numpy.array(the_cell)).transpose()

    kpointsmesh = [
        max(int(numpy.ceil(round(numpy.linalg.norm(b) / distance.value, 5))), 1) if pbc else 1
        for pbc, b in zip(structure.pbc, reciprocal_cell)
    ]
    if force_parity.value:
        kpointsmesh = [k + (k % 2) if pbc else 1 for pbc, k in zip(structure.pbc, kpointsmesh)]

    lengths_vector = [linalg.norm(vector) for vector in the_cell]

    is_symmetric_cell = all(abs(length - lengths_vector[0]) < epsilon for length in lengths_vector)
    is_symmetric_mesh = all(length == kpointsmesh[0] for length in kpointsmesh)

    # If the vectors of the cell all have the same length, the kpoint mesh should be isotropic as well
    if is_symmetric_cell and not is_symmetric_mesh:
        nkpoints = max(kpointsmesh)
        kpointsmesh = [nkpoints, nkpoints, nkpoints]

    new_calc_para = Dict(dict={'kpt': {'div1': kpointsmesh[0], 'div2': kpointsmesh[1], 'div3': kpointsmesh[2]}})

    if calc_parameters is not None:
        # Override false, since we want to keep other kpts keys in calc_parameters
        new_calc_para = merge_parameter(new_calc_para, calc_parameters, overwrite=False, merge=True)

    return new_calc_para
