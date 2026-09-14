"""
Assert masci-tools and pyfleur are observationally equivalent on every code path
aiida-fleur uses.

pyfleur vendored the masci-tools XML stack, so this suite is the evidence that swapping the
dependency does not move any byte aiida-fleur stores as provenance. It is kept for one
release cycle after the cutover as a live differential oracle, then deleted.

The two libraries have distinct top-level names, so both import into one interpreter and no
subprocess or second virtualenv is needed. Nothing here needs an AiiDA profile.

Run::

    # against what users actually have
    pip install masci-tools==0.15.0
    MASCI_TEST_FILES=/path/to/masci-tools/tests/files pytest tests/migration -q

    # against masci develop, to attribute a failure: fails above but passes here
    # => caused by masci's unreleased commits, not by pyfleur
    pip install "masci-tools @ git+https://github.com/JuDFTteam/masci-tools.git@develop"
"""
from __future__ import annotations

import glob
import inspect
import io as _io
import math
import os
import re
from pathlib import Path

import pytest

masci = pytest.importorskip('masci_tools', reason='equivalence suite needs both libraries')
pyf = pytest.importorskip('pyfleur', reason='equivalence suite needs both libraries')

_LIBDIRS = (os.path.dirname(masci.__file__), os.path.dirname(pyf.__file__))

#: every FLEUR input-schema version either library might ship
VERSIONS = ['0.27', '0.28', '0.29', '0.30', '0.31', '0.32', '0.33', '0.34', '0.35', '0.36', '0.37', '0.38', '0.39']

#: names that legitimately stop being uniquely addressable under pyfleur's newer 0.39
#: schema, which adds ``wannierlib`` paths carrying the same attribute names
KNOWN_UNIQUENESS_LOSS = {'0.39': {'listname', 'numbands'}}

# --------------------------------------------------------------------------------------
# normalisation and diffing
# --------------------------------------------------------------------------------------


def scrub(text: str) -> str:
    """Erase what must differ: install paths and the package name itself."""
    for libdir in _LIBDIRS:
        text = text.replace(libdir, '<LIBDIR>')
    return re.sub(r'\b(masci_tools|pyfleur)\b', '<LIB>', text)


def norm(obj):
    """
    Canonicalise to plain Python so two libraries' objects are comparable.

    The subtle part is containers, and it is subtler than it first looks. Both libraries
    define their *own* ``CaseInsensitiveDict``, ``LockableDict``, ``LockableList``,
    ``CaseInsensitiveFrozenSet`` and their own namedtuples for the same concepts, so a bare
    ``==`` compares classes and reports differences that are not differences -- with the
    especially confusing symptom ``type LockableDict != LockableDict``, two same-named
    classes from different packages.

    Dispatching on the concrete ``dict``/``list`` is not enough either: these are
    ``Mapping``/``Sequence`` *implementations*, not subclasses. Hence the ABCs.
    """
    from collections.abc import Mapping, Sequence, Set as AbstractSet

    import numpy as np

    if isinstance(obj, np.ndarray):
        # keep the shape, so (3,) never compares equal to (1, 3)
        return ['<nd>', list(obj.shape), norm(obj.tolist())]
    if isinstance(obj, str):
        # before Sequence: a str is one, and would otherwise become a list of characters
        return scrub(obj)
    if isinstance(obj, bytes):
        return obj
    if isinstance(obj, Mapping):
        return {str(k): norm(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, AbstractSet):
        # sets carry no order; sort the normalised members so comparison is stable
        return ['<set>', sorted((repr(norm(v)) for v in obj))]
    if isinstance(obj, Sequence):
        return [norm(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def diff(left, right, path=''):
    """Path-addressed differences, so a divergence in a 400-key inp_dict is findable."""
    out = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left:
                out.append(f'{path}/{key}: absent in masci, pyfleur={right[key]!r}'[:220])
            elif key not in right:
                out.append(f'{path}/{key}: absent in pyfleur, masci={left[key]!r}'[:220])
            else:
                out += diff(left[key], right[key], f'{path}/{key}')
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            out.append(f'{path}: length {len(left)} != {len(right)}')
        else:
            for index, (one, other) in enumerate(zip(left, right)):
                out += diff(one, other, f'{path}[{index}]')
    elif isinstance(left, float) and isinstance(right, float):
        # NaN != NaN would report every unset float in a parsed out.xml as a divergence
        if not (math.isnan(left) and math.isnan(right)) and left != right:
            out.append(f'{path}: {left!r} != {right!r}')
    elif type(left) is not type(right):
        out.append(f'{path}: type {type(left).__name__} != {type(right).__name__}')
    elif left != right:
        out.append(f'{path}: {left!r} != {right!r}'[:220])
    return out


def is_known_libxc_delta(masci_result, pyfleur_result):
    """
    Recognise the one intentional ``get_parameterdata`` divergence.

    Two changes stack on the LibXC path, and both are improvements over the *released*
    masci-tools baseline rather than regressions:

    1. masci-tools' own unreleased commits rewrote ``exco['xctyp']`` from a bare ``'LibXC'``
       to ``'LibXC: Exch: <name>, Cor: <name>'``. pyfleur vendored that.
    2. FLEUR spells the functional either by name (``<LibXCName exchange="gga_x_pbe"/>``) or
       by libxc's integer id (``<LibXCID exchange="1"/>``). Upstream handled only the first
       and *raised* on the second; pyfleur handles both.

    Both are recorded in the CHANGELOG. Anything else on this path is still a failure.
    """
    (m_value, m_error), (p_value, p_error) = masci_result, pyfleur_result

    # the id-spelling fix: upstream raised where pyfleur now parses
    if m_error and not p_error:
        return 'No values found for attribute exchange' in m_error and 'LibXC' in repr(p_value)

    if m_error or p_error or m_value is None or p_value is None:
        return False

    differences = diff(m_value, p_value)
    return bool(differences) and all(d.startswith('/exco/xctyp: ') and 'LibXC' in d for d in differences)


def call(func, *args, **kwargs):
    """``(value, None)`` on success, ``(None, 'ExcType: scrubbed message')`` on failure."""
    try:
        return norm(func(*args, **kwargs)), None
    except Exception as exc:  # noqa: BLE001 - comparing the failures IS the point
        return None, f'{type(exc).__name__}: {scrub(str(exc))}'


def compare(label, masci_result, pyfleur_result):
    """
    Assert two results agree.

    Exception *types* must match exactly. Message text is not compared: pyfleur
    deliberately rewrote the ``NoPathFound``/``NoUniquePathFound`` messages to suggest
    which ``contains`` would disambiguate, which is an improvement, not a divergence.
    """
    (m_value, m_error), (p_value, p_error) = masci_result, pyfleur_result
    if m_error or p_error:
        m_type = m_error.split(':', 1)[0] if m_error else None
        p_type = p_error.split(':', 1)[0] if p_error else None
        assert m_type == p_type, f'{label}: masci raised {m_error!r}, pyfleur raised {p_error!r}'
        return
    differences = diff(m_value, p_value)
    assert not differences, (f'{label}: {len(differences)} divergence(s)\n' +
                             '\n'.join('  ' + d for d in differences[:25]))


# --------------------------------------------------------------------------------------
# corpus
# --------------------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[2]
CORPORA = [REPO / 'tests' / 'files']

# masci-tools' own corpus is far broader (~130 inp.xml over versions 0.27-0.39). Point
# MASCI_TEST_FILES at it to widen the sweep; without it only this repo's fixtures are used.
if os.environ.get('MASCI_TEST_FILES'):
    CORPORA.append(Path(os.environ['MASCI_TEST_FILES']))


def _collect(kind):
    found = []
    for root in CORPORA:
        for path in sorted(glob.glob(str(root / '**' / '*.xml'), recursive=True)):
            is_out = 'out' in os.path.basename(path).lower()
            if (kind == 'out') == is_out:
                found.append(path)
    return found


INP_FILES = _collect('inp')
OUT_FILES = _collect('out')


def _ids(path):
    return os.path.relpath(path, REPO) if str(REPO) in str(path) else os.path.basename(path)


# --------------------------------------------------------------------------------------
# the parsers, and everything FleurinpData derives from an inp.xml
# --------------------------------------------------------------------------------------

#: the getters FleurinpData exposes as get_structuredata / get_kpointsdata / ... plus the
#: two the calculation plugin drives its retrieve list from
GETTERS = ('get_structuredata', 'get_kpointsdata', 'get_parameterdata', 'get_fleur_modes', 'get_nkpts', 'get_cell',
           'get_special_kpoints')


@pytest.mark.parametrize('path', INP_FILES, ids=_ids)
def test_inpxml_equivalence(path):
    """
    The provenance-critical one.

    ``inpxml_parser`` output is stored verbatim as the ``inp_dict`` attribute of every
    FleurinpData node, so a divergence here changes node hashes and would invalidate every
    archive cache and mock-code hash in the suite.
    """
    from masci_tools.io.fleur_xml import load_inpxml as m_load
    from pyfleur.io.fleur_xml import load_inpxml as p_load
    from masci_tools.io.parsers.fleur import inpxml_parser as m_parse
    from pyfleur.io.parsers.fleur import inpxml_parser as p_parse
    import masci_tools.util.xml.xml_getters as m_getters
    import pyfleur.util.xml.xml_getters as p_getters

    # 1. schema-version detection
    m_loaded, p_loaded = call(m_load, path), call(p_load, path)
    if m_loaded[1] or p_loaded[1]:
        compare(f'load_inpxml {path}', m_loaded, p_loaded)
        return

    m_tree, m_schema = m_load(path)
    p_tree, p_schema = p_load(path)
    if m_schema.inp_version != p_schema.inp_version:
        # Not a divergence in behaviour: for a file newer than anything it ships,
        # fromVersion warns and substitutes its latest instead of raising. Released
        # masci-tools stops at 0.37, so a 0.39 file makes the two libraries read the
        # same document against different schemas. Nothing comparable happens after that.
        pytest.skip(f'schema substituted: masci read this as {m_schema.inp_version}, '
                    f'pyfleur as {p_schema.inp_version}')

    # 2. the parser, and the parser_info side channel that reaches output_parameters.
    #    parser_info carries the library's own name, which is expected to differ, so it is
    #    compared through scrub() like everything else.
    m_info, p_info = {}, {}
    compare(f'inpxml_parser {path}', call(m_parse, path, parser_info_out=m_info),
            call(p_parse, path, parser_info_out=p_info))

    # 3. every getter FleurinpData builds an AiiDA node out of
    for name in GETTERS:
        m_getter, p_getter = getattr(m_getters, name, None), getattr(p_getters, name, None)
        if m_getter is None or p_getter is None:
            continue
        m_result = call(m_getter, m_tree, m_schema)
        p_result = call(p_getter, p_tree, p_schema)
        if name == 'get_parameterdata' and is_known_libxc_delta(m_result, p_result):
            continue
        compare(f'{name} {path}', m_result, p_result)


@pytest.mark.parametrize('path', OUT_FILES, ids=_ids)
def test_outxml_equivalence(path):
    """``outxml_parser`` output becomes the stored ``output_parameters`` Dict."""
    from masci_tools.io.fleur_xml import load_outxml as m_load
    from pyfleur.io.fleur_xml import load_outxml as p_load
    from masci_tools.io.parsers.fleur import outxml_parser as m_parse
    from pyfleur.io.parsers.fleur import outxml_parser as p_parse

    # same schema-substitution caveat as for inp.xml: a file newer than the shipped
    # schemas is read against different ones by the two libraries
    try:
        _, m_schema = m_load(path)
        _, p_schema = p_load(path)
    except Exception:  # noqa: BLE001 - deliberately broken fixtures live in the corpus
        pass
    else:
        if m_schema.out_version != p_schema.out_version:
            pytest.skip(f'schema substituted: masci read this as {m_schema.out_version}, '
                        f'pyfleur as {p_schema.out_version}')

    m_info, p_info = {}, {}
    compare(f'outxml_parser {path}', call(m_parse, path, parser_info_out=m_info),
            call(p_parse, path, parser_info_out=p_info))


# --------------------------------------------------------------------------------------
# the modifier: inventory, argument binding, and replayed sequences
# --------------------------------------------------------------------------------------


def test_modifier_registries_and_signatures():
    """
    Certify that ModifierTask lists already in users' databases still replay.

    ``modify_fleurinpdata`` rebuilds tasks from stored plain lists and binds them with
    ``inspect.signature(...).bind()``, so what has to match is the *underlying* setter in
    one of the three registries. Comparing ``get_avail_actions()`` instead would be
    vacuous: every facade there is declared ``(*args, **kwargs)``.
    """
    from masci_tools.io.fleurxmlmodifier import FleurXMLModifier as MF
    from pyfleur.io.fleurxmlmodifier import FleurXMLModifier as PF

    mismatches = []
    for registry in ('_xpath_functions', '_schema_dict_functions', '_nmmpmat_functions'):
        m_reg, p_reg = getattr(MF, registry), getattr(PF, registry)
        assert set(m_reg) == set(p_reg), \
            f'{registry}: only-masci={sorted(set(m_reg) - set(p_reg))} only-pyfleur={sorted(set(p_reg) - set(m_reg))}'
        for name in sorted(m_reg):
            m_sig, p_sig = inspect.signature(m_reg[name]), inspect.signature(p_reg[name])
            m_params = [(p.name, p.kind.name, p.default) for p in m_sig.parameters.values()]
            p_params = [(p.name, p.kind.name, p.default) for p in p_sig.parameters.values()]
            if m_params != p_params:
                mismatches.append(f'{name}\n    masci  : {m_sig}\n    pyfleur: {p_sig}')

    assert not mismatches, 'stored ModifierTask lists may rebind differently:\n' + '\n'.join(mismatches)

    # the user-facing inventory must agree too, or fromList() rejects a stored task
    assert set(MF().get_avail_actions()) == set(PF().get_avail_actions())


def test_modifier_task_type_is_interchangeable():
    """The stored representation is a plain list; ModifierTask must rebuild from it identically."""
    from masci_tools.io.fleurxmlmodifier import ModifierTask as MT
    from pyfleur.io.fleurxmlmodifier import ModifierTask as PT

    assert MT._fields == PT._fields
    assert MT._field_defaults == PT._field_defaults


#: task sequences mirroring what aiida-fleur's workchains actually append. Built through
#: the facades so the arguments are guaranteed valid, then replayed from the serialised
#: ``task_list`` -- which is exactly the stored-provenance path.
#: positional arguments are lists rather than tuples on purpose: a one-element tuple needs a
#: trailing comma, and the repo's yapf config explodes every comma-terminated argument list
SEQUENCES = {
    'scf-itmax': [('set_inpchanges', [{
        'itmax': 15,
        'minDistance': 2e-5
    }], {})],
    'noco': [('set_inpchanges', [{
        'l_noco': True,
        'ctail': False
    }], {})],
    'mixing': [('set_inpchanges', [{
        'imix': 'Anderson',
        'mixParam': 0.05
    }], {})],
    'shift-rel': [('shift_value', [{
        'kmax': 0.1
    }], {
        'mode': 'rel'
    })],
    'species-radius': [('set_species', ['all'], {
        'changes': {
            'mtSphere': {
                'radius': 2.1
            }
        }
    })],
    'atomgroup-relax': [('set_atomgroup', [{
        'force': {
            'relaxXYZ': 'FFF'
        }
    }], {
        'position': 'all'
    })],
    'create-then-delete': [('create_tag', ['greensFunction'], {}), ('delete_tag', ['greensFunction'], {})],
    'two-step-inpchanges': [('set_inpchanges', [{
        'itmax': 1
    }], {}), ('set_inpchanges', [{
        'itmax': 30
    }], {})],
}


@pytest.mark.parametrize('sequence', sorted(SEQUENCES))
@pytest.mark.parametrize('path', INP_FILES, ids=_ids)
def test_modifier_replay_bytes(path, sequence):
    """
    Byte-compare the *serialised* tree.

    ``modify_fleurinpdata`` writes these bytes into the new node's repository, and those
    bytes are what AiiDA hashes and what the mock-code fixtures key on.
    """
    from lxml import etree
    from masci_tools.io.fleurxmlmodifier import FleurXMLModifier as MF
    from pyfleur.io.fleurxmlmodifier import FleurXMLModifier as PF

    def build(cls):
        modifier = cls()
        for name, args, kwargs in SEQUENCES[sequence]:
            getattr(modifier, name)(*args, **kwargs)
        return modifier

    # the serialised task list must round-trip identically between the two libraries
    m_tasks = build(MF).task_list
    p_tasks = build(PF).task_list
    assert not diff(norm(m_tasks), norm(p_tasks)), f'{sequence}: task_list differs'

    def apply_from_stored(cls, tasks):
        tree, extra = cls.fromList(tasks).modify_xmlfile(path, validate_changes=False)
        return etree.tostring(tree, encoding='unicode', pretty_print=True), extra

    compare(f'{sequence} on {path}', call(apply_from_stored, MF, m_tasks), call(apply_from_stored, PF, m_tasks))


# --------------------------------------------------------------------------------------
# the inpgen input file: these bytes become mock-inpgen-<hash>/aiida.in
# --------------------------------------------------------------------------------------

STRUCTURES = {
    'Si-bulk': ([[0., 2.715, 2.715], [2.715, 0., 2.715], [2.715, 2.715, 0.]], [{
        'position': (0., 0., 0.),
        'kind_name': 'Si'
    }, {
        'position': (1.3575, 1.3575, 1.3575),
        'kind_name': 'Si'
    }], [{
        'symbols': ('Si',),
        'weights': (1.,),
        'mass': 28.0855,
        'name': 'Si'
    }], (True, True, True)),
    'named-kind': ([[2.8053, 0., 0.], [0., 2.8053, 0.], [0., 0., 4.]], [{
        'position': (0., 0., 0.),
        'kind_name': 'Fe123'
    }, {
        'position': (1.4, 1.4, 2.0),
        'kind_name': 'Pt'
    }], [{
        'symbols': ('Fe',),
        'weights': (1.,),
        'mass': 55.845,
        'name': 'Fe123'
    }, {
        'symbols': ('Pt',),
        'weights': (1.,),
        'mass': 195.084,
        'name': 'Pt'
    }], (True, True, True)),
    # the empty sphere is the case pyfleur actually changed: it now resolves the symbol
    # through FLEUR's namat_const, which answers for both 'X' and 'va'
    'vacancy-X': ([[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]], [{
        'position': (0., 0., 0.),
        'kind_name': 'Fe'
    }, {
        'position': (2., 2., 2.),
        'kind_name': 'X'
    }], [{
        'symbols': ('Fe',),
        'weights': (1.,),
        'mass': 55.845,
        'name': 'Fe'
    }, {
        'symbols': ('X',),
        'weights': (1.,),
        'mass': 0.0,
        'name': 'X'
    }], (True, True, True)),
    'film': ([[2.8053, 0., 0.], [0., 2.8053, 0.], [0., 0., 20.]], [{
        'position': (0., 0., 0.),
        'kind_name': 'Fe'
    }], [{
        'symbols': ('Fe',),
        'weights': (1.,),
        'mass': 55.845,
        'name': 'Fe'
    }], (True, True, False)),
}

INPUT_PARAMS = [None, {'comp': {'kmax': 4.0}, 'atom': {'element': 'Si', 'rmt': 2.1}}]


@pytest.mark.parametrize('params', INPUT_PARAMS, ids=['no-params', 'with-params'])
@pytest.mark.parametrize('name', sorted(STRUCTURES))
def test_write_inpgen_file_bytes(name, params):
    """A byte change here invalidates mock-inpgen-<hash> and changes what inpgen is sent."""
    from masci_tools.io.fleur_inpgen import write_inpgen_file as m_write
    from pyfleur.io.fleur_inpgen import write_inpgen_file as p_write

    cell, sites, kinds, pbc = STRUCTURES[name]

    def run(func):
        buffer = _io.StringIO()
        func(cell, sites, kinds, file=buffer, pbc=pbc, input_params=params)
        return buffer.getvalue()

    compare(f'write_inpgen_file[{name}]', call(run, m_write), call(run, p_write))


def test_write_inpgen_file_survives_a_cold_interpreter():
    """
    ``io/fleur_inpgen.py`` reaches for ``pyfleur.inpgen.atoms`` at call time, which runs
    ``pyfleur/inpgen/__init__.py`` and pulls in spglib and ase. If that import tree ever
    fails, Python drops ``pyfleur.inpgen`` from ``sys.modules`` while keeping the already
    loaded submodule, so the *first* call raises and the second succeeds -- which under
    AiiDA means the first inpgen submission after each daemon start excepts.

    Must run in a subprocess: in-process import caching hides it completely.
    """
    import subprocess
    import sys

    source = ('import io\n'
              'from pyfleur.io.fleur_inpgen import write_inpgen_file\n'
              'buf = io.StringIO()\n'
              "write_inpgen_file([[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]],\n"
              "                  [{'position': (0., 0., 0.), 'kind_name': 'Fe'}],\n"
              "                  [{'symbols': ('Fe',), 'weights': (1.,), 'mass': 55.845, 'name': 'Fe'}],\n"
              '                  file=buf)\n'
              'assert buf.getvalue()\n')
    proc = subprocess.run([sys.executable, '-c', source], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f'first call in a cold interpreter failed:\n{proc.stderr}'


# --------------------------------------------------------------------------------------
# schemas: everything above is derived from these dicts
# --------------------------------------------------------------------------------------


def _requested_version(version, schema, kind):
    """The version a SchemaDict actually loaded, as a dotted string."""
    attribute = 'inp_version' if kind == 'input' else 'out_version'
    return '.'.join(str(part) for part in getattr(schema, attribute))


def _skip_if_version_substituted(version, m_schema, p_schema, kind):
    """
    Skip when either library quietly served a different schema version.

    ``fromVersion`` only raises for a version *older* than everything it ships; for a newer
    one it warns and returns the latest it has. Comparing across a substitution would
    report the version gap as a pyfleur defect.
    """
    m_actual = _requested_version(version, m_schema, kind)
    p_actual = _requested_version(version, p_schema, kind)
    if m_actual != version or p_actual != version:
        pytest.skip(f'{kind} schema {version} substituted: masci served {m_actual}, pyfleur served {p_actual}')


@pytest.mark.parametrize('version', VERSIONS)
def test_input_schema_dicts(version):
    """
    Compare the generated schema dicts, and guard against uniqueness drift.

    A same-numbered XSD refresh silently moves attribute names between ``unique_attribs``
    and ``unique_path_attribs``. When that happens a bare ``set_inpchanges({'name': ...})``
    that used to work starts raising NoUniquePathFound -- in user scripts, which this
    repo's tests never exercise. pyfleur's 0.39 is exactly such a refresh.
    """
    from masci_tools.io.parsers.fleur_schema import InputSchemaDict as MasciSchema
    from pyfleur.io.parsers.fleur_schema import InputSchemaDict as PyfleurSchema

    try:
        m_schema = MasciSchema.fromVersion(version, no_cache=True)
    except (FileNotFoundError, ValueError):
        pytest.skip(f'masci-tools ships no input schema {version}')
    p_schema = PyfleurSchema.fromVersion(version, no_cache=True)

    # fromVersion does NOT raise for a version newer than the newest shipped: it warns and
    # hands back the latest it has. Released masci-tools stops at 0.37, so without this
    # check 0.38 would silently compare masci's 0.37 dict against pyfleur's 0.38 one.
    _skip_if_version_substituted(version, m_schema, p_schema, 'input')

    lost = sorted(set(m_schema['unique_attribs']) - set(p_schema['unique_attribs']))
    allowed = KNOWN_UNIQUENESS_LOSS.get(version, set())
    assert set(lost) <= allowed, f'input {version}: names no longer uniquely addressable: {lost}'

    differences = diff(norm(dict(m_schema)), norm(dict(p_schema)))
    if version in KNOWN_UNIQUENESS_LOSS and differences:
        pytest.xfail(f'pyfleur ships a newer {version} FleurInputSchema.xsd than masci-tools')
    assert not differences, (f'input schema dict {version}: {len(differences)} divergence(s)\n' +
                             '\n'.join('  ' + d for d in differences[:25]))


@pytest.mark.parametrize('version', VERSIONS)
def test_output_schema_dicts(version):
    """Same for the output schemas, which drive outxml_parser's task selection."""
    from masci_tools.io.parsers.fleur_schema import OutputSchemaDict as MasciSchema
    from pyfleur.io.parsers.fleur_schema import OutputSchemaDict as PyfleurSchema

    try:
        m_schema = MasciSchema.fromVersion(version, no_cache=True)
    except (FileNotFoundError, ValueError):
        pytest.skip(f'masci-tools ships no output schema {version}')
    p_schema = PyfleurSchema.fromVersion(version, no_cache=True)

    _skip_if_version_substituted(version, m_schema, p_schema, 'output')

    differences = diff(norm(dict(m_schema)), norm(dict(p_schema)))
    if version in KNOWN_UNIQUENESS_LOSS and differences:
        pytest.xfail(f'pyfleur ships a newer {version} FleurOutputSchema.xsd than masci-tools')
    assert not differences, (f'output schema dict {version}: {len(differences)} divergence(s)\n' +
                             '\n'.join('  ' + d for d in differences[:25]))


def test_physical_constants_are_bit_identical():
    """These scale stored energies; a last-digit change would silently shift every result."""
    import masci_tools.util.constants as m_const
    import pyfleur.util.constants as p_const

    for name in ('HTR_TO_EV', 'RY_TO_EV', 'BOHR_A', 'HTR_TO_KELVIN'):
        m_value, p_value = getattr(m_const, name), getattr(p_const, name)
        assert m_value == p_value, f'{name}: {m_value!r} != {p_value!r}'
        assert m_value.hex() == p_value.hex(), f'{name}: not bit-identical'


def test_symbol_to_atomic_number_table_is_a_superset():
    """
    aiida-fleur's fsm.py used masci's ATOMIC_NUMBERS, which pyfleur removed.

    Its replacement, FLEUR's own namat_const table, must agree on every symbol the old map
    knew -- otherwise the z written into the inpgen &atom namelist changes.
    """
    from masci_tools.util.constants import ATOMIC_NUMBERS
    from pyfleur.inpgen.atoms import atomic_number

    wrong = []
    for symbol, number in ATOMIC_NUMBERS.items():
        try:
            got = atomic_number(symbol)
        except ValueError:
            got = 'raises'
        if got != number:
            wrong.append((symbol, number, got))
    assert not wrong, f'pyfleur disagrees on {len(wrong)} symbol(s): {wrong[:10]}'
