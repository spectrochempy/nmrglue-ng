# Initial technical baseline audit — 2026-09-30

## Purpose

This audit records the first technical baseline of the independent `nmrglue-ng` project. It is a historical snapshot, not a living status document.

## Baseline

- Branch: `master`
- Audited HEAD: `7ff6d5379934b85f277277aaea59e7844cb5d62d`
- First independent commit: `7ff6d537…` (`Revise README to introduce nmrglue-ng`)
- Common upstream parent: `5e2f095705bb90c6dc2f6a916abdfda82bac8e04`
- At audit time: 1 commit ahead and 0 behind `upstream/master`
- Repository state at the end of the audit: clean

Observed environment: Python 3.13.13, NumPy 2.5.1, SciPy 1.18.0, pytest 9.1.1, setuptools 82.0.1, pip 26.1.2.

## Test baseline

The inherited GitHub Actions command is:

```text
pytest --pyargs nmrglue
```

It passed:

```text
48 passed
0 failed
1 warning
```

A complete repository collection found 270 tests:

```text
97 passed
172 failed
1 skipped
```

The 172 failures were classified as:

- 169 missing external test files/directories;
- 2 requiring an NMRPipe installation;
- 1 real current-NumPy defect in `zd_*`: `TypeError: 'float' object cannot be interpreted as an integer`.

The green inherited CI therefore validates only a subset of the collectable tests.

## CI

The inherited workflow runs on Ubuntu for Python 3.10–3.14 and installs the project with `pip install .` before running the 48 packaged tests.

It does not currently cover:

- top-level `tests/`;
- external NMR datasets;
- macOS or Windows;
- minimum/current dependency matrices;
- optional dependencies;
- documentation builds;
- wheel/sdist build and installation checks;
- linting, typing, or coverage.

The retained `.travis.yml` targets Python 3.6–3.11 and is inconsistent with the current 3.10–3.14 policy; its role is historical unless an active Travis integration is demonstrated.

## Packaging

The inherited packaging uses `setup.py`, `setup.cfg`, and `MANIFEST.in`.

At audit time it produced:

```text
nmrglue-0.13.dev0.tar.gz
nmrglue-0.13.dev0-py2.py3-none-any.whl
```

Important findings:

1. Distribution metadata still says `Name: nmrglue`, while the independent project contract is distribution `nmrglue-ng` with import `nmrglue`.
2. `universal=1` still advertises Python 2 compatibility.
3. No `Requires-Python` metadata is emitted despite classifiers targeting Python 3.10–3.14.
4. The version is duplicated between packaging and `nmrglue/__init__.py`.
5. NumPy and SciPy have no declared bounds.
6. Optional dependencies such as `xmltodict`, `h5py`, and `csdmpy` are not represented as extras.
7. Several project URLs and metadata still identify upstream nmrglue.

Upstream PR #263 already addresses much of the generic packaging modernization, but also mixes in a `zd_*` numerical fix. nmrglue-ng should keep packaging and scientific fixes separate.

## Documentation

The local Sphinx build succeeded with three structural warnings plus several numpydoc warnings.

Important inconsistencies include:

- local version: `0.13-dev`;
- installation documentation still states Python 3.6+, NumPy 1.16+, SciPy 0.16+;
- CI/classifiers target Python 3.10–3.14;
- historical `setup.py install`, HTTP, and `git://` instructions remain;
- source links still target `jjhelmus/nmrglue`;
- `.readthedocs.yml` still requests Python 3.8.

The public upstream Read the Docs site was last built in 2021 and displays `nmrglue 0.9-dev`. No independent nmrglue-ng documentation deployment existed at audit time.

## Test data

The historical upstream v0.5 release still exposes `test_data_v0.5-dev.zip`, approximately 164 MiB, but it predates many later readers and fixtures.

Upstream issue #87 documents the unresolved test-data problem; a more complete reconstructed dataset was reported at approximately 5.7 GiB.

The repository itself contains only small fixtures sufficient for part of Bruker and NMRPipe coverage. External data are required for substantial testing of Varian/Agilent, Bruker, NMRPipe, Sparky/UCSF, RNMRTK, SIMPSON, JCAMP-DX, JEOL, RS2D, Spinsolve, Tecmag, and CSDM conversion.

## Format coverage snapshot

- Bruker: read/write/low-memory; universal-dictionary import/export; partial CI coverage.
- Varian/Agilent: read/write/low-memory; universal-dictionary import/export; external-data tests, none in inherited CI.
- NMRPipe: read/write/low-memory; broad conversion support; substantial packaged tests plus external and NMRPipe-dependent comparisons.
- Sparky/UCSF/Poky: read/write/low-memory for common dimensions; external tests.
- RNMRTK: read/write/low-memory; external tests.
- Tecmag/TNMR: read; `guess_udic`; synthetic tests plus an optional real-file test.
- JEOL/JDF: read; `guess_udic`; mostly fixture-dependent tests.
- RS2D: read; `guess_udic`; external test.
- Spinsolve: read; `guess_udic`; external tests.
- JCAMP-DX: read; `guess_udic`; limited fixture-dependent coverage.
- nmrML: read; no autonomous test identified.
- SIMPSON: read; external tests.
- CSDM: export through `to_csdm()`; optional dependency.
- Glue/HDF5: read/write/low-memory; optional dependency and no effective inherited CI coverage identified.

## Significant technical debt

Items requiring later focused work include:

- `proc_lp.find_lpc_qr()` uses removed `scipy.linalg.pinv2`;
- `proc_lp` contains `raise NotImplemented` rather than `NotImplementedError`;
- `leastsqbound.py` uses private SciPy `_minpack` API;
- several processing and optional-format paths have little autonomous coverage;
- some NMRPipe comparison cases are historically excluded;
- the fitting test reaches `maxfev` but still passes.

These observations are not authorization for broad refactoring. Each correction should be isolated, justified, and regression-tested.

## Scientific risks

The initial audit identified the following higher-risk areas:

1. Vendor I/O coverage is much broader than what inherited CI exercises.
2. Observation, reference, and carrier-frequency semantics are not robustly separated across the universal dictionary and conversions.
3. Low-memory `data_nd` operations have known copy/negative-axis defects.
4. Varian multi-trace reading and low-memory writing have known header/structure defects.
5. JCAMP-DX behavior is incomplete for several real-world encodings and multidimensional cases.
6. Some spectral-processing paths are insufficiently tested against current SciPy/NumPy.
7. Fitting convergence warnings require an explicit scientific decision rather than suppression.

## Priorities established by this audit

### P0

- establish independent distribution metadata and modern packaging;
- define a self-contained CI test contract;
- define reproducible test-data provenance and acquisition;
- establish independent documentation deployment;
- review known `data_nd`, Varian, and `zd_*` defects before the first release.

### P1

- broaden platform/dependency CI;
- declare optional dependency groups where appropriate;
- increase autonomous coverage of weakly tested modules;
- review reference-frequency semantics and JCAMP-DX as separate scientific changes.

### P2

- improve examples and historical documentation incrementally;
- evaluate linting, typing, and benchmarks without imposing a wholesale rewrite.

## Upstream opportunities

Generic corrections should be considered for upstream contribution when they are small, reproducible, compatible with upstream scope, and independent of nmrglue-ng-specific decisions.

Relevant existing upstream work includes #243, #244, #263, #264, #268, #270, #272, #275, and the JCAMP-DX series #260/#261/#262/#277.

No upstream issue or pull request is created by recording this audit.
