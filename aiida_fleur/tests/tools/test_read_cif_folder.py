import pytest


# read-cif_folder
@pytest.mark.usefixtures("aiida_env")
def test_read_cif_folder_interface(aiida_env):
    """
    this test set reads in the cif files in the ../files/cif/ directory and subdirs
    it stores the datastructures, with some comments and extras.

    """
    import os
    from aiida_fleur.tools.read_cif_folder import read_cif_folder
    
    # preparation
    
    cif_folderpath = os.path.abspath('../files/cif/')
    print cif_folderpath
    #read_in
    structure_data, filenames = read_cif_folder(path=os.getcwd(), rekursive=True,
                                                store=False, log=False,
                                               comments='', extras='')
    #test number of structurs written
    #test number of cif files written
    #test if extras are set right
    #test prov
    #test
    pass

    #read_in again
    # test if cif files are not rewritten.
