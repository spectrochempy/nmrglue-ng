# NMRPipe 13 compatibility audit — 2026-09-30

## Purpose

This audit records a differential comparison of the 46 inherited
`pipe_proc` tests against NMRPipe 13.0. It is a historical snapshot and must
not be rewritten to reflect later results; a later campaign should create a
new dated audit.

## Baseline

- Audited branch: `master`
- Audited HEAD: `96b20f56b1c226590dcb44964a93b82edb1e17dd`
- NMRPipe: 13.0, revision 2026.072.12.03, 64-bit
- NMRPipe installation: `~/pipe`
- Environment: Linux, Python 3.13.13, NumPy 2.5.3, SciPy 1.18.1,
  pytest 9.1.1

Command:

```bash
csh -c 'source ~/pipe/com/nmrInit.linux239_64.com; python -m pytest tests/test_pipe_proc.py -v'
```

Result:

```text
41 passed
5 failed
```

The failures were `test_jmod`, `test_ht`, `test_tp`, `test_zd`, and
`test_save`.

## Summary

| Test | Result | Nature | Cause | Classification | Issue |
|---|---|---|---|---|---|
| JMOD | `jmod2` diverges | data and derived extrema | NMRPipe 13 applies a global `-i` phase in the sine/off=0 case | NMRPipe-version difference | none |
| HT | `ht6` diverges | data only | different `-auto` policy: zero fill in nmrglue, no zero fill in NMRPipe 13 | NMRPipe-version difference | none for HT6 |
| TP | `tp9` diverges | data only | the test encodes an older `-nohyper` behavior | historical-test difference | none |
| ZD | exception | execution | an integer width represented as float reaches `np.linspace(num=...)` | confirmed nmrglue bug | [#4](https://github.com/spectrochempy/nmrglue-ng/issues/4) |
| SAVE | header diverges | `FDPIPECOUNT` only | nmrglue explicitly writes 1 while NMRPipe 13 writes 0 | confirmed nmrglue metadata bug | [#6](https://github.com/spectrochempy/nmrglue-ng/issues/6) |

A separate dormant defect was confirmed for HT `ps90-180` and is tracked by
[#7](https://github.com/spectrochempy/nmrglue-ng/issues/7). It is not one of
the five current failures because the historical HT4 case was already
excluded.

## Comparison mechanics

`nmrglue.util.misc.pair_similar()` returns:

```text
r1 = data comparison
r2 = dictionary/header comparison
```

The data comparison requires identical dtypes and shapes before applying
`numpy.allclose()` with:

```text
atol = 0.1001
rtol = 0.1001
```

Numeric header values use an absolute tolerance of `0.5001`. The TP tests
ignore the display fields `FDMIN`, `FDMAX`, `FDDISPMIN`, `FDDISPMAX`, and
`FDSCALEFLAG`.

## JMOD

The cosine case `jmod1` agrees, with a maximum absolute error of approximately
`4.32e-5`.

For `jmod2`:

```text
shape                 (332, 1500), complex64
max(abs(delta))       630.78424
mean(abs(delta))      20.06132
RMS(delta)            26.00251
points differing      496331 / 498000
```

The essential relationship is:

```text
NMRPipe 13 result ≈ -i × nmrglue result
```

After compensating for this phase:

```text
max(abs(delta))       5.39e-6
RMS(delta)            3.88e-7
points outside tolerance = 0
```

NMRPipe 13 produces this rotation for both `-sin` and `-off 0.0`. It does not
produce it for `-cos` or `-off 0.25`. The observed `FDMAX`, `FDMIN`,
`FDDISPMAX`, and `FDDISPMIN` differences are consequences of the differently
phased data rather than independent header defects.

This behavior appears inconsistent with the consulted NMRPipe JMOD
documentation, which describes a real exponentially damped sinusoidal window
and identifies `-sin` with `-off 0.0`. No nmrglue correction is justified from
this comparison alone. The observed behavior is classified as an NMRPipe 13
behavior/version difference.

## HT

### HT6 auto mode

```text
shape                 (1500,), complex64
max(abs(delta))       66550.34375
mean(abs(delta))      883.15222
RMS(delta)            3483.82959
points differing      1258 / 1500
```

The real components are identical and the divergence is entirely in the
imaginary components. For this fixture:

```text
nmrglue auto    = ordinary HT with temporary zero fill
NMRPipe 13 auto = ordinary HT without temporary zero fill
```

The tested explicit ordinary modes agree. HT6 is therefore an auto-selection
policy difference, not evidence of an incorrect ordinary Hilbert transform.
No nmrglue bug is opened for HT6.

### Dormant HT4 / ps90-180 defect

The historical suite omitted case HT4 from its first committed form. The
corresponding `ps90-180` branch remains unimplemented as an explicit `pass`,
so nmrglue performs the ordinary transform instead of the documented
mirror-image Hilbert transform.

A reconstructed NMRPipe comparison found a maximum absolute difference of
`92843.02`, entirely in the imaginary component. This is a confirmed dormant
nmrglue defect, distinct from HT6, and is tracked by
[#7](https://github.com/spectrochempy/nmrglue-ng/issues/7).

## TP

The TP9 input is mixed-mode data:

```text
input shape       (332, 1500)
dtype             float32
FDF1QUADFLAG      0
FDF2QUADFLAG      1
```

The measured divergence is:

```text
max(abs(delta))       336.24402
mean(abs(delta))      29.41969
RMS(delta)            33.50438
points differing      248079 / 249000
```

With NMRPipe 13, default TP, `-auto`, and `-nohyper` are identical and produce
`(1500, 166)` complex64 data. NMRPipe interleaves adjacent real/imaginary rows.
The historical nmrglue `nohyper=True` path produces a different organization,
whereas `pipe_proc.tp(..., auto=True)` matches NMRPipe 13 exactly.

TP9 was introduced to test the earlier `-nohyper` semantics. Its current
failure is classified as a historical-test difference caused by NMRPipe
semantic evolution. No corrective nmrglue-ng issue is justified at this
stage.

Upstream issue [#223](https://github.com/jjhelmus/nmrglue/issues/223) is a
different problem: it concerns quadrature flags produced by Bruker conversion,
which can subsequently cause TP to select an inappropriate mode.

## ZD

The failure occurs before the NMRPipe comparison:

```text
wide=float -> np.linspace(num=float)
TypeError: 'float' object cannot be interpreted as an integer
```

Replacing only the integral float widths by their integer equivalents gave:

```text
ZD1 max error = 0
ZD2 max error = 1.53e-5
ZD3 max error = 4.77e-7
ZD4 max error = 2.70e-6
```

Upstream PR [#263](https://github.com/jjhelmus/nmrglue/pull/263) contains
`wide = int(wide)` for the affected window functions. This works for the
integral values used by the historical tests. The contract for a genuinely
fractional width remains to be specified; this audit does not make that
implementation decision. The defect is tracked by
[#4](https://github.com/spectrochempy/nmrglue-ng/issues/4).

## SAVE

The data agree exactly:

```text
data max(abs(delta)) = 0
```

The saved headers contain:

```text
nmrglue:
FDPIPEFLAG  = 0
FDPIPECOUNT = 1

NMRPipe 13:
FDPIPEFLAG  = 0
FDPIPECOUNT = 0
```

Several successive NMRPipe SAVE operations also retained
`FDPIPECOUNT=0`. The installed NMRPipe header documentation describes this
field as the function count for pipeline structure when `FDPIPEFLAG != 0`.
nmrglue does not appear to consume the field elsewhere.

The identified impact is therefore structural metadata compatibility, not
scientific data. The defect is tracked by
[#6](https://github.com/spectrochempy/nmrglue-ng/issues/6).

## Overall compatibility

```text
41/46 historical pipe_proc comparisons pass unchanged against NMRPipe 13.0

Current five failures:

confirmed nmrglue bugs:           2
NMRPipe-version/test differences: 3
still ambiguous:                  0

additional dormant nmrglue bug discovered: 1
HT ps90-180 (#7)
```

## Priorities

### P0 — #4 ZD

Define the `wide` contract explicitly for values such as `5`, `5.0`, and
`5.5`, then correct the confirmed compatibility failure. A genuinely
fractional value must not be truncated silently without an explicit decision.

### P1 — #6 SAVE

Correct the localized `FDPIPECOUNT` mismatch. The data already agree. This is
a good candidate for a generic upstream correction after validation in
nmrglue-ng.

### P1 — #7 HT ps90-180

Specify and implement the missing scientific behavior in a separate change,
validated against NMRPipe and with explicit endpoint tests.

## Upstream opportunities

- ZD: the correction is already present in upstream PR #263.
- SAVE: small generic fix and upstream candidate after nmrglue-ng validation.
- HT `ps90-180`: upstream candidate after scientific implementation and
  validation.
- JMOD, HT6, and TP9: no upstream correction is currently justified.

No upstream issue or pull request was created by this audit.
