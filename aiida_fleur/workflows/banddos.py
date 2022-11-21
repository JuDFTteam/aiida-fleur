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
import copy
from lxml import etree
from ase.dft.kpoints import bandpath
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


class FleurBandDosWorkChain(WorkChain):
    '''
    This workflow calculated a bandstructure from a Fleur calculation

    :Params: a Fleurcalculation node
    :returns: Success, last result node, list with convergence behavior
    '''
    # wf_parameters: {  'tria', 'nkpts', 'sigma', 'emin', 'emax'}
    # defaults : tria = True, nkpts = 800, sigma=0.005, emin= , emax =

    _workflowversion = '0.7.0'

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
        'kpath': 'auto',  #seek (aiida), fleur (only Max4) or string to pass to ase
        'mode': 'band',
        'klistname': None,
        'kpoints_number': None,
        'kpoints_distance': None,
        'kpoints_explicit': None,  #dictionary containing a list of kpoints, weights
        #and additional arguments to pass to set_kpointlist
        'sigma': 0.005,
        'emin': -0.50,
        'emax': 0.90,
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
        spec.expose_inputs(FleurScfWorkChain,
                           namespace_options={
                               'required': False,
                               'populate_defaults': False
                           },
                           namespace='scf')
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('kpoints', valid_type=KpointsData, required=False)
        spec.input('options', valid_type=Dict, required=False)

        spec.outline(cls.start,
                     if_(cls.scf_needed)(
                         cls.converge_scf,
                         cls.banddos_after_scf,
                     ).else_(
                         cls.banddos_wo_scf,
                     ), cls.return_results)

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
        self.report(f'started bandsdos workflow version {self._workflowversion}')
        #print("Workchain node identifiers: ")#'{}'
        #"".format(ProcessRegistry().current_calc_node))

        self.ctx.scf_needed = False
        self.ctx.banddos_calc = None
        self.ctx.fleurinp_banddos = None
        self.ctx.scf = None
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
            error = f'ERROR: input wf_parameters for Banddos contains extra keys: {extra_keys}'
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

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur')
            except ValueError:
                error = 'The code you provided for FLEUR does not use the plugin fleur.fleur'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'scf' in inputs:
            self.ctx.scf_needed = True
            if 'remote' in inputs:
                error = 'ERROR: you gave SCF input + remote for the BandDOS calculation'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
            if 'fleurinp' in inputs:
                error = 'ERROR: you gave SCF input + fleurinp for the BandDOS calculation'
                self.report(error)
                return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        elif 'remote' not in inputs:
            error = 'ERROR: you gave neither SCF input nor remote'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_CONFIG
        else:
            self.ctx.scf_needed = False

        if wf_dict['mode'] == 'dos' and wf_dict['kpath'] not in ('auto', 'skip'):
            error = 'ERROR: you specified the DOS mode but provided a non default kpath argument'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if wf_dict['kpoints_number'] is not None and wf_dict['kpoints_distance'] is not None:
            error = 'ERROR: Only provide either the distance or number for the kpoints'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def change_fleurinp(self):
        """
        create a new fleurinp from the old with certain parameters
        """
        # TODO allow change of kpoint mesh?, tria?
        wf_dict = self.ctx.wf_dict

        if self.ctx.scf_needed:
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

    def banddos_after_scf(self):
        """
        This method submits the BandDOS calculation after the initial SCF calculation
        """
        calc = self.ctx.scf

        if not calc.is_finished_ok:
            message = ('The SCF calculation was not successful.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        try:
            outpara_node = calc.outputs.output_scf_wc_para
        except NotExistent:
            message = ('The SCF calculation failed, no scf output node.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        outpara = outpara_node.get_dict()

        if 'total_energy' not in outpara:
            message = ('Did not manage to extract float total energy from the SCF calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_FAILED

        self.report('INFO: run BandDOS calculation')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp_banddos
        if fleurin is None:
            error = ('ERROR: Creating BandDOS Fleurinp failed for an unknown reason')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder of the reference calculation
        pk_last = 0
        scf_ref_node = load_node(calc.pk)
        for i in scf_ref_node.called:
            if i.node_type == 'process.workflow.workchain.WorkChainNode.':
                if i.process_class is FleurBaseWorkChain:
                    if pk_last < i.pk:
                        pk_last = i.pk
        try:
            remote = load_node(pk_last).outputs.remote_folder
        except AttributeError:
            message = ('Found no remote folder of the reference scf calculation.')
            self.control_end_wc(message)
            return self.exit_codes.ERROR_SCF_CALCULATION_NOREMOTE

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
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(banddos_calc=future)

    def banddos_wo_scf(self):
        """
        This method submits the BandDOS calculation without a previous SCF calculation
        """
        self.report('INFO: run BandDOS calculation')

        status = self.change_fleurinp()
        if status:
            return status

        fleurin = self.ctx.fleurinp_banddos
        if fleurin is None:
            error = ('ERROR: Creating BandDOS Fleurinp failed for an unknown reason')
            self.control_end_wc(error)
            return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED

        # Do not copy mixing_history* files from the parent
        settings = {'remove_from_remotecopy_list': ['mixing_history*']}

        # Retrieve remote folder from the inputs
        remote = self.inputs.remote

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
        future = self.submit(FleurBaseWorkChain, **inputs_builder)
        return ToContext(banddos_calc=future)

    def get_inputs_scf(self):
        """
        Initialize inputs for scf workflow:
        wf_param, options, calculation parameters, codes, structure
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
        return input_scf

    def return_results(self):
        '''
        return the results of the calculations
        '''
        # TODO more here
        self.report('BandDOS workflow Done')

        if self.ctx.banddos_calc:
            self.report(f'A bandstructure/DOS was calculated and is found under pk={self.ctx.banddos_calc.pk}, '
                        f'calculation {self.ctx.banddos_calc}')

        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.banddos_calc.outputs.output_parameters
            retrieved = self.ctx.banddos_calc.outputs.retrieved
            if 'fleurinp' in self.ctx.banddos_calc.inputs:
                fleurinp = self.ctx.banddos_calc.inputs.fleurinp
            else:
                fleurinp = get_fleurinp_from_remote_data(self.ctx.banddos_calc.inputs.parent_folder)
            last_calc_out_dict = last_calc_out.get_dict()
        except (NotExistent, AttributeError):
            last_calc_out = None
            last_calc_out_dict = {}
            retrieved = None
            fleurinp = None

        #check if band file exists: if not succesful = False
        #TODO be careful with general bands.X
        bandfiles = ['bands.1', 'bands.2', 'banddos.hdf', 'Local.1', 'Local.2']

        bandfile_res = []
        if retrieved:
            bandfile_res = retrieved.list_object_names()

        for name in bandfiles:
            if name in bandfile_res:
                self.ctx.successful = True
        if not self.ctx.successful:
            self.report('!NO bandstructure/DOS file was found, something went wrong!')

        # # get efermi from last calculation
        scf_results = None
        efermi_scf = 0
        bandgap_scf = 0
        if 'remote' in self.inputs:
            scf_results = self.inputs.remote.creator.res
        elif 'scf' in self.inputs:
            if self.ctx.scf and self.ctx.scf.is_finished_ok:
                scf_results = self.ctx.scf.outputs.last_calc.output_parameters.dict

        if scf_results is not None:
            efermi_scf = scf_results.fermi_energy
            bandgap_scf = scf_results.bandgap

        efermi_band = last_calc_out_dict.get('fermi_energy', None)
        bandgap_band = last_calc_out_dict.get('bandgap', None)

        diff_efermi = None
        if efermi_band is not None:
            diff_efermi = efermi_scf - efermi_band

        diff_bandgap = None
        if bandgap_band is not None:
            diff_bandgap = bandgap_scf - bandgap_band

        outputnode_dict = {}

        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['Warnings'] = self.ctx.warnings
        outputnode_dict['successful'] = self.ctx.successful
        outputnode_dict['mode'] = self.ctx.wf_dict.get('mode')
        outputnode_dict['fermi_energy_band'] = efermi_band
        outputnode_dict['bandgap_band'] = bandgap_band
        outputnode_dict['fermi_energy_scf'] = efermi_scf
        outputnode_dict['bandgap_scf'] = bandgap_scf
        outputnode_dict['diff_efermi'] = diff_efermi
        outputnode_dict['diff_bandgap'] = diff_bandgap
        outputnode_dict['bandgap_units'] = 'eV'
        outputnode_dict['fermi_energy_units'] = 'Htr'

        outputnode_t = Dict(outputnode_dict)
        if last_calc_out:
            outdict = create_band_result_node(outpara=outputnode_t,
                                              last_calc_out=last_calc_out,
                                              last_calc_retrieved=retrieved)

            if self.ctx.wf_dict.get('mode') == 'band' and fleurinp is not None and retrieved is not None:
                bands = create_aiida_bands_data(fleurinp=fleurinp, retrieved=retrieved)
                if isinstance(bands, BandsData):
                    outdict['output_banddos_wc_bands'] = bands
            elif self.ctx.wf_dict.get('mode') == 'dos' and retrieved is not None:
                dos = create_aiida_dos_data(retrieved=retrieved)
                if isinstance(dos, XyData):
                    outdict['output_banddos_wc_dos'] = dos

        else:
            outdict = create_band_result_node(outpara=outputnode_t)

        if self.ctx.banddos_calc:
            self.out_many(self.exposed_outputs(self.ctx.banddos_calc, FleurBaseWorkChain, namespace='banddos_calc'))

        #TODO parse Bandstructure
        for link_name, node in outdict.items():
            self.out(link_name, node)

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_band_result_node(**kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in kwargs.items():
        if key == 'outpara':  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_banddos_wc_para'
    outputnode.description = ('Contains band calculation results')

    outdict['output_banddos_wc_para'] = outputnode

    return outdict


@cf
def create_aiida_bands_data(fleurinp, retrieved):
    """
    Creates :py:class:`aiida.orm.BandsData` object containing the kpoints and eigenvalues
    from the `banddos.hdf` file of the calculation

    :param fleurinp: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` for the calculation
    :param retrieved: :py:class:`aiida.orm.FolderData` for the bandstructure calculation

    :returns: :py:class:`aiida.orm.BandsData` for the bandstructure calculation

    :raises: ExitCode 300, banddos.hdf file is missing
    :raises: ExitCode 310, banddos.hdf reading failed
    :raises: ExitCode 320, reading kpointsdata from Fleurinp failed
    """
    from masci_tools.io.parsers.hdf5 import HDF5Reader, HDF5TransformationError
    from masci_tools.io.parsers.hdf5.recipes import FleurSimpleBands  #no projections only eigenvalues for now
    from aiida.engine import ExitCode

    try:
        kpoints = fleurinp.get_kpointsdata_ncf(only_used=True)
    except ValueError as exc:
        return ExitCode(320, message=f'Retrieving kpoints data from fleurinp failed with: {exc}')

    if 'banddos.hdf' in retrieved.list_object_names():
        try:
            with retrieved.open('banddos.hdf', 'rb') as f:
                with HDF5Reader(f) as reader:
                    data, attributes = reader.read(recipe=FleurSimpleBands)
        except (HDF5TransformationError, ValueError) as exc:
            return ExitCode(310, message=f'banddos.hdf reading failed with: {exc}')
    else:
        return ExitCode(300, message='banddos.hdf file not in the retrieved files')

    bands = BandsData()
    bands.set_kpointsdata(kpoints)

    nkpts, nbands = attributes['nkpts'], attributes['nbands']
    eigenvalues = data['eigenvalues_up'].reshape((nkpts, nbands))
    if 'eigenvalues_down' in data:
        eigenvalues_dn = data['eigenvalues_down'].reshape((nkpts, nbands))
        eigenvalues = [eigenvalues, eigenvalues_dn]

    bands.set_bands(eigenvalues, units='eV')

    bands.label = 'output_banddos_wc_bands'
    bands.description = ('Contains BandsData for the bandstructure calculation')

    return bands


@cf
def create_aiida_dos_data(retrieved):
    """
    Creates :py:class:`aiida.orm.XyData` object containing the standard DOS components
    from the `banddos.hdf` file of the calculation

    :param retrieved: :py:class:`aiida.orm.FolderData` for the DOS calculation

    :returns: :py:class:`aiida.orm.XyData` containing all standard DOS components

    :raises: ExitCode 300, banddos.hdf file is missing
    :raises: ExitCode 310, banddos.hdf reading failed
    """
    from masci_tools.io.parsers.hdf5 import HDF5Reader, HDF5TransformationError
    from masci_tools.io.parsers.hdf5.recipes import FleurDOS  #only standard DOS for now
    from aiida.engine import ExitCode

    if 'banddos.hdf' in retrieved.list_object_names():
        try:
            with retrieved.open('banddos.hdf', 'rb') as f:
                with HDF5Reader(f) as reader:
                    data, attributes = reader.read(recipe=FleurDOS)
        except (HDF5TransformationError, ValueError) as exc:
            return ExitCode(310, message=f'banddos.hdf reading failed with: {exc}')
    else:
        return ExitCode(300, message='banddos.hdf file not in the retrieved files')

    dos = XyData()
    dos.set_x(data['energy_grid'], 'energy', x_units='eV')

    names = [key for key in data if key != 'energy_grid']
    arrays = [entry for key, entry in data.items() if key != 'energy_grid']
    units = ['1/eV'] * len(names)
    dos.set_y(arrays, names, y_units=units)

    dos.label = 'output_banddos_wc_dos'
    dos.description = (
        'Contains XyData for the density of states calculation with total, interstitial, atom and orbital weights')

    return dos
