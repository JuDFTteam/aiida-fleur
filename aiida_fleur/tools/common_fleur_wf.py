#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
In here we put all things (methods) that are common to workflows AND
depend on AiiDA classes, therefore can only be used if the dbenv is loaded.
Util that does not depend on AiiDA classes should go somewhere else. 
"""

from aiida.orm import DataFactory
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
