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
This is the workflow 'corehole' using the Fleur code, which calculates binding
energies and corelevel shifts with different methods.
'divide and conquer'
"""

# TODO maybe also calculate the reference structure to check on the supercell calculation
# TODO creation of wf_para nodes for scf fleurinp_changes for corelevel has to be right
# TODO maybe always rewrite hole econfig tag in inp.xml otherwise it might lead to errors,
# be careful with LOs.
# TODO corelevel workflow, rename species of 0,0,0 position in inp.xml

#import os.path
from __future__ import absolute_import
from __future__ import print_function
import six
import re
import numpy as np
from pprint import pprint
from aiida.plugins import DataFactory
from aiida.orm import Code, load_node, CalcJobNode
from aiida.orm import Int, StructureData, Dict, RemoteData
from aiida.engine import WorkChain, if_, ToContext
from aiida.engine import submit
#from aiida.work.process_registry import ProcessRegistry
from aiida.engine.processes.functions import calcfunction as cf
from aiida_fleur.calculation.fleur import FleurCalculation
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.tools.StructureData_util import supercell
from aiida_fleur.tools.create_corehole import create_corehole_para  #, create_corehole_fleurinp
from aiida_fleur.tools.extract_corelevels import extract_corelevels
from aiida_fleur.tools.StructureData_util import break_symmetry
from aiida_fleur.tools.StructureData_util import find_equi_atoms
from aiida_fleur.tools.element_econfig_list import get_econfig, get_coreconfig
from aiida_fleur.tools.element_econfig_list import econfigstr_hole, states_spin
from aiida_fleur.tools.element_econfig_list import get_state_occ, highest_unocc_valence
from aiida_fleur.tools.dict_util import dict_merger, extract_elementpara
from aiida_fleur.data.fleurinp import FleurinpData


class fleur_corehole_wc(WorkChain):
    """
    Turn key solution for a corehole calculation with the FLEUR code.
    Has different protocols for different core-hole types (valence, charge).

    Calculates supercells. Extracts binding energies
    for certain corelevels from the total energy differences a the calculation with
    corehole and without.

    Documentation:
    See help for details.

    Two paths are possible:

    (1) Start from a structure -> workchains run inpgen first (recommended)
    (2) Start from a Fleurinp data object

    Also it is recommended to provide a calc parameter node for the structure

    :param wf_parameters: Dict node, specify, resources and what should be calculated
    :param structure: structureData node, crystal structure
    :param calc_parameters: Dict node, inpgen parameters for the crystal structure
    :param fleurinp:  fleurinpData node,
    :param inpgen: Code node,
    :param fleur: Code node,

    :return: output_corehole_wc_para Dict node,  successful=True if no error

    :uses workchains: fleur_scf_wc, fleur_relax_wc
    :uses calcfunctions: supercell, create_corehole_result_node, prepare_struc_corehole_wf

    """
    # This block of commented code was removed from the docstring and should be put
    # to the other place in the documentation.
    # minimum input example:
    # 1. Code1, Code2, Structure, (Parameters), (wf_parameters)
    # 2. Code2, FleurinpData, (wf_parameters)

    # maximum input example:
    # 1. Code1, Code2, Structure, Parameters,
    #    wf_parameters: {
    #         'method' : 'valence', # what method to use, default for valence to highest open shell
    #         'hole_charge' : 1.0,       # what is the charge of the corehole? 0<1.0
    #         'atoms' : ['all'],           # coreholes on what atoms, positions or index for list, or element ['Be', (0.0, 0.5, 0.334), 3]
    #         'corelevel': ['all'],        # coreholes on which corelevels [ 'Be1s', 'W4f', 'Oall'...]
    #         'supercell_size' : [2,1,1], # size of the supercell [nx,ny,nz]
    #         'para_group' : None,       # use parameter nodes from a parameter group
    #         #'references' : 'calculate',# at some point aiida will have fast forwarding
    #         'relax' : False,          # relax the unit cell first?
    #         'relax_mode': 'Fleur',    # what releaxation do you want
    #         'relax_para' : None, # parameter dict for the relaxation
    #         'scf_para' : None,    # wf parameter dict for the scfs
    #         'same_para' : True,        # enforce the same atom parameter/cutoffs on the corehole calc and ref
    #         'resources' : {"num_machines": 1},# resources per job
    #         'max_wallclock_seconds' : 6*60*60,    # walltime per job
    #         'queue_name' : '',       # what queue to submit to
    #         'serial' : True,           # run fleur in serial, or parallel?
    #         #'job_limit' : 100          # enforce the workflow not to spawn more scfs wcs then this number(which is roughly the number of fleur jobs)
    #         'magnetic' : True          # jspins=2, makes a difference for coreholes
    #         }
    # 2. Code2, FleurinpData, (remote-data), wf_parameters as in 1.

    # Hints:
    # 1. This workflow does not work with local codes!

    _workflowversion = '0.4.0'
    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1,
        },
        'max_wallclock_seconds': 6 * 60 * 60,
        'queue_name': '',
        #'custom_scheduler_commands': '',
        #'import_sys_environment': False,
        #'environment_variables': {}
    }
    _default_wf_para = {
        'method': 'valence',  # what method to use, default for valence to highest open shell
        'hole_charge': 1.0,  # what is the charge of the corehole? 0<1.0
        'atoms':
        ['all'],  # coreholes on what atoms, positions or index for list, or element ['Be', (0.0, 0.5, 0.334), 3]
        'corelevel': ['all'],  # coreholes on which corelevels [ 'Be1s', 'W4f', 'Oall'...]
        'supercell_size': [2, 1, 1],  # size of the supercell [nx,ny,nz]
        'para_group': None,  # use parameter nodes from a parameter group
        #'references' : 'calculate',# at some point aiida will have fast forwarding
        #'relax' : False,          # relax the unit cell first?
        #'relax_mode': 'Fleur',    # what releaxation do you want
        #'relax_para' : None, # parameter dict for the relaxation
        'scf_para': None,  # wf parameter dict for the scfs
        'same_para': True,  # enforce the same atom parameter/cutoffs on the corehole calc and ref
        'serial': True,  # run fleur in serial, or parallel?
        #'job_limit' : 100          # enforce the workflow not to spawn more scfs wcs then this number(which is roughly the number of fleur jobs)
        'magnetic': True
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('wf_parameters', valid_type=Dict, required=False, default=lambda: Dict(dict=cls._default_wf_para))
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('inpgen', valid_type=Code, required=True)
        spec.input('structure', valid_type=StructureData, required=False)
        spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.input('options', valid_type=Dict, required=False)  #, default=lambda: Dict(dict=cls._default_options))

        spec.outline(
            cls.check_input,  # first check if input is consistent
            if_(cls.relaxation_needed)(  # ggf relax the given cell
                cls.relax),
            if_(cls.supercell_needed)(  # create a supercell from the given/relaxed cell
                cls.create_supercell),
            cls.create_coreholes,
            cls.run_ref_scf,  # calculate the reference supercell first
            cls.check_scf,
            cls.run_scfs,  # calculate all other corehole calculations
            cls.check_scf,
            cls.return_results)
        spec.output('output_corehole_wc_para', valid_type=Dict)

        spec.exit_code(1, 'ERROR_INVALID_INPUT_RESOURCES', message='The input resources are invalid.')
        spec.exit_code(2, 'ERROR_INVALID_INPUT_RESOURCES_UNDERSPECIFIED', message='Input resources are missing.')
        spec.exit_code(3,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='The code provided is invalid, or not of the right kind.')
        spec.exit_code(4, 'ERROR_INPGEN_CALCULATION_FAILED', message='Inpgen calculation FAILED, check output')
        spec.exit_code(5,
                       'ERROR_CHANGING_FLEURINPUT_FAILED',
                       message='Changing of the FLEURINP data went wrong, check log.')
        spec.exit_code(6,
                       'ERROR_CALCULATION_INVALID_INPUT_FILE',
                       message='The FLEUR input file for the calculation did not validate.')
        spec.exit_code(7,
                       'ERROR_FLEUR_CALCULATION_FAiLED',
                       message='At least one FLEUR calculation FAILED, check the output and log.')
        spec.exit_code(8,
                       'ERROR_CONVERGENCE_NOT_ARCHIVED',
                       message=('At least one FLEUR calculation did not/could not reach the'
                                'desired convergece Criteria, with the current parameters.'))
        spec.exit_code(9,
                       'ERROR_IN_REFERENCE_CREATION',
                       message=('Something went wrong in the determiation what coreholes to '
                                'calculate, probably the input format was not correct. Check log.'))

    def check_input(self):
        """
        init all context parameters, variables.
        Do some input checks. Further input checks are done in further workflow steps
        """
        # TODO: document parameters
        self.report('started fleur_corehole_wc version {} '
                    'Workchain node identifiers: '  #{}"
                    ''.format(self._workflowversion))  #, ProcessRegistry().current_calc_node))

        ### init ctx ###

        # internal variables
        self.ctx.calcs_torun = []
        self.ctx.calcs_ref_torun = []
        self.ctx.labels = []
        self.ctx.calcs_res = []

        # input variables
        inputs = self.inputs
        if 'calc_parameters' in inputs:
            self.ctx.ref_para = inputs.get('calc_parameters')
        else:
            self.ctx.ref_para = None

        wf_dict = inputs.wf_parameters.get_dict()
        self.ctx.method = wf_dict.get('method', 'valence')
        self.ctx.joblimit = wf_dict.get('joblimit')
        self.ctx.serial = wf_dict.get('serial')
        self.ctx.same_para = wf_dict.get('same_para')
        self.ctx.scf_para = wf_dict.get('scf_para', {})
        self.ctx.be_to_calc = wf_dict.get('corelevel')
        self.ctx.atoms_to_calc = wf_dict.get('atoms')
        self.ctx.base_structure = inputs.get('structure')  # ggf get from fleurinp
        self.ctx.relax = False
        self.ctx.supercell_size = wf_dict.get('supercell_size', [2, 1, 1])  # 2x2x2 or smaller?
        self.ctx.hole_charge = wf_dict.get('hole_charge', 1.0)
        self.ctx.magnetic = wf_dict.get('magnetic', True)

        defaultoptions = self._default_options
        options = wf_dict.get('options', defaultoptions)
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        #self.ctx.relax = wf_dict.get('relax', default.get('relax'))
        #self.ctx.relax_mode = wf_dict.get('relax_mode', default.get('relax_mode'))
        #self.ctx.relax_para = wf_dict.get('relax_para', default.get('dos_para'))
        self.ctx.base_structure_relax = self.ctx.base_structure

        # return variables initalized here, that at any time an output node can be written.
        self.ctx.successful = True
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
        self.ctx.wbindingenergies = []
        ### input check ###
        """
        #ususal fleur stuff check
        if fleurinp.get structure
        self.ctx.inputs.base_structure
        wf_para = self.inputs.wf_parameters
        corelevel_to_calc = wf_para.get('corelevel', None)
        if not corelevel_to_calc:
            errormsg = 'You need to specify unter 'corelevel' in the wf_para node on what corelevel you want to have a corehole calculated. (Default is 'all')'
            self.abort_nowait(errormsg)

        """

    def supercell_needed(self):
        """
        check if a supercell is needed and what size it should be
        """
        #think about a rule here to apply 2x2x2 should be enough for nearly everything.
        # but for larger unit cells smaller onces might be ok.
        # So far we just go with what the user has given
        # Is there a way to tell if a supercell was already given as base?
        # Do we want to detect it with some spglib methods?
        self.ctx.supercell_boal = True
        needed = self.ctx.supercell_boal
        # TODO, otherwise in the new system if something else is returned this might fail...?
        return needed

    def create_supercell(self):
        """
        create the needed supercell
        """

        supercell_base = self.ctx.supercell_size
        description = (u'WF, Creates a supercell of a crystal structure x({},{},{}).'
                       ''.format(supercell_base[0], supercell_base[0], supercell_base[2]))

        supercell_s = supercell(self.ctx.base_structure_relax,
                                Int(supercell_base[0]),
                                Int(supercell_base[1]),
                                Int(supercell_base[2]),
                                metadata={
                                    'label': u'supercell_wf',
                                    'description': description
                                })

        # overwrite label and description of new structure
        supercell_s.label = '{}x{}x{} of {}'.format(supercell_base[0], supercell_base[1], supercell_base[2],
                                                    self.ctx.base_structure_relax.uuid)
        supercell_s.description = supercell_s.description + ' created in a fleur_corehole_wc'
        self.ctx.ref_supercell = supercell_s
        calc_para = self.ctx.ref_para
        if calc_para is None:
            new_calc = supercell_s
        else:
            new_calc = [supercell_s, calc_para]
        self.ctx.calcs_ref_torun.append(new_calc)

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
        # move all the atoms in the cell that impurity is in the origin (0.0, 0.0, 0.0)
        # use the fleurinp_change feature of scf to create the corehole after inpgen gen in the scf
        # start the scf with the last charge density of the ref calc? so far no, might not make sense

        # TODO if this becomes to long split
        """
        self.report('INFO: In create_coreholes of fleur_corehole_wc. ' 'Preparing everything for calculation launches.')

        ########### init variables ##############

        base_struc = self.ctx.base_structure_relax  # one unit cell (given cell)
        base_atoms_sites = base_struc.sites  # list of AiiDA Site types of cell
        base_kinds = base_struc.kinds  # list of AiiDA Kind types of cell
        valid_elements = list(base_struc.get_composition().keys())  # elements in structure
        base_supercell = self.ctx.ref_supercell  # supercell of base cell
        base_k_symbols = {}  #map kind names to elements

        for kind in base_kinds:
            base_k_symbols[kind.name] = kind.symbol

        # we have to find the atoms we want a corelevel on and make them a new kind,
        # also we have to figure out what electron config to set
        atoms_toc = self.ctx.atoms_to_calc  #['Be', (0.0, 0.5, 0.334)/ 3(index)/ 'all']
        if self.ctx.be_to_calc[0] == 'all':
            corelevels_toc_new = []
            for element in valid_elements:
                corelevels_toc_new.append('{}-all'.format(element))
        else:
            corelevels_toc_new = self.ctx.be_to_calc

        corelevels_toc = corelevels_toc_new  # [ 'Be 1s', 'W_4f', 'O all', 'W-3d'...]

        coreholes_atoms = []  # list of aiida sites
        corehole_to_create = []  # prepare list of dicts for final loop, for calculation creation
        #[{'site' : sites[8], 'kindname' : 'W1', 'econfig': "[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2", 'fleurinp_change' : []}]

        # get the symmetry equivivalent atoms by ase
        # equi_info_symbol = [['W', 1,2,3,8], ['Be', 4,5,6,7,9] ...]
        #n_equi_info_symbol= {'Be' : count, ...}
        equi_info_symbol, n_equi_info_symbol = find_equi_atoms(base_struc)
        #print(n_equi_info_symbol)
        method = self.ctx.method
        if method == 'valence':
            hole_charge = self.ctx.hole_charge
            correct_val_charge = False  # the routines add the electron per default to the valence
            htype = 'valence'
        elif method == 'charge':
            hole_charge = self.ctx.hole_charge
            correct_val_charge = True
            htype = 'charge'
        else:
            htype = 'valence'  # default so far, otherwise not defined.
            # TODO probally better, to throw error
            hole_charge = self.ctx.hole_charge
            correct_val_charge = False  # the routines add the electron per default to the valence

        ##########
        # 1. Find out what atoms to put coreholes on
        self.report('Atoms to calculate : {}'.format(atoms_toc))
        for atom_info in atoms_toc:
            if isinstance(atom_info, (str, six.text_type)):  #basestring):
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
            elif isinstance(atom_info, tuple):  # coordinates
                if len(atom_info) == 3:
                    for site in base_atoms_sites:
                        if site.position == atom_info:  #ggf give a threshold...
                            coreholes_atoms.append(site)
                else:
                    # wrong tuple length this is not a  position
                    self.report('WARNING: strange position/coordinates given: {}'.format(atom_info))
                    #
            elif isinstance(atom_info, int):  # index for sites
                to_append = None
                try:
                    to_append = base_atoms_sites[atom_info]
                except IndexError:
                    error = ("ERROR: The index/integer: {} specified in 'atoms' key is not valid."
                             'There are only {} atom sites in your provided structure.'
                             ''.format(atom_info, len(base_atoms_sites)))
                    to_append = None
                    self.report(error)
                if to_append:
                    coreholes_atoms.append(to_append)
            else:
                self.report("WARNING: input: {} of 'atoms' not recongized".format(atom_info))

        # TODO: remove doubles in coreholes_atoms?
        #print(coreholes_atoms)
        #print(corelevels_toc)
        dict_corelevel = {}
        # dict_corelevel['W' : {corelevel: ['1s 1/2','4f 7/2', '4f 3/2'], econfig: [config], fleur_changes : []}]

        #########
        # 2. now check what type of corelevel shall we create on those atoms
        self.report('Corelevels to calculate : {}'.format(corelevels_toc))
        for corel in corelevels_toc:
            if isinstance(corel, (str, six.text_type)):  #basestring):
                # split string (Be1s) s.replace(';',' ')... could get rid of re
                elm_cl = re.split('[, ;:-]', corel)
                #print(elm_cl)
                if len(elm_cl) != 2:
                    # something went wrong, wrong input
                    # TODO log, error and hint
                    error = ('ERROR: corelevel was given in the wrong format: {},'
                             'should have len 2. Hint hast to be the format '
                             "['Element,corelevel',...] i.e ['Be,1s', 'W,all]".format(elm_cl))
                    self.control_end_wc(error)
                    return self.exit_codes.ERROR_IN_REFERENCE_CREATION
                else:
                    # we assume for now ['Element', 'corelevel'] i.e ['Be', '1s']
                    econfigs = []
                    all_corestates = []
                    all_changed_valence = []
                    elm_cl = [str(elm_cl[0]), str(elm_cl[1])]  #otherwise stuff fails because of basestrings
                    if elm_cl[0] in valid_elements:
                        # get corelevel econfig of element
                        dict_corelevel_elm = {}
                        # if econfig given in calc parameter use this econfig...
                        para = self.ctx.ref_para
                        if para is not None:
                            para_dict = para.get_dict()
                            self.report('INFO para is here: {}'.format(para_dict))
                            element_para = extract_elementpara(para_dict, elm_cl[0])
                            valid_coreconfig = element_para.get('econfig', get_coreconfig(elm_cl[0], full=True))
                        else:
                            valid_coreconfig = get_coreconfig(elm_cl[0], full=True)
                        oriegconfig = get_econfig(elm_cl[0], full=True)
                        highest_unocc = highest_unocc_valence(oriegconfig)
                        if elm_cl[1] == 'all':
                            # add all corelevels to calculate
                            corestates = valid_coreconfig.split()
                            for state in corestates:
                                holeconfig = econfigstr_hole(oriegconfig, state, highest_unocc, htype=htype)
                                rel_states = states_spin.get(state[1], [])
                                for rel in rel_states:
                                    econfigs.append(holeconfig)
                                    all_corestates.append(state + ' ' + rel)
                                    all_changed_valence.append(highest_unocc[:2])
                        elif elm_cl[1] in valid_coreconfig:  # check if corelevel in valid coreconfig
                            #add corelevel to calculate.
                            state_index = oriegconfig.find(elm_cl[1])
                            state = oriegconfig[state_index:state_index + 4].rstrip(' ')  # +4: icii, or ici
                            holeconfig = econfigstr_hole(oriegconfig, state, highest_unocc, htype=htype)
                            rel_states = states_spin.get(state[1], [])
                            # get rel core level (for 4f 5/2, 7/2)
                            for rel in rel_states:
                                econfigs.append(holeconfig)
                                all_corestates.append(state + ' ' + rel)
                                all_changed_valence.append(highest_unocc[:2])  # the methods below need them without occ
                        elif '/' in elm_cl[1]:
                            pass  # TODO FUll state information given...[4f 7/2]
                        else:
                            # corelevel provided wrong, not understood, warning
                            continue
                        # TODO several corelevels of one element... update lists instead of override...
                        dict_corelevel_elm['corelevel'] = all_corestates
                        dict_corelevel_elm['valence'] = all_changed_valence
                        dict_corelevel_elm['econfig'] = econfigs
                        tempd = dict_corelevel.get(elm_cl[0], {})
                        # dict_merger also addes numbers!
                        together = dict_merger(dict_corelevel_elm, tempd)
                        #pprint(together)
                        dict_corelevel[elm_cl[0]] = together
                    else:
                        pass
                        #element or string provieded not in structure,
                        # what about upper and lower caps

        #print(dict_corelevel)
        #output of above
        #list of sites [site_bla, ..]
        #dict_corelevel = {'Be' : {'corelevel' : ['1s1/2'], 'valence' : [], 'econfig' : ['1s2 | 2s2']}}
        # now put atom and corehole information together
        for site in coreholes_atoms:
            selem = base_k_symbols[site.kind_name]
            cl_dict = dict_corelevel.get(selem, None)
            if cl_dict:
                # what coreholes need to be created for that element
                for i, econfig in enumerate(cl_dict.get('econfig', [])):
                    fleurinp_change = []
                    change_kind = site.kind_name + '_corehole1'  # the number at the end
                    # is important otherwise inpgen does not make this a new species
                    # through the hard coded one might lead to conflicts..

                    kind = site.kind_name  # + '1'# this will be the kind name in the broke sym structure,
                    #its name will be changed later to change_kind
                    # maybe the kind name cann also not be known at this point
                    #self.report('{}, {}, {}, {}'.format(econfig, cl_dict.get('corelevel')[i], cl_dict.get('valence')[i], hole_charge))
                    #print(cl_dict.get('corelevel')[i])
                    #print(cl_dict.get('valence')[i])
                    #print(econfig)
                    state_tag_list = get_state_occ(econfig,
                                                   corehole=cl_dict.get('corelevel')[i],
                                                   valence=cl_dict.get('valence')[i],
                                                   ch_occ=hole_charge)
                    attributedict = {'electronConfig': {'stateOccupation': state_tag_list}}
                    #pprint(state_tag_list)
                    change = ('set_species', {
                        'species_name': change_kind,
                        'attributedict': attributedict,
                        'create': False
                    })
                    fleurinp_change.append(change)
                    if correct_val_charge:  # only needed in certain methods
                        charge_change = (
                            'add_num_to_att',
                            {
                                'xpathn': '/fleurInput/calculationSetup/bzIntegration',
                                'attributename': 'valenceElectrons',
                                'set_val': -1.0000,  #-hole_charge,  #one electron was added by ingen, we remove it
                                'mode': 'abs',
                                'occ': [0],
                            })
                        fleurinp_change.append(charge_change)
                    elif hole_charge != 1.0:  # fractional valence hole
                        charge_change = (
                            'add_num_to_att',
                            {
                                'xpathn': '/fleurInput/calculationSetup/bzIntegration',
                                'attributename': 'valenceElectrons',
                                'set_val': -1.0000 + hole_charge,  # one electron was already added by inpgen
                                'mode': 'abs',
                                'occ': [0],
                            })
                        fleurinp_change.append(charge_change)
                    if self.ctx.magnetic:  # Do a collinear magentic calculation
                        charge_change = ('set_inpchanges', {'change_dict': {'jspins': 2}})
                        fleurinp_change.append(charge_change)
                    #self.report('{}'.format(fleurinp_change))
                    # because there might be already some kinds and another number is right...
                    # repacking of sites, because input to a calcfunction, otherwise not storeable...
                    corehole = {
                        'site': {
                            'kind_name': kind,  #site.kind_name,
                            'position': site.position
                        },
                        'econfig': econfig,
                        'kindname': change_kind,
                        'inpxml_changes': fleurinp_change
                    }
                    corehole_to_create.append(corehole)

        #state_tag_list = get_state_occ(econfigstr, corehole = '', valence = '', ch_occ = 1.0):

        # lesson go over site position to get atom in supercell
        # set econfig for this atom in the supercell
        # (default kind name = element + id) use this for paramter settings

        # fill calcs_torun with (sturcutre, parameter, wf_para)
        #corehole_to_create = [{'site' : sites[8], 'kindname' : 'W1', 'econfig': "[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2", 'fleurinp_change' : []}]
        calcs = []
        for corehole in corehole_to_create:
            para = self.ctx.ref_para
            wf_para = Dict(dict=corehole)
            #print(corehole)
            #print(base_supercell)
            #print(para)
            # all these steps can be calcfunctions, we have grouped them all in one
            ret_dict = prepare_struc_corehole_wf(base_supercell, wf_para, para)
            moved_struc = ret_dict['moved_struc']
            calc_para = ret_dict['hole_para']
            #print('calc_para:')
            #pprint(calc_para.get_dict())
            #pprint('inpxml_changes {}'.format(corehole['inpxml_changes']))
            # create_wf para or write in last line what should be in 'fleur_change'
            #  for scf, which with the changes in the inp.xml needed
            para = self.ctx.scf_para  # Otherwise inline edit... What about Provenance? TODO check
            if para is None:
                wf_parameter = {}
            else:
                wf_parameter = para
            #print(wf_parameter)
            wf_parameter['serial'] = self.ctx.serial
            wf_parameter['inpxml_changes'] = corehole['inpxml_changes']

            wf_parameters = Dict(dict=wf_parameter)
            calcs.append([moved_struc, calc_para, wf_parameters])
        self.ctx.calcs_torun = calcs
        #print('ctx.calcs_torun {}'.format(self.ctx.calcs_torun))
        #self.report('INFO: end of create coreholes')

    '''
    def run_scf2(self):
        """
        Run scf
        """
        calcs = {}
        i = 0
        for scf_input in self.ctx.calcs_ref_torun:
            try:
                res = submit(fleur_scf_wc,
                          fleur=self.inputs.fleur,
                          inpgen = self.inputs.inpgen,
                          **scf_input)
            except: # TODO only if input is wrong
                self.report('WARNING: something in run_ref_scf which I do not reconise: {}'.format(scf_input))
                continue

            label = str('calc_ref{}'.format(i))
            self.ctx.labels.append(label)
            calcs[label] = res

        self.ctx.calcs_ref_torun = []
        return ToContext(**calcs)#  this is a blocking return
    '''

    def run_ref_scf(self):
        """
        Run a scf for the reference super cell
        """

        # TODO: idea instead of a list, just use a dictionary...
        self.report('INFO: In run_ref_scf fleur_corehole_wc')
        print('INFO: In run_ref_scf fleur_corehole_wc')
        para = self.ctx.scf_para
        if para is None:
            wf_parameter = {}
        else:
            wf_parameter = para
        wf_parameter['serial'] = self.ctx.serial
        wf_parameters = Dict(dict=wf_parameter)
        options = Dict(dict=self.ctx.options)
        '''
        #res_all = []
        calcs = {}

        i = 0
        for node in self.ctx.calcs_ref_torun: # usually just 1, but we leave the default.
            #print(node)
            i = i+1
            if isinstance(node, StructureData):
                res = fleur_scf_wc.run(wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, FleurinpData):
                res = fleur_scf_wc.run(wf_parameters=wf_parameters, structure=node,
                            inpgen = self.inputs.inpgen, fleur=self.inputs.fleur)#
            elif isinstance(node, tuple):
                if isinstance(node[0], StructureData) and isinstance(node[1], Dict):
                    #print(node[1].get_dict())
                    res = fleur_scf_wc.run(wf_parameters=wf_parameters, calc_parameters=node[1], structure=node[0],
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

        '''
        #res_all = []
        calcs = {}
        scf_label = 'corehole_wc ref cell'
        scf_desc = '|corehole_wc|'
        i = 0
        for node in self.ctx.calcs_ref_torun:  # usually just 1, but we leave the default.
            #print node
            i = i + 1
            if isinstance(node, StructureData):
                res = self.submit(FleurScfWorkChain,
                                  wf_parameters=wf_parameters,
                                  structure=node,
                                  inpgen=self.inputs.inpgen,
                                  fleur=self.inputs.fleur,
                                  options=options,
                                  metadata={
                                      'label': scf_label,
                                      'description': scf_desc
                                  })  #
            elif isinstance(node, FleurinpData):
                res = self.submit(FleurScfWorkChain,
                                  wf_parameters=wf_parameters,
                                  structure=node,
                                  inpgen=self.inputs.inpgen,
                                  fleur=self.inputs.fleur,
                                  options=options,
                                  metadata={
                                      'label': scf_label,
                                      'description': scf_desc
                                  })  #
            elif isinstance(node, list):
                if isinstance(node[0], StructureData) and isinstance(node[1], Dict):
                    res = self.submit(FleurScfWorkChain,
                                      wf_parameters=wf_parameters,
                                      options=options,
                                      calc_parameters=node[1],
                                      structure=node[0],
                                      inpgen=self.inputs.inpgen,
                                      fleur=self.inputs.fleur,
                                      metadata={
                                          'label': scf_label,
                                          'description': scf_desc
                                      })  #
                else:
                    self.report('WARNING: a tuple in run_ref_scf which I do not reconise: {}'.format(node))
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
        return ToContext(**calcs)  #  this is a blocking return

    def check_scf(self):
        """
        Check if ref scf was successful, or something needs to be dealt with.
        If unsuccesful abort, because makes no sense to continue.
        """
        #so far not implemented

        for i, label in enumerate(self.ctx.labels):
            calc = self.ctx[label]
            print('collect results ...')
            print(calc)
            if not calc.is_finished_ok:
                self.report('SCF workchain {} failed'.format(calc))
                print('SCF workchain {} failed'.format(calc))

    def relaxation_needed(self):
        """
        If the structures should be relaxed, check if their Forces are below a certain
        threshold, otherwise throw them in the relaxation wf.
        """
        self.report('In relaxation fleur_corehole_wc')
        if self.ctx.relax:
            # TODO check all forces of calculations
            forces_fine = True
            return bool(forces_fine)
        else:
            return False

    def relax(self):
        """
        Do structural relaxation for certain structures.
        """
        self.report('In relax fleur_corehole_wc workflow')
        self.ctx.base_structure_relax = self.ctx.base_structure
        #for calc in self.ctx.dos_to_calc:
        #    pass
        #    # TODO run relax workflow

    def run_scfs(self):
        """
        Run a scf for the all corehole calculations in parallel super cell
        """
        self.report('INFO: In run_scfs fleur_corehole_wc')
        print('INFO: In run_scfs fleur_corehole_wc')
        para = self.ctx.scf_para
        if para is None:
            wf_parameter = {}
        else:
            wf_parameter = para
        wf_parameter['serial'] = self.ctx.serial
        #wf_parameter['queue_name'] = self.ctx.queue
        #wf_parameter['custom_scheduler_commands'] = self.ctx.custom_scheduler_commands
        wf_parameters = Dict(dict=wf_parameter)
        options = Dict(dict=self.ctx.options)
        #res_all = []
        calcs = {}
        scf_label = 'corehole_wc cell'
        scf_desc = '|corehole_wc|'
        # now in parallel
        #print self.ctx.ref_calcs_torun
        i = 0  #
        self.report('Calculations to launch : {}'.format(self.ctx.calcs_torun))
        for node in self.ctx.calcs_torun:
            #print node
            i = i + 1
            if isinstance(node, StructureData):
                res = self.submit(FleurScfWorkChain,
                                  wf_parameters=wf_parameters,
                                  structure=node,
                                  inpgen=self.inputs.inpgen,
                                  fleur=self.inputs.fleur,
                                  options=options,
                                  metadata={
                                      'label': scf_label,
                                      'description': scf_desc
                                  })  #
            elif isinstance(node, FleurinpData):
                res = self.submit(FleurScfWorkChain,
                                  wf_parameters=wf_parameters,
                                  structure=node,
                                  inpgen=self.inputs.inpgen,
                                  fleur=self.inputs.fleur,
                                  options=options,
                                  metadata={
                                      'label': scf_label,
                                      'description': scf_desc
                                  })  #
            elif isinstance(node, list):
                if isinstance(node[0], StructureData) and isinstance(node[1], Dict):
                    if isinstance(node[2], Dict):
                        res = self.submit(FleurScfWorkChain,
                                          wf_parameters=node[2],
                                          calc_parameters=node[1],
                                          structure=node[0],
                                          options=options,
                                          inpgen=self.inputs.inpgen,
                                          fleur=self.inputs.fleur,
                                          metadata={
                                              'label': scf_label,
                                              'description': scf_desc
                                          })  #
            else:
                self.report('ERROR: Something in run_scfs which I do not recognize: {}'.format(node))
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
            self.to_context(**{label: res})
        self.ctx.calcs_torun = []
        #return ToContext(**calcs)

    def collect_results(self):
        """
        Collect results from certain calculation, check if everything is fine,
        calculate the wanted quantities. currently all energies are in hartree (as provided by Fleur)
        """

        # TODO: what about partial collection?
        # if some calc failed do not abort, but collect the others.
        message = ('INFO: Collecting results of fleur_corehole_wc workflow')
        self.report(message)

        all_CLS = {}
        ref_calcs = []
        ref_cl_energies = {}
        cl_energies = {}
        bindingenergies = []  # atomtype, binding eneergy
        weighted_binding_energies = []  # *(1+1- coreholecharge)
        calcs = []
        # get results from calc/scf
        #calcs = self.ctx.calcs_res
        for i, label in enumerate(self.ctx.labels):
            calc = self.ctx[label]
            #print('collect results ...')
            #print(calc)
            #if not calc.is_finished_ok:
            #    print('calculation failed')
            #    continue
            if i == 0:
                ref_calcs.append(calc)
            else:
                calcs.append(calc)

        fermi_energies, bandgaps, atomtypes, all_corelevel, total_energies = extract_results_corehole(calcs)
        ref_fermi_energies, ref_bandgaps, ref_atomtypes, ref_all_corelevel, ref_total_energies = extract_results_corehole(
            ref_calcs)

        # now calculate binding energies of the coreholes.
        # Differences of total energies
        #for number, energy in total_energies:#.iteritems():
        for energy in total_energies:  #.iteritems():
            #print ref_total_energies
            bde = energy - ref_total_energies[0]  #.get('0', 0)
            bindingenergies.append(bde)
            hole_charge = self.ctx.hole_charge
            if hole_charge != 0.0:
                weighted_binding_energy = bde * (1.0 / hole_charge)
            else:
                weighted_binding_energy = bde
            weighted_binding_energies.append(weighted_binding_energy)
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
        self.ctx.bindingenergies = bindingenergies
        self.ctx.wbindingenergies = weighted_binding_energies
        #print(bindingenergies)
        #print(weighted_binding_energies)
        #return

    def return_results(self):
        """
        return the results of the calculations
        """
        # TODO: make sure ouputnodes are always produced
        # get
        # TODO: Maybe all variables should come from the context, therefore they
        # they will be proper initialiezed and you can call return_results, on a controlled
        # abort of the wc. with all output nodes produced....

        #print('coreholes were calculated bla bla')
        # call one routine, that will set all variables in the ctx
        #cl, cls, ref_cl, efermi, gap, ref_efermi, ref_gap, at, at_ref, te, te_ref = self.collect_results()
        # check if this should be called
        if self.ctx.successful:  # TODO parse partially results...
            self.collect_results()

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['total_energy_ref'] = self.ctx.ref_total_energies
        outputnode_dict['total_energy_ref_units'] = 'eV'
        outputnode_dict['total_energy_all'] = self.ctx.total_energies
        outputnode_dict['total_energy_all_units'] = 'eV'
        outputnode_dict['binding_energy'] = self.ctx.bindingenergies
        outputnode_dict['binding_energy_units'] = 'eV'
        outputnode_dict['weighted_binding_energy'] = self.ctx.wbindingenergies  # BE for scaled hole charge 1.0
        outputnode_dict['weighted_binding_energy_units'] = 'eV'
        outputnode_dict['binding_energy_convention'] = 'negativ'
        outputnode_dict['corehole_type'] = self.ctx.method
        outputnode_dict['coreholes_calculated'] = ''  # on what atom what level basicly description of the other lists
        outputnode_dict['coreholes_calculated_details'] = ''  # the dict internally used
        #outputnode_dict['corelevel_energies'] = cl
        #outputnode_dict['reference_corelevel_energies'] = ref_cl
        outputnode_dict['fermi_energy'] = self.ctx.fermi_energies
        outputnode_dict['fermi_energy_unit'] = 'eV'
        outputnode_dict['coresetup'] = []  #cls
        outputnode_dict['reference_coresetup'] = []  #cls
        outputnode_dict['bandgap'] = self.ctx.bandgaps
        outputnode_dict['bandgap_units'] = 'eV'
        outputnode_dict['reference_bandgaps'] = self.ctx.ref_bandgaps
        outputnode_dict['atomtypes'] = self.ctx.atomtypes
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors
        outputnode_dict['hints'] = self.ctx.hints

        outputnode = Dict(dict=outputnode_dict)
        outdict = {}
        outdict['output_corehole_wc_para'] = outputnode

        # To have to ouput node linked to the calculation output nodes
        outnodedict = {}
        outnode = Dict(dict=outputnode_dict)
        outnodedict['results_node'] = outnode

        # TODO: bad design, make bullet proof.
        for i, label in enumerate(self.ctx.labels):
            calc = self.ctx[label]
            #print(calc)
            #print(calc.get_outgoing().all())
            try:
                calc_dict = calc.get_outgoing().get_node_by_label(
                    'output_scf_wc_para')  #calc.outputs.output_scf_wc_para
            except (KeyError, ValueError):
                print('continue 2')
            outnodedict[label] = calc_dict

        outdict = create_corehole_result_node(**outnodedict)

        #outdict = {}
        #outdict['output_eos_wc_para'] = ouputnode

        for k, v in six.iteritems(outdict):
            self.out(k, v)
        msg = ('INFO: fleur_corehole_wc workflow Done')
        self.report(msg)

    def control_end_wc(self, errormsg):
        """
        Controled way to shutdown the workchain.
        report errors and always initalize/produce output nodes.
        But log successful=False
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.ctx.errors.append(errormsg)
        self.report(errormsg)
        self.return_results()


@cf
def create_corehole_result_node(**kwargs):  #*args):
    """
    This is a pseudo wf, to create the rigth graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_corehole_wc_para'] = outpara.clone()
    # copy, because we rather produce the same node twice then have a circle in the database for now...
    #output_para = args[0]
    #return {'output_eos_wc_para'}
    return outdict


#                    corehole = {'site' : {'kind_name' : change_kind,#site.kind_name,
#                                          'position' : site.position},
#                               'econfig' : econfig, 'kindname' : kind,
#                               'inpxml_changes' : fleurinp_change}
@cf
def prepare_struc_corehole_wf(
    base_supercell,
    wf_para,
    para=None,
):  #, _label='prepare_struc_corehole_wf', _description='WF, used in the corehole_wc, breaks the symmetry and moves the cell, prepares the inpgen parameters for a corehole.'):
    """
    calcfunction which does all/some the structure+calcparameter manipulations together
    (therefore less nodes are produced and proverance is kept)
    wf_para: Dict node dict: {'site' : sites[8], 'kindname' : 'W1', 'econfig': "[Kr] 5s2 4d10 4f13 | 5p6 5d5 6s2", 'fleurinp_change' : []}
    """
    from aiida_fleur.tools.StructureData_util import move_atoms_incell

    #from aiida.orm.data.structure import Site

    wf_para_dict = wf_para.get_dict()
    # has to be repacked, site object is not jason serializable...
    site_info = wf_para_dict['site']
    #site = Site(kind_name=site_info['kind_name'], position=site_info['position'])
    pos = site_info['position']  #site.position
    species_name = wf_para_dict['kindname']
    broke_kn = site_info['kind_name']
    new_kinds_names = {broke_kn: [species_name]}
    #print pos
    npos = -np.array(pos)

    # break the symmetry, make corehole atoms its own species. # pos has to be tuple, unpack problem here.. #TODO rather not so nice
    inputs = dict(structure=base_supercell,
                  atoms=[],
                  site=[],
                  pos=[(pos[0], pos[1], pos[2])],
                  new_kinds_names=new_kinds_names)
    if para is not None:
        inputs['parameterdata'] = para
    new_struc, new_para = break_symmetry(**inputs)
    #kinds = new_struc.kinds
    #for kind in kinds:
    #    if kind.name == broke_kn:
    #        kind.name = species_name
    #        print('kindset?')
    # move unit cell that impurity is in 0,0,0
    moved_struc = move_atoms_incell(new_struc, npos)
    # Make sure to provide a parameter node otherwise create_corhole para won't work
    para = create_corehole_para(
        moved_struc,
        species_name,  #wf_para_dict['kindname'],
        wf_para_dict['econfig'],
        parameterdata=new_para,
        species_name=species_name)

    # return of a wf has to be dictionary of nodes...
    return {'moved_struc': moved_struc, 'hole_para': para}


def extract_results_corehole(calcs):
    """
    Collect results from certain calculation, check if everything is fine,
    calculate the wanted quantities.

    params: calcs : list of scf workchains nodes
    """
    # TODO maybe import from somewhere move to common wf

    calc_uuids = []
    for calc in calcs:
        print(calc)
        print(calc.exit_status, calc.exit_message)
        print(calc.get_outgoing().all())
        try:
            calc_uuid = calc.outputs.output_scf_wc_para.get_dict()['last_calc_uuid']
        except (KeyError, AttributeError):
            print('continue')
            continue
        if calc_uuid is not None:
            calc_uuids.append(calc_uuid)
    #print(calc_uuids)

    #all_corelevels = {}
    #fermi_energies = {}
    #bandgaps = {}
    #all_atomtypes = {}
    #all_total_energies = {}

    all_corelevels = []
    fermi_energies = []
    bandgaps = []
    all_atomtypes = []
    all_total_energies = []
    # more structures way: divide into this calc and reference calcs.
    # currently the order in calcs is given, but this might change if you submit
    # check if calculation pks belong to successful fleur calculations
    for i, uuid in enumerate(calc_uuids):
        calc = load_node(uuid)
        if not isinstance(calc, CalcJobNode):
            #raise ValueError("Calculation with pk {} must be a FleurCalculation".format(pk))
            # log and continue
            continue
        if calc.is_finished_ok:
            # get out.xml file of calculation
            #outxml = calc.outputs.retrieved.folder.get_abs_path('path/out.xml')
            outxml = calc.outputs.retrieved.open('out.xml')
            #print outxml
            try:
                corelevels, atomtypes = extract_corelevels(outxml)
            finally:
                outxml.close()
            #all_corelevels.append(core)
            #print('corelevels: {}'.format(corelevels))
            #print('atomtypes: {}'.format(atomtypes))
            #for i in range(0,len(corelevels[0][0]['corestates'])):
            #    print corelevels[0][0]['corestates'][i]['energy']

            #TODO how to store?
            efermi = calc.res.fermi_energy
            #print efermi
            bandgap = calc.res.bandgap
            total_energy = calc.res.energy
            total_energy_units = calc.res.energy_units
            #total_energy = calc.res.total_energy
            #total_energy_units = calc.res.total_energy_units

            # TODO: maybe different, because it is prob know from before
            #fleurinp = calc.inp.fleurinpdata
            #structure = fleurinp.get_structuredata(fleurinp)
            #compound = structure.get_formula()
            #print compound
            #number = '{}'.format(i)
            #fermi_energies[number] = efermi
            #bandgaps[number] = bandgap
            #all_atomtypes[number] = atomtypes
            #all_corelevels[number] = corelevels
            #all_total_energies[number] = total_energy
        else:
            # log and continue
            total_energy = 2e308  #float('nan'))
            bandgap = 2e308  #float('nan')
            efermi = 2e308  #float('nan')
            corelevels = [2e308]  #[float('nan')]
            atomtypes = [2e308]  #[float('nan')]
            #continue
            #raise ValueError("Calculation with pk {} must be in state FINISHED".format(pk))
        fermi_energies.append(efermi)
        bandgaps.append(bandgap)
        all_atomtypes.append(atomtypes)
        all_corelevels.append(corelevels)
        all_total_energies.append(total_energy)

    return fermi_energies, bandgaps, all_atomtypes, all_corelevels, all_total_energies
