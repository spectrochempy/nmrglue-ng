# nmrglue-ng roadmap

Status updated on **2026-10-14**, against `27f1909` (tag `v1.0.2`). This is the current
action list; dated evidence and qualifications live in the
[maintainer reports](README.md). Consolidation is not a new test run or a
change to scientific validation results. The approved local-data policy below
changes how rights/acquisition evidence is assessed; other recommendations
require maintainer approval where they change the release contract.

## P0 — First independent release

The first independent release line is published: **1.0.0**, **1.0.1** and
**1.0.2** were released on 2026-10-14 and uploaded to PyPI by the manual
`publish-pypi` workflow; Read the Docs `stable` and `latest` are live. Versions
are derived from Git tags with `setuptools_scm` (#99), so the release tag is the
version source. Publication stays an explicit maintainer action for every
release: tag creation, PyPI/GitHub release publication and any Conda
publication are never implied by a merge. The remaining scientific reliability
topics below are tracked follow-up work rather than first-release blockers.

- [x] Independent identity, attribution and contribution governance.
- [x] Independent packaging: distribution `nmrglue-ng`, import `nmrglue`.
- [x] Autonomous CI contract, representative platforms, optional CSDM job,
  installed-distribution validation and minimal pre-commit checks.
- [x] Historical critical contract identified: 16 logical groups / 42 tests.
- [x] Versioned external-data manifest and local size/SHA-256 verifier.
- [x] Implement the approved first-release corpus dispositions in the
  capability/test/reference contract (see [policy](testdata-policy.md)).
  Contract translation and local reference integration were completed on
  2026-10-09 at `7a7f935` and reviewed the same day in a separate session
  (changes requested: three minor documentation/coverage findings, no
  scientific or gating defect; findings verified addressed the same day — see the
  review note and implementer follow-up in the
  [corpus report](reports/2026-10-critical-corpus.md#independent-review-of-the-contract-translation-and-integration--2026-10-09)):
  the manifest contract
  now carries 29 first-release critical tests plus 13 explicitly deferred
  (RNMRTK/Sparky/JEOL historical reference profiles, tests and declarations
  retained), and the validated NMRPipe/SIMPSON references are in the local
  corpus with their inventory. The historical Bruker pdata replacement is
  complete and independently rechecked: fixture-derived metadata and
  read/write round-trip evidence pass, and the verifier rejects `replaced`
  declarations without non-empty license and provenance. The two pdata
  components count as explicit `replaced` coverage. The two JCAMP-DX critical
  components are replaced by committed synthetic CC0 fixtures covering
  AFFN/PAC/SQZ/DIF equivalence and NTUPLES real/imaginary arrays.
  Historical counts (14/42 passes,
  28 missing-file failures at `34e057c`) remain evidence of the old contract,
  not a new result.
- [x] Correct manifest scope: missing conversion references are inventoried
  or explicitly declared absent before calling groups complete; the verifier
  separates file integrity from required-component availability and returns 2
  while critical components are missing. Independent review and targeted
  counter-review corrections are applied (manifest shipped in the sdist,
  extractor scope stated exactly and pinned, module docstring qualified);
  the maintainer confirmed the reserved scope decisions recorded in the
  corpus report.
  [Corpus report](reports/2026-10-critical-corpus.md).
- [x] Accept the identified historical nmrglue archive for local validation
  (maintainer decision 2026-10-08). Keep use acceptance separate from
  redistribution status; see [test-data policy](testdata-policy.md).
- [x] Establish provenance and accepted test use for retained critical sources,
  and rights for data actually distributed. As of `3369943`, the manifest and
  verifier record 19/19 release-critical components covered (15 present, 4
  replaced, 0 absent). Accepted local-only archive and generated-reference inputs
  remain `UNRESOLVED` for redistribution under the policy and are not cleared for
  publication; the distributed Bruker `pdata` and JCAMP-DX replacement fixtures
  record CC0 provenance/license and checksummed fixture inventory.
- [x] Document reproducible, checksum-verified acquisition and record complete
  critical-dataset validation. Local/manual evidence is acceptable; public
  dataset CI and redistribution of the whole corpus are not prerequisites.
  Maintainer decision 2026-10-14: the recorded local validation, manifest,
  replacement fixtures, deferred historical references and non-blocking P1
  scientific follow-ups are sufficient to prepare the stable 1.0.0 release.
- [x] Complete the broader inherited-defect assessment for first-release scope.
  Maintainer decision 2026-10-11: tracked release-critical inherited defects are
  fixed, independently reviewed, replaced, or deferred under the current
  first-release contract. Remaining scientific-reliability topics under P1
  (Bruker axis coverage, observation/reference/carrier and Tecmag semantics,
  JCAMP-DX real-data and tuple-size validation, and NMRPipe/JRES dimensional
  metadata) remain visible follow-up work but do not block the first independent
  release.
- [x] Independent review of PRs #56/#57 and their interaction, completed
  2026-10-07 at `23cdba1`: all three verdicts approved. PR #55 also has a
  recorded independent review; its documentation findings were addressed by #58.
- [x] Documentation build and public documentation structure verified. Private
  documentation build verified on 2026-10-11 at `fe85fe2` with
  `python -m sphinx -W -b html doc/source <local-html-output>` in a disposable
  environment. PRs #90 and #92–#96 completed the tutorial-first public path,
  example notebook migration, top-level contribution docs, English/French
  documentation build and targeted French translations. Final RTD project setup
  remains an operational publication step, not a content blocker.
- [x] Finalize version, release notes, artifact scope and publication procedure
  (version scheme decided 2026-10-11: independent SemVer line, target `1.0.0`;
  the `-dev` suffix, dated changelog heading, known PR-reference cleanup,
  artifact build, tag and publication all remain explicit maintainer-authorized
  release-preparation steps; see Decisions and near-term work).

The [critical-corpus report](reports/2026-10-critical-corpus.md) records the
42-test breakdown, all 16 groups, reference gaps and rights status. The
[release report](reports/2026-10-release-validation.md) records the
NMRPipe differential result: 44/47 on version 13.0 Rev 2026.072.12.03.
Neither missing data nor classified historical differences are passing tests.

## Decisions and near-term work

| Topic | Next action / decision |
|---|---|
| Release publication | Manual `publish-pypi` workflow (`workflow_dispatch` with `tag` and `expected_version`) using Trusted Publishing; each release is a separate maintainer action. Stable `1.0.0`, `1.0.1` and `1.0.2` were published on 2026-10-14; `1.0.2` shipped the documentation `What's new` page and navigation/sidebar updates. |
| Version scheme | Maintainer decision 2026-10-11: `nmrglue-ng` adopts its own independent SemVer line rather than continuing the historical `0.13`, because the two distributions can evolve in parallel and a shared line would imply a linear succession that does not exist. First independent release targets `1.0.0` (optionally published first as `1.0.0rc1`). The number is a public-API compatibility contract internal to `nmrglue-ng`, not a comparison with historical `nmrglue`, which never left `0.x`. Since #99 the version is derived from Git tags with `setuptools_scm`, so the release tag is the version source and no version file is edited. Stable `1.0.0`, `1.0.1` and `1.0.2` were published on 2026-10-14. |
| Upstream synchronization before `1.0.0rc1` | New release-candidate gate (2026-10-11): before publishing `1.0.0rc1`, audit the then-current `jjhelmus/nmrglue` upstream and ensure `nmrglue-ng` either includes upstream changes that should be carried into the release, or explicitly records a maintainer decision to defer/exclude them with scope and rationale. This does not authorize upstream contribution and does not require adopting upstream changes whose behavior conflicts with documented `nmrglue-ng` decisions. |
| Documentation and RTD before final `1.0.0` | Maintainer decision 2026-10-11: do not rush the final release before public Read the Docs documentation is substantially useful to new users. Additional release candidates such as `1.0.0rc2` or `rc3` are acceptable if needed for documentation review. Keep a mixed source model: reStructuredText remains appropriate for API/reference and stable inherited pages, while MyST-NB is preferred for modern tutorials and rewritten examples. Before final `1.0.0`, differentiate the documentation from historical upstream `nmrglue`, provide a tutorial-first public path, and progressively migrate selected historical examples into pedagogical notebooks with figures, explicit outputs, downloadable data and provenance. Preserve historical attribution and keep unmigrated examples accessible as legacy material rather than converting them mechanically. |
| Critical contract | The 2026-10-08 decisions are translated into the generator/manifest at `7a7f935` (2026-10-09, reviewed the same day; minor findings addressed the same day): `CRITICAL_TESTS` holds the 29 first-release ids, `DEFERRED_TESTS` the 13 deferred RNMRTK/Sparky/JEOL ids, component scope is three-valued (`critical`/`deferred`/`extended`), manifest schema v4. Bruker pdata replacement is complete: the two components are explicitly `replaced` against committed CC0 fixtures, with checksummed inventory, fixture-derived read metadata and read/write round trips. Independent follow-up confirms malformed replacement license/provenance declarations fail structurally. JCAMP-DX critical components are now replaced by synthetic CC0 fixtures with checksummed inventory for AFFN/PAC/SQZ/DIF and NTUPLES coverage. SIMPSON requirements remain. [Corpus report](reports/2026-10-critical-corpus.md#bruker-pdata-replacement--2026-10-09). |
| Coverage badge | Maintainer decision 2026-10-14: coverage badge policy is postponed until after stable `1.0.0` (now released) and is not a release blocker. Track as `NMRNG-kb5.22`; any badge must describe autonomous CI coverage only and must not imply external-corpus or NMRPipe differential validation. |
| Conda packages | Maintainer decision 2026-10-14: Conda publication is postponed until after stable `1.0.0` (now released) and is not a release blocker. Track as `NMRNG-kb5.20`; evaluate conda-forge, spectrocat, or both using the published 1.0.x artifacts. |
| Google Colab validation | Maintainer decision 2026-10-14: hosted Colab validation is postponed until after stable `1.0.0` (now released) and is not a release blocker. Track as `NMRNG-kb5.21`; public install commands and stable artifacts now exist. |
| Local corpus use | Historical archive accepted for local testing; `UNRESOLVED` redistribution status alone no longer blocks those tests. Identify missing references and record actual results. |
| Data redistribution | Distribute only files/groups with recorded public-domain status, an applicable license or permission; keep other accepted inputs local/private. |
| NMRPipe conversion references | The `FDDMXVAL` correction is integrated in #65 (`7ef9b8f`). Recorded NMRPipe 13.0 validation: all eight Agilent/Bruker full/low-memory cases pass in disposable copies. On 2026-10-09 the five references were regenerated (132 files) and validated with the FDDMXVAL regression (9 passed) then integrated into the local corpus; Bruker outputs are byte-identical to the 2026-10-08 receipts, Agilent outputs differ only in the var2pipe conversion-timestamp header fields. Independently reviewed 2026-10-09 (byte identity and timestamp property reproduced by the reviewer). [Corpus evidence](reports/2026-10-critical-corpus.md#contract-translation-and-local-reference-integration--2026-10-09). |
| RNMRTK/Sparky references | Deferred from first-release critical scope by maintainer decision; retain tests and format support, document absent real-reference validation, and revisit with contributed data. The deferral is translated into the contract (`DEFERRED_TESTS`, component scope `deferred`); nothing remains to do on the manifest side. |
| Packaged fixtures | Choose a consistent provenance/checksum verification scheme; the external manifest does not currently cover them. |
| Bruker `pdata` | Replacement implemented and independently reviewed: fixture metadata and `read -> write -> read` evidence replace the four historical tests; the two components are `replaced` with checksummed CC0 fixtures. Missing, blank and whitespace-only license/provenance declarations fail structurally. Integrated in #69 (`9296e3f`). |
| Bruker JCAMP line endings | Fixed in #81 (`2c50110`): `read_jcamp()` uses universal newline handling after deterministic decoding, with a self-contained CR-only regression and the installed-wheel functional count updated to 65. |
| JCAMP-DX encodings | Synthetic CC0 replacement fixtures preserve the historical AFFN/PAC/SQZ/DIF equivalence, metadata, point-count and sampled-value checks for `test_jcampdx1`. |
| JCAMP-DX tuples | Synthetic CC0 NTUPLES replacement fixtures preserve real/imaginary array shape, metadata, point-count and sampled-value checks for `test_jcampdx1`; `(XYW..XYW)` / `(XYM..XYM)` tuple-size behavior remains a separate P1 validation before adapting upstream #262. |
| JCAMP-DX FID metadata | Aligned locally with final upstream #231/#291 semantics after #54: FID sweep width uses `(N - 1) / (LAST-FIRST)`, complex arrays use `np.iscomplexobj`, `as_complex=True` leaves incomplete R/I pairs unchanged, and NTUPLES fallback requires exact `NMR FID` when `DATATYPE` is absent. The synthetic FID fixture now uses sampling-consistent LAST coordinates. Targeted validation: `tests/fileio/test_jcampdx_fixtures.py` passed on 2026-10-08. |
| JCAMP-DX processed endpoint axes | Fix prepared for GitHub issue #86: for descending processed spectra, `guess_udic()` converts `FIRSTX`/`LASTX` endpoint spans to the universal-dictionary spectral-width convention and adjusts `car`, so `uc_from_udic()` reconstructs point 0 and point `N - 1` at the JCAMP endpoints. |
| Bruker processing-file priority | Investigated 2026-10-14 (`NMRNG-kb5.7.1`): the default status files (`procs`/`procNs`) are the correct source for the axis, shape and scaling parameters `nmrglue` consumes, and the singular `proc`/`procN` files may carry stale `NC_proc`/`XDIM`/`STSI`, so broadening default discovery (upstream #264) is rejected. Maintainer decision 2026-10-14: keep the default, keep explicit `procs_files` selection (#55) for the editor-only parameters such as `ABSF1`/`ABSF2` (unused by axis/shape/scaling), and document the two file families; the docstring clarification and test-only regression are a separate follow-up task. [Evidence](reports/2026-10-bruker-processing-file-selection.md). |
| SIMPSON | Shape correction integrated in #66 (`d9ba184`): single-element 1D TEXT/BINARY returns `(NP,)`, preserving multi-element/2D behavior and BINARY header checks. Independent review and counter-review approved it. Recorded validation: 441 autonomous passes with CSDM and 4/4 dataset tests on disposable outputs. On 2026-10-09 the 16 encoding outputs were regenerated from `rr.in`/`2d.in` (SIMPSON 4.2.1, system Tcl 8.6.17), validated (4/4 dataset tests, 9/9 autonomous shape regressions) and integrated into the local corpus. Independently reviewed 2026-10-09 (1D outputs reproduced byte-identically by the reviewer). [Resolution evidence](reports/2026-10-critical-corpus.md#shape-contract-resolution--2026-10-08) and [integration evidence](reports/2026-10-critical-corpus.md#contract-translation-and-local-reference-integration--2026-10-09). |
| JEOL | Historical independent reference pairs are deferred from first-release critical scope; retain the reader and licensed autonomous tests. Revisit with user demand or contributed data/reference results, potentially from the reader author. No contact is authorized by this entry. |
| `data_nd` | Reviews approved at `23cdba1`; changelog references corrected to #56/#57. The documented Boolean-axis compatibility difference remains outside these fixes. |
| Test hygiene | Make failed NMRPipe comparisons clean generated artifacts reliably. |
| Single test tree | Integrated in #64 at `805c6f2`, following implementation/review based on `35fd95d`; [evidence](reports/2026-10-test-layout-plan.md) records parity and distribution validation. |

Upstream gate audit on 2026-10-11 compared `jjhelmus/nmrglue` master
`cd0c2c9` with local/origin master `443bbcf`, then #81 (`2c50110`) carried the
missing #261 CR-only Bruker JCAMP newline correction. The only new
upstream-master change since `812bfa0`, JCAMP-DX FID #231, is already carried
by local #54/#63; EXT #289 is carried by #62 with the reviewed local clipping
distinctions. Maintainer decision 2026-10-11: defer optional #258 bounded
autophase to P2, exclude #283's conflicting ZD API/boxcar change for rc1, and
classify the remaining optional upstream proposals as non-blocking for rc1.
Existing P1 Bruker axis/processing-file and JCAMP-DX tuple-size follow-ups
retain the approved non-blocking scope. With #81 merged and these dispositions
recorded, **NMRNG-kb5.17 is closed**.
The complete merged-change inventory, open-proposal screening, rationale and
limits are in the
[rc1 synchronization assessment](reports/2026-10-upstream-sync.md#release-candidate-reconciliation--2026-10-11).

Follow-up upstream review on 2026-10-13 found `jjhelmus/nmrglue` master still
at `cd0c2c9`, with no new upstream commits since the 2026-10-11 gate review.
Upstream PRs #291 and #293 are open and cleanly mergeable with no maintainer
feedback; their corresponding JCAMP-DX fixes are already carried locally by the
recorded FID and descending-endpoint work. Upstream issues #290 and #292 are
also already covered locally by the reviewed `pipe_proc.ext` clipping and
FDDMXVAL corrections. PRs #280-#282 remain open without comments or reviews, so
the nonurgent test-infrastructure contribution hold remains in force. No new
local release-blocking backport was selected; review again before `1.0.0rc1` or
when upstream master/PR feedback changes.

## P1 — Scientific reliability

- [x] `data_nd` copy and negative-axis fixes (#33), 1D transpose (#56), and
  integer-axis validation (#57). [Scope and evidence](reports/2026-10-data-nd.md).
- [x] Varian multi-trace reading and low-memory writer headers (#36–#38).
- [x] ZD width contract (#9), SAVE metadata (#13), QR solver (#14), and
  HT `ps90-180` (#15).
- [x] Explicit Bruker processing-parameter selection (#55), documentation and
  provenance clarification (#58). This is an option, not evidence of a general
  defect in the historical default. [Scientific report](reports/2026-10-bruker-axes.md).
- [ ] Complete Bruker axis coverage with coherent raw/processed references,
  an indirect acquisition header and genuine `STSR`/`STSI` extraction cases.
  Default-path changes require evidence and a separate compatibility decision.
- [ ] Specify `obs` / `ref` / `car` semantics and ppm conversions; assess the
  still-unintegrated parts of the proposed reference-frequency/Tecmag work
  ([historical contribution #275](https://github.com/jjhelmus/nmrglue/pull/275))
  against current code before deciding on implementation.
- [ ] Complete JCAMP-DX real-data and encoding-equivalence validation after
  #46/#47/#49/#52/#54. [Reader decisions](reports/2026-10-maintenance.md).
- [ ] Investigate NMRPipe/JRES dimensional metadata behavior.
- [x] `pipe_proc.ext` indirect metadata and upper-bound correction: targeted
  third review on 2026-10-08 approved the reviewed correction; PR #62 was
  integrated at `a662316` (master verified on 2026-10-08). All nine
  regressions pass within the 48-test unit file, and independent NMRPipe comparisons verify
  clipping, rounded-window placement and saturation. Track inherited
  X1/XN/APOD, fractional-CENTER and quadrature limitations separately.
  [Evidence and scope](reports/2026-10-pipe-proc-ext.md).

## P2 — Broader maintenance

- [x] Repair and modernize historical examples selected for the current docs
  structure. PRs #92–#95 converted conversion, processing, plotting,
  quantification, coadd, separation/acquisition, interactive and simulation
  examples to executable MyST-NB pages or retained them as explicit historical
  material.
- [ ] Define optional-dependency extras where useful.
- [ ] Increase autonomous processing-module coverage.
- [x] Prepare the dedicated test-reorganization plan after EXT #62:
  [inventory, mapping and validation design](reports/2026-10-test-layout-plan.md),
  assessed on 2026-10-08 at `a662316`: 269 tracked files, 35 collected modules,
  575 collected items. Collection is not a functional validation result.
- [x] Test layout A — approved fixture checksum policy, runtime-only wheel,
  `_dataset_paths.py`, preserved pytest import mode and validation
  environments. Captured IDs, parameters, markers/skips and fixture hashes on
  `35fd95d`; the 578-item comparison is bijective in matched environments.
- [x] Test layout B — one atomic migration to a single `tests/` tree with
  `fileio/`, `process/`, `analysis/`, `infrastructure/`, `fixtures/` and
  `tests/conftest.py`, updating all path
  consumers, CI, packaging, docs/examples and manifest declarations together.
  The 42-test critical contract / nine scanned modules, assertions, tolerances,
  dependency markers/skips and external `data/` are retained. Fixtures match
  by SHA-256, size and mode.
- [x] Test layout C — independent review of parity and artifact evidence:
  execute the mapped 65 NMRPipe/Bruker wheel cases outside checkout with
  site-packages origin checks inside pytest; retain separate sdist functional
  validation and all CI guarantees. Report unavailable dataset/software
  coverage explicitly and clean disposable validation resources. No durable
  dual layout, scientific correction, new release gate or critical-scope
  reduction is implied by this work; integrated in #64 at `805c6f2`.
- [x] Modernize documentation and links for the current release structure.
- [x] Differentiate documentation identity before final `1.0.0`: update the
  theme/template, introduction and `nmrglue`/`nmrglue-ng` references where
  needed, while preserving historical and import-compatibility references.
- [x] Prepare public RTD-quality documentation before final `1.0.0`, using
  additional release candidates if useful. The planned work is tracked under
  `NMRNG-kb5.18.1`: add a fast documentation build without the expensive API
  reference for iteration, rewrite the public skeleton, modernize the core
  tutorials as MyST-NB notebooks, triage legacy examples for notebook migration
  versus archive/defer status, and define RTD-ready validation criteria. The
  reference API remains available in the full build; mixed `.rst` and `.md`
  sources are intentional. Completed for the current structure by PRs #90–#96;
  future improvements should be opened as focused post-release beads.
- [ ] Introduce linting, typing and benchmarks only through separately scoped
  work. Ruff linting/formatting remain deferred; minimal pre-commit is active.

## Contribution boundary

Generic improvements may be candidates for the historical project, but local
development and external submission are separate decisions. Follow
[AGENTS.md](../AGENTS.md): the existing pause is tied to meaningful feedback on
[PRs #279–#282](https://github.com/jjhelmus/nmrglue/pulls?q=is%3Apr+author%3Afernandezc)
and concerns QR solving, HT, NMRPipe fixtures and Bruker text fixtures.
Live check on 2026-10-08 confirms [#279](https://github.com/jjhelmus/nmrglue/pull/279)
was merged (`255855d`), providing substantive upstream action on this group.
Other contribution and publication permissions remain explicit. Any future
port starts from the then-current `jjhelmus/nmrglue:master`.

Candidates previously deferred include the autonomous JCAMP-DX, CSDM,
SIMPSON and RNMRTK tests (#22–#25), and corpus isolation (#27).
Maintainer decision (2026-10-08): defer new nonurgent test-infrastructure and
test-migration contributions until the anticipated upstream test reorganization
can be assessed. Avoid overlapping maintenance PRs and unnecessary review load.
This does not close or withdraw existing PRs, and does not assume a delivery
date for that reorganization. Reassess these candidates against the resulting
current upstream tree before preparing a port. Generic product fixes remain
separate, individually authorized contribution decisions.
Show the exact text of every proposed upstream issue, PR or
comment and obtain explicit approval before publishing it. Outbound drafts
and correspondence tracking belong in local notes, not this roadmap.
