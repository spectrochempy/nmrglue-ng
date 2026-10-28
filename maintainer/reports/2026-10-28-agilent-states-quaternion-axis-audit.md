# Agilent States 2D: quaternion-axis representation audit

Date: 2026-10-28

## Verdict

**La convention d’acquisition est justifiée; la conversion quaternion Agilent
actuelle est scientifiquement suspecte et utilise probablement le mauvais axe.**

The current SpectroChemPy `set_quaternion()` result is numerically reproducible
from the nmrglue matrix, but that correspondence is not an independent proof
of physical quadrature meaning. The raw dimensions and procpar phase layout
indicate that the States phase branches expand the indirect trace axis, while
`set_quaternion()` groups the final direct axis.

## Dimension evidence

For the local `agilent_2d` acquisition:

```text
procpar np = 3000       -> 1500 complex direct F2 points
procpar ni = 166        -> phase=[1,2] expands to 332 stored F1 traces
varian.read()           -> (332,1500) complex64
SpectroChemPy quaternion -> (332,750,4)
```

The nmrglue `find_shape()` implementation explicitly multiplies an indirect
`ni` by `len(phase)`, so the States expansion is represented on the leading
trace axis. For 2D data `ntraces=1`, and `flat`, `regular` and `opposite`
orders are observationally indistinguishable in this corpus.

The hypercomplex plugin's `set_quaternion()` implementation converts a 2D
complex array with:

```text
as_quaternion(data[:, ::2], data[:, 1::2])
```

It therefore halves the final/direct axis and creates four float components
from adjacent direct complex samples. It does not pair `data[0::2]` and
`data[1::2]` on the indirect States axis.

The official Varian/Agilent VnmrJ documentation supplied for this audit
(`VnmrJ User Programming`, publication `01-999379-00`, Rev. A 0708,
pp. 123–124 and 276–279) states that `phase=1,2` produces two hypercomplex
experiments. The companion VnmrJ Liquids guide explicitly states that the
phase array is traversed faster than the evolution-time (`d2`) array, so each
`d2` increment has successive phase-1 and phase-2 experiments. This agrees
with `arraydim=332`, `ni=166` and `phase=[1,2]` in the real procpar.

The nmrglue `find_shape()` implementation independently applies
`len(phase)` to indirect `ni`, and `ntraces=1` means no higher-dimensional
`torder` permutation occurs. The raw row order is therefore the physical
States-pair order for this 2D acquisition.

## What is established

- Binary Varian decoding and shape `(332,1500)` are validated by the existing
  reader and synthetic binary impulse round-trips.
- `phase=[1,2]` is the documented/plugin classification for an indirect States
  acquisition in this dataset.
- The plugin q0..q3 arrays are numerically reproducible from direct-axis
  adjacent samples with residuals below `2e-7` after scalar fitting.
- The independent `var2pipe -yMODE States -aq2D States` conversion follows the
  exact raw-storage operator `(-1)**row * conjugate(input[row])`, established by
  basis impulses and confirmed on the experimental signal.

## What is not established

The q0..q3 numerical match is not independent of the plugin implementation.
It does not prove that direct-axis grouping is the physical Agilent States
quadrature, nor that q0/q1/q2/q3 may be renamed RR/RI/IR/II. The available
corpus has no independent processed component oracle or pulse-cycle-labelled
component file that resolves this distinction.

The alternative hypothesis—pairing States branches on the leading trace axis
and retaining the full direct complex axis—is the convention supported by the
VnmrJ phase-array documentation. The `var2pipe` row-wise conjugation/sign
operator independently acts on that trace axis. The remaining ambiguity is
the canonical naming of the resulting branches, not which raw axis carries
the two phase acquisitions.

## Scientific basis and next experiment

Agilent/VNMR documentation describes `phase` values as phase selection used to
provide indirect-dimension quadrature and explicitly identifies `phase=1,2`
as the two hypercomplex experiments. It does not specify the downstream
component ordering in a third-party quaternion container.

The next decisive experiment requires a phase-cycle-labelled synthetic or
vendor-compatible acquisition with:

1. isolated impulses in each indirect States branch;
2. independent real/imaginary direct samples;
3. a known pulse/receiver phase table;
4. the same binary header/procpar fields;
5. comparison of both candidate assemblies before any FFT.

The experiment must determine whether the canonical representation is
row-paired, column-paired, or a fixed linear combination of both. It must be
repeated on a second signal before productizing the result.

## Decision impact

- A descriptive raw ReadResult preserving the original `(332,1500)` matrix,
  procpar and `phase=[1,2]` remains appropriate.
- q0..q3 may be retained as a plugin-specific documented view, not as a
  universal nmrglue-ng component contract.
- No RR/RI/IR/II components should be fabricated.
- No Agilent 2D NMRPipe export or quaternion conversion should be enabled.
- No SpectroChemPy reader or algorithm should be changed from this audit.

No code, fixture, task, PR, publication or release was created. Existing
`NMRNG-kb5.8.1`, `scpy-97j.5` and `scpy-89a` scopes remain unchanged.
