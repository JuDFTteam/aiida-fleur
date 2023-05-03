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
from __future__ import annotations
import os
import io
import re
import warnings
import pathlib

from aiida import orm
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import InputValidationError, ValidationError

from typing import Any, cast, Iterator, BinaryIO, TextIO, ContextManager, Dict, List

from lxml import etree
from masci_tools.io.parsers.fleur_schema import InputSchemaDict

__all__ = ('FleurinpData', 'get_fleurinp_from_folder_data', 'get_fleurinp_from_remote_data', 'get_structuredata',
           'get_kpointsdata', 'get_parameterdata', 'convert_inpxml', 'get_fleurinp_from_folder_data_cf',
           'get_fleurinp_from_remote_data_cf')


@cf
def get_fleurinp_from_folder_data_cf(folder_node: orm.FolderData,
                                     additional_files: orm.List | None = None) -> FleurinpData:
    """
    Create FleurinpData object from the given FolderData object

    :param remote_node: FolderData to use for the generation of the FleurinpData

    :returns: FleurinpData object with the input xml files from the FolderData
    """

    if additional_files is None:
        additional_files = orm.List(list=[])

    return get_fleurinp_from_folder_data(folder_node, additional_files=additional_files.get_list())


@cf
def get_fleurinp_from_remote_data_cf(remote_node: orm.RemoteData,
                                     additional_files: orm.List | None = None) -> FleurinpData:
    """
    Create FleurinpData object from the given RemoteData object

    :param remote_node: RemoteData to use for the generation of the FleurinpData
    :param store: bool, if True the FleurinpData object will be stored after generation

    :returns: FleurinpData object with the input xml files from the retrieved folder
              of the calculation associated RemoteData
    """

    if additional_files is None:
        additional_files = orm.List(list=[])

    return get_fleurinp_from_remote_data(remote_node, additional_files=additional_files.get_list())


def get_fleurinp_from_folder_data(folder_node: orm.FolderData,
                                  store: bool = False,
                                  additional_files: list[str] | None = None) -> FleurinpData:
    """
    Create FleurinpData object from the given RemoteData object

    :param remote_node: RemoteData to use for the generation of the FleurinpData
    :param store: bool, if True the FleurinpData object will be stored after generation

    :returns: FleurinpData object with the input xml files from the retrieved folder
              of the calculation associated RemoteData
    """
    if additional_files is None:
        additional_files = []
    if isinstance(additional_files, orm.List):
        additional_files = additional_files.get_list()

    input_xml_files = [file for file in folder_node.list_object_names() if file.endswith('.xml') and 'out' not in file]

    fleurinp = FleurinpData(files=input_xml_files + additional_files, node=folder_node)
    if store:
        fleurinp.store()

    return fleurinp


def get_fleurinp_from_remote_data(remote_node: orm.RemoteData,
                                  store: bool = False,
                                  additional_files: list[str] | None = None) -> FleurinpData:
    """
    Create FleurinpData object from the given RemoteData object

    :param remote_node: RemoteData to use for the generation of the FleurinpData
    :param store: bool, if True the FleurinpData object will be stored after generation

    :returns: FleurinpData object with the input xml files from the retrieved folder
              of the calculation associated RemoteData
    """

    for link in remote_node.base.links.get_incoming().all():
        if isinstance(link.node, orm.CalcJobNode):
            parent_calc_node = link.node
    retrieved = parent_calc_node.base.links.get_outgoing().get_node_by_label('retrieved')

    return get_fleurinp_from_folder_data(cast(orm.FolderData, retrieved),
                                         store=store,
                                         additional_files=additional_files)


class FleurinpData(orm.Data):
    """
    AiiDA data object representing everything a FLEUR calculation needs.

    It is initialized with an absolute path to an ``inp.xml`` file or a
    FolderData node containing ``inp.xml``.
    Other files can also be added that will be copied to the remote machine, where the
    calculation takes place.

    It stores the files in the repository and stores the input parameters of the
    ``inp.xml`` file of FLEUR in the database as a python dictionary (as internal attributes).
    When an ``inp.xml`` (name important!) file is added to files, parsed into a XML tree
    and validated against the XML schema file for the given file version. These XML schemas
    are provided by the `masci-tools` library


    FleurinpData also provides the user with
    methods to extract AiiDA StructureData, KpointsData nodes
    and Dict nodes with LAPW parameters.

    Remember that most attributes of AiiDA nodes can not be changed after they
    have been stored in the database! Therefore, you have to use the FleurinpModifier class and its
    methods if you want to change somthing in the ``inp.xml`` file. You will retrieve a new
    FleurinpData that way and start a new calculation from it.
    """

    __version__ = '0.6.1'

    def __init__(self, files: list[str] | None = None, node: orm.Node | str | int | None = None, **kwargs: Any) -> None:
        """
        Initialize a FleurinpData object set the files given
        """
        super().__init__(**kwargs)
        if files is None:
            files = []

        for filename in files:
            if 'inp.xml' in filename:
                files.pop(files.index(filename))
                files.append(filename)
                break

        if files:
            self.set_files(files, node=node)

    @property
    def parser_info(self) -> dict[str, Any]:
        """
        Dict property, with the info and warnings from the inpxml_parser
        """
        return self.base.extras.get('_parser_info', {})

    @parser_info.setter
    def parser_info(self, info_dict: dict[str, Any]) -> None:
        """
        Setter for has_schema
        """
        self.base.extras.set('_parser_info', info_dict)

    # files
    @property
    def files(self) -> list[str]:
        """
        Returns the list of the names of the files stored
        """
        return self.base.attributes.get('files', [])

    @files.setter
    def files(self, filelist: list[str]) -> None:
        """
        Add a list of files to FleurinpData.
        Alternative use setter method.

        :param files: list of filepaths or filenames of node is specified
        """
        self.set_files(filelist)

    def set_files(self, files: list[str], node: orm.Node | str | int | None = None) -> None:
        """
        Add the list of files to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.
        Can by used as an alternative to the setter.

        :param files: list of abolute filepaths or filenames of node is specified
        :param node: a :class:`~aiida.orm.FolderData` node containing files from the filelist
        """
        for filename in files:
            self.set_file(filename, node=node)

    def set_file(self,
                 filename: str,
                 dst_filename: str | None = None,
                 node: orm.Node | str | int | None = None) -> None:
        """
        Add a file to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` instance.

        :param filename: absolute path to the file or a filename of node is specified
        :param node: a :class:`~aiida.orm.FolderData` node containing the file
        """
        self._add_path(filename, dst_filename=dst_filename, node=node)

    def open(self, path: str = 'inp.xml', mode: str = 'r') -> ContextManager[BinaryIO | TextIO]:
        """
        Returns an open file handle to the content of this data node.

        :param key: name of the file to be opened
        :param mode: the mode with which to open the file handle
        :returns: A file handle in read mode
        """
        return self.base.repository.open(path, mode=mode)

    def get_content(self, filename: str = 'inp.xml') -> str:
        """
        Returns the content of the single file stored for this data node.

        :returns: A string of the file content
        """
        with self.open(path=filename, mode='r') as handle:
            return handle.read()  #type: ignore[return-value]

    def del_file(self, filename: str) -> None:
        """
        Remove a file from FleurinpData instancefind

        :param filename: name of the file to be removed from FleurinpData instance
        """
        # remove from files attr list
        filelist_attribute = self.base.attributes.get('files', [])
        if filename in filelist_attribute:
            filelist_attribute.remove(filename)
            self.base.attributes.set('files', filelist_attribute)
            self.delete_object(filename)
        else:
            raise ValueError(f'Could not delete file {filename} from fleurinp node {self.pk}'
                             'File does not exist on the node')

    def _add_path(self,
                  path_or_handle: str | pathlib.Path | BinaryIO,
                  dst_filename: str | None = None,
                  node: orm.Node | str | int | None = None) -> None:
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

        if node is not None:
            if not isinstance(node, orm.Node):
                node = orm.load_node(node)
            if not isinstance(path_or_handle, str):
                raise ValueError('When providing node the path has to be a string')

            if path_or_handle not in node.list_object_names():
                # throw error, you try to add something that is not there
                raise ValueError(f'The file {path_or_handle} has to be present in the specified node {node.pk}')

            is_filelike = True
            final_filename = path_or_handle

            # Get bytestring of file
            # since we have to use 'with', and node has no method to copy files
            # we read the whole file and write it again later
            # this is not so nice, but we assume that input files are rather small...
            with node.base.repository.open(path_or_handle, mode='rb') as file:
                path_or_handle = io.BytesIO(file.read())  #type: ignore[arg-type]

        elif isinstance(path_or_handle, (str, pathlib.Path)):
            is_filelike = False
            path_or_handle = pathlib.Path(path_or_handle)

            if not path_or_handle.is_absolute():
                path_or_handle = path_or_handle.resolve()

            if not path_or_handle.is_file():
                raise ValueError(f'Path {os.fspath(path_or_handle)} must exist and must be a single file')

            final_filename = path_or_handle.name
        else:
            is_filelike = True

            try:
                final_filename = os.path.basename(path_or_handle.name)
            except AttributeError:
                final_filename = 'UNKNOWN'

        if dst_filename is not None:
            final_filename = dst_filename

        if final_filename == 'UNKNOWN':
            raise ValueError('Provided an anonymous file handle without a filename')

        old_files_list = self.base.attributes.get('files', [])

        # remove file from folder first if it exists
        if final_filename not in old_files_list:
            old_files_list.append(final_filename)

        if is_filelike:
            self.put_object_from_filelike(path_or_handle, final_filename)
        else:
            self.put_object_from_file(path_or_handle, final_filename)

        self.base.attributes.set('files', old_files_list)  # We want to keep the other files

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
                                           f'in given input file: {path_or_handle}. {lines}'
                                           'Please check if this is a valid fleur input file. '
                                           'It can not be validated and I can not use it. ')

            self.base.attributes.set('inp_version', inp_version_number)
            # finally set inp dict of Fleurinpdata
            self._set_inp_dict()

    def _set_inp_dict(self) -> None:
        """
        Sets the inputxml_dict from the ``inp.xml`` file attached to FleurinpData

        1. load ``inp.xml`` file
        2. insert all files to include into the etree
        3. call masci-tools input file parser (Validation happens inside here)
        4. set inputxml_dict
        """
        from masci_tools.io.parsers.fleur import inpxml_parser

        #The schema_dict is not needed outside the inpxml_parser so we ignore it with the underscore
        xmltree, _ = self.load_inpxml()  #type: ignore[misc]

        parser_info: dict[str, Any] = {}
        try:
            inpxml_dict = inpxml_parser(xmltree, parser_info_out=parser_info)
        except (ValueError, FileNotFoundError) as exc:
            raise InputValidationError(f'inp.xml parser failed: {exc}') from exc
        finally:
            #Always try to provide the error/warning information
            self.parser_info = parser_info

        # set inpxml_dict attribute
        self.base.attributes.set('inp_dict', inpxml_dict)

    def load_inpxml(
        self,
        validate_xml_schema: bool = True,
        return_included_tags: bool = False,
        **kwargs: Any
    ) -> tuple[etree._ElementTree, InputSchemaDict] | tuple[etree._ElementTree, InputSchemaDict, set[str]]:
        """
        Returns the lxml etree and the schema dictionary corresponding to the version. If validate_xml_schema=True
        the file will also be validated against the schema

        Keyword arguments are passed on to the parser
        """
        from masci_tools.io.fleur_xml import load_inpxml

        self._validate()

        with self.open(path='inp.xml', mode='rb') as inpxmlfile:
            try:
                xmltree, schema_dict = load_inpxml(inpxmlfile, **kwargs)
            except ValueError as exc:
                # prob inp.xml file broken
                err_msg = ('The inp.xml file is probably broken, could not parse it to an xml etree.')
                raise InputValidationError(err_msg) from exc
            except FileNotFoundError as exc:
                # prob inp.xml file broken
                err_msg = ('The inp.xml file is probably broken, could not find corresponding input schema.')
                raise InputValidationError(err_msg) from exc

        xmltree, included_tags = self._include_files(xmltree)
        develop_version = self.inp_version != schema_dict['inp_version']

        if validate_xml_schema and not develop_version:
            try:
                schema_dict.validate(xmltree)
            except ValueError as err:
                raise InputValidationError(err) from err
        elif develop_version and self.logger is not None:
            self.logger.warning(f'You are using a Fleur input file with file version {self.inp_version}.\n'
                                'This version has no corresponding XML Schema stored in masci-tools.\n'
                                'Unexpected Errors can occur. If that is the case you can try to add the '
                                'XML Schema for this file version to masci-tools')

        if return_included_tags:
            return xmltree, schema_dict, included_tags
        return xmltree, schema_dict

    def _include_files(self, xmltree: etree._ElementTree) -> tuple[etree._ElementTree, set[str]]:
        """
        Tries to insert all .xml, which are not inp.xml file into the etree since they are
        not naturally available for the parser (open vs self.open)

        Creates a NamedTemporaryFile for each one with their content
        and replaces the name in the `href` attributes of the `xi:include` tags.
        Then these are expanded with `xmltree.xinclude()`
        """
        from masci_tools.util.xml.common_functions import clear_xml, eval_xpath
        import tempfile

        temp_files = []
        for file in self.files:
            #Check if the filename appears in a xi:include tag
            nodes = eval_xpath(xmltree,
                               '//xi:include[@href=$filename]',
                               namespaces={'xi': 'http://www.w3.org/2001/XInclude'},
                               filename=file,
                               list_return=True)
            if not nodes:
                continue

            #Get file content from node
            include_content = self.get_content(file)

            #Write content into temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as fo:
                fo.write(include_content)
                temp_files.append(fo.name)
                for node in nodes:
                    node.set('href', fo.name)

        #Performs the inclusions and remove comments
        cleared_tree, included_tags = clear_xml(xmltree)

        #Remove created temporary files
        for file in temp_files:
            os.remove(file)

        return cleared_tree, included_tags

    # dict with inp paramters parsed from inp.xml
    @property
    def inp_dict(self) -> dict[str, Any]:
        """
        Returns the inp_dict (the representation of the ``inp.xml`` file) as it will
        or is stored in the database.
        """
        return self.base.attributes.get('inp_dict', {})

    # version of the inp.xml file
    @property
    def inp_version(self) -> str | None:
        """
        Returns the version string corresponding to the inp.xml file
        """
        return self.base.attributes.get('inp_version', None)

    def _validate(self) -> None:  #type: ignore[override]
        """
        A validation method. Checks if an ``inp.xml`` file is in the FleurinpData.
        """
        #from aiida.common.exceptions import ValidationError
        # check if schema file path exists.
        super()._validate()

        if 'inp.xml' not in self.files:
            raise ValidationError('inp.xml file not in attribute "files". '
                                  'FleurinpData needs to have and inp.xml file!')

    def get_fleur_modes(self) -> dict[str, Any]:
        """
        Analyses ``inp.xml`` file to set up a calculation mode. 'Modes' are paths a FLEUR
        calculation can take, resulting in different output.
        This files can be automatically addded to the retrieve_list of the calculation.

        Common modes are: scf, jspin2, dos, band, pot8, lda+U, eels, ...

        :return: a dictionary containing all possible modes.
        """
        from masci_tools.util.xml.xml_getters import get_fleur_modes

        xmltree, schema_dict = self.load_inpxml()  #type: ignore[misc]

        return get_fleur_modes(xmltree, schema_dict)

    def get_nkpts(self) -> int:
        """
        This routine returns the number of kpoints used in the fleur calculation
        defined in this input

        :returns: int with the number of kPoints
        """
        from masci_tools.util.xml.xml_getters import get_nkpts

        xmltree, schema_dict = self.load_inpxml()  #type: ignore[misc]

        return get_nkpts(xmltree, schema_dict)

    def get_structuredata_ncf(self, normalize_kind_name: bool = True) -> orm.StructureData:
        """
        This routine returns an AiiDA Structure Data type produced from the ``inp.xml``
        file. not a calcfunction

        :param self: a FleurinpData instance to be parsed into a StructureData
        :returns: StructureData node, or None
        """
        from masci_tools.util.xml.xml_getters import get_structuredata as get_structuredata_xml

        xmltree, schema_dict = self.load_inpxml()  #type: ignore[misc]

        atoms, cell, pbc = get_structuredata_xml(xmltree, schema_dict, normalize_kind_name=normalize_kind_name)

        struc = orm.StructureData(cell=cell, pbc=pbc)

        for atom in atoms:
            struc.append_atom(position=atom.position, symbols=atom.symbol, name=atom.kind)

        # TODO DATA-DATA links are not wanted, you might want to use a cf instead
        #struc.add_link_from(self, label='self.structure', link_type=LinkType.CREATE)
        # label='self.structure'
        # return {label : struc}
        return struc

    def get_structuredata(self, normalize_kind_name: orm.Bool | None = None) -> orm.StructureData:
        """
        This routine return an AiiDA Structure Data type produced from the ``inp.xml``
        file. If this was done before, it returns the existing structure data node.
        This is a calcfunction and therefore keeps the provenance.

        :param fleurinp: a FleurinpData instance to be parsed into a StructureData
        :returns: StructureData node
        """
        return get_structuredata(self, normalize_kind_name=normalize_kind_name)

    def get_kpointsdata_ncf(self,
                            name: str | None = None,
                            index: int | None = None,
                            only_used: bool = False) -> orm.KpointsData | dict[str, orm.KpointsData]:
        """
        This routine returns an AiiDA :class:`~aiida.orm.KpointsData` type produced from the
        ``inp.xml`` file. This only works if the kpoints are listed in the in inpxml.
        This is NOT a calcfunction and does not keep the provenance!

        :param name: str, optional, if given only the kpoint set with the given name
                     is returned
        :param index: int, optional, if given only the kpoint set with the given index
                      is returned

        :returns: :class:`~aiida.orm.KpointsData` node
        """
        from masci_tools.util.xml.xml_getters import get_kpointsdata as get_kpointsdata_xml

        # HINT, TODO:? in this routine, the 'cell' you might get in an other way
        # exp: StructureData.cell, but for this you have to make a structureData Node,
        # which might take more time for structures with lots of atoms.
        # then just parsing the cell from the inp.xml
        # as in the routine get_structureData

        xmltree, schema_dict = self.load_inpxml()  #type: ignore[misc]

        if name is None and index is None:
            kpoints, weights, cell, pbc = get_kpointsdata_xml(xmltree, schema_dict, only_used=only_used)
        else:
            kpoints, weights, cell, pbc = get_kpointsdata_xml(xmltree,
                                                              schema_dict,
                                                              name=name,
                                                              index=index,
                                                              only_used=only_used)

        if isinstance(kpoints, dict):
            weights = cast(Dict[str, List[float]], weights)
            kpoints_data = {}
            for (label, kpoints_set), weights_set in zip(kpoints.items(), weights.values()):
                kps = orm.KpointsData()
                kps.set_cell(cell)
                kps.pbc = pbc
                kps.set_kpoints(kpoints_set, cartesian=False, weights=weights_set)
                #kpoints_data.add_link_from(self, label='fleurinp.kpts', link_type=LinkType.CREATE)
                pattern = re.compile(r'\W', re.UNICODE)
                kpoint_identifier = re.sub(pattern, '', label.replace('-', '_'))
                if kpoint_identifier != label.replace('-', '_'):
                    warnings.warn(
                        f'Normed the name of the kpoint set {label} to {kpoint_identifier}'
                        ' to be able to use it as a link label', UserWarning)
                kps.label = f'fleurinp.kpts.{kpoint_identifier}'
                kpoints_data[kpoint_identifier] = kps
            return kpoints_data

        kps = orm.KpointsData()
        kps.set_cell(cell)
        kps.pbc = pbc
        kps.set_kpoints(kpoints, cartesian=False, weights=weights)
        #kps.add_link_from(self, label='fleurinp.kpts', link_type=LinkType.CREATE)
        kps.label = 'fleurinp.kpts'
        return kps

    def get_kpointsdata(self,
                        name: orm.Str | None = None,
                        index: orm.Int | None = None,
                        only_used: orm.Bool | None = None) -> orm.KpointsData | dict[str, orm.KpointsData]:
        """
        This routine returns an AiiDA :class:`~aiida.orm.KpointsData` type produced from the
        ``inp.xml`` file. This only works if the kpoints are listed in the in inpxml.
        This is a calcfunction and keeps the provenance!

        :returns: :class:`~aiida.orm.KpointsData` node
        """
        return get_kpointsdata(self, name=name, index=index, only_used=only_used)

    def get_parameterdata_ncf(self, inpgen_ready: bool = True, write_ids: bool = True) -> orm.Dict:
        """
        This routine returns an AiiDA :class:`~aiida.orm.Dict` type produced from the ``inp.xml``
        file. This node can be used for inpgen as `calc_parameters`.
        This is NOT a calcfunction and does NOT keep the provenance!

        :returns: :class:`~aiida.orm.Dict` node
        """
        from masci_tools.util.xml.xml_getters import get_parameterdata as get_parameterdata_xml

        xmltree, schema_dict = self.load_inpxml()  #type: ignore[misc]

        parameter_data = get_parameterdata_xml(xmltree, schema_dict, inpgen_ready=inpgen_ready, write_ids=write_ids)

        return orm.Dict(parameter_data)

    def get_parameterdata(self, inpgen_ready: orm.Bool | None = None, write_ids: orm.Bool | None = None) -> orm.Dict:
        """
        This routine returns an AiiDA :class:`~aiida.orm.Dict` type produced from the ``inp.xml``
        file. The returned node can be used for inpgen as `calc_parameters`.
        This is a calcfunction and keeps the provenance!

        :returns: :class:`~aiida.orm.Dict` node
        """
        return get_parameterdata(self, inpgen_ready=inpgen_ready, write_ids=write_ids)

    def convert_inpxml(self, to_version: orm.Str) -> FleurinpData:
        """
        Convert the fleurinp data node to a different inp.xml version
        and return a clone of the node

        .. note::
            If the Fleurinp contains included xml trees the resulting
            FleurinpData will contain only the combined inp.xml
        """
        return convert_inpxml(self, to_version.value)

    def convert_inpxml_ncf(self, to_version: str) -> FleurinpData:
        """
        Convert the fleurinp data node to a different inp.xml version
        and return a clone of the node

        .. note::
            If the Fleurinp contains included xml trees the resulting
            FleurinpData will contain only the combined inp.xml
        """
        from masci_tools.tools.fleur_inpxml_converter import convert_inpxml as convert_inpxml_actual
        import tempfile
        clone = self.clone()

        xmltree, schema_dict = clone.load_inpxml(remove_blank_text=True)
        try:
            converted_tree = convert_inpxml_actual(xmltree, schema_dict, to_version)
        except FileNotFoundError as exc:
            raise ValueError(
                f"No conversion available from version {schema_dict['inp_version']} to {to_version}\n"
                'Please create the conversion by running\n'
                f"     masci-tools generate-conversion {schema_dict['inp_version']}  {to_version}\n") from exc

        clone.del_file('inp.xml')
        with tempfile.TemporaryDirectory() as td:
            inpxml_path = os.path.join(td, 'inp.xml')
            converted_tree.write(inpxml_path, encoding='utf-8', pretty_print=True)
            clone.set_file(inpxml_path, 'inp.xml')

        # default label and description
        clone.label = 'fleurinp_converted'
        clone.description = f"Fleurinpdata converted from version {schema_dict['inp_version']} to {to_version}"

        return clone


@cf
def get_kpointsdata(fleurinp: FleurinpData,
                    name: orm.Str | None = None,
                    index: orm.Int | None = None,
                    only_used: orm.Bool | None = None) -> orm.KpointsData | dict[str, orm.KpointsData]:
    """
    This routine returns an AiiDA :class:`~aiida.orm.KpointsData` type produced from the
    ``inp.xml`` file. This only works if the kpoints are listed in the in inpxml.
    This is a calcfunction and keeps the provenance!

    :returns: :class:`~aiida.orm.KpointsData` node or dict of :class:`~aiida.orm.KpointsData`
    """
    if only_used is None:
        only_used = orm.Bool(False)
    return fleurinp.get_kpointsdata_ncf(name=name, index=index, only_used=only_used)  #type: ignore[arg-type]


@cf
def get_structuredata(fleurinp: FleurinpData, normalize_kind_name: orm.Bool | None = None) -> orm.StructureData:
    """
    This routine return an AiiDA Structure Data type produced from the ``inp.xml``
    file. If this was done before, it returns the existing structure data node.
    This is a calcfunction and therefore keeps the provenance.

    :param fleurinp: a FleurinpData instance to be parsed into a StructureData
    :returns: StructureData node
    """
    if normalize_kind_name is None:
        normalize_kind_name = orm.Bool(True)
    return fleurinp.get_structuredata_ncf(normalize_kind_name=normalize_kind_name.value)


@cf
def get_parameterdata(fleurinp: FleurinpData,
                      inpgen_ready: orm.Bool | None = None,
                      write_ids: orm.Bool | None = None) -> orm.Dict:
    """
    This routine returns an AiiDA :class:`~aiida.orm.Dict` type produced from the ``inp.xml``
    file. The returned node can be used for inpgen as `calc_parameters`.
    This is a calcfunction and keeps the provenance!

    :returns: :class:`~aiida.orm.Dict` node
    """
    if inpgen_ready is None:
        inpgen_ready = orm.Bool(True)

    if write_ids is None:
        write_ids = orm.Bool(True)

    return fleurinp.get_parameterdata_ncf(inpgen_ready=inpgen_ready.value, write_ids=write_ids.value)


@cf
def convert_inpxml(fleurinp: FleurinpData, to_version: orm.Str) -> FleurinpData:
    """
    Convert the fleurinp data node to a different inp.xml version
    and return a clone of the node

    .. note::
        If the Fleurinp contains included xml trees the resulting
        FleurinpData will contain only the combined inp.xml
    """
    return fleurinp.convert_inpxml_ncf(to_version.value)
