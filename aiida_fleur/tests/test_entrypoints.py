#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

@pytest.mark.usefixtures("aiida_env")
class TestAiida_fleur_entrypoints:
    """
    tests all the entry points of the Fleur plugin. Therefore if the plugin is reconized by AiiDA 
    and installed right. 
    """
    
    # Calculation
    def test_inpgen_calculation_entry_point(aiida_env):
        from aiida.orm import CalculationFactory
        inpgen_calculation = CalculationFactory('fleur.inpgen')
        assert inpgen_calculation is not None

    def test_fleur_calculation_entry_point(aiida_env):
        from aiida.orm import CalculationFactory
        
        fleur_calculation = CalculationFactory('fleur.fleur')
        assert fleur_calculation is not None
    
    # Data
    def test_fleur_fleurinpdata_entry_point(aiida_env):
        from aiida.orm import DataFactory
        from aiida_fleur.data.fleurinp import FleurinpData
    
        fleurinp = DataFactory('fleur.fleurinp')
        assert fleurinp == FleurinpData

    def test_fleur_fleurinpmodifier_entry_point(aiida_env):
        from aiida.orm import DataFactory
        from aiida_fleur.data.fleurinpmodifier import FleurinpModifier

        fleurinpmod = DataFactory('fleur.fleurinpmodifier')
        assert fleurinpmod == FleurinpModifier


    # Parsers

    def test_inpgen_parser_entry_point(aiida_env):
        from aiida.parsers import ParserFactory
        from aiida_fleur.parsers.fleur_inputgen import Fleur_inputgenParser

        parser = ParserFactory('fleur.fleurinpgenparser')
        assert parser == Fleur_inputgenParser

    def test_fleur_parser_entry_point(aiida_env):
        from aiida.parsers import ParserFactory
        from aiida_fleur.parsers.fleur import FleurParser

        parser = ParserFactory('fleur.fleurparser')
        assert parser == FleurParser


    # Workflows/workchains

    def test_fleur_scf_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_fleur.workflows.scf import fleur_scf_wc
        
        workflow = WorkflowFactory('fleur.scf')
        assert workflow == fleur_scf_wc
        
    def test_fleur_dos_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_fleur.workflows.dos import fleur_dos_wc
        
        workflow = WorkflowFactory('fleur.dos')
        assert workflow == fleur_dos_wc
        
    def test_fleur_band_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_fleur.workflows.band import fleur_band_wc
        
        workflow = WorkflowFactory('fleur.band')
        assert workflow == fleur_band_wc

    def test_fleur_eos_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_fleur.workflows.eos import fleur_eos_wc
        
        workflow = WorkflowFactory('fleur.eos')
        assert workflow == fleur_eos_wc
    
    # this entry point has currently a problem...
    #def test_fleur_inital_cls_wc_entry_point(aiida_env):
    #    from aiida.orm import WorkflowFactory
    #    from aiida_fleur.workflows.initial_cls import fleur_initial_cls_wc

    #    workflow = WorkflowFactory('fleur.init_cls')
    #    assert workflow == fleur_initial_cls_wc
        
    def test_fleur_corehole_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_fleur.workflows.corehole import fleur_corehole_wc
        
        workflow = WorkflowFactory('fleur.corehole')
        assert workflow == fleur_corehole_wc
