# Agilent States 2D quaternion-axis verdict

Date: 2026-10-29

## Verdict

**BUG CONFIRMED for the current Agilent reader use of `set_quaternion()`.**

The generic conversion groups the final/direct axis, while the documented
States branches are successive traces on the indirect acquisition axis.

## Independent documentary evidence

The supplied Varian/Agilent `VnmrJ User Programming` reference (publication
`01-999379-00`, Rev. A 0708, pp. 123–124 and 276–279) describes the
hypercomplex States acquisition, `phase=1,2` and `arraydim=ni*2`.

The VnmrJ Liquids guide gives the acquisition order explicitly: for each `d2`
evolution increment, the `phase=1` and `phase=2` experiments are acquired
successively; the phase array is traversed faster than the evolution-time
array. Thus States branches are paired along the indirect trace axis.

For `agilent_2d`:

```text
ni=166
phase=[1,2]
arraydim=332
np=3000 -> 1500 complex F2 points
varian.read() -> (332,1500) complex64
```

The nmrglue `find_shape()` implementation independently multiplies indirect
`ni` by `len(phase)`, and `ntraces=1` means no higher-dimensional `torder`
permutation occurs. The raw row order is therefore the physical States-pair
order for this acquisition.

## Reader mismatch

The current SpectroChemPy hypercomplex conversion uses:

```text
as_quaternion(data[:, ::2], data[:, 1::2])
```

This halves the direct axis from 1500 to 750 and leaves 332 indirect rows. It
does not pair the successive `phase=1`/`phase=2` traces. The numerical match
with the resulting q0..q3 arrays is not independent evidence: it is a direct
consequence of the code under test.

The physically motivated alternative is row pairing, retaining the full direct
axis:

```text
as_quaternion(data[0::2], data[1::2])
```

which would produce 166 F1 States pairs by 1500 F2 points. The exact canonical
component labels and signs still require a dedicated product correction and
review; this audit does not modify them.

## NMRPipe evidence

The independently established conversion operator remains:

```text
var2pipe[row, col] = (-1)**row * conjugate(input[row, col])
```

It acts on the successive States rows, reinforcing the F1 pair interpretation.

## Decision and next action

- The issue belongs to the SpectroChemPy Agilent reader/hypercomplex adapter,
  not to nmrglue-ng binary decoding.
- No nmrglue-ng or SpectroChemPy product code was changed in this audit.
- A separate SpectroChemPy corrective task/PR is required before relying on
  Agilent States quaternion processing.
- No Agilent 2D ReadResult canonical RR/RI/IR/II profile or NMRPipe export should
  be enabled until the correction is independently validated.
- Existing `scpy-89a`, `scpy-97j.5` and `NMRNG-kb5.8.1` scopes remain unchanged.
