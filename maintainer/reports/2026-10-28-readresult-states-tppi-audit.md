# Raw Bruker States-TPPI ReadResult profile

Date: 2026-10-28

## Scope

This increment extends `read_bruker_ser()` for the strict Bruker raw 2D
States-TPPI profile. It does not add quaternion dependencies, FFT processing,
TPPI alternation, phase correction, NMRPipe export, or changes to public
readers.

Baseline: `1ceab0d`, containing the merged raw 1D, QF 2D and QF NMRPipe
transport increments.

## Contract

For `FnMODE=5` and direct `AQ_mod=3`, `ReadResult.data` remains the decoded
stored trace matrix in `(F1-storage, F2)` order. The profile declares:

```text
encoding = ("STATES-TPPI", "DQD")
domains = ("time", "time")
trace_order = "F1-major, F2-contiguous"
```

Adjacent stored trace pairs are exposed as canonical named components without
changing `data`:

```text
RR[a] = real(trace[2a])
RI[a] = imag(trace[2a])
IR[a] = real(trace[2a+1])
II[a] = imag(trace[2a+1])
```

The result also records the pair rule, canonical shape, storage shape, TD,
TDeff when explicitly present, per-axis SW/OBS/carrier/dwell, provenance and
correction state. TPPI alternation is declared as `declared_not_applied`; no
sign alternation, conjugation, FFT or phase operation is performed.

Odd stored trace counts are rejected because adjacent States pairing is
undefined. QF `FnMODE=1` behavior and existing raw/processed 1D profiles are
preserved.

## Scientific validation

### Synthetic

The synthetic tests use four discriminating nonzero component arrays and
verify exact RR/RI/IR/II values, storage/canonical dimensions, immutability,
filter correction provenance, invalid FnMODE, and odd trace rejection.

### `topspin_2d/1`

The authorized local corpus was read without modification:

- `ser` SHA-256:
  `4da89ec781d2a1da254819d4d173fb53fdf2d89e1e9cff8fc749ab912a033015`;
- stored matrix: `(192, 1024)` `complex128`;
- canonical paired shape: `(96, 1024)`;
- all four components are finite and nonzero;
- encoding: `STATES-TPPI/DQD`;
- TD: `(147, 2048)`; TDeff absent and therefore reported as `None`;
- no corpus mutation occurred.

The independent SpectroChemPy NMR comparison used the same raw SER with its
historical `remove_digital_filter=False` path. It produced the same shape and
component mapping. The observed difference is the documented historical
representation policy: alternating imaginary component signs and a global
scale factor (`1 / 294400`), not a permutation or decoding mismatch. nmrglue-ng
preserves the decoded raw amplitude and does not apply RG/NS normalization.

## Validation

- Focused interop/compatibility tests: **69 passed**.
- Autonomous profile: **605 passed, 3 skipped, 142 deselected**; skips are
  pre-existing optional `csdmpy` skips.
- Ruff, format, `py_compile`, and `git diff --check`: passed.

NMRPipe, quaternion and SpectroChemPy are not CI/runtime dependencies. No
States-TPPI NMRPipe export is included.

## Limitations

- The profile does not apply TPPI alternation or perform Fourier processing.
- It does not provide quaternion arrays.
- It does not support pure States, pure TPPI or Echo-Antiecho.
- It does not add NMRPipe hypercomplex export.
- The Bruker storage padding versus vendor `TD` remains represented explicitly
  as storage/canonical shapes rather than inferred TDeff.
- Multi-constructor migration remains open; `scpy-97j.5` remains open.
