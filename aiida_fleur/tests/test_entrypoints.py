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
''' Contains smoke tests for all aiida-fleur entry points '''
from __future__ import absolute_import
import pytest


@pytest.mark.usefixtures('aiida_profile', 'clear_database')
class TestFleurEntrypoints:
    """
    tests all the entry points of the Fleur plugin. Therefore if the plugin is
    recognized by AiiDA and installed right.
    """

    # Calculations

    def test_inpgen_calculation_entry_point(self):
        from aiida.plugins import CalculationFactory
        inpgen_calculation = CalculationFactory('fleur.inpgen')
        assert inpgen_calculation is not None

    def test_fleur_calculation_entry_point(self):
        from aiida.plugins import CalculationFactory

        fleur_calculation = CalculationFactory('fleur.fleur')
        assert fleur_calculation is not None

    # Data

    def test_fleur_fleurinpdata_entry_point(self):
        from aiida.plugins import DataFactory
        from aiida_fleur.data.fleurinp import FleurinpData

        fleurinp = DataFactory('fleur.fleurinp')
        assert fleurinp == FleurinpData

    # Parsers

    def test_inpgen_parser_entry_point(self):
        from aiida.plugins import ParserFactory
        from aiida_fleur.parsers.fleur_inputgen import Fleur_inputgenParser

        parser = ParserFactory('fleur.fleurinpgenparser')
        assert parser == Fleur_inputgenParser

    def test_fleur_parser_entry_point(self):
        from aiida.plugins import ParserFactory
        from aiida_fleur.parsers.fleur import FleurParser

        parser = ParserFactory('fleur.fleurparser')
        assert parser == FleurParser

    # Workflows/workchains

    def test_fleur_scf_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.scf import FleurScfWorkChain

        workflow = WorkflowFactory('fleur.scf')
        assert workflow == FleurScfWorkChain

    def test_fleur_dos_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.dos import fleur_dos_wc

        workflow = WorkflowFactory('fleur.dos')
        assert workflow == fleur_dos_wc

    def test_fleur_band_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.band import FleurBandWorkChain

        workflow = WorkflowFactory('fleur.band')
        assert workflow == FleurBandWorkChain

    def test_fleur_banddos_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.banddos import FleurBandDosWorkChain

        workflow = WorkflowFactory('fleur.banddos')
        assert workflow == FleurBandDosWorkChain

    def test_fleur_eos_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.eos import FleurEosWorkChain

        workflow = WorkflowFactory('fleur.eos')
        assert workflow == FleurEosWorkChain

    # this entry point has currently a problem...
    def test_fleur_initial_cls_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.initial_cls import fleur_initial_cls_wc

        workflow = WorkflowFactory('fleur.init_cls')
        assert workflow == fleur_initial_cls_wc

    def test_fleur_corehole_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.corehole import fleur_corehole_wc

        workflow = WorkflowFactory('fleur.corehole')
        assert workflow == fleur_corehole_wc

    def test_fleur_mae_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.mae import FleurMaeWorkChain

        workflow = WorkflowFactory('fleur.mae')
        assert workflow == FleurMaeWorkChain

    def test_fleur_mae_conv_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.mae_conv import FleurMaeConvWorkChain

        workflow = WorkflowFactory('fleur.mae_conv')
        assert workflow == FleurMaeConvWorkChain

    def test_fleur_ssdisp_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.ssdisp import FleurSSDispWorkChain

        workflow = WorkflowFactory('fleur.ssdisp')
        assert workflow == FleurSSDispWorkChain

    def test_fleur_ssdisp_conv_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.ssdisp_conv import FleurSSDispConvWorkChain

        workflow = WorkflowFactory('fleur.ssdisp_conv')
        assert workflow == FleurSSDispConvWorkChain

    def test_fleur_dmi_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.dmi import FleurDMIWorkChain

        workflow = WorkflowFactory('fleur.dmi')
        assert workflow == FleurDMIWorkChain

    def test_fleur_base_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain

        workflow = WorkflowFactory('fleur.base')
        assert workflow == FleurBaseWorkChain

    def test_fleur_base_relax_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.base_relax import FleurBaseRelaxWorkChain

        workflow = WorkflowFactory('fleur.base_relax')
        assert workflow == FleurBaseRelaxWorkChain

    def test_fleur_create_magnetic_wc_entry_point(self):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.create_magnetic_film import FleurCreateMagneticWorkChain

        workflow = WorkflowFactory('fleur.create_magnetic')
        assert workflow == FleurCreateMagneticWorkChain
