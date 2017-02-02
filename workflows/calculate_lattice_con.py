#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this module you find the worklfow 'lattice_constant' for the calculation of 
of a lattice constant"""

#TODO: print more user info
#  allow different inputs, make things optional(don't know yet how)
#  half number of iteration if you are close to be converged. (therefore one can start with 18 iterations, and if thats not enough run agian 9 or something)

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import sys,os
from ase import *
from ase.lattice.surface import *
from ase.io import *
from aiida.orm import Code, CalculationFactory, DataFactory
from aiida.orm import Computer
from aiida.orm import load_node
#from aiida.orm.data.fleurinp import FleurinpData as FleurInpData
from aiida.orm.data.singlefile import SinglefileData
#from aiida.workflows2.run import run, async
#from aiida.workflows2.fragmented_wf import FragmentedWorkfunction, \
#    ResultToContext, if_, while_
#from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData
#from aiida.workflows2.defaults import registry

from aiida.work.workfunction import workfunction as wf
from aiida.work.workchain import WorkChain

from aiida.orm.calculation.job.fleur_inp.fleurinputgen import FleurinputgenCalculation
from aiida.orm.calculation.job.fleur_inp.fleur import FleurCalculation
from aiida.tools.codespecific.fleur.StructureData_util import eos_structures
from convergence import fleur_convergence
#from convergence2 import fleur_convergence2
from aiida.work.workchain import ToContext



StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleurinp.fleurinp')
#computer_name = 'local_mac'
#computer = Computer.get(computer_name)

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"


class lattice_constant(WorkChain):
    """
    This workflow calculates a lattice constant

    :Params: a parameterData node,
    :returns: Success, last result node, list with convergence behavior
    """
    @classmethod
    def _define(cls, spec):
        spec.input("wf_parameters", valid_type=ParameterData)
        spec.input("structure", valid_type=StructureData)
        spec.input("calc_parameters", valid_type=ParameterData)
        spec.input("inpgen", valid_type=Code)
        spec.input("fleur", valid_type=Code)
        spec.outline(
            cls.start,
            cls.structures,
            cls.converge_scf,
            cls.return_results
        )
        spec.dynamic_output()

    def start(self, ctx):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        ### input check ### ? or done automaticly, how optional?
        ctx.last_calc2 = None
        ctx.calcs1 = []
        ctx.structures = []
        ctx.scalelist = []
        ctx.successful2 = True#False # TODO get all succesfull from convergence, if all True this
        wf_dict = self.inputs.wf_parameters.get_dict()
        ctx.points = wf_dict.get('points', 2)#9
        ctx.step = wf_dict.get('step', 0.002)
        ctx.guess = wf_dict.get('guess', 1.00)
        # set values, or defaults, default: always converge charge density, crit < 0.00002, max 4 fleur runs
        ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)
        print 'start'

    def structures(self, ctx):
        """
        Creates structure data nodes with different Volume (lattice constants)
        """

        points = ctx.points
        step = ctx.step
        guess = ctx.guess
        startscale = guess-(points-1)/2*step
        for point in range(points):
            ctx.scalelist.append(startscale + point*step)
        print 'scaling factors which will be calculated:{}'.format(ctx.scalelist)

        ctx.structurs = eos_structures(self.inputs.structure, ctx.scalelist)

    def converge_scf(self, ctx):
        """
        start scf-cycle from Fleur calculation
        """
        calcs = []
        # run a convergence worklfow# TODO or sumbit?
        for struc in ctx.structurs:
            inputs = self.get_inputs_scf(ctx)
            inputs['structure'] = struc
            res = run(fleur_convergence, wf_parameters=inputs['wf_parameters'],
                      structure=inputs['structure'], calc_parameters=inputs['calc_parameters'], inpgen = inputs['inpgen'], fleur=inputs['fleur'] )# async
            ctx.calcs1.append(res)
            print ctx.calcs1
            #ResultToContext(ctx.calcs1.append(res))
            #calcs.append(res)
        #ctx.last_calc2 = res#.get('remote_folder', None)
        return ctx.calcs1#ResultToContext(**calcs) #calcs.append(future),

    def get_inputs_scf(self, ctx):
        """
        get the inputs for a scf-cycle
        """
        inputs = {}
        # produce the inputs for a convergence worklfow
        # create input from that
        print 'getting inputs for scf'
        inputs['wf_parameters'] = self.inputs.wf_parameters
        #inputs['structure'] = self.inputs.structure
        inputs['calc_parameters'] = self.inputs.calc_parameters
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur

        return inputs

    def fit_latticeconstant(self, scale, eT):
        """
        Extract the lattice constant out of an parabola fit.
        
        scale : list of scales, or lattice constants
        eT: list of total energies
        """
        import numpy as np
        # call fitt pol2 # or something else
        #def func(x, a, b, c):
        #    return a*x**2 + b*x + c
        f1 = np.polyfit(scale,eT,2)
        a0 = f1[0]
        a1 = f1[1]
        a2 = f1[2]
        la = -0.5*a1/a0
        c = a2 - a1**2/a2
        return a0,la,c, f1

    def return_results(self, ctx):
        """
        return the results of the calculations
        """
        # TODO create parameterNode with all results, all total energy and their, scaling
        #factor and lattice constant.
        # TODO: maybe create a standart plot?
        # node : {scaling: list, total_energy: list, structures : list, calculations_outputs : list,
        # convergence : list, nsteps : int, guess :float, stepsize : float, lattice_constant :float, lattice_constant_units : 'Angstroem'
        distancelist = []
        t_energylist = []
        latticeconstant = 0
        print ctx.calcs1
        for calc in ctx.calcs1:
            if calc.get('successful', False) == False:
                ctx.successful2 = False
                # TODO print something
            outpara = calc['output_parameters'].get_dict()
            #get total_energy, density distance
            t_e = outpara.get('energy', -1)
            dis = outpara.get('charge_density', -1)
            t_energylist.append(t_e)
            distancelist.append(dis)
        # fit lattice constant
        a, latticeconstant, c, fit = self.fit_latticeconstant(ctx.scalelist, t_energylist)
        out = {'scaling': ctx.scalelist, 'total_energy': t_energylist,
               'structures' : ctx.structures, 'calculations' : ctx.calcs1,#[]
               'convergence' : distancelist, 'nsteps' : ctx.points,
               'guess' : ctx.guess , 'stepsize' : ctx.step,
               'lattice_constant' : latticeconstant,
               'lattice_constant_units' : 'Angstroem',
               'fitresults' : [a, latticeconstant, c], 'fit' : fit, 'successful' : ctx.successful2}
        if ctx.successful2:
            print 'Done, lattice constant calculation complete'
        else:
            print 'Done, but something went wrong.... Properly some individual calculation failed or a scf-cylcle did not reach the desired distance.'
        outdict = out#ctx.last_calc2
        for k, v in outdict.iteritems():
            self.out(k, v)        # return success, and the last calculation outputs
        # ouput must be aiida Data types.

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='lattice constant calculation with Fleur. Do scf-cycles for a structure with different scalling.')
    parser.add_argument('--wf_para', type=ParameterData, dest='wf_parameters',
                        help='Parameter data node, specifing workflow parameters', required=False)
    parser.add_argument('--inpgen', type=Code, dest='inpgen',
                        help='The inpgen code node to use', required=True)
    parser.add_argument('--fleur', type=Code, dest='fleur',
                        help='The FLEUR code node to use', required=True)
    parser.add_argument('--structure', type=StructureData, dest='structure',
                        help='The crystal structure node', required=True)
    parser.add_argument('--calc_para', type=ParameterData, dest='calc_parameters',
                        help='Parameters for the FLEUR calculation', required=False)
    args = parser.parse_args()
    res = run(lattice_constant, wf_parameters=args.wf_parameters, structure=args.structure, calc_parameters=args.calc_parameters, inpgen = args.inpgen, fleur=args.fleur)



def parabola(x, a, b, c):
    return a*x**2 + b*x + c










