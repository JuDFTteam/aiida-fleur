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
In this module is the plot_fleur method and its logic. The methods allows for the visualization on
every database node specifc to aiida-fleur. It depends on plot more general plot routines from
masci-tools which use matplotlib or bokeh as backend.
"""
# TODO but allow to optional parse information for saving and title,
#  (that user can put pks or structure formulas in there)
# INFO: AiiDAlab has implemented an extendable viewer class for data structures,
# which might be some point moved to aiida-core and extensible over entrypoints.

from __future__ import absolute_import
from __future__ import print_function
from pprint import pprint
import six
import numpy as np
#import matplotlib.pyplot as pp
#from masci_tools.vis.plot_methods import *
from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.orm import WorkChainNode
from aiida.orm import Node

###########################
## general plot routine  ##
###########################


def plot_fleur(*args, **kwargs):
    """
    This methods takes any amount of AiiDA node and starts
    the standard visualisation either as single or together visualisation.
    (if they are provided as list)
    i.e plot_fleur(123, [124,125], uuid, save=False, backend='bokeh')

    Some general parameters of plot methods can be given as
    keyword arguments.
    reservedd keywords are:

    save: bool, should the plots be saved automatically
    backend: str, 'bokeh' or else matplotlib
    show_dict: bool, print the output dictionaries of the given nodes

    returns a list of plot objects for further modification or handling
    this might be used for a quick dashboard build.
    """
    '''
    def set_plot_defaults(title_fontsize = 16,
                      linewidth = 2.0,
                      markersize = 4.0,
                      labelfonstsize = 15,
                      ticklabelsize = 14,
                      tick_params = {'size' : 4.0, 'width' : 1.0,
                                     'labelsize' : ticklabelsize_g,
                                     'length' : 5},
                      save_plots = False, #True,
                      save_format = 'pdf'):
    '''
    from masci_tools.vis.plot_methods import set_plot_defaults

    save = False
    show_dict = False
    show = True
    backend = 'matplotlib'
    for key, val in six.iteritems(kwargs):
        if key == 'save':
            save = val
        if key == 'show_dict':
            show_dict = val
        if key == 'backend':
            backend = val
        if key == 'show':
            show = val
    #    # the rest we ignore for know
    #Just call set plot defaults
    # TODO, or rather parse it onto plot functions...?
    set_plot_defaults(**kwargs)

    all_plots = []
    for arg in args:
        if isinstance(arg, list):
            # try plot together
            p1 = plot_fleur_mn(arg, save=save, show=show, backend=backend)
        else:
            #print(arg)
            # plot alone
            p1 = plot_fleur_sn(arg, show_dict=show_dict, show=show, save=save, backend=backend)
        all_plots.append(p1)

    return all_plots


def plot_fleur_sn(node, show_dict=False, save=False, show=True, backend='bokeh'):
    """
    This methods takes any single AiiDA node and starts the standard visualisation for
    if it finds one
    """
    #show_dic = show_dic
    ParameterData = DataFactory('dict')
    if isinstance(node, int):  #pk
        node = load_node(node)

    if isinstance(node, (str, six.text_type)):  #uuid
        node = load_node(node)  #try

    if isinstance(node, Node):
        if isinstance(node, WorkChainNode):
            output_list = node.get_outgoing().all()
            found = False
            for out_link in output_list:
                if 'output_' in out_link.link_label:
                    if 'wc' in out_link.link_label or 'wf' in out_link.link_label:
                        if 'para' in out_link.link_label:  # We are just looking for parameter
                            #nodes, structures, bands, dos and so on we tread different
                            node = out_link.node  # we only visualize last output node
                            found = True
            if not found:
                print('Sorry, I do not know how to visualize this WorkChainNode {}, which contains'
                      ' the following outgoing links {}. Maybe it is not (yet) finished successful.'
                      ''.format(node, [link.link_label for link in output_list]))
                return
        if isinstance(node, ParameterData):
            p_dict = node.get_dict()
            workflow_name = p_dict.get('workflow_name', None)
            try:
                plotf = FUNCTIONS_DICT[workflow_name]
            except KeyError:
                print(('Sorry, I do not know how to visualize this workflow: {}, node {}.'
                       'Please implement me in plot_fleur_aiida!'.format(workflow_name, node)))
                if show_dict:
                    pprint(p_dict)
                return
            p1 = plotf(node, save=save, show=show, backend=backend)
        else:
            print('I do not know how to visualize this node: {}, type {}'.format(node, type(node)))
    else:
        print(('The node provided: {}, type {} is not an AiiDA object'.format(node, type(node))))
    # check if AiiDa node
    #check what type of node
    # if calcfunction, get certain output node
    #if parameterData, output node check if workflow name tag
    # if routine known plot,
    #else say I do not know
    return p1


def plot_fleur_mn(nodelist, save=False, show=True, backend='bokeh'):
    """
    This methods takes any amount of AiiDA node as a list and starts
    the standard visualisation for it, if it finds one.

    Some nodes types it tries to display together if it knows how to.
    and if they are given as a list.

    param: save showed the plots be saved automatically

    """
    ###
    # Things to plot together
    all_nodes = {}
    ###
    ParameterData = DataFactory('dict')

    if not isinstance(nodelist, list):
        print(('The nodelist provided: {}, type {} is not a list. ' 'I abort'.format(nodelist, type(nodelist))))
        return None

    node_labels = []
    for node in nodelist:
        # first find out what we have then how to visualize
        if isinstance(node, int):  #pk
            node = load_node(node)
        if isinstance(node, (str, six.text_type)):  #uuid
            node = load_node(node)  #try

        if isinstance(node, Node):
            node_labels.append(node.label)
            if isinstance(node, WorkChainNode):
                output_list = node.get_outgoing().all()
                for out_link in output_list:
                    if 'output_' in out_link.link_label:
                        if 'wc' in out_link.link_label or 'wf' in out_link.link_label:
                            if 'para' in out_link.link_label:  # We are just looking for parameter
                                #nodes, structures, bands, dos and so on we tread different
                                node = out_link.node  # we only visualize last output node
            if isinstance(node, ParameterData):
                p_dict = node.get_dict()
                workflow_name = p_dict.get('workflow_name', None)
                cur_list = all_nodes.get(workflow_name, [])
                cur_list.append(node)
                all_nodes[workflow_name] = cur_list
            else:
                print(('I do not know how to visualize this node: {}, '
                       'type {} from the nodelist length {}'.format(node, type(node), len(nodelist))))
        else:
            print(('The node provided: {} of type {} in the nodelist length {}'
                   ' is not an AiiDA object'.format(node, type(node), len(nodelist))))

    #print(all_nodes)
    all_plot_res = []
    for node_key, nodelist1 in six.iteritems(all_nodes):
        try:
            plotf = FUNCTIONS_DICT[node_key]
        except KeyError:
            print(('Sorry, I do not know how to visualize'
                   ' these nodes (multiplot): {} {}'.format(node_key, nodelist1)))
            continue
        plot_res = plotf(nodelist1, labels=node_labels, save=save, show=show, backend=backend)
        all_plot_res.append(plot_res)
    return all_plot_res


###########################
## general plot routine  ##
###########################


def plot_fleur_scf_wc(nodes, labels=None, save=False, show=True, backend='bokeh'):
    """
    This methods takes an AiiDA output parameter node or a list from a scf workchain and
    plots number of iteration over distance and total energy
    """
    if backend == 'bokeh':
        from masci_tools.vis.bokeh_plots import plot_convergence_results_m
    else:
        from masci_tools.vis.plot_methods import plot_convergence_results_m

    if labels is None:
        labels = []

    if isinstance(nodes, list):
        if len(nodes) >= 2:
            #return # TODO
            pass
        else:
            nodes = [nodes[0]]
    else:
        nodes = [nodes]  #[0]]
    #scf_wf = load_node(6513)

    iterations = []
    distance_all_n = []
    total_energy_n = []
    modes = []
    nodes_pk = []

    for node in nodes:
        iteration = []
        output_d = node.get_dict()
        total_energy = output_d.get('total_energy_all')
        if not total_energy:
            print('No total energy data found, skip this node: {}'.format(node))
            continue
        distance_all = output_d.get('distance_charge_all')
        iteration_total = output_d.get('iterations_total')
        if not distance_all:
            print('No distance_charge_all data found, skip this node: {}'.format(node))
            continue
        if not iteration_total:
            print('No iteration_total data found, skip this node: {}'.format(node))
            continue

        mode = output_d.get('conv_mode')
        nodes_pk.append(node.pk)
        for i in range(1, len(total_energy) + 1):
            iteration.append(iteration_total - len(total_energy) + i)

        if len(distance_all) == 2 * len(total_energy):  # not sure if this is best solution
            # magnetic calculation, we plot only spin 1 for now.
            distance_all = [distance_all[j] for j in range(0, len(distance_all), 2)]

        iterations.append(iteration)
        distance_all_n.append(distance_all)
        total_energy_n.append(total_energy)
        modes.append(mode)

    #plot_convergence_results(distance_all, total_energy, iteration)
    if labels:
        plt = plot_convergence_results_m(distance_all_n,
                                         total_energy_n,
                                         iterations,
                                         plot_labels=labels,
                                         nodes=nodes_pk,
                                         modes=modes,
                                         show=show)
    else:
        plt = plot_convergence_results_m(distance_all_n,
                                         total_energy_n,
                                         iterations,
                                         nodes=nodes_pk,
                                         modes=modes,
                                         show=show)

    return plt


def plot_fleur_dos_wc(node, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes an AiiDA output parameter node from a density of states
    workchain and plots a simple density of states
    """
    from masci_tools.vis.plot_methods import plot_dos

    if labels is None:
        labels = []

    if isinstance(node, list):
        if len(node) > 2:
            return  # TODO
        else:
            node = node[0]

    output_d = node.get_dict()
    path_to_dosfile = output_d.get('dosfile', None)
    print(path_to_dosfile)
    if path_to_dosfile:
        plot_dos(path_to_dosfile, only_total=False, show=show)
        p1 = None  # FIXME masci-tools should return something
    else:
        print('Could not retrieve dos file path from output node')

    return p1


def plot_fleur_eos_wc(node, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes an AiiDA output parameter node from a density of states
    workchain and plots a simple density of states
    """
    from masci_tools.vis.plot_methods import plot_lattice_constant

    if labels is None:
        labels = []

    if isinstance(node, list):
        if len(node) > 2:
            Total_energy = []
            scaling = []
            plotlables = []

            for i, nd in enumerate(node):
                outpara = nd.get_dict()
                volume_gs = outpara.get('volume_gs')
                scale_gs = outpara.get(u'scaling_gs')
                total_e = outpara.get('total_energy')
                total_e_norm = np.array(total_e) - total_e[0]
                Total_energy.append(total_e_norm)
                scaling.append(outpara.get('scaling'))
                plotlables.append((r'gs_vol: {:.3} A^3, gs_scale {:.3}, data {}' ''.format(volume_gs, scale_gs, i)))
                plotlables.append(r'fit results {}'.format(i))
            plot_lattice_constant(Total_energy, scaling, multi=True, plotlables=plotlables, show=show)
            return  # TODO
        else:
            node = node[0]

    outpara = node.get_dict()
    Total_energy = outpara.get('total_energy')
    scaling = outpara.get('scaling')
    #fit = outpara.get('fitresults')
    #fit = outpara.get('fit')

    #def parabola(x, a, b, c):
    #    return a*x**2 + b*x + c

    #fit_y = []
    #fit_y = [parabola(scale2, fit[0], fit[1], fit[2]) for scale2 in scaling]
    p1 = plot_lattice_constant(Total_energy, scaling, show=show)  #, fit_y)
    return p1


def plot_fleur_band_wc(node, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes an AiiDA output parameter node from a band structure
    workchain and plots a simple band structure
    """
    from masci_tools.vis.plot_methods import plot_bands

    if labels is None:
        labels = []

    if isinstance(node, list):
        if len(node) > 2:
            return  # TODO
        else:
            node = node[0]

    output_d = node.get_dict()
    path_to_bands_file = output_d.get('bandfile', None)
    print(path_to_bands_file)
    kpath = output_d.get('kpath', {})  #r"$\Gamma$": 0.00000, r"$H$" : 1.04590,
    #    r"$N$" : 1.78546, r"$P$": 2.30841, r"$\Gamma1$" : 3.21419, r"$N1$" : 3.95375} )

    if path_to_bands_file:
        plot_bands(path_to_bands_file, kpath)
    else:
        print('Could not retrieve dos file path from output node')


def plot_fleur_relax_wc(node, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes an AiiDA output parameter node from a relaxation
    workchain and plots some information about atom movements and forces
    """
    if labels is None:
        labels = []

    # TODO: implement
    #plot_relaxation_results


def plot_fleur_corehole_wc(nodes, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes AiiDA output parameter nodes from a corehole
    workchain and plots some information about Binding energies
    """

    if labels is None:
        labels = []

    # TODO: implement


def plot_fleur_initial_cls_wc(nodes, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes AiiDA output parameter nodes from a initial_cls
    workchain and plots some information about corelevel shifts.
    (Spectra)
    """
    if labels is None:
        labels = []

    # TODO: implement


FUNCTIONS_DICT = {
    'fleur_scf_wc': plot_fleur_scf_wc,  #support of < 1.0 release
    'fleur_eos_wc': plot_fleur_eos_wc,  #support of < 1.0 release
    'FleurScfWorkChain': plot_fleur_scf_wc,
    'FleurEosWorkChain': plot_fleur_eos_wc,
    'fleur_dos_wc': plot_fleur_dos_wc,
    'fleur_band_wc': plot_fleur_band_wc,
    'FleurBandWorkChain': plot_fleur_band_wc,
    #'fleur_corehole_wc' : plot_fleur_corehole_wc,
    #'fleur_initial_cls_wc' : plot_fleur_initial_cls_wc
}


def clear_dict_empty_lists(to_clear_dict):
    """
    Removes entries from a nested dictionary which are empty lists.

    param to_clear_dict dict: python dictionary which should be 'compressed'
    return new_dict dict: compressed python dict version of to_clear_dict

    Hints: recursive
    """
    new_dict = {}
    if not to_clear_dict:
        return new_dict

    if not isinstance(to_clear_dict, dict):
        return to_clear_dict

    for key, value in six.iteritems(to_clear_dict):
        if value:
            new_value = clear_dict_empty_lists(value)
            if new_value:
                new_dict[key] = new_value
    return new_dict
