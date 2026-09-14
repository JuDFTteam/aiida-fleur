"""
Local overrides for the inpgen parity suite.

These checks compare two input generators on plain files and never store a node, so the
profile-creating fixtures the top-level ``conftest.py`` applies with ``autouse=True`` are
overridden here with no-ops. Fixture lookup is nearest-first, so redefining the names is
enough.
"""
import pytest


@pytest.fixture(scope='function', autouse=True)
def clear_database_aiida_fleur():
    """No-op: the parity checks never touch a database."""


@pytest.fixture(scope='function', autouse=True)
def configure_aiida_loggers():
    """No-op: the parity checks never emit through the aiida logger."""
