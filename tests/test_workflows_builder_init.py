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
'''
Contains smoke tests for all workchains of aiida-fleur,
checks if builderis from aiida-core gets the correct class.
'''
#pylint: disable=no-self-use
import pytest


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class TestFleurWorkchainInterfaces:
    """
    Test all aiida-fleur workflow interfaces
    """

    # TODO
    # prepare some nodes:
    # structure, option, fleurinp, wfparameters
    # add to builder and see if he takes it
    # ggf if possible run initial step only, that the input is checked...
    # In general the interfaces should be fixed and not changed. this is what
    # these tests are for, to test be aware of interface breaks

    def test_fleur_scf_wc_init(self):
        """
        Test the interface of the scf workchain
        """
        from aiida_fleur.workflows.scf import FleurScfWorkChain

        builder = FleurScfWorkChain.get_builder()

    def test_fleur_eos_wc_init(self):
        """
        Test the interface of the eos workchain
        """
        from aiida_fleur.workflows.eos import FleurEosWorkChain

        builder = FleurEosWorkChain.get_builder()

    def test_fleur_dos_wc_init(self):
        """
        Test the interface of the dos workchain
        """
        from aiida_fleur.workflows.dos import fleur_dos_wc

        builder = fleur_dos_wc.get_builder()

    def test_fleur_corehole_wc_init(self):
        """
        Test the interface of the corehole workchain
        """
        from aiida_fleur.workflows.corehole import FleurCoreholeWorkChain

        builder = FleurCoreholeWorkChain.get_builder()

    def test_fleur_initial_cls_wc_init(self):
        """
        Test the interface of the scf workchain
        """
        from aiida_fleur.workflows.initial_cls import FleurInitialCLSWorkChain

        builder = FleurInitialCLSWorkChain.get_builder()

    def test_fleur_relax_wc_init(self):
        """
        Test the interface of the relax workchain
        """
        from aiida_fleur.workflows.relax import FleurRelaxWorkChain

        builder = FleurRelaxWorkChain.get_builder()

    def test_fleur_mae_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.mae import FleurMaeWorkChain

        builder = FleurMaeWorkChain.get_builder()

    def test_fleur_mae_conv_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.mae_conv import FleurMaeConvWorkChain

        builder = FleurMaeConvWorkChain.get_builder()

    def test_fleur_ssdisp_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain

        builder = FleurSSDispWorkChain.get_builder()

    def test_fleur_ssdisp_conv_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.ssdisp_conv import FleurSSDispConvWorkChain

        builder = FleurSSDispConvWorkChain.get_builder()

    def test_fleur_dmi_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.dmi import FleurDMIWorkChain

        builder = FleurDMIWorkChain.get_builder()

    def test_fleur_base_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain

        builder = FleurBaseWorkChain.get_builder()

    def test_fleur_base_relax_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.base_relax import FleurBaseRelaxWorkChain

        builder = FleurBaseRelaxWorkChain.get_builder()

    def test_fleur_create_magnetic_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.create_magnetic_film import FleurCreateMagneticWorkChain

        builder = FleurCreateMagneticWorkChain.get_builder()

    def test_fleur_strain_wc_init(self):
        """
        Test the interface of the dmi workchain
        """
        from aiida_fleur.workflows.strain import FleurStrainWorkChain

        builder = FleurStrainWorkChain.get_builder()

    def test_fleur_orbcontrol_wc_init(self):
        """
        Test the interface of the orbcontrol workchain
        """
        from aiida_fleur.workflows.orbcontrol import FleurOrbControlWorkChain

        builder = FleurOrbControlWorkChain.get_builder()

    def test_fleur_cfcoeff_wc_init(self):
        """
        Test the interface of the cfcoeff workchain
        """
        from aiida_fleur.workflows.cfcoeff import FleurCFCoeffWorkChain

        builder = FleurCFCoeffWorkChain.get_builder()

    def test_fleur_relax_torque_wc_init(self):
        """
        Test the interface of the cfcoeff workchain
        """
        from aiida_fleur.workflows.relax_torque import FleurRelaxTorqueWorkChain

        builder = FleurRelaxTorqueWorkChain.get_builder()
