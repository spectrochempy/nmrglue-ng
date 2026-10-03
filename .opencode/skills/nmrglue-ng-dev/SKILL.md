---
name: nmrglue-ng-dev
description: "Develop, fix, or refactor nmrglue-ng. Use for any change to nmrglue sources, tests, packaging, or documentation: repository discovery, baseline check, reproduction, minimal generic fix, targeted tests, corpus safety, maintainer notes, and report. Handles branch, commit, push, and PR authorization."
metadata:
  audience: maintainer
  workflow: development
---

## Trigger

Use this skill when modifying source code, tests, packaging, or documentation
in `nmrglue-ng`.

Read `AGENTS.md` and `CONTRIBUTING.md` at the start of each session. When
rules overlap, follow the stricter requirement.

This skill is the procedure behind `AGENTS.md`. `AGENTS.md` states the
permanent rules; this skill states the steps.

---

## Authorization Levels

Identify which level applies before acting, and never exceed it.

| Level | Allows |
|---|---|
| **Analyze** | Read, search, audit, report. No file modification. |
| **Fix** | Modify source, tests, and docs, then validate them. No Git write operations. |
| **Deliver** | *Only on explicit request:* create a branch, commit, push, open a PR. |

Always requires a **separate, explicit** authorization, never implied by
"Fix":

* merge a pull request;
* create or push a tag;
* upload or publish an artifact or release;
* open an upstream issue or pull request;
* install or upgrade dependencies in the user's primary environment.

Analyze never modifies. Fix modifies and validates. Commit, push, and PR
creation happen only when asked.

---

## Step 1 — Discover the repository

Do not assume any path. The clone location is not a stable historical fact.

```bash
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git remote -v
```

Confirm this is the `nmrglue-ng` project (distribution `nmrglue-ng`, import
`nmrglue`) and not the upstream `jjhelmus/nmrglue` clone. Do not create a new
worktree unless explicitly asked; work in the existing clone.

Read, in this order:

1. `AGENTS.md`
2. `CONTRIBUTING.md`
3. the relevant `maintainer/` document (`roadmap.md`, or a dated
   `maintainer/audits/` entry for the topic)
4. `.opencode/skills/` — only the sections you need

---

## Step 2 — Establish and announce the baseline

```bash
git fetch origin
git status --short --untracked-files=all
git log --oneline -5
```

Announce the baseline before the first edit:

```text
repo:    <path>
branch:  <branch>
commit:  <short sha> (<subject>)
state:   clean | <list of pre-existing local changes>
```

**Preserve local modifications.** Untracked files, unstaged edits, and
uncommitted work that is not part of the task must survive untouched. Never
run `git checkout -- .`, `git restore .`, `git stash`, `git clean`, or any
command that discards work. If a pre-existing local change conflicts with the
task, report it and stop.

Branch from an updated `master`:

```bash
git fetch origin
git switch master
git merge --ff-only origin/master
git switch -c <type>/<short-topic>
```

Use a dedicated branch for every task. Conventional prefixes: `fix/`, `feat/`,
`test/`, `docs/`, `chore/`, `refactor/`, `perf/`. Never reuse an unrelated
existing branch. Never mix two independent defects in one branch. If switching
to `master` would overwrite a pre-existing local modification, stop and report
the conflict; never discard or stash it to make the sequence succeed.

---

## Step 3 — Audit and reproduce before modifying

Reproduce the defect first. A fix applied without a reproduction cannot be
shown to work and cannot be shown to be needed.

1. Locate the defect site (`rg` for the symbol, error text, or marker).
2. Read the surrounding code and its existing tests.
3. Build the smallest reproducer that fails on the current code.
4. Record: the exact command, the observed output, and the expected output.
5. If the defect cannot be reproduced, **stop and report**. Do not guess-fix.

Search for a minimal and generic fix:

* Is the defect one symptom of a single wrong assumption?
* Is an existing helper or utility already doing this correctly?
* Would the fix change behavior outside the reported symptom?
* Would the same fix be acceptable upstream (generic, no `nmrglue-ng`-specific
  dependency)?

Reject a fix that special-cases one dataset, one file name, or one caller
when a general correction exists.

---

## Step 4 — Implement the minimal fix

* Smallest change that resolves the reproduced defect.
* Follow existing patterns; prefer existing helpers over new ones.
* Add no dependency and no new public API without explicit approval.
* Add no comments unless asked.
* Never change an expected test value to make a test pass. If an expected
  value must change, first justify the new value from a format
  specification, vendor behavior, a real file, a publication, or NMRPipe.
* Preserve the distribution name `nmrglue-ng` and the public import `nmrglue`.
* Preserve upstream attribution: keep authorship, reference the original
  issue or PR, and never present existing work as new.

### Writer changes

Add a round-trip test (`read -> write -> read`) when reasonably possible.

### Corpus safety — mandatory

**A test must never write to the canonical corpus.** Any test that writes must
copy to a temporary location first and read and write only the copy:

```python
def test_something(tmp_path):
    work = tmp_path / "dataset"
    shutil.copytree(SOURCE, work)
    # all reads and writes target `work`
```

Corollary rules:

* no test may create, delete, or overwrite a file under the corpus;
* any `tempfile` intermediate directory must live under `tmp_path`, or under a
  directory created with `mktemp -d` (create `/tmp/opencode` first if you use
  it);
* if a test is discovered to mutate the corpus, that is a defect in its own
  right — report it rather than silently working around it.

---

## Step 5 — Validate with the smallest sufficient scope

Know which category each test belongs to before reporting a result:

| Profile | Marker | Requires |
|---|---|---|
| Self-contained (CI) | `-m "not dataset and not external_software"` | nothing external |
| Dataset | `-m dataset` | external `data/` directory |
| External software | `-m external_software` | NMRPipe, `/bin/csh` |
| Optional dependency | `-m optional_dependency` | optional package |

```bash
# self-contained profile (matches CI)
python -m pytest -m "not dataset and not external_software"

# focused file
python -m pytest nmrglue/fileio/tests/test_pipe.py
python -m pytest tests/test_peakpick.py

# single test
python -m pytest tests/test_x.py::test_y -v

# dataset profile (only when data/ is present)
python -m pytest -m dataset

# external software (only when nmrPipe is available)
python -m pytest -m external_software
```

Run the smallest scope that proves the claim, then widen only as far as the
change requires. Do not run the full suite unless the task needs it.

Reporting rules — these are correctness requirements, not style:

* Report the exact command, the exact counts, and the exit status.
* **A `skipped` test is not a validated test.** Report each skip with its
  reason and state plainly that the behavior it covers is unverified.
* A missing dataset is *not* a product failure. Say so explicitly.
* State which profile you ran. Never let a reader assume the self-contained
  profile covers the whole suite.
* If external software was used, name it and its version (for example
  NMRPipe 13.0).
* Record corpus integrity when a dataset-dependent test ran (for example a
  SHA-256 check before and after) to prove the run mutated nothing.

---

## Step 6 — Repository checks

```bash
git diff --check
git status --short --untracked-files=all
```

`git diff --check` must be silent (no whitespace errors, no conflict
markers).

This project has no linter or formatter in the standard loop; do not introduce
one as a side effect. If a `.codespellrc` exists, respect it when editing
prose.

If the change touched Markdown or reStructuredText, re-read the rendered
structure: heading levels, table syntax, list indentation, code fences closed.

---

## Step 7 — Maintainer notes and changelog

Update the relevant maintainer document when the task produces a decision or
durable knowledge that must outlive it:

* `maintainer/roadmap.md` — priorities and status changed;
* a new dated `maintainer/audits/` file — a substantive assessment;
* prefer editing an existing document over creating a new one;
* audits are historical snapshots: never rewrite one to reflect a later
  state, add a new dated file instead.

`CHANGELOG.md` `Unreleased` must be updated for every user- or
developer-visible change, referencing the pull request number as `(#NNN)`.
Purely internal tooling may instead state `Changelog: not required` with a
brief reason in the PR description.

---

## Step 8 — Upstream opportunity assessment

Assess whether the fix is generic enough to be proposed upstream, and report
the answer explicitly — do not act on it:

* **Portable** — minimal, generic, reproducible in the upstream repository
  alone, no `nmrglue-ng`-specific dependency, compatible with upstream API and
  scope.
* **Not portable** — depends on `nmrglue-ng` packaging, governance, branding,
  test infrastructure, or roadmap choices.

Even when portable: **do not open an upstream issue or pull request, and do
not prepare an upstream branch or commit.** Additional upstream contributions
are paused until PRs #279–#282 receive significant maintainer feedback. Any
future portage must restart from the then-current `jjhelmus/nmrglue:master`.
See `maintainer/roadmap.md`.

---

## Self-verification (implementation side)

Before reporting completion, verify your own diff. **This is not an
independent review.**

1. **Conformance** — does the change satisfy the stated need? Any scope creep?
2. **Consistency** — are code, tests, and documentation coherent? Do test
   names and docstrings describe the actual behavior?
3. **Obvious errors** — typos, wrong names, off-by-one, bad imports, dead
   code, leftover debug statements.
4. **Behavior preservation** — is existing public behavior preserved? Any
   unintended side effect?
5. **Corpus integrity** — is the canonical corpus unchanged?

Fix anything found before reporting.

---

## Report format

Report exactly this structure:

```text
## Baseline
repo / branch / commit / pre-existing local state

## Problem
Observed behavior, expected behavior, exact reproducer command

## Change
Files changed, one line each, and why

## Validation
Exact commands, exact counts, exit status, skips with reasons,
which profile was run, corpus integrity result

## Maintainer notes
Documents updated

## Upstream
Portable / not portable + one-line justification, or "no upstream candidate"

## Limitations
Anything not verified, and what would be needed to verify it

## Next step
What is staged and awaiting authorization (branch / commit / push / PR),
or the handoff prompt for a separate review
```

Never claim a check passed that was not run. Never report a skip as a pass.

---

## Handoff to separate review

When a separate review is required (see `AGENTS.md`), do **not** launch
another session or model. Produce a short prompt usable as-is in a new
OpenCode session, containing:

1. **Need** — the original problem statement.
2. **Branch / commit** — branch name and commit to examine.
3. **Base** — the exact base commit, so the reviewer can run
   `git diff <base>..<commit>`.
4. **Sensitive points** — the specific areas you flag for attention.

The implementer's report is information to verify, not authority.

---

## When commit, push, and PR are requested

Only on explicit request, and only for the files of this task:

```bash
git add <files>                 # stage explicitly; never `git add -A`
git diff --cached --check
git status --short
```

Stage explicitly. `git add -A` can capture unrelated local work and pre-existing
untracked files.

Then:

```bash
git commit -m "<prefix>: <summary>"
git push origin <branch>
gh pr create --base master --head <branch> ...
```

Open the PR against `spectrochempy/nmrglue-ng:master`, from `origin`, never
from a fork of the maintainer's choosing and never against the upstream
repository. **Stop after the PR is opened.** Do not merge, tag, or release.
