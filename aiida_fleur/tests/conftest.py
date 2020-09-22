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

# aiida_testing.mock_codes in development, not yet a stable dependency..
pytest_plugins = ['aiida.manage.tests.pytest_fixtures', 'aiida_testing.mock_code', 'aiida_testing.export_cache']  # pylint: disable=invalid-name


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
            filepath = os.path.join(basepath, 'parsers', 'fixtures', entry_point_name[len('quantumespresso.'):],
                                    test_name)

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
        cell = [[0, param / 2., param / 2.], [param / 2., 0, param / 2.], [param / 2., param / 2., 0]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
        structure.append_atom(position=(param / 4., param / 4., param / 4.), symbols='Si', name='Si')

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

        if test_name is not None:
            basepath = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(basepath, 'parsers', 'fixtures', entry_point_name[len('quantumespresso.'):],
                                    test_name)

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
        cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., -1.99285 * bohr_a_0), symbols='Fe')
        structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
        structure.append_atom(position=(0., 0., 2.65059 * bohr_a_0), symbols='Pt')
        structure.pbc = (True, True, False)

        return structure

    return _generate_film_structure


@pytest.fixture(scope='function', autouse=True)
def clear_database_aiida_fleur(clear_database):  # pylint: disable=redefined-outer-name
    """Clear the database before each test.
    """
    #aiida_profile.reset_db()
    #yield
    #aiida_profile.reset_db()


@pytest.fixture
def read_dict_from_file():
    """returns a dict read from a json file to construct and Outputnode of a JobCalc or Workchain"""

    def _read_dict_from_file(jsonfilepath):
        """Return dict from json"""
        import json

        node_dict = {}
        with open(jsonfilepath, 'r') as jfile:
            node_dict = json.load(jfile)

        return node_dict

    return _read_dict_from_file


@pytest.fixture
def generate_structure2():
    """Return a `StructureData` representing bulk silicon."""

    def _generate_structure2():
        """Return a `StructureData` representing bulk silicon."""
        from aiida.orm import StructureData

        def rel_to_abs(vector, cell):
            """
            converts interal coordinates to absolut coordinates in Angstroem.
            """
            if len(vector) == 3:
                postionR = vector
                row1 = cell[0]
                row2 = cell[1]
                row3 = cell[2]
                new_abs_pos = [
                    postionR[0] * row1[0] + postionR[1] * row2[0] + postionR[2] * row3[0],
                    postionR[0] * row1[1] + postionR[1] * row2[1] + postionR[2] * row3[1],
                    postionR[0] * row1[2] + postionR[1] * row2[2] + postionR[2] * row3[2]
                ]
                return new_abs_pos

        bohr_a_0 = 0.52917721092  # A
        a = 5.167355275190 * bohr_a_0
        cell = [[0.0, a, a], [a, 0.0, a], [a, a, 0.0]]
        structure = StructureData(cell=cell)
        pos1 = rel_to_abs((1. / 8., 1. / 8., 1. / 8.), cell)
        pos2 = rel_to_abs((-1. / 8., -1. / 8., -1. / 8.), cell)
        structure.append_atom(position=pos1, symbols='Si')
        structure.append_atom(position=pos2, symbols='Si')

        return structure

    return _generate_structure2


@pytest.fixture
def generate_structure_W():
    """Return a `StructureData` representing bulk tungsten."""

    def _generate_structure_W():
        """Return a `StructureData` representing bulk tungsten."""
        from aiida.orm import StructureData

        # W bcc structure
        bohr_a_0 = 0.52917721092  # A
        a = 3.013812049196 * bohr_a_0
        cell = [[-a, a, a], [a, -a, a], [a, a, -a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='W', name='W')

        #param = 3.18968 # 1.58950065353588 * 0.5291772109
        #cell = [[-param, param, param], [param, -param, param], [param, param, -param]]
        #structure = StructureData(cell=cell)
        #structure.append_atom(position=(0., 0., 0.), symbols='W', name='W')

        return structure

    return _generate_structure_W


@pytest.fixture
def generate_structure_cif():
    """Return a `StructureData` from a cif file path."""

    def _generate_structure_cif(cif_filepath):
        """Return a `StructureData` from a cif file."""
        from aiida.orm import CifData

        structure = CifData.get_or_create(cif_filepath)[0].get_structure()
        return structure

    return _generate_structure_cif


@pytest.fixture(scope='function')
def create_or_fake_local_code(aiida_local_code_factory):

    def _get_code(executable, exec_relpath, entrypoint):
        import pathlib
        from aiida.tools.importexport import import_data, export
        from aiida.orm import ProcessNode, QueryBuilder, Code, load_node

        _exe_path = os.path.abspath(exec_relpath)

        # if path is non existent, we create a dummy executable
        # if all caches are there, it should run, like on a CI server
        if not os.path.exists(_exe_path):
            open(_exe_path, 'a').close()

        # make sure code is found in PATH
        os.environ['PATH'] += ':' + _exe_path

        # get code using aiida_local_code_factory fixture
        code = aiida_local_code_factory(entrypoint, executable)

        return code

    return _get_code


@pytest.fixture(scope='function')
def inpgen_local_code(create_or_fake_local_code):
    """
    Create, inpgen code
    """
    executable = 'inpgen'  # name of the inpgen executable
    exec_rel_path = 'local_exe/'  # location where it is found
    entrypoint = 'fleur.inpgen'  # entrypoint
    # prepend text to be added before execution
    inpgen_code = create_or_fake_local_code(executable, exec_rel_path, entrypoint)
    return inpgen_code


@pytest.fixture(scope='function')
def fleur_local_code(create_or_fake_local_code):
    """
    Create or load Fleur code
    """
    executable = 'fleur'  # name of the KKRhost executable
    exec_rel_path = 'local_exe/'  # location where it is found
    entrypoint = 'fleur.fleur'  # entrypoint
    fleur_code = create_or_fake_local_code(executable, exec_rel_path, entrypoint)

    return fleur_code


@pytest.fixture(scope='function')
def clear_spec():
    """Ficture to delete the spec of workchains"""
    from aiida_fleur.workflows.scf import FleurScfWorkChain
    from aiida_fleur.workflows.base_fleur import FleurBaseWorkChain
    from aiida_fleur.workflows.eos import FleurEosWorkChain

    def clear_sp():
        # I do not fully comprehend why do we require this for a clean environment
        if hasattr(FleurScfWorkChain, '_spec'):
            # we require this as long we have mutable types as defaults, see aiidateam/aiida-core#3143
            # otherwise we will run into DbNode matching query does not exist
            del FleurScfWorkChain._spec
        if hasattr(FleurBaseWorkChain, '_spec'):
            # we require this as long we have mutable types as defaults, see aiidateam/aiida-core#3143
            # otherwise we will run into DbNode matching query does not exist
            del FleurBaseWorkChain._spec
        if hasattr(FleurEosWorkChain, '_spec'):
            del FleurEosWorkChain._spec

    clear_sp()
    yield  # test runs
    clear_sp()
