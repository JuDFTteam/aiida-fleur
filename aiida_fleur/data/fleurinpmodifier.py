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
import os
from lxml import etree
import warnings

from aiida.engine.processes.functions import calcfunction as cf
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.tools.xml_aiida_modifiers import set_kpointsdata_f

from masci_tools.io.fleurxmlmodifier import ModifierTask, FleurXMLModifier


class FleurinpModifier(FleurXMLModifier):
    """
    A class which represents changes to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` object.
    """

    _extra_functions = {'schema_dict': {'set_kpointsdata': set_kpointsdata_f}}

    def __init__(self, original):
        """
        Initiation of FleurinpModifier.
        """
        assert isinstance(original, FleurinpData), 'Wrong AiiDA data type'

        self._original = original
        self._other_nodes = {}

        super().__init__()

    @classmethod
    def apply_fleurinp_modifications(cls, new_fleurinp, modification_tasks):
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
        for task in modification_tasks:
            if task.name in fleurinp_mod_functions:
                modification_tasks.remove(task)
                action = fleurinp_mod_functions[task.name]
                action(*task.args, **task.kwargs)
                if warn:
                    warnings.warn('The modification methods operating directly adding/removing files '
                                  'are performed before any XML modification methods')
            else:
                warn = True

    def get_avail_actions(self):
        """
        Returns the allowed functions from FleurinpModifier
        """
        outside_actions_fleurinp = {
            'set_kpointsdata': self.set_kpointsdata,
            'set_atomgr_att': self.set_atomgr_att,
            'set_atomgr_att_label': self.set_atomgr_att_label,
            'xml_set_attribv_occ': self.xml_set_attribv_occ,
            'xml_set_first_attribv': self.xml_set_first_attribv,
            'xml_set_all_attribv': self.xml_set_all_attribv,
            'xml_set_text_occ': self.xml_set_text_occ,
            'xml_set_text': self.xml_set_text,
            'xml_set_all_text': self.xml_set_all_text,
            'add_num_to_att': self.add_num_to_att,
            'set_file': self.set_file,
            'del_file': self.del_file
        }

        outside_actions_fleurxml = super().get_avail_actions().copy()

        return {**outside_actions_fleurxml, **outside_actions_fleurinp}

    def set_kpointsdata(self, kpointsdata_uuid, name=None, switch=False, kpoint_type='path'):
        """
        Appends a :py:func:`~aiida_fleur.tools.xml_aiida_modifiers.set_kpointsdata_f()` to
        the list of tasks that will be done on the FleurinpData.

        :param kpointsdata_uuid: node identifier or :class:`~aiida.orm.KpointsData` node to be written into ``inp.xml``
        :param name: str name to give the newly entered kpoint list (only MaX5 or later)
        :param switch: bool if True the entered kpoint list will be used directly (only Max5 or later)
        :param kpoint_type: str of the type of kpoint list given (mesh, path, etc.) only Max5 or later
        """
        from aiida.orm import KpointsData, load_node

        if isinstance(kpointsdata_uuid, KpointsData):
            kpointsdata_uuid = kpointsdata_uuid.uuid
        # Be more careful? Needs to be stored, otherwise we cannot load it

        num_nodes = sum('kpoints' in label for label in self._other_nodes) + 1
        node_label = f'kpoints_{num_nodes}'

        self._other_nodes[node_label] = load_node(kpointsdata_uuid)
        self._tasks.append(
            ModifierTask('set_kpointsdata',
                         args=(kpointsdata_uuid,),
                         kwargs={
                             'name': name,
                             'switch': switch,
                             'kpoint_type': kpoint_type
                         }))

    #Modification functions that were renamed in masci-tools

    def shift_value_species_label(self, *args, **kwargs):
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_names.shift_value_species_label()` to
        the list of tasks that will be done on the xmltree.

        :param atom_label: string, a label of the atom which specie will be changed. 'all' if set up all species
        :param attributename: name of the attribute to change
        :param value_given: value to add or to multiply by
        :param mode: 'rel' for multiplication or 'abs' for addition

        Kwargs if the attributename does not correspond to a unique path:
            :param contains: str, this string has to be in the final path
            :param not_contains: str, this string has to NOT be in the final path

        """
        if 'label' in kwargs:
            warnings.warn("The argument label is deprecated. Use 'atom_label' instead", DeprecationWarning)
            kwargs['atom_label'] = kwargs.pop('label')

        if 'att_name' in kwargs:
            warnings.warn("The argument att_name is deprecated. Use 'attributename' instead", DeprecationWarning)
            kwargs['attributename'] = kwargs.pop('att_name')

        if 'value' in kwargs:
            warnings.warn("The argument value is deprecated. Use 'value_given' instead", DeprecationWarning)
            kwargs['value_given'] = kwargs.pop('value')

        super().shift_value_species_label(*args, **kwargs)

    def set_species_label(self, *args, **kwargs):
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_names.set_species_label()` to
        the list of tasks that will be done on the xmltree.

        :param atom_label: string, a label of the atom which specie will be changed. 'all' to change all the species
        :param attributedict: a python dict specifying what you want to change.

        """
        if 'at_label' in kwargs:
            warnings.warn("The argument at_label is deprecated. Use 'atom_label' instead", DeprecationWarning)
            kwargs['atom_label'] = kwargs.pop('at_label')

        super().set_species_label(*args, **kwargs)

    def set_atomgr_att(self, *args, **kwargs):
        """
        Deprecated method for setting attributes on atomgroups
        """
        warnings.warn('This modification method is deprecated.'
                      "Use the 'set_atomgroup' method instead", DeprecationWarning)

        self.set_atomgroup(*args, **kwargs)

    def set_atomgr_att_label(self, *args, **kwargs):
        """
        Deprecated method for setting attributes on atomgroups identified by an atom label
        """
        warnings.warn('This modification method is deprecated.'
                      "Use the 'set_atomgroup_label' method instead", DeprecationWarning)

        if 'atom_label' not in kwargs:
            if len(args) == 2:
                kwargs['atom_label'], args = args[1], args[:1]
            elif len(args) > 2:
                kwargs['atom_label'], args = args[1], args[:1] + args[2:]

        self.set_atomgroup_label(*args, **kwargs)

    def xml_set_attribv_occ(self, *args, **kwargs):
        """
        Deprecated method for setting attributes for occurrences on a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'xml_set_attrib_value_no_create' or"
            "'set_attrib_value' method instead", DeprecationWarning)

        if 'xpathn' in kwargs:
            kwargs['xpath'] = kwargs.pop('xpathn')

        occ = kwargs.pop('occ', None)
        kwargs.pop('create', None)

        self.xml_set_attrib_value_no_create(*args, **kwargs, occurrences=occ)

    def xml_set_first_attribv(self, *args, **kwargs):
        """
        Deprecated method for setting the first attribute on a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'xml_set_first_attrib_value_no_create' with 'occurrences=0' or"
            "'set_first_attrib_value' method instead", DeprecationWarning)

        if 'xpathn' in kwargs:
            kwargs['xpath'] = kwargs.pop('xpathn')
        kwargs.pop('create', None)

        self.xml_set_attrib_value_no_create(*args, occurrences=0, **kwargs)

    def xml_set_all_attribv(self, *args, **kwargs):
        """
        Deprecated method for setting all attributes on a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'xml_set_attrib_value_no_create' or"
            "'set_attrib_value' method instead", DeprecationWarning)

        if 'xpathn' in kwargs:
            kwargs['xpath'] = kwargs.pop('xpathn')
        kwargs.pop('create', None)

        self.xml_set_attrib_value_no_create(*args, **kwargs)

    def xml_set_text_occ(self, *args, **kwargs):
        """
        Deprecated method for setting texts for occurrences on a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'xml_set_text_no_create' or"
            "'set_text' method instead", DeprecationWarning)

        if 'xpathn' in kwargs:
            kwargs['xpath'] = kwargs.pop('xpathn')
        occ = kwargs.pop('occ', None)
        kwargs.pop('create', None)
        kwargs.pop('place_index', None)
        kwargs.pop('tag_order', None)

        self.xml_set_text_no_create(*args, **kwargs, occurrences=occ)

    def xml_set_text(self, *args, **kwargs):
        """
        Deprecated method for setting attributes for occurrences on a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'xml_set_text_no_create' with 'occurrences=0' or"
            "'set_first_text' method instead", DeprecationWarning)

        if 'xpathn' in kwargs:
            kwargs['xpath'] = kwargs.pop('xpathn')
        kwargs.pop('create', None)
        kwargs.pop('place_index', None)
        kwargs.pop('tag_order', None)

        self.xml_set_text_no_create(*args, occurrences=0, **kwargs)

    def xml_set_all_text(self, *args, **kwargs):
        """
        Deprecated method for setting attributes for occurrences on a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'xml_set_text_no_create' or"
            "'set_text' method instead", DeprecationWarning)

        if 'xpathn' in kwargs:
            kwargs['xpath'] = kwargs.pop('xpathn')
        kwargs.pop('create', None)
        kwargs.pop('place_index', None)
        kwargs.pop('tag_order', None)

        self.xml_set_text_no_create(*args, **kwargs)

    def xml_create_tag(self, *args, **kwargs):
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
        self._validate_signature('xml_create_tag', *args, **kwargs)

        if 'element' in kwargs:
            element = kwargs
        else:
            element = args[1]

        if etree.iselement(element):
            warnings.warn('Creating a tag from a given etree Element is only supported via the show()'
                          'and validate() methods on the Fleurinpmodifier and cannot be used with freeze()')

        super().xml_create_tag(*args, **kwargs)

    def create_tag(self, *args, **kwargs):
        """
        Deprecation layer for create_tag if there are slashes in the first positional argument or xpath is is in kwargs.
        We know that it is the old usage.

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

        old_interface = 'xpath' in kwargs
        if args:
            old_interface = old_interface or '/' in args[0]

        if old_interface:
            warnings.warn(
                "The 'create_tag' method no longer requires an explicit xpath. "
                'This Usage is deprecated. '
                "Use the 'xml_create_tag' method instead or only pass in the name of the tag, you want to use",
                DeprecationWarning)

            if 'xpath' in kwargs:
                xpath = kwargs.pop('xpath')
            else:
                xpath, args = args[0], args[1:]

            if 'newelement' in kwargs:
                element = kwargs.pop('newelement')
            else:
                element, args = args[0], args[1:]

            self.xml_create_tag(xpath, element, *args, **kwargs)
        else:
            tag = kwargs.get('tag')
            if tag is None:
                tag = args[0]

            if etree.iselement(tag):
                warnings.warn('Creating a tag from a given etree Element is only supported via the show()'
                              'and validate() methods on the Fleurinpmodifier and cannot be used with freeze()')

            super().create_tag(*args, **kwargs)

    def delete_tag(self, *args, **kwargs):
        """
        Deprecation layer for delete_tag if there are slashes in the first positional argument or xpath is is in kwargs.
        We know that it is the old usage.

        Appends a :py:func:`~masci_tools.util.xml.xml_setters_names.delete_tag()` to
        the list of tasks that will be done on the xmltree.

        :param tag: str of the tag to delete
        :param complex_xpath: an optional xpath to use instead of the simple xpath for the evaluation
        :param occurrences: int or list of int. Which occurence of the parent nodes to delete a tag.
                            By default all nodes are used.

        Kwargs:
            :param contains: str, this string has to be in the final path
            :param not_contains: str, this string has to NOT be in the final path
        """

        old_interface = 'xpath' in kwargs
        if args:
            old_interface = old_interface or '/' in args[0]

        if old_interface:
            warnings.warn(
                "The 'delete_tag' method no longer requires an explicit xpath. "
                'This Usage is deprecated. '
                "Use the 'xml_delete_tag' method instead or only pass in the name of the tag, you want to use",
                DeprecationWarning)

            if 'xpath' in kwargs:
                xpath = kwargs.pop('xpath')
            else:
                xpath, args = args[0], args[1:]

            self.xml_delete_tag(xpath, *args, **kwargs)
        else:
            super().delete_tag(*args, **kwargs)

    def delete_att(self, *args, **kwargs):
        """
        Deprecation layer for delete_att if there are slashes in the first positional argument or xpath is is in kwargs.
        We know that it is the old usage.

        Appends a :py:func:`~masci_tools.util.xml.xml_setters_names.delete_att()` to
        the list of tasks that will be done on the xmltree.

        :param tag: str of the attribute to delete
        :param complex_xpath: an optional xpath to use instead of the simple xpath for the evaluation
        :param occurrences: int or list of int. Which occurence of the parent nodes to delete a attribute.
                            By default all nodes are used.

        Kwargs:
            :param tag_name: str, name of the tag where the attribute should be parsed
            :param contains: str, this string has to be in the final path
            :param not_contains: str, this string has to NOT be in the final path
            :param exclude: list of str, here specific types of attributes can be excluded
                            valid values are: settable, settable_contains, other
        """

        old_interface = 'xpath' in kwargs
        if args:
            old_interface = old_interface or '/' in args[0]

        if old_interface:
            warnings.warn(
                "The 'delete_att' method no longer requires an explicit xpath. "
                'This Usage is deprecated. '
                "Use the 'xml_delete_att' method instead or only pass in the name of the attribute, you want to use",
                DeprecationWarning)

            if 'xpath' in kwargs:
                xpath = kwargs.pop('xpath')
            else:
                xpath, args = args[0], args[1:]

            self.xml_delete_att(xpath, *args, **kwargs)
        else:
            super().delete_att(*args, **kwargs)

    def xml_replace_tag(self, *args, **kwargs):
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_basic.xml_replace_tag()` to
        the list of tasks that will be done on the xmltree.

        :param xpath: a path to the tag to be replaced
        :param newelement: a new tag
        :param occurrences: int or list of int. Which occurence of the parent nodes to create a tag.
                            By default all nodes are used.
        """
        self._validate_signature('xml_replace_tag', *args, **kwargs)

        warnings.warn('Creating a tag from a given etree Element is only supported via the show()'
                      'and validate() methods on the Fleurinpmodifier and cannot be used with freeze()')

        super().xml_replace_tag(*args, **kwargs)

    def replace_tag(self, *args, **kwargs):
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

        warnings.warn('Replacing a tag with a given etree Element is only supported via the show()'
                      'and validate() methods on the Fleurinpmodifier and cannot be used with freeze()')

        old_interface = 'xpath' in kwargs
        if args:
            old_interface = old_interface or '/' in args[0]

        if old_interface:
            warnings.warn(
                "The 'delete_att' method no longer requires an explicit xpath. "
                'This Usage is deprecated. '
                "Use the 'xml_delete_att' method instead or only pass in the name of the attribute, you want to use",
                DeprecationWarning)

            if 'xpath' in kwargs:
                xpath = kwargs.pop('xpath')
            else:
                xpath, args = args[0], args[1:]

            self.xml_replace_tag(xpath, *args, **kwargs)
        else:
            super().replace_tag(*args, **kwargs)

    def add_num_to_att(self, *args, **kwargs):
        """
        Deprecated method for adding a number to a attribute at a specific xpath
        """

        warnings.warn(
            'This modification method is deprecated.'
            "Use the 'add_number_to_attrib' or 'add_number_to_first_attrib' method instead", DeprecationWarning)

        #Since the new method takes only an attribute we extract the xpath and pass it in as complex_xpath

        if len(args) == 0:
            xpath = kwargs.pop('xpathn')
        else:
            xpath, args = args[0], args[1:]

        if 'occ' not in kwargs:
            self.add_number_to_first_attrib(*args, **kwargs, complex_xpath=xpath)
        else:
            occ = kwargs.pop('occ')
            self.add_number_to_attrib(*args, **kwargs, complex_xpath=xpath, occurrences=occ)

    def set_nmmpmat(self, *args, **kwargs):
        """
        Appends a :py:func:`~masci_tools.util.xml.xml_setters_nmmpmat.set_nmmpmat()` to
        the list of tasks that will be done on the xmltree.

        :param species_name: string, name of the species you want to change
        :param orbital: integer, orbital quantum number of the LDA+U procedure to be modified
        :param spin: integer, specifies which spin block should be modified
        :param state_occupations: list, sets the diagonal elements of the density matrix and everything
                          else to zero
        :param denmat: matrix, specify the density matrix explicitely
        :param phi: float, optional angle (radian), by which to rotate the density matrix before writing it
        :param theta: float, optional angle (radian), by which to rotate the density matrix before writing it
        """

        if 'occStates' in kwargs:
            warnings.warn("The argument occStates is deprecated. Use 'state_occupations' instead", DeprecationWarning)
            kwargs['state_occupations'] = kwargs.pop('occStates')

        super().set_nmmpmat(*args, **kwargs)

    def set_file(self, filename, dst_filename=None, node=None):
        """
        Appends a :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.set_file()` to
        the list of tasks that will be done on the FleurinpData instance.

        :param filename: absolute path to the file or a filename of node is specified
        :param dst_filename: str of the filename, which should be used instead of the real filename
                             to store it
        :param node: a :class:`~aiida.orm.FolderData` node containing the file
        """
        from aiida.orm import load_node, Data

        node_uuid = None
        if node is not None:
            if isinstance(node, Data):
                node_uuid = node.uuid
            num_nodes = sum('folder' in label for label in self._other_nodes) + 1
            node_label = f'folder_{num_nodes}'
            # Be more careful? Needs to be stored, otherwise we cannot load it
            self._other_nodes[node_label] = load_node(node_uuid)

        self._tasks.append(
            ModifierTask('set_file', args=(filename,), kwargs={
                'dst_filename': dst_filename,
                'node': node_uuid
            }))

    def del_file(self, filename):
        """
        Appends a :py:func:`~aiida_fleur.data.fleurinp.FleurinpData.del_file()` to
        the list of tasks that will be done on the FleurinpData instance.

        :param filename: name of the file to be removed from FleurinpData instance
        """
        self._tasks.append(ModifierTask('del_file', args=(filename,), kwargs={}))

    def validate(self):
        """
        Extracts the schema-file.
        Makes a test if all the changes lead to an inp.xml file that is validated against the
        schema.

        :return: a lxml tree representing inp.xml with applied changes
        """

        new_fleurinp = self._original.clone()
        self.apply_fleurinp_modifications(new_fleurinp, self._tasks)

        xmltree, schema_dict = new_fleurinp.load_inpxml(remove_blank_text=True)
        develop_version = new_fleurinp.inp_version != schema_dict['inp_version']

        try:
            with new_fleurinp.open(path='n_mmp_mat', mode='r') as n_mmp_file:
                nmmplines = n_mmp_file.read().split('\n')
        except FileNotFoundError:
            nmmplines = None

        try:
            xmltree, nmmp = super().apply_modifications(xmltree, nmmplines, self._tasks)
        except etree.DocumentInvalid as exc:
            if not develop_version:
                raise
            else:
                new_fleurinp.logger.warning(f'Ignoring validation errors for modifications of develop version: \n{exc}')

        return xmltree

    def show(self, display=True, validate=False):
        """
        Applies the modifications and displays/prints the resulting ``inp.xml`` file.
        Does not generate a new
        :class:`~aiida_fleur.data.fleurinp.FleurinpData` object.

        :param display: a boolean that is True if resulting ``inp.xml`` has to be printed out
        :param validate: a boolean that is True if changes have to be validated

        :return: a lxml tree representing inp.xml with applied changes
        """

        if validate:
            xmltree = self.validate()
        else:
            new_fleurinp = self._original.clone()
            self.apply_fleurinp_modifications(new_fleurinp, self._tasks)

            xmltree, schema_dict = new_fleurinp.load_inpxml(remove_blank_text=True)
            try:
                with new_fleurinp.open(path='n_mmp_mat', mode='r') as n_mmp_file:
                    nmmplines = n_mmp_file.read().split('\n')
            except FileNotFoundError:
                nmmplines = None

            xmltree, nmmp = super().apply_modifications(xmltree, nmmplines, self._tasks, validate_changes=False)

        if display:
            xmltreestring = etree.tostring(xmltree, encoding='unicode', pretty_print=True)
            print(xmltreestring)
        return xmltree

    def freeze(self):
        """
        This method applies all the modifications to the input and
        returns a new stored fleurinpData object.

        :return: stored :class:`~aiida_fleur.data.fleurinp.FleurinpData` with applied changes
        """
        from aiida.orm import Dict
        modifications = Dict(dict={'tasks': self._tasks})
        modifications.description = 'Fleurinpmodifier Tasks and inputs of these.'
        modifications.label = 'Fleurinpdata modifications'
        # This runs in a inline calculation to keep provenance
        inputs = dict(original=self._original,
                      modifications=modifications,
                      metadata={
                          'label': 'fleurinp modifier',
                          'description': 'This calcfunction modified an Fleurinpdataobject'
                      },
                      **self._other_nodes)
        out = modify_fleurinpdata(**inputs)
        return out

    #Deactivate modify_xmlfile method from FleurXMLModifier (Only modify fleurinp)
    def modify_xmlfile(self, *args, **kwargs):  #pylint: disable=missing-function-docstring
        raise Exception(f'modify_xmlfile is disabled on {self.__class__.__name__}')


@cf
def modify_fleurinpdata(original, modifications, **kwargs):
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
            with open(n_mmp_path, 'w') as n_mmp_file:
                n_mmp_file.write('\n'.join(new_nmmplines))
            new_fleurinp.set_file(n_mmp_path, 'n_mmp_mat')

    # default label and description
    new_fleurinp.label = 'mod_fleurinp'
    new_fleurinp.description = 'Fleurinpdata with modifications (see inputs of modify_fleurinpdata)'

    return new_fleurinp
