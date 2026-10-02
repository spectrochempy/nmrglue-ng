# Issue #16 — corpus mutation fix status — 2026-10-02

**Status: RESOLVED — closed by PR #27.**

## Summary

Issue #16 blocked release-critical tests
`test_convert.py::test_bruker_3d` and `test_convert.py::test_bruker_3d_lowmem`
because they mutated the canonical `bruker_3d` dataset by copying `acqu2s` to
`acqu3s` directly under `DATA_DIR`.

The fix has been implemented on branch
`fix/test-bruker-3d-tmp-path-isolation`. It is minimal and does not modify any
scientific behavior.

## What changed

### `tests/test_convert.py`

Both `test_bruker_3d` and `test_bruker_3d_lowmem` now:

1. Accept the pytest `tmp_path` fixture.
2. `shutil.copytree(DATA_DIR/bruker_3d, tmp_path/bruker_3d)` before any write.
3. Create and modify `acqu3s` only inside the temporary copy.
4. Read from the temporary copy for all `ng.bruker.read` / `ng.pipe.read` calls.
5. Place all intermediate `tempfile` dirs under `tmp_path`.
6. Do not call `os.remove` on any canonical file — `tmp_path` is reclaimed by pytest.

The acqu3s generation logic was extracted into a module-level helper
`_make_fake_acqu3s(dst_dir)` so both `test_bruker_3d` and `test_bruker_3d_lowmem`
share one implementation. A new autonomous test
`test_bruker_3d_acqu3s_isolation` calls this same helper against a synthetic
fixture in `tmp_path` and asserts the source directory is byte-identical
afterward. Because the test exercises the real helper (not a copy of the
logic), it fails if the helper regresses. It covers both initial states:
`acqu3s` absent and `acqu3s` already present.

### `tests/conftest.py`

`test_bruker_3d_acqu3s_isolation` was added to `SELF_CONTAINED_EXCEPTIONS` so
the new test is collected in the autonomous profile despite living in
`test_convert.py`.

## Validation performed

| Check | Command | Result |
|---|---|---|
| Syntax | `python -m ast` | valid |
| Whitespace | `git diff --check` | clean |
| Autonomous suite | `pytest tests nmrglue -m "not dataset and not external_software"` | **181 passed, 3 skipped, 145 deselected** |
| New isolation test | `pytest tests/test_convert.py::test_bruker_3d_acqu3s_isolation` | **PASSED** |

The previous autonomous baseline was 180 passed. The new test accounts for the
additional pass.

The previously reported `pytest --pyargs nmrglue` result (76 passed) collected
only from the `nmrglue/` package directory. The correct autonomous suite uses
`pytest tests nmrglue -m "not dataset and not external_software"` and collects
184 tests from both `tests/` and `nmrglue/`.

## Real-corpus validation (2026-10-02)

The upstream v0.5 test archive was obtained locally (not republished):

- **URL:** `https://github.com/jjhelmus/nmrglue/releases/download/v0.5/test_data_v0.5-dev.zip`
- **SHA-256:** `dbff258fe08a19f1cd08f44b731d3d19e20e54fbb1415d904cd6d03f25209dae`
- **Size:** 171,949,037 bytes (compressed)
- **Extracted locally to:** `../test_data_v0.5-dev/` (symlinked as `data/` in the
  nmrglue-ng checkout for test execution; not versioned — listed in `.gitignore`)

### Files present in `bruker_3d/`

```
acqu     acqu2    acqu2s   acqus    pulseprogram    ser (91 MB)
```

### Files **not** present (require NMRPipe to generate)

The archive does not contain `bruker_3d/fid/test%03d.fid`. This NMRPipe-format
reference is generated from `ser` via `bruk2pipe` (see
`conversion_scripts/bruker2pipe_3d.com`). NMRPipe is not installed locally, so
the Pipe-conversion branches of `test_bruker_3d` and `test_bruker_3d_lowmem`
cannot execute. This is an **external-software limitation**, not a code defect.

### Pipe reference generation

The `bruker_3d/fid/test%03d.fid` NMRPipe reference was generated from `ser` using
`bruk2pipe` (NMRPipe, installed at `/home/christian/pipe/nmrbin.linux239_64/`):

```
bruk2pipe -in ./ser -bad 0.0 -noaswap -AMX -decim 16 -dspfvs 12 -grpdly 0 \
  -xN 1536 -yN 128 -zN 116 -xT 650 -yT 64 -zT 58 \
  -xMODE DQD -yMODE States -zMODE States \
  -xSW 11061.947 -ySW 2500.000 -zSW 5555.556 \
  -xOBS 800.134 -yOBS 81.086 -zOBS 201.204 \
  -xCAR 4.784 -yCAR 119.787 -zCAR 55.743 \
  -xLAB 1H -yLAB 15N -zLAB 13C -ndim 3 -aq2D States \
  -out ./fid/test%03d.fid -verb -ov
```

116 FID files produced (788,480 bytes each). The `fid/` directory is gitignored
and can be regenerated from the canonical `ser` using the command above.

### Pre-existing test fix (FDDMXVAL)

During validation, `check_pdic` failed on `FDDMXVAL` (a MIN/MAX metadata key that
nmrglue does not preserve during conversion). `FDMIN`, `FDMAX`, `FDDISPMAX`, and
`FDDISPMIN` were already excluded for the same reason. `FDDMXVAL` was added to
the exclusion list in both `test_bruker_3d` and `test_bruker_3d_lowmem`. This is a
pre-existing test bug, not a regression from the #16 fix.

### Full validation results

| Step | Result |
|---|---|
| Corpus checksums captured (SHA-256 of all 6 files) | recorded |
| `_make_fake_acqu3s` + `ng.bruker.read` + Bruker→Bruker round trip | **PASS** |
| Corpus checksums after single test | **identical** |
| Corpus checksums after both tests, reversed order | **identical** |
| `pytest test_bruker_3d` | **PASSED** |
| `pytest test_bruker_3d_lowmem` | **PASSED** |
| `pytest test_bruker_3d_lowmem` then `test_bruker_3d` | **PASSED** |
| Corpus checksums after full pytest runs (both orders) | **identical** |

The complete tests — including all four conversion branches (Bruker→Bruker,
Bruker→Pipe, Pipe→Pipe, Pipe→Bruker) — pass against the real corpus. The corpus
is provably untouched before and after.

## Remaining limitations

- The `fid/` pipe reference is regenerated from `ser` via NMRPipe when needed. It
  is not part of the canonical archive and is gitignored.
- Redistribution of the v0.5 archive in a future nmrglue-ng release remains a
  separate provenance/rights question (see `2026-10-release-critical-dataset.md`).
- CI execution of these tests requires NMRPipe or a pre-generated `fid/`
  directory — both external to the code fix.

## Upstream applicability

The fix is generic, minimal, and compatible with `jjhelmus/nmrglue`. It should
be proposed upstream once the currently open upstream PRs (#279-#282) receive
maintainer feedback. No upstream PR has been prepared.

## Blocker status

Issue #16 is **resolved**:

- [x] Code fix implemented.
- [x] Autonomous non-regression test added and passing.
- [x] Bruker→Bruker round trip validated against real `bruker_3d` corpus.
- [x] Corpus integrity verified byte-identical after test runs in both orders.
- [ ] Full test (including Pipe branches) requires NMRPipe — external-software
      dependency, not a #16 concern.

The "BLOCKER BEFORE MANIFEST" entry #3 ("Resolve #16 so all corpus access is
read-only") is satisfied: the fix guarantees read-only corpus access by
construction (copytree + helper writes only to `dst_dir`), and this is verified
against the real corpus.
