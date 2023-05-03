# pylint: disable=inconsistent-return-statements,protected-access,missing-docstring
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
In this module is the FleurinpModifier class, which is used to manipulate
FleurinpData objects in a way which keeps the provernance.
"""
from __future__ import annotations
from contextlib import contextmanager

import os
from lxml import etree
import warnings

from aiida.engine import calcfunction as cf
from aiida.engine import ProcessBuilderNamespace
from aiida.common import AttributeDict
from aiida import orm

from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.tools.xml_aiida_modifiers import set_kpointsdata_f

from masci_tools.io.fleurxmlmodifier import ModifierTask, FleurXMLModifier
from masci_tools.util.xml.common_functions import serialize_xml_objects
from typing import Any, Generator, Callable

__all__ = ('FleurinpModifier', 'inpxml_changes', 'modify_fleurinpdata')


@contextmanager
def inpxml_changes(wf_parameters: dict | orm.Dict | ProcessBuilderNamespace,
                   append: bool = True,
                   builder_entry: str = 'wf_parameters',
                   builder_replace_stored: bool = True) -> Generator[FleurinpModifier, None, None]:
    """
    Contextmanager to construct an `inpxml_changes` entry in the given dictionary

    Usage::

        with inpxml_changes(parameters) as fm: #parameters is a dict, which can also already contain an inpxml_changes entry
            fm.set_inpchanges({'l_noco': True, 'ctail': False})
            fm.set_species('all-Nd', {'electronConfig': {'flipspins': True}})

        print(parameters) #The parameters now also contains the tasks defined in the with block

    Example for usage with a Builder::

        from aiida import plugins

        FleurBandDOS = plugins.WorkflowFactory('fleur.banddos')
        inputs = FleurBandDOS.get_builder()

        with inpxml_changes(inputs) as fm:
            fm.set_inpchanges({'l_noco': True, 'ctail': False})
            fm.set_species('all-Nd', {'electronConfig': {'flipspins': True}})

        #The wf_parameters in the root level namespace are now set
        print(inputs.wf_parameters['inpxml_changes'])

        with inpxml_changes(inputs.scf) as fm:
            fm.switch_kpointset('my-awesome-kpoints')

        #The wf_parameters in the scf namespace are now set
        print(inputs.scf.wf_parameters['inpxml_changes'])

    :param wf_parameters: dict or aiida Dict (no stored) into which to enter the changes
    :param append: bool if True the tasks are appended behind any evtl. already defined. For False the tasks are added in front
    :param builder_entry: name of the entry for the inp.xml changes inside the parameters dictionary
    :param builder_replace_stored: if True and a ProcessBuilder is given and the wf_parameters input is given and
                                   already stored the produced changes will replace the node
    """

    _INPXML_CHANGES_KEY = 'inpxml_changes'

    if isinstance(wf_parameters, orm.Dict) and wf_parameters.is_stored:
        raise ValueError('Cannot modify already stored wf_parameters')

    #Make sure that a AiiDA node in a ProcessBuilder is not already stored
    if not builder_replace_stored \
       and isinstance(wf_parameters,(ProcessBuilderNamespace, AttributeDict)) \
       and wf_parameters.get(builder_entry, orm.Dict()).is_stored:
        raise ValueError('Cannot modify already stored wf_parameters')

    fm = FleurinpModifier()  #Since no original is provided this will crash if validate/show or freeze are called on it
    try:
        yield fm
    finally:
        builder = None
        if isinstance(wf_parameters, (ProcessBuilderNamespace, AttributeDict)):
            builder = wf_parameters
            wf_parameters = wf_parameters.setdefault(builder_entry, orm.Dict())

        if isinstance(wf_parameters, orm.Dict):
            wf_parameters = wf_parameters.get_dict()

        changes = wf_parameters.get(_INPXML_CHANGES_KEY, [])  #type: ignore[call-arg]
        if append:
            changes.extend(fm.task_list)
        else:
            for change in reversed(fm.task_list):
                changes.insert(0, change)

        wf_parameters[_INPXML_CHANGES_KEY] = changes
        if builder is not None and builder_replace_stored:
            builder[builder_entry] = orm.Dict(dict=wf_parameters)


class FleurinpModifier(FleurXMLModifier):
    """
    A class which represents changes to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` object.
    """

    _extra_functions = {'schema_dict': {'set_kpointsdata': set_kpointsdata_f}}

    def __init__(self, original: FleurinpData | None = None) -> None:
        """
        Initiation of FleurinpModifier.

        .. note::
            The original argument can be `None`. However in this case the methods :py:meth:`show()`,
            :py:meth:`validate()` and :py:meth:`freeze()` can no longer be used. Only the task_list
            property is accessible in this case

        :param original: FleurinpData to modify
        """

        if original is not None:
            if not isinstance(original, FleurinpData):
                raise TypeError(
                    f'Wrong Type for {self.__class__.__name__}. Expected {FleurinpData.__name__}. Got: {original.__class__.__name__}'
                )

        self._original = original
        self._other_nodes: dict[str, orm.Node] = {}

        super().__init__()

    def _get_setter_func_kwargs(self, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Map the given args and kwargs to just kwargs for the setter function with the given name

        :param name: name of the setter function
        :param args: positional arguments to the setter function
        :param kwargs: keyword arguments to the setter function
        """
        from inspect import signature

        if name not in ('set_file', 'del_file'):
            return super()._get_setter_func_kwargs(name, args, kwargs)

        #The fleurinp file modifying function signatures are taken from teh FleruinpModifier directly
        sig = signature(getattr(self, name))
        bound = sig.bind(*args, **kwargs)

        kwargs_complete = dict(bound.arguments)

        #Fix if the function has an explicit kwargs
        if 'kwargs' in kwargs_complete:
            kwargs_explicit = kwargs_complete.pop('kwargs')
            kwargs_complete = {**kwargs_complete, **kwargs_explicit}

        return kwargs_complete

    @classmethod
    def apply_fleurinp_modifications(cls, new_fleurinp: FleurinpData, modification_tasks: list[ModifierTask]) -> None:
        """
        Apply the modifications working directly on the cloned
        FleurinpData instance. The functions will warn the user if one of the methods
        executed here are after XML modifications in the task list, since this method will implictly
        reorder the order of the execution

        .. warning::
            These should be performed BEFORE the XML Modification methods
            in any of the functions doing modifcations (:py:meth:`FleurinpModifier.show()`,
            :py:meth:`FleurinpModifier.validate()`, :py:meth:`FleurinpModifier.freeze()`).

        :param new_fleurinp: The Fleurinpdata instance cloned from the original
        :param modification_tasks: a list of modification tuples
        """
        #These functions from the FleurinpData are supported
        fleurinp_mod_functions = {'set_file': new_fleurinp.set_file, 'del_file': new_fleurinp.del_file}

        warn = False
        for task in modification_tasks.copy():
            if task.name in fleurinp_mod_functions:
                modification_tasks.remove(task)
                action = fleurinp_mod_functions[task.name]
                action(*task.args, **task.kwargs)  #type:ignore[operator]
                if warn:
                    warnings.warn('The modification methods operating directly adding/removing files '
                                  'are performed before any XML modification methods')
            else:
                warn = True

    def get_avail_actions(self) -> dict[str, Callable]:
        """
        Returns the allowed functions from FleurinpModifier
        """
        outside_actions_fleurinp = {
            'set_kpointsdata': self.set_kpointsdata,
            'set_file': self.set_file,
            'del_file': self.del_file
        }

        outside_actions_fleurxml = super().get_avail_actions().copy()

        return {**outside_actions_fleurxml, **outside_actions_fleurinp}  #type: ignore[arg-type]

    def set_kpointsdata(self,
                        kpointsdata_uuid: int | str | orm.KpointsData,
                        name: str | None = None,
                        switch: bool = False,
                        kpoint_type: str = 'path') -> None:
        """
        Appends a :py:func:`~aiida_fleur.tools.xml_aiida_modifiers.set_kpointsdata_f()` to
        the list of tasks that will be done on the FleurinpData.

        :param kpointsdata_uuid: node identifier or :class:`~aiida.orm.KpointsData` node to be written into ``inp.xml``
        :param name: str name to give the newly entered kpoint list (only MaX5 or later)
        :param switch: bool if True the entered kpoint list will be used directly (only Max5 or later)
        :param kpoint_type: str of the type of kpoint list given (mesh, path, etc.) only Max5 or later
        """

        if isinstance(kpointsdata_uuid, orm.KpointsData):
            kpointsdata_uuid = kpointsdata_uuid.uuid
        # Be more careful? Needs to be stored, otherwise we cannot load it

        num_nodes = sum('kpoints' in label for label in self._other_nodes) + 1
        node_label = f'kpoints_{num_nodes}'

        self._other_nodes[node_label] = orm.load_node(kpointsdata_uuid)
        self._tasks.append(
            ModifierTask('set_kpointsdata',
                         args=(kpointsdata_uuid,),
                         kwargs={
                             'name': name,
                             'switch': switch,
                             'kpoint_type': kpoint_type
                         }))

    #Modification functions that accept XML elements, which have to be serialized beforehand
    def xml_create_tag(self, *args: Any, **kwargs: Any) -> None:
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_basic.xml_create_tag()` to
        the list of tasks that will be done on the xmltree.

        :param xpath: a path where to place a new tag
        :param element: a tag name or etree Element to be created
        :param place_index: defines the place where to put a created tag
        :param tag_order: defines a tag order
        :param occurrences: int or list of int. Which occurence of the parent nodes to create a tag.
                            By default all nodes are used.
        """
        self._validate_arguments('xml_create_tag', args, kwargs)
        args, kwargs = serialize_xml_objects(args, kwargs)
        super().xml_create_tag(*args, **kwargs)

    def create_tag(self, *args: Any, **kwargs: Any) -> None:
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_names.create_tag()` to
        the list of tasks that will be done on the xmltree.

        :param tag: str of the tag to create
        :param complex_xpath: an optional xpath to use instead of the simple xpath for the evaluation
        :param create_parents: bool optional (default False), if True and the given xpath has no results the
                               the parent tags are created recursively
        :param occurrences: int or list of int. Which occurence of the parent nodes to create a tag.
                            By default all nodes are used.

        Kwargs:
            :param contains: str, this string has to be in the final path
            :param not_contains: str, this string has to NOT be in the final path
        """
        self._validate_arguments('create_tag', args, kwargs)
        args, kwargs = serialize_xml_objects(args, kwargs)
        super().create_tag(*args, **kwargs)

    def xml_replace_tag(self, *args: Any, **kwargs: Any) -> None:
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_basic.xml_replace_tag()` to
        the list of tasks that will be done on the xmltree.

        :param xpath: a path to the tag to be replaced
        :param element: a new tag
        :param occurrences: int or list of int. Which occurence of the parent nodes to create a tag.
                            By default all nodes are used.
        """
        self._validate_arguments('xml_replace_tag', args, kwargs)
        args, kwargs = serialize_xml_objects(args, kwargs)
        super().xml_replace_tag(*args, **kwargs)

    def replace_tag(self, *args: Any, **kwargs: Any) -> None:
        """
        Deprecation layer for replace_tag if there are slashes in the first positional argument or xpath is is in kwargs.
        We know that it is the old usage.

        Appends a :py:func:`~masci_tools.util.xml.xml_setters_names.replace_tag()` to
        the list of tasks that will be done on the xmltree.

        :param tag: str of the tag to replace
        :param newelement: a new tag
        :param complex_xpath: an optional xpath to use instead of the simple xpath for the evaluation
        :param occurrences: int or list of int. Which occurence of the parent nodes to replace a tag.
                            By default all nodes are used.

        Kwargs:
            :param contains: str, this string has to be in the final path
            :param not_contains: str, this string has to NOT be in the final path
        """
        self._validate_arguments('replace_tag', args, kwargs)
        args, kwargs = serialize_xml_objects(args, kwargs)
        super().replace_tag(*args, **kwargs)

    def set_file(self,
                 filename: str,
                 dst_filename: str | None = None,
                 node: int | str | orm.Data | None = None) -> None:
        """
        Appends a :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.set_file()` to
        the list of tasks that will be done on the FleurinpData instance.

        :param filename: absolute path to the file or a filename of node is specified
        :param dst_filename: str of the filename, which should be used instead of the real filename
                             to store it
        :param node: a :class:`~aiida.orm.FolderData` node containing the file
        """

        node_uuid: None | int | str = None
        if node is not None:
            if isinstance(node, orm.Data):
                node_uuid = node.uuid
            else:
                node_uuid = node
            num_nodes = sum('folder' in label for label in self._other_nodes) + 1
            node_label = f'folder_{num_nodes}'
            # Be more careful? Needs to be stored, otherwise we cannot load it
            self._other_nodes[node_label] = orm.load_node(node_uuid)

        self._tasks.append(
            ModifierTask('set_file', args=(filename,), kwargs={
                'dst_filename': dst_filename,
                'node': node_uuid
            }))

    def del_file(self, filename: str) -> None:
        """
        Appends a :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.del_file()` to
        the list of tasks that will be done on the FleurinpData instance.

        :param filename: name of the file to be removed from FleurinpData instance
        """
        self._tasks.append(ModifierTask('del_file', args=(filename,), kwargs={}))

    def validate(self) -> etree._ElementTree:
        """
        Extracts the schema-file.
        Makes a test if all the changes lead to an inp.xml file that is validated against the
        schema.

        :return: a lxml tree representing inp.xml with applied changes
        """
        if self._original is None:
            raise ValueError('The validate() method can only be used if a original FleurinpData'
                             ' was given on initialization')

        new_fleurinp = self._original.clone()
        tasks = self._tasks.copy()
        self.apply_fleurinp_modifications(new_fleurinp, tasks)

        xmltree, schema_dict = new_fleurinp.load_inpxml(remove_blank_text=True)
        develop_version = new_fleurinp.inp_version != schema_dict['inp_version']

        try:
            with new_fleurinp.open(path='n_mmp_mat', mode='r') as n_mmp_file:
                nmmplines = n_mmp_file.read().split('\n')
        except FileNotFoundError:
            nmmplines = None

        try:
            xmltree, nmmp = super().apply_modifications(xmltree, nmmplines, tasks)
        except etree.DocumentInvalid as exc:
            if not develop_version:
                raise
            new_fleurinp.logger.warning(f'Ignoring validation errors for modifications of develop version: \n{exc}')

        return xmltree

    def show(self, display: bool = True, validate: bool = False) -> etree._ElementTree:
        """
        Applies the modifications and displays/prints the resulting ``inp.xml`` file.
        Does not generate a new
        :class:`~aiida_fleur.data.fleurinp.FleurinpData` object.

        :param display: a boolean that is True if resulting ``inp.xml`` has to be printed out
        :param validate: a boolean that is True if changes have to be validated

        :return: a lxml tree representing inp.xml with applied changes
        """
        if self._original is None:
            raise ValueError('The show() method can only be used if a original FleurinpData'
                             ' was given on initialization')

        if validate:
            xmltree = self.validate()
        else:
            new_fleurinp = self._original.clone()
            tasks = self._tasks.copy()

            self.apply_fleurinp_modifications(new_fleurinp, tasks)

            xmltree, schema_dict = new_fleurinp.load_inpxml(remove_blank_text=True)
            try:
                with new_fleurinp.open(path='n_mmp_mat', mode='r') as n_mmp_file:
                    nmmplines = n_mmp_file.read().split('\n')
            except FileNotFoundError:
                nmmplines = None

            xmltree, nmmp = super().apply_modifications(xmltree, nmmplines, tasks, validate_changes=False)

        if display:
            xmltreestring = etree.tostring(xmltree, encoding='unicode', pretty_print=True)
            print(xmltreestring)
        return xmltree

    def freeze(self) -> FleurinpData:
        """
        This method applies all the modifications to the input and
        returns a new stored fleurinpData object.

        :return: stored :class:`~aiida_fleur.data.fleurinp.FleurinpData` with applied changes
        """
        if self._original is None:
            raise ValueError('The freeze() method can only be used if a original FleurinpData'
                             ' was given on initialization')
        from aiida.orm import Dict
        modifications = Dict({'tasks': self._tasks})
        modifications.description = 'Fleurinpmodifier Tasks and inputs of these.'
        modifications.label = 'Fleurinpdata modifications'
        # This runs in a inline calculation to keep provenance
        inputs = {
            'original': self._original,
            'modifications': modifications,
            'metadata': {
                'label': 'fleurinp modifier',
                'description': 'This calcfunction modified an Fleurinpdataobject'
            },
            **self._other_nodes
        }
        out = modify_fleurinpdata(**inputs)  #type: ignore[arg-type]
        return out

    #Deactivate modify_xmlfile method from FleurXMLModifier (Only modify fleurinp)
    def modify_xmlfile(self, *args, **kwargs):  #pylint: disable=missing-function-docstring
        raise Exception(f'modify_xmlfile is disabled on {self.__class__.__name__}')  #pylint: disable=broad-exception-raised


@cf
def modify_fleurinpdata(original: FleurinpData, modifications: orm.Dict, **kwargs: orm.Node) -> FleurinpData:
    """
    A CalcFunction that performs the modification of the given FleurinpData and stores
    the result in a database.

    :param original: a FleurinpData to be modified
    :param modifications: a python dictionary of modifications in the form of {'task': ...}
    :param kwargs: dict of other aiida nodes to be linked to the modifications
    :returns new_fleurinp: a modified FleurinpData that is stored in a database
    """
    # copy
    # get schema
    # read in inp.xml
    # add modifications
    # validate
    # save inp.xml
    # store new fleurinp (copy)
    import tempfile
    from masci_tools.util.schema_dict_util import reverse_xinclude

    new_fleurinp = original.clone()

    modification_tasks = modifications.get_dict()['tasks']

    #We need to rebuild the namedtuples since the serialization for the calcufunction inputs
    #converts the namedtuples into lists
    modification_tasks = [ModifierTask(*task) for task in modification_tasks]

    FleurinpModifier.apply_fleurinp_modifications(new_fleurinp, modification_tasks)

    xmltree, schema_dict, included_tags = new_fleurinp.load_inpxml(remove_blank_text=True, return_included_tags=True)

    try:
        with new_fleurinp.open(path='n_mmp_mat', mode='r') as n_mmp_file:
            nmmplines = n_mmp_file.read().split('\n')
    except FileNotFoundError:
        nmmplines = None

    new_fleurtree, new_nmmplines = FleurinpModifier.apply_modifications(xmltree=xmltree,\
                                                                        nmmp_lines=nmmplines,\
                                                                        modification_tasks=modification_tasks,
                                                                        validate_changes=False)

    # To include object store storage this prob has to be done differently

    inpxmltree, includedtrees = reverse_xinclude(new_fleurtree, schema_dict, included_tags)

    new_fleurinp.del_file('inp.xml')
    with tempfile.TemporaryDirectory() as td:
        inpxml_path = os.path.join(td, 'inp.xml')
        inpxmltree.write(inpxml_path, encoding='utf-8', pretty_print=True)
        new_fleurinp.set_file(inpxml_path, 'inp.xml')

        for file_name, tree in includedtrees.items():
            file_path = os.path.join(td, file_name)
            tree.write(file_path, encoding='utf-8', pretty_print=True)
            new_fleurinp.set_file(file_path, file_name)

        if new_nmmplines is not None:
            n_mmp_path = os.path.join(td, 'n_mmp_mat')
            with open(n_mmp_path, 'w', encoding='utf-8') as n_mmp_file:
                n_mmp_file.write('\n'.join(new_nmmplines))
            new_fleurinp.set_file(n_mmp_path, 'n_mmp_mat')

    # default label and description
    new_fleurinp.label = 'mod_fleurinp'
    new_fleurinp.description = 'Fleurinpdata with modifications (see inputs of modify_fleurinpdata)'

    return new_fleurinp
