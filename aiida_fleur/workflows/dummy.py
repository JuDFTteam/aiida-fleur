#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A dummy workchain to test nested workchains
"""
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import time
from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain
from aiida.work.run import submit, async
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry
from aiida.work.workchain import Outputs
from aiida.orm.data.base import Str
RemoteData = DataFactory('remote')
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')


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

    def run_sub3(self):
        print('run_sub3')
        inputs_sub = Str('This is wonderful 3.1')
        inputs_sub2 = Str('This is wonderful 3.2')
        res = async(sub_dummy_wc, str_display=inputs_sub)
        res2 = async(sub_dummy_wc, str_display=inputs_sub2)

        return ToContext(sub31 = res, sub32 = res2)

    def return_out(self):
        message = 'generating output nodes'
        self.report(message)
        subout = '{} | {} | {}, {}'.format(self.ctx.sub1, self.ctx.sub2, self.ctx.sub31, self.ctx.sub32)
        self.report(subout)
        outdict = {'out_dummy_wc' : Str('wonderful dummy_wc')}
        for link_name, node in outdict.iteritems():
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
        for link_name, node in outdict.iteritems():
            self.out(link_name, node)


class dummy_wf():
    pass
