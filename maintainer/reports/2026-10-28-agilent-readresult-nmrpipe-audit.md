# Agilent/Varian raw 1D ReadResult and NMRPipe audit

Date: 2026-10-28

## Scope and baseline

This is a read-only multi-constructor audit. No nmrglue-ng product code,
reader, test fixture, or workflow was modified.

Audited nmrglue-ng baseline: `b28ad22` (merged raw Bruker ReadResult and
NMRPipe profiles through PR #145).

Existing task coordination was checked before this audit:

- `NMRNG-kb5.8.1` remains open for Varian-to-Pipe observation/carrier
  semantics;
- `scpy-89a` is closed after a bounded SpectroChemPy Agilent TPPI defect fix;
- `scpy-97j.5` remains deferred/open for the plugin ReadResult adapter;
- no duplicate Agilent ReadResult task was created.

## nmrglue-ng Agilent/Varian capabilities

The historical `nmrglue.fileio.varian` reader parses `procpar`, reads the
binary Varian file header and interleaved real/imaginary samples, returns
`complex64`, and reshapes data according to an explicit or inferred `torder`.
The supported trace-order vocabulary is `flat`, `regular` and `opposite`, with
callable mappings for less common layouts. `guess_udic()` currently populates
shape defaults but does not normalize SW/OBS/carrier metadata into a complete
interop result.

Relevant Agilent `procpar` fields are:

| Meaning | Typical fields | Audit finding |
|---|---|---|
| direct point count | `np` | real+imag storage; reader returns `np/2` complex points when even |
| direct width | `sw` | Hz |
| direct observation | `sfrq` or `dfrq` | MHz; fallback policy exists in SpectroChemPy reader |
| direct nucleus | `dn` or `tn` | string |
| indirect size | `ni`, `ni2`, ... | phase-array and shape logic required |
| indirect encoding | `phase`, `phase2`, ... | one value is treated as TPPI, two as States by plugin logic |
| reference/carrier candidates | `rfl`, `rfp`, `reffrq`, `tof` | semantics are not interchangeable; no generic inference is safe |
| scans/normalization | `ns`, `ne`, `nt` | plugin normalizes by `ns*ne`; nmrglue raw reader does not |

The converter and NMRPipe writer can consume a universal dictionary, but the
Varian reader does not currently produce a normalized `ReadResult` profile.

## Agilent raw 1D experiment

The local historical Agilent `agilent_1d` corpus was used read-only. Its
provenance/redistribution status remains historical and unresolved; it is
local validation evidence, not a new public fixture.

Observed nmrglue-ng values:

```text
shape/dtype: (1500,) complex64
np: 3000
sw: 50000 Hz
sfrq: 125.6811107 MHz
direct nucleus: H1 / tn C13 metadata ambiguity retained
fid SHA-256: 4a4ccf9b8a8c20e4dd5d151564d84585fd13a15f53cc967cbaa77c556b29e145
```

The current SpectroChemPy NMR reader returns the same `(1500,) complex64`
values for this acquisition. The relative L2 difference after scalar fitting
was approximately `9.0e-8`, consistent with dtype-level comparison; norms
were identical. The plugin reports `QSIM`, time domain, `sw=50000 Hz`,
`sfrq=125.6811107 MHz`, and `ns_norm=1` for this dataset.

### Independent `var2pipe` comparison

NMRPipe 13.0 `var2pipe` was run with explicit axis flags because the supplied
Varian file does not provide a directly usable NMRPipe header:

```text
var2pipe -noaswap -ndim 1
  -xN 3000 -xT 1500 -xSW 50000
  -xOBS 125.6811107 -xCAR 99 -xMODE Complex -xFT Time
  -aq2D Complex
```

The resulting NMRPipe file has shape `(1500,)` `complex64`, matching SW, OBS,
carrier, quadrature and size fields. Its samples are exactly the complex
conjugate of nmrglue's raw result:

```text
var2pipe_data == conjugate(nmrglue_varian_read_data): True
relative L2 after conjugation: 0
```

This is a convention difference in the independent conversion, not a
decoding failure. No empirical conjugation was added to nmrglue-ng.

The `rfl` procpar value is `25000`, whereas the independently specified
NMRPipe recipe uses `xCAR=99 ppm`. This demonstrates that `rfl` cannot be
silently used as a normalized carrier. The future Agilent adapter must require
an explicit reference/carrier policy or emit a diagnostic/block export.

## ReadResult contract assessment

The current neutral contract can represent the Agilent raw 1D case without
Bruker-specific fields once a thin adapter supplies:

```text
domains = ("time",)
encoding = ("QSIM",)          # inferred from even np, with evidence retained
data = complex64 samples
axes[0] = time coordinate with dwell = 1 / sw
acquisition = spectral width, observation frequency, explicit carrier policy
metadata = complete procpar/file-header dictionaries
applied_corrections = explicit ns/ne normalization policy (or "none")
diagnostics = missing/ambiguous reference and trace-order conditions
```

No new hierarchy is required for 1D. The missing piece is not a Bruker-like
field; it is a normalized, constructor-independent reference/carrier policy
and an explicit trace-order/procpar provenance record.

The existing `write_readresult_nmrpipe()` exports such a manually normalized
Agilent ReadResult without a constructor branch. A synthetic normalized result
round-trips exactly after explicit complex64 storage and produces the same
NMRPipe quadrature/size/SW/OBS/CAR header fields as the explicit `var2pipe`
recipe. This proves writer genericity, not automatic Agilent parsing.

## 2D inventory and future order

The local historical corpus contains:

| Dataset | Shape | Observed encoding | Status |
|---|---:|---|---|
| `agilent_2d` | `(332,1500)` complex64 | States from `phase=[1,2]` | candidate; no matched processed oracle |
| `agilent_2d_tppi` | `(600,1400)` complex64 | TPPI from `phase=[3]` | candidate; historical plugin has a prior overflow/NaN issue and no independent processed oracle |
| `agilent_1d` | `(1500,)` complex64 | QSIM | first suitable transport case |

The Agilent 2D cases have unresolved historical corpus redistribution terms.
They must not be added to CI or redistributed. Their `torder`, phase-array
semantics and indirect quadrature require separate validation. Recommended
order is:

1. normalized Agilent raw 1D ReadResult and NMRPipe transport;
2. Agilent States 2D after an independent component/order contract;
3. Agilent TPPI 2D only after the existing non-finite/overflow issue and an
   independent oracle are dispositioned.

No 2D Agilent implementation is proposed by this audit.

## Risks and minimal next increment

The first implementation should add only an additive `read_agilent_fid()`
interop profile in nmrglue-ng, reusing `varian.read()` and preserving procpar
metadata. Acceptance should require:

- explicit shape and trace order;
- finite complex data and no implicit amplitude normalization;
- SW/OBS/dwell normalization;
- explicit carrier/reference input or a blocking diagnostic;
- provenance of `np`, `phase`, `ns`, `ne`, byte order and file header;
- exact comparison with the historical reader and the SpectroChemPy reader;
- independent `var2pipe` comparison with its conjugation convention recorded;
- synthetic self-contained tests and no external NMRPipe dependency in CI.

`NMRNG-kb5.8.1` should be reused rather than duplicated for observation/carrier
semantics. The Agilent profile should not expand to 2D in this increment.

## Conclusion

ReadResult and the existing NMRPipe exporter are sufficiently generic for a
normalized Agilent raw 1D result. They are not currently sufficient to claim
automatic Agilent parsing because carrier/reference semantics, normalization
policy and trace-order provenance are not normalized by nmrglue-ng. The
independent tool comparison establishes a deterministic conjugation
convention, not a reason to add an empirical correction.

No product code, SpectroChemPy reader, Beads task, release configuration or PR
was created by this audit. No roadmap change is warranted: the result is a
format-specific candidate under existing Varian axis/reference follow-up work.
