#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the worklfow 'corehole' using the Fleur code, which calculates Binding
energies and corelevel shifts with different methods.
'divide and conquer'
"""

# TODO maybe also calculate the reference structure to check on the supercell calculation
from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
    
import os.path
from aiida.orm import Code, DataFactory, load_node
from aiida.orm.data.base import Int
from aiida.work.workchain import WorkChain
from aiida.work.workchain import while_, if_

from aiida.work.run import submit
from aiida.work.run import async as asy
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry

from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.StructureData_util import supercell
from aiida_fleur_ad.util.create_corehole import create_corehole
from aiida_fleur_ad.util.extract_corelevels import extract_corelevels
from aiida_fleur.workflows.scf import fleur_scf_wc

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleur.fleurinp')
#FleurProcess = FleurCalculation.process()


class fleur_corehole_wc(WorkChain):
    """
    Turn key solution for a corehole calculation with FLEUR
    

    """
    
    _workflowversion = "0.0.1"
    
    @classmethod
    def define(cls, spec):
        super(fleur_corehole_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
            default=ParameterData(dict={
                'method' : 'full valence', # what method to use
                'atoms' : 'all',           # coreholes on what atoms, positions or index for list, or element
                'corelevel': 'all',        # coreholes on which corelevels [ '1s', '4f', ...]
                'para_group' : None,       # use parameter nodes from a parameter group
                #'references' : 'calculate',# at some point aiida will have fast forwarding
                #'relax' : False,          # relax the unit cell first?
                #'relax_mode': 'Fleur',    # what releaxation do you want
                #'relax_para' : 'default', # parameter dict for the relaxation
                'scf_para' : 'default',    # wf parameter dict for the scfs
                'same_para' : True,        # enforce the same atom parameter/cutoffs on the corehole calc and ref
                'resources' : {"num_machines": 1},# resources per job
                'walltime_sec' : 10*30,    # walltime per job
                'queue_name' : None,       # what queue to submit to
                'serial' : True,           # run fleur in serial, or parallel?
                'job_limit' : 100          # enforce the workflow not to spawn more scfs wcs then this number(which is roughly the number of fleur jobs)
                }))
        spec.input("fleurinp", valid_type=FleurinpData, required=False)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("inpgen", valid_type=Code, required=True)
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)

        spec.outline(
            cls.check_input,              # first check if input is consistent
            #if_(cls.relaxation_needed)(  # ggf relax the given cell
            #    cls.relax),
            if_(cls.supercell_needed)(    # create a supercell from the given/relaxed cell
                cls.create_supercell
                    ),
            cls.run_ref_scf,              # calculate the reference supercell
            cls.check_scf,
            cls.create_coreholes,
            cls.run_scfs,
            #cls.collect_results,
            cls.return_results
        )
        #spec.dynamic_output()


    def check_input(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ###
        self.report("started fleur_corehole_wc version {}"
                    "Workchain node identifiers: {}"
              "".format(self._workflowversion, ProcessRegistry().current_calc_node))

        '''
        #ususal fleur stuff check
        if fleurinp.get structure
        self.ctx.inputs.base_structure
        wf_para = self.inputs.wf_parameters
        corelevel_to_calc = wf_para.get('corelevel', None)
        if not corelevel_to_calc:
            errormsg = 'You need to specify unter 'corelevel' in the wf_para node on what corelevel you want to have a corehole calculated. (Default is 'all')'
            self.abort_nowait(errormsg)

        '''
        ### init ctx ###

        self.ctx.calcs_torun = []
        
        inputs = self.inputs
        self.ctx.base_structure = inputs.get('structure') # ggf get from fleurinp
        self.ctx.supercell_size = (2, 2, 2) # 2x2x2
        self.ctx.calcs_to_run = []
        if 'calc_parameters' in inputs:
            self.ctx.ref_para = inputs.get('calc_parameters')
        else:
            self.ctx.ref_para = None


        wf_dict = self.inputs.wf_parameters.get_dict()

        self.ctx.joblimit = wf_dict.get('joblimit')
        self.ctx.serial = wf_dict.get('serial')
        self.ctx.same_para = wf_dict.get('same_para')
        self.ctx.scf_para = wf_dict.get('scf_para', {})
        
        #self.ctx.relax = wf_dict.get('relax', default.get('relax'))
        #self.ctx.relax_mode = wf_dict.get('relax_mode', default.get('relax_mode'))
        #self.ctx.relax_para = wf_dict.get('relax_para', default.get('dos_para'))
        self.ctx.resources = wf_dict.get('resources')
        self.ctx.walltime_sec = wf_dict.get('walltime_sec')
        self.ctx.queue = wf_dict.get('queue_name')




    def supercell_needed(self):
        """
        check if a supercell is needed and what size
        """
        #think about a rule here to apply 2x2x2 should be enough for nearly everything.
        # but for larger unit cells smaller onces might be ok.
        # So far we just go with what the user has given
        # Is there a way to tell if a supercell was already given as base?
        # Do we want to detect it with some spglib methods?
        self.ctx.supercell_boal = True
        needed = self.ctx.supercell_boal

        return needed


    def create_supercell(self):
        """
        create the needed supercell
        """
        print('in create_supercell')
        supercell_base = self.ctx.supercell_size
        supercell_s = supercell(
                        self.ctx.base_structure,
                        Int(supercell_base[0]),
                        Int(supercell_base[1]),
                        Int(supercell_base[2]))
        self.ctx.ref_supercell = supercell_s
        print(self.ctx.base_structure)
        print(self.ctx.base_structure.sites)
        print(supercell_s)
        print(supercell_s.sites)
        calc_para = self.ctx.ref_para
        new_calc = (supercell_s, calc_para)
        self.ctx.calcs_torun.append(new_calc)

        return

    def run_ref_scf(self):
        """
        Run a scf for the reference super cell
        """
        self.report('INFO: In run_ref_scf fleur_corehole_wc')
        #TODO if submiting of workdlows work, use that.
        #async here because is closer to submit
        
        para = self.ctx.scf_para
        if para == 'default': 
            wf_parameter = {}
        else:
            wf_parameter = para
        print(wf_parameter)
        wf_parameter['serial'] = self.ctx.serial
        wf_parameter['queue_name'] = self.ctx.queue
        wf_parameters =  ParameterData(dict=wf_parameter)
        res_all = []
        calcs = {}
        # now in parallel
        #print self.ctx.ref_calcs_torun
        i = 0
        for node in self.ctx.calcs_torun:
            #print node
            i = i+1
            if isinstance(node, StructureData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, (StructureData, ParameterData)):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, calc_parameters=node(1), structure=node(0), 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            else:
                print('something in run_ref_scf which I do not reconise: {}'.format(node))
                continue
            label = str('calc_ref{}'.format(i))
            #print(label)
            #calc_node = res['output_scf_wc_para'].get_inputs()[0] # if run is used, otherwise use labels
            self.ctx.labels.append(label)
            calcs[label] = res
            res_all.append(res)
            #print res  
            self.ctx.calcs_res.append(res)
            #self.ctx.calcs_torun.remove(node)
            #print res    
        self.ctx.calcs_torun = []
        return ToContext(**calcs)

    def check_scf(self):
        """
        Check if ref scf was successful, or something needs to be dealt with
        """
        #so far not implemented
        pass

    def create_coreholes(self):
        """
        create structurs with all the need coreholes
        """
        print('in create_coreholes fleur_corehole_wc')

        #Check what coreholes should be created.
        # said in the input
        # look in the original cell
        # are the positions the same for the supercell?
        # find these atoms in the supercell
        # break the symmetry?
        # use the fleurinpdate from the supercell calculation
        # create a new species and a corehole for this atom group.
        # start the scf with the last charge density of the ref calc?
        # only possible if symmetry allready the same.


    def relaxation_needed(self):
        """
        If the structures should be relaxed, check if their Forces are below a certain 
        threshold, otherwise throw them in the relaxation wf.
        """
        print('In relaxation fleur_corehole_wc')
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
        print('In relax fleur_corehole_wc workflow')
        #for calc in self.ctx.dos_to_calc:
        #    pass
        #    # TODO run relax workflow


    def run_scfs(self):
        """
        Run a scf for the all corehole calculations in parallel super cell
        """
        self.report('INFO: In run_scfs fleur_corehole_wc')
        #TODO if submiting of workdlows work, use that.
        #async here because is closer to submit
        
        para = self.ctx.scf_para
        if para == 'default': 
            wf_parameter = {}
        else:
            wf_parameter = para
        wf_parameter['serial'] = self.ctx.serial
        wf_parameter['queue_name'] = self.ctx.queue
        wf_parameters =  ParameterData(dict=wf_parameter)
        res_all = []
        calcs = {}
        # now in parallel
        #print self.ctx.ref_calcs_torun
        i = 1 # 0 is reference
        for node in self.ctx.calcs_torun:
            #print node
            i = i+1
            if isinstance(node, StructureData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, (StructureData, ParameterData)):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, calc_parameters=node(1), structure=node(0), 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            else:
                print('something in run_ref_scf which I do not reconise: {}'.format(node))
                continue
            label = str('calc_ref{}'.format(i))
            #print(label)
            #calc_node = res['output_scf_wc_para'].get_inputs()[0] # if run is used, otherwise use labels
            self.ctx.labels.append(label)
            calcs[label] = res
            res_all.append(res)
            #print res  
            self.ctx.calcs_res.append(res)
            #self.ctx.calcs_torun.remove(node)
            #print res    
        self.ctx.calcs_torun = []
        return ToContext(**calcs)


    def collect_results(self):
        """
        Collect results from certain calculation, check if everything is fine, 
        calculate the wanted quantities. currently all energies are in hartree (as provided by Fleur)
        """
        message=('INFO: Collecting results of fleur_corehole_wc workflow')
        self.report(message)

        all_CLS = {}
        ref_calcs = []
        ref_cl_energies = {}
        cl_energies = {}

        calcs = []
        # get results from calc/scf
        calcs = self.ctx.calcs_res
        for i, label in enumerate(self.ctx.labels):
            calc = self.ctx[label]
            if i==0:
                ref_calcs.append(calc)
            else:
                calcs.append(calc)

        fermi_energies, bandgaps, atomtypes, all_corelevel, total_energies = extract_results(calcs)
        ref_fermi_energies, ref_bandgaps, ref_atomtypes, ref_all_corelevel, ref_total_energies = extract_results(ref_calcs)


        # now calculate binding energies of the coreholes.
        # Differences of total energies
        # make a return dict
        return cl_energies, all_CLS, ref_cl_energies, fermi_energies, bandgaps, ref_fermi_energies, ref_bandgaps, atomtypes, ref_atomtypes, total_energies, ref_total_energies

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more output, info here
        
        print('coreholes were calculated bla bla')
        cl, cls, ref_cl, efermi, gap, ref_efermi, ref_gap, at, at_ref, te, te_ref =  self.collect_results()
        
        outputnode_dict ={}
        
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['total_energy_ref'] = te_ref
        outputnode_dict['total_energy_ref_units'] = 'eV'
        outputnode_dict['total_energy_all'] = te
        outputnode_dict['total_energy_all_units'] = 'eV'
        outputnode_dict['binding_energy'] = []
        outputnode_dict['binding_energy_units'] = 'eV'
        outputnode_dict['binding_energy_convention'] = 'negativ'
        outputnode_dict['corehole_type'] = ''
        outputnode_dict['coreholes_calculated'] = '' # on what atom what level basicly description of the other lists

        #outputnode_dict['corelevel_energies'] = cl
        #outputnode_dict['reference_corelevel_energies'] = ref_cl
        outputnode_dict['fermi_energy'] = efermi
        outputnode_dict['fermi_energy_unit'] = ''

        outputnode_dict['coresetup'] = []#cls
        outputnode_dict['reference_coresetup'] = []#cls
        outputnode_dict['bandgap'] = gap
        outputnode_dict['bandgap_unit'] = ''

        outputnode_dict['reference_bandgaps'] = ref_gap
        outputnode_dict['atomtypes'] = at


        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['output_corehole_wc_para'] = outputnode
        #print outdict
        for k, v in outdict.iteritems():
            self.out(k, v)
        msg=('INFO: fleur_corehole_wc workflow Done')
        self.report(msg)


def extract_results(calcs):
    """
    Collect results from certain calculation, check if everything is fine, 
    calculate the wanted quantities.
    
    params: calcs : list of scf workchains nodes
    """
    # TODO maybe import from somewhere move to common wf

    calc_uuids = []
    for calc in calcs:
        #print(calc)
        calc_uuids.append(calc.get_outputs_dict()['output_scf_wc_para'].get_dict()['last_calc_uuid'])
        #calc_uuids.append(calc['output_scf_wc_para'].get_dict()['last_calc_uuid'])
    #print(calc_uuids)
    
    all_corelevels = {}
    fermi_energies = {}
    bandgaps = {}
    all_atomtypes = {}
    all_total_energies = {}
    # more structures way: divide into this calc and reference calcs.
    # currently the order in calcs is given, but this might change if you submit
    # check if calculation pks belong to successful fleur calculations
    for i,uuid in enumerate(calc_uuids):
        calc = load_node(uuid)
        if (not isinstance(calc, FleurCalculation)):
            #raise ValueError("Calculation with pk {} must be a FleurCalculation".format(pk))
            # log and continue
            continue
        if calc.get_state() != 'FINISHED':
            # log and continue
            continue
            #raise ValueError("Calculation with pk {} must be in state FINISHED".format(pk))
        
        # get out.xml file of calculation
        outxml = calc.out.retrieved.folder.get_abs_path('path/out.xml')
        #print outxml
        corelevels, atomtypes = extract_corelevels(outxml)
        #all_corelevels.append(core)
        #print('corelevels: {}'.format(corelevels))
        #print('atomtypes: {}'.format(atomtypes))
        #for i in range(0,len(corelevels[0][0]['corestates'])):
        #    print corelevels[0][0]['corestates'][i]['energy']
            
        #TODO how to store?
        efermi = calc.res.fermi_energy
        #print efermi
        bandgap = calc.res.bandgap
        total_energy = calc.res.total_energy
        total_energy_units = calc.res.total_energy_units
        
        # TODO: maybe different, because it is prob know from before
        #fleurinp = calc.inp.fleurinpdata
        #structure = fleurinp.get_structuredata(fleurinp)
        #compound = structure.get_formula()
        #print compound
        number = '{}'.format(i)
        fermi_energies[number] = efermi
        bandgaps[number] = bandgap
        all_atomtypes[number] = atomtypes
        all_corelevels[number] = corelevels
        all_total_energies[number] = total_energy

    return fermi_energies, bandgaps, all_atomtypes, all_corelevels, all_total_energies


