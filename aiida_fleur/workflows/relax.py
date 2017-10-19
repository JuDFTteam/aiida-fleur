#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module, contains the crystal structure relaxation workflow for FLEUR.
"""

#TODO: print more user info
#  allow different inputs, make things optional(don't know yet how)
#  half number of iteration if you are close to be converged. (therefore one can start with 18 iterations, and if thats not enough run agian 9 or something)

#import sys,os
#from ase import *
#from ase.lattice.surface import *
#from ase.io import *
from aiida.orm import Code, DataFactory, load_node
from aiida.work.workchain import WorkChain, while_, if_, ToContext
from aiida.work.run import run, submit
from aiida_fleur.calculation.fleurinputgen import FleurinputgenCalculation
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.workflows.scf import fleur_scf_wc


StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

class fleur_relax_wc(WorkChain):
    """
    This workflow relaxes a structure with Fleur calculation.

    :Params: a parameterData node,
    :returns: Success, last result node, list with convergence behavior
    """
    # wf_parameters: { wf_convergence_para:{  'density_criterion', 'energy_criterion'} #'converge_density' = True, 'converge_energy'= True}, max_force_cycle, force_criterion
    # calc_parameters: Parameter data for inpgen calculation
    @classmethod
    def _define(cls, spec):
        super(fleur_relax_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=True)
                   #, required=False, default = ParameterData(
                   #dict={'relax_runmax' : 4, 'fleur_runmax' : 10, 'density_criterion' : 0.00002 , 'converge_density': True, 'converge_energy' : True, 'energy_criterion' : 0.00002})# htr
                   #{default=make_str('quantumespresso.pw')))
        spec.input("structure", valid_type=StructureData)#, required=False
        spec.input("calc_parameters", valid_type=ParameterData)#, required=False
        #spec.input("parent_calculation", valid_type=JobCalculation)#, required=False # either fleur or inpgen.
        spec.input("inpgen", valid_type=Code)#, required=False
        #spec.input("computer", valid_type=Computer)#, required=False, default=get_computer_from_string('iff003')
        spec.input("fleur", valid_type=Code)#, required=True
        spec.outline(
            cls.start,
            cls.converge_scf,
            cls.calculate_forces,
            while_(cls.condition)(
                cls.converge_scf,
                cls.calculate_forces
                ),
            cls.return_results,
        )
        spec.dynamic_output()

    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        ### input check ### ? or done automaticly, how optional?
        self.ctx.last_calc2 = None
        self.ctx.loop_count2 = 0
        self.ctx.calcs = []
        self.ctx.successful2 = False

        # set values, or defaults, default: always converge charge density, crit < 0.00002, max 4 fleur runs
        self.ctx.max_number_runs = self.inputs.wf_parameters.get_dict().get('relax_runmax', 4)
        self.ctx.max_force_cycle = self.inputs.wf_parameters.get_dict().get('max_force_cycle', 4)
        print 'start'

    def converge_scf(self):
        """
        start scf-cycle from Fleur calculation
        """
        # run a convergence worklfow
        # Comment: Here we wait, because of run,
        # maybe using a future and submit instead might be better
        #print 'ctx, before scf {} {}'.format(ctx, [a for a in self.ctx])
        inputs = self.get_inputs_scf(self.ctx)

        if self.ctx.last_calc2:
            #print 'inputs for convergnce2: {}'.format(inputs)
            res = run(fleur_scf_wc,
                      wf_parameters=inputs['wf_parameters'],
                      fleurinp=inputs['fleurinp'],
                      fleur=inputs['fleur'])
                      #inputs)#
                  #wf_parameters=wf_para,
                  #structure=s,
                  #calc_parameters=parameters,
                  #inpgen = code,
                  #fleur=code2)#, computer=computer)
        else:
            res = run(fleur_scf_wc, wf_parameters=inputs['wf_parameters'],
                      structure=inputs['structure'], calc_parameters=inputs['calc_parameters'], inpgen = inputs['inpgen'], fleur=inputs['fleur'] )#inputs)#
        #print 'ctx, after scf {} {}'.format(ctx, [a for a in self.ctx])

        #print 'output of convergence: {}'.format(res)
        self.ctx.last_calc2 = res#.get('remote_folder', None)
        #print res
        #return ResultToContext(last_calc2=res)

    def get_inputs_scf(self):
        """
        get the inputs for a scf-cycle
        """
        inputs = {}
        # produce the inputs for a convergence worklfow
        # if last calculation
        # create input from that
        print 'getting inputs for scf'
        #print 'last calc: {} '.format(ctx.last_calc2)
        if self.ctx.last_calc2:
            # get fleurinpData from inp_new.xml
            inputs['wf_parameters'] = self.inputs.wf_parameters
            inputs['fleur'] = self.inputs.fleur
            inputs['fleurinp'] = self.ctx['last_calc2']['fleurinpData']
            #inputs.wf_parameters = self.inputs.wf_parameters#.get_dict()
            #inputs.fleur = self.inputs.fleur
            #inputs.fleurinp = self.ctx['last_calc22']['fleurinp']
            #inputs.parent_folder = self.ctx['last_calc2']['remote_folder']
        # if not use input given from workflow
        else:
            inputs['wf_parameters'] = self.inputs.wf_parameters
            inputs['structure'] = self.inputs.structure
            inputs['calc_parameters'] = self.inputs.calc_parameters
            inputs['inpgen'] = self.inputs.inpgen
            inputs['fleur'] = self.inputs.fleur
            #inputs.wf_parameters = self.inputs.wf_parameters#.get_dict()
            #inputs.structure = self.inputs.structure
            #inputs.calc_parameters = self.input.calc_parameters
            #inputs.inpgen = self.inputs.inpgen
            #inputs.fleur = self.inputs.fleur


        return inputs

    def calculate_forces(self):
        """
        starts a Fleur calculation which calculates forces.
        """
        # get converged calculation
        # create new calculation with l_f =T, gff allow for relaxation of certain
        # atomtyps or species
        # dont copy broyden files, copy cdn1?
        # run fleur
        self.ctx.loop_count2 = self.ctx.loop_count2 + 1
        last_calc2 = self.ctx.last_calc2
        # be careful, test if convergence success or not...
        fleurinp = last_calc2.get('fleurinp', None)
        if fleurinp:
            fleurinp_new = fleurinp.copy()
        else: # warning
            fleurinp_new = None
            print 'no fleurinp data was found in last_calc2'
        if False: # TODO something other specified in wf parameters
            change_dict = {'l_f' : True}
        else: # relax every atom in all direction specified in inp.xml
            change_dict = {'l_f' : True} # for calculation of forces

        fleurinp_new.set_inpchanges(change_dict)
        #fleurinp_new.store()# needed?

        remote = last_calc2.get('remote_folder', None)

        # run fleur
        FleurProcess = FleurCalculation.process()
        inputs = FleurCalculation.process().get_inputs_template()

        #inputs.parent_folder = remote
        inputs.code = self.inputs.fleur
        inputs.fleurinpdata = fleurinp_new
        inputs.parent_folder = remote # we need to copy cnd1
        inputs._options.resources = {"num_machines": 1}
        inputs._options.max_wallclock_seconds = 30 * 60
        # if code local use
        #if self.inputs.fleur.is_local():
        #    inputs._options.computer = computer
        #else:
        #    inputs._options.queue_name = 'th1'
        inputs._options.withmpi = False # for now
        print 'Relax structure with Fleur, cycle: {}'.format(self.ctx.loop_count2)
        future = self.submit(FleurProcess, inputs)

        self.ctx.calcs.append(future)

        return ToContext(last_calc2=future)

    def condition(self):
        """
        check convergence condition
        """
        #pass max_force_cycle, force_criterion
        forces_converged = False
        energy_converged = False
        largest_force = self.ctx.last_calc2['output_parameters'].get_dict().get('force_largest')
        print 'largest_force: {}'.format(largest_force)
        if self.inputs.wf_parameters.get_dict().get('converge_density', True):
            #print self.ctx.last_calc2['output_parameters'].get_dict()
            if self.inputs.wf_parameters.get_dict().get('force_criterion', 0.00002) >= largest_force:
                forces_converged = True


        # TODO?
        if self.inputs.wf_parameters.get_dict().get('converge_energy', True):
            #print self.ctx.last_calc2['output_parameters'].dict.energy_hartree
            #if self.inputs.wf_parameters.get_dict().get('energy_criterion', 0.0002) >= self.ctx.last_calc2['output_parameters'].dict.energy_hartree:
                #last_energy: # energy converged
            energy_converged = True
        else:
            energy_converged = False

        if forces_converged and energy_converged:
            self.ctx.successful2 = True
            return False
        elif self.ctx.loop_count2 >= self.ctx.max_force_cycle:
            return False
        else:
            return True


    def return_results(self):
        """
        return the results of the calculations
        """
        largest_force = self.ctx.last_calc2['output_parameters'].get_dict().get('force_largest')

        if self.ctx.successful2:
            print 'Done, Des wors, forces converged'
            print 'Fleur converged the total forces after {} scf-force cycles to {} ""'.format(self.ctx.loop_count2, largest_force)
        else: # loopcount reached
            print 'Done, I reached the number of forces cycles, system is not relaxed enough.'
            print 'Fleur converged the total forces after {} scf-force cycles to {} ""'.format(self.ctx.loop_count2, largest_force)
        outdict = self.ctx.last_calc2
        for k, v in outdict.iteritems():
            self.out(k, v)        # return success, and the last calculation outputs
        # ouput must be aiida Data types.