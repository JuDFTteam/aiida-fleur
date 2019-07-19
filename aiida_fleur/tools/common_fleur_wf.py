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
from aiida.orm import Node, load_node
from aiida.plugins import DataFactory, CalculationFactory

import six
KpointsData =  DataFactory('array.kpoints')
RemoteData = DataFactory('remote')
Dict = DataFactory('dict')
#FleurInpData = DataFactory('fleurinp.fleurinp')
FleurInpData = DataFactory('fleur.fleurinp')
FleurProcess = CalculationFactory('fleur.fleur')
FleurinpProcess = CalculationFactory('fleur.inpgen')


def is_code(code):
    """
    Test if the given input is a Code node, by object, id, uuid, or pk
    if yes returns a Code node in all cases
    if no returns None
    """
    from aiida.orm import Code, load_node
    #Test if Code
    if isinstance(code, Code):
        return code
    #Test if pk, if yes, is the corresponding node Code
    pk = None
    try:
        pk=int(code)
    except:
        pass
    if pk:
        code = load_node(pk)
        if isinstance(code, Code):
            return code
        else:
            return None
    #given as string
    codestring = None
    try:
        codestring = str(code)
    except:
        pass
    if codestring:
        code = Code.get_from_string(codestring)
        return code
    #Test if uuid, if yes, is the corresponding node Code
    # TODO: test for uuids not for string (guess is ok for now)
    '''
    uuid = None
    try:
        uuid = str(code)
    except:
        pass
    if uuid:
        code = load_node(uuid)
        if isinstance(code, Code):
            return code
        else:
            return None
    '''
    return None

def get_inputs_fleur(code, remote, fleurinp, options, label='', description='', settings=None,
                     serial=False):
    '''
    get the input for a FLEUR calc
    '''
    inputs = {}
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
    #TODO check  if code is parallel version?
    if serial:
        if not options:
            options = {}
        options['withmpi'] = False # for now
        #TODO not every machine/scheduler type takes number of machines
        #  lsf takes number of total_mpi_procs,slurm and psb take num_machinces,\
        # also a full will run here mpi on that node... also not what we want.ß
        options['resources'] = {"num_machines": 1}
    else:
        # set withmpi explicitly
        options['withmpi'] = True

    if settings:
        inputs['settings'] = Dict(dict=settings)

    if options:
        inputs['options'] = Dict(dict=options)

    return inputs


def get_inputs_inpgen(structure, inpgencode, options, label='', description='', params=None, **kwargs):
    """
    get the input for a inpgen calc
    """
    inputs = FleurinpProcess.get_builder()#.get_inputs_template()
    #print('Template inpgen {} '.format(inputs))

    if structure:
        inputs.structure = structure
    if inpgencode:
        inputs.code = inpgencode
    if params:
        inputs.parameters = params

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
    #inpgen run always serial
    options['withmpi'] = False # for now
    options['resources'] = {"num_machines": 1}
    #print(inputs)
    if options:
        inputs.metadata.options = options
    
    # Currently this does not work, find out howto...
    #for key, val in kwargs.items():
    #    inputs[key] = val
    
    return inputs




def get_scheduler_extras(code, resources, extras={}, project='jara0172'):
    """
    This is a utilty function with the goal to make prepare the right resource and scheduler extras for a given computer.
    Since this is user dependend you might want to create your own.

    return: dict, custom scheduler commands
    """
    nnodes = resources.get('num_machines', 1)
    
    # TODO memmory has to be done better...
    mem_per_node = 120000# max recommend 126000 MB on claix jara-clx nodes
    mem_per_process = mem_per_node/24
    if not extras:
        # use defaults # TODO add other things, span, pinnning... openmp
        extras = {'lsf' : '#BSUB -P {} \n#BSUB -M {}  \n#BSUB -a intelmpi'.format(project, mem_per_process),#{'-P' : 'jara0043', '-M' : memp_per_node*nnodes, '-a' : 'intelmpi'},
                 'torque' : '',#{},
                 'direct' : ''}#{}}

    # get the scheduler type from the computer the code is run on.
    com = code.get_computer()
    #com_name = com.get_name()
    scheduler_type = com.get_scheduler_type()

    default_per_machine = com.get_default_mpiprocs_per_machine()
    if not default_per_machine:
        default_per_machine = 24# claix, lsf does can not have default mpiprocs... #TODO this better
    tot_num_mpiprocs = resources.get('tot_num_mpiprocs', default_per_machine*nnodes)

    if scheduler_type == 'lsf':
        new_resources = {'tot_num_mpiprocs' : tot_num_mpiprocs}# only this needs to be given
    elif scheduler_type == 'torque':
        new_resources = resources#{'num_machines', 1} # on iff003 currently we do not do multinode mpi,
        #like this it will get stuck on iff003
    else:
        new_resources = resources
    scheduler_extras = extras.get(scheduler_type, '')

    return new_resources, scheduler_extras


#test
###############################
#codename = 'inpgen@local_mac'#'inpgen_v0.28@iff003'#'inpgen_iff@local_iff'
#codename2 = 'fleur_v0.28@iff003'#'fleur_mpi_v0.28@iff003'# 'fleur_iff_0.28@local_iff''
#codename2 = 'fleur_max_1.3_dev@iff003'
#codename2 = 'fleur_mpi_max_1.3_dev@iff003'
#codename4 = 'fleur_mpi_v0.28@claix'
###############################
#code = Code.get_from_string(codename)
#code2 = Code.get_from_string(codename2)
#code4 = Code.get_from_string(codename4)
#print(get_scheduler_extras(code, {'num_machines' : 1}))
#print(get_scheduler_extras(code2, {'num_machines' : 2}))
#print(get_scheduler_extras(code4, {'num_machines' : 1}))

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
        if codenode is None:
            raise ValueError
        code = codenode
        if code.get_input_plugin_name() != expected_code_type:
            raise ValueError
    except (NotExistent, ValueError):
        from aiida.orm.querybuilder import QueryBuilder
        qb = QueryBuilder()
        qb.append(Code,
                  filters={'attributes.input_plugin':
                               {'==': expected_code_type}},
                  project='*')

        valid_code_labels = ["{}@{}".format(c.label, c.get_computer().name)
                             for [c] in qb.all()]

        if valid_code_labels:
            msg = ("Pass as further parameter a valid code label.\n"
                   "Valid labels with a {} executable are:\n".format(
                expected_code_type))
            msg += "\n".join("* {}".format(l) for l in valid_code_labels)

            if use_exceptions:
                raise ValueError(msg)
            else:
                print(msg)#, file=sys.stderr)
                sys.exit(1)
        else:
            msg = ("Code not valid, and no valid codes for {}.\n"
                   "Configure at least one first using\n"
                   "    verdi code setup".format(
                expected_code_type))
            if use_exceptions:
                raise ValueError(msg)
            else:
                print(msg)#, file=sys.stderr)
                sys.exit(1)

    return code


def get_kpoints_mesh_from_kdensity(structure, kpoint_density):
    """
    params: structuredata, Aiida structuredata
    params: kpoint_density

    returns: tuple (mesh, offset)
    returns: kpointsdata node
    """
    kp = KpointsData()
    kp.set_cell_from_structure(structure)
    density  = kpoint_density #1/A
    kp.set_kpoints_mesh_from_density(density)
    mesh = kp.get_kpoints_mesh()
    return mesh, kp

# test
# print(get_kpoints_mesh_from_kdensity(load_node(structure(120)), 0.1))
#(([33, 33, 18], [0.0, 0.0, 0.0]), <KpointsData: uuid: cee9d05f-b31a-44d7-aa72-30a406712fba (unstored)>)
# mesh, kp = get_kpoints_mesh_from_kdensity(structuredata, 0.1)
#print mesh[0]

# TODO maybe allow lists of uuids in workchain dict, or write a second funtion for this,...
# The question is how do get the 'enthalpy for a reaction out of my database?
# where I have redundant calculations or calculations with different parameters...
# are total energies comparable?
# -> as long as the same scheme ist used (all GGA or all GGA+U)
# total energies are compareable and the gibs enthalpy is approximatily the
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
    """
    from aiida.orm import load_node
    from aiida.orm.calculation.work import WorkCalculation
    from aiida_fleur.tools.common_fleur_wf_util import get_enhalpy_of_equation
    # for each reaction get the total energy sum
    # make sure to use the right multipliers...
    # then sort the given list from (lowest if negativ energies to highest)
    energy_sorted_reactions = []
    formenergy_dict ={}
    for compound, uuid in six.iteritems(workchain_dict):
        # TODO ggf get formation energy from ouput node, or extras
        if isinstance(uuid, float):# allow to give values
            formenergy_dict[compound] = uuid
            continue
        n = load_node(uuid)
        extras = n.get_extras() # sadly there is no get(,) method...
        try:
            formenergy = extras.get('formation_energy', None)
        except KeyError:
            formenergy = None
        if not formenergy: # test if 0 case ok
            if isinstance(n, WorkCalculation):
                plabel = n.get_attr('_process_label')
                if plabel == 'fleur_initial_cls_wc':
                    try:
                        ouputnode = n.out.output_initial_cls_wc_para.get_dict()
                    except AttributeError:
                        try:
                            ouputnode = n.out.output_inital_cls_wc_para.get_dict()
                        except:
                            ouputnode = None
                            formenergy = None
                            print(('WARNING: ouput node of {} not found. I skip'.format(n)))
                            continue
                    formenergy = ouputnode.get('formation_energy')
                    # TODO is this value per atom?
                else: # check if corehole wc?
                     pass

        formenergy_dict[compound] = formenergy


    for reaction_string in reaction_list:
        ent_peratom = get_enhalpy_of_equation(reaction_string, formenergy_dict)
        print(ent_peratom)
        energy_sorted_reactions.append([reaction_string, ent_peratom])
    energy_sorted_reactions = sorted(energy_sorted_reactions, key=lambda ent: ent[1])
    return energy_sorted_reactions


# test
#reaction_list = ['1*Be12W->1*Be12W', '2*Be12W->1*Be2W+1*Be22W', '11*Be12W->5*W+6*Be22W', '1*Be12W->12*Be+1*W', '1*Be12W->1*Be2W+10*Be']
#workchain_dict = {'Be12W' : '4f685bc5-b5fb-46d3-aad6-e0f512c3313d',
#                  'Be2W' : '045d3071-f442-46b4-8d6b-3c85d72b24d4',
#                  'Be22W' : '1e32880a-bdc9-4081-a5da-be04860aa1bc',
#                  'W' : 'f8b12b23-0b71-45a1-9040-b51ccf379439',
#                  'Be' : 0.0}
#reac_list = determine_favorable_reaction(reaction_list, workchain_dict)
#print reac_list
#{'products': {'Be12W': 1}, 'educts': {'Be12W': 1}}
#0.0
#{'products': {'Be2W': 1, 'Be22W': 1}, 'educts': {'Be12W': 2}}
#0.114321037514
#{'products': {'Be22W': 6, 'W': 5}, 'educts': {'Be12W': 11}}
#-0.868053153884
#{'products': {'Be': 12, 'W': 1}, 'educts': {'Be12W': 1}}
#-0.0946046496213
#{'products': {'Be': 10, 'Be2W': 1}, 'educts': {'Be12W': 1}}
#0.180159355144
#[['11*Be12W->5*W+6*Be22W', -0.8680531538839534], ['1*Be12W->12*Be+1*W', -0.0946046496213127], ['1*Be12W->1*Be12W', 0.0], ['2*Be12W->1*Be2W+1*Be22W', 0.11432103751404535], ['1*Be12W->1*Be2W+10*Be', 0.1801593551436103]]


def performance_extract_calcs(calcs):
    """
    Extracts some runtime and system data from given fleur calculations
    
    :params calcs: list of calculation nodes/pks/or uuids. Fleur calc specific
    
    :returns data_dict: dictionary, dictionary of arrays with the same lengt, 
                        from with a panda frame can be created.
    
    Note: Is not the fastest for many calculations > 1000.
    """
    data_dict = {u'n_symmetries':[], u'n_spin_components' : [],
                 u'n_kpoints': [], u'n_iterations': [], 
                 u'walltime_sec' : [], u'walltime_sec_per_it' : [], 
                 u'n_iterations_total' : [], 
                 u'density_distance': [], u'computer':[],
                 u'n_atoms' : [], u'kmax':[],
                 u'cost' : [], u'costkonstant' : [], 
                 u'walltime_sec_cor' : [], u'total_cost' : [],
                 u'fermi_energy' : [], u'bandgap' : [], 
                 u'energy' : [], u'force_largest' : [], 
                 u'ncores' : [], u'pk' : [],
                 u'uuid' : [], u'serial' : [],
                 u'resources' : []}
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
            continue # we skip these entries
            efermi = -10000

        try:
            gap = res.bandgap
        except AttributeError:
            gap = -10000   
            continue
            print(('skipping 2 {}, {}'.format(pk, calc.uuid)))


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
        else: # magnetic, old
            data_dict['density_distance'].append(res.overall_charge_density)


        walltime = res.walltime
        if walltime <= 0:
            # date was not considert yet, we assume one day...
            walltime_new = walltime + 86400
        else:
            walltime_new = walltime

        walltime_periteration = walltime_new/niter


        data_dict['walltime_sec'].append(walltime)
        data_dict['walltime_sec_cor'].append(walltime_new)
        data_dict['walltime_sec_per_it'].append(walltime_periteration)
        cname = calc.get_computer().name
        data_dict['computer'].append(cname)
        natom = res.number_of_atoms
        data_dict['n_atoms'].append(natom)

        fleurinp = calc.get_inputs_dict()['fleurinpdata']
        kmax = fleurinp.inp_dict['calculationSetup']['cutoffs']['Kmax']
        data_dict['kmax'].append(kmax)


        cost = calc_time_cost_function(natom, nkpt, kmax, nspins)
        total_cost = cost * niter

        serial = not calc.get_withmpi()
        #codename = calc.get_code().label
        #code_col.append(codename)
        
        #if 'mpi' in codename:
        #    serial = False
        #else:
        #    serial = True
        data_dict['serial'].append(serial)
        
        resources = calc.get_resources()
        mpi_proc = get_mpi_proc(resources)    

        c_ratio = cost_ratio(cost, walltime_new, mpi_proc)
        data_dict['resources'].append(resources)
        data_dict['cost'].append(cost)
        data_dict['costkonstant'].append(c_ratio)
        data_dict['total_cost'].append(total_cost)
        data_dict['ncores'].append(mpi_proc)  

    return data_dict


def get_mpi_proc(resources):
    nmachines = resources.get('num_machines', 0)
    total_proc = resources.get('tot_num_mpiprocs', 0)
    if not total_proc:
        if nmachines:
            total_proc = nmachines*resources.get('default_mpiprocs_per_machine', 12)
        else:
            total_proc = resources.get('tot_num_mpiprocs', 24)
        
    return total_proc

def calc_time_cost_function(natom, nkpt, kmax, nspins=1):
    costs = natom**3 * kmax**3 * nkpt * nspins
    return costs

def calc_time_cost_function_total(natom, nkpt, kmax, niter, nspins=1):
    costs = natom**3 * kmax**3 * nkpt * nspins * niter
    return costs

def cost_ratio(total_costs, walltime_sec, ncores):
    ratio = total_costs/(walltime_sec*ncores)
    return ratio
    
def optimize_calc_options(fleurinpData, nodes, cpus_per_node):
    """
    This routine checks if the total number of requested cpus
    is a factor of kpts and suggests the optimisation.
    """
    from sympy.ntheory.factor_ import factorint, divisors
    kpts = fleurinpData.get_tag('/fleurInput/calculationSetup/bzIntegration/kPointList/@count')
    kpts = int(kpts[0])
    divisors_kpts = divisors(kpts)
    possible_nodes = [x for x in divisors_kpts if x<=nodes]
    suggestions = []
    for n_n in possible_nodes:
        adviced_cpu_per_node = max([x for x in divisors(kpts//n_n) if x<=cpus_per_node])
        suggestions.append((n_n, adviced_cpu_per_node))
    
    def best_criterion(suggestion):
        """
        The best setup uses as many as possible total number of
        CPUs. If there are more than one such a setup, it is more efficient
        to use less computations nodes.
        """
        return (suggestion[0]*suggestion[1], 1.0/suggestion[0])
    
    best_suggestion = max(suggestions, key=best_criterion)
    message = ''
    exit_status = 0
    
    if (float(best_suggestion[1])/cpus_per_node < 0.6):
        exit_status = 1
        message = ('WARNING: Changed the number of CPUs per node from {} to {}. '
                        'Changed the number of nodes from {} to {}. '
                        'Computational setup, needed for a given number k-points ({})'
                        ' provides less then 60% of node load.'.format(cpus_per_node, best_suggestion[1], nodes, best_suggestion[0], kpts))
    elif (best_suggestion[1] == cpus_per_node):
        if (best_suggestion[0] != nodes):
            message = 'WARNING: Changed the number of nodes from {} to {}'.format(nodes, best_suggestion[0])
        else:
            message = 'Computaional setup is perfect! Nodes: {}, CPUs per node {}. Number of k-points is {}'.format(best_suggestion[0], best_suggestion[1], kpts )
    else:
        message = ('WARNING: Changed the number of CPUs per node from {} to {}. '
            'Changed the number of nodes from {} to {}. Number of k-points is {}.'.format(cpus_per_node, best_suggestion[1], nodes, best_suggestion[0], kpts))
    return best_suggestion[0], best_suggestion[1], message, exit_status

def cleanup_inputs(original_inputs):
    """ Remove input nodes that is None from the input dict"""
    import copy
    inputs = copy.deepcopy(original_inputs)
    for key, value in six.iteritems(original_inputs):
        if value is None:
            inputs.pop(key)
    return inputs