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
In this module you find the workflow 'fleur_eos_wc' for the calculation of
of an equation of state
"""
#TODO: print more user info
#  allow different inputs, make things optional(don't know yet how)
#  half number of iteration if you are close to be converged. (therefore one can start with 18 iterations, and if thats not enough run agian 9 or something)
#from sys import argv
#import time
import numpy as np
from aiida.orm import Code, DataFactory, load_node
from aiida.orm.data.base import Float
from aiida.work.workchain import WorkChain, ToContext#,Outputs
from aiida.work import workfunction as wf
from aiida.work.run import submit
from aiida_fleur.tools.StructureData_util import rescale, is_structure
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf_util import check_eos_energies

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
FleurInpData = DataFactory('fleur.fleurinp')


class fleur_eos_wc(WorkChain):
    """
    This workflow calculates the equation of states of a structure.
    Calculates several unit cells with different volumes.
    A Birch_Murnaghan  equation of states fit determines the Bulk modulus and the
    groundstate volume of the cell.

    :param wf_parameters: ParameterData node, optional 'wf_parameters', protocol specifieing parameter dict
    :param structure: StructureData node, 'structure' crystal structure
    :param calc_parameters: ParameterData node, optional 'calc_parameters' parameters for inpgen
    :param inpgen: Code node,
    :param fleur: Code node,


    :return output_eos_wc_para: ParameterData node, contains relevant output information.
    about general succces, fit results and so on.


    example input.
    """

    _workflowversion = "0.3.3"

    _default_options = {
                        u'resources' : {"num_machines": 1},
                        u'max_wallclock_seconds' : 6*60*60,
                        u'queue_name' : u'',
                        u'custom_scheduler_commands' : u'',
                        u'import_sys_environment' : False,
                        u'environment_variables' : {}}    

                        
    ERROR_INVALID_INPUT_RESOURCES = 1
    ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED = 2
    ERROR_INVALID_CODE_PROVIDED = 3
    ERROR_INPGEN_CALCULATION_FAILED = 4
    ERROR_CHANGING_FLEURINPUT_FAILED = 5
    ERROR_CALCULATION_INVALID_INPUT_FILE = 6
    ERROR_FLEUR_CALCULATION_FALIED = 7
    ERROR_CONVERGENCE_NOT_ARCHIVED = 8
    
    
    def __init__(self, *args, **kwargs):
        super(fleur_eos_wc, self).__init__(*args, **kwargs)


    @classmethod
    def define(cls, spec):
        super(fleur_eos_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={
                       'fleur_runmax': 4,
                       'points' : 9,
                       'step' : 0.002,
                       'guess' : 1.00}))
        spec.input("structure", valid_type=StructureData, required=True)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("options", valid_type=ParameterData, required=False, 
                   default=ParameterData(dict={
                            'resources': {"num_machines": 1},
                            'max_wallclock_seconds': 60*60,
                            'queue_name': '',
                            'custom_scheduler_commands' : '',
                            'import_sys_environment' : False,
                            'environment_variables' : {}}))
        spec.input("settings", valid_type=ParameterData, required=False)

        spec.outline(
            cls.start,
            cls.structures,
            cls.converge_scf,
            cls.return_results
        )

        
    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        self.report("Started eos workflow version {} "
                    #"Workchain node identifiers: {}"
                    "".format(self._workflowversion))#, self.uuid))

        
        ### input check ### ? or done automaticly, how optional?
        self.ctx.last_calc2 = None
        self.ctx.calcs = []
        self.ctx.calcs_future = []
        self.ctx.structures = []
        self.ctx.temp_calc = None
        self.ctx.structurs_uuids = []
        self.ctx.scalelist = []
        self.ctx.volume = []
        self.ctx.volume_peratom = []
        self.ctx.org_volume = -1# avoid div 0
        self.ctx.labels = []
        self.ctx.successful = True#False
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        # TODO get all succesfull from convergence, if all True this


        wf_dict = self.inputs.wf_parameters.get_dict()
        # set values, or defaults, default: always converge charge density,
        # crit < 0.00002, max 4 fleur runs

        self.ctx.points = wf_dict.get('points', 9)
        self.ctx.step = wf_dict.get('step', 0.002)
        self.ctx.guess = wf_dict.get('guess', 1.00)
        self.ctx.serial = wf_dict.get('serial', False)#True
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)

        #defaultoptions = self._default_options
        #options = wf_dict.get('options', defaultoptions)
        #if 'options' in self.inputs:
        #    options = self.inputs.options.get_dict()
        #else:
        #    options = defaultoptions
        #for key, val in defaultoptions.iteritems():
        #    options[key] = options.get(key, val)
        #self.ctx.options = options
        
        inputs = self.inputs

        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for inpgen of FLEUR does not "
                         "use the plugin fleur.inpgen")
                self.control_end_wc(error)
                return self.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for FLEUR does not "
                         "use the plugin fleur.fleur")
                self.control_end_wc(error)
                return self.ERROR_INVALID_CODE_PROVIDED

    def structures(self):
        """
        Creates structure data nodes with different Volume (lattice constants)
        """
        points = self.ctx.points
        step = self.ctx.step
        guess = self.ctx.guess
        startscale = guess-(points-1)/2*step

        for point in range(points):
            self.ctx.scalelist.append(startscale + point*step)

        self.report('scaling factors which will be calculated:{}'.format(self.ctx.scalelist))
        self.ctx.org_volume = self.inputs.structure.get_cell_volume()
        self.ctx.structurs = eos_structures(self.inputs.structure, self.ctx.scalelist)

    def converge_scf(self):
        """
        Launch fleur_scfs from the generated structures
        """
        calcs = {}

        for i, struc in enumerate(self.ctx.structurs):
            inputs = self.get_inputs_scf()
            inputs['structure'] = struc
            natoms = len(struc.sites)
            label = str(self.ctx.scalelist[i])
            label_c = '|eos| fleur_scf_wc'
            description = '|fleur_eos_wc|fleur_scf_wc|scale {}, {}'.format(label, i)
            inputs['_label'] = label_c
            inputs['_description'] = description
            
            self.ctx.volume.append(struc.get_cell_volume())
            self.ctx.volume_peratom.append(struc.get_cell_volume()/natoms)
            self.ctx.structurs_uuids.append(struc.uuid)

            #calc_para = inputs['calc_parameters']
            
            # Here we give the same wf_parameters to the fleur_scf...
            #if calc_para:
            #     res = self.submit(fleur_scf_wc,
            #                  wf_parameters=inputs['wf_parameters'],
            #                  structure=inputs['structure'],
            #                  calc_parameters=calc_para,
            #                  inpgen=inputs['inpgen'],
            #                  fleur=inputs['fleur'],
            #                  label=label_c,
            #                  description=description)
            # else:
            #     res = self.submit(fleur_scf_wc,
            #                  wf_parameters=inputs['wf_parameters'],
            #                  structure=inputs['structure'],
            #                  inpgen=inputs['inpgen'],
            #                  fleur=inputs['fleur'],
            #                  label=label_c,
            #                  description=description)
            #time.sleep(5)
            res = submit(fleur_scf_wc, **inputs)
            self.ctx.labels.append(label)
            calcs[label] = res

        return ToContext(**calcs)


    def get_inputs_scf(self):
        """
        get and 'produce' the inputs for a scf-cycle
        """
        inputs = {}

        # create input from that
        wf_para_dict = self.inputs.wf_parameters.get_dict()
        if wf_para_dict.get('scf_para', None):
            inputs['wf_parameters'] = wf_para_dict.get('scf_para', None)

        #if not inputs['wf_parameters']:
        #    para = {}
        #    para['options'] = wf_para_dict.get('options')            
        #    #para['resources'] = wf_para_dict.get('resources')
        #    #para['walltime_sec'] = wf_para_dict.get('walltime_sec')
        #    #para['queue_name'] = wf_para_dict.get('queue_name')
        #    para['serial'] = wf_para_dict.get('serial')
        #    #para['custom_scheduler_commands'] = wf_para_dict.get('custom_scheduler_commands')
        #    inputs['wf_parameters'] = ParameterData(dict=para)
        if 'options' in self.inputs:
            inputs['options'] = self.inputs.options
        try:
            calc_para = self.inputs.calc_parameters
        except AttributeError:
            calc_para = None

        if calc_para:
            inputs['calc_parameters'] = calc_para
        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur

        return inputs


    def return_results(self):
        """
        return the results of the calculations  (scf workchains) and do a
        Birch-Murnaghan fit for the equation of states
        """
        distancelist = []
        t_energylist = []
        t_energylist_peratom = []
        outnodedict = {}
        natoms = len(self.inputs.structure.sites)
        htr2eV = 27.21138602

        for label in self.ctx.labels:
            calc = self.ctx[label]
            try:
                outnodedict[label] = calc.get_outputs_dict()['output_scf_wc_para']
            except KeyError:
                message = ('One SCF workflow failed, no scf output node: {}. I skip this one.'.format(label))
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue
            
            outpara = calc.get_outputs_dict()['output_scf_wc_para'].get_dict()

            if not outpara.get('successful', False):
                #TODO: maybe do something else here
                # (exclude point and write a warning or so, or error treatment)
                # bzw implement and scf_handler,
                #also if not perfect converged, results might be good
                message = ('One SCF workflow was not successful: {}'.format(label))
                self.ctx.warning.append(message)
                self.ctx.successful = False
                
            t_e = outpara.get('total_energy', float('nan'))
            e_u = outpara.get('total_energy_units', 'eV')
            if e_u == 'Htr' or 'htr':
                t_e = t_e * htr2eV
            dis = outpara.get('distance_charge', float('nan'))
            dis_u = outpara.get('distance_charge_units')
            t_energylist.append(t_e)
            t_energylist_peratom.append(t_e/natoms)
            distancelist.append(dis)
        
        not_ok, an_index = check_eos_energies(t_energylist_peratom)
        
        if not_ok:
            message = ('Abnormality in Total energy list detected. Check '
                       'entr(ies) {}.'.format(an_index))
            hint = ('Consider refining your basis set.')
            self.ctx.info.append(hint)
            self.ctx.warnings.append(message)
            
            
        a = np.array(t_energylist_peratom)
        b = np.array(self.ctx.volume_peratom)

        # all erros should be caught before\
        
        # TODO: different fits
        volume, bulk_modulus, bulk_deriv, residuals = birch_murnaghan_fit(a, b)
        
        volumes = self.ctx.volume
        gs_scale = volume*natoms/self.ctx.org_volume
        if (volume*natoms < volumes[0]) or (volume*natoms > volumes[-1]):
            warn = ('Groundstate volume was not in the scaling range.')         
            hint = ('Consider rerunnning around point {}'.format(gs_scale))
            self.ctx.info.append(hint)
            self.ctx.warnings.append(warn)
            # TODO maybe make it a feature to rerun with centered around the gs.
        
        out = {'workflow_name' : self.__class__.__name__,
               'workflow_version' : self._workflowversion,
               'scaling': self.ctx.scalelist,
               'scaling_gs' : gs_scale,
               'initial_structure': self.inputs.structure.uuid,
               'volume_gs' : volume*natoms,
               'volumes' : volumes,
               'volume_units' : 'A^3',
               'natoms' : natoms,
               'total_energy': t_energylist,
               'total_energy_units' : e_u,
               'structures' : self.ctx.structurs_uuids,
               'calculations' : [],#self.ctx.calcs1,
               'scf_wfs' : [],#self.converge_scf_uuids,
               'distance_charge' : distancelist,
               'distance_charge_units' : dis_u,
               'nsteps' : self.ctx.points,
               'guess' : self.ctx.guess,
               'stepsize' : self.ctx.step,
               #'fitresults' : [a, latticeconstant, c],
               #'fit' : fit_new,
               'residuals' : residuals,
               'bulk_deriv' : bulk_deriv,
               'bulk_modulus' : bulk_modulus * 160.217733,#* echarge * 1.0e21,#GPa
               'bulk_modulus_units' : 'GPa',
               'successful' : self.ctx.successful,
               'info' : self.ctx.info,
               'warnings' : self.ctx.warnings,
               'errors' : self.ctx.errors}
               
        if self.ctx.successful:
            self.report('Done, Equation of states calculation complete')
        else:
            self.report('Done, but something went wrong.... Properly some individual calculation failed or a scf-cylcle did not reach the desired distance.')

        # output must be aiida Data types.
        outnode = ParameterData(dict=out)
        outnodedict['results_node'] = outnode

        # create links between all these nodes...
        outputnode_dict = create_eos_result_node(**outnodedict)
        outputnode = outputnode_dict.get('output_eos_wc_para')
        outputnode.label = 'output_eos_wc_para'
        outputnode.description = 'Contains equation of states results and information of an fleur_eos_wc run.'

        outputstructure = outputnode_dict.get('gs_structure')
        outputstructure.label = 'ouput_eos_wc_structure'
        outputstructure.description = 'Structure with the scaling/volume of the lowest total energy extracted from fleur_eos_wc'

        returndict = {}
        returndict['output_eos_wc_para'] = outputnode
        returndict['output_eos_wc_structure'] = outputstructure

        # create link to workchain node
        for link_name, node in returndict.iteritems():
            self.out(link_name, node)

            
    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain. will initalize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg) # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()
        
        return

if __name__ == "__main__":
    import argparse

    # TODO: this is not usable in the command line, since you cannot provide the nodes in the shell
    # instead you need to use somehting that will load the nodes from pks or uuids
    # checkout what other aiida people do here
    parser = argparse.ArgumentParser(description='Equation of states workchain with Fleur. Does scf-cycles for a structure with different scaleings.')
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
    res = fleur_eos_wc.run(wf_parameters=args.wf_parameters,
                           structure=args.structure,
                           calc_parameters=args.calc_parameters,
                           inpgen=args.inpgen, fleur=args.fleur)


@wf
def create_eos_result_node(**kwargs):
    """
    This is a pseudo wf, to create the rigth graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_eos_wc_para'] = outpara.copy()#clone()
    # copy, because we rather produce the same node twice
    # then have a circle in the database for now...
    outputdict = outpara.get_dict()
    structure = load_node(outputdict.get('initial_structure'))
    gs_scaling = outputdict.get('scaling_gs', 0)
    if gs_scaling:
        gs_structure = rescale(structure, Float(gs_scaling))
        outdict['gs_structure'] = gs_structure

    return outdict


def eos_structures(inp_structure, scalelist):
    """
    Creates many rescalled StrucutureData nodes out of a crystal structure.
    Keeps the provanance in the database.

    :param StructureData, a StructureData node (pk, sor uuid)
    :param scalelist, list of floats, scaling factors for the cell

    :returns: list of New StructureData nodes with rescalled structure, which are linked to input Structure
    """
    structure = is_structure(inp_structure)
    if not structure:
        #TODO: log something (test if it gets here at all)
        return None
    re_structures = []

    for scale in scalelist:
        s = rescale(structure, Float(scale)) # this is a wf
        re_structures.append(s)

    return re_structures

'''
def fit_latticeconstant(scale, eT):
    """
    Extract the lattice constant out of an parabola fit.

    scale : list of scales, or lattice constants
    eT: list of total energies
    """
    # TODO Fit teh real function Mun... not a parabola
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

def parabola(x, a, b, c):
    return a*x**2 + b*x + c
'''

# TODO other fits
def birch_murnaghan_fit(energies, volumes):
    """
    least squares fit of a Birch-Murnaghan equation of state curve. From delta project
    containing in its columns the volumes in A^3/atom and energies in eV/atom
    # The following code is based on the source code of eos.py from the Atomic
    # Simulation Environment (ASE) <https://wiki.fysik.dtu.dk/ase/>.
    :params energies: list (numpy arrays!) of total energies eV/atom
    :params volumes: list (numpy arrays!) of volumes in A^3/atom

    #volume, bulk_modulus, bulk_deriv, residuals = Birch_Murnaghan_fit(data)
    """
    fitdata = np.polyfit(volumes[:]**(-2./3.), energies[:], 3, full=True)
    ssr = fitdata[1]
    sst = np.sum((energies[:] - np.average(energies[:]))**2.)
    #print(fitdata)
    #print(ssr)
    #print(sst)
    residuals0 = ssr/sst
    deriv0 = np.poly1d(fitdata[0])
    deriv1 = np.polyder(deriv0, 1)
    deriv2 = np.polyder(deriv1, 1)
    deriv3 = np.polyder(deriv2, 1)

    volume0 = 0
    x = 0
    for x in np.roots(deriv1):
        if x > 0 and deriv2(x) > 0:
            volume0 = x**(-3./2.)
            break

    if volume0 == 0:
        print('Error: No minimum could be found')
        exit()

    derivV2 = 4./9. * x**5. * deriv2(x)
    derivV3 = (-20./9. * x**(13./2.) * deriv2(x) -
               8./27. * x**(15./2.) * deriv3(x))
    bulk_modulus0 = derivV2 / x**(3./2.)
    #print('bulk modulus 0: {} '.format(bulk_modulus0))
    bulk_deriv0 = -1 - x**(-3./2.) * derivV3 / derivV2

    return volume0, bulk_modulus0, bulk_deriv0, residuals0

def birch_murnaghan(volumes, volume0, bulk_modulus0, bulk_deriv0):
    """
    This evaluates the Birch Murnaghan equation of states
    """
    PV = []
    EV = []
    v0 = volume0
    bm = bulk_modulus0
    dbm = bulk_deriv0

    for vol in volumes:
        pv_val = 3 * bm/2. * ((v0/vol)**(7/3.) - (v0/vol)**(5/3.)) * (1 + 3/4. * (dbm -4) * ((v0/vol)**(2/3.)-1))
        PV.append(pv_val)
        ev_val = 9 * bm*v0/16. * ((dbm*(v0/vol)**(2/3.) - 1)**(3) * ((v0/vol)**(2/3.)-1)**2 * (6-4*(v0/vol)**(2/3.)))
        EV.append(ev_val)
    return EV, PV
