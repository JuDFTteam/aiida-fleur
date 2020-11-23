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
Module with CLI commands for various visualizations of data types.
"""
# if in the future there are futher sub commands of plot, the current plot
# command can become plot_fleur
import click
from aiida.cmdline.utils import decorators
from aiida.cmdline.params import arguments


@click.command('plot')
@arguments.NODES('nodes')
#                help='The pks for the nodes to be parsed to plot_fleur')
# type=click.Path(exists=True))
@click.option('-f', 'filename', type=click.File('r'), default=None)
@click.option('--save',
              type=click.BOOL,
              default=False,
              show_default=True,
              help='Should the result of plot_fleur be saved to a files.')
@click.option('--show/--no-show', default=True, show_default=True, help='Show the output of plot_fleur.')
@click.option('--show_dict/--no-show_dict', default=False, show_default=True, help='Show the output of plot_fleur.')
@click.option('--bokeh', 'backend', flag_value='bokeh')
@click.option('--matplotlib', 'backend', flag_value='matplotlib', default=True)
#@decorators.with_dbenv()
def cmd_plot(nodes, filename, save, show_dict, backend, show):
    """
    Invoke the plot_fleur command on given nodes
    """
    if backend != 'bokeh':
        # Try to set a working GUI backend for matplotlib
        # normally we assume to be on ipython which is not good.
        # The order is arbitrary.
        import matplotlib
        gui_env = [
            'WebAgg', 'GTK3Agg', 'GTK3Cairo', 'MacOSX', 'Qt4Agg', 'Qt4Cairo', 'Qt5Agg', 'Qt5Cairo', 'TkAgg', 'TkCairo',
            'WX', 'WXAgg', 'WXCairo', 'nbAgg', 'agg', 'cairo', 'pdf', 'pgf', 'ps', 'svg'
        ]
        for gui in gui_env:
            try:
                print('testing', gui)
                matplotlib.use(gui, force=True)
                from matplotlib import pyplot as plt
                break
            except ImportError as ex:
                print(ex)
                continue
        print('Using:', matplotlib.get_backend())

    from aiida_fleur.tools.plot.fleur import plot_fleur

    nodes = list(nodes)
    nodesf = []
    if filename is not None:
        nodesf = filename.read().split()
        filename.close()
    nodes = nodes + nodesf
    p = plot_fleur(nodes, save=save, show_dict=show_dict, backend=backend, show=show)
