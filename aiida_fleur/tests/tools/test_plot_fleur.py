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
from aiida import orm
from aiida_fleur.tools.plot.fleur import plot_fleur


def test_plot_fleur_single_wc_matplotlib(
        aiida_profile, generate_fleur_outpara_node, generate_fleur_scf_outpara_node,
        generate_fleur_eos_outpara_node):
    """test if plot fleur can visualize a workchain"""
    import matplotlib.pyplot as plt

    fleur_outputnode = orm.Dict(dict=generate_fleur_outpara_node, label='output_para')
    p_calc = plot_fleur(fleur_outputnode, show=False)

    assert isinstance(p_calc, list)
    assert p_calc[0] is None  # isinstance(p_scf[0], plt.figure)

    fleurscf_outputnode = orm.Dict(dict=generate_fleur_scf_outpara_node, label='output_scf_wc_para')
    p_scf = plot_fleur(fleurscf_outputnode, show=False)

    assert isinstance(p_scf, list)
    assert p_scf[0] is None  # isinstance(p_scf[0], plt.figure)

    fleureos_outputnode = orm.Dict(dict=generate_fleur_scf_outpara_node, label='output_eos_wc_para')
    p_eos = plot_fleur(fleureos_outputnode, show=False)

    assert isinstance(p_eos, list)
    assert p_eos[0] is None  # isinstance(p_scf[0], plt.figure)


def test_plot_fleur_multiple_wc_matplotlin(
        aiida_profile, generate_fleur_outpara_node, generate_fleur_scf_outpara_node,
        generate_fleur_eos_outpara_node):
    """test if plot fleur can visualize a multiple workchain output node, Fleur calcjob output nodes """

    import matplotlib.pyplot as plt

    fleur_outputnode = orm.Dict(dict=generate_fleur_outpara_node, label='output_para')
    p_calc = plot_fleur([fleur_outputnode, fleur_outputnode], show=False)

    assert isinstance(p_calc, list)
    assert p_calc[0] == []  # isinstance(p_scf[0], plt.figure)

    fleurscf_outputnode = orm.Dict(dict=generate_fleur_scf_outpara_node, label='output_scf_wc_para')
    p_scf = plot_fleur([fleurscf_outputnode, fleurscf_outputnode], show=False)

    assert isinstance(p_scf, list)
    assert p_scf[0] == [None]  # isinstance(p_scf[0], plt.figure)

    fleureos_outputnode = orm.Dict(dict=generate_fleur_scf_outpara_node, label='output_eos_wc_para')
    p_eos = plot_fleur([fleureos_outputnode, fleureos_outputnode], show=False)

    assert isinstance(p_eos, list)
    assert p_eos[0] == [None]  # isinstance(p_scf[0], plt.figure)


def test_plot_fleur_single_wc_bokeh(
        aiida_profile, generate_fleur_outpara_node, generate_fleur_scf_outpara_node,
        generate_fleur_eos_outpara_node):
    """test if plot fleur can visualize a single workchain with bokeh backend"""

    from bokeh.layouts import column  # gridplot

    fleur_outputnode = orm.Dict(dict=generate_fleur_outpara_node, label='output_para')
    p_calc = plot_fleur(fleur_outputnode, show=False, backend='bokeh')

    assert isinstance(p_calc, list)
    assert p_calc[0] is None  # currently does not have a visualization

    fleurscf_outputnode = orm.Dict(dict=generate_fleur_scf_outpara_node, label='output_scf_wc_para')
    p_scf = plot_fleur(fleurscf_outputnode, show=False, backend='bokeh')

    assert isinstance(p_scf, list)
    assert isinstance(p_scf[0], type(column()))

    fleureos_outputnode = orm.Dict(dict=generate_fleur_scf_outpara_node,
                                   label='output_eos_wc_para')
    p_eos = plot_fleur(fleureos_outputnode, show=False, backend='bokeh')

    assert isinstance(p_eos, list)
    assert isinstance(p_eos[0], type(column()))
