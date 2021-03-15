# -*- coding: utf-8 -*-
'''Contains tests for read and with work cif file routines.'''

import pytest


# read-cif_folder
#@pytest.mark.skip(reason='Test not implemented')
def test_read_cif_folder_interface(temp_dir):
    """
    this test set reads in the cif files in the ../files/cif/ directory and subdirs
    it stores the datastructures, with some comments and extras.

    """
    import os
    from aiida_fleur.tools.read_cif_folder import read_cif_folder
    import aiida_fleur
    from aiida import orm

    path = os.path.dirname(aiida_fleur.__file__)
    cif_folderpath = os.path.join(path, '../tests/files/cif/')
    out_filename = os.path.join(temp_dir, 'out.txt')
    add_extra = {'test': 1}
    #read_in
    structure_data, filenames = read_cif_folder(path=cif_folderpath,
                                                recursive=True,
                                                store=True,
                                                log=True,
                                                comments='Test_comment',
                                                extras=add_extra,
                                                logfile_name=out_filename)

    #test number of structurs written
    #test number of cif files written
    #test if extras are set right
    #test prov
    #test
    for structure in structure_data:
        assert isinstance(structure, orm.StructureData)
        assert structure.is_stored
        assert structure.extras['test'] == 1

    assert len(structure_data) == len(filenames)

    #read_in again
    structure_data, filenames = read_cif_folder(path=cif_folderpath,
                                                recursive=False,
                                                store=False,
                                                log=True,
                                                comments='',
                                                extras='myproject',
                                                logfile_name=out_filename)
    for structure in structure_data:
        assert isinstance(structure, orm.StructureData)
        assert not structure.is_stored
        assert 'test' not in structure.extras
        #assert structure.extras['specification'] == 'myproject'
        assert 'specification' not in structure.extras
        # extras get only written if structures are stored
    assert len(structure_data) == len(filenames)
