# -*- coding: utf-8 -*-
'''Contains tests for the set_nmmpmat routine used for modifying the
   density matrix for LDA+U calculations.'''

from __future__ import absolute_import
import os
import pytest
import aiida_fleur
import numpy as np

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_INP_XML_PATH = os.path.join(aiida_path, '../tests/files/inpxml/GaAsMultiForceXML/inp.xml')
TEST_NMMPMAT_PATH = os.path.join(aiida_path, '../tests/files/n_mmp_mat/n_mmp_mat_GaAsMultiForceXML')


def test_set_nmmpmat_nofile(inpxml_etree, file_regression):
    """Test setting of nmmpmat with no initial nmmpmat file given"""
    from aiida_fleur.tools.set_nmmpmat import set_nmmpmat
    etree = inpxml_etree(TEST_INP_XML_PATH)

    nmmp_lines = None
    nmmp_lines = set_nmmpmat(etree, nmmp_lines, species_name='Ga-1', orbital=2, spin=1, occStates=[1, 2, 3, 4, 5])
    nmmp_lines = set_nmmpmat(etree, nmmp_lines, 'As-2', orbital=1, spin=1, denmat=[[1, -2, 3], [4, -5, 6], [7, -8, 9]])

    file_regression.check(prepare_for_file_dump(nmmp_lines))


def test_set_nmmpmat_file(inpxml_etree, file_regression):
    """Test setting of nmmpmat with initial nmmpmat file given"""
    from aiida_fleur.tools.set_nmmpmat import set_nmmpmat
    etree = inpxml_etree(TEST_INP_XML_PATH)

    with open(TEST_NMMPMAT_PATH, mode='r') as nmmpfile:
        nmmp_lines = nmmpfile.read().split('\n')

    nmmp_lines = set_nmmpmat(etree, nmmp_lines, species_name='Ga-1', orbital=2, spin=1, occStates=[1, 2, 3, 4, 5])
    nmmp_lines = set_nmmpmat(etree, nmmp_lines, 'As-2', orbital=1, spin=1, denmat=[[1, -2, 3], [4, -5, 6], [7, -8, 9]])

    file_regression.check(prepare_for_file_dump(nmmp_lines))


def test_set_nmmpmat_file_get_wigner_matrix(inpxml_etree, file_regression):
    """Test get_wigner_matrix by calling set_nmmpmat_file with theta, or phi != None"""
    from aiida_fleur.tools.set_nmmpmat import set_nmmpmat

    etree = inpxml_etree(TEST_INP_XML_PATH)

    nmmp_lines = None
    nmmp_lines = set_nmmpmat(etree,
                             nmmp_lines,
                             species_name='Ga-1',
                             orbital=1,
                             spin=1,
                             occStates=[1, 0, 1],
                             theta=np.pi / 2.0)
    nmmp_lines = set_nmmpmat(etree,
                             nmmp_lines,
                             'As-2',
                             orbital=1,
                             spin=1,
                             denmat=[[1, 0, 1], [0, 0, 0], [1, 0, 1]],
                             phi=np.pi / 4.0,
                             theta=np.pi / 2.0)

    file_regression.check(prepare_for_file_dump(nmmp_lines))


def test_validate_nmmpmat(inpxml_etree):
    """Test validation method of nmmpmat file together with inp.xml file"""
    from aiida_fleur.tools.set_nmmpmat import set_nmmpmat, validate_nmmpmat
    etree = inpxml_etree(TEST_INP_XML_PATH)

    with open(TEST_NMMPMAT_PATH, mode='r') as nmmpfile:
        nmmp_lines_orig = nmmpfile.read().split('\n')

    validate_nmmpmat(etree, nmmp_lines_orig)  #should not raise

    #Test number of lines error
    nmmp_lines = nmmp_lines_orig
    nmmp_lines.append('0.0')
    with pytest.raises(ValueError):
        validate_nmmpmat(etree, nmmp_lines)
    nmmp_lines.remove('0.0')

    #Test invalid diagonal element error
    nmmp_lines = nmmp_lines_orig
    nmmp_lines = set_nmmpmat(etree, nmmp_lines, species_name='Ga-1', orbital=2, spin=1, occStates=[1, 2, 3, 4, 5])
    nmmp_lines = set_nmmpmat(etree, nmmp_lines, 'As-2', orbital=1, spin=1, denmat=[[1, -2, 3], [4, -5, 6], [7, -8, 9]])
    with pytest.raises(ValueError):
        validate_nmmpmat(etree, nmmp_lines)

    #Test invalid outsied value error
    nmmp_lines = nmmp_lines_orig
    nmmp_lines[
        0] = '     0.0000000000000     9.0000000000000     0.0000000000000     0.0000000000000     0.0000000000000     0.0000000000000     0.0000000000000'

    with pytest.raises(ValueError):
        validate_nmmpmat(etree, nmmp_lines)

def prepare_for_file_dump(file_lines):
    """
    Join lines together with linebreaks and remove negative zeros
    """
    return '\n'.join([line.replace('-0.0000000000000', ' 0.0000000000000') for line in file_lines])

