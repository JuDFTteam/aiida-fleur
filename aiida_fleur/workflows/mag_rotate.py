import copy

from aiida.engine import WorkChain, ToContext, if_, while_
from aiida.engine import calcfunction as cf
from aiida.engine import ExitCode
from aiida import orm
from aiida.common.extendeddicts import AttributeDict

from masci_tools.util.constants import HTR_TO_EV

from .scf import FleurScfWorkChain


class FleurMagRotateWorkChain(WorkChain):
    """
    Workchain for calculating different magnetic directions
    both for second variation SOC and noco
    """
    _workflowversion = '0.0.1'

    _wf_default = {
        'angles': [],  #[(0.0,0.0), (np.pi/4, 0.0), ...]
        'reuse_charge_density': False,
        'noco': True,
        'noco_species_name': 'all'
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain, namespace='scf')
        spec.input('wf_parameters_first_scf', valid_type=orm.Dict, required=False)
        spec.input('wf_parameters', valid_type=orm.Dict)

        spec.outline(
            cls.start,
            if_(cls.run_all)(cls.submit_calculations).else_(
                while_(cls.configurations_left)(cls.submit_next_calculation)), cls.return_results)

        spec.output('output_mag_rotate_wc_para', valid_type=orm.Dict, required=True)

        spec.exit_code(400, 'ERROR_SUBPROCESS_FAILED', message='Some configurations failed')

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
        self.ctx.successful = False
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
                return self.exit_codes.ERROR_SUBPROCESS_FAILED

            inputs_scf.remote_data = last_scf.outputs.last_calc.remote_folder
            if 'fleurinp' in inputs_scf:
                inputs_scf.pop('fleurinp')

        wf_parameters = {}
        if 'wf_parameters' in inputs_scf:
            wf_parameters = inputs_scf.wf_parameters.get_dict()
        if self.ctx.current_configuration == 0 and 'wf_parameters_first_scf' in self.inputs:
            wf_parameters = self.inputs.wf_parameters_first_scf.get_dict()

        theta, phi = self.ctx.wf_dict['angles'][self.ctx.current_configuration]
        if self.ctx.wf_dict['noco']:
            wf_parameters.setdefault('inpxml_changes', []).extend([('set_inpchanges', {
                'changes': {
                    'l_noco': True,
                    'ctail': False
                }
            }),
                                                                   ('set_atomgroup', {
                                                                       'species': self.ctx.wf_dict['noco_species_name'],
                                                                       'changes': {
                                                                           'nocoparams': {
                                                                               'alpha': phi,
                                                                               'beta': theta
                                                                           }
                                                                       }
                                                                   })])
        else:
            wf_parameters.setdefault('inpxml_changes', []).extend([('set_inpchanges', {
                'changes': {
                    'l_soc': True
                }
            }),
                                                                   ('set_inpchanges', {
                                                                       'changes': {
                                                                           'phi': phi,
                                                                           'theta': theta
                                                                       },
                                                                       'path_spec': {
                                                                           'phi': {
                                                                               'contains': 'soc'
                                                                           },
                                                                           'theta': {
                                                                               'contains': 'soc'
                                                                           }
                                                                       }
                                                                   })])
        inputs_scf.wf_parameters = orm.Dict(dict=wf_parameters)
        label = f'scf_{self.ctx.current_configuration}'
        inputs_scf.metadata.call_link_label = label

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
        outnodedict = {}
        n_configurations = len(self.ctx.wf_dict['angles'])
        e_u = 'eV'
        dis_u = 'me/bohr^3'
        for index in range(n_configurations):
            label = f'scf_{index}'

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
            if e_u in ['Htr', 'htr']:
                t_e = t_e * HTR_TO_EV
            dis = outpara.get('distance_charge', float('nan'))
            dis_u = outpara.get('distance_charge_units', 'me/bohr^3')
            t_energylist.append(t_e)
            distancelist.append(dis)

        out = {
            'workflow_name': self.__class__.__name__,
            'workflow_version': self._workflowversion,
            'angles': self.ctx.wf_dict['angles'],
            'total_energy': t_energylist,
            'total_energy_units': e_u,
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
