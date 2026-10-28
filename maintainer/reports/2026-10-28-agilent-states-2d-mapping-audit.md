# Agilent/Varian raw 2D States mapping audit

Date: 2026-10-28

## Scope

This audit characterizes storage and quadrature conventions only. No product
reader, ReadResult profile, NMRPipe writer, SpectroChemPy reader, fixture or
workflow was modified.

Baseline: nmrglue-ng `dd68e63`, after merged Agilent raw 1D support (#146).

Related existing tasks were reused: `NMRNG-kb5.8.1` for Varian OBS/CAR/ppm,
`scpy-89a` for the separate Agilent TPPI numerical defect, and `scpy-97j.5`
for the deferred plugin adapter. No new task was created.

## Stored data and procpar

The local historical `agilent_2d` dataset reports:

```text
data shape/dtype: (332, 1500) complex64
np: 3000
ni: 166
phase: [1, 2]
direct sw/sfrq: 50000 Hz / 125.6906107 MHz
indirect dfrq2: 50.6480504 MHz
fid SHA-256: 4a35f4b98f9116ba67760d1c0c83cc48a17b4e53897b5dbe1e25f85f28b1eac8
```

The historical `varian.read()` path decodes interleaved direct real/imaginary
words to complex64 and reshapes the data to `(332,1500)`. Since the file has
`ntraces=1`, `flat`, `regular` and `opposite` torders are observationally
indistinguishable on this dataset. This is not evidence that the conventions
are equivalent in general.

The `phase=[1,2]` procpar values are classified by the SpectroChemPy reader as
States. The separate `agilent_2d_tppi` candidate (`(600,1400)`, `phase=[3]`)
remains outside this audit.

## Synthetic binary campaign

A temporary Varian dataset was generated with the existing `varian.write()`
function, a controlled procpar (`np=12`, `ni=2`, `phase=[0,1]`) and a `(4,6)`
complex matrix. All 24 single-position complex impulse cases round-tripped
exactly through `varian.write()` → `varian.read()`.

This establishes binary storage and interleaving behavior for the controlled
file. The same basis impulses were converted with `var2pipe -yMODE States`.
For every real and imaginary basis vector, the exact output operator was:

```text
var2pipe_output[row, col] = (-1)**row * conjugate(nmrglue_input[row, col])
```

The operator was also verified on the independent `agilent_2d` signal with
zero residual. This is a conversion convention, not an empirical correction.

## Component mapping result

The Bruker-like hypothesis:

```text
RR = real(data[0::2])
RI = imag(data[0::2])
IR = real(data[1::2])
II = imag(data[1::2])
```

does not reproduce the SpectroChemPy quaternion representation for
`agilent_2d`. Component-wise residuals remain approximately `0.999` after
independent scalar fits. The plugin representation has shape `(332,750,4)`,
which groups the direct dimension differently from the naive adjacent-row
projection.

The Bruker-style row-pair mapping is rejected. The SpectroChemPy quaternion
representation is instead reproduced by direct-axis grouping:

```text
q0 = real(data[:, 0::2])
q1 = imag(data[:, 0::2])
q2 = real(data[:, 1::2])
q3 = imag(data[:, 1::2])
```

Each component matched the plugin representation with relative residual below
`2e-7` after independent scalar fitting. This establishes the plugin's q0/q1/
q2/q3 grouping, but does not authorize assigning the labels RR/RI/IR/II.

## Independent NMRPipe conversion

NMRPipe 13.0 `var2pipe` was run on the same Agilent 2D FID with an explicit
States profile:

```text
var2pipe -noaswap -ndim 2
  -xN 3000 -xT 1500 -xMODE Complex
  -yN 332 -yT 166 -yMODE States -aq2D States
```

The output has shape `(332,1500)` complex64 and headers:

```text
FDF1QUADFLAG=0, FDF2QUADFLAG=0
FDF1TDSIZE=166, FDF2TDSIZE=1500, FDSPECNUM=332
FDF1AQSIGN=0, FDF2AQSIGN=0
```

It is not sample-equal to nmrglue data, but the deterministic alternating
conjugation operator above reproduces it exactly. This demonstrates an
additional States storage/recombination operation in `var2pipe`; it does not
identify a decoding error in either representation.
The command is reproducible but not yet a scientific acceptance oracle because
the carrier/reference and phase-cycle mapping are not independently fixed.

No FFT processing was run. The temporal conversion operator and direct-axis
plugin grouping are established, while a canonical RR/RI/IR/II naming and F1
processing contract remain open.

## SpectroChemPy comparison

SpectroChemPy reads the same raw file as a finite quaternion dataset with shape
`(332,750,4)` and encoding `QSIM/STATES`. The raw values have the same source
shape but the component projection differs from the adjacent-row hypothesis.
The plugin's prior TPPI defect (`scpy-89a`) is not evidence for or against this
States mapping.

The difference must be separated into:

- raw binary decoding, which is validated by the synthetic round-trip;
- phase-cycle/quadrature reconstruction, which remains unresolved;
- later FFT conventions, not tested here;
- normalization, which is not used as a mapping criterion.

## ReadResult and export consequences

The existing ReadResult fields can carry the raw Agilent matrix, procpar,
dimensions, encoding and axes once OBS/carrier/reference semantics are
normalized. A future Agilent States profile should keep that matrix as primary
data and expose phase-array, trace-order and reconstruction metadata.

It must not fabricate RR/RI/IR/II until the mapping is established. The
generic NMRPipe writer is not yet validated for Agilent 2D States; adding a
writer branch now would hide the unresolved transformation.

## Recommended next increment

1. Generate a true phase-cycle-discriminating Agilent fixture or documented
   simulator output with independent States branches.
2. Freeze the plugin q0/q1/q2/q3 grouping and decide whether/how canonical
   RR/RI/IR/II labels apply to Agilent.
3. Compare the established operator against an independent signal, not just
   the original dataset.
4. Freeze the metadata contract before adding `read_agilent_ser()`.
5. Only then define NMRPipe export and FFT checkpoints.

No product implementation, PR, new task, fixture, publication or release was
created by this audit. No roadmap change is warranted; Agilent 2D States is
blocked on a validated storage/quadrature mapping.
