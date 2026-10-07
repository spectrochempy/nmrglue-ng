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
- [ ] Correct manifest scope: missing conversion references must be inventoried
  or explicitly declared absent before calling groups complete.
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
| Conversion references | Document all dependencies first; evaluate generation in a temporary copy, then assess provenance and redistribution separately. |
| Packaged fixtures | Choose a consistent provenance/checksum verification scheme; the external manifest does not currently cover them. |
| Bruker `pdata` writer | Add autonomous read/write/read evidence using a copied, licensed fixture. |
| JCAMP-DX encodings | Split the monolithic dataset test while preserving AFFN/PAC/SQZ/DIF equivalence and metadata checks. |
| SIMPSON | Evaluate regeneration of 1D/2D encoding sets before deciding whether to reduce release scope. |
| JEOL | Decide whether packaged fixtures can replace missing historical groups; explicitly account for the lost NMRPipe cross-reference. |
| `data_nd` | Reviews approved at `23cdba1`; changelog references corrected to #56/#57. The documented Boolean-axis compatibility difference remains outside these fixes. |
| Test hygiene | Make failed NMRPipe comparisons clean generated artifacts reliably. |

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

## P2 — Broader maintenance

- [ ] Repair historical examples, including the Bruker processed 1D example,
  and retain an extraction/`strip_fake` demonstration.
- [ ] Define optional-dependency extras where useful.
- [ ] Increase autonomous processing-module coverage.
- [ ] Modernize documentation and links incrementally.
- [ ] Introduce linting, typing and benchmarks only through separately scoped
  work. Ruff linting/formatting remain deferred; minimal pre-commit is active.

## Contribution boundary

Generic improvements may be candidates for the historical project, but local
development and external submission are separate decisions. Follow
[AGENTS.md](../AGENTS.md): the existing pause tied to meaningful feedback on
[PRs #279–#282](https://github.com/jjhelmus/nmrglue/pulls?q=is%3Apr+author%3Afernandezc)
is unchanged. They concern QR solving, HT, NMRPipe fixtures and Bruker text
fixtures. Check live feedback before interpreting this condition. Any future
port starts from the then-current `jjhelmus/nmrglue:master`.

Candidates previously deferred include the autonomous JCAMP-DX, CSDM,
SIMPSON and RNMRTK tests (#22–#25), and corpus isolation (#27). No submission
is implied. Show the exact text of every proposed upstream issue, PR or
comment and obtain explicit approval before publishing it. Outbound drafts
and correspondence tracking belong in local notes, not this roadmap.
