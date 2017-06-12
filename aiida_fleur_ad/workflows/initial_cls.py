#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is the worklfow 'corelevel' using the Fleur code, which calculates Binding
energies and corelevel shifts with different methods.
'divide and conquer'
"""
#TODO parsing of eigenvalues of LOS!

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
    
#import os.path
from aiida.orm import Code, DataFactory, CalculationFactory, load_node
from aiida.work.workchain import WorkChain
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process_registry import ProcessRegistry

from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida.work.workchain import  if_ #while_,
from aiida_fleur_ad.util.extract_corelevels import extract_corelevels

StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')
FleurinpData = DataFactory('fleur.fleurinp')
FleurProcess = FleurCalculation.process()
FleurCalc = CalculationFactory('fleur.fleur')

htr_to_eV = 1

class fleur_initial_cls_wc(WorkChain):
    '''
    Turn key solution for the calculation of core level shift and Binding energies
    
    '''
    # wf_Parameters: ParameterData, 
    '''
    'method' : ['initial', 'full_valence ch', 'half_valence_ch', 'ch', ...]
    'Bes' : [W4f, Be1s]
    'CLS' : [W4f, Be1s]
    'atoms' : ['all', 'postions' : []]
    #'references' : ['calculate', and use # calculate : 'all' , or 'calculate' : ['W', 'Be']
    'references' : { 'W': [calc/ouputnode or  fleurinp, or structure data or structure data + Parameter  ], 'Be' : }
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
    _default_wf_para = {#'references' : {'calculate' : 'all'},
                        'structure_ref' : {},
                        'relax' : True,
                        'relax_mode': 'QE Fleur',
                        'relax_para' : 'default',
                        'scf_para' : 'default',
                        'same_para' : True,
                        'resources' : {"num_machines": 1},
                        'walltime_sec' : 10*30,
                        'queue_name' : None,
                        'serial' : True}    
    
    '''
    def get_defaut_wf_para(self):
        return self._default_wf_para
     '''     
    @classmethod
    def define(cls, spec):
        super(fleur_initial_cls_wc, cls).define(spec)
        spec.input("wf_parameters", valid_type=ParameterData, required=False,
                   default=ParameterData(dict={ 
                        #'references' : {'calculate' : 'all'}, 
                        'references' : {},
                        'relax' : True,
                        'relax_mode': 'QE Fleur',
                        'relax_para' : 'default',
                        'scf_para' : 'default',
                        'same_para' : True,
                        'resources' : {"num_machines": 1},
                        'walltime_sec' : 10*60,
                        'queue_name' : None,
                        'serial' : True}))#TODO_default_wf_para out of here#
        spec.input("fleurinp", valid_type=FleurinpData, required=False)
        spec.input("fleur", valid_type=Code, required=True)
        spec.input("inpgen", valid_type=Code, required=False)        
        spec.input("structure", valid_type=StructureData, required=False)
        spec.input("calc_parameters", valid_type=ParameterData, required=False)
        spec.outline(
            cls.check_input,
            cls.get_refernces,
            cls.run_fleur_scfs,
            if_(cls.relaxation_needed)(
                cls.relax),
            cls.find_parameters,
            cls.run_scfs_ref,
            cls.return_results
        )
        #spec.dynamic_output()


    def check_input(self):
        """
        Init same context and check what input is given if it makes sence
        """
        ### input check ### ? or done automaticly, how optional?
        print('Started inital_state_CLS workflow version {}'.format(self._workflowversion))
        print("Workchain node identifiers: {}"
              "".format(ProcessRegistry().current_calc_node))
        
        # init
        self.ctx.last_calc = None
        self.ctx.eximated_jobs = 0
        self.ctx.run_jobs = 0
        self.ctx.calcs_res = []
        self.ctx.calcs_torun = []
        self.ctx.ref_calcs_torun = []
        self.ctx.ref_calcs_res = []
        self.ctx.struc_to_relax = []
        self.ctx.successful = False
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.ref = {}
        
        #Style: {atomtype : listof all corelevel, atomtype_coresetup... }
        #ie: { 'W-1' : [shift_1s, ... shift 7/2 4f], 
        #      'W-1_coreconfig' : ['1s','2s',...], 
        #      'W-2' : [...], 'Be-1': [], ...} #all in eV!
        self.ctx.CLS = {}
        self.ctx.cl_energies = {}# same style as CLS only energy <-> shift   
        self.ctx.ref_cl_energies = {}
        #Style: {'Compound' : energy, 'ref_x' : energy , ...}
        #i.e {'Be12W' : 0.0, 'Be' : 0.104*htr_eV , 'W' : 0.12*htr_eV} # all in eV!
        self.ctx.fermi_energies = {}
        self.ctx.bandgaps = {}
        self.ctx.atomtypes = {}
        # set values, or defaults for Wf_para
        wf_dict = self.inputs.wf_parameters.get_dict()
        default = self._default_wf_para

        self.ctx.serial = wf_dict.get('serial', default.get('serial'))
        self.ctx.same_para = wf_dict.get('same_para', default.get('same_para'))
        self.ctx.scf_para = wf_dict.get('scf_para', default.get('scf_para'))
        
        self.ctx.relax = wf_dict.get('relax', default.get('relax'))
        self.ctx.relax_mode = wf_dict.get('relax_mode', default.get('relax_mode'))
        self.ctx.relax_para = wf_dict.get('relax_para', default.get('dos_para'))
        self.ctx.resources = wf_dict.get('resources', default.get('resources'))
        self.ctx.walltime_sec = wf_dict.get('walltime_sec', default.get('walltime_sec'))
        self.ctx.queue = wf_dict.get('queue_name', default.get('queue_name'))
        # check if inputs given make sense
        inputs = self.inputs        
        if 'fleurinp' in inputs:
            #TODO make a check if an extracted structure exists, since get_structuredata is wf
            structure = inputs.fleurinp.get_structuredata(inputs.fleurinp)
            self.ctx.elements = list(structure.get_composition().keys())
            self.ctx.calcs_torun.append(inputs.get('fleurinp'))
            #print('here1')
            if 'structure' in inputs:
                warning = 'WARNING: Ignoring Structure input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
            if 'calc_parameters' in inputs:
                warning = 'WARNING: Ignoring parameter input, because Fleurinp was given'
                print(warning)
                self.ctx.warnings.append(warning)
        elif 'structure' in inputs:
            self.ctx.elements = list(inputs.structure.get_composition().keys())
            #self.ctx.elements = list(s.get_symbols_set())  
            if not 'inpgen' in inputs:
                error = 'ERROR: StructureData was provided, but no inpgen code was provided'
                print(error)
                self.ctx.errors.append(error)
                #TODO kill workflow
            if 'calc_parameters' in inputs:
                self.ctx.calcs_torun.append((inputs.get('calc_parameters'), inputs.get('structure')))
                #print('here2')
            else:
                self.ctx.calcs_torun.append(inputs.get('structure'))
                #print('here3')
        else:
            error = 'ERROR: No StructureData nor FleurinpData was provided'
            print(error)
            self.ctx.errors.append(error)
            #TODO kill workflow          
        print('elements in structure: {}'.format(self.ctx.elements))
        
        
    def get_refernces(self):
        """
        To calculate a CLS in inital state approx, we need reference calculations
        to the Elemental crystals. First it is checked if the user has provided them
        Second the database is checked, if there are structures with certain extras.
        Third the COD database is searched for the elemental Cystal structures.
        If some referneces are not found stop here.
        Are there already calculation of these 'references', ggf use them.
        We do not put these calculation in the calculation queue yet because we
        need specific parameters for them
        """
        print('In Get_references inital_state_CLS workflow')   
        #references = self.inputs.wf_parameters.get_dict().get('references', {'calculate' : 'all'})
        references = self.inputs.wf_parameters.get_dict().get('references', {})
        # should be of the form of
        #'references' : { 'W': calc, outputnode of workflow or fleurinp, 
                         #or structure data or (structure data + Parameter), 
        #                 'Be' : ...}
        
        self.ctx.ref = {}
         
        #TODO better checks if ref makes sense?
        for elem in self.ctx.elements:
            #to_calc[elem] = 'find' 
            ref_el = references.get(elem, None)
            if ref_el:
                if isinstance(ref_el, (StructureData, ParameterData)):
                    #self.ctx.ref[elem] = ref_el
                    #enforced parameters, add directly to run queue
                    self.ctx.ref_calcs_torun.append(ref_el)
                elif isinstance(ref_el, FleurCalc):
                    #extract from fleur calc TODO
                    self.ctx.ref_cl_energies[elem] = {}
                elif isinstance(ref_el, ParameterData):
                    #extract from workflow output TODO
                    self.ctx.ref_cl_energies[elem] = {}             
                elif isinstance(ref_el, FleurinpData):
                    # add to calculations
                    #enforced parameters, add directly to run queue
                    self.ctx.ref_calcs_torun.append(ref_el)
                    #self.ctx.ref[elem] = ref_el
                elif isinstance(ref_el, StructureData):
                    self.ctx.ref[elem] = ref_el
                #elif isinstance(ref_el, initial_state_CLS):
                #    extract TODO
                else:
                    error = (" I do not know what to do with this given reference"
                             "{} for element {}".format(ref_el, elem))
                    print(error)
                    self.ctx.errors.append(error)
                    #TODO log, ggf warning or error
            else: # no ref given, we have to look for it.
                structure = querry_for_ref_structure(elem)
                if structure:
                    self.ctx.ref[elem] = ref_el
                else: #not found
                    error = ("Reference structure for element: {} not found."
                             "checkout the 'querry_for_ref_structure' method."
                             "to see what extras are querried for.".format(elem))
                    print(error)
                    self.ctx.errors.append(error)
                    #TODO log, warning or error
        print('self.ctx.ref: {} '.format(self.ctx.ref))
        #StructureData 
        #ParameterData
        #FleurinpData
        #FleurCalc
        
        # check if a structureData for these elements was given
        #if yes add to ref_calc to run
        #was also a prameter node given for the element?
        #yes run with these
        #no was on given for the host structure, extract element parameternode
        
        #else use parameters extracted from host calculation # TODO
        
        #check if there is a structure from this element in the database with extras: 
        # with extra.type = 'bulk', extra.specific = 'reference', 'extra.elemental' = True, extra.structure = 'W'
        # check if input parameter node values for the calculation are the same.
        
        #if yes, if a calculation exists use that result
        #else do a calculation on that structure as above
 

    
    def run_fleur_scfs(self):
        """
        Run SCF-cycles for all structures, calculations given in certain workflow arrays.
        """
        print('In run_fleur_scfs inital_state_CLS workflow')        
        #from aiida.work import run, async, 
        from aiida.tools.codespecific.fleur.convergence import fleur_convergence
        #TODO if submiting of workdlows work, use that. 
        #or run them with async (if youy know how to extract results) 
        
        para = self.ctx.scf_para
        if para == 'default': 
            wf_parameter = {}
        else:
            wf_parameter = para
        
        wf_parameter['queue_name'] = self.ctx.queue
        wf_parameters =  ParameterData(dict=wf_parameter)
        res_all = []
        # for each calulation in self.ctx.calcs_torun #TODO what about wf params?
        print self.ctx.calcs_torun
        for node in self.ctx.calcs_torun:
            print node
            if isinstance(node, StructureData):
                res = fleur_convergence.run(wf_parameters=wf_parameters, structure=node, 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = fleur_convergence.run(wf_parameters=wf_parameters, structure=node, 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, (StructureData, ParameterData)):
                res = fleur_convergence.run(wf_parameters=wf_parameters, calc_parameters=node(1), structure=node(0), 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            else:
                print('something in calcs_torun which I do not reconise: {}'.format(node))
                continue
            res_all.append(res)
            print res  
            self.ctx.calcs_res.append(res)
            #self.ctx.calcs_torun.remove(node)
            #print res    
        self.ctx.calcs_torun = []
        #return ToContext(last_calc=res)
        
        '''    
        inputs = get_inputs_fleur(code, remote, fleurin, options)
        future = submit(FleurProcess, **inputs)
        self.ctx.loop_count = self.ctx.loop_count + 1
        print 'run FLEUR number: {}'.format(self.ctx.loop_count)
        self.ctx.calcs.append(future)
        '''
        #return ToContext(last_calc=res) #calcs.append(future

        
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

    
    def find_parameters(self):
        """
        If the same parameters shall be used in the calculations you have to 
        find some that match. For low error on CLS. therefore use the ones enforced
        or extract from the previous Fleur calculation.
        """
        #self.ctx.ref[elem] = ref_el        
        #self.ctx.ref_calcs_torun.append(ref_el)
        
        # for entry in ref[elem] find parameter node
        for elm, struc in self.ctx.ref:
            pass
            # if parameter node given, extract from there, 
            #parameter_dict
            # else
            #extract parameter out of previous calculation
            #parameter_dict = fleurinp.extract_para(element)
            # BE CAREFUL WITH LOs! soc and co

    def run_scfs_ref(self):
        """
        Run SCF-cycles for ref structures, calculations given in certain workflow arrays.
        parameter nodes should be given
        """
        print('In run_fleur_scfs inital_state_CLS workflow')        
        #from aiida.work import run, async, 
        from aiida.tools.codespecific.fleur.convergence import fleur_convergence
        #TODO if submiting of workdlows work, use that. 
        #or run them with async (if youy know how to extract results) 
        
        para = self.ctx.scf_para
        if para == 'default': 
            wf_parameter = {}
        else:
            wf_parameter = para
        
        wf_parameter['queue_name'] = self.ctx.queue
        wf_parameters =  ParameterData(dict=wf_parameter)
        res_all = []
        # for each calulation in self.ctx.calcs_torun #TODO what about wf params?
        print self.ctx.ref_calcs_torun
        for node in self.ctx.ref_calcs_torun:
            print node
            if isinstance(node, StructureData):
                res = fleur_convergence.run(wf_parameters=wf_parameters, structure=node, 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = fleur_convergence.run(wf_parameters=wf_parameters, structure=node, 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, (StructureData, ParameterData)):
                res = fleur_convergence.run(wf_parameters=wf_parameters, calc_parameters=node(1), structure=node(0), 
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            else:
                print('something in calcs_torun which I do not reconise: {}'.format(node))
                continue
            res_all.append(res)
            print res  
            self.ctx.ref_calcs_res.append(res)
            #self.ctx.calcs_torun.remove(node)
            #print res    
        self.ctx.ref_calcs_torun = []
        #return ToContext(last_calc=res)
        

        
    def collect_results(self):
        """
        Collect results from certain calculation, check if everything is fine, 
        calculate the wanted quantities. currently all energies are in hartree (as provided by Fleur)
        """
        print('Collecting results of inital_state_CLS workflow')        
        # TODO be very careful with core config?
        #from pprint import pprint
        
        #self.ctx.ref_cl_energies
        all_CLS = {}
        # get results from calc
        calcs = self.ctx.calcs_res
        ref_calcs = self.ctx.ref_calcs_res         
        fermi_energies, bandgaps, atomtypes, all_corelevel = extract_results(calcs)
        ref_fermi_energies, ref_bandgaps, ref_atomtypes, ref_all_corelevel = extract_results(ref_calcs)

        ref_cl_energies = {}
        cl_energies = {}
        
        #first substract efermi from corelevel of reference structures
        for compound, atomtypes_list in ref_atomtypes.iteritems():
            # atomtype_list contains a list of dicts of all atomtypes from compound x 
            # get corelevels of compound x
            cls_all_atomtyps = ref_all_corelevel[compound]
            for i, atomtype in enumerate(atomtypes_list):
                #atomtype a dict which contains one atomtype
                elm = atomtype.get('element', None)
                cls_atomtype = cls_all_atomtyps[i][0]
                ref_cl_energies[elm] = []
                ref_cls = []
                for corelevel in cls_atomtype['corestates']:
                    ref_cls.append(corelevel['energy']-ref_fermi_energies[compound])
                ref_cl_energies[elm].append(ref_cls)
        
        #pprint(ref_cl_energies)
        #pprint(all_corelevel)
        
        #now substract efermi from corelevel of compound structure
        #and calculate core level shifts
        for compound, cls_atomtypes_list in all_corelevel.iteritems():
            #init, otherwise other types will override
            for i, atomtype in enumerate(atomtypes[compound]):
                elm = atomtype.get('element', None)
                cl_energies[elm] = []
                all_CLS[elm] = []
            
            #now fill
            for i, atomtype in enumerate(atomtypes[compound]):
                elm = atomtype.get('element', None)
                print elm
                cls_atomtype = cls_atomtypes_list[i]
                corelevels = []
                for corelevel in cls_atomtype[0]['corestates']:
                    correct_cl = corelevel['energy']-fermi_energies[compound]
                    corelevels.append(correct_cl)
                cl_energies[elm].append(corelevels)   
                
                #now calculate CLS
                ref = ref_cl_energies[elm][-1]# We just use one (last) atomtype
                #of elemental reference (in general might be more complex,
                #since certain elemental unit cells could have several atom types (graphene))
                corelevel_shifts = []
                #TODO shall we store just one core-level shift per atomtype?
                for i, corelevel in enumerate(cl_energies[elm][-1]):
                    corelevel_shifts.append(corelevel - float(ref[i]))
                all_CLS[elm].append(corelevel_shifts)
        
        # TODO make simpler format of atomtypes for node
        # TODO write corelevel explanation/coresetup in a format like 4f7/2 
        #TODO ? also get total energies?
        return cl_energies, all_CLS, ref_cl_energies, fermi_energies, bandgaps, ref_fermi_energies, ref_bandgaps, atomtypes, ref_atomtypes
        
    def return_results(self):
        """
        return the results of the calculations
        """
        # TODO more output, info here
        
        #print corelevel shifts were calculated bla bla
        cl, cls, ref_cl, efermi, gap, ref_efermi, ref_gap, at, at_ref =  self.collect_results()
        
        outputnode_dict ={}
        
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['warnings'] = self.ctx.warnings               
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['corelevel_energies'] = cl #self.ctx.cl_energies
        outputnode_dict['reference_corelevel_energies'] = ref_cl #self.ctx.cl_energies
        outputnode_dict['fermi_energy'] = efermi #self.ctx.fermi_energies               
        outputnode_dict['corelevelshifts'] = cls #self.ctx.CLS
        outputnode_dict['coresetup'] = []#cls
        outputnode_dict['reference_coresetup'] = []#cls
        outputnode_dict['bandgap'] = gap#self.ctx.bandgaps
        outputnode_dict['reference_bandgaps'] = ref_gap#self.ctx.bandgaps
        outputnode_dict['atomtypes'] = at#self.ctx.atomtypes
        #print outputnode_dict
        outputnode = ParameterData(dict=outputnode_dict)
        outdict = {}
        outdict['output_inital_cls_wc_para'] = outputnode
        #print outdict
        for k, v in outdict.iteritems():
            self.out(k, v)
        print('Inital_state_CLS workflow Done')

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

def querry_for_ref_structure(element_string):
    """
    This methods finds StructureData nodes with the following extras:
    extra.type = 'bulk', # Should be done by looking at pbc, but I could not get querry to work.
    extra.specific = 'reference', 
    'extra.elemental' = True, 
    extra.structure = element_string
    
    param: element_string: string of an element
    return: the latest StructureData node that was found
    
    """
    from aiida.orm import QueryBuilder

    #query db
    q = QueryBuilder()
    q.append(StructureData,
        filters = {
            'extras.type' : {'==' : 'bulk'},
            'extras.specification' : {'==' : 'reference'},
            'extras.elemental' : {'==' : True},
            'extras.element' : {'==' : element_string}
            }
        )
    q.order_by({StructureData : 'ctime'})#always use the most recent
    structures = q.all()
    
    if structures:
        return structures[-1][0]            
    else:
        return None

    
def fleur_calc_get_structure(calc_node):
    #get fleurinp
    fleurinp = calc_node.inp.fleurinpdata
    structure = fleurinp.get_structuredata(fleurinp)
    return structure

def extract_results(calcs):
    """
    Collect results from certain calculation, check if everything is fine, 
    calculate the wanted quantities.
    """
    calc_uuids = []
    for calc in calcs:
        print(calc)
        calc_uuids.append(calc['output_scf_wf_para'].get_dict()['last_calc_uuid'])
    print(calc_uuids)
    
    all_corelevels = {}
    fermi_energies = {}
    bandgaps = {}
    all_atomtypes = {}  
    # more structures way: divide into this calc and reference calcs.
    # currently the order in calcs is given, but this might change if you submit
    # check if calculation pks belong to successful fleur calculations
    for uuid in calc_uuids:
        calc = load_node(uuid)
        if (not isinstance(calc, FleurCalc)):
            #raise ValueError("Calculation with pk {} must be a FleurCalculation".format(pk))
            # log and continue
            continue
        if calc.get_state() != 'FINISHED':
            # log and continue
            continue
            #raise ValueError("Calculation with pk {} must be in state FINISHED".format(pk))
        
        # get out.xml file of calculation
        outxml = calc.out.retrieved.folder.get_abs_path('path/out.xml')
        corelevels, atomtypes = extract_corelevels(outxml)
        #all_corelevels.append(core)
        #print('corelevels: {}'.format(corelevels))
        #print('atomtypes: {}'.format(atomtypes))
        #for i in range(0,len(corelevels[0][0]['corestates'])):
        #    print corelevels[0][0]['corestates'][i]['energy']
            
        #TODO how to store?
        efermi = calc.res.fermi_energy
        print efermi
        bandgap = calc.res.bandgap
        
        # TODO: maybe different, because it is prob know from before
        fleurinp = calc.inp.fleurinpdata
        structure = fleurinp.get_structuredata(fleurinp)            
        compound = structure.get_formula()
        #print compound
        fermi_energies[compound] = efermi
        bandgaps[compound] = bandgap
        all_atomtypes[compound] = atomtypes
        all_corelevels[compound] = corelevels
        #fermi_energies = efermi
        #bandgaps = bandgap
        #all_atomtypes = atomtypes
        #all_corelevels = corelevels
    
    return fermi_energies, bandgaps, all_atomtypes, all_corelevels
    #TODO validate results and give some warnings
    
    # check bandgaps, if not all metals, throw warnings:
    # bandgap and efermi prob wrong, which makes some results meaningless
    
    # check fermi energy differences, correct results for fermi energy diff
    # ggf TODO make a raw core-level and core-level to fermi energy variable
    #TODO to what reference energy? or better not to fermi, but first unocc? (add bandgap)

    #Style: {atomtype : listof all corelevel, atomtype_coresetup... }
    #ie: { 'W-1' : [shift_1s, ... shift 7/2 4f], 
    #      'W-1_coreconfig' : ['1s','2s',...], 
    #      'W-2' : [...], 'Be-1': [], ...} #all in eV!
    #self.ctx.CLS = {}
    #self.ctx.cl_energies = {}# same style as CLS only energy <-> shift   
    
    #Style: {'Compound' : energy, 'ref_x' : energy , ...}
    #i.e {'Be12W' : 0.0, 'Be' : 0.104*htr_eV , 'W' : 0.12*htr_eV} # all in eV!
    #self.ctx.fermi_energies = {}    
