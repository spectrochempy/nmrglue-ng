# Maintainer material

This directory contains maintainer-oriented material for **nmrglue-ng**.

- `audits/` is ignored local workspace for dated technical assessments. It is
  not versioned or shared; each maintainer may keep independent notes there.
- `roadmap.md` is the living development roadmap and should be updated as priorities and decisions evolve.

User documentation belongs under `doc/`. Contributor-facing instructions belong in `CONTRIBUTING.md`.

## Agent workflow

The versioned, tool-neutral agent workflow lives at the repository root:

- `AGENTS.md` — permanent rules and authorization limits. Read it first.
- `.agents/skills/nmrglue-ng-dev/` — development procedure (baseline, reproduction, minimal fix, targeted tests, corpus safety, report).
- `.agents/skills/nmrglue-ng-review/` — independent review by an independent session or agent.
- `.agents/skills/nmrglue-ng-release/` — release-readiness audit; never publishes.
- `opencode.json` — OpenCode discovery configuration for the shared skills.

Start from `AGENTS.md`, then load the relevant skill. `roadmap.md` is the
shared source of truth for priorities and decisions. Local files in `audits/`
may support a session but are not shared. `.opencode/rules.md` is only a
compatibility pointer; no tool-specific skill copies are kept.

The purpose of this directory is deliberately limited: preserve the technical reasoning behind maintenance decisions without creating a second documentation system.
