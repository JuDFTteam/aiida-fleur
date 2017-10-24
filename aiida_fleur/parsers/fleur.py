# -*- coding: utf-8 -*-
"""
This module contains the parser for a FLEUR calculation and methods for parsing
different files produced by FLEUR.

Please implement file parsing routines that they can be executed from outside
the parser. Makes testing and portability easier.
"""
# TODO: cleanup
# TODO: move methods to utils, xml or other
# TODO: warnings
import os
#import numpy

from aiida.orm.data.parameter import ParameterData
from aiida.parsers.parser import Parser#, ParserParamManager
from aiida.orm.data.array.bands import BandsData
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.parsers import FleurOutputParsingError
from aiida_fleur.data.fleurinp import FleurinpData


__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


class FleurParser(Parser):
    """
    This class is the implementation of the Parser class for FLEUR.
    It parses the FLEUR output if the calculation was successful,
    i.e checks if all files are there that should be and their condition.
    Then it parses the out.xml file and returns a (simple) parameterData node
    with the results of the last iteration.
    Other files (DOS.x, bands.x, ...) are also parsed if they are retrieved.
    """

    _setting_key = 'parser_options'

    def __init__(self, calc):
        """
        Initialize the instance of FleurParser
        """
        # check for valid input
        if not isinstance(calc, FleurCalculation):
            raise FleurOutputParsingError("Input calculation for the FleurParser"
                                          "must be a FleurCalculation")

        # these files should be at least present after success of a Fleur run

        self._default_files = {calc._OUTXML_FILE_NAME, calc._INPXML_FILE_NAME}
        self._other_files = {}#"enpara","inp","sym.out", "cdn1", }
        #plus other special files? corelevels.xx, DOS.1 Bands.1 ...
        self._should_retrieve = []#calc.Calcinfo.retrieve_list()
        # somehow calc.CalcInfo does not work..
        super(FleurParser, self).__init__(calc)

    def get_linkname_outparams_complex(self):
        """
        Returns the name of the link to the output_complex
        Node contains the Fleur output in a rather complex dictionary.
        """
        return 'output_complex'


    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here. Checks presents of files.
        Calls routines to parse them and returns parameter nodes and sucess.

        :return successful: Bool, if overall parsing was successful or not
        :return new_nodes_list: list of tuples of two (linkname, Dataobject),
                                nodes to be stored by AiiDA

        """

        ####### init some variables ######

        successful = True

        has_xml_outfile = False
        has_dos_file = False
        has_bands_file = False
        has_new_xmlinp_file = False

        dos_file = None
        band_file = None
        new_nodes_list = []

        ######### Check presents of files ######

        # select the folder object
        # Check that the retrieved folder is there
        try:
            out_folder = retrieved[self._calc._get_linkname_retrieved()]
        except KeyError:
            self.logger.error("No retrieved folder found")
            return False, ()

        # check what is inside the folder
        list_of_files = out_folder.get_folder_list()
        self.logger.info("file list {}".format(list_of_files))

        # has output xml file, otherwise error
        if self._calc._OUTXML_FILE_NAME not in list_of_files:
            successful = False
            self.logger.error(
                "XML out not found '{}'".format(self._calc._OUTXML_FILE_NAME))
        else:
            has_xml_outfile = True

        # check if all files expected are there for the calculation
        #print self._should_retrieve
        for filel in self._should_retrieve:
            if filel not in list_of_files:
                successful = False
                self.logger.warning(
                    "'{}' file not found in retrived folder, it"
                    " was probable not created by fleur".format(filel))

        # check if something was written to the error file
        if self._calc._ERROR_FILE_NAME in list_of_files:
            errorfile = os.path.join(out_folder.get_abs_path('.'),
                                     self._calc._ERROR_FILE_NAME)
            # read
            error_file_lines = ''
            try:
                with open(errorfile, 'r') as efile:
                    error_file_lines = efile.read()  # Note: read(), not readlines()
            except IOError:
                self.logger.error(
                    "Failed to open error file: {}.".format(errorfile))

            # if not empty, has_error equals True, parse error.
            if error_file_lines:
                self.logger.warning(
                    "The following was written into std error and piped to {} : \n {}"
                    "".format(self._calc._ERROR_FILE_NAME, error_file_lines))

                if 'OK' in error_file_lines: # if judft-error # TODO maybe change.
                    successful = True
                else:
                    successful = False

        if successful == False:
            return successful, ()

        #what about other files?
        #check input dict

        if self._calc._DOS_FILE_NAME in list_of_files:
            has_dos = True
        if self._calc._BAND_FILE_NAME in list_of_files:
            has_bands = True

        #if a new inp.xml file was created (new stucture)
        if self._calc._NEW_XMlINP_FILE_NAME in list_of_files:
            self.logger.error("new inp.xml file found in retrieved folder")
            has_new_xmlinp_file = True
        # add files which should also be there in addition to default_files.

        ################################
        ####### Parse the files ########

        if has_xml_outfile:
            # get outfile path and call xml out parser
            outxmlfile = os.path.join(
                out_folder.get_abs_path('.'), self._calc._OUTXML_FILE_NAME)
            simpledata, complexdata, parser_info, success = parse_xmlout_file(outxmlfile)

            # Call routines for output node creation
            if simpledata:
                outputdata = dict(simpledata.items() + parser_info.items())
                outxml_params = ParameterData(dict=outputdata)
                link_name = self.get_linkname_outparams()# accessible via c.res
                new_nodes_list.append((link_name, outxml_params))

            if complexdata:
                parameter_data = dict(complexdata.items() + parser_info.items())
                outxml_params_complex = ParameterData(dict=parameter_data)
                link_name = self.get_linkname_outparams_complex()
                new_nodes_list.append((link_name, outxml_params_complex))

            #greate new fleurinpData object if needed

            #fleurinp_Data = FleurinpData(files= [inpxmlfile])
            #, symoutfile, enparafile])
            #self.logger.info('FleurinpData initialized')
            #self.logger.info
            #link_name_fleurinp = 'fleurinpData'

            # return it to the execmanager / maybe later not
            #new_nodes_list.append((link_name_fleurinp, fleurinp_Data))

            # load old fleurinpdata

            # if structure changed, create new fleurinpdata of new inp.xml file.
            # and parse the structure

        # optional parse other files

        # DOS
        if has_dos_file:
            dos_file = os.path.join(
                out_folder.get_abs_path('.'), self._calc._DOS_FILE_NAME)
            #if dos_file is not None:
            try:
                with open(dos_file, 'r') as dosf:
                    dos_lines = dosf.read()  # Note: read() and not readlines()
            except IOError:
                raise FleurOutputParsingError(
                    "Failed to open DOS file: {}.".format(dos_file))
            dos_data = parse_dos_file(dos_lines)#, number_of_atom_types)

            # save array

        # Bands
        if has_bands_file:
            # TODO be carefull there might be two files.
            band_file = os.path.join(
                out_folder.get_abs_path('.'), self._calc._BAND_FILE_NAME)

            #if band_file is not None:
            try:
                with open(band_file, 'r') as bandf:
                    bands_lines = bandf.read()  # Note: read() and not readlines()
            except IOError:
                raise FleurOutputParsingError(
                          "Failed to open bandstructure file: {}."
                          "".format(band_file))
            bands_data = parse_bands_file(bands_lines)

                # save array
        if has_new_xmlinp_file:
            new_inpxmlfile = os.path.join(
                out_folder.get_abs_path('.'), self._calc._NEW_XMlINP_FILE_NAME)
            new_fleurinpData = FleurinpData()
            new_fleurinpData.set_file(new_inpxmlfile, dst_filename= 'inp.xml')
            self.logger.info('New FleurinpData initialized')
            link_name = 'fleurinpData'#self.get_linkname_outparams()# accessible via c.res
            new_nodes_list.append((link_name, new_fleurinpData))

        # Spectra

        return successful, new_nodes_list

def parse_xmlout_file(outxmlfile):
    """
    Parses the out.xml file of a FLEUR calculation
    Receives as input the absolut path to the xml output file

    :param outxmlfile: path to out.xml file

    :returns xml_data_dict: a simple dictionary (QE output like)
                            with parsed data

    :raises FleurOutputParsingError: for errors in the parsing?
    """
    from lxml import etree#, objectify
    #from lxml.etree import XMLSyntaxError

    global parser_info_out

    parser_info_out = {'parser_warnings': [], 'unparsed' : []}
    parser_version = '0.1beta'
    parser_info_out['parser_info'] = 'AiiDA Fleur Parser v{}'.format(parser_version)
    #parsed_data = {}

    successful = True
    outfile_broken = False
    parse_xml = True
    parser = etree.XMLParser(recover=False)#, remove_blank_text=True)

    try:
        tree = etree.parse(outxmlfile, parser)
    except etree.XMLSyntaxError:
        outfile_broken = True
        parser_info_out['parser_warnings'].append(
            'The out.xml file is broken I try to repair it.')


    if outfile_broken:
        #repair xmlfile and try to parse what is possible.
        parser = etree.XMLParser(recover=True)#, remove_blank_text=True)
        try:
            tree = etree.parse(outxmlfile, parser)
        except etree.XMLSyntaxError:
            #raise FleurOutputParsingError(
            #    "Failed to parse broken xml file: {}.".format(xml_file))
            parser_info_out['parser_warnings'].append(
                'Skipping the parsing of the xml file. '
                'Repairing was not possible.')
            parse_xml = False
            successful = False

    def parse_simplexmlout_file(root, outfile_broken):
        """
        Parses the xml.out file of a Fleur calculation
        Receives in input the root of an xmltree of the xml output file

        :param xmltree: root node of etree of out.xml file

        :returns xml_data_dict: a simple dictionary (QE output like)
                                with parsed data

        :raises FleurOutputParsingError: for errors in the parsing?
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
        #lda_plus_u_calculation_xpath = ''
        #non_colinear_calculation_xpath = ''
        #inversion_symmetry = ''
        #coretail_correction = ''
        #xc_relatvistic_correction =''
        #lapw_basis_size =''
        spin_orbit_calculation = 'calculationSetup/soc'
        smearing_energy_xpath = 'calculationSetup/bzIntegration/@fermiSmearingEnergy'
        jspin_name = 'jspins'

        # timing
        start_time_xpath  = '/fleurOutput/startDateAndTime/@time'
        end_time_xpath = '/fleurOutput/endDateAndTime/@time'
        start_date_xpath  = '/fleurOutput/startDateAndTime/@date'
        end_date_xpath = '/fleurOutput/endDateAndTime/@date'



        ###########

        # get all iterations in out.xml file
        iteration_nodes = eval_xpath2(root, iteration_xpath)
        nIteration = len(iteration_nodes)
        #print nIteration
        data_exists = True

        # parse only last stable interation
        # (if modes (dos and co) maybe parse anyway if broken?)
        if outfile_broken and (nIteration >= 2):
            iteration_to_parse = iteration_nodes[-2]
            parser_info_out['last_iteration_parsed'] = nIteration-2
        elif outfile_broken and (nIteration == 1):
            iteration_to_parse = iteration_nodes[0]
            parser_info_out['last_iteration_parsed'] = nIteration
        elif not outfile_broken and (nIteration >= 1):
            iteration_to_parse = iteration_nodes[-1]
        else: # dont parse? # there was no iteration found.
            # maybe only the starting charge density was calculated
            parser_info_out['parser_warnings'].append(
                'There was no iteration found in the outfile, either just a '
                'starting density was generated or something went wrong.')
            data_exists = False
            iteration_to_parse = None

        # for getting the fleur modes use fleurinp methods
        spin = get_xml_attribute(eval_xpath(root, magnetism_xpath), jspin_name)
        if spin:
            Fleurmode = {'jspin' : int(spin)}
        else:
            Fleurmode = {'jspin' : 1}
        if data_exists:
            simple_data = parse_simple_outnode(iteration_to_parse, Fleurmode)
        else:
            simple_data = {}


        warnings={'info': {}, 'debug' : {}, 'warning' : {}, 'error' : {}}

        simple_data['number_of_atoms'] = (len(eval_xpath2(root, relPos_xpath)) +
                                          len(eval_xpath2(root, absPos_xpath)) +
                                          len(eval_xpath2(root, filmPos_xpath)))
        simple_data['number_of_atom_types'] = len(eval_xpath2(root, atomstypes_xpath))
        simple_data['number_of_iterations'] = nIteration
        simple_data['number_of_symmetries'] = len(eval_xpath2(root, symmetries_xpath))
        simple_data['number_of_species'] = len(eval_xpath2(root, species_xpath))
        simple_data['number_of_kpoints'] = len(eval_xpath2(root, kpoints_xpath))
        simple_data['number_of_spin_components'] = Fleurmode['jspin']

        title = eval_xpath(root, title_xpath)
        if title:
            title = str(title).strip()
        simple_data['title'] = title
        simple_data['creator_name'] = eval_xpath(root, creator_name_xpath)
        simple_data['creator_target_architecture'] = eval_xpath(root, creator_target_architecture_xpath)
        simple_data['creator_target_structure'] = eval_xpath(root, creator_target_structure_xpath)
        simple_data['output_file_version'] = eval_xpath(root, output_version_xpath)

        warnings['info'] = {}#TODO
        warnings['debug'] = {} #TODO
        warnings['warning'] = {}#TODO
        warnings['error'] = {}#TODO
        simple_data['warnings'] = warnings


        # time
        starttime = eval_xpath(root, start_time_xpath)
        #print starttime
        if starttime:
            starttimes = starttime.split(':')
        else:
            starttimes = [0,0,0]

        endtime = eval_xpath(root, end_time_xpath)
        if endtime:
            endtime = endtime.split(':')
        else:
            endtime = [0,0,0]
        start_date = eval_xpath(root, start_date_xpath)
        end_date = eval_xpath(root, end_date_xpath)

        offset = 0
        if start_date != end_date:
            pass
            offset = 0

        time = offset + (int(endtime[0])-int(starttimes[0]))*60*60 + (int(endtime[1])-int(starttimes[1]))*60 + int(endtime[2]) - int(starttimes[2])
        simple_data['walltime'] = time
        simple_data['walltime_units'] = 'seconds'
        simple_data['start_date'] = {'date' : start_date, 'time' : starttime}
        return simple_data


    def eval_xpath(node, xpath):
        """
        Tries to evalutate an xpath expression. If it fails it logs it.

        :param root node of an etree and an xpath expression (relative, or absolute)
        :returns either nodes, or attributes, or text
        """
        try:
            return_value = node.xpath(xpath)
        except etree.XPathEvalError:
            parser_info_out['parser_warnings'].append(
                'There was a XpathEvalError on the xpath: {} \n Either it does '
                'not exist, or something is wrong with the expression.'
                ''.format(xpath))
            return []# or rather None?
        if len(return_value) == 1:
            return return_value[0]
        else:
            return return_value

    def eval_xpath2(node, xpath):
        """
        Tries to evalutate an xpath expression. If it fails it logs it.

        :param root node of an etree and an xpath expression (relative, or absolute)
        :returns ALWAYS a node list
        """
        try:
            return_value = node.xpath(xpath)
        except etree.XPathEvalError:
            parser_info_out['parser_warnings'].append(
                'There was a XpathEvalError on the xpath: {} \n Either it does '
                'not exist, or something is wrong with the expression.'
                ''.format(xpath))
            return []
        if len(return_value) == 1:
            return return_value
        else:
            return return_value

    def get_xml_attribute(node, attributename):
        """
        Get an attribute value from a node.

        :param node: a node from etree
        :param attributename: a string with the attribute name.
        :returns either attributevalue, or None
        """
        if etree.iselement(node):
            attrib_value = node.get(attributename)
            if attrib_value:
                return attrib_value
            else:
                parser_info_out['parser_warnings'].append(
                    'Tried to get attribute: "{}" from element {}.\n '
                    'I recieved "{}", maybe the attribute does not exist'
                    ''.format(attributename, node, attrib_value))
                return None
        else: # something doesn't work here, some nodes get through here
            parser_info_out['parser_warnings'].append(
                'Can not get attributename: "{}" from node "{}", '
                'because node is not an element of etree.'
                ''.format(attributename, node))

            return None


    def convert_to_float(value_string):
        """
        Tries to make a float out of a string. If it can't it logs a warning
        and returns True or False if convertion worked or not.

        :param value_string: a string
        :returns value: the new float or value_string: the string given
        :retruns True or Falses
        """
        # TODO lowercase everything
        try:
            value = float(value_string)
        except TypeError:
            parser_info_out['parser_warnings'].append(
                'Could not convert: "{}" to float, TypeError'
                ''.format(value_string))
            return value_string, False
        except ValueError:
            parser_info_out['parser_warnings'].append(
                'Could not convert: "{}" to float, ValueError'
                ''.format(value_string))
            return value_string, False
        return value, True

    def convert_to_int(value_string):
        """
        Tries to make a int out of a string. If it can't it logs a warning
        and returns True or False if convertion worked or not.

        :param value_string: a string
        :returns value: the new int or value_string: the string given
        :retruns True or False
        """
        try:
            value = int(value_string)
        except TypeError:
            parser_info_out['parser_warnings'].append(
                'Could not convert: "{}" to int, TypeError'
                ''.format(value_string))
            return value_string, False
        except ValueError:
            parser_info_out['parser_warnings'].append(
                'Could not convert: "{}" to int, ValueError'
                ''.format(value_string))
            return value_string, False
        return value, True


    def convert_htr_to_ev(value):
        """
        Multiplies the value given with the Hartree factor (converts htr to eV)
        """
        htr = 27.21138602
        suc = False
        value_to_save, suc = convert_to_float(value)
        if suc:
            return value_to_save*htr
        else:
            return value

    def parse_simple_outnode(iteration_node, Fleurmode):
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

        #magnetic moments
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


        spinupcharge_name = 'spinUpCharge'
        spindowncharge_name = 'spinDownCharge'
        moment_name = 'moment'


        # all electron charges

        allelectronchages_xpath = ''

        a = 'total'
        b = 'interstitial'
        c ='value'
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
        ###################################################

        jspin = Fleurmode['jspin']
        simple_data = {}


        def write_simple_outnode(value, value_type, value_name, dict):
            """
            writes a value (int or float) in the simple data dict.
            if path does not exit it initializes it!

            if the value has not the type given,
            it will be logged in parser info instead of writing.

            :param value: value
            """

            interation_current_number_name = 'numberForCurrentRun'
            suc = False

            if value_type == 'float':
                value_to_save, suc = convert_to_float(value)
            elif value_type == 'int':
                value_to_save, suc = convert_to_int(value)
            elif value_type == 'str':
                suc = True
                value_to_save = value
                #value_to_save, suc = convert_to_str(value)
            elif value_type =='list':
                suc = True
                value_to_save = value
            elif value_type =='list_floats':
                value_to_save = []
                for val in value:
                    value_to_savet, suct = convert_to_float(val)
                    value_to_save.append(value_to_savet)
                suc = True # TODO individual or common error message?
            elif value_type =='list_list_floats':
                value_to_save = []
                for val in value:
                    value_to_savet = []
                    for val1 in val:
                        value_to_savet1, suct = convert_to_float(val1)
                        value_to_savet.append(value_to_savet1)
                    value_to_save.append(value_to_savet)
                suc = True # TODO individual or common error message?
            else:
                print 'I dont know the type you gave me {}'.format(type)
                # TODO log error
            if suc:
                dict[value_name] = value_to_save
            else:
                parser_info_out['unparsed'].append(
                    {value_name : value,
                     'iteration' : get_xml_attribute(iteration_node, interation_current_number_name)})


        # total energy
        units_e = get_xml_attribute(
            eval_xpath(iteration_node, totalenergy_xpath), units_name)
        write_simple_outnode(
            units_e, 'str', 'energy_hartree_units', simple_data)

        tE_htr = get_xml_attribute(
            eval_xpath(iteration_node, totalenergy_xpath), value_name)
        write_simple_outnode(tE_htr, 'float', 'energy_hartree', simple_data)

        write_simple_outnode(
            convert_htr_to_ev(tE_htr), 'float', 'energy', simple_data)
        write_simple_outnode('eV', 'str', 'energy_units', simple_data)

        sumofeigenvalues = get_xml_attribute(
            eval_xpath(iteration_node, sumofeigenvalues_xpath), value_name)
        write_simple_outnode(
            sumofeigenvalues, 'float', 'sum_of_eigenvalues', simple_data)

        coreElectrons = get_xml_attribute(
            eval_xpath(iteration_node, core_electrons_xpath), value_name)
        write_simple_outnode(
            coreElectrons, 'float', 'energy_core_electrons', simple_data)

        valenceElectrons = get_xml_attribute(
            eval_xpath(iteration_node, valence_electrons_xpath), value_name)
        write_simple_outnode(
            valenceElectrons, 'float', 'energy_valence_electrons', simple_data)

        ch_d_xc_d_inte = get_xml_attribute(
            eval_xpath(iteration_node, chargeden_xc_den_integral_xpath), value_name)
        write_simple_outnode(
            ch_d_xc_d_inte, 'float', 'charge_den_xc_den_integral', simple_data)

        # bandgap
        units_bandgap = get_xml_attribute(
            eval_xpath(iteration_node, bandgap_xpath), units_name)
        write_simple_outnode(units_bandgap, 'str', 'bandgap_units', simple_data)

        bandgap = get_xml_attribute(
            eval_xpath(iteration_node, bandgap_xpath), value_name)
        write_simple_outnode(bandgap, 'float', 'bandgap', simple_data)

        # fermi
        fermi_energy = get_xml_attribute(
            eval_xpath(iteration_node, fermi_energy_xpath), value_name)
        write_simple_outnode(fermi_energy, 'float', 'fermi_energy', simple_data)
        units_fermi_energy = get_xml_attribute(
            eval_xpath(iteration_node, fermi_energy_xpath), units_name)
        write_simple_outnode(
            units_fermi_energy, 'str', 'fermi_energy_units', simple_data)

        # density convergence
        units = get_xml_attribute(
            eval_xpath(iteration_node, densityconvergence_xpath), units_name)
        write_simple_outnode(
            units, 'str', 'density_convergence_units', simple_data)


        if jspin == 1:
            charge_density = get_xml_attribute(
                eval_xpath(iteration_node, chargedensity_xpath), distance_name)
            write_simple_outnode(
                charge_density, 'float', 'charge_density', simple_data)

        elif jspin == 2:
            charge_densitys = eval_xpath(iteration_node, chargedensity_xpath)
            charge_density1 = get_xml_attribute(charge_densitys[0], distance_name)
            write_simple_outnode(
                charge_density1, 'float', 'charge_density1', simple_data)

            charge_density2 = get_xml_attribute(charge_densitys[1], distance_name)
            write_simple_outnode(
                charge_density2, 'float', 'charge_density2', simple_data)

            spin_density = get_xml_attribute(
                eval_xpath(iteration_node, spindensity_xpath), distance_name)
            write_simple_outnode(
                spin_density, 'float', 'spin_density', simple_data)

            overall_charge_density = get_xml_attribute(
                eval_xpath(iteration_node, overallchargedensity_xpath), distance_name)
            write_simple_outnode(
                overall_charge_density, 'float', 'overall_charge_density', simple_data)

            # magnetic moments            #TODO orbMag Moment
            m_units = get_xml_attribute(
                eval_xpath(iteration_node, magnetic_moments_in_mtpheres_xpath), units_name)
            write_simple_outnode(
                m_units, 'str', 'magnetic_moment_units', simple_data)
            write_simple_outnode(
                m_units, 'str', 'orbital_magnetic_moment_units', simple_data)

            moments = eval_xpath(iteration_node, magneticmoments_xpath)
            write_simple_outnode(
                moments, 'list_floats', 'magnetic_moments', simple_data)

            spinup = eval_xpath(iteration_node, magneticmoments_spinupcharge_xpath)
            write_simple_outnode(
                spinup, 'list_floats', 'magnetic_spin_up_charges', simple_data)

            spindown = eval_xpath(iteration_node, magneticmoments_spindowncharge_xpath)
            write_simple_outnode(
                spindown, 'list_floats', 'magnetic_spin_down_charges', simple_data)

            #orbital magnetic moments
            orbmoments = eval_xpath(iteration_node, orbmagneticmoments_xpath)
            write_simple_outnode(
                orbmoments, 'list_floats', 'orbital_magnetic_moments', simple_data)

            orbspinup = eval_xpath(iteration_node, orbmagneticmoments_spinupcharge_xpath)
            write_simple_outnode(
                orbspinup, 'list_floats', 'orbital_magnetic_spin_up_charges', simple_data)

            orbspindown = eval_xpath(iteration_node, orbmagneticmoments_spindowncharge_xpath)
            write_simple_outnode(
                orbspindown, 'list_floats', 'orbital_magnetic_spin_down_charges', simple_data)

            # TODO atomtype dependence
            #moment = get_xml_attribute(
            #    eval_xpath(iteration_node, magneticmoment_xpath), moment_name)
            #print moment
            #write_simple_outnode(moment, 'float', 'magnetic_moment', simple_data)

            #spinup = get_xml_attribute(
            #    eval_xpath(iteration_node, magneticmoment_xpath), spinupcharge_name)
            #write_simple_outnode(spinup, 'float', 'spin_up_charge', simple_data)

            #spindown = get_xml_attribute(
            #    eval_xpath(iteration_node, magneticmoment_xpath), spindowncharge_name)
            #write_simple_outnode(spindown, 'float', 'spin_down_charge', simple_data)

            #Total charges, total magentic moment

        # total iterations
        number_of_iterations_total = get_xml_attribute(
            eval_xpath(iteration_node, iteration_xpath), overall_number_name)
        write_simple_outnode(
            number_of_iterations_total, 'int', 'number_of_iterations_total', simple_data)


        #forces atomtype dependend
        forces = eval_xpath2(iteration_node, forces_total_xpath)
        # length should be ntypes
        #print forces
        largest_force = -0.0
        for force in forces:
            atomtype, success = convert_to_int(get_xml_attribute(force, atomtype_name))

            forces_unit = get_xml_attribute(
                eval_xpath(iteration_node, forces_units_xpath), units_name)
            write_simple_outnode(forces_unit, 'str', 'force_units', simple_data)

            force_x = get_xml_attribute(force, f_x_name)
            write_simple_outnode(
                force_x, 'float', 'force_x_type{}'.format(atomtype), simple_data)

            force_y = get_xml_attribute(force, f_y_name)
            write_simple_outnode(
                force_y, 'float', 'force_y_type{}'.format(atomtype), simple_data)

            force_z = get_xml_attribute(force, f_z_name)
            write_simple_outnode(
                force_z, 'float', 'force_z_type{}'.format(atomtype), simple_data)


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
            write_simple_outnode(
                pos_x, 'float', 'abspos_x_type{}'.format(atomtype), simple_data)
            pos_y = get_xml_attribute(force, new_y_name)
            write_simple_outnode(
                pos_y, 'float', 'abspos_y_type{}'.format(atomtype), simple_data)
            pos_z = get_xml_attribute(force, new_z_name)
            write_simple_outnode(
                pos_z, 'float', 'abspos_z_type{}'.format(atomtype), simple_data)

        write_simple_outnode(
            largest_force, 'float', 'force_largest', simple_data)

        return simple_data


    if parse_xml:
        root = tree.getroot()
        simple_out = parse_simplexmlout_file(root, outfile_broken)
        simple_out['outputfile_path'] = outxmlfile
        #TODO parse complex out
        complex_out = {} #parse_xmlout_file(root)
        return simple_out, complex_out, parser_info_out, successful
    else:
        return {}, {}, parser_info_out, successful



def parse_dos_file(dos_lines):#, number_of_atom_types):
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
    #pass
    return 0

def parse_bands_file(bands_lines):
    '''
    Parses the returned bands.1 and bands.2 file and returns a complete
    bandsData object. bands.1 has the form: k value, energy

    :param bands_lines: string of the read in bands file
    '''
    # TODO not finished
    # read bands out of file:
    nrows = 0 # get number of rows (known form number of atom types
    bands_values = [] #init an array of arrays nkpoint * ...
    bands_labels = [] # label for each row.

    # fill and correct fermi energy.
    bands_values = []


    # TODO we need to get the cell from StructureData node
    # and KpointsData node from inpxml
    fleur_bands = BandsData()
    #fleur_bands.set_cell(cell)
    #fleur_bands.set_kpoints(kpoints, cartesian=True)
    fleur_bands.set_bands(bands=bands_values,
                          units='eV',
                          labels=bands_labels)

    for line in bands_lines:
        pass
    return fleur_bands

