# nmrglue-ng roadmap

This roadmap is intentionally short and living. It records shared decisions and
evidence that must remain available to all contributors. Local audit notes may
be kept under the ignored `maintainer/audits/` directory.

## NMRPipe 13 differential baseline

44/47 historical comparisons now pass against NMRPipe 13.0 after resolving ZD
in #9, SAVE in #13, and HT `ps90-180` in #15. HT4 is now genuinely collected,
so the denominator increased from 46 to 47. The remaining differences are
JMOD, HT6, and TP9; they retain their NMRPipe-version or historical-test
classifications rather than being treated as confirmed bugs.

## P0 — First independent release

The `nmrglue-ng-release` skill audits the gates below; it never publishes and
never declares readiness while an item is open.

- [x] Establish independent project identity and preserve upstream attribution.
- [x] Add contribution governance.
- [x] Establish independent packaging: distribution `nmrglue-ng`, import `nmrglue`.
- [x] Define and enforce the self-contained CI test contract.
- [ ] Establish independent documentation and Read the Docs deployment.
- [x] Migrate high-value tests to existing packaged/generated fixtures
  (12 NMRPipe path/bytes API, 3 Bruker text-parser, 2 JCAMP-DX block-structure,
  3 CSDM conversion, 1 SIMPSON error-path, and 10 RNMRTK file-I/O tests
  migrated; 31 total).
- [x] Define the residual release-critical external dataset: 16 logical groups
  protecting 42 tests.
- [ ] Clear provenance and redistribution rights for release-critical data.
  Manifest records redistribution_status=UNRESOLVED for all local groups:
  the v0.5 release asset has no explicit data license, and the repository
  BSD-3-Clause license scope for contributed data is unconfirmed. JEOL data
  not found in examined sources (repository, release archive, local corpus).
  Missing groups (Sparky, RNMRTK, JCAMP-DX, SIMPSON encoding sets) need
  acquisition or regeneration. 116 Bruker 3D files are locally generated
  NMRPipe references, not in the release archive.
- [x] Add a versioned manifest with sizes and SHA-256 checksums.
  `maintainer/testdata-manifest.toml` tracks 145 files across 11 local
  groups with provenance classes, availability, and evidence fields.
  Regeneration and verification scripts provided (Python >= 3.11).
- [ ] Add an explicit checksum-verifying test-data fetcher.
  `scripts/verify_testdata.py` verifies local data against the manifest.
  A download fetcher remains to be designed once redistribution rights are
  established for the missing groups.
- [ ] Add scheduled/manual dataset validation.
  CI dataset job requires the corpus to be reproducibly obtainable; blocked
  on rights resolution for missing groups.
- [ ] Review critical inherited defects before the first release.
- [x] Define the integer/float width contract and resolve the `zd_*` defect (#4).

### Release-readiness audit — 2026-10-06

Audited published `master` at `fd84c0666015b3a09fa6818ca4fd34c434c6c804`:
**BLOCKED** under the existing P0 gates. This is a dated baseline, not a
validation of subsequent commits.

- [CI run 37454926973](https://github.com/spectrochempy/nmrglue-ng/actions/runs/37454926973)
  passed all 10 jobs. Local autonomous validation: 364 passed, 3 skipped
  (`csdmpy` absent), 147 deselected. The dedicated CSDM job passed in CI.
  CI artifact reports contain 24 passing sdist tests and 64 passing installed
  wheel tests, without skips.
- Local corpus verification passed for all 145 manifest files. This does not
  validate the 9 missing-group entries or the dataset test profile. Reconcile
  the historical critical contract with the new licensed Bruker/JEOL/JCAMP-DX
  fixtures using an explicit capability/test/reference mapping before deciding
  which missing groups remain necessary. Rights, verified acquisition and a
  current complete critical-profile result remain open. Dataset and NMRPipe
  profiles were not rerun in this audit.
- Issue [#48](https://github.com/spectrochempy/nmrglue-ng/issues/48) reproduces
  on the packaged HSQC fixture: the direct first point is 5.99683966 ppm versus
  processing `OFFSET = 7.99684` (about -2 ppm). **Recommendation pending
  maintainer triage:** block release on this silent axis error; validate the
  raw/processed metadata precedence and axis sampling convention independently.
  Issues #31 (1D transpose failure, now fixed) and #32 (float axes silently
  accepted, now fixed) also reproduce and need explicit release disposition.
- **Issue #48 investigation (2026-10-06)**: root cause confirmed in
  `add_axis_to_udic()` (`bruker.py:123-141`). When both `acqus` and `procs` are
  present, `sw` comes from acquisition (`SW_h`) but `car` is derived from
  processing (`SFO1 - SF`). For the HSQC fixture, this produces a -2 ppm
  offset because the acquisition and processing carrier frequencies disagree
  (the spectrum was re-referenced). The COSY fixture is unaffected because its
  acqus and procs agree. The HSQC indirect dimension is unaffected because it
  has no `acqu2s` and falls back to `proc2s`. The SI vs SI-1 convention
  question remains open: Convention A (SW_p/SI bins, first point at OFFSET) is
  consistent with the data and the existing `unit_conversion` formula.
  Proposed fix: add a `pdata` parameter to `guess_udic()` for explicit
  raw/processed disambiguation. Detailed report: `audits/2026-10-06-bruker-processed-axes.md`.
- Strict Sphinx HTML build reports structural errors in the Sparky and Varian
  docstrings. `.readthedocs.yml` requests Python 3.8 despite the package's
  Python >=3.10 requirement; documentation still contains upstream branding
  and installation commands. Repair the build and establish independent
  deployment and migration guidance.
- Source `0.13-dev` and CI artifact `0.13.dev0` versions are coherent, but the
  final version/changelog/tag remain to be chosen. Consolidate duplicate
  changelog sections and correct issue-versus-PR references. The sdist omits
  the manifest required by its bundled corpus verifier: include it or document
  checkout-only usage. Establish a publication procedure; PyPI access was not
  checked.

The detailed local report is `audits/2026-10-06-release-readiness.md` (ignored).
The findings above are the shared record; no release gate or critical-corpus
requirement has been waived by this audit.

## P1 — Scientific reliability

- [x] Secure `data_nd` copy and negative-axis behavior.
- [x] Fix and validate Varian low-memory I/O defects.
  Multi-trace block-header reading fixed (#36, upstream #270).
  `write_fid_lowmem` structural header correction fixed (#37, upstream #268).
  Block-header repetition fixed: `write_fid_lowmem` now uses each block's own
  header instead of always `dic["blockheader"][0]`, matching `write_fid()`.
- [x] Correct SAVE `FDPIPECOUNT` metadata compatibility (#6).
- [x] Specify and implement HT `ps90-180` with scientific validation (#7).
- [x] Restore and validate the `proc_lp` QR solver (#10).
- [ ] Specify observation/reference/carrier-frequency semantics and ppm conversion.
- [ ] Resolve Bruker processing-parameter source selection.
  Investigation complete (2026-10-06): root cause is in `add_axis_to_udic()`
  mixing acquisition and processing parameters when both are present.
  Fix implemented: `pdata` parameter on `guess_udic()`. Convention A
  (SW_p/SI bins) adopted from data evidence. 8 regression tests added.
  Self-contained suite: 372 passed, 3 skipped, 0 failures.
  See issue #48 and `audits/2026-10-06-bruker-processed-axes.md`.
  **Awaiting independent review.**
- [ ] Consolidate JCAMP-DX behavior against documented and real-world fixtures.
  All harivyasi PRs adapted: #259 (read_err, PR #49), #260 (nD NTUPLES, PR #46),
  #262 (XY..XY/PEAKTABLE, PR #47), #277 (read_blocks, PR #52).
  FID handling improved: `guess_udic()` sw corrected, `get_complex_array()`,
  `as_complex` parameter, `time`/`freq`/`complex`/`car` flags (PR #54).
  Bruker locale fix from #261 adapted and merged (PR #53).
  Upstream issue #284 opened for `sw` FID bug. Comments on PR #231 for
  indentation errors, `as_complex`, `[None, imag]` crash, NTUPLES detection.
- [ ] Investigate NMRPipe/JRES dimensional metadata behavior.

## Upstream contribution status (2026-10)

Local issues #31 (1D transpose) and #32 (float axes in swapaxes) were reproduced
on upstream `5e2f095` on 2026-10-06. Issue drafts prepared in
`audits/2026-10-06-data-nd-upstream-drafts.md`. #31 published as upstream #286.
#32 draft ready; awaiting maintainer approval before submission.

Bruker processed-axis issue
[#285](https://github.com/jjhelmus/nmrglue/issues/285) opened on explicit
maintainer request (2026-10-06), following PR #55 here. Reproduced against
fresh upstream `master` at `5e2f095`: direct first point 5.99683966 ppm versus
processing OFFSET 7.99684 ppm; omitting `acqus` only in memory restores
7.99684 ppm. The issue links original CC0 nmrXiv S208 data and offers a
focused opt-in fix. No upstream PR prepared; awaiting feedback on the approach.
This specific issue authorization does not change the general contribution
pause. Local evidence: `audits/2026-10-06-bruker-upstream-issue.md`.

9 PRs submitted on jjhelmus/nmrglue (#268, #270, #272, #275, #278-#282).
None have received maintainer feedback as of 2026-10-06.

New upstream PR #283 (harivyasi): `zd_*` width rounding half up (NMRPipe
compatible). Our code is stricter (`_normalize_zd_width` rejects fractions).
Decision: wait for upstream merge, then adapt if needed.

Audit notes: `maintainer/audits/2026-10-jcampdx.md`, `2026-10-bruker.md`,
`2026-10-06-bruker-processed-axes.md`.

### Bruker pdata fixtures — added

Three packaged Bruker experiments with raw and processed data:
- 1D sucrose standard (nmrXiv P52, CC0)
- 2D HSQC Ginsenoside Rg1 with all 4 quadrature components (CENAPTNMR, CC0)
- 2D COSY Gossypol with 2rr (CENAPTNMR, CC0)

22 autonomous tests cover `read()` and `read_pdata()` for 1D and 2D data,
including `all_components=True` for the HSQC experiment.

### JEOL 2D and JCAMP-DX fixtures — added

One JEOL 2D HSQC and two JCAMP-DX 1D fixtures from nmrXiv CENAPTNMR P33
(CC0 1.0). 10 autonomous tests cover `jeol.read()` for 2D data and
`jcampdx.read()` for 1D data with numerical reference values.

### JEOL fixtures — added

Four packaged JEOL fixtures with 17 autonomous reader tests including
numerical reference values. Fluorine/phosphorus from jeol-data-test commit
70bf716 (MIT); Rutin 1H/13C from Harvard Dataverse doi:10.7910/DVN/ZAZDNM
(CC0 1.0). External-data JEOL tests (cyclosporine etc.) remain
dataset-dependent; their data was never published.

## Issue #17 — symmetric numerical tolerances — IN VALIDATION

The direct one-sided proximity assertions in the Bruker processed-data, JEOL
`udic`, `vdlist`, and synthetic integration tests were converted to symmetric
absolute-error checks without changing expected values. Dataset and `vdlist`
tolerances are unchanged. The integration test used an invalid one-epsilon
bound once symmetry exposed its accumulated float64 summation error; its new
bound is `data.size * eps`. The expected integrals remain unchanged. The local
v0.5 corpus has the Bruker raw groups but lacks the processed-data and JEOL
groups, so the release-critical dataset assertions remain unvalidated
until those groups are available. The audit retained the Tecmag sign checks
and Spinsolve interval bounds because they are intentional one-sided
properties, not proximity checks. Issue #18 is resolved: empty JEOL placeholder
tests (test_1d_real, test_2d_rr) are explicitly skipped with documented
reasons; real-axis JEOL data is not available in any sourced dataset.

## P2 — Broader maintenance

- [x] Expand CI to representative Linux, macOS, and Windows jobs (#34).
- [ ] Define optional dependency extras where appropriate.
- [ ] Increase autonomous coverage of processing modules and examples.
- [ ] Modernize historical documentation and links incrementally.
- [ ] Introduce linting, typing, and benchmarks only where they add clear
  maintenance value. Ruff linting/formatting remain deferred pending a
  separate audit.
- [x] Introduce minimal pre-commit structural and text-hygiene hooks with
  CI enforcement (#35).

### CI validation expansion — validated (#34)

The workflow retains Linux Python 3.10–3.14 and adds Windows/macOS
Python 3.14, a Linux CSDM job requiring executed tests without skips, and an
isolated sdist-to-wheel installation check using packaged NMRPipe/Bruker tests.
The sdist includes the CI report test and its helper; packaging validation runs
that test from the extracted archive to protect their distribution contract.
JUnit reports, weekly/manual runs, and pip caching make these profiles easier
to inspect and reproduce. PR #34 at `40cd743` passed all nine hosted checks:
five Linux versions, Windows, macOS, CSDM, and distribution validation
([run 37234329307](https://github.com/spectrochempy/nmrglue-ng/actions/runs/37234329307)).
Windows exposed a pre-existing `os.rename` overwrite failure in the Bruker
test helper; `os.replace` resolved it with the same temporary paths and
unchanged assertions. Independent review confirmed the CI/sdist changes and
the final Windows correction as ready to merge. Scheduled/manual triggering,
branch-protection requirements, and cancellation behavior are separate from
the evidence supplied by this successful PR run.
External dataset and NMRPipe executable validation still require their own
infrastructure and evidence.

### Pre-commit introduction — validated

A minimal pre-commit configuration now covers trailing whitespace, final
newlines, line endings, YAML/TOML syntax, merge conflicts, Python AST
validation, and a large-file guard. Historical examples, documentation, and
binary/text fixtures are explicitly excluded so hooks never modify scientific
data. A CI `quality` job runs `pre-commit run --all-files` on Python 3.13.
Ruff linting (137 existing violations) and formatting (106 files to
reformat) remain deferred: introducing them requires a separate, reviewed
mechanical change. The existing `.codespellrc` is preserved but codespell is
not part of the pre-commit configuration.

## Issue #16 — corpus mutation fix — RESOLVED

`test_convert.py::test_bruker_3d` and `test_convert.py::test_bruker_3d_lowmem` were mutating the
canonical `bruker_3d` dataset by copying `acqu2s` to `acqu3s` directly under
`DATA_DIR`. Fixed in PR #27:

- Both tests now `shutil.copytree` the dataset into `tmp_path` before any write.
- `acqu3s` is created only in the temporary copy; all reads use that copy.
- Intermediate `tempfile` dirs are placed under `tmp_path`.
- No file in the canonical corpus is created or removed.

An autonomous non-regression test `test_bruker_3d_acqu3s_isolation` calls the real
`_make_fake_acqu3s` helper and verifies the source is byte-identical afterward,
covering both initial states (acqu3s absent and acqu3s present).

Validation:

- Autonomous suite (`pytest tests nmrglue -m "not dataset and not external_software"`):
  181 passed, 3 skipped — no regression.
- Full validation against real `bruker_3d` from the upstream v0.5 archive:
  both tests pass in both orders; corpus integrity verified via SHA-256.
- Pipe reference (`fid/`) regenerated from `ser` via NMRPipe (external software).
- Pre-existing `FDDMXVAL` test exclusion added (separate bug, same pattern as
  FDMIN/FDMAX/FDDISPMAX).

Archive reference for local test data:

- URL: `https://github.com/jjhelmus/nmrglue/releases/download/v0.5/test_data_v0.5-dev.zip`
- SHA-256: `dbff258fe08a19f1cd08f44b731d3d19e20e54fbb1415d904cd6d03f25209dae`

This fix is generic, minimal, and compatible with upstream. It is a candidate
for upstream contribution but is explicitly deferred (see below).


## Upstream policy

Generic, reproducible fixes that do not depend on the independent direction of nmrglue-ng should be considered for contribution back to `jjhelmus/nmrglue`. Upstream issues or pull requests are proposed separately and are never opened automatically.

The upstream contribution procedure itself is **not** documented here. It is
governed by `AGENTS.md` and by the `nmrglue-ng-dev` skill for the assessment
step, and by a separate, local-only policy in the `jjhelmus/nmrglue` working
clone for the audit, portage, and review steps. Independent development in
`nmrglue-ng` and generic upstream contribution stay separate activities: a fix
is developed, validated, and merged here first, and only then assessed for
portability.

### Deferred upstream contributions

Wait for maintainer feedback on the currently open upstream PRs before
submitting additional test-maintenance contributions.

Currently open upstream:

- #279 — `proc_lp`: replace removed `scipy.linalg.pinv2`.
- #280 — implement NMRPipe-compatible `HT -ps90-180`.
- #281 — migrate NMRPipe file-I/O tests to packaged fixtures.
- #282 — make Bruker JCAMP/pulse-program tests self-contained.

Do not prepare additional upstream PRs until #279–#282 receive meaningful
maintainer feedback. When that feedback arrives, resume upstream work from the
then-current `jjhelmus/nmrglue:master`, reconciling intervening upstream
changes before preparing each contribution. Do not reuse an old local
`upstream/master` snapshot for a portage.

Validated in nmrglue-ng but intentionally not yet ported upstream:

- JCAMP-DX `dicstructure` / nested-block autonomous tests (#22).
- CSDM synthetic conversion tests (#23).
- SIMPSON reader error-path autonomous test (#24).
- RNMRTK generated file-I/O tests (#25).
- **Corpus isolation for `test_bruker_3d` / `test_bruker_3d_lowmem` (#16)** —
  fix implemented and fully validated in nmrglue-ng (autonomous test +
  real-corpus round-trip with all four conversion branches). No upstream PR
  prepared.
