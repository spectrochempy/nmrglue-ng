# Contributing to nmrglue-ng

Thank you for helping maintain `nmrglue-ng`.

## Project Scope

`nmrglue-ng` is an independent continuation of
[`nmrglue`](https://github.com/jjhelmus/nmrglue). Its goals are to preserve the
established API where practical, provide active maintenance, improve
reproducibility, protect scientific correctness, and evolve the project
carefully.

The distribution name is intended to be `nmrglue-ng`, while the Python import
remains compatible with existing code:

```python
import nmrglue as ng
```

Large redesigns and general style rewrites are not initial project goals.

## Development Setup

The repository uses `pyproject.toml` with setuptools as its build backend. A
development environment can be created with:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

On Windows, activate the environment with the appropriate script under
`.venv\Scripts`.

Documentation dependencies can currently be installed with:

```bash
python -m pip install -e '.[docs]'
```

Avoid adding a mandatory dependency unless it is necessary and justified.
Features based on optional libraries should remain optional when reasonably
possible.

## Running Tests

The test suite distinguishes external requirements with three pytest markers:

- `dataset` requires files under the repository's external `data/` directory;
- `external_software` requires non-Python software such as NMRPipe;
- `optional_dependency` requires an optional Python package.

### Self-contained tests

Run every test that needs neither external datasets nor external software with:

```bash
python -m pytest -m "not dataset and not external_software"
```

This is the standard CI profile. All tests live under `tests/`, including
strict expected failures that track known autonomous defects.

Run focused tests for the code you change as well. For example:

```bash
python -m pytest tests/fileio/test_pipe.py
python -m pytest tests/analysis/test_peakpick.py
```

### Dataset-dependent tests

Run the tests marked as requiring the external `data/` directory with:

```bash
python -m pytest -m dataset
```

When `data/` is absent, these tests are skipped with an explicit reason. When
it is present, the tests run normally so missing or invalid individual files
remain visible as failures. The project does not yet provide automated dataset
installation.

### External-software tests

NMRPipe comparison tests use the `external_software` marker. Run them with:

```bash
python -m pytest -m external_software
```

They are skipped explicitly unless `nmrPipe` and `/bin/csh` are available.
Document the external software and version used when reporting their results.

Tests that use an optional Python package also carry the
`optional_dependency` marker and skip explicitly when that package is absent.
Optional dependencies are not installed by the standard test profile.

### Continuous integration

The CI workflow runs on pull requests and pushes to `master`, weekly, and on
manual dispatch. It has four validation profiles:

| Profile | Environment | Contract |
|---|---|---|
| Autonomous | Linux Python 3.10–3.14; Windows/macOS Python 3.14 | The standard self-contained suite; optional packages are not installed. |
| CSDM | Linux Python 3.13 with `csdmpy` | Existing synthetic CSDM conversion tests must execute and pass, with no skips. |
| Distribution | Linux Python 3.13, fresh virtual environment | Build an sdist and a wheel from that sdist, check metadata, run CI report tests from the extracted sdist, then verify installed imports and packaged NMRPipe/Bruker tests outside the checkout. |
| Pre-commit | Linux Python 3.13 | Run the configured hooks on all tracked files; structural and text-hygiene checks must pass. |

The existing Linux check names `build (3.10)` through `build (3.14)` are
preserved. New check requirements must be configured separately in repository
branch protection after their first successful runs.

All pytest invocations use strict marker/configuration validation and `-ra` to
report skips. JUnit reports are retained for seven days, including after test
failures; the packaging job also retains its distributions. Reports can be
absent if installation or collection fails before they are produced. These
profiles do not validate the external corpus or NMRPipe executable comparisons.

To reproduce the CSDM job in a disposable development environment:

```bash
python -m pip install '.[test]' csdmpy astropy matplotlib
python -c "import csdmpy"
python -m pytest tests/fileio/test_convert_csdm.py --strict-markers --strict-config -ra --junitxml=csdm.xml
python .github/scripts/check_test_report.py csdm.xml
```

Astropy and Matplotlib are explicit CI dependencies because CSDMpy 0.7.0
imports them without declaring them in its runtime requirements. They remain
optional for nmrglue-ng.

The wheel is runtime-only: it deliberately contains neither `tests` nor
fixtures, and no longer exposes `nmrglue.fileio.tests` or
`nmrglue.analysis.tests`. Build with `python -m build` (without separate
`--sdist --wheel` flags, so the wheel is built from the sdist), run
`python -m twine check --strict dist/*`, and install the wheel plus pytest and
packaging into a fresh virtual environment. Extract that exact sdist outside
the checkout, then use the environment's Python with `-I` to run its
`.github/scripts/check_installed_wheel.py`, passing the extracted sdist root
and an absolute JUnit output path. The harness stages the 45 NMRPipe and 19
Bruker functional tests from the sdist, requires all 64 cases to execute, and
verifies `nmrglue` imports from site-packages inside pytest. Run
`check_test_report.py wheel.xml 64` as well.

The sdist contains all `tests/`, fixtures, `pytest.ini`, the manifest and their
infrastructure dependencies. The packaging job separately extracts it outside
the checkout and executes `tests/infrastructure/test_ci_validation.py` and
`tests/infrastructure/test_testdata_manifest.py` with the fresh environment's
Python (`-I -m pytest`). It requires all 55 cases through the extracted
`check_test_report.py sdist.xml 55`. This focused check does not claim that the
complete repository test suite runs from the sdist.

### Pre-commit

The repository uses [pre-commit](https://pre-commit.com) with a minimal
configuration in `.pre-commit-config.yaml`. Hooks cover trailing whitespace,
final newlines, line endings, YAML/TOML syntax, merge conflicts, Python AST
validation, and a large-file guard. Ruff linting and formatting are not yet
enabled; a separate future change will introduce them after an audit of the
existing codebase.

The CI `quality` job runs `pre-commit run --all-files` on Python 3.13. Run the
same command locally before opening a pull request:

```bash
python -m pip install pre-commit
pre-commit run --all-files
```

The first run downloads hook environments; subsequent runs are fast. The
configuration deliberately excludes historical example scripts under
`examples/`, documentation under `doc/`, binary and text fixtures under
`tests/fixtures/fileio/data/`, `tests/fixtures/fileio/bruker_test_data/`, and
`tests/fixtures/process/pipe_proc_tests/`, and common binary or data extensions (`.fid`,
`.ft2`, `.ft3`, `.ft4`, `.ser`, `.acqus`, `.procs`, `.jdf`, `.ucsf`, `.par`,
`.sec`, `.1r`, `.2r`, `.in`, `.com`, `.tab`, `.png`, `.zip`, `.txt`, `.dat`,
`.jdx`). These exclusions prevent hooks from modifying scientific fixtures or
historical example material.

The existing `.codespellrc` is preserved but codespell is not part of the
pre-commit configuration; it remains an optional manual check.

## Maintainer records

Current maintainer priorities and curated validation evidence are indexed in
[`maintainer/README.md`](maintainer/README.md). Shared technical reports belong
in `maintainer/reports/`; `maintainer/audits/` remains ignored local working
material. Reports must distinguish historical checks from new validation and
must not depend on local-only notes to support shared conclusions.

## Test Data

Prefer the smallest fixture that demonstrates the required behavior. Every
new external dataset should have documented:

- provenance and acquisition or generation details;
- permission and license for redistribution;
- a checksum;
- the format and relevant software or instrument version;
- instructions for obtaining or regenerating it.

Do not commit large datasets to Git when a small fixture is sufficient. Do not
add automatic multi-gigabyte downloads to the standard CI. If data must remain
external, document how contributors can obtain and verify it.

### Test-data manifest and verification

The release-critical external corpus is documented in
`maintainer/testdata-manifest.toml`, which is tracked in Git. Both scripts
require Python >= 3.11 (for `tomllib`); on Python 3.10, install `tomli`.

The data comes from the upstream nmrglue v0.5 release archive. The repository
has a BSD-3-Clause license, but no explicit data license was specified for
release assets. Redistribution status for each group is therefore recorded as
`UNRESOLVED` pending explicit rights evidence. JEOL test data was not found
in the nmrglue repository, the v0.5 release archive, or the local corpus;
PR #228 added code and tests only. Tests referencing `data/jeol/` fail with
`FileNotFoundError` when the data is absent (the conftest skip checks for
the `data/` directory, not `data/jeol/` specifically).

The manifest records, for each logical group:

- format and provenance;
- repository license and redistribution status (`UNRESOLVED`,
  `NOT_AVAILABLE`, or `CLEAR`);
- evidence supporting the redistribution assessment;
- every file with its SHA-256 checksum, size, and provenance class
  (`original` from the v0.5 archive, or `derived` from local generation);
- required components (see below) and the derived availability
  (`complete`, `partial`, or `not_available`) with a missing-component
  summary;
- groups and reference sets that are not present in the local corpus
  (`[missing.*]`).

Required components are the reference paths the dataset tests consume:
raw datasets, NMRPipe conversion outputs such as `test.fid`, RNMRTK `.sec`
files with their `.par` parameter files, processed datasets, or encoding
outputs. Each component lists its paths, the tests that need it
(`required_by`), and a status:

- `present` — every listed path is inventoried with a checksum;
- `absent` — explicitly declared missing; no file matches the paths.

Two independent controls keep the declarations honest, each with a stated
scope:

- **declaration closure** — every `required_by` id must resolve to a real
  test in a scanned module, and all 42 release-critical test ids must
  appear in at least one component; the manifest is not written otherwise;
- **reference cross-check** — a static extractor collects the `DATA_DIR`
  references it recognizes (joins and `Path` division with literal
  segments, f-strings interpolating a resolved alias, alias assignments,
  and loop variables bound to `x.append(...)` lists, as used by the
  JCAMP-DX tests), and the manifest is not written while a recognized
  reference is neither inventoried nor declared absent.

The extractor is a complementary control limited to those constructions:
references built at runtime — from parameters, from a literal list
iterated directly, from glob or temporary paths — are not recognized.
Declaring all 42 test ids therefore does not, by itself, prove that every
file a test consumes is declared. The exact scope of the automated
controls, and the independent review that confronted the extractor with
every `DATA_DIR` use of the current modules, are recorded in
`maintainer/reports/2026-10-critical-corpus.md`.

A component is `critical` when at least one consumer belongs to the
historical 42-test release-critical contract, `extended` otherwise. Group
availability is derived from its components and is never asserted by hand,
so a group whose raw data is present while a conversion reference is missing
is reported `partial`, not `complete`. References consumed only by
extended-validation or low-priority tests are recorded under
`[missing.extended_test_references]` so no consumed path stays silent;
promoting any of them into the release-critical contract is a maintainer
decision.

Two scripts support this manifest:

```bash
# Regenerate the manifest from the current data/ directory
python scripts/generate_testdata_manifest.py

# Verify local data against the manifest
python scripts/verify_testdata.py
```

The verifier reports two result axes that must not be conflated:

- **integrity** — every inventoried file exists with the expected checksum
  and size, no extra file sits under `data/`, and the declared counters form
  a consistent chain;
- **availability** — every required component is present or explicitly
  declared absent, the declared statuses match the on-disk reality, and the
  declared group availability follows from the components.

`INTEGRITY: PASSED` never claims that the critical corpus is complete; read
the `AVAILABILITY` section or the exit code for that. Exit codes are:

- `0` — integrity OK and every release-critical component is present
  (extended-only absences are listed but do not change the exit code);
- `1` — error: structural inconsistency, integrity failure, or a component
  whose declaration does not match the corpus;
- `2` — integrity OK and every declaration consistent, but at least one
  release-critical component is explicitly declared absent (files conform,
  critical corpus incomplete).

The archive reference for the upstream v0.5 test data is:

- URL: `https://github.com/jjhelmus/nmrglue/releases/download/v0.5/test_data_v0.5-dev.zip`
- SHA-256: `dbff258fe08a19f1cd08f44b731d3d19e20e54fbb1415d904cd6d03f25209dae`

Several release-critical groups are not present in the local corpus or are
only partially available. See the `[missing.*]` sections and the
`availability` / `missing_components` fields in the manifest, and
`maintainer/roadmap.md`.

## Bug Fixes

A bug-fix contribution should provide:

- a minimal reproducer;
- the current behavior;
- the expected behavior;
- a regression test that fails before the fix;
- a scientific justification when the expected result depends on an NMR or
  file-format convention.

Avoid changing expected test values without explaining and supporting the new
expectation.

## File-Format Contributions

For a reader or writer change:

- identify the format and, when applicable, its version;
- cite a format specification, vendor manual, or other reliable reference;
- provide a small legally redistributable fixture when possible;
- test relevant metadata, dimensions, dtype, endianness, axis ordering,
  quadrature, and units;
- test malformed or unsupported input where relevant;
- add a `read -> write -> read` or equivalent round trip for writer changes
  when practical.

Synthetic files are welcome, but vendor-specific conventions may also require
validation against a verified real file or vendor software.

## Scientific Changes

Changes to scientific conventions require an explicit rationale and regression
tests. This includes, in particular:

- observation frequency (`obs`);
- reference frequency (`ref`);
- carrier frequency (`car`);
- spectral width;
- point, Hz, and ppm coordinates;
- quadrature and complex-data conventions;
- dimension and axis ordering.

Suitable evidence may include a format specification, vendor documentation,
verified software behavior, a real reference file, or a scientific
publication. Scientific correctness can justify a compatibility change, but
the impact must be identified, tested, documented, and accompanied by
migration guidance when needed.

## Pull Requests

Keep pull requests small and focused. Explain the problem, the proposed
solution, the tests performed, and any limitations. Avoid unrelated cleanup.

In particular, keep these concerns separate unless there is a clear technical
reason to combine them:

- infrastructure;
- packaging;
- documentation;
- bug fixes;
- scientific or API changes;
- performance.

Before submitting, run the relevant tests and:

```bash
git diff --check
git status --short
```

Every pull request with user- or developer-visible changes must update the
`Unreleased` section of `CHANGELOG.md`. Changelog entries should reference
the corresponding pull request using `(#NNN)`; the number must identify the
pull request, not an issue. When multiple pull requests materially contribute
to one entry, reference each of them. A purely internal change may instead state
`Changelog: not required` in the pull request description, with a brief reason.

## Relationship With Upstream nmrglue

The historical upstream project remains
[`jjhelmus/nmrglue`](https://github.com/jjhelmus/nmrglue). A generic fix made
for `nmrglue-ng` may also be suitable for upstream, but contributing here does
not automatically create or authorize an upstream contribution.

When work is shared or adapted between the projects, preserve authorship,
reference the original issue or pull request, and explain substantial changes.
Branding, packaging, governance, and roadmap decisions unique to
`nmrglue-ng` normally remain in this project.

## Compatibility

Compatibility with existing `nmrglue` code is a priority. Preserve public API
and behavior when that does not conflict with scientific correctness. Clearly
identify and document unavoidable incompatibilities and provide a migration
path where appropriate.
