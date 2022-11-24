import copy
import re

from aiida.engine import WorkChain, ToContext, if_, while_
from aiida.engine import calcfunction as cf
from aiida.engine import ExitCode
from aiida import orm
from aiida.common.extendeddicts import AttributeDict

from masci_tools.util.constants import HTR_TO_EV
from aiida_fleur.data import inpxml_changes
from aiida_fleur.calculation.fleur import FleurCalculation

from .scf import FleurScfWorkChain


class FleurMagRotateWorkChain(WorkChain):
    """
    Workchain for calculating different magnetic directions
    both for second variation SOC and noco
    """
    _workflowversion = '0.4.0'

    _wf_default = {
        'angles': [],  #[(0.0,0.0), (np.pi/4, 0.0), ...]
        'reuse_charge_density': False,
        'noco': True,
        'noco_species_name': 'all',
        'first_calculation_reference': False,
        'dftu_rotation': False,
        'dftu_density_matrix_relaxation': None  #Which density matrices are allowed to relax
        # None -> All configurations are frozen
        # First -> The first one is relaxed and then used
        #          as a reference
        # All  -> All density matrices can relax
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.input('wf_parameters_first_scf', valid_type=orm.Dict, required=False)
        spec.input('wf_parameters', valid_type=orm.Dict)
        spec.input('dftu_denmat_source', valid_type=(orm.SinglefileData, orm.FolderData), required=False)
        spec.input_namespace('remotes', valid_type=orm.RemoteData, dynamic=True, required=False)

        spec.outline(
            cls.start,
            if_(cls.run_first)(cls.submit_next_calculation,
                               cls.submit_calculations).elif_(cls.run_all)(cls.submit_calculations).else_(
                                   while_(cls.configurations_left)(cls.submit_next_calculation)), cls.return_results)

        spec.output('output_mag_rotate_wc_para', valid_type=orm.Dict, required=True)

        spec.exit_code(400, 'ERROR_SOME_DIRECTIONS_FAILED', message='Some configurations failed')
        spec.exit_code(320, 'ERROR_ALL_DIRECTIONS_FAILED', message='All configurations failed')
        spec.exit_code(401, 'ERROR_NEEDED_DIRECTION_FAILED', message='A required configuration failed')

    @classmethod
    def get_builder_continue(cls, node):
        """
        Get a Builder prepared with inputs to continue from the charge densities of
        a already finished MagRotateWorkChain

        :param node: Instance, from which the calculation should be continued
        """
        builder = node.get_builder_restart()
        scf_nodes = node.get_outgoing(node_class=FleurScfWorkChain).all()
        for link in scf_nodes:
            if not link.node.is_finished_ok:
                continue
            if not re.fullmatch(r'scf\_[0-9]+', link.link_label):
                continue
            builder.remotes[link.link_label] = link.node.outputs.last_calc.remote_folder

        #Remove all the different starting configurations
        #to start from the remote folders
        if 'fleurinp' in builder.scf:
            del builder.scf.fleurinp
        if 'structure' in builder.scf:
            del builder.scf.structure
            del builder.scf.inpgen
        if 'calc_parameters' in builder.scf:
            del builder.scf.calc_parameters

        if 'wf_parameters' in builder:
            wf_parameters = builder.wf_parameters.get_dict()
            wf_parameters['first_calculation_reference'] = False
            builder.wf_parameters = orm.Dict(dict=wf_parameters)

        return builder

    def start(self):
        '''
        check parameters, what condictions? complete?
        check input nodes
        '''
        ### input check ### ? or done automaticly, how optional?
        # check if fleuinp corresponds to fleur_calc
        self.report(f'started Mag rotate workflow version {self._workflowversion}')
        #print("Workchain node identifiers: ")#'{}'
        #"".format(ProcessRegistry().current_calc_node))

        self.ctx.run_sequentially = False
        self.ctx.current_configuration = 0
        self.ctx.successful = True
        self.ctx.info = []
        self.ctx.warnings = []
        self.ctx.errors = []

        inputs = self.inputs

        wf_default = copy.deepcopy(self._wf_default)
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

        self.ctx.run_sequentially = self.ctx.wf_dict['reuse_charge_density']

        if self.ctx.wf_dict['dftu_density_matrix_relaxation'] not in (None, 'all', 'first'):
            error = f"ERROR: invalid option for DFT+U density matrix relaxation: {self.ctx.wf_dict['dftu_density_matrix_relaxation']}"
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if self.ctx.wf_dict['dftu_density_matrix_relaxation'] == 'first' \
           and not self.ctx.wf_dict['first_calculation_reference']:
            error = 'ERROR: For only relaxing the first density matrix the first_calculation_reference option has t also be true'
            self.report(error)
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

    def run_first(self):
        return self.ctx.wf_dict['first_calculation_reference']

    def run_all(self):
        return not self.ctx.run_sequentially

    def configurations_left(self):
        return self.ctx.current_configuration < len(self.ctx.wf_dict['angles'])

    def generate_next_configuration(self):

        self.report(f'Generating Inputs for configuration {self.ctx.current_configuration}')
        inputs_scf = AttributeDict(self.exposed_inputs(FleurScfWorkChain, namespace='scf'))

        if self.ctx.wf_dict['reuse_charge_density'] and self.ctx.current_configuration > 0:
            last_scf = self.ctx[f'scf_{self.ctx.current_configuration-1}']

            if not last_scf.is_finished_ok:
                message = f'The Configuration {self.ctx.current_configuration} was not successful.'
                self.report(message)
                return self.exit_codes.ERROR_NEEDED_DIRECTION_FAILED

            inputs_scf.remote_data = last_scf.outputs.last_calc.remote_folder
            if 'fleurinp' in inputs_scf:
                inputs_scf.pop('fleurinp')

        reuse_first = self.ctx.wf_dict['first_calculation_reference'] and self.ctx.current_configuration > 0
        if reuse_first:
            first_scf = self.ctx['scf_0']

            if not first_scf.is_finished_ok:
                message = 'Configuration 0 was not successful.'
                self.report(message)
                return self.exit_codes.ERROR_NEEDED_DIRECTION_FAILED

            inputs_scf.remote_data = first_scf.outputs.last_calc.remote_folder
            if 'fleurinp' in inputs_scf:
                inputs_scf.pop('fleurinp')
            if 'structure' in inputs_scf:
                inputs_scf.pop('structure')
                inputs_scf.pop('inpgen')
            if 'calc_parameters' in inputs_scf:
                inputs_scf.pop('calc_parameters')

        wf_parameters = {}
        if 'wf_parameters' in inputs_scf:
            wf_parameters = inputs_scf.wf_parameters.get_dict()
        if self.ctx.current_configuration == 0 and 'wf_parameters_first_scf' in self.inputs:
            wf_parameters = self.inputs.wf_parameters_first_scf.get_dict()

        theta, phi = self.ctx.wf_dict['angles'][self.ctx.current_configuration]

        #The tasks are put in front of any evtl. already user-defined tasks
        #THis is so that users can already use the defined directions for other
        #customizations
        with inpxml_changes(wf_parameters, append=False) as fm:
            if self.ctx.wf_dict['noco']:
                fm.set_inpchanges({'l_noco': True, 'ctail': False})
                fm.set_atomgroup(self.ctx.wf_dict['noco_species_name'], {'nocoparams': {'alpha': phi, 'beta': theta}})
            else:
                fm.set_inpchanges({
                    'l_soc': True,
                    'phi': phi,
                    'theta': theta
                },
                                  path_spec={
                                      'phi': {
                                          'contains': 'soc'
                                      },
                                      'theta': {
                                          'contains': 'soc'
                                      }
                                  })

            if self.ctx.wf_dict['dftu_rotation']:
                if 'dftu_denmat_source' in self.inputs or reuse_first:
                    if not reuse_first:
                        source = self.inputs.dftu_denmat_source
                    else:
                        source = inputs_scf.remote_data.creator.outputs.retrieved

                    if isinstance(source, orm.SinglefileData):
                        fm.set_file(source.filename, dst_filename=FleurCalculation._NMMPMAT_FILE_NAME, node=source.uuid)
                    else:
                        fm.set_file(FleurCalculation._NMMPMAT_HDF5_FILE_NAME,
                                    dst_filename=FleurCalculation._NMMPMAT_FILE_NAME,
                                    node=source.uuid)

                if self.ctx.wf_dict['dftu_density_matrix_relaxation'] is None:
                    fm.set_inpchanges({'l_linmix': True, 'mixparam': 0})
                    wf_parameters['nmmp_converged'] = 999  #To prevent the SCF workchain from running with fixed DFT+U
                elif self.ctx.wf_dict['dftu_density_matrix_relaxation'] == 'first' \
                     and reuse_first:
                    fm.set_inpchanges({'l_linmix': True, 'mixparam': 0})
                    wf_parameters['nmmp_converged'] = 999  #To prevent the SCF workchain from running with fixed DFT+U
                else:
                    fm.set_inpchanges({'l_linmix': False})

                #TODO: angles before could be non-zero
                fm.align_nmmpmat_to_sqa()

                #Overwrite any existing density matrix in the remote folder
                settings = {}
                if 'settings' in inputs_scf:
                    settings = inputs_scf.settings.get_dict()
                settings['fleurinp_nmmpmat_priority'] = True
                inputs_scf.settings = orm.Dict(dict=settings)

        inputs_scf.wf_parameters = orm.Dict(dict=wf_parameters)
        label = f'scf_{self.ctx.current_configuration}'
        inputs_scf.metadata.call_link_label = label

        if 'remotes' in self.inputs:
            current_label = f'scf_{self.ctx.current_configuration}'
            if current_label in self.inputs.remotes:
                inputs_scf.remote_data = self.inputs.remotes[current_label]

        self.ctx.current_configuration += 1
        return label, inputs_scf

    def submit_next_calculation(self):

        res = self.generate_next_configuration()
        if isinstance(res, ExitCode):
            return res
        label, inputs = res
        calc = self.submit(FleurScfWorkChain, **inputs)

        return ToContext(**{label: calc})

    def submit_calculations(self):

        calcs = {}
        while self.configurations_left():
            res = self.generate_next_configuration()
            if isinstance(res, ExitCode):
                return res
            label, inputs = res
            calcs[label] = self.submit(FleurScfWorkChain, **inputs)

        return ToContext(**calcs)

    def return_results(self):

        distancelist = []
        t_energylist = []
        t_energylist_all = []
        outnodedict = {}
        n_configurations = len(self.ctx.wf_dict['angles'])
        e_u = 'eV'
        dis_u = 'me/bohr^3'
        for index in range(n_configurations):
            label = f'scf_{index}'

            calc = self.ctx[label]

            try:
                outputnode_scf = calc.outputs.output_scf_wc_para
            except KeyError:
                message = f'One SCF workflow failed, no scf output node: {label}. I skip this one.'
                self.ctx.errors.append(message)
                t_energylist_all.append(None)
                t_energylist.append(None)
                distancelist.append(None)
                self.ctx.successful = False
                continue

            if not calc.is_finished_ok:
                message = f'One SCF workflow was not successful: {label}'
                self.ctx.warnings.append(message)
                self.ctx.successful = False
                if calc.exit_status not in FleurScfWorkChain.get_exit_statuses(['ERROR_DID_NOT_CONVERGE']):
                    t_energylist_all.append(None)
                    t_energylist.append(None)
                    distancelist.append(None)
                    continue

            outnodedict[label] = outputnode_scf

            outpara = outputnode_scf.get_dict()

            t_e = outpara.get('total_energy', None)
            e_u = outpara.get('total_energy_units', 'eV')
            if e_u.lower() == 'htr' and t_e is not None:
                t_e = t_e * HTR_TO_EV
            dis = outpara.get('distance_charge', None)
            dis_u = outpara.get('distance_charge_units', 'me/bohr^3')
            if calc.is_finished_ok:
                t_energylist.append(t_e)
            else:
                t_energylist.append(None)
            t_energylist_all.append(t_e)
            distancelist.append(dis)

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'angles': self.ctx.wf_dict['angles'],
            'total_energy_including_non_converged': t_energylist_all,
            'total_energy': t_energylist,
            'total_energy_units': 'eV',
            'distance_charge': distancelist,
            'distance_charge_units': dis_u,
            'number_configurations': n_configurations,
            'info': self.ctx.info,
            'warnings': self.ctx.warnings,
            'errors': self.ctx.errors
        }

        if self.ctx.successful:
            self.report('Done, MagRotate calculation complete')
        else:
            self.report('Done, but something went wrong.... Probably some individual calculation failed or'
                        ' a scf-cycle did not reach the desired distance.')

        outnode = orm.Dict(dict=out)
        outnodedict['results_node'] = outnode

        # create links between all these nodes...
        outputnode_dict = create_mag_rotate_result_node(**outnodedict)
        outputnode = outputnode_dict.get('output_mag_rotate_wc_para')
        outputnode.label = 'output_mag_rotate_wc_para'
        outputnode.description = (
            'Contains results for the different configurations and information of an FleurMagRotateWorkChain run.')

        returndict = {}
        returndict['output_mag_rotate_wc_para'] = outputnode

        # create link to workchain node
        for link_name, node in returndict.items():
            self.out(link_name, node)

        if all(e is None for e in t_energylist):
            return self.exit_codes.ERROR_ALL_DIRECTIONS_FAILED
        if not self.ctx.successful:
            return self.exit_codes.ERROR_SOME_DIRECTIONS_FAILED


@cf
def create_mag_rotate_result_node(**kwargs):
    """
    This is a pseudo cf, to create the right graph structure of AiiDA.
    This calcfunction will create the output nodes in the database.
    It also connects the output_nodes to all nodes the information comes from.
    This includes the output_parameter node for the eos, connections to run scfs,
    and returning of the gs_structure (best scale)
    So far it is just parsed in as kwargs argument, because we are to lazy
    to put most of the code overworked from return_results in here.
    """
    outdict = {}
    outpara = kwargs.get('results_node', {})
    outdict['output_mag_rotate_wc_para'] = outpara.clone()
    # copy, because we rather produce the same node twice
    # then have a circle in the database for now...
    return outdict
