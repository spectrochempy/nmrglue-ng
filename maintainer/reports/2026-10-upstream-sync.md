# Upstream synchronization — October 2026

Audit date 2026-10-08. Baselines: `jjhelmus/nmrglue` master `812bfa0`
(fetched 2026-10-08) and nmrglue-ng `5619a1b` (master, equal to
`origin/master` when the audit ran). Every local check below was executed by
the current author in the project development environment; nothing is
transcribed from a prior audit and nothing is taken from hosted CI. This is a
read-only synchronization audit: it is not an independent review and not a
release validation. No product code, roadmap entry or release gate was
changed by it.

Scope: recent upstream merges and open pull requests/issues, compared with
recorded nmrglue-ng decisions on the same subjects. Findings are observations
and recommendations. The two items explicitly marked *awaiting maintainer
decision* are not decided here.

## Recent upstream merges

| Upstream | Merged | Content | nmrglue-ng state | Consequence |
|---|---|---|---|---|
| [#279](https://github.com/jjhelmus/nmrglue/pull/279) (`1a1d2dc`) | 2026-10-08 | `proc_lp`: replace removed `scipy.linalg.pinv2` with `pinv` | Already present in `nmrglue/process/proc_lp.py` and `tests/test_proc_lp.py`; this is the nmrglue-ng fix submitted upstream | No product change; see pause status |
| [#258](https://github.com/jjhelmus/nmrglue/pull/258) (`61a45e6`…`2743c01`) | 2026-10-07 | `autops(..., p1_bounds=None)`: optional first-order phase bounds, unbounded wrapped p0, regression tests | Absent; `autops` has no `p1_bounds` and nmrglue-ng has no autophase tests | Backward-compatible feature; candidate only for P2 processing coverage |
| [#289](https://github.com/jjhelmus/nmrglue/pull/289) (`7851bef`, `b72a959`) | 2026-10-08 | `pipe_proc.ext` indirect-dimension metadata and window clamp; closes [#276](https://github.com/jjhelmus/nmrglue/issues/276) | Absent; both defects reproduce (below) | Bug fix touching instrumental metadata; see defects |
| [#257](https://github.com/jjhelmus/nmrglue/pull/257), [#266](https://github.com/jjhelmus/nmrglue/pull/266) | 2026-06-22, 2026-08-16 | Tecmag `guess_tables`; Python 3.10–3.14 | Already aligned (`nmrglue/fileio/tecmag.py`, `pyproject.toml`) | None |

## Defects fixed upstream, still present in nmrglue-ng

1. **`pipe_proc.ext` stale slice metadata** ([#289](https://github.com/jjhelmus/nmrglue/pull/289) / [#276](https://github.com/jjhelmus/nmrglue/issues/276)).
   On nmrglue-ng `5619a1b`, `ext()` over a (512, 1024) array:
   - `y1=2, yn=512` → data (511, 1024) but `FDSPECNUM=512`, `FDSLICECOUNT=512`;
   - `y1=1, yn=128` → data (128, 1024) but `FDSPECNUM=512`, `FDSLICECOUNT=512`;
   - `y1=400, yn=700` (window past the end) → `ZeroDivisionError` in
     `recalc_orig`, the clamp writing `y_min = data.shape[0]` instead of
     `y_max` producing an empty crop.

   The upstream change is two lines and uses `old_y`, which the nmrglue-ng
   function already defines. Belongs to the P1 NMRPipe dimensional-metadata
   item and to the instrumental-metadata sensitivity rule.

2. **`bruker.read_jcamp` line endings** ([#261](https://github.com/jjhelmus/nmrglue/pull/261) commit `6034f64`).
   The strict-decode loop introduced by nmrglue-ng #53 passes decoded text to
   `io.StringIO(text)`, whose default newline handling leaves CR-only files as
   a single line where `open()` translated them. Upstream fixes this with
   `io.StringIO(text, newline=None)`. Established by source comparison with
   the upstream commit, not by a local reproduction. The gap is a consequence
   of our own adaptation, not of the historical code.

3. **Singular Bruker processing files** ([#264](https://github.com/jjhelmus/nmrglue/pull/264), fixes [#253](https://github.com/jjhelmus/nmrglue/issues/253)).
   nmrglue-ng reads only `procs`, `proc2s`, `proc3s`, `proc4s`. TopSpin may
   keep current values (e.g. `ABSF1`, `ABSF2`) in the singular `proc`/`proc2`
   files. The upstream proposal prefers the singular file per dimension while
   keeping the conventional dictionary keys; which file wins when both exist
   is a semantic choice that needs validation before any adoption.

4. **`(XYW..XYW)` / `(XYM..XYM)` coordinate tables** ([#262](https://github.com/jjhelmus/nmrglue/pull/262) commit `b531d16`).
   nmrglue-ng #47 reads coordinate data as pairs: on `15,420,1` / `16,1201,2`
   the width column is dropped and pairs are formed from the remaining
   numbers. Upstream sets the tuple size from the header variable list and
   returns numeric columns with shape (1, N, 3). Leading-dot values (`.5,3`)
   are already accepted by our parsers; only tuple-size handling is missing.

## Recorded divergences on settled scopes

| Subject | nmrglue-ng decision | Upstream position | Status |
|---|---|---|---|
| ZD widths | #9: `proc_base.zd_*` discrete (fractional widths raise), NMRPipe rule `W = floor(wide + 0.5)` applied in `pipe_proc.zd`, boxcar unchanged | [#283](https://github.com/jjhelmus/nmrglue/pull/283) (open): same rule inside `proc_base.zd_*` for all four windows, so `zd_boxcar(5.5)` would round to 6 instead of truncating to 5 | **Awaiting maintainer decision** (deferred 2026-10-08). Same scientific rule, established against NMRPipe 13.0 Rev 2026.072.12.03 over 113 outputs; the disagreement is API placement and boxcar scope. If #283 merges, a later port would conflict with the #9 contract. |
| Bruker JCAMP encoding | #53: strict chain `utf-8-sig`, `cp1252`, `latin-1`, independent of the locale (documented in [maintenance report](2026-10-maintenance.md)) | [#261](https://github.com/jjhelmus/nmrglue/pull/261) commit `bc39452` inserts `locale.getpreferredencoding(False)` before latin-1, on review request | Divergence recorded. The documented decision stands; no change is proposed. |
| JCAMP comma decimals | #47: no comma-to-dot in `(XY..XY)`; restricted comma-to-dot in `(X..XY)` and undeclared formats | [#262](https://github.com/jjhelmus/nmrglue/pull/262) commit `d5ef606` drops the heuristic entirely, citing the same file survey (253 CENAPTNMR files, no decimal comma observed) | Recommendation: evaluate removing the remaining restricted paths; integer-pair tables such as mass peak lists can still be rewritten by them. |

## Upstream contribution pause

The recorded condition is "no additional upstream contribution while PRs
#279–#282 have received no significant maintainer feedback". Status on
2026-10-08:

| PR | State | Feedback |
|---|---|---|
| [#279](https://github.com/jjhelmus/nmrglue/pull/279) | **Merged** 2026-10-08 01:42 UTC by kaustubhmote | none recorded (merge without comment or review) |
| [#280](https://github.com/jjhelmus/nmrglue/pull/280) | open | none |
| [#281](https://github.com/jjhelmus/nmrglue/pull/281) | open | none |
| [#282](https://github.com/jjhelmus/nmrglue/pull/282) | open | none |
| [#278](https://github.com/jjhelmus/nmrglue/pull/278), [#275](https://github.com/jjhelmus/nmrglue/pull/275) | open | none |

The clause is no longer literally accurate because #279 was merged. **Awaiting
maintainer decision** (deferred 2026-10-08): reformulate or lift the pause.
This audit opened and authorized no upstream issue, pull request or comment.

## Open upstream items mapped to the roadmap

| Item | Subject | Roadmap contact |
|---|---|---|
| [#288](https://github.com/jjhelmus/nmrglue/issues/288) | release versions diverge across GitHub / PyPI / Read the Docs | P0 documentation gate G5 ("Repair the documentation build"); already covered |
| [#87](https://github.com/jjhelmus/nmrglue/issues/87) | historical test dataset archive unavailable | P0 corpus provenance and redistribution; historical evidence that the gap is known upstream |
| [#221](https://github.com/jjhelmus/nmrglue/issues/221), [#21](https://github.com/jjhelmus/nmrglue/issues/21) | `make_uc` obs/car, ppm from reference frequency | P1 obs/ref/car semantics, with [#275](https://github.com/jjhelmus/nmrglue/pull/275) |
| [#253](https://github.com/jjhelmus/nmrglue/issues/253) with [#264](https://github.com/jjhelmus/nmrglue/pull/264) | `ABSF1`/`ABSF2` via singular proc files | P1 Bruker axis/pdata work; the defect is also present here (above) |
| [#223](https://github.com/jjhelmus/nmrglue/issues/223) | `proc_pipe.tp` on Bruker→Pipe hypercomplex flags | P1 NMRPipe metadata; follow-up to the #274 subject |
| [#254](https://github.com/jjhelmus/nmrglue/pull/254) | `ht`/`ha`/Bruker reorder speedups | P2, separately scoped performance work |
| [#265](https://github.com/jjhelmus/nmrglue/pull/265) / [#255](https://github.com/jjhelmus/nmrglue/issues/255) | ML denoising module | outside P0–P2; not retained |

JCAMP-DX and Bruker pull requests already adapted here (#259, #260, #261,
#262, #277 → nmrglue-ng #46/#47/#49/#52/#53) gained new upstream commits on
2026-10-06/07; the parts affecting our code are the line-ending fix, the
locale divergence and the tuple-size gap listed above.

## Evidence and limits

- Executed by the current author on 2026-10-08: fetch of `jjhelmus/nmrglue`,
  GitHub pull request and issue listing and detail reads, source comparison
  of the touched files, and in-memory reproductions of the `pipe_proc.ext`
  and `jcampdx` behaviours quoted above on nmrglue-ng `5619a1b` code.
- Not executed: the autonomous test suite, the dataset profile, the NMRPipe
  differential suite, and any independent review. No figure in this report
  comes from hosted CI or from a fresh full validation.
- GitHub pull request and issue state is a snapshot of 2026-10-08 and will
  drift.

## Remaining decisions

1. **Contribution pause #279–#282** — reformulate or lift (deferred by the
   maintainer on 2026-10-08).
2. **ZD width contract versus upstream #283** — keep the #9 placement and
   boxcar scope, or adopt the `proc_base`-level rule (deferred by the
   maintainer on 2026-10-08).

Approval of this report does not approve any scope reduction, change a
release gate, or authorize an upstream submission.
