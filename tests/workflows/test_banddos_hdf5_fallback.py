"""Tests for the DOS/band reading fallback in FleurBandDosWorkChain.

These tests cover the case where ``banddos.hdf`` is produced by an older
FLEUR HDF5 schema whose ``/Local/DOS`` children (``INT``, ``MT:1s``,
``Sym``, ``Total``, ...) are not compatible with masci-tools' ``FleurDOS``
recipe (which expects the newer multi-segment naming), or whose HDF5 file
lacks the attributes (``/kpts/specialPointLabels``) the
``FleurSimpleBands`` recipe expects. The workchain must fall back to a
direct h5py read instead of exiting with code 310.
"""
from pathlib import Path

import pytest

from aiida.engine import ExitCode
from aiida.orm import FolderData, KpointsData

from aiida_fleur.workflows.banddos import (
    _create_aiida_dos_data_impl as create_aiida_dos_data,
    _create_aiida_bands_data_impl as create_aiida_bands_data,
)


BANDDOS_HDF5_PATH = Path(__file__).resolve().parents[2] / 'banddos.hdf'


def _make_retrieved_with_banddos(banddos_bytes):
    folder = FolderData()
    folder.put_object_from_bytes(banddos_bytes, 'banddos.hdf')
    return folder


@pytest.fixture
def legacy_banddos_retrieved():
    """FolderData holding the sample banddos.hdf captured from a real run.

    Skipped automatically if the file is not present in the repo root.
    """
    if not BANDDOS_HDF5_PATH.exists():
        pytest.skip(f'Sample banddos.hdf not found at {BANDDOS_HDF5_PATH}')
    return _make_retrieved_with_banddos(BANDDOS_HDF5_PATH.read_bytes())


def test_create_aiida_dos_data_legacy_schema(legacy_banddos_retrieved):
    """The legacy-schema fallback should produce an XyData, not ExitCode 310."""
    result = create_aiida_dos_data(retrieved=legacy_banddos_retrieved)

    assert not isinstance(result, ExitCode), (
        f'create_aiida_dos_data returned {result!r}; expected XyData')
    assert result.label == 'output_banddos_wc_dos'

    result.store()

    # aiida-core versions differ in attributes vs extras, so look in both.
    attrs = {k: v for k, v in result.base.attributes.items()}
    extras = {k: v for k, v in result.base.extras.items()}
    x_arr = attrs.get('array|x_array') or extras.get('x_array')
    x_name = attrs.get('x_name')
    x_unit = attrs.get('x_units') or extras.get('x_units')
    assert x_name == 'energy'
    assert len(x_arr) > 0
    assert x_unit in ('Ha', 'eV')

    y_names = attrs.get('y_names')
    y_units = attrs.get('y_units')
    assert y_names is not None and len(y_names) >= 1
    assert y_units is not None and len(y_units) == len(y_names)


def test_missing_banddos_dos_returns_exit_300():
    """When banddos.hdf is not retrieved, return ExitCode 300."""
    folder = FolderData()
    folder.put_object_from_bytes(b'not used', 'some_other.txt')
    result = create_aiida_dos_data(retrieved=folder)
    assert isinstance(result, ExitCode)
    assert result.status == 300


def test_corrupted_banddos_dos_returns_exit_310():
    """When banddos.hdf is unreadable, return ExitCode 310."""
    folder = FolderData()
    folder.put_object_from_bytes(b'this is not an HDF5 file', 'banddos.hdf')
    result = create_aiida_dos_data(retrieved=folder)
    assert isinstance(result, ExitCode)
    assert result.status == 310


class _FakeFleurinp:
    """Minimal stand-in for FleurinpData used only by create_aiida_bands_data.

    The real FleurinpData.get_kpointsdata_ncf needs to parse inp.xml, which
    requires a full FLEUR input. The fallback in create_aiida_bands_data only
    uses kpoints for BandsData.set_kpointsdata, so we hand it a KpointsData
    built from the same coordinates that are already inside banddos.hdf.
    """

    def get_kpointsdata_ncf(self, only_used=True):  # noqa: D401, ARG002
        import h5py
        with h5py.File(BANDDOS_HDF5_PATH, 'r') as f:
            coords = f['/kpts/coordinates'][:]
        kp = KpointsData()
        kp.set_kpoints(coords)
        return kp


def test_create_aiida_bands_data_legacy_schema(legacy_banddos_retrieved):
    """The legacy-schema fallback should produce a BandsData, not ExitCode 310."""
    fleurinp = _FakeFleurinp()
    result = create_aiida_bands_data(fleurinp=fleurinp, retrieved=legacy_banddos_retrieved)

    assert not isinstance(result, ExitCode), (
        f'create_aiida_bands_data returned {result!r}; expected BandsData')
    assert result.label == 'output_banddos_wc_bands'

    # BandsData has methods to inspect the kpoints/bands arrays.
    result.store()
    kp = result.base.attributes.get('array|kpoints')
    bands = result.base.attributes.get('array|bands')
    units = result.base.attributes.get('units')
    assert kp is not None and len(kp) > 0
    assert bands is not None and len(bands) > 0
    assert units in ('eV', None)  # set_bands(units='eV')


def test_missing_banddos_bands_returns_exit_300():
    """When banddos.hdf is missing, return ExitCode 300."""
    folder = FolderData()
    folder.put_object_from_bytes(b'not used', 'some_other.txt')
    fleurinp = _FakeFleurinp()
    result = create_aiida_bands_data(fleurinp=fleurinp, retrieved=folder)
    assert isinstance(result, ExitCode)
    assert result.status == 300


def test_corrupted_banddos_bands_returns_exit_310():
    """When banddos.hdf is unreadable, return ExitCode 310."""
    folder = FolderData()
    folder.put_object_from_bytes(b'this is not an HDF5 file', 'banddos.hdf')
    fleurinp = _FakeFleurinp()
    result = create_aiida_bands_data(fleurinp=fleurinp, retrieved=folder)
    assert isinstance(result, ExitCode)
    assert result.status == 310