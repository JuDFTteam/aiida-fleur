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
In here we put all things util (methods, code snipets) that are often useful, but not yet in AiiDA
itself.
So far it contains:

export_extras
import_extras
delete_nodes
delete_trash
create_group

"""
# TODO import, export of descriptions, and labels...?
from __future__ import absolute_import
from __future__ import print_function
import json
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.orm.querybuilder import QueryBuilder
from aiida.orm import Group, Node
import six
from six.moves import input


RemoteData = DataFactory('remote')
ParameterData = DataFactory('dict')
FleurInpData = DataFactory('fleur.fleurinp')



def export_extras(nodes, filename='node_extras.txt'):
    """
    writes uuids and extras of given nodes to a file (json).
    This is useful for import/export because currently extras are lost.
    Therefore this can be used to save and restore the extras on the nodes.

    :param: nodes: list of AiiDA nodes, pks, or uuids
    :param: filename, string where to store the file and its name

    example use:
    node_list = [120,121,123,46]
    export_extras(node_list)
    """

    #outstring = ''#' node uuid | extras \n'
    outdict = {}
    for node in nodes:
        if isinstance(node, int): #pk
            node = load_node(node)
        elif isinstance(node, six.string_types): #uuid
            node = load_node(node)

        if not isinstance(node, Node):
            print(('skiped node {}, is not an AiiDA node, did not know what to do.'.format(node)))
            continue
        uuid = node.uuid
        extras_dict = node.get_extras()
        outdict[uuid] = extras_dict
        #line = '{} | {}\n'.format(uuid, extras_dict)
        #outstring = outstring + line

    #outfile = open(filename, 'w')
    #outfile.write(outstring)
    #outfile.close()
    json.dump(outdict, open(filename,'w'))
    return


def import_extras(filename):
    """
    reads in nodes uuids and extras from a file and aplies them to nodes in the DB.

    This is useful for import/export because currently extras are lost.
    Therefore this can be used to save and restore the extras on the nodes.

    :param: filename, string what file to read from (has to be json format)

    example use:
    import_extras('node_extras.txt')
    """

    all_extras = {}

    # read file
    #inputfile = open(filename, 'r')
    #lines = inputfile.readlines()
    #for line in lines[1:]:
    #    splitted = line.split(' | ')
    #    uuid = splitted[0].rstrip(' ')
    #    extras = splitted[1].rstrip(' ')
    #    #extras = dict(extras)
    #    print(extras)
    #    all_extras[uuid] = extras
    #inputfile.close()
    try:
        all_extras = json.load(open(filename))
    except:
        print('The file has to be loadabel by json. i.e json format (which it is not).')

    for uuid, extras in six.iteritems(all_extras):

        try:
            node = load_node(uuid)
        except:
            # Does not exists
            print(('node with uuid {} does not exist in DB'.format(uuid)))
            node = None
            continue
        if isinstance(node, Node):
            node.set_extras(extras)
        else:
            print('node is not instance of an AiiDA node')
        #print(extras)
    return



def delete_nodes(pks_to_delete):
    """
    Delete a set of nodes. (From AiiDA cockbook)
    Note: TODO this has to be improved for workchain removal. (checkpoints and co)
    Also you will be backchecked.

    BE VERY CAREFUL!
    
    .. note:: 
    
        The script will also delete
        all children calculations generated from the specified nodes.

    :params pks_to_delete: a list of the PKs of the nodes to delete
    """
    # TODO: CHECK IF THIS IS UP TO DATE!
    from django.db import transaction
    from django.db.models import Q
    from aiida.backends.djsite.db import models
    from aiida.orm import load_node

    # Delete also all children of the given calculations
    # Here I get a set of all pks to actually delete, including
    # all children nodes.
    all_pks_to_delete = set(pks_to_delete)
    for pk in pks_to_delete:
        all_pks_to_delete.update(models.DbNode.objects.filter(
            parents__in=pks_to_delete).values_list('pk', flat=True))

    print(("I am going to delete {} nodes, including ALL THE CHILDREN"
          "of the nodes you specified. Do you want to continue? [y/N]"
          "".format(len(all_pks_to_delete))))
    answer = input()

    if answer.strip().lower() == 'y':
        # Recover the list of folders to delete before actually deleting
        # the nodes.  I will delete the folders only later, so that if
        # there is a problem during the deletion of the nodes in
        # the DB, I don't delete the folders
        folders = [load_node(pk).folder for pk in all_pks_to_delete]

        with transaction.atomic():
            # Delete all links pointing to or from a given node
            models.DbLink.objects.filter(
                Q(input__in=all_pks_to_delete) |
                Q(output__in=all_pks_to_delete)).delete()
            # now delete nodes
            models.DbNode.objects.filter(pk__in=all_pks_to_delete).delete()

        # If we are here, we managed to delete the entries from the DB.
        # I can now delete the folders
        for f in folders:
            f.erase()

def delete_trash():
    """
    This method deletes all AiiDA nodes in the DB, which have a extra trash=True
    And all their children. Could be advanced to a garbage collector.

    Be careful to use it.
    """

    #query db for marked trash
    q = QueryBuilder()
    nodes_to_delete_pks = []

    q.append(Node,
            filters = {'extras.trash': {'==' : True}
                       }
            )
    res = q.all()
    for node in res:
        nodes_to_delete_pks.append(node[0].dbnode.pk)
        print(('pk {}, extras {}'.format(node[0].dbnode.pk, node[0].get_extras())))

    #Delete the trash nodes

    print(('deleting nodes {}'.format(nodes_to_delete_pks)))
    delete_nodes(nodes_to_delete_pks)

    return

def create_group(name, nodes, description=None):
    """
    Creates a group for a given node list.

    So far this is only an AiiDA verdi command.

    :params name: string name for the group
    :params nodes: list of AiiDA nodes, pks, or uuids
    :params description: optional string that will be stored as description for the group

    :returns: the group, AiiDa group

    Usage example:

    .. code-block:: python

        group_name = 'delta_structures_gustav'
        nodes_to_goup_pks =[2142, 2084]
        create_group(group_name, nodes_to_group_pks, description='delta structures added by hand. from Gustavs inpgen files')

    """
    group, created = Group.objects.get_or_create(label=name)
    if created:
        print(('Group created with PK={} and name {}'.format(group.pk, group.label)))
    else:
        print(('Group with name {} and pk {} already exists. Do you want to add nodes?[y/n]'.format(group.label, group.pk)))
        answer = input()
        if answer.strip().lower() == 'y':
            pass
        else:
            return
    nodes2 = []
    nodes2_pks = []
    for node in nodes:
        try:
            node = int(node)
        except ValueError:
            pass
        nodes2_pks.append(node)
        try:
            nodes2.append(load_node(node))
        except:# NotExistentError:
            pass

    group.add_nodes(nodes2)
    print(('added nodes: {} to group {} {}'.format(nodes2_pks, group.label, group.pk)))

    if description:
        group.description = description

    return group


def get_nodes_from_group(group, return_format='uuid'):
    """
    returns a list of node uuids for a given group as, name, pk, uuid or group object
    """
    from aiida.orm import Group
    from aiida.common.exceptions import NotExistent

    nodes = []
    g_nodes = []


    try:
        group_pk = int(group)
    except ValueError:
        group_pk = None
        group_name = group

    if group_pk is not None:
        try:
            str_group = Group(dbgroup=group_pk)
        except NotExistent:
            str_group = None
            message = ('You have to provide a valid pk for a Group '
                       'or a Group name. Reference key: "group".'
                      'given pk= {} is not a valid group'
                      '(or is your group name integer?)'.format(group_pk))
            print(message)
    elif group_name is not None:
        try:
            str_group = Group.get_from_string(group_name)
        except NotExistent:
            str_group = None
            message = ('You have to provide a valid pk for a Group or a Group name.'
                      'given group name= {} is not a valid group'
                      '(or is your group name integer?)'.format(group_name))
            print(message)
    elif isinstance(group, Group):
        str_group = group
    else:
        str_group = None
        print('I could not handle given input, either Group, pk, or group name please.')
        return nodes

    g_nodes = str_group.nodes

    for node in g_nodes:
        if return_format == 'uuid':
            nodes.append(node.uuid)
        elif return_format == 'pk':
            nodes.append(node.pk)

    return nodes



