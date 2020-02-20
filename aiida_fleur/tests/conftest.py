# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Initialise a text database and profile for pytest.
This part of code is copied from aiida-quantumespresso"""
from __future__ import absolute_import

import io
import os
import collections
import pytest
import six

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture(scope='function')
def fixture_sandbox():
    """Return a `SandboxFolder`."""
    from aiida.common.folders import SandboxFolder
    with SandboxFolder() as folder:
        yield folder


@pytest.fixture
def fixture_localhost(aiida_localhost):
    """Return a localhost `Computer`."""
    localhost = aiida_localhost
    localhost.set_default_mpiprocs_per_machine(1)
    return localhost


@pytest.fixture
def fixture_code(fixture_localhost):
    """Return a `Code` instance configured to run calculations of given entry point on localhost `Computer`."""

    def _fixture_code(entry_point_name):
        from aiida.orm import Code
        return Code(input_plugin_name=entry_point_name, remote_computer_exec=[fixture_localhost, '/bin/ls'])

    return _fixture_code


@pytest.fixture
def generate_calc_job():
    """Fixture to construct a new `CalcJob` instance and call `prepare_for_submission` for testing `CalcJob` classes.

    The fixture will return the `CalcInfo` returned by `prepare_for_submission` and the temporary folder that was passed
    to it, into which the raw input files will have been written.
    """

    def _generate_calc_job(folder, entry_point_name, inputs=None):
        """Fixture to generate a mock `CalcInfo` for testing calculation jobs."""
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager
        from aiida.plugins import CalculationFactory

        manager = get_manager()
        runner = manager.get_runner()

        process_class = CalculationFactory(entry_point_name)
        process = instantiate_process(runner, process_class, **inputs)

        calc_info = process.prepare_for_submission(folder)

        return calc_info

    return _generate_calc_job


@pytest.fixture
def generate_calc_job_node():
    """Fixture to generate a mock `CalcJobNode` for testing parsers."""

    def flatten_inputs(inputs, prefix=''):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in six.iteritems(inputs):
            if isinstance(value, collections.Mapping):
                flat_inputs.extend(flatten_inputs(value, prefix=prefix + key + '__'))
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def _generate_calc_job_node(entry_point_name, computer, test_name=None, inputs=None, attributes=None):
        """Fixture to generate a mock `CalcJobNode` for testing parsers.

        :param entry_point_name: entry point name of the calculation class
        :param computer: a `Computer` instance
        :param test_name: relative path of directory with test output files in the `fixtures/{entry_point_name}` folder.
        :param inputs: any optional nodes to add as input links to the corrent CalcJobNode
        :param attributes: any optional attributes to set on the node
        :return: `CalcJobNode` instance with an attached `FolderData` as the `retrieved` node
        """
        from aiida import orm
        from aiida.common import LinkType
        from aiida.plugins.entry_point import format_entry_point_string

        entry_point = format_entry_point_string('aiida.calculations', entry_point_name)

        node = orm.CalcJobNode(computer=computer, process_type=entry_point)
        node.set_attribute('input_filename', 'aiida.in')
        node.set_attribute('output_filename', 'aiida.out')
        node.set_attribute('error_filename', 'aiida.err')
        node.set_option('resources', {'num_machines': 1, 'num_mpiprocs_per_machine': 1})
        node.set_option('withmpi', True)
        node.set_option('max_wallclock_seconds', 1800)

        if attributes:
            node.set_attribute_many(attributes)

        if inputs:
            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.add_incoming(input_node, link_type=LinkType.INPUT_CALC, link_label=link_label)

        # node.store()

        if test_name is not None:
            basepath = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(
                basepath, 'parsers', 'fixtures', entry_point_name[len(
                    'quantumespresso.'):], test_name
            )

            retrieved = orm.FolderData()
            retrieved.put_object_from_tree(filepath)
            retrieved.add_incoming(node, link_type=LinkType.CREATE, link_label='retrieved')
            retrieved.store()

            remote_folder = orm.RemoteData(computer=computer, remote_path='/tmp')
            remote_folder.add_incoming(node, link_type=LinkType.CREATE, link_label='remote_folder')
            remote_folder.store()

        return node

    return _generate_calc_job_node


@pytest.fixture
def generate_structure():
    """Return a `StructureData` representing bulk silicon."""

    def _generate_structure():
        """Return a `StructureData` representing bulk silicon."""
        from aiida.orm import StructureData

        param = 5.43
        cell = [[param / 2., param / 2., 0], [param / 2., 0, param / 2.], [0, param / 2., param / 2.]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
        structure.append_atom(position=(param / 4., param / 4., param / 4.),
                              symbols='Si', name='Si')

        return structure

    return _generate_structure


@pytest.fixture
def generate_kpoints_mesh():
    """Return a `KpointsData` node."""

    def _generate_kpoints_mesh(npoints):
        """Return a `KpointsData` with a mesh of npoints in each direction."""
        from aiida.orm import KpointsData

        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([npoints] * 3)

        return kpoints

    return _generate_kpoints_mesh


@pytest.fixture(scope='session')
def generate_parser():
    """Fixture to load a parser class for testing parsers."""

    def _generate_parser(entry_point_name):
        """Fixture to load a parser class for testing parsers.

        :param entry_point_name: entry point name of the parser class
        :return: the `Parser` sub class
        """
        from aiida.plugins import ParserFactory
        return ParserFactory(entry_point_name)

    return _generate_parser


@pytest.fixture
def generate_remote_data():
    """Return a `RemoteData` node."""

    def _generate_remote_data(computer, remote_path, entry_point_name=None):
        """Return a `KpointsData` with a mesh of npoints in each direction."""
        from aiida.common.links import LinkType
        from aiida.orm import CalcJobNode, RemoteData
        from aiida.plugins.entry_point import format_entry_point_string

        entry_point = format_entry_point_string('aiida.calculations', entry_point_name)

        remote = RemoteData(remote_path=remote_path)
        remote.computer = computer

        if entry_point_name is not None:
            creator = CalcJobNode(computer=computer, process_type=entry_point)
            creator.set_option('resources', {'num_machines': 1, 'num_mpiprocs_per_machine': 1})
            remote.add_incoming(creator, link_type=LinkType.CREATE, link_label='remote_folder')
            creator.store()

        return remote

    return _generate_remote_data

############### Here AiiDA-Fleur fixtures begin ##################


@pytest.fixture
def create_fleurinp():
    """Returns fleurinp constuctor"""

    from aiida.plugins import DataFactory
    fleurinp = DataFactory('fleur.fleurinp')

    def _make_fleurinp(inpxmlfilepath):
        return fleurinp(files=[inpxmlfilepath])

    return _make_fleurinp


@pytest.fixture
def inpxml_etree():
    """Returns the etree generator"""
    def _get_etree(path):
        from lxml import etree
        with open(path, 'r') as inpxmlfile:
            tree = etree.parse(inpxmlfile)
        return tree
    return _get_etree


@pytest.fixture
def generate_work_chain_node():
    """Fixture to generate a mock `WorkChainNode` for testing parsers."""

    def flatten_inputs(inputs, prefix=''):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in six.iteritems(inputs):
            if isinstance(value, collections.Mapping):
                flat_inputs.extend(flatten_inputs(value, prefix=prefix + key + '__'))
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def _generate_work_chain_node(entry_point_name, computer, test_name=None, inputs=None, attributes=None):
        """Fixture to generate a mock `WorkChainNode` for testing parsers.

        :param entry_point_name: entry point name of the calculation class
        :param computer: a `Computer` instance
        :param test_name: relative path of directory with test output files in the `fixtures/{entry_point_name}` folder.
        :param inputs: any optional nodes to add as input links to the corrent CalcJobNode
        :param attributes: any optional attributes to set on the node
        :return: `CalcJobNode` instance with an attached `FolderData` as the `retrieved` node
        """
        from aiida import orm
        from aiida.common import LinkType
        from aiida.plugins.entry_point import format_entry_point_string

        entry_point = format_entry_point_string('aiida.workchains', entry_point_name)

        node = orm.WorkChainNode(computer=computer, process_type=entry_point)

        if attributes:
            node.set_attribute_many(attributes)

        if inputs:
            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.add_incoming(input_node, link_type=LinkType.INPUT_WORK, link_label=link_label)

        node.store()

        if test_name is not None:
            basepath = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(
                basepath, 'parsers', 'fixtures', entry_point_name[len(
                    'quantumespresso.'):], test_name
            )

            retrieved = orm.FolderData()
            retrieved.put_object_from_tree(filepath)
            retrieved.add_incoming(node, link_type=LinkType.CREATE, link_label='retrieved')
            retrieved.store()

            remote_folder = orm.RemoteData(computer=computer, remote_path='/tmp')
            remote_folder.add_incoming(node, link_type=LinkType.CREATE, link_label='remote_folder')
            remote_folder.store()

        return node

    return _generate_work_chain_node


@pytest.fixture
def generate_film_structure():
    """Return a `StructureData` representing bulk silicon."""

    def _generate_film_structure():
        """Return a `StructureData` representing bulk silicon."""
        from aiida.orm import StructureData

        bohr_a_0 = 0.52917721092  # A
        a = 7.497 * bohr_a_0
        cell = [[0.7071068*a, 0.0, 0.0],
                [0.0, 1.0*a, 0.0],
                [0.0, 0.0, 0.7071068*a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., -1.99285*bohr_a_0), symbols='Fe')
        structure.append_atom(position=(0.5*0.7071068*a, 0.5*a, 0.0), symbols='Pt')
        structure.append_atom(position=(0., 0., 2.65059*bohr_a_0), symbols='Pt')
        structure.pbc = (True, True, False)

        return structure

    return _generate_film_structure


@pytest.fixture(scope='function', autouse=True)
def clear_database_aiida_fleur(aiida_profile):  # pylint: disable=redefined-outer-name
    """Clear the database before each test.
    """
    aiida_profile.reset_db()

# These outputnode fixtures are hardcoded, it would be nice
# if they produced by workflow test on the fly to ensure that the functions which use them can
# deal with the current version of the output nodes. and if there would be only one fixture
# ggf also backcompability checks of output node versions would be nice


@pytest.fixture
def generate_output_node_from_file(jsonfilepath):
    """returns a dict read from a json file to construcut and Outputnode of a Calculation or Workchain"""
    pass


@pytest.fixture
def generate_fleur_outpara_node():
    """returns a dict of a Outputnode of a FleurCalcJob"""

    para_dict = {
        "CalcJob_uuid": "a6511a00-7759-484a-839d-c100dafd6118",
        "bandgap": 0.0029975592,
        "bandgap_units": "eV",
        "charge_den_xc_den_integral": -3105.2785777045,
        "charge_density1": 3.55653e-05,
        "charge_density2": 6.70788e-05,
        "creator_name": "fleur 27",
        "creator_target_architecture": "GEN",
        "creator_target_structure": " ",
        "density_convergence_units": "me/bohr^3",
        "end_date": {
            "date": "2019/07/17",
            "time": "12:50:27"
        },
        "energy": -4405621.1469633,
        "energy_core_electrons": -99592.985569309,
        "energy_hartree": -161903.59225823,
        "energy_hartree_units": "Htr",
        "energy_units": "eV",
        "energy_valence_electrons": -158.7015525598,
        "fermi_energy": -0.2017877885,
        "fermi_energy_units": "Htr",
        "force_largest": 0.0,
        "magnetic_moment_units": "muBohr",
        "magnetic_moments": [
            2.7677822875,
            2.47601e-05,
            2.22588e-05,
            6.05518e-05,
            0.0001608849,
            0.0001504687,
            0.0001321699,
            -3.35528e-05,
            1.87169e-05,
            -0.0002957294
        ],
        "magnetic_spin_down_charges": [
            5.8532354421,
            6.7738647125,
            6.8081938915,
            6.8073232631,
            6.8162583243,
            6.8156475799,
            6.8188399492,
            6.813423175,
            6.7733972589,
            6.6797683064
        ],
        "magnetic_spin_up_charges": [
            8.6210177296,
            6.7738894726,
            6.8082161503,
            6.8073838149,
            6.8164192092,
            6.8157980486,
            6.8189721191,
            6.8133896222,
            6.7734159758,
            6.679472577
        ],
        "number_of_atom_types": 10,
        "number_of_atoms": 10,
        "number_of_iterations": 49,
        "number_of_iterations_total": 49,
        "number_of_kpoints": 240,
        "number_of_species": 1,
        "number_of_spin_components": 2,
        "number_of_symmetries": 2,
        "orbital_magnetic_moment_units": "muBohr",
        "orbital_magnetic_moments": [],
        "orbital_magnetic_spin_down_charges": [],
        "orbital_magnetic_spin_up_charges": [],
        "output_file_version": "0.27",
        "overall_charge_density": 7.25099e-05,
        "parser_info": "AiiDA Fleur Parser v0.2beta",
        "parser_warnings": [],
        "spin_density": 7.91911e-05,
        "start_date": {
            "date": "2019/07/17",
            "time": "10:38:24"
        },
        "sum_of_eigenvalues": -99751.687121869,
        "title": "A Fleur input generator calculation with aiida",
        "unparsed": [],
        "walltime": 7923,
        "walltime_units": "seconds",
        "warnings": {
            "debug": {},
            "error": {},
            "info": {},
            "warning": {}
        }
    }

    return para_dict


@pytest.fixture
def generate_fleur_scf_outpara_node():
    """returns a dict of a Outputnode of a FleurScfWorkchain"""
    para_dict = {
        "conv_mode": "density",
        "distance_charge": 0.1406279038,
        "distance_charge_all": [
            61.1110641131,
            43.7556515683,  # deleted some
            43.7556515683,
        ],
        "distance_charge_units": "me/bohr^3",
        "errors": [],
        "force_diff_last": "can not be determined",
        "force_largest": 0.0,
        "info": [],
        "iterations_total": 23,
        "last_calc_uuid": "b20b5b94-5d80-41a8-82bf-b4d8eee9bddc",
        "loop_count": 1,
        "material": "FePt2",
        "total_energy": -38166.176928494,
        "total_energy_all": [
            -38166.542950054,
            -38166.345602746,  # deleted some
            -38166.345602746,
        ],
        "total_energy_units": "Htr",
        "total_wall_time": 245,
        "total_wall_time_units": "s",
        "warnings": [],
        "workflow_name": "FleurScfWorkChain",
        "workflow_version": "0.4.0"
    }

    return para_dict


@pytest.fixture
def generate_fleur_eos_outpara_node():
    """returns a dict of a Outputnode of a FleurEOSWorkchain"""

    para_dict = {
        "bulk_deriv": -612.513884563477,
        "bulk_modulus": 29201.4098068761,
        "bulk_modulus_units": "GPa",
        "calculations": [],
        "distance_charge": [
            4.4141e-06,
            4.8132e-06,
            1.02898e-05,
            1.85615e-05
        ],
        "distance_charge_units": "me/bohr^3",
        "errors": [],
        "guess": 1.0,
        "info": [
            "Consider refining your basis set."
        ],
        "initial_structure": "d6985712-7eca-4730-991f-1d924cbd1062",
        "natoms": 1,
        "nsteps": 4,
        "residuals": [],
        "scaling": [
            0.998,
            1.0,
            1.002,
            1.004
        ],
        "scaling_gs": 1.00286268683922,
        "scf_wfs": [],
        "stepsize": 0.002,
        "structures": [
            "f7fddbb5-51af-4dac-a4ba-021d1bf5795b",
            "28e9ed28-837c-447e-aae7-371b70454dc4",
            "fc340850-1a54-4be4-abed-576621b3015f",
            "77fd128b-e88c-4d7d-9aea-d909166926cb"
        ],
        "successful": True,
        "total_energy": [
            -439902.565469453,
            -439902.560450163,
            -439902.564547518,
            -439902.563105211
        ],
        "total_energy_units": "Htr",
        "volume_gs": 16.2724654374658,
        "volume_units": "A^3",
        "volumes": [
            16.1935634057491,
            16.2260154366224,
            16.2584674674955,
            16.290919498369
        ],
        "warnings": [
            "Abnormality in Total energy list detected. Check entr(ies) [1]."
        ],
        "workflow_name": "fleur_eos_wc",
        "workflow_version": "0.3.3"
    }

    return para_dict
