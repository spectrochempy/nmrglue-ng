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

The repository currently uses `setup.py`; it does not yet use
`pyproject.toml`. A development environment can be created with:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
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

The test suite currently has three practical categories.

### Self-contained tests

The standard GitHub Actions workflow currently runs:

```bash
python -m pytest --pyargs nmrglue
```

This exercises the tests shipped inside the `nmrglue` package. It does not run
the complete repository test suite.

Run focused tests for the code you change as well. For example:

```bash
python -m pytest nmrglue/fileio/tests/test_pipe.py
python -m pytest tests/test_peakpick.py
```

### Dataset-dependent tests

Many tests under `tests/` expect an external `data/` directory at the
repository root. Running the complete configured suite with:

```bash
python -m pytest
```

will currently fail when those datasets are not installed. Until dataset
handling is formalized, state clearly which fixtures you used and which tests
could not run. Do not describe the standard CI as full-suite coverage.

### External-software tests

Some processing comparisons require NMRPipe or other external NMR software.
If your change relies on those tests, document the software and version used.
A missing external program must be distinguished from a failure in
`nmrglue-ng` itself.

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
