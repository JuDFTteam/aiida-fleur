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
'''Contains tests for routines in data_handling. '''
import os
import pytest
import aiida_fleur

aiida_path = os.path.dirname(aiida_fleur.__file__)
TEST_CIF = os.path.join(aiida_path, 'tests/files/cif/AlB.cif')


def test_extract_structure_info(clear_database_aiida_fleur, generate_structure, generate_work_chain_node,
                                fixture_localhost):
    """
    I do not test 'extras' here due to some kind of bug
    """
    from aiida_fleur.tools.data_handling import extract_structure_info
    from aiida_fleur.tools.common_aiida import create_group
    from aiida_fleur.tools.read_cif_folder import wf_struc_from_cif
    from aiida.orm import CalcFunctionNode, load_node, CifData
    from aiida.common import LinkType

    pks = []
    uuids = []

    for i in range(3):
        structure_bulk = generate_structure()
        structure_bulk.append_atom(position=(i, 0., -1.99285), symbols='Se')
        structure_bulk.store()
        pks.append(structure_bulk.pk)
        uuids.append(structure_bulk.uuid)

    cif_data = CifData(file=TEST_CIF)
    cif_data.store()
    cif_structure = wf_struc_from_cif(cif_data)

    print(cif_structure.get_incoming().all())

    # create CalcFunction having StructureData input
    calc_function = CalcFunctionNode()
    calc_function.set_attribute('process_label', 'test_label')
    calc_function.add_incoming(structure_bulk, link_type=LinkType.INPUT_CALC, link_label='test_calcfundtion')
    calc_function.store()

    # create WorkChainNode scf having StructureData input
    scf_wc = generate_work_chain_node(computer=fixture_localhost,
                                      entry_point_name='aiida_fleur.scf',
                                      inputs={'structure': load_node(pks[1])})
    scf_wc.store()
    scf_wc.set_attribute('process_label', 'fleur_scf_wc')

    # create a group
    group = create_group(name='test_group', nodes=pks[:2], description='test_description')

    result = extract_structure_info(keys=[
        'uuid', 'formula', 'pk', 'symmetry', 'pbc', 'volume', 'total_energy', 'child_nodes', 'natoms', 'group', 'label',
        'description', 'cif_file', 'cif_number', 'cif_uuid', 'cif_ref', 'calcfunctions', 'band', 'dos', 'eos',
        'init_cls', 'corehole', 'primitive', 'cell', 'scf'
    ])

    # print(result)
    # assert 0
    correct_result = [
        sorted({
            'formula': 'AlB2',
            'pk': cif_structure.pk,
            'uuid': cif_structure.uuid,
            'natoms': 3,
            'cell': '[[3.009, 0.0, 0.0], [-1.5045, 2.6058704399874, 0.0], [0.0, 0.0, 3.262]]',
            'pbc': '(True, True, True)',
            'label': '',
            'description': '',
            # 'extras': "{{'_aiida_hash': {0}}}".format(cif_structure.get_hash()),
            'symmetry': 'Amm2 (38)',
            'volume': 25.57755127009385,
            'child_nodes': 0,
            'primitive': False,
            'cif_file': ['AlB.cif', cif_data.uuid],
            'group': [],
            'scf': [],
            'band': [],
            'dos': [],
            'eos': [],
            'init_cls': [],
            'corehole': [],
            'calcfunctions': [[], []],
        }),
        sorted({
            'formula': 'SeSi2',
            'pk': pks[2],
            'uuid': uuids[2],
            'natoms': 3,
            'cell': '[[2.715, 2.715, 0.0], [2.715, 0.0, 2.715], [0.0, 2.715, 2.715]]',
            'pbc': '(True, True, True)',
            'label': '',
            'description': '',
            # 'extras': "{{'_aiida_hash': {0}}}".format(load_node(pks[2]).get_hash()),
            'symmetry': 'P1 (1)',
            'volume': 40.02575174999999,
            'child_nodes': 1,
            'primitive': False,
            'cif_file': ['', ''],
            'group': [],
            'scf': [],
            'band': [],
            'dos': [],
            'eos': [],
            'init_cls': [],
            'corehole': [],
            'calcfunctions': [[calc_function.uuid], ['test_label']],
        }),
        sorted({
            'formula': 'SeSi2',
            'pk': pks[1],
            'uuid': uuids[1],
            'natoms': 3,
            'cell': '[[2.715, 2.715, 0.0], [2.715, 0.0, 2.715], [0.0, 2.715, 2.715]]',
            'pbc': '(True, True, True)',
            'label': '',
            'description': '',
            # 'extras': "{{'_aiida_hash': {0}}}".format(load_node(pks[1]).get_hash()),
            'symmetry': 'P1 (1)',
            'volume': 40.02575174999999,
            'child_nodes': 1,
            'primitive': False,
            'cif_file': ['', ''],
            'group': ['test_group'],
            'scf': [scf_wc.uuid],
            'band': [],
            'dos': [],
            'eos': [],
            'init_cls': [],
            'corehole': [],
            'calcfunctions': [[], []],
        }),
        sorted({
            'formula': 'SeSi2',
            'pk': pks[0],
            'uuid': uuids[0],
            'natoms': 3,
            'cell': '[[2.715, 2.715, 0.0], [2.715, 0.0, 2.715], [0.0, 2.715, 2.715]]',
            'pbc': '(True, True, True)',
            'label': '',
            'description': '',
            # 'extras': "{{'_aiida_hash': {0}}}".format(load_node(pks[0]).get_hash),
            'symmetry': 'Imm2 (44)',
            'volume': 40.02575174999999,
            'child_nodes': 0,
            'primitive': False,
            'cif_file': ['', ''],
            'group': ['test_group'],
            'scf': [],
            'band': [],
            'dos': [],
            'eos': [],
            'init_cls': [],
            'corehole': [],
            'calcfunctions': [[], []],
        })
    ]

    for i in result:
        assert sorted(i) in correct_result
