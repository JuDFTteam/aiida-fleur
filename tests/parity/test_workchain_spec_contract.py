"""
Pin the public interface of every workchain.

The modularisation refactor moved shared code into ``workflows/_base.py`` and
``workflows/_force_theorem.py``. None of it was supposed to change what a workchain accepts or
produces, so this asserts the contract directly: every workchain still declares the ports,
outputs and exit codes callers depend on.

Beyond that it enforces the conventions written down in
``docs/source/devel_guide/writing_workchains.rst``, so that the next workchain composes with the
existing ones instead of becoming a special case. Every deliberate deviation is listed here as a
named exemption **with a comment saying why**; that list is the record of what is intentional and
what is merely old.

Needs no database and no FLEUR -- building a process spec only needs the class -- so it runs
everywhere, unlike the workchain regression tests.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pathlib
import re
from importlib.metadata import entry_points

import pytest
from aiida.engine import WorkChain

MODULES = [
    'scf', 'base_fleur', 'base_relax', 'relax', 'relax_torque', 'eos', 'strain', 'banddos',
    'orbcontrol', 'cfcoeff', 'jij', 'mae', 'mae_conv', 'ssdisp', 'ssdisp_conv', 'dmi', 'fsm',
    'cutoff_conv', 'initial_cls', 'corehole', 'create_magnetic_film'
]


def workchains():
    """Every WorkChain defined in aiida_fleur.workflows, by module."""
    for name in MODULES:
        mod = importlib.import_module(f'aiida_fleur.workflows.{name}')
        for obj in vars(mod).values():
            if (inspect.isclass(obj) and issubclass(obj, WorkChain) and obj is not WorkChain
                    and obj.__module__ == mod.__name__):
                yield name, obj


ALL = list(workchains())


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_spec_builds(module, cls):
    """Every workchain's spec is constructible and declares a version."""
    spec = cls.spec()
    assert spec.inputs is not None
    assert getattr(cls, '_workflowversion', None), f'{cls.__name__} has no _workflowversion'


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_exit_codes_are_in_the_plugin_range(module, cls):
    """
    0-199 belong to aiida-core. Corehole used to declare 1-9 and InitialCLS returned a bare
    integer, so this is the gate that keeps them out of that range.
    """
    #every Process inherits ERROR_UNSPECIFIED, ERROR_LEGACY_FAILURE, ERROR_INVALID_OUTPUT and
    #ERROR_MISSING_OUTPUT from aiida-core in that range; only what the plugin adds is our business
    inherited = set(WorkChain.spec().exit_codes)
    offenders = {name: ec.status for name, ec in cls.spec().exit_codes.items()
                 if name not in inherited and not name.startswith('_') and 0 < ec.status < 230}
    assert not offenders, f'{cls.__name__} declares exit codes below 230: {offenders}'


#: the starting points a workchain may name, after the v3.0.0 vocabulary harmonisation
ENTRY_POINT_NAMES = {'structure', 'fleurinp', 'remote_data'}
#: ports that used to mean "restart from a previous calculation" under another name
RETIRED_NAMES = {'remote'}


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_no_retired_entry_point_names(module, cls):
    """`remote` was renamed `remote_data`; nothing may reintroduce the old spelling."""
    found = RETIRED_NAMES & set(cls.spec().inputs.keys())
    assert not found, f'{cls.__name__} declares retired input port(s) {found}'


FORCE_THEOREM = ['mae', 'ssdisp', 'dmi']


@pytest.mark.parametrize('module', FORCE_THEOREM)
def test_force_theorem_workchains_share_one_base(module):
    """
    MAE, SSDisp and DMI inherit `define`, `control_end_wc`, `force_wo_scf` and `scf_needed`
    from FleurForceTheoremWorkChain, and keep the physics methods of their own.
    """
    from aiida_fleur.workflows._force_theorem import FleurForceTheoremWorkChain

    cls = dict((m, c) for m, c in ALL if m == module)[module]
    assert issubclass(cls, FleurForceTheoremWorkChain)

    for name in ('_OUTPUT_NAME', '_FT_LABEL', '_FT_DESCRIPTION'):
        assert getattr(cls, name), f'{cls.__name__} does not set {name}'
    assert cls._OUTPUT_NAME in cls.spec().outputs

    for shared in ('define', 'control_end_wc', 'force_wo_scf', 'scf_needed'):
        owner = getattr(cls, shared).__qualname__.split('.')[0]
        assert owner == 'FleurForceTheoremWorkChain', f'{shared} is not shared, it lives on {owner}'

    for own in ('start', 'converge_scf', 'change_fleurinp', 'force_after_scf', 'get_results'):
        owner = getattr(cls, own).__qualname__.split('.')[0]
        assert owner == cls.__name__, f'{own} was moved to {owner}; it carries per-workchain physics'


#: directory holding the workchain modules, for the AST-level checks below
WORKFLOWS_DIR = pathlib.Path(__file__).resolve().parents[2] / 'aiida_fleur' / 'workflows'


def test_every_workchain_is_registered():
    """
    A workchain that is not an entry point cannot be loaded with WorkflowFactory, so from a user's
    point of view it does not exist. This catches a new module that was never added to
    pyproject.toml (and, after a rename, an entry point left pointing at nothing).
    """
    registered = {ep.name: ep for ep in entry_points(group='aiida.workflows') if ep.name.startswith('fleur.')}

    #load_entry_point would need aiida's own registry; the module:class string is enough here
    registered_classes = {ep.value.split(':')[-1] for ep in registered.values()}
    defined_classes = {cls.__name__ for _, cls in ALL}

    missing = sorted(defined_classes - registered_classes)
    assert not missing, f'workchains defined but not registered in pyproject.toml: {missing}'

    dangling = sorted(registered_classes - defined_classes)
    assert not dangling, f'entry points pointing at no workchain in MODULES: {dangling}'


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_workflowversion_is_semver(module, cls):
    """``_workflowversion`` is compared and recorded as a version string, so it has to parse."""
    version = cls._workflowversion
    assert re.fullmatch(r'\d+\.\d+\.\d+', version), \
        f'{cls.__name__}._workflowversion is {version!r}, expected "X.Y.Z"'


#: BaseRestartWorkChain wrappers expose the wrapped process's ports without a namespace and pass
#: them straight through. They own no steering dict and no result node of their own, and what shows
#: up on them is the wrapped process's vocabulary, not this package's
RESTART_WRAPPERS = {'FleurBaseWorkChain', 'FleurBaseRelaxWorkChain'}

#: workchains that do not produce a result Dict of their own.
#: create_magnetic builds a structure rather than computing a quantity, so it returns
#: `magnetic_structure`; the two restart wrappers re-expose what they wrap
NO_RESULT_DICT = RESTART_WRAPPERS | {'FleurCreateMagneticWorkChain'}


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_one_main_result_node(module, cls):
    """
    Every workchain returns exactly one `output_<wcname>_wc_para` holding the physical results.
    Exactly one, because a caller that has to guess which of two result Dicts to read has no
    contract at all.
    """
    if cls.__name__ in NO_RESULT_DICT:
        pytest.skip(f'{cls.__name__} re-exposes or returns a structure instead of a result Dict')

    para = [name for name in cls.spec().outputs.keys() if re.fullmatch(r'output_\w+_wc_para', name)]
    assert len(para) == 1, f'{cls.__name__} declares {len(para)} output_*_wc_para ports: {para}'


#: output link labels that predate the naming convention. Renaming a link label breaks stored
#: provenance, so these stay -- but nothing new may join them
GRANDFATHERED_OUTPUTS = {
    'magnetic_structure',  # create_magnetic, pre-3.0
    'optimized_structure',  # relax, pre-3.0
    'groundstate_denmat',  # orbcontrol, pre-3.0
    'fleurinp',  # scf: the generated input, named after the data type since 2.0
    #jij returns its tensors under their physical names rather than output_jij_wc_*
    'jij_tensor_z',
    'jij_tensor_x',
    'jij_tensor_y',
    'jij_tensor_z_file',
    'jij_tensor_x_file',
    'jij_tensor_y_file',
    'full_jij_tensor',
    'full_jij_tensor_file',
    'jij_interactions',
    'jij_interactions_file',
}


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_output_link_naming(module, cls):
    """
    Further outputs are `output_<wcname>_wc_<what>`, so a result is recognisable in the graph.

    Output *namespaces* are exempt on purpose: a re-exposed sub-process goes into a namespace named
    after the role it played (`last_calc`, `last_scf`, `banddos_calc`, `groundstate_scf`), which is
    itself the convention.
    """
    from aiida.engine.processes.ports import PortNamespace

    if cls.__name__ in RESTART_WRAPPERS:
        #these expose the wrapped process's outputs into the root namespace unchanged, so what shows
        #up here is CalcJob vocabulary (`retrieved`, `remote_folder`, `relax_parameters`), which
        #follows the aiida-core conventions rather than this one
        pytest.skip(f'{cls.__name__} re-exposes the wrapped process outputs verbatim')

    offenders = sorted(name for name, port in cls.spec().outputs.items()
                       if not isinstance(port, PortNamespace)
                       and not name.startswith('output_') and name not in GRANDFATHERED_OUTPUTS)
    assert not offenders, (f'{cls.__name__} declares output(s) {offenders} that neither start with '
                           "'output_' nor are grandfathered; see GRANDFATHERED_OUTPUTS")


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_steering_dicts_have_defaults(module, cls):
    """
    A `wf_parameters` port is merged onto `_default_wf_para` and an `options` port onto
    `_default_options`. A port without its defaults dict cannot be merged; a defaults dict without
    its port is dead weight that only misleads -- five of those were removed in 3.0.0.
    """
    inputs = cls.spec().inputs
    is_wrapper = cls.__name__ in RESTART_WRAPPERS

    if 'wf_parameters' in inputs and not is_wrapper:
        assert getattr(cls, '_default_wf_para', None) is not None, \
            f'{cls.__name__} takes wf_parameters but defines no _default_wf_para'
    #note the reverse does not hold: create_magnetic keeps defaults it hands to sub-workchains

    has_options_port = 'options' in inputs
    has_options_defaults = getattr(cls, '_default_options', None) is not None
    if has_options_port:
        #FleurBaseWorkChain deliberately has no defaults: `options` is required there, so omitting
        #it is a hard validation error rather than a silent single-core run
        if not is_wrapper:
            assert has_options_defaults, f'{cls.__name__} takes options but defines no _default_options'
    else:
        assert not has_options_defaults, \
            f'{cls.__name__} defines _default_options but declares no options port; it can never be read'


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_no_reversed_defaults_spelling(module, cls):
    """`_wf_default` was the reversed spelling three workchains used; it was renamed in 3.0.0."""
    assert not hasattr(cls, '_wf_default'), \
        f'{cls.__name__} defines _wf_default; the name is _default_wf_para'


#: the only camelCase port in the package, on a vestigial accepted-and-ignored input
CAMELCASE_PORT_EXEMPTIONS = {('FleurFsmWorkChain', 'inpgenCompRes')}


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_port_names_are_snake_case(module, cls):
    """Port names are lower_with_underscores; they are public API and appear in every script."""
    offenders = sorted(name for name in cls.spec().inputs.keys()
                       if not re.fullmatch(r'[a-z][a-z0-9_]*', name)
                       and (cls.__name__, name) not in CAMELCASE_PORT_EXEMPTIONS)
    assert not offenders, f'{cls.__name__} declares non-snake_case input port(s) {offenders}'


#: The shared exit-code meanings from docs/source/user_guide/hints/exit_codes.rst. Since v3.0.0
#: these numbers mean the same thing in every workchain, so a script can branch on the status
#: without knowing which workchain produced the node. One number -> one name.
CANONICAL_EXIT_CODES = {
    230: 'ERROR_INVALID_INPUT_PARAM',
    231: 'ERROR_INVALID_INPUT_CONFIG',
    233: 'ERROR_INVALID_CODE_PROVIDED',
    235: 'ERROR_CHANGING_FLEURINPUT_FAILED',
    236: 'ERROR_INVALID_INPUT_FILE',
    311: 'ERROR_VACUUM_SPILL_RELAX',
    313: 'ERROR_MT_RADII_RELAX',
    334: 'ERROR_REFERENCE_CALCULATION_FAILED',
    335: 'ERROR_REFERENCE_CALCULATION_NOREMOTE',
    345: 'ERROR_SCF_FAILED',
    360: 'ERROR_INPGEN_CALCULATION_FAILED',
    361: 'ERROR_FLEUR_CALCULATION_FAILED',
    362: 'ERROR_DID_NOT_CONVERGE',
}

#: 343/344 mean "all / some sub-runs of a scan failed", but each workchain names what it scanned
#: over (SQAs, q-vectors, configurations, FSM values). The shape is fixed, the noun is not.
CANONICAL_EXIT_CODE_PATTERNS = {
    343: re.compile(r'ERROR_(ALL|NO_SUCCESSFUL)_\w+'),
    344: re.compile(r'ERROR_SOME_\w+_FAILED'),
}

#: Known drift, not a decision: 360 means "input generation failed" everywhere, but CutoffConv
#: spells it ERROR_INITIAL_INPGEN_FAILED while scf/corehole/fsm/orbcontrol use
#: ERROR_INPGEN_CALCULATION_FAILED. Renaming it is an API change, so it is recorded here rather
#: than silently allowed. Remove this entry when the name is unified.
EXIT_CODE_NAME_EXEMPTIONS = {('FleurCutoffConvWorkChain', 360, 'ERROR_INITIAL_INPGEN_FAILED')}


def _declared_exit_codes(cls):
    """The exit codes this plugin declares, without the four every Process inherits."""
    inherited = set(WorkChain.spec().exit_codes)
    return {name: ec.status for name, ec in cls.spec().exit_codes.items()
            if name not in inherited and not name.startswith('_')}


@pytest.mark.parametrize('module,cls', ALL, ids=[f'{m}:{c.__name__}' for m, c in ALL])
def test_shared_exit_codes_use_their_canonical_name(module, cls):
    """
    A number in the shared range carries the meaning the exit-code table gives it.

    Checked in both directions, because either half alone is easy to satisfy by accident: a shared
    number must use the canonical name, and the canonical name must not be attached to some other
    number.
    """
    declared = _declared_exit_codes(cls)

    for name, status in sorted(declared.items()):
        if (cls.__name__, status, name) in EXIT_CODE_NAME_EXEMPTIONS:
            continue

        expected = CANONICAL_EXIT_CODES.get(status)
        if expected is not None:
            assert name == expected, (
                f'{cls.__name__} declares {status} as {name}; {status} means {expected} in every '
                'other workchain. Reuse the shared meaning or pick a free number >= 380.')

        pattern = CANONICAL_EXIT_CODE_PATTERNS.get(status)
        if pattern is not None:
            assert pattern.fullmatch(name), (
                f'{cls.__name__} declares {status} as {name}, which does not match '
                f'{pattern.pattern}; {status} is reserved for "all/some sub-runs of a scan failed".')

    #`declared` maps name -> status, so this is the other direction: a canonical name that ended up
    #on some other number
    for status, canonical in CANONICAL_EXIT_CODES.items():
        actual = declared.get(canonical)
        if actual is not None and actual != status:
            if (cls.__name__, actual, canonical) in EXIT_CODE_NAME_EXEMPTIONS:
                continue
            raise AssertionError(
                f'{cls.__name__} declares {canonical} as {actual}, but that name means '
                f'exit code {status} everywhere else.')


def _functions_with_merge(tree):
    """Yield (function node, name of the raw dict) for each merge_parameter_dicts assignment."""
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            if not (isinstance(call.func, ast.Name) and call.func.id == 'merge_parameter_dicts'):
                continue
            #the assignment we care about is `self.ctx.wf_dict = merge_parameter_dicts(raw, ...)`
            targets = [t for t in node.targets
                       if isinstance(t, ast.Attribute) and t.attr == 'wf_dict']
            if not targets or not call.args or not isinstance(call.args[0], ast.Name):
                continue
            yield func, call.args[0].id, node.lineno


@pytest.mark.parametrize('module', sorted(MODULES))
def test_merged_wf_dict_is_not_bypassed(module):
    """
    After merging onto the defaults, only ``self.ctx.wf_dict`` holds the full parameter set.

    ``merge_parameter_dicts`` returns a *new* dict and leaves its argument untouched, so the raw
    dict still holds only what the user typed -- and is empty when ``wf_parameters`` was omitted.
    Three workchains subscripted it on the line after the merge and raised ``KeyError`` for every
    run that did not pass ``wf_parameters``.

    Reading it with ``.get(key, <literal>)`` is not caught here because it cannot crash, but it is
    just as wrong: it duplicates a default that will drift from ``_default_wf_para``.
    """
    path = WORKFLOWS_DIR / f'{module}.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))

    offenders = []
    for func, raw_name, merge_line in _functions_with_merge(tree):
        for node in ast.walk(func):
            if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
                    and isinstance(node.value, ast.Name) and node.value.id == raw_name
                    and node.lineno > merge_line):
                offenders.append(f'{path.name}:{node.lineno} reads {raw_name}[...] '
                                 f'after the merge on line {merge_line}')

    assert not offenders, ('the merged parameters live in self.ctx.wf_dict; the raw dict holds only '
                           'what the user passed:\n  ' + '\n  '.join(offenders))
