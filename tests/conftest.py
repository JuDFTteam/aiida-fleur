# pylint: disable=redefined-outer-name
"""Initialise a text database and profile for pytest.
This part of code is copied from aiida-quantumespresso"""

import io
import os
from collections.abc import Mapping
import pytest
import sys
from aiida.orm import Node, Code, Dict, RemoteData, CalcJobNode
from pathlib import Path

CONFTEST_LOCATION = Path(__file__).parent.resolve()

# aiida_testing.mock_codes in development, not yet a stable dependency
# therefore we try to import it and if it fails we skip tests with it

RUN_REGRESSION_TESTS = True
try:
    import aiida_testing
    from aiida_testing.export_cache._fixtures import run_with_cache, export_cache, load_cache, hash_code_by_entrypoint
except ImportError:
    print('AiiDA-testing not in path. Running without regression tests for Workchains and CalcJobs.')
    RUN_REGRESSION_TESTS = False

if RUN_REGRESSION_TESTS:
    pytest_plugins = [
        'aiida.manage.tests.pytest_fixtures', 'aiida_testing.mock_code', 'aiida_testing.export_cache',
        'masci_tools.testing.bokeh'
    ]  # pylint: disable=invalid-name
else:
    pytest_plugins = ['aiida.manage.tests.pytest_fixtures', 'masci_tools.testing.bokeh']


def pytest_addoption(parser):
    parser.addoption('--local-exe-hdf5', action='store_true', help='Is the local executable compiled with HDF5')


def pytest_configure(config):
    """
    Here you can add things by a pytest config, could be also part of a separate file
    So far we add some markers here to be able to execute a certain group of tests
    We make them all lowercaps as convention
    """
    config.addinivalue_line('markers',
                            'regression_test: test using the aiida-testing plugin for workflow regression tests')


def pytest_collection_modifyitems(session, config, items):
    """After test collection modify collection.

    Skip regression test if aiida-tesing is not there
    """
    import aiida

    skip_regression = pytest.mark.skip(
        reason='Workflow regression test is skipped, because aiida-testing is not available')
    aiida_version_skip = pytest.mark.skipif(
        aiida.get_version().startswith('2.'),
        reason='Workflow regression test is skipped, because aiida-testing is not compatible with AiiDA 2.0')

    regression_items = [item for item in items if 'regression_test' in item.keywords]
    if not RUN_REGRESSION_TESTS:
        for item in regression_items:
            item.add_marker(skip_regression)

    for item in regression_items:
        item.add_marker(aiida_version_skip)


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

        return Code(input_plugin_name=entry_point_name, remote_computer_exec=[fixture_localhost, '/bin/ls'])

    return _fixture_code


@pytest.fixture(name='test_file')
def test_file_fixture():
    """Test file fixture"""

    def _test_file(relative_path):
        """
        Return path to file in the tests/files folder
        Returns filesystem path
        """
        return os.fspath(CONFTEST_LOCATION / 'files' / Path(relative_path))

    return _test_file


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
def generate_calc_job_node(fixture_localhost):
    """Fixture to generate a mock `CalcJobNode` for testing parsers."""

    def flatten_inputs(inputs, prefix=''):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in inputs.items():
            if isinstance(value, Mapping):
                flat_inputs.extend(flatten_inputs(value, prefix=prefix + key + '__'))
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def _generate_calc_job_node(entry_point_name,
                                computer=None,
                                test_name=None,
                                inputs=None,
                                attributes=None,
                                store=False,
                                retrieve_list=None):
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

        if computer is None:
            computer = fixture_localhost

        entry_point = format_entry_point_string('aiida.calculations', entry_point_name)

        node = orm.CalcJobNode(computer=computer, process_type=entry_point)
        node.set_attribute('input_filename', 'aiida.in')
        node.set_attribute('output_filename', 'aiida.out')
        node.set_attribute('error_filename', 'aiida.err')
        node.set_option('resources', {'num_machines': 1, 'num_mpiprocs_per_machine': 1})
        node.set_option('withmpi', True)
        node.set_option('max_wallclock_seconds', 1800)

        if retrieve_list is not None:
            node.set_attribute('retrieve_list', retrieve_list)
        if attributes:
            node.set_attribute_many(attributes)

        if inputs:
            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.add_incoming(input_node, link_type=LinkType.INPUT_CALC, link_label=link_label)

        if store:  # needed if test_name is not None
            node.store()

        if test_name is not None:
            basepath = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(basepath, 'parsers', 'fixtures', entry_point_name[len('fleur.'):], test_name)

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
def generate_smco5_structure():
    """Return a `StructureData` representing SmCo5"""

    def _generate_structure():
        """Return a `StructureData` representing SmCo5"""
        from aiida.orm import StructureData
        import numpy as np

        a = 4.9679
        c = 3.9629
        cell = np.array([[a, 0.0, 0.0], [a * np.cos(2 * np.pi / 3), a * np.sin(2 * np.pi / 3), 0.0], [0.0, 0.0, c]])
        structure = StructureData(cell=cell)
        structure.append_atom(position=[0.0, 0.0, 0.0], symbols='Sm', name='Sm')
        structure.append_atom(position=np.array([1 / 3, 2 / 3, 0.0]) @ cell, symbols='Co', name='Co')
        structure.append_atom(position=np.array([2 / 3, 1 / 3, 0.0]) @ cell, symbols='Co', name='Co')
        structure.append_atom(position=np.array([0.0, 0.5, 0.5]) @ cell, symbols='Co', name='Co')
        structure.append_atom(position=np.array([0.5, 0.0, 0.5]) @ cell, symbols='Co', name='Co')
        structure.append_atom(position=np.array([0.5, 0.5, 0.5]) @ cell, symbols='Co', name='Co')

        return structure

    return _generate_structure


@pytest.fixture
def generate_retrieved_data():
    """
    Generate orm.FolderData for retrieved output
    """

    def _generate_retrieved_data(node, name, calc_type='fleur'):
        """
        Generate FolderData for the retrieved output of the given node
        """
        from aiida import orm
        from aiida.common import LinkType

        basepath = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(basepath, 'parsers', 'fixtures', calc_type, name)

        retrieved = orm.FolderData()
        retrieved.put_object_from_tree(filepath)
        retrieved.add_incoming(node, link_type=LinkType.CREATE, link_label='retrieved')
        retrieved.store()
        return retrieved

    return _generate_retrieved_data


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
        """Return a `RemoteData` node pointing to given path."""
        from aiida.common.links import LinkType
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

    def _make_fleurinp(inpxmlfilepath, additional_files=None):
        if additional_files is None:
            additional_files = []
        return fleurinp(files=[inpxmlfilepath] + additional_files)

    return _make_fleurinp


@pytest.fixture
def inpxml_etree():
    """Returns the etree generator"""

    def _get_etree(path, return_schema=False):
        from lxml import etree
        from masci_tools.io.parsers.fleur_schema import InputSchemaDict
        with open(path) as inpxmlfile:
            tree = etree.parse(inpxmlfile)
            version = tree.getroot().attrib['fleurInputVersion']
            schema_dict = InputSchemaDict.fromVersion(version)
        if return_schema:
            return tree, schema_dict
        else:
            return tree

    return _get_etree


@pytest.fixture
def eval_xpath():
    """Return the eval_xpath function"""

    def _eval_xpath(node, xpath, list_return=False):
        from masci_tools.util.xml.common_functions import eval_xpath

        return eval_xpath(node, xpath, list_return=list_return)

    return _eval_xpath


@pytest.fixture
def generate_inputs_base(fixture_code, create_fleurinp, generate_kpoints_mesh):
    """Generate default inputs for a `PwCalculation."""

    def _generate_inputs_base():
        """Generate default inputs for a `PwCalculation."""
        from aiida_fleur.common.defaults import default_options

        TEST_INPXML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'files/inpxml/Si/inp.xml'))

        inputs = {
            'code': fixture_code('fleur'),
            'fleurinpdata': create_fleurinp(TEST_INPXML_PATH),
            'options': Dict(dict=default_options)
        }

        return inputs

    return _generate_inputs_base


@pytest.fixture
def generate_workchain_base(generate_workchain, generate_inputs_base, generate_calc_job_node):
    """Generate an instance of a `FleurBaseWorkChain`."""

    def _generate_workchain_base(exit_code=None, inputs=None, return_inputs=False):
        from plumpy import ProcessState

        entry_point = 'fleur.base'

        if inputs is None:
            inputs = generate_inputs_base()

        if return_inputs:
            return inputs

        process = generate_workchain(entry_point, inputs)

        if exit_code is not None:
            node = generate_calc_job_node('fleur.fleur', inputs={'parameters': Dict()})
            node.set_process_state(ProcessState.FINISHED)
            node.set_exit_status(exit_code.status)

            process.ctx.iteration = 1
            process.ctx.children = [node]

        return process

    return _generate_workchain_base


@pytest.fixture
def generate_workchain():
    """Generate an instance of a `WorkChain`."""

    def _generate_workchain(entry_point, inputs):
        """Generate an instance of a `WorkChain` with the given entry point and inputs.
        :param entry_point: entry point name of the work chain subclass.
        :param inputs: inputs to be passed to process construction.
        :return: a `WorkChain` instance.
        """
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager
        from aiida.plugins import WorkflowFactory

        process_class = WorkflowFactory(entry_point)
        runner = get_manager().get_runner()
        process = instantiate_process(runner, process_class, **inputs)

        return process

    return _generate_workchain


@pytest.fixture
def generate_work_chain_node():
    """Fixture to generate a mock `WorkChainNode` for testing parsers."""

    def flatten_inputs(inputs, prefix=''):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in inputs.items():
            if isinstance(value, Mapping):
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
        from aiida_fleur.common.constants import BOHR_A
        a = 7.497 * BOHR_A
        cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., -1.99285 * BOHR_A), symbols='Fe')
        structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
        structure.append_atom(position=(0., 0., 2.65059 * BOHR_A), symbols='Pt')
        structure.pbc = (True, True, False)

        return structure

    return _generate_film_structure


@pytest.fixture
def generate_sym_film_structure():
    """Return a `StructureData` representing bulk silicon."""

    def _generate_film_structure():
        """Return a `StructureData` representing bulk silicon."""
        from aiida.orm import StructureData
        from aiida_fleur.common.constants import BOHR_A
        a = 7.497 * BOHR_A
        cell = [[0.7071068 * a, 0.0, 0.0], [0.0, 1.0 * a, 0.0], [0.0, 0.0, 0.7071068 * a]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., -1.99285 * BOHR_A), symbols='Fe')
        structure.append_atom(position=(0.5 * 0.7071068 * a, 0.5 * a, 0.0), symbols='Pt')
        structure.append_atom(position=(0., 0., 1.99285 * BOHR_A), symbols='Fe')
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
        with open(jsonfilepath) as jfile:
            node_dict = json.load(jfile)

        return node_dict

    return _read_dict_from_file


@pytest.fixture
def generate_structure2():
    """Return a `StructureData` representing bulk silicon."""

    def _generate_structure2():
        """Return a `StructureData` representing bulk silicon."""
        from aiida.orm import StructureData
        from masci_tools.io.common_functions import rel_to_abs

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
def inpgen_local_code(mock_code_factory, request):
    """
    Create, inpgen code
    """
    #Adapted from shared_datadir of pytest-datadir to not use paths
    #in the tmp copies created by pytest
    data_dir = Path(os.path.join(request.fspath.dirname, 'calculations'))
    if not data_dir.is_dir():
        data_dir.mkdir()

    InpgenCode = mock_code_factory(label='inpgen',
                                   data_dir_abspath=data_dir,
                                   entry_point='fleur.inpgen',
                                   ignore_files=[
                                       '_aiidasubmit.sh', 'FleurInputSchema.xsd', 'scratch', 'usage.json', '*.config',
                                       '*.econfig', 'struct.xsf'
                                   ])

    return InpgenCode


@pytest.fixture(scope='function')
def fleur_local_code(mock_code_factory, pytestconfig, request):
    """
    Create or load Fleur code
    """
    #Adapted from shared_datadir of pytest-datadir to not use paths
    #in the tmp copies created by pytest
    data_dir = Path(os.path.join(request.fspath.dirname, 'calculations'))
    if not data_dir.is_dir():
        data_dir.mkdir()

    FleurCode = mock_code_factory(label='fleur',
                                  data_dir_abspath=data_dir,
                                  entry_point='fleur.fleur',
                                  ignore_files=[
                                      '_aiidasubmit.sh', 'cdnc', 'out', 'FleurInputSchema.xsd', 'FleurOutputSchema.xsd',
                                      'cdn.hdf', 'usage.json', 'cdn*', 'mixing_history*', 'juDFT_times.json',
                                      '*.config', '*.econfig', 'struct*.xsf', 'band.gnu'
                                  ])

    if pytestconfig.getoption('--local-exe-hdf5'):
        FleurCode.description = 'Local executable with HDF5'

    return FleurCode


@pytest.fixture
def import_with_migrate(temp_dir):
    """Import an aiida export file and migrate it

    We want to be able to run the test with several aiida versions,
    therefore imports have to be migrate, but we also do not want to use verdi
    """
    # This function has some deep aiida imports which might change in the future
    _DEFAULT_IMPORT_KWARGS = {'group': None}

    try:
        from aiida.tools.importexport import import_data

        def _import_with_migrate(filename, tempdir=temp_dir, import_kwargs=None, try_migration=True):
            from click import echo
            from aiida.tools.importexport import import_data
            from aiida.tools.importexport import EXPORT_VERSION, IncompatibleArchiveVersionError
            # these are only availbale after aiida >= 1.5.0, maybe rely on verdi import instead
            from aiida.tools.importexport import detect_archive_type
            from aiida.tools.importexport.archive.migrators import get_migrator
            from aiida.tools.importexport.common.config import ExportFileFormat
            if import_kwargs is None:
                import_kwargs = _DEFAULT_IMPORT_KWARGS
            archive_path = filename

            try:
                import_data(archive_path, **import_kwargs)
            except IncompatibleArchiveVersionError:
                #raise ValueError
                if try_migration:
                    echo(f'incompatible version detected for {archive_path}, trying migration')
                    migrator = get_migrator(detect_archive_type(archive_path))(archive_path)
                    archive_path = migrator.migrate(EXPORT_VERSION, None, out_compression='none', work_dir=tempdir)
                    import_data(archive_path, **import_kwargs)
                else:
                    raise

    except ImportError:
        # This is the case for aiida >= 2.0.0
        def _import_with_migrate(filename, import_kwargs=None, try_migration=True):
            from click import echo
            from aiida.tools.archive import import_archive, get_format
            from aiida.common.exceptions import IncompatibleStorageSchema

            if import_kwargs is None:
                import_kwargs = _DEFAULT_IMPORT_KWARGS
            archive_path = filename

            try:
                import_archive(archive_path, **import_kwargs)
            except IncompatibleStorageSchema:
                if try_migration:
                    echo(f'incompatible version detected for {archive_path}, trying migration')
                    archive_format = get_format()
                    version = archive_format.latest_version
                    archive_format.migrate(archive_path, archive_path, version, force=True, compression=6)
                    import_archive(archive_path, **import_kwargs)
                else:
                    raise

    return _import_with_migrate
