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
This is the worklfow 'dos' for the Fleur code, which calculates a
density of states (DOS).
"""
from __future__ import absolute_import
from __future__ import print_function
import os.path
import six

from aiida.plugins import DataFactory
from aiida.orm import Code, StructureData, Dict, RemoteData
from aiida.engine import WorkChain, ToContext
from aiida.engine import submit
#from aiida.work.process_registry import ProcessRegistry
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.data.fleurinp import FleurinpData


class fleur_dos_wc(WorkChain):
    """
    This workflow calculated a DOS from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior

    wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    defaults : tria = True, nkpts = 800, sigma=0.005, emin= -0.3, emax = 0.8
    """

    _workflowversion = '0.3.3'

    _default_options = {
        'resources': {
            'num_machines': 1
        },
        'max_wallclock_seconds': 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        # 'max_memory_kb' : None,
        'import_sys_environment': False,
        'environment_variables': {}
    }
    _default_wf_para = {'tria': True, 'nkpts': 800, 'sigma': 0.005, 'emin': -0.30, 'emax': 0.80}

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('wf_parameters', valid_type=Dict, required=False, default=lambda: Dict(dict=cls._default_wf_para))
        spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.input('settings', valid_type=Dict, required=False)
        spec.input('options', valid_type=Dict, required=False, default=lambda: Dict(dict=cls._default_options))
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        # TODO ggf run convergence first
        spec.input('remote_data', valid_type=RemoteData, required=False)
        #spec.input("inpgen", valid_type=Code, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.outline(cls.start, cls.create_new_fleurinp, cls.run_fleur, cls.return_results)
        # spec.dynamic_output()

    def start(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        # input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        self.report('Started dos workflow version {}'
                    # "Workchain node identifiers: ")#{}"
                    ''.format(self._workflowversion))  # ProcessRegistry().current_calc_node))

        self.ctx.fleurinp1 = ''
        self.ctx.last_calc = None
        self.ctx.successful = False
        self.ctx.warnings = []

        wf_dict = self.inputs.wf_parameters.get_dict()

        # if MPI in code name, execute parallel
        self.ctx.serial = wf_dict.get('serial', False)

        # set values, or defaults
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)

        inputs = self.inputs
        if 'options' in inputs:
            self.ctx.options = inputs.options.get_dict()

        if 'remote_data' in inputs:
            self.ctx.remote = inputs.remote_data

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ('The code you provided for FLEUR does not use the plugin fleur.fleur')
                # self.control_end_wc(error)
                self.report(error)
                return 1

    def create_new_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.inputs.wf_parameters.get_dict()
        nkpts = wf_dict.get('nkpts', 800)
        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        tria = wf_dict.get('tria', True)
        sigma = wf_dict.get('sigma', 0.005)
        emin = wf_dict.get('emin', -0.30)
        emax = wf_dict.get('emax', 0.80)

        fleurmode = FleurinpModifier(self.inputs.fleurinp)

        # change_dict = {'dos': True, 'ndir' : -1, 'minEnergy' : self.inputs.wf_parameters.get_dict().get('minEnergy', -0.30000000),
        # 'maxEnergy' :  self.inputs.wf_parameters.get_dict().get('manEnergy','0.80000000'),
        # 'sigma' :  self.inputs.wf_parameters.get_dict().get('sigma', '0.00500000')}
        change_dict = {'dos': True, 'ndir': -1, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}

        fleurmode.set_inpchanges(change_dict)
        if tria:
            change_dict = {'mode': 'tria'}
            fleurmode.set_inpchanges(change_dict)
        if nkpts:
            fleurmode.set_nkpts(count=nkpts)
            # fleurinp_new.replace_tag()
        fleurmode.show(validate=True, display=False)  # needed?
        fleurinp_new = fleurmode.freeze()
        self.ctx.fleurinp1 = fleurinp_new
        # print(fleurinp_new)
        # print(fleurinp_new.folder.get_subfolder('path').get_abs_path(''))

    def run_fleur(self):
        """
        run a FLEUR calculation
        """
        fleurin = self.ctx.fleurinp1
        remote = self.inputs.remote_data
        code = self.inputs.fleur

        options = self.ctx.options

        inputs = get_inputs_fleur(code, remote, fleurin, options, serial=self.ctx.serial)
        future = submit(FleurCalculation, **inputs)

        return ToContext(last_calc=future)  # calcs.append(future),

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        self.report('Dos workflow Done')
        # self.report('A DOS was calculated for calculation {} and is found under pk=, '
        #      'calculation {}')#.format(self.ctx.last_calc, ctx['last_calc'] )

        # check if dos file exists: if not succesful = False
        # TODO be careful with general DOS.X
        dosfilename = 'DOS.1'  # ['DOS.1', 'DOS.2', ...]
        # TODO this should be easier...
        dosfilepath = self.ctx.last_calc.get_outputs_dict()['retrieved'].folder.get_subfolder('path').get_abs_path(
            dosfilename)
        print(dosfilepath)
        # dosfilepath = "path to dosfile" # Array?
        if os.path.isfile(dosfilepath):
            self.ctx.successful = True
        else:
            dosfilepath = None
            self.report('!NO DOS.1 file was found, something went wrong!')

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['Warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        #outputnode_dict['last_calc_pk'] = self.ctx.last_calc.pk
        #outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid
        outputnode_dict['dosfile'] = dosfilepath
        # add nkpoints, emin, emax, sigma, tria

        # print outputnode_dict
        outputnode = Dict(dict=outputnode_dict)
        outdict = {}
        # TODO parse dos to dosnode
        #dosnode = ''
        #outdict['output_band'] = dosnode
        # or if spin =2
        #outdict['output_band1'] = dosnode1
        #outdict['output_band2'] = dosnode2
        outdict['output_dos_wc_para'] = outputnode
        # print outdict
        for k, v in six.iteritems(outdict):
            self.out(k, v)
