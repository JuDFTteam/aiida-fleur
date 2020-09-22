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
Tests for the `plot_fleur` function.
All test are executed with show false, if some plot opens, something is not right
"""

from __future__ import absolute_import
import pytest
import os
from aiida import orm
from aiida_fleur.tools.plot.fleur import plot_fleur
import aiida_fleur
import matplotlib as plt
plt.use('Agg')


def test_plot_fleur_single_wc_matplotlib(aiida_profile, read_dict_from_file):
    """test if plot fleur can visualize a workchain"""

    aiida_path = os.path.dirname(aiida_fleur.__file__)
    out_node_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_outputpara.json')
    out_node_scf_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_output_scf_wc_para.json')
    out_node_eos_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_output_eos_wc_para.json')

    fleur_outputnode = orm.Dict(dict=read_dict_from_file(out_node_path), label='output_para')
    p_calc = plot_fleur(fleur_outputnode, show=False)

    assert isinstance(p_calc, list)
    assert p_calc[0] is None  # isinstance(p_scf[0], plt.figure)

    scf_output = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')
    p_scf = plot_fleur(scf_output, show=False)

    assert isinstance(p_scf, list)
    # assert isinstance(p_scf[0], type(plt.axes))  # isinstance(p_scf[0], plt.figure)

    eos_output = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_eos_wc_para')
    p_eos = plot_fleur(eos_output, show=False)

    assert isinstance(p_eos, list)
    #assert isinstance(p_eos[0], type(plt.axes))


def test_plot_fleur_multiple_wc_matplotlib(aiida_profile, read_dict_from_file):
    """test if plot fleur can visualize a multiple workchain output node, Fleur calcjob output nodes """

    from matplotlib.axes import Axes

    aiida_path = os.path.dirname(aiida_fleur.__file__)
    out_node_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_outputpara.json')
    out_node_scf_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_output_scf_wc_para.json')
    out_node_eos_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_output_eos_wc_para.json')

    fleur_outputnode = orm.Dict(dict=read_dict_from_file(out_node_path), label='output_para')
    p_calc = plot_fleur([fleur_outputnode, fleur_outputnode], show=False)

    assert isinstance(p_calc, list)
    assert p_calc[0] == []  # isinstance(p_scf[0], plt.figure)

    scf_output = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')
    p_scf = plot_fleur([scf_output, scf_output], show=False)

    assert isinstance(p_scf, list)
    # assert isinstance(p_scf[0][0], type(Axes))  # return 2 plots

    eos_output = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_eos_wc_para')
    p_eos = plot_fleur([eos_output, eos_output], show=False)

    assert isinstance(p_eos, list)
    #assert isinstance(p_eos[0], type(Axes))


@pytest.mark.skip(reason='does work, but requires current masci-tool develop branch >0.10.3')
def test_plot_fleur_single_wc_bokeh(aiida_profile, read_dict_from_file):
    """test if plot fleur can visualize a single workchain with bokeh backend"""
    try:  #bokeh is not a prerequisite of Aiida-Fleur, might become of masci-tools
        from bokeh.layouts import column  # gridplot
    except ImportError:
        return

    aiida_path = os.path.dirname(aiida_fleur.__file__)
    out_node_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_outputpara.json')
    out_node_scf_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_output_scf_wc_para.json')
    out_node_eos_path = os.path.join(aiida_path, 'tests/files/jsons/fleur_output_eos_wc_para.json')

    fleur_outputnode = orm.Dict(dict=read_dict_from_file(out_node_path), label='output_para')
    p_calc = plot_fleur(fleur_outputnode, show=False, backend='bokeh')

    assert isinstance(p_calc, list)
    assert p_calc[0] is None  # currently does not have a visualization

    scf_out = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')
    p_scf = plot_fleur(scf_out, show=False, backend='bokeh')

    assert isinstance(p_scf, list)
    assert isinstance(p_scf[0], type(column()))

    # eos_out = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_eos_wc_para')
    # p_eos = plot_fleur(eos_out, show=False, backend='bokeh')

    # assert isinstance(p_eos, list)
    # assert isinstance(p_eos[0], type(column()))
