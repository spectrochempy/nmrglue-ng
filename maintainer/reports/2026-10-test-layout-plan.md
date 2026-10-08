# Plan for a single test tree

Date: **2026-10-08**. Status: **implemented at `35fd95d`, independently
reviewed and ready to merge**.
Baseline: `spectrochempy/nmrglue-ng:master`,
`a66231653854f01ccd73e81f960380101b003caf`, equal to freshly fetched
`origin/master`. PR [#62](https://github.com/spectrochempy/nmrglue-ng/pull/62)
is integrated at this commit. Its EXT correction is part of the baseline.

Evidence below comes from a fresh tracked-file inventory, source inspection
and collection-only runs on that commit. No test, fixture, helper or product
file was moved or changed. No functional suite or distribution build was run
for this planning assessment. This report does not constitute an independent
review or alter any release gate.

## Recommended decisions

1. Keep one source tree, `tests/`, with `conftest.py`, `fileio/`, `process/`,
   `analysis/`, `infrastructure/` and `fixtures/`. Preserve module basenames,
   test function/class names and parametrization IDs.
2. Move versioned fixture trees without flattening or rewriting their bytes.
   Preserve their provenance READMEs and generation scripts. Keep external
   `data/` in place and outside all distributions.
3. Include the single test tree and its infrastructure dependencies in the
   **sdist**. Recommend a **runtime-only wheel**, validated functionally using
   tests and fixtures extracted from the exact sdist used to build it.
   Approval is needed for removal of the distributed `nmrglue.*.tests`
   namespaces and their old `pytest --pyargs` invocation. Scientific/public
   runtime APIs remain outside this reorganization.
4. Prepare the evidence/validation machinery against the existing layout,
   then migrate all path consumers atomically in one dedicated change. Do not
   introduce compatibility copies, symlinks or a second collected test tree.
5. Keep the 16-group / 42-test critical contract, existing CI profiles,
   assertions, tolerances, expected values and skip semantics. Resolve any
   scientific failure independently; do not absorb it into the relocation.

## 1. Complete source inventory and mapping

The three requested roots contain **269 tracked files**: 35 collected test
modules, `conftest.py`, `setup.py`, one NMRPipe fixture generator, 122 files
under the packaged `data/` tree, four under `bruker_test_data/`, and 105
NMRPipe comparison assets. There are no `__init__.py` files in these test
roots and no duplicate collected module basenames at this baseline.
Generated caches and bytecode are not source assets and must not be moved.

The following table is the complete module mapping. Counts are collected
items, including class methods and expanded parametrizations, not executed
tests. Every `::Class::test[parameter]` suffix is retained exactly.

| Old module | New module | Items |
|---|---|---:|
| `tests/test_agilent.py` | `tests/fileio/test_agilent.py` | 9 |
| `tests/test_bruker_pdata.py` | `tests/fileio/test_bruker_pdata.py` | 32 |
| `tests/test_bruker_with_test_data.py` | `tests/fileio/test_bruker_with_test_data.py` | 11 |
| `tests/test_convert.py` | `tests/fileio/test_convert.py` | 25 |
| `tests/test_jcampdx.py` | `tests/fileio/test_jcampdx.py` | 2 |
| `tests/test_jcampdx_fixtures.py` | `tests/fileio/test_jcampdx_fixtures.py` | 58 |
| `tests/test_jeol.py` | `tests/fileio/test_jeol.py` | 14 |
| `tests/test_jeol_2d_fixtures.py` | `tests/fileio/test_jeol_2d_fixtures.py` | 10 |
| `tests/test_jeol_fixtures.py` | `tests/fileio/test_jeol_fixtures.py` | 21 |
| `tests/test_pipe_with_test_data.py` | `tests/fileio/test_pipe_with_test_data.py` | 25 |
| `tests/test_rnmrtk.py` | `tests/fileio/test_rnmrtk.py` | 2 |
| `tests/test_rs2d.py` | `tests/fileio/test_rs2d.py` | 1 |
| `tests/test_simpson.py` | `tests/fileio/test_simpson.py` | 4 |
| `tests/test_sparky.py` | `tests/fileio/test_sparky.py` | 4 |
| `tests/test_spinsolve.py` | `tests/fileio/test_spinsolve.py` | 5 |
| `tests/test_tecmag.py` | `tests/fileio/test_tecmag.py` | 27 |
| `nmrglue/fileio/tests/test_bruker.py` | `tests/fileio/test_bruker.py` | 19 |
| `nmrglue/fileio/tests/test_convert_csdm.py` | `tests/fileio/test_convert_csdm.py` | 3 |
| `nmrglue/fileio/tests/test_data_nd_subclasses.py` | `tests/fileio/test_data_nd_subclasses.py` | 4 |
| `nmrglue/fileio/tests/test_fileiobase.py` | `tests/fileio/test_fileiobase.py` | 41 |
| `nmrglue/fileio/tests/test_jcampdx_structure.py` | `tests/fileio/test_jcampdx_structure.py` | 2 |
| `nmrglue/fileio/tests/test_pipe.py` | `tests/fileio/test_pipe.py` | 45 |
| `nmrglue/fileio/tests/test_rnmrtk_generated.py` | `tests/fileio/test_rnmrtk_generated.py` | 10 |
| `nmrglue/fileio/tests/test_simpson_errors.py` | `tests/fileio/test_simpson_errors.py` | 1 |
| `nmrglue/fileio/tests/test_varian.py` | `tests/fileio/test_varian.py` | 9 |
| `nmrglue/fileio/tests/test_varian_blockheaders.py` | `tests/fileio/test_varian_blockheaders.py` | 1 |
| `tests/test_pipe_proc.py` | `tests/process/test_pipe_proc.py` | 47 |
| `tests/test_pipe_proc_unit.py` | `tests/process/test_pipe_proc_unit.py` | 48 |
| `tests/test_proc_base.py` | `tests/process/test_proc_base.py` | 20 |
| `tests/test_proc_lp.py` | `tests/process/test_proc_lp.py` | 3 |
| `tests/test_peakpick.py` | `tests/analysis/test_peakpick.py` | 12 |
| `nmrglue/analysis/tests/test_analysis_integration.py` | `tests/analysis/test_analysis_integration.py` | 4 |
| `nmrglue/analysis/tests/test_analysis_linesh.py` | `tests/analysis/test_analysis_linesh.py` | 1 |
| `tests/test_ci_validation.py` | `tests/infrastructure/test_ci_validation.py` | 8 |
| `tests/test_testdata_manifest.py` | `tests/infrastructure/test_testdata_manifest.py` | 47 |

### Non-test files: exhaustive prefix rules

Each subtree rule below maps **every tracked descendant**, retaining its full
relative suffix, file mode and bytes. The two Python infrastructure files need
the explicitly listed path/classification adjustments. Together with the
module table, these rules cover all 269 files; implementation must expand them
to a per-file mapping and reject uncovered files or duplicate destinations.

| Old path / subtree | Proposed new path / subtree | Contents |
|---|---|---|
| `tests/conftest.py` | same path | Central dependency classification hook; no declared pytest fixtures |
| `tests/setup.py` | `tests/fileio/_dataset_paths.py` | `TESTS_DIR`, `NMRGLUE_ROOT`, `DATA_DIR` path helper; adjust depth, preserve external data location and string-valued `DATA_DIR` |
| `nmrglue/fileio/tests/data/` | `tests/fixtures/fileio/data/` | 122 files, detailed below |
| `nmrglue/fileio/tests/bruker_test_data/` | `tests/fixtures/fileio/bruker_test_data/` | `1/acqus`, `1/pdata/1/1r`, `1/pdata/1/procs`, `synthetic_pulseprogram` |
| `nmrglue/fileio/tests/create_test_data_nmrpipe.sh` | `tests/fixtures/fileio/create_test_data_nmrpipe.sh` | Keep relative `data/` output layout and csh interpreter; never run in the versioned fixture tree |
| `tests/pipe_proc_tests/` | `tests/fixtures/process/pipe_proc_tests/` | 49 `.py`/`.com` pairs plus seven input files |

The 122-file `data/` inventory comprises:

- `bruker_pdata/`: 28 files including README, complete `exp1`, `exp2d_cosy`
  and `exp2d_hsqc` subtrees (27 acquisition/processing/data/title files).
- `jcampdx/`: README and five `.jdx` files (epicatechin 1H/13C, beta-pinene
  1H/COSY, caffeic acid 13C).
- `jeol/`: README and eight `.jdf` files (two Rutin, beta-pinene, three
  epicatechin 2D, fluorine, phosphorus).
- The remaining 79 files: 77 NMRPipe single files and indexed 3D/4D planes,
  `synthetic_jcampdx_blocks.jdx`, and `test.tab`. Preserve `.dir` names,
  numbered planes and `%03d` patterns; no flattening or deduplication.

The 49 comparison pair stems are `2d_complex_processing`, `add`, `apod`,
`base`, `cbf`, `coad`, `coadd`, `cs`, `dev`, `dx`, `em`, `ext`, `fsh`, `ft`,
`gm`, `gmb`, `ha`, `ht`, `ht4`, `integ`, `jmod`, `known_fail`, `ls`, `mc`,
`mir`, `mult`, `null`, `ps`, `qart`, `qmix`, `rev`, `rft`, `rs`, `save`, `set`,
`shuf`, `sign`, `sine`, `smo`, `sp`, `tm`, `to_fix`, `tp`, `tri`, `units`,
`xy2yx`, `ytp`, `zd`, `zf`. Preserve even scripts not currently selected by
the 47 tests. Inputs are `1D_freq_complex.dat`, `1D_freq_real.dat`,
`1D_time.fid`, `1D_time_real.fid`, `freq_real.ft2`, `time_complex.fid`,
`time_real.fid`. Scripts are executable/reference assets, not pytest modules.

### Helpers, imports and collisions

Keep module-local helpers with their tests; do not consolidate similar
functions or fixtures as part of relocation. Source inspection found no
direct imports from one collected test module into another and no project
`@pytest.fixture` definitions in these roots. Built-in fixtures such as
`tmp_path` remain pytest-provided. Inventory of module-local helper families:

| Module | Helpers retained in that module |
|---|---|
| `test_agilent.py` | Four regular/low-memory FID and generic readback helpers |
| `test_bruker_with_test_data.py` | `dic_similar`, regular/pdata/low-memory readback helpers |
| `test_pipe_with_test_data.py` | Five readback variants, `check_ppm_limits` |
| `test_sparky.py` | `dic_similar`, regular/low-memory readback helpers |
| `test_convert.py` | `check_sdic`, `check_dic`, `check_pdic`, `check_rdic`, `_make_fake_acqu3s` |
| `test_peakpick.py` | `_generate_1d_data`, `_generate_2d_data`, `_generate_3d_data`, `_test_1d`, `_test_2d`, `_test_3d` |
| `test_pipe_proc.py` | `_perform_test`, `_standard_args`, `_standard_test` |
| `test_tecmag.py` | `_pascal_string`, `_tlv_section`, `_build_minimal_tnt`, `_write_tnt` |
| `test_testdata_manifest.py` | `make_component`, `make_manifest`, `make_group`, `make_missing`, `make_file_entry`, `run_verify`, TOML serialization helpers, `load_tracked_manifest`, `tracked_component_paths` |
| `test_ci_validation.py` | `check_report` loaded using `runpy` from `.github/scripts/check_test_report.py` |
| `test_bruker.py` | `_make_2d_dic`, `_real_acqus_bytes`, `_write_temp` |
| `test_convert_csdm.py` | `_synthetic_input`, `_to_csdm` and four dimension/common assertion helpers |
| `test_data_nd_subclasses.py` | `assert_view`, `assert_data_nd_contract` |
| `test_fileiobase.py` | `DummyDataND` and its methods |
| `test_pipe.py` | `check_simple_roundtrip`, `check_ppm_limits`, `read_with_bytes_or_buffer` |
| `test_rnmrtk_generated.py` | `_values`, `_write_independent_fixture`, `_assert_metadata`, `_expected_bytes`, `_assert_written_file`, `_check_regular`, `_check_lowmem` |
| `test_varian.py` | `make_file_dic`, `make_data`, `read_raw_file_header`, `read_blockheader_indices` |
| `test_analysis_integration.py` | `_build_1d_ppm_scale` |

The 12 consumers of `from setup import DATA_DIR` are Agilent, Bruker external
data, conversion, JCAMP-DX, JEOL, NMRPipe external data, RNMRTK, RS2D,
SIMPSON, Sparky, Spinsolve and Tecmag. Recommend a sibling import
`from _dataset_paths import DATA_DIR` in `tests/fileio/`, retaining the
checkout's default pytest import mode. This avoids an ambiguous top-level
`setup` import without introducing a globally importable `tests` package.
Keep `TESTS_DIR` semantically the single test root and `NMRGLUE_ROOT` the
checkout root. All 12 consumers continue to resolve `<root>/data`.

`test_pipe.py` and `test_pipe_with_test_data.py`, and `test_bruker.py`,
`test_bruker_with_test_data.py` and `test_bruker_pdata.py`, are distinct:
do not merge or rename them to the same basename. Repeated helper names are
module-local and need no change. Gate the expanded map for case-folded path
collisions as well as duplicate destinations for Windows/macOS. If later
master introduces a collision, stop and decide an explicit rename in the
mapping; do not silently switch import mode for the entire suite.

## 2. Path dependency register

All rows must be addressed in the atomic migration unless marked historical
or unchanged. This is more than replacing strings matching old directories.

| Consumer | Required treatment |
|---|---|
| `tests/conftest.py` | Map `DATASET_MODULES` (11), `SELF_CONTAINED_EXCEPTIONS` (3), `DATASET_TESTS` (Tecmag), `OPTIONAL_DEPENDENCIES` (3 CSDM + RS2D), and the NMRPipe module equality. Preserve stripping only the parameter suffix for classification. |
| Conftest scope/root | It currently lives under `tests/` but its collection hook classifies the session, including CSDM under `nmrglue/`. Focused old packaged-test invocations may not load it. Verify both full and focused invocations after migration; do not mistake this old loading asymmetry for a reason to lose markers. Preserve `<root>/data` presence check, not per-dataset auto-skips. |
| `pytest.ini` | Change `testpaths` from `tests`, `nmrglue` to `tests` only. Preserve all five registered markers and strict CI flags; ensure assets are not newly collected. |
| `tests/setup.py` and its 12 imports | Apply the helper mapping above. No dependency on invocation cwd or installed `nmrglue.__file__` for source fixture discovery. |
| Packaged `test_pipe`, `test_fileiobase`, `test_data_nd_subclasses`, `test_jcampdx_structure` | Replace sibling `data/` lookup with `tests/fixtures/fileio/data/`; preserve numbered NMRPipe path templates. |
| Packaged `test_bruker` | Point to `tests/fixtures/fileio/bruker_test_data/`, including `synthetic_pulseprogram`. |
| Root `test_bruker_pdata`, `test_jcampdx_fixtures`, `test_jeol_fixtures`, `test_jeol_2d_fixtures` | Replace paths assembled as `../nmrglue/fileio/tests/data/...`; preserve all parameter values apart from the expected path prefix. |
| `test_pipe_proc.py` | Its `chdir` assumes a sibling `pipe_proc_tests`. Update destination lookup. It executes scripts using `exec`/`os.system`, writes output in that tree and does not restore cwd on every failure. Execute validation against disposable copies; cleanup repair is separate test-hygiene work. |
| NMRPipe asset scripts / generator | Retain relative filenames, `.com` execute permissions, csh requirements, and relative `data/` generator output layout. Never regenerate inputs during migration. |
| `test_ci_validation.py` | `parents[1]` for `.github/scripts` becomes root lookup from the deeper module (`parents[2]`). |
| `test_testdata_manifest.py` | Adjust `parents[1] / scripts`, literal real test IDs and assumptions in coverage tests. Keep fake `tests/test_dummy.py` and synthetic extractor examples distinguishable from live paths. Do not rewrite mock examples blindly. |
| `scripts/generate_testdata_manifest.py` | Keep `TESTS_DIR=<root>/tests`; use `fileio/test_*.py` in the nine `SCANNED_TEST_MODULES`. Audit `known_test_ids()` and diagnostic `tests/{module}` construction, `CRITICAL_TESTS`, every `REQUIRED_COMPONENTS.*.required_by`, and extractor documentation. |
| `maintainer/testdata-manifest.toml` | Map `manifest.critical_tests` and every component `required_by`, including missing/extended references. No changes to corpus-relative paths, SHA-256, sizes, provenance, scopes or availability. |
| `scripts/verify_testdata.py` | Root `data/` and manifest lookup stay valid; run verifier/structural tests with migrated declarations. Preserve exit-code meanings 0/1/2. It is not the packaged-fixture verifier. |
| `.github/workflows/ci.yml` | Update CSDM selector, both extracted-sdist infrastructure selectors, and wheel harness inputs. Retain matrix/check names, `pip check`, strict pytest flags, JUnit/distribution retention and nonempty/no-skip report gates. |
| `.github/scripts/check_installed_wheel.py` | Replace `--pyargs nmrglue.fileio.tests...` with relocated tests from staged sdist assets; strengthen import-origin proof as described below. |
| `.github/scripts/check_test_report.py` | No inherent layout dependency; preserve it, ship it in the sdist and run it on both reports. It rejects incomplete reports but does not establish the expected identity set alone. |
| `pyproject.toml` | Remove `nmrglue.analysis.tests` and `nmrglue.fileio.tests` from explicit package list if runtime-only wheel is approved. Do not install `tests` as a runtime package. Retain backend, dependencies and runtime packages. |
| `MANIFEST.in` | Replace old fixture includes and infrastructure selectors. Explicitly include the single tests tree, `pytest.ini`, required scripts, report helper, wheel harness and `maintainer/testdata-manifest.toml`. Inspect actual archives, not just declarations. |
| `.gitignore` | Replace obsolete exception `!nmrglue/fileio/tests/data/` with the necessary exception for `tests/fixtures/fileio/data/`; the unanchored `data` rule otherwise hides it. Test with `git check-ignore --no-index`. |
| `.pre-commit-config.yaml` | Remap all three fixture exclusions for whitespace/newline/line-ending hooks and the relevant large-file exclusions before running hooks. Preserve the effective protection of raw acquisition files without extensions. |
| `CONTRIBUTING.md` | Update organization, focused commands, CSDM, wheel/sdist procedure and fixture exclusions. Current prose mentions only CI-report sdist tests; actual CI also runs manifest tests. |
| `doc/source/devel/index.rst` | Update split-suite description, `setup.py` data path guidance and stale focused selector `tests/test_pipe.py`. Broader historical doc repairs stay separate. |
| `doc/source/tutorial.rst` | Its `tests/pipe_proc_tests` link targets historical upstream, not this checkout. Keep attribution; if adding a current local example, link separately rather than rewriting upstream history. |
| `examples/bruker_processed_2d/bruker_processed_2d.py` | Update constructed `nmrglue/fileio/tests/data` fixture path. |
| `examples/bruker_write_pdata/write_2d.py` | Uses external `<root>/data/bruker_2d`, not versioned fixtures; leave path unchanged and do not run it on canonical corpus (it writes `pdata/10`). |
| Maintainer reports / roadmap / skills | Update live relative links in Bruker axes, critical corpus and data_nd reports, development skill commands and release skill artifact guidance. Preserve dated commands/results as historical evidence, with a relocation note/map rather than pretending they ran at new paths. |
| `CHANGELOG.md` | Future migration entry describes developer test paths and approved artifact scope, with that PR's number. This planning document does not announce a shipped migration. |

For the manifest, path-only changes must preserve exactly nine scanned
modules (Agilent, external Bruker, convert, JCAMP-DX, JEOL, RNMRTK, SIMPSON,
Sparky, Tecmag) and 42 critical IDs under the bijection. NMRPipe external
file-I/O, RS2D and Spinsolve remain outside this manifest's current scope.
`_assign_env` recognizes `DATA_DIR` in an `ImportFrom` independently of its
source module, so the proposed helper import need not expand extractor scope.
Compare extracted corpus-reference sets per mapped function before/after;
keep recognized references and declared absent components identical. Run
declaration closure against the nine real modules, not just TOML syntax.
If regeneration is used, direct output to a disposable destination and
compare semantically; never replace inventory facts from a different local
corpus or use regeneration to conceal missing references.

## 3. Collection baseline and proof of equivalence

Fresh collection on 2026-10-08: **575 items in 35 modules**, exit 0, using
Python 3.13.13, pytest 9.1.1, NumPy 2.5.1 and SciPy 1.18.0. Collection used
`--collect-only -qq -p no:cacheprovider --strict-markers --strict-config`,
with bytecode disabled and an in-memory reporting plugin. No dependencies
were installed. This is a collection baseline, not a passing functional run.

| Property | Observed items |
|---|---:|
| Parametrized (`callspec` present) | 152 |
| `dataset` | 100 |
| `external_software` | 47 |
| `optional_dependency` | 4 |
| `fast` / `slow` | 17 / 7 |
| `skip` marker | 6 |
| `skipif` marker | 1 (condition false locally) |
| `xfail` marker | 0 |

Marker categories overlap. With this full collection, the autonomous
selection should contain 428 items and deselect 147. That arithmetic is not
a recorded execution result. Local `data/`, `nmrPipe` and `/bin/csh` exist;
`csdmpy` and `xmltodict` are absent. Six explicit skip markers are the three
CSDM tests (missing `csdmpy`), RS2D (missing `xmltodict`), and JEOL
`test_1d_real` / `test_2d_rr` (unavailable real-axis fixtures). Tecmag's
`test_tecmag_load_time_domain` has its own data-file `skipif`, false here.
Collection cannot prove runtime skips, outcomes or corpus completeness.

### Required before/after capture, before the first move

At implementation time, refresh master and rerun the baseline on the exact
base commit. Persist **full structured records**, not only counts or hashes.
The current table is a reproducible planning anchor; the ephemeral diagnostic
hashes from this assessment are not a canonical comparison artifact.

Use one identical reporting plugin on both revisions, without modifying test
objects. Capture after classification hooks, and capture deselected items
separately when applying `-m`. Record:

- full root-relative `nodeid`, module, class/function chain and ordered
  parameter suffix; source function identity and duplicate-ID multiplicity;
- `callspec.id`, parameter names, values, types and indices, including nested
  parametrization order; serialize arrays by dtype/shape/bytes hash, paths
  by declared root-relative identity, and callables by qualified name;
- effective markers including duplicates, arguments and keyword arguments
  (`skip`, `skipif`, `xfail` strictness/conditions/reasons included), plus
  requested fixture names and fixture scope/source;
- selection/deselection sets, collection errors and collection-time skips;
- runtime setup/call/teardown results and skip/xfail reasons from actual
  profile execution (JUnit plus a node-ID-keyed outcome record).

Normalize only approved changes: old module prefix through this mapping,
fixture parameter paths through the fixture mapping, and absolute temporary,
checkout and environment roots through explicit tokens. Do not erase
parameter suffixes, collapse markers to a set, normalize away tolerances or
replace arbitrary substrings. Avoid unstable `repr` containing memory
addresses; reject unsupported serialization rather than silently dropping it.
Emit a readable mismatch report per old/new ID and fail on any unexplained
addition, deletion, collision, changed parameter or changed marker/skip.
Compare source/AST diffs too: collection metadata does not prove preservation
of assertions, expected values, warning checks, fixture factories or helper
bodies. Allow only reviewed path/import adjustments.

Use the same Python/dependency/plugin versions, platform and availability
profile before/after. Exercise classification with data present and absent,
NMRPipe/csh present and absent, and each optional dependency present/absent.
Absent-data simulations belong in disposable source/test copies or a
classifier harness, never by renaming canonical `data/`. Check all 11 dataset
modules, the three autonomous exceptions, Tecmag and four optional IDs.
Do not download a corpus for this check. The optional-present CSDM execution
uses the already established CI job dependencies; no new dependency is needed.

Run the autonomous suite, CSDM job, infrastructure tests and artifact tests
before/after. Dataset and external-software profiles require matched local
availability and recorded software versions. Preserve existing failures and
skips explicitly; a matching failure is parity evidence, not validation of
the underlying science. For NMRPipe comparisons, stage the test and assets
in disposable trees on both revisions so generated files and failed cleanup
cannot dirty canonical fixtures. Do not run external corpus writers until
their copy-to-temp behavior is verified. Missing references remain visible
as failures when `data/` exists, following current semantics.

### Fixture integrity controls

- Existing SHA-256 tables, relative to `nmrglue/fileio/tests/`:
  `data/bruker_pdata/README.md` (27 data files), `data/jcampdx/README.md` (5),
  `data/jeol/README.md` (8; resolve the two Rutin
  wildcard labels unambiguously). These are provenance records, not currently
  a comprehensive automated checksum gate for all packaged assets.
- `maintainer/testdata-manifest.toml` and `scripts/verify_testdata.py` cover
  the external corpus, with declared exclusions, not versioned fixtures.
  Do not claim their integrity result covers the 122-file fixture tree or
  the comparison scripts. Run the verifier before/after any dataset execution;
  preserve integrity versus availability and exit 2 for incomplete critical
  data. An additional complete file inventory is needed if claiming all
  external corpus bytes, including verifier-excluded scripts, are unchanged.
- Before relocation, record path, size, SHA-256 and Git mode for all 232
  non-test asset files: 122 + 4 + 105 + the generator. Include READMEs and
  scripts; do not regenerate or normalize line endings. Check the old/new
  per-file mapping for byte equality and missing/extra files, then repeat
  after tests and against extracted sdist members. Git blob equality is an
  additional check, not a substitute for on-disk SHA-256 validation.
- Recommend a dedicated versioned-fixture checksum inventory/verifier, separate
  from the external manifest. Its schema/location and maintenance policy need
  approval. A migration capture is mandatory even if that durable mechanism
  is deferred. Existing provenance/rights records move intact; relocation
  does not resolve or enlarge redistribution permissions.

## 4. Installed wheel and sdist validation

Current CI builds via `python -m build` (wheel **from sdist**), checks metadata
with `twine check --strict`, installs in a fresh virtual environment and runs
`pip check`. The wheel harness checks imports/version and executes 45 NMRPipe
plus 19 Bruker tests with `--pyargs`. Its present prefix check verifies only
that the import is under `sys.prefix`; the migration must not replace its
64 functional cases with an import-only smoke test.

Recommended replacement protocol, retaining existing CI job/check names:

1. Build sdist and wheel-from-sdist, then inspect both archive member lists.
   The sdist contains `tests/`, configuration, manifest and validation-script
   dependencies; external `data/`, audit notes, caches and generated outputs
   are absent. The wheel contains every existing runtime package (including
   `process.nmrtxt`) and metadata; tests/fixtures are absent if approved.
2. Install the wheel, pytest and packaging in a fresh environment, without
   editable installs; run `pip check` and metadata/version checks. Use the
   exact corresponding sdist, not a possibly different checkout's tests.
3. Extract the sdist outside the checkout. Keep the existing **separate sdist
   functional validation**: execute relocated `test_ci_validation.py` and
   `test_testdata_manifest.py` with `-I -m pytest`, strict flags and `sdist.xml`.
   At this baseline these represent 8 + 47 items. Include all nine scanned
   dataset modules so closure checks run against real sources in the sdist.
   Use the extracted report checker and require the expected mapped cases,
   no skips, errors or failures. This does not claim a full sdist suite run.
4. In a second disposable directory outside both checkout and extracted source,
   stage the **single-source** `tests/` tree, `pytest.ini` and wheel-validation
   harness from the sdist, but **no `nmrglue/` source directory**. This is a
   transient validation copy, not a maintained second organization. Verify
   copied fixture hashes. Execute `tests/fileio/test_pipe.py` and
   `tests/fileio/test_bruker.py` with the fresh environment's Python `-I`,
   strict flags, explicit root/config and absolute `wheel.xml` output.
   These two modules have no `_dataset_paths` dependency, so the isolated
   runner may use `--import-mode=importlib` without changing checkout-wide
   imports. Full-suite isolated import mode is not part of this proposal.
5. Prove imports **inside the pytest process**, not only in a parent process.
   The harness should invoke `pytest.main(..., plugins=[origin_guard])` under
   `python -I`. Before collection and after execution, resolve
   `nmrglue.__file__`, representative module `__file__` values and every loaded
   `nmrglue.*` module location against that environment's `sysconfig` purelib /
   platlib (site-packages). Check package search paths too. Reject origins in
   checkout, extracted sdist or staged tests; print absolute paths and the
   distribution version. Verify paths against the installed distribution's
   recorded files where applicable. A source tree merely located under the
   virtualenv prefix must not pass. Require absence of the source roots from
   import search paths; `-I` alone does not prevent pytest path insertion.
6. Require exactly the mapped 64 current functional cases, not just a nonempty
   passing XML report, with unchanged assertions/expected data. Retain
   `check_test_report.py` and its no-skip/failure/error gate. Record the import
   guard evidence, collection/outcome map, fixture integrity and `wheel.xml`.
   Missing fixtures, substituted source imports or a missing test must fail
   this validation. Broader wheel coverage can be added separately.
7. Retain both XML reports and distribution artifacts for seven days, including
   failures, as today. Clean disposable builds/environments/staging areas and
   stop owned processes after validation.

This approach removes the coupling between runtime package layout and test
distribution while preserving actual read/write/round-trip and metadata
validation. It needs no new runtime or optional dependency and no data
download. If maintainers require tests to remain installed with the wheel,
decide that artifact contract before implementation; do not retain old source
copies as a workaround or silently delete the current functional gate.

## 5. Delivery sequence and acceptance

### A — Approve decisions and establish executable evidence

Refresh baseline, expand the 269-file map, capture complete collection and
outcome records and fixture hashes, and define the artifact member contract.
Implement the comparison/import-origin harness in a narrowly scoped preparatory
change, if authorized, against the existing layout. It can accept explicit
test/config paths so migration requires only updated inputs. Keep existing
wheel functional validation active until its replacement is proven. There
is still one current test organization and no duplicated source tests.

Acceptance: baseline commands and environment are recorded; every source file
has one destination; marker/parameter/skip comparisons detect deliberate
mismatches in disposable evidence; the current wheel's 64-case functional
contract and sdist checks remain green or any blocker is explicitly resolved
outside the relocation. Decide fixture hash policy and runtime-only wheel
scope. No fixture regeneration or dependency change is justified here.

### B — One atomic relocation change

Move all modules/helpers/assets and update **all** live consumers in section 2,
including hooks, manifest declarations, CI, packaging, examples and docs, in
the same coherent change. Protect fixtures before running formatting hooks.
Remove old package test entries and old paths only when their replacement
artifact validation is in that same change. Do not land a fileio-only move
that leaves wheel validation or corpus closure broken.

Acceptance: bijective ID/parameter/marker/skip comparison; unchanged scientific
assertions and helpers except reviewed paths/imports; all fixture bytes/modes
preserved; critical 42 IDs and nine module reference sets preserved; no stale
live paths or unapproved artifact members; autonomous/CSDM/CI matrices,
functional wheel and separate sdist gates retain their guarantees. Matched
dataset/external runs have outcome and integrity reports with unavailable
coverage called out. No canonical corpus writes and no new download policy.

### C — Independent review and closure

A fresh independent session reviews infrastructure, packaging, corpus/fixture
protection and evidence, including adversarial origin substitution and missing
fixture/test rejection. Recheck focused invocations and examples' path
resolution without executing examples that write canonical data. Record
decisions, validation limits and review result, then obtain separate delivery
authorization. Cleanup task-owned temporary resources when no longer needed.
There is no long-lived dual-layout transition and no separate later PR needed
to make documentation or CI catch up with a broken intermediate layout.

## 6. Implementation evidence

The maintainer approved the decisions in section 1. The atomic migration was
implemented on 2026-10-08 against `35fd95d`, after PR #63 advanced master from
the planning baseline. All 269 originally tracked files have one destination
under `tests/`; the current collection has 578 items because #63 added three
JCAMP-DX cases after the planning count. `scripts/test-layout-mapping.json` and
`scripts/test_layout_evidence.py` retain the specific relocation map and
collection/fixture comparison mechanism.

Before/after collection in the same CSDM-absent disposable environment is
bijective for all 578 node IDs after the approved path mapping, including
parameters, effective markers, declared skips and requested fixtures. The
original working environment acquired `csdmpy` during the session, so its later
collection has three fewer optional-dependency skip markers; this environment
change is not attributed to the migration. The CSDM profile was then executed
with the dependency present.

Validated implementation results are recorded in the local audit:

- autonomous profile: 431 passed, 147 deselected, no skips; this execution
  includes the three CSDM cases because `csdmpy` had become available;
- CSDM profile: 3 passed, no skips;
- infrastructure tests from extracted sdist: 55 passed, no skips;
- installed runtime wheel: 64 NMRPipe/Bruker cases passed, no skips, with
  `nmrglue` origins checked inside pytest against site-packages;
- `build`, `twine check --strict` and `pip check`: passed; the wheel contains
  no tests/fixtures and the sdist contains all 232 fixture assets without
  bytecode; SHA-256, sizes and modes match before/after and in the sdist;
- external corpus verifier: 145/145 inventoried files pass integrity; the
  existing 19 declared critical absences remain availability exit code 2.

The temporary no-corpus dataset profile selected 100 and skipped 100 cases as
specified. The available NMRPipe executable was exercised only in a temporary
source/fixture copy; 44 of 47 passed while historical JMOD, HT and TP metadata/data differences
failed, matching the existing 44/47 qualified result. These failures are not
scientific validation and were not altered. The historical NMRPipe cleanup
defect stays separately tracked. This is nmrglue-ng-specific test/packaging
maintenance, not an upstream submission.

Independent review examined staged, unstaged and untracked changes with
`git diff HEAD`, including adversarial installed-wheel checks. It confirmed the
578-case mapping, 232 fixtures, manifest contract and distribution validation.
Its initial P2 finding, stale live test links and one roadmap path, was
corrected and independently rechecked on 2026-10-08. No scientific
recomputation applies to this non-scientific test/packaging change.

## Independent-review prompt

Need: review the complete migration of all tests into one `tests/` tree, with
runtime-only wheel and sdist-derived functional validation. Examine the
uncommitted worktree on `master` based on `35fd95d7305f085d9995da61d7c09fb770f3dfab`.
Some relocations are already staged by `git mv`; begin with `git status`,
`git diff HEAD` (all tracked staged and unstaged changes), and
`git ls-files --others --exclude-standard` (new files). Do not rely on this
implementation report as authority.

Verify: every old/new mapping and case-fold collision; the 578-item bijection
including parametrizations, markers and skips; unchanged assertions,
tolerances and fixture hashes/modes; the 42 critical IDs, nine scanned modules
and all manifest `required_by` declarations; `conftest` behavior with absent
and present optional/dataset dependencies; sdist membership and runtime-only
wheel membership; the 55 sdist and 64 installed-wheel test identities; and
the pytest-process site-packages origin guard, including adversarial source
path leakage. Confirm that NMRPipe/dataset runs used only copies and that the
three historical NMRPipe failures are neither hidden nor reclassified. Check
CI command quoting, artifact reports and documentation. Report findings first,
then an explicit verdict. No commit, push, PR or upstream action is authorized.
