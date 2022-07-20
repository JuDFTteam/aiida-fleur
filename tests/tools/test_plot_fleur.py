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
#TODO: Tests for banddos and orbcontrol workchain
import pytest
import os
from aiida import orm, plugins
from aiida_fleur.tools.plot import plot_fleur
import aiida_fleur
import matplotlib.pyplot as plt
import matplotlib
import aiida
from packaging import version

matplotlib.use('Agg')


@pytest.mark.mpl_image_compare(baseline_dir='test_plot_fleur')
def test_plot_fleur_single_scf_wc_matplotlib(read_dict_from_file, test_file):
    """
    Test of visualization of single SCF workchain with matplotlib
    """

    out_node_scf_path = test_file('jsons/fleur_output_scf_wc_para.json')

    plt.gcf().clear()

    scf_output = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')

    p_scf = plot_fleur(scf_output, show=False)
    assert isinstance(p_scf, list)

    return plt.gcf()


def test_plot_fleur_single_scf_wc_bokeh(read_dict_from_file, check_bokeh_plot, test_file):
    """
    Test of visualization of single SCF workchain with bokeh
    """
    pytest.importorskip('bokeh')
    from bokeh.layouts import gridplot  # pylint: disable=import-error

    out_node_scf_path = test_file('jsons/fleur_output_scf_wc_para.json')

    scf_output = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')

    p_scf = plot_fleur(scf_output, show=False, backend='bokeh')
    assert isinstance(p_scf, list)

    grid = gridplot(p_scf[0], ncols=1)

    check_bokeh_plot(grid)


@pytest.mark.mpl_image_compare(baseline_dir='test_plot_fleur')
def test_plot_fleur_multiple_scf_wc_matplotlib(read_dict_from_file, test_file):
    """
    Test of visualization of single SCF workchain with matplotlib
    """
    out_node_scf_path = test_file('jsons/fleur_output_scf_wc_para.json')

    plt.gcf().clear()

    scf_output = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    p_scf = plot_fleur([scf_output, scf_output], show=False, axis_energy=ax1, axis_distance=ax2)
    assert isinstance(p_scf, list)

    return fig


def test_plot_fleur_multiple_scf_wc_bokeh(read_dict_from_file, check_bokeh_plot, test_file):
    """
    Test of visualization of single SCF workchain with bokeh
    """
    pytest.importorskip('bokeh')
    from bokeh.layouts import gridplot  # pylint: disable=import-error

    out_node_scf_path = test_file('jsons/fleur_output_scf_wc_para.json')

    scf_output = orm.Dict(dict=read_dict_from_file(out_node_scf_path), label='output_scf_wc_para')

    p_scf = plot_fleur([scf_output, scf_output], show=False, backend='bokeh')
    assert isinstance(p_scf, list)

    grid = gridplot(p_scf[0], ncols=1)

    check_bokeh_plot(grid)


@pytest.mark.mpl_image_compare(baseline_dir='test_plot_fleur')
def test_plot_fleur_single_eos_wc_matplotlib(read_dict_from_file, test_file):
    """
    Test of visualization of single SCF workchain with matplotlib
    """

    out_node_eos_path = test_file('jsons/fleur_output_eos_wc_para.json')

    plt.gcf().clear()

    eos_output = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_scf_wc_para')
    print(eos_output.get_dict())

    p_eos = plot_fleur(eos_output, show=False)
    assert isinstance(p_eos, list)

    return plt.gcf()


def test_plot_fleur_single_eos_wc_bokeh(read_dict_from_file, check_bokeh_plot, test_file):
    """
    Test of visualization of single SCF workchain with bokeh
    """
    pytest.importorskip('bokeh')

    out_node_eos_path = test_file('jsons/fleur_output_eos_wc_para.json')

    eos_output = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_eos_wc_para')

    p_eos = plot_fleur(eos_output, show=False, backend='bokeh')
    assert isinstance(p_eos, list)

    check_bokeh_plot(p_eos[0])


@pytest.mark.mpl_image_compare(baseline_dir='test_plot_fleur')
def test_plot_fleur_multiple_eos_wc_matplotlib(read_dict_from_file, test_file):
    """
    Test of visualization of single SCF workchain with matplotlib
    """

    out_node_eos_path = test_file('jsons/fleur_output_eos_wc_para.json')

    plt.gcf().clear()

    eos_output = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_scf_wc_para')

    p_eos = plot_fleur([eos_output, eos_output], show=False)
    assert isinstance(p_eos, list)

    return plt.gcf()


def test_plot_fleur_multiple_eos_wc_bokeh(read_dict_from_file, check_bokeh_plot, test_file):
    """
    Test of visualization of single SCF workchain with bokeh
    """
    pytest.importorskip('bokeh')

    out_node_eos_path = test_file('jsons/fleur_output_eos_wc_para.json')

    eos_output = orm.Dict(dict=read_dict_from_file(out_node_eos_path), label='output_eos_wc_para')

    p_eos = plot_fleur([eos_output, eos_output], show=False, backend='bokeh')
    assert isinstance(p_eos, list)

    check_bokeh_plot(p_eos[0])


def test_plot_fleur_single_invalid_node(read_dict_from_file, test_file):
    """
    Test that plot_fleur raises for non-workchain nodes
    """

    out_node_path = test_file('jsons/fleur_outputpara.json')

    fleur_outputnode = orm.Dict(dict=read_dict_from_file(out_node_path), label='output_para')
    with pytest.raises(ValueError, match=r'Sorry, I do not know how to visualize'):
        plot_fleur(fleur_outputnode, show=False)


def test_plot_fleur_mulitple_invalid_node(read_dict_from_file, test_file):
    """
    Test that plot_fleur raises for non-workchain nodes
    """

    out_node_path = test_file('jsons/fleur_outputpara.json')

    fleur_outputnode = orm.Dict(dict=read_dict_from_file(out_node_path), label='output_para')
    with pytest.warns(UserWarning, match=r'Sorry, I do not know how to visualize'):
        plot_fleur([fleur_outputnode, fleur_outputnode], show=False)


file_path = '../workflows/caches/fleur_orbcontrol_structure.tar.gz'
thisfilefolder = os.path.dirname(os.path.abspath(__file__))
EXPORTFILE_FILE = os.path.abspath(os.path.join(thisfilefolder, file_path))

@pytest.mark.skipif(version.parse(aiida.__version__) < version.parse('1.5.0'),
                    reason='archive import and migration works only with aiida-core > 1.5.0')
@pytest.mark.skipif(not os.path.isfile(EXPORTFILE_FILE),
                    reason='Workflow regression files are being regenerated. Skipping plot test'
                    '(Based on results of workflow test)')
@pytest.mark.mpl_image_compare(baseline_dir='test_plot_fleur')
def test_plot_fleur_single_orbcontrol_wc_matplotlib(import_with_migrate, clear_database):
    """
    Test of visualization of single Orbcontrol workchain with matplotlib
    """
    # import an an aiida export, this does not migrate
    import_with_migrate(EXPORTFILE_FILE)
    node = orm.QueryBuilder().append(plugins.WorkflowFactory('fleur.orbcontrol')).one()[0]

    plt.gcf().clear()
    p_orbcontrol = plot_fleur(node, show=False)
    assert isinstance(p_orbcontrol, list)

    return plt.gcf()
