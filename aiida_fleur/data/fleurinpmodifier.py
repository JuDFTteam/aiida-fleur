# -*- coding: utf-8 -*-
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

from __future__ import absolute_import
from __future__ import print_function
import os

from lxml import etree

from aiida.plugins import DataFactory
from aiida.engine.processes.functions import calcfunction as cf
from aiida_fleur.data.fleurinp import FleurinpData


class FleurinpModifier(object):
    """
    A class which represents changes to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` object.
    """

    def __init__(self, original):
        """
        Initiation of FleurinpModifier.
        """
        assert isinstance(original, FleurinpData), "Wrong AiiDA data type"

        self._original = original
        self._tasks = []

    @staticmethod
    @cf
    def modify_fleurinpdata(original, modifications):
        """
        A CalcFunction that performs the modification of the given FleurinpData and stores
        the result in a database.

        :param original: a FleurinpData to be modified
        :param modifications: a python dictionary of modifications in the form of {'task': ...}

        :returns new_fleurinp: a modified FleurinpData that is stored in a database
        """

        # copy
        # get schema
        # read in inp.xml
        # add modifications
        # validate
        # save inp.xml
        # store new fleurinp (copy)
        from aiida_fleur.tools.xml_util import clear_xml

        new_fleurinp = original.clone()
        # TODO test if file is there!
        inpxmlfile = new_fleurinp.open(key='inp.xml')
        modification_tasks = modifications.get_dict()['tasks']

        xmlschema_doc = etree.parse(new_fleurinp._schema_file_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        parser = etree.XMLParser(attribute_defaults=True, remove_blank_text=True)

        tree = etree.parse(inpxmlfile, parser)

        if not xmlschema.validate(clear_xml(tree)):
            raise ValueError("Input file is not validated against the schema.")

        new_fleurtree = FleurinpModifier.apply_modifications(fleurinp_tree_copy=tree,
                                                             modification_tasks=modification_tasks)

        # To include object store storage this prob has to be done differently

        inpxmlfile_new = inpxmlfile.name.replace('inp.xml', 'temp_inp.xml')
        inpxmlfile.close()

        new_fleurtree.write(inpxmlfile_new, pretty_print=True)

        new_fleurinp.del_file('inp.xml')
        new_fleurinp._add_path(str(inpxmlfile_new), 'inp.xml')
        os.remove(inpxmlfile_new)

        # default label and description
        new_fleurinp.label = 'mod_fleurinp'
        new_fleurinp.description = ('Fleurinpdata with modifications'
                                    ' (see inputs of modify_fleurinpdata)')

        return new_fleurinp

    @staticmethod
    def apply_modifications(fleurinp_tree_copy, modification_tasks, schema_tree=None):
        """
        Applies given modifications to the fleurinp lxml tree.
        It also checks if a new lxml tree is validated against schema.
        Does not rise an error if inp.xml is not validated, simple prints a message about it.

        :param fleurinp_tree_copy: a fleurinp lxml tree to be modified
        :param modification_tasks: a list of modification tuples

        :returns: a modified fleurinp lxml tree
        """
        from aiida_fleur.tools.xml_util import xml_set_attribv_occ, xml_set_first_attribv
        from aiida_fleur.tools.xml_util import xml_set_all_attribv, xml_set_text
        from aiida_fleur.tools.xml_util import xml_set_text_occ, xml_set_all_text
        from aiida_fleur.tools.xml_util import create_tag, replace_tag, delete_tag
        from aiida_fleur.tools.xml_util import delete_att, set_species
        from aiida_fleur.tools.xml_util import change_atomgr_att, add_num_to_att
        from aiida_fleur.tools.xml_util import change_atomgr_att_label, set_species_label
        from aiida_fleur.tools.xml_util import set_inpchanges, set_nkpts, shift_value
        from aiida_fleur.tools.xml_util import clear_xml

        def xml_set_attribv_occ1(fleurinp_tree_copy, xpathn, attributename,
                                 attribv, occ=None, create=False):
            if occ is None:
                occ = [0]
            xml_set_attribv_occ(
                fleurinp_tree_copy,
                xpathn,
                attributename,
                attribv,
                occ=occ,
                create=create)
            return fleurinp_tree_copy

        def xml_set_first_attribv1(fleurinp_tree_copy, xpathn,
                                   attributename, attribv, create=False):
            xml_set_first_attribv(fleurinp_tree_copy, xpathn, attributename, attribv, create=create)
            return fleurinp_tree_copy

        def xml_set_all_attribv1(fleurinp_tree_copy, xpathn, attributename, attribv, create=False):
            xml_set_all_attribv(fleurinp_tree_copy, xpathn, attributename, attribv, create=create)
            return fleurinp_tree_copy

        def xml_set_text1(fleurinp_tree_copy, xpathn, text, create=False):
            xml_set_text(fleurinp_tree_copy, xpathn, text, create=create)
            return fleurinp_tree_copy

        def xml_set_text_occ1(fleurinp_tree_copy, xpathn, text, create=False, occ=0):
            xml_set_text_occ(fleurinp_tree_copy, xpathn, text, create=create, occ=occ)
            return fleurinp_tree_copy

        def xml_set_all_text1(fleurinp_tree_copy, xpathn, text, create=False):
            xml_set_all_text(fleurinp_tree_copy, xpathn, text, create=create)
            return fleurinp_tree_copy

        def create_tag1(fleurinp_tree_copy, xpath, newelement, create=False):
            fleurinp_tree_copy = create_tag(fleurinp_tree_copy, xpath, newelement, create=create)
            return fleurinp_tree_copy

        def delete_att1(fleurinp_tree_copy, xpath, attrib):
            fleurinp_tree_copy = delete_att(fleurinp_tree_copy, xpath, attrib)
            return fleurinp_tree_copy

        def delete_tag1(fleurinp_tree_copy, xpath):
            fleurinp_tree_copy = delete_tag(fleurinp_tree_copy, xpath)
            return fleurinp_tree_copy

        def replace_tag1(fleurinp_tree_copy, xpath, newelement):
            fleurinp_tree_copy = replace_tag(fleurinp_tree_copy, xpath, newelement)
            return fleurinp_tree_copy

        def set_species1(fleurinp_tree_copy, species_name, attributedict, create=False):
            fleurinp_tree_copy = set_species(
                fleurinp_tree_copy, species_name, attributedict, create=create)
            return fleurinp_tree_copy

        def set_species2(fleurinp_tree_copy, at_label, attributedict, create=False):
            fleurinp_tree_copy = set_species_label(
                fleurinp_tree_copy, at_label, attributedict, create=create)
            return fleurinp_tree_copy

        def change_atomgr_att1(fleurinp_tree_copy, attributedict,
                               position=None, species=None, create=False):
            fleurinp_tree_copy = change_atomgr_att(fleurinp_tree_copy,
                                                   attributedict,
                                                   position=position,
                                                   species=species)
            return fleurinp_tree_copy

        def change_atomgr_att2(fleurinp_tree_copy, attributedict,
                               atom_label, create=False):
            fleurinp_tree_copy = change_atomgr_att_label(fleurinp_tree_copy,
                                                         attributedict,
                                                         at_label=atom_label)
            return fleurinp_tree_copy

        def add_num_to_att1(fleurinp_tree_copy, xpathn, attributename,
                            set_val, mode='abs', occ=None):
            if occ is None:
                occ = [0]
            fleurinp_tree_copy = add_num_to_att(fleurinp_tree_copy,
                                                xpathn,
                                                attributename,
                                                set_val,
                                                mode=mode,
                                                occ=occ)
            return fleurinp_tree_copy

        def set_inpchanges1(fleurinp_tree_copy, change_dict):
            fleurinp_tree_copy = set_inpchanges(fleurinp_tree_copy, change_dict)
            return fleurinp_tree_copy

        def shift_value1(fleurinp_tree_copy, change_dict, mode):
            fleurinp_tree_copy = shift_value(fleurinp_tree_copy, change_dict, mode)
            return fleurinp_tree_copy

        def set_nkpts1(fleurinp_tree_copy, count, gamma):
            fleurinp_tree_copy = set_nkpts(fleurinp_tree_copy, count, gamma)
            return fleurinp_tree_copy

        actions = {
            'xml_set_attribv_occ': xml_set_attribv_occ1,
            'xml_set_first_attribv': xml_set_first_attribv1,
            'xml_set_all_attribv': xml_set_all_attribv1,
            'xml_set_text': xml_set_text1,
            'xml_set_text_occ': xml_set_text_occ1,
            'xml_set_all_text': xml_set_all_text1,
            'create_tag': create_tag1,
            'replace_tag': replace_tag1,
            'delete_tag': delete_tag1,
            'delete_att': delete_att1,
            'set_species': set_species1,
            'set_species_label': set_species2,
            'set_atomgr_att': change_atomgr_att1,
            'set_atomgr_att_label': change_atomgr_att2,
            'set_inpchanges': set_inpchanges1,
            'shift_value': shift_value1,
            'set_nkpts': set_nkpts1,
            'add_num_to_att': add_num_to_att1

        }

        workingtree = fleurinp_tree_copy
        if schema_tree:
            #xmlschema_doc = etree.parse(new_fleurinp._schema_file_path)
            xmlschema = etree.XMLSchema(schema_tree)

        for task in modification_tasks:
            try:
                action = actions[task[0]]
            except KeyError:
                raise ValueError("Unknown task {}".format(task[0]))

            workingtree = action(workingtree, *task[1:])

            if schema_tree:
                if not xmlschema.validate(clear_xml(workingtree)):
                    # TODO maybe even delete wrong task
                    #print('changes were not valid: {}({})'.format(task[0], task[1:]))
                    raise ValueError('changes were not valid: {}({})'.format(task[0], task[1:]))

        return workingtree

    def get_avail_actions(self):
        """
        Returns the allowed functions from FleurinpModifier
        """
        outside_actions = {
            'xml_set_attribv_occ': self.xml_set_attribv_occ,
            'xml_set_first_attribv': self.xml_set_first_attribv,
            'xml_set_all_attribv': self.xml_set_all_attribv,
            'xml_set_text': self.xml_set_text,
            'xml_set_text_occ': self.xml_set_text_occ,
            'xml_set_all_text': self.xml_set_all_text,
            'create_tag': self.create_tag,
            'replace_tag': self.replace_tag,
            'delete_tag': self.delete_tag,
            'delete_att': self.delete_att,
            'set_species': self.set_species,
            'set_species_label': self.set_species_label,
            'set_atomgr_att': self.set_atomgr_att,
            'set_atomgr_att_label': self.set_atomgr_att_label,
            'set_inpchanges': self.set_inpchanges,
            'shift_value': self.shift_value,
            'set_nkpts': self.set_nkpts,
            'add_num_to_att': self.add_num_to_att

        }
        return outside_actions

    def xml_set_attribv_occ(self, xpathn, attributename, attribv, occ=None, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.xml_set_attribv_occ()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute
        :param attributename: an attribute name
        :param attribv: an attribute value which will be set
        :param occ: a list of integers specifying number of occurrence to be set
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        """
        if occ is None:
            occ = [0]
        self._tasks.append(('xml_set_attribv_occ', xpathn, attributename, attribv, occ, create))

    def xml_set_first_attribv(self, xpathn, attributename, attribv, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.xml_set_first_attribv()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute
        :param attributename: an attribute name
        :param attribv: an attribute value which will be set
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        """
        self._tasks.append(('xml_set_first_attribv', xpathn, attributename, attribv, create))

    def xml_set_all_attribv(self, xpathn, attributename, attribv, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.xml_set_all_attribv()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute
        :param attributename: an attribute name
        :param attribv: an attribute value which will be set
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        """
        self._tasks.append(('xml_set_all_attribv', xpathn, attributename, attribv, create))

    def xml_set_text(self, xpathn, text, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.xml_set_text()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute
        :param text: text to be set
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        """
        self._tasks.append(('xml_set_text', xpathn, text, create))

    def xml_set_text_occ(self, xpathn, text, create=False, occ=0):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.xml_set_text_occ()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute
        :param text: text to be set
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        :param occ: an integer specifying number of occurrence to be set
        """
        self._tasks.append(('xml_set_text_occ', xpathn, text, create, occ))

    def xml_set_all_text(self, xpathn, text, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.xml_set_all_text()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute
        :param text: text to be set
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        """
        self._tasks.append(('xml_set_all_text', xpathn, text, create))

    def create_tag(self, xpath, newelement, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.create_tag()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path where to place a new tag
        :param newelement: a tag name to be created
        :param create: if True and there is no given xpath in the FleurinpData, creates it
        """
        self._tasks.append(('create_tag', xpath, newelement, create))

    def delete_att(self, xpath, attrib):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.delete_att()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the attribute to be deleted
        :param attrib: the name of an attribute
        """
        self._tasks.append(('delete_att', xpath, attrib))

    def delete_tag(self, xpath):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.delete_tag()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the tag to be deleted
        """
        self._tasks.append(('delete_tag', xpath))

    def replace_tag(self, xpath, newelement):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.replace_tag()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: a path to the tag to be replaced
        :param newelement: a new tag
        """
        self._tasks.append(('replace_tag', xpath, newelement))

    def set_species(self, species_name, attributedict, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.set_species()` to
        the list of tasks that will be done on the FleurinpData.

        :param species_name: a path to the tag to be replaced
        :param attributedict: attribute dictionary to be set into the specie
        :param create: if True and there is no given specie in the FleurinpData, creates it
        """
        self._tasks.append(('set_species', species_name, attributedict, create))

    def set_species_label(self, at_label, attributedict, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.set_species_label()` to
        the list of tasks that will be done on the FleurinpData.

        :param at_label: Atom label which specie will be set
        :param attributedict: attribute dictionary to be set into the specie
        :param create: if True and there is no given specie in the FleurinpData, creates it
        """
        self._tasks.append(('set_species_label', at_label, attributedict, create))

    def set_atomgr_att(self, attributedict, position=None, species=None, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.change_atomgr_att()` to
        the list of tasks that will be done on the FleurinpData.

        :param species_name: a path to the tag to be replaced
        :param attributedict: attribute dictionary to be set into the atom group
        :param create: if True and there is no given atom group in the FleurinpData, creates it
        """
        self._tasks.append(('set_atomgr_att', attributedict, position, species, create))

    def set_atomgr_att_label(self, attributedict, atom_label, create=False):
        """
        Appends a :func:`~aiida_fleur.tools.xml_util.change_atomgr_att_label()` to
        the list of tasks that will be done on the FleurinpData.

        :param attributedict: a new tag
        :param atom_label: Atom label which atom group will be set
        :param create: if True and there is no given atom group in the FleurinpData, creates it
        """
        self._tasks.append(('set_atomgr_att_label', attributedict, atom_label, create))

    def set_inpchanges(self, change_dict):
        """
        Appends a :py:func:`~aiida_fleur.tools.xml_util.set_inpchanges()` to
        the list of tasks that will be done on the FleurinpData.

        :param change_dict: a dictionary with changes

        An example of change_dict::

            change_dict = {'itmax' : 1,
                           'l_noco': True,
                           'ctail': False,
                           'l_ss': True}
        """
        self._tasks.append(('set_inpchanges', change_dict))

    def shift_value(self, change_dict, mode='abs'):
        """
        Appends a :py:func:`~aiida_fleur.tools.xml_util.shift_value()` to
        the list of tasks that will be done on the FleurinpData.

        :param change_dict: a dictionary with changes
        :param mode: 'abs' if change given is absolute, 'rel' if relative

        An example of change_dict::

            change_dict = {'itmax' : 1, dVac = -2}
        """
        self._tasks.append(('shift_value', change_dict, mode))

    def set_nkpts(self, count, gamma='F'):
        """
        Appends a :py:func:`~aiida_fleur.tools.xml_util.set_nkpts()` to
        the list of tasks that will be done on the FleurinpData.
        """
        self._tasks.append(('set_nkpts', count, gamma))

    def add_num_to_att(self, xpathn, attributename, set_val, mode='abs', occ=None):
        """
        Appends a :py:func:`~aiida_fleur.tools.xml_util.add_num_to_att()` to
        the list of tasks that will be done on the FleurinpData.

        :param xpathn: an xml path to the attribute to change
        :param attributename: a name of the attribute to change
        :param set_val: a value to be added/multiplied to the previous value
        :param mode: 'abs' if to add set_val, 'rel' if multiply
        :param occ: a list of integers specifying number of occurrence to be set
        """
        if occ is None:
            occ = [0]
        self._tasks.append(('add_num_to_att', xpathn, attributename, set_val, mode, occ))

    def validate(self):
        """
        Extracts the schema-file.
        Makes a test if all the changes lead to an inp.xml file that is validated against the
        schema.

        :return: a lxml tree representing inp.xml with applied changes
        """
        with self._original.open(key='inp.xml') as inpxmlfile:
            tree = etree.parse(inpxmlfile)

        try:  # could be not found or on another computer...
            xmlschema_tree = etree.parse(self._original._schema_file_path)
            with_schema = True
        except BaseException:
            with_schema = False
            print('No schema file found')
            return
        if with_schema:
            tree = self.apply_modifications(tree, self._tasks, schema_tree=xmlschema_tree)
        return tree

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
            tree = self.validate()
        else:
            with self._original.open(key='inp.xml') as inpxmlfile:
                tree = etree.parse(inpxmlfile)
            tree = self.apply_modifications(tree, self._tasks)

        if display:
            xmltreestring = etree.tostring(tree, xml_declaration=True, pretty_print=True)
            print(xmltreestring)
        return tree

    def changes(self):
        """
        Prints out all changes given in a
        :class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` instance.
        """
        from pprint import pprint
        pprint(self._tasks)
        return self._tasks

    def freeze(self):
        """
        This method applies all the modifications to the input and
        returns a new stored fleurinpData object.

        :return: stored :class:`~aiida_fleur.data.fleurinp.FleurinpData` with applied changes
        """
        modifications = DataFactory("dict")(dict={"tasks": self._tasks})
        modifications.description = 'Fleurinpmodifier Tasks and inputs of these.'
        modifications.label = 'Fleurinpdata modifications'
        # This runs in a inline calculation to keep provenance
        out = self.modify_fleurinpdata(
            original=self._original,
            modifications=modifications,
            metadata={'label': 'fleurinp modifier',
                      'description': 'This calcfunction modified an Fleurinpdataobject'})
        return out

    def undo(self, all=False):
        """
        Cancels the last change or all of them

        :param all: set True if need to cancel all the changes, False if the last one.
        """
        if all:
            self._tasks = []
        else:
            if self._tasks:
                self._tasks.pop()
                #del self._tasks[-1]
        return self._tasks
