# -*- coding: utf-8 -*-
"""
In this module is the FleurinpData class, and useful methods for FLEUR input
manipulation.
"""

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"
 # TODO implement undo
import os
import re
from lxml import etree
from lxml.etree import XMLSyntaxError
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import DataFactory
#from aiida.workflows2.wf import wf
from aiida.work.workfunction import workfunction as wf


class FleurinpModifier(object):

    def __init__(self, original):
        assert isinstance(original, DataFactory("fleurinp.fleurinp")), "Wrong AiiDA data type"
        
        self._original = original
        self._tasks = []

    @staticmethod
    @wf
    def modify_fleurinpdata(original, modifications):
        """
        WF, original must be a fleurinp data, modifications a fleurinp data as well
        modification a python dict of the form {'task':
        
        modifications parameter data of the form: {'tasks:
        out: a modified fleurinp data
        """

        # copy
        # get schema
        # read in inp.xml
        # add modifications
        # validate
        # save inp.xml
        # store new fleurinp (copy)

        new_fleurinp = original.copy()
        inpxmlfile = new_fleurinp.get_file_abs_path('inp.xml')
        modification_tasks = modifications.get_dict()['tasks']

        xmlschema_doc = etree.parse(new_fleurinp._schema_file_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)

        tree = etree.parse(inpxmlfile)
        # there is a bug when validating at parsetime, therefore we only
        #validate at parse time if file is invalid, to get nice error message
        if not xmlschema.validate(tree):
            tree = etree.parse(inpxmlfile, parser)

        new_fleurtree = FleurinpModifier.apply_modifications(fleurinp_tree_copy=tree,
            modification_tasks=modification_tasks)

        inpxmlfile = os.path.join(
                         new_fleurinp._get_folder_pathsubfolder.abspath, 'temp_inp.xml')
        new_fleurtree.write(inpxmlfile)

        new_fleurinp.del_file('inp.xml')
        new_fleurinp._add_path(str(inpxmlfile), 'inp.xml')
        os.remove(inpxmlfile)

        return new_fleurinp


    @staticmethod
    def apply_modifications(fleurinp_tree_copy, modification_tasks, schema_tree=None):
        """
        lxml etree of inp.xml
        and task dictionary
        """
        from aiida.tools.codespecific.fleur.xml_util import xml_set_attribv_occ,xml_set_first_attribv,xml_set_all_attribv, xml_set_text, xml_set_all_text, create_tag, replace_tag, delete_tag, delete_att, set_species, change_atomgr_att#, set_inpchanges

        def xml_set_attribv_occ1(fleurinp_tree_copy, xpathn, attributename, attribv, occ=[0], create=False):
            xml_set_attribv_occ(fleurinp_tree_copy, xpathn, attributename, attribv, occ=occ, create=create)
            return fleurinp_tree_copy

        def xml_set_first_attribv1(fleurinp_tree_copy, xpathn, attributename, attribv, create=False):
            xml_set_first_attribv(fleurinp_tree_copy, xpathn, attributename, attribv, create=create)
            return fleurinp_tree_copy

        def xml_set_all_attribv1(fleurinp_tree_copy, xpathn, attributename, attribv, create=False):
            xml_set_all_attribv(fleurinp_tree_copy, xpathn, attributename, attribv, create=create)
            return fleurinp_tree_copy

        def xml_set_text1(fleurinp_tree_copy, xpathn, text, create=False):
            xml_set_text(fleurinp_tree_copy, xpathn, text, create=create)
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
            fleurinp_tree_copy = set_species(fleurinp_tree_copy, species_name, attributedict, create=create)
            return fleurinp_tree_copy

        def change_atomgr_att1(fleurinp_tree_copy, attributedict, position=None, species=None,create=False):
            fleurinp_tree_copy = change_atomgr_att1(fleurinp_tree_copy, attributedict, position=position, species=species,create=create)
            return fleurinp_tree_copy


        def set_inpchanges1(fleurinp_tree_copy, change_dict):
            #fleurinp_tree_copy = set_inpchanges(fleurinp_tree_copy, change_dict)
            print 'in set_inpchanges'
            return fleurinp_tree_copy
        '''
        def set_species1(fleurinp_tree_copy, species_name, attributedict):
            #fleurinp_tree_copy = set_species(fleurinp_tree_copy , species_name, attributedict)
            print 'in set_species'
            return fleurinp_tree_copy

        def change_atom1(fleurinp_tree_copy, attrib, value, position=None, species=None):
            #fleurinp_tree_copy = change_atom(fleurinp_tree_copy, attrib, value, position=None, species=None)

            print 'in change_atom'
            return fleurinp_tree_copy

        def set_xpath1(fleurinp_tree_copy, xpath, value):
            #fleurinp_tree_copy = set_xpath(fleurinp_tree_copy, xpath, value)

            print 'in set_xpath'
            return fleurinp_tree_copy
        '''

        actions = {
            'xml_set_attribv_occ' : xml_set_attribv_occ1,
            'xml_set_first_attribv' : xml_set_first_attribv1,
            'xml_set_all_attribv' : xml_set_all_attribv1,
            'xml_set_text' : xml_set_text1,
            'xml_set_all_text' : xml_set_all_text1,
            'create_tag' : create_tag1,
            'replace_tag' : replace_tag1,
            'delete_tag' : delete_tag1,
            'delete_att' : delete_att1,
            'set_species' : set_species1,
            'change_atomgr_att' : change_atomgr_att1,
            #'set_inpchanges': set_inpchanges1

        }

        workingtree = fleurinp_tree_copy#.copy()
        if schema_tree:
            #xmlschema_doc = etree.parse(new_fleurinp._schema_file_path)
            xmlschema = etree.XMLSchema(schema_tree)
            parser = etree.XMLParser(schema=xmlschema, attribute_defaults=True)

        for task in modification_tasks:
            try:
                action = actions[task[0]]
            except KeyError:
                raise ValueError("Unknown task {}".format(task[0]))

            #print task[1:]
            workingtree = action(workingtree, *task[1:])
            if schema_tree:
                if not xmlschema.validate(fleurinp_tree_copy):
                    pass# do something to get nice error message
                    # TODO maybe even delete wrong task
                    print 'change not valid: {}'.format(task[1:])
                else:
                    print 'change validated'
        return workingtree
    '''
    def set_inpchanges(self, change_dict):
        self._tasks.append(('set_inpchanges', change_dict))

    def set_species(self, species_name, attributedict):
        self._tasks.append(('set_species', species_name, attributedict))

    def change_atom(self, attrib, value, position=None, species=None):
        self._tasks.append(('change_atom', attrib, value, position, species))

    def set_xpath(self, xpath, value):
        self._tasks.append(('set_xpath', xpath, value))
    '''
    def xml_set_attribv_occ(self, xpathn, attributename, attribv, occ=[0], create=False):
        self._tasks.append(('xml_set_attribv_occ', xpathn, attributename, attribv, occ, create))

    def xml_set_first_attribv(self, xpathn, attributename, attribv, create=False):
        self._tasks.append(('xml_set_first_attribv', xpathn, attributename, attribv, create))

    def xml_set_all_attribv(self, xpathn, attributename, attribv, create=False):
        self._tasks.append(('xml_set_all_attribv', xpathn, attributename, attribv, create))

    def xml_set_text(self, xpathn, text, create=False):
        self._tasks.append(('xml_set_text', xpathn, text, create))

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

    def change_atomgr_att(self, attributedict, position=None, species=None,create=False):
        self._tasks.append(('change_atomgr_att', attributedict, position, species, create))

    def validate(self):
        inpxmlfile = self._original.get_file_abs_path('inp.xml')
        tree = etree.parse(inpxmlfile)

        try:# could be not found or on another computer...
            xmlschema_tree = etree.parse(self._original._schema_file_path)
            with_schema = True
        except:
            with_schema = False
            print 'No schema file found'
            return
        if with_schema:
            tree = self.apply_modifications(tree, self._tasks, schema_tree=xmlschema_tree)
        return tree

    def show(self, display=True, validate=False):
        # apply modification


        if validate:
            tree = self.validate()
        else:
            inpxmlfile = self._original.get_file_abs_path('inp.xml')
            tree = etree.parse(inpxmlfile)
            tree = self.apply_modifications(tree, self._tasks)

        if display:
            xmltreestring = etree.tostring(tree, xml_declaration=True, pretty_print = True)
            print xmltreestring
        return tree
        #print self.apply_modifications(self._original.get_dict(), self._tasks)

    def changes(self):
        from pprint import pprint
        pprint(self._tasks)
        return self._tasks

    def freeze(self):
        modifications = DataFactory("parameter")(dict={"tasks": self._tasks})
        # This runs in a inline calculation to keep provenance
        out = self.modify_fleurinpdata(
            original=self._original, 
            modifications=modifications)
        return out


if __name__ == "__main__":

    P = DataFactory("fleurinp.fleurinp")
    '''
    orig = P(dict={'a': 1, 'b': True, 'c': "aaa"}).store()


    print "Original: {}".format(orig.pk)
    #print json.dumps(orig.get_dict(), indent=2)


    modifier = fleurinpModifier(orig)


    new = modifier.freeze()
    print "new: {}".format(new.pk)
    #print json.dumps(new.get_dict(), indent=2)
    '''





