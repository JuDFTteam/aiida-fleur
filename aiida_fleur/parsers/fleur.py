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
This module contains the parser for a FLEUR calculation and methods for parsing
different files produced by FLEUR.

Please implement file parsing routines that they can be executed from outside
the parser. Makes testing and portability easier.
"""
# TODO: move methods to utils, xml or other
# TODO: warnings
from __future__ import absolute_import
import os
import re
import json
from lxml import etree

from aiida.parsers import Parser
from aiida.orm import Dict, BandsData
from aiida.common.exceptions import NotExistent

from masci_tools.io.parsers.fleur import outxml_parser
from masci_tools.io.parsers.fleur.fleur_schema import InputSchemaDict


class FleurParser(Parser):
    """
    This class is the implementation of the Parser class for FLEUR.
    It parses the FLEUR output if the calculation was successful,
    i.e checks if all files are there that should be and their condition.
    Then it parses the out.xml file and returns a (simple) parameterData node
    with the results of the last iteration.
    Other files (DOS.x, bands.x, relax.xml, ...) are also parsed if they are retrieved.
    """

    _setting_key = 'parser_options'

    def get_linkname_outparams_complex(self):
        """
        Returns the name of the link to the output_complex
        Node contains the Fleur output in a rather complex dictionary.
        """
        return 'output_complex'

    def get_linkname_outparams(self):
        """
        Returns the name of the link to the output_complex
        Node contains the Fleur output in a rather complex dictionary.
        """
        return 'output_parameters'

    def parse(self, **kwargs):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here. Checks presents of files.
        Calls routines to parse them and returns parameter nodes and success.

        :return successful: Bool, if overall parsing was successful or not
        :return new_nodes_list: list of tuples of two (linkname, Dataobject),
                                nodes to be stored by AiiDA

        """

        ####### init some variables ######

        # these files should be at least present after success of a Fleur run
        calc = self.node
        FleurCalculation = calc.process_class

        # this files should be retrieved
        should_retrieve = calc.get_attribute('retrieve_list')

        has_xml_outfile = False
        has_dos_file = False
        has_bands_file = False
        has_relax_file = False

        dos_file = None
        band_file = None

        ######### Check presence of files ######

        # select the folder object
        # Check that the retrieved folder is there
        try:
            output_folder = self.retrieved
        except NotExistent:
            self.logger.error('No retrieved folder found')
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # check what is inside the folder
        list_of_files = output_folder.list_object_names()
        self.logger.info('file list {}'.format(list_of_files))

        # has output xml file, otherwise error
        if FleurCalculation._OUTXML_FILE_NAME not in list_of_files:
            self.logger.error("XML out not found '{}'".format(FleurCalculation._OUTXML_FILE_NAME))
            return self.exit_codes.ERROR_NO_OUTXML
        else:
            has_xml_outfile = True

        # check if all files expected are there for the calculation
        for file in should_retrieve:
            if file not in list_of_files:
                self.logger.warning("'{}' file not found in retrived folder, it"
                                    ' was probably not created by fleur'.format(file))

        # check if something was written to the error file
        if FleurCalculation._ERROR_FILE_NAME in list_of_files:
            errorfile = FleurCalculation._ERROR_FILE_NAME
            # read
            try:
                with output_folder.open(errorfile, 'r') as efile:
                    error_file_lines = efile.read()  # Note: read(), not readlines()
            except IOError:
                self.logger.error('Failed to open error file: {}.'.format(errorfile))
                return self.exit_codes.ERROR_OPENING_OUTPUTS

            if error_file_lines:

                if isinstance(error_file_lines, type(b'')):
                    error_file_lines = error_file_lines.replace(b'\x00', b' ')
                else:
                    error_file_lines = error_file_lines.replace('\x00', ' ')
                if 'Run finished successfully' not in error_file_lines:
                    self.logger.warning('The following was written into std error and piped to {}'
                                        ' : \n {}'.format(errorfile, error_file_lines))
                    self.logger.error('FLEUR calculation did not finish' ' successfully.')

                    # here we estimate how much memory was available and consumed
                    mpiprocs = self.node.get_attribute('resources').get('num_mpiprocs_per_machine', 1)

                    kb_used = 0.0
                    with output_folder.open(FleurCalculation._OUTXML_FILE_NAME,
                                            'r') as out_file:  # lazy out.xml parsing
                        outlines = out_file.read()
                        try:
                            line_avail = re.findall(r'<mem memoryPerNode="\d+', outlines)[0]
                            mem_kb_avail = int(re.findall(r'\d+', line_avail)[0])
                        except IndexError:
                            mem_kb_avail = 1.0
                            self.logger.info('Did not manage to find memory available info.')
                        else:
                            usage_json = FleurCalculation._USAGE_FILE_NAME
                            if usage_json in list_of_files:
                                with output_folder.open(usage_json, 'r') as us_file:
                                    usage = json.load(us_file)
                                kb_used = usage['data']['VmPeak']
                            else:
                                try:
                                    line_used = re.findall(r'used.+', error_file_lines)[0]
                                    kb_used = int(re.findall(r'\d+', line_used)[2])
                                except IndexError:
                                    self.logger.info('Did not manage to find memory usage info.')

                    # here we estimate how much walltime was available and consumed
                    try:
                        time_avail_sec = self.node.attributes['last_job_info']['requested_wallclock_time_seconds']
                        time_calculated = self.node.attributes['last_job_info']['wallclock_time_seconds']
                        if 0.97 * time_avail_sec < time_calculated:
                            return self.exit_codes.ERROR_TIME_LIMIT
                    except KeyError:
                        pass

                    if (kb_used * mpiprocs / mem_kb_avail > 0.93 or
                            'cgroup out-of-memory handler' in error_file_lines or 'Out Of Memory' in error_file_lines):
                        return self.exit_codes.ERROR_NOT_ENOUGH_MEMORY
                    elif 'TIME LIMIT' in error_file_lines or 'time limit' in error_file_lines:
                        return self.exit_codes.ERROR_TIME_LIMIT
                    elif 'Atom spills out into vacuum during relaxation' in error_file_lines:
                        return self.exit_codes.ERROR_VACUUM_SPILL_RELAX
                    elif 'Error checking M.T. radii' in error_file_lines:
                        return self.exit_codes.ERROR_MT_RADII
                    elif 'Overlapping MT-spheres during relaxation: ' in error_file_lines:
                        overlap_line = re.findall(r'\S+ +\S+ olap: +\S+', error_file_lines)[0].split()
                        with output_folder.open('relax.xml', 'r') as rlx:
                            schema_dict = InputSchemaDict.fromVersion('0.34')
                            relax_dict = parse_relax_file(rlx, schema_dict)
                            it_number = len(relax_dict['energies']) + 1  # relax.xml was not updated
                        error_params = {
                            'error_name': 'MT_OVERLAP_RELAX',
                            'description': ('This output node contains information'
                                            'about FLEUR error'),
                            'overlapped_indices': overlap_line[:2],
                            'overlaping_value': overlap_line[3],
                            'iteration_number': it_number
                        }
                        link_name = self.get_linkname_outparams()
                        error_params = Dict(dict=error_params)
                        self.out('error_params', error_params)
                        return self.exit_codes.ERROR_MT_RADII_RELAX
                    elif 'parent_folder' in calc.inputs:  # problem in reusing cdn for relaxations, drop cdn
                        if 'fleurinpdata' in calc.inputs:
                            if 'relax.xml' in calc.inputs.fleurinpdata.files:
                                return self.exit_codes.ERROR_DROP_CDN
                        return self.exit_codes.ERROR_FLEUR_CALC_FAILED
                    else:
                        return self.exit_codes.ERROR_FLEUR_CALC_FAILED

        if FleurCalculation._DOS_FILE_NAME in list_of_files:
            has_dos = True
        if FleurCalculation._BAND_FILE_NAME in list_of_files:
            has_bands = True

        # if a relax.xml was retrieved
        if FleurCalculation._RELAX_FILE_NAME in list_of_files:
            self.logger.info('relax.xml file found in retrieved folder')
            has_relax_file = True

        ####### Parse the files ########

        if has_xml_outfile:
            # open output file

            with output_folder.open(FleurCalculation._OUTXML_FILE_NAME, 'rb') as outxmlfile_opened:
                success = True
                parser_info = {}
                try:
                    out_dict = outxml_parser(outxmlfile_opened, parser_info_out=parser_info, ignore_validation=True)
                except (ValueError, FileNotFoundError, KeyError) as exc:
                    self.logger.error(f'XML output parsing failed: {str(exc)}')
                    success = False

            # Call routines for output node creation
            if not success:
                self.logger.error('Parsing of XML output file was not successfull.')
                parameter_data = dict(list(parser_info.items()))
                outxml_params = Dict(dict=parameter_data)
                link_name = self.get_linkname_outparams()
                self.out(link_name, outxml_params)
                return self.exit_codes.ERROR_XMLOUT_PARSING_FAILED
            elif out_dict:
                outputdata = dict(list(out_dict.items()) + list(parser_info.items()))
                outxml_params = Dict(dict=outputdata)
                link_name = self.get_linkname_outparams()
                self.out(link_name, outxml_params)
            else:
                self.logger.error('Something went wrong, no out_dict found')
                parameter_data = dict(list(parser_info.items()))
                outxml_params = Dict(dict=parameter_data)
                link_name = self.get_linkname_outparams()
                self.out(link_name, outxml_params)

        # optional parse other files
        # DOS
        if has_dos_file:
            dos_file = FleurCalculation._DOS_FILE_NAME
            # if dos_file is not None:
            try:
                with output_folder.open(dos_file, 'r') as dosf:
                    dos_lines = dosf.read()  # Note: read() and not readlines()
            except IOError:
                self.logger.error('Failed to open DOS file: {}.'.format(dos_file))
                return self.exit_codes.ERROR_OPENING_OUTPUTS
            dos_data = parse_dos_file(dos_lines)  # , number_of_atom_types)

        # Bands
        if has_bands_file:
            # TODO: be carefull there might be two files.
            band_file = FleurCalculation._BAND_FILE_NAME

            # if band_file is not None:
            try:
                with output_folder.open(band_file, 'r') as bandf:
                    bands_lines = bandf.read()  # Note: read() and not readlines()
            except IOError:
                self.logger.error('Failed to open bandstructure file: {}.' ''.format(band_file))
                return self.exit_codes.ERROR_OPENING_OUTPUTS
            bands_data = parse_bands_file(bands_lines)

        if has_relax_file:
            relax_name = FleurCalculation._RELAX_FILE_NAME
            try:
                fleurinp = calc.inputs.fleurinpdata
            except NotExistent:
                old_relax_text = ''
            else:
                if relax_name in fleurinp.list_object_names():
                    with fleurinp.open(relax_name, 'r') as rlx:
                        old_relax_text = rlx.read()
                else:
                    old_relax_text = ''

            inp_version = outxml_params.get_dict().get('input_file_version', '0.34')
            schema_dict = InputSchemaDict.fromVersion(inp_version)
            # dummy comparison between old and new relax
            with output_folder.open(relax_name, 'rb') as rlx:
                new_relax_text = rlx.read()
                if new_relax_text != old_relax_text:
                    try:
                        relax_dict = parse_relax_file(rlx, schema_dict)
                    except etree.XMLSyntaxError:
                        return self.exit_codes.ERROR_RELAX_PARSING_FAILED
                    self.out('relax_parameters', relax_dict)


def parse_dos_file(dos_lines):  # , number_of_atom_types):
    """
    Parses the returned DOS.X files.
    Structure:
    (100(1x,e10.3))   e,totdos,interstitial,vac1,vac2,
    (at(i),i=1,ntype),((q(l,i),l=1,LMAX),i=1,ntype)
    where e is the energy in eV (= 1/27.2 htr) at(i) is the local DOS of a
    single atom of the i'th atom-type and q(l,i) is the l-resolved DOS at
    the i'th atom but has to be multiplied by the number of atoms of this type.

    :param dos_lines: string of the read in dos file
    :param number_of_atom_types: integer, number of atom types
    """
    # pass
    return 0


def parse_bands_file(bands_lines):
    '''
    Parses the returned bands.1 and bands.2 file and returns a complete
    bandsData object. bands.1 has the form: k value, energy

    :param bands_lines: string of the read in bands file
    '''
    # TODO: not finished
    # read bands out of file:
    nrows = 0  # get number of rows (known form number of atom types
    bands_values = []  # init an array of arrays nkpoint * ...
    bands_labels = []  # label for each row.

    # fill and correct fermi energy.
    bands_values = []

    # TODO: we need to get the cell from StructureData node
    # and KpointsData node from inpxml
    fleur_bands = BandsData()
    # fleur_bands.set_cell(cell)
    #fleur_bands.set_kpoints(kpoints, cartesian=True)
    fleur_bands.set_bands(bands=bands_values, units='eV', labels=bands_labels)

    for line in bands_lines:
        pass
    return fleur_bands


def parse_relax_file(relax_file, schema_dict):
    """
    This function parsers relax.xml output file and
    returns a Dict containing all the data given there.
    """
    from masci_tools.util.xml.xml_getters import get_relaxation_information

    relax_file.seek(0)
    tree = etree.parse(relax_file)

    out_dict = get_relaxation_information(tree, schema_dict)

    return Dict(dict=out_dict)
