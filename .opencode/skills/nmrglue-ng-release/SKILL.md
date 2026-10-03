---
name: nmrglue-ng-release
description: "Audit nmrglue-ng release readiness without publishing. Use to check the P0 release gates, changelog completeness, version and artifact coherence, CI state, and the release-critical dataset rule, and produce a readiness report. Never tags, uploads, or publishes."
metadata:
  audience: maintainer
  workflow: release
---

## Trigger

Use this skill when asked whether `nmrglue-ng` is ready to release, or to
prepare a release-readiness report.

**This skill is an audit. Its default and normal output is a dry run.** It
does not create a tag, does not upload an artifact, and does not publish a
release — not even with a plausible justification. Those require a separate,
explicit maintainer authorization that this skill does not grant and does not
assume.

### Why this skill exists in its current form

The SpectroChemPy release skill assumes a mature release pipeline. `nmrglue-ng`
does not have one yet: there is no publication workflow in
`.github/workflows/` (only `ci.yml`), no versioned test-data manifest, no
checksum-verifying fetcher, and unresolved provenance questions on
release-critical data.

What *can* honestly be automated today is the **gate audit**: checking the
documented preconditions and reporting exactly which ones still block. So this
skill is a readiness auditor, not a release procedure. It is expected to
return "not ready" for as long as the P0 items below are open, and that result
is a success, not a failure.

If a future change makes the pipeline real (manifest, fetcher, dataset
validation, publication workflow), this skill should be extended then — not
guessed at now.

---

## Step 1 — P0 gates (evaluated first, and they gate everything)

A release cannot be declared ready while any of these is open. Check each one
against the repository, not against this document.

| # | Gate | Evidence to look for |
|---|---|---|
| G1 | **Provenance and redistribution rights** for the release-critical corpus | `maintainer/roadmap.md` P0 item; `maintainer/audits/2026-10-release-critical-dataset.md` § *Provenance and rights* |
| G2 | **Versioned manifest** with sizes and SHA-256 checksums | a tracked manifest file; roadmap P0 item |
| G3 | **Checksum-verifying test-data fetcher** | a script or documented command that downloads and verifies; roadmap P0 item |
| G4 | **Dataset validation** run and recorded | recorded result for the release-critical dataset profile |
| G5 | **Independent documentation** and a working documentation build | `doc/`, `.readthedocs.yml`, and an actual build/deployment record |
| G6 | **Version and artifact coherence** | version source, `CHANGELOG.md`, and any built artifact agree |

**Verdict lock:** if any of G1–G6 is open, set the final verdict to
**BLOCKED** and list the open gates with their evidence. Continue every
remaining step as a **read-only audit** so the report is complete: changelog,
version and artifacts, CI, additional blockers, and the validation record
still matter to the maintainer's next decision.

Do not proceed to a "probably fine" verdict, and do not create a tag or branch
to "start preparing". An open P0 gate can never be offset by a green CI run or
a complete changelog.

Never announce a release as ready while a P0 gate is blocking.

---

## Step 2 — Release-critical dataset rule

The dataset release rule is documented in
`maintainer/audits/2026-10-release-critical-dataset.md` (§ *Release rule*).
Verify each clause against a recorded result; do not restate the audit as if
it were a fresh validation.

A release may proceed only when the autonomous suite is green, all
release-critical groups are reproducibly available and checksum-verified, the
release-critical dataset tests pass against an immutable corpus, the inherited
release-critical defects are resolved, the Varian / low-memory blockers have an
explicit validated outcome, provenance is acceptable for every distributed
group, and the extended and NMRPipe differential profiles have recorded
outcomes.

Failures confined to the historical low-priority set do not block release. An
extended-profile failure blocks only if it reveals a defect in a capability
promoted into the release-critical contract — and that judgement belongs to
the maintainer, not to this skill.

---

## Step 3 — Changelog completeness

Read `CHANGELOG.md`:

* every entry since the last release is present under `Unreleased`;
* entries explain what changed and why it matters to a user or contributor;
* no implementation-journal entries (those belong in `maintainer/audits/`);
* no duplicate or near-duplicate entries for the same work;
* pull-request references `(#NNN)` identify pull requests, not issues.

Propose a consolidated entry when many small entries describe one outcome.
Do not invent user-facing claims for changes that have none.

---

## Step 4 — Version and artifact coherence

The version is dynamic:

```toml
# pyproject.toml
[tool.setuptools.dynamic]
version = {attr = "nmrglue.__version__"}
```

```bash
grep -n "__version__" nmrglue/__init__.py
git describe --tags
```

Check that:

* `nmrglue.__version__` states the intended next version, and that a
  development suffix (for example `-dev`) is either intentional and documented
  or removed deliberately;
* `CHANGELOG.md` and the version agree;
* `pyproject.toml` distribution name is `nmrglue-ng`, readme and license files
  resolve, and the package list covers the intended modules;
* `MANIFEST.in` still ships the fixtures the packaged tests need;
* a locally built artifact, if one was built for validation, reports the same
  name and version — and note that a local build is **not** the released
  artifact.

Before a tag exists, the SCM version and the target version legitimately
differ. Report both; never paper over the difference.

---

## Step 5 — CI and blockers

```bash
gh pr checks <PR> --json name,state
gh issue list --state open
gh pr list --state open
```

Check CI status once for the exact commit; do not poll in a loop.

Then list open blockers:

* failing tests on the target branch;
* open issues or pull requests that the roadmap marks as release blockers;
* inherited defects not yet reviewed;
* any uncommitted change in the working tree.

---

## Step 6 — Validate after the final commit is actually pushed

Release validation must be run against the **pushed** commit, not against a
local working state:

```bash
git fetch origin
git rev-parse origin/master        # or the release branch
git status --short                 # must be empty
python -m pytest -m "not dataset and not external_software"
```

Rules:

* run the self-contained profile and report exact counts;
* report every skip with its reason — a skip is not a pass;
* if a dataset or external-software profile is claimed, the dependency must
  actually have been present, and its version recorded;
* verify corpus integrity (for example a checksum before and after) whenever a
  dataset profile ran;
* a validation result obtained before the final commit was pushed is stale;
  re-run it or say that it is stale.

---

## Step 7 — Report

Produce a release-readiness report and nothing else:

```text
## Verdict
READY | NOT READY | BLOCKED

## P0 gates
G1..G6, each: open / met, with the evidence found

## Release-critical dataset
Clauses met, clauses open, and where each result is recorded

## Version and artifacts
Version source, current SCM version, target version, coherence notes

## Changelog
Entries present, consolidation proposed, references checked

## CI and blockers
CI state for the exact commit, open blockers

## Validation performed
Exact commands, exact counts, skips with reasons, corpus integrity

## Next steps
Ordered, concrete, and naming who must decide what
```

State the verdict from the gates. If any P0 gate is open, the verdict is
**BLOCKED** even after the later audit steps finish. Never soften "blocked"
into "nearly ready" to be agreeable, and never present a partially validated
state as a green one.

---

## Rules

* **Dry run / audit by default.** Report only.
* **No tag, no upload, no publication** without a separate explicit
  authorization. Do not create a `release/*` branch "to be ready".
* Do not install, upgrade, or publish anything in the user's environment.
* Do not modify `CHANGELOG.md`, version files, or packaging to make readiness
  checks pass. This skill reports; changes belong to a `chore/` or `REL:`
  task under `nmrglue-ng-dev`.
* Never declare a release ready while a P0 gate is blocking.
* If asked to go beyond an audit, say what authorization is missing and stop.
