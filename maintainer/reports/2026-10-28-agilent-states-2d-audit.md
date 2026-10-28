# Agilent/Varian raw 2D States audit

Date: 2026-10-28

## Scope and baseline

This is a read-only scientific audit. No nmrglue-ng product code, reader,
writer, fixture, or workflow was modified.

Audited baseline: `dd68e63`, including the merged Agilent raw 1D profile #146.
The Agilent historical corpus remains local-only; no files are added to the
repository.

Existing task coordination was checked:

- `NMRNG-kb5.8.1` remains open for Varian OBS/CAR/ppm semantics;
- `scpy-89a` is closed for a separate Agilent TPPI FFT NaN/overflow defect;
- `scpy-97j.5` remains deferred/open for plugin ReadResult adaptation;
- no new task was created.

## Corpus and procpar

The local `agilent_2d` acquisition has:

```text
shape/dtype: (332, 1500) complex64
procpar np: 3000
procpar ni: 166
procpar phase: [1, 2]
direct sw: 50000 Hz
direct sfrq: 125.6906107 MHz
direct dn: H1 / tn: C13
indirect dfrq2: 50.6480504 MHz
fid SHA-256: 4a35f4b98f9116ba67760d1c0c83cc48a17b4e53897b5dbe1e25f85f28b1eac8
```

The historical reader returns finite complex64 data. Because `ntraces=1` for
this file, `torder=flat`, `torder=regular` and `torder=opposite` all return the
same `(332,1500)` matrix. The usual higher-dimensional Varian `torder`
heuristic therefore provides no independent ordering proof for this dataset.

The existing plugin classifies `phase=[1,2]` as States and converts the data
to a quaternion representation with shape `(332,750,4)`. This is a plugin
representation choice; it is not a raw nmrglue canonical component contract.

The separate `agilent_2d_tppi` dataset remains outside this audit. It is
classified as TPPI and is covered by the pre-existing Agilent TPPI defect
history in `scpy-89a`.

## Storage and component mapping

The Bruker-style hypothesis

```text
RR = real(data[0::2])
RI = imag(data[0::2])
IR = real(data[1::2])
II = imag(data[1::2])
```

was not accepted for Agilent States. Applying it to the raw matrix and
comparing component-wise with the plugin quaternion representation produced
large residuals (approximately 0.999 relative L2 after independent scalar
fits). The plugin quaternion shape also halves the direct axis, confirming
that its representation groups direct channels differently from the naive
adjacent-row interpretation.

No independent signal/impulse fixture was available to identify the Agilent
phase-cycle permutation, signs and conjugations. Therefore no RR/RI/IR/II
mapping is claimed. A future profile must preserve the raw matrix first and
carry the Agilent phase-array/trace-order evidence separately until this
mapping is established.

## Independent `var2pipe` experiment

NMRPipe 13.0 `var2pipe` was run with an explicit States profile:

```text
var2pipe -noaswap -ndim 2
  -xN 3000 -xT 1500 -xMODE Complex
  -yN 332 -yT 166 -yMODE States -aq2D States
```

The generated NMRPipe data has shape `(332,1500)` complex64 and headers:

```text
FDF1QUADFLAG=0, FDF2QUADFLAG=0
FDF1TDSIZE=166, FDF2TDSIZE=1500, FDSPECNUM=332
FDF1AQSIGN=0, FDF2AQSIGN=0
```

It is not sample-equal to the nmrglue matrix and is not a simple global
conjugation or sign change. This is evidence that `var2pipe` performs a
States-specific storage/recombination convention; it is not sufficient to
declare a decoding error in either reader. The exact axis carrier/reference
flags also require an explicit recipe; they must not be inferred from
`procpar` `rfl`/`reffrq` without a convention decision.

No FFT treatment comparison was started because temporal storage mapping is
not yet established.

## ReadResult assessment

The current ReadResult fields can carry the raw Agilent matrix and normalized
per-axis acquisition metadata, but a validated Agilent States profile would
need an explicit representation contract for:

- raw trace order and physical F1 increment order;
- phase-array interpretation and States pair grouping;
- component basis, signs and conjugations;
- storage shape versus physical/canonical shape;
- applied versus merely declared quadrature transformations.

No new object hierarchy is needed, but the profile must not reuse Bruker
adjacent-pair semantics by analogy. The raw matrix should remain the primary
data representation; named canonical components should be added only after
an independent mapping proof.

The generic NMRPipe writer is therefore not yet proven applicable to Agilent
2D States. The existing 1D adapter/export path is sufficient for normalized
Agilent 1D data, but a 2D export must wait for the representation contract.

## Compatibility and duplication risks

The plugin currently owns Agilent metadata extraction, quaternion adaptation
and processing validation. nmrglue-ng owns binary parsing and could own a
future raw ReadResult profile, but duplicating phase-cycle interpretation in
both repositories would create a circular scientific authority. The first
future increment should establish a small independent synthetic/impulse
mapping, then compare both readers component-wise before adding a public
Agilent 2D profile.

## Recommended next increment

1. Construct a deterministic Agilent-like raw matrix with separately
   controlled phase-cycle channels and documented procpar `phase` values.
2. Verify the binary trace layout and `var2pipe` States recipe with isolated
   impulses, recording permutations/signs/conjugations.
3. Compare the resulting components against the plugin quaternion adapter and
   NMRPipe storage checkpoints.
4. Define a vendor-neutral ReadResult representation only after this mapping
   is stable.
5. Add `read_agilent_ser()` or equivalent as a separate implementation task;
   keep TPPI and other 2D encodings separate.

No code, PR, fixture, release, or new task was created by this audit. No
roadmap change is warranted: Agilent 2D States remains blocked on a validated
storage/component mapping rather than on the 1D ReadResult contract.
