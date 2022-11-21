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
In this module you find the workflow 'FleurStrainWorkChain' for the calculation of
of deformation potential
"""

import numpy as np

from aiida.plugins import DataFactory
from aiida.orm import Code, load_node
from aiida.orm import Float, StructureData, Dict
from aiida.engine import WorkChain, ToContext  # ,Outputs
from aiida.engine import calcfunction as cf

from aiida_fleur.tools.StructureData_util import rescale, rescale_nowf, is_structure
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.tools.common_fleur_wf import test_and_get_codenode
from aiida_fleur.tools.common_fleur_wf_util import check_eos_energies

from masci_tools.util.constants import HTR_TO_EV

# pylint: disable=invalid-name
FleurInpData = DataFactory('fleur.fleurinp')
# pylint: enable=invalid-name


class FleurStrainWorkChain(WorkChain):
    """
    This workflow calculates the deformation potential a structure = -BdEg/dP = d(Eg)/d(ln(V)).
    Calculates several unit cells with different volumes.
    A Birch_Murnaghan  equation of states fit determines the Bulk modulus(B) and the
    ground-state volume of the cell.

    :params wf_parameters: Dict node, optional 'wf_parameters', protocol specifying parameter dict
    :params structure: StructureData node, 'structure' crystal structure
    :params calc_parameters: Dict node, optional 'calc_parameters' parameters for inpgen
    :params inpgen: Code node,
    :params fleur: Code node,


    :return output_strain_wc_para: Dict node, contains relevant output information.
                                about general succeed, fit results and so on.
    """

    _workflowversion = '0.3.6'

    _default_options = {
        'resources': {
            'num_machines': 1
        },
        'max_wallclock_seconds': 6 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }

    _wf_default = {
        'fleur_runmax': 4,
        'density_converged': 0.02,
        'itmax_per_run': 30,
        'inpxml_changes': [],
        'points': 3,
        'step': 0.02,
        'guess': 1.00
    }

    _scf_keys = ['fleur_runmax', 'density_converged', 'itmax_per_run', 'inpxml_changes']

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('structure', valid_type=StructureData, required=True)
        spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.input('inpgen', valid_type=Code, required=True)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('options', valid_type=Dict, required=False)
        spec.input('settings', valid_type=Dict, required=False)

        spec.outline(cls.start, cls.structures, cls.converge_scf, cls.return_results)

        spec.output('output_strain_wc_para', valid_type=Dict)

        # exit codes
        spec.exit_code(331,
                       'ERROR_INVALID_CODE_PROVIDED',
                       message='Invalid code node specified, check inpgen and fleur code nodes.')

    def start(self):
        """
        check parameters, what conditions? complete?
        check input nodes
        """
        self.report(f'Started strain workflow version {self._workflowversion}')

        self.ctx.last_calc2 = None
        self.ctx.calcs = []
        self.ctx.calcs_future = []
        self.ctx.structures = []
        self.ctx.temp_calc = None
        self.ctx.structurs_uuids = []
        self.ctx.scalelist = []
        self.ctx.volume = []
        self.ctx.volume_peratom = {}
        self.ctx.org_volume = -1  # avoid div 0
        self.ctx.labels = []
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []
        # TODO get all successful from convergence, if all True this

        # initialize the dictionary using defaults if no wf parameters are given
        wf_default = self._wf_default
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        # extend wf parameters given by user using defaults
        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        self.ctx.points = wf_dict.get('points', 3)
        self.ctx.step = wf_dict.get('step', 0.02)
        self.ctx.guess = wf_dict.get('guess', 1.00)
        self.ctx.max_number_runs = wf_dict.get('fleur_runmax', 4)

        # initialize the dictionary using defaults if no options are given
        defaultoptions = self._default_options
        if 'options' in self.inputs:
            options = self.inputs.options.get_dict()
        else:
            options = defaultoptions

        # extend options given by user using defaults
        for key, val in defaultoptions.items():
            options[key] = options.get(key, val)
        self.ctx.options = options

        # Check if user gave valid inpgen and fleur executables
        inputs = self.inputs
        if 'inpgen' in inputs:
            try:
                test_and_get_codenode(inputs.inpgen, 'fleur.inpgen')
            except ValueError:
                error = ('The code you provided for inpgen of FLEUR does not use the plugin fleur.inpgen')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

        if 'fleur' in inputs:
            try:
                test_and_get_codenode(inputs.fleur, 'fleur.fleur')
            except ValueError:
                error = ('The code you provided for FLEUR does not use the plugin fleur.fleur')
                self.control_end_wc(error)
                return self.exit_codes.ERROR_INVALID_CODE_PROVIDED

    def structures(self):
        """
        Creates structure data nodes with different Volume (lattice constants)
        """
        points = self.ctx.points
        step = self.ctx.step
        guess = self.ctx.guess
        startscale = guess - (points - 1) / 2 * step

        for point in range(points):
            self.ctx.scalelist.append(startscale + point * step)

        self.report(f'scaling factors which will be calculated:{self.ctx.scalelist}')
        self.ctx.org_volume = self.inputs.structure.get_cell_volume()
        self.ctx.structurs = strain_structures(self.inputs.structure, self.ctx.scalelist)

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
            label_c = '|strain| fleur_scf_wc'
            description = f'|FleurStrainWorkChain|fleur_scf_wc|scale {label}, {i}'
            # inputs['label'] = label_c
            # inputs['description'] = description

            self.ctx.volume.append(struc.get_cell_volume())
            self.ctx.volume_peratom[label] = struc.get_cell_volume() / natoms
            self.ctx.structurs_uuids.append(struc.uuid)

            result = self.submit(FleurScfWorkChain, **inputs)
            self.ctx.labels.append(label)
            calcs[label] = result

        return ToContext(**calcs)

    def get_inputs_scf(self):
        """
        get and 'produce' the inputs for a scf-cycle
        """
        inputs = {}

        scf_wf_param = {}
        for key in self._scf_keys:
            scf_wf_param[key] = self.ctx.wf_dict.get(key)
        inputs['wf_parameters'] = scf_wf_param

        inputs['options'] = self.ctx.options

        try:
            calc_para = self.inputs.calc_parameters.get_dict()
        except AttributeError:
            calc_para = {}
        inputs['calc_parameters'] = calc_para

        inputs['inpgen'] = self.inputs.inpgen
        inputs['fleur'] = self.inputs.fleur

        inputs['options'] = Dict(inputs['options'])
        inputs['wf_parameters'] = Dict(inputs['wf_parameters'])
        inputs['calc_parameters'] = Dict(inputs['calc_parameters'])

        return inputs

    def return_results(self):
        """
        Return the results of the calculations  (scf workchains) and do a
        polynomial fit
        """
        distancelist = []
        t_energylist = []
        t_energylist_peratom = []
        bandgaplist = []
        calc_uuids = []
        vol_peratom_success = []
        natoms = len(self.inputs.structure.sites)

        for label in self.ctx.labels:
            calc = self.ctx[label]

            if not calc.is_finished_ok:
                message = f'One SCF workflow was not successful: {label}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                continue

            try:
                _ = calc.outputs.output_scf_wc_para
            except KeyError:
                message = f'One SCF workflow failed, no scf output node: {label}. I skip this one.'
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue

            outpara = calc.outputs.output_scf_wc_para.get_dict()

            t_e = outpara.get('total_energy', float('nan'))
            e_u = outpara.get('total_energy_units', 'eV')
            if e_u in ('Htr', 'htr'):
                t_e = t_e * HTR_TO_EV
            dis = outpara.get('distance_charge', float('nan'))
            dis_u = outpara.get('distance_charge_units')
            t_energylist.append(t_e)
            t_energylist_peratom.append(t_e / natoms)
            vol_peratom_success.append(self.ctx.volume_peratom[label])
            distancelist.append(dis)
            calc_uuid = calc.outputs.last_calc.remote_folder.creator.uuid
            calc_uuids.append(calc_uuid)
            bandgaplist.append(load_node(calc_uuid).res.bandgap)

        en_array = np.array(t_energylist_peratom)
        vol_array = np.array(vol_peratom_success)
        eg_array = np.array(bandgaplist)
        vol_unitcell_array = vol_array * natoms

        if len(en_array):
            volume, bulk_modulus, bulk_deriv, residuals = birch_murnaghan_fit(en_array, vol_array)
            dprime = deformation_potential(vol_unitcell_array, eg_array)

            volumes = self.ctx.volume
            gs_scale = volume * natoms / self.ctx.org_volume
            if (volume * natoms < volumes[0]) or (volume * natoms > volumes[-1]):
                warn = ('Groundstate volume was not in the scaling range.')
                hint = f'Consider rerunning around point {gs_scale}'
                self.ctx.info.append(hint)
                self.ctx.warnings.append(warn)
        else:
            volumes = None
            gs_scale = None
            residuals = None
            volume = 0
            bulk_modulus = None
            bulk_deriv = None
            dprime = None

        # if (self.inputs.structure.get_extra('local_name')):
        #     local_name=self.inputs.structure.get_extra('local_name')
        # else:
        #     local_name=''

        outputnode_dict = {}
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['material'] = self.inputs.structure.get_formula()
        outputnode_dict['kind_names'] = self.inputs.structure.get_kind_names()
        # outputnode_dict['local_name'] = local_name
        outputnode_dict['deformation_potential'] = dprime
        outputnode_dict['scaling'] = self.ctx.scalelist
        outputnode_dict['scaling_gs'] = gs_scale
        outputnode_dict['initial_structure'] = self.inputs.structure.uuid
        outputnode_dict['volume_gs'] = volume * natoms
        outputnode_dict['volumes'] = volumes
        outputnode_dict['volume_units'] = 'A^3'
        outputnode_dict['natoms'] = natoms
        outputnode_dict['total_energy'] = t_energylist
        outputnode_dict['total_energy_units'] = e_u
        outputnode_dict['bandgaps'] = bandgaplist
        outputnode_dict['structures'] = self.ctx.structurs_uuids
        outputnode_dict['calculations'] = calc_uuids
        outputnode_dict['distance_charge'] = distancelist
        outputnode_dict['distance_charge_units'] = dis_u
        outputnode_dict['nsteps'] = self.ctx.points
        # outputnode_dict['guess']= self.ctx.guess,
        outputnode_dict['stepsize'] = self.ctx.step
        outputnode_dict['residuals'] = residuals
        outputnode_dict['bulk_deriv'] = bulk_deriv
        outputnode_dict['bulk_modulus'] = bulk_modulus * 160.217733  # * echarge * 1.0e21,#GPa
        outputnode_dict['bulk_modulus_units'] = 'GPa'
        outputnode_dict['info'] = self.ctx.info
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors

        if self.ctx.successful:
            self.report('Done, Strain calculation complete')
        else:
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance.')

        outputnode_t = Dict(outputnode_dict)
        outdict = create_strain_result_node(outpara=outputnode_t)

        # create link to work-chain node
        for link_name, node in outdict.items():
            self.out(link_name, node)

    def control_end_wc(self, errormsg):
        """
        Controlled way to shut-down the work-chain. It will initialize the output nodes
        The shut-down of the work-chain will has to be done afterwards
        """
        self.ctx.successful = False
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_strain_result_node(**kwargs):
    """
    Pseudo wf, to create the right graph structure of AiiDA.
    This work function will create the output node in the database.
    It also connects the output_node to all nodes the information comes from.
    """
    for key, val in kwargs.items():
        if key == 'outpara':
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_strain_wc_para'
    outputnode.description = ('Contains results and information of a FleurStrainWorkChain run.')
    outdict['output_strain_wc_para'] = outputnode

    return outdict


def strain_structures(inp_structure, scalelist):
    """
    Creates many re-scaled StructureData nodes out of a crystal structure.
    Keeps the provenance in the database.

    :param StructureData, a StructureData node (pk, sor uuid)
    :param scale-list, list of floats, scaling factors for the cell

    :returns: list of New StructureData nodes with rescalled structure, which are linked to input
              Structure
    """
    structure = is_structure(inp_structure)
    if not structure:
        # TODO: log something (test if it gets here at all)
        return None
    re_structures = []

    for scale in scalelist:
        structure_rescaled = rescale(structure, Float(scale))  # this is a wf
        re_structures.append(structure_rescaled)

    return re_structures


# pylint: disable=invalid-name
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
    fitdata = np.polyfit(volumes[:]**(-2. / 3.), energies[:], 3, full=True)
    ssr = fitdata[1]
    sst = np.sum((energies[:] - np.average(energies[:]))**2.)

    residuals0 = ssr / sst
    deriv0 = np.poly1d(fitdata[0])
    deriv1 = np.polyder(deriv0, 1)
    deriv2 = np.polyder(deriv1, 1)
    deriv3 = np.polyder(deriv2, 1)

    volume0 = 0
    x = 0
    for x in np.roots(deriv1):
        if x > 0 and deriv2(x) > 0:
            volume0 = x**(-3. / 2.)
            break

    if volume0 == 0:
        print('Error: No minimum could be found')
        return None

    derivV2 = 4. / 9. * x**5. * deriv2(x)
    derivV3 = (-20. / 9. * x**(13. / 2.) * deriv2(x) - 8. / 27. * x**(15. / 2.) * deriv3(x))
    bulk_modulus0 = derivV2 / x**(3. / 2.)
    bulk_deriv0 = -1 - x**(-3. / 2.) * derivV3 / derivV2

    return volume0, bulk_modulus0, bulk_deriv0, residuals0


def deformation_potential(volume, bandgap):
    """Calculate the deformation potential"""
    xs = np.log(volume)
    ys = bandgap
    dprime = (((np.mean(xs) * np.mean(ys)) - np.mean(xs * ys)) / ((np.mean(xs)**2) - np.mean(xs**2)))
    return dprime
