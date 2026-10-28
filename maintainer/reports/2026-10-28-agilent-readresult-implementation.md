# Agilent/Varian raw 1D ReadResult implementation

Date: 2026-10-28

## Scope

This increment adds the additive `ng.interop.read_agilent_fid()` profile. It
reuses `nmrglue.fileio.varian.read()` and does not change the historical
reader, processing algorithms, SpectroChemPy, or the NMRProcessingPlan.

The profile requires no SpectroChemPy, NMRPipe or quaternion dependency.

## Contract

The profile returns complex raw 1D data with:

- `domains=("time",)` and `encoding=("QSIM",)`;
- immutable complex samples and one named `complex` component;
- `TD`, `TDeff`, returned shape and direct-FID storage convention;
- SW, dwell, OBS, nucleus, NS and NE metadata;
- `dfrq` is retained as decoupler metadata but never used as an OBS fallback;
- the complete original Varian file/procpar dictionary in `metadata`;
- explicit `carrier_hz`/`carrier_ppm` only when supplied by the caller;
- a diagnostic when normalized SW, observation or carrier metadata is absent;
- no ns/ne normalization, conjugation, FFT or other processing.

`rfl`, `rfp`, `reffrq` and `tof` are preserved as original reference
candidates, but none is interpreted silently as the NMRPipe carrier.

When a source path is too long for NMRPipe's fixed comment field, the existing
writer now falls back to a compact provenance summary rather than truncating
the comment or rejecting an otherwise valid normalized result.

## Validation

Synthetic validation covers complex decoding, metadata, explicit/absent/
invalid carriers, procpar preservation, immutability, missing metadata and
structural NMRPipe compatibility.

Local historical Agilent `agilent_1d` validation:

- nmrglue reader and new ReadResult samples: exact parity;
- shape/dtype: `(1500,) complex64`;
- SW: `50000 Hz`;
- OBS: `125.6811107 MHz`;
- explicit conversion carrier: `99 ppm`;
- ReadResult-to-NMRPipe round-trip: exact after complex64 storage;
- `var2pipe -noaswap` comparison: exact conjugate relation;
- relative residual after conjugation: `0`;
- source `fid` SHA-256 unchanged:
  `4a4ccf9b8a8c20e4dd5d151564d84585fd13a15f53cc967cbaa77c556b29e145`.

The SpectroChemPy NMR reader produced the same raw 1D values, shape and dtype
on this acquisition. Its historical normalization policy is not applied by
the nmrglue-ng profile.

## Limitations and next step

- Carrier/reference semantics remain explicit caller responsibility.
- Agilent raw 2D, States and TPPI profiles are not implemented.
- The historical Agilent corpus remains local-only and is not added to CI or
  distribution.
- `NMRNG-kb5.8.1` remains the related OBS/CAR/ppm follow-up.
- `scpy-97j.5` remains open.
