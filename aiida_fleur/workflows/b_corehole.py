#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the worklfow 'corehole' using the Fleur code, which calculates Binding
energies and corelevel shifts with different methods.
'divide and conquer'
"""
# TODO alow certain kpoint path, or kpoint node, so far auto
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

import os.path
from aiida.orm import Code, DataFactory
from aiida.work.workchain import WorkChain
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry

from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida.work.workchain import while_, if_
from aiida_fleur.tools.create_corehole import create_corehole

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleur.fleurinp')
FleurProcess = FleurCalculation.process()


class fleur_corehole_wc(WorkChain):
    '''
    Turn key solution for the calculation of core level shift and Binding energies


    '''
    # wf_Parameters: ParameterData,
    '''
    'method' : ['initial', 'full_valence ch', 'half_valence_ch', 'ch', ...]
    'Bes' : [W4f, Be1s]
    'CLS' : [W4f, Be1s]
    'atoms' : ['all', 'postions' : []]
    'references' : ['calculate', or
    'scf_para' : {...}, 'default'
    'relax' : True
    'relax_mode': ['Fleur', 'QE Fleur', 'QE']
    'relax_para' : {...}, 'default'
    'calculate_doses' : False
    'dos_para' : {...}, 'default'
    '''
    '''
    # defaults
    default wf_Parameters::
    'method' : 'initial'
    'atoms' : 'all
    'references' : 'calculate'
    'scf_para' : 'default'
    'relax' : True
    'relax_mode': 'QE Fleur'
    'relax_para' : 'default'
    'calculate_doses' : False
    'dos_para' : 'default'
    '''

    _workflowversion = "0.0.1"

    @classmethod
    def define(cls, spec):
        super(fleur_corehole_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={
                                            'method' : 'initial',
                                            'atoms' : 'all',
                                            'references' : 'calculate',
                                            'relax' : False,
                                            'relax_mode': 'Fleur',
                                            'relax_para' : 'default',
                                            'scf_para' : 'default',
                                            }))
        spec.input("fleurinp", valid_type=FleurinpData, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.outline(
            cls.check_input,
            if_(cls.relaxation_needed)(
                cls.relax),
            if_(cls.supercell_needed)(
                cls.create_supercell
                    ),
            cls.create_new_fleurinp,
            cls.create_coreholes,
            cls.run_scfs,
            cls.collect_results,
            cls.return_results
        )
        #spec.dynamic_output()


    def check_input(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        print('started bands workflow version {}'.format(self._workflowversion))
        print("Workchain node identifiers: {}"
              "".format(ProcessRegistry().current_calc_node))

    def relaxation_needed(self):
        """
        If the structures should be relaxed, check if their Forces are below a certain
        threshold, otherwise throw them in the relaxation wf.
        """
        print('In relaxation inital_state_CLS workflow')
        if self.ctx.relax:
            # TODO check all forces of calculations
            forces_fine = True
            if forces_fine:
                return True
            else:
                return False
        else:
            return False


    def relax(self):
        """
        Do structural relaxation for certain structures.
        """
        print('In relax inital_state_CLS workflow')
        for calc in self.ctx.dos_to_calc:
            pass
            # TODO run relax workflow

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
        print(fleurinp_new)
        #print(fleurinp_new.folder.get_subfolder('path').get_abs_path(''))

    def get_inputs_fleur(self):
        '''
        get the input for a FLEUR calc
        '''
        inputs = FleurProcess.get_inputs_template()

        fleurin = self.ctx.fleurinp1
        #print fleurin
        remote = self.inputs.remote
        inputs.parent_folder = remote
        inputs.code = self.inputs.fleur
        inputs.fleurinpdata = fleurin

        # TODO nkpoints decide n core

        core = 12 # get from computer nodes per machine
        inputs._options.resources = {"num_machines": 1, "num_mpiprocs_per_machine" : core}
        inputs._options.max_wallclock_seconds = 30 * 60

        if self.ctx.serial:
            inputs._options.withmpi = False # for now
            inputs._options.resources = {"num_machines": 1}

        if self.ctx.queue:
            inputs._options.queue_name = self.ctx.queue
            print self.ctx.queue
        # if code local use
        #if self.inputs.fleur.is_local():
        #    inputs._options.computer = computer
        #    #else use computer from code.
        #else:
        #    inputs._options.queue_name = 'th1'

        if self.ctx.serial:
            inputs._options.withmpi = False # for now
            inputs._options.resources = {"num_machines": 1}

        return inputs

    def run_fleur(self):
        '''
        run a fleur calculation
        '''
        FleurProcess = FleurCalculation.process()
        inputs = {}
        inputs = self.get_inputs_fleur()
        #print inputs
        future = submit(FleurProcess, **inputs)
        print 'run Fleur in band workflow'

        return ToContext(last_calc=future)

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        print('Band workflow Done')
        print('A bandstructure was calculated for fleurinpdata {} and is found under pk={}, '
              'calculation {}'.format(self.inputs.fleurinp, self.ctx.last_calc.pk, self.ctx.last_calc))

        #check if band file exists: if not succesful = False
        #TODO be careful with general bands.X

        bandfilename = 'bands.1' # ['bands.1', 'bands.2', ...]
        # TODO this should be easier...
        last_calc_retrieved = self.ctx.last_calc.get_outputs_dict()['retrieved'].folder.get_subfolder('path')
        bandfilepath = self.ctx.last_calc.get_outputs_dict()['retrieved'].folder.get_subfolder('path').get_abs_path(bandfilename)
        print bandfilepath
        #bandfilepath = "path to bandfile" # Array?
        if os.path.isfile(bandfilepath):
            self.ctx.successful = True
        else:
            bandfilepath = None
            print '!NO bandstructure file was found, something went wrong!'
        #TODO corret efermi:
        # get efermi from last calculation
        efermi1 = self.inputs.remote.get_inputs()[-1].res.fermi_energy
        #get efermi from this caclulation
        efermi2 = self.ctx.last_calc.res.fermi_energy
        diff_efermi = efermi1 - efermi2
        # store difference in output node
        # adjust difference in band.gnu
        #filename = 'gnutest2'

        outputnode_dict ={}

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
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['output_corehole_wc_para'] = outputnode
        #print outdict
        for k, v in outdict.iteritems():
            self.out(k, v)
