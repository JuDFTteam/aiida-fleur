.. _writing_workchains:

Writing a new FLEUR WorkChain
=============================

.. contents::
   :local:

A workchain is **software other people build on**, not a script. Its input and output names become
part of stored provenance the moment someone runs it, and changing them later breaks their
databases. This page describes the shape every aiida-fleur workchain has, so that a new one composes
with the existing ones instead of becoming a special case.

The conventions themselves are listed in ``STYLE_CONVENTION.txt`` at the repository root; this page
explains how to apply them and which helpers already exist so you do not re-implement them. The
user-facing side of the same contract is :ref:`using_workflows` — read it first, because everything
promised there is what you are implementing.

Where the code goes
+++++++++++++++++++

One workchain per module in ``aiida_fleur/workflows/``, named after the physics
(``eos.py``, ``banddos.py``). The class is registered as an entry point in ``pyproject.toml``::

    [project.entry-points."aiida.workflows"]
    "fleur.myprop" = "aiida_fleur.workflows.myprop:FleurMyPropWorkChain"

AiiDA only sees it after a reinstall::

    pip install -e .[testing,pre-commit,graphs,docs]

A module whose name starts with an underscore is deliberately **not** an entry point — that is how
``_base.py`` and ``_force_theorem.py`` hold shared code without appearing as workchains.

Pick the right layer
++++++++++++++++++++

The layers stack strictly, each wrapping the next::

    FleurXxxWorkChain (physics: eos, mae, jij, banddos, relax, orbcontrol, ...)
      └─ FleurScfWorkChain            (fleur.scf — converge charge density)
           └─ FleurBaseWorkChain      (fleur.base — error handling / restarts)
                └─ FleurCalculation   (fleur.fleur — the CalcJob)

Your workchain almost always belongs at the top and drives ``FleurScfWorkChain``. Do **not** submit
``FleurCalculation`` or an inpgen CalcJob directly: you would lose the restart and error handling
that ``FleurBaseWorkChain`` provides, and input generation now runs in-process anyway. This is
enforced — ``tests/parity/test_no_inpgen_calcjob_in_workchains.py`` fails the build if any module
under ``aiida_fleur/workflows/`` references ``fleur.inpgen``, ``get_inputs_inpgen`` or
``InpgenCalculation``.

If you only need a single FLEUR run with error handling, drive ``FleurBaseWorkChain`` through
:py:func:`~aiida_fleur.tools.common_fleur_wf.get_inputs_fleur` rather than building its inputs by
hand — it is what translates the workchain vocabulary (``fleur``, ``remote_data``) into the CalcJob
vocabulary (``code``, ``parent_folder``).

The class skeleton
++++++++++++++++++

Class attributes
----------------

Three, with these exact names::

    class FleurMyPropWorkChain(WorkChain):
        """One sentence on what this computes, then the details."""

        _workflowversion = '0.1.0'

        _default_wf_para = {
            'some_physical_knob': 1.0,
            'add_comp_para': {
                'only_even_MPI': False,
                'forbid_single_mpi': False,
                'max_queue_nodes': 20,
                'max_queue_wallclock_sec': 86400,
            },
            'inpxml_changes': [],
        }

        _default_options = {
            'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 1},
            'max_wallclock_seconds': 6 * 60 * 60,
            'queue_name': '',
            'custom_scheduler_commands': '',
            'import_sys_environment': False,
            'environment_variables': {},
        }

``_default_wf_para`` is required whenever you declare a ``wf_parameters`` port. Declare
``_default_options`` **only** if you also declare an ``options`` port — five workchains used to
carry a ``_default_options`` they never read, which only misled readers.

``num_mpiprocs_per_machine`` is not optional in ``_default_options``: ``FleurBaseWorkChain`` turns
resource optimisation off entirely when it is missing, and reports "Computation resources were not
optimised" for every run.

Do not spell these ``_wf_default`` — three workchains used the reversed name and were renamed in
3.0.0.

``define()``
------------

::

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(FleurScfWorkChain,
                           namespace='scf',
                           namespace_options={'required': False, 'populate_defaults': False})
        spec.input('wf_parameters', valid_type=Dict, required=False)
        spec.input('fleur', valid_type=Code, required=True)
        spec.input('remote_data', valid_type=RemoteData, required=False)
        spec.input('fleurinp', valid_type=FleurinpData, required=False)
        spec.input('options', valid_type=Dict, required=False)
        spec.inputs.validator = validate_fleur_entry_points

        spec.outline(cls.start,
                     if_(cls.scf_needed)(cls.converge_scf, cls.run_after_scf)
                     .else_(cls.run_wo_scf),
                     cls.get_results, cls.return_results)

        spec.output('output_myprop_wc_para', valid_type=Dict)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')
        spec.exit_code(231, 'ERROR_INVALID_INPUT_CONFIG', message='Invalid input configuration.')
        ...

Points that matter:

* **The namespace name is public API.** ``spec.expose_inputs(FleurScfWorkChain, namespace='scf')``
  means users write ``inputs['scf'][...]`` forever. Name a namespace after the **role** the
  sub-process plays (``scf``, ``final_scf``, ``scf_no_ldau``, ``orbcontrol``), never after a class.
* **Use the three starting-point names** — ``structure``, ``fleurinp``, ``remote_data``. No
  synonyms. ``remote`` in particular was retired in 3.0.0 and a test blocks its return.
* **Prefer a spec validator to a runtime check.** If your rule is "either the ``scf`` namespace or a
  ``remote_data``", set ``spec.inputs.validator = validate_fleur_entry_points``
  (:py:mod:`aiida_fleur.tools.common_fleur_wf`) and the illegal combination is rejected at
  submission instead of creating a node that aborts in its first step. Only write your own check if
  your workchain has extra entry points, as ``jij`` and ``orbcontrol`` do.
* **Declare an output ``required=False`` if you emit it conditionally.** Six ports were declared
  required but only emitted on the happy path, so the engine marked the workchain failed for a
  missing output whenever anything went wrong.
* Do not read a port you have not declared. ``self.inputs.get('label', ...)`` in two workchains
  silently always returns the fallback, because no ``label`` port exists.

The ``start`` step
------------------

Every workchain merges ``wf_parameters`` onto its defaults the same way. Use the helpers in
:py:mod:`aiida_fleur.workflows._base` rather than a hand-rolled loop::

    from aiida_fleur.workflows._base import merge_parameter_dicts, unknown_parameter_keys

    def start(self):
        self.report(f'Started MyProp workflow version {self._workflowversion}')
        self.ctx.info, self.ctx.warnings, self.ctx.errors = [], [], []
        self.ctx.successful = True

        wf_dict = self.inputs.wf_parameters.get_dict() if 'wf_parameters' in self.inputs else {}

        extra_keys = unknown_parameter_keys(wf_dict, self._default_wf_para)
        if extra_keys:
            self.report(f'ERROR: input wf_parameters for MyProp contains extra keys: {extra_keys}')
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        self.ctx.wf_dict = merge_parameter_dicts(wf_dict, self._default_wf_para, nested=False)

.. warning::

    **After the merge, only ever read** ``self.ctx.wf_dict``. The raw ``wf_dict`` holds only what
    the user typed; it is empty when ``wf_parameters`` was omitted. Three workchains subscripted it
    on the line after the merge and raised ``KeyError`` for every run that did not pass
    ``wf_parameters``. ``tests/parity/test_workchain_spec_contract.py`` now fails the build on this
    pattern. The same applies to ``wf_dict.get(key, <literal>)``: it silently duplicates a default
    that will drift from ``_default_wf_para``.

Rejecting unknown keys is not optional. Three workchains still silently ignore them, which turns a
typo into a run with the wrong physics; do not copy them.

The ``nested`` flag
^^^^^^^^^^^^^^^^^^^

``nested=True`` merges a dict-valued default key-by-key, so a user who sets one sub-key keeps the
others. ``nested=False`` lets the user's sub-dict replace the default wholesale.

Choose per key semantics, not per taste:

* ``nested=False`` when a dict-valued key is an **open-ended map** — keyed by atom label, q-vector
  name, species. Merging defaults into ``beta``, ``sqas``, ``q_vectors``, ``references`` or
  ``replacements`` would silently add entries the user never asked for.
* ``nested=True`` when it is a **fixed set of knobs**, such as ``add_comp_para`` or ``force_dict``.

Whichever you pick, document it on the workchain, because it changes what a partial
``add_comp_para`` does.

Applying ``inpxml_changes``
---------------------------

A stored node is immutable, so ``inp.xml`` edits are recorded as a task list and replayed inside the
``modify_fleurinpdata`` calcfunction. Never mutate a stored ``FleurinpData``.

If you only replay the user's list::

    from aiida_fleur.workflows._base import apply_inpxml_changes

    modified, failure = apply_inpxml_changes(fleurin, self.ctx.wf_dict['inpxml_changes'], self.report)
    if failure == 'invalid':
        return self.exit_codes.ERROR_INVALID_INPUT_FILE
    if failure is not None:
        self.control_end_wc('Applying the requested inp.xml changes failed.')
        return self.exit_codes.ERROR_CHANGING_FLEURINPUT_FAILED
    self.ctx.fleurinp = modified

If you also add changes of your own, append them with the ``inpxml_changes`` context manager first,
so that yours and the user's go through one validated replay::

    from aiida_fleur.data.fleurinpmodifier import inpxml_changes

    with inpxml_changes(self.ctx.wf_dict) as fm:
        fm.set_inpchanges({'itmax': 1, 'l_soc': True})

If you build a :py:class:`~aiida_fleur.data.fleurinpmodifier.FleurinpModifier` directly — because
you need a k-point list or a Green's-function contour — finish with
:py:func:`~aiida_fleur.workflows._base.validate_and_freeze`, which validates against the FLEUR
schema and maps the failure onto the same two exit codes. Do not call ``freeze()`` without
validating; several older workchains do and produce an ``inp.xml`` that only fails once FLEUR runs.

To hand changes **down** to a sub-workchain, use the context manager on its input namespace::

    with inpxml_changes(input_scf) as fm:
        fm.set_species_label('49999', {'special': {'socscale': 0.0}})

Collecting sub-workchain results
--------------------------------

For a workchain that scans a parameter and collects sub-SCFs, use
:py:func:`~aiida_fleur.workflows._base.collect_scf_results` instead of writing the loop::

    results, failed = collect_scf_results(self.ctx.scf_runs, self.report)

It skips a failed sub-SCF rather than aborting. Note the exception to catch is ``NotExistent``, not
``KeyError``: ``calc.outputs.output_scf_wc_para`` raises ``NotExistentAttributeError``, which
derives from ``AttributeError``. Four workchains guarded it with ``except KeyError``, so the handler
was dead and the whole workchain crashed on one failed sub-run.

Naming
++++++

Class
    ``FleurNameWorkChain``. The ``Fleur`` prefix avoids collisions in multi-code environments; other
    plugins have an ``EosWorkChain`` too.

Input ports
    ``lower_with_underscores``. ``structure`` / ``fleurinp`` / ``remote_data`` for starting points,
    ``fleur`` for the code, ``wf_parameters`` and ``options`` for the two steering dicts.

Result node
    ``output_<wcname>_wc_para``, with ``.label`` set to the same string and a one-sentence
    ``.description``. Any further output is ``output_<wcname>_wc_<what>``.

Re-exposed sub-process outputs
    A namespace named after the role: ``last_calc``, ``last_scf``, ``banddos_calc``,
    ``groundstate_scf``. **Do re-expose them** — a caller that cannot reach the underlying
    calculation has to hunt through the provenance graph by pk.

Call links
    Set ``metadata.call_link_label`` on every sub-process you submit, again naming the role
    (``'scf_no_ldau'``, ``'rare_earth_scf'``, ``'analogue_scf_0'``), and a short
    ``metadata.label`` so ``verdi process list`` is readable.
    :py:func:`~aiida_fleur.tools.common_fleur_wf.get_inputs_fleur` takes ``label`` and
    ``description`` for exactly this.

A handful of pre-3.0 names do not follow these rules (``output_convergence_wc_para``,
``magnetic_structure``, ``optimized_structure``, ``jij_tensor_z``). They are kept because renaming
a link label breaks stored provenance. Do not copy them.

Exit codes
++++++++++

``0``–``199`` belong to ``aiida-core``; plugin codes start at ``230``. Since 3.0.0 the numbers below
400 have **one meaning across all workchains**, so reuse them rather than inventing a number:

=========  ================================================  ===============================================
Code       Name                                              Meaning
=========  ================================================  ===============================================
230        ``ERROR_INVALID_INPUT_PARAM``                     unknown ``wf_parameters`` key or invalid value
231        ``ERROR_INVALID_INPUT_CONFIG``                    illegal combination of input ports
233        ``ERROR_INVALID_CODE_PROVIDED``                   a ``Code`` node uses the wrong plugin
235        ``ERROR_CHANGING_FLEURINPUT_FAILED``              ``inpxml_changes`` could not be applied
236        ``ERROR_INVALID_INPUT_FILE``                      modified ``inp.xml`` fails schema validation
334        ``ERROR_REFERENCE_CALCULATION_FAILED``            the reference/parent SCF failed
335        ``ERROR_REFERENCE_CALCULATION_NOREMOTE``          the reference produced no remote folder
343        ``ERROR_ALL_..._FAILED``                          every sub-calculation of a scan failed
344        ``ERROR_SOME_..._FAILED``                         some, but not all, sub-calculations failed
345        ``ERROR_SCF_FAILED``                              a sub-SCF workchain failed
360        ``ERROR_INPGEN_CALCULATION_FAILED``               in-process input generation failed
361        ``ERROR_FLEUR_CALCULATION_FAILED``                a FLEUR calculation failed
362        ``ERROR_DID_NOT_CONVERGE``                        an SCF cycle did not converge
=========  ================================================  ===============================================

Codes at 346 and above that are not in this table, and everything from 380 up, are
workchain-specific — allocate a free number there for anything genuinely new. The contract test
checks both directions: a shared number must carry its canonical name, and a canonical name must
not appear on a different number.

When you add a code, add a row to
``docs/source/user_guide/hints/exit_codes.rst``. That table is maintained by hand; there is no
generator in the repository.

Error handling in general: write ``inspect_xx`` / ``handle_xx`` steps, never loop forever on a
failing sub-process, and never let the workchain crash at a later point because an earlier
sub-process failed — a caller cannot build error handling on top of a workchain that raises.

Helpers you should reuse
++++++++++++++++++++++++

From :py:mod:`aiida_fleur.workflows._base` (shared workchain body):

``merge_parameter_dicts(given, defaults, nested=True)``
    the ``wf_parameters`` / ``options`` merge.
``unknown_parameter_keys(given, defaults)``
    top-level key check feeding exit code 230.
``apply_inpxml_changes(fleurinp, changes, reporter)``
    replay a task list; returns ``(new_fleurinp, failure)``.
``validate_and_freeze(fleurmode, reporter)``
    validate a prepared modifier against the schema and freeze it.
``collect_scf_results(workchains, reporter)``
    gather sub-SCF result Dicts, skipping failures.

From :py:mod:`aiida_fleur.tools.common_fleur_wf` (AiiDA-dependent helpers):

``get_inputs_fleur(code, remote, fleurinp, options, label, description, settings, add_comp_para)``
    assemble ``FleurBaseWorkChain`` inputs. Use it instead of building the dict yourself.
``validate_fleur_entry_points(inputs, port_namespace)``
    the shared ``spec.inputs.validator``.
``test_and_get_codenode(codenode, expected_code_type)``
    validate a ``Code`` and raise a message listing the valid candidates; this backs exit code 233.
``optimize_calc_options(...)``
    factorise MPI/OpenMP against the k-point count; used by ``FleurBaseWorkChain.check_kpts``.
``find_last_submitted_calcjob(restart_wc)`` / ``find_nested_process(wc_node, p_class)``
    provenance navigation.

Anything that does **not** depend on AiiDA belongs in ``pyfleur``, not here.

Provenance rules
++++++++++++++++

* Build the result node inside a ``@calcfunction`` (conventionally
  ``create_<name>_result_node``) so the result is linked to the nodes it came from, rather than
  appearing from nowhere in the graph.
* The result Dict always carries ``workflow_name``, ``workflow_version``, ``info``, ``warnings``,
  ``errors``, and ``successful`` where the workchain tracks it — alongside the physics. Someone
  reading the node years later must be able to tell what ran, what came out, and whether it is
  trustworthy.
* Do not put UUIDs of sub-processes in the result dict where you can avoid it; it defeats AiiDA's
  caching. Re-expose the sub-process outputs instead.
* **Bump** ``_workflowversion`` whenever the inputs, outputs or produced provenance change.
* Avoid renaming node classes, link labels or entry points — that requires a database migration for
  existing users.

What is machine-checked
+++++++++++++++++++++++

``tests/parity/test_workchain_spec_contract.py`` builds every workchain's spec and asserts the
conventions above. It needs no database and no FLEUR, so it runs everywhere::

    cd tests && python -m pytest parity/test_workchain_spec_contract.py -v

It currently checks that every workchain: is registered as an entry point; declares a semver
``_workflowversion``; declares no exit code below 230; uses the canonical name for any shared exit
code; does not reintroduce the retired ``remote`` port; declares exactly one
``output_<name>_wc_para``; names every other output ``output_*`` unless grandfathered; defines
``_default_wf_para`` if it takes ``wf_parameters`` and ``_default_options`` if and only if it takes
``options``; uses ``lower_with_underscores`` port names; and does not read the raw ``wf_dict``
after merging it into ``self.ctx.wf_dict``.

Deliberate deviations are recorded as named exemption sets in that file rather than being silently
tolerated. If your workchain genuinely needs one, add it there **with a comment saying why** — that
is the record future readers will find.

Testing a new workchain
+++++++++++++++++++++++

Workchain tests are regression tests that never run FLEUR. See
``tests/workflows/`` for the pattern:

* ``fleur_local_code`` / ``inpgen_local_code`` build *mock codes* that replay recorded outputs from
  ``tests/<suite>/calculations/mock-<code>-<hash>/``, keyed by a hash of the generated input files.
  Anything that changes the written input invalidates the hash.
* ``enable_archive_cache('<name>.tar.gz')`` loads or stores an AiiDA archive of the whole run from
  ``tests/workflows/caches/``.
* Structure and ``inp.xml`` generators (``generate_structure``, ``create_fleurinp``,
  ``generate_film_structure``, ...) live in ``tests/conftest.py``. Reuse them rather than building
  nodes by hand.
* Tests **must** be run from the ``tests/`` directory — the helper scripts set ``AIIDA_PATH`` and
  create a local profile. ``cd tests && ./run.sh workflows/test_myprop_workchain.py``.
* These tests are marked ``@pytest.mark.regression_test`` and are skipped automatically when the
  optional ``aiida-test-cache`` dependency is absent. Install it with
  ``pip install git+https://github.com/aiidateam/aiida-testing.git@main`` — the repository still
  carries the old name, the package it installs is ``aiida_test_cache``. Its ``aiida-mock-code``
  console script must be on ``PATH``, so activate the environment rather than calling the
  interpreter by path.

To refresh recorded data, run the suite against real ``inpgen``/``fleur`` binaries placed in
``tests/local_exe/``, then use ``tests/update_workflow_caches.py``.

Also add a cheap builder smoke test to ``tests/test_workflows_builder_init.py``, which needs no
mock code.

Checklist before opening a PR
+++++++++++++++++++++++++++++

#. Entry point added to ``pyproject.toml`` and the package reinstalled.
#. ``_workflowversion``, ``_default_wf_para`` (and ``_default_options`` only if there is an
   ``options`` port).
#. Exit codes reuse the shared allocation; new ones added to
   ``docs/source/user_guide/hints/exit_codes.rst``.
#. One ``output_<wcname>_wc_para``, sub-process outputs re-exposed under a role namespace.
#. ``tests/parity/test_workchain_spec_contract.py`` passes.
#. A regression test and an entry in ``tests/test_workflows_builder_init.py``.
#. A user page under ``docs/source/user_guide/workflows/``, listed in ``wc_index.rst``, plus a row
   in the table in :ref:`using_workflows` and an ``automodule`` entry in
   ``docs/source/module_guide/code.rst``.
#. A ``CHANGELOG.md`` entry.
