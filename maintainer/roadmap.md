# nmrglue-ng roadmap

Status consolidated on **2026-10-07**, against `23cdba1`. This is the current
action list; dated evidence and qualifications live in the
[maintainer reports](README.md). Consolidation is not a new test run or a
change to release gates. Recommendations below require maintainer approval
where they change the release contract.

## P0 — First independent release

The recorded readiness verdict remains **BLOCKED**. See
[release validation](reports/2026-10-release-validation.md) for gates G1–G6.

- [x] Independent identity, attribution and contribution governance.
- [x] Independent packaging: distribution `nmrglue-ng`, import `nmrglue`.
- [x] Autonomous CI contract, representative platforms, optional CSDM job,
  installed-distribution validation and minimal pre-commit checks.
- [x] Historical critical contract identified: 16 logical groups / 42 tests.
- [x] Versioned external-data manifest and local size/SHA-256 verifier.
- [ ] Approve a revised capability/test/reference contract. At `34e057c`,
  14 historical critical tests passed and 28 failed for missing files;
  new autonomous fixtures do not automatically replace those references.
- [x] Correct manifest scope: missing conversion references are inventoried
  or explicitly declared absent before calling groups complete; the verifier
  separates file integrity from required-component availability and returns 2
  while critical components are missing. Independent review and targeted
  counter-review corrections are applied (manifest shipped in the sdist,
  extractor scope stated exactly and pinned, module docstring qualified);
  the maintainer confirmed the reserved scope decisions recorded in the
  corpus report.
  [Corpus report](reports/2026-10-critical-corpus.md).
- [ ] Resolve provenance/redistribution for the retained critical corpus.
- [ ] Provide reproducible, checksum-verified data acquisition and
  scheduled/manual critical-dataset validation.
- [ ] Complete the broader inherited-defect assessment; the targeted reviews
  below do not settle all scientific questions, including the reference-frequency
  and Tecmag work discussed under P1.
- [x] Independent review of PRs #56/#57 and their interaction, completed
  2026-10-07 at `23cdba1`: all three verdicts approved. PR #55 also has a
  recorded independent review; its documentation findings were addressed by #58.
- [ ] Repair the documentation build and establish independent deployment.
- [ ] Finalize version, release notes, artifact scope and publication procedure.

The [critical-corpus report](reports/2026-10-critical-corpus.md) records the
42-test breakdown, all 16 groups, reference gaps and rights status. The
[release report](reports/2026-10-release-validation.md) records the
NMRPipe differential result: 44/47 on version 13.0 Rev 2026.072.12.03.
Neither missing data nor classified historical differences are passing tests.

## Decisions and near-term work

| Topic | Next action / decision |
|---|---|
| Critical contract | Approve replacements individually; no JEOL, JCAMP-DX or SIMPSON requirement has been waived. |
| NMRPipe conversion references | Local NMRPipe 13.0 generation and the independently reviewed focused `FDDMXVAL` correction are recorded in the [corpus report](reports/2026-10-critical-corpus.md): all eight Agilent/Bruker full/low-memory cases pass in disposable copies. Corpus/manifest/provenance integration remains a separate explicit authorization. |
| Packaged fixtures | Choose a consistent provenance/checksum verification scheme; the external manifest does not currently cover them. |
| Bruker `pdata` writer | Add autonomous read/write/read evidence using a copied, licensed fixture. |
| Bruker JCAMP line endings | Reproduce CR-only decoding with a self-contained fixture, then consider the upstream #261 `StringIO(..., newline=None)` correction in a separate fix. |
| JCAMP-DX encodings | Split the monolithic dataset test while preserving AFFN/PAC/SQZ/DIF equivalence and metadata checks. |
| JCAMP-DX tuples | Validate `(XYW..XYW)` / `(XYM..XYM)` tuple-size behavior independently, then adapt upstream #262 in a separate change if the evidence supports it. |
| JCAMP-DX FID metadata | Aligned locally with final upstream #231/#291 semantics after #54: FID sweep width uses `(N - 1) / (LAST-FIRST)`, complex arrays use `np.iscomplexobj`, `as_complex=True` leaves incomplete R/I pairs unchanged, and NTUPLES fallback requires exact `NMR FID` when `DATATYPE` is absent. The synthetic FID fixture now uses sampling-consistent LAST coordinates. Targeted validation: `tests/fileio/test_jcampdx_fixtures.py` passed on 2026-10-08. |
| Bruker processing-file priority | Scientific investigation and a compatibility decision are still required before choosing `proc`/`proc2` versus `procs`/`proc2s` precedence. |
| SIMPSON | Single-element 1D TEXT/BINARY returns `(NP,)`; multi-element and 2D shapes are preserved. Nine autonomous regressions include BINARY missing-NP/short-block guards. Review and targeted counter-review approved the correction on 2026-10-08; delivery is authorized, integration pending. Recorded validation: 441 autonomous passes and 4/4 dataset tests on disposable outputs. Generated-reference/corpus integration remains separately authorized. [Resolution evidence](reports/2026-10-critical-corpus.md#shape-contract-resolution--2026-10-08). |
| JEOL | Decide whether packaged fixtures can replace missing historical groups; explicitly account for the lost NMRPipe cross-reference. |
| `data_nd` | Reviews approved at `23cdba1`; changelog references corrected to #56/#57. The documented Boolean-axis compatibility difference remains outside these fixes. |
| Test hygiene | Make failed NMRPipe comparisons clean generated artifacts reliably. |
| Single test tree | Implemented and independently reviewed at `35fd95d`; [evidence](reports/2026-10-test-layout-plan.md) records the atomic move, runtime-only wheel and sdist-derived functional validation. |

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

- [ ] Repair historical examples, including the Bruker processed 1D example,
  and retain an extraction/`strip_fake` demonstration.
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
  execute the mapped 64 NMRPipe/Bruker wheel cases outside checkout with
  site-packages origin checks inside pytest; retain separate sdist functional
  validation and all CI guarantees. Report unavailable dataset/software
  coverage explicitly and clean disposable validation resources. No durable
  dual layout, scientific correction, new release gate or critical-scope
  reduction is implied by this plan; implementation needs authorization.
- [ ] Modernize documentation and links incrementally.
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
SIMPSON and RNMRTK tests (#22–#25), and corpus isolation (#27). No submission
is implied. Show the exact text of every proposed upstream issue, PR or
comment and obtain explicit approval before publishing it. Outbound drafts
and correspondence tracking belong in local notes, not this roadmap.
