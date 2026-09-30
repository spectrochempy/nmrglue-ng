# nmrglue-ng roadmap

This roadmap is intentionally short and living. Detailed evidence belongs in dated files under `maintainer/audits/`.

## NMRPipe 13 differential baseline

42/46 historical comparisons now pass against NMRPipe 13.0 after resolving ZD
in #9. The four remaining differences are JMOD, HT6, TP9, and SAVE. The
original 41/46 baseline and detailed classifications are recorded in
[`2026-09-nmrpipe-13-compatibility.md`](audits/2026-09-nmrpipe-13-compatibility.md).

## P0 — First independent release

- [x] Establish independent project identity and preserve upstream attribution.
- [x] Add contribution governance.
- [x] Establish independent packaging: distribution `nmrglue-ng`, import `nmrglue`.
- [x] Define and enforce the self-contained CI test contract.
- [ ] Establish independent documentation and Read the Docs deployment.
- [ ] Define reproducible test-data infrastructure and provenance.
- [ ] Review critical inherited defects before the first release.
- [x] Define the integer/float width contract and resolve the `zd_*` defect (#4).

## P1 — Scientific reliability

- [ ] Secure `data_nd` copy and negative-axis behavior.
- [ ] Fix and validate Varian low-memory I/O defects.
- [ ] Correct SAVE `FDPIPECOUNT` metadata compatibility (#6).
- [ ] Specify and implement HT `ps90-180` with scientific validation (#7).
- [ ] Restore and validate the `proc_lp` QR solver (#10).
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
