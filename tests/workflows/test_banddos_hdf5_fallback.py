"""Tests for the DOS/band reading fallback in FleurBandDosWorkChain.

These tests cover the case where ``banddos.hdf`` is produced by an older
FLEUR HDF5 schema whose ``/Local/DOS`` children (``INT``, ``MT:1s``,
``Sym``, ``Total``, ...) are not compatible with masci-tools' ``FleurDOS``
recipe (which expects the newer multi-segment naming), or whose HDF5 file
lacks the attributes (``/kpts/specialPointLabels``) the
``FleurSimpleBands`` recipe expects. The workchain must fall back to a
direct h5py read instead of exiting with code 310.

They also cover non-collinear (SOC, nspin=4) runs, whose ``banddos.hdf``
stores four spin channels (``up``, ``down``, ``mx``, ``my``) per DOS
quantity: the stock ``FleurDOS`` recipe only splits into ``up``/``down``
and fails on those files, so the recipe path retries with a 4-suffix
variant to keep the spin-resolved and orbital-projected (``MT:*``)
channels.
"""
import io
from pathlib import Path

import h5py
import numpy as np
import pytest

from aiida.engine import ExitCode
from aiida.orm import FolderData, KpointsData

from aiida_fleur.workflows.banddos import (
    _create_aiida_dos_data_impl as create_aiida_dos_data,
    _create_aiida_bands_data_impl as create_aiida_bands_data,
)


BANDDOS_HDF5_PATH = Path(__file__).resolve().parents[2] / 'banddos.hdf'
BANDDOS_BANDS_HDF5_PATH = Path(__file__).resolve().parents[2] / 'banddos_bands.hdf'


def _make_retrieved_with_banddos(banddos_bytes):
    folder = FolderData()
    folder.put_object_from_bytes(banddos_bytes, 'banddos.hdf')
    return folder


def _make_retrieved_from_hdf5(datasets):
    """Build a FolderData holding an in-memory banddos.hdf from ``datasets``."""
    buffer = io.BytesIO()
    with h5py.File(buffer, 'w') as h5:
        for path, array in datasets.items():
            h5.create_dataset(path, data=array)
    return _make_retrieved_with_banddos(buffer.getvalue())


@pytest.fixture
def legacy_banddos_retrieved():
    """FolderData holding the sample banddos.hdf captured from a real run.

    Skipped automatically if the file is not present in the repo root.
    """
    if not BANDDOS_HDF5_PATH.exists():
        pytest.skip(f'Sample banddos.hdf not found at {BANDDOS_HDF5_PATH}')
    return _make_retrieved_with_banddos(BANDDOS_HDF5_PATH.read_bytes())


@pytest.fixture
def legacy_banddos_bands_retrieved():
    """FolderData holding a band-mode banddos.hdf that uses /Local/BS/."""
    if not BANDDOS_BANDS_HDF5_PATH.exists():
        pytest.skip(f'Sample banddos_bands.hdf not found at {BANDDOS_BANDS_HDF5_PATH}')
    return _make_retrieved_with_banddos(BANDDOS_BANDS_HDF5_PATH.read_bytes())


def test_create_aiida_dos_data_legacy_schema(legacy_banddos_retrieved):
    """The sample banddos.hdf (a 4-channel SOC file) must produce an XyData.

    This is a smoke test for the full DOS pipeline: whatever path parses the
    file (recipe path with 4 spin suffixes for the SOC sample, or the direct
    h5py fallback for truly legacy files), the result must be a complete
    XyData with an energy axis and at least one y channel.
    """
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

    Set ``cls.hdf_path`` to point at a specific sample file if the default
    one (DOS-mode ``banddos.hdf``) does not match the test data.
    """

    hdf_path = BANDDOS_HDF5_PATH

    def get_kpointsdata_ncf(self, only_used=True):  # noqa: D401, ARG002
        import h5py
        with h5py.File(self.hdf_path, 'r') as f:
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


def test_create_aiida_bands_data_local_bs_schema(legacy_banddos_bands_retrieved):
    """A band-mode banddos.hdf that uses /Local/BS/ (older FLEUR) must also work.

    The fallback looks up /Local/EV/eigenvalues first, then /Local/BS/eigenvalues.
    This regression test guards against the second lookup going missing again.
    """
    fleurinp = _FakeFleurinp()
    fleurinp.hdf_path = BANDDOS_BANDS_HDF5_PATH
    result = create_aiida_bands_data(fleurinp=fleurinp, retrieved=legacy_banddos_bands_retrieved)
    assert not isinstance(result, ExitCode), (
        f'create_aiida_bands_data returned {result!r}; expected BandsData')
    assert result.label == 'output_banddos_wc_bands'
    result.store()
    kp = result.base.attributes.get('array|kpoints')
    bands = result.base.attributes.get('array|bands')
    assert kp is not None and len(kp) > 0
    assert bands is not None and len(bands) > 0


def test_corrupted_banddos_bands_returns_exit_310():
    """When banddos.hdf is unreadable, return ExitCode 310."""
    folder = FolderData()
    folder.put_object_from_bytes(b'this is not an HDF5 file', 'banddos.hdf')
    fleurinp = _FakeFleurinp()
    result = create_aiida_bands_data(fleurinp=fleurinp, retrieved=folder)
    assert isinstance(result, ExitCode)
    assert result.status == 310


# ---------------------------------------------------------------------------
# Non-collinear (SOC, nspin=4) DOS: the recipe path must split the 4 spin
# channels (up, down, mx, my) instead of degrading to the fallback.
# ---------------------------------------------------------------------------


def test_create_aiida_dos_data_soc_spin_channels(legacy_banddos_retrieved):
    """A 4-channel (SOC) banddos.hdf must go through the recipe path.

    The stock FleurDOS recipe only knows the suffixes ``['up', 'down']`` and
    fails on non-collinear runs ("Too few suffixes provided: Expected 4
    Got: 2"). The recipe path retries with a 4-suffix variant, which keeps
    the spin-resolved channels (``Total_up``/``Total_down``) as well as the
    orbital-projected (``MT:*``) ones.
    """
    result = create_aiida_dos_data(retrieved=legacy_banddos_retrieved)

    assert not isinstance(result, ExitCode), (
        f'create_aiida_dos_data returned {result!r}; expected XyData')
    assert result.label == 'output_banddos_wc_dos'

    result.store()
    y_names = result.base.attributes.get('y_names')
    assert y_names is not None

    # Spin channels are now split up/down (not a single dos_tot = up only).
    assert 'Total_up' in y_names
    assert 'Total_down' in y_names
    assert 'Total_mx' in y_names
    assert 'Total_my' in y_names

    # Orbital-projected channels survive (needed for projected-DOS plots).
    assert any(name.startswith('MT:1s_') for name in y_names)
    assert any(name.startswith('MT:1d_') for name in y_names)

    # The up/down channels are Kramers-degenerate for non-magnetic SOC.
    x_name, _, x_units = result.get_x()
    assert x_name == 'energy'
    y_by_name = {name: array for name, array, _ in result.get_y()}
    assert np.allclose(y_by_name['Total_up'], y_by_name['Total_down'])
    # The recipe path reports energies in eV.
    assert x_units == 'eV'


def test_create_aiida_dos_data_soc_fallback_4ch_minimal():
    """A minimal 4-channel banddos.hdf still works via the fallback.

    The recipe path (including the 4-suffix SOC variant) needs the HDF5
    groups that the recipe's attributes section reads (``/general``,
    ``/atoms``, ...). A file that only contains ``/Local/DOS`` falls through
    to the direct h5py read, which must still return an XyData.
    """
    n_points = 50
    retrieved = _make_retrieved_from_hdf5({
        '/Local/DOS/energyGrid': np.linspace(-1.0, 1.0, n_points),
        '/Local/DOS/Total': np.random.rand(4, n_points),
    })
    result = create_aiida_dos_data(retrieved=retrieved)
    assert not isinstance(result, ExitCode), (
        f'create_aiida_dos_data returned {result!r}; expected XyData')
    assert result.label == 'output_banddos_wc_dos'
    result.store()
    y_names = result.base.attributes.get('y_names')
    assert y_names is not None and len(y_names) >= 1
    # The fallback emits the legacy 4-channel naming (tot, mx, my, mz).
    assert 'dos_tot' in y_names


def test_create_aiida_dos_data_nspin2_minimal():
    """A minimal 2-channel (collinear) banddos.hdf produces spin-resolved dos.

    Guards the n_spin == 2 branch of the fallback when the recipe path
    cannot read the file (missing /general and /atoms groups).
    """
    n_points = 50
    retrieved = _make_retrieved_from_hdf5({
        '/Local/DOS/energyGrid': np.linspace(-1.0, 1.0, n_points),
        '/Local/DOS/Total': np.random.rand(2, n_points),
    })
    result = create_aiida_dos_data(retrieved=retrieved)
    assert not isinstance(result, ExitCode)
    result.store()
    y_names = result.base.attributes.get('y_names')
    assert 'dos_spin_up' in y_names
    assert 'dos_spin_down' in y_names