# Issue #16 — corpus mutation fix status — 2026-10-02

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

## Limitations

- The `bruker_3d` dataset is **not present locally**. `test_bruker_3d` and
  `test_bruker_3d_lowmem` remain skipped. Their correctness against real data
  has **not** been confirmed.
- The isolation test verifies the *pattern* (source directory untouched) but
  does not validate scientific conversion results against a real 3D Bruker dataset.
- Reversing test order and re-running is not applicable: without the corpus,
  both tests skip regardless of order.

## Upstream applicability

The fix is generic, minimal, and compatible with `jjhelmus/nmrglue`. It should
be proposed upstream once the currently open upstream PRs (#279-#282) receive
maintainer feedback. No upstream PR has been prepared.

## Blocker status

Issue #16 is **partially resolved**:

- [x] Code fix implemented.
- [x] Autonomous non-regression test added and passing.
- [ ] Real-corpus validation of `test_bruker_3d` and `test_bruker_3d_lowmem`.
- [ ] Confirmation that canonical corpus is byte-identical after test run.

The "BLOCKER BEFORE MANIFEST" entry #3 ("Resolve #16 so all corpus access is
read-only") can be considered satisfied from the code perspective. The
independent real-corpus verification remains outstanding.
