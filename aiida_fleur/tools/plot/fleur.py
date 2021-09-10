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

from pprint import pprint
import numpy as np
#import matplotlib.pyplot as pp
#from masci_tools.vis.plot_methods import *
from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.orm import WorkChainNode
from aiida.orm import Node, Dict
from aiida.common.exceptions import UniquenessError
from aiida_fleur.common.constants import HTR_TO_EV

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

    save = kwargs.pop('save', False)
    show_dict = kwargs.pop('show_dict', False)
    show = kwargs.pop('show', True)
    backend = kwargs.pop('backend', 'matplotlib')

    all_plots = []
    for arg in args:
        if isinstance(arg, list):
            # try plot together
            p1 = plot_fleur_mn(arg, save=save, show=show, backend=backend, **kwargs)
        else:
            #print(arg)
            # plot alone
            p1 = plot_fleur_sn(arg, show_dict=show_dict, show=show, save=save, backend=backend, **kwargs)
        all_plots.append(p1)

    return all_plots


def plot_fleur_sn(node, show_dict=False, **kwargs):
    """
    This methods takes any single AiiDA node and starts the standard visualization for
    if it finds one
    """

    plot_nodes, workflow_name, _ = classify_node(node)

    if show_dict:
        pprint(plot_nodes[0])

    try:
        plotf = FUNCTIONS_DICT[workflow_name]
    except KeyError as exc:
        raise ValueError('Sorry, I do not know how to visualize'
                         f' this node in plot_fleur: {workflow_name} {node}') from exc

    plot_result = plotf(*plot_nodes, **kwargs)

    return plot_result


def plot_fleur_mn(nodelist, **kwargs):
    """
    This methods takes any amount of AiiDA node as a list and starts
    the standard visualisation for it, if it finds one.

    Some nodes types it tries to display together if it knows how to.
    and if they are given as a list.

    param: save showed the plots be saved automatically

    """
    from collections import defaultdict
    ###
    # Things to plot together
    all_nodes = defaultdict(list)
    node_labels = defaultdict(list)
    ###

    if not isinstance(nodelist, list):
        raise ValueError(f'The nodelist provided: {nodelist}, type {type(nodelist)} is not a list. ')

    node_labels = []
    for node in nodelist:
        try:
            plot_nodes, workflow_name, label = classify_node(node)
        except ValueError as exc:
            print(f'Failed to classify node {node}: {exc}' 'Skipping this one')
            continue

        all_nodes[workflow_name].append(plot_nodes)
        node_labels[workflow_name].append(label)

    all_plot_res = []
    for workflow_name, plot_nodes in all_nodes.items():
        try:
            plotf = FUNCTIONS_DICT[workflow_name]
        except KeyError:
            print('Sorry, I do not know how to visualize'
                  f' these nodes in plot_fleur (mulitplot): {workflow_name} {plot_nodes}')
            continue

        #Convert to tuple of lists
        plot_nodes = zip(*plot_nodes)

        plot_res = plotf(*plot_nodes, labels=node_labels, **kwargs)
        all_plot_res.append(plot_res)

    return all_plot_res


def classify_node(node):
    """
    Classify the given node and select, which nodes should be passed to the visualization
    function for the node.

    :param node: Aiida node or integer of the pk or str of the uuid

    :returns: tuple of nodes to pass to the corresponding visualization function,
              name of the workflow and label of the node
    """

    #Define any additional node hat should be passed to the plotting function
    ADDITIONAL_OUTPUTS = {'FleurBandDosWorkChain': ('last_calc_retrieved',)}

    if isinstance(node, (int, str)):
        node = load_node(node)

    if not isinstance(node, Node):
        raise ValueError(f'Given node {node} is not an AiiDA object')

    label = node.label

    params = None
    if isinstance(node, WorkChainNode):
        output_list = node.get_outgoing().all()
        for out_link in output_list:
            if 'output_' in out_link.link_label:
                if 'wc' in out_link.link_label or 'wf' in out_link.link_label:
                    if 'para' in out_link.link_label:  # We are just looking for parameter
                        #nodes, structures, bands, dos and so on we tread different
                        params = out_link.node  # we only visualize last output node
    elif isinstance(node, Dict):
        params = node
        workflow = params.get_incoming(node_class=WorkChainNode).all()
        n_parents = len(workflow)
        if n_parents != 1:
            raise UniquenessError(f'Parameter node {params} has no unique WorkChainNode parent')
        node = workflow[0].node

    if isinstance(params, Dict):
        parameter_dict = params.get_dict()
        workflow_name = parameter_dict.get('workflow_name', None)
    else:
        raise ValueError(f'I do not know how to visualize this node: {node}')

    outputs = (parameter_dict,) + tuple(node.get_outgoing().get_node_by_label(out_label)
                                        for out_label in ADDITIONAL_OUTPUTS.get(workflow_name, tuple()))

    return outputs, workflow_name, label


###########################
## general plot routine  ##
###########################


def plot_fleur_scf_wc(nodes, labels=None, save=False, show=True, backend='bokeh', **kwargs):
    """
    This methods takes an AiiDA output parameter node or a list from a scf workchain and
    plots number of iteration over distance and total energy
    """
    if backend == 'bokeh':
        from masci_tools.vis.bokeh_plots import plot_convergence_results_m
    else:
        from masci_tools.vis.plot_methods import plot_convergence_results_m

    if not isinstance(nodes, list):
        nodes = [nodes]

    if labels is None:
        labels = [node.pk for node in nodes]

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

    plot_res = plot_convergence_results_m(iterations,
                                          distance_all_n,
                                          total_energy_n,
                                          plot_label=labels,
                                          nodes=nodes_pk,
                                          modes=modes,
                                          show=show,
                                          **kwargs)
    return plot_res


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
        data = np.loadtxt(path_to_dosfile, skiprows=0)

        energy = data[..., 0]
        dos_labels = ['Total', 'Interstitial', 'MT-Total']
        dos_data = [data[:, 1], data[:, 2], data[:, 1] - data[:, 2]]

        p1 = plot_dos(energy, dos_data, show=show, plot_labels=dos_labels)
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
            plot_lattice_constant(scaling, Total_energy, multi=True, plot_label=plotlables, show=show, **kwargs)
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
    p1 = plot_lattice_constant(scaling, Total_energy, show=show, **kwargs)  #, fit_y)
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
        data = np.loadtxt(path_to_bands_file, skiprows=0)
        kdata = data[..., 0]
        evdata = data[..., 1]
        p1 = plot_bands(kdata, evdata, special_kpoints=kpath)
    else:
        print('Could not retrieve dos file path from output node')

    return p1


def plot_fleur_banddos_wc(param_node,
                          file_node,
                          labels=None,
                          save=False,
                          show=True,
                          backend='bokeh',
                          hdf_recipe=None,
                          **kwargs):
    """
    This methods takes an AiiDA output parameter node and retrieved files from a banddos
    workchain and plots the bandstructure/DOS
    """
    from masci_tools.io.parsers.hdf5 import HDF5Reader
    from masci_tools.io.parsers.hdf5.recipes import FleurDOS, FleurBands
    from masci_tools.vis.fleur import plot_fleur_bands, plot_fleur_dos

    if isinstance(param_node, list):
        if len(param_node) > 2:
            return  # TODO
        else:
            param_node = param_node[0]
            file_node = file_node[0]

    output_d = param_node.get_dict()
    mode = output_d.get('mode')

    if mode is None:
        raise ValueError('Could not retrieve mode from output node')

    if hdf_recipe is None:
        if mode == 'dos':
            hdf_recipe = FleurDOS
        else:
            hdf_recipe = FleurBands

    if 'banddos.hdf' not in file_node.list_object_names():
        raise ValueError('No banddos.hdf file found')

    with file_node.open('banddos.hdf', mode='rb') as hdf_file:
        with HDF5Reader(hdf_file) as h5reader:
            data, attributes = h5reader.read(recipe=hdf_recipe)

    if mode == 'dos':
        plot_res = plot_fleur_dos(data, attributes, backend=backend, save=save, show=show, **kwargs)
    else:
        plot_res = plot_fleur_bands(data, attributes, backend=backend, save=save, show=show, **kwargs)

    return plot_res


def plot_fleur_relax_wc(node, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes an AiiDA output parameter node from a relaxation
    workchain and plots some information about atom movements and forces
    """
    if labels is None:
        labels = []

    raise NotImplementedError


def plot_fleur_corehole_wc(nodes, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes AiiDA output parameter nodes from a corehole
    workchain and plots some information about Binding energies
    """

    if labels is None:
        labels = []

    raise NotImplementedError


def plot_fleur_initial_cls_wc(nodes, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes AiiDA output parameter nodes from a FleurInitialCLSWorkChain
    workchain and plots some information about corelevel shifts.
    (Spectra)
    """
    if labels is None:
        labels = []

    raise NotImplementedError


def plot_fleur_orbcontrol_wc(node, labels=None, save=False, show=True, **kwargs):
    """
    This methods takes AiiDA output parameter nodes from a orbcontrol
    workchain and plots the energy of the individual configurations.
    """
    from masci_tools.vis.common import scatter

    if labels is None:
        labels = []

    if isinstance(node, list):
        if len(node) >= 2:
            return  # TODO
        else:
            node = node[0]

    output_d = node.get_dict()

    total_energy = output_d['total_energy']

    #Divide into converged and non converged
    converged_energy = np.array(
        [total_energy[i] for i in output_d['successful_configs'] if i not in output_d['non_converged_configs']])
    converged_configs = [i for i in output_d['successful_configs'] if i not in output_d['non_converged_configs']]
    non_converged_energy = np.array([total_energy[i] for i in output_d['non_converged_configs']])

    #Convert to relative eV
    refE = min(converged_energy)
    converged_energy -= refE
    non_converged_energy -= refE

    converged_energy *= HTR_TO_EV
    non_converged_energy *= HTR_TO_EV

    if kwargs.get('backend', 'matplotlib'):
        if 'plot_label' not in kwargs:
            kwargs['plot_label'] = ['converged', 'not converged']
    else:
        if 'legend_label' not in kwargs:
            kwargs['legend_label'] = ['converged', 'not converged']

    p1 = scatter([converged_configs, output_d['non_converged_configs']], [converged_energy, non_converged_energy],
                 xlabel='Configurations',
                 ylabel=r'$E_{rel}$ [eV]',
                 title='Results for orbcontrol node',
                 linestyle='',
                 colors=['darkblue', 'darkred'],
                 markersize=10.0,
                 legend=True,
                 legend_option={'loc': 'upper right'},
                 save=save,
                 show=show,
                 **kwargs)
    return p1


FUNCTIONS_DICT = {
    'fleur_scf_wc': plot_fleur_scf_wc,  #support of < 1.0 release
    'fleur_eos_wc': plot_fleur_eos_wc,  #support of < 1.0 release
    'FleurScfWorkChain': plot_fleur_scf_wc,
    'FleurEosWorkChain': plot_fleur_eos_wc,
    'fleur_dos_wc': plot_fleur_dos_wc,
    'fleur_band_wc': plot_fleur_band_wc,
    'FleurBandWorkChain': plot_fleur_band_wc,
    'FleurBandDosWorkChain': plot_fleur_banddos_wc,
    #'fleur_corehole_wc' : plot_fleur_corehole_wc,  #support of < 1.5 release
    #'fleur_initial_cls_wc' : plot_fleur_initial_cls_wc,  #support of < 1.5 release
    #'FleurInitialCLSWorkChain' : plot_fleur_initial_cls_wc,
    #'FleurCoreholeWorkChain' :  plot_fleur_corehole_wc,
    'FleurOrbControlWorkChain': plot_fleur_orbcontrol_wc,
}
