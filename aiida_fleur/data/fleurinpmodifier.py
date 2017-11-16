# -*- coding: utf-8 -*-
"""
In this module is the Fleurinpmodefier class, which is used to manipulate
fleurinpdata objects in a way which keeps the proverance.
"""

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

# TODO implement undo
# TODO general clean up
# TODO discuss design again what is really needed and the default way to du things
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

FleurinpData = DataFactory('fleur.fleurinp')

class FleurinpModifier(object):

    def __init__(self, original):
        #print(type(original), type(FleurinpData))
        assert isinstance(original, FleurinpData), "Wrong AiiDA data type"

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
        # TODO test if file is there!
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

        # default label and description
        new_fleurinp.label = 'mod_fleurinp'# {}'.format(original.label)
        new_fleurinp.description = 'Fleurinpdata with modifications (see inputs of modify_fleurinpdata)'
        #return {'modified_fleurinp' : new_fleurinp} # this will break other stuff (Scf), also link was not renamed somehow.
        return new_fleurinp

    @staticmethod
    def apply_modifications(fleurinp_tree_copy, modification_tasks, schema_tree=None):
        """
        lxml etree of inp.xml
        and task dictionary
        """
        from aiida_fleur.tools.xml_util import xml_set_attribv_occ,xml_set_first_attribv,xml_set_all_attribv, xml_set_text, xml_set_all_text, create_tag, replace_tag, delete_tag, delete_att, set_species, change_atomgr_att#, set_inpchanges
        from aiida_fleur.tools.xml_util import add_num_to_att

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
            fleurinp_tree_copy = change_atomgr_att(fleurinp_tree_copy, attributedict, position=position, species=species,create=create)
            return fleurinp_tree_copy


        def add_num_to_att1(fleurinp_tree_copy, xpathn, attributename, set_val, mode='abs', occ=[0], create=False):
            fleurinp_tree_copy = add_num_to_att(fleurinp_tree_copy, xpathn, attributename, set_val, mode=mode, occ=occ, create=create)
            return fleurinp_tree_copy

        '''
        def set_inpchanges1(fleurinp_tree_copy, change_dict):
            #fleurinp_tree_copy = set_inpchanges(fleurinp_tree_copy, change_dict)
            print 'in set_inpchanges'
            return fleurinp_tree_copy
        '''
        def set_inpchanges1(fleurinp_tree_copy, change_dict):
            """
            Does changes directly on the inp.xml file. Afterwards
            updates the inp.xml file representation and the current inp_userchanges
            dictionary with the keys provided in the 'change_dict' dictionary.

            :param change_dict: a python dictionary with the keys to substitute.
                                It works like dict.update(), adding new keys and
                                overwriting existing keys.
            """
            #print 'in set_inpchanges'
            from aiida_fleur.tools.xml_util import write_new_fleur_xmlinp_file, get_inpxml_file_structure

            #TODO if we still want tracking that way, have to get fleurinp in argument
            '''
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
            '''
            tree = fleurinp_tree_copy
            #apply changes to etree
            xmlinpstructure = get_inpxml_file_structure()
            new_tree = write_new_fleur_xmlinp_file(tree, change_dict, xmlinpstructure)

            return new_tree


        def set_nkpts1(fleurinp_tree_copy, count, gamma):#_orgi

            kpointlist_xpath = '/fleurInput/calculationSetup/bzIntegration/kPointList'
            #kpoint_xpath = '/fleurInput/calculationSetup/bzIntegration/kPoint*'

            tree = fleurinp_tree_copy
            new_kpo = etree.Element('kPointCount', count="{}".format(count), gamma="{}".format(gamma))
            #print new_kpo
            new_tree = replace_tag(tree, kpointlist_xpath, new_kpo)

            return new_tree

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
            'set_atomgr_att' : change_atomgr_att1,
            'set_inpchanges': set_inpchanges1,
            'set_nkpts' : set_nkpts1,
            'add_num_to_att' : add_num_to_att1

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
                    pass
                    #print 'change validated'
        return workingtree

    def get_avail_actions(self):
        """
        returns the allowed functions from fleurinpmod, this is for checking purposes of other routines
        """
        outside_actions = {
            'xml_set_attribv_occ' : self.xml_set_attribv_occ,
            'xml_set_first_attribv' : self.xml_set_first_attribv,
            'xml_set_all_attribv' : self.xml_set_all_attribv,
            'xml_set_text' : self.xml_set_text,
            'xml_set_all_text' : self.xml_set_all_text,
            'create_tag' : self.create_tag,
            'replace_tag' : self.replace_tag,
            'delete_tag' : self.delete_tag,
            'delete_att' : self.delete_att,
            'set_species' : self.set_species,
            'set_atomgr_att' : self.set_atomgr_att,
            'set_inpchanges': self.set_inpchanges,
            'set_nkpts' : self.set_nkpts,
            'add_num_to_att' : self.add_num_to_att

        }
        return outside_actions

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

    def set_atomgr_att(self, attributedict, position=None, species=None, create=False):
        self._tasks.append(('set_atomgr_att', attributedict, position, species, create))

    #for now
    def set_inpchanges(self, change_dict):
        self._tasks.append(('set_inpchanges', change_dict))

    def set_nkpts(self, count, gamma='F'):
        self._tasks.append(('set_nkpts', count, gamma))

    def add_num_to_att(self, xpathn, attributename, set_val, mode='abs', occ=[0], create=False):
        self._tasks.append(('add_num_to_att', xpathn, attributename, set_val, mode, occ, create))
    #def set_attribute(self, key, value):
    #    pass

    #def set_inpchanges(self, attributedict):
    #    for k, v in attrib

    def validate(self):
        #print('in validate')
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
        modifications.description = u'Fleurinpmodifier Tasks and inputs of these.'
        modifications.label = u'Fleurinpdata modifications'
        # This runs in a inline calculation to keep provenance
        out = self.modify_fleurinpdata(
            original=self._original,
            modifications=modifications,
            _label='fleurinp modifier',
            _description='This workfunction modified an Fleurinpdataobject')
        return out

    def undo(self, all=False):
        if all:
            self._tasks = []
        else:
            if self._tasks:
                self._tasks.pop()
                #del self._tasks[-1]
        return self._tasks

if __name__ == "__main__":

    P = FleurinpData
    '''
    orig = P(dict={'a': 1, 'b': True, 'c': "aaa"}).store()


    print "Original: {}".format(orig.pk)
    #print json.dumps(orig.get_dict(), indent=2)


    modifier = fleurinpModifier(orig)


    new = modifier.freeze()
    print "new: {}".format(new.pk)
    #print json.dumps(new.get_dict(), indent=2)
    '''





