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
  Assessment: the corpus comes from the upstream nmrglue v0.5 release under
  the project's BSD-3-Clause license. No separate data license was specified;
  the repository license applies to release assets by default. 11 local groups
  are now marked BSD-3-Clause. JEOL data was never published upstream (PR #228
  added code+tests only; maintainer asked about data but no resolution was
  recorded) — marked NOT_AVAILABLE. Missing groups (Sparky, RNMRTK, JCAMP-DX,
  SIMPSON encoding sets) need acquisition or regeneration.
- [x] Add a versioned manifest with sizes and SHA-256 checksums.
  `maintainer/testdata-manifest.toml` tracks 145 files across 11 local
  groups; regeneration and verification scripts provided.
- [ ] Add an explicit checksum-verifying test-data fetcher.
  `scripts/verify_testdata.py` verifies local data against the manifest.
  A download fetcher remains to be designed once redistribution rights are
  established for the missing groups.
- [ ] Add scheduled/manual dataset validation.
  CI dataset job requires the corpus to be reproducibly obtainable; blocked
  on rights resolution for missing groups.
- [ ] Review critical inherited defects before the first release.
- [x] Define the integer/float width contract and resolve the `zd_*` defect (#4).

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
- [ ] Consolidate JCAMP-DX behavior against documented and real-world fixtures.
- [ ] Investigate NMRPipe/JRES dimensional metadata behavior.

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
properties, not proximity checks. Issue #18 remains separate and untouched.

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
