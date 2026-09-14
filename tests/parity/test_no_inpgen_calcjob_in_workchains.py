"""
Assert that no workchain can submit an inpgen calculation.

Input generation moved in-process. The CalcJob still exists and is still registered as
``fleur.inpgen`` -- running the Fortran generator deliberately is supported -- but nothing
under ``aiida_fleur/workflows/`` may reach it any more. Two generators reachable from one
workchain is the state this change removed, and it is easy to reintroduce by copying an old
submission block, so it is worth a test.

Source-level rather than provenance-level on purpose: this needs no database, no profile and
no FLEUR, so it runs everywhere including CI. A provenance assertion over a real workchain
run is the complement to it, not a substitute -- it can only cover the workchains a test
actually executes, while this covers all of them.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

WORKFLOWS = pathlib.Path(__file__).resolve().parents[2] / 'aiida_fleur' / 'workflows'

#: the names that would mean a workchain had got hold of the CalcJob again. ``fleur.inpgen``
#: is the entry point; the other two are the ways to reach it from Python
FORBIDDEN = ('fleur.inpgen', 'get_inputs_inpgen', 'InpgenCalculation')

MODULES = sorted(WORKFLOWS.glob('*.py'))


def _strings_and_names(source: str, path: str):
    """Every string literal and dotted name in a module, so comments do not count."""
    tree = ast.parse(source, path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
        elif isinstance(node, ast.Name):
            found.append(node.id)
        elif isinstance(node, ast.Attribute):
            found.append(node.attr)
        elif isinstance(node, ast.alias):
            found.append(node.name)
            if node.asname:
                found.append(node.asname)
    return found


@pytest.mark.parametrize('module', MODULES, ids=lambda p: p.name)
def test_workchain_cannot_submit_an_inpgen_calculation(module):
    """
    No workchain names the inpgen CalcJob, its entry point, or its input builder.

    Docstrings and comments are exempt -- only real code is inspected -- so a module may
    still explain that generation used to be a job.
    """
    source = module.read_text(encoding='utf-8')
    used = _strings_and_names(source, str(module))

    #`pyfleur.inpgen` is a different thing entirely: it is the in-process generator
    hits = sorted({name for name in used if name in FORBIDDEN})

    assert not hits, (
        f'{module.name} refers to {hits}. Input generation runs in-process; a workchain '
        'must call generate_fleurinp_in_workchain instead of submitting fleur.inpgen.')


def test_the_check_would_notice_a_reintroduced_submission():
    """
    The detector actually fires.

    A test that can only pass is worth nothing, so this pins that the three forbidden names
    are each caught, in the forms they would realistically come back in.
    """
    reintroduced = (
        "from aiida.plugins import CalculationFactory\n"
        "InpgenCalculation = CalculationFactory('fleur.inpgen')\n"
        "from aiida_fleur.tools.common_fleur_wf import get_inputs_inpgen\n")
    used = _strings_and_names(reintroduced, '<test>')

    assert {name for name in used if name in FORBIDDEN} == set(FORBIDDEN)


def test_a_comment_mentioning_inpgen_is_not_a_hit():
    """Prose about the old behaviour must not fail the check."""
    prose = "#this used to submit fleur.inpgen via get_inputs_inpgen\nx = 1\n"
    used = _strings_and_names(prose, '<test>')

    assert not {name for name in used if name in FORBIDDEN}
