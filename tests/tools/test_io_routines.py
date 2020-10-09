# -*- coding: utf-8 -*-
''' Contains Tests of io routines within aiida-fleur. '''

from __future__ import absolute_import
import pytest


def test_write_results_to_file_interface():
    """
    is the basic file writter wraper working as indended
    """
    from aiida_fleur.tools.io_routines import write_results_to_file
    from os.path import isfile, abspath
    from os import remove
    #import os
    from numpy import array

    # testing some defaults
    inputhead = 'head\n'
    data = array([[1, 2], [3, 4]])
    destination = './outputfiletest'
    write_results_to_file(inputhead, data, destination=destination)
    isfile_ = isfile(abspath('./outputfiletest'))
    test_file = open(destination, 'r')
    content = test_file.read()
    test_file.close()

    content_exp = 'head\n1.00000000  3.00000000\n2.00000000  4.00000000\n'
    remove(destination)

    assert isfile_
    assert content == content_exp


# write_xps_spectra_datafile
@pytest.mark.skip(reason='Test not implemented')
def test_write_xps_spectra_datafile_interface():
    """
    is the xps data file writter working, is the file ok?
    """
    from aiida_fleur.tools.io_routines import write_xps_spectra_datafile

    #TODO how to test this?
    # provide all sample inputs and check contents of outputfile
    #assert 1 == 2
    assert False


def test_compress_fleuroutxml():
    """
    test the compress_fleuroutxml function, checks if right number of iterations is kept, or deleted.
    Further checks if new file is written and if eigenvalues are deleted.
    """

    from os.path import abspath, isfile
    from os import remove
    from lxml import etree
    from aiida_fleur.tools.xml_util import eval_xpath2
    from aiida_fleur.tools.io_routines import compress_fleuroutxml

    testfilepath = abspath('./files/outxml/BeTi_out.xml')
    dest_path = testfilepath.replace('.xml', '_test.xml')
    niter_file = 19
    xpath_iter = '/fleurOutput/scfLoop/iteration'
    xpath_eig = '/fleurOutput/scfLoop/iteration/eigenvalues'

    def get_npath(filepath, xpath):
        """helper function to get amount of a certain xpath eval in file"""

        xpath_iter = '/fleurOutput/scfLoop/iteration'
        parser = etree.XMLParser(recover=False)
        tree = etree.parse(filepath, parser)

        return len(eval_xpath2(tree.getroot(), xpath))

    # test new file exists, and right number of iteration, eig del
    compress_fleuroutxml(testfilepath, dest_file_path=dest_path, iterations_to_keep=15)
    isfile_ = isfile(abspath(dest_path))
    niter1 = get_npath(dest_path, xpath_iter)
    neig = get_npath(dest_path, xpath_eig)

    assert isfile  # check outfile
    assert niter1 == 15  # check if 15 iterations are kept
    assert neig == 0  # check if eigenvalues del

    compress_fleuroutxml(testfilepath, dest_file_path=dest_path, iterations_to_keep=-1)
    niter2 = get_npath(dest_path, xpath_iter)

    assert niter2 == 1  # check of only one iteration kept

    # test if more iteration given then in file should change nothing
    compress_fleuroutxml(testfilepath, dest_file_path=dest_path, iterations_to_keep=25)
    niter3 = get_npath(dest_path, xpath_iter)

    assert niter3 == niter_file  # check if no iteration deleted

    # cleanup
    remove(dest_path)
