"""
Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
               All rights reserved.                                         #
This file is part of the AiiDA-FLEUR package.                               #
                                                                            #
The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
For further information on the license, see the LICENSE.txt file            #
For further information please visit http://www.flapw.de or                 #
http://aiida-fleur.readthedocs.io/en/develop/                               #
##############################################################################
"""
"""
In this module you find the workflow 'FleurStressWorkChain' for the calculation of
of an equation of state
"""
# TODO: print more user info
# allow different inputs, make things optional(don't know yet how)
# half number of iteration if you are close to be converged. (therefore
# one can start with 18 iterations, and if thats not enough run again 9 or something)
import numpy as np

from aiida import orm
from aiida.orm import load_node
from aiida.orm import Float, StructureData, Dict, List
from aiida.engine import WorkChain, ToContext
from aiida.engine import calcfunction as cf
from aiida.common import AttributeDict
from masci_tools.util.constants import HTR_TO_EV
from aiida_fleur.data.fleurinp import FleurinpData
from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

from aiida_fleur.tools.StructureData_util import rescale, rescale_nowf, is_structure
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.tools.common_fleur_wf_util import check_eos_energies


class FleurStressWorkChain(WorkChain):
    """
    This workflow calculates the equation of states of a structure.
    Calculates several unit cells with different volumes.
    A Birch_Murnaghan  equation of states fit determines the Bulk modulus and the
    groundstate volume of the cell.

    :params wf_parameters: Dict node, optional 'wf_parameters', protocol specifying parameter dict
    :params structure: StructureData node, 'structure' crystal structure
    :params calc_parameters: Dict node, optional 'calc_parameters' parameters for inpgen
    :params inpgen: Code node,
    :params fleur: Code node,


    :return output_stress_wc_para: Dict node, contains relevant output information.
                                about general succeed, fit results and so on.
    """

    _workflowversion = '0.6.0'

    # _default_wf_para = {'points': 9, 'step': 0.005, 'guess': 1.00, 'enforce_same_para': True}
    _default_wf_para = {'scale': 0.01, 'enforce_same_para': True}
    _default_options = FleurScfWorkChain._default_options

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf', exclude=(
            'structure',
            'remote_data',
            'fleurinp',
        ))
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('structure', valid_type=StructureData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)

        spec.outline(
            cls.start,
            cls.structures,
            cls.run_first,
            cls.inspect_first, 
            cls.converge_scf,        
            cls.return_results
        )
        spec.output('output_stress_wc_para', valid_type=Dict)
        spec.output('output_stress_wc_structure', valid_type=StructureData, required=False)
        #new output with dynamic
        spec.output_namespace('structures', valid_type=StructureData, dynamic=True)

        # exit codes
        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(400,
                       'ERROR_SUB_PROCESS_FAILED',
                       message='At least one of the SCF sub processes did not finish successfully.')

    def start(self):
        """
        check parameters, what condictions? complete?
        check input nodes
        """
        self.report(f'Started stress workflow version {self._workflowversion}')

        self.ctx.last_calc2 = None
        self.ctx.calcs = []
        self.ctx.calcs_future = []
        self.ctx.structures = []
        self.ctx.temp_calc = None
        self.ctx.structures_uuids = []
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

        # initialize the dictionary using defaults if no wf paramters are given
        wf_default = self._default_wf_para
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        extra_keys = []
        for key in wf_dict:
            if key not in wf_default:
                extra_keys.append(key)
        if extra_keys:
            error = f'ERROR: input wf_parameters for stress contains extra keys: {extra_keys}'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        # extend wf parameters given by user using defaults
        for key, val in wf_default.items():
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        # self.ctx.points = wf_dict.get('points', 9)
        # self.ctx.step = wf_dict.get('step', 0.005)
        # self.ctx.guess = wf_dict.get('guess', 1.00)
        self.ctx.scale = wf_dict.get('scale', 0.01)
        
        self.ctx.enforce_para = wf_dict.get('enforce_same_para', True)


    def structures(self):
        #------------------------------------------------------------------
        #------------------------------------------------------------------
        # BUILDING STRESS TENSOR
        # volume preserving
        """
        Creates structure data nodes for all 6 independent strain components
        (xx, yy, zz, yz, xz, xy), each with +/- delta -> 12 configs + reference.
        """
        delta = float(self.ctx.scale)
        
        def deform_matrix(eta):
            I = np.eye(3)
            F = I + np.array(eta)
            detF = np.linalg.det(F)
            F_exact = F / detF**(1.0 / 3.0)
            return tuple(tuple(row) for row in F_exact)
        
        voigt_labels = ['xx', 'yy', 'zz', 'yz', 'xz', 'xy'] 
        
        self.ctx.strains = [
            ("ref", ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
        ]
        
        for i, label in enumerate(voigt_labels):
            for sign, tag in [(+1, 'plus'), (-1, 'minus')]:
                e = [0.0] * 6
                strain_val = sign * delta
                e[i] = strain_val
        
                # Construct the 3x3 symmetric strain tensor
                eta = np.array([
                    [e[0],      e[5] / 2.0, e[4] / 2.0],
                    [e[5] / 2.0, e[1],      e[3] / 2.0],
                    [e[4] / 2.0, e[3] / 2.0, e[2]      ],
                ])
        
                self.ctx.strains.append((f"{label}_{tag}", deform_matrix(eta)))
        # #------------------------------------------------------------------
        # # #------------------------------------------------------------------
        
        # below should always there
        self.ctx.scalelist = [s[1] for s in self.ctx.strains]
        self.ctx.labels = [s[0] for s in self.ctx.strains]

        self.report(f'Scaling factors: {self.ctx.scalelist}')
        self.report(f'Labels: {self.ctx.labels}')

        if 'structure' in self.inputs:
            structure = self.inputs.structure
            self.ctx.org_volume = structure.get_cell_volume()
            
            strain_dict = {label: vals for label, vals in self.ctx.strains}
            
            strained_structures = apply_strain_structures(
                structure,
                Dict(dict=strain_dict)
                )
            
            for label in self.ctx.labels:
                new_struct = strained_structures[label]
                self.ctx.structures.append(new_struct)
                self.out(f"structures.{label}", new_struct)
                
        else:
            self.report("No input structure found")
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        self.report(f'Created {len(self.ctx.structures)} strained structures.')
                
    def run_first(self):
        """
        Launch the first fleur SCF workchain
        """
        calcs = {}

        i = 0
        struc_or_fleurinp = self.ctx.structures[i]
        inputs = self.get_inputs_scf_first()
        if isinstance(struc_or_fleurinp,FleurinpData):
            inputs.fleurinp=struc_or_fleurinp
            struc=struc_or_fleurinp.get_structuredata_ncf()
        else:    
            inputs.structure = struc_or_fleurinp
            struc=inputs.structure
        natoms = len(struc.sites)

        label = self.ctx.labels[i]
        # label = f'scale_{self.ctx.scalelist[i]}'.replace('.', '_')
        
        label_c = '|stress| fleur_scf_wc'
        description = f'|FleurStressWorkChain|fleur_scf_wc|{label}, {i}'

        self.ctx.volume.append(struc.get_cell_volume())
        self.ctx.volume_peratom[label] = struc.get_cell_volume() / natoms
        self.ctx.structures_uuids.append(struc.uuid)

        result = self.submit(FleurScfWorkChain, **inputs)
        # self.ctx.labels.append(label) 
        calcs[label] = result

        return ToContext(**calcs)

    def inspect_first(self):
        """
        Check if the first calculation failed and capture its generated inputs.
        """
        label = self.ctx.labels[0]
        first_scf = self.ctx[label]
    
        if not first_scf.is_finished_ok:
            self.report('Initial sub process did not finish successfully; aborting the workchain.')
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED
    
        # Store the output fleurinp data containing the dynamically generated parameters
        self.ctx.first_fleurinp = first_scf.outputs.fleurinp
        
    def converge_scf(self):
        """
        Launch fleur_scfs from the generated structures, ensuring
        kmax, k-mesh and MT radii are strictly frozen.
        """
        self.report('INFO: Moving to secondary strained calculations. Freezing parameters...')
        calcs = {}
    
        first_fleurinp = getattr(self.ctx, 'first_fleurinp', None)
        if first_fleurinp is None:
            raise RuntimeError("Missing first_fleurinp in context.")
    
        # 1. Grab baseline parameters from the original user inputs
        base_p = {}
        if 'calc_parameters' in self.inputs.scf:
            base_p = self.inputs.scf.calc_parameters.get_dict()
    
        frozen_p = dict(base_p)
    
        # 2. Extract kmax and k-mesh from get_parameterdata_ncf()
        try:
            ref_params = first_fleurinp.get_parameterdata_ncf().get_dict()
            self.report(f'DEBUG ref_params keys: {list(ref_params.keys())}')
            self.report(f'DEBUG ref_params: {ref_params}')
    
            kmax = ref_params.get('comp', {}).get('kmax')
            if kmax:
                if 'comp' not in frozen_p:
                    frozen_p['comp'] = {}
                frozen_p['comp']['kmax'] = float(kmax)
                self.report(f'Freezing kmax: {kmax}')
            else:
                self.report('WARNING: kmax not found in ref_params')
    
            kpt = ref_params.get('kpt', {})
            if kpt:
                frozen_p['kpt'] = kpt
                self.report(f'Freezing kpt: {kpt}')
            else:
                self.report('WARNING: kpt not found in ref_params')
    
        except Exception as e:
            self.report(f'WARNING: Could not extract params via get_parameterdata_ncf: {e}')
    
        # 3. Freeze MT radii using atom entries from ref_params
        mt_radii = {}
        atom_params = {k: v for k, v in ref_params.items() if k.startswith('atom')}
        self.report(f'DEBUG atom_params: {atom_params}')
    
        for atom_key, atom_val in atom_params.items():
            atom_id = atom_val.get('id')
            rmt = atom_val.get('rmt')
            if atom_id and rmt:
                mt_radii[atom_id] = float(rmt)
    
        if mt_radii:
            for atom_key, atom_val in atom_params.items():
                atom_id = atom_val.get('id')
                if atom_id and atom_id in mt_radii:
                    full_atom = dict(atom_val)
                    full_atom['rmt'] = mt_radii[atom_id]
                    # use element number as id instead of '29.1'
                    element_id = atom_id.split('.')[0]  # '29.1' -> '29'
                    full_atom['id'] = element_id
                    frozen_p[atom_key] = full_atom
            self.report(f'Freezing MT radii by atom id: {mt_radii}')
            self.report(f'DEBUG frozen atom entries: {[{k:v} for k,v in frozen_p.items() if k.startswith("atom")]}')
        else:
            self.report('WARNING: No MT radii found in ref_params atom entries')
    
        self.report(f'Final frozen_p: {frozen_p}')
        frozen_params_node = orm.Dict(dict=frozen_p)
            
        # 4. Launch strained calculations with the frozen parameters
        for i, struc_or_fleurinp in enumerate(self.ctx.structures[1:], 1):
            inputs = self.get_inputs_scf()
            inputs.calc_parameters = frozen_params_node
    
            if isinstance(struc_or_fleurinp, FleurinpData):
                inputs.fleurinp = struc_or_fleurinp
                struc = struc_or_fleurinp.get_structuredata_ncf()
            else:
                inputs.structure = struc_or_fleurinp
                struc = struc_or_fleurinp
    
            label = self.ctx.labels[i]
            self.ctx.volume.append(struc.get_cell_volume())
            self.ctx.volume_peratom[label] = struc.get_cell_volume() / len(struc.sites)
            self.ctx.structures_uuids.append(struc.uuid)
    
            result = self.submit(FleurScfWorkChain, **inputs)
            calcs[label] = result
    
        return ToContext(**calcs)

            
    def get_inputs_scf_first(self):
        """
        get and 'produce' the inputs for a scf-cycle
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if "fleurinp" in self.inputs:
            input_scf.pop("inpgen", None)
            input_scf.pop("calc_parameters", None)

        return input_scf

    def get_inputs_scf(self):
        """
        get and 'produce' the inputs for a scf-cycle
        """
        input_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))
    
        # ensure that all are run with the same FLAPW parameters
        if ('calc_parameters' not in input_scf) and self.ctx.enforce_para:
            input_scf['calc_parameters'] = self.ctx.first_calc_parameters
    
        if "fleurinp" in self.inputs:
            input_scf.pop("inpgen", None)
            input_scf.pop("calc_parameters", None)
    
        return input_scf
            
    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. It will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.report(errormsg)
        self.ctx.errors.append(errormsg)
        self.return_results()

    def inpxml_structures(self,scalelist):
        """
        Rescales a inp.xml by modification of scaling factor

        :param scalelist: scaling factors
        """

        input_dict = self.inputs.fleurinp.inp_dict
        
        re_structures={}
        for scale in scalelist:
            fm=FleurinpModifier(self.inputs.fleurinp)
            if 'bulkLattice' in input_dict["cell"]:
                fm.add_number_to_first_attrib("scale",scale,contains="/fleurInput/cell/bulkLattice/@scale",mode='rel') #rel means multiplaction here
            if 'filmLattice' in input_dict["cell"]:
                fm.add_number_to_first_attrib("scale",scale,contains="/fleurInput/cell/filmLattice/@scale",not_contains="/a",mode='rel')
            re_structures[scale]=fm.freeze()

        # in AiiDA link labels are always strings, because of namespaces '.' are not allowed.
        # replace '.' by underscore to store floats in link label
        res_new = {}
        for key, struc in re_structures.items():
            # label already set by rescale_nowf
            struc.description = str(key)
            link_name = f'scale_{key}'.replace('.', '_')
            res_new[link_name] = struc    
        return res_new

    def return_results(self):
        """
        return the results of the calculations  (scf workchains) and do a
        Birch-Murnaghan fit for the equation of states
        """
        
        if "corrected_calcs" in self.ctx:
            self.ctx.update(self.ctx.corrected_calcs)

        distancelist = []
        t_energylist = []
        t_energylist_peratom = []
        vol_peratom_success = []
        outnodedict = {}
        if "fleurinp" in self.inputs:
            natoms = len(self.inputs.fleurinp.get_structuredata_ncf().sites)
        else:    
            natoms = len(self.inputs.structure.sites)

        e_u = 'eV'
        dis_u = 'me/bohr^3'
        for label in self.ctx.labels:
            calc = self.ctx[label]

            if not calc.is_finished_ok:
                message = f'One SCF workflow was not successful: {label}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                continue

            try:
                outputnode_scf = calc.outputs.output_scf_wc_para
            except KeyError:
                message = f'One SCF workflow failed, no scf output node: {label}. I skip this one.'
                self.ctx.errors.append(message)
                self.ctx.successful = False
                continue

            outnodedict[label] = outputnode_scf

            outpara = outputnode_scf.get_dict()

            t_e = outpara.get('total_energy', float('nan'))
            e_u = outpara.get('total_energy_units', 'eV')
            dis = outpara.get('distance_charge', float('nan'))
            dis_u = outpara.get('distance_charge_units', 'me/bohr^3')
            t_energylist.append(t_e)
            t_energylist_peratom.append(t_e / natoms)
            vol_peratom_success.append(self.ctx.volume_peratom[label])
            distancelist.append(dis)

        not_ok, an_index = check_eos_energies(t_energylist_peratom)

        if not_ok:
            message = f'Abnormality in Total energy list detected. Check entr(ies) {an_index}.'
            hint = ('Consider refining your basis set.')
            self.ctx.info.append(hint)
            self.ctx.warnings.append(message)

        en_array = np.array(t_energylist_peratom)
        vol_array = np.array(vol_peratom_success)

        write_defaults_fit = False
        # TODO: different fits
        if len(en_array):  # for some reason just en_array does not work
            volume, bulk_modulus, bulk_deriv, residuals = birch_murnaghan_fit(en_array, vol_array)

            # something went wrong with the fit
            for i in volume, bulk_modulus, bulk_deriv, residuals:
                if isinstance(i, complex):
                    write_defaults_fit = True
                if i == None:
                    write_defaults_fit = True

            if all(i is not None for i in (volume, bulk_modulus, bulk_deriv, residuals)):
                # cast float, because np datatypes are sometimes not serialable
                volume, bulk_modulus = float(volume), float(bulk_modulus)
                bulk_deriv, residuals = float(bulk_deriv), residuals.tolist()

                volumes = self.ctx.volume
                gs_scale = volume * natoms / self.ctx.org_volume
                bulk_modulus = bulk_modulus * 160.217733  # *echarge*1.0e21,#GPa
                if (volume * natoms < volumes[0]) or (volume * natoms > volumes[-1]):
                    warn = ('Groundstate volume was not in the scaling range.')
                    hint = f'Consider rerunning around point {gs_scale}'
                    self.ctx.info.append(hint)
                    self.ctx.warnings.append(warn)
                    # TODO maybe make it a feature to rerun with centered around the gs.
        else:
            write_defaults_fit = True

        if write_defaults_fit:
            volumes = None
            gs_scale = None
            residuals = None
            volume = 0
            bulk_modulus = None
            bulk_deriv = None

        if "fleurinp" in self.inputs:
            uuid=self.inputs.fleurinp.get_structuredata().uuid
        else:    
            uuid=self.inputs.structure.uuid

        calc_uuids=[]
        for label in self.ctx.labels:
            calc_uuids.append(self.ctx[label].uuid)
    
        # for i,scale in enumerate(self.ctx.scalelist):
        #      label = f'scale_{self.ctx.scalelist[i]}'.replace('.', '_')
        #      calc_uuids.append(self.ctx[label].uuid)

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'scaling': self.ctx.scalelist,
            'scaling_gs': gs_scale,
            'initial_structure': uuid,
            'volume_gs': volume * natoms,
            'volumes': self.ctx.volume,
            'volume_units': 'A^3',
            'natoms': natoms,
            'total_energy': t_energylist,
            'total_energy_units': e_u,
            'structures': self.ctx.structures_uuids,
            'calculations': calc_uuids,
            'scf_wfs': [],  # self.converge_scf_uuids,
            'distance_charge': distancelist,
            'distance_charge_units': dis_u,
            'scale': self.ctx.scale,
            # 'nsteps': self.ctx.points,
            # 'guess': self.ctx.guess,
            # 'stepsize': self.ctx.step,
            # 'fitresults' : [a, latticeconstant, c],
            # 'fit' : fit_new,
            'residuals': residuals,
            'bulk_deriv': bulk_deriv,
            'bulk_modulus': bulk_modulus,
            'bulk_modulus_units': 'GPa',
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        if self.ctx.successful:
            self.report('Done, Equation of states calculation complete')
        else:
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance.')

        outnode = Dict(out)
        outnodedict['results_node'] = outnode

        # create links between all these nodes...
        outputnode_dict = create_stress_result_node(**outnodedict)
        outputnode = outputnode_dict.get('output_stress_wc_para')
        outputnode.label = 'output_stress_wc_para'
        outputnode.description = ('Contains equation of states results and information of an FleurStressWorkChain run.')

        returndict = {}
        returndict['output_stress_wc_para'] = outputnode

        outputstructure = outputnode_dict.get('gs_structure', None)
        if outputstructure:
            outputstructure.label = 'output_stress_wc_structure'
            outputstructure.description = ('Structure with the scaling/volume of the lowest total '
                                           'energy extracted from FleurStressWorkChain')

            returndict['output_stress_wc_structure'] = outputstructure

        # create link to workchain node
        for link_name, node in returndict.items():
            self.out(link_name, node)


@cf
def create_stress_result_node(**kwargs):
    """
    This is a pseudo cf, to create the right graph structure of AiiDA.
    This calcfunction will create the output nodes in the database.
    It also connects the output_nodes to all nodes the information comes from.
    This includes the output_parameter node for the stress, connections to run scfs,
    and returning of the gs_structure (best scale)
    So far it is just parsed in as kwargs argument, because we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_stress_wc_para'] = outpara.clone()
    # copy, because we rather produce the same node twice
    # then have a circle in the database for now...
    outputdict = outpara.get_dict()
    structure = load_node(outputdict.get('initial_structure'))
    gs_scaling = outputdict.get('scaling_gs', 0)
    if gs_scaling:
        gs_structure = rescale_nowf(structure, Float(gs_scaling))
        outdict['gs_structure'] = gs_structure

    return outdict

def apply_strain(structure: StructureData, F) -> StructureData:
    """
    Apply diagonal strain tensor by deforming lattice vectors
    """

    F = np.array(F, dtype=float)
    cell = np.array(structure.cell, dtype=float)

    # correct physics: a' = F · a
    new_cell = F @ cell

    new_structure = structure.clone()
    new_structure.set_cell(new_cell.tolist())

    return new_structure

@cf
def apply_strain_structures(structure, strains):

    strains = strains.get_dict()
    result = {}

    for label, F in strains.items():
        new_structure = apply_strain(structure, F)
        result[label] = new_structure

    return result

def birch_murnaghan_fit(energies, volumes):
    """
    least squares fit of a Birch-Murnaghan equation of state curve. From delta project
    containing in its columns the volumes in A^3/atom and energies in eV/atom
    # The following code is based on the source code of stress.py from the Atomic
    # Simulation Environment (ASE) <https://wiki.fysik.dtu.dk/ase/>.
    :params energies: list (numpy arrays!) of total energies eV/atom
    :params volumes: list (numpy arrays!) of volumes in A^3/atom

    #volume, bulk_modulus, bulk_deriv, residuals = Birch_Murnaghan_fit(data)
    """
    fitdata = np.polyfit(volumes[:]**(-2. / 3.), energies[:], 3, full=True)
    ssr = fitdata[1]
    sst = np.sum((energies[:] - np.average(energies[:]))**2.)
    #print(ssr, sst, energies)
    if sst == 0:
        residuals0 = -1
    else:
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
        return None, None, None, None  #exit()

    derivV2 = 4. / 9. * x**5. * deriv2(x)
    derivV3 = (-20. / 9. * x**(13. / 2.) * deriv2(x) - 8. / 27. * x**(15. / 2.) * deriv3(x))
    bulk_modulus0 = derivV2 / x**(3. / 2.)
    bulk_deriv0 = -1 - x**(-3. / 2.) * derivV3 / derivV2

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
        pv_val = 3 * bm / 2. * ((v0 / vol)**(7 / 3.) - (v0 / vol)**(5 / 3.)) * \
            (1 + 3 / 4. * (dbm - 4) * ((v0 / vol)**(2 / 3.) - 1))
        PV.append(pv_val)
        ev_val = 9 * bm * v0 / 16. * ((dbm * (v0 / vol)**(2 / 3.) - 1)**(3) * ((v0 / vol)**(2 / 3.) - 1)**2 *
                                      (6 - 4 * (v0 / vol)**(2 / 3.)))
        EV.append(ev_val)
    return EV, PV





