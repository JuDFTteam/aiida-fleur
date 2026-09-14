# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`aiida-fleur` is an [AiiDA](http://www.aiida.net) plugin for the all-electron FLAPW DFT code
[FLEUR](http://www.flapw.de): a data type for FLEUR's XML input, CalcJob plugins for `fleur` and
`inpgen`, output parsers, and a large set of high-level WorkChains. Everything is wired into AiiDA
through the entry points declared in [pyproject.toml](pyproject.toml) (`aiida.data`,
`aiida.calculations`, `aiida.parsers`, `aiida.workflows`) — a new workchain/calculation/parser is
only reachable after adding it there and reinstalling.

## Commands

Development install: `pip install -e .[testing,pre-commit,graphs,docs]`

### Tests

Tests **must be run from the `tests/` directory** — the helper scripts set `AIIDA_PATH=$(pwd)` and
create a local `.aiida` profile dir; running `pytest` from the repo root will use the wrong profile.
A running **PostgreSQL and RabbitMQ** are required (calcfunction/workchain tests fail otherwise).

```bash
cd tests
./run.sh                                   # all tests, verbose (-vs)
./run_all.sh                               # all tests, quiet
./run_all_cov.sh                           # all tests + coverage xml (what CI runs)
./run_all_cov_show.sh                      # coverage with term-missing report

./run.sh workflows/test_scf_workchain.py                                  # single file
./run.sh workflows/test_scf_workchain.py::test_fleur_scf_fleurinp_Si      # single test
./run.sh -m regression_test                                               # only regression tests
./run.sh parsers/test_fleur_parser.py::test_fleur_was_built_with_hdf5   # a DB-free unit test
```

`--mpl` (matplotlib image comparison) is passed by all the scripts; failures dump to
`tests/mpl-results/`. `pyproject.toml`'s `addopts` always enables coverage.

### Lint / format / docs

```bash
pre-commit run --all-files       # yapf, flynt, pyupgrade, single-quote fixer, pylint, mypy
pylint aiida_fleur               # config in pyproject.toml, most checks disabled
mypy --config-file=pyproject.toml aiida_fleur/data/  # mypy runs ONLY on data/ + tools/xml_aiida_modifiers.py
make -C docs html                # sphinx docs
bumpver update --patch           # version lives in aiida_fleur/__init__.py
```

Style: yapf google style, 120 columns, **single quotes** (enforced by `double-quote-string-fixer`).

## Architecture

The layers stack strictly, each one wrapping the next:

```
FleurXxxWorkChain (physics: eos, mae, jij, banddos, relax, orbcontrol, …)
  └─ FleurScfWorkChain            (fleur.scf — converge charge density, the workhorse subworkflow)
       └─ FleurBaseWorkChain      (fleur.base — BaseRestartWorkChain, error handling/restarts)
            └─ FleurCalculation   (fleur.fleur — CalcJob)
```

- **`aiida_fleur/data/fleurinp.py`** — `FleurinpData`, an `orm.Data` node holding `inp.xml` (plus
  optional `n_mmp_mat`, `kpts.xml`, …) in the repository, validated against the FLEUR XML schema for
  its file version. Schemas and the XML parsers come from the **`pyfleur`** dependency
  (`pyfleur.io.parsers.fleur_schema`), not from this repo. It exposes `get_structuredata`,
  `get_kpointsdata`, `get_parameterdata` as calcfunctions so extraction keeps provenance.
  The dict `inpxml_parser` returns is stored verbatim as the node's `inp_dict` attribute, so the
  parser's output format is part of stored provenance — never change it casually.
- **`aiida_fleur/data/fleurinpmodifier.py`** — `FleurinpModifier` (subclass of pyfleur's
  `FleurXMLModifier`). Since stored nodes are immutable, all `inp.xml` edits are recorded as a *task
  list* and replayed inside the `modify_fleurinpdata` calcfunction, producing a **new**
  `FleurinpData`. The `inpxml_changes(...)` context manager writes that task list into a workchain's
  `wf_parameters['inpxml_changes']`; workchains apply it in their `change_fleurinp` step. This is the
  canonical way for a workchain to alter FLEUR input — never mutate a stored node.
- **`aiida_fleur/calculation/`** — `FleurCalculation` and `FleurinputgenCalculation`. All FLEUR file
  names are class constants (`_INPXML_FILE_NAME`, `_CDN_HDF5_FILE_NAME`, …); the `settings` input
  accepts only the keys in `FleurCalculation._settings_keys`
  (`additional_retrieve_list`, `remove_from_retrieve_list`, `additional_remotecopy_list`,
  `remove_from_remotecopy_list`, `cmdline`, `fleurinp_nmmpmat_priority`).
  **FLEUR must be built with HDF5** — there is no plain-text file layout any more, and no
  detection: `prepare_for_submission` always writes `-last_extra -no_send` and retrieves
  `cdn_last.hdf`. The parser rejects a build that reports no `CPP_HDF` in its `out.xml`
  `<additionalCompilerFlags>` (exit 319). Note the text `bands.*`/`Local.*` files are *not* a
  non-HDF5 leftover — an HDF5 build writes them alongside `banddos.hdf`, so they stay retrieved.
- **`aiida_fleur/parsers/fleur.py`** — parses `out.xml` via pyfleur's `outxml_parser`, plus
  `relax.xml` and HDF5 outputs when retrieved.
- **`aiida_fleur/workflows/`** — one module per entry point. `base_fleur.py` holds the
  `@process_handler` error recovery (out-of-memory, walltime, MT radii, vacuum spill, …);
  `base_relax.py` does the same for the relax workchain.
- **`aiida_fleur/tools/`** — AiiDA-dependent helpers (`common_fleur_wf.get_inputs_fleur`,
  `optimize_calc_options`, structure utilities, corehole creation, plotting wrappers). Anything
  AiiDA-independent belongs in pyfleur instead.
- **`aiida_fleur/cmdline/`** — the `aiida-fleur` click CLI (`aiida-fleur launch scf|relax|eos|…`).

### WorkChain conventions

Every workchain follows the same shape, and deviating from it breaks composability:

- class attributes `_workflowversion`, `_default_wf_para`, `_default_options`; the
  `wf_parameters` input dict is merged onto `_default_wf_para` in the `start`/`validate` step. Most
  workchains reject unknown keys with `ERROR_INVALID_INPUT_PARAM`; `corehole`, `initial_cls` and
  `strain` are the exceptions that silently ignore them. Note the merge has two incompatible
  semantics: `scf`, `jij` and `corehole` merge nested dicts key-by-key, the other 13 replace a
  user-supplied sub-dict wholesale — so a partial `add_comp_para` behaves differently depending on
  which workchain you pass it to.
- inputs of subworkchains are pulled in with `spec.expose_inputs(FleurScfWorkChain, namespace='scf')`
  — the namespace name is part of the public API.
- one main output node per workchain named `output_<wcname>_wc_para` (a `Dict`) containing the
  physical results, `workflow_version`, and enough info to judge data quality.
- exit codes start at 230 (0–199 belong to aiida-core). Since 3.0.0 the numbers below 400 have one
  meaning across all workchains — 230 invalid `wf_parameters`, 231 illegal input combination, 233
  bad code, 235/236 inpxml change failed / result invalid, 334/335 reference SCF failed / has no
  remote, 343/344 all / some sub-runs failed, 345 a sub-SCF failed, 360/361/362 generation / FLEUR
  / convergence failed. Reuse those rather than inventing a number.
  [docs/source/user_guide/hints/exit_codes.rst](docs/source/user_guide/hints/exit_codes.rst) holds
  the full table and is generated from the source, so regenerate it when you add a code.
- a workchain starts from a `structure`, a `fleurinp`, or a `remote_data` — those three names, no
  synonyms. `FleurBandDos`/`Mae`/`SSDisp`/`DMI` enforce the combination with the shared
  `common_fleur_wf.validate_fleur_entry_points` as `spec.inputs.validator`, so it fails at
  submission rather than in the first step.
- `_workflowversion` / `FleurinpData.__version__` must be bumped whenever the produced provenance
  changes. Avoid renaming node classes, link labels, or entry points — that would require a DB
  migration for existing users.

See [STYLE_CONVENTION.txt](STYLE_CONVENTION.txt) for the full list.

## Testing infrastructure

Workchain tests are **regression tests that never run FLEUR**. They rely on the **`aiida-test-cache`**
plugin (an optional, unpinned dependency — if it is missing, tests marked `@pytest.mark.regression_test`
are skipped automatically). It used to be called `aiida-testing`; the upstream repo
(`github.com/aiidateam/aiida-testing`, still the install URL) was renamed and now ships the package
as `aiida_test_cache`, with the same submodules and fixture names but a different config file name:

- `fleur_local_code` / `inpgen_local_code` fixtures build *mock codes* that replay recorded outputs
  from `tests/<suite>/calculations/mock-<code>-<hash>/`, keyed by a hash of the generated inputs.
  Changing anything that alters the written input files invalidates the hash and the test fails with
  a missing-mock error.
- `enable_archive_cache('<name>.tar.gz')` loads/stores an AiiDA archive of the whole workchain run
  from `tests/workflows/caches/`.
- Paths and ignore lists for both live in [tests/.aiida-test-cache-config.yml](tests/.aiida-test-cache-config.yml)
  and in the fixtures' `ignore_paths` in [tests/conftest.py](tests/conftest.py). Its `mock_code`
  section is empty for normal runs: a label listed there must point at an executable that exists,
  or the fixture raises before any test runs.
- To refresh recorded data, uncomment the `mock_code` entries, run the suite against real
  `inpgen`/`fleur` binaries placed in `tests/local_exe/`, then use
  [tests/update_workflow_caches.py](tests/update_workflow_caches.py) to copy the regenerated
  `caches/` and `calculations/` folders back in.
- `conftest.py` carries a shim publishing `get_format` into `aiida.tools.archive`: the plugin
  imports it from there, but no supported aiida-core version (2.8–2.9) exports it from the package
  root — it lives in `aiida.tools.archive.abstract`. Without the shim every archive-cache test
  errors at import.

`tests/conftest.py` also provides the structure/inpxml generators (`generate_structure`,
`create_fleurinp`, `generate_film_structure`, …) used throughout — reuse them rather than building
nodes by hand.

## Compatibility constraints

Code must stay valid for **Python 3.10** (mypy target, lowest CI leg) through 3.13, against
`aiida-core>=2.8.0`. 2.8.0 is the floor because it is the first release whose numpy requirement
(`numpy<3,>=1.21`) admits NumPy 2; every earlier release pins `numpy~=1.21` and would cap the whole
environment below it. The FLEUR/`inp.xml` file versions supported are those known to the installed
`pyfleur` (currently 0.27–0.39 for input, 0.29–0.39 for output).

The CI matrix is spelled out leg by leg rather than as a cross product, because the stored
matplotlib/bokeh plot baselines under `tests/tools/test_plot_fleur/` only hold for
`matplotlib==3.6.3`/`bokeh==3.0.3`, and matplotlib gained NumPy 2 support only in 3.9. The two
NumPy 2 legs (3.12, 3.13) are therefore `allowed-to-fail` until those baselines are regenerated.

`pyfleur` replaced `masci-tools` in 3.0.0. It vendored the masci-tools XML stack, so the module
paths are unchanged below the top-level package name (`masci_tools.util.xml.xml_getters` →
`pyfleur.util.xml.xml_getters`). Two things did *not* survive the rename: `ATOMIC_NUMBERS` is gone
(use `pyfleur.inpgen.atoms.atomic_number`, which raises rather than returning a default), and the
bokeh pytest plugin moved to `pyfleur.testing.bokeh`. Until pyfleur is published on PyPI the
dependency is a SHA-pinned git URL, which means **aiida-fleur cannot be released to PyPI or
conda-forge** — PyPI rejects direct-URL dependencies.

`tests/migration/` holds a differential harness asserting pyfleur and masci-tools agree on every
code path this plugin uses. It is kept for one release cycle after the cutover, then deleted.
