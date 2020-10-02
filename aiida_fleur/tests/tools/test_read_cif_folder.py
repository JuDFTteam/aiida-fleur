# -*- coding: utf-8 -*-
'''Contains tests for read and with work cif file routines.'''

from __future__ import absolute_import
from __future__ import print_function
import pytest


# read-cif_folder
@pytest.mark.skip(reason='Test not implemented')
def test_read_cif_folder_interface(temp_dir):
    """
    this test set reads in the cif files in the ../files/cif/ directory and subdirs
    it stores the datastructures, with some comments and extras.

    """
    import os
    from aiida_fleur.tools.read_cif_folder import read_cif_folder
    import aiida_fleur

    path = os.path.dirname(aiida_fleur.__file__)
    cif_folderpath = os.path.join(path, 'tests/files/cif/')
    out_filename = os.path.join(temp_dir, 'out.txt')

    #read_in
    structure_data, filenames = read_cif_folder(path=os.getcwd(),
                                                recursive=True,
                                                store=True,
                                                log=True,
                                                comments='Test_comment',
                                                extras={'test': 1},
                                                logfile_name=out_filename)

    structure_data, filenames = read_cif_folder(path=cif_folderpath,
                                                recursive=False,
                                                store=False,
                                                log=False,
                                                comments='',
                                                extras='')
    #test number of structurs written
    #test number of cif files written
    #test if extras are set right
    #test prov
    #test

    #read_in again
    # test if cif files are not rewritten.
    assert False
