#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the worklfow 'corehole' using the Fleur code, which calculates Binding
energies and corelevel shifts with different methods.
'divide and conquer'
"""

__copyright__ = (u"Copyright (c), 2016, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.27"
__contributors__ = "Jens Broeder"

# TODO maybe also calculate the reference structure to check on the supercell calculation

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
    
#import os.path
import re
from aiida.orm import Code, DataFactory, load_node
from aiida.orm.data.base import Int
from aiida.work.workchain import WorkChain
from aiida.work.workchain import if_

#from aiida.work.run import submit
from aiida.work.run import async as asy
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry

from aiida_fleur.calculation.fleur import FleurCalculation
#from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.StructureData_util import supercell
from aiida_fleur_ad.util.create_corehole import create_corehole_para#, create_corehole_fleurinp
from aiida_fleur_ad.util.extract_corelevels import extract_corelevels
from aiida_fleur.tools.StructureData_util import break_symmetry
from aiida_fleur.workflows.scf import fleur_scf_wc
from aiida_fleur.tools.StructureData_util import find_equi_atoms
from aiida_fleur_ad.util.element_econfig_list import get_econfig #,get_coreconfig, rek_econ

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleur.fleurinp')
#FleurProcess = FleurCalculation.process()


class fleur_corehole_wc(WorkChain):
    """
    Turn key solution for a corehole calculation with the FLEUR code.
    Has different protocolls for different core-hole types (Full-valence, 
    partial valence, charged).
    
    Calculates supercells. From the total energy differences binding energies
    for certain corelevels are extracted.
    
    Documentation: 
    See help for details.
    """
    
    _workflowversion = "0.1.0"
    
    def __init__(self, *args, **kwargs):
        super(fleur_corehole_wc, self).__init__(*args, **kwargs)
    
    
    @classmethod
    def define(cls, spec):
        super(fleur_corehole_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
            default=ParameterData(dict={
                'method' : 'full valence', # what method to use, default for valence to highest open shel
                'atoms' : ['all'],           # coreholes on what atoms, positions or index for list, or element ['Be', (0.0, 0.5, 0.334), 3]
                'corelevel': ['all'],        # coreholes on which corelevels [ 'Be1s', 'W4f', 'Oall'...]
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
            cls.create_coreholes,
            cls.run_ref_scf,              # calculate the reference supercell
            cls.check_scf,            
            cls.run_scfs,
            cls.check_scf,
            #cls.collect_results,
            cls.return_results
        )
        #spec.dynamic_output()


    def check_input(self):
        '''
        init all context parameters, variables.
        Do some input checks. Further input checks are done in further workflow steps
        '''
        # TODO: document parameters
        self.report("started fleur_corehole_wc version {}"
                    "Workchain node identifiers: {}"
              "".format(self._workflowversion, ProcessRegistry().current_calc_node))

        ### init ctx ###
        
        # internal variables
        self.ctx.calcs_torun = []
        self.ctx.calcs_ref_torun = []
        self.ctx.labels = []
        self.ctx.calcs_res = []
        #self.ctx.get_res = True
        
        # input variables
        inputs = self.inputs
        self.ctx.supercell_size = (2, 1, 1) # 2x2x2 or smaller?
        if 'calc_parameters' in inputs:
            self.ctx.ref_para = inputs.get('calc_parameters')
        else:
            self.ctx.ref_para = None

        
        wf_dict = inputs.wf_parameters.get_dict()
        self.ctx.method = wf_dict.get('method', 'full valence')
        self.ctx.joblimit = wf_dict.get('joblimit')
        self.ctx.serial = wf_dict.get('serial')
        self.ctx.same_para = wf_dict.get('same_para')
        self.ctx.scf_para = wf_dict.get('scf_para', {})
        self.ctx.resources = wf_dict.get('resources')
        self.ctx.walltime_sec = wf_dict.get('walltime_sec')
        self.ctx.queue = wf_dict.get('queue_name')
        self.ctx.be_to_calc = wf_dict.get('corelevel')
        self.ctx.atoms_to_calc = wf_dict.get('atoms')
        self.ctx.base_structure = inputs.get('structure') # ggf get from fleurinp

        #self.ctx.relax = wf_dict.get('relax', default.get('relax'))
        #self.ctx.relax_mode = wf_dict.get('relax_mode', default.get('relax_mode'))
        #self.ctx.relax_para = wf_dict.get('relax_para', default.get('dos_para'))       
        
        # return variables        
        self.ctx.bindingenergies = []
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.hints = []
        self.ctx.cl_energies = []
        self.ctx.all_CLS = [] 
        self.ctx.ref_cl_energies = []
        self.ctx.fermi_energies = []
        self.ctx.bandgaps = []
        self.ctx.ref_fermi_energies = []
        self.ctx.ref_bandgaps = []
        self.ctx.atomtypes = []
        self.ctx.ref_atomtypes = []
        self.ctx.total_energies = []
        self.ctx.ref_total_energies = []
        ### input check ###


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
        #print('in create_supercell')
        supercell_base = self.ctx.supercell_size
        supercell_s = supercell(
                        self.ctx.base_structure,
                        Int(supercell_base[0]),
                        Int(supercell_base[1]),
                        Int(supercell_base[2]))
        self.ctx.ref_supercell = supercell_s
        calc_para = self.ctx.ref_para
        new_calc = (supercell_s, calc_para)
        self.ctx.calcs_ref_torun.append(new_calc)

        return

    def create_coreholes(self):
        """
        Check the input for the corelevel specification,
        create structure and parameter nodes with all the need coreholes.
        create the wf_parameter nodes for the scfs. Add all calculations to 
        scfs_to_run.
        
        Layout:
        # Check what coreholes should be created.
        # said in the input, look in the original cell
        # These positions are the same for the supercell. 
        # break the symmetry for the supercells. (make the corehole atoms its own atom type)
        # create a new species and a corehole for this atom group.
        # move all the atoms in the cell that impurity is in 0.0, 0.0, 0.0
        # use the fleurinp_change feature of scf to create the corehole after inpgen gen in the scf        
        # start the scf with the last charge density of the ref calc? so far no, might not make sense      
        
        """
        self.report('INFO: In create_coreholes of fleur_corehole_wc. '
                    'Preparing everything for calcualtion launches.')

        ########### init variables ##############
        
        base_struc = self.ctx.base_structure # one unit cell (given cell)
        base_atoms_sites = base_struc.sites  # list of AiiDA Site types of cell
        base_kinds = base_struc.kinds        # list of AiiDA Kind types of cell
        base_supercell = self.ctx.ref_supercell # supercell of base cell
        base_k_symbols = {}                    #map kind names to elements 
        
        for kind in base_kinds:
            base_k_symbols[kind.name] = kind.symbol
        
        # we have to find the atoms we want a corelevel on and make them a new kind,
        # also we have to figure out what electron config to set
        atoms_toc = self.ctx.atoms_to_calc #['Be', (0.0, 0.5, 0.334), 3, 'all']
        corelevels_toc = self.ctx.be_to_calc # [ 'Be 1s', 'W_4f', 'O all', 'W-3d'...]
        coreholes_atoms = []  # list of aiida sites
        corehole_to_create = []
        valid_elements = list(base_struc.get_composition().keys())# get elements in structure
        
        # get the symmetry equivivalent atoms by ase
        # equi_info_symbol = [['W', 1,2,3,8], ['Be', 4,5,6,7,9] ...], n_equi_info_symbol= {'Be' : number, ...}
        equi_info_symbol, n_equi_info_symbol = find_equi_atoms(base_struc)  
        print(atoms_toc)
        # 1. Find out what atoms to do coreholes on
        for atom_info in atoms_toc:
            print(atom_info, type(atom_info))
            if isinstance(atom_info, basestring):
                if atom_info == 'all':
                    # add all symmetry equivivalent atoms of structure to create coreholes
                    #coreholes_atoms = base_atoms_sites
                    coreholes_atoms = []
                    for equi_group in equi_info_symbol:
                        # only calculate first element of group, 0 entry is an element string
                        # and there is always a first atom element
                        site_index = equi_group[1][0]
                        coreholes_atoms.append(base_atoms_sites[site_index])
                elif 'all' in atom_info:
                    elem = atom_info.split('all')[0]
                    # check what element we are taking about
                    if elem in valid_elements:
                        for equi_group in equi_info_symbol:
                            # only calculate first element of group, 0 entry is an element string
                            # and there is always a first atom element
                            if equi_group[0] == elem:                         
                                site_index = equi_group[1][0]
                                coreholes_atoms.append(base_atoms_sites[site_index])                        
                else:
                    # check if a valid element or some garbage
                    pass
            elif isinstance(atom_info, tuple): # coordinates
                if len(atom_info) == 3:
                    for site in base_atoms_sites:
                        if site.position == atom_info:#ggf give a threshold...
                            coreholes_atoms.append(site)
                else:
                    # wrong tuple length this is not a  position
                    print('strange position/coordinates given: {}'.format(atom_info))
                    #
            elif isinstance(atom_info, int): # index for sites
                to_append = None                
                try:
                    to_append = base_atoms_sites[atom_info]
                except IndexError:
                    print("The index/integer: {} specified in 'atoms' key is not valid."
                          "There are only {} atom sites in your provided structure."
                          "".format(atom_info, len(base_atoms_sites)))
                    to_append = None
                if to_append:         
                    coreholes_atoms.append(to_append)
            else:
                print("input: {} of 'atoms' not recongized".format(atom_info))
                
        # remove doubles in coreholes_atoms?
        #a = s.sites
        #a[0] == a[0]
        
        # 2. now check what type of corelevel shall we create on those atoms
        for corel in corelevels_toc:
            if isinstance(corel, basestring):
                # split string (Be1s) s.replace(';',' ')... could get rid of re 
                elm_cl = re.split("[, ;:-]", corel)
                if len(elm_cl) != 2:                
                        pass
                        # something went wrong, wrong input
                        continue                
                else:
                    # we assume for now ['Element', 'corelevel'] i.e ['Be', '1s']                    
                    if elm_cl[0] in valid_elements:
                        # get corelevel econfig of element
                        valid_coreconfig = get_econfig(elm_cl[0], full=True)
                        if 'all' == elm_cl[1]:
                            # add all corelevels to calculate
                            pass
                        elif elm_cl in valid_coreconfig: # check if corelevel in valid coreconfig
                            #add corelevel to calculate.
                            # get rel core level (for 4f 5/2, 7/2)
                            pass
                        else:
                            pass
                            # corelevel provided wrong, not understood, warning
                    else:
                        pass
                        #element or string provieded not in structure,
                        # what about upper and lower caps
 
        method = self.ctx.method       
        if method == 'full valence':
            pass
        elif method == 'full charge':
            pass
        elif method == 'half_valence':
            pass
        elif method == 'fractional':
            pass
        
        #output of about                
        #list of sites [site_bla, ..]
        # dict_corelevel['W' : {corelevel: ['3d','4f 7/2', '4f 3/2'], econfig: [config], fleur_changes : []}]
        dict_corelevel = {'Be' : {'corelevel' : ['1s'], 'econfig' : ['1s2 | 2s2']}}
        
        for site in coreholes_atoms:
            selem = base_k_symbols[site.kind_name]
            cl_dict = dict_corelevel.get(selem, None)
            if cl_dict:
                # what coreholes need to be created for that element
                for econfig in cl_dict.get('econfig', []):
                    kind = site.kind_name + '1' # # TODO do rigth, this might lead to errors
                    corehole = {'site' : site, 'econfig' : econfig, 'kindname' : kind}
                    corehole_to_create.append(corehole)
        
        # lesson go over site position to get atom in supercell
        # set econfig for this atom in the supercell
        # (default kind name = element + id) use this for paramter settings

        # fill calcs_torun with (sturcutre, parameter, wf_para)
        #corehole_to_create = [{'site' : sites[8], 'kindname' : 'W1', 'econfig': "[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2"}]
        calcs = []
        for corehole in corehole_to_create:
            site = corehole['site']
            pos = site.position
            para =  self.ctx.ref_para
            # make sure to provide a parameter data node....!
            # otherwise create_corehole para won't work
            # break symmetry for the corehole atom in supercell

            new_struc, new_para = break_symmetry(base_supercell, atoms=[], site=[], pos=[pos], parameterData=para)
            # get kind name from new_para?
            
            # move unit cell that impurity is in 0,0,0
            para = create_corehole_para(new_struc, corehole['kindname'], corehole['econfig'], parameterData=new_para)
            
            # create_wf para or write in last line what should be in 'fleur_change'            
            #  for scf, which with the changes in the inp.xml needed

            calcs.append((new_struc, para))
        self.ctx.calcs_torun = calcs
        
                


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
        #print(wf_parameter)
        wf_parameter['serial'] = self.ctx.serial
        wf_parameter['queue_name'] = self.ctx.queue
        wf_parameters =  ParameterData(dict=wf_parameter)
        #res_all = []
        calcs = {}

        i = 0
        for node in self.ctx.calcs_ref_torun: # usually just 1, but we leave the default.
            #print node
            i = i+1
            if isinstance(node, StructureData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, tuple):
                if isinstance(node[0], StructureData) and isinstance(node[1], ParameterData):
                    res = asy(fleur_scf_wc, wf_parameters=wf_parameters, calc_parameters=node[1], structure=node[0], 
                                inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
                else:
                    self.report(' WARNING: a tuple in run_ref_scf which I do not reconise: {}'.format(node))
            else:
                self.report('WARNING: something in run_ref_scf which I do not reconise: {}'.format(node))
                continue
            
            #calc_node = res['output_scf_wc_para'].get_inputs()[0] # if run is used, otherwise use labels            
            label = str('calc_ref{}'.format(i))
            self.ctx.labels.append(label)
            calcs[label] = res
            #res_all.append(res)
            #self.ctx.calcs_res.append(res)
            
        self.ctx.calcs_ref_torun = []
        return ToContext(**calcs)#  this is a blocking return

    def check_scf(self):
        """
        Check if ref scf was successful, or something needs to be dealt with.
        If unsuccesful abort, because makes no sense to continue.
        """
        #so far not implemented
        pass

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
        #res_all = []
        calcs = {}
        # now in parallel
        #print self.ctx.ref_calcs_torun
        i = 0 #
        for node in self.ctx.calcs_torun:
            #print node
            i = i+1
            if isinstance(node, StructureData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = asy(fleur_scf_wc, wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, tuple):
                if isinstance(node[0], StructureData) and isinstance(node[1], ParameterData):                
                    res = asy(fleur_scf_wc, wf_parameters=wf_parameters, calc_parameters=node[1], structure=node[0], 
                                inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            else:
                print('something in run_scfs which I do not recognize: {}'.format(node))
                continue
            label = str('calc{}'.format(i))
            #print(label)
            #calc_node = res['output_scf_wc_para'].get_inputs()[0] # if run is used, otherwise use labels
            self.ctx.labels.append(label)
            calcs[label] = res
            #res_all.append(res)
            #print res  
            #self.ctx.calcs_res.append(res)
            #self.ctx.calcs_torun.remove(node)
            #print res    
        self.ctx.calcs_torun = []
        return ToContext(**calcs)


    def collect_results(self):
        """
        Collect results from certain calculation, check if everything is fine, 
        calculate the wanted quantities. currently all energies are in hartree (as provided by Fleur)
        """
        
        # TODO: what about partial collection?
        message=('INFO: Collecting results of fleur_corehole_wc workflow')
        self.report(message)

        all_CLS = {}
        ref_calcs = []
        ref_cl_energies = {}
        cl_energies = {}
        bindingenergies = [] # atomtype, binding eneergy

        calcs = []
        # get results from calc/scf
        #calcs = self.ctx.calcs_res
        for i, label in enumerate(self.ctx.labels):
            calc = self.ctx[label]
            if i==0:
                ref_calcs.append(calc)
            else:
                calcs.append(calc)

        fermi_energies, bandgaps, atomtypes, all_corelevel, total_energies = extract_results_corehole(calcs)
        ref_fermi_energies, ref_bandgaps, ref_atomtypes, ref_all_corelevel, ref_total_energies = extract_results_corehole(ref_calcs)


        # now calculate binding energies of the coreholes.
        # Differences of total energies
        for number, energy in total_energies:
            bde = energy - ref_total_energies[0]
            bindingenergies.append(bde)
        # make a return dict
        self.ctx.cl_energies = cl_energies
        self.ctx.all_CLS = all_CLS 
        self.ctx.ref_cl_energies = ref_cl_energies
        self.ctx.fermi_energies = fermi_energies
        self.ctx.bandgaps = bandgaps
        self.ctx.ref_fermi_energies = ref_fermi_energies
        self.ctx.ref_bandgaps = ref_bandgaps
        self.ctx.atomtypes = atomtypes
        self.ctx.ref_atomtypes = ref_atomtypes
        self.ctx.total_energies = total_energies
        self.ctx.ref_total_energies = ref_total_energies

        
        return
        
    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more output, info here
        # TODO: Maybe all variables should come from the context, therefore they
        # they will be proper initialiezed and you can call return_results, on a controlled
        # abort of the wc. with all output nodes produced....
        
        print('coreholes were calculated bla bla')
        # call one routine, that will set all variables in the ctx
        #cl, cls, ref_cl, efermi, gap, ref_efermi, ref_gap, at, at_ref, te, te_ref =  self.collect_results()    
        # check if this should be called
        self.collect_results()
        
        outputnode_dict ={}
        
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['total_energy_ref'] = self.ctx.ref_total_energies
        outputnode_dict['total_energy_ref_units'] = 'eV'
        outputnode_dict['total_energy_all'] = self.ctx.total_energies
        outputnode_dict['total_energy_all_units'] = 'eV'
        outputnode_dict['binding_energy'] = self.ctx.bindingenergies
        outputnode_dict['binding_energy_units'] = 'eV'
        outputnode_dict['binding_energy_convention'] = 'negativ'
        outputnode_dict['corehole_type'] = self.ctx.method
        outputnode_dict['coreholes_calculated'] = '' # on what atom what level basicly description of the other lists
        outputnode_dict['coreholes_calculated_details'] = '' # the dict internally used
        #outputnode_dict['corelevel_energies'] = cl
        #outputnode_dict['reference_corelevel_energies'] = ref_cl
        outputnode_dict['fermi_energy'] = self.ctx.fermi_energies
        outputnode_dict['fermi_energy_unit'] = 'eV'
        outputnode_dict['coresetup'] = []#cls
        outputnode_dict['reference_coresetup'] = []#cls
        outputnode_dict['bandgap'] = self.ctx.bandgaps
        outputnode_dict['bandgap_unit'] = ''
        outputnode_dict['reference_bandgaps'] = self.ctx.ref_bandgaps
        outputnode_dict['atomtypes'] = self.ctx.atomtypes
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors
        outputnode_dict['hints'] = self.ctx.hints
        
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['output_corehole_wc_para'] = outputnode
        for k, v in outdict.iteritems():
            self.out(k, v)
        msg=('INFO: fleur_corehole_wc workflow Done')
        self.report(msg)


def extract_results_corehole(calcs):
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


