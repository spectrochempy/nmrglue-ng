# nmrglue-ng roadmap

This roadmap is intentionally short and living. Detailed evidence belongs in dated files under `maintainer/audits/`.

## NMRPipe 13 differential baseline

44/47 historical comparisons now pass against NMRPipe 13.0 after resolving ZD
in #9, SAVE in #13, and HT `ps90-180` in #15. HT4 is now genuinely collected,
so the denominator increased from 46 to 47. The remaining differences are
JMOD, HT6, and TP9; they retain their NMRPipe-version or historical-test
classifications rather than being treated as confirmed bugs. The original
41/46 baseline and detailed classifications are recorded in
[`2026-09-nmrpipe-13-compatibility.md`](audits/2026-09-nmrpipe-13-compatibility.md).

## P0 — First independent release

- [x] Establish independent project identity and preserve upstream attribution.
- [x] Add contribution governance.
- [x] Establish independent packaging: distribution `nmrglue-ng`, import `nmrglue`.
- [x] Define and enforce the self-contained CI test contract.
- [ ] Establish independent documentation and Read the Docs deployment.
- [ ] Migrate high-value tests to existing packaged/generated fixtures
  (12 NMRPipe path/bytes API, 3 Bruker text-parser, 2 JCAMP-DX block-structure,
  and 3 CSDM conversion tests migrated).
- [ ] Define the residual release-critical external dataset.
- [ ] Clear provenance and redistribution rights for release-critical data.
- [ ] Add a versioned manifest with sizes and SHA-256 checksums.
- [ ] Add an explicit checksum-verifying test-data fetcher.
- [ ] Add scheduled/manual dataset validation.
- [ ] Review critical inherited defects before the first release.
- [x] Define the integer/float width contract and resolve the `zd_*` defect (#4).

## P1 — Scientific reliability

- [ ] Secure `data_nd` copy and negative-axis behavior.
- [ ] Fix and validate Varian low-memory I/O defects.
- [x] Correct SAVE `FDPIPECOUNT` metadata compatibility (#6).
- [x] Specify and implement HT `ps90-180` with scientific validation (#7).
- [x] Restore and validate the `proc_lp` QR solver (#10).
- [ ] Specify observation/reference/carrier-frequency semantics and ppm conversion.
- [ ] Resolve Bruker processing-parameter source selection.
- [ ] Consolidate JCAMP-DX behavior against documented and real-world fixtures.
- [ ] Investigate NMRPipe/JRES dimensional metadata behavior.

## P2 — Broader maintenance

- [ ] Expand CI to representative Linux, macOS, and Windows jobs.
- [ ] Define optional dependency extras where appropriate.
- [ ] Increase autonomous coverage of processing modules and examples.
- [ ] Modernize historical documentation and links incrementally.
- [ ] Introduce linting, typing, and benchmarks only where they add clear maintenance value.

## Upstream policy

Generic, reproducible fixes that do not depend on the independent direction of nmrglue-ng should be considered for contribution back to `jjhelmus/nmrglue`. Upstream issues or pull requests are proposed separately and are never opened automatically.


### Deferred upstream contributions

Wait for maintainer feedback on the currently open upstream PRs before
submitting additional test-maintenance contributions.

Currently open upstream:

- #279 — `proc_lp`: replace removed `scipy.linalg.pinv2`.
- #280 — implement NMRPipe-compatible `HT -ps90-180`.
- #281 — migrate NMRPipe file-I/O tests to packaged fixtures.
- #282 — make Bruker JCAMP/pulse-program tests self-contained.

Validated in nmrglue-ng but intentionally not yet ported upstream:

- JCAMP-DX `dicstructure` / nested-block autonomous tests (#22).
- CSDM synthetic conversion tests (#23).

Do not prepare additional upstream PRs until #279–#282 receive meaningful
maintainer feedback. Resume upstream work from the then-current
`jjhelmus/nmrglue:master`, reconciling intervening upstream changes before
preparing each contribution.
