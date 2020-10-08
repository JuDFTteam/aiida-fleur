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

# aiida-testing dependencies

import uuid
import inspect
import shutil
import click
import yaml
import hashlib
import pathlib
import typing as ty
from voluptuous import Schema
from enum import Enum
from aiida.engine import run_get_node
from aiida.engine import ProcessBuilderNamespace
from aiida.common.hashing import make_hash
from aiida.orm import Node, Code, Dict, SinglefileData, List, FolderData, RemoteData
from aiida.orm import CalcJobNode, ProcessNode  #, load_node
from aiida.orm.querybuilder import QueryBuilder
from aiida.manage.caching import enable_caching
from contextlib import contextmanager
### end aiida-testing dep

# aiida_testing.mock_codes in development, not yet a stable dependency..
pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  #, 'aiida_testing.mock_code', 'aiida_testing.export_cache']  # pylint: disable=invalid-name


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
        from aiida.tools.importexport import import_data, export
        from aiida.orm import load_node

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


######################### Fixtures from aiida-testing ###########
# export cache branch, not released
# and mock code
# see https://github.com/aiidateam/aiida-testing/tree/export_cache
# if this becomes stable and is released remove everything below

#### utils


def unnest_dict(nested_dict: ty.Union[dict, ProcessBuilderNamespace]) -> dict:  # type: ignore
    """
    Returns a simple dictionary from a possible arbitray nested dictionary
    or Aiida ProcessBuilderNamespace by adding keys in dot notation, rekrusively
    """
    new_dict = {}
    for key, val in nested_dict.items():
        if isinstance(val, (dict, ProcessBuilderNamespace)):
            unval = unnest_dict(val)  #rekursive!
            for key2, val2 in unval.items():
                key_new = str(key) + '.' + str(key2)
                new_dict[key_new] = val2
        else:
            new_dict[str(key)] = val  # type: ignore
    return new_dict


def get_hash_process(  # type: ignore # pylint: disable=dangerous-default-value
        builder: ty.Union[dict, ProcessBuilderNamespace],
        input_nodes: list = []):
    """ creates a hash from a builder/dictionary of inputs"""

    # hashing the builder
    # currently workchains are not hashed in AiiDA so we create a hash for the filename
    unnest_builder = unnest_dict(builder)
    md5sum = hashlib.md5()
    for key, val in sorted(unnest_builder.items()):  # pylint: disable=unused-variable
        if isinstance(val, Code):
            continue  # we do not include the code in the hash, might be mocked
            #TODO include the code to some extent
        if isinstance(val, Node):
            if not val.is_stored:
                val.store()
            val_hash = val.get_hash()  # only works if nodes are stored!
            input_nodes.append(val)
        else:
            val_hash = make_hash(val)
        md5sum.update(val_hash.encode())
    bui_hash = md5sum.hexdigest()

    return bui_hash, input_nodes


####

#### fixtures


@pytest.fixture(scope='function')
def export_cache(hash_code_by_entrypoint):
    """Fixture to export an AiiDA graph from given node(s)"""

    def _export_cache(node, savepath, default_data_dir=None, overwrite=True):
        """
        Function to export an AiiDA graph from a given node.
        Currenlty, uses the export functionalities of aiida-core
        :param node: AiiDA node which graph is to be exported, or list of nodes
        :param savepath: str or path where the export file is to be saved
        :param overwrite: bool, default=True, if existing export is overwritten
        """
        from aiida.tools.importexport import export

        # we rehash before the export, what goes in the hash is monkeypatched
        qub = QueryBuilder()
        qub.append(ProcessNode)  # rehash all ProcesNodes
        to_hash = qub.all()
        for node1 in to_hash:
            node1[0].rehash()

        if os.path.isabs(savepath):
            full_export_path = savepath
        else:
            if default_data_dir is None:
                default_data_dir = os.path.join(os.getcwd(), 'data_dir')  # May not be best idea
            full_export_path = os.path.join(default_data_dir, savepath)
            #print(full_export_path)

        if isinstance(node, list):
            to_export = node
        else:
            to_export = [node]
        export(to_export, outfile=full_export_path, overwrite=overwrite,
               include_comments=True)  # extras are automatically included

    return _export_cache


# Do we always want to use hash_code_by_entrypoint here?
@pytest.fixture(scope='function')
def load_cache(hash_code_by_entrypoint):
    """Fixture to load a cached AiiDA graph"""

    def _load_cache(path_to_cache=None, node=None, load_all=False):
        """
        Function to import an AiiDA graph
        :param path_to_cache: str or path to the AiiDA export file to load,
            if path_to_cache points to a directory, all import files in this dir are imported
        :param node: AiiDA node which cache to load,
            if no path_to_cache is given tries to guess it.
        :raises : OSError, if import file non existent
        """
        from aiida.tools.importexport import import_data

        if path_to_cache is None:
            if node is None:
                raise ValueError('Node argument can not be None ' "if no explicit 'path_to_cache' is specified")
            #else:  # create path from node
            #    pass
            #    # get default data dir
            #    # get hash for give node
            #    # construct path from that
        else:
            # relative paths given will be completed with cwd
            full_import_path = pathlib.Path(path_to_cache)

        if full_import_path.exists():
            if os.path.isfile(full_import_path):
                # import cache, also import extras
                import_data(full_import_path, extras_mode_existing='ncu', extras_mode_new='import')
            elif os.path.isdir(full_import_path):
                for filename in os.listdir(full_import_path):
                    file_full_import_path = os.path.join(full_import_path, filename)
                    # we curretly assume all files are valid aiida exports...
                    # maybe check if valid aiida export, or catch exception
                    import_data(file_full_import_path, extras_mode_existing='ncu', extras_mode_new='import')
            else:  # Should never get there
                raise OSError(
                    'Path: {} to be imported exists, but is neither a file or directory.'.format(full_import_path))
        else:
            raise OSError('File: {} to be imported does not exist.'.format(full_import_path))

        # need to rehash after import, otherwise cashing does not work
        # for this we rehash all process nodes
        # this way we use the full caching mechanism of aiida-core.
        # currently this should only cache CalcJobNodes
        qub = QueryBuilder()
        qub.append(ProcessNode)  # query for all ProcesNodes
        to_hash = qub.all()
        for node1 in to_hash:
            node1[0].rehash()

    return _load_cache


@pytest.fixture(scope='function')
def with_export_cache(export_cache, load_cache):
    """
    Fixture to use in a with() environment within a test to enable caching in the with-statement.
    Requires to provide an absolutpath to the export file to load or export to.
    Export the provenance of all calcjobs nodes within the test.
    """

    @contextmanager
    def _with_export_cache(data_dir_abspath, calculation_class=None, overwrite=False):
        """
        Contextmanager to run calculation within, which aiida graph gets exported
        """

        # check and load export
        export_exists = os.path.isfile(data_dir_abspath)
        if export_exists:
            load_cache(path_to_cache=data_dir_abspath)

        # default enable globally for all jobcalcs
        if calculation_class is None:
            identifier = None
        else:
            identifier = calculation_class.build_process_type()
        with enable_caching(identifier=identifier):
            yield  # now the test runs

        # This is executed after the test
        if not export_exists or overwrite:
            # in case of yield: is the db already cleaned?
            # create export of all calculation_classes
            # Another solution out of this is to check the time before and
            # after the yield and export ONLY the jobcalc classes created within this time frame
            if calculation_class is None:
                queryclass = CalcJobNode
            else:
                queryclass = calculation_class
            qub = QueryBuilder()
            qub.append(queryclass, tag='node')  # query for CalcJobs nodes
            to_export = [entry[0] for entry in qub.all()]
            export_cache(node=to_export, savepath=data_dir_abspath, overwrite=overwrite)

    return _with_export_cache


@pytest.fixture
def hash_code_by_entrypoint(monkeypatch):
    """
    Monkeypatch .get_objects_to_hash of Code and CalcJobNodes of aiida-core
    to not include the uuid of the computer and less information of the code node in the hash
    """
    from aiida.common.links import LinkType

    def mock_objects_to_hash_code(self):
        """
        Return a list of objects which should be included in the hash of a Code node
        """
        # computer names are changed by aiida-core if imported and do not have same uuid.
        return [self.get_attribute(key='input_plugin')]  #, self.get_computer_name()]

    def mock_objects_to_hash_calcjob(self):
        """
        Return a list of objects which should be included in the hash of a CalcJobNode.
        code from aiida-core, only self.computer.uuid is commented out
        """
        #from pprint import pprint
        #from importlib import import_module
        ignored = list(self._hash_ignored_attributes)
        ignored.append('version')
        objects = [
            #import_module(self.__module__.split('.', 1)[0]).__version__,
            {
                key: val
                for key, val in self.attributes_items()
                if key not in ignored and key not in self._updatable_attributes
            },
            #self.computer.uuid if self.computer is not None else None,
            {
                entry.link_label: entry.node.get_hash()
                for entry in self.get_incoming(link_type=(LinkType.INPUT_CALC, LinkType.INPUT_WORK))
                if entry.link_label not in self._hash_ignored_inputs
            }
        ]
        #pprint('{} objects to hash calcjob: {}'.format(type(self), objects))
        return objects

    monkeypatch.setattr(Code, '_get_objects_to_hash', mock_objects_to_hash_code)
    monkeypatch.setattr(CalcJobNode, '_get_objects_to_hash', mock_objects_to_hash_calcjob)

    # for all other data, since they include the version

    def mock_objects_to_hash(self):
        """
        Return a list of objects which should be included in the hash of all Nodes.
        """
        ignored = list(self._hash_ignored_attributes)  # pylint: disable=protected-access
        ignored.append('version')
        self._hash_ignored_attributes = tuple(ignored)  # pylint: disable=protected-access

        objects = [
            #importlib.import_module(self.__module__.split('.', 1)[0]).__version__,
            {
                key: val
                for key, val in self.attributes_items()
                if key not in self._hash_ignored_attributes and key not in self._updatable_attributes
            },
            #self._repository._get_base_folder(),
            #self.computer.uuid if self.computer is not None else None
        ]
        #print('{} objects to hash: {}'.format(type(self), objects))
        return objects

    # since we still want versioning for plugin datatypes and calcs we only monkeypatch aiida datatypes
    classes_to_patch = [Dict, SinglefileData, List, FolderData, RemoteData]
    for classe in classes_to_patch:
        monkeypatch.setattr(classe, '_get_objects_to_hash', mock_objects_to_hash)

    #BaseData, List, Array, ...


@pytest.fixture(scope='function')
def run_with_cache(export_cache, load_cache):
    """
    Fixture to automatically import an aiida graph for a given process builder.
    """
    def _run_with_cache( # type: ignore
        builder: ty.Union[dict, ProcessBuilderNamespace
                          ],  #aiida process builder class, or dict, if process class is given
        process_class=None,
        label: str = '',
        data_dir: ty.Union[str, pathlib.Path] = 'data_dir',
        overwrite: bool = False,
    ):
        """
        Function, which checks if a aiida export for a given Process builder exists,
        if it does it imports the aiida graph and runs the builder with caching.
        If the cache does not exists, it still runs the builder but creates an
        export afterwards.
        Inputs:
        builder : AiiDA Process builder class,
        data_dir: optional
            Absolute path of the directory where the exported workchain graphs are
            stored.
        overwrite: enforce exporting of a new cache
        #ignore_nodes : list string, ignore input nodes with these labels/link labels to ignore in hash.
        # needed?
        """

        cache_exists = False
        bui_hash, input_nodes = get_hash_process(builder)  # pylint: disable=unused-variable

        if process_class is None:  # and isinstance(builder, dict):
            process_class = builder.process_class  # type: ignore
            # we assume ProcessBuilder, since type(ProcessBuilder) is abc
        #else:
        #    raise TypeError(
        #        'builder has to be of type ProcessBuilder if no process_class is specified'
        #    )
        name = label + str(process_class).split('.')[-1].strip("'>") + '-nodes-' + bui_hash
        print(name)

        # check existence
        full_import_path = pathlib.Path(data_dir) / (name + '.tar.gz')
        # make sure the path is absolute (this is needed by export_cache)
        full_import_path = full_import_path.absolute()
        print(full_import_path)
        if full_import_path.exists():
            cache_exists = True

        if cache_exists:
            # import data from previous run to use caching
            load_cache(path_to_cache=full_import_path)

        # now run process/workchain whatever
        with enable_caching():  # should enable caching globally in this python interpreter
            #yield #test is running
            #res, resnode = run_get_node(builder)
            res, resnode = run_get_node(process_class, **builder)

        # This is executed after the test
        if not cache_exists or overwrite:
            # TODO create datadir if not existent

            # in case of yield:
            # is the db already cleaned?
            # since we do not the stored process node we try to get it from the inputs,
            # i.e to which node they are all connected, with the lowest common pk
            #union_pk: ty.Set[int] = set()
            #for node in input_nodes:
            #    pks = {ent.node.pk for ent in node.get_outgoing().all()}
            #    union_pk = union_pk.union(pks)
            #if len(union_pk) != 0:
            #    process_node_pk = min(union_pk)
            #    #export data to reuse it later
            #    export_cache(node=load_node(process_node_pk), savepath=full_import_path)
            #else:
            #    print("could not find the process node, don't know what to export")

            # if no yield
            export_cache(node=resnode, savepath=full_import_path, overwrite=overwrite)

        return res, resnode

    return _run_with_cache

###### mock-code

CONFIG_FILE_NAME = '.aiida-testing-config.yml'


class ConfigActions(Enum):
    """
    An enum containing the actions to perform on the config file.
    """
    READ = 'read'
    GENERATE = 'generate'
    REQUIRE = 'require'


class Config(collections.abc.MutableMapping):
    """Configuration of aiida-testing package."""

    schema = Schema({'mock_code': Schema({str: str})})

    def __init__(self, config=None):
        self._dict = config or {}
        self.validate()

    def validate(self):
        """Validate configuration dictionary."""
        return self.schema(self._dict)

    @classmethod
    def from_file(cls):
        """
        Parses the configuration file ``.aiida-testing-config.yml``.
        The file is searched in the current working directory and all its parent
        directories.
        """
        cwd = pathlib.Path(os.getcwd())
        config: ty.Dict[str, str]
        for dir_path in [cwd, *cwd.parents]:
            config_file_path = (dir_path / CONFIG_FILE_NAME)
            if config_file_path.exists():
                with open(config_file_path) as config_file:
                    config = yaml.load(config_file, Loader=yaml.SafeLoader)
                    break
        else:
            config = {}

        return cls(config)

    def to_file(self):
        """Write configuration to file in yaml format.
        Writes to current working directory.
        :param handle: File handle to write config file to.
        """
        cwd = pathlib.Path(os.getcwd())
        config_file_path = (cwd / CONFIG_FILE_NAME)

        with open(config_file_path, 'w') as handle:
            yaml.dump(self._dict, handle, Dumper=yaml.SafeDumper)

    def __getitem__(self, item):
        return self._dict.__getitem__(item)

    def __setitem__(self, key, value):
        return self._dict.__setitem__(key, value)

    def __delitem__(self, key):
        return self._dict.__delitem__(key)

    def __iter__(self):
        return self._dict.__iter__()

    def __len__(self):
        return self._dict.__len__()


class EnvKeys(Enum):
    """
    An enum containing the environment variables defined for
    the mock code execution.
    """
    LABEL = 'AIIDA_MOCK_LABEL'
    DATA_DIR = 'AIIDA_MOCK_DATA_DIR'
    EXECUTABLE_PATH = 'AIIDA_MOCK_EXECUTABLE_PATH'
    IGNORE_FILES = 'AIIDA_MOCK_IGNORE_FILES'
    REGENERATE_DATA = 'AIIDA_MOCK_REGENERATE_DATA'


def pytest_addoption(parser):
    """Add pytest command line options."""
    parser.addoption(
        '--testing-config-action',
        type=click.Choice((c.value for c in ConfigActions)),
        default=ConfigActions.READ.value,
        help=f"Read {CONFIG_FILE_NAME} config file if present ('read'), require config file ('require') or " \
             "generate new config file ('generate').",
    )
    parser.addoption('--mock-regenerate-test-data', action='store_true', default=False, help='Regenerate test data.')


@pytest.fixture(scope='session')
def testing_config_action(request):
    return request.config.getoption('--testing-config-action')


@pytest.fixture(scope='session')
def mock_regenerate_test_data(request):
    return request.config.getoption('--mock-regenerate-test-data')


@pytest.fixture(scope='session')
def testing_config(testing_config_action):  # pylint: disable=redefined-outer-name
    """Get content of .aiida-testing-config.yml
    testing_config_action :
        Read config file if present ('read'), require config file ('require') or generate new config file ('generate').
    """
    config = Config.from_file()

    if not config and testing_config_action == ConfigActions.REQUIRE.value:
        raise ValueError(f'Unable to find {CONFIG_FILE_NAME}.')

    yield config

    if testing_config_action == ConfigActions.GENERATE.value:
        config.to_file()


@pytest.fixture(scope='function')
def mock_code_factory(aiida_localhost, testing_config, testing_config_action, mock_regenerate_test_data):  # pylint: disable=redefined-outer-name
    """
    Fixture to create a mock AiiDA Code.
    testing_config_action :
        Read config file if present ('read'), require config file ('require') or generate new config file ('generate').
    """

    def _get_mock_code(
        label: str,
        entry_point: str,
        data_dir_abspath: ty.Union[str, pathlib.Path],
        ignore_files: ty.Iterable[str] = ('_aiidasubmit.sh'),
        executable_name: str = '',
        _config: dict = testing_config,
        _config_action: str = testing_config_action,
        _regenerate_test_data: bool = mock_regenerate_test_data,
    ):
        """
        Creates a mock AiiDA code. If the same inputs have been run previously,
        the results are copied over from the corresponding sub-directory of
        the ``data_dir_abspath``. Otherwise, the code is executed.
        Parameters
        ----------
        label :
            Label by which the code is identified in the configuration file.
        entry_point :
            The AiiDA calculation entry point for the default calculation
            of the code.
        data_dir_abspath :
            Absolute path of the directory where the code results are
            stored.
        ignore_files :
            A list of files which are not copied to the results directory
            after the code has been executed.
        executable_name :
            Name of code executable to search for in PATH, if configuration file does not specify location already.
        _config :
            Dict with contents of configuration file
        _config_action :
            If 'require', raise ValueError if config dictionary does not specify path of executable.
            If 'generate', add new key (label) to config dictionary.
        _regenerate_test_data :
            If True, regenerate test data instead of reusing.
        """
        # we want to set a custom prepend_text, which is why the code
        # can not be reused.
        code_label = f'mock-{label}-{uuid.uuid4()}'

        data_dir_pl = pathlib.Path(data_dir_abspath)
        if not data_dir_pl.exists():
            raise ValueError("Data directory '{}' does not exist".format(data_dir_abspath))
        if not data_dir_pl.is_absolute():
            raise ValueError('Please provide absolute path to data directory.')

        mock_executable_path = shutil.which('aiida-mock-code')
        if not mock_executable_path:
            raise ValueError("'aiida-mock-code' executable not found in the PATH. " +
                             'Have you run `pip install aiida-testing` in this python environment?')

        # try determine path to actual code executable
        mock_code_config = _config.get('mock_code', {})
        if _config_action == ConfigActions.REQUIRE.value and label not in mock_code_config:
            raise ValueError(
                f"Configuration file {CONFIG_FILE_NAME} does not specify path to executable for code label '{label}'.")
        code_executable_path = mock_code_config.get(label, 'TO_SPECIFY')
        if (not code_executable_path) and executable_name:
            code_executable_path = shutil.which(executable_name) or 'NOT_FOUND'
        if _config_action == ConfigActions.GENERATE.value:
            mock_code_config[label] = code_executable_path

        code = Code(input_plugin_name=entry_point, remote_computer_exec=[aiida_localhost, mock_executable_path])
        code.label = code_label
        code.set_prepend_text(
            inspect.cleandoc(f"""
                export {EnvKeys.LABEL.value}="{label}"
                export {EnvKeys.DATA_DIR.value}="{data_dir_abspath}"
                export {EnvKeys.EXECUTABLE_PATH.value}="{code_executable_path}"
                export {EnvKeys.IGNORE_FILES.value}="{':'.join(ignore_files)}"
                export {EnvKeys.REGENERATE_DATA.value}={'True' if _regenerate_test_data else 'False'}
                """))

        code.store()
        return code

    return _get_mock_code


#################### end from aiida-testing ####
