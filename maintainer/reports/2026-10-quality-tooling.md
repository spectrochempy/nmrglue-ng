# Quality-tooling baseline

**Date:** 2026-10-16
**Historical diagnostic baseline:** `10bf7d2` (`DOC: record Conda packaging`)
**Ruff F821 validation commit:** `4c7a213` (`DOC: record Ruff gate pull request`, PR #120 head)
**Scope:** Ruff adoption baseline, scoped Codespell introduction and the first
Ruff F821 gate; no formatter, typing, benchmark, runtime-behavior or public-API
change was made. Source docstrings were corrected.

## Evidence

The existing pre-commit configuration provides structural and text-hygiene
checks. It deliberately excludes historical examples, documentation and data
fixtures from rewriting hooks. Codespell and the bounded Ruff F821 gate are
active; broader Ruff rules, typing and benchmarks are not quality gates.

The following commands were run locally with Python 3.13.13 and Ruff 0.15.20:

| Command | Result |
| --- | --- |
| `python -m ruff check nmrglue tests --output-format concise` | Exit 1: 132 diagnostics in 30 files. |
| `python -m ruff check . --output-format concise` | Exit 1: 182 diagnostics in 44 files; historical example scripts add Python-2 syntax diagnostics. |
| `python -m ruff format --check .` | Exit 2: 18 historical scripts could not be parsed; 170 other files would be reformatted. |
| `pre-commit run --all-files` | Exit 0: all eight configured hooks passed. |

The 132 core/test diagnostics are: F401 (37), E741 (34), F821 (24), F841 (8),
E712 (6), E722 (6), E402 (6), F403 (5), E731 (2), and one each of E713, E721,
F541 and F901. These counts are not directly comparable to the historical
137-finding measurement at `7a060fa`: the audit used a newer Ruff and the tree
has changed.

## Ruff interpretation

A repository-wide Ruff gate is not currently reviewable without broad style
churn. Formatter activation is separately blocked by the 170-file rewrite and
historical Python-2 scripts that Ruff cannot parse.

Even the otherwise high-value undefined-name rule requires classification
before activation. Most F821 reports are intentional TopSpin/Jython globals in
`nmrglue/util/xcpy.py` or Python-2 compatibility/fixture code. One report in
`nmrglue/fileio/glue.py` (`sY, sY = slices`, then use of `sX`) needs a separate
behavioral investigation; this audit does not change it or suppress it.

Adding broader Ruff coverage merely with broad exclusions or blanket per-file
ignores would hide unclassified defects and would not meet the project
requirement for a minimal, reviewable change.

## Ruff F821 gate

The first Ruff gate runs only `F821` on maintained paths under `nmrglue/`.
Forty in-scope package files are clean. Two explicit exclusions have distinct
dispositions: `nmrglue/util/xcpy.py` receives its 20 reported globals from the
TopSpin/Jython host, while `nmrglue/fileio/glue.py` is tracked by
`NMRNG-kb5.15.7` and [issue #119](https://github.com/spectrochempy/nmrglue-ng/issues/119).
Its public indexing fails earlier with an axis-order contract error, so the
reported `sX` is not treated as a one-line correction or silently suppressed.

`ruff-pre-commit` v0.17.1 runs `--select F821` for changed package files and
the existing CI quality job runs it on the complete scoped package tree. The
combined configuration passed `pre-commit run ruff --all-files` and
`pre-commit run --all-files` with ten hooks.

## Codespell baseline and scope

Codespell 2.4.1 was run once in an isolated pre-commit environment with the
existing `.codespellrc`. It exited 1 with 30 reports. The reports divide into
scientific fixtures and historical formats (Bruker parameter names, JCAMP-DX
content and raw-data values), two valid words (`unparseable` and the French
`statuts`), and confirmed spelling errors in source and test/docstrings.

The confirmed errors were corrected without renaming identifiers or changing
scientific values. Codespell is now a pre-commit hook at v2.4.1. Its exclusion
set matches the existing rewriting-hook policy: `examples/`, `doc/`, the three
fixture trees and data/binary extensions. This protects historical scripts and
scientific data while making spelling regressions in maintained source,
tests, metadata and maintainer records fail the quality job. `.codespellrc`
retains only the project vocabulary plus the two verified words above.

Post-change validation was run locally with Python 3.13.13: `pre-commit run
--all-files` passed all nine hooks, `pre-commit run codespell --files
nmrglue/process/proc_base.py` passed, and Codespell skipped the protected
Bruker fixture supplied with `--files`. The focused self-contained test profile
on `tests/fileio/test_pipe.py`, `tests/fileio/test_bruker.py` and
`tests/fileio/test_jeol.py` executed 65 tests successfully; 14 dataset-marked
tests were deselected.

## Decision and follow-up

The quality-tooling parent item is divided into independent Beads work:

- `NMRNG-kb5.15.1`: define a phased Ruff adoption plan, beginning with
  classification of diagnostics and a deliberately narrow lint-only scope;
- `NMRNG-kb5.15.2`: audit Codespell independently, including scientific and
  domain-specific false positives;
- `NMRNG-kb5.15.5`: implement the validated scoped Codespell hook;
- `NMRNG-kb5.15.6`: implement the bounded Ruff F821 gate;
- `NMRNG-kb5.15.7`: investigate the excluded `glue_2d` indexing contract;
- `NMRNG-kb5.15.3`: assess static typing without annotating the legacy tree
  wholesale;
- `NMRNG-kb5.15.4`: define a reproducible benchmark policy and first target.

No release gate changes are justified by this baseline. Any future pre-commit
or CI change requires separate review under `AGENTS.md`.

## Limitations

The Ruff assessment did not run tests because it changed no runtime behavior.
The Codespell hook is a CI/tooling change and needs separate review under
`AGENTS.md`. No external dataset or scientific-software profile was used.
