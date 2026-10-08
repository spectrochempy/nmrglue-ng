# NMRPipe `pipe_proc.ext` indirect extraction

Audit and implementation date: 2026-10-08. Implementation baseline:
`nmrglue-ng` `master` `1e3e29c`; the results below identify the subsequent
uncommitted working-tree change. The initial sections record implementer
self-validation. Three review rounds dated 2026-10-08 are recorded below.
The third round approves the current nine-case correction: **Ready to merge**.
It closes the earlier clipping, fixture and rounding findings. Earlier review
evidence remains historical; inherited calibration/quadrature limits are not
claimed as fixed.

## Scope and attribution

This report covers only the 2D indirect-dimension metadata and out-of-range
upper-bound defects in `nmrglue.process.pipe_proc.ext`. The correction adapts
two upstream commits by reneeotten, merged as
[jjhelmus/nmrglue#289](https://github.com/jjhelmus/nmrglue/pull/289):
`7851bef` (stale indirect size metadata; closes #276) and `b72a959` (correct
the upper-bound assignment after review).

The changes are independent symptoms: one compares a post-slice shape where
the original indirect size is required; the other assigns the upper clamp to
the lower bound. They remain one focused fix because both are in the same
`EXT` indirect extraction path and have one shared regression matrix. If
separate history is wanted, they can be split into two commits without changing
the code or tests.

## Reproduction before the correction

The following in-memory command was run on `1e3e29c` before editing, with a
monotonic `float32` array shaped `(512, 1024)`, a 2D NMRPipe dictionary whose
`FDSPECNUM` and `FDSLICECOUNT` were both set to 512, and frequency-domain F1:

```console
python -c "... ng.pipe_proc.ext(dic.copy(), data.copy(), **kwargs) ..."
```

| Arguments | Observed data | Observed metadata / error |
|---|---|---|
| `y1=2, yn=512` | `(511, 1024)`, rows 2 through 512 | `FDSPECNUM=512`, `FDSLICECOUNT=512` |
| `y1=1, yn=128` | `(128, 1024)`, rows 1 through 128 | `FDSPECNUM=512`, `FDSLICECOUNT=512` |
| `y1=400, yn=700` | none | empty crop then `ZeroDivisionError: float division by zero` in `recalc_orig` |

## Convention and expected results

The NMRPipe [EXT reference](https://spin.niddk.nih.gov/NMRPipe/ref/nmrpipe/ext.html)
defines `-y1` and `-yn` as the first and last included vectors, respectively.
It states that `-sw` updates the number of points and the calibration values
`NDSW`, `NDCENTER`, `NDORIG`, `NDX1`, `NDXN`, and `NDAPOD` as applicable. This
is independent of the upstream patch and establishes why a sliced indirect
dimension must have matching structural header counts and recalculated F1
coordinates.

The new autonomous test uses a numbered `(512, 1024)` array. It verifies the
exact extracted rows, shape, `FDSPECNUM`, `FDSLICECOUNT`, F1 `APOD`, `CENTER`,
`SW`, `ORIG`, and, where the existing path updates them, F1 `X1`/`XN`. It then
writes and reads an NMRPipe file in `tmp_path`; the read shape, `FDSPECNUM`, and
values must agree with the extraction. The out-of-range request is intentionally
clipped to rows 400 through 512, as NMRPipe 13.0 does; it returns 113 vectors
rather than translating the requested window.

## Initial implementation validation (historical)

Run by the current author after the correction, with the system Python 3.13.13
and pytest 9.1.1:

```console
python -m pytest tests/test_pipe_proc_unit.py::test_ext_updates_indirect_metadata_and_axis -v --strict-markers --strict-config -ra
```

Result: 3 passed, 0 skipped, exit 0. This is a self-contained test and writes
only beneath pytest's temporary directory. The external NMRPipe executable
comparison was not run; the documented NMRPipe reference is the convention
source. The focused unit-file validation also passed:

```console
python -m pytest tests/test_pipe_proc_unit.py -v --strict-markers --strict-config -ra
```

Result: 42 passed, 0 skipped, exit 0. The standard autonomous profile was not
run because this focused processing regression and its unit-file context are
the smallest sufficient validation scope.

## Out-of-scope behavior

`EXT -y1 1 -yn 128 -sw` has pre-existing F1 `XN` and `APOD` update conditions
that compare `y_max` with the post-slice row count; they therefore retain their
old values for this particular first-row crop. The same conditions predate this
fix, are separate from the structural-count and empty-crop defects, and are
not modified or asserted as corrected here. Likewise, `pipe.write()` currently
requires a string rather than a `pathlib.Path`; the regression passes `str()`
and does not expand scope to that writer API behavior.

## Review and upstream status

At implementation time the targeted regression was only self-validated.
The first two reviews requested changes. The third review below independently
approves the current correction within its stated scope, including the
rounding follow-up and direct executable comparisons.
The original source adaptation is generic and based on the two merged upstream
commits. The clipping follow-up goes beyond those commits; it must not be
described as already merged upstream in its current form. No upstream message,
issue, PR, branch, or commit was created; the contribution pause remains a
maintainer decision.

## Response to independent review

The independent review identified two unsafe consequences of the original
upper-bound assignment repair: clipping only the upper bound could leave a
negative lower slice index, and preserving the requested width by translating
the window contradicted NMRPipe. The implementation now clips each Y bound
independently to the data domain. This keeps `y1=1, yn=700` at 512 rows with
counts 512, and makes `y1=400, yn=700` return rows 400 through 512 with counts
113. The latter was checked after this follow-up against NMRPipe 13.0 Rev
2026.072.12.03: both returned `(113, 1024)` with identical values and both
count fields equal to 113.

The synthetic frequency-domain F1 fixture now sets `FDF1ORIG=-500.0` together
with `CENTER=256`, `SW=1000`, and `CAR * OBS=0`, making its 512-point frequency
grid coherent. The five regression cases include the previously unsafe 1–700
request and assert its returned shape/counts and successful NMRPipe round trip.
The fifth case verifies NMRPipe's positive out-of-range lower-bound convention:
600–700 resolves to the final row, rather than creating an empty slice.
The inherited first-row `X1`/`XN`/`APOD`, mixed-quadrature, TPPI, and higher-
dimensional limitations remain outside this targeted change. At the time of
this response another review was pending; the second review below records its
outcome. After this response, the targeted
five-case regression passed 5 tests and the focused unit file passed 44 tests,
both with 0 skips and exit 0.

## Independent review prompt

```text
Troisième revue indépendante — arbre de travail sur master, sans commit
Besoin : vérifier la réponse au blocage `round`/`pow2` dans `pipe_proc.ext` 2D.
Les coordonnées demandées doivent être rognées avant l'expansion; la fenêtre
agrandie doit ensuite conserver sa taille dans le domaine. Base : `1e3e29c`;
examiner `git diff 1e3e29c` et l'arbre de travail courant.
Points sensibles : (1) comparer à NMRPipe les quatre cas 1–128/round=256,
1–100/pow2, 400–500/round=128 et 400–700/pow2 ; (2) confirmer saturation
correcte quand l'expansion excède toute la dimension ; (3) vérifier valeurs,
forme, comptes et calibration avec la fixture F1 cohérente ; (4) confirmer que
les cinq cas de clipping et les limitations X1/XN/APOD, quadrature mixte, TPPI
et 3D gardent leurs statuts respectifs ; (5) vérifier l'attribution #289.
```

## First independent review — 2026-10-08 (historical)

**Verdict: Changes requested.** Target: the uncommitted source/test diff over
`1e3e29cea1a1b2f2bb31fb097e0872647af2089d`, on `master`. This review was
performed in a fresh session, without implementing the correction. No source,
assertion, canonical corpus, or release gate was changed during the review.

### Evidence and reproduction

The original three parametrized tests were executed against the baseline by
loading `git show 1e3e29c:nmrglue/process/pipe_proc.py` into a separate namespace
and replacing `ng.pipe_proc.ext` **only in the test process**. Result: **3 failed,
0 skipped**, exit 1: stale `FDSPECNUM` (512 instead of 511 and 128), then
`ZeroDivisionError` for 400–700. Against the working tree:

```console
python -m pytest tests/test_pipe_proc_unit.py -v --strict-markers --strict-config -ra
```

**42 passed, 0 skipped**, exit 0, including the three added cases and their
temporary-file round trips. The review invocation additionally disabled pytest's
cache and set a task-owned `--basetemp`. Environment: Linux, Python 3.13.13,
NumPy 2.5.3, pytest 9.1.1. The complete autonomous suite, dataset suite, and
existing external-software suite were not run; this is focused validation.

`command -v nmrPipe` resolved the executable under `~/pipe/nmrbin.linux239_64`,
already on `PATH`; lowercase `nmrpipe` did not resolve. `nmrPipe -help` identified
**13.0 Rev 2026.072.12.03 64-bit**. `/bin/csh` was available. The comparisons
below actually invoked this executable, rather than merely reading back files
written by nmrglue. All input arrays were synthetic; no corpus data was used.

This self-contained reproducer reconstructs the exact new test header and the
key external comparisons. Outputs are disposable and removed on exit:

```python
import copy
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import nmrglue as ng

data = np.arange(512 * 1024, dtype="float32").reshape(512, 1024)
udic = ng.fileiobase.create_blank_udic(2)
udic[0].update(size=512, complex=False, sw=1000., obs=1., car=0.)
udic[1].update(size=1024, complex=False)
dic = ng.pipe.create_dic(udic)
dic["FDSPECNUM"] = dic["FDSLICECOUNT"] = 512.
dic["FDF1FTFLAG"] = dic["FDF2FTFLAG"] = 1.
dic["FDF1APOD"] = 512.
dic["FDF1CENTER"] = 256.
keys = ["FDSPECNUM", "FDSLICECOUNT", "FDF1X1", "FDF1XN",
        "FDF1APOD", "FDF1CENTER", "FDF1SW", "FDF1ORIG"]
with tempfile.TemporaryDirectory() as directory:
    src, dst = [Path(directory) / name for name in ("in.ft2", "out.ft2")]
    ng.pipe.write(str(src), dic, data)
    for first, last in [(2, 512), (1, 128), (400, 700), (1, 700)]:
        actual, values = ng.pipe_proc.ext(copy.deepcopy(dic), data.copy(),
                                         y1=first, yn=last)
        subprocess.run(["nmrPipe", "-in", str(src), "-fn", "EXT",
                        "-y1", str(first), "-yn", str(last), "-sw",
                        "-out", str(dst), "-ov"], check=True)
        reference, expected = ng.pipe.read(str(dst))
        print(first, last, values.shape, expected.shape,
              np.array_equal(values, expected))
        print({k: (actual[k], reference[k]) for k in keys})
```

### Findings introduced by this change

1. **High — newly successful oversized extraction returns inconsistent data
   and counts** (`pipe_proc.py:2048–2058`). With 512 rows, `y1=1, yn=700`
   now computes `y_min=-188`, slices `data[-188:512]` (rows 325–512), and
   returns shape `(188, 1024)` with **both counts 700**, `X1=-187`, and
   `CENTER=444`. `pipe.find_shape` predicts `(700, 1024)`; write/read returns a
   flat `(192512,)` array with a reshape warning. Baseline raised
   `ZeroDivisionError`; the new silent, apparently successful corrupt output
   is an introduced failure mode, even though the inadequate bound algorithm
   was latent in the old code and has an X-axis analogue. `y1=1, yn=512,
   round=1024` likewise returns 512 rows with counts 1024. This belongs to the
   requested upper-bound correction, not a separate axis-calibration redesign.
   A follow-up must bound or reject impossible windows and ensure structural
   counts describe the actual returned data.

2. **High — the newly asserted shifted-window contract is not independently
   supported** (`pipe_proc.py:2048–2050`, `test_pipe_proc_unit.py:129–130`).
   Arithmetic explains the implementation: the requested inclusive width is
   `700-400+1=301`; shifting the zero-based start by the overflow gives
   `399-(700-512)=211`. It does **not** establish the intended convention.
   NMRPipe actually clips this request to **400–512**, i.e. `slice(399,512)`,
   shape `(113,1024)`, counts 113, `X1=400`, `XN=512`, `APOD=113`,
   `CENTER=-143`, `SW=220.703125`. The fix returns 301 rows starting at 212.
   The manual establishes inclusivity but does not promise width-preserving
   translation of out-of-range coordinates. The unchanged X-axis algorithm
   and upstream #289 are implementation precedents, not independent scientific
   evidence. This is a newly pinned observable contract on a path that used to
   fail, not a regression of an already functioning Y extraction. Resolve the
   convention against this evidence; retaining the divergence requires an
   explicit maintainer compatibility decision and documentation.

3. **Medium — the new scientific fixture has inconsistent calibration**
   (`test_pipe_proc_unit.py:138–144`, origin assertion at 157). `create_dic`
   gives F1 `CENTER=257`, `ORIG=-498.046875`; the test overrides only `CENTER`
   to 256. Thus the header is inconsistent by `1000/512 = 1.953125 Hz`.
   NMRPipe preserves the input frequency coordinates, whereas nmrglue
   recalculates from `CENTER`. On the exact test input NMRPipe produces origins
   `-498.046875`, `251.953125`, `-498.046875` for the three requests, not
   `-500`, `250`, `-500`. The inherited recalculation is not a new source bug;
   introducing this inconsistent fixture as axis-validation evidence is a test
   defect. A review-only diagnostic setting input `ORIG=-500` made NMRPipe
   agree with the asserted origins for the first two crops, without changing
   any repository assertion. A future implementation must use a coherent
   reference or explicitly document what inconsistent-header policy it tests.

### Independent axis calculation and omitted assertions

For a **coherent** real F1 header with 512 points, `CENTER=256`, `SW=1000 Hz`,
and `CAR*OBS=0`, the spacing is `d=1000/512=1.953125 Hz` and the last point is
`ORIG=-500 Hz`. For zero-based start `a`, stop `b`, length `n=b-a`:

```text
SW' = n*d
CENTER' = 256-a
ORIG' = -500 + (512-b)*d
APOD' = floor(512*n/512)
```

This independently gives `(APOD,CENTER,SW,ORIG)`:
`(511,255,998.046875,-500)` for `[1:512]`,
`(128,256,250,250)` for `[0:128]`, and
`(301,45,587.890625,-500)` **conditional on choosing** `[211:512]`.
`CENTER=256` outside a 128-point crop is legitimate: the carrier reference
point lies outside the retained region. These are not grounds for centering
the cropped data at 64/65. The exact current test input, however, describes
another frequency origin; its output coordinates move by one point.
All these F1 values are binary-exact fractions, so the exact equality assertions
are not inherently too strict. External float32 storage rounding seen on
default F2 values and nonbinary fractions is separate from the 1.953125-Hz error.

**Pre-existing:** at `pipe_proc.py:2095–2100`, a crop beginning at row 1
retains `X1=0`, `XN=0`, `APOD=512` instead of NMRPipe's `1,128,128` for
1–128. The omitted assertions cover **X1 as well as XN and APOD**. These
omissions do not weaken an old assertion (all three tests are additions),
but they deliberately leave that calibration/history defect unvalidated.
`SW=250` and `CENTER=256` are independently supported; `ORIG=250` requires
the coherent input described above. A successful structural round trip cannot
establish scientific validity of these fields. No metadata assertion was
modified during this review.

### Limits, dimensions, and quadrature

- In-bounds differential matrix: **68 assertion-checked cases** over real/real,
  real-indirect/complex-direct, and hypercomplex arrays, TD/FD, `sw=True/False`,
  full, first-row, second-row, interior and endpoint windows (excluding a lone
  hypercomplex component). Values equal the direct NumPy slice; counts equal
  the row count in these storage layouts; every other header field equals the
  baseline. **Three additional checks** with `FDSLICECOUNT=0` verify exact
  before/after preservation when no Y crop occurs (default, explicit full
  range, X-only crop). Neither claims that inherited metadata are all correct.
- With real 2D arrays, first/last singleton, full/default, interior and
  `sw=False` checks support the structural fix. `round=128` on 400–500
  produces `[384:512]` in both the correction and NMRPipe. Conversely,
  2–513 and 600–700 shift in nmrglue but clip in NMRPipe; `pow2=True` on
  400–700 yields 512 versus 128 rows. These further constrain the unresolved
  upper-bound convention.
- Real transposed 2D data (`FDDIMORDER=[1,2,3,4]`) correctly update the current
  indirect axis F2 and the counts. The tested 1D X crop is unchanged. A 3D
  ndarray ignores Y extraction before and after; support for full 3D/4D arrays
  is not established by this fix. No 4D or 3D plane-stream comparison was run.
- **Pre-existing:** hypercomplex FD data halve `SW` even without extraction
  (`1000 -> 500`); with 3–128, `APOD=31` versus NMRPipe 63 and `CENTER=126`
  versus 127 reflect mixing physical rows and complex points. Hypercomplex TD
  1–128 gives counts 128, `APOD=TDSIZE=64`, `CENTER=33`, `ORIG=-484.375`,
  matching NMRPipe for tested phase codes 2/3/4. An odd 511-row TD crop keeps
  `APOD=TDSIZE=255.5` rather than NMRPipe's 255, before and after. The TPPI
  probe (phase 1, real indirect/complex direct) preserves values/counts but
  inherits `CENTER=65`, `ORIG=15.625` versus 33 and -484.375 in NMRPipe.
- **Pre-existing:** mixed real-direct/complex-indirect storage needs special
  handling. A valid `(512,1024)` array can have `FDSPECNUM=256`,
  `FDSLICECOUNT=512`; `pipe.find_shape` doubles the former. On this valid input,
  1–128 yields 128 physical rows in nmrglue: baseline counts 256/512, new
  counts 128/128 predicting 256 rows, both inconsistent. NMRPipe interprets
  that request as 128 complex vectors and returns 256 physical rows with
  counts 128/128. The correction does not make this layout compatible.
  The initial ten mixed/phase probes wrongly used `FDSPECNUM=512` and were
  rejected by NMRPipe's file-size check; they are **not validation**. Corrected
  diagnostic headers and valid phase layouts were subsequently compared.
- **Pre-existing:** zero/negative bounds differ from NMRPipe (negative integers
  there are end-relative); reversed bounds 200–100 still raise
  `ZeroDivisionError` in both nmrglue versions. These are separate follow-ups.

Across the exploratory matrix, **66 executable invocations** completed:
56 exited 0 and 10 rejected the invalid diagnostic headers just described.
An exit 0 is not a declaration of header/value equivalence; the divergences
above are results of those successful executions. There were no pytest skips
or xfails. Synthetic comparisons do not validate real-corpus interoperability,
all acquisition modes, malformed inputs generally, or cross-platform behavior.

### Required follow-up and scope

Address the newly successful oversized-window corruption and settle the newly
asserted shifted-window convention. Establish coherent scientific test inputs
before treating the asserted origins as validated. Keep inherited X1/XN/APOD,
mixed-quadrature, TPPI and higher-dimensional limitations separately tracked;
they are not reasons to silently expand this patch. The unrelated roadmap
items (Bruker, JCAMP-DX, test reorganization) present in the local diff were
preserved and are outside this review's approval scope. Release gates remain
unchanged. The minimal source change is generic and already merged upstream
as #289 by reneeotten (both commit identities and authorship checked); no
additional upstream contribution is implied or authorized.

## Second review — 2026-10-08 (historical)

**Verdict: Changes requested.** This is follow-up verification by the same
independent reviewer, who did not implement either revision. It evaluates the
current uncommitted correction over `1e3e29c`, including the five-case test and
the new lower/upper Y clamps. No reviewed source, test or assertion was edited.
The three findings in the first review are resolved for the targeted ordinary
real-2D extractions. A new interaction with `round`/`pow2` prevents approval.

### Confirmed corrections

All five current tests fail on `1e3e29c`: two stale-count assertion failures,
then three `ZeroDivisionError`s. They all pass with the current correction.
Fresh comparisons with the actual `nmrPipe` executable confirm identical
values, shape and both structural counts for each case:

| Request | Zero-based rows | Rows / both counts | F1 CENTER | F1 SW (Hz) | F1 ORIG (Hz) |
|---|---|---|---|---|---|
| 2–512 | `[1:512]` | 511 | 255 | 998.046875 | -500 |
| 1–128 | `[0:128]` | 128 | 256 | 250 | 250 |
| 400–700 | `[399:512]` | 113 | -143 | 220.703125 | -500 |
| 1–700 | `[0:512]` | 512 | 256 | 1000 | -500 |
| 600–700 | `[511:512]` | 1 | -255 | 1.953125 | -500 |

The fixture's added `ORIG=-500` is coherent with `CENTER=256`, `SW=1000`,
512 real points and `CAR*OBS=0`. Independently, spacing is `1000/512` Hz;
113 points therefore span `220.703125` Hz, and subtracting the 399 removed
leading points gives `CENTER=256-399=-143`. The last original point is retained,
so ORIG remains -500. For 1–128, ORIG is
`-500+(512-128)*(1000/512)=250`. Negative or outside-window CENTER values are
valid reference positions. The asserted axis numbers agree with NMRPipe.

The first-row history fields remain a **pre-existing** limitation: 1–128
retains `X1=0, XN=0, APOD=512` versus NMRPipe `1,128,128`; 1–700 retains
`X1=XN=0` versus `1,512` (APOD=512 is correct). These are precisely the
conditional coverage gaps in the current test, not newly removed assertions.
The five `ng.pipe.write/read` round trips also pass; they verify serialization
and shape, **not** execution of NMRPipe or independent calibration conventions.

### Introduced finding: rounding is truncated at the domain boundary

**High — `nmrglue/process/pipe_proc.py:2035–2051`, especially the removed
compensation at 2044–2045.** The correction clips a window *after* expanding
it for `round`/`pow2`. This discards the requested expansion rather than moving
the rounded window inside the available domain. It changes previously correct
data selections even when the user's original bounds are entirely in range:

| Request on 512 rows | Data on baseline 1e3e29c | Current data | NMRPipe 13.0 data |
|---|---|---|---|
| `y1=1, yn=128, round=256` | `[0:256]`, 256 rows | `[0:192]`, 192 rows | `[0:256]`, 256 rows |
| `y1=1, yn=100, pow2=True` | `[0:128]`, 128 rows | `[0:114]`, 114 rows | `[0:128]`, 128 rows |
| `y1=400, yn=500, round=128` | ZeroDivisionError | `[386:512]`, 126 rows | `[384:512]`, 128 rows |
| `y1=400, yn=700, pow2=True` | ZeroDivisionError | `[294:512]`, 218 rows | `[384:512]`, 128 rows |

The first two are genuine regressions of the **data selection** against the
baseline; their old structural headers were separately defective. For example,
128 points rounded to 256 expand to `[-64:192]`; merely replacing -64 by 0
leaves 192 points, although a 256-point interval fits in the array. With
`pow2=True`, the analogous expansion `[-14:114]` loses 14 points. These
results are neither the requested multiple nor a power of two. Current counts
accurately describe the wrong-length output: checking only header/shape
agreement cannot catch this regression. The associated SW/ORIG also change
because a different region is selected (375/125 instead of 500/0 in the first
case; 222.65625/277.34375 instead of 250/250 in the second).

The NMRPipe EXT manual and executable help describe size expansion for these
options. The observed convention distinguishes clipping user coordinates from
fitting a subsequently expanded rounded interval into the domain. Correcting
that interaction is part of preserving this function's existing options; it
does not require fixing inherited X1/XN/APOD or quadrature behavior. Add
regressions for lower-bound expansion, upper-bound expansion and combined
out-of-range/rounding requests. Do not restore unconditional translation of
the original 400–700 request. A requested multiple larger than the whole array
remains a separate saturation case: 1–512 with `round=1024` now correctly
returns all 512 rows and counts 512, matching NMRPipe.

Minimal independent reproducer for the new blocker (run from the checkout):

```python
import copy
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import nmrglue as ng

u = ng.fileiobase.create_blank_udic(2)
u[0].update(size=512, complex=False, sw=1000., obs=1., car=0.)
u[1].update(size=1024, complex=False)
d = ng.pipe.create_dic(u)
d.update(FDSPECNUM=512., FDSLICECOUNT=512., FDF1FTFLAG=1.,
         FDF2FTFLAG=1., FDF1APOD=512., FDF1CENTER=256., FDF1ORIG=-500.)
a = np.arange(512*1024, dtype="float32").reshape(512, 1024)
old = dict(ng.pipe_proc.__dict__)
exec(compile(subprocess.check_output(
    ["git", "show", "1e3e29c:nmrglue/process/pipe_proc.py"], text=True),
    "<baseline>", "exec"), old)
with tempfile.TemporaryDirectory() as directory:
    src, dst = [Path(directory)/name for name in ("in.ft2", "out.ft2")]
    ng.pipe.write(str(src), d, a)
    for kw, flags in [({"y1": 1, "yn": 128, "round": 256},
                       ["-y1", "1", "-yn", "128", "-round", "256"]),
                      ({"y1": 1, "yn": 100, "pow2": True},
                       ["-y1", "1", "-yn", "100", "-pow2"])]:
        for name, fn in [("baseline", old["ext"]), ("current", ng.pipe_proc.ext)]:
            header, data = fn(copy.deepcopy(d), a.copy(), **kw)
            print(name, kw, data.shape, header["FDSPECNUM"], header["FDF1SW"])
        subprocess.run(["nmrPipe", "-in", str(src), "-fn", "EXT", *flags,
                        "-sw", "-out", str(dst), "-ov"], check=True)
        header, data = ng.pipe.read(str(dst))
        print("nmrPipe", kw, data.shape, header["FDSPECNUM"], header["FDF1SW"])
```

### Fresh validation and limits of this round

- Linux Python 3.13.13 / pytest 9.1.1, same local NMRPipe 13.0 executable
  resolved on PATH as in the first review. `nmrPipe -fn EXT -help` confirmed
  the `round` and `pow2` options; executable comparisons exited normally.
- Baseline substitution in the pytest process: **5 failed, 0 skipped**, exit 1
  (two stale counts, three exceptions). No file was reverted to run this.
- `python -m pytest tests/test_pipe_proc_unit.py -v --strict-markers
  --strict-config -ra`: **44 passed, 0 skipped**, exit 0; actual invocation
  also used `-p no:cacheprovider` and a disposable `--basetemp`.
- **15 synthetic external comparisons**, all executable exit codes 0:
  **11 identical value arrays and 4 divergent rounded selections** listed
  above. Counts match output shape in all 15 current outputs; for `sw=True`,
  retained frequency coordinates match the coherent input grid within
  `1e-10 Hz` absolute tolerance. External metadata differences are separately
  reported; 11 equal arrays do not mean 11 completely equal headers.
- **72 in-bounds differential assertion cases**: real/real, complex-direct/
  real-indirect, hypercomplex; TD/FD; `sw=True/False`; default/full, 2–512,
  1–128, 3–128 and X-only extraction. Data and all noncount header fields
  match baseline; current counts agree with returned rows. **Two transposed
  real-2D checks** also pass. These assertions establish preservation, not
  scientific correctness of inherited hypercomplex calibration.
- No pytest skips or xfails, and no invalid external diagnostic header in
  this round. Full autonomous/dataset/external suites were not rerun. Mixed
  quadrature, TPPI and 3D limitations from the first review remain recorded
  as **pre-existing**, not freshly revalidated or promoted to blockers here.
  Real-corpus, byte-order, 4D and plane-stream coverage remain outside scope.
  The canonical corpus was not accessed; all generated files were temporary.

The earlier validation summary had mixed the new five-case result with the
old 42-test result and the original lack of executable comparison. It is now
explicitly historical (3/42); the implementation response records 5/44, and
this section records the follow-up review. Attribution to reneeotten/#289 is
retained, with the local clipping adaptation distinguished from upstream.
Release gates and unrelated roadmap work are unchanged. Approval requires
resolution of the introduced rounding regression, not a broad calibration
or quadrature rewrite.

## Response to second review

The review established that coordinates and expanded-window placement are
distinct operations. `ext` now first clips the requested positive Y limits to
the available vectors, including the last-vector behavior for a lower limit
beyond the data. It computes `round`/`pow2` from that clipped request. It then
fits the expanded interval into the array without changing its size; an
expansion at least as large as the dimension saturates to the full dimension.

Four new autonomous regressions cover the review matrix: `1–128, round=256`
returns `[0:256]`; `1–100, pow2=True` returns `[0:128]`; both `400–500,
round=128` and `400–700, pow2=True` return `[384:512]`. A direct NMRPipe 13.0
Rev 2026.072.12.03 comparison after this response found identical arrays,
shapes and both indirect count fields in all four cases. The previous five
clipping regressions remain unchanged. At the time of this self-validation a
third review was pending; its outcome is recorded below. The nine-case
regression passed 9 tests
and the focused unit file passed 48 tests, both with 0 skips and exit 0.

## Third review — 2026-10-08

**Verdict: Ready to merge.** Follow-up by the same independent reviewer, who
did not implement any revision. Target: the current uncommitted diff over
`1e3e29cea1a1b2f2bb31fb097e0872647af2089d`, including the nine-case regression.
The current source clips requested Y coordinates before expansion, computes
the rounded size from the clipped interval, then fits that interval into the
domain or saturates to the full dimension. No introduced defect remains in
the reviewed positive-coordinate extraction/rounding scope. This verdict
supersedes the earlier requests for changes, not their historical evidence.

### Closure and independent scientific evidence

All nine regression selections now agree exactly with the NMRPipe executable
for values, shape, FDSPECNUM and FDSLICECOUNT. F1 CENTER/SW/ORIG agree as well.
The four formerly blocking rounded cases give:

| Request on 512 rows | Zero-based slice | Rows / both counts | CENTER | SW (Hz) | ORIG (Hz) |
|---|---|---|---|---|---|
| 1–128, round=256 | `[0:256]` | 256 | 256 | 500 | 0 |
| 1–100, pow2=True | `[0:128]` | 128 | 256 | 250 | 250 |
| 400–500, round=128 | `[384:512]` | 128 | -128 | 250 | -500 |
| 400–700, pow2=True | `[384:512]` | 128 | -128 | 250 | -500 |

The first five selections retain the independently verified results in the
second-review table. The fixture remains coherent with input CENTER=256,
SW=1000 and ORIG=-500. Independent arithmetic, rather than copying `ext`:
1–100 requires a 128-point power-of-two interval; at the left edge it fits
as `[0:128]`. The clipped 400–700 interval has 113 vectors and expands to 128;
fitting at the right edge gives start `512-128=384`. With spacing
`1000/512=1.953125 Hz`, its SW is 250, CENTER is `256-384=-128`, and the
unchanged final point fixes ORIG at -500. `[0:256]` gives SW=500 and
ORIG=`-500+(512-256)*1.953125=0`. All asserted F1 fractions for the
512-row fixture are binary-exact, justifying exact equality in the tests.

Saturation was separately compared with the executable: on 512 rows,
1–512 with round=512 or 1024 and 1–700 with pow2 all return 512 rows/counts;
600–700 with round=128 returns `[384:512]`. On 511 rows, a full-range pow2
request returns 511 rows, while 400–700/pow2 returns `[383:511]`, 128 rows.
A one-row input also saturates safely. These checks cover an expanded length
equal to and greater than the dimension, both edges, and a non-power-of-two
dimension. There is no negative slicing index or impossible structural count
in the tested ordered positive-coordinate cases.

### Validation performed in this round

Environment: Linux, Python 3.13.13, NumPy 2.5.3, pytest 9.1.1; actual
`nmrPipe` on PATH under `~/pipe/nmrbin.linux239_64`, version 13.0 Rev
2026.072.12.03 identified earlier in this review session. No corpus was used.

- Current nine tests with **baseline ext substituted only in the pytest
  process**: **9 failed, 0 skipped**, exit 1. Four failures are stale-count
  assertions and five are ZeroDivisionErrors. The lower-edge rounded
  selections already worked on the baseline but their structural counts did
  not; the intermediate revision's selection regressions were independently
  demonstrated in round 2 and are now resolved.
- `python -m pytest tests/test_pipe_proc_unit.py -v --strict-markers
  --strict-config -ra`: **48 passed, 0 skipped**, exit 0, including all nine
  regression cases and their temporary-file round trips. The actual invocation
  also used `-p no:cacheprovider` and a task-owned `--basetemp`.
- **25 initial synthetic executable comparisons:** all processes exited 0,
  and all value arrays, shapes and both counts matched. The 22 tests on the
  standard 512-row fixture also matched CENTER/SW/ORIG. Three diagnostic
  inputs of sizes 511/1 used fractional CENTER and differed in that field;
  consequently the initial aggregate comparison script **exited 1**, not 0.
  These differences were investigated rather than silently waived.
- **Eight follow-up executable comparisons** using integer CENTER and
  coherent ORIG on 511-row and one-row inputs matched values, shapes, counts
  and CENTER/SW/ORIG (allowing float32 storage rounding for nonbinary values).
  **Two fractional-CENTER baseline/current comparisons** established that the
  differences below already existed. All ten executable calls exited 0;
  both diagnostic commands exited 0. Total: **35 executable invocations**,
  not a claim of 35 identical complete headers.
- **96 baseline-preservation assertion cases** passed: real/real,
  real-indirect/complex-direct and hypercomplex layouts; TD/FD;
  sw=True/False; default/full, 2–512, 1–128, 3–128, X-only 100–200,
  1–128/round=256 and 1–100/pow2. Data and noncount metadata match baseline,
  and counts match returned rows in those layouts. **Two transposed real-2D
  checks** passed, including a rounded request beyond the transposed domain.
  Preservation does not validate inherited hypercomplex calibration.

External invocation pattern was `nmrPipe -in INPUT -fn EXT [coordinates and
round/pow2 options] -sw -out OUTPUT -ov`, omitting -sw for sw=False. This
executes NMRPipe on a fresh synthetic file; the unit tests' `ng.pipe.write/read`
round trips are separate serialization evidence. Values and counts were
compared exactly. For external CENTER/SW/ORIG comparison the diagnostic used
`atol=1e-4, rtol=0` to allow float32 header rounding on 511-point grids;
observed ordinary rounding differences were below 0.00003 Hz. For sw=True,
current output frequency coordinates were also compared to the retained
input grid with `atol=1e-10 Hz, rtol=0` in all 25 initial cases.

The central comparison reproducer in the second-review section remains usable:
its formerly divergent results now agree. Extend its case list using the
table above and saturation cases to reproduce this verification. For odd/single
row diagnostics, set `n` rows, `CENTER=n//2+1` and
`ORIG=-1000*(n-CENTER)/n` with SW=1000; do not generalize the even fixture's
`CENTER=n/2` to every size without accounting for NMRPipe's handling below.

### Classified remaining observations and limits

- **Introduced by this change:** none remaining identified in the reviewed
  scope. All original review blockers and the round-2 regression are closed.
- **Pre-existing:** first-row X1/XN/APOD omissions remain explicit. For
  1–128/round=256, nmrglue retains `0,0,512` versus NMRPipe `1,256,256`;
  for 1–100/pow2 it retains `0,0,512` versus `1,128,128`. These fields are
  still excluded by the conditional assertions; no old assertion was removed.
  The independently supported CENTER/SW/ORIG expectations are not affected.
- **Pre-existing:** fractional CENTER handling differs from NMRPipe. With
  511 rows, CENTER=255.5, ORIG=-500 and crop 3–128, both baseline and current
  nmrglue give CENTER=253.5; NMRPipe gives 253. With one row, CENTER=0.5,
  ORIG=-500 and crop 1–1, both nmrglue versions retain 0.5; NMRPipe returns
  -666 in CENTER while retaining ORIG=-500. These are the same types of
  differences that failed the initial diagnostic; no fractional-CENTER policy
  is changed or approved here. Integer-CENTER follow-up inputs agree.
- **Pre-existing:** mixed quadrature, TPPI, hypercomplex calibration, negative
  end-relative coordinates and full-3D ndarray limitations retain the statuses
  established in the first review. They were not repaired or broadly
  revalidated by the rounding correction.
- **Out of scope:** corpus interoperability, byte-order matrices, 4D and
  plane-stream formats, and unrelated roadmap changes. Complete autonomous,
  dataset and historical external suites were not run. There were no pytest
  skips/xfails; omitted profiles are not passing evidence. No release gate is
  changed by approval of this focused correction.

Attribution to reneeotten and #289 remains correct for the original adaptation;
the independently verified clipping/rounding follow-ups are additional local
work. Approval is technical review evidence, not authorization to commit,
publish, merge or contribute upstream. The canonical corpus, product source
and assertions were untouched by this review; disposable diagnostics were
cleaned after recording the evidence.
