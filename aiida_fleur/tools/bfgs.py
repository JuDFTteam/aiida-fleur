import numpy as np
from numpy.linalg import eigh
from numpy import cos, sin


class BFGS_torques():
    """
    BFGS optimiser for spin directions
    """
    defaults = {'maxstep': 0.1, 'alpha': 1}

    def __init__(self, current_workchain, atoms, workchains=None, maxstep=None, alpha=None):
        """
        Initiates a BFGS optimiser.

        :param current_workchain: the final SCF workchain that calculated torques
        :param atoms: the total number of atoms
        :param workchains: a list of workchains, in which SCF workchains will be searched and the relaxation history
                           will be built up
        :param maxstep: the maximal allowed displacement between two iterations
        :param alpha: initial guess for the Hessian

        """

        if maxstep is None:
            self.maxstep = self.defaults['maxstep']
        else:
            self.maxstep = maxstep

        if alpha is None:
            self.alpha = self.defaults['alpha']
        else:
            self.alpha = alpha

        if workchains is None:
            self.workchains = []
        else:
            self.workchains = workchains

        self.current_workchain = current_workchain

        self.H0 = np.eye(2 * atoms) * self.alpha

        self.H = None
        self.r0 = None
        self.f0 = None
        self.new_positions = None

        self.replay_trajectory()

    def step(self, f=None):
        """
        Proposes alphas and betas for the next iteration
        """
        if f is None:
            f = get_forces(self.current_workchain)

        r = get_positions(self.current_workchain)

        self.update(r, f, self.r0, self.f0)
        omega, V = eigh(self.H)

        dr = np.dot(V, np.dot(f, V) / np.fabs(omega))
        dr = self.determine_step(dr)
        self.new_positions = r + dr
        self.r0 = r.copy()
        self.f0 = f.copy()

    def determine_step(self, dr):
        """Determine step to take according to maxstep
        Normalize all steps as the largest step. This way
        we still move along the eigendirection.
        """
        maxsteplength = np.max(dr)
        if maxsteplength >= self.maxstep:
            scale = self.maxstep / maxsteplength

            dr *= scale

        return dr

    def update(self, r, f, r0, f0):
        if self.H is None:
            self.H = self.H0
            return
        dr = r - r0

        if np.abs(dr).max() < 1e-7:
            # Same configuration again (maybe a restart):
            return

        df = f - f0
        a = np.dot(dr, df)
        dg = np.dot(self.H, dr)
        b = np.dot(dr, dg)
        self.H -= np.outer(df, df) / a + np.outer(dg, dg) / b

    def replay_trajectory(self):
        """Initialize hessian from old trajectory."""

        workchains = unwrap_workchains(self.workchains) + [self.current_workchain]

        r0 = get_positions(workchains[0])
        f0 = get_forces(workchains[0])
        for scf in workchains:
            r = get_positions(scf)
            f = get_forces(scf)

            self.update(r, f, r0, f0)
            r0 = r
            f0 = f

        self.r0 = r0
        self.f0 = f0


def unwrap_workchains(workchains):
    """
    Finds all nested SCF workchains and sorts them according to the PK
    """
    from aiida_fleur.tools.common_fleur_wf import find_nested_process
    from aiida_fleur.workflows.scf import FleurScfWorkChain
    from aiida.orm import load_node, WorkChainNode

    unwrapped = []
    for workchain in workchains:
        if not isinstance(workchain, WorkChainNode):
            workchain = load_node(workchain)
        if workchain.process_class is not FleurScfWorkChain:
            unwrapped.extend(find_nested_process(workchain, FleurScfWorkChain))
        else:
            unwrapped.append(workchain)

    unwrapped = [x for x in unwrapped if x.is_finished_ok]

    return sorted(unwrapped, key=lambda x: x.pk)


def get_positions(workchain):
    """
    Extracts alpha and beta angles
    """
    output_dict = workchain.outputs.output_scf_wc_para.get_dict()
    r = np.array(output_dict['alphas'] + output_dict['betas'])
    return r


def get_forces(workchain):
    """
    Extracts torques and converts them from the local frame to the global spherical one
    """
    output_dict = workchain.outputs.output_scf_wc_para.get_dict()
    alphas = output_dict['alphas']
    betas = output_dict['betas']
    x_torques = output_dict['last_x_torques']
    y_torques = output_dict['last_y_torques']
    f_theta = []
    f_phi = []

    def rotation_matrix(alpha, beta):
        'This matrix converts local spin directions to the global frame'
        return np.array([[cos(alpha) * cos(beta), -sin(alpha),
                          cos(alpha) * sin(beta)], [sin(alpha) * cos(beta),
                                                    cos(alpha),
                                                    sin(alpha) * sin(beta)], [-sin(beta), 0, cos(beta)]])

    for alpha, beta, x_torque, y_torque in zip(alphas, betas, x_torques, y_torques):
        torque = np.dot(rotation_matrix(alpha, beta), np.array([x_torque, y_torque, 0]))

        f_theta.append(torque[0] * cos(alpha) * cos(beta) + torque[1] * sin(alpha) * cos(beta) - torque[2] * sin(beta))
        f_phi.append(-torque[0] * sin(alpha) * sin(beta) + torque[1] * cos(alpha) * sin(beta))

    f = f_phi + f_theta
    f = -np.array(f)

    return f
