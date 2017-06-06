#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the worklfow 'fleur_delta_wc' which is a turnkey solution to calculate a delta for a given code with AiiDA.
"""

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain
from aiida.work.workchain import while_, if_
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry
from aiida.orm.querybuilder import QueryBuilder

from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur, get_inputs_inpgen
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.wokrlfows.eos import fleur_eos_wc

from aiida_fleur.tools.xml_util import eval_xpath2
from lxml import etree

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')


class fleur_delta_wc(WorkChain):
    """
    This workflow calculates a equation of states and from a given 
    group of structures in the database using a group of given parameter nodes in the database

    """

    _workflowversion = "0.0.1"
    _wf_default = {'points' : 4,
                   'step' : 0.002,
                   'queue_name' : '',
                   'resources' : {"num_machines": 1},
                   'walltime_sec' : 60*60}

    def __init__(self, *args, **kwargs):
        super(fleur_delta_wc, self).__init__(*args, **kwargs)

    @classmethod
    def define(cls, spec):
        super(fleur_delta_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False, 
                   default=ParameterData(dict={
                                               'struc_group': 'delta',
                                               'para_group' : 'delta',
                                               'add_extra' : {'type' : 'delta run'},
                                               'group_label' : 'delta_eos',
                                               'points' : 4,
                                               'step' : 0.02,
                                               'queue_name' : '',
                                               'options' : {'resources' : {"num_machines": 1},
                                               'walltime_sec' : 60*60}}))
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.outline(
            cls.start_up,
            cls.run_eos,
            cls.get_res,
            cls.calc_delta,
            cls.return_results,

        )
        spec.dynamic_output()

    def start_up(self):
        """
        init context and some parameters
        """
        
        #print('started delta workflow version {}'.format(self._workflowversion))
        #print("Workchain node identifiers: {}".format(ProcessRegistry().current_calc_node))
        self.report('started delta workflow version {} with idenifier: {}'
                    ''.format(self._workflowversion, ProcessRegistry().current_calc_node))

        # init
        self.ctx.calcs_to_run =[]
        # input  check

        # check if right codes
        wf_dict = self.inputs.wf_parameters.get_dict()
        self.ctx.inputs_eos = {
            'fleur': self.inputs.fleur,
            'inpgen': self.inputs.inpgen,
            'wf_parameters': {'points' : wf_dict.get('points', 5), wf_dict.get('step', 0.02), 'guess' : 1.0},
            'options': wf_dict.get('options',
            {'resources': {'num_machines': 1}, 'max_wallclock_seconds': 1800})
            }
        self.ctx.wc_eos_para = ParameterData(dict=self.ctx.inputs_eos.get('wf_parameters'))

        #get all delta structure
        #qb = QueryBuilder()
        #qb.append(StructureData, filters={})
        #all_delta_struc = qb.all()

        #get all delta parameters
        #all_parama = load_group()
        all_para = []
        
        #fill calcs to run
        calcs = []
        for para in all_para:
            struc_uuid = para.get_extra('structure_uuid')
            struc = load_node(struc_uuid)
            calcs.append((struc, para))
        self.ctx.calcs_to_run = calcs

    def run_eos(self):
        """
        Run the equation of states for all delta structures with their parameters
        """
        pass

        '''
        eos_results =[]
        wc_eos_para = self.ctx.wc_eos_para
        fleur = self.ctx.inputs_eos.get('fleur')
        inpgen = self.ctx.inputs_eos.get('inpgen')
        for struc, para in self.ctx.calcs_to_run:
            eos_future = submit(fleur_eos_wc, 
                                wf_parameters=wc_eos_para, structure=struc,
                                calc_parameters=para, inpgen=inpgen, fleur=fleur)
            self.report('launching fleur_eos_wc<{}> on structure {} with parameter {}'.format(runnning.pid, struc.pk, para.pk)
            eos_results.append(eos_future)

        return ToContext(workchain_eos=eos_results)
        '''


    def return_results(self):
        """
        return the results of the calculations
        """

        # log some stuff in report

        # a text file should be written and stored as single file data and
        #parameter data node in the database

        outputnode_dict ={}


        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid

        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['output_delta_wc_para'] = outputnode
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
