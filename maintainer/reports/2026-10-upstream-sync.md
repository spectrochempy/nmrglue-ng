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
| ZD widths | #9: `proc_base.zd_*` discrete (fractional widths raise), NMRPipe rule `W = floor(wide + 0.5)` applied in `pipe_proc.zd`, boxcar unchanged | [#283](https://github.com/jjhelmus/nmrglue/pull/283) (open): same rule inside `proc_base.zd_*` for all four windows, so `zd_boxcar(5.5)` would round to 6 instead of truncating to 5 | Maintainer decision 2026-10-11: exclude #283 from rc1 to preserve the #9 API placement and boxcar scope. Same scientific rule, established against NMRPipe 13.0 Rev 2026.072.12.03 over 113 outputs; the disagreement is API placement and boxcar scope. If #283 merges upstream, any later port remains a separate compatibility decision. |
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
2. **ZD width contract versus upstream #283** — resolved for rc1 by maintainer
   decision 2026-10-11: keep the #9 placement and boxcar scope; any later port
   remains a separate compatibility decision.

Approval of this report does not approve any scope reduction, change a
release gate, or authorize an upstream submission.

## Release-candidate reconciliation — 2026-10-11

Fresh read-only upstream fetch and GitHub queries, compared with local source
and recorded decisions; no scientific tests or independent review were run.
Exact snapshots:

- `jjhelmus/nmrglue:master`: `cd0c2c9d1cac4f1125a89dbe6ecdcd8ca194b59d`.
- `spectrochempy/nmrglue-ng:master` and local `origin/master` after the
  CR-only newline fix: `2c50110892ed7b74882fd137af70e870e03ae27f`.
- Previous upstream snapshot: `812bfa0805952bc0edceab9783e022541a29b736`.

**NMRNG-kb5.17 is closed.** The only new upstream master commit is
`cd0c2c9` ([#231](https://github.com/jjhelmus/nmrglue/pull/231)), whose
functional changes are already included through local #54/#63. Older gaps
still need explicit release-candidate dispositions. Recommendations below
are not maintainer decisions. The 2026-10-11 inherited-defect decision covers
the named P1 scientific-reliability subjects; it does not explicitly settle
bounded autophase or the pending ZD API choice. The local CR-only regression
was carried after this audit in #81 (`2c50110`).

### Complete upstream-master delta

`git log --no-merges HEAD..upstream/master` contains nine commits, grouped
below. Merge commits #258/#279/#289 introduce no additional subject.

| Upstream commits | Classification at the local snapshot | rc1 disposition |
|---|---|---|
| `cd0c2c9` (#231) | Already included: FID `(N - 1) / (LAST-FIRST)`, processed sweep/carrier, complex-array helper, time/frequency/complex flags. Local #63 (`35fd95d`) aligns the final FID formula and `np.iscomplexobj`; local safeguards and NTUPLES support are retained. | No carry needed. Upstream's formatting-only hunks need no synchronization. |
| `7851bef`, `b72a959` (#289) | Already adapted in #62 (`a662316`): original indirect counts and upper-bound assignment fixes, plus independently reviewed local coordinate clipping, rounded-window placement and saturation. | Keep local adaptation; do not replace it with upstream's shift-before-clipping algorithm. See [EXT evidence](2026-10-pipe-proc-ext.md). |
| `1a1d2dc` (#279) | Already included in #14 (`71862fe`): `scipy.linalg.pinv` replaces removed `pinv2`. Source comparison differs only in the explanatory comment. | No carry needed. |
| `61a45e6`, `c5aa626`, `b0514c4`, `9c6803d`, `2743c01` (#258) | Not included: optional `p1_bounds`, bounded solver path, option translation and tests. The unbounded default algorithm is retained upstream. | Maintainer decision 2026-10-11: defer to P2 processing coverage because this is optional new capability, with no identified repair to the existing default path. |

### Known open proposals and divergences

All PR numbers in this subsection refer to `jjhelmus/nmrglue`.

| Subject | Current evidence | Recommended or existing disposition |
|---|---|---|
| #261 CR-only Bruker JCAMP newlines | Upstream head `bc39452212a3561ebd189478fda22527e76d825c` contains `StringIO(text, newline=None)` from `6034f64`. Local #81 (`2c50110`) now carries the newline-normalization part with a self-contained CR-only regression and leaves the locale policy unchanged. | Included before rc1; no further carry needed for the newline defect. |
| #261 locale fallback | Local #53 deliberately uses strict UTF-8-BOM/CP1252/Latin-1 decoding independently of locale. | Exclude locale insertion under the existing [reader decision](2026-10-maintenance.md#bruker-reader-decisions); carrying newline normalization does not require it. |
| #264 singular `proc`/`proc2` discovery | Still open at `04fc1b82d794551b0600f3b84d4cf935085d6010`; local singular-file priority remains unresolved. | P1 Bruker axis/pdata follow-up under the 2026-10-11 non-blocking first-release decision. Preserve current default pending coherent vendor evidence and compatibility decision. |
| #262 `(XYW..XYW)` / `(XYM..XYM)` | Still open at `b531d16ddd5087a86b61cadc3366fad4872b349d`; local coordinate parser remains pair-based. | P1 JCAMP-DX tuple-size validation, explicitly non-blocking under the 2026-10-11 first-release decision. Synthetic critical replacements do not establish triple-column support. |
| #262 remaining comma-decimal heuristic | Upstream removed it; local `(X..XY)` and undeclared-format normalization remains, whereas `(XY..XY)` preserves delimiters. | Retain the documented local reader choice for this audit. Broader real-data/encoding semantics remain P1 under the existing non-blocking decision; no evidence here approves removing the remaining paths. |
| #283 ZD widths | Still open at `db649649bebc74346902732117dd46c2f269e592`. Local #9 rejects fractional `proc_base` triangle/sinebell/Gaussian widths, rounds at `pipe_proc.zd`, and preserves boxcar truncation. Upstream rounds all four base windows, including boxcar. | Maintainer decision 2026-10-11: exclude from rc1 to preserve the existing API placement and boxcar scope. This is not a new assertion of boxcar equivalence with NMRPipe; any later port remains a separate compatibility decision. |
| #291 FID follow-ups | Still open at `22db649230f85828d824670c9d2d53fc3777610d`; diff inspected. Complete-pair-only `as_complex`, available-component size and exact NTUPLES FID fallback are present locally. | Already included through #54/#63; no carry needed. |
| #275 reference frequency / Tecmag | Unintegrated semantics remain recorded in the maintenance report. | P1, explicitly non-blocking under the 2026-10-11 obs/ref/car and Tecmag decision. |

Maintainer decision 2026-10-11: the remaining optional upstream proposals are
not rc1 blockers under the dispositions below. The remaining open-PR inventory
was also screened: #259/#260/#277 are the
already-adapted reader work; #268/#270/#272 are the local Varian/`data_nd`
fixes; #278/#280/#281/#282 originate in already-carried SAVE, HT and fixture
work. These are source/history mappings, not fresh validation of every PR.
For optional #254 performance work and older #48 autophase proposals,
recommend P2 assessment after rc1. For #263 packaging, #243 test repairs and
#244 Nox, recommend excluding wholesale import in favor of the independent
packaging, reviewed single test tree and current CI contract. #265 denoising
remains outside the retained scope; its 2026-10-10 discussion now favors a
standalone package. These recommendations do not approve new scope decisions
and need not turn every open upstream proposal into a product requirement.

The two open issues updated since the prior snapshot were read: #290's
positive-Y EXT defect is handled locally by #62 (the separately noted X-axis
behavior remains outside that correction); #292's Pipe-to-Pipe `FDDMXVAL`
loss is handled by #65 (`7ef9b8f`). Existing dimensional-metadata limitations
remain under the recorded P1 non-blocking scope.

### Evidence, limits and next action

Commands executed on 2026-10-11 included `git fetch upstream`, exact-ref
resolution, `git log 812bfa0..upstream/master`, the complete upstream-only
commit inventory, `git show cd0c2c9`, source diffs (using
`--ignore-space-at-eol` for historical CRLF files), and `gh pr list`,
`gh pr view`, `gh pr diff`, `gh issue list` and `gh issue view` explicitly
targeting `jjhelmus/nmrglue`. GitHub master API reads confirmed both exact
remote snapshots above. Open PR metadata was screened in full (22 PRs),
with targeted diffs for #261/#283/#291; this is not a full review of all
unmerged proposals.

Next: refresh this reconciliation if upstream advances before publication.
NMRNG-kb5.6 is unblocked by this gate; its final pushed-commit validation,
current G1–G6 evidence and release preparation are separate work. No
release-readiness verdict is inferred from this source audit, and historical
test results were not rerun.
