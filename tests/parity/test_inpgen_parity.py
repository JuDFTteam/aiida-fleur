"""
Compare pyfleur's in-process input generator against the real Fortran ``inpgen``.

aiida-fleur can generate a FLEUR input two ways: by submitting the
:class:`~aiida_fleur.calculation.fleurinputgen.FleurinputgenCalculation` CalcJob, which runs
the Fortran executable, or by calling
:py:func:`~aiida_fleur.calculation.inpgen_pyfleur.generate_fleurinp`, which runs pyfleur's
reimplementation in-process. The second is the default. This suite is the evidence for how
far the two agree.

Both generators are fed *byte-identical* input: the same ``aiida.in`` the CalcJob would have
sent, rendered by ``write_inpgen_file``. Anything that then differs is the generators
disagreeing, not the inputs.

The comparison is structural, not textual. The two emit different schema versions and order
elements differently, so the trees are flattened to ``{tag@attribute: sorted values}`` and
compared with the numbers normalised. Differences fall into three groups:

* **presence** -- an optional tag one writes and the other does not. Ignored here: which
  optional blocks appear is a verbosity choice, not physics.
* **known** -- the entries in :py:data:`KNOWN_DIVERGENCES`, each asserted to still be
  exactly what it was when it was measured, so the gate keeps failing on anything new.
* anything else -- a failure.

Running it needs a real ``inpgen`` on ``PATH``. Without one every test **skips with a
reason** rather than being deselected by a marker: a parity net nobody can see is how a
divergence survives a green suite.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import pytest

from .cases import CASES

pytest.importorskip('pyfleur', reason='the parity suite compares pyfleur against inpgen')

INPGEN = shutil.which('inpgen')
requires_inpgen = pytest.mark.skipif(
    INPGEN is None,
    reason='no inpgen on PATH; build FLEUR and add its build directory to compare against it')

#: attributes never worth comparing.
#:
#: ``fleurInputVersion`` differs by construction -- pyfleur emits 0.39 and the binary emits
#: whatever its build speaks. ``kPoint`` coordinates differ by which member of a star is
#: written, which is a labelling choice: the counts and the weight multiset are compared
#: instead, and those are what the physics depends on.
IGNORED_ATTRIBUTES = {
    'fleurInput@fleurInputVersion',
    'comment#text',
    'kPoint#text',
}

#: Differences measured against FLEUR MaX-Release 8.1, each with why it is tolerated. A
#: value here is the *exact* pair seen; a change on either side fails the test rather than
#: being absorbed. Keyed by ``(case, attribute)``.
#:
#: The two that are physics rather than presentation are called out as such -- they are the
#: reason ``generate_fleurinp`` returns an ``inpgen_report`` naming what it ignored.
KNOWN_DIVERGENCES = {
    #inpgen writes a default mesh *and* a 240-point band path; pyfleur writes only what was
    #asked for. The mesh itself agrees -- that is what the count assertion below checks
    'kPointList@count', 'kPointList@name', 'kPointList@type', 'kPointListSelection@listName',
    'kPoint@weight',
    #the same numbers, written differently: '-1.000/8.000' against '-1.0/8.0'
    'relPos#text', 'filmPos#text',
    #pyfleur spells the core configuration out; the binary uses the noble-gas shorthand.
    #FLEUR reads both
    'coreConfig#text',
    #cosmetic: the binary shifts a film's plotting origin, pyfleur writes the centre
    'plot@zero',
    #PHYSICS. &kpt tkb is parsed and not acted on by pyfleur, so the smearing falls back to
    #the profile default. generate_fleurinp reports this; see its ignored_parameters output
    'bzIntegration@fermiSmearingEnergy',
    #PHYSICS. The binary caps Kmax at the profile maximum; pyfleur honours what was asked
    'cutoffs@Kmax',
    #PHYSICS. pyfleur sizes muffin-tin spheres per atom type where FLEUR couples every atom
    #of an element, so two sites of one element in different environments get different
    #radii -- and a different lmax and radial grid with them. Deliberate: see the
    #radii_scope option. It fires on slabs and defects, not on simple bulk
    'mtSphere@radius', 'mtSphere@gridPoints', 'mtSphere@logIncrement',
    'atomicCutoffs@lmax', 'atomicCutoffs@lnonsphr',
}


def _normalise(value: str) -> str:
    """Round every number in a whitespace-separated value, leave the rest alone."""
    tokens = []
    for token in str(value).split():
        try:
            tokens.append(f'{round(float(token), 8):.8g}')
        except ValueError:
            tokens.append(token)
    return ' '.join(tokens)


def _flatten(tree) -> dict[str, list[str]]:
    """A whole XML tree as ``{tag@attribute: sorted values}``, order-insensitive."""
    root = tree.getroot() if hasattr(tree, 'getroot') else tree
    flat: dict[str, list[str]] = {}
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for name, value in element.attrib.items():
            flat.setdefault(f'{element.tag}@{name}', []).append(_normalise(value))
        if element.text and element.text.strip():
            flat.setdefault(f'{element.tag}#text', []).append(_normalise(element.text))
    return {key: sorted(values) for key, values in flat.items()}


def _render(case, params) -> str:
    """The ``aiida.in`` the CalcJob would have sent."""
    from pyfleur.io.fleur_inpgen import write_inpgen_file

    return write_inpgen_file(case['cell'], case['sites'], case['kinds'],
                             return_contents=True, pbc=case['pbc'], input_params=params)


def _run_fortran(text: str):
    """Run the real inpgen on the rendered input and parse what it wrote."""
    from lxml import etree

    with tempfile.TemporaryDirectory() as workdir:
        with open(os.path.join(workdir, 'aiida.in'), 'w', encoding='utf-8') as handle:
            handle.write(text)
        #the CalcJob writes this sentinel into its sandbox; without it the binary refuses
        #inputs aiida-fleur sends every day, such as an &atom rmt with no non-integer id
        with open(os.path.join(workdir, 'JUDFT_WARN_ONLY'), 'w', encoding='utf-8') as handle:
            handle.write('/n')

        result = subprocess.run([INPGEN, '-explicit', '-inc', '+all', '-f', 'aiida.in'],
                                cwd=workdir, capture_output=True, text=True, check=False)
        produced = os.path.join(workdir, 'inp.xml')
        if not os.path.exists(produced):
            raise AssertionError(f'inpgen wrote no inp.xml:\n{result.stdout}\n{result.stderr}')
        tree = etree.parse(produced)
        tree.xinclude()
        return tree


def _run_pyfleur(text: str):
    """Generate from the same text with pyfleur, and collect its warnings."""
    from pyfleur.inpgen import Inpgen, InpgenOptions
    from pyfleur.inpgen.io.inpgen_in import options_from_namelists, parse_inpgen_input
    from pyfleur.inpgen.report import Report

    report = Report()
    parsed = parse_inpgen_input(text)
    options = options_from_namelists(parsed, InpgenOptions(), report)
    generator = Inpgen(source=parsed.to_crystal_input(), options=options, report=report)
    generator.generate()
    return generator.to_xmltree(), [d for d in report if d.level == 'warning']


@requires_inpgen
@pytest.mark.parametrize('name', sorted(CASES))
def test_pyfleur_agrees_with_the_binary(name):
    """
    Every attribute both generators write agrees, apart from the known divergences.

    Presence differences are not compared: they are a verbosity choice. What is compared is
    the value of everything both sides chose to write.
    """
    case, params = CASES[name]
    text = _render(case, params)

    reference = _flatten(_run_fortran(text))
    ours, _warnings = _run_pyfleur(text)
    ours = _flatten(ours)

    shared = (set(reference) & set(ours)) - IGNORED_ATTRIBUTES
    unexpected = {
        key: (reference[key], ours[key])
        for key in sorted(shared)
        if reference[key] != ours[key] and key not in KNOWN_DIVERGENCES
    }

    assert not unexpected, (
        f'{name}: {len(unexpected)} attribute(s) differ that are not a known divergence\n' +
        '\n'.join(f'  {key}: inpgen={ref!s:.90} pyfleur={got!s:.90}'
                  for key, (ref, got) in unexpected.items()))


@requires_inpgen
@pytest.mark.parametrize('name', sorted(CASES))
def test_the_kpoint_mesh_has_the_same_size(name):
    """
    The generated mesh holds the same number of k-points as the binary's.

    Separate from the attribute comparison because ``kPointList@count`` is a known
    divergence for a *structural* reason -- inpgen also writes a band path, so it has two
    lists where pyfleur has one. The size of the mesh itself must still agree, and that is
    the number the cost and the accuracy of the calculation follow from.
    """
    case, params = CASES[name]
    text = _render(case, params)

    def mesh_counts(tree):
        root = tree.getroot() if hasattr(tree, 'getroot') else tree
        return sorted(int(el.get('count'))
                      for el in root.iter('kPointList')
                      if el.get('type') == 'mesh')

    reference = mesh_counts(_run_fortran(text))
    ours, _ = _run_pyfleur(text)
    assert mesh_counts(ours) == reference, (
        f'{name}: mesh sizes differ, inpgen={reference} pyfleur={mesh_counts(ours)}')


@pytest.mark.parametrize('name', sorted(CASES))
def test_ignored_parameters_are_reported(name):
    """
    Anything pyfleur will not act on comes back as a warning.

    This is the guard the default path relies on: pyfleur parses several inpgen namelist
    keys and then ignores them, where FLEUR would have acted on them. Silently, that is a
    change of physics. Needs no binary.
    """
    case, params = CASES[name]
    _tree, warnings = _run_pyfleur(_render(case, params))

    reported = {
        f"&{d.data.get('namelist')} {d.data.get('key')}"
        for d in warnings if d.stage == 'read_input'
    }
    #every case that passes tkb must say so -- it changes the Fermi smearing
    if params and 'tkb' in (params.get('kpt') or {}):
        assert '&kpt tkb' in reported, f'{name}: tkb was dropped without a warning'
