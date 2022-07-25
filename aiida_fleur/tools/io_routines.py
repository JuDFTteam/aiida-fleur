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
Here we collect IO routines and their utility, for writting certain things to files, or post process files.
For example collection of data or database evaluations, for other people.
"""
import warnings


def write_results_to_file(headerstring, data, destination='./outputfile', seperator='  ', transpose=True):
    """
    Writes data to a file

    param headerstring: string with information
    param data: 2D array (numpy,scipy) with data [colum1 colum2, ...]
    """

    with open(destination, 'w', encoding='utf-8') as thefile:
        thefile.write(headerstring)
        datastring = ''
        #seperator = seperator  # '\t'
        if transpose:
            datat = data.transpose()
        else:
            datat = data
        for item in datat:
            itemstring = ''
            for value in item:
                if isinstance(value, str):
                    itemstring = itemstring + f'{value}{seperator}'
                else:
                    itemstring = itemstring + f'{float(value):0.8f}{seperator:s}'
            datastring = datastring + itemstring.strip() + '\n'
        thefile.write(datastring)
    #thefile.close()


def write_xps_spectra_datafile(nodes,
                               factors,
                               natomtypes_dict,
                               bindingenergies,
                               bindingenergies_ref,
                               xdata_spec,
                               ydata_spec,
                               ydata_single_all,
                               xdata_all,
                               ydata_all,
                               compound_info,
                               xdatalabel,
                               destination='./outputfile'):
    '''
    special file write routine. Writes theoretical spectra data from plot spectra to file

    uses write_results_to_file
    '''
    import numpy as np

    dataprep = [xdata_spec, ydata_spec] + ydata_single_all
    data = np.array(dataprep)  #, ydata_single_all])

    formulastring = compound_info, factors
    nodesinvolvedstring = nodes
    atomtypesstring = natomtypes_dict
    be_string = bindingenergies
    reference_be_string = bindingenergies_ref

    headstring = (
        '# Theoretical Data provided as is without warranty. Copyright 2017-2018 Forschungszentrum Juelich GmbH\n'
        '# produced at PGI-1 with the FLEUR code within the AiiDA framework (with aiida-fleur), MIT License, please cite: \n'
        '################# Data meta information #############\n')
    tempst = (
        '# System: {}\n# Nodes: {}\n# Elements and natomtypes: {}\n# Bindingenergies [eV], pos: {}\n# Reference Energies [eV] pos: {}\n'
        ''.format(formulastring, nodesinvolvedstring, atomtypesstring, be_string, reference_be_string))
    tempst1 = ''
    for label in xdatalabel:
        tempst1 = tempst1 + ' | ' + label
    tempst2 = (f'#####################  Data  ######################\n# Energy [eV] | Total intensity {tempst1}\n')

    headstring = headstring + tempst + tempst2

    print(f'Writting theoretical XPS data to file: {destination}')
    write_results_to_file(headstring, data, destination=destination, seperator='  ')


# example/test
#from plot_methods.plot_fleur_aiida import plot_spectra
#import plot_methods
#all_wc_BeTi_uuid = ['107b0727-15cf-4436-b614-79801cdadd8c', 'f8b12b23-0b71-45a1-9040-b51ccf379439']
#factors = [1,1]
#returnvalues = plot_spectra(all_wc_BeTi_uuid, factors=factors, energy_range=[109,112], energy_grid=0.2)
#write_xps_spectra_datafile(all_wc_BeTi_uuid, factors, *returnvalues, destination='./out.txt')


def compress_fleuroutxml(outxmlfilepath, dest_file_path=None, delete_eig=True, iterations_to_keep=None):
    """
    Compresses a fleur out.xml file by deleting certain things
    like eigenvalues tags and/or iterations from it

    :param outxmlfilepath: (absolut) file path
    :type outxmlfilepath: str
    :param dest_file_path: (absolut) for the compressed file to be saved, if no desitination file path is given the file is overriden in place (default)!
    :type dest_file_path: str, optional
    :param delete_eig:  if eigenvalues are deleted from file default is True
    :type delete_eig: boolean, optional
    :param iterations_to_keep: index of 'till' whihc iterations to be keep, i.e '-2' means only last two, '15' default (None) is keep all
    :type iterations_to_keep: int

     ###
     usage example:
     outxmldes = '/Users/broeder/test/FePt_out_test.xml'
     outxmlsrc = '/Users/broeder/test/FePt_out.xml'
     compress_fleuroutxml(outxmlsrc, dest_file_path=outxmldes, iterations_to_keep=14)
     compress_fleuroutxml(outxmlsrc, dest_file_path=outxmldes, iterations_to_keep=-1)
    """
    from masci_tools.util.xml.xml_setters_names import delete_tag
    from masci_tools.util.schema_dict_util import get_number_of_nodes
    from masci_tools.util.schema_dict_util import eval_simple_xpath
    from masci_tools.io.fleur_xml import load_outxml
    from lxml import etree

    xmltree, schema_dict = load_outxml(outxmlfilepath)
    xpath_iteration = schema_dict.tag_xpath('iteration')

    # delete eigenvalues (all)
    if delete_eig:
        iteration_nodes = eval_simple_xpath(xmltree, schema_dict, 'iteration', list_return=True)
        for iteration in iteration_nodes:
            #The explicit conversion is done since delete_tag expects a ElementTree in masci-tools <= 0.6.2
            delete_tag(etree.ElementTree(iteration), schema_dict, 'eigenvalues')

    # delete certain iterations
    if iterations_to_keep is not None:
        root = xmltree.getroot()
        n_iters = get_number_of_nodes(root, schema_dict, 'iteration')
        print(f'Found {n_iters} iterations')
        if iterations_to_keep < 0:
            # the first element has 1 (not 0) in xpath expresions
            position_keep = n_iters + iterations_to_keep + 1
            delete_xpath = f'{xpath_iteration}[position()<{int(position_keep)}]'
        else:
            delete_xpath = f'{xpath_iteration}[position()>{int(iterations_to_keep)}]'

        if abs(iterations_to_keep) > n_iters:
            warnings.warn(
                'iterations_to_keep is larger then the number of iterations'
                ' in the given out.xml file, I keep all.', UserWarning)
        else:
            print(f'Deleting iterations under the xpath: {delete_xpath}')
            xmltree = delete_tag(xmltree, schema_dict, 'iteration', complex_xpath=delete_xpath)

    etree.indent(xmltree)  #Make sure the print looks nice

    if dest_file_path is None:
        dest_file_path = outxmlfilepath  # overwrite file
    if xmltree.getroot() is not None:  #otherwise write fails
        xmltree.write(dest_file_path, encoding='utf-8', pretty_print=True)
    else:
        raise ValueError('xmltree has no root..., I cannot write to proper xml')


# usage example
#outxml15 = '/Users/broeder/test/FePt_out_test.xml'
#outxml14 = '/Users/broeder/test/FePt_out.xml'
#compress_fleuroutxml(outxml14, dest_file_path=outxml15, iterations_to_keep=14)
#compress_fleuroutxml(outxml14, dest_file_path=outxml15, iterations_to_keep=-1)
