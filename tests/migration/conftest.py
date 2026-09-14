"""
Local overrides for the pyfleur/masci-tools equivalence suite.

These checks compare two libraries against each other on plain files. They touch no
database, so the profile-creating fixtures the top-level ``conftest.py`` applies with
``autouse=True`` are overridden here with no-ops -- otherwise every check would drag in a
PostgreSQL service for nothing.

Fixture lookup is nearest-first, so redefining the names is enough; the parent versions
are never instantiated for tests in this directory.
"""
import pytest


@pytest.fixture(scope='function', autouse=True)
def clear_database_aiida_fleur():
    """No-op: these checks never store a node."""


@pytest.fixture(scope='function', autouse=True)
def configure_aiida_loggers():
    """No-op: these checks never emit through the aiida logger."""
