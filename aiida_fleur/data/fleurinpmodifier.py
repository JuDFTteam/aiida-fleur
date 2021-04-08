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
import os
import io
from lxml import etree
import warnings

from masci_tools.io.fleurxmlmodifier import ModifierTask, FleurXMLModifier

from aiida_fleur.tools.xml_aiida_modifiers import FLEURINPMODIFIER_EXTRA_FUNCS
from aiida.engine.processes.functions import calcfunction as cf
from aiida_fleur.data.fleurinp import FleurinpData

class FleurinpModifier(FleurXMLModifier):
    """
    A class which represents changes to the :class:`~aiida_fleur.data.fleurinp.FleurinpData` object.
    """

    def __init__(self, original):
        """
        Initiation of FleurinpModifier.
        """
        assert isinstance(original, FleurinpData), 'Wrong AiiDA data type'

        self._original = original
        self._other_nodes = {}

        super().__init__()

    def get_avail_actions(self):
        """
        Returns the allowed functions from FleurinpModifier
        """
        outside_actions_fleurinp = {
            'set_kpointsdata': self.set_kpointsdata,
        }

        outside_actions_fleurxml = super().get_avail_actions().copy()

        return {**outside_actions_fleurxml, **outside_actions_fleurinp}

    def set_kpointsdata(self, kpointsdata_uuid):
        """
        Appends a :py:func:`~aiida_fleur.data.fleurinpmodifier.set_kpointsdata_f()` to
        the list of tasks that will be done on the FleurinpData.

        :param kpointsdata_uuid: an :class:`aiida.orm.KpointsData` or node uuid, since the node is self cannot be be serialized in tasks.
        """
        from aiida.orm import KpointsData, load_node

        if isinstance(kpointsdata_uuid, KpointsData):
            kpointsdata_uuid = kpointsdata_uuid.uuid
        # Be more careful? Needs to be stored, otherwise we cannot load it
        self._other_nodes['kpoints'] = load_node(kpointsdata_uuid)
        self._tasks.append(ModifierTask('set_kpointsdata', args=[kpointsdata_uuid], kwargs={}))

    #Modification functions that were renamed in masci-tools

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

        self.set_atomgroup_label(*args, **kwargs)

    def xml_set_attribv_occ(self, *args, **kwargs):
        """
        Deprecated method for setting attributes for occurrences on a specific xpath
        """

        warnings.warn('This modification method is deprecated.'
                      "Use the 'xml_set_attrib_value_no_create' or"
                      "'set_attrib_value' method instead", DeprecationWarning)

        self.xml_set_attrib_value_no_create(*args, **kwargs)

    def xml_set_first_attribv(self, *args, **kwargs):
        """
        Deprecated method for setting the first attribute on a specific xpath
        """

        warnings.warn('This modification method is deprecated.'
                      "Use the 'xml_set_first_attrib_value_no_create' with 'occ=0' or"
                      "'set_first_attrib_value' method instead", DeprecationWarning)

        self.xml_set_attrib_value_no_create(*args, occ=0, **kwargs)

    def xml_set_all_attribv(self, *args, **kwargs):
        """
        Deprecated method for setting all attributes on a specific xpath
        """

        warnings.warn('This modification method is deprecated.'
                      "Use the 'xml_set_attrib_value_no_create' with occ='all' or"
                      "'set_attrib_value' method instead", DeprecationWarning)

        self.xml_set_attrib_value_no_create(*args, occ='all', **kwargs)

    def xml_set_text_occ(self, *args, **kwargs):
        """
        Deprecated method for setting texts for occurrences on a specific xpath
        """

        warnings.warn('This modification method is deprecated.'
                      "Use the 'xml_set_text_no_create' or"
                      "'set_text' method instead", DeprecationWarning)

        self.xml_set_text_no_create(*args, **kwargs)

    def xml_set_text(self, *args, **kwargs):
        """
        Deprecated method for setting attributes for occurrences on a specific xpath
        """

        warnings.warn('This modification method is deprecated.'
                      "Use the 'xml_set_text_no_create' with 'occ=0' or"
                      "'set_first_text' method instead", DeprecationWarning)

        self.xml_set_text_no_create(*args, occ=0, **kwargs)

    def xml_set_all_text(self, *args, **kwargs):
        """
        Deprecated method for setting attributes for occurrences on a specific xpath
        """

        warnings.warn('This modification method is deprecated.'
                      "Use the 'xml_set_text_no_create' with occ='all' or"
                      "'set_text' method instead", DeprecationWarning)

        self.xml_set_text_no_create(*args, occ='all', **kwargs)

    def validate(self):
        """
        Extracts the schema-file.
        Makes a test if all the changes lead to an inp.xml file that is validated against the
        schema.

        :return: a lxml tree representing inp.xml with applied changes
        """

        xmltree, schema_dict = self._original.load_inpxml(remove_blank_text=True)

        try:
            with self._original.open(path='n_mmp_mat', mode='r') as n_mmp_file:
                nmmplines = n_mmp_file.read().split('\n')
        except FileNotFoundError:
            nmmplines = None

        xmltree, nmmp = super().apply_modifications(xmltree, nmmplines, self._tasks, extra_funcs=FLEURINPMODIFIER_EXTRA_FUNCS)
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
            xmltree, schema_dict = self._original.load_inpxml(remove_blank_text=True)
            xmltree, temp_nmmp = self.apply_modifications(xmltree, None, self._tasks, schema_dict)
            try:
                with self._original.open(path='n_mmp_mat', mode='r') as n_mmp_file:
                    nmmplines = n_mmp_file.read().split('\n')
            except FileNotFoundError:
                nmmplines = None

            tree, nmmp = super().apply_modifications(tree, nmmplines, self._tasks, extra_funcs=FLEURINPMODIFIER_EXTRA_FUNCS)

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
    def modify_xmlfile(self, *args, **kwargs): #pylint: disable=missing-function-docstring
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
    from masci_tools.util.xml.common_functions import reverse_xinclude

    new_fleurinp = original.clone()
    modification_tasks = modifications.get_dict()['tasks']

    xmltree, schema_dict, included_tags = new_fleurinp.load_inpxml(remove_blank_text=True, return_included_tags=True)

    try:
        with new_fleurinp.open(path='n_mmp_mat', mode='r') as n_mmp_file:
            nmmplines = n_mmp_file.read().split('\n')
    except FileNotFoundError:
        nmmplines = None

    new_fleurtree, new_nmmplines = FleurinpModifier.apply_modifications(xmltree=xmltree,\
                                                                        nmmp_lines=nmmplines,\
                                                                        modification_tasks=modification_tasks,
                                                                        validate_changes=False,
                                                                        extra_funcs=FLEURINPMODIFIER_EXTRA_FUNCS)

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

