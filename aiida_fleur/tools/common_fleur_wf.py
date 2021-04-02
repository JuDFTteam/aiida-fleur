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
In here we put all things (methods) that are common to workflows AND
depend on AiiDA classes, therefore can only be used if the dbenv is loaded.
Util that does not depend on AiiDA classes should go somewhere else.
"""

from __future__ import absolute_import
from __future__ import print_function
import six

from aiida.orm import Node, load_node, Bool
from aiida.plugins import DataFactory, CalculationFactory


def is_code(code):
    """
    Test if the given input is a Code node, by object, id, uuid, or pk
    if yes returns a Code node in all cases
    if no returns None
    """
    from aiida.orm import Code
    from aiida.common.exceptions import NotExistent, MultipleObjectsError, InputValidationError

    if isinstance(code, Code):
        return code

    try:
        pk = int(code)
    except ValueError:
        codestring = str(code)
        try:
            code = Code.get_from_string(codestring)
        except NotExistent:
            try:
                code = load_node(codestring)
            except NotExistent:
                code = None
        except (InputValidationError, MultipleObjectsError):
            code = None
    else:
        try:
            code = load_node(pk)
        except NotExistent:
            code = None

    if isinstance(code, Code):
        return code
    else:
        return None


def get_inputs_fleur(code,
                     remote,
                     fleurinp,
                     options,
                     label='',
                     description='',
                     settings=None,
                     serial=False,
                     only_even_MPI=False):
    '''
    Assembles the input dictionary for Fleur Calculation. Does not check if a user gave
    correct input types, it is the work of FleurCalculation to check it.

    :param code: FLEUR code of Code type
    :param remote: remote_folder from the previous calculation of RemoteData type
    :param fleurinp: FleurinpData object representing input files
    :param options: calculation options that will be stored in metadata
    :param label: a string setting a label of the CalcJob in the DB
    :param description: a string setting a description of the CalcJob in the DB
    :param settings: additional settings of Dict type
    :param serial: True if run a calculation in a serial mode

    Example of use::

        inputs_build = get_inputs_inpgen(structure, inpgencode, options, label,
                                         description, params=params)
        future = self.submit(inputs_build)


    '''
    Dict = DataFactory('dict')
    inputs = {}
    if isinstance(only_even_MPI, Bool):
        inputs['only_even_MPI'] = only_even_MPI
    else:
        inputs['only_even_MPI'] = Bool(only_even_MPI)

    if remote:
        inputs['parent_folder'] = remote
    if code:
        inputs['code'] = code
    if fleurinp:
        inputs['fleurinpdata'] = fleurinp

    if description:
        inputs['description'] = description
    else:
        inputs['description'] = ''
    if label:
        inputs['label'] = label
    else:
        inputs['label'] = ''
    # TODO check  if code is parallel version?
    if serial:
        if not options:
            options = {}
        options['withmpi'] = False  # for now
        # TODO not every machine/scheduler type takes number of machines
        #  lsf takes number of total_mpi_procs,slurm and psb take num_machines,\
        # also a full will run here mpi on that node... also not what we want.ß
        options['resources'] = {'num_machines': 1, 'num_mpiprocs_per_machine': 1}
    else:
        options['withmpi'] = True

    custom_commands = options.get('custom_scheduler_commands', '')
    options['custom_scheduler_commands'] = custom_commands

    if settings:
        if isinstance(settings, Dict):
            inputs['settings'] = settings
        else:
            inputs['settings'] = Dict(dict=settings)

    if options:
        inputs['options'] = Dict(dict=options)

    return inputs


def get_inputs_inpgen(structure, inpgencode, options, label='', description='', settings=None, params=None, **kwargs):
    '''
    Assembles the input dictionary for Fleur Calculation.

    :param structure: input structure of StructureData type
    :param inpgencode: inpgen code of Code type
    :param options: calculation options that will be stored in metadata
    :param label: a string setting a label of the CalcJob in the DB
    :param description: a string setting a description of the CalcJob in the DB
    :param params: input parameters for inpgen code of Dict type

    Example of use::

        inputs_build = get_inputs_inpgen(structure, inpgencode, options, label,
                                         description, params=params)
        future = self.submit(inputs_build)

    '''

    FleurinpProcess = CalculationFactory('fleur.inpgen')
    inputs = FleurinpProcess.get_builder()

    if structure:
        inputs.structure = structure
    if inpgencode:
        inputs.code = inpgencode
    if params:
        inputs.parameters = params
    if settings:
        inputs.settings = settings
    if description:
        inputs.metadata.description = description
    else:
        inputs.metadata.description = ''

    if label:
        inputs.metadata.label = label
    else:
        inputs.metadata.label = ''

    if not options:
        options = {}
    # inpgen run always serial
    options['withmpi'] = False
    options['resources'] = {'num_machines': 1, 'num_mpiprocs_per_machine': 1}

    if options:
        inputs.metadata.options = options

    # Currently this does not work, find out howto...
    # for key, val in kwargs.items():
    #    inputs[key] = val

    return inputs


def test_and_get_codenode(codenode, expected_code_type, use_exceptions=False):
    """
    Pass a code node and an expected code (plugin) type. Check that the
    code exists, is unique, and return the Code object.

    :param codenode: the name of the code to load (in the form label@machine)
    :param expected_code_type: a string with the plugin that is expected to
      be loaded. In case no plugins exist with the given name, show all existing
      plugins of that type
    :param use_exceptions: if True, raise a ValueError exception instead of
      calling sys.exit(1)
    :return: a Code object
    """
    import sys
    from aiida.common.exceptions import NotExistent
    from aiida.orm import Code

    try:
        if codenode is None or not isinstance(codenode, Code):
            raise ValueError
        code = codenode
        if code.get_input_plugin_name() != expected_code_type:
            raise ValueError
    except ValueError as exc:
        from aiida.orm.querybuilder import QueryBuilder
        qb = QueryBuilder()
        qb.append(Code, filters={'attributes.input_plugin': {'==': expected_code_type}}, project='*')

        valid_code_labels = ['{}@{}'.format(c.label, c.computer.name) for [c] in qb.all()]

        if valid_code_labels:
            msg = ('Given Code node is not of expected code type.\n'
                   'Valid labels for a {} executable are:\n'.format(expected_code_type))
            msg += '\n'.join('* {}'.format(l) for l in valid_code_labels)

            if use_exceptions:
                raise ValueError(msg) from exc
            else:
                print(msg)  # , file=sys.stderr)
                sys.exit(1)
        else:
            msg = ('Code not valid, and no valid codes for {}.\n'
                   'Configure at least one first using\n'
                   '    verdi code setup'.format(expected_code_type))
            if use_exceptions:
                raise ValueError(msg) from exc
            else:
                print(msg)  # , file=sys.stderr)
                sys.exit(1)

    return code


def get_kpoints_mesh_from_kdensity(structure, kpoint_density):
    """
    params: structuredata, Aiida structuredata
    params: kpoint_density

    returns: tuple (mesh, offset)
    returns: kpointsdata node
    """
    KpointsData = DataFactory('array.kpoints')
    kp = KpointsData()
    kp.set_cell_from_structure(structure)
    density = kpoint_density  # 1/A
    kp.set_kpoints_mesh_from_density(density)
    mesh = kp.get_kpoints_mesh()
    return mesh, kp


# test
# print(get_kpoints_mesh_from_kdensity(load_node(structure(120)), 0.1))
# (([33, 33, 18], [0.0, 0.0, 0.0]), <KpointsData: uuid: cee9d05f-b31a-44d7-aa72-30a406712fba (unstored)>)
# mesh, kp = get_kpoints_mesh_from_kdensity(structuredata, 0.1)
# print mesh[0]

# TODO maybe allow lists of uuids in workchain dict, or write a second funtion for this,...
# The question is how do get the 'enthalpy for a reaction out of my database?
# where I have redundant calculations or calculations with different parameters...
# are total energies comparable?
# -> as long as the same scheme ist used (all GGA or all GGA+U)
# total energies are compareable and the gibs enthalpy is approximately the
# total energy difference
# there are tricks to also compare mixed energies, with experimental fits
# for binary reactions, where both is needed


def determine_favorable_reaction(reaction_list, workchain_dict):
    """
    Finds out with reaction is more favorable by simple energy standpoints

    # TODO check physics
    reaction list: list of reaction strings
    workchain_dict = {'Be12W' : uuid_wc or output, 'Be2W' : uuid, ...}

    return dictionary that ranks the reactions after their enthalpy

    TODO: refactor aiida part out of this, leaving an aiida independent part and one
    more universal
    """
    from aiida.engine import WorkChain
    from aiida_fleur.tools.common_fleur_wf_util import get_enhalpy_of_equation
    # for each reaction get the total energy sum
    # make sure to use the right multipliers...
    # then sort the given list from (lowest if negativ energies to highest)
    energy_sorted_reactions = []
    formenergy_dict = {}
    for compound, uuid in six.iteritems(workchain_dict):
        # TODO ggf get formation energy from output node, or extras
        if isinstance(uuid, float):  # allow to give values
            formenergy_dict[compound] = uuid
            continue
        n = load_node(uuid)
        extras = n.get_extras()  # sadly there is no get(,) method...
        try:
            formenergy = extras.get('formation_energy', None)
        except KeyError:
            formenergy = None
        if not formenergy:  # test if 0 case ok
            if isinstance(n, WorkChain):  # TODO: untested for aiida > 1.0
                plabel = n.get_attr('_process_label')
                if plabel == 'fleur_initial_cls_wc':
                    try:
                        ouputnode = n.out.output_initial_cls_wc_para.get_dict()
                    except AttributeError:
                        try:
                            ouputnode = n.out.output_inital_cls_wc_para.get_dict()
                        except (AttributeError, KeyError, ValueError):  # TODO: Check this
                            ouputnode = None
                            formenergy = None
                            print(('WARNING: output node of {} not found. I skip'.format(n)))
                            continue
                    formenergy = ouputnode.get('formation_energy')
                    # TODO is this value per atom?
                else:  # check if corehole wc?
                    pass

        formenergy_dict[compound] = formenergy

    for reaction_string in reaction_list:
        ent_peratom = get_enhalpy_of_equation(reaction_string, formenergy_dict)
        print(ent_peratom)
        energy_sorted_reactions.append([reaction_string, ent_peratom])
    energy_sorted_reactions = sorted(energy_sorted_reactions, key=lambda ent: ent[1])
    return energy_sorted_reactions


def performance_extract_calcs(calcs):
    """
    Extracts some runtime and system data from given fleur calculations

    :params calcs: list of calculation nodes/pks/or uuids. Fleur calc specific

    :returns data_dict: dictionary, dictionary of arrays with the same length,
                        from with a panda frame can be created.

    Note: Is not the fastest for many calculations > 1000.
    """
    data_dict = {
        u'n_symmetries': [],
        u'n_spin_components': [],
        u'n_kpoints': [],
        u'n_iterations': [],
        u'walltime_sec': [],
        u'walltime_sec_per_it': [],
        u'n_iterations_total': [],
        u'density_distance': [],
        u'computer': [],
        u'n_atoms': [],
        u'kmax': [],
        u'cost': [],
        u'costkonstant': [],
        u'walltime_sec_cor': [],
        u'total_cost': [],
        u'fermi_energy': [],
        u'bandgap': [],
        u'energy': [],
        u'force_largest': [],
        u'ncores': [],
        u'pk': [],
        u'uuid': [],
        u'serial': [],
        u'resources': []
    }
    count = 0
    for calc in calcs:
        if not isinstance(calc, Node):
            calc = load_node(calc)
        count = count + 1
        pk = calc.pk
        print((count, pk))
        res = calc.res
        res_keys = list(res)
        try:
            efermi = res.fermi_energy
        except AttributeError:
            print(('skipping {}, {}'.format(pk, calc.uuid)))
            efermi = -10000
            continue  # we skip these entries
        try:
            gap = res.bandgap
        except AttributeError:
            gap = -10000
            print(('skipping 2 {}, {}'.format(pk, calc.uuid)))
            continue

        try:
            energy = res.energy
        except AttributeError:
            energy = 0.0
            print(('skipping 3 {}, {}'.format(pk, calc.uuid)))
            continue

        data_dict['bandgap'].append(gap)
        data_dict['fermi_energy'].append(efermi)
        data_dict['energy'].append(energy)
        data_dict['force_largest'].append(res.force_largest)
        data_dict['pk'].append(pk)
        data_dict['uuid'].append(calc.uuid)
        data_dict['n_symmetries'].append(res.number_of_symmetries)
        nspins = res.number_of_spin_components
        data_dict['n_spin_components'].append(nspins)
        nkpt = res.number_of_kpoints
        data_dict['n_kpoints'].append(nkpt)
        niter = res.number_of_iterations
        data_dict['n_iterations'].append(niter)
        data_dict['n_iterations_total'].append(res.number_of_iterations_total)

        if u'charge_density' in res_keys:
            data_dict['density_distance'].append(res.charge_density)
        else:  # magnetic, old
            data_dict['density_distance'].append(res.overall_charge_density)

        walltime = res.walltime
        if walltime <= 0:
            # date was not considert yet, we assume one day...
            walltime_new = walltime + 86400
        else:
            walltime_new = walltime

        walltime_periteration = walltime_new / niter

        data_dict['walltime_sec'].append(walltime)
        data_dict['walltime_sec_cor'].append(walltime_new)
        data_dict['walltime_sec_per_it'].append(walltime_periteration)
        cname = calc.computer.name
        data_dict['computer'].append(cname)
        natom = res.number_of_atoms
        data_dict['n_atoms'].append(natom)

        # fleurinp = calc.get_inputs_dict()['fleurinpdata']
        # kmax = fleurinp.inp_dict['calculationSetup']['cutoffs']['Kmax']
        kmax = res.kmax
        data_dict['kmax'].append(kmax)

        cost = calc_time_cost_function(natom, nkpt, kmax, nspins)
        total_cost = cost * niter

        serial = not calc.attributes['withmpi']
        # codename = calc.get_code().label
        # code_col.append(codename)

        # if 'mpi' in codename:
        #    serial = False
        # else:
        #    serial = True
        data_dict['serial'].append(serial)

        resources = calc.attributes['resources']
        mpi_proc = get_mpi_proc(resources)

        c_ratio = cost_ratio(cost, walltime_new, mpi_proc)
        data_dict['resources'].append(resources)
        data_dict['cost'].append(cost)
        data_dict['costkonstant'].append(c_ratio)
        data_dict['total_cost'].append(total_cost)
        data_dict['ncores'].append(mpi_proc)

    return data_dict


def get_mpi_proc(resources):
    """Determine number of total processes from given resource dict"""
    nmachines = resources.get('num_machines', 0)
    total_proc = resources.get('tot_num_mpiprocs', 0)
    if not total_proc:
        if nmachines:
            total_proc = nmachines * resources.get('default_mpiprocs_per_machine', 12)
        else:
            total_proc = resources.get('tot_num_mpiprocs', 24)

    return total_proc


def calc_time_cost_function(natom, nkpt, kmax, nspins=1):
    """Estimates the cost of simulating a single iteration of a system"""
    costs = natom**3 * kmax**3 * nkpt * nspins
    return costs


def calc_time_cost_function_total(natom, nkpt, kmax, niter, nspins=1):
    """Estimates the cost of simulating a all  iteration of a system"""
    costs = natom**3 * kmax**3 * nkpt * nspins * niter
    return costs


def cost_ratio(total_costs, walltime_sec, ncores):
    """Estimates if simulation cost matches resources"""
    ratio = total_costs / (walltime_sec * ncores)
    return ratio


def optimize_calc_options(nodes,
                          mpi_per_node,
                          omp_per_mpi,
                          use_omp,
                          mpi_omp_ratio,
                          fleurinpData=None,
                          kpts=None,
                          sacrifice_level=0.9,
                          only_even_MPI=False):
    """
    Makes a suggestion on parallelisation setup for a particular fleurinpData.
    Only the total number of k-points is analysed: the function suggests ideal k-point
    parallelisation + OMP parallelisation (if required). Note: the total number of used CPUs
    per node will not exceed mpi_per_node * omp_per_mpi.

    Sometimes perfect parallelisation is terms of idle CPUs is not what
    used wanted because it can harm MPI/OMP ratio. Thus the function first chooses first top
    parallelisations in terms of total CPUs used
    (bigger than sacrifice_level * maximal_number_CPUs_possible). Then a parallelisation which is
    the closest to the MPI/OMP ratio is chosen among them and returned.

    :param nodes: maximal number of nodes that can be used
    :param mpi_per_node: an input suggestion of MPI tasks per node
    :param omp_per_mpi: an input suggestion for OMP tasks per MPI process
    :param use_omp: False if OMP parallelisation is not needed
    :param mpi_omp_ratio: requested MPI/OMP ratio
    :param fleurinpData: FleurinpData to extract total number of kpts from
    :param kpts: the total number of kpts
    :param sacrifice_level: sets a level of performance sacrifice that a user can afford for better
                            MPI/OMP ratio.
    :parm only_even_MPI: if set to True, the function does not set MPI to an odd number (if possible)
    :returns nodes, MPI_tasks, OMP_per_MPI, message: first three are parallelisation info and
                                                     the last one is an exit message.
    """
    from sympy.ntheory.factor_ import divisors
    import numpy as np

    cpus_per_node = mpi_per_node * omp_per_mpi
    if fleurinpData:
        modes = fleurinpData.get_fleur_modes()
        kpts = fleurinpData.attributes['inp_dict']['calculationSetup']['bzIntegration']
        if modes['band'] or modes['gw']:
            kpts = kpts['altKPointSet']['count']
        else:
            if 'kPointList' in kpts:
                kpts = kpts['kPointList']['count']
            else:
                kpts = kpts['kPointCount']['count']
        kpts = int(kpts)
    elif not kpts:
        raise ValueError('You must specify either kpts of fleurinpData')
    divisors_kpts = divisors(kpts)
    possible_nodes = [x for x in divisors_kpts if x <= nodes]
    suggestions = []
    for n_n in possible_nodes:
        advise_cpus = [x for x in divisors(kpts // n_n) if x <= cpus_per_node]
        for advised_cpu_per_node in advise_cpus:
            suggestions.append((n_n, advised_cpu_per_node))

    def add_omp(suggestions, only_even_MPI_1):
        """
        Also adds possibility of omp parallelisation
        """
        final_suggestion = []
        for suggestion in suggestions:
            if use_omp:
                omp = cpus_per_node // suggestion[1]
            else:
                omp = 1
            # here we drop parallelisations having odd number of MPIs
            if only_even_MPI_1 and suggestion[1] % 2 == 0 or not only_even_MPI_1:
                final_suggestion.append([suggestion[0], suggestion[1], omp])
        return final_suggestion

    # all possible suggestions taking into account omp
    suggestions_save = suggestions
    suggestions = np.array(add_omp(suggestions, only_even_MPI))
    if not len(suggestions):  # only odd MPI parallelisations possible, ignore only_even_MPI
        suggestions = np.array(add_omp(suggestions_save, False))

    best_resources = max(np.prod(suggestions, axis=1))
    top_suggestions = suggestions[np.prod(suggestions, axis=1) > sacrifice_level * best_resources]

    def best_criterion(suggestion):
        if use_omp:
            return -abs(suggestion[1] / suggestion[2] - mpi_omp_ratio)
        return (suggestion[0] * suggestion[1], -suggestion[0])

    best_suggestion = max(top_suggestions, key=best_criterion)

    message = ''

    if float(best_suggestion[1] * best_suggestion[2]) / cpus_per_node < 0.6:
        message = ('WARNING: Changed the number of MPIs per node from {} to {} and OMP per MPI '
                   'from {} to {}.'
                   'Changed the number of nodes from {} to {}. '
                   'Computational setup, needed for a given number k-points ({})'
                   ' provides less then 60% of node load.'
                   ''.format(mpi_per_node, best_suggestion[1], omp_per_mpi, best_suggestion[2], nodes,
                             best_suggestion[0], kpts))
        raise ValueError(message)
    elif best_suggestion[1] * best_suggestion[2] == cpus_per_node:
        if best_suggestion[0] != nodes:
            message = ('WARNING: Changed the number of nodes from {} to {}' ''.format(nodes, best_suggestion[0]))
        else:
            message = ('Computational setup is perfect! Nodes: {}, MPIs per node {}, OMP per MPI '
                       '{}. Number of k-points is {}'.format(best_suggestion[0], best_suggestion[1], best_suggestion[2],
                                                             kpts))
    else:
        message = ('WARNING: Changed the number of MPIs per node from {} to {} and OMP from {} to {}'
                   '. Changed the number of nodes from {} to {}. Number of k-points is {}.'
                   ''.format(mpi_per_node, best_suggestion[1], omp_per_mpi, best_suggestion[2], nodes,
                             best_suggestion[0], kpts))

    return int(best_suggestion[0]), int(best_suggestion[1]), int(best_suggestion[2]), message


def find_last_submitted_calcjob(restart_wc):
    """
    Finds the last CalcJob submitted in a higher-level workchain
    and returns it's uuid
    """
    from aiida.common.exceptions import NotExistent
    from aiida.orm import CalcJobNode
    links = restart_wc.get_outgoing().all()
    calls = [x for x in links if isinstance(x.node, CalcJobNode)]
    if calls:
        calls = sorted(calls, key=lambda x: x.node.pk)
        return calls[-1].node.uuid
    else:
        raise NotExistent


def find_last_submitted_workchain(restart_wc):
    """
    Finds the last WorkChain submitted in a higher-level workchain
    and returns it's uuid
    """
    from aiida.common.exceptions import NotExistent
    from aiida.orm import WorkChainNode
    links = restart_wc.get_outgoing().all()
    calls = [x for x in links if isinstance(x.node, WorkChainNode)]
    if calls:
        calls = sorted(calls, key=lambda x: x.node.pk)
        return calls[-1].node.uuid
    else:
        raise NotExistent
