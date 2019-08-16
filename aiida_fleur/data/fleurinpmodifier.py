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
import copy

from lxml import etree

from aiida.plugins import DataFactory
from aiida.engine.processes.functions import calcfunction as cf

FleurinpData = DataFactory('fleur.fleurinp')


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

        new_fleurinp = original.clone()
        # TODO test if file is there!
        inpxmlfile = new_fleurinp.open(key='inp.xml')
        modification_tasks = modifications.get_dict()['tasks']

        xmlschema_doc = etree.parse(new_fleurinp._schema_file_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        parser = etree.XMLParser(attribute_defaults=True, remove_comments=True)

        tree = etree.parse(inpxmlfile, parser)
        tree_x = copy.deepcopy(tree)

        # replace XInclude parts to validate against schema
        tree_x.xinclude()
        if not xmlschema.validate(tree_x):
            raise ValueError("Input file is not validated against the schema.")

        new_fleurtree = FleurinpModifier.apply_modifications(fleurinp_tree_copy=tree,
                                                             modification_tasks=modification_tasks)

        # To include object store storage this prob has to be done differently

        inpxmlfile_new = inpxmlfile.name.replace('inp.xml', 'temp_inp.xml')
        inpxmlfile.close()

        new_fleurtree.write(inpxmlfile_new)

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
            fleurinp_tree_copy = change_atomgr_att(
                                                   fleurinp_tree_copy,
                                                   attributedict,
                                                   position=position,
                                                   species=species,
                                                   create=create)
            return fleurinp_tree_copy

        def change_atomgr_att2(fleurinp_tree_copy, attributedict,
                               atom_label, create=False):
            fleurinp_tree_copy = change_atomgr_att_label(
                                                        fleurinp_tree_copy,
                                                        attributedict,
                                                        at_label=atom_label,
                                                        create=create)
            return fleurinp_tree_copy

        def add_num_to_att1(fleurinp_tree_copy, xpathn, attributename,
                            set_val, mode='abs', occ=None, create=False):
            if occ is None:
                occ = [0]
            fleurinp_tree_copy = add_num_to_att(
                                                fleurinp_tree_copy,
                                                xpathn,
                                                attributename,
                                                set_val,
                                                mode=mode,
                                                occ=occ,
                                                create=create)
            return fleurinp_tree_copy

        def set_inpchanges1(fleurinp_tree_copy, change_dict):
            """
            Makes given changes directly in the inp.xml file. Afterwards
            updates the inp.xml file representation and the current inp_userchanges
            dictionary with the keys provided in the 'change_dict' dictionary.

            :param fleurinp_tree_copy: a lxml tree that represents inp.xml
            :param change_dict: a python dictionary with the keys to substitute.
                                It works like dict.update(), adding new keys and
                                overwriting existing keys.
            
            :returns new_tree: a lxml tree with applied changes
            """
            from aiida_fleur.tools.xml_util import write_new_fleur_xmlinp_file
            from aiida_fleur.tools.xml_util import get_inpxml_file_structure

            # TODO if we still want tracking that way, have to get fleurinp in argument
            '''
            if self.inp_userchanges is None:
                self._set_attr('inp_userchanges', {})

            # store change dict, to trace changes
            currentchangedict = self.inp_userchanges
            currentchangedict.update(change_dict)
            self._set_attr('inp_userchanges', currentchangedict)

            # load file, if it does not exist error will be thrown in routine
            inpxmlfile = self.get_file_abs_path('inp.xml')

            if self._has_schema:
               #schema file for validation will be loaded later
               pass
            elif self._schema_file_path != None:
                print('Warning: The User set the XMLSchema file path manually, your'
                      'inp.xml will be evaluated! If it fails it is your own fault!')
            else:
                print('Warning: No XMLSchema file was provided, your inp.xml file '
                      'will not be evaluated and parsed! (I should never get here)')

            #read in tree
            tree = etree.parse(inpxmlfile)
            '''
            tree = fleurinp_tree_copy
            # apply changes to etree
            xmlinpstructure = get_inpxml_file_structure()
            new_tree = write_new_fleur_xmlinp_file(tree, change_dict, xmlinpstructure)

            return new_tree

        def set_nkpts1(fleurinp_tree_copy, count, gamma):
            """
            Sets a k-point mesh directly into inp.xml

            :param fleurinp_tree_copy: a lxml tree that represents inp.xml
            :param count: number of k-points
            :param gamma: a fortran-type boolen that controls if the gamma-point should be included
                          in the k-point mesh

            :returns new_tree: a lxml tree with applied changes
            """

            kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList'
            #kpoint_xpath = '/fleurInput/calculationSetup/bzIntegration/kPoint*'

            tree = fleurinp_tree_copy
            new_kpo = etree.Element(
                'kPointCount',
                count="{}".format(count),
                gamma="{}".format(gamma))
            new_tree = replace_tag(tree, kpointlist_xpath, new_kpo)

            return new_tree

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

        workingtree_x = copy.deepcopy(workingtree)
        workingtree_x.xinclude()
        if schema_tree:
            if not xmlschema.validate(workingtree_x):
                # TODO maybe even delete wrong task
                print('changes were not valid: {}')
                #raise ValueError('change not valid: {}'.format(task[1:]))

        return workingtree

    def get_avail_actions(self):
        """
        Returns the allowed functions from fleurinpmod
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
            'set_nkpts': self.set_nkpts,
            'add_num_to_att': self.add_num_to_att

        }
        return outside_actions

    def xml_set_attribv_occ(self, xpathn, attributename, attribv, occ=None, create=False):
        if occ is None:
            occ = [0]
        self._tasks.append(('xml_set_attribv_occ', xpathn, attributename, attribv, occ, create))

    def xml_set_first_attribv(self, xpathn, attributename, attribv, create=False):
        self._tasks.append(('xml_set_first_attribv', xpathn, attributename, attribv, create))

    def xml_set_all_attribv(self, xpathn, attributename, attribv, create=False):
        self._tasks.append(('xml_set_all_attribv', xpathn, attributename, attribv, create))

    def xml_set_text(self, xpathn, text, create=False):
        self._tasks.append(('xml_set_text', xpathn, text, create))

    def xml_set_text_occ(self, xpathn, text, create=False, occ=0):
        self._tasks.append(('xml_set_text_occ', xpathn, text, create, occ))

    def xml_set_all_text(self, xpathn, text, create=False):
        self._tasks.append(('xml_set_all_text', xpathn, text, create))

    def create_tag(self, xpath, newelement, create=False):
        self._tasks.append(('create_tag', xpath, newelement, create))

    def delete_att(self, xpath, attrib):
        self._tasks.append(('delete_att', xpath, attrib))

    def delete_tag(self, xpath):
        self._tasks.append(('delete_tag', xpath))

    def replace_tag(self, xpath, newelement):
        self._tasks.append(('replace_tag', xpath, newelement))

    def set_species(self, species_name, attributedict, create=False):
        self._tasks.append(('set_species', species_name, attributedict, create))

    def set_species_label(self, at_label, attributedict, create=False):
        self._tasks.append(('set_species_label', at_label, attributedict, create))

    def set_atomgr_att(self, attributedict, position=None, species=None, create=False):
        self._tasks.append(('set_atomgr_att', attributedict, position, species, create))

    def set_atomgr_att_label(self, attributedict, atom_label, create=False):
        self._tasks.append(('set_atomgr_att_label', attributedict, atom_label, create))

    def set_inpchanges(self, change_dict):
        self._tasks.append(('set_inpchanges', change_dict))

    def set_nkpts(self, count, gamma='F'):
        self._tasks.append(('set_nkpts', count, gamma))

    def add_num_to_att(self, xpathn, attributename, set_val, mode='abs', occ=None, create=False):
        if occ is None:
            occ = [0]
        self._tasks.append(('add_num_to_att', xpathn, attributename, set_val, mode, occ, create))

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
