import pytest

from aiida import orm
from aiida.orm import Dict

from aiida_fleur.workflows.cutoff_conv import (
    FleurCutoffConvWorkChain,
    create_result_node,
    create_plot_nodes,
)


def build_bcc_fe_structure():
    a = 2.87
    cell = [
        [a, 0.0, 0.0],
        [0.0, a, 0.0],
        [0.0, 0.0, a],
    ]

    structure = orm.StructureData(cell=cell)
    structure.append_atom(position=(0.0, 0.0, 0.0), symbols='Fe')
    structure.append_atom(position=(0.5 * a, 0.5 * a, 0.5 * a), symbols='Fe')
    return structure


def test_cutoff_conv_create_result_node():
    result_data = Dict(dict={
        'workflow_name': 'FleurCutoffConvWorkChain',
        'workflow_version': '1.2.0',
        'successful': True,
        'kmax_results': [],
        'kpoints_results': [],
    }).store()

    outnode = create_result_node(result_data)
    assert outnode.get_dict()['workflow_name'] == 'FleurCutoffConvWorkChain'
    assert outnode.label == 'output_convergence_wc_para'


def test_cutoff_conv_create_plot_nodes():
    result_data = Dict(dict={
        'kmax_results': [
            {
                'kmax': 3.0,
                'total_energy': -100.0,
                'total_energy_units': 'Htr',
                'delta_to_previous_Htr': None,
                'delta_to_previous_meV': None,
            },
            {
                'kmax': 3.25,
                'total_energy': -100.1,
                'total_energy_units': 'Htr',
                'delta_to_previous_Htr': 0.1,
                'delta_to_previous_meV': 2721.1386245988,
            },
        ],
        'kpoints_results': [
            {
                'mesh': [4, 4, 4],
                'nkpts_full_grid': 64,
                'total_energy': -100.0,
                'total_energy_units': 'Htr',
                'delta_to_previous_Htr': None,
                'delta_to_previous_meV': None,
            },
            {
                'mesh': [8, 8, 8],
                'nkpts_full_grid': 512,
                'total_energy': -100.05,
                'total_energy_units': 'Htr',
                'delta_to_previous_Htr': 0.05,
                'delta_to_previous_meV': 1360.5693122994,
            },
        ],
    }).store()

    outdict = create_plot_nodes(result_data)

    kmax_plot = outdict['output_kmax_plot'].get_dict()
    kpoints_plot = outdict['output_kpoints_plot'].get_dict()

    assert kmax_plot['ylabel'] == 'Total energy (Htr)'
    assert kmax_plot['x'] == [3.0, 3.25]

    assert kpoints_plot['ylabel'] == 'Total energy (Htr)'
    assert kpoints_plot['x'] == [64, 512]
    assert kpoints_plot['mesh_labels'] == ['4x4x4', '8x8x8']


def test_cutoff_conv_builder_smoke():
    builder = FleurCutoffConvWorkChain.get_builder()

    builder.structure = build_bcc_fe_structure()
    builder.wf_parameters = Dict(dict={
        'kmax_values': [3, 3.25, 3.5, 3.75, 4.0, 4.25],
        'kpoint_meshes': [
            [4, 4, 4],
            [8, 8, 8],
            [12, 12, 12],
            [16, 16, 16],
            [24, 24, 24],
            [28, 28, 28],
            [32, 32, 32],
        ],
        'kmax_energy_tol_meV': 1.0,
        'kpoints_energy_tol_meV': 1.0,
    })

    assert builder.structure.get_formula() == 'Fe2'
    assert builder.wf_parameters.get_dict()['kmax_values'][0] == 3
    assert builder.wf_parameters.get_dict()['kpoint_meshes'][-1] == [32, 32, 32]