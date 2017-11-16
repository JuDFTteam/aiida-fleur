#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In here we put all things (methods) that are common to workflows
"""

from aiida.orm import Code, DataFactory, load_node
#from aiida.tools.codespecific.fleur.queue_defaults import queue_defaults
#from aiida.work.workchain import WorkChain
#from aiida.work.workchain import while_, if_
#from aiida.work.run import submit
#from aiida.work.workchain import ToContext
#from aiida.work.process_registry import ProcessRegistry
#from aiida.tools.codespecific.fleur.decide_ncore import decide_ncore
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

KpointsData =  DataFactory('array.kpoints')
RemoteData = DataFactory('remote')
ParameterData = DataFactory('parameter')
#FleurInpData = DataFactory('fleurinp.fleurinp')
FleurInpData = DataFactory('fleur.fleurinp')
FleurProcess = FleurCalculation.process()
FleurinpProcess = FleurinputgenCalculation.process()


def is_code(code):
    """
    Test if the given input is a Code node, by object, id, uuid, or pk
    if yes returns a Code node in all cases
    if no returns None
    """

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

def get_inputs_fleur(code, remote, fleurinp, options, label='', description='', settings=None, serial=False):
    '''
    get the input for a FLEUR calc
    '''
    inputs = FleurProcess.get_inputs_template()
    #print('Template fleur {} '.format(inputs))
    if remote:
        inputs.parent_folder = remote
    if code:
        inputs.code = code
    if fleurinp:
        inputs.fleurinpdata = fleurinp

    for key, val in options.iteritems():
        if val==None:
            continue
        else:
            inputs._options[key] = val

    if description:
        inputs['_description'] = description
    else:
        inputs['_description'] = ''
    if label:
        inputs['_label'] = label
    else:
        inputs['_label'] = ''
    #TODO check  if code is parallel version?
    if serial:
        inputs._options.withmpi = False # for now
        inputs._options.resources = {"num_machines": 1}

    if settings:
        inputs.settings = settings

    '''
    options = {
    "max_wallclock_seconds": int,
    "resources": dict,
    "custom_scheduler_commands": unicode,
    "queue_name": basestring,
    "computer": Computer,
    "withmpi": bool,
    "mpirun_extra_params": Any(list, tuple),
    "import_sys_environment": bool,
    "environment_variables": dict,
    "priority": unicode,
    "max_memory_kb": int,
    "prepend_text": unicode,
    "append_text": unicode}
    '''
    return inputs


def get_inputs_inpgen(structure, inpgencode, options, label='', description='', params=None):
    """
    get the input for a inpgen calc
    """
    inputs = FleurinpProcess.get_inputs_template()
    #print('Template inpgen {} '.format(inputs))

    if structure:
        inputs.structure = structure
    if inpgencode:
        inputs.code = inpgencode
    if params:
        inputs.parameters = params
    for key, val in options.iteritems():
        if val==None:
            #leave them out, otherwise the dict schema won't validate
            continue
        else:
            inputs._options[key] = val

    if description:
        inputs['_description'] = description
    else:
        inputs['_description'] = ''

    if label:
        inputs['_label'] = label
    else:
        inputs['_label'] = ''

    #inpgen run always serial
    inputs._options.withmpi = False # for now
    inputs._options.resources = {"num_machines": 1}
    #print(inputs)
    return inputs


def get_natoms_element(formula):
    """
    Converts 'Be24W2' to {'Be': 24, 'W' : 2}, also BeW to {'Be' : 1, 'W' : 1}
    """

    import re
    elem_count_dict = {}
    elements = re.findall('[A-Z][^A-Z]*', formula)
    #re.split('(\D+)', formula)

    for i, elm in enumerate(elements):
        elem_count = re.findall('\d+|\D+', elm)
        #print(elem_count)
        if len(elem_count) == 1:
            elem_count_dict[elem_count[0]] = 1
        else:
            elem_count_dict[elem_count[0]] = float(elem_count[1])

    return elem_count_dict

# test
#get_natoms_element('BeW')
#get_natoms_element('Be2W')

def get_atomprocent(formula):
    """
    This converts a formula to a dictionary with elemnt : atomprocent
    example converts 'Be24W2' to {'Be': 24/26, 'W' : 2/26}, also BeW to {'Be' : 0.5, 'W' : 0.5}
    :params: formula: string
    :returns: a dict, element : atomprocent

    # Todo alternative with structuredata
    """
    form_dict_new = {}
    form_dict = get_natoms_element(formula)
    ntotal = sum(form_dict.values())
    for key, val in form_dict.iteritems():
        val_new = float(val)/ntotal
        form_dict_new[key] = val_new
    return form_dict_new

# test

def get_weight_procent(formula):
    """
    This converts a formula to a dictionary with elemnt : weightprocent
    example converts 'Be24W2' to {'Be': , 'W' : }, also BeW to {'Be' : , 'W' : }
    :params: formula: string
    :returns: a dict, element : weightprocent

    # Todo alternative with structuredata
    """

    pass


def determine_formation_energy(struc_te_dict, ref_struc_te_dict):
    """
    This method determines the formation energy.
    E_form =  E(A_xB_y) - x*E(A) - y*E(B)

    :inputs: struc_te_dict: python dictionary in the form of {'formula' : total_energy} for the compound(s)
    :inputs: ref_struc_te_dict: python dictionary in the form of {'formula' : total_energy per atom} for the elements
    (if the formula of the elements contains a number the total energy is devided by that number)
    :returns: list of floats, dict {formula : eform, ..} units energy/per atom, energies have some unit as energies given
    """
    eform_list = []
    eform_dict = {}
    #ref_el = ref_struc_te_dict.keys()
    ref_struc_te_dict_norm = {}
    # normalize reference
    for key, val in ref_struc_te_dict.iteritems():
        elem_n = get_natoms_element(key)
        ref_struc_te_dict_norm[elem_n.keys()[0]] = val / elem_n.values()[0]
    ref_el_norm = ref_struc_te_dict_norm.keys()

    for formula, tE in struc_te_dict.iteritems():
        elements_count = get_natoms_element(formula)
        ntotal = float(sum(elements_count.values()))
        eform = tE#abs(tE)
        for elem, count in elements_count.iteritems():
            if elem in ref_el_norm:
                eform = eform - count * ref_struc_te_dict_norm.get(elem)#abs(ref_struc_te_dict.get(elem))
            else:
                print('Reference energy missing for element {}. '
                      'You need to provide reference energies for all elements in you compound.'
                       ''.format(elem))
        eform_dict[formula] = eform/ntotal
        eform_list.append(eform/ntotal)
    return eform_list, eform_dict

# test
#determine_formation_energy({'BeW' : 2, 'Be2W' : 2.5}, {'Be' : 1, 'W' : 1})

def determine_convex_hull(formation_en_grid):
    """
    Wraps the scipy.spatial ConvexHull algo for our purposes.
    For now only for 2D phase diagrams
    Adds the points [1.0, 0.0] and [0.0, 1.0], because in material science these
    are always there.

    :params: formation_en_grid: list of points in phase space [[x, formation_energy]]
    :returns: a hul datatype
    """
    import numpy as np
    from scipy.spatial import ConvexHull

    # TODO multi d
    # check if endpoints are in
    if [1.0, 0.0] not in formation_en_grid:
        formation_en_grid.append([1.0, 0.0])
    if [0.0, 0.0] not in formation_en_grid:
        formation_en_grid.append([0.0, 0.0])

    points = np.array(formation_en_grid)
    hull = ConvexHull(points)

    return hull


def get_scheduler_extras(code, resources, extras={}, project='jara0043'):
    """
    This is a utilty function with the goal to make prepare the right resource and scheduler extras for a given computer.
    Since this is user dependend you might want to create your own.

    return: dict, custom scheduler commands
    """
    nnodes = resources.get('num_machines', 1)

    memp_per_node = 125000# max recommend 126000 MB on claix jara-clx nodes
    if not extras:
        # use defaults # TODO add other things, span, pinnning... openmp
        extras = {'lsf' : '#BSUB -P {} \n#BSUB -M {}  \n#BSUB -a intelmpi'.format(project, memp_per_node*nnodes),#{'-P' : 'jara0043', '-M' : memp_per_node*nnodes, '-a' : 'intelmpi'},
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
                print >> sys.stderr, msg
                sys.exit(1)
        else:
            msg = ("Code not valid, and no valid codes for {}.\n"
                   "Configure at least one first using\n"
                   "    verdi code setup".format(
                expected_code_type))
            if use_exceptions:
                raise ValueError(msg)
            else:
                print >> sys.stderr, msg
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


def inpgen_dict_set_mesh(inpgendict, mesh):
    """
    params: python dict, used for inpgen parameterdata node
    params: mesh either as returned by kpointsdata or tuple of 3 integers

    returns: python dict, used for inpgen parameterdata node
    """
    if len(mesh) == 2:
        kmesh = mesh[0]
    elif len(mesh) == 3:
        kmesh = mesh
    kpt_dict = inpgendict.get('kpt', {})
    kpt_dict['div1'] = kmesh[0]
    kpt_dict['div2'] = kmesh[1]
    kpt_dict['div3'] = kmesh[2]

    inpgendict_new = inpgendict
    inpgendict_new['kpt'] = kpt_dict

    return inpgendict_new

# test
#inpgen_dict_set_mesh(Be_para.get_dict(), mesh)
