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
This module contains useful methods for initializing or modifying a n_mmp_mat file
for LDA+U via the FleurinpModifier
"""
from __future__ import absolute_import
from __future__ import print_function
import numpy as np
from aiida_fleur.tools.xml_util import eval_xpath, eval_xpath2
from aiida_fleur.tools.xml_util import get_xml_attribute, convert_to_int

def set_nmmpmat(fleurinp_tree_copy, nmmp_lines_copy, species_name, orbital, spin,\
                occStates=None, denmat=None, phi=None, theta=None):
    """Routine sets the block in the n_mmp_mat file specified by species_name, orbital and spin
    to the desired density matrix

    :param fleurinp_tree_copy: an xmltree that represents inp.xml
    :param nmmp_lines_copy: list of lines in the n_mmp_mat file
    :param species_name: string, name of the species you want to change
    :param orbital: integer, orbital quantum number of the LDA+U procedure to be modified
    :param spin: integer, specifies which spin block should be modified
    :param occStates: list, sets the diagonal elements of the density matrix and everything
                      else to zero
    :param denmat: matrix, specify the density matrix explicitely
    :param phi: float, optional angle (radian), by which to rotate the density matrix before writing it
    :param theta: float, optional angle (radian), by which to rotate the density matrix before writing it

    :raises ValueError: If something in the input is wrong
    :raises KeyError: If no LDA+U procedure is found on a species
    """

    #All lda+U procedures have to be considered since we need to keep the order
    ldau_xpath = '/fleurInput/atomSpecies/species/ldaU'
    magnetism_xpath = '/fleurInput/calculationSetup/magnetism'

    if species_name == 'all':
        species_xpath = '/fleurInput/atomSpecies/species'
    elif species_name[:4] == 'all-':  #format all-<string>
        species_xpath = '/fleurInput/atomSpecies/species[contains(@name,"{}")]'.format(species_name[4:])
    else:
        species_xpath = '/fleurInput/atomSpecies/species[@name = "{}"]'.format(species_name)

    all_species = eval_xpath2(fleurinp_tree_copy, species_xpath)

    #Get number of spins (TODO for develop version also read l_mtnocoPot)
    mag_elem = eval_xpath(fleurinp_tree_copy, magnetism_xpath)
    nspins = convert_to_int(get_xml_attribute(mag_elem, 'jspins'), suc_return=False)

    if spin > nspins:
        raise ValueError(f'Invalid input: spin {spin} requested, but input has only {nspins} spins')

    all_ldau = eval_xpath2(fleurinp_tree_copy, ldau_xpath)
    numRows = nspins * 14 * len(all_ldau)

    #Check that numRows matches the number of lines in nmmp_lines_copy
    #If not either there was an n_mmp_mat file present in Fleurinp before and a lda+u calculation
    #was added or removed or the n_mmp_mat file was initialized and after the fact lda+u procedures were added
    #or removed. In both cases the resolution of this modification is very involved so we throw an error
    if nmmp_lines_copy is not None:
        #Remove blank lines
        while '' in nmmp_lines_copy:
            nmmp_lines_copy.remove('')
        if numRows != len(nmmp_lines_copy):
            raise ValueError('The number of lines in n_mmp_mat does not match the number expected from '+\
                             'the inp.xml file. Either remove the existing file before making modifications '+\
                             'and only use set_nmmpmat after all modifications to the inp.xml')

    if phi is not None or theta is not None:
        if phi is None:
            phi = 0.0
        if theta is None:
            theta = 0.0
        d_wigner = get_wigner_matrix(orbital, phi, theta)

    for species in all_species:
        current_name = get_xml_attribute(species, 'name')

        #Determine the place at which the given U procedure occurs
        ldau_index = None
        for index, ldau in enumerate(all_ldau):
            ldau_species = get_xml_attribute(ldau.getparent(), 'name')
            ldau_orbital = convert_to_int(get_xml_attribute(ldau, 'l'), suc_return=False)
            if current_name == ldau_species and ldau_orbital == orbital:
                ldau_index = index

        if ldau_index is None:
            raise KeyError(f'No LDA+U procedure found on species {current_name} with l={orbital}')

        if occStates is not None:
            #diagonal density matrix
            denmatpad = np.zeros((7, 7), dtype=complex)

            #Fill out the outer states with zero
            occStatespad = np.zeros(7, dtype=complex)
            occStatespad[3 - orbital:4 + orbital] = occStates[:]

            for i, occ in enumerate(occStatespad):
                denmatpad[i, i] = occ
        elif denmat is not None:
            #density matrix is completely specified
            denmatpad = np.zeros((7, 7), dtype=complex)
            denmatpad[3 - orbital:4 + orbital, 3 - orbital:4 + orbital] = denmat
        else:
            raise ValueError('Invalid definition of density matrix. Provide either occStates or denmat')

        if phi is not None and theta is not None:
            #Rotate the density matrix
            denmatpad = d_wigner.T.conj().dot(denmatpad.dot(d_wigner))

        #check if fleurinp has a specified n_mmp_mat file if not initialize it with 0
        if nmmp_lines_copy is None:
            nmmp_lines_copy = []
            for index in range(numRows):
                nmmp_lines_copy.append(''.join(map(str, [f'{0.0:20.13f}' for x in range(7)])))

        #Select the right block from n_mmp_mat and overwrite it with denmatpad
        startRow = ((spin - 1) * len(all_ldau) + ldau_index) * 14
        for index in range(startRow, startRow + 14):
            currentLine = index - startRow
            currentRow = currentLine // 2
            if currentLine % 2 == 0:
                #Line ends with a real part
                nmmp_lines_copy[index] = ''.join(map(str, [f'{x.real:20.13f}{x.imag:20.13f}'\
                                                           for x in denmatpad[currentRow, :3]])) +\
                                         f'{denmatpad[currentRow, 3].real:20.13f}'
            else:
                #Line begins with a imaginary part
                nmmp_lines_copy[index] = f'{denmatpad[currentRow, 3].imag:20.13f}' +\
                                         ''.join(map(str, [f'{x.real:20.13f}{x.imag:20.13f}'\
                                                           for x in denmatpad[currentRow, 4:]]))

    return nmmp_lines_copy


def validate_nmmpmat(fleurinp_tree, nmmp_lines):
    """
    Checks that the given nmmp_lines is valid with the given fleurinp_tree

    Checks that the number of blocks is as expected from the inp.xml and each
    block does not contain non-zero elements outside their size given by the
    orbital quantum number in the inp.xml. Additionally the occupations, i.e.
    diagonal elements are checked that they are in between 0 and the maximum
    possible occupation

    :param fleurinp_tree_copy: an xmltree that represents inp.xml
    :param nmmp_lines_copy: list of lines in the n_mmp_mat file

    :raises ValueError: if any of the above checks are violated.
    """

    #First check the number of ldau procedures
    ldau_xpath = '/fleurInput/atomSpecies/species/ldaU'
    magnetism_xpath = '/fleurInput/calculationSetup/magnetism'

    #Get number of spins (TODO for develop version also read l_mtnocoPot)
    mag_elem = eval_xpath(fleurinp_tree, magnetism_xpath)
    nspins = convert_to_int(get_xml_attribute(mag_elem, 'jspins'), suc_return=False)

    all_ldau = eval_xpath2(fleurinp_tree, ldau_xpath)
    numRows = nspins * 14 * len(all_ldau)

    tol = 0.01
    if nspins > 1:
        maxOcc = 1.0
    else:
        maxOcc = 2.0

    #Check that numRows matches the number of lines in nmmp_lines
    if nmmp_lines is not None:
        #Remove blank lines
        while '' in nmmp_lines:
            nmmp_lines.remove('')
        if numRows != len(nmmp_lines):
            raise ValueError('The number of lines in n_mmp_mat does not match the number expected from '+\
                             'the inp.xml file.')
    else:
        return

    #Now check for each block if the numbers make sense
    #(no numbers outside the valid area and no nonsensical occupations)
    for ldau_index, ldau in enumerate(all_ldau):

        orbital = convert_to_int(get_xml_attribute(ldau, 'l'), suc_return=False)
        species_name = get_xml_attribute(ldau.getparent(), 'name')

        for spin in range(nspins):
            startRow = (spin * len(all_ldau) + ldau_index) * 14

            for index in range(startRow, startRow + 14):
                currentLine = index - startRow
                currentRow = currentLine // 2

                line = nmmp_lines[index].split('    ')
                while '' in line:
                    line.remove('')
                nmmp = np.array([float(x) for x in line])

                outside_val = False
                if abs(currentRow - 3) > orbital:
                    if any(np.abs(nmmp) > 1e-12):
                        outside_val = True

                if currentLine % 2 == 0:
                    #m=-3 to m=0 real part
                    if any(np.abs(nmmp[:(3 - orbital) * 2]) > 1e-12):
                        outside_val = True

                else:
                    #m=0 imag part to m=3
                    if any(np.abs(nmmp[orbital * 2 + 1:]) > 1e-12):
                        outside_val = True

                if outside_val:
                    raise ValueError(f'Found value outside of valid range in for species {species_name}, spin {spin+1}'
                                     f' and l={orbital}')

                invalid_diag = False
                if spin < 2:
                    if currentRow - 3 <= 0 and currentLine % 2 == 0:
                        if nmmp[currentRow * 2] < -tol or nmmp[currentRow * 2] > maxOcc + tol:
                            invalid_diag = True
                    else:
                        if nmmp[(currentRow - 3) * 2 - 1] < -tol or nmmp[(currentRow - 3) * 2 - 1] > maxOcc + tol:
                            invalid_diag = True

                if invalid_diag:
                    raise ValueError(f'Found invalid diagonal element for species {species_name}, spin {spin+1}'
                                     f' and l={orbital}')


def get_wigner_matrix(l, phi, theta):
    """Produces the wigner rotation matrix for the density matrix

   :param l: int, orbital quantum number
   :param phi: float, angle (radian) corresponds to euler angle alpha
   :param theta: float, angle (radian) corresponds to euler angle beta
   """
    d_wigner = np.zeros((7, 7), dtype=complex)
    for m in range(-l, l + 1):
        for mp in range(-l, l + 1):
            base = np.sqrt(fac(l + m) * fac(l - m) * fac(l + mp) * fac(l - mp))
            base *= np.exp(-1j * phi * mp)

            for x in range(max(0, m - mp), min(l - mp, l + m) + 1):
                denom = fac(l - mp - x) * fac(l + m - x) * fac(x) * fac(x + mp - m)

                d_wigner[m + 3, mp + 3] += base/denom * (-1)**x * np.cos(theta/2.0)**(2*l+m-mp-2*x) \
                                          * np.sin(theta/2.0)**(2*x+mp-m)

    return d_wigner


def fac(n):
    """Returns the factorial of n"""
    if n < 2:
        return 1
    else:
        return n * fac(n - 1)
