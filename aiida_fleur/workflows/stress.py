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
This is the workflow 'stress' for the Fleur code, which calculates a
stress-tensor
"""
import copy
from lxml import etree
import numpy as np

from aiida.orm import Code, Dict, RemoteData, KpointsData
from aiida.orm import load_node, FolderData, BandsData, XyData
from aiida.engine import WorkChain, ToContext, if_
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent
from aiida.common import AttributeDict
from aiida.tools.data.array.kpoints import get_explicit_kpoints_path

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier
from aiida_fleur.tools.common_fleur_wf import get_inputs_fleur
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.data.fleurinp import FleurinpData, get_fleurinp_from_remote_data


class FleurStressWorkChain(WorkChain):
    '''
    This workflow calculated a bandstructure from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior
    '''
    # wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    # defaults : tria = True, nkpts = 800, sigma=0.005, emin= , emax =

    _workflowversion = '0.0.1'

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }
    _default_wf_para = {
        'add_comp_para': {
            'only_even_MPI': False,
            'max_queue_nodes': 20,
            'max_queue_wallclock_sec': 86400
        },
        'inpxml_changes': [],
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('inpgen', valid_type=Code, required=True)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('structure', valid_type=StructureData, required=False)
        spec.input('options', valid_type=Dict, required=False)

        spec.outline(cls.start,
                     cls.create_configs,
                     cls.run_fleur_undistorted,
                     cls.run_fleur,
                     cls.return_results)

        #Output still has to be created
        spec.output('output_banddos_wc_para', valid_type=Dict)
        spec.expose_outputs(FleurBaseWorkChain, namespace='banddos_calc')
        spec.output('output_banddos_wc_bands', valid_type=BandsData, required=False)
        spec.output('output_banddos_wc_dos', valid_type=XyData, required=False)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        spec.exit_code(233,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')
        spec.exit_code(235, 'ERROR_CHANGING_FLEURINPUT_FAILED', message='Input file modification failed.')
        spec.exit_code(236, 'ERROR_INVALID_INPUT_FILE', message="Input file was corrupted after user's modifications.")
        spec.exit_code(334, 'ERROR_SCF_CALCULATION_FAILED', message='SCF calculation failed.')
        spec.exit_code(335, 'ERROR_SCF_CALCULATION_NOREMOTE', message='Found no SCF calculation remote repository.')

    def start(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        self.report(f'started stress workflow version {self._workflowversion}')
        #print("Workchain node identifiers: ")#'{}'
        #"".format(ProcessRegistry().current_calc_node))

        self.ctx.successful = False
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        inputs = self.inputs

        wf_default = copy.deepcopy(self._default_wf_para)
        if 'wf_parameters' in inputs:
            wf_dict = inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        extra_keys = []
        for key in self.ctx.wf_dict.keys():
            if key not in wf_default.keys():
                extra_keys.append(key)
        if extra_keys:
            error = f'ERROR: input wf_parameters for Stress contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        defaultoptions = self._default_options
        if 'options' in inputs:
            options = inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        try:
            test_and_get_codenode(inputs.fleur, 'fleur.fleur')
        except ValueError:
            error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        try:
            test_and_get_codenode(inputs.inpgen, 'fleur.inpgen')
        except ValueError:
            error = 'The code you provided for INPGEN does not use the plugin fleur.inpgen'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_CODE_PROVIDED


        if 'structure' in inputs and 'fleurinp' in inputs:
            error = 'ERROR: you gave struture input + fleurinp for the Stress calculation'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        if not ('structure' in inputs or 'fleurinp' in inputs):
            error = 'ERROR: you neither struture input + fleurinp for the Stress calculation'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        
        self.ctx.inpgen_needed='structure' in inputs


    def run_fleur_undistorted(self):
        label = 'bansddos_calculation'
        description = 'Bandstructure or DOS is calculated for the given structure'

        code = self.inputs.fleur
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_fleur(code,
                                            remote,
                                            fleurin,
                                            options,
                                            label,
                                            description,
                                            settings,
                                            add_comp_para=self.ctx.wf_dict['add_comp_para'])
        future = self.submit(FleurSCFWorkChain, **inputs_builder)
        return ToContext(undistored=future)


    def run_fleur(self):

        calc = self.ctx.undistored

        if not calc.is_finished_ok:
            message = ('The undistored SCF calculation was not successful.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        try:
            outpara_node = calc.outputs.output_scf_wc_para
        except NotExistent:
            message = ('The undistored SCF calculation failed, no scf output node.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        code = self.inputs.fleur
        options = self.ctx.options.copy()
        remote=calc.outputs.remote
        settings=self.ctx.settings

        self.ctx.distored=[]

        for i,fi in enumerate(self.ctx.inp_data):
            label = f'distored_calculation{i}'
            self.ctx.distored.append(label)
            description = 'Description '
            inputs_builder = get_inputs_fleur(code,
                                            remote,
                                            fi,
                                            options,
                                            label,
                                            description,
                                            settings,
                                            add_comp_para=self.ctx.wf_dict['add_comp_para'])
            future = self.submit(FleurSCFWorkChain, **inputs_builder)
            self.ToContext(**{label: future})


    def change_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
      
        if self.ctx.inpgen_needed:


            
            try:
                fleurin = self.ctx.scf.outputs.fleurinp
            except NotExistent:
                error = 'Fleurinp generated in the SCF calculation is not found.'
                self.control_end_wc(error)
                return self.exit_codes.ERROR_SCF_CALCULATION_FAILED
        else:
            if 'fleurinp' not in self.inputs:
                fleurin = get_fleurinp_from_remote_data(self.inputs.remote)
            else:
                fleurin = self.inputs.fleurinp

        # how can the user say he want to use the given kpoint mesh, ZZ nkpts : False/0
        fleurmode = FleurinpModifier(fleurin)

        fchanges = wf_dict.get('inpxml_changes', [])
        # apply further user dependend changes
        if fchanges:
            try:
                fleurmode.add_task_list(fchanges)
            except (ValueError, TypeError) as exc:
                error = ('ERROR: Changing the inp.xml file failed. Tried to apply inpxml_changes'
                         f', which failed with {exc}. I abort, good luck next time!')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        kpath = wf_dict['kpath']
        explicit = wf_dict['kpoints_explicit']
        distance = wf_dict['kpoints_distance']
        nkpts = wf_dict['kpoints_number']
        listname = wf_dict['klistname']

        if explicit is not None:
            try:
                fleurmode.set_kpointlist(**explicit)
            except (ValueError, TypeError) as exc:
                error = ('ERROR: Changing the inp.xml file failed. Tried to apply kpoints_explicit'
                         f', which failed with {exc}. I abort, good luck next time!')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        if listname is None and wf_dict['mode'] == 'band':
            listname = 'path-2'

        if nkpts is None and distance is None:
            nkpts = 500

        if 'kpoints' in self.inputs:
            kpoint_type = 'path' if wf_dict['mode'] == 'band' else 'mesh'
            fleurmode.set_kpointsdata(self.inputs.kpoints, switch=True, kpoint_type=kpoint_type)
        elif kpath == 'auto':
            if fleurin.inp_version >= '0.32' and listname is not None:
                fleurmode.switch_kpointset(listname)
        elif isinstance(kpath, dict):
            if fleurin.inp_version < '0.32':
                if distance is not None:
                    raise ValueError('set_kpath only supports specifying the number of points for the kpoints')
                fleurmode.set_kpath(kpath, nkpts)
            else:
                raise ValueError('set_kpath is only supported for inputs up to Max4')
        elif kpath == 'seek':
            #Use aiida functionality
            struc = fleurin.get_structuredata_ncf()

            if distance is not None:
                output = get_explicit_kpoints_path(struc, reference_distance=distance)
            else:
                output = get_explicit_kpoints_path(struc)
            primitive_struc = output['primitive_structure']

            #check if primitive_structure and input structure are identical:
            maxdiff_cell = sum(abs(np.array(primitive_struc.cell) - np.array(struc.cell))).max()

            if maxdiff_cell > 3e-9:
                self.report(f'Error in cell : {maxdiff_cell}')
                self.report(
                    'WARNING: The structure data from the fleurinp is not the primitive structure type, which is mandatory in some cases'
                )

            output['explicit_kpoints'].store()

            fleurmode.set_kpointsdata(output['explicit_kpoints'], switch=True)

        elif kpath == 'skip':
            pass
        else:
            #Use ase
            struc = fleurin.get_structuredata_ncf()

            path = bandpath(kpath, cell=struc.cell, npoints=nkpts, density=distance)

            special_points = path.special_points

            labels = []
            for label, special_kpoint in special_points.items():
                for index, kpoint in enumerate(path.kpts):
                    if sum(abs(np.array(special_kpoint) - np.array(kpoint))).max() < 1e-12:
                        labels.append((index, label))
            labels = sorted(labels, key=lambda x: x[0])

            kpts = KpointsData()
            kpts.set_cell(struc.cell)
            kpts.pbc = struc.pbc
            weights = np.ones(len(path.kpts)) / len(path.kpts)
            kpts.set_kpoints(kpoints=path.kpts, cartesian=False, weights=weights, labels=labels)

            kpts.store()
            fleurmode.set_kpointsdata(kpts, switch=True)

        sigma = wf_dict['sigma']
        emin = wf_dict['emin']
        emax = wf_dict['emax']

        if fleurin.inp_version < '0.32' and wf_dict['mode'] == 'dos':
            fleurmode.set_inpchanges({'ndir': -1})

        if wf_dict['mode'] == 'dos':
            change_dict = {'dos': True, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}
        else:
            change_dict = {'band': True, 'minEnergy': emin, 'maxEnergy': emax, 'sigma': sigma}
        fleurmode.set_inpchanges(change_dict)

        try:
            fleurmode.show(display=False, validate=True)
        except etree.DocumentInvalid:
            error = ('ERROR: input, user wanted inp.xml changes did not validate')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_INVALID_INPUT_FILE
        except ValueError as exc:
            error = ('ERROR: input, user wanted inp.xml changes could not be applied.'
                     f'The following error was raised {exc}')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        fleurinp_new = fleurmode.freeze()
        self.ctx.fleurinp_banddos = fleurinp_new

    def scf_needed(self):
        """
        Returns True if SCF WC is needed.
        """
        return self.ctx.scf_needed

    def converge_scf(self):
        """
        Converge charge density.
        """
        inputs = self.get_inputs_scf()
        res = self.submit(FleurScfWorkChain, **inputs)
        return ToContext(scf=res)

 

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        self.report('Stress workflow Done')
        energies=[]
        output_nodes={}
        failed=False
        for label in self.ctx.distored
            try:  # if something failed, we still might be able to retrieve something      
                energies.append(self.ctx[label].output_scf_wc_para["total_energy"])
                output_nodes[label]=self.ctx[label].output_scf_wc_para
            except (NotExistent, AttributeError):
                self.report(f'SCF WF failed: {label} {self.ctx[label].pk}')
                failed=True

        if failed:
            error = ('ERROR: Text falsch Changing the inp.xml file failed. Tried to apply inpxml_changes'
                         f', which failed with {exc}. I abort, good luck next time!')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        tensor=calc_tensor(energies,self.ctx.h_delta)

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['Warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['tensor'] = tensor
        
        outputnode_dict['tensor_units'] = 'tensor_a.u.'

        outputnode_t = Dict(outputnode_dict)
        outdict = create_band_result_node(outpara=outputnode_t,**output_nodes)

        
        
        self.out("output_stress_wc_para",outputnode_t )
        
    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_stress_result_node(outpara, **kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """

    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_stress_wc_para'
    outputnode.description = ('Contains stress-temsor calculation results')

    outdict['output_stress_wc_para'] = outputnode

    return outdict



def create_inps():

    from aiida_fleur.data.fleurinp import



    fi.get_structuredata() #AiiDA structure data

    xmltree, schema_dict = fi.load_inpxml() #XML data

    from masci_tools.util.xml.xml_getters import get_cell, get_fleur_modes, get_structuredata


    c,pbc =get_cell(xmltree, schema_dict) #3x3 array 3-vec for boundary cond

    from masci_tools.util.schema_dict_util import evaluate_text

    relpos = evaluate_text(xmltree, schema_dict, 'relPos')


    atoms, cell, pbc = get_structuredata(xmltree, schema_dict, convert_to_angstroem=False)

    relative_pos = [np.array(site.position) @ np.linalg.inv(cell) for site in atoms]

    film = not all(pbc)
    #modify cell

    from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

    fm = FleurinpModifier(fi)


    fm.set_first_text('row-1',c[0,:], contains='cell/bulk')
    fm.set_first_text('row-2',c[1,:], contains='bulk')
    fm.set_first_text('row-3',c[2,:], contains='bulk')
    new_fi = fm.freeze()
