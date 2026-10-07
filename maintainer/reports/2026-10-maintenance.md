# Reader and infrastructure maintenance — October 2026

Consolidated 2026-10-07 at `ce98382`, from October reader/CI/pre-commit
assessments and the versioned change history. This report retains decisions,
limitations and attribution, not correspondence or session handoffs. It does
not provide new scientific validation or current lint counts.

## Bruker reader decisions

- **#50 — optional DC removal.** `remove_dc_offset=False` preserves the
  historical default. Opting in subtracts the mean along the last dimension
  before digital-filter removal; it also suppresses genuine signal at the
  carrier. This is an explicit trade-off, not a universally safe preprocessing
  step. It cannot be combined with `post_proc=True`.
- **#51 — DSPFVS fallback.** Values below 10 are clamped to 10. The local
  assessment records this as an accepted heuristic: no cited Bruker
  specification establishes the version-10 phase for every value 0–9.
  Do not describe this as vendor-validated support for all old filters.
- **#53 — text encoding.** Strict detection tries UTF-8 with BOM support,
  CP1252, then Latin-1 (warning on fallback), avoiding locale-dependent reads.
  Adapted from Shashank S. Harivyasi's
  [PR #261](https://github.com/jjhelmus/nmrglue/pull/261).
- **#55/#58 — axes.** See [processed-axis selection](2026-10-bruker-axes.md)
  for the option contract and corrected fixture interpretation.

The earlier reader note recorded 18 focused passes and 359 autonomous passes
with 3 skips, but did not pin those figures to a final commit. Use the
[dated release records](2026-10-release-validation.md), not those interim
counts, for release evidence.

## JCAMP-DX behavior and attribution

| nmrglue-ng PR | Behavior | Original contribution |
|---|---|---|
| #46 | nD NTUPLES pages and scaling | [Harivyasi #260](https://github.com/jjhelmus/nmrglue/pull/260) |
| #47 | Coordinate pairs, PEAKTABLE/XYPOINTS and decimal handling | [Harivyasi #262](https://github.com/jjhelmus/nmrglue/pull/262) |
| #49 | Configurable `read_err` decoding | [Harivyasi #259](https://github.com/jjhelmus/nmrglue/pull/259) |
| #52 | `read_blocks()` and block termination handling | [Harivyasi #277](https://github.com/jjhelmus/nmrglue/pull/277) |
| #54 | FID spectral-width calculation, complex-array option/helper and metadata flags | Local follow-up; related [FID discussion #231](https://github.com/jjhelmus/nmrglue/pull/231) |

Durable choices:

- In `(XY..XY)` data, commas delimit X/Y coordinates; blanket comma-to-dot
  replacement would destroy that structure. Decimal-comma handling must be
  distinguished by the data format. The local audit found no real example of
  this ambiguity among 253 inspected CENAPTNMR files, so that survey alone
  does not establish a complete real-world convention.
- `as_complex=False` preserves list-based return behavior; the opt-in helper
  produces a complex array for compatible real/imaginary components.
- If `DATATYPE` is absent, FID detection also examines `NTUPLES`.
- Time-domain spectral width uses `npoints / acquisition_time`, rather than
  interpreting a time-axis span as frequency width. Tests must preserve the
  time-unit and acquisition-time convention behind that formula.

At `34e057c`, the corpus audit recorded 58 autonomous JCAMP-DX tests passing.
The missing historical encoding-equivalence set remains a separate gap;
see [critical corpus](2026-10-critical-corpus.md). The old notes' instruction
to wait for reviews of already-merged #53 is superseded by the merge history.

## Varian and cross-format work

Varian multi-trace block-header reading (#36) and low-memory structural header
correction (#37) adapted the generic fixes proposed in
[PR #270](https://github.com/jjhelmus/nmrglue/pull/270) and
[PR #268](https://github.com/jjhelmus/nmrglue/pull/268). #38 corrected repetition
of the first block header: each block uses its own metadata, matching the
normal writer. Implementation is complete; real conversion references and
rights remain separate corpus requirements.

Observation/reference/carrier semantics are not fully settled across formats.
The reference-frequency/Tecmag proposal in
[PR #275](https://github.com/jjhelmus/nmrglue/pull/275) is not integrated in
full. Its proposed optional `ref` field and Tecmag metadata corrections need
comparison with current code, reproducible evidence and appropriately scoped
changes. The proposal itself is not proof of correctness in nmrglue-ng.

## CI and distribution design

#34 established Linux Python 3.10–3.14, Windows/macOS 3.14, optional CSDM
execution and isolated distribution validation. Key findings retained:

- CSDMpy 0.7.0 imported undeclared Astropy/Matplotlib dependencies; the CI job
  installs them explicitly, checks the import and rejects empty/skipped JUnit
  reports. These packages remain optional for nmrglue-ng.
- Compare source and installed versions using PEP 440 normalization:
  `0.13-dev` and `0.13.dev0` are equivalent development versions.
- A report test shipped in the sdist needs its imported helper too. Both
  `tests/test_ci_validation.py` and `.github/scripts/check_test_report.py`
  are explicitly included; CI exercises the extracted-sdist test outside the
  checkout. This does not assert that the full repository suite runs from sdist.
- Wheel validation checks installed imports outside the source tree and then
  runs selected packaged tests. Source-tree import success alone is insufficient.
- Windows exposed `os.rename()` refusing an existing destination in the Bruker
  isolation helper. `os.replace()` preserves the intended overwrite operation.
  Independent review and hosted CI confirmed the bounded correction.

[Run 37234329307](https://github.com/spectrochempy/nmrglue-ng/actions/runs/37234329307)
at PR #34 commit `40cd743` passed all nine then-configured jobs. Subsequent
pre-commit adds the tenth. The current validation profiles and reproduction
instructions are maintained in [CONTRIBUTING.md](../../CONTRIBUTING.md).
Artifact retention, schedules and successful PR jobs do not by themselves
establish branch-protection configuration or release-corpus validation.

## Minimal code-quality checks

#35 introduced structural/text checks with exclusions protecting scientific
fixtures and historical examples. The large-file hook uses `--enforce-all`
so a clean CI checkout is checked, with an explicit exclusion for known large
NMRPipe fixtures. The implementation audit checked that a 600 KB temporary
file outside the exclusion failed and excluded fixtures were skipped.

An initial Ruff audit at base `7a060fa` recorded 137 lint findings and 106
files that formatting would change. These are historical counts, not current
measurements. Ruff linting/formatting remain deferred to a separate reviewed
change; codespell is not part of the active pre-commit configuration.

## Corpus safety and test migration

Thirty-one high-value tests were migrated to packaged/generated fixtures:
NMRPipe path/bytes (12), Bruker text (3), JCAMP-DX structure (2), CSDM (3),
SIMPSON error path (1), RNMRTK I/O (10). That migration does not replace all
external scientific references.

#27 moved Bruker 3D conversion setup to copied temporary data, protecting the
canonical corpus from `acqu3s` creation. The isolation regression covers both
source states. Historical execution recorded both conversion orders and
unchanged checksums; the recorded `FDDMXVAL` exclusion remains a qualification.
Current corpus integrity and coverage are in the
[corpus report](2026-10-critical-corpus.md).
