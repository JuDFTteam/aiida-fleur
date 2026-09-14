# Changelog

## v.3.0.0
Replaces the `masci-tools` dependency with [pyfleur](https://iffgit.fz-juelich.de/fleur/pyfleur).
pyfleur vendored the masci-tools XML stack, so every module path below the top-level package name is
unchanged (`masci_tools.util.xml.xml_getters` → `pyfleur.util.xml.xml_getters`). A differential
harness in `tests/migration/` asserts the two libraries agree on every code path this plugin uses:
`inpxml_parser`, `outxml_parser`, all the `FleurinpData` getters, the modifier task registries and
their replay, `write_inpgen_file`, and the generated schema dicts. **Stored provenance does not
move**, so no database migration is needed and existing `FleurinpData` nodes and `ModifierTask`
lists remain valid and replayable.

### Breaking changes
- **`aiida-core>=2.8.0` is now required** (was `>=2.0.1`). 2.8.0 is the first release whose numpy
  requirement (`numpy<3,>=1.21`) admits NumPy 2; everything earlier pins `numpy~=1.21` and caps the
  entire environment below it. Together with dropping aiida-fleur's own `numpy~=1.16` cap this
  makes NumPy 2 installable — the cap was never justified by this codebase, which uses no API
  removed or renamed in 2.0.
- **Dependencies removed: `future`, `pyhull`, `MarkupSafe<2.1.0`.** `future` is a Python 2 shim with
  no imports anywhere. `MarkupSafe<2.1.0` was added in Feb 2022 to dodge a Jinja2 `soft_unicode`
  break in `aiida-core<1.6.7`, a condition the current floor excludes; it forced a 2021 MarkupSafe
  with no py3.12/3.13 wheels. `pyhull` is replaced by **`scipy`**, now an explicit dependency (it
  previously arrived only transitively through `aiida-core[atomic_tools]`).
- `determine_convex_hull` returns a `scipy.spatial.ConvexHull` instead of a
  `pyhull.convex_hull.ConvexHull`. Note the two types differ in meaning: pyhull's `.vertices` is a
  list of facets, scipy's is a flat index array of hull points. The function also no longer appends
  to the list it is given. Its docstring previously claimed it adds `[0.0, 1.0]`; it adds
  `[0.0, 0.0]`, as the code always did.
- **A FLEUR compiled with HDF5 is now required.** The plugin used to decide this by
  string-matching `'hdf5'`/`'Hdf5'`/`'HDF5'` against the `Code` node's description — a hand-typed
  field, so `'HDF'` or `'hdf'` silently selected the plain-text layout. The description is no
  longer inspected and can say anything. `prepare_for_submission` always passes
  `-last_extra -no_send` and retrieves `cdn_last.hdf`; `cdn1` is gone, along with the copy lists
  that restarted from it, so a `remote_data` produced by a non-HDF5 run can no longer be used as a
  parent. New exit code `319 ERROR_FLEUR_WITHOUT_HDF5`, raised when `out.xml` reports
  `<additionalCompilerFlags>` without `CPP_HDF`; FLEUR versions that omit the element are accepted.
  The `--local-exe-hdf5` pytest option is removed — CI already passed it on every leg.
- **The deprecated `fleur.dos` workchain is removed** (`aiida_fleur.workflows.dos:fleur_dos_wc`),
  with its entry point. It only ever read the plain-text `DOS.1`, and had been broken since
  `get_outputs_dict()` was dropped from aiida-core. Use `FleurBandDosWorkChain`.
- `plot_fleur_dos_wc` and `plot_fleur_band_wc` are removed from `aiida_fleur.tools.plot.fleur`,
  together with the `FUNCTIONS_DICT` keys `fleur_dos_wc`, `fleur_band_wc` and
  `FleurBandWorkChain`. They plotted the text `dosfile`/`bandfile` paths that only the removed
  workchain produced, so `plot_fleur` can no longer plot nodes from those legacy workchains.
- **Python 3.8 and 3.9 are no longer supported.** pyfleur requires >=3.10. The CI matrix is now
  3.10 (aiida-core 2.0.1, 2.3.0) and 3.11 (aiida-core 2.3.0).
- **`aiida-fleur` cannot currently be installed from PyPI or conda-forge.** pyfleur is not yet
  published, so the dependency is a PEP 508 direct git reference, which PyPI rejects on upload.
  Install from the repository until pyfleur ships.
- The `graphs` extra now requires `pyfleur[bokeh,plotting]` instead of `masci-tools[bokeh-plots]`.
  pyfleur moved `seaborn` out of its core dependencies into the `plotting` extra.
- `aiida_fleur.tools.plot` re-exports six plotting-default helpers (`set_defaults`,
  `set_default_backend`, `show_defaults`, `save_defaults`, `load_defaults`, `reset_defaults`). They
  now come from `pyfleur.vis.common`. The names and signatures are unchanged.
- The pytest plugin providing `check_bokeh_plot` moved from `masci_tools.testing.bokeh` to
  `pyfleur.testing.bokeh`. Downstream test suites registering it must update `pytest_plugins`.
- `NoPathFound`/`NoUniquePathFound` messages were rewritten to suggest which `contains` would
  disambiguate. Same exception types, same raise sites, but code matching on the message text
  (`pytest.raises(..., match=...)`) will break.

### Provenance-visible changes
- The parser identifies itself as `pyfleur Fleur out.xml Parser v0.7.1` rather than
  `Masci-Tools ...` in the `parser_info` merged into `output_parameters`. This is deliberate: it is
  the only marker distinguishing nodes parsed before and after the switch.
- `FleurinpData.__version__` is bumped to `0.7.0` to record the schema change below.
- pyfleur ships a **newer FLEUR 0.39 input schema** than masci-tools did under the same version
  number (it adds Wannier projections, `relLO`, `sdNocoIR`, Mössbauer parameters and a `plane`
  k-point type), plus a 0.39 *output* schema masci-tools lacked. A 0.39 `inp.xml` therefore yields a
  larger `inp_dict` than before. Two consequences for 0.39 inputs only: `listName` and `numBands`
  are no longer uniquely addressable, so a bare `set_inpchanges({'numbands': ...})` now raises
  `NoUniquePathFound` and must name its tag.
- Empty spheres (Z=0) are labelled `va`, FLEUR's own spelling, rather than `X` in the
  `atoms_elements` of the banddos/DOS HDF5 recipes. Affects plot legends and banddos output labels.
- `get_parameterdata` reports the concrete libxc functional (`LibXC: Exch: <x>, Cor: <c>`) instead
  of a bare `LibXC`, and now handles the `<LibXCID>` spelling that previously raised
  `ValueError: No values found for attribute exchange`.
- A local orbital whose `eDeriv` attribute is absent is now kept rather than silently dropped from
  `get_parameterdata`, which feeds the `&atom lo=` string of a subsequent inpgen run.

### Workflow API harmonisation

A review of the 20 workchains found the same concept spelled several ways across them. v3.0.0
settles on one spelling for each. These are breaking changes to input names, output labels and
exit-code numbers.

- **`remote` is renamed to `remote_data`** in `FleurBandDosWorkChain`, `FleurMaeWorkChain`,
  `FleurSSDispWorkChain`, `FleurDMIWorkChain`, `FleurJijWorkChain` and
  `FleurOrbControlWorkChain`. `FleurScfWorkChain` already used `remote_data`, so restarting from
  a previous calculation now has one name everywhere. OrbControl previously accepted both
  spellings for the same object. `aiida-fleur launch banddos/mae` were updated.
- **`FleurBandDos`, `Mae`, `SSDisp` and `DMI` reject an illegal combination of starting points at
  submission** rather than creating a process node that aborts in its first step, via a shared
  `spec.inputs.validator`. The rule is unchanged: give either the `scf` namespace or a
  `remote_data` (optionally with a `fleurinp`), not both and not neither. `Jij` and `OrbControl`
  keep their own checks because they have further entry points.
- **Exit codes are renumbered onto one allocation.** `FleurCoreholeWorkChain` used 1-9, inside
  the range `aiida-core` reserves for itself, and `FleurInitialCLSWorkChain` returned a bare
  integer because it declared no exit codes at all; both now use the common 230+ numbers.
  `FleurCutoffConvWorkChain` used 231/233/235/236 for meanings that nine other workchains give
  those numbers for, and moves to 240-243 and 360. "A sub-SCF failed" collapses onto 345 (from
  345/351/400). "All sub-runs failed"/"some failed" align on 343/344 (from 340/341, 342/343,
  343/344, 370). `FleurStrainWorkChain`'s 331 becomes the common 233. BandDos's
  `ERROR_SCF_CALCULATION_*` is renamed to `ERROR_REFERENCE_CALCULATION_*`, matching the four
  workchains that already used that name at the same number, and Jij's
  `ERROR_GREENSF_CALCULATION_FAILED` moves off 336 to 338. A typo'd
  `ERROR_FLEUR_CALCULATION_FAiLED` is fixed. The full allocation, with the shared meanings, is
  documented at `docs/source/user_guide/hints/exit_codes.rst`.
- **`output_convergence_wc_para` is renamed `output_cutoff_conv_wc_para`**, following the
  `output_<wcname>_wc_para` convention every other workchain obeys.
- **Six output ports declared `required` were only emitted conditionally**, so on the sad path
  the engine marked the workchain failed for a missing output: `eos.output_eos_wc_structure`,
  `relax.optimized_structure`, `scf.fleurinp`, `scf.last_calc`, `orbcontrol.groundstate_scf` and
  Jij's six per-direction tensors are now `required=False`.
- `FleurRelaxTorqueWorkChain` exposes the `last_scf` namespace, as `FleurRelaxWorkChain` does; the
  two are now interchangeable for a consumer reading the final SCF.
- `FleurOrbControlWorkChain` declares and emits `output_orbcontrol_wc_gs_scf` and
  `output_orbcontrol_wc_gs_fleurinp`. They were being created and labelled, then left stored but
  unreachable as workchain outputs.
- Result Dicts now carry `workflow_name`, `workflow_version`, `info`, `warnings` and `errors`
  consistently, and `successful` wherever the workchain tracks it. `corehole` and `initial_cls`
  gained the keys they were missing.
- `_wf_default` is renamed `_default_wf_para` in `orbcontrol`, `strain` and `cfcoeff`, the three
  that used the reversed spelling.
- Five dead `_default_options` class attributes are removed (`eos`, `relax`, `relax_torque`,
  `mae_conv`, `fsm`); none of those workchains has an `options` port, so the attribute only
  misled. `FleurStrainWorkChain` takes its SCF convergence defaults from `FleurScfWorkChain`
  instead of re-typing them — its `density_converged` had drifted to `0.02`, 1000x looser than
  SCF's own default, with nothing recording that as deliberate.

### Internal: shared workchain code

Refactoring only — no input, output or exit code changed. A spec-contract test
(`tests/parity/test_workchain_spec_contract.py`) pins that, and it needs no database.

- New `aiida_fleur/workflows/_base.py` holds what the workchains each carried a copy of:
  `merge_parameter_dicts`, `unknown_parameter_keys`, `apply_inpxml_changes`,
  `validate_and_freeze` and `collect_scf_results`, plus `DEFAULT_ADD_COMP_PARA` and
  `DEFAULT_COMPUTE_OPTIONS`. The copies had drifted — two of them caught only `ValueError`
  around a call that also raises `TypeError` — so the widest variant is used.
- New `aiida_fleur/workflows/_force_theorem.py` holds `FleurForceTheoremWorkChain`, the base
  `FleurMae`/`FleurSSDisp`/`FleurDMI` now inherit. `define`, `control_end_wc`, `force_wo_scf`
  and `scf_needed` were identical across the three apart from two label strings and the output
  name, which are now the class attributes `_OUTPUT_NAME`, `_FT_LABEL` and `_FT_DESCRIPTION`.
  The methods that differ — `start`, `converge_scf`, `get_inputs_scf`, `change_fleurinp`,
  `force_after_scf`, `get_results`, `return_results` — stay in the subclasses: they carry the
  physics, not the same code under different names.
- **The `wf_parameters` merge semantics are deliberately *not* unified.** `scf`, `jij` and
  `corehole` merge dict-valued defaults key-by-key; the rest replace a user sub-dict wholesale.
  That looks like drift but is load-bearing: `beta`, `sqas`, `q_vectors`, `references` and
  `replacements` are open-ended maps keyed by atom or q-point label, and merging defaults into
  them would silently add entries the user did not ask for. Each workchain keeps its own
  semantics via the `nested` flag on `merge_parameter_dicts`.

### Testing: the workflow regression tests actually run again

They had been silently skipped everywhere, CI included. `tests/conftest.py` gated them on
`import aiida_testing`, but the upstream repository was renamed and the install URL CI uses
(`git+https://github.com/aiidateam/aiida-testing.git@main`) now ships the package as
`aiida_test_cache`. The import therefore always failed, `RUN_REGRESSION_TESTS` was `False`, and
every `@pytest.mark.regression_test` was skipped.

- `tests/conftest.py` imports `aiida_test_cache`. Its fixtures (`mock_code_factory`,
  `enable_archive_cache`, `absolute_archive_path`) keep the same names and signatures and are
  registered through the package's own `pytest11` entry points. There is deliberately no fallback
  to the old name — anything still importing as `aiida_testing` predates the rename and would not
  find its config under the new file name.
- `tests/.aiida-testing-config.yml` → **`tests/.aiida-test-cache-config.yml`**, the name the
  renamed package looks for. Same schema. Its `mock_code` section is now empty, with the real
  binary paths commented out: the new fixture *validates that a listed path exists* and raises
  before collection otherwise, whereas a label that is simply absent means "replay only", which is
  what an ordinary run wants. Uncomment the entries to regenerate recorded data.
- `conftest.py` gained a shim publishing `get_format` into `aiida.tools.archive`.
  `aiida_test_cache.archive_cache._utils.load_node_archive` imports it from there at function
  entry, but **no supported aiida-core exports it from the package root** — not 2.8.0 (the declared
  floor) nor 2.9.x; it lives in `aiida.tools.archive.abstract`. Without the shim every archive-cache
  test raises `ImportError` before doing anything.
- The same stale import in `conftest.py`'s own `import_with_migrate` fixture is fixed.

This also fixed three `tests/cmdline` tests that were failing on the dead `aiida_testing` import.

### Bug fixes
- **`click_completion` is now a declared dependency.** `aiida_fleur/cmdline/__init__.py` imports it
  unconditionally and the `aiida-fleur` console script loads that module, so on a clean install the
  entire CLI died with `ModuleNotFoundError`. It used to arrive transitively through aiida-core,
  which no longer depends on it.
- **The FLEUR parser no longer raises `UnboundLocalError` on a failed calculation without a log
  file.** `aiida_fleur/parsers/fleur.py` imports `json` at module level, but carried a second,
  function-local `import json` inside the `_LOG_FILE_NAME` branch. A local import binds the name
  for the *entire* function, so when no log file was retrieved that branch never ran and the
  `json.load` of `usage.json` further down hit an unbound local — exactly on the error path where
  the memory-usage estimate matters. Fixed by dropping the redundant import.
- **`relax`, `ssdisp` and `dmi` no longer raise `KeyError` when `wf_parameters` is omitted.** All
  three merged the user dict onto the defaults into `self.ctx.wf_dict` and then, on the next line,
  subscripted the *raw* `wf_dict` — which holds only what the user typed, and is empty when the
  port is not given. `FleurRelaxWorkChain` read `wf_dict['atoms_off']`, `FleurSSDispWorkChain` and
  `FleurDMIWorkChain` read `wf_dict['ref_qss']`/`wf_dict['q_vectors']`. The workchains that merge
  in place (`scf`, `banddos`, …) were never affected. A new check in
  `tests/parity/test_workchain_spec_contract.py` fails the build on the pattern.
- **`FleurBandDosWorkChain`'s result Dict renames `Warnings` to `warnings`** and gains the
  `workflow_version`, `info` and `errors` keys the other workchains already emit. The capitalised
  key was unique in the package, so `output_banddos_wc_para['warnings']` used to raise `KeyError`.
  `errors` mattered most: `control_end_wc` appended to `ctx.errors` and nothing ever published it,
  so on the abort path the error message was silently discarded. `_workflowversion` is bumped to
  `0.8.0` accordingly.
- **A failed sub-SCF no longer crashes `eos`, `strain`, `mae_conv` and `ssdisp_conv`.** Their
  result-collection loops guarded `calc.outputs.output_scf_wc_para` with `except KeyError`, but
  that attribute access raises `NotExistentAttributeError`, which derives from `AttributeError`
  and `NotExistent` — never `KeyError`. The handler was dead, so instead of skipping the failed
  calculation the workchain aborted with an unhandled exception.
- **`FleurRelaxTorqueWorkChain` declares the four exit codes it returns** —
  `ERROR_NO_RELAX_OUTPUT` (352), `ERROR_NO_SCF_OUTPUT` (353), `ERROR_VACUUM_SPILL_RELAX` (311) and
  `ERROR_MT_RADII_RELAX` (313), at the same numbers `FleurRelaxWorkChain` uses for the same
  conditions. They were copy-pasted into the body without the declarations, so each raised
  `AttributeError` rather than failing cleanly.
- **`FleurSSDispWorkChain`** passed `kmesh.uuis` instead of `kmesh.uuid` to `set_kpointsdata`,
  raising `AttributeError` for every run that set `wf_parameters['kmesh_force_theorem']`.
- **`FleurInitialCLSWorkChain`** looked up its `relax_para` default under the key `dos_para`, which
  does not exist, so omitting `relax_para` silently gave `None` instead of `'default'`.
- **`FleurCFCoeffWorkChain`** assigned the analogue SCF's `wf_parameters` outside the `soc_off`
  guard that builds it. With `soc_off` disabled the first loop iteration raised `NameError` and
  subsequent ones reused the previous analogue's dict. The sibling `get_inputs_scf` was already
  correct.
- **`FleurStrainWorkChain`**: `_default_options` omitted `num_mpiprocs_per_machine`, so
  `FleurBaseWorkChain` hit a `KeyError`, reported "Computation resources were not optimised" and
  silently disabled resource optimisation for every run that did not override `options`. Its
  `settings` input is also now forwarded to the sub-SCF — the port was declared but never read.
- Removed the dead `ERROR_INPGEN_MISSING` (231) declaration from `FleurRelaxWorkChain` and
  `FleurRelaxTorqueWorkChain`, and a `pop('inpgen')` in `FleurCutoffConvWorkChain` that could never
  match because `inpgen` is excluded from the exposed namespace. All three were left behind when
  input generation moved in-process.
- **`aiida-fleur config` now actually takes effect.** `aiida_fleur/cmdline/util/defaults.py` never
  imported `json`, so reading `~/.aiida-fleur/cli.json` raised `NameError`, which a bare `except:`
  swallowed — the file was written but never read back, and `--fleur`/`--inpgen` silently defaulted
  to the most recently added code instead of the configured one.
- The FLEUR parser no longer misreports a successful run as failed when `shell.out` or `out.error`
  is missing from the retrieved folder. Both were read unconditionally although only assigned when
  the corresponding file was retrieved, so the resulting `NameError` was caught and turned into
  `run_was_successful = False`. Output read as bytes is now decoded rather than left as bytes, which
  also fixes the downstream error-classification checks that assume text.
- All nine bare `except:` clauses in the package were narrowed to the exceptions they were meant to
  catch. `find_nested_process` no longer silently swallows `RecursionError`, and skips non-process
  nodes explicitly rather than relying on `AttributeError`.

### Documentation: the workchain contract is written down

The conventions the 3.0.0 harmonisation settled on lived only in `STYLE_CONVENTION.txt`, the
CHANGELOG and a partly pre-2.0 developer guide. They are now two pages, and most of them are
machine-checked.

- **New `docs/source/user_guide/workflows/using_workflows.rst`** — the cross-cutting user contract:
  a table of all 21 workchains, the three starting points and which combination is legal, the
  `wf_parameters` merge (including which workchains merge nested and which wholesale, and the three
  that still ignore unknown keys), where `options` goes (the ten workchains with their own port vs
  the ten that take resources only through a sub-namespace), the `inpxml_changes` task-list format
  and context manager, a worked two-level EOS builder and the three-level `create_magnetic` case,
  the output naming and re-exposed namespaces, and the shared exit codes. `wc_index.rst`'s
  "General design" preamble is replaced by a pointer to it.
- **New `docs/source/devel_guide/writing_workchains.rst`** — how to write one: entry point
  registration, which layer to build on, the `define()`/`start()` skeleton using the `_base.py`
  helpers, the `nested` merge decision, `inpxml_changes` replay, naming, the shared exit-code
  allocation, provenance rules, what the contract test enforces, how to test, and a PR checklist.
  `dg_index.rst`'s stale "Workflow/chain development" and `setup.json`-era "Entrypoints" sections
  point at it; its package-layout table and test paths are corrected.
- `docs/source/user_guide/workflows/wc_index.rst` documented `('set_inpchanges', {'change_dict':
  ...})`. `add_task_list` replays tasks as `method(**kwargs)` and pyfleur's parameter is `changes`,
  so the documented form raised at replay time.
- `docs/source/module_guide/code.rst` gains the seven workflow modules it never listed
  (`base_relax`, `jij`, `relax_torque`, `strain`, `cutoff_conv`, `fsm`, `create_magnetic_film`), so
  the five workchains without a dedicated page at least have API documentation.
- `tests/parity/test_workchain_spec_contract.py` grows from 4 checks to 12. New: every workchain is
  registered as an entry point; `_workflowversion` parses as semver; exactly one
  `output_*_wc_para`; every other output is `output_*` or explicitly grandfathered; a
  `wf_parameters`/`options` port implies its defaults dict and vice versa; no `_wf_default`
  spelling; snake_case port names; **shared exit codes carry their canonical name**, checked in
  both directions; and the merged `wf_dict` is not bypassed. Deliberate deviations are named
  exemption sets with a comment giving the reason, so what is intentional is distinguishable from
  what is merely old.

### Notes
- `aiida-kkr` still depends on masci-tools, so a shared environment will hold both libraries. They
  define distinct `ModifierTask`, `AtomSiteProperties` and `InputSchemaDict` classes, so objects
  cannot be passed across an aiida-kkr/aiida-fleur boundary and satisfy `isinstance`.
- `pyfleur` fixes `plot_crystal_field_potential` on scipy >= 1.15, which removed
  `scipy.special.sph_harm`; the masci-tools version is broken there.

## v.2.0.0
First release with official support for AiiDA version 2.0. Support for AiiDA 1.X is only
available with releases from the 1.X series of aiida-fleur. Dropped python 3.7 support.
Added support for python 3.11.

### Breaking changes
- The entries `last_calc_uuid` from output dictionary of `FleurSCFWorkChain` and `last_scf_wc_uuid` from `FleurRelaxWorkChain` are removed. Reasoning for this is that having UUIDs in the output dictionary makes it impossible to take advantage of AiiDA's caching mechanism. Both workchains expose the relevant outputs of the under the namespaces `last_calc` and `last_scf` respectively
- Several input/output port changes:
  - `FleurBandDOSworkChain`: Removed `last_calc_retrieved`, replaced with namespace `banddos_calc`
  - `FleurBaseWorkChain`: Removed `final_calc_uuid`
  - Adjusted name of output dictionary to the naming schema `output_<wc_abbrev>_wc_para`: `FleurDMIWorkChain`, `FleurMAEConvWorkChain`, `FleurSSDispWorkChain`, `FleurSSDicpConvWorkChain`
  - `FleurSCFWorkChain`: Removed `last_fleur_calc_output`. Is available under `last_calc.output_parameters`
  - Ports for generic `FleurinpData` are renamed to consistently be `fleurinp`. Affects `FleurCalculation`, `FleurinputgenCalculation`, `FleurBaseWorkChain`

### Expired Deprecations
- `FleurinpModifier`: Removed compatibility with old method names/behaviour before introducing `masci-tools`
- `FleurinpData`: Removed `get_tag`. Use `load_inpxml` and any evaluation routine afterwards instead
- Coordinate conversion functions `abs_to_rel`, etc., These are available in `masci-tools`
- Removed `constants` module. Now only available in `masci-tools`


### Improvements
- New workchain `FleurRelaxTorqueWorkChain` for relaxing non-collinear magnetic configurations
- Fixes in DFT+U handling
  - `FleurCalculation`: added `fleurinp_nmmpmat_priority` key to `settings` to control from where to take the `n_mmp_mat` file if it's in the fleurinp and parent_folder input
  - Fixed several errors in orbcontrol workchain when handling non-converged/failed calculation
  - Added inputs to orbcontrol to restart from intermediate charge densities
- Added `inpxml_changes` contextmanager for easier creation of the workflow parameters input of the same name
```python
from aiida_fleur.data import inpxml_changes

wf_parameters = {}

with inpxml_changes(wf_parameters) as fm:
  fm.set_inpchanges({'kmax': 4, 'itmax': 100})
  fm.set_species('all', {'mtsphere': {'radius': 3}})

print(wf_parameters['inpxml_changes']) #now contains the list like before
```



## v.1.3.1
### release compatible with AiiDA-core 1.3.0+
- Fix for masci-tools dependency constraint. The constraint would previously reject the next minor version of masci-tools (i.e `0.10.0`)
- Small fixes in zenodo metadata
- Added `convert_inpxml` method to `FleurinpData` to convert to different file versions

## v.1.3.0
### release compatible with AiiDA-core 1.3.0+
- Guraranteed support for Fleur versions up to Max6
- Dropped support for python 3.6
- Added CFCoeff Workchain for calculating 4f crystal field coefficients
- General Improvements of Forcetheorem workchains, allow switching kpoints for force theorem calculations
- General Improvements of Orbcontrol workchain, allow starting from structure/charge density without SCF workchain
- Added support for inpgen profiles
- Refactored BaseFleurWorkChain; switched implementation of BaseRestartWorkChain from aiida-fleur to implementation provided by aiida-core
- Added support for starting SCF Workchain with first calculation using straight mixing either for the charge density or the DTF+U density matrix

## v.1.2.1
### release compatible with AiiDA-core 1.3.0+
- General improvements for CreateMagnetic workchain and related methods
- Added OrbControl workchain
- FleurBandDosWorkchain provides AiiDA BandsData for bandstructure calculations and XyData for DOS calculations as outputs
- General Improvements to plot_fleur function, e.g. can now visualize FleurBandDosWorkChain

## v.1.2.0
### release compatible with AiiDA-core 1.3.0+
possibly ready for aiida-core 2.0.0
- supports Fleur MaXR4 and MaXR5 versions with new inpgen
MaXR4 requires providing versions in the code nodes
- Some features relying on the id in the inpgen files,
may be broken by the new inpgen interface change when using MaXR5.1
- Added support for GW calculations with Spex, and the Strain workchain
- Major code refactoring, moving all xml tools to masci-tools (therefore requires masci-tools >=0.4.8)
- Also all file parsers are overworked and moved to masci-tools
- Work over of the BanddosWorkChain.
- FleurinpData now consistently supports more included xml files (kpts.xml, sym.xml, ...)
- Added new modification functions to the FleurinpModifier for kpoint manipulation for Max5


## v.1.1.4
### release compatible with AiiDA-core 1.3.0
- still support of Fleur MaXR4 version with inpgen
- Does not support yet Fleur MaXR5 and new inpgen
- Fixed numpy dependency issue with aiida-common-workflows and quantum mobile

## v1.1.3
### release compatible with AiiDA-core 1.3.0
- still support of Fleur MaXR4 version with inpgen
- Does not support yet for Fleur MaXR5 and new inpgen
- Set_kpoints was moved from fleurinp to fleurinpmodifier
- Break_symmetry of a structure was refactored
- Implemented feature in fleurinputCalculation to set significant figures
- Implemented feature scf can now use default queues specified in code extras
- First implementation of relax type None, which cases the relax workchain to skip the
relaxation, becoming a usual scf wc,  which might make it easier to switch relaxation on
and off in other workchains.
- Fleur parser parses now the total magnetic moment of the cell
- Introduced common constants, for bohr and htr, increased precision
- Command line interface (CLI) `aiida-fleur` with various functionalities exposed
- For devs: Increased test coverage, codecov is now added to CI and linked to badge
removed some older outdated code

## v1.1.2
### release compatible with AiiDA-core 1.3.0
- still support of Fleur MaX4 version (release branch) with inpgen
- downdgraded aiida-core dependency, do release does not depend on aiida-testing
- Added userfriendly LDA+U support
- SCF workchain can generate kpoints from a given density
- Base fleur has now time limit error handler
- Relax workchain can now run a final scf
- Update documentation for corehole, initial CLS and create magnetic workchains
- Various bug fixes and robustness improvements of magnetic workchains
- For devs: Enforced pre-commit, tests dir moved out of source

## v1.1.1
### release compatible with AiiDA-core 1.4.0
- still support of Fleur MaX4 version (release branch) with inpgen
- bugfixes and other general improvements
- new: BandDos workchain: workchain for Band and DOS calculation using the new Fleur BandDOS file
- basic workchains are now cachable, by moving cf out of workchains
- first calcjob and workchain regression tests for outside CI env
- provenance of the result nodes of magnetic workchains is fixed
- corehole and initial_cls workchain are fixed and working
- exit codes for inpgen parser

## v1.1.0
### release compatible with AiiDA-core 1.1.0
- support of Fleur Max4 version (release branch)
- make use of namespaces for nested workchains
- inputs for the workchains are checked more strictly
- exit codes are organised and consistent
- FleurRestart workchain: automatic parallelisation is able to make OMP threading
- new: BaseRelax workchain wrapping RelaxWorkChain and fixes its failures
- new: CreateMagnetic workchain that creates relaxed film structure
- increased unit test coverage for tools and utilities
- code clean-ups, pylint score increased to 7.49

## v1.0.0a
### release compatible with AiiDA-core 1.0.0b5
- added magnetic workchains
- added geometry optimisation (relax) workchain
- implemented the use of exit codes
- added FLEUR restart workchain
- integrated new Fleur input schema files
- other improvements of the workchains and calculations
- code clean-ups, documentation updates

## v0.6.0
### release for MaX virtual machine, not so well testet, but used in production mode. some things are currently half done
- added CI
- added basic tests, coverage still bad, but tests if plugin is installed right
- added MANIFEST
- fixed fleur_schema isssued if installed as python package (with manifest)
- integrated the new Fleur schema files
- bunch of new utiltity
- advancements of workflows
- correction of AiiDA graphs of most workchains, Quick and dirt, still unclear what is the right way to do these things, aiida_core still changes
- increased pylint score from 0 to >5

## v0.5.0
### Merge with advanced workflow repo
- this included the corehole and inital corehole workflow as well calculation of formation energies
  Therefore this is the first public released verison of them with in MaX
- all the utility of the corelevel repo is now under aiida_fleur/tools


## v0.4.0
- further improvment of scf, eos and other workchains
- a workchain delta form calculation a delta value, or performing calculation on the delta structures or a group of structures in a single shot
- lots of new utilty methods for structure dealings, fleur parameters and so on
- lots of bugfixes
- new system for the schema files, user does not has to add aiida-fleur to pythonpath or hack the schema paths.
- added new tests, submission tests and standard fleur tests
- first documention online, still very rusty still some issues there (stay with local one)

## v0.3.0

### Merge with workflows repo
- the second repository with basic workflows was merged into the plugin repostitory.
- Afterwards the repo was renamed from aiida_fleur_plugin to aiida-fleur

### Installation (new aiida plugin system):
- everything is now pip installable (pip install -e .) (not yet on pypi)
Therefore the files do not have to be copied anymore into the aiida_core source folder
(make sure to add the aiida-fleur folder to your PYTHONPATH variable)
- all modules are now importet from the aiida_fleur folder
 (example 'from aiida.tools.codespecific.fleur.convergence import fleur_convergence' -> 'from aiida_fleur.workflows.scf import fleur_scf_wc)

### Renaming
- In the process (and due to the entry points some things have to be renamed)
  The plugin in aiida (fleur_inp.fleur -> fleur.fleur; fleur_inp.fleurinp -> fleur.fleurinp; fleur_inp.fleurinputgen -> fleur.inpgen)

### Workflows
- some fine tuning of workflows. Naming scheme was introduced.
- Some first error catching and controlled shutdown (because of new AiiDA features).
- added consistent through all workflows the 'serial' key in wf_parameter nodes, which will turn of mpi.
- scf now uses minDistance and passes the walltime to fleur by default.

### Dokumentation
- Due to the new plugin system of AiiDA the Dokumentation is now online on read-the-docs.
(so far incomplete because of old AiiDA version on pypi) We still recommend to take a look at the docs in the repo itself (ggf build it)

### Utils
- read fleur cif folder does not break the proverance any more


### Further stuff
- 0.28 Fleur schema added to aiida-fleur



## v0.2.0 tutorial version

Version for used at the MAX AiiDA-fleur tutorial in May 2017

### Dokumentation
- added some basic explainations pages beyond the pure in code docs


### Tests
- added basic tests of Fleur itself and tests for submission

### Ploting
- There is a plot_methods repo on bitbucket which has methods to visualize common workflow output nodes.

### Workflows
- first basic working workflows available
- some common workflow stuff is now in common_fleur_wf.py

### Fleurmodifier
- Introduction of the Fleurinpmodifier class, to change fleurinp data

### Fleurinp data
- restructureing of fleurinp data and Fleurinpmodifier, moved most xml methods into xml_util
- plus added further xml routines and rough tests.


## v0.1 Base commit

### Moved everything von bitbucket to github

### Dokumentation
-Basic docs available locally

### Installation
- provided copy_files script to copy the plugin files into AiiDA folder

### Workflows
- Some basic sketches of basic workflows available (working AiiDa workflow system just released)i
