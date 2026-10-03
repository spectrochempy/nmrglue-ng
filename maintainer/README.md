# Maintainer material

This directory contains maintainer-oriented material for **nmrglue-ng**.

- `audits/` contains dated technical assessments. Audits are historical snapshots: once committed, they should not be rewritten to reflect later project state. If a new assessment is needed, add a new dated audit.
- `roadmap.md` is the living development roadmap and should be updated as priorities and decisions evolve.

User documentation belongs under `doc/`. Contributor-facing instructions belong in `CONTRIBUTING.md`.

## Agent workflow

The versioned OpenCode workflow lives at the repository root:

- `AGENTS.md` — permanent rules and authorization limits. Read it first.
- `.opencode/skills/nmrglue-ng-dev/` — development procedure (baseline, reproduction, minimal fix, targeted tests, corpus safety, report).
- `.opencode/skills/nmrglue-ng-review/` — independent review in a fresh session.
- `.opencode/skills/nmrglue-ng-release/` — release-readiness audit; never publishes.

Start from `AGENTS.md`, then load the relevant skill. `roadmap.md` and the
dated files in `audits/` remain the source of truth for priorities and
decisions; the skills do not duplicate them.

The purpose of this directory is deliberately limited: preserve the technical reasoning behind maintenance decisions without creating a second documentation system.
