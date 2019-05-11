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
Here we collect io routines and their utility. For writting certain things to files.
For example collection of data or database evaluations, for other people.
"""

from __future__ import absolute_import
from __future__ import print_function
import six
def write_results_to_file(headerstring, data, destination='./outputfile', seperator='  ', transpose=True):
    """
    Writes data to a file

    param headerstring: string with information
    param data: 2D array (numpy,scipy) with data [colum1 colum2, ...]
    """

    thefile = open(destination, 'w')
    thefile.write(headerstring)
    datastring = ''
    seperator = seperator# '\t'
    if transpose:
        datat = data.transpose()
    else:
        datat = data
    for item in datat:
        itemstring = ''
        for value in item:
            if isinstance(value, str) or isinstance(value, six.string_types):
                itemstring = itemstring + '{}{}'.format(value, seperator)
            else:
                itemstring = itemstring + '{0:0.8f}{1:s}'.format(float(value), seperator)
        datastring = datastring + itemstring.strip() + '\n'
    thefile.write(datastring)
    thefile.close()



def write_xps_spectra_datafile(nodes, factors, natomtypes_dict, bindingenergies, bindingenergies_ref, xdata_spec, ydata_spec, ydata_single_all, xdata_all, ydata_all, compound_info, xdatalabel, destination='./outputfile'):
    '''
    special file write routine. Writes theoretical spectra data from plot spectra to file

    uses write_results_to_file
    '''
    import numpy as np

    dataprep = [xdata_spec, ydata_spec] + ydata_single_all
    data = np.array(dataprep)#, ydata_single_all])

    formulastring = compound_info, factors
    nodesinvolvedstring = nodes
    atomtypesstring = natomtypes_dict
    be_string = bindingenergies
    reference_be_string = bindingenergies_ref

    headstring = ('# Theoretical Data provided as is without warranty. Copyright 2017-2018 Forschungszentrum Juelich GmbH\n'
                  '# produced at PGI-1 with the FLEUR code within the AiiDA framework (with aiida-fleur), MIT License, please cite: \n'
                  '################# Data meta information #############\n')
    tempst = ('# System: {}\n# Nodes: {}\n# Elements and natomtypes: {}\n# Bindingenergies [eV], pos: {}\n# Reference Energies [eV] pos: {}\n'
              ''.format(formulastring, nodesinvolvedstring, atomtypesstring, be_string, reference_be_string))
    tempst1 = ''
    for label in xdatalabel:
        tempst1 = tempst1 + ' | ' + label
    tempst2 = ('#####################  Data  ######################\n# Energy [eV] | Total intensity {}\n'.format(tempst1))

    headstring =  headstring + tempst + tempst2

    print(('Writting theoretical XPS data to file: {}'.format(destination)))
    write_results_to_file(headstring, data, destination=destination, seperator='  ')

# example/test
#from plot_methods.plot_fleur_aiida import plot_spectra
#import plot_methods
#all_wc_BeTi_uuid = ['107b0727-15cf-4436-b614-79801cdadd8c', 'f8b12b23-0b71-45a1-9040-b51ccf379439']
#factors = [1,1]
#returnvalues = plot_spectra(all_wc_BeTi_uuid, factors=factors, energy_range=[109,112], energy_grid=0.2)
#write_xps_spectra_datafile(all_wc_BeTi_uuid, factors, *returnvalues, destination='./out.txt')


