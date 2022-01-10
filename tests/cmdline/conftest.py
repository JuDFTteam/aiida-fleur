# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Fixtures for the command line interface.
Most of these fixtures are taken from the aiida-quantum espresso package since they
are needed to mock commands running aiida process
"""
import pytest


def mock_launch_process(*_, **__):
    """Mock the :meth:`~aiida_fleur.cmdline.util.utils.launch_process` to be a no-op."""
    return


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
            from aiida.tools.archive import import_archive
            from aiida.tools.archive import IncompatibleArchiveVersionError, get_format

            if import_kwargs is None:
                import_kwargs = _DEFAULT_IMPORT_KWARGS
            archive_path = filename

            try:
                import_archive(archive_path, **import_kwargs)
            except IncompatibleArchiveVersionError:
                if try_migration:
                    echo(f'incompatible version detected for {archive_path}, trying migration')
                    archive_format = get_format()
                    version = archive_format.latest_version
                    archive_format.migrate(archive_path, archive_path, version, force=True, compression=6)
                    import_archive(archive_path, **import_kwargs)
                else:
                    raise

    return _import_with_migrate


@pytest.fixture
def struct_file_type():
    """Return instance of ``StructureNodeOrFileParamType``."""
    from aiida_fleur.cmdline.util.types import StructureNodeOrFileParamType
    return StructureNodeOrFileParamType()


@pytest.fixture
def run_cli_command():
    """Run a `click` command with the given options.

    The call will raise if the command triggered an exception or the exit code returned is non-zero.
    """

    def _run_cli_command(command, options=None, raises=None):
        """Run the command and check the result.

        :param command: the command to invoke
        :param options: the list of command line options to pass to the command invocation
        :param raises: optionally an exception class that is expected to be raised
        """
        import traceback
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(command, options or [])

        if raises is not None:
            assert result.exception is not None, result.output
            assert result.exit_code != 0
        else:
            assert result.exception is None, ''.join(traceback.format_exception(*result.exc_info))
            assert result.exit_code == 0, result.output

        result.output_lines = [line.strip() for line in result.output.split('\n') if line.strip()]

        return result

    return _run_cli_command


@pytest.fixture
def run_cli_process_launch_command(run_cli_command, monkeypatch):
    """Run a process launch command with the given options.

    The call will raise if the command triggered an exception or the exit code returned is non-zero.

    :param command: the command to invoke
    :param options: the list of command line options to pass to the command invocation
    :param raises: optionally an exception class that is expected to be raised
    """

    def _inner(command, options=None, raises=None):
        """Run the command and check the result."""
        from aiida_fleur.cmdline.util import utils
        monkeypatch.setattr(utils, 'launch_process', mock_launch_process)
        return run_cli_command(command, options, raises)

    return _inner
