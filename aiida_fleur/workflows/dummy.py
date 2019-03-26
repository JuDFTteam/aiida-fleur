# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

"""
A dummy workchain to test nested workchains
"""
from __future__ import absolute_import
from __future__ import print_function
import time
from aiida.plugins import Code, DataFactory
from aiida.engine import WorkChain
from aiida.engine import submit
from aiida.engine import ToContext
from aiida.engine.process_registry import ProcessRegistry
from aiida.engine.workchain import Outputs
from aiida.orm.nodes.base import Str
import six
from six.moves import range
RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
Dict = DataFactory('dict')


class dummy_wc(WorkChain):

    def __init__(self, *args, **kwargs):
        super(dummy_wc, self).__init__(*args, **kwargs)

    @classmethod
    def define(cls, spec):
        super(dummy_wc, cls).define(spec)
        spec.input("str_display", valid_type=Str, required=True),
        spec.outline(
            cls.display,
            cls.run_sub1,
            #cls.run_sub2,
            #cls.run_sub3,
            cls.return_out
        )
        spec.dynamic_output()

    def display(self):
        message = 'message from dummy_wc: {}'.format(self.inputs.str_display)
        self.report(message)

        self.ctx.sub1 = None
        self.ctx.sub2 = None
        self.ctx.sub31 = None
        self.ctx.sub32 = None
        time.sleep(65)


    def get_input(self):
        message = 'I am here'
        self.report(message)
        time.sleep(10)


    def run_sub1(self):
        """
        Submiting this subwork chain is still buggy somehow...
        """
        print('run_sub1')
        n = 3
        allres = {}
        time.sleep(35)
        for i in range(0,n):
            inputs_sub = Str('This is wonderful 1.{}'.format(i))
            res = submit(sub_dummy_wc, str_display=inputs_sub)
            label = 'sub1_run{}'.format(i)
            allres[label] = res
            time.sleep(65)
            self.get_input()
        return ToContext(**allres)


    def run_sub2(self):
        print('run_sub2')
        inputs_sub = Str('This is wonderful 2')
        res = sub_dummy_wc.run(str_display=inputs_sub)

        self.ctx.sub2 = res


    def return_out(self):
        message = 'generating output nodes'
        self.report(message)
        subout = '{} | {} | {}, {}'.format(self.ctx.sub1, self.ctx.sub2, self.ctx.sub31, self.ctx.sub32)
        self.report(subout)
        outdict = {'out_dummy_wc' : Str('wonderful dummy_wc')}
        for link_name, node in six.iteritems(outdict):
            self.out(link_name, node)


class sub_dummy_wc(WorkChain):

    def __init__(self, *args, **kwargs):
        super(sub_dummy_wc, self).__init__(*args, **kwargs)

    @classmethod
    def define(cls, spec):
        super(sub_dummy_wc, cls).define(spec)
        spec.input("str_display", valid_type=Str, required=True),
        spec.outline(
            cls.display,
            cls.run_sub,
            cls.return_out
        )
        spec.dynamic_output()

    def display(self):
        message = 'message from sub_dummy_wc: {}'.format(self.inputs.str_display)
        self.report(message)
        time.sleep(65)
    def run_sub(self):
        pass
        # ggf to test further depth call this wc rekursively


    def return_out(self):
        time.sleep(65)
        message = 'generating output nodes sub_dummy'
        self.report(message)
        outdict = {'out_sub_dummy_wc' : Str('wonderful sub_dummy_wc')}
        for link_name, node in six.iteritems(outdict):
            self.out(link_name, node)


class dummy_wf():
    pass
