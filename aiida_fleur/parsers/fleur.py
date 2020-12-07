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
import numpy as np
from datetime import date
from lxml import etree

from aiida.parsers import Parser
from aiida.orm import Dict, BandsData
from aiida.common.exceptions import NotExistent
from aiida_fleur.common.constants import HTR_TO_EV


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
        invalid_mmpmat = False

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
                        if time_avail_sec < 1.01 * time_calculated:
                            return self.exit_codes.ERROR_TIME_LIMIT
                    except KeyError:
                        pass

                    if (kb_used * mpiprocs / mem_kb_avail > 0.93 or
                            'cgroup out-of-memory handler' in error_file_lines or 'Out Of Memory' in error_file_lines):
                        return self.exit_codes.ERROR_NOT_ENOUGH_MEMORY
                    elif 'Atom spills out into vacuum during relaxation' in error_file_lines:
                        return self.exit_codes.ERROR_VACUUM_SPILL_RELAX
                    elif 'Error checking M.T. radii' in error_file_lines:
                        return self.exit_codes.ERROR_MT_RADII
                    elif 'Overlapping MT-spheres during relaxation: ' in error_file_lines:
                        overlap_line = re.findall(r'\S+ +\S+ olap: +\S+', error_file_lines)[0].split()
                        with output_folder.open('relax.xml', 'r') as rlx:
                            relax_dict = parse_relax_file(rlx)
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
                    elif 'Invalid elements in mmpmat' in error_file_lines:
                        invalid_mmpmat = True
                    elif 'parent_folder' in calc.inputs:
                        if 'fleurinpdata' in calc.inputs:
                            if 'relax.xml' in calc.inputs.fleurinpdata.files:
                                return self.exit_codes.ERROR_DROP_CDN
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
            with output_folder.open(FleurCalculation._OUTXML_FILE_NAME, 'r') as outxmlfile_opened:
                simpledata, complexdata, parser_info, success = parse_xmlout_file(outxmlfile_opened)

            # Call routines for output node creation
            if not success:
                self.logger.error('Parsing of XML output file was not successfull.')
                return self.exit_codes.ERROR_XMLOUT_PARSING_FAILED
            elif simpledata:
                outputdata = dict(list(simpledata.items()) + list(parser_info.items()))
                outxml_params = Dict(dict=outputdata)
                link_name = self.get_linkname_outparams()
                self.out(link_name, outxml_params)
            elif complexdata:
                parameter_data = dict(list(complexdata.items()) + list(parser_info.items()))
                outxml_params_complex = Dict(dict=parameter_data)
                link_name = self.get_linkname_outparams_complex()
                self.out(link_name, outxml_params_complex)
            else:
                self.logger.error('Something went wrong, neither simpledata nor complexdata found')
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

            # dummy comparison between old and new relax
            with output_folder.open(relax_name, 'r') as rlx:
                new_relax_text = rlx.read()
                if new_relax_text != old_relax_text:
                    try:
                        relax_dict = parse_relax_file(rlx)
                    except etree.XMLSyntaxError:
                        return self.exit_codes.ERROR_RELAX_PARSING_FAILED
                    self.out('relax_parameters', relax_dict)

        if invalid_mmpmat:
            return self.exit_codes.ERROR_INVALID_ELEMENTS_MMPMAT


def parse_xmlout_file(outxmlfile):
    """
    Parses the out.xml file of a FLEUR calculation
    Receives as input the absolute path to the xml output file

    :param outxmlfile: path to out.xml file

    :returns xml_data_dict: a simple dictionary (QE output like)
                            with parsed data

    """
    #from lxml import etree

    #global parser_info_out
    # FIXME: This is global, look for a different way to do this, python logging?

    parser_info_out = {'parser_warnings': [], 'unparsed': []}
    parser_version = '0.3.2'
    parser_info_out['parser_info'] = 'AiiDA Fleur Parser v{}'.format(parser_version)
    #parsed_data = {}

    successful = True
    outfile_broken = False
    parse_xml = True
    parser = etree.XMLParser(recover=False)

    try:
        tree = etree.parse(outxmlfile, parser)
    except etree.XMLSyntaxError:
        outfile_broken = True
        parser_info_out['parser_warnings'].append('The out.xml file is broken I try to repair it.')

    if outfile_broken:
        # repair xmlfile and try to parse what is possible.
        parser = etree.XMLParser(recover=True)
        try:
            tree = etree.parse(outxmlfile, parser)
        except etree.XMLSyntaxError:
            parser_info_out['parser_warnings'].append('Skipping the parsing of the xml file. '
                                                      'Repairing was not possible.')
            parse_xml = False
            successful = False

    def parse_simplexmlout_file(root, outfile_broken):
        """
        Parses the xml.out file of a Fleur calculation
        Receives in input the root of an xmltree of the xml output file

        :param root: root node of etree of out.xml file
        :param outfile_broken: a boolen that indicates if an out.xml has a broken last iteration
                               output

        :returns xml_data_dict: a simple dictionary (QE output like)
                                with parsed data
        """

        ### all xpath used. (maintain this) ###
        iteration_xpath = '/fleurOutput/scfLoop/iteration'
        magnetism_xpath = '/fleurOutput/inputData/calculationSetup/magnetism'

        relPos_xpath = '/fleurOutput/inputData/atomGroups/atomGroup/relPos'
        absPos_xpath = '/fleurOutput/inputData/atomGroups/atomGroup/absPos'
        filmPos_xpath = '/fleurOutput/inputData/atomGroups/atomGroup/filmPos'

        atomstypes_xpath = '/fleurOutput/inputData/atomGroups/atomGroup'
        symmetries_xpath = '/fleurOutput/inputData/cell/symmetryOperations/symOp'
        kpoints_xpath = '/fleurOutput/inputData/calculationSetup/bzIntegration/kPointList/kPoint'
        species_xpath = '/fleurOutput/inputData/atomSpecies'

        # input parameters
        creator_name_xpath = 'programVersion/@version'
        output_version_xpath = '/fleurOutput/@fleurOutputVersion'
        creator_target_architecture_xpath = 'programVersion/targetComputerArchitectures/text()'
        creator_target_structure_xpath = 'programVersion/targetStructureClass/text()'
        precision_xpath = 'programVersion/precision/@type'

        title_xpath = '/fleurOutput/inputData/comment/text()'
        kmax_xpath = 'calculationSetup/cutoffs'
        gmax_xpath = 'calculationSetup/cutoffs'
        mixing_xpath = 'calculationSetup/scfLoop'
        number_of_bands_xpath = 'calculationSetup/cutoffs'
        spin_orbit_calculation = 'calculationSetup/soc'
        smearing_energy_xpath = 'calculationSetup/bzIntegration/@fermiSmearingEnergy'
        jspin_name = 'jspins'
        l_f_xpath = '/fleurOutput/inputData/calculationSetup/geometryOptimization/@l_f'
        ldau_xpath = '/fleurOutput/inputData/atomSpecies/species/ldaU'

        # timing
        start_time_xpath = '/fleurOutput/startDateAndTime/@time'
        end_time_xpath = '/fleurOutput/endDateAndTime/@time'
        start_date_xpath = '/fleurOutput/startDateAndTime/@date'
        end_date_xpath = '/fleurOutput/endDateAndTime/@date'

        ###########

        # get all iterations in out.xml file
        iteration_nodes = eval_xpath2(root, iteration_xpath)
        n_iters = len(iteration_nodes)
        data_exists = True

        # parse only last stable interation
        # (if modes (dos and co) maybe parse anyway if broken?)
        if outfile_broken and (n_iters >= 2):
            iteration_to_parse = iteration_nodes[-2]
            parser_info_out['last_iteration_parsed'] = n_iters - 2
        elif outfile_broken and (n_iters == 1):
            iteration_to_parse = iteration_nodes[0]
            parser_info_out['last_iteration_parsed'] = n_iters
        elif not outfile_broken and (n_iters >= 1):
            iteration_to_parse = iteration_nodes[-1]
        else:  # there was no iteration found.
            # only the starting charge density could be generated
            parser_info_out['parser_warnings'].append('There was no iteration found in the outfile, either just a '
                                                      'starting density was generated or something went wrong.')
            data_exists = False
            iteration_to_parse = None

        # for getting the fleur modes use fleurinp methods
        spin = get_xml_attribute(eval_xpath(root, magnetism_xpath), jspin_name)

        if spin:
            fleurmode = {'jspin': int(spin)}
        else:
            fleurmode = {'jspin': 1}

        relax = eval_xpath(root, l_f_xpath)
        fleurmode['relax'] = relax == 'T'
        fleurmode['ldau'] = len(eval_xpath2(root, ldau_xpath)) != 0

        if data_exists:
            simple_data = parse_simple_outnode(iteration_to_parse, fleurmode)
        else:
            simple_data = {}

        # TODO: in the future add here the warnings returned from parse_simple_outnode
        # Currently Fleur warnings an errors are not written to the out.xml
        # should they be lists or dicts?
        warnings = {'info': {}, 'debug': {}, 'warning': {}, 'error': {}}

        simple_data['number_of_atoms'] = (len(eval_xpath2(root, relPos_xpath)) + len(eval_xpath2(root, absPos_xpath)) +
                                          len(eval_xpath2(root, filmPos_xpath)))
        simple_data['number_of_atom_types'] = len(eval_xpath2(root, atomstypes_xpath))
        simple_data['number_of_iterations'] = n_iters
        simple_data['number_of_symmetries'] = len(eval_xpath2(root, symmetries_xpath))
        simple_data['number_of_species'] = len(eval_xpath2(root, species_xpath))
        simple_data['number_of_kpoints'] = len(eval_xpath2(root, kpoints_xpath))
        simple_data['number_of_spin_components'] = fleurmode['jspin']

        if fleurmode['ldau']:
            ldaU_definitions = eval_xpath2(root, ldau_xpath)
            for ldaU in ldaU_definitions:
                parent = ldaU.getparent()
                element_name = get_xml_attribute(parent, 'element')
                species_name = get_xml_attribute(parent, 'name')
                ldauKey = f'{element_name}/{species_name}'

                if ldauKey not in simple_data['ldau_info']:
                    simple_data['ldau_info'][ldauKey] = {}

                ldau_l = get_xml_attribute(ldaU, 'l')
                ldau_l, suc = convert_to_int(ldau_l)
                ldau_l = 'spdf'[ldau_l]
                simple_data['ldau_info'][ldauKey][ldau_l] = {}

                ldau_u = get_xml_attribute(ldaU, 'U')
                simple_data['ldau_info'][ldauKey][ldau_l]['u'], suc = convert_to_float(ldau_u)

                ldau_j = get_xml_attribute(ldaU, 'J')
                simple_data['ldau_info'][ldauKey][ldau_l]['j'], suc = convert_to_float(ldau_j)

                simple_data['ldau_info'][ldauKey][ldau_l]['unit'] = 'eV'

                ldau_amf = get_xml_attribute(ldaU, 'l_amf') == 'T'
                if ldau_amf:
                    ldau_dc = 'AMF'
                else:
                    ldau_dc = 'FLL'
                simple_data['ldau_info'][ldauKey][ldau_l]['double_counting'] = ldau_dc

        title = eval_xpath(root, title_xpath)
        if title:
            title = str(title).strip()
        simple_data['title'] = title
        simple_data['creator_name'] = eval_xpath(root, creator_name_xpath)
        simple_data['creator_target_architecture'] = eval_xpath(root, creator_target_architecture_xpath)
        simple_data['creator_target_structure'] = eval_xpath(root, creator_target_structure_xpath)
        simple_data['output_file_version'] = eval_xpath(root, output_version_xpath)

        # time
        # Maybe change the behavior if things could not be parsed...
        # Especially if file was broken, ie endtime it not there.
        starttime = eval_xpath(root, start_time_xpath)
        if starttime:
            starttimes = starttime.split(':')
        else:
            starttimes = [0, 0, 0]
            msg = 'Startime was unparsed, inp.xml prob not complete, do not believe the walltime!'
            if data_exists:
                parser_info_out['parser_warnings'].append(msg)

        endtime = eval_xpath(root, end_time_xpath)
        if endtime:
            endtimes = endtime.split(':')
        else:
            endtimes = [0, 0, 0]
            msg = 'Endtime was unparsed, inp.xml prob not complete, do not believe the walltime!'
            if data_exists:
                parser_info_out['parser_warnings'].append(msg)
        start_date = eval_xpath(root, start_date_xpath)
        end_date = eval_xpath(root, end_date_xpath)

        offset = 0
        if start_date != end_date:
            # date="2018/01/15", Can this fail? what happens if not there
            if start_date and end_date:
                date_sl = [int(ent) for ent in start_date.split('/')]
                date_el = [int(ent) for ent in end_date.split('/')]
                date_s = date(*date_sl)
                date_e = date(*date_el)
                diff = date_e - date_s
                offset = diff.days * 86400
        # ncores = 12 #TODO parse parallelization_Parameters
        time = offset + (int(endtimes[0]) - int(starttimes[0])) * 60 * 60 + (
            int(endtimes[1]) - int(starttimes[1])) * 60 + int(endtimes[2]) - int(starttimes[2])
        simple_data['walltime'] = time
        simple_data['walltime_units'] = 'seconds'
        #simple_data['core_hours'] = time*ncores*1.0/3600
        #simple_data['parallelization_Parameters'] = {'mpiPEs' : ncores}
        simple_data['start_date'] = {'date': start_date, 'time': starttime}
        simple_data['end_date'] = {'date': end_date, 'time': endtime}

        warnings['info'] = {}  # TODO
        warnings['debug'] = {}  # TODO
        warnings['warning'] = {}  # TODO
        warnings['error'] = {}  # TODO
        simple_data['warnings'] = warnings

        return simple_data

    # TODO find a way to import these from xml_util, but make the parser logger work...
    def eval_xpath(node, xpath):
        """
        Tries to evaluate an xpath expression. If it fails it logs it.

        :param node: root node of an etree
        :param xpath: xpath expression (relative, or absolute)
        :returns: text, attribute or a node list
        """
        try:
            return_value = node.xpath(xpath)
        except etree.XPathEvalError:
            parser_info_out['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n Either it does '
                                                      'not exist, or something is wrong with the expression.'
                                                      ''.format(xpath))
            return []  # or rather None?
        if len(return_value) == 1:
            return return_value[0]
        else:
            return return_value

    def eval_xpath2(node, xpath):
        """
        Tries to evaluate an xpath expression. If it fails it logs it.
        It always return a list even if a single element was evaluated.

        :param node: root node of an etree
        :param xpath: xpath expression (relative, or absolute)
        :returns: a node list
        """
        try:
            return_value = node.xpath(xpath)
        except etree.XPathEvalError:
            parser_info_out['parser_warnings'].append('There was a XpathEvalError on the xpath: {} \n Either it does '
                                                      'not exist, or something is wrong with the expression.'
                                                      ''.format(xpath))
            return []
        return return_value

    def get_xml_attribute(node, attributename):
        """
        Get an attribute value from a node.

        :param node: a node from etree
        :param attributename: a string with the attribute name.
        :returns: attributevalue or None
        """
        if etree.iselement(node):
            attrib_value = node.get(attributename)
            if attrib_value:
                return attrib_value
            else:
                parser_info_out['parser_warnings'].append('Tried to get attribute: "{}" from element {}.\n '
                                                          'I received "{}", maybe the attribute does not exist'
                                                          ''.format(attributename, node, attrib_value))
                return None
        else:  # something doesn't work here, some nodes get through here
            parser_info_out['parser_warnings'].append('Can not get attributename: "{}" from node "{}", '
                                                      'because node is not an element of etree.'
                                                      ''.format(attributename, node))

            return None

    def convert_to_float(value_string):
        """
        Tries to make a float out of a string. If it can't it logs a warning
        and returns True or False if convertion worked or not.

        :param value_string: a string
        :returns value: the new float or value_string: the string given
        :returns: True if convertation was successfull, False otherwise
        """
        try:
            value = float(value_string)
        except TypeError:
            parser_info_out['parser_warnings'].append('Could not convert: "{}" to float, TypeError'
                                                      ''.format(value_string))
            return value_string, False
        except ValueError:
            parser_info_out['parser_warnings'].append('Could not convert: "{}" to float, ValueError'
                                                      ''.format(value_string))
            return value_string, False
        return value, True

    def convert_to_int(value_string):
        """
        Tries to make a int out of a string. If it can't it logs a warning
        and returns True or False if convertion worked or not.

        :param value_string: a string
        :returns value: the new int or value_string: the string given
        :returns: True or False
        """
        try:
            value = int(value_string)
        except TypeError:
            parser_info_out['parser_warnings'].append('Could not convert: "{}" to int, TypeError'
                                                      ''.format(value_string))
            return value_string, False
        except ValueError:
            parser_info_out['parser_warnings'].append('Could not convert: "{}" to int, ValueError'
                                                      ''.format(value_string))
            return value_string, False
        return value, True

    def convert_htr_to_ev(value):
        """
        Multiplies the value given with the Hartree factor (converts htr to eV)
        """
        #htr = 27.21138602
        suc = False
        value_to_save, suc = convert_to_float(value)
        if suc:
            return value_to_save * HTR_TO_EV
        else:
            return value

    def parse_simple_outnode(iteration_node, fleurmode):
        """
        Parses the data from the iteration given (usually last iteration)
        and some other data for the 'simple' output node.

        :param iteration_node: etree node of an interation
        :param Fleurmode: python dictionary, with all the modes,
                          which influence the parsing

        :returns simple_data: a python dictionary with all results
        """
        ###################################################
        ##########  all xpaths (maintain this) ############
        # (specifies where to find things in the out.xml) #

        # density
        densityconvergence_xpath = 'densityConvergence'
        chargedensity_xpath = 'densityConvergence/chargeDensity'
        overallchargedensity_xpath = 'densityConvergence/overallChargeDensity'
        spindensity_xpath = 'densityConvergence/spinDensity'

        bandgap_xpath = 'bandgap'
        fermi_energy_xpath = 'FermiEnergy'

        # magnetic moments
        magnetic_moments_in_mtpheres_xpath = 'magneticMomentsInMTSpheres'
        magneticmoment_xpath = 'magneticMomentsInMTSpheres/magneticMoment'

        magneticmoments_xpath = 'magneticMomentsInMTSpheres/magneticMoment/@moment'
        magneticmoments_spinupcharge_xpath = 'magneticMomentsInMTSpheres/magneticMoment/@spinUpCharge'
        magneticmoments_spindowncharge_xpath = 'magneticMomentsInMTSpheres/magneticMoment/@spinDownCharge'

        orbmagnetic_moments_in_mtpheres_xpath = 'orbitalMagneticMomentsInMTSpheres'
        orbmagneticmoment_xpath = 'orbitalMagneticMomentsInMTSpheres/orbMagMoment'

        orbmagneticmoments_xpath = 'orbitalMagneticMomentsInMTSpheres/orbMagMoment/@moment'
        orbmagneticmoments_spinupcharge_xpath = 'orbitalMagneticMomentsInMTSpheres/orbMagMoment/@spinUpCharge'
        orbmagneticmoments_spindowncharge_xpath = 'orbitalMagneticMomentsInMTSpheres/orbMagMoment/@spinDownCharge'

        mae_force_theta_xpath = 'Forcetheorem_MAE/Angle/@theta'
        mae_force_phi_xpath = 'Forcetheorem_MAE/Angle/@phi'
        mae_force_evsum_xpath = 'Forcetheorem_MAE/Angle/@ev-sum'
        mae_force_energ_units_xpath = 'Forcetheorem_Loop_MAE/sumValenceSingleParticleEnergies/@units'

        spst_force_xpath = 'Forcetheorem_SSDISP/@qvectors'
        spst_force_q_xpath = 'Forcetheorem_SSDISP/Entry/@q'
        spst_force_evsum_xpath = 'Forcetheorem_SSDISP/Entry/@ev-sum'
        spst_force_energ_units_xpath = 'Forcetheorem_Loop_SSDISP/sumValenceSingleParticleEnergies/@units'

        dmi_force_xpath = 'Forcetheorem_DMI'
        dmi_force_q_xpath = 'Forcetheorem_DMI/Entry/@q'
        dmi_force_theta_xpath = 'Forcetheorem_DMI/Entry/@theta'
        dmi_force_phi_xpath = 'Forcetheorem_DMI/Entry/@phi'
        dmi_force_evsum_xpath = 'Forcetheorem_DMI/Entry/@ev-sum'
        dmi_force_angles_xpath = 'Forcetheorem_DMI/@Angles'
        dmi_force_qs_xpath = 'Forcetheorem_DMI/@qPoints'
        dmi_force_energ_units_xpath = 'Forcetheorem_Loop_DMI/sumValenceSingleParticleEnergies/@units'

        spinupcharge_name = 'spinUpCharge'
        spindowncharge_name = 'spinDownCharge'
        moment_name = 'moment'

        # All electron charges
        all_spin_charges_total_xpath = 'allElectronCharges/spinDependentCharge/@total'
        all_spin_charges_interstitial_xpath = 'allElectronCharges/spinDependentCharge/@interstitial'
        all_spin_charges_mt_spheres_xpath = 'allElectronCharges/spinDependentCharge/@mtSpheres'
        all_total_charge_xpath = 'allElectronCharges/totalCharge/@value'

        # energy
        totalenergy_xpath = 'totalEnergy'
        sumofeigenvalues_xpath = 'totalEnergy/sumOfEigenvalues'
        core_electrons_xpath = 'totalEnergy/sumOfEigenvalues/coreElectrons'
        valence_electrons_xpath = 'totalEnergy/sumOfEigenvalues/valenceElectrons'
        chargeden_xc_den_integral_xpath = 'totalEnergy/chargeDenXCDenIntegral'

        #free_energy_xpath = 'totalEnergy/freeEnergy'

        # forces
        forces_units_xpath = 'totalForcesOnRepresentativeAtoms'
        forces_total_xpath = 'totalForcesOnRepresentativeAtoms/forceTotal'

        #ldau
        eldau_xpath = 'totalEnergy/dftUCorrection/@value'
        ldaudistances_xpath = 'ldaUdensityMatrixConvergence/distance/'

        #
        iteration_xpath = '.'

        units_name = 'units'
        value_name = 'value'
        distance_name = 'distance'

        overall_number_name = 'overallNumber'
        atomtype_name = 'atomType'

        # forces
        f_x_name = 'F_x'
        f_y_name = 'F_y'
        f_z_name = 'F_z'
        new_x_name = 'x'
        new_y_name = 'y'
        new_z_name = 'z'

        species_xpath = '/fleurOutput/inputData/atomSpecies'
        relPos_xpath = '/fleurOutput/inputData/atomGroups/atomGroup/relPos'
        absPos_xpath = '/fleurOutput/inputData/atomGroups/atomGroup/absPos'
        filmPos_xpath = '/fleurOutput/inputData/atomGroups/atomGroup/filmPos'
        atomstypes_xpath = '/fleurOutput/inputData/atomGroups/atomGroup'

        film_lat_xpath = '/fleurOutput/inputData/cell/filmLattice/bravaisMatrix/'
        bulk_lat_xpath = '/fleurOutput/inputData/cell/bulkLattice/bravaisMatrix/'
        kmax_xpath = '/fleurOutput/inputData/calculationSetup/cutoffs/@Kmax'

        ###################################################

        jspin = fleurmode['jspin']
        relax = fleurmode['relax']
        ldaU = fleurmode['ldau']
        simple_data = {}

        def write_simple_outnode(value, value_type, value_name, dict_out):
            """
            Writes a value (int or float) in the simple data dict.
            if path does not exit it initializes it!

            If the value has not the type given,
            it will be logged in parser info instead of writing.

            :param value: value ti write
            :param value_type: a type of a value: 'float', 'int', 'str', 'list', 'list_floats',
                               'list_ints', list_list_floats
            :param value_name: a name of a value to be used in the dictionary
            """

            iteration_current_number_name = 'numberForCurrentRun'
            suc = False

            if value_type == 'float':
                value_to_save, suc = convert_to_float(value)
            elif value_type == 'int':
                value_to_save, suc = convert_to_int(value)
            elif value_type == 'str':
                suc = True
                value_to_save = value
                #value_to_save, suc = convert_to_str(value)
            elif value_type == 'list':
                suc = True
                value_to_save = value
            elif value_type == 'list_floats':
                value_to_save = []
                for val in value:
                    value_to_savet, suct = convert_to_float(val)
                    value_to_save.append(value_to_savet)
                suc = True  # TODO individual or common error message?
            elif value_type == 'list_ints':
                value_to_save = []
                for val in value:
                    value_to_savet, suct = convert_to_int(val)
                    value_to_save.append(value_to_savet)
                suc = True
            elif value_type == 'list_list_floats':
                value_to_save = []
                for val in value:
                    value_to_savet = []
                    for val1 in val:
                        value_to_savet1, suct = convert_to_float(val1)
                        value_to_savet.append(value_to_savet1)
                    value_to_save.append(value_to_savet)
                suc = True  # TODO individual or common error message?
            else:
                #self.logger.error('I dont know the type you gave me {}'.format(type))
                pass
                # TODO log error, self is not known here...
            if suc:
                dict_out[value_name] = value_to_save
            else:
                parser_info_out['unparsed'].append({
                    value_name:
                    value,
                    'iteration':
                    get_xml_attribute(iteration_node, iteration_current_number_name)
                })

        if eval_xpath(iteration_node, mae_force_theta_xpath) != []:
            # extract MAE force theorem parameters
            mae_force_theta = eval_xpath2(iteration_node, mae_force_theta_xpath)
            write_simple_outnode(mae_force_theta, 'list_floats', 'mae_force_theta', simple_data)

            mae_force_evsum = eval_xpath2(iteration_node, mae_force_evsum_xpath)
            write_simple_outnode(mae_force_evsum, 'list_floats', 'mae_force_evSum', simple_data)

            mae_force_phi = eval_xpath2(iteration_node, mae_force_phi_xpath)
            write_simple_outnode(mae_force_phi, 'list_floats', 'mae_force_phi', simple_data)

            units_e = eval_xpath2(iteration_node, mae_force_energ_units_xpath)
            write_simple_outnode(units_e[0], 'str', 'energy_units', simple_data)
        elif eval_xpath(iteration_node, spst_force_xpath) != []:
            # extract Spin spiral dispersion force theorem parameters
            spst_force_q = eval_xpath2(iteration_node, spst_force_q_xpath)
            write_simple_outnode(spst_force_q, 'list_floats', 'spst_force_q', simple_data)

            spst_force_evsum = eval_xpath2(iteration_node, spst_force_evsum_xpath)
            write_simple_outnode(spst_force_evsum, 'list_floats', 'spst_force_evSum', simple_data)

            units_e = eval_xpath2(iteration_node, spst_force_energ_units_xpath)
            write_simple_outnode(units_e[0], 'str', 'energy_units', simple_data)
        elif eval_xpath(iteration_node, dmi_force_xpath) != []:
            # extract DMI force theorem parameters
            dmi_force_q = eval_xpath2(iteration_node, dmi_force_q_xpath)
            write_simple_outnode(dmi_force_q, 'list_ints', 'dmi_force_q', simple_data)

            dmi_force_evsum = eval_xpath2(iteration_node, dmi_force_evsum_xpath)
            write_simple_outnode(dmi_force_evsum, 'list_floats', 'dmi_force_evSum', simple_data)

            dmi_force_theta = eval_xpath2(iteration_node, dmi_force_theta_xpath)
            write_simple_outnode(dmi_force_theta, 'list_floats', 'dmi_force_theta', simple_data)

            dmi_force_phi = eval_xpath2(iteration_node, dmi_force_phi_xpath)
            write_simple_outnode(dmi_force_phi, 'list_floats', 'dmi_force_phi', simple_data)

            dmi_force_angles = eval_xpath(iteration_node, dmi_force_angles_xpath)
            write_simple_outnode(dmi_force_angles, 'int', 'dmi_force_angles', simple_data)

            dmi_force_qs = eval_xpath(iteration_node, dmi_force_qs_xpath)
            write_simple_outnode(dmi_force_qs, 'int', 'dmi_force_qs', simple_data)

            units_e = eval_xpath2(iteration_node, dmi_force_energ_units_xpath)
            write_simple_outnode(units_e[0], 'str', 'energy_units', simple_data)
        else:
            # total energy

            kmax_used = eval_xpath2(root, kmax_xpath)[0]
            write_simple_outnode(kmax_used, 'float', 'kmax', simple_data)

            units_e = get_xml_attribute(eval_xpath(iteration_node, totalenergy_xpath), units_name)
            write_simple_outnode(units_e, 'str', 'energy_hartree_units', simple_data)

            tE_htr = get_xml_attribute(eval_xpath(iteration_node, totalenergy_xpath), value_name)
            write_simple_outnode(tE_htr, 'float', 'energy_hartree', simple_data)

            write_simple_outnode(convert_htr_to_ev(tE_htr), 'float', 'energy', simple_data)
            write_simple_outnode('eV', 'str', 'energy_units', simple_data)

            sumofeigenvalues = get_xml_attribute(eval_xpath(iteration_node, sumofeigenvalues_xpath), value_name)
            write_simple_outnode(sumofeigenvalues, 'float', 'sum_of_eigenvalues', simple_data)

            coreElectrons = get_xml_attribute(eval_xpath(iteration_node, core_electrons_xpath), value_name)
            write_simple_outnode(coreElectrons, 'float', 'energy_core_electrons', simple_data)

            valenceElectrons = get_xml_attribute(eval_xpath(iteration_node, valence_electrons_xpath), value_name)
            write_simple_outnode(valenceElectrons, 'float', 'energy_valence_electrons', simple_data)

            ch_d_xc_d_inte = get_xml_attribute(eval_xpath(iteration_node, chargeden_xc_den_integral_xpath), value_name)
            write_simple_outnode(ch_d_xc_d_inte, 'float', 'charge_den_xc_den_integral', simple_data)

            # bandgap
            units_bandgap = get_xml_attribute(eval_xpath(iteration_node, bandgap_xpath), units_name)
            write_simple_outnode(units_bandgap, 'str', 'bandgap_units', simple_data)

            bandgap = get_xml_attribute(eval_xpath(iteration_node, bandgap_xpath), value_name)
            write_simple_outnode(bandgap, 'float', 'bandgap', simple_data)

            # fermi
            fermi_energy = get_xml_attribute(eval_xpath(iteration_node, fermi_energy_xpath), value_name)
            write_simple_outnode(fermi_energy, 'float', 'fermi_energy', simple_data)
            units_fermi_energy = get_xml_attribute(eval_xpath(iteration_node, fermi_energy_xpath), units_name)
            write_simple_outnode(units_fermi_energy, 'str', 'fermi_energy_units', simple_data)

            # density convergence
            units = get_xml_attribute(eval_xpath(iteration_node, densityconvergence_xpath), units_name)
            write_simple_outnode(units, 'str', 'density_convergence_units', simple_data)

            if jspin == 1:
                if not relax:  # there are no charge densities written if relax
                    charge_density = get_xml_attribute(eval_xpath(iteration_node, chargedensity_xpath), distance_name)
                    write_simple_outnode(charge_density, 'float', 'charge_density', simple_data)

            elif jspin == 2:
                charge_densitys = eval_xpath2(iteration_node, chargedensity_xpath)

                if not relax:  # there are no charge densities written if relax
                    if charge_densitys:  # otherwise we get a keyerror if calculation failed.
                        charge_density1 = get_xml_attribute(charge_densitys[0], distance_name)
                        charge_density2 = get_xml_attribute(charge_densitys[1], distance_name)
                    else:  # Is non a problem?
                        charge_density1 = None
                        charge_density2 = None
                    write_simple_outnode(charge_density1, 'float', 'charge_density1', simple_data)
                    write_simple_outnode(charge_density2, 'float', 'charge_density2', simple_data)

                    spin_density = get_xml_attribute(eval_xpath(iteration_node, spindensity_xpath), distance_name)
                    write_simple_outnode(spin_density, 'float', 'spin_density', simple_data)

                    overall_charge_density = get_xml_attribute(eval_xpath(iteration_node, overallchargedensity_xpath),
                                                               distance_name)
                    write_simple_outnode(overall_charge_density, 'float', 'overall_charge_density', simple_data)

                # magnetic moments
                m_units = get_xml_attribute(eval_xpath(iteration_node, magnetic_moments_in_mtpheres_xpath), units_name)
                write_simple_outnode(m_units, 'str', 'magnetic_moment_units', simple_data)
                write_simple_outnode(m_units, 'str', 'orbital_magnetic_moment_units', simple_data)

                moments = eval_xpath(iteration_node, magneticmoments_xpath)
                write_simple_outnode(moments, 'list_floats', 'magnetic_moments', simple_data)

                spinup = eval_xpath(iteration_node, magneticmoments_spinupcharge_xpath)
                write_simple_outnode(spinup, 'list_floats', 'magnetic_spin_up_charges', simple_data)

                spindown = eval_xpath(iteration_node, magneticmoments_spindowncharge_xpath)
                write_simple_outnode(spindown, 'list_floats', 'magnetic_spin_down_charges', simple_data)

                spindown = eval_xpath(iteration_node, magneticmoments_spindowncharge_xpath)
                write_simple_outnode(spindown, 'list_floats', 'magnetic_spin_down_charges', simple_data)

                # Total charges, total magentic moment

                total_c = eval_xpath2(iteration_node, all_spin_charges_total_xpath)
                write_simple_outnode(total_c, 'list_floats', 'spin_dependent_charge_total', simple_data)

                total_magentic_moment_cell = None
                if len(total_c) == 2:
                    val, suc = convert_to_float(total_c[0])
                    val2, suc2 = convert_to_float(total_c[1])
                    total_magentic_moment_cell = np.abs(val - val2)
                write_simple_outnode(total_magentic_moment_cell, 'float', 'total_magnetic_moment_cell', simple_data)

                total_c_i = eval_xpath2(iteration_node, all_spin_charges_interstitial_xpath)
                write_simple_outnode(total_c_i, 'list_floats', 'spin_dependent_charge_interstitial', simple_data)

                total_c_mt = eval_xpath2(iteration_node, all_spin_charges_mt_spheres_xpath)
                write_simple_outnode(total_c_mt, 'list_floats', 'spin_dependent_charge_mt', simple_data)

                total_c = eval_xpath(iteration_node, all_total_charge_xpath)
                write_simple_outnode(total_c, 'float', 'total_charge', simple_data)

                # orbital magnetic moments
                orbmoments = eval_xpath(iteration_node, orbmagneticmoments_xpath)
                write_simple_outnode(orbmoments, 'list_floats', 'orbital_magnetic_moments', simple_data)

                orbspinup = eval_xpath(iteration_node, orbmagneticmoments_spinupcharge_xpath)
                write_simple_outnode(orbspinup, 'list_floats', 'orbital_magnetic_spin_up_charges', simple_data)

                orbspindown = eval_xpath(iteration_node, orbmagneticmoments_spindowncharge_xpath)
                write_simple_outnode(orbspindown, 'list_floats', 'orbital_magnetic_spin_down_charges', simple_data)

            if ldaU:
                simple_data['ldau_info'] = {}
                eldau = eval_xpath(iteration_node, eldau_xpath)
                write_simple_outnode(eldau, 'float', 'ldau_energy_correction', simple_data['ldau_info'])
                write_simple_outnode(units_e, 'str', 'unit', simple_data['ldau_info'])

                ldau_distances = eval_xpath2(iteration_node, ldaudistances_xpath)
                write_simple_outnode(ldau_distances, 'list_floats', 'density_matrix_distance', simple_data['ldau_info'])

            if relax:
                # check if it is a film or a bulk structure
                film = eval_xpath2(root, os.path.join(film_lat_xpath, 'row-1'))
                if film:
                    lat_path = film_lat_xpath
                    pos_attr = 'filmPos'
                else:
                    lat_path = bulk_lat_xpath
                    pos_attr = 'relPos'

                v_1 = eval_xpath(root, os.path.join(lat_path, 'row-1'))
                v_1 = [float(x) for x in v_1.text.split()]

                v_2 = eval_xpath(root, os.path.join(lat_path, 'row-2'))
                v_2 = [float(x) for x in v_2.text.split()]

                v_3 = eval_xpath(root, os.path.join(lat_path, 'row-3'))
                v_3 = [float(x) for x in v_3.text.split()]

                relax_brav_vectors = [v_1, v_2, v_3]

                atom_positions = []
                relax_atom_info = []

                all_atoms = eval_xpath2(root, atomstypes_xpath)
                for a_type in all_atoms:
                    species = get_xml_attribute(a_type, 'species')
                    full_xpath = species_xpath + '/species[@name = "{}"]/@element'.format(species)
                    element = eval_xpath(root, full_xpath)
                    type_positions = eval_xpath2(a_type, pos_attr)
                    for pos in type_positions:
                        pos = [convert_frac(x) for x in pos.text.split()]
                        atom_positions.append(pos)
                        relax_atom_info.append([species, element])

                write_simple_outnode(relax_atom_info, 'list', 'relax_atomtype_info', simple_data)
                write_simple_outnode(relax_brav_vectors, 'list', 'relax_brav_vectors', simple_data)
                write_simple_outnode(atom_positions, 'list', 'relax_atom_positions', simple_data)
                write_simple_outnode(str(bool(film)), 'str', 'film', simple_data)

            # total iterations
            number_of_iterations_total = get_xml_attribute(eval_xpath(iteration_node, iteration_xpath),
                                                           overall_number_name)
            write_simple_outnode(number_of_iterations_total, 'int', 'number_of_iterations_total', simple_data)

            # forces atomtype dependend
            forces = eval_xpath2(iteration_node, forces_total_xpath)
            # length should be ntypes
            largest_force = -0.0
            for force in forces:
                atomtype, _ = convert_to_int(get_xml_attribute(force, atomtype_name))

                forces_unit = get_xml_attribute(eval_xpath(iteration_node, forces_units_xpath), units_name)
                write_simple_outnode(forces_unit, 'str', 'force_units', simple_data)

                force_x = get_xml_attribute(force, f_x_name)
                write_simple_outnode(force_x, 'float', 'force_x_type{}'.format(atomtype), simple_data)

                force_y = get_xml_attribute(force, f_y_name)
                write_simple_outnode(force_y, 'float', 'force_y_type{}'.format(atomtype), simple_data)

                force_z = get_xml_attribute(force, f_z_name)
                write_simple_outnode(force_z, 'float', 'force_z_type{}'.format(atomtype), simple_data)

                force_xf, suc1 = convert_to_float(force_x)
                force_yf, suc2 = convert_to_float(force_y)
                force_zf, suc3 = convert_to_float(force_z)

                if suc1 and suc2 and suc3:
                    if abs(force_xf) > largest_force:
                        largest_force = abs(force_xf)
                    if abs(force_yf) > largest_force:
                        largest_force = abs(force_yf)
                    if abs(force_zf) > largest_force:
                        largest_force = abs(force_zf)

                pos_x = get_xml_attribute(force, new_x_name)
                write_simple_outnode(pos_x, 'float', 'abspos_x_type{}'.format(atomtype), simple_data)
                pos_y = get_xml_attribute(force, new_y_name)
                write_simple_outnode(pos_y, 'float', 'abspos_y_type{}'.format(atomtype), simple_data)
                pos_z = get_xml_attribute(force, new_z_name)
                write_simple_outnode(pos_z, 'float', 'abspos_z_type{}'.format(atomtype), simple_data)

            write_simple_outnode(largest_force, 'float', 'force_largest', simple_data)

        return simple_data

    if parse_xml:
        root = tree.getroot()
        if root is None:
            parser_info_out['parser_warnings'].append(
                'Somehow the root from the xmltree is None, which it should not be, I skip the parsing.')
            successful = False
            return {}, {}, parser_info_out, successful
        else:
            simple_out = parse_simplexmlout_file(root, outfile_broken)
            #simple_out['outputfile_path'] = outxmlfile
            # TODO: parse complex out
            complex_out = {}  # parse_xmlout_file(root)
            return simple_out, complex_out, parser_info_out, successful
    else:
        return {}, {}, parser_info_out, successful


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


def parse_relax_file(rlx):
    """
    This function parsers relax.xml output file and
    returns a Dict containing all the data given there.
    """
    from aiida_fleur.tools.xml_util import eval_xpath2

    rlx.seek(0)
    tree = etree.parse(rlx)

    xpath_disp = '/relaxation/displacements/displace'
    xpath_energy = '/relaxation/relaxation-history/step/@energy'
    xpath_steps = '/relaxation/relaxation-history/step'

    root = tree.getroot()

    displacements = eval_xpath2(root, xpath_disp)
    float_displ = []
    for i in displacements:
        temp = [convert_frac(x) for x in i.text.split()]
        float_displ.append(temp)

    energies = eval_xpath2(root, xpath_energy)
    energies = [float(x) for x in energies]

    float_posforces = []
    iter_all = eval_xpath2(root, xpath_steps)
    for posf in iter_all:
        posforces = eval_xpath2(posf, 'posforce')
        temp2 = []
        for i in posforces:
            temp = [convert_frac(x) for x in i.text.split()]
            temp2.append(temp)
        float_posforces.append(temp2)

    out_dict = {}
    out_dict['displacements'] = float_displ
    out_dict['energies'] = energies
    out_dict['posforces'] = float_posforces

    return Dict(dict=out_dict)


def convert_frac(ratio):
    """ Converts ratio strings into float, e.g. 1.0/2.0 -> 0.5 """
    try:
        return float(ratio)
    except ValueError:
        num, denom = ratio.split('/')
        return float(num) / float(denom)
