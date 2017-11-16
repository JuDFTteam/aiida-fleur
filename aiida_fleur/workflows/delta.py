#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the worklfow 'fleur_delta_wc' which is a turnkey solution to calculate a delta for a given code with AiiDA.
"""
#TODO: calculation of delta value from the files
# submit everything if subworkchaining works in Aiida
# parameter node finding is not optimal.
import os
from string import digits
from pprint import pprint

from aiida.orm import Code, DataFactory, Group
from aiida.work.workchain import WorkChain, ToContext
from aiida.work.process_registry import ProcessRegistry
from aiida.work import workfunction as wf
from aiida.work import submit
from aiida.work import async as asy
from aiida.common.exceptions import NotExistent
from aiida_fleur.workflows.eos import fleur_eos_wc

#from aiida_fleur.tools.xml_util import eval_xpath2
#from lxml import etree


__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')
SingleData = DataFactory('singlefile')

class fleur_delta_wc(WorkChain):
    """
    This workflow calculates a equation of states and from a given
    group of structures in the database using a group of given parameter nodes in the database
    """

    _workflowversion = "0.0.1"
    _wf_default = {}

    def __init__(self, *args, **kwargs):
        super(fleur_delta_wc, self).__init__(*args, **kwargs)

    @classmethod
    def define(cls, spec):
        super(fleur_delta_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={'struc_group': 'delta',
                                               'para_group' : 'delta',
                                               'add_extra' : {'type' : 'delta run'},
                                               #'group_label' : 'delta_eos',
                                               'points' : 5,
                                               'step' : 0.02,
                                               'queue_name' : '',
                                               'options' : {'resources' : {"num_machines": 1},
                                               'walltime_sec' : 3600}}))
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.outline(
            cls.start_up,
            cls.run_eos,
            cls.extract_results_eos,
            cls.calculate_delta,
            cls.return_results,

        )
        #spec.dynamic_output()

    def start_up(self):
        """
        init context and some parameters
        """

        #print('started delta workflow version {}'.format(self._workflowversion))
        #print("Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node))
        self.report('started delta workflow version {} with idenifier: {}'
                    ''.format(self._workflowversion, ProcessRegistry().current_calc_node))

        # init
        self.ctx.calcs_to_run = []
        # input  check

        # check if right codes
        wf_dict = self.inputs.wf_parameters.get_dict()
        self.ctx.inputs_eos = {
            'fleur': self.inputs.fleur,
            'inpgen': self.inputs.inpgen,
            'wf_parameters':
                {'points' : wf_dict.get('points', 5),
                 'step' : wf_dict.get('step', 0.02),
                 'guess' : 1.0,
                 'resources' : wf_dict.get('resources', {"num_machines": 1}),
                 'walltime_sec':  wf_dict.get('walltime_sec', 3600),
                 'queue_name' : wf_dict.get('queue_name', ''),
                 'serial' : wf_dict.get('serial', False)
             }}
        self.ctx.wc_eos_para = ParameterData(dict=self.ctx.inputs_eos.get('wf_parameters'))
        self.get_calcs_from_groups()
        self.ctx.successful = True
        self.ctx.warnings = []
        self.ctx.labels = []

    def get_calcs_from_groups(self):
        """
        Extract the crystal structures and parameter data nodes from the given
        groups and create calculation 'pairs' (stru, para).
        """
        wf_dict = self.inputs.wf_parameters.get_dict()
        #get all delta structure
        str_gr = wf_dict.get('struc_group', 'delta')

        try:
            group_pk = int(str_gr)
        except ValueError:
            group_pk = None
            group_name = str_gr

        if group_pk is not None:
            try:
                str_group = Group(dbgroup=group_pk)
            except NotExistent:
                str_group = None
                message = ('You have to provide a valid pk for a Group of'
                          'structures or a Group name. Wf_para key: "struc_group".'
                          'given pk= {} is not a valid group'
                          '(or is your group name integer?)'.format(group_pk))
                #print(message)
                self.report(message)
                self.abort_nowait('I abort, because I have no structures to calculate ...')
        else:
            try:
                str_group = Group.get_from_string(group_name)
            except NotExistent:
                str_group = None
                message = ('You have to provide a valid pk for a Group of'
                          'structures or a Group name. Wf_para key: "struc_group".'
                          'given group name= {} is not a valid group'
                          '(or is your group name integer?)'.format(group_name))
                #print(message)
                self.report(message)
                self.abort_nowait('I abort, because I have no structures to calculate ...')


        #get all delta parameters
        para_gr = wf_dict.get('para_group', 'delta')

        if not para_gr:
            #waring use defauls
            message = 'COMMENT: I did recieve "para_group=None" as input. I will use inpgen defaults'
            self.report(message)

        try:
            group_pk = int(para_gr )
        except ValueError:
            group_pk = None
            group_name = para_gr

        if group_pk is not None:
            try:
                para_group = Group(dbgroup=group_pk)
            except NotExistent:
                para_group = None
                message = ('ERROR: You have to provide a valid pk for a Group of'
                          'parameters or a Group name (or use None for inpgen defaults). Wf_para key: "para_group".'
                          'given pk= {} is not a valid group'
                          '(or is your group name integer?)'.format(group_pk))
                #print(message)
                self.report(message)
                self.abort_nowait('ERROR: I abort, because I have no paremeters to calculate and '
                                  'I guess you did not want to use the inpgen default...')
        else:
            try:
                para_group = Group.get_from_string(group_name)
            except NotExistent:
                para_group = None
                message = ('ERROR: You have to provide a valid pk for a Group of'
                          'parameters or a Group name (or use None for inpgen defaults). Wf_para key: "struc_group".'
                          'given group name= {} is not a valid group'
                          '(or is your group name integer?)'.format(group_name))
                #print(message)
                self.report(message)
                self.abort_nowait('ERROR: I abort, because I have no paremeters to calculate and '
                                  'I guess you did not want to use the inpgen default...')

        # creating calculation pairs (structure, parameters)

        para_nodesi = para_group.nodes
        para_nodes = []

        for para in para_nodesi:
            para_nodes.append(para)
        #print para_nodes
        n_para = len(para_nodes)
        stru_nodes = str_group.nodes
        n_stru = len(stru_nodes)
        if n_para != n_stru:
            message = ('COMMENT: You did not provide the same number of parameter'
                       'nodes as structure nodes. Is this wanted? npara={} nstru={}'.format(n_para, n_stru))
            self.report(message)
        calcs = []
        for struc in stru_nodes:
            para = get_paranode(struc, para_nodes)
            #if para:
            calcs.append((struc, para))
            #else:
            #    calcs.append((struc))
        pprint(calcs[:20])
        self.ctx.calcs_to_run = calcs

    def run_eos(self):
        """
        Run the equation of states for all delta structures with their parameters
        """

        eos_results = {}
        inputs = self.get_inputs_eos()

        
        for struc, para in self.ctx.calcs_to_run[10:33]:#[10:33]
            print para
            formula = struc.get_formula()
            label = '|delta_wc|eos|{}'.format(formula)
            description = '|delta| fleur_eos_wc on {}'.format(formula)            
            if para:
                eos_future = submit(fleur_eos_wc,
                                wf_parameters=inputs['wc_eos_para'], structure=struc,
                                calc_parameters=para, inpgen=inputs['inpgen'], fleur=inputs['fleur'],
                                _label=label, _description=description)
                #fleur_eos_wc.run(#
            else: # TODO: run eos_wc_simple
                eos_future = submit(fleur_eos_wc,
                                wf_parameters=inputs['wc_eos_para'], structure=struc,
                                inpgen=inputs['inpgen'], fleur=inputs['fleur'],
                                _label=label, _description=description)
                #fleur_eos_wc.run(#a
            self.report('launching fleur_eos_wc<{}> on structure {} with parameter {}'
                        ''.format(eos_future.pid, struc.pk, para.pk))
            label = formula
            self.ctx.labels.append(label)
            eos_results[label] = eos_future

        return ToContext(**eos_results)

        '''
        #async to limit through put
        eos_results = {}
        inputs = self.get_inputs_eos()


        for struc, para in self.ctx.calcs_to_run[:4]:
            print para
            formula = struc.get_formula()
            label = '|delta_wc|eos|{}'.format(formula)
            description = '|delta| fleur_eos_wc on {}'.format(formula)
            if para:
                eos_future = asy(fleur_eos_wc,
                                wf_parameters=inputs['wc_eos_para'], structure=struc,
                                calc_parameters=para, inpgen=inputs['inpgen'], fleur=inputs['fleur'],
                                _label=label, _description=description)
                #fleur_eos_wc.run(#
            else:
                eos_future = asy(fleur_eos_wc,
                                wf_parameters=inputs['wc_eos_para'], structure=struc,
                                inpgen=inputs['inpgen'], fleur=inputs['fleur'],
                                _label=label, _description=description)
                #fleur_eos_wc.run(#a
            self.report('launching fleur_eos_wc<{}> on structure {} with parameter {}'
                        ''.format(eos_future.pid, struc.pk, para.pk))
            label = formula
            self.ctx.labels.append(label)
            eos_results[label] = eos_future

        return ToContext(**eos_results)
        '''
        '''
        # with run
        eos_results = {}
        inputs = self.get_inputs_eos()


        for struc, para in self.ctx.calcs_to_run[:]:
            print para
            formula = struc.get_formula()
            if para:
                #print('here')
                eos_future = fleur_eos_wc.run(
                                wf_parameters=inputs['wc_eos_para'], structure=struc,
                                calc_parameters=para, inpgen=inputs['inpgen'], fleur=inputs['fleur'])
                #fleur_eos_wc.run(#
            else:
                self.report('INFO: default parameters for structure {}'.format(formula))
                eos_future = fleur_eos_wc.run(
                                wf_parameters=inputs['wc_eos_para'], structure=struc,
                                inpgen=inputs['inpgen'], fleur=inputs['fleur'])
                #fleur_eos_wc.run(#a
            #self.report('launching fleur_eos_wc<{}> on structure {} with parameter {}'
            #            ''.format(eos_future.pid, struc.pk, para.pk))
            label = formula
            self.ctx.labels.append(label)
            eos_results[label] = eos_future

        return ToContext(**eos_results)
        '''
    def get_inputs_eos(self):
        """
        get the inputs for a scf-cycle
        """
        inputs = {}
        # produce the inputs for a eos worklfow (collect here...)

        inputs['wc_eos_para'] = self.ctx.wc_eos_para
        #inputs['calc_parameters'] = self.inputs.calc_parameters
        inputs['inpgen'] = self.ctx.inputs_eos.get('inpgen')
        inputs['fleur'] = self.ctx.inputs_eos.get('fleur')

        return inputs

    def extract_results_eos(self):
        """
        extract information out of the result nodes of the the eos workchains
        ran in the step before
        """

        self.ctx.all_results = {}
        self.ctx.all_succ = {}
        self.ctx.eos_uuids ={}
        outstr = ('''\
             Delta calculation FLEUR {} (AiiDA wc).

             Crystal \t V0 \t \t  B0 \t \t  BP [A^3/at] \t [GPa] \t \t [--] \n
             '''.format(self.ctx.inputs_eos.get('fleur')))
        outfile = open('delta_wc.out', 'w')
        outfile.write(outstr)
        outfile.close()
        for label in self.ctx.labels:
            eos_res = self.ctx[label]
            #print(calc)
            outpara1 = eos_res.get_outputs_dict()
            #print outpara1
            try:
                outpara= outpara1['output_eos_wc_para'].get_dict()
            except KeyError:
                self.report('ERROR: Eos wc for element: {} failed. I retrieved {} '
                            'I skip the results retrieval for that element.'.format(label, eos_res))
                continue
            eos_succ = outpara.get('successful', False)
            if not eos_succ:
                #maybe do something else here (exclude point and write a warning or so, or error treatment)
                self.ctx.successful = False

            natoms = outpara.get('natoms', None)
            gs_vol = outpara.get('volume_gs', None)
            bm = outpara.get('bulk_modulus', None)
            #bm_u = outpara.get('bulk_modulus_units', 'GPa')
            dbm = outpara.get('bulk_deriv', None)
            if natoms:
                gs_vol_pera = gs_vol/natoms
            else:
                gs_vol_pera = gs_vol

            element = label.translate(None, digits) # remove all numbers from string
            self.ctx.all_results[element] = [gs_vol_pera, bm, dbm]
            self.ctx.all_succ[element] = eos_succ
            self.ctx.eos_uuids[element] = eos_res.get_inputs()[0].uuid

            outstr = outstr + '{} \t {:.5f} \t {:.5f} \t {:.5f} \n'.format(element, gs_vol_pera, bm, dbm)
            #write inside the loop to have at least partially results...
            #outfile = open('delta_wc.out', 'a')
            #outstr = '{} \t {:.5f} \t {:.5f} \t {:.5f} \n'.format(element, gs_vol_pera, bm, dbm)
            #outfile.write(outstr)
            #outfile.close()
        # produce a single file
        # maybe put in try(or write in a certain place where is sure that you have the permissions)
        #outfile = open('delta_wc.out', 'w')
        outfile = open('delta_wc.out', 'a') # for testing purposes
        outfile.write(outstr)

        outfile.close()

        self.ctx.outfilepath = os.path.abspath(outfile.name)


    def calculate_delta(self):
        """
        Execute here the script to calculate a delta factor
        """
        pass

    def return_results(self):
        """
        return the results of the calculations
        """

        # log some stuff in report

        # a text file should be written and stored as single file data and
        #parameter data node in the database

        #produce a single file data with all the numbers

        all_res = self.ctx.all_results
        bm_dic = {}
        bmd_dic = {}
        vol_dic = {}

        for elem,val in all_res:
            vol_dic[elem] = val[0]
            bm_dic[elem] = val[1]
            bmd_dic[elem] = val[2]

        outputnode_dict ={}


        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['eos_uuids'] = self.ctx.eos_uuids
        outputnode_dict['eos_success'] = self.ctx.all_succ
        outputnode_dict['bulk_modulus'] = bm_dic
        outputnode_dict['bulk_modulus_units'] = 'GPa'
        outputnode_dict['bulk_modulus_dev'] = bmd_dic
        outputnode_dict['volumes'] = vol_dic
        outputnode_dict['volumes_units'] = 'A^3/per atom'
        outputnode_dict['delta_factor'] = {'Wien2K' : '', 'Fleur_026' : ''}

        #outputnode = ParameterData(dict=outputnode_dict)

        if self.ctx.successful:
            self.report('INFO: Done, delta worklfow complete')
            #print 'Done, delta worklfow complete'
        else:
            self.report('INFO: Done, but something went wrong.... Properly some '
                        'individual eos workchain failed. Check the log.')
            #print('Done, but something went wrong.... Properly some '
            #            'individual eos workchain failed. Check the log.')

        delta_file = SingleData.filename = self.ctx.outfilepath

        print delta_file

        # output must be aiida Data types.
        outnodedict = {}
        outnode = ParameterData(dict=outputnode_dict)
        outnodedict['results_node'] = outnode
        for label in self.ctx.labels:
            eos_res = self.ctx[label]
            #print(calc)
            outpara1 = eos_res.get_outputs_dict()
            #print outpara1
            try:
                outpara = outpara1['output_eos_wc_para']
            except KeyError:
                #self.report('ERROR: Eos wc for element: {} failed. I retrieved {} '
                #            'I skip the results retrieval for that element.'.format(label, eos_res))
                continue
            outnodedict[label] = outpara

        outputnode = create_delta_result_node(**outnodedict)

        outdict = {}
        outdict['output_delta_wc_para'] = outputnode.get('output_delta_wc_para')
        #outdict['delta_file'] = delta_file
        #print outdict
        for link_name, node in outdict.iteritems():
            self.out(link_name, node)
'''
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SCF with FLEUR. workflow to'
                 ' converge the chargedensity and optional the total energy.')
    parser.add_argument('--wf_para', type=ParameterData, dest='wf_parameters',
                        help='The pseudopotential family', required=False)
    parser.add_argument('--structure', type=StructureData, dest='structure',
                        help='The crystal structure node', required=False)
    parser.add_argument('--calc_para', type=ParameterData, dest='calc_parameters',
                        help='Parameters for the FLEUR calculation', required=False)
    parser.add_argument('--fleurinp', type=FleurInpData, dest='fleurinp',
                        help='FleurinpData from which to run the FLEUR calculation', required=False)
    parser.add_argument('--remote', type=RemoteData, dest='remote_data',
                        help=('Remote Data of older FLEUR calculation, '
                        'from which files will be copied (broyd ...)'), required=False)
    parser.add_argument('--inpgen', type=Code, dest='inpgen',
                        help='The inpgen code node to use', required=False)
    parser.add_argument('--fleur', type=Code, dest='fleur',
                        help='The FLEUR code node to use', required=True)

    args = parser.parse_args()
    res = fleur_scf_wc.run(wf_parameters=args.wf_parameters,
                                structure=args.structure,
                                calc_parameters=args.calc_parameters,
                                fleurinp=args.fleurinp,
                                remote_data=args.remote_data,
                                inpgen = args.inpgen,
                                fleur=args.fleur)
'''
@wf
def create_delta_result_node(**kwargs):#*args):
    """
    This is a pseudo wf, to create the rigth graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.

    """
    outdict = {}
    outpara =  kwargs.get('results_node', {})
    outdict['output_delta_wc_para'] = outpara.copy()
    # copy, because we rather produce the same node twice then have a circle in the database for now...
    #output_para = args[0]
    #return {'output_eos_wc_para'}
    return outdict


def get_paranode(struc, para_nodes):
    """
    find out if a parameter node for a structure is in para_nodes
    (currently very creedy, but lists are small (100x100) but maybe reduce database accesses)
    """

    suuid = struc.uuid
    formula = struc.get_formula()
    element = formula.translate(None, digits)
    #print para_nodes
    for para in para_nodes:
        struc_uuid = para.get_extra('struc_uuid', None)
        para_form = para.get_extra('formula', None)
        para_ele = para.get_extra('element', None)
        if suuid == struc_uuid:
            return para
        elif formula == para_form:
            return para
        elif element == para_ele:
            return para
        elif element == para_form:
            return para
        else:
            pass
            #Do something else (test if parameters for a certain element are there)
            #....
    # we found no parameter node for the given structure therefore return none
    return None

def write_delta_file(result_dict):
    pass

