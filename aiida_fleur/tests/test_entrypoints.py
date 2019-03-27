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

from __future__ import absolute_import
import pytest

@pytest.mark.usefixtures("aiida_env")
class TestAiida_fleur_entrypoints:
    """
    tests all the entry points of the Fleur plugin. Therefore if the plugin is 
    reconized by AiiDA and installed right. 
    """
    
    # Calculations
    
    def test_inpgen_calculation_entry_point(aiida_env):
        from aiida.plugins import CalculationFactory
        inpgen_calculation = CalculationFactory('fleur.inpgen')
        assert inpgen_calculation is not None

    def test_fleur_calculation_entry_point(aiida_env):
        from aiida.plugins import CalculationFactory
        
        fleur_calculation = CalculationFactory('fleur.fleur')
        assert fleur_calculation is not None
    
    
    # Data
    
    def test_fleur_fleurinpdata_entry_point(aiida_env):
        from aiida.plugins import DataFactory
        from aiida_fleur.data.fleurinp import FleurinpData
    
        fleurinp = DataFactory('fleur.fleurinp')
        assert fleurinp == FleurinpData

    def test_fleur_fleurinpmodifier_entry_point(aiida_env):
        from aiida.plugins import DataFactory
        from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

        fleurinpmod = DataFactory('fleur.fleurinpmodifier')
        assert fleurinpmod == FleurinpModifier


    # Parsers

    def test_inpgen_parser_entry_point(aiida_env):
        from aiida.plugins import ParserFactory
        from aiida_fleur.parsers.fleur_inputgen import Fleur_inputgenParser

        parser = ParserFactory('fleur.fleurinpgenparser')
        assert parser == Fleur_inputgenParser

    def test_fleur_parser_entry_point(aiida_env):
        from aiida.plugins import ParserFactory
        from aiida_fleur.parsers.fleur import FleurParser

        parser = ParserFactory('fleur.fleurparser')
        assert parser == FleurParser


    # Workflows/workchains

    def test_fleur_scf_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.scf import fleur_scf_wc
        
        workflow = WorkflowFactory('fleur.scf')
        assert workflow == fleur_scf_wc
        
    def test_fleur_dos_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.dos import fleur_dos_wc
        
        workflow = WorkflowFactory('fleur.dos')
        assert workflow == fleur_dos_wc
        
    def test_fleur_band_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.band import fleur_band_wc
        
        workflow = WorkflowFactory('fleur.band')
        assert workflow == fleur_band_wc

    def test_fleur_eos_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.eos import fleur_eos_wc
        
        workflow = WorkflowFactory('fleur.eos')
        assert workflow == fleur_eos_wc
    
    # this entry point has currently a problem...
    def test_fleur_inital_cls_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.initial_cls import fleur_initial_cls_wc

        workflow = WorkflowFactory('fleur.init_cls')
        assert workflow == fleur_initial_cls_wc
        
    def test_fleur_corehole_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.corehole import fleur_corehole_wc
        
        workflow = WorkflowFactory('fleur.corehole')
        assert workflow == fleur_corehole_wc

    def test_fleur_mae_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.mae import fleur_mae_wc
        
        workflow = WorkflowFactory('fleur.mae')
        assert workflow == fleur_mae_wc

    def test_fleur_spst_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.spst import fleur_spst_wc
        
        workflow = WorkflowFactory('fleur.spst')
        assert workflow == fleur_spst_wc

    def test_fleur_dmi_wc_entry_point(aiida_env):
        from aiida.plugins import WorkflowFactory
        from aiida_fleur.workflows.dmi import fleur_dmi_wc
        
        workflow = WorkflowFactory('fleur.dmi')
        assert workflow == fleur_dmi_wc
