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
In this module is the :class:`~aiida_fleur.data.fleurinp.FleurinpData` class, and methods for FLEUR
input manipulation plus methods for extration of AiiDA data structures.
"""
# TODO: maybe add a modify method which returns a fleurinpmodifier class
# TODO: inpxml to dict: maybe kpts should not be written to the dict? same with symmetry
# TODO: test for large input files, I believe the recursion is still quite slow..
# TODO: 2D cell get kpoints and get structure also be carefull with tria = T!!!
# TODO : maybe save when get_structure or get_kpoints was executed on fleurinp,
# because otherwise return this node instead of creating a new one!
# TODO: get rid of duplicate code for parsing the inp.xml to an etree

from __future__ import absolute_import
from __future__ import print_function
import os
import io
import re
import six
from lxml import etree

from aiida.orm import Data, Node, load_node
from aiida.common.exceptions import InputValidationError, ValidationError
from aiida.engine.processes.functions import calcfunction as cf

from aiida_fleur.tools.xml_util import replace_tag
from aiida_fleur.fleur_schema.schemafile_index import get_internal_search_paths, get_schema_paths
from aiida_fleur.common.constants import BOHR_A


class FleurinpData(Data):
    """
    AiiDA data object representing everything a FLEUR calculation needs.

    It is initialized with an absolute path to an ``inp.xml`` file or a
    FolderData node containing ``inp.xml``.
    Other files can also be added that will be copied to the remote machine, where the
    calculation takes place.

    It stores the files in the repository and stores the input parameters of the
    ``inp.xml`` file of FLEUR in the database as a python dictionary (as internal attributes).
    When an ``inp.xml`` (name important!) file is added to files, FleurinpData searches
    for a corresponding xml schema file in the PYTHONPATH environment variable.
    Therefore, it is recommend to have the plug-in source code directory in the python environment.
    If no corresponding schema file is found an error is raised.

    FleurinpData also provides the user with
    methods to extract AiiDA StructureData and
    KpointsData nodes.

    Remember that most attributes of AiiDA nodes can not be changed after they
    have been stored in the database! Therefore, you have to use the FleurinpModifier class and its
    methods if you want to change somthing in the ``inp.xml`` file. You will retrieve a new
    FleurinpData that way and start a new calculation from it.
    """

    # search in current folder and search in aiida source code
    # we want to search in the Aiida source directory, get it from python path,
    # maybe better from somewhere else.
    # TODO: don not walk the whole python path, test if dir below is aiida?
    # needs to be improved, schema file is often after new installation not found...
    # installation with pip should always lead to a schema file in the python path, or even specific place

    def __init__(self, **kwargs):
        """
        Initialize a FleurinpData object set the files given
        """
        files = kwargs.pop('files', None)
        for filename in files:
            if 'inp.xml' in filename:
                files.pop(files.index(filename))
                files.append(filename)
                break
        node = kwargs.pop('node', None)
        super().__init__(**kwargs)

        search_paths = []
        ifolders = get_internal_search_paths()
        ischemas = get_schema_paths()
        for path in ischemas:
            search_paths.append(path)
        for path in ifolders:
            search_paths.append(path)
        search_paths.append('./')

        # Now add also python path maybe will be decaptivated
        # if pythonpath is non existent catch error
        try:
            pythonpath = os.environ['PYTHONPATH'].split(':')
        except KeyError:
            pythonpath = []

        for path in pythonpath[:]:
            search_paths.append(path)

        self.set_attribute('_has_schema', False)
        self.set_attribute('_schema_file_path', None)
        self.set_attribute('_search_paths', search_paths)
        if files:
            if node:
                self.set_files(files, node=node)
            else:
                self.set_files(files)

    # ignore machine dependent attributes in hash
    _hash_ignored_attributes = ['_schema_file_path', '_search_paths']

    @property
    def _has_schema(self):
        """
        Boolean property, which stores if a schema file is already known
        """
        return self.get_attribute('_has_schema')

    @property
    def _schema_file_path(self):
        """
        A string, which stores the absolute path to the schemafile found
        """
        return self.get_attribute('_schema_file_path')

    @property
    def _search_paths(self):
        """
        A string, which stores the paths to search for  schemafiles
        """
        return self.get_attribute('_search_paths')

    @_has_schema.setter
    def _has_schema(self, boolean):
        """
        Setter for has_schema
        """
        self.set_attribute('_has_schema', boolean)

    @_schema_file_path.setter
    def _schema_file_path(self, schemapath):
        """
        Setter for the schema file path
        """
        self.set_attribute('_schema_file_path', schemapath)

    # files
    @property
    def files(self):
        """
        Returns the list of the names of the files stored
        """
        return self.get_attribute('files', [])

    @files.setter
    def files(self, filelist, node=None):
        """
        Add a list of files to FleurinpData.
        Alternative use setter method.

        :param files: list of filepaths or filenames of node is specified
        :param node: a Folder node containing files from the filelist
        """
        for file1 in filelist:
            self.set_file(file1, node=node)

    def set_files(self, files, node=None):
        """
        Add the list of files to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.
        Can by used as an alternative to the setter.

        :param files: list of abolute filepaths or filenames of node is specified
        :param node: a :class:`~aiida.orm.FolderData` node containing files from the filelist
        """
        for file1 in files:
            self.set_file(file1, node=node)

    def set_file(self, filename, dst_filename=None, node=None):
        """
        Add a file to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.

        :param filename: absolute path to the file or a filename of node is specified
        :param node: a :class:`~aiida.orm.FolderData` node containing the file
        """
        self._add_path(filename, dst_filename=dst_filename, node=node)

    def open(self, path='inp.xml', mode='r', key=None):
        """
        Returns an open file handle to the content of this data node.

        :param key: name of the file to be opened
        :param mode: the mode with which to open the file handle
        :returns: A file handle in read mode
         """

        if key is not None:
            path = key

        return self._repository.open(path, mode=mode)

    def get_content(self, filename='inp.xml'):
        """
        Returns the content of the single file stored for this data node.

        :returns: A string of the file content
        """
        with self.open(path=filename, mode='r') as handle:
            return handle.read()

    def del_file(self, filename):
        """
        Remove a file from FleurinpData instancefind

        :param filename: name of the file to be removed from FleurinpData instance
        """
        # remove from files attr list
        if filename in self.get_attribute('files'):
            try:
                self.get_attribute('files').remove(filename)
                # self._del_attribute(‘filename')
            except AttributeError:
                # There was no file set
                pass
        # remove from sandbox folder
        if filename in self.list_object_names():  # get_folder_list():
            self.delete_object(filename)

    def find_schema(self, inp_version_number):
        """
        Method which searches for a schema files (.xsd) which correspond
        to the input xml file. (compares the version numbers)

        :param inp_version_number: a version of ``inp.xml`` file schema to be found

        :return: A two-element tuple:

                     1. A list of paths where schema files are located
                     2. A boolen which shows if the required version schema file was found

        """
        # user changed version number, or no file yet known.
        # TODO test if this still does the right thing if user adds one
        # inp.xml and then an inp.xml with different version.
        # or after copying and read
        schemafile_paths = []

        for path in self._search_paths:  # paths:
            for root, dirs, files in os.walk(path):
                for file1 in files:
                    if file1.endswith('.xsd'):
                        if ('Fleur' in file1) or ('fleur' in file1):
                            schemafile_path = os.path.join(root, file1)
                            schemafile_paths.append(schemafile_path)
                            i = 0
                            imin = 0
                            imax = 0
                            schemafile = open(schemafile_path, 'r')
                            for line in schemafile.readlines():
                                i = i + 1
                                # This kind of hardcoded
                                if re.search('name="FleurVersionType"', line):
                                    imax = i + 10  # maybe make larger or different
                                    imin = i
                                    schema_version_numbers = []
                                if imin < i <= imax:
                                    if re.search('enumeration value', line):
                                        schema_version_number = re.findall(r'\d+.\d+', line)[0]
                                    elif re.search('simpleType>', line):
                                        break
                            schema_version_numbers.append(schema_version_number)
                            schemafile.close()
                            # test if schemafiles works with multiple fleur versions
                            for version_number in schema_version_numbers:
                                if version_number == inp_version_number:
                                    # we found the right schemafile for the current inp.xml
                                    self.set_attribute('_schema_file_path', schemafile_path)
                                    self.set_attribute('_has_schema', True)
                                    return schemafile_paths, True

        return schemafile_paths, False

    def _add_path(self, file1, dst_filename=None, node=None):
        """
        Add a single file to the FleurinpData folder.
        The destination name can be different. ``inp.xml`` is a special case.
        file names are stored in the db, the whole file in the reporsitory.

        :param file1: the file to be added, either string, absolute path, or filelike object whose contents to copy
            Hint: Pass io.BytesIO(b"my string") to construct the file directly from a string.
        :param dst_filename: string, new filename for given file in repo and db
        :param node: aiida.orm.Node, usually FolderData if node is given get the 'file1' from the node

        :raise: ValueError, InputValidationError
        :return: None
        """
        # TODO? Maybe only certain files should be allowed to be added
        # contra: has to be maintained, also these files can be inputed from byte strings...
        #_list_of_allowed_files = ['inp.xml', 'enpara', 'cdn1', 'sym.out', 'kpts']

        if node:
            if not isinstance(node, Node):
                node = load_node(node)  # if this fails it will raise
            if file1 not in node.list_object_names():
                # throw error, you try to add something that is not there
                raise ValueError('file1 has to be in the specified node')

            is_filelike = True
            if dst_filename is None:
                final_filename = file1
            else:
                final_filename = dst_filename
            # Override file1 with bytestring of file
            # since we have to use 'with', and node has no method to copy files
            # we read the whole file and write it again later
            # this is not so nice, but we assume that input files are rather small...
            with node.open(file1, mode='rb') as file2:
                file1 = io.BytesIO(file2.read())

        elif isinstance(file1, six.string_types):
            is_filelike = False

            if not os.path.isabs(file1):
                file1 = os.path.abspath(file1)
                #raise ValueError("Pass an absolute path for file1: {}".format(file1))

            if not os.path.isfile(file1):
                raise ValueError('file1 must exist and must be a single file: {}'.format(file1))

            if dst_filename is None:
                final_filename = os.path.split(file1)[1]
            else:
                final_filename = dst_filename
        else:
            is_filelike = True
            if dst_filename is None:
                try:
                    final_filename = os.path.basename(file1.name)  # Not sure if this still works for aiida>2.0
                except AttributeError:
                    final_filename = 'inp.xml'  # fall back to default
            else:
                final_filename = dst_filename

        key = final_filename

        old_file_list = self.list_object_names()
        old_files_list = self.get_attribute('files', [])

        # remove file from folder first if it exists
        if final_filename not in old_file_list:
            old_files_list.append(final_filename)
        else:
            try:
                old_file_list.remove(final_filename)
            except ValueError:
                pass

        if is_filelike:
            self.put_object_from_filelike(file1, key, mode='wb')
        else:
            self.put_object_from_file(file1, key)

        self.set_attribute('files', old_files_list)  # We want to keep the other files

        ### Special case: 'inp.xml' ###
        # here this is hardcoded, might want to change? get filename from elsewhere

        if final_filename == 'inp.xml':
            # get input file version number
            inp_version_number = None
            lines = self.get_content(filename=final_filename).split('\n')
            for line in lines:
                if re.search('fleurInputVersion', str(line)):
                    inp_version_number = re.findall(r'\d+.\d+', str(line))[0]
                    break
            if inp_version_number is None:
                raise InputValidationError('No fleurInputVersion number found '
                                           'in given input file: {}. {}'
                                           'Please check if this is a valid fleur input file. '
                                           'It can not be validated and I can not use it. '
                                           ''.format(file1, lines))
            # search for Schema file with same version number
            schemafile_paths, found = self.find_schema(inp_version_number)

            if (not self._has_schema) and (self._schema_file_path is None):
                err_msg = ('No XML schema file (.xsd) with matching version number {} '
                           'to the inp.xml file was found. I have looked here: {} '
                           'and have found only these schema files for Fleur: {}. '
                           'I need this file to validate your input and to know the structure '
                           'of the current inp.xml file, sorry.'.format(inp_version_number, self._search_paths,
                                                                        schemafile_paths))
                raise InputValidationError(err_msg)
            if self._schema_file_path is None:
                schemafile_paths, found = self.find_schema(inp_version_number)
                if not found:
                    err_msg = ('No XML schema file (.xsd) with matching version number {} '
                               'to the inp.xml file was found. I have looked here: {} '
                               'and have found only these schema files for Fleur: {}. '
                               'I need this file to validate your input and to know the structure '
                               'of the current inp.xml file, sorry.'.format(inp_version_number, self._search_paths,
                                                                            schemafile_paths))
                raise InputValidationError(err_msg)

            # finally set inp dict of Fleurinpdata
            self._set_inp_dict()

    def _set_inp_dict(self):
        """
        Sets the inputxml_dict from the ``inp.xml`` file attached to FleurinpData

        1. get ``inp.xml`` structure/layout
        2. load ``inp.xml`` file
        3. call inpxml_to_dict
        4. set inputxml_dict
        """
        from aiida_fleur.tools.xml_util import get_inpxml_file_structure, inpxml_todict, clear_xml
        import tempfile
        # get inpxml structure
        inpxmlstructure = get_inpxml_file_structure()

        # read xmlinp file into an etree with autocomplition from schema
        # we do not validate here because we want this to always succeed

        xmlschema_doc = etree.parse(self._schema_file_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        parser = etree.XMLParser(attribute_defaults=True, encoding='utf-8')
        # dtd_validation=True
        with self.open(path='inp.xml', mode='r') as inpxmlfile:
            try:
                tree_x = etree.parse(inpxmlfile, parser)
            except etree.XMLSyntaxError as exc:
                # prob inp.xml file broken
                err_msg = ('The inp.xml file is probably broken, could not parse it to an xml etree.')
                raise InputValidationError(err_msg) from exc
        # relax.xml should be available to be used in xinclude
        # hence copy relax.xml from the retrieved node into the temp file
        fo = tempfile.NamedTemporaryFile(mode='w', delete=False)
        try:
            with self.open(path='relax.xml', mode='r') as relax_file:
                relax_content = relax_file.read()
        except FileNotFoundError:
            relax_content = ''
        fo.write(relax_content)
        tempfile_name = fo.name
        fo.close()

        # replace relax.xml by the temp file path
        tree_x_string = etree.tostring(tree_x)
        tree_x_string = tree_x_string.replace(bytes('relax.xml', 'utf-8'), bytes(tempfile_name, 'utf-8'))
        tree_x = etree.fromstring(tree_x_string).getroottree()

        # replace XInclude parts to validate against schema
        tree_x = clear_xml(tree_x)
        os.remove(tempfile_name)

        # check if it validates against the schema
        if not xmlschema.validate(tree_x):
            # get a more information on what does not validate
            message = ''
            parser_on_fly = etree.XMLParser(attribute_defaults=True, schema=xmlschema, encoding='utf-8')
            inpxmlfile = etree.tostring(tree_x)
            try:
                tree_x = etree.fromstring(inpxmlfile, parser_on_fly)
            except etree.XMLSyntaxError as msg:
                message = msg
                raise InputValidationError(
                    'Input file does not validate against the schema: {}'.format(message)) from msg

            raise InputValidationError('Input file is not validated against the schema.' 'Reason is unknown')

        # convert etree into python dictionary
        root = tree_x.getroot()
        inpxml_dict = inpxml_todict(root, inpxmlstructure)
        # set inpxml_dict attribute
        self.set_attribute('inp_dict', inpxml_dict)

    # dict with inp paramters parsed from inp.xml
    @property
    def inp_dict(self):
        """
        Returns the inp_dict (the representation of the ``inp.xml`` file) as it will
        or is stored in the database.
        """
        return self.get_attribute('inp_dict', {})

    # TODO better validation? other files, if has a schema

    def _validate(self):
        """
        A validation method. Checks if an ``inp.xml`` file is in the FleurinpData.
        """
        #from aiida.common.exceptions import ValidationError

        super()._validate()

        if 'inp.xml' in self.files:
            # has_inpxml = True # does nothing so far
            pass
        else:
            raise ValidationError('inp.xml file not in attribute "files". '
                                  'FleurinpData needs to have and inp.xml file!')

    def get_fleur_modes(self):
        '''
        Analyses ``inp.xml`` file to set up a calculation mode. 'Modes' are paths a FLEUR
        calculation can take, resulting in different output files.
        This files can be automatically addded to the retrieve_list of the calculation.

        Common modes are: scf, jspin2, dos, band, pot8, lda+U, eels, ...

        :return: a dictionary containing all possible modes. A mode is activated assigning a
                 non-empty string to the corresponding key.
        '''
        # TODO these should be retrieved by looking at the inpfile structure and
        # then setting the paths.
        # use methods from fleur parser...
        # For now they are hardcoded.
        #    'dos': '/fleurInput/output',
        #    'band': '/fleurInput/output',
        #    'jspins': '/fleurInput/calculationSetup/magnetism',
        fleur_modes = {'jspins': '', 'dos': '', 'band': '', 'ldau': '', 'forces': '', 'force_theorem': '', 'gw': ''}
        if 'inp.xml' in self.files:
            fleur_modes['jspins'] = self.inp_dict['calculationSetup']['magnetism']['jspins']
            fleur_modes['dos'] = self.inp_dict['output']['dos']  # 'fleurInput']
            fleur_modes['band'] = self.inp_dict['output']['band']
            fleur_modes['forces'] = self.inp_dict['calculationSetup']['geometryOptimization']['l_f']
            fleur_modes['force_theorem'] = 'forceTheorem' in self.inp_dict
            try:
                fleur_modes['gw'] = int(self.inp_dict['calculationSetup']['expertModes']['gw']) != 0
            except KeyError:
                fleur_modes['gw'] = False
            fleur_modes['ldau'] = False
            for species in self.inp_dict['atomSpecies']['species']:
                if 'ldaU' in species:
                    fleur_modes['ldau'] = True
        return fleur_modes

    def get_structuredata_ncf(self):
        """
        This routine returns an AiiDA Structure Data type produced from the ``inp.xml``
        file. not a calcfunction

        :param self: a FleurinpData instance to be parsed into a StructureData
        :returns: StructureData node, or None
        """
        from aiida.orm import StructureData
        from aiida_fleur.tools.StructureData_util import rel_to_abs, rel_to_abs_f

        # StructureData = DataFactory(‘structure’)
        # Disclaimer: this routine needs some xpath expressions. these are hardcoded here,
        # therefore maintainance might be needed, if you want to circumvent this, you have
        # to get all the paths from somewhere.

        #######
        # all hardcoded xpaths used and attributes names:
        bravaismatrix_bulk_xpath = '/fleurInput/cell/bulkLattice/bravaisMatrix/'
        bravaismatrix_film_xpath = '/fleurInput/cell/filmLattice/bravaisMatrix/'
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

        if 'inp.xml' not in self.files:
            print('cannot get a StructureData because fleurinpdata has no inp.xml file yet')
            # TODO what to do in this case?
            return None

        # read in inpxml

        if self._schema_file_path:  # Schema there, parse with schema
            xmlschema_doc = etree.parse(self._schema_file_path)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            parser = etree.XMLParser(attribute_defaults=True, encoding='utf-8')
            with self.open(path='inp.xml', mode='r') as inpxmlfile:
                tree = etree.parse(inpxmlfile, parser)
            tree.xinclude()
            # remove comments from inp.xml
            comments = tree.xpath('//comment()')
            for c in comments:
                p = c.getparent()
                p.remove(c)
            if not xmlschema.validate(tree):
                raise ValueError('Input file is not validated against the schema.')
        else:  # schema not there, parse without
            print('parsing inp.xml without XMLSchema')
            with self.open(path='inp.xml', mode='r') as inpxmlfile:
                tree = etree.parse(inpxmlfile)
            tree.xinclude()
            # remove comments from inp.xml
            comments = tree.xpath('//comment()')
            for c in comments:
                p = c.getparent()
                p.remove(c)
        root = tree.getroot()

        # Fleur uses atomic units, convert to Angstrom
        # get cell matrix from inp.xml
        row1 = root.xpath(bravaismatrix_bulk_xpath + row1_tag_name)  # [0].text.split()
        cell = None

        if row1:  # bulk calculation
            row1 = row1[0].text.split()
            row2 = root.xpath(bravaismatrix_bulk_xpath + row2_tag_name)[0].text.split()
            row3 = root.xpath(bravaismatrix_bulk_xpath + row3_tag_name)[0].text.split()
            # TODO? allow math?
            for i, cor in enumerate(row1):
                row1[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row2):
                row2[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row3):
                row3[i] = float(cor) * BOHR_A

            cell = [row1, row2, row3]
            # create new structure Node
            struc = StructureData(cell=cell)
            struc.pbc = [True, True, True]

        elif root.xpath(bravaismatrix_film_xpath + row1_tag_name):
            # film calculation
            row1 = root.xpath(bravaismatrix_film_xpath + row1_tag_name)[0].text.split()
            row2 = root.xpath(bravaismatrix_film_xpath + row2_tag_name)[0].text.split()
            row3 = root.xpath(bravaismatrix_film_xpath + row3_tag_name)[0].text.split()
            for i, cor in enumerate(row1):
                row1[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row2):
                row2[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row3):
                row3[i] = float(cor) * BOHR_A
            # row3 = [0, 0, 0]#? TODO:what has it to be in this case?
            cell = [row1, row2, row3]
            struc = StructureData(cell=cell)
            struc.pbc = [True, True, False]

        if cell is None:
            print('Could not extract Bravias matrix out of inp.xml. Is the '
                  'Bravias matrix explicitly given? i.e Latnam definition '
                  'not supported.')
            return None

        # get species for atom kinds
        #species = root.xpath(species_xpath)
        species_name = root.xpath(species_xpath + '/@' + species_attrib_name)
        species_element = root.xpath(species_xpath + '/@' + species_attrib_element)
        # alternativ: loop over species and species.get(species_attrib_name)

        # save species info in a dict
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

            if group_atom_positions_abs:  # we have absolute positions
                for atom in group_atom_positions_abs:
                    postion_a = atom.text.split()
                    # allow for math *, /
                    for i, pos in enumerate(postion_a):
                        if '/' in pos:
                            temppos = pos.split('/')
                            postion_a[i] = float(temppos[0]) / float(temppos[1])
                        elif '*' in pos:
                            temppos = pos.split('*')
                            postion_a[i] = float(temppos[0]) * float(temppos[1])
                        else:
                            postion_a[i] = float(pos)
                        postion_a[i] = postion_a[i] * BOHR_A
                    # append atom to StructureData
                    struc.append_atom(position=postion_a, symbols=species_dict[current_species][species_attrib_element])

            elif group_atom_positions_rel:  # we have relative positions
                # TODO: check if film or 1D calc, because this is not allowed! I guess
                for atom in group_atom_positions_rel:
                    postion_r = atom.text.split()
                    # allow for math * /
                    for i, pos in enumerate(postion_r):
                        if '/' in pos:
                            temppos = pos.split('/')
                            postion_r[i] = float(temppos[0]) / float(temppos[1])
                        elif '*' in pos:
                            temppos = pos.split('*')
                            postion_r[i] = float(temppos[0]) * float(temppos[1])
                        else:
                            postion_r[i] = float(pos)

                    # now transform to absolute Positions
                    new_abs_pos = rel_to_abs(postion_r, cell)

                    # append atom to StructureData
                    struc.append_atom(position=new_abs_pos,
                                      symbols=species_dict[current_species][species_attrib_element])

            elif group_atom_positions_film:  # Do we support mixture always, or only in film case?
                # either support or throw error
                for atom in group_atom_positions_film:
                    # film pos are rel rel abs, therefore only transform first two coordinates
                    postion_f = atom.text.split()
                    # allow for math * /
                    for i, pos in enumerate(postion_f):
                        if '/' in pos:
                            temppos = pos.split('/')
                            postion_f[i] = float(temppos[0]) / float(temppos[1])
                        elif '*' in postion_f[i]:
                            temppos = pos.split('*')
                            postion_f[i] = float(temppos[0]) * float(temppos[1])
                        else:
                            postion_f[i] = float(pos)
                    # now transform to absolute Positions
                    postion_f[2] = postion_f[2] * BOHR_A
                    new_abs_pos = rel_to_abs_f(postion_f, cell)
                    # append atom to StructureData
                    struc.append_atom(position=new_abs_pos,
                                      symbols=species_dict[current_species][species_attrib_element])
            else:
                # TODO throw error
                print('I should never get here, 1D not supported yet, ' 'I only know relPos, absPos, filmPos')
                # TODO throw error
        # TODO DATA-DATA links are not wanted, you might want to use a cf instead
        #struc.add_link_from(self, label='self.structure', link_type=LinkType.CREATE)
        # label='self.structure'
        # return {label : struc}
        return struc

    @cf
    def get_structuredata(self):
        """
        This routine return an AiiDA Structure Data type produced from the ``inp.xml``
        file. If this was done before, it returns the existing structure data node.
        This is a calcfunction and therefore keeps the provenance.

        :param fleurinp: a FleurinpData instance to be parsed into a StructureData
        :returns: StructureData node
        """
        return self.get_structuredata_ncf()

    def get_kpointsdata_ncf(self):
        """
        This routine returns an AiiDA :class:`~aiida.orm.KpointsData` type produced from the
        ``inp.xml`` file. This only works if the kpoints are listed in the in inpxml.
        This is NOT a calcfunction and does not keep the provenance!

        :returns: :class:`~aiida.orm.KpointsData` node
        """
        from aiida.orm import KpointsData

        # HINT, TODO:? in this routine, the 'cell' you might get in an other way
        # exp: StructureData.cell, but for this you have to make a structureData Node,
        # which might take more time for structures with lots of atoms.
        # then just parsing the cell from the inp.xml
        # as in the routine get_structureData

        # Disclaimer: this routine needs some xpath expressions.
        # these are hardcoded here, therefore maintainance might be needed,
        # if you want to circumvent this, you have
        # to get all the paths from somewhere.

        #######
        # all hardcoded xpaths used and attributes names:
        bravaismatrix_bulk_xpath = '/fleurInput/cell/bulkLattice/bravaisMatrix/'
        bravaismatrix_film_xpath = '/fleurInput/cell/filmLattice/bravaisMatrix/'
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

        if 'inp.xml' not in self.files:
            print('cannot get a KpointsData because fleurinpdata has no inp.xml file yet')
            # TODO what to do in this case?
            return False

        # else read in inpxml

        if self._schema_file_path:  # Schema there, parse with schema
            xmlschema_doc = etree.parse(self._schema_file_path)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            parser = etree.XMLParser(attribute_defaults=True, encoding='utf-8')
            with self.open(path='inp.xml', mode='r') as inpxmlfile:
                tree = etree.parse(inpxmlfile, parser)
            tree.xinclude()
            # remove comments from inp.xml
            comments = tree.xpath('//comment()')
            for c in comments:
                p = c.getparent()
                p.remove(c)
            if not xmlschema.validate(tree):
                raise ValueError('Input file is not validated against the schema.')
        else:  # schema not there, parse without
            print('parsing inp.xml without XMLSchema')
            with self.open(path='inp.xml', mode='r') as inpxmlfile:
                tree = etree.parse(inpxmlfile)
            tree.xinclude()
            # remove comments from inp.xml
            comments = tree.xpath('//comment()')
            for c in comments:
                p = c.getparent()
                p.remove(c)
        root = tree.getroot()

        # get cell matrix from inp.xml
        cell = None
        row1 = root.xpath(bravaismatrix_bulk_xpath + row1_tag_name)  # [0].text.split()

        if row1:  # bulk calculation
            row1 = row1[0].text.split()
            row2 = root.xpath(bravaismatrix_bulk_xpath + row2_tag_name)[0].text.split()
            row3 = root.xpath(bravaismatrix_bulk_xpath + row3_tag_name)[0].text.split()
            # TODO? allow math?
            for i, cor in enumerate(row1):
                row1[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row2):
                row2[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row3):
                row3[i] = float(cor) * BOHR_A

            cell = [row1, row2, row3]
            # set boundary conditions
            pbc1 = [True, True, True]

        elif root.xpath(bravaismatrix_film_xpath + row1_tag_name):
            # film calculation
            row1 = root.xpath(bravaismatrix_film_xpath + row1_tag_name)[0].text.split()
            row2 = root.xpath(bravaismatrix_film_xpath + row2_tag_name)[0].text.split()
            row3 = root.xpath(bravaismatrix_film_xpath + row3_tag_name)[0].text.split()
            for i, cor in enumerate(row1):
                row1[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row2):
                row2[i] = float(cor) * BOHR_A
            for i, cor in enumerate(row3):
                row3[i] = float(cor) * BOHR_A
            # row3 = [0, 0, 0]#? TODO:what has it to be in this case?
            cell = [row1, row2, row3]
            pbc1 = [True, True, False]

        if cell is None:
            print('Could not extract Bravias matrix out of inp.xml. Is the '
                  'Bravias matrix explicitly given? i.e Latnam definition '
                  'not supported.')
            return None
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
                    kpoint_pos[i] = float(kval) / float(posscale[0])
                    kpoint_weight = float(kpoint.get(kpoint_attrib_weight)) / float(weightscale[0])
                kpoints_pos.append(kpoint_pos)
                kpoints_weight.append(kpoint_weight)
            totalw = 0
            for weight in kpoints_weight:
                totalw = totalw + weight
            kps = KpointsData()
            kps.set_cell(cell)
            kps.pbc = pbc1

            kps.set_kpoints(kpoints_pos, cartesian=False, weights=kpoints_weight)
            #kps.add_link_from(self, label='fleurinp.kpts', link_type=LinkType.CREATE)
            kps.label = 'fleurinp.kpts'
            # return {label: kps}
            return kps
        else:  # TODO parser other kpoints formats, if they fit in an AiiDA node
            print('No kpoint list in inp.xml')
            return None

    @cf
    def get_kpointsdata(self):
        """
        This routine returns an AiiDA :class:`~aiida.orm.KpointsData` type produced from the
        ``inp.xml`` file. This only works if the kpoints are listed in the in inpxml.
        This is a calcfunction and keeps the provenance!

        :returns: :class:`~aiida.orm.KpointsData` node
        """

        return self.get_kpointsdata_ncf()

    def get_parameterdata_ncf(self):
        """
        This routine returns an AiiDA :class:`~aiida.orm.Dict` type produced from the ``inp.xml``
        file. This node can be used for inpgen as `calc_parameters`.
        This is NOT a calcfunction and does NOT keep the provenance!

        :returns: :class:`~aiida.orm.Dict` node
        """
        from aiida_fleur.tools.xml_util import get_inpgen_paranode_from_xml
        if 'inp.xml' not in self.files:
            print('cannot get a StructureData because fleurinpdata has no inp.xml file yet')
            # TODO what to do in this case?
            return False

        # read in inpxml
        with self.open(path='inp.xml', mode='r') as inpxmlfile:
            new_parameters = get_inpgen_paranode_from_xml(etree.parse(inpxmlfile))
        return new_parameters

    # Is there a way to give self to calcfunctions?
    @staticmethod
    @cf
    def get_parameterdata(fleurinp):
        """
        This routine returns an AiiDA :class:`~aiida.orm.Dict` type produced from the ``inp.xml``
        file. The returned node can be used for inpgen as `calc_parameters`.
        This is a calcfunction and keeps the provenance!

        :returns: :class:`~aiida.orm.Dict` node
        """

        return fleurinp.get_parameterdata_ncf()

    def get_tag(self, xpath):
        """
        Tries to evaluate an xpath expression for ``inp.xml`` file. If it fails it logs it.

        :param xpath: an xpath expression
        :returns: A node list retrived using given xpath
        """

        if 'inp.xml' in self.files:
            # read in inpxml
            if self._schema_file_path:  # Schema there, parse with schema
                #xmlschema_doc = etree.parse(self._schema_file_path)
                #xmlschema = etree.XMLSchema(xmlschema_doc)
                #parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)
                with self.open(path='inp.xml', mode='r') as inpxmlfile:
                    tree = etree.parse(inpxmlfile)  # , parser)
            else:  # schema not there, parse without
                print('parsing inp.xml without XMLSchema')
                with self.open(path='inp.xml', mode='r') as inpxmlfile:
                    tree = etree.parse(inpxmlfile)
            root = tree.getroot()
        else:
            raise InputValidationError('No inp.xml file yet specified, to get a tag from')

        try:
            return_value = root.xpath(xpath)
        except etree.XPathEvalError as exc:
            raise InputValidationError('There was a XpathEvalError on the xpath: {} \n Either it does '
                                       'not exist, or something is wrong with the expression.'
                                       ''.format(xpath)) from exc

        if len(return_value) == 1:
            return return_value
        else:
            return return_value
