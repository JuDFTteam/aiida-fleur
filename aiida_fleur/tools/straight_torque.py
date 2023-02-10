import numpy as np
from numpy import cos, sin


def analyse_relax_straight(alphas, betas, x_torques, y_torques, relax_alpha, maxstep):
    """
    This function generates a new fleurinp analysing parsed relax.xml from the previous
    calculation.

    :param relax_dict: parsed relax.xml from the previous calculation
    :return new_fleurinp: new FleurinpData object that will be used for next relax iteration
    """

    def rotation_matrix(alpha, beta):
        'This matrix converts local spin directions to the global frame'
        return np.array([[cos(alpha) * cos(beta), -sin(alpha),
                          cos(alpha) * sin(beta)], [sin(alpha) * cos(beta),
                                                    cos(alpha),
                                                    sin(alpha) * sin(beta)], [-sin(beta), 0, cos(beta)]])

    def convert_to_xyz(alpha, beta):
        x = sin(beta) * cos(alpha)
        y = sin(beta) * sin(alpha)
        z = cos(beta)
        return np.array([x, y, z])

    def convert_to_angles(vector):
        alpha = np.arctan2(vector[1], vector[0])
        beta = np.arccos(vector[2] / np.linalg.norm(vector))

        return alpha, beta

    torques = []
    for alpha, beta, x_torque, y_torque in zip(alphas, betas, x_torques, y_torques):
        torque = np.dot(rotation_matrix(alpha, beta), np.array([x_torque, y_torque, 0]))
        torque = np.array(torque)
        if np.linalg.norm(torque) > np.pi / 180 * 5:
            torque = torque / np.linalg.norm(torque) * np.pi / 180 * 5
        torques.append(np.array(torque))

    spin_coordinates = [np.array(convert_to_xyz(alpha, beta)) for alpha, beta in zip(alphas, betas)]

    new_spin_coordinates = [spin + relax_alpha * torque for spin, torque in zip(spin_coordinates, torques)]
    new_alpha_beta = [convert_to_angles(vector) for vector in new_spin_coordinates]
    new_alpha_beta = {'alphas': [x[0] for x in new_alpha_beta], 'betas': [x[1] for x in new_alpha_beta]}

    return new_alpha_beta
