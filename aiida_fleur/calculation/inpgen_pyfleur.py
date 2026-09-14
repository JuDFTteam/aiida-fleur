###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
"""
Generate a :class:`~aiida_fleur.data.fleurinp.FleurinpData` without running ``inpgen``.

pyfleur carries a pure-Python reimplementation of FLEUR's input generator, so the work the
:class:`~aiida_fleur.calculation.fleurinputgen.FleurinputgenCalculation` CalcJob ships to a
scheduler can be done in-process instead: no ``Code`` node, no queue wait, no remote working
directory, and one copy of ``inp.xml`` rather than two.

The route deliberately goes *through the legacy input text*. ``write_inpgen_file`` already
renders the exact ``aiida.in`` the Fortran binary is given today, so rendering it and parsing
it straight back keeps every ``calc_parameters`` semantic the CalcJob has, and lets a parity
test feed both generators byte-identical input.

This is how every workchain in this package generates its input; none of them can submit the
CalcJob any more. The CalcJob itself remains registered as ``fleur.inpgen`` for anyone who
wants the Fortran generator deliberately, through ``aiida-fleur launch inpgen`` or by hand.

Two things this path does not do, and a caller should know about:

* it emits ``inp.xml`` version 0.39 only, so the FLEUR build that consumes it must be new
  enough to read that. Against an older build, run the CalcJob directly.
* pyfleur acts on most of the legacy namelists but not all of them. The ones it parses and
  then ignores come back as warnings in the report (see :py:func:`generate_fleurinp`), and
  :py:func:`generate_fleurinp_in_workchain` is what puts those in front of a user.
"""
from __future__ import annotations

import io
import os
import tempfile
from typing import Any

from aiida import orm
from aiida.engine import calcfunction as cf

from aiida_fleur.data.fleurinp import FleurinpData

__all__ = ('InpgenGenerationFailed', 'generate_fleurinp', 'generate_fleurinp_in_workchain',
           'generate_fleurinp_ncf', 'generate_inpxml_files', 'report_inpgen_diagnostics',
           'warn_if_inpgen_code_given')

#: settings keys the CalcJob honours that describe *running an executable*, and so mean
#: nothing here. Reported rather than ignored, so tuning them does not silently stop working
IRRELEVANT_SETTINGS = ('additional_retrieve_list', 'remove_from_retrieve_list', 'cmdline')


class InpgenGenerationFailed(Exception):
    """
    In-process input generation failed.

    Carries a message ready to hand to ``control_end_wc``. Raised by
    :py:func:`generate_fleurinp_in_workchain` so that each workchain can map the failure onto
    whichever exit code it declares.
    """


def generate_inpxml_files(
    cell: list,
    atom_sites: list[dict],
    kinds: list[dict],
    pbc: tuple[bool, bool, bool] = (True, True, True),
    params: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> tuple[dict[str, str], list[dict[str, Any]], str]:
    """
    Run pyfleur's input generator and return the files it produced, as text.

    Free of AiiDA on purpose: everything that can go wrong in the translation from
    ``calc_parameters`` to a FLEUR input happens here, where it can be tested without a
    database or a profile.

    :param cell: the 3x3 cell, in Angstrom, as ``StructureData.cell`` gives it
    :param atom_sites: the sites, as ``[site.get_raw() for site in structure.sites]``
    :param kinds: the kinds, as ``[kind.get_raw() for kind in structure.kinds]``
    :param pbc: periodic boundary conditions
    :param params: the ``calc_parameters`` namelist dictionary
    :param settings: the ``settings`` dictionary; ``significant_figures_cell``,
                     ``significant_figures_positions`` and ``profile`` are honoured
    :returns: ``({filename: contents}, diagnostics, summary)``, where a diagnostic is
              ``{'level', 'stage', 'message', 'data'}``

    :raises ValueError: if the parameters cannot be translated
    :raises pyfleur.inpgen.InpgenError: if generation fails
    """
    from pyfleur.inpgen import Inpgen, InpgenOptions
    from pyfleur.inpgen.io.inpgen_in import options_from_namelists, parse_inpgen_input
    from pyfleur.inpgen.report import Report
    from pyfleur.io.fleur_inpgen import write_inpgen_file

    settings = settings or {}

    write_settings = {}
    for key in ('significant_figures_cell', 'significant_figures_positions'):
        if key in settings:
            write_settings[key] = settings[key]

    #the same bytes the CalcJob would have sent to the executable
    text = write_inpgen_file(
        cell,
        atom_sites,
        kinds,
        return_contents=True,
        pbc=pbc,
        input_params=params,
        **write_settings,
    )

    report = Report()
    parsed = parse_inpgen_input(text)

    base = InpgenOptions()
    if settings.get('profile'):
        base = InpgenOptions(profile=settings['profile'])

    #the report picks up a warning per namelist key pyfleur will not act on
    options = options_from_namelists(parsed, base, report)

    generator = Inpgen(source=parsed.to_crystal_input(), options=options, report=report)
    generator.generate()

    files: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as folder:
        #``split='none'`` gives one self-contained inp.xml rather than the default
        #inp.xml + kpts.xml + sym.xml. That is what the CalcJob produces -- it runs the
        #executable with ``-inc +all`` -- so FleurinpData.files stays {'inp.xml'} on both
        #paths and nothing downstream has to learn about xincluded siblings
        for path in generator.write(os.path.join(folder, 'inp.xml'), split='none'):
            with open(path, encoding='utf-8') as handle:
                files[os.path.basename(path)] = handle.read()

    diagnostics = [
        {
            'level': entry.level,
            'stage': entry.stage,
            'message': entry.message,
            'data': entry.data,
        } for entry in report
    ]
    return files, diagnostics, generator.summary()


def generate_fleurinp_ncf(
    structure: orm.StructureData,
    calc_parameters: orm.Dict | None = None,
    settings: orm.Dict | None = None,
) -> dict[str, orm.Node]:
    """
    The body of :py:func:`generate_fleurinp`, without the provenance.

    Useful for a quick check from a shell, and for tests that do not want a calcfunction
    node. Prefer :py:func:`generate_fleurinp` anywhere the result is kept.

    :param structure: the structure to generate an input for
    :param calc_parameters: the inpgen namelists
    :param settings: ``significant_figures_*`` and ``profile`` are honoured
    :returns: ``{'fleurinp': FleurinpData, 'inpgen_report': Dict}``
    """
    from aiida_fleur.calculation.fleurinputgen import _lowercase_dict

    params = None
    if calc_parameters is not None:
        #the CalcJob lowercases the namelist names before writing, so this path must too or
        #the two would disagree on a dict keyed 'Comp'
        params = _lowercase_dict(calc_parameters.get_dict(), 'parameters')

    settings_dict = settings.get_dict() if settings is not None else {}

    files, diagnostics, summary = generate_inpxml_files(
        structure.cell,
        [site.get_raw() for site in structure.sites],
        [kind.get_raw() for kind in structure.kinds],
        pbc=structure.pbc,
        params=params,
        settings=settings_dict,
    )

    fleurinp = FleurinpData()
    with tempfile.TemporaryDirectory() as folder:
        #inp.xml last, so that if a future change reinstates the xincluded siblings they
        #are already on the node when FleurinpData parses inp.xml in set_file
        for name in sorted(files, key=lambda n: n == 'inp.xml'):
            path = os.path.join(folder, name)
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(files[name])
            fleurinp.set_file(path, name)

    fleurinp.label = 'fleurinp'
    fleurinp.description = 'FleurinpData generated in-process by pyfleur (no inpgen run)'

    ignored = [
        d for d in diagnostics
        if d['level'] == 'warning' and d['stage'] == 'read_input'
    ]
    report_node = orm.Dict({
        'summary': summary,
        'diagnostics': diagnostics,
        'ignored_parameters': [f"&{d['data'].get('namelist')} {d['data'].get('key')}" for d in ignored],
        'irrelevant_settings': [k for k in IRRELEVANT_SETTINGS if k in settings_dict],
        'generator': 'pyfleur',
    })
    report_node.label = 'inpgen_report'

    return {'fleurinp': fleurinp, 'inpgen_report': report_node}


@cf
def generate_fleurinp(
    structure: orm.StructureData,
    calc_parameters: orm.Dict | None = None,
    settings: orm.Dict | None = None,
) -> dict[str, orm.Node]:
    """
    Generate a FleurinpData from a structure with pyfleur's in-process input generator.

    The in-process counterpart of
    :class:`~aiida_fleur.calculation.fleurinputgen.FleurinputgenCalculation`. Same inputs,
    same ``fleurinp`` output, no executable.

    Returns a second node, ``inpgen_report``, rather than only logging: it carries every
    diagnostic pyfleur produced, and in particular ``ignored_parameters`` — the
    ``calc_parameters`` entries pyfleur parsed and did not act on, which FLEUR's own inpgen
    *would* have acted on. A caller should surface those; the workchains do it with
    ``self.report``. Without that they are a silent change of physics.

    :param structure: the structure to generate an input for
    :param calc_parameters: the inpgen namelists, as for the CalcJob's ``parameters``
    :param settings: ``significant_figures_cell``, ``significant_figures_positions`` and
                     ``profile`` are honoured; the executable-related keys are recorded in
                     the report as inapplicable
    :returns: ``{'fleurinp': FleurinpData, 'inpgen_report': Dict}``
    """
    return generate_fleurinp_ncf(structure, calc_parameters, settings)


def report_inpgen_diagnostics(report_node: orm.Dict, reporter) -> None:
    """
    Push what pyfleur had to say into a workchain's report.

    The ignored parameters are the point. pyfleur acts on most of the legacy inpgen
    namelists but not all of them, and FLEUR's own inpgen acts on the rest — so a
    ``calc_parameters`` carrying, say, ``&kpt tkb`` produces a valid input that describes a
    slightly different calculation from the one that was asked for. A calcfunction cannot
    call ``self.report``, so it hands the diagnostics back as a node and the caller logs
    them here.

    :param report_node: the ``inpgen_report`` output of :py:func:`generate_fleurinp`
    :param reporter: the calling workchain's ``self.report``
    """
    info = report_node.get_dict()

    ignored = info.get('ignored_parameters') or []
    if ignored:
        reporter(
            f"WARNING: the input generator does not act on {', '.join(ignored)}, which "
            "FLEUR's own inpgen would have. The generated input describes a different "
            'calculation in that respect. To get the Fortran behaviour, run the '
            'fleur.inpgen calculation directly and pass the resulting fleurinp in.')

    irrelevant = info.get('irrelevant_settings') or []
    if irrelevant:
        reporter(f"INFO: {', '.join(irrelevant)} describe running an executable and have no "
                 'effect when the input is generated in-process')

    for entry in info.get('diagnostics') or []:
        if entry.get('level') == 'warning' and entry.get('stage') != 'read_input':
            reporter(f"WARNING: inpgen ({entry.get('stage')}): {entry.get('message')}")


def warn_if_inpgen_code_given(inputs, reporter, port: str = 'inpgen',
                              label: str | None = None) -> None:
    """
    Say so when an inpgen ``Code`` was supplied, because it will not be used.

    The port is still accepted so that submission scripts written against earlier versions
    keep running, but no workchain submits the CalcJob any more. Saying nothing would leave
    a user believing the Fortran generator produced their input.

    :param inputs: the namespace to look in, e.g. ``self.inputs`` or ``self.inputs.scf``
    :param port: the key to look for in that namespace
    :param label: how to name it in the message, when the namespace it lives in makes the
                  bare key ambiguous -- ``'scf.inpgen'`` rather than ``'inpgen'``. Defaults
                  to ``port``
    :param reporter: the calling workchain's ``self.report``
    """
    if port in inputs:
        reporter(f'WARNING: the {label or port!r} code input is ignored. Input generation '
                 'now runs in-process; no inpgen calculation is submitted. Remove it from '
                 'your submission script -- the port will be dropped in the next major '
                 'release.')


def generate_fleurinp_in_workchain(structure, reporter, calc_parameters=None, settings=None,
                                   call_link_label='inpgen'):
    """
    Generate the input inside a workchain step, reporting whatever the generator said.

    The one place a workchain should call the generator from. It keeps the call-link label,
    the diagnostics reporting and the exception mapping in a single place rather than
    repeated per workchain, and it makes the generation a node in the provenance graph the
    same way the CalcJob used to be.

    Failure is signalled by an exception rather than an exit code, because the exit code a
    workchain wants differs between them -- 360 in most, 231 and 234 in ``cutoff_conv``.

    :param structure: the structure to generate for
    :param reporter: the calling workchain's ``self.report``
    :param calc_parameters: the inpgen namelists, or None
    :param settings: ``significant_figures_*`` and ``profile`` are honoured, or None
    :param call_link_label: the provenance link label for the generation node
    :returns: the generated FleurinpData

    :raises InpgenGenerationFailed: with a message ready to pass to ``control_end_wc``
    """
    from pyfleur.inpgen import InpgenError

    inputs = {'structure': structure, 'metadata': {'call_link_label': call_link_label}}
    if calc_parameters is not None:
        inputs['calc_parameters'] = calc_parameters
    if settings is not None:
        inputs['settings'] = settings

    try:
        generated = generate_fleurinp(**inputs)
    except (InpgenError, ValueError) as exc:
        raise InpgenGenerationFailed(f'Input generation failed: {exc}') from exc

    report_inpgen_diagnostics(generated['inpgen_report'], reporter)
    return generated['fleurinp']
