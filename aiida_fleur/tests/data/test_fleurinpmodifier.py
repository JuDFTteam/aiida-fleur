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
''' Contains tests for modifing FleurinpData with Fleurinpmodifier '''

from __future__ import absolute_import
import os
import pytest

# Collect the input files
file_path1 = '../files/inpxml/FePt/inp.xml'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
inpxmlfilefolder = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))


def test_fleurinp_modifier1(create_fleurinp):
    from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)

    fm = FleurinpModifier(fleurinp_tmp)
    fm.set_inpchanges({'dos': True, 'Kmax': 3.9})
    fm.shift_value({'Kmax': 0.1}, 'rel')
    fm.shift_value_species_label('                 222', 'radius', 3, mode='abs')
    fm.set_species('all', {'mtSphere': {'radius': 3.333}})
    fm.undo()
    changes = fm.changes()
    assert changes == [('set_inpchanges', {
        'Kmax': 3.9,
        'dos': True
    }), ('shift_value', {
        'Kmax': 0.1
    }, 'rel'), ('shift_value_species_label', '                 222', 'radius', 3, 'abs')]

    fm.show(validate=True)
    fm.freeze()


def test_fleurinp_modifier2(create_fleurinp, inpxml_etree):
    from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
    from aiida_fleur.tools.xml_util import eval_xpath
    fleurinp_tmp = create_fleurinp(inpxmlfilefolder)
    etree = inpxml_etree(inpxmlfilefolder)

    fm = FleurinpModifier(fleurinp_tmp)

    new_tag = eval_xpath(etree, '/fleurInput/calculationSetup/scfLoop')
    fm.delete_tag('/fleurInput/calculationSetup/scfLoop')
    fm.replace_tag('/fleurInput/calculationSetup/cutoffs', new_tag)
    fm.delete_att('/fleurInput/calculationSetup/soc', 'theta')
    fm.create_tag('/fleurInput/calculationSetup/soc', 'theta')
    fm.xml_set_all_text('/fleurInput/cell/symmetryOperations/symOp/row-1', 'test text')
    fm.xml_set_text_occ('/fleurInput/cell/symmetryOperations/symOp/row-1', 'test text')
    fm.xml_set_text('/fleurInput/cell/symmetryOperations/symOp/row-1', 'test text')
    fm.xml_set_all_attribv('/fleurInput/calculationSetup/soc', 'theta', 12)
    fm.xml_set_first_attribv('/fleurInput/calculationSetup/soc', 'theta', 12)
    fm.xml_set_attribv_occ('/fleurInput/calculationSetup/soc', 'theta', 12)
    fm.set_species_label('                 222', {'mtSphere': {'radius': 3.333}})
    fm.set_atomgr_att_label(attributedict={'force': [('relaxXYZ', 'FFF')]}, atom_label='                 222')
    fm.set_atomgr_att(attributedict={'force': [('relaxXYZ', 'TFF')]}, species='Fe-1')
    fm.show()
