# nmrglue-ng roadmap

This roadmap is intentionally short and living. Detailed evidence belongs in dated files under `maintainer/audits/`.

## P0 — First independent release

- [x] Establish independent project identity and preserve upstream attribution.
- [x] Add contribution governance.
- [ ] Establish independent packaging: distribution `nmrglue-ng`, import `nmrglue`.
- [ ] Define and enforce the self-contained CI test contract.
- [ ] Establish independent documentation and Read the Docs deployment.
- [ ] Define reproducible test-data infrastructure and provenance.
- [ ] Review critical inherited defects before the first release.

## P1 — Scientific reliability

- [ ] Secure `data_nd` copy and negative-axis behavior.
- [ ] Fix and validate Varian low-memory I/O defects.
- [ ] Resolve the current `zd_*` NumPy compatibility defect.
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
