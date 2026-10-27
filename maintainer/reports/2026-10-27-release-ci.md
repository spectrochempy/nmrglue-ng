# Release CI audit and change — 2026-10-27

## Baseline

The audit started from `f82fc7f` on `chore/centralize-private-audits`. The
working tree already contained an unrelated modification to
`maintainer/roadmap.md`, which was preserved.

## Findings

Tags `v1.1.0`, `v1.1.1` and `v1.1.2` exist on `origin`, while the GitHub API
listed only the `v1.1.0` release in that series. `publish-pypi.yml` was
`workflow_dispatch`-only and required manually supplied `tag` and
`expected_version` values, so creating a release tag did not start publication
or GitHub Release synchronization.

## Decision

The PyPI workflow now starts on `v*` tag pushes. It derives the version from
the tag, validates the tag format and existence, validates the tagged source
and changelog, publishes to PyPI, and synchronizes the matching GitHub Release.
Manual dispatch remains for retries. No existing tag or release was modified by
this change.

The roadmap was updated with the new contract. The historical `1.1.x` GitHub
Release discrepancy still requires a separate, explicit maintainer repair.
