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
import warnings
import numpy as np
import re

from aiida.common.links import LinkType
from aiida.orm import load_node, Node, WorkChainNode, Dict

from masci_tools.util.constants import HTR_TO_EV
from masci_tools.vis.common import set_defaults, set_default_backend, show_defaults, save_defaults, load_defaults, reset_defaults

__all__ = ('plot_fleur', 'set_defaults', 'set_default_backend', 'show_defaults', 'save_defaults', 'load_defaults',
           'reset_defaults')


def plot_fleur(*args, save=False, show_dict=False, show=True, backend=None, **kwargs):
    """
    Plot single or multiple Fleur WorkChainNodes. Can be started from the Workchain or output parameters (Dict) node.
    The following WorkChains are supported:

        - `FleurSCFWorkChain`: Plots the convergence of energy and distance for the calculation
        - `FleurEOSWorkChain`: Plots the total energy vs. volume for the calculated scalings
        - `FleurBandDosWorkChain`: Plot the bandstructure/DOS calculated
        - `FleurOrbControlWorkChain`: Plot the distribution of total energies for all run calculations

    This method takes any amount of AiiDA nodes as positional arguments and starts
    the standard visualisation either as single or multiple nodes in one visualisation (if supported and nodes provided in a list).
    i.e ``plot_fleur(123, [124,125], uuid)``

    :param save: bool if True the produced plots are saved to file
    :param show: bool if True the produced plots are immediately shown
    :param show_dict: bool if True the parameter/Dict node of the WorkChain is printed 9for single visualizations)
    :param backend: str, 'bokeh' or else 'matplotlib'/'mpl' (default None uses default in masci-tools routines)

    Kwargs are passed on to the plotting functions for each WorkChainNode

    :returns: a list of plot objects produced by the used plotting library for further modification or handling
              this might be used for a quick dashboard build.
    """

    all_plots = []
    for arg in args:
        if isinstance(arg, list):
            # try plot together
            p1 = plot_fleur_mn(arg, save=save, show=show, backend=backend, **kwargs)
            if len(p1) == 1:
                p1 = p1[0]
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
    from collections.abc import Iterable
    ###
    # Things to plot together
    all_nodes = defaultdict(list)
    node_labels = defaultdict(list)
    ###

    if not isinstance(nodelist, list):
        raise ValueError(f'The nodelist provided: {nodelist}, type {type(nodelist)} is not a list.')

    for node in nodelist:

        try:
            plot_nodes, workflow_name, label = classify_node(node)
        except ValueError as exc:
            warnings.warn(f'Failed to classify node {node}: {exc}\n'
                          'Skipping this one')
            continue

        all_nodes[workflow_name].append(plot_nodes)
        node_labels[workflow_name].append(label)

    all_plot_res = []
    for workflow_name, plot_nodes in all_nodes.items():
        try:
            plotf = FUNCTIONS_DICT[workflow_name]
        except KeyError:
            warnings.warn('Sorry, I do not know how to visualize'
                          f' these nodes in plot_fleur (multiplot): {workflow_name} {plot_nodes}')
            continue

        #Convert to tuple of lists
        plot_nodes = zip(*plot_nodes)
        plot_nodes = tuple(list(nodes) for nodes in plot_nodes)
        labels = node_labels[workflow_name]

        plot_res = plotf(*plot_nodes, labels=labels, **kwargs)
        if isinstance(plot_res, Iterable):
            all_plot_res.extend(plot_res)
        else:
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
    ADDITIONAL_OUTPUTS = {
        'FleurBandDosWorkChain': ('banddos_calc__retrieved',),
        'FleurCFCoeffWorkChain': ('output_cfcoeff_wc_charge_densities', 'output_cfcoeff_wc_potentials')
    }

    if isinstance(node, (int, str)):
        node = load_node(node)

    if not isinstance(node, Node):
        raise ValueError(f'Given node {node} is not an AiiDA object')

    label = node.label

    parameter_node = None
    workchain_node = None
    if isinstance(node, WorkChainNode):
        workchain_node = node
        output_list = workchain_node.get_outgoing(link_type=LinkType.RETURN).all()
        for out_link in output_list:
            if re.fullmatch('output_.+_w[cf]_para', out_link.link_label):
                parameter_node = out_link.node  # we only visualize last output node
    elif isinstance(node, Dict):
        parameter_node = node

    if parameter_node is None:
        raise ValueError(f'I do not know how to visualize this node: {node}')

    parameter_dict = parameter_node.get_dict()
    workflow_name = parameter_dict.get('workflow_name', None)

    add_outputs = ADDITIONAL_OUTPUTS.get(workflow_name, tuple())
    add_nodes = tuple()
    if add_outputs:
        if workchain_node is None:
            workchain_node = parameter_node.get_incoming(node_class=WorkChainNode).one().node
        add_nodes = tuple(workchain_node.get_outgoing().get_node_by_label(out_label) for out_label in add_outputs)

    outputs = (parameter_node,) + add_nodes

    return outputs, workflow_name, label


###########################
## general plot routine  ##
###########################


def plot_fleur_scf_wc(nodes, labels=None, save=False, show=True, backend='bokeh', **kwargs):
    """
    This methods takes an AiiDA output parameter node or a list from a scf workchain and
    plots number of iteration over distance and total energy
    """
    from masci_tools.vis.common import convergence_plot

    if not isinstance(nodes, list):
        nodes = [nodes]

    if labels is None:
        labels = [node.pk for node in nodes]

    all_energies = []
    all_distances = []
    all_iterations = []
    modes = []

    for node in nodes:
        iteration = []
        output_d = node.get_dict()
        total_energy = output_d.get('total_energy_all')
        if not total_energy:
            warnings.warn(f'No total energy data found, skip this node: {node}')
            continue

        distance = output_d.get('distance_charge_all')
        num_iterations = output_d.get('iterations_total')
        if not distance:
            warnings.warn(f'No distance_charge_all data found, skip this node: {node}')
            continue
        if not num_iterations:
            warnings.warn(f'No iteration_total data found, skip this node: {node}')
            continue

        mode = output_d.get('conv_mode')
        for i in range(1, len(total_energy) + 1):
            iteration.append(num_iterations - len(total_energy) + i)

        if len(distance) == 2 * len(total_energy):  # not sure if this is best solution
            # magnetic calculation, we plot only spin 1 for now.
            distance = [distance[j] for j in range(0, len(distance), 2)]

        all_energies.append(total_energy)
        all_iterations.append(iteration)
        all_distances.append(distance)
        modes.append(mode)

    add_args = {}
    if backend == 'bokeh':
        add_args['legend_label'] = labels
    else:
        add_args['plot_label'] = labels

    plot_res = convergence_plot(all_iterations,
                                all_distances,
                                all_energies,
                                show=show,
                                save_plots=save,
                                drop_last_iteration=any(mode == 'force' for mode in modes),
                                backend=backend,
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


def plot_fleur_eos_wc(nodes, labels=None, save=False, show=True, backend='bokeh', **kwargs):
    """
    This methods takes an AiiDA output parameter node from a equation of states
    workchain and plots a simple scaling vs volume plot
    """
    from masci_tools.vis.common import eos_plot

    if not isinstance(nodes, list):
        nodes = [nodes]

    energy = []
    scaling = []
    default_labels = []

    for i, nd in enumerate(nodes):
        outpara = nd.get_dict()
        volume_gs = outpara.get('volume_gs')
        scale_gs = outpara.get('scaling_gs')
        total_e = outpara.get('total_energy')
        if len(nodes) >= 2:
            total_e_norm = np.array(total_e) - total_e[0]
            energy.append(total_e_norm)
        else:
            energy.append(total_e)
        scaling.append(outpara.get('scaling'))
        default_labels.append(f'gs_vol: {volume_gs:.3} A^3, gs_scale {scale_gs:.3}, data {i}')

    labels = default_labels

    add_args = {}
    if backend == 'bokeh':
        add_args['legend_label'] = labels
    else:
        add_args['plot_label'] = labels

    plot_res = eos_plot(scaling, energy, show=show, save_plots=save, backend=backend, **add_args, **kwargs)

    return plot_res


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
        plot_res = plot_fleur_dos(data, attributes, backend=backend, save_plots=save, show=show, **kwargs)
    else:
        plot_res = plot_fleur_bands(data, attributes, backend=backend, save_plots=save, show=show, **kwargs)

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


def plot_fleur_orbcontrol_wc(nodes,
                             labels=None,
                             save=False,
                             show=True,
                             line_labels=None,
                             backend='matplotlib',
                             size_func=None,
                             **kwargs):
    """
    This methods takes AiiDA output parameter nodes from a orbcontrol
    workchain and plots the energy of the individual configurations.
    """
    from masci_tools.vis.common import scatter, PlotBackend
    from itertools import chain

    if labels is None:
        labels = []

    if not isinstance(nodes, list):
        nodes = [nodes]

    offset = 0
    lines = []
    converged_configs = []
    converged_energy = []
    non_converged_configs = []
    non_converged_energy = []
    converged_size_data = []
    non_converged_size_data = []
    for node in nodes:
        outputs = node.get_dict()

        total_energy = outputs['total_energy']

        non_converged = outputs['non_converged_configs']
        converged = [i for i in outputs['successful_configs'] if i not in non_converged]

        converged_configs.extend(i + offset for i in converged)
        converged_energy.extend(total_energy[i] for i in converged)

        non_converged_configs.extend(i + offset for i in non_converged)
        non_converged_energy.extend(total_energy[i] for i in non_converged)

        if size_func is not None:
            #The size_func operates on the original workchain node (to make introspection easier)
            wc_node = node.get_incoming(link_type=LinkType.RETURN).one().node
            size = size_func(wc_node)
            if not isinstance(size, list) or len(size) != len(total_energy):
                raise ValueError(f'Wrong length of size data. Expected {len(total_energy)} entries: '
                                 f'Got {len(size) if isinstance(size, list) else size}')

            converged_size_data.extend(size[i] for i in converged)
            non_converged_size_data.extend(size[i] for i in non_converged)

        offset += max(chain(converged, non_converged, outputs['failed_configs'])) + 1
        lines.append(offset - 0.5)

    #Convert to relative eV
    refE = min(converged_energy)
    converged_energy = np.array(converged_energy) - refE
    non_converged_energy = np.array(non_converged_energy) - refE

    converged_energy *= HTR_TO_EV
    non_converged_energy *= HTR_TO_EV

    backend = PlotBackend.from_str(backend)
    if backend == PlotBackend.mpl:
        kwargs.setdefault('plot_label', ['converged', 'not converged'])
    else:
        kwargs.setdefault('legend_label', ['converged', 'not converged'])

    kwargs.setdefault('xlabel', 'Configurations')
    kwargs.setdefault('ylabel', r'$E_{rel}$ [eV]')
    kwargs.setdefault('title', 'Results for orbcontrol node')
    kwargs.setdefault('legend_options', {'loc': 'upper right'})
    kwargs.setdefault('markersize', 10.0)
    kwargs.setdefault('legend', True)
    if len(lines) > 1:
        kwargs.setdefault('lines', {'vertical': lines[:-1]})
    if size_func is not None:
        kwargs.setdefault('size_data', [converged_size_data, non_converged_size_data])

    p1 = scatter([converged_configs, non_converged_configs], [converged_energy, non_converged_energy],
                 color=['darkblue', 'darkred'],
                 save_plots=save,
                 show=show,
                 backend=backend,
                 **kwargs)

    if line_labels and backend == PlotBackend.mpl:
        for label, pos in zip(line_labels, [0] + [p + 0.25 for p in lines]):
            p1.annotate(label, xy=(pos, 0.95), xycoords=('data', 'axes fraction'), ha='left', va='center', size=16)

    return p1


def plot_fleur_cfcoeff_wc(param_node,
                          cdn_node,
                          pot_node,
                          mode='calculation',
                          labels=None,
                          save=False,
                          show=True,
                          backend='matplotlib',
                          **kwargs):
    """
    Plot the CFCoeff workchain. Either plot the used potentials/charge densities or the angular dependence
    of the resulting potential
    """
    from masci_tools.tools.cf_calculation import plot_crystal_field_calculation, plot_crystal_field_potential
    from aiida_fleur.workflows.cfcoeff import reconstruct_cfcalculation, reconstruct_cfcoeffcients

    if isinstance(param_node, list):
        if len(param_node) > 2:
            return  # TODO
        else:
            param_node = param_node[0]
            cdn_node = cdn_node[0]
            pot_node = pot_node[0]

    output_d = param_node.get_dict()

    if mode not in ('calculation', 'potential'):
        raise ValueError(f'Invalid mode for plotting: {mode}')

    if backend != 'matplotlib':
        raise ValueError('Changing backend not yet implemented for CFCoeffWorkChain')

    plot_res = []
    if mode == 'potential':
        for atom_type in output_d['cf_coefficients_atomtypes']:
            coefficients = reconstruct_cfcoeffcients(output_d, atom_type)
            plot_res.append(plot_crystal_field_potential(coefficients, save=save, show=show, **kwargs))
    else:
        for atom_type in output_d['cf_coefficients_atomtypes']:
            cfcalc = reconstruct_cfcalculation(cdn_node, pot_node, atom_type)
            plot_res.append(plot_crystal_field_calculation(cfcalc, save=save, show=show, **kwargs))

    return plot_res


FUNCTIONS_DICT = {
    'fleur_scf_wc': plot_fleur_scf_wc,  #support of < 1.0 release
    'fleur_eos_wc': plot_fleur_eos_wc,  #support of < 1.0 release
    'FleurScfWorkChain': plot_fleur_scf_wc,
    'FleurEosWorkChain': plot_fleur_eos_wc,
    'fleur_dos_wc': plot_fleur_dos_wc,
    'fleur_band_wc': plot_fleur_band_wc,
    'FleurBandWorkChain': plot_fleur_band_wc,
    'FleurBandDosWorkChain': plot_fleur_banddos_wc,
    'FleurCFCoeffWorkChain': plot_fleur_cfcoeff_wc,
    #'fleur_corehole_wc' : plot_fleur_corehole_wc,  #support of < 1.5 release
    #'fleur_initial_cls_wc' : plot_fleur_initial_cls_wc,  #support of < 1.5 release
    #'FleurInitialCLSWorkChain' : plot_fleur_initial_cls_wc,
    #'FleurCoreholeWorkChain' :  plot_fleur_corehole_wc,
    'FleurOrbControlWorkChain': plot_fleur_orbcontrol_wc,
}
