# -*- coding: utf-8 -*-
"""
In this module is the FleurinpData class, and methods for FLEUR input
manipulation plus methods for extration of AiiDA data structures.
"""
# TODO: this needs to be cleaned up and redocumented
# TODO: all methods to change now in fleurinpmodifier, do we still want to
# store the userchanges, or rather delete them? depends how well one can see things
# from fleurinpmodifier...
# TODO: maybe add a modify method which returns a fleurinpmodifier class
# TODO: inpxml to dict: maybe kpts should not be writen to the dict? same with symmetry
# TODO: test for large input files, I believe the recursion is still quite slow..
# TODO: 2D cell get kpoints and get structure also be carefull with tria = T!!!
#TODO : maybe save when get_structure or get_kpoints was executed on fleurinp,
# because otherwise return this node instead of creating a new one!
__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

import os
import re
from lxml import etree
#from lxml.etree import XMLSyntaxError
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import Data
from aiida.common.exceptions import InputValidationError, ValidationError
from aiida_fleur.tools.xml_util import xml_set_attribv_occ, xml_set_first_attribv
from aiida_fleur.tools.xml_util import  xml_set_all_attribv, xml_set_text, replace_tag
from aiida.work.workfunction import workfunction as wf
from aiida_fleur.fleur_schema.schemafile_index import get_internal_search_paths, get_schema_paths

bohr_a = 0.52917721092#A, todo: get from somewhereA


class FleurinpData(Data):
    """
    AiiDA data object representing everything a FLEUR calculation needs.

    It is initialized with an absolute path to an inp.xml file.
    Other files can also be added, which will be compied to the remote machine, where the calculation takes place.

    It stores the files in the repository and stores the input parameters of the
    inp.xml file of FLEUR in the Database as a python dictionary (as internal attributes).
    When an inp.xml (name important!) file is added to files, FleurinpData searches
    for a corresponding xml schema file in the PYTHONPATH environment variable.
    Therefore, it is recommened to have the plug-in source code directory in the python environment..
    If no corresponding schema file is found an error is raised.

    FleurinpData further provides the user with
    methods to extract AiiDA StructureData and KpointsData nodes.

    Remember that most attributes of AiiDA nodes can not be changed after they
    have been stored in the DB! Therefore, you have to use the FleurinpModifier class and its methods
    if you want to change somthing in the inp.xml file. You will retrieve a new FLeurinpdata that way and
    start a new calculation from it.
    """

    # serach in current folder and search in aiida source code
    # we want to search in the Aiida source directory, get it from python path,
    # maybe better from somewhere else.
    #TODO: dont walk the whole python path, test if dir below is aiida?
    #needs to be imporved, schema file is often after new installation not found...
    #installation with pip should always lead to a schmea file in the python path, or even specific place

    _search_paths = []
    ifolders = get_internal_search_paths()
    ischemas = get_schema_paths()
    for path in ischemas:
        _search_paths.append(path)
    for path in ifolders:
        _search_paths.append(path)
    _search_paths.append('./')

    # Now add also python path maybe will be decaptivated
    #if pythonpath is non existant catch error
    try:
        pythonpath = os.environ['PYTHONPATH'].split(':')
    except KeyError:
        pythonpath = []

    for path in pythonpath[:]:
        _search_paths.append(path)

    #_search_paths = ['./', '/Users/broeder/aiida/codes/fleur/',
    #                 str(get_repository_folder())]

    @property
    def _has_schema(self):
        """
        Boolean property, which stores if a schema file is already known
        """
        return self.get_attr('_has_schema', False)

    @property
    def _schema_file_path(self):
        """
        A string, which stores the absolute path to the schemafile fount
        """
        return self.get_attr('_schema_file_path', None)

    @_has_schema.setter
    def _has_schema(self, boolean):
        """
        Setter for has_schema
        """
        self._set_attr('_has_schema', boolean)

    @_schema_file_path.setter
    def _schema_file_path(self, schemapath):
        """
        Setter for the schema file path
        """
        self._set_attr('_schema_file_path', schemapath)

    # files
    @property
    def files(self):
        """
        Returns the list of the names of the files stored
        """
        return self.get_attr('files', [])

    @files.setter
    def files(self, filelist):
        """
        Add a list of files to FleurinpData.
        Alternative use setter method.

        :param files: list of filepaths
        """
        for file1 in filelist:
            self.set_file(file1)

    def set_files(self, files):
        """
        Add a list of files to FleurinpData
        Alternative setter

        :param files: list of filepaths
        """
        self.files = files

    def set_file(self, filename, dst_filename=None):
        """
        Add a file to the FleurinpData

        :param filename: absolute path to the file
        """
        self._add_path(filename, dst_filename=dst_filename)

    def del_file(self, filename):
        """
        Remove a file from FleurinpData

        :param filename: name of the file stored in the DB
        """
        # remove from files attr list
        if filename in self.get_attr('files'):
            try:
                self.get_attr('files').remove(filename)
                #self._del_attr('filename')
            except AttributeError:
                ## There was no file set
                pass
        # remove from sandbox folder
        if filename in self.get_folder_list():
            super(FleurinpData, self).remove_path(filename)

    def get_file_abs_path(self, filename):
        """
        Return the absolute path to a file in the repository

        :param filename: name of the file

        """
        if filename in self.files:
            return os.path.join(self._get_folder_pathsubfolder.abspath, filename)
        else:
            raise ValueError(
                '{} is not in {}'.format(filename,
                    os.path.join(self._get_folder_pathsubfolder.abspath)))

    def find_schema(self, inp_version_number):
        """
        Method which searches for a schema files (.xsd) which corresponds
        to the input xml file. (compares the version numbers)
        """
        # user changed version number, or no file yet known.
        # TODO test if this still does the right thing if user adds one
        #inp.xml and then an inp.xml with different version.
        # or after copying and read
        schemafile_paths = []
        #print 'searching schema file'
        for path in self._search_paths:#paths:
            for root, dirs, files in os.walk(path):
                for file1 in files:
                    if file1.endswith(".xsd"):
                        if ('Fleur' in file1) or ('fleur' in file1):
                            schemafile_path = os.path.join(root, file1)
                            #print schemafile_path
                            schemafile_paths.append(schemafile_path)
                            i = 0
                            imin = 0
                            imax = 0
                            schemafile = open(schemafile_path, 'r')
                            for line in schemafile.readlines():
                                i = i + 1
                                # This kind of hardcoded
                                if re.search('name="FleurVersionType"', line):
                                    imax = i + 10 # maybe make larger or different
                                    imin = i
                                    schema_version_numbers = []
                                if (i > imin) and (i <= imax):
                                    if re.search('enumeration value', line):
                                        schema_version_number = re.findall(r'\d+.\d+', line)[0]
                                        #print 'schemaversion number: ' + str(schema_version_number)
                                        #break
                                        schema_version_numbers.append(schema_version_number)
                                    elif re.search('simpleType>', line):
                                        break
                            schemafile.close()
                            #test if schemafiles works with multiple fleur versions
                            for version_number in schema_version_numbers:
                                if version_number == inp_version_number:
                                    #we found the right schemafile for the current inp.xml
                                    self._set_attr('_schema_file_path', schemafile_path)
                                    self._set_attr('_has_schema', True)
                                    #print schemafile_paths
                                    return schemafile_paths, True
        #print schemafile_paths
        return schemafile_paths, False

    def _add_path(self, src_abs, dst_filename=None):
        """
        Add a single file to folder

        """
        #TODO, only certain files should be allowed to be added
        #_list_of_allowed_files = ['inp.xml', 'enpara', 'cdn1', 'sym.out', 'kpts']

        old_file_list = self.get_folder_list()

        if not os.path.isabs(src_abs):
            raise ValueError("Pass an absolute path for src_abs: {}".format(src_abs))

        if not os.path.isfile(src_abs):
            raise ValueError("src_abs must exist and must be a single file: {}".format(src_abs))

        if dst_filename is None:
            final_filename = os.path.split(src_abs)[1]
        else:
            final_filename = dst_filename

        super(FleurinpData, self).add_path(src_abs, final_filename)

        old_files_list = self.get_attr('files', [])

        if final_filename not in old_file_list:
            old_files_list.append(final_filename)
        self._set_attr('files', old_files_list)

        # here this is hardcoded, might want to change? get filename from elsewhere
        if final_filename == 'inp.xml':
            #get input file version number
            inpfile = open(src_abs, 'r')
            for line in inpfile.readlines():
                if re.search('fleurInputVersion', line):
                    inp_version_number = re.findall(r'\d+.\d+', line)[0]
                    break
            inpfile.close()
            # search for Schema file with same version number
            schemafile_paths, found = self.find_schema(inp_version_number)
            #print 'found: {}'.format(found)
            #print self._schema_file_path
            #print self.inp_userchanges.has_key('fleurInputVersion')

            if (self._schema_file_path is None) or (self.inp_userchanges.has_key('fleurInputVersion')): #(not)
                schemafile_paths, found = self.find_schema(inp_version_number)
                if not(found):
                    raise InputValidationError("No XML schema file (.xsd) with matching version number {} "
                        "to the inp.xml file was found. I have looked here: {} "
                        "and have found only these schema files for Fleur: {}. "
                        "I need this file to validate your input and to know the structure "
                        "of the current inp.xml file, sorry.".format(inp_version_number,
                                                          self._search_paths, schemafile_paths))
            if (not self._has_schema) and (self._schema_file_path is None):
                raise InputValidationError("No XML schema file (.xsd) with matching version number {} "
                    "to the inp.xml file was found. I have looked here: {} "
                    "and have found only these schema files for Fleur: {}. "
                    "I need this file to validate your input and to know the structure "
                    "of the current inp.xml file, sorry.".format(inp_version_number,
                                                          self._search_paths, schemafile_paths))
            #print 'self._schema_file_path: {}'.format(self._schema_file_path)
            #print 'self._has_schema: {}'.format(self._has_schema)
            # set inp dict of Fleurinpdata
            self._set_inp_dict()

    def _set_inp_dict(self):
        """
        Sets the inputxml_dict from the inp.xml file attached to FleurinpData

        1. get inp.xml strucutre/layout
        2. load inp.xml file
        3. call inpxml_to_dict
        4. set inputxml_dict
        """
        from aiida_fleur.tools.xml_util import get_inpxml_file_structure, inpxml_todict
        # get inpxml structure
        inpxmlstructure = get_inpxml_file_structure()

        # read xmlinp file into an etree with autocomplition from schema
        inpxmlfile = self.get_file_abs_path('inp.xml')

        xmlschema_doc = etree.parse(self._schema_file_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
        #dtd_validation=True

        tree = etree.parse(inpxmlfile)#, parser)
        # there is a bug when validating at parsetime, therefore we only
        #validate at parse time if file is invalid, to get nice error message
        if not xmlschema.validate(tree):
            tree = etree.parse(inpxmlfile, parser)

        root = tree.getroot()

        # convert etree into python dictionary
        inpxml_dict = inpxml_todict(root, inpxmlstructure)

        # set inpxml_dict attribute
        self._set_attr('inp_dict', inpxml_dict)


    # tracing user changes
    @property
    def inp_userchanges(self):
        """
        Return the changes done by the user on the inp.xml file.
        """
        return self.get_attr('inp_userchanges', {})

    # dict with inp paramters parsed from inp.xml
    @property
    def inp_dict(self):
        """
        Returns the inp_dict (the representation of the inp.xml file) as it will
        or is stored in the database.
        """
        return self.get_attr('inp_dict', {})
    '''
    def set_inpchanges(self, change_dict):
        """
        Does changes directly on the inp.xml file. Afterwards
        updates the inp.xml file representation and the current inp_userchanges
        dictionary with the keys provided in the 'change_dict' dictionary.

        :param change_dict: a python dictionary with the keys to substitute.
                            It works like dict.update(), adding new keys and
                            overwriting existing keys.
        """
        from aiida_fleur.tools.xml_util import write_new_fleur_xmlinp_file, get_inpxml_file_structure
        #TODO make some checks
        if self.inp_userchanges is None:
            self._set_attr('inp_userchanges', {})

        # store change dict, to trac changes
        currentchangedict = self.inp_userchanges
        currentchangedict.update(change_dict)
        self._set_attr('inp_userchanges', currentchangedict)

        # load file, if it does not exsist error will be thrown in routine
        inpxmlfile = self.get_file_abs_path('inp.xml')

        if self._has_schema:
           #schema file for validation will be loaded later
           pass
        elif self._schema_file_path != None:
            print ('Warning: The User set the XMLSchema file path manually, your'
                  'inp.xml will be evaluated! If it fails it is your own fault!')
        else:
            print ('Warning: No XMLSchema file was provided, your inp.xml file '
                  'will not be evaluated and parsed! (I should never get here)')

        #read in tree
        tree = etree.parse(inpxmlfile)

        #apply changes to etree
        xmlinpstructure = get_inpxml_file_structure()
        new_tree = write_new_fleur_xmlinp_file(tree, change_dict, xmlinpstructure)

        # TODO source this part out for other methods
        # somehow directly writing inp.xml does not work, create new one
        inpxmlfile = os.path.join(
                         self._get_folder_pathsubfolder.abspath, 'temp_inp.xml')

        # write new inp.xml, schema evaluation will be done when the file gets added
        new_tree.write(inpxmlfile)
        #print 'wrote tree to' + str(inpxmlfile)

        #TODO maybe do some checks before
        self.del_file('inp.xml')

        # now the new inp.xml file is added and with that the inpxml_dict will
        # be overwritten, and the file validated
        self._add_path(str(inpxmlfile), 'inp.xml')

        # remove temporary inp.xml file
        os.remove(inpxmlfile)

    def set_xpath(self, xpath, value):
        """
        This is a general setter routine to change things in the inp.xml file.
        """
        from aiida_fleur.tools.xml_util import xml_set_all_attribv, xml_set_text

        # get file,
        # parse in etree
        # apply xpath
        #write and parse new_inp.xml

        inpxmlfile = self.get_file_abs_path('inp.xml')
        tree = etree.parse(inpxmlfile)

        # set xpath expression: # check how complicated xpath can be
        # check if last one is attribute, if yes get attribute name
        # set attrib #xml_set_all_attribv
        # if text use xml_set_text

        #xml_set_xpath(tree, xpath, value)
        inpxmlfile = os.path.join(
                         self._get_folder_pathsubfolder.abspath, 'temp_inp.xml')
        new_tree.write(inpxmlfile)
        self.del_file('inp.xml')
        self._add_path(str(inpxmlfile), 'inp.xml')
        os.remove(inpxmlfile)
        # write something in fleurinp change dict


    def set_species(self, species_name, attributedict):
        """
        This method can set certain things of a species in the inp.xml file
        """
        pass
        # get file
        # parse in etree
        # get species node
        # hardcode xpath? or find all?
        # for change in attribute dict
        # write something in fleurinp change dict

    def change_atom(self, attrib, value, position=None, species=None):
        """
        """
        pass
        #check if species and or postion is given
        # if position given, find atom with postion and change attrib value
        # if species given find all atom types of that species and change attrib value

        if position:
            pass
        elif species:
            pass
        else:
            pass
            # DO nothing
    '''


    '''
    ## !!! DATA-DATA links should not be done, until an other solution is found, I use them
    # and override methods from data
    @override
    def add_link_from(self, src, label=None, link_type=LinkType.UNSPECIFIED):
        #from aiida.orm.calculation import Calculation
        from aiida.orm import Node

        if link_type is LinkType.CREATE and \
                        len(self.get_inputs(link_type=LinkType.CREATE)) > 0:
            raise ValueError("At most one CREATE node can enter a data node")

        #if not isinstance(src, Calculation):
        #    raise ValueError(
        #        "Links entering a data object can only be of type calculation")
        #print 'I AM FREE'
        return super(Data, self).add_link_from(src, label, link_type) # <- does not work

    @override
    def _linking_as_output(self, dest, link_type):
        """
        Raise a ValueError if a link from self to dest is not allowed.

        An output of a data can only be a calculation
        """
        from aiida.orm import Node
        #from aiida.orm.calculation import Calculation
        #if not isinstance(dest, Calculation):
        #    raise ValueError(
        #        "The output of a data node can only be a calculation")
        #print 'I AM FREE TOOO'
        return super(Data, self)._linking_as_output(dest, link_type)# <- does not work
    '''
    def copy(self):
        """
        Method to copy a FleurinpData and keep the proverance.
        (because currently that is not default)
        """
        # copy only the files not the user changes and so on.

        filepath = []
        for file in self.files:
            filepath.append(self.get_file_abs_path(file))

        new = FleurinpData(files=filepath)
        #new.add_link_from(self, label='fleurinp.copy', link_type=LinkType.CREATE)
        return new

    # TODO better validation? other files, if has a schema
    def _validate(self):
        """
        validation method. Check here for properties that have to be there, for
        a valid fleurinpData object.
        """
        #from aiida.common.exceptions import ValidationError

        super(FleurinpData, self)._validate()

        if 'inp.xml' in self.files:
            #has_inpxml = True # does nothing so far
            pass
        else:
            raise ValidationError('inp.xml file not in attribute "files". '
                                  'FleurinpData needs to have and inp.xml file!')


    '''
        try:
            has_inpxml = 'inp.xml' in self.files
        except AttributeError:
            raise ValidationError("attribute 'filename' not set.")

        if self.files != self.get_folder_list():
            raise ValidationError("The list of files in the folder does not "
                                  "match the 'files' attribute. "
                                  "_files='{}', content: {}".format(
                self.files, self.get_folder_list()))
    '''

    '''
    def _write_new_fleur_xmlinp_file(self, inp_file_xmltree, fleur_change_dic):
        """
        This modifies the xml-inp file. Makes all the changes wanted by
        the user or sets some default values for certain modes

        :param inp_file_lines_o xml-tree of the xml-inp file
        :param fleur_change_dic dictionary {attrib_name : value} with all the
               wanted changes.

        return an etree of the xml-inp file with changes.
        """
        # TODO rename, name is misleaded just changes the tree.
        xmltree_new = inp_file_xmltree

        #get all attributes of a inpxml file
        xmlinpstructure = get_inpxml_file_structure()

        pos_switch_once = xmlinpstructure[0]
        pos_switch_several = xmlinpstructure[1]
        pos_attrib_once = xmlinpstructure[2]
        #pos_int_attributes_once = xmlinpstructure[3]
        #pos_float_attributes_once = xmlinpstructure[4]
        #pos_string_attributes_once = xmlinpstructure[5]
        pos_attrib_several = xmlinpstructure[6]
        pos_int_attributes_several = xmlinpstructure[7]
        #pos_float_attributes_several = xmlinpstructure[8]
        #pos_string_attributes_several = xmlinpstructure[9]
        #pos_tags_several = xmlinpstructure[10]
        pos_text = xmlinpstructure[11]
        pos_xpaths = xmlinpstructure[12]
        expertkey = xmlinpstructure[13]


        for key in fleur_change_dic:
            if key in pos_switch_once:
                # call routine set (key,value) in tree.
                # TODO: a test here if path is plausible and if exist
                # ggf. create tags and key.value is 'T' or 'F' if not convert,
                # if garbage, exception
                # convert user input into 'fleurbool'
                fleur_bool = convert_to_fortran_bool(fleur_change_dic[key])

                xpath_set = pos_xpaths[key]
                #TODO: check if something in setup is inconsitent?

                # apply change to tree
                #print xmltree_new, xpath_set, key, fleur_bool
                xml_set_first_attribv(xmltree_new, xpath_set, key, fleur_bool)

            elif key in pos_attrib_once:
                # TODO: same here, check existance and plausiblility of xpath
                xpath_set = pos_xpaths[key]
                #print xmltree_new, xpath_set, key, fleur_change_dic[key]
                xml_set_first_attribv(xmltree_new, xpath_set, key, fleur_change_dic[key])
            elif key in pos_attrib_several:
                # TODO What attribute shall be set? all, one or several specific onces?
                pass
            elif key in pos_switch_several:
                # TODO
                pass
            elif key in pos_text:
                # can be several times, therefore check
                xpath_set = pos_xpaths[key]
                xml_set_text(xmltree_new, xpath_set, fleur_change_dic[key])
            elif key == expertkey:
                # posibility for experts to set something, not suported by the plug-in directly
                pass
            else:
                # this key is not know to plug-in
                raise ValidationError(
                    "You try to set the key:'{}' to : '{}', but the key is unknown"
                    " to the fleur plug-in".format(key, fleur_change_dic[key]))
        return xmltree_new
    '''
    def get_fleur_modes(self):
        '''
        Retrieve information from the inp.xml file. 'Modes' are paths a FLEUR
        calculation can take, resulting in different output files, dependend on the input.
        i.e other files need to be copied before and after the calculation.
        common modes are: scf, jspin 2, dos, band, pot8, lda+U, eels, ...
        '''
        # TODO these should be retrieved by looking at the inpfile struture and
        # then setting the paths.
        # use methods from fleur parser...
        # For now they are hardcoded.
        #    'dos': '/fleurInput/output',
        #    'band': '/fleurInput/output',
        #    'pot8': '/fleurInput/calculationSetup/expertModes',
        #    'jspins': '/fleurInput/calculationSetup/magnetism',
        fleur_modes = {'jspins' : '', 'dos' : '', 'band' : '', 'pot8' : '', 'ldau' : '', 'forces' : ''}
        if 'inp.xml' in self.files:
            fleur_modes['jspins'] = self.inp_dict['calculationSetup']['magnetism']['jspins'] #['fleurInput']
            fleur_modes['dos'] = self.inp_dict['output']['dos']#'fleurInput']
            fleur_modes['band'] = self.inp_dict['output']['band']
            fleur_modes['pot8'] = self.inp_dict['calculationSetup']['expertModes']['pot8']
            fleur_modes['forces'] = self.inp_dict['calculationSetup']['geometryOptimization']['l_f']
            ldau = False # TODO test if ldau in inp_dict....
            fleur_modes['ldau'] = False
        return fleur_modes

    #@staticmethod
    def get_structuredata_nwf(fleurinp):
        """
        This routine return an AiiDA Structure Data type produced from the inp.xml
        file. not a workfunction

        :return: StructureData node
        """
        from aiida.orm.data.structure import StructureData
        from aiida_fleur.tools.StructureData_util import rel_to_abs, rel_to_abs_f

        #Disclaimer: this routine needs some xpath expressions. these are hardcoded here,
        #therefore maintainance might be needed, if you want to circumvent this, you have
        #to get all the paths from somewhere.

        #######
        # all hardcoded xpaths used and attributes names:
        bravaismatrix_bulk_xpath = '/fleurInput/cell/bulkLattice/bravaisMatrix/'
        bravaismatrix_film_xpath = 'fleurInput/cell/filmLattice/bravaisMatrix/'
        species_xpath = '/fleurInput/atomSpecies/species'
        all_atom_groups_xpath = '/fleurInput/atomGroups/atomGroup'

        species_attrib_name = 'name'
        species_attrib_element = 'element'

        row1_tag_name = 'row-1'
        row2_tag_name = 'row-2'
        row3_tag_name = 'row-3'

        atom_group_attrib_species = 'species'
        atom_group_tag_abspos = 'absPos'
        atom_group_tag_relpos = 'relPos'
        atom_group_tag_filmpos = 'filmPos'
        ########

        if not ('inp.xml' in fleurinp.files):
            print 'cannot get a StructureData because fleurinpdata has no inp.xml file yet'
            # TODO what to do in this case?
            return False

        # read in inpxml
        inpxmlfile = fleurinp.get_file_abs_path('inp.xml')#'./inp.xml'

        if fleurinp._schema_file_path: # Schema there, parse with schema
            xmlschema_doc = etree.parse(fleurinp._schema_file_path)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
            tree = etree.parse(inpxmlfile)#, parser) # parser somewhat broken TODO, lxml version?
        else: #schema not there, parse without
            print 'parsing inp.xml without XMLSchema'
            tree = etree.parse(inpxmlfile)

        root = tree.getroot()

        # Fleur uses atomic units, convert to Angstrom
        # get cell matrix from inp.xml
        row1 = root.xpath(bravaismatrix_bulk_xpath + row1_tag_name)#[0].text.split()

        if row1: #bulk calculation
            #print 'bulk'
            row1 = row1[0].text.split()
            row2 = root.xpath(bravaismatrix_bulk_xpath + row2_tag_name)[0].text.split()
            row3 = root.xpath(bravaismatrix_bulk_xpath + row3_tag_name)[0].text.split()
            # TODO? allow math?
            for i, cor in enumerate(row1):
                row1[i] = float(cor)*bohr_a
            for i, cor in enumerate(row2):
                row2[i] = float(cor)*bohr_a
            for i, cor in enumerate(row3):
                row3[i] = float(cor)*bohr_a

            cell = [row1, row2, row3]
            # create new structure Node
            struc = StructureData(cell=cell)
            struc.pbc = [True, True, True]

        elif root.xpath(bravaismatrix_film_xpath + row1_tag_name): #film calculation
            #print 'film'
            row1 = root.xpath(bravaismatrix_film_xpath + row1_tag_name)[0].text.split()
            row2 = root.xpath(bravaismatrix_film_xpath + row2_tag_name)[0].text.split()
            for i, cor in enumerate(row1):
                row1[i] = float(cor)*bohr_a
            for i, cor in enumerate(row2):
                row2[i] = float(cor)*bohr_a
            row3 = [0, 0, 0]#? TODO:what has it to be in this case?
            cell = [row1, row2, row3]
            # create new structure Node
            struc = StructureData(cell=cell)
            struc.pbc = [True, True, False]


        #get species for atom kinds
        #species = root.xpath(species_xpath)
        species_name = root.xpath(species_xpath + '/@' + species_attrib_name)
        species_element = root.xpath(species_xpath + '/@' + species_attrib_element)
        # alternativ: loop over species and species.get(species_attrib_name)

        #save species info in a dict
        species_dict = {}
        for i, spec in enumerate(species_name):
            species_dict[spec] = {species_attrib_element: species_element[i]}

        # Now we have to get all atomgroups, look what their species is and
        # their positions are.
        # Then we append them to the new structureData

        all_atom_groups = root.xpath(all_atom_groups_xpath)

        for atom_group in all_atom_groups:
            current_species = atom_group.get(atom_group_attrib_species)

            group_atom_positions_abs = atom_group.xpath(atom_group_tag_abspos)
            group_atom_positions_rel = atom_group.xpath(atom_group_tag_relpos)
            group_atom_positions_film = atom_group.xpath(atom_group_tag_filmpos)

            if group_atom_positions_abs: #we have absolut positions
                for atom in group_atom_positions_abs:
                    postion_a = atom.text.split()
                    # allow for math *, /
                    for i, pos in enumerate(postion_a):
                        if '/' in pos:
                            temppos = pos.split('/')
                            postion_a[i] = float(temppos[0])/float(temppos[1])
                        elif '*' in pos:
                            temppos = pos.split('*')
                            postion_a[i] = float(temppos[0])*float(temppos[1])
                        else:
                            postion_a[i] = float(pos)
                        postion_a[i] = postion_a[i]*bohr_a
                    # append atom to StructureData
                    struc.append_atom(
                            position=postion_a,
                            symbols=species_dict[current_species][species_attrib_element])

            elif group_atom_positions_rel: #we have relative positions
                # TODO: check if film or 1D calc, because this is not allowed! I guess
                for atom in group_atom_positions_rel:
                    postion_r = atom.text.split()
                    # allow for math * /
                    for i, pos in enumerate(postion_r):
                        if '/' in pos:
                            temppos = pos.split('/')
                            postion_r[i] = float(temppos[0])/float(temppos[1])
                        elif '*' in pos:
                            temppos = pos.split('*')
                            postion_r[i] = float(temppos[0])*float(temppos[1])
                        else:
                            postion_r[i] = float(pos)

                    # now transform to absolut Positions
                    new_abs_pos = rel_to_abs(postion_r, cell)

                    # append atom to StructureData
                    struc.append_atom(
                        position=new_abs_pos,
                        symbols=species_dict[current_species][species_attrib_element])

            elif group_atom_positions_film: # Do we support mixture always, or only in film case?
                #either support or throw error
                for atom in group_atom_positions_film:
                    # film pos are rel rel abs, therefore only transform first two coordinates
                    postion_f = atom.text.split()
                    # allow for math * /
                    for i, pos in enumerate(postion_f):
                        if '/' in pos:
                            temppos = pos.split('/')
                            postion_f[i] = float(temppos[0])/float(temppos[1])
                        elif '*' in postion_f[i]:
                            temppos = pos.split('*')
                            postion_f[i] = float(temppos[0])*float(temppos[1])
                        else:
                            postion_f[i] = float(pos)
                    # now transform to absolut Positions
                    new_abs_pos = rel_to_abs_f(postion_r, cell)
                    # append atom to StructureData
                    struc.append_atom(
                        position=new_abs_pos,
                        symbols=species_dict[current_species][species_attrib_element])
            else:
                print ('I should never get here, 1D not supported yet, '
                      'I only know relPos, absPos, filmPos')
                #TODO throw error
        # TODO DATA-DATA links are not wanted, you might want to use a wf instead
        #struc.add_link_from(fleurinp, label='fleurinp.structure', link_type=LinkType.CREATE)
        #label='fleurinp.structure'
        #return {label : struc}
        return struc

    @staticmethod
    @wf
    def get_structuredata(fleurinp):
        """
        This routine return an AiiDA Structure Data type produced from the inp.xml
        file. This is a workfunction and therefore keeps the provenance.

        :return: StructureData node
        """
        return fleurinp.get_structuredata_nwf(fleurinp)



    @staticmethod
    def get_kpointsdata_nwf(fleurinp):
        """
        This routine returns an AiiDA kpoint Data type produced from the inp.xml
        file. This only works if the kpoints are listed in the in inpxml.
        This is NOT a workfunction and does not keep the provenance!
        :return: KpointsData node
        """
        from aiida.orm.data.array.kpoints import KpointsData


        #HINT, TODO:? in this routine, the 'cell' you might get in an other way
        #exp: StructureData.cell, but for this you have to make a structureData Node,
        # which might take more time for structures with lots of atoms.
        # then just parsing the cell from the inp.xml
        #as in the routine get_structureData

        #Disclaimer: this routine needs some xpath expressions.
        #these are hardcoded here, therefore maintainance might be needed,
        # if you want to circumvent this, you have
        #to get all the paths from somewhere.

        #######
        # all hardcoded xpaths used and attributes names:
        bravaismatrix_bulk_xpath = '/fleurInput/cell/bulkLattice/bravaisMatrix/'
        bravaismatrix_film_xpath = 'fleurInput/cell/filmLattice/bravaisMatrix/'
        kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList/'

        kpoint_tag = 'kPoint'
        kpointlist_attrib_posscale = 'posScale'
        kpointlist_attrib_weightscale = 'weightScale'
        #kpointlist_attrib_count = 'count'
        kpoint_attrib_weight = 'weight'
        row1_tag_name = 'row-1'
        row2_tag_name = 'row-2'
        row3_tag_name = 'row-3'
        ########

        if not ('inp.xml' in fleurinp.files):
            print 'cannot get a KpointsData because fleurinpdata has no inp.xml file yet'
            # TODO what to do in this case?
            return False

        # else read in inpxml
        inpxmlfile = fleurinp.get_file_abs_path('inp.xml')

        if fleurinp._schema_file_path: # Schema there, parse with schema
            xmlschema_doc = etree.parse(fleurinp._schema_file_path)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
            tree = etree.parse(inpxmlfile, parser)
        else: #schema not there, parse without
            print 'parsing inp.xml without XMLSchema'
            tree = etree.parse(inpxmlfile)

        root = tree.getroot()

        # get cell matrix from inp.xml

        row1 = root.xpath(bravaismatrix_bulk_xpath + row1_tag_name)#[0].text.split()

        if row1: #bulk calculation
            #print 'bulk'
            row1 = row1[0].text.split()
            row2 = root.xpath(bravaismatrix_bulk_xpath + row2_tag_name)[0].text.split()
            row3 = root.xpath(bravaismatrix_bulk_xpath + row3_tag_name)[0].text.split()
            # TODO? allow math?
            for i, cor in enumerate(row1):
                row1[i] = float(cor)
            for i, cor in enumerate(row2):
                row2[i] = float(cor)
            for i, cor in enumerate(row3):
                row3[i] = float(cor)

            cell = [row1, row2, row3]
            #set boundary conditions
            pbc1 = [True, True, True]

        elif root.xpath(bravaismatrix_film_xpath + row1_tag_name):
            #film calculation
            #print 'film'
            row1 = root.xpath(bravaismatrix_film_xpath + row1_tag_name)[0].text.split()
            row2 = root.xpath(bravaismatrix_film_xpath + row2_tag_name)[0].text.split()
            for i, cor in enumerate(row1):
                row1[i] = float(cor)
            for i, cor in enumerate(row2):
                row2[i] = float(cor)
            row3 = [0, 0, 0]#? TODO:what has it to be in this case?
            cell = [row1, row2, row3]
            pbc1 = [True, True, False]

        # get kpoints only works if kpointlist in inp.xml
        kpoints = root.xpath(kpointlist_xpath + kpoint_tag)

        if kpoints:
            posscale = root.xpath(kpointlist_xpath + '@' + kpointlist_attrib_posscale)
            weightscale = root.xpath(kpointlist_xpath + '@' + kpointlist_attrib_weightscale)
            #count = root.xpath(kpointlist_xpath + '@' + kpointlist_attrib_count)

            kpoints_pos = []
            kpoints_weight = []

            for kpoint in kpoints:
                kpoint_pos = kpoint.text.split()
                for i, kval in enumerate(kpoint_pos):
                    kpoint_pos[i] = float(kval)/float(posscale[0])
                    kpoint_weight = float(kpoint.get(kpoint_attrib_weight))/float(weightscale[0])
                kpoints_pos.append(kpoint_pos)
                kpoints_weight.append(kpoint_weight)
            totalw = 0
            for weight in kpoints_weight:
                totalw = totalw + weight
            #print 'total w {} '.format(totalw)
            kps = KpointsData(cell=cell)
            kps.pbc = pbc1

            kps.set_kpoints(kpoints_pos, cartesian=False, weights=kpoints_weight)
            #kps.add_link_from(fleurinp, label='fleurinp.kpts', link_type=LinkType.CREATE)
            kps.label='fleurinp.kpts'
            #return {label: kps}
            return kps
        else: # TODO parser other kpoints formats, if they fit in an AiiDA node
            print 'No kpoint list in inp.xml'
            return None


    @staticmethod
    @wf
    def get_kpointsdata(fleurinp):
        """
        This routine returns an AiiDA kpoint Data type produced from the inp.xml
        file. This only works if the kpoints are listed in the in inpxml.
        This is a workfunction and does keep the provenance!
        :return: KpointsData node
        """

        return fleurinp.get_kpointsdata_nwf(fleurinp)

    '''
    @staticmethod
    def get_parameterdata_nwf(fleurinp):
        """
        This routine returns an AiiDA ParameterData type produced from the inp.xml
        file. This node can be used for inpgen.
        This is NOT a workfunction and does NOT keep the provenance!
        :return: ParameterData node
        """
        parameters = None
        return parameters


    @staticmethod
    @wf
    def get_parameterdata(fleurinp):
        """
        This routine returns an AiiDA ParameterData type produced from the inp.xml
        file. This node can be used for inpgen.
        This is a workfunction and does keep the provenance!
        :return: ParameterData node
        """

        return fleurinp.get_parameterdata_nwf(fleurinp)
    '''





    '''
    def set_nkpts(fleurinp, count, gamma='F'):#_orgi

        kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList'
        kpoint_xpath = '/fleurInput/calculationSetup/bzIntegration/kPoint*'
        #fleurinp = fleurinp_orgi.copy()
        if 'inp.xml' in fleurinp.files:
            # read in inpxml
            inpxmlfile = fleurinp.get_file_abs_path('inp.xml')

            if fleurinp._schema_file_path: # Schema there, parse with schema
                xmlschema_doc = etree.parse(fleurinp._schema_file_path)
                xmlschema = etree.XMLSchema(xmlschema_doc)
                parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
                tree = etree.parse(inpxmlfile, parser)
            else: #schema not there, parse without
                print 'parsing inp.xml without XMLSchema'
                tree = etree.parse(inpxmlfile)

            root = tree.getroot()
        else:
            raise InputValidationError(
                      "No inp.xml file yet specified, to add kpoints to.")

        new_kpo = etree.Element('kPointCount', count="{}".format(count), gamma="{}".format(gamma))
        print new_kpo
        new_tree = replace_tag(tree, kpointlist_xpath, new_kpo)
        inpxmlfile = os.path.join(
                         fleurinp._get_folder_pathsubfolder.abspath, 'temp_inp.xml')

        new_tree.write(inpxmlfile)
        print 'wrote tree to' + str(inpxmlfile)
        fleurinp.del_file('inp.xml')
        fleurinp._add_path(str(inpxmlfile), 'inp.xml')
        os.remove(inpxmlfile)

        return fleurinp
    '''

    @wf
    def set_kpointsdata(fleurinp_orgi, KpointsDataNode):
        """
        This function writes the all the kpoints from a KpointsDataNode in the
        inp.xml file as a kpointslist. It replaces the Kpoints written in the
        inp.xml file.

        # currently it is the users resposibility to provide a full
        KpointsDataNode with weights. In the future FLEUR might recalculate them.
        :params: KpointsData node
        """
        from aiida.orm.data.array.kpoints import KpointsData
        #from aiida.common.exceptions import InputValidationError

        #TODO: This is probably broken and should be moved to fleurinpmodifier

        # all hardcoded xpaths used and attributes names:
        fleurinp = fleurinp_orgi.copy()
        kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList'
        #kpoint_tag = 'kPoint'
        #kpointlist_attrib_posscale = 'posScale'
        #kpointlist_attrib_weightscale = 'weightScale'
        #kpointlist_attrib_count = 'count'
        #kpoint_attrib_weight = 'weight'

        #### method layout: #####
        # Check if Kpoints node
        # get kpoints, weights, inp.xml

        # replace the kpoints tag.(delete old write new)
        # kpoint list posScale, wightScale, count
        # <kPointList posScale="36.00000000" weightScale="324.00000000" count="324">
        #    <kPoint weight="    1.000000">   17.000000     0.000000     0.000000</kPoint>

        # add new inp.xml to fleurinpdata

        if not isinstance(KpointsDataNode, KpointsData):
            raise InputValidationError(
                      "The node given is not a valid KpointsData node.")

        if 'inp.xml' in fleurinp.files:
            # read in inpxml
            inpxmlfile = fleurinp.get_file_abs_path('inp.xml')

            if fleurinp._schema_file_path: # Schema there, parse with schema
                xmlschema_doc = etree.parse(fleurinp._schema_file_path)
                xmlschema = etree.XMLSchema(xmlschema_doc)
                parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
                tree = etree.parse(inpxmlfile, parser)
            else: #schema not there, parse without
                print 'parsing inp.xml without XMLSchema'
                tree = etree.parse(inpxmlfile)

            #root = tree.getroot()
        else:
            raise InputValidationError(
                      "No inp.xml file yet specified, to add kpoints to.")

        #cell_k = KpointsDataNode.cell

        # TODO: shall we check if cell is the same as cell from structure?
        # or is that to narrow?

        kpoint_list = KpointsDataNode.get_kpoints(also_weights=True, cartesian=False)
        nkpts = len(kpoint_list[0])
        totalw = 0
        for weight in kpoint_list[1]:
            totalw = totalw + weight
        #weightscale = totalw
        #for j, kpos in enumerate(kpoint_list[0]):
        #    print '<kPoint weight="{}">{}</kPoint>'.format(kpoint_list[1][j], str(kpos).strip('[]'))


        new_kpo = etree.Element('kPointList',  posScale="1.000", weightScale="1.0", count="{}".format(nkpts))
        for i, kpos in enumerate(kpoint_list[0]):
            new_k = etree.Element('kPoint', weight="{}".format(kpoint_list[1][i]))
            new_k.text = "{} {} {}".format(kpos[0], kpos[1], kpos[2])
            new_kpo.append(new_k)

        new_tree = replace_tag(tree, kpointlist_xpath, new_kpo)
        #use _write_new_fleur_xmlinp_file(fleurinp, inp_file_xmltree, fleur_change_dic):

        #TODO this should be sourced out to other methods.
        # somehow directly writing inp.xml does not work, create new one
        inpxmlfile = os.path.join(
                         fleurinp._get_folder_pathsubfolder.abspath, 'temp_inp.xml')

        # write new inp.xml, schema evaluation will be done when the file gets added
        new_tree.write(inpxmlfile)
        print 'wrote tree to' + str(inpxmlfile)

        # delete old inp.xml file, not needed anymore
        #TODO maybe do some checks before
        fleurinp.del_file('inp.xml')

        # now the new inp.xml file is added and with that the inpxml_dict will
        # be overwritten, and the file validated
        fleurinp._add_path(str(inpxmlfile), 'inp.xml')

        # remove temporary inp.xml file
        os.remove(inpxmlfile)

        return fleurinp

    def get_tag(self, xpath):
        """
        Tries to evalutate an xpath expression. If it fails it logs it.

        :param root node of an etree and an xpath expression (relative, or absolute)
        :returns ALWAYS a node list
        """
        from lxml import etree

        if 'inp.xml' in self.files:
            # read in inpxml
            inpxmlfile = self.get_file_abs_path('inp.xml')

            if self._schema_file_path: # Schema there, parse with schema
                #xmlschema_doc = etree.parse(self._schema_file_path)
                #xmlschema = etree.XMLSchema(xmlschema_doc)
                #parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
                tree = etree.parse(inpxmlfile)#, parser)
            else: #schema not there, parse without
                print 'parsing inp.xml without XMLSchema'
                tree = etree.parse(inpxmlfile)

            root = tree.getroot()
        else:
            raise InputValidationError(
                      "No inp.xml file yet specified, to get a tag from")

        try:
            return_value = root.xpath(xpath)
        except etree.XPathEvalError:
            #print (
            raise InputValidationError(
                'There was a XpathEvalError on the xpath: {} \n Either it does '
                'not exist, or something is wrong with the expression.'
                ''.format(xpath))
            return []
        if len(return_value) == 1:
            return return_value
        else:
            return return_value

'''
from aiida.orm.data.base import Str

#@wf
def extract_parameterdata(fleurinp, element=Str('all'))
    """
    Method to extract a ParameterData node from a fleurinp data object.
    This parameter node can be used as an input node for inpgen.

    :param: fleurinp: an FleurinpData node
    :param: element: string ('all', 'W', 'W O') default all, or specify the
    species you want to extract

    :return: ParameterData node
    """
    pass
    print("sorry not implemented yet")
    if element=='all':
        pass
    else:
        species = element.split()

    #open inpxml tree
    #use xpath expressions to extract parameters for all species or certain species

    #store species paremeters in the right form in a parameter data node.
'''
'''
# TODO write xml util and put all these functions there, parse as option a logger,
# that parser can use these methods too.

def delete_tag(tagname, xpath):
    pass
    # check existance,
    #delete Tag and all tags

def replace_tag(xmltree, xpath, newelement):
    root = xmltree.getroot()

    nodes = root.xpath(xpath)
    #print nodes
    if nodes:
        for node in nodes:
            #print newelement
            parent = node.getparent()
            parent.remove(node)
            parent.append(newelement)

    return xmltree


def eval_xpath2(node, xpath):
    """
    Tries to evalutate an xpath expression. If it fails it logs it.

    :param root node of an etree and an xpath expression (relative, or absolute)
    :returns ALWAYS a node list
    """
    try:
        return_value = node.xpath(xpath)
    except etree.XPathEvalError:
        print(
            'There was a XpathEvalError on the xpath: {} \n Either it does '
            'not exist, or something is wrong with the expression.'
            ''.format(xpath))
        return []
    if len(return_value) == 1:
        return return_value
    else:
        return return_value

def get_xml_attribute(node, attributename, parser_info_out={}):
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
            if parser_info_out:
                parser_info_out['parser_warnings'].append(
                    'Tried to get attribute: "{}" from element {}.\n '
                    'I recieved "{}", maybe the attribute does not exist'
                    ''.format(attributename, node, attrib_value))
            else:
                print(
                    'Can not get attributename: "{}" from node "{}", '
                    'because node is not an element of etree.'
                    ''.format(attributename, node))
            return None
    else: # something doesn't work here, some nodes get through here
        if parser_info_out:
            parser_info_out['parser_warnings'].append(
                'Can not get attributename: "{}" from node "{}", '
                'because node is not an element of etree.'
                ''.format(attributename, node))
        else:
            print(
                'Can not get attributename: "{}" from node "{}", '
                'because node is not an element of etree.'
                ''.format(attributename, node))
        return None
'''
