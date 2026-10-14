# Bruker processing-file selection: `proc`/`procNs` versus `procs`/`procNs`

Assessed 2026-10-14 at `9694f45` (tag `v1.0.2`). Covers upstream issue
[jjhelmus/nmrglue#253](https://github.com/jjhelmus/nmrglue/issues/253) and the
reviewed-then-rejected upstream proposal
[jjhelmus/nmrglue#264](https://github.com/jjhelmus/nmrglue/pull/264). This is a
local audit, not an independent review, and it does not perform a new TopSpin
run.

## Question

TopSpin writes two families of processed-parameter files in `pdata/N/`:

- singular: `proc`, `proc2`, `proc3`, `proc4`;
- status: `procs`, `proc2s`, `proc3s`, `proc4s`.

Issue #253 reports that a parameter such as `ABSF1`/`ABSF2`, changed in the
TopSpin editor, may appear updated in the singular files rather than the status
files, so `read_pdata(..., procs_files=None)` (the default, which reads only the
status files) does not reflect it. PR #264 proposed discovering both families by
default. Upstream review rejected that as overbroad and asked for a
parameter-aware decision instead.

The decision requested here: should `nmrglue-ng` change the default precedence,
expose clearer selection, or document the compatibility boundary?

## What nmrglue actually consumes

`read_pdata` defaults to the status files only
(`nmrglue/fileio/bruker.py:673`, `:689`: `["procs", "proc2s", "proc3s",
"proc4s"]`). Downstream axis, shape and scaling logic is hard-wired to the
status keys:

- scaling factor: `dic['procs']['NC_proc']` (`bruker.py:1397`);
- endianness / dtype: `dic['procs']['BYTORDP']`, `dic['procs']['DTYPP']`
  (`bruker.py:1347`, `:1356`);
- shape: `dic['procs']`/`dic['proc2s']` `SI`/`XDIM`
  (`bruker.py:1444`, `:1454`).

The editor-only parameters named in #253 (`ABSF1`, `ABSF2`, and also `ABSG`,
`ABSL`, `SIGF1/2`, `NOISF1/2`) are **not read or used anywhere** in the package
(`rg 'ABSF|ABSG|ABSL|SIGF|NOISF' nmrglue/` returns no hits). Consequently the
issue changes what the returned `dic` exposes, not the reconstructed spectrum,
axes, shape or scaling.

## Real-file evidence (committed CC0 fixtures)

The packaged Bruker fixtures already ship both families, so the split is
reproducible without external data (provenance in
[fixture README](../../tests/fixtures/fileio/data/bruker_pdata/README.md)):

| File | SHA-256 | Writer (header) | `OFFSET` | `SW_p` | `NC_proc` | `XDIM` |
|---|---|---:|---:|---:|---:|---:|
| `exp1/pdata/1/proc`  | `b32a4e56…30fb3d` | `proc1d.exe` | 4.7 | 11904.7619047594 | 0 | 0 |
| `exp1/pdata/1/procs` | `1b4cfc2f…c6c7126f` | `dataserver.exe` | 15.11477 | 12500 | 13 | 0 |
| `exp2d_hsqc/pdata/1/proc2`  | `e388266c…df6186bc` | `edparproc.exe` | 164.9559 | 25641.0256410257 | 0 | 0 |
| `exp2d_hsqc/pdata/1/procs`  | `e242cda9…e82df0ba` | `proc2d.exe` | 7.99684 | 3597.12230215827 | -12 | 4096 |
| `exp2d_hsqc/pdata/1/proc2s` | `492cb85e…b7f53d340` | `proc2d.exe` | 189.3282 | 33112.5827814569 | -12 | 256 |
| `exp2d_cosy/pdata/1/proc2`  | `bb2fb188…879384704` | `edparproc.exe` | 10.50281 | 6605.01981505945 | 0 | 0 |
| `exp2d_cosy/pdata/1/procs`  | `869c95a5…93da5237` | `dataserver.exe` | 16.00128 | 10204.0816326531 | -4 | 2048 |
| `exp2d_cosy/pdata/1/proc2s` | `accc8b05…1c65ec0` | `proc2d.exe` | 16.00128 | 10204.081632653 | -4 | 512 |

The singular files are written by `edparproc.exe` (the parameter editor) and
carry `NC_proc = 0`, `XDIM = 0`, `STSI = 0`. The status files are written by the
processing engine (`proc1d.exe`, `proc2d.exe`, `dataserver.exe`) and carry the
`NC_proc`, `XDIM` and `STSI` values that actually produced the stored
`1r`/`2rr`. The status files are also the later write in every fixture (e.g.
`exp1`: `proc` 2024-01-01 23:21, `procs` 2024-01-02 18:51).

The direction of the `ABSF1`/`ABSF2` disagreement is not consistent, so no
single "always correct" file exists: in `exp1` the status file holds the
applied values (`procs` `ABSF1=15.11424`), whereas #253 reports the editor value
landing in the singular file. That confirms the two files have distinct roles,
not that one family is universally authoritative.

`read_pdata` consuming a stale singular `NC_proc = 0` / `XDIM = 0` instead of
the status values would corrupt the result: for `exp1`, scaling is a factor
`2**13` derived from `procs NC_proc = 13`, while `proc NC_proc = 0` would give
`2**0 = 1`; for `exp2d_hsqc`, `XDIM` and `NC_proc` are absent (zero) in `proc2`
but define the true 256×4096 shape in `proc2s`.

### Reproducer (read-only, current `master`)

```bash
python - <<'PY'
import nmrglue as ng, numpy as np
p1 = "tests/fixtures/fileio/data/bruker_pdata/exp1/pdata/1"

dic, data = ng.bruker.read_pdata(p1)                 # default: status files
print(sorted(dic.keys()))                            # ['acqus', 'procs']
print(dic['procs']['NC_proc'])                       # 13
_, raw = ng.bruker.read_pdata(p1, scale_data=False)
print(float(np.max(np.abs(data)) / np.max(np.abs(raw))))   # 8192.0 == 2**13

dic2, _ = ng.bruker.read_pdata(p1, procs_files=["proc", "procs"])
print(sorted(dic2.keys()))                           # ['acqus', 'proc', 'procs']
print(dic2['proc']['ABSF1'], dic2['procs']['ABSF1']) # 10 15.11424
print(dic2['proc']['NC_proc'], dic2['procs']['NC_proc'])   # 0 13

p2 = "tests/fixtures/fileio/data/bruker_pdata/exp2d_hsqc/pdata/1"
dic3, data3 = ng.bruker.read_pdata(p2)
print(sorted(dic3.keys()), data3.shape)              # ['acqus','proc2s','procs'] (256, 4096)
PY
```

Observed on `9694f45`: default keys `['acqus', 'procs']`, `NC_proc 13`, ratio
`8192.0`; explicit selection adds `dic['proc']` (`ABSF1 10`, `NC_proc 0`) next
to `dic['procs']` (`ABSF1 15.11424`, `NC_proc 13`); the 2D default reads
`procs`/`proc2s` and returns shape `(256, 4096)`.

## Conclusion and recommendation

For the parameters `nmrglue` reads, the status files are the correct default;
broadening default discovery (as in #264) would inject stale `NC_proc`/`XDIM`/
`STSI` and ambiguous duplicate parameter sets without changing the computed
spectrum. Recommended, compatible position:

1. **Keep the default** (`procs`/`procNs`) — no behavior change.
2. **Keep explicit selection** through `procs_files` (the existing #55 option),
   which already surfaces the editor-only parameters when a user needs them:
   `read_pdata(dir, procs_files=["proc", "procs", "proc2", "proc2s"])`.
3. **Document the boundary**: state the two file families and their roles in the
   `read_pdata` docstring (and note that `ABSF*`-style editor parameters are not
   used by axis/shape/scaling).
4. **Optional regression test** (test-only, verifies existing behavior): using
   the committed fixtures, assert that the default reads the status values and
   that explicit selection exposes `dic['proc']`/`dic['proc2']`. No dataset,
   no new data.

Maintainer decision 2026-10-14: the recommendation above is adopted as policy.
The `read_pdata` docstring clarification and the test-only regression are
tracked as a separate follow-up task; this audit authorizes no product-code
change by itself.

## Validation performed and omitted

- Performed: source inspection of `bruker.py`; `rg` confirmation that the
  editor-only parameters are unused; read-only execution of the reproducer above
  against the committed fixtures at `9694f45` (`python`, numpy 2.5.3).
- Omitted: no TopSpin execution, no live re-referencing pair, no upstream
  interaction. The evidence is from committed real TopSpin 4.3.0 outputs and the
  upstream issue thread.

## Remaining decisions / limits

- The general per-parameter rule ("which file holds the current value") is
  TopSpin-operation dependent and was not enumerated parameter by parameter;
  only the parameters `nmrglue` consumes were assessed.
- Whether to add the optional regression test and the docstring clarification is
  a separate, small authorized task (see roadmap row "Bruker processing-file
  priority").

## Related

- [Bruker processed-axis parameter selection](2026-10-bruker-axes.md) — axis
  construction (`pdata=True`), distinct from file selection.
- Roadmap row "Bruker processing-file priority".
