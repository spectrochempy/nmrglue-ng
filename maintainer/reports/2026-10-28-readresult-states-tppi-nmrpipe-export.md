# Raw States-TPPI ReadResult to NMRPipe export

Date: 2026-10-28

## Scope

This increment extends the experimental `ReadResult`-to-NMRPipe exporter to
strict Bruker raw States-TPPI storage. It does not add a binary writer,
quaternion dependency, FFT implementation, TPPI processing, or public-reader
changes.

Baseline: `cc73d1c`, containing merged PR #144 and the preceding 1D/QF
ReadResult and NMRPipe increments.

## Contract and headers

The exporter accepts only a two-axis result with:

```text
domains = ("time", "time")
encoding = ("STATES-TPPI", "DQD")
data = stored complex trace matrix, F1-major/F2-contiguous
components = RR, RI, IR, II matching adjacent stored trace pairs
```

The existing `pipe.create_dic()`/`pipe.write()` writer is reused. The
normalized universal dictionary sets:

| Convention | NMRPipe field |
|---|---|
| F1/F2 complex storage | `FDF1QUADFLAG=0`, `FDF2QUADFLAG=0` |
| States-TPPI indirect mode | `FDF1AQSIGN=16`, `FD2DPHASE=2` |
| pair count | `FDF1TDSIZE` |
| stored trace count | `FDSPECNUM` |
| direct size | `FDF2TDSIZE`, `FDSIZE` |
| per-axis SW/OBS/carrier | `FDF1*`/`FDF2*` fields |

The exporter validates all four canonical components against the stored data,
converts explicitly to complex64/float32, rejects non-finite or unrepresentable
values, and records compact bounded provenance. It does not apply TPPI
alternation, conjugation, FFT, phase correction or RG/NS normalization.

## Synthetic oracle validation

The existing deterministic States-TPPI oracle was loaded into a ReadResult and
exported. NMRPipe 13.0 was run with the established chain:

```text
ZF -zf 1 -auto | FT -nodf
TP
ZF -zf 1 -auto | FT -alt
```

The exported checkpoints matched the committed oracle exactly:

| Checkpoint | Shape | relative L2 | max absolute error |
|---|---:|---:|---:|
| input | `(64, 256)` | 0 | 0 |
| F2 | `(64, 512)` | 0 | 0 |
| TP | `(1024, 32)` | 0 | 0 |
| final | `(1024, 64)` | 0 | 0 |

The generated header contained `FDF1AQSIGN=16`, `FD2DPHASE=2`,
`FDF1TDSIZE=32` and `FDSPECNUM=64`.

## Independent Bruker transport validation

The local `topspin_2d/1/ser` was exported and independently converted with
NMRPipe 13.0 `bruk2pipe` using the documented storage profile:

```text
-AMX -aswap -skip -1 -ndim 2
-xMODE DQD -yMODE Complex -aq2D Complex
-xN 2048 -xT 1024 -yN 192 -yT 96
```

Both outputs read as `(192,1024)` complex64 with exact sample equality
(`relative L2=0`, maximum residual `0`). `bruk2pipe` reports the raw complex
storage convention (`FDF1TDSIZE=96`, `FDF1AQSIGN=0`); the nmrglue-ng export
adds the explicit States-TPPI semantics (`FDF1AQSIGN=16`, `FD2DPHASE=2`) while
preserving the same samples. This is a documented header-convention
difference, not an empirical data correction.

The SER checksum used for the local comparison is:

```text
4da89ec781307b5d137f3b4dcb2d6f14f0f994e1cac60ae3c89c9248277a66c6
```

No corpus file or generated binary was added to the repository.

## Validation and limitations

- Focused interop/compatibility tests: **88 passed** before final doc-only
  changes.
- Final focused export suite: **21 passed**.
- Autonomous profile: **610 passed, 3 skipped, 142 deselected**; skips are
  pre-existing optional `csdmpy` skips.
- Ruff, format, `py_compile`, and `git diff --check`: passed.

The profile does not support pure States, pure TPPI or Echo-Antiecho, does not
produce quaternion data, and does not apply TPPI processing. NMRPipe and
`bruk2pipe` remain manual validation tools and are not CI/runtime dependencies.
`scpy-97j.5` remains open.
