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
'''
Module to test all CLI commands to launch for calcjob and workflows of aiida-fleur.

Comment: while 'launch process' is mocked to do nothing these tests are still quite slow
but execute large parts of the workchain code base.
'''
import os
from aiida.orm import Dict
file_path1 = '../../files/inpxml/FePt/inp.xml'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))
FEPT_INPXML_FILE = os.path.abspath(os.path.join(inpxmlfilefolder, file_path1))


def test_launch_inpgen_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the inpgen launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_inpgen

    code = fixture_code('fleur.inpgen').store()
    options = ['--inpgen', code.uuid]
    run_cli_process_launch_command(launch_inpgen, options=options)

    options = ['--inpgen', code.uuid, '--daemon']
    run_cli_process_launch_command(launch_inpgen, options=options)


def test_launch_fleur_base(run_cli_process_launch_command, fixture_code, create_fleurinp):
    """Test invoking the fleur launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_fleur

    code = fixture_code('fleur.fleur').store()
    fleurinp = create_fleurinp(FEPT_INPXML_FILE).store()

    #Calcjob
    options = ['--fleur', code.uuid, '-inp', fleurinp.uuid, '--no-launch_base']
    run_cli_process_launch_command(launch_fleur, options=options)

    #Base_fleur
    options = ['--fleur', code.uuid, '-inp', fleurinp.uuid]
    run_cli_process_launch_command(launch_fleur, options=options)


def test_launch_scf_base(run_cli_process_launch_command, fixture_code, create_fleurinp):
    """Test invoking the scf workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_scf

    #Path 1
    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid]
    run_cli_process_launch_command(launch_scf, options=options)

    #Path2
    fleurinp = create_fleurinp(FEPT_INPXML_FILE).store()
    options = ['--fleur', fleur.uuid, '-inp', fleurinp.uuid]
    run_cli_process_launch_command(launch_scf, options=options)


def test_launch_eos_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the eos workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_eos

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid]
    run_cli_process_launch_command(launch_eos, options=options)


def test_launch_relax_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the relax workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_relax

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid]
    run_cli_process_launch_command(launch_relax, options=options)


def test_launch_corehole_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the corehole workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_corehole

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid]
    run_cli_process_launch_command(launch_corehole, options=options)


def test_launch_init_cls_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the initial_cls workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_init_cls

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid]
    run_cli_process_launch_command(launch_init_cls, options=options)


def test_launch_banddos_base(run_cli_process_launch_command, fixture_code, generate_remote_data, create_fleurinp):
    """Test invoking the banddow workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_banddos

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()
    path = os.path.abspath(os.path.join(inpxmlfilefolder, '../../files/outxml/tmp'))
    remote = generate_remote_data(fleur.computer, path).store()
    fleurinp = create_fleurinp(FEPT_INPXML_FILE).store()

    options = ['--fleur', fleur.uuid, '-P', remote.uuid, '-inp', fleurinp.uuid]
    run_cli_process_launch_command(launch_banddos, options=options)


def test_launch_mae_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the mae workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_mae

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()

    wf_para = {
        'lattice': 'fcc',
        'directions': [[-1, 1, 0], [0, 0, 1], [1, 1, 0]],
        'host_symbol': 'Pt',
        'latticeconstant': 4.0,
        'size': (1, 1, 5),
        'replacements': {
            0: 'Fe',
            -1: 'Fe'
        },
        'decimals': 10,
        'pop_last_layers': 1,
        'total_number_layers': 8,
        'num_relaxed_layers': 3
    }

    wf_para = Dict(dict=wf_para).store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid, '-wf', wf_para.uuid]
    run_cli_process_launch_command(launch_mae, options=options)


def test_launch_create_magnetic_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the mae workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_create_magnetic

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()

    wf_para = {
        'sqa_ref': [0.7, 0.7],
        'use_soc_ref': False,
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'serial': False,
        'soc_off': [],
        'inpxml_changes': [],
    }

    wf_para = Dict(dict=wf_para).store()

    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid, '-wf', wf_para.uuid]
    run_cli_process_launch_command(launch_create_magnetic, options=options)


def test_launch_dmi_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the mae workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_dmi

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()

    wf_para = {
        'serial': False,
        'beta': {
            '123': 1.57079
        },
        'sqas_theta': [0.0, 1.57079, 1.57079],
        'sqas_phi': [0.0, 0.0, 1.57079],
        'soc_off': [],
        #  'prop_dir': [0.125, 0.15, 0.24],
        'q_vectors': [[0.0, 0.0, 0.0], [0.1, 0.1, 0.0]],
        'ref_qss': [0.0, 0.0, 0.0],
        'inpxml_changes': []
    }

    wf_para = Dict(dict=wf_para).store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid, '-wf', wf_para.uuid]
    run_cli_process_launch_command(launch_dmi, options=options)


def test_launch_ssdisp_base(run_cli_process_launch_command, fixture_code):
    """Test invoking the mae workchain launch command with only required inputs."""
    from aiida_fleur.cmdline.launch import launch_ssdisp

    inpgen = fixture_code('fleur.inpgen').store()
    fleur = fixture_code('fleur.fleur').store()

    wf_para = {
        'beta': {
            'all': 1.57079
        },
        'prop_dir': [0.125, 0.125, 0.0],
        'q_vectors': [[0.0, 0.0, 0.0], [0.125, 0.125, 0.0], [0.250, 0.250, 0.0], [0.375, 0.375, 0.0],
                      [0.500, 0.500, 0.0]],
        'ref_qss': [0.0, 0.0, 0.0],
        'inpxml_changes': []
    }

    wf_para = Dict(dict=wf_para).store()
    options = ['--inpgen', inpgen.uuid, '--fleur', fleur.uuid, '-wf', wf_para.uuid]
    run_cli_process_launch_command(launch_ssdisp, options=options)
