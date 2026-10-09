# Release validation — October 2026

Consolidated 2026-10-07 at `ce98382`. Results below come from the recorded
2026-10-06 audits and hosted CI, not new executions during consolidation.
The first audit tested `fd84c06`; the corpus revalidation tested `34e057c`.
PR #58 (`ce98382`) subsequently changed documentation only.

## Conclusion and gates

The recorded verdict is **BLOCKED**. Autonomous tests and distribution builds
are healthy, but the complete critical-data contract, documentation and final
release preparation have not been validated. The table below retains the
historical assessment; the 2026-10-08 maintainer decision immediately below
updates the rights/acquisition interpretation without waiving test coverage.

| Gate | Evidence / remaining work |
|---|---|
| G1 — Provenance and rights | Historical external groups remain `UNRESOLVED`; evaluate rights for each retained group. Licensed packaged fixtures are a distinct category. |
| G2 — Versioned manifest | Present: 145 files, 11 local groups, size/SHA-256 and provenance fields. Completeness gaps described in the corpus report remain open. |
| G3 — Verified acquisition | A local verifier exists; a reproducible checksum-verifying fetcher does not. |
| G4 — Dataset validation | 14/42 historical critical tests passed; 28 lacked input files. No complete current critical-profile result or dataset CI job. |
| G5 — Independent documentation | Strict build errors, outdated RTD configuration and historical installation links remain. Independent deployment was not verified. |
| G6 — Release version/artifacts | Development version and artifacts agree; final version, dated notes and publication procedure are not finalized. |

The [critical-corpus report](2026-10-critical-corpus.md) gives the evidence
behind G1–G4 and proposals requiring a maintainer decision.

### Approved policy update — 2026-10-08

Under the [test-data policy](../testdata-policy.md), the historical nmrglue
archive is accepted for local validation. This supplies a recorded local-use
basis for that source, not blanket redistribution permission. Individual
files/groups with established public-domain status or redistribution licenses
may be distributed; the other accepted inputs remain local/private.

- **G1** now distinguishes provenance and accepted test use from redistribution
  rights for data actually distributed. The archive's unresolved redistribution
  status alone does not block its local validation. Other sources and files
  selected for publication still need their own assessment.
- **G3** accepts documented retrieval/checksum verification in the authorized
  environment; a public mirror or public download automation is not mandatory.
- **G4** accepts recorded local/manual critical-profile results with identified
  commit, inputs, software and integrity checks. Absence of public dataset CI
  is not itself a blocker. Missing files and unexecuted tests remain gaps.

The local-use decision does not rerun any profile or close the complete
validation gate. It supersedes the older blanket requirement to resolve
redistribution for all critical inputs,
not the historical test results. Current gate definitions are in the release
skill; current actions are in the [roadmap](../roadmap.md).

A subsequent maintainer disposition on the same date explicitly defers the
RNMRTK/Sparky/JEOL historical reference requirements from the first-release
critical scope, approves replacement of historical Bruker pdata, and retains the other
validation work described in the [policy](../testdata-policy.md). This is a
scope decision, not a successful execution. Its translation into the manifest
and generator remains pending; recorded 42-test/19-absence totals still refer
to the historical machine-readable contract.

## Recorded validation

| Baseline | Profile | Result |
|---|---|---|
| `fd84c06` | Autonomous, Python 3.13.13 / NumPy 2.5.3 / SciPy 1.18.0 | 364 passed, 3 skipped (`csdmpy` absent), 147 deselected. |
| `fd84c06` | CI distribution artifact reports | Extracted-sdist tests: 24 passed; installed-wheel tests: 64 passed; neither skipped. |
| `34e057c` | Autonomous | 385 passed, 3 skipped (`csdmpy` absent), 147 deselected. |
| `34e057c` | External dataset | 17 passed, 80 failed for missing files, 3 skipped; 435 deselected. |
| `34e057c` | NMRPipe differential | 44 passed, 3 failed; 488 deselected; NMRPipe 13.0 Rev 2026.072.12.03. |

Dataset skips: JEOL `test_1d_real` and `test_2d_rr` are documented placeholders;
RS2D skipped because `xmltodict` was absent. The optional-dependency marker
overlaps the other profiles and is not an additional disjoint test count.
An initial differential run with NMRPipe absent from `PATH` skipped all 47
tests; only the later executed run supports the 44/47 result.

Relevant commands (run at the stated baseline with dependencies available):

```bash
python -m pytest -m "not dataset and not external_software" --strict-markers --strict-config -ra
python scripts/verify_testdata.py
python -m pytest -m dataset --strict-markers --strict-config -ra -v
python -m pytest -m external_software --strict-markers --strict-config -ra
python scripts/verify_testdata.py
```

The dataset and external commands above specify the profiles and strict flags
for reproduction; local notes abbreviated some original command arguments.
Do not infer unrecorded exit codes or a new execution from this listing.
Corpus verification before/after revalidation: **145/145 files, 0 errors**;
documented fixture hashes independently checked: **40/40 match**. Missing
references are not included in those integrity-pass totals.

### Differential baseline

Remaining failures are `test_jmod`, `test_ht`, `test_tp` (historical cases
JMOD, HT6 and TP9). They retain their version/historical-test classification;
they are not passing comparisons or automatically new product defects.
HT4 is genuinely collected, explaining the increase from 46 to 47 comparisons.
Earlier corrections covered ZD (#9), SAVE (#13) and HT `ps90-180` (#15).

Failed comparisons leave generated `.dat`/`.glue` files because cleanup in
`tests/pipe_proc_tests` does not cover all failure paths. The audit removed
its leftovers. A `finally`/temporary-directory fix remains separate work.

## Hosted CI evidence

- [Run 37454926973](https://github.com/spectrochempy/nmrglue-ng/actions/runs/37454926973)
  at `fd84c06`: all 10 jobs passed.
- [Run 37505500330](https://github.com/spectrochempy/nmrglue-ng/actions/runs/37505500330)
  at `34e057c`: all 10 jobs passed. Distribution artifacts were not re-inspected
  during the corpus audit; the 24/64 artifact counts above belong to `fd84c06`.
- [PR #58 run 37625009967](https://github.com/spectrochempy/nmrglue-ng/actions/runs/37625009967)
  passed all 10 checks before the documentation merge.

Jobs cover Linux Python 3.10–3.14, Windows/macOS 3.14, CSDM conversion,
installed distributions and pre-commit. CSDM's dedicated CI job requires real
execution without skips; local missing-dependency skips do not validate CSDM.
These jobs do not cover the external corpus or executable NMRPipe comparisons.

## Version and distribution

At the audited baseline, `nmrglue.__version__` is `0.13-dev`; CI metadata
normalizes this to `0.13.dev0`, distribution `nmrglue-ng`, import `nmrglue`,
Python >=3.10. `git describe` at `fd84c06` was `v0.12-54-gfd84c06`, relative
to a historical upstream tag rather than an independent release.

Inspected CI artifacts: sdist 33,253,849 bytes; wheel 33,376,632 bytes. The
wheel is built from the sdist, checked with Twine, installed in a fresh
environment and exercised outside the checkout. These are development
artifacts, not released artifacts.

The sdist includes corpus scripts but omits `maintainer/testdata-manifest.toml`,
which the verifier expects by default. Decide whether to include it or limit
the tool explicitly to checkouts. No publication workflow exists; establish
a documented manual procedure or workflow. PyPI access and a minimum-runtime-
dependency matrix were not checked by these audits.

## Documentation and release notes

At `fd84c06`, the strict command
`python -m sphinx -b html -W --keep-going doc/source <temporary-output>`
reported structural errors in Sparky and Varian docstrings, plus numpydoc
warnings. `.readthedocs.yml` requests Python 3.8 while packaging requires
>=3.10. The Sphinx project name and installation/development pages still refer
to the historical distribution. Build repair, independent deployment and
migration guidance remain necessary. The corpus audit did not rebuild docs.

Changelog cleanup still includes duplicate `Fixed` headings, issue-versus-PR
references (#31/#32 should reference #56/#57; #18 must be distinguished from
PR #43), missing references for test migrations, and consolidation of fixture
entries. PR #58 already corrected the #55 entry and its interpretation.

## Review disposition

- #55: independent scientific review recorded 2026-10-07; documentation
  findings addressed by #58. The original general-defect claim was withdrawn
  after provenance analysis. See [Bruker axes](2026-10-bruker-axes.md).
- #56/#57: review evidence was missing at the initial consolidation. Update
  2026-10-07: a separate-session review at `23cdba1` approved each PR and their
  combined behavior. Commands, counts, skips and the Boolean-axis qualification
  are recorded in [data_nd](2026-10-data-nd.md). This closes the targeted
  review follow-up, not the broader inherited-defect assessment or other gates.

Closing an issue or merging a PR is neither an independent review nor a
replacement for missing scientific validation. Final release validation must
be recorded again on the published candidate commit.
