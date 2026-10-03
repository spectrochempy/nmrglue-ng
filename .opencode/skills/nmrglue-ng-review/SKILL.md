---
name: nmrglue-ng-review
description: "Independent review of an nmrglue-ng change in a fresh session. The reviewer starts from the need, the issue, the diff, and the sources, never from the implementer's history. Verifies scientific behavior, expected values, tolerances, units, tests actually run, skips, corpus integrity, and maintainer documents, then gives a normalized verdict."
metadata:
  audience: maintainer
  workflow: review
---

## Trigger

Use this skill when asked to perform a **separate review** of an nmrglue-ng
implementation.

This review runs in a **new OpenCode session, or by another agent**, without
the implementation history. If you participated in writing the code, you are
the implementer, not the reviewer — say so and decline.

Do not use this skill for trivial changes (typos, formatting, mechanical
refactoring with no behavior change). Those are covered by the implementer's
self-verification.

---

## Context

The reviewer works from:

1. **The original need** — the problem statement, issue, or handoff prompt.
2. **Applicable instructions** — `AGENTS.md`, `CONTRIBUTING.md`, and only the
   relevant sections of `nmrglue-ng-dev` (read the sections you need, not the
   whole skill).
3. **The diff** — the exact commit or branch range.
4. **Relevant sources** — implementation code, tests, and maintainer
   documents.

The implementer's report is **information to verify, not authority**. Trust the
code, the tests, and the data — not the summary. A claim in the report that is
not verifiable from the repository is an open question, not a fact.

---

## Inputs

Expected from the implementer:

* need / requirement;
* branch name or PR number;
* base commit and commit to examine;
* sensitive points flagged by the implementer.

**Do not ask for missing elements.** Find them first:

```bash
gh pr view <PR>                 # need, description, checklist
gh issue view <issue>           # original problem statement
git log --oneline <base>..<head>
git diff <base>..<head>
```

If the branch has moved since the handoff, resolve the exact target commit
yourself and state it in the report.

---

## Procedure

### 1. Establish the diff

```bash
git diff <base>..<commit>
gh pr diff <PR_NUMBER>
```

Confirm the base and the commit match what was requested. If they do not,
stop and report: the review targets a specific commit.

Read the full diff before reading anything else.

### 2. Reconstruct the need

Restate the requirement in your own words. Identify:

* what problem is being solved;
* what behavior should change;
* what behavior must be preserved.

Then check the diff actually solves *that* problem, and nothing else. Scope
creep is a finding.

### 3. Verify the scientific behavior

This is the part a general-purpose reviewer is most likely to get wrong. For
any change touching frequencies, spectral widths, axes, point/Hz/ppm
conversion, carrier/reference/observation frequencies, quadrature, complex
data, endianness, dimensions, axis ordering, instrumental metadata, or a file
format, verify explicitly:

| Check | Question |
|---|---|
| **Expected values** | Where does each expected number come from? Is the source a specification, vendor behavior, a real file, a publication, or NMRPipe? |
| **Units** | Is every value in the unit the code assumes? Points vs Hz vs ppm; Hz vs kHz; Hz^-1 vs ppm^-1. |
| **Tolerances** | Is `atol`/`rtol`/`places` tight enough to catch a real regression, and loose enough not to be flaky across platforms? |
| **Signs and conventions** | Frequency sign, mirror-image (`ps90-180`-style) conventions, reference direction, phasing. |
| **Endianness and dtype** | Integer vs float widths, byte order, `float32` vs `float64`. |
| **Provenance of a changed expectation** | If a test value changed, the justification must be independent of the code under test. A value adjusted to match new output is a defect, not a fix. |

When the change makes a scientific claim or changes a scientific value,
recompute at least one key expected value yourself, by hand or with an
independent calculation. Do not accept a number because the code produced it.
For a non-scientific change, state why no scientific value needs independent
recomputation.

### 4. Verify the tests were really run

The implementer's report claims certain tests passed. Verify independently:

```bash
python -m pytest -m "not dataset and not external_software" <targeted paths>
```

Then audit the report against reality:

* **Which profile was run?** The self-contained profile does not cover
  dataset or external-software tests.
* **Were tests skipped?** A `skipped` test is **not** a validated test. List
  every skip with its reason and state that the behavior it covers is
  unverified. `xfail`/`strict xfail` entries deserve the same scrutiny.
* **Were external dependencies present?** A `dataset` test that "passed"
  because the dataset was absent did not pass. A `external_software` test
  that "passed" without NMRPipe did not pass.
* **Is the failing-before test real?** For a bug fix, confirm the added test
  actually fails without the fix and passes with it. If that was not
  demonstrated, say so.
* **Is coverage honest?** Does the new test exercise the changed code path,
  or only a neighboring one?

### 5. Verify corpus and data integrity

* Does anything in the diff write to, create, or delete a file in the canonical
  corpus? That is a blocker.
* Are temporary files confined to `tmp_path` or a properly created temporary
  directory?
* Are the three data categories kept distinct — versioned fixture, local
  corpus, external reference?
* Is any new data being versioned or republished without established
  provenance and redistribution rights?
* If dataset-dependent tests ran, is there evidence the corpus was unchanged
  (before/after checksum)?

### 6. Verify maintainer documents

* Does the change touch `maintainer/roadmap.md`, a dated
  `maintainer/audits/` entry, or `CHANGELOG.md` `Unreleased`?
* Is a `CHANGELOG.md` entry required? For user- or developer-visible changes:
  yes. If the PR claims `Changelog: not required`, judge whether the reason
  holds.
* Are audits treated as historical snapshots rather than rewritten?
* Is the change free of several independent defects in one PR?

### 7. Search for counter-examples

For each behavioral change, try to break it:

* edge cases — empty arrays, single element, negative values, NaN, infinity,
  zero-length axes, one-dimensional masquerading as multi-dimensional;
* type and layout variations — dtype, byte order, axis order, non-monotonic
  axes;
* interactions with existing features that are not explicitly tested;
* behavior when the optional dependency, the dataset, or the external
  software is absent.

Report any reproducible counter-example with the exact input and the
expected versus actual behavior.

### 8. Assess regression risk and upstream portability

* Does the change alter a code path used by other features?
* Is backward compatibility preserved (public API, file formats, expected
  values)?
* Is the fix generic, or does it special-case one dataset, one file name, or
  one caller?
* Would it be acceptable upstream (`jjhelmus/nmrglue`) on its own? If the
  change carries `nmrglue-ng`-specific packaging, governance, or test
  infrastructure into a fix, that is a scope problem.
* Does the change propose, prepare, or imply an upstream contribution while
  PRs #279–#282 remain unanswered?

---

## Deliverable

Produce a review report with this structure.

### Summary

One or two sentences: what the change does relative to the stated need.

### Findings

For each finding:

* **Location** — file and line.
* **Defect** — what is wrong or at risk.
* **Consequence** — what happens if it is not addressed.
* **Evidence** — the input, test, code path, or recomputation that shows it.

Classify every finding as exactly one of:

| Category | Meaning |
|---|---|
| **Introduced by this change** | The change is wrong, or breaks something that worked before. |
| **Pre-existing** | Already wrong before this change; not a reason to block, but must not be silently absorbed. |
| **Out of scope** | A real observation unrelated to the stated need; report it, do not expand the PR for it. |

Keeping these three apart is mandatory: conflating them either blocks a good
change or hides a real one.

### Validation

State what you ran yourself, with exact commands and counts. List the skips
you observed. List the targeted commands that would confirm or refute each
key concern.

### Verdict

Exactly one of:

* **Ready to merge** — no introduced defect; scientific claims verified
  independently; tests genuinely run and reported honestly; corpus untouched.
* **Changes requested** — at least one introduced defect must be fixed.
  List them.
* **Blocker / maintainer decision required** — the change needs a maintainer
  judgment (scientific convention, compatibility trade-off, release-critical
  data, upstream strategy) that a reviewer must not decide alone.

---

## Rules

* **Do not modify code or documentation.** Do not fix, do not commit, do not
  push, do not open a PR. This is a review. Report what is wrong and stop.
  If a fix seems obvious, describe it; do not apply it.
* **Trust code, tests, and data**, not the implementer's summary.
* **Distinguish facts from judgments** — an introduced defect is a fact you can
  demonstrate; a design preference is not a blocker.
* **Do not launch another session or another model.** Produce the report and
  stop.
* If you cannot verify a claim, record it as an open question rather than
  assuming the implementer is right.

---

## Completion criteria

The review is complete when:

* the full diff has been read;
* the need has been reconstructed independently;
* every scientific claim has been checked against its stated source, with at
  least one value recomputed when the change makes such a claim;
* the tests actually run are identified, and every skip is listed;
* corpus integrity and maintainer documents have been checked;
* each finding is classified as introduced, pre-existing, or out of scope;
* the verdict follows from the findings.
