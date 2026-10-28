# Independent review of PR #139 — 2026-10-27

## Summary

PR #139 changes `publish-pypi` from manual-only publication to automatic
publication on `vX.Y.Z`-style tag pushes, derives the version from the tag, and
synchronizes the PyPI artifacts into the matching GitHub Release. It also adds
tag-parser tests and updates contributor and maintainer documentation.

## Findings

### 1. **Introduced by this change**

- **Location** — `.github/scripts/release_version.py:9`, exercised by
  `.github/workflows/publish-pypi.yml:32-41`.
- **Defect** — The release-tag validator accepts any alphabetic suffix followed
  by digits, not only the documented `vX.Y.Z` and `vX.Y.ZrcN` forms. For
  example, `v1.2.3dev1`, `v1.2.3foo99`, and `v1.2.3RC1` are accepted.
- **Consequence** — A malformed/non-release tag matching `v*` can enter the
  publication workflow and become the source of a PyPI/GitHub release, or fail
  later after consuming release CI. The tag/version gate does not enforce the
  stated release contract.
- **Evidence** — Independently loading `version_from_tag` returned
  `1.2.3dev1`, `1.2.3foo99`, and `1.2.3RC1` for those inputs. The added tests
  cover `v1.0.0rc1` and a dotted dev version, but not these accepted invalid
  forms.

### 2. **Introduced by this change**

- **Location** — `CHANGELOG.md:8` and the PR description's
  `Changelog: not required` declaration; the developer-visible workflow and
  release-contract changes are in `.github/workflows/publish-pypi.yml` and
  `CONTRIBUTING.md`.
- **Defect** — The required `Unreleased` changelog entry is missing. The
  repository's contribution rules require every user- or developer-visible
  change to update `Unreleased`; the exception is for a purely internal change,
  which this release-process and contributor-documentation change is not.
- **Consequence** — The new automatic publication behavior and its tag/version
  contract are absent from the project's release history and the PR does not
  satisfy the documented contribution gate.
- **Evidence** — `CHANGELOG.md` has an empty `## Unreleased` section, while
  `CONTRIBUTING.md:471-476` requires an entry for developer-visible changes.

## Validation

The review targeted exactly `origin/master..ba12172` (`ba12172e1daaf02c38dc690eaebdbf169b0519d1`), whose base was
`origin/master` at `3149e34f8ad10c0617bdddd3a6cf177523d9c7a6`. The full diff,
workflow, release scripts, tests, `CONTRIBUTING.md`, roadmap, and maintainer
reports were read. No scientific values or corpus files are involved, so no
scientific recomputation was needed.

Commands run independently:

```text
python -m pytest tests/infrastructure/test_release_version.py tests/infrastructure/test_release_assets.py tests/infrastructure/test_release_notes.py tests/infrastructure/test_pypi_release_artifacts.py -q
12 passed

python -m pytest -m "not dataset and not external_software" -q
563 passed, 142 deselected, 42 warnings

git diff --check origin/master..ba12172
passed

Python/PyYAML workflow parse of .github/workflows/*.yml
passed
```

The targeted and self-contained test runs produced no skips. The full
self-contained result does not validate dataset or external-software tests,
consistent with the repository's test policy; those tests were not run. The
manual parser probe reproduced the invalid accepted tags described in Finding
1. I did not run a hosted GitHub Actions job, Trusted Publishing, or a real
PyPI/GitHub Release mutation.

The workflow's job ordering, explicit `contents: write` permission on the
release job, tag-source checkout, PyPI hash verification, exact two-artifact
check, surplus-asset deletion, and `--clobber` upload were inspected and did
not reveal another introduced defect. The existing unrelated working-tree
modification to `maintainer/roadmap.md` was preserved.

## Verdict

**Changes requested** — fix the tag grammar to enforce the documented release
forms and add the required `Unreleased` changelog entry. The independently
reproduced 12-target-test and 563-test claims are accurate, but those tests do
not cover the accepted malformed suffixes or the changelog requirement.
