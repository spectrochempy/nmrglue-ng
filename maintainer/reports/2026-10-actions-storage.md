# GitHub Actions storage audit — October 2026

Date: **2026-10-13**. Baseline: `a7315a7` on `master`.
Scope: `spectrochempy/nmrglue-ng` only; the historical upstream
`jjhelmus/nmrglue` was not inspected or modified.

## Summary

The dominant Actions storage cost was routine retention of built distributions.
The GitHub API reported 748 active workflow artifacts totaling 4,463,825,071
bytes. Of that total, `distribution-py3.13` accounted for 4,413,208,834 bytes
across 84 artifacts. JUnit reports accounted for about 3 MB, and one manual
release dry-run artifact accounted for 47,533,001 bytes.

The repository also had 70 pip cache entries totaling 3,943,026,290 bytes.
Cache storage has a separate repository allowance from Actions artifacts and was
below GitHub's documented 10 GB cache limit. No cache deletion was performed.

Organization billing data was not accessible with the available token: the old
billing endpoint returned HTTP 410 and required `admin:org` for the replacement.
The measured artifact inventory therefore must not be presented as the exact
organization billing total.

## Current validation contract

The CI workflow keeps four validation profiles:

- autonomous self-contained tests on Linux Python 3.10-3.14 and Windows/macOS
  Python 3.14;
- CSDM conversion tests with `csdmpy` on Linux Python 3.13;
- distribution validation on Linux Python 3.13, building an sdist and wheel,
  checking metadata, testing infrastructure from the extracted sdist, installing
  the wheel in a fresh environment, and executing 65 packaged functional cases;
- pre-commit checks on Linux Python 3.13.

These profiles do not validate the external corpus or executable NMRPipe
comparisons. The marker and dataset policy in `CONTRIBUTING.md`,
`AGENTS.md`, and `maintainer/testdata-policy.md` remains unchanged.

## Decision

Maintainer decision on 2026-10-13: the built distribution artifacts retained by
routine CI and by the manual release dry-run workflow are not needed for the
current review process. The workflows should still build and validate the same
files, but they should no longer retain those distributions as GitHub Actions
artifacts.

The CI packaging job may keep only its JUnit reports so failed or incomplete
validation remains diagnosable. The manual release dry-run workflow should not
upload workflow artifacts; official release files belong in an explicitly
authorized GitHub Release or publication workflow.

## Expected storage effect

Removing `dist/*` from routine CI artifact upload eliminates the source of about
4.41 GB in the observed active-artifact inventory. Removing the manual release
dry-run upload avoids the 47.5 MB temporary release artifact. Existing artifacts
expire according to their original retention; this report does not authorize or
perform manual deletion.

This is a storage optimization only. It does not remove tests, reduce matrices,
change markers, change assertions or tolerances, alter expected values, or
change release-critical dataset policy.

## Follow-up

- Reconcile repository artifact inventory with organization billing from an
  account that has billing access.
- Consider shorter report retention separately if reports become a material
  storage concern; they were not material in this audit.
- Do not add `paths` filters without first checking required-check behavior, to
  avoid leaving pull requests blocked by skipped required checks.
