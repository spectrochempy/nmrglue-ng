# ReadResult raw 1D NMRPipe export audit

Date: 2026-10-28

## Scope

This audit evaluates the first controlled export path from a raw 1D
`ReadResult` to NMRPipe. It is limited to one time-domain axis and does not
replace historical readers, implement a binary writer, or add NMRPipe as a
runtime or CI dependency.

Audited baseline: `fe98f14` (`ENH: add raw Bruker ReadResult profile (#140)`).

## Existing capabilities

The existing `nmrglue.fileio.pipe` implementation provides the reusable
writer. `pipe.create_dic()` accepts the repository's universal dictionary and
sets the direct-axis fields; `pipe.write()` writes the existing NMRPipe binary
format. Complex data are stored as concatenated real and imaginary float32
vectors, and are reconstructed by `pipe.read()`.

The existing Bruker converter uses the same universal-dictionary path, but it
starts from vendor dictionaries. The new adapter deliberately starts from
normalized `ReadResult.acquisition` fields instead.

## Prototype contract

`nmrglue.interop.write_readresult_nmrpipe(result, filename, overwrite=False)`
accepts only a 1D time-domain result with:

| ReadResult field | NMRPipe field/convention |
| --- | --- |
| `data.size` | `FDF2TDSIZE`, `FDSIZE`, `FDREALSIZE` through `create_dic()` |
| complex/real dtype | `FDF2QUADFLAG=0/1` |
| `acquisition["spectral_width_hz"]` | `FDF2SW` |
| `acquisition["observation_frequency_mhz"]` | `FDF2OBS` |
| `acquisition["carrier_hz"]` | `FDF2CAR` in ppm via the existing universal convention |
| time axis in seconds | validated against `1 / spectral_width_hz` |
| `source`, `applied_corrections` | bounded `FDSRCNAME`, `FDTITLE`, `FDCOMMENT` provenance |

No `RG`, `NS`, or normalization operation is read or applied during export.
The input result is not mutated. The NMRPipe format stores float32 samples, so
complex input is explicitly converted to `complex64` and real input to
`float32`; tests compare against those explicit representations.

Profiles currently supported:

- `AQ_mod=1` / `QSIM` complex direct data;
- `AQ_mod=0` / `QF` real direct data.

Raw 2D, hypercomplex data, processed data export, phase/sign correction and
NMRPipe processing orchestration are intentionally out of scope.

## Validation

Self-contained validation:

- `tests/interop/test_interop_nmrpipe.py` plus Bruker interop and pipe tests:
  **108 passed**;
- standard autonomous profile:
  **583 passed, 3 skipped, 142 deselected**;
- Ruff, format check, `py_compile`, and `git diff --check`: passed.

Independent NMRPipe 13.0 validation used temporary synthetic files only; no
experimental corpus was added:

- `bruk2pipe` complex input with eight deterministic complex points: exact
  sample equality, `FDF2QUADFLAG=0`, `FDF2TDSIZE=8`;
- `bruk2pipe` real input with eight deterministic real points: exact sample
  equality, `FDF2QUADFLAG=1`, `FDF2TDSIZE=8`;
- `nmrPipe -fn FT` on the exported complex signal compared with
  `nmrglue.proc_base.fft_positive`: relative L2 error `3.26e-8`, maximum
  absolute error `2.38e-7`, attributable to float32 storage.

The external commands used NMRPipe 13.0 Rev 2026.072.12.03. They are an
independent validation record, not a CI requirement.

The broader external-software test profile also had three pre-existing
processing-comparison failures (`jmod`, `ht`, and `tp`). They are unrelated to
this export adapter and are not attributed to this change.

## Limitations and next gates

NMRPipe's fixed header has bounded provenance fields; the prototype rejects a
provenance comment that cannot fit rather than truncating it silently. The
prototype has no sidecar manifest, no `bruk2pipe` subprocess integration, and
does not claim that every vendor raw profile is representable. A real raw
Bruker corpus remains a separate local-validation and provenance gate.

Before delivery beyond an experimental API, review should decide whether the
bounded header provenance is sufficient or whether an explicit export receipt
or manifest contract is required. No roadmap change is warranted by this
audit: raw 2D/hypercomplex and multi-constructor migration gates remain open.
