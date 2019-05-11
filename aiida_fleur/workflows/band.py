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
This is the worklfow 'band' for the Fleur code, which calculates a
electron bandstructure.
"""
# TODO alow certain kpoint path, or kpoint node, so far auto
# TODO alternative parse a structure and run scf
from __future__ import absolute_import
from __future__ import print_function
import os.path
from aiida.plugins import DataFactory
from aiida.orm import Code
from aiida.engine import WorkChain, ToContext
from aiida.engine import submit
#from aiida.work.process_registry import ProcessRegistry
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
import six

StructureData = DataFactory('structure')
Dict = DataFactory('dict')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleur.fleurinp')


class fleur_band_wc(WorkChain):
    '''
    This workflow calculated a bandstructure from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior
    '''
    # wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    # defaults : tria = True, nkpts = 800, sigma=0.005, emin= , emax =

    _workflowversion = "0.3.3"
    
    _default_options = {'resources': {"num_machines": 1},
                        'max_wallclock_seconds': 60*60,
                        'queue_name': '',
                        'custom_scheduler_commands' : '',
                        #'max_memory_kb' : None,
                        'import_sys_environment' : False,
                        'environment_variables' : {}}
    _default_wf_para = {'kpath' : 'auto',
                        'nkpts' : 800,
                        'sigma' : 0.005,
                        'emin' : -0.50,
                        'emax' :  0.90}
    
    @classmethod
    def define(cls, spec):
        super(fleur_band_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=Dict, required=False,
                   default=Dict(dict=cls._default_wf_para))
        spec.input("options", valid_type=Dict, required=False, 
                   default=Dict(dict=cls._default_wf_para))
        spec.input("remote_data", valid_type=RemoteData, required=True)#TODO ggf run convergence first
        spec.input("fleurinp", valid_type=FleurinpData, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.outline(
            cls.start,
            cls.create_new_fleurinp,
            cls.run_fleur,
            cls.return_results
        )


    def start(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        self.report('started bands workflow version {}'.format(self._workflowversion))
        #print("Workchain node identifiers: ")#'{}'
              #"".format(ProcessRegistry().current_calc_node))

        self.ctx.fleurinp1 = ""
        self.ctx.last_calc = None
        self.ctx.successful = False
        self.ctx.warnings = []
        
        inputs = self.inputs

        wf_dict = inputs.wf_parameters.get_dict()

        # if MPI in code name, execute parallel
        self.ctx.serial = wf_dict.get('serial', False)

        # set values, or defaults
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        #self.ctx.resources = wf_dict.get('resources', {"num_machines": 1})
        #self.ctx.walltime_sec = wf_dict.get('walltime_sec', 10*30)
        #self.ctx.queue = wf_dict.get('queue_name', None)
        
        if 'options' in inputs:
            self.ctx.options = inputs.options.get_dict()
            
    def create_new_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.inputs.wf_parameters.get_dict()
        nkpts = wf_dict.get('nkpts', 500)
        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        sigma = wf_dict.get('sigma', 0.005)
        emin = wf_dict.get('emin', -0.30)
        emax = wf_dict.get('emax', 0.80)

        fleurmode = FleurinpModifier(self.inputs.fleurinp)

        #change_dict = {'band': True, 'ndir' : -1, 'minEnergy' : self.inputs.wf_parameters.get_dict().get('minEnergy', -0.30000000),
        #'maxEnergy' :  self.inputs.wf_parameters.get_dict().get('manEnergy','0.80000000'),
        #'sigma' :  self.inputs.wf_parameters.get_dict().get('sigma', '0.00500000')}
        change_dict = {'band': True, 'ndir' : 0, 'minEnergy' : emin,
                       'maxEnergy' : emax, 'sigma' : sigma} #'ndir' : 1, 'pot8' : True

        fleurmode.set_inpchanges(change_dict)

        if nkpts:
            fleurmode.set_nkpts(count=nkpts)
            #fleurinp_new.replace_tag()

        fleurmode.show(validate=True, display=False) # needed?
        fleurinp_new = fleurmode.freeze()
        self.ctx.fleurinp1 = fleurinp_new

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

        return ToContext(last_calc=future) #calcs.append(future),



    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        self.report('Band workflow Done')
        self.report('A bandstructure was calculated for fleurinpdata {} and is found under pk={}, '
              'calculation {}'.format(self.inputs.fleurinp, self.ctx.last_calc.pk, self.ctx.last_calc))

        #check if band file exists: if not succesful = False
        #TODO be careful with general bands.X

        bandfilename = 'bands.1' # ['bands.1', 'bands.2', ...]
        # TODO this should be easier...
        last_calc_retrieved = self.ctx.last_calc.get_outputs_dict()['retrieved'].folder.get_subfolder('path').get_abs_path('')
        bandfilepath = self.ctx.last_calc.get_outputs_dict()['retrieved'].folder.get_subfolder('path').get_abs_path(bandfilename)
        print(bandfilepath)
        #bandfilepath = "path to bandfile" # Array?
        if os.path.isfile(bandfilepath):
            self.ctx.successful = True
        else:
            bandfilepath = None
            self.report('!NO bandstructure file was found, something went wrong!')
        #TODO corret efermi:
        # get efermi from last calculation
        efermi1 = self.inputs.remote_data.get_inputs()[-1].res.fermi_energy
        #get efermi from this caclulation
        efermi2 = self.ctx.last_calc.res.fermi_energy
        diff_efermi = efermi1 - efermi2
        # store difference in output node
        # adjust difference in band.gnu
        #filename = 'gnutest2'

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['Warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['diff_efermi'] = diff_efermi
        #outputnode_dict['last_calc_pk'] = self.ctx.last_calc.pk
        #outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid
        outputnode_dict['bandfile'] = bandfilepath
        outputnode_dict['last_calc_uuid'] = self.ctx.last_calc.uuid
        outputnode_dict['last_calc_retrieved'] = last_calc_retrieved
        #print outputnode_dict
        outputnode = Dict(dict=outputnode_dict)
        outdict = {}
        #TODO parse Bandstructure
        #bandstructurenode = ''
        #outdict['output_band'] = bandstructurenode
        #or if spin =2
        #outdict['output_band1'] = bandstructurenode1
        #outdict['output_band2'] = bandstructurenode1
        outdict['output_band_wc_para'] = outputnode
        #print outdict
        for key, val in six.iteritems(outdict):
            self.out(key, val)
