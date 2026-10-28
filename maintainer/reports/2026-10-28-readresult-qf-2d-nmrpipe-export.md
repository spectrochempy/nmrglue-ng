# Raw QF 2D ReadResult to NMRPipe export

Date: 2026-10-28

## Scope and baseline

This report records the first QF 2D extension of the experimental
`ReadResult`-to-NMRPipe adapter. It does not add a binary writer, quaternion
conversion, processing algorithm, mandatory NMRPipe dependency, or a public
reader replacement.

Baseline: `61aa2b4` (`ENH: add raw Bruker QF 2D ReadResult profile (#142)`),
which includes the merged 1D export from #141 and the raw QF 2D reader from
#142.

## Export contract

`write_readresult_nmrpipe()` now accepts one additional, intentionally narrow
profile:

```text
domains = ("time", "time")
encoding = ("QF", "DQD")
data = complex 2D matrix, shape (F1, F2)
components = one named "complex" component
dimensions.axis_order = ("F1", "F2")
dimensions.trace_order = "F1-major, F2-contiguous"
```

The exporter requires per-axis normalized metadata:

| ReadResult metadata | NMRPipe field |
|---|---|
| F1/F2 data shape | `FDSPECNUM`, `FDSIZE`, `FDF1TDSIZE`, `FDF2TDSIZE` |
| `axes[i]` time coordinates | validated against `1 / SW_hz` |
| `SW_hz` | `FDF1SW`, `FDF2SW` |
| `observation_frequency_mhz` | `FDF1OBS`, `FDF2OBS` |
| `carrier_hz` | `FDF1CAR`, `FDF2CAR` in ppm through `create_dic()` |
| QF/DQD encoding | `FDF1QUADFLAG=1`, `FDF2QUADFLAG=0` |

The existing `pipe.create_dic()` and `pipe.write()` functions remain the only
binary writer. Complex data are explicitly converted to `complex64`; NMRPipe
stores the real and imaginary portions as float32. Non-finite and out-of-range
values are rejected. No RG/NS normalization, filter correction, FFT, TP, MC,
apodization, phasing or linear prediction is applied by export.

Physical/storage/returned dimensions remain distinguishable in ReadResult.
The bounded NMRPipe comment records source basename, applied correction flags,
returned shape and float32 storage. Full vendor metadata remains in the source
ReadResult; a future external manifest remains possible and is not required by
this API.

Unsupported States, States-TPPI, Echo-Antiecho, quaternion and incomplete
profiles are rejected explicitly.

## Synthetic transport and processing oracle

The existing deterministic QF oracle from the standalone SpectroChemPy NMR
campaign was loaded into a synthetic QF ReadResult and exported. NMRPipe 13.0
was run with the documented pipeline:

```text
ZF -zf 1 -auto | FT -nodf
TP
ZF -zf 1 -auto | FT -neg
MC | TP
```

The exported input and every checkpoint matched the committed oracle exactly:

| Checkpoint | Shape | dtype | relative L2 | max absolute error |
|---|---:|---|---:|---:|
| input | `(33, 257)` | complex64 | 0 | 0 |
| F2 | `(33, 1024)` | complex64 | 0 | 0 |
| TP | `(1024, 33)` | complex64 | 0 | 0 |
| F1 | `(1024, 128)` | complex64 | 0 | 0 |
| magnitude | `(128, 1024)` | float32 | 0 | 0 |

This validates transport and the NMRPipe processing conventions independently
of the Bruker reader. The fixture is synthetic and already governed by its
existing manifest/SHA-256; no generated binary output was added here.

## `exam2d_HH` transport and `bruk2pipe`

The authorized local Bruker corpus was read without modification. The
ReadResult has shape `(128, 1024)` and dtype `complex128`. It was exported to
NMRPipe in a temporary directory. `bruk2pipe` 13.0 was run on the same `ser`
with the explicit `-aswap` convention and `-skip -1` so no digital-filter
correction was silently introduced:

```text
bruk2pipe -AMX -aswap -skip -1 -ndim 2
  -xN 2048 -xT 1024 -xMODE DQD
  -yN 128 -yT 128 -yMODE Real -aq2D Magnitude
```

Results:

- both files read as `(128, 1024)` complex64;
- `FDF1QUADFLAG=1`, `FDF2QUADFLAG=0` in both headers;
- `FDF1TDSIZE=128`, `FDF2TDSIZE=1024`, `FDSPECNUM=128`, `FDSIZE=1024`;
- sample equality after float32 storage: exact;
- relative L2 difference: `0`;
- maximum absolute difference: `0`;
- SW/OBS/CAR fields differ only by float32 header rounding;
- corpus `ser` SHA-256 remains
  `641707c170f8352785ee3bc923c52f85a335984c38e0ace7c591c054d32ccc6b`.

The first attempted `-noaswap` comparison was deliberately rejected as a
convention mismatch: it produced a nonzero transport residual. The explicit
`-aswap` result is the validated independent comparison and is documented
rather than hidden by a correction.

## Processing validation on the experimental corpus

The same exported `exam2d_HH` file was processed with NMRPipe 13.0 using the
four-step pipeline above. All checkpoints were finite and retained the
expected QF header transitions:

```text
input       (128, 1024) complex64
F2          (128, 2048) complex64
TP          (2048, 128) complex64
F1          (2048, 256) complex64
magnitude   (256, 2048) float32
```

No comparison to the processed TopSpin `2rr` is claimed here: that reference
contains F1 linear prediction and is outside this first transport increment.
The synthetic oracle is the authoritative treatment comparison for this
change.

## Tests and limitations

Self-contained tests cover QF 2D round-trip, header flags and dimensions,
trace-order metadata, per-axis axes and acquisition metadata, immutability,
float32 preservation, missing metadata and unsupported encodings.

Final local validation:

- focused interop/export suite: **79 passed**;
- autonomous profile: **599 passed, 3 skipped, 142 deselected**; the skips are
  pre-existing optional `csdmpy` skips;
- Ruff, format, `py_compile`, and `git diff --check`: passed.

The focused interop suite passed after the extension, and the standard
autonomous suite remains the CI profile. NMRPipe and `bruk2pipe` are manual
validation tools only; they are not required by runtime or CI.

This increment does not support raw 2D States, States-TPPI or Echo-Antiecho,
hypercomplex components, quaternion conversion, NMRPipe 2D import, or vendor
processing replay. `scpy-97j.5` remains open.
