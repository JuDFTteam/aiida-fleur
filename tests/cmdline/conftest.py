# pylint: disable=redefined-outer-name
"""Fixtures for the command line interface.
Most of these fixtures are taken from the aiida-quantum espresso package since they
are needed to mock commands running aiida process
"""
import pytest
import os
import click


def mock_launch_process(*_, **__):
    """Mock the :meth:`~aiida_fleur.cmdline.util.utils.launch_process` to be a no-op."""
    return


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


@pytest.fixture()
def non_interactive_editor(request):
    """Fixture to patch click's `Editor.edit_file`.

    In `click==7.1` the `Editor.edit_file` command was changed to escape the `os.environ['EDITOR']` command. Our tests
    are currently abusing this variable to define an automated vim command in order to make an interactive command
    non-interactive, and escaping it makes bash interpret the command and its arguments as a single command instead.
    Here we patch the method to remove the escaping of the editor command.

    :param request: the command to set for the editor that is to be called
    """
    from unittest.mock import patch

    from click._termui_impl import Editor

    os.environ['EDITOR'] = request.param
    os.environ['VISUAL'] = request.param

    def edit_file(self, filename):
        import subprocess

        editor = self.get_editor()
        if self.env:
            environ = os.environ.copy()
            environ.update(self.env)
        else:
            environ = None
        try:
            with subprocess.Popen(
                f'{editor} {filename}',  # This is the line that we change removing `shlex_quote`
                env=environ,
                shell=True,
            ) as process:
                exit_code = process.wait()
                if exit_code != 0:
                    raise click.ClickException(f'{editor}: Editing failed!')
        except OSError as exception:
            raise click.ClickException(f'{editor}: Editing failed: {exception}')

    with patch.object(Editor, 'edit_file', edit_file):
        yield
