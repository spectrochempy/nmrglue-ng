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

This is the standard CI profile. It collects tests from both `tests/` and the
tests shipped inside `nmrglue`, including strict expected failures that track
known autonomous defects.

Run focused tests for the code you change as well. For example:

```bash
python -m pytest nmrglue/fileio/tests/test_pipe.py
python -m pytest tests/test_peakpick.py
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
python -m pytest nmrglue/fileio/tests/test_convert_csdm.py --strict-markers --strict-config -ra --junitxml=csdm.xml
python .github/scripts/check_test_report.py csdm.xml
```

Astropy and Matplotlib are explicit CI dependencies because CSDMpy 0.7.0
imports them without declaring them in its runtime requirements. They remain
optional for nmrglue-ng.

For installed-wheel validation, build with `python -m build` (without separate
`--sdist --wheel` flags, so the wheel is built from the sdist), run
`python -m twine check --strict dist/*`, and install the wheel plus pytest and
packaging into a fresh virtual environment. From a temporary directory outside
the checkout, use that environment's Python with `-I` to run the absolute path to
`.github/scripts/check_installed_wheel.py`, passing an absolute JUnit output
path. The script runs packaged tests in its own temporary working directory
next to the report. Run `check_test_report.py` on that report as well to reject
empty or skipped validation.

The sdist explicitly includes `tests/test_ci_validation.py` and its helper
`.github/scripts/check_test_report.py`. The packaging job also extracts the
sdist outside the checkout and executes that test file with the fresh
environment's Python (`-I -m pytest`). It checks the resulting `sdist.xml` with
the extracted helper and retains that report alongside `wheel.xml`. This
focused check guarantees the CI report test's source-distribution dependency;
it does not claim that the complete repository test suite runs from the sdist.

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
`nmrglue/fileio/tests/data/`, `nmrglue/fileio/tests/bruker_test_data/`, and
`tests/pipe_proc_tests/`, and common binary or data extensions (`.fid`,
`.ft2`, `.ft3`, `.ft4`, `.ser`, `.acqus`, `.procs`, `.jdf`, `.ucsf`, `.par`,
`.sec`, `.1r`, `.2r`, `.in`, `.com`, `.tab`, `.png`, `.zip`, `.txt`, `.dat`,
`.jdx`). These exclusions prevent hooks from modifying scientific fixtures or
historical example material.

The existing `.codespellrc` is preserved but codespell is not part of the
pre-commit configuration; it remains an optional manual check.

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
external, document how contributors can obtain and verify it. The project does
not yet provide a complete managed dataset infrastructure, so proposals should
not assume one exists.

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
