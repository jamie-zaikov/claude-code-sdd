# Requirements: non-code-feature-track

<!-- This file is owned by the requirements-agent. Do not edit manually during SDD workflow. -->
<!-- Attempt 2 (restart). Attempt 1 retired 2026-08-09; see "Provenance" below. -->

## Overview

The SDD pipeline currently hard-assumes that every feature ships application code plus unit
tests. A feature whose output is a recon/investigation write-up, documentation, or a
knowledge-vault update therefore FAILs validation ("tests missing"), leaves both reviewers with
an empty or docs-only diff and no defined verdict, and so never reaches the whole-feature review
PASS that is the *only* condition under which `ready-to-merge` is applied. The PR then sits on a
permanently failing `sdd-review-gate`, and the only escape is hand-adding the label — precisely
the audit bypass the gate exists to prevent.

This feature adds a **first-class non-code track**: the orchestrator explicitly classifies a
feature as code-bearing or non-code and records the classification in `.spec-state.json`; the
task-tester and task-validator switch to artifact-conformance behaviour when a task produces no
application code; and both reviewers gain a defined, emittable verdict for empty or non-code
scope, with the review re-pointed at the spec artifacts, the committed documentation, and the
vault changelog. The track terminates in a **real** reviewer PASS flowing through the existing
single application point — it never bypasses, weakens, or shortcuts the gate. All changes are to
agent definitions (markdown contracts), tests under `tests/`, and documentation, **all of them
inside this repository**; the corresponding copies under `~/.claude/` are synchronised after
merge by the operator running `./install.sh` (FR-12.1, NFR-10). No CI change.

This is a change to the SDD framework source repository itself. The feature being specified
governs how the pipeline handles non-code (including vault-update) features in **consumer**
projects; this repository has no knowledge vault of its own (`.specs/steering/tech.md`), so no
vault-reader/vault-writer routing applies to the work itself.

## Provenance: what attempt 2 changes, and what it keeps

*(Non-normative. Kept short deliberately — steering rule 6: an amendment's outcome is folded into
the base text, and only a changelog remains.)*

Attempt 1 ran 4 of 11 tasks and was retired on 2026-08-09 (revert `41880b7`, PR #7). Its
`requirements.md` is preserved verbatim at
`.specs/features/non-code-feature-track/spec-memory/retired-attempt1-requirements.md`.

**Re-derived figures for the retired document** *(counting convention: lines as numbered by a
sequential read of the file; a requirement ID is a heading line matching `^#{1,6} ` that contains
an `FR-`/`NFR-` token, deduplicated)*:

| Figure | Value re-derived here | Expected on any re-derivation |
|---|---|---|
| Lines in the retired `requirements.md` | 760 | 760 — matches the restart brief |
| Requirement IDs (heading definition sites) | 88 | 88 = 77 `FR-*` + 11 `NFR-*`, `FR-1..FR-13` and `NFR-1..NFR-11` with no gaps |
| Bytes | **not re-derived** | brief states 42074; this agent has no shell, so `wc -c` could not be run. Treat 42074 as *unverified here*. |

**Changes attempt 2 makes to the retired requirement set:**

1. **FR-6.4 is rewritten in place** around a fenced, complete attribution rule (`AT-1`..`AT-6`).
   Attempt 1's FR-6.4 named "attributable to the feature's tasks" without saying what attributes,
   and design spent five amendments and four audits failing to say it. Locked decision **O5** puts
   all five evidence signals in play and moves the decision here. The ID is retained; only the
   text changes.
2. **FR-9.1 is rewritten in place** to pin the *property* rather than the vocabulary, after the
   token-free bypass family (postmortem §3.6): four probes defeated the gate without ever naming
   the `ready-to-merge` label and left the whole suite green. *(Postmortem §3.6 records that suite
   as 367 tests. That figure is historical — it will not re-derive on today's tree, because the
   retired attempt's tests were reverted with it. Do not treat a different count as a regression.)*
3. **Four new sub-requirements under retained parents:** FR-3.5, FR-3.6, FR-6.9, FR-6.10, FR-11.9.
   These extend a retained parent's numbering above attempt 1's highest sub-ordinal, so nothing is
   renumbered and no external citation moves.
4. **Four new top-level requirements** FR-14..FR-17 and three new NFRs NFR-12..NFR-14, per the
   restart brief's rule that genuinely new requirements start at FR-14 / NFR-12.
5. **Amendments A1 and A2 are folded into FR-11.8's base text.** Their narrative survives only as
   this changelog line. No constraint they imposed is dropped.
6. **Nothing is deleted and nothing is renumbered.** Zero attempt-1 IDs are superseded or
   absorbed. *(Expected on re-derivation: the ID register at the end of this document lists all 88
   attempt-1 IDs as `carried`, none as `superseded` or `absorbed`.)*

Attempt 1's three disclosed-not-closed residuals (postmortem §3.3) are **all closed** by FR-6.4's
rule; the argument is Appendix A, and the one new bounded residual it leaves is Appendix A §A.5.

## Definitions used throughout

These terms are load-bearing; every requirement below uses them as defined here.

- **Non-code artifact** — exactly one of:
  1. a spec artifact under `.specs/features/<feature-name>/` (`requirements.md`, `design.md`,
     `tasks.md`, `scope.md`, `.spec-state.json`);
  2. a committed prose/documentation file (e.g. a markdown write-up under a documentation
     directory or the feature's own directory) that the project's layout or steering does **not**
     designate as source, agent/prompt contract, template, script, or configuration;
  3. a knowledge-vault mutation recorded by `vault-writer` in
     `.specs/features/<feature-name>/vault/.write-log.jsonl`.
- **Application code** — any produced or changed file that is not a non-code artifact: executable
  source, tests, scripts, hooks, CI workflows, templates, runtime configuration, and any prose
  file the project designates as a behaviour-bearing contract (in this repository, for example,
  `agents/*.md` and `commands/*.md`).
- **Non-code feature** — a feature every one of whose tasks declares only non-code artifacts as
  its outputs.
- **`featureClass`** — the classification value recorded in `.spec-state.json`; one of `"code"`
  or `"non-code"`.
- **Non-code review scope** — the artifact set a reviewer reviews when the git diff is empty or
  contains only non-code artifacts (defined normatively in FR-6).
- **Plan set** — the tracked artifacts `/sdd-feature` scaffolds, plus the scratch-pattern block it
  appends to the repository-root `.gitignore`. Enumerated normatively in FR-6.4 `AT-2(a)` and
  pinned against `/sdd-feature` by FR-14. *(Re-derived from `commands/sdd-feature.md` for this
  document: it creates seven artifacts — `.spec-state.json`, `scope.md`, `requirements.md`,
  `design.md`, `tasks.md`, `input-data/README.md`, `spec-memory/README.md` — of which
  `.spec-state.json` is untracked because `.gitignore:7` carries `**/.spec-state.json`, leaving
  **six tracked** scaffold files; and it appends four scratch patterns plus a comment line to the
  repository-root `.gitignore`. **Expected on re-derivation: 7 created, 6 tracked, 1 modified
  file.** Counting convention: `###`-level path headings in `commands/sdd-feature.md`, minus those
  matched by a pattern in the repository-root `.gitignore`.)*
- **Implementation-task commit** — a commit on the feature branch created by github-agent under
  the orchestrator's per-task `commit-push` action for a numbered task in `tasks.md`
  (`agents/orchestrator.md`, lifecycle row "Per-task pipeline pass"), identified by the task
  marker FR-15 requires in its message. Planning-phase `commit-push` actions (requirements,
  design, tasks confirmation) are **not** implementation-task commits.
- **Produced output** — the artifact set that discharges FR-6.4's emptiness test, determined
  solely by the attribution rule fenced in FR-6.4. No other definition of "the feature's tasks
  produced this" is normative anywhere in this feature.

Each requirement is annotated with its `scope.md` driver: problem-statement items **P1**
(validator tests-required), **P2** (reviewers' undefined verdict on empty/non-code scope), **P3**
(single `ready-to-merge` application point / CI deadlock); resolved questions **O1–O5**;
reconciled discrepancies **D1–D2**. Requirements that exist because of a postmortem finding cite
it as **§n.n** of `.specs/retrospectives/non-code-feature-track.md`.

## Functional Requirements

### Feature classification (orchestrator)

#### FR-1: The orchestrator explicitly classifies every feature

*(drivers: O1, D1, D2)*

**When** the task list is confirmed and before implementation begins, **the system shall** have
the orchestrator classify the feature as code-bearing or non-code and record the classification
in `.spec-state.json`.

##### FR-1.1
**The system shall** record the classification in `.spec-state.json` under the key `featureClass`
with the value `"code"` or `"non-code"`, and shall specify that key and its two permitted values
in the orchestrator's state-file schema.

##### FR-1.2
**The system shall** derive the classification from the outputs the confirmed tasks in `tasks.md`
declare they will produce — never from whether the git diff happens to be empty (D1).

##### FR-1.3
**The system shall** classify a feature `"non-code"` only when **every** task's declared outputs
fall entirely within the non-code artifact set defined above; if any task declares application
code, the feature is `"code"`.

##### FR-1.4
**If** the classification is ambiguous or cannot be determined from `tasks.md`, **then the system
shall** classify the feature `"code"` (the fail-safe direction, which preserves today's behaviour
exactly) rather than guessing `"non-code"`.

##### FR-1.5
**When** the orchestrator records the classification, **the system shall** report to the user the
value recorded and the basis for it (which tasks' declared outputs drove it), and shall record
that basis in `.spec-state.json` alongside `featureClass`.

##### FR-1.6
**Where** the user overrides the classification, **the system shall** always honour an override
toward `"code"`, and shall honour an override toward `"non-code"` only when FR-1.3 already holds
for the confirmed tasks; an override is recorded in `.spec-state.json`.

##### FR-1.7
**If** `featureClass` is absent from an existing state file (a feature started before this
change), **then the system shall** treat the feature as `"code"` and proceed on the unchanged
code path.

#### FR-2: The orchestrator routes the pipeline on the classification

*(drivers: O1, P1, P2)*

**When** the orchestrator invokes the task-tester, task-validator, code-reviewer, or
security-reviewer, **the system shall** pass the current `featureClass` value and, for a task
stage, whether the task's declared outputs contain application code.

##### FR-2.1
**Where** `featureClass` is `"non-code"` and the current task produces no application code, **the
system shall** instruct the task-validator to run in artifact-conformance mode (FR-5) and the
task-tester to apply its defined no-code behaviour (FR-4).

##### FR-2.2
**When** the Feature Review Gate runs for a `"non-code"` feature, **the system shall** invoke both
reviewers in `feature` mode with the non-code review scope instruction (FR-6), keeping the
existing concurrent, opus-pinned invocation unchanged.

##### FR-2.3
**Where** `featureClass` is `"code"`, **the system shall** run the existing five-stage pipeline and
Feature Review Gate with no behavioural change whatsoever.

##### FR-2.4
**The system shall** keep the stage order unchanged for both classes: execute → test → validate →
code review → security review, with the reviews running only after validation passes.

#### FR-3: Fallback to the full code path when code appears

*(drivers: D2; §3.4 — the C4 divergence)*

**If** a task in a feature classified `"non-code"` produces or modifies application code, **then
the system shall** reclassify the feature as `"code"` and apply the full code path — tests
required — rather than retaining any exemption.

##### FR-3.1
**When** reclassification occurs, **the system shall** update `featureClass` to `"code"` in
`.spec-state.json`, record the triggering file path(s) and the task number, and report the
reclassification to the user.

##### FR-3.2
**When** reclassification occurs, **the system shall** re-run the current task's test and
validation stages under the code path before the task may be marked complete.

##### FR-3.3
**The system shall** record in `.spec-state.json` which tasks were validated under the non-code
exemption, and **when** a feature is reclassified, **the system shall** require the whole-feature
review to cover those tasks' outputs under the code path.

##### FR-3.4
**The system shall** make reclassification monotonic: once a feature is `"code"`, it shall never
be reclassified back to `"non-code"` for the remainder of that feature.

##### FR-3.5 *(new in attempt 2)*

*(driver: §3.4 — the shipped arming predicate was better than design C4, and nothing pinned it)*

**The system shall** state the reclassification triggers with an explicit **arming predicate**, in
this form, replicated verbatim wherever the triggers are written:

```
Triggers. Any one of the following, arising during the per-task pipeline of a
feature whose recorded `featureClass` is `"non-code"`:
```

##### FR-3.6 *(new in attempt 2)*

*(drivers: D2; §3.3 Residual 2)*

**The system shall** scope the reclassification triggers to files a **task** produced or modified;
a change made by `/sdd-feature`'s scaffolding — including its append to the repository-root
`.gitignore` — **shall not** trigger reclassification and **shall not** affect FR-1's
classification, because no task produced it.

### task-tester: defined behaviour when there is nothing to unit-test

#### FR-4: Defined no-code tester behaviour

*(drivers: O1, P1)*

**When** the task-tester is invoked for a task that produces no application code, **the system
shall** define in `agents/task-tester.md` exactly what the tester does, instead of leaving the
outcome undefined.

##### FR-4.1
**The system shall** prohibit the tester from writing vacuous or placeholder tests (assertions
that cannot fail, tests asserting only that a file exists when the requirement is about its
content) solely to satisfy the tests-exist expectation.

##### FR-4.2
**Where** a produced non-code artifact is machine-checkable (for example a structural or content
lint over a markdown contract, a schema check, or a link check), **the system shall** have the
tester write such a check in the project's conventional test directory, following the project's
existing test patterns.

##### FR-4.3
**If** no meaningful machine check is feasible for the task's artifacts, **then the system shall**
have the tester emit a defined "no applicable tests" completion block that names each produced
artifact, cites the requirement each satisfies, and states why no automated check is feasible —
an explicit, auditable outcome rather than an empty or improvised summary.

##### FR-4.4
**The system shall** require the tester, in all cases, to run the project's existing tests in the
affected area and report regressions, exactly as it does today.

##### FR-4.5
**If** the tester finds that the task in fact produced application code, **then the system shall**
have it report that fact to the orchestrator (triggering FR-3) and write tests for that code
normally, rather than applying the no-code behaviour.

### task-validator: artifact-conformance mode

#### FR-5: Artifact-conformance validation mode

*(drivers: P1, O1, D2)*

**Where** the orchestrator instructs the task-validator that the task produces no application
code, **the system shall** have the validator run in artifact-conformance mode, validating the
produced artifacts against the cited requirements.

##### FR-5.1
**The system shall** define artifact-conformance mode explicitly in `agents/task-validator.md`,
named and entered only on the orchestrator's instruction — never self-selected by the validator
because a diff looked empty.

##### FR-5.2
**When** in artifact-conformance mode, **the system shall** require the validator to map every
cited requirement to at least one named produced artifact — a file path, or an identified entry
in `.specs/features/<feature-name>/vault/.write-log.jsonl` — and to read that artifact.

##### FR-5.3
**When** in artifact-conformance mode, **the system shall** require the validator to verify that
each mapped artifact exists, is non-empty, and substantively states or delivers what the cited
requirement demands; a placeholder, stub, or TODO-only artifact is a FAIL.

##### FR-5.4
**When** in artifact-conformance mode, **the system shall** specify that the absence of unit tests
is **not** a failure, replacing the unconditional "at least one test exists for this requirement"
check for that mode only.

##### FR-5.5
**If** machine checks were written for the artifacts (FR-4.2), **then the system shall** require
the validator to run them and FAIL if any check fails.

##### FR-5.6
**If** the validator finds that a task running in artifact-conformance mode modified application
code, **then the system shall** require it to refuse the exemption, return FAIL, and report the
offending path(s) so the orchestrator reclassifies the feature per FR-3.

##### FR-5.7
**The system shall** keep the validator's existing scope check and quality check active in
artifact-conformance mode (no scope creep; conventions in `.specs/steering/tech.md` respected; no
leftover TODOs).

##### FR-5.8
**The system shall** define the artifact-conformance verdict block so it reports, per cited
requirement, the artifact satisfying it and the mode under which it was validated, keeping the
verdict machine-readable and stage-attributable for verbatim transcription to the PR.

##### FR-5.9
**The system shall** preserve the validator's existing all-or-nothing rule: if any cited
requirement fails in artifact-conformance mode, the whole task fails.

### Reviewers: a defined verdict for empty or non-code scope

#### FR-6: Non-code review scope resolution (both reviewers)

*(drivers: P2, D1, O1)*

**When** a reviewer is invoked and the git diff for its mode is empty or contains only non-code
artifacts, **the system shall** have the reviewer resolve and review the **non-code review
scope** rather than reporting that there is nothing to review.

##### FR-6.1
**The system shall** define the non-code review scope, in both `agents/code-reviewer.md` and
`agents/security-reviewer.md`, as the union of: (a) the feature's spec artifacts
(`requirements.md`, `design.md`, `tasks.md`, and `scope.md` where present), (b) every non-code
file present in the diff for the reviewer's mode, and (c) the vault changelog entries for this
feature in `.specs/features/<feature-name>/vault/.write-log.jsonl`.

**The system shall** state, in both contracts, that the **review scope** (what the reviewer reads
and judges) is a different set from **produced output** (what discharges the emptiness test,
FR-6.4): a plan document is always in scope for review and never counts as produced output.

##### FR-6.2
**The system shall** specify the scope-resolution order: attempt the existing diff
(`git diff` for `task` mode, `git diff <base>...HEAD` for `feature` mode) first; **if** that diff
is empty or contains only non-code artifacts, resolve the non-code review scope and review it.

##### FR-6.3
**The system shall** require each reviewer to emit exactly one of `PASS` or `FAIL` for a non-code
or empty scope — a hedge, an abstention, an "N/A", or a "nothing to review" is not a permitted
outcome (P2).

##### FR-6.4: The emptiness test and the attribution rule

*(drivers: P2, P3, O5; §3.2, §3.3, §6.2 item 1 — the requirement attempt 1 could not settle)*

**If** the feature has produced no output at all, **then the system shall** require the reviewer
to return `FAIL` with a Critical finding stating that the feature produced no reviewable output,
so an empty feature can never reach `ready-to-merge`.

**The system shall** determine what "produced output" means solely by the following rule, and
**shall** replicate it verbatim into `agents/code-reviewer.md` and `agents/security-reviewer.md`:

```
ATTRIBUTION RULE — what evidences that a feature's tasks produced an artifact

AT-1  A changed file in the diff for the reviewer's mode COUNTS as produced
      output unless AT-2 excludes it. Separately, the vault changelog
      `.specs/features/<feature-name>/vault/.write-log.jsonl` COUNTS whenever it
      holds at least one entry for this feature, whether or not it is in the diff.
AT-2  A file is EXCLUDED only on positive evidence, of exactly two kinds:
      (a) PLAN SET — under `.specs/features/<feature-name>/` it is `requirements.md`,
          `design.md`, `tasks.md`, `scope.md`, `.spec-state.json`,
          `input-data/README.md`, or `spec-memory/README.md`; or it is the
          repository-root `.gitignore` and its change is confined to the
          per-feature scratch patterns `/sdd-feature` appends.
      (b) NO TASK TOUCHED IT — no commit that touches the file on the feature
          branch carries a task marker (FR-15), AND every commit that touches it
          predates the earliest task-marked commit on that branch. Where the
          branch carries no task-marked commit at all, this limb excludes
          nothing.
AT-3  Absence of evidence never excludes. Where the evidence for AT-2 is
      unavailable, indeterminate, or contradictory, the file COUNTS.
AT-4  No other signal may include or exclude a file. A task's `**Files:**`
      declaration, a task's body or sub-tasks, and an executor's completion
      summary MAY be cited as context in the report and MAY NOT promote a file to
      produced output nor remove one from it.
AT-5  If no file and no changelog entry COUNTS, the emptiness test fires: return
      FAIL with a Critical finding naming what was inspected and excluded.
AT-6  The rule yields the same verdict in `task` mode and in `feature` mode. No
      limb of it may depend on an input available in only one mode.
```

*(Non-normative: Appendix A shows that this rule cannot produce a false-FAIL on a genuine
non-code feature (BB1) or a false-PASS on an empty one (BB2), and that attempt 1's trilemma does
not bind under the five signals locked decision O5 puts in play.)*

##### FR-6.5
**The system shall** require each reviewer's `Scope Reviewed` section to enumerate the non-code
review scope actually inspected, including the vault changelog entries by target and operation, so
the verdict is auditable.

##### FR-6.6
**The system shall** keep the existing severity model unchanged in non-code scope: any Critical or
High finding blocks; Medium and Low are reported and do not block.

##### FR-6.7
**The system shall** keep both reviewers read-only with their existing tool sets; resolving the
non-code scope and applying the attribution rule shall require no new tool and no new write
target. *(Verified at authoring time: `agents/code-reviewer.md` and `agents/security-reviewer.md`
each grant `Read`, `Glob`, `Grep`, `Bash` at lines 9–13. **Expected on re-derivation: `Bash`
present in both tool lists.** If it is ever absent, `AT-2(b)` is unevaluable, `AT-3` applies, and
the rule degrades safely to `AT-2(a)`. Reading commit provenance uses the reviewer's existing `git`
access, the same access `AT-1`'s diff already requires.)*

##### FR-6.8
**The system shall** require reviewers to read the in-repo vault changelog only, never the
knowledge-vault notes themselves; **if** a reviewer needs a vault fact to judge a change, **then
the system shall** have it halt with `VAULT REQUEST: <need>` per the existing isolation rule.

##### FR-6.9 *(new in attempt 2)*: the role of each evidence signal

*(driver: O5 — the locked decision names five signals and requires each to be given a role)*

**The system shall** state, in both reviewer contracts, the role of each of the five signals, in
this form:

```
SIGNAL ROLES (attribution)
1. git diff for the reviewer's mode  — NECESSARY for a file to count (AT-1).
2. a task's `**Files:**` declaration — CONTEXT ONLY; never promotes, never demotes
   (AT-4). It is a prediction written before execution, is not rule-enforced, and
   has been observed wrong in both directions.
3. an executor's completion summary — CONTEXT ONLY, and absent in `feature` mode;
   no limb of the rule may depend on it (AT-4, AT-6).
4. a task's body or sub-tasks         — CONTEXT ONLY (AT-4).
5. commit provenance                  — DECISIVE IN THE EXCLUDING DIRECTION ONLY
   (AT-2(b)). It may remove a file from produced output; it may never be required
   to admit one, and indeterminate provenance excludes nothing (AT-3).
```

##### FR-6.10 *(new in attempt 2)*: the attribution outcome is reported, not just used

*(drivers: P2; §3.2 — the rule that could not be checked is the rule that consumed five amendments)*

**When** a reviewer applies the attribution rule, **the system shall** require its report to list,
for each changed file it considered, whether the file COUNTED or was EXCLUDED and, where excluded,
which limb — `AT-2(a)` or `AT-2(b)` — excluded it. **If** the emptiness test fires, **then the
system shall** require that list to be present in the FAIL, so a false-FAIL is visible and
correctable in one step rather than indistinguishable from a genuine empty feature.

#### FR-7: code-reviewer findings in non-code scope

*(drivers: P2, O1)*

**When** the code-reviewer reviews a non-code scope, **the system shall** define the finding
classes it hunts for, so its PASS is a genuine judgement and not a default.

##### FR-7.1
**The system shall** have the code-reviewer check the reviewed artifacts for internal
contradictions, statements that conflict with the confirmed `requirements.md`/`design.md`, and
instructions that cannot be followed as written.

##### FR-7.2
**The system shall** have the code-reviewer check for stale, dangling, or incorrect references:
broken file paths, dead links, cited requirement or task IDs that do not exist, and references to
renamed or removed artifacts.

##### FR-7.3
**The system shall** have the code-reviewer check for content duplicated or divergent across the
reviewed artifacts (including the two synchronised copies of a document, where the project keeps
such copies and both copies are within the reviewed scope, subject to the pending-sync allowance
in NFR-10) and for content left incomplete (placeholders, unresolved TODOs).

##### FR-7.4
**Where** the scope is a vault update, **the system shall** have the code-reviewer judge the
changelog entries for coherence with the feature's requirements — each recorded write traceable to
a requirement, target and operation consistent with the stated intent.

##### FR-7.5
**The system shall** require every blocking non-code finding to state a concrete failure
scenario — the reader or downstream consumer who is misled and the wrong outcome that follows —
mirroring the existing rule that "this looks fragile" is not a finding.

#### FR-8: security-reviewer findings in non-code scope

*(drivers: P2, O1)*

**When** the security-reviewer reviews a non-code scope, **the system shall** define the finding
classes it hunts for, so its PASS is a genuine judgement and not a default.

##### FR-8.1
**The system shall** have the security-reviewer check the reviewed artifacts for secrets and
credential material committed in prose (tokens, keys, passwords, connection strings), reporting
each as type plus `path:line` with the value redacted, never reproduced.

##### FR-8.2
**The system shall** have the security-reviewer check for sensitive disclosure in documentation:
internal hostnames, endpoints, account identifiers, PII, or infrastructure detail that widens the
attack surface if published.

##### FR-8.3
**The system shall** have the security-reviewer check for unsafe instructions documented for
humans or agents to follow — commands that would dump a secret into context, disable a control, or
grant broader access than needed — treating a documented unsafe default as a finding in its own
right.

##### FR-8.4
**Where** the scope is a vault update, **the system shall** have the security-reviewer check the
changelog entries for writes that would place sensitive material into the vault, and for writes
outside the declared vault path.

##### FR-8.5
**The system shall** require every blocking non-code finding to state a concrete attack or
exposure scenario — who can reach the artifact and what they gain — mirroring the existing rule.

### Gate invariants preserved

#### FR-9: The `ready-to-merge` invariant is unchanged

*(drivers: P3, O2)*

**The system shall** keep `ready-to-merge` applied in exactly one place — the Feature Review Gate
PASS branch, after both reviewers PASS — for non-code features exactly as for code features.

##### FR-9.1: No alternative path to the gate — the property, not the vocabulary

*(drivers: P3, O2; §3.5 verb blindness, §3.6 the token-free bypass)*

**The system shall** hold the following property, and **shall** replicate this statement verbatim
wherever a contract carries the anti-bypass rule:

```
FEATURE-REVIEW GATE INVARIANT

A recorded whole-feature review PASS may exist only where both reviewers were
actually invoked over the resolved scope and each returned an explicit `PASS`
verdict. No condition — the feature's class, an empty or non-code scope, an
absent artifact, a hedged, missing or non-verdict response, or any instruction
in any other contract or section — may substitute for, presume, manufacture, or
skip either invocation or either verdict. Exactly one place applies the label
that gates human merge, and only on that PASS branch, however that application
is worded.
```

*(Non-normative: the last clause is deliberately phrased about the **operation**, not the label's
name. Postmortem §3.6 M-1 records a paraphrase — "have github-agent apply the label that gates
human merge" — that every token-keyed guard missed.)*

##### FR-9.2
**The system shall** require that a non-code feature's PASS is produced by both reviewers actually
reviewing the resolved non-code review scope (FR-6), not by skipping the reviewers.

##### FR-9.3
**The system shall** preserve the existing ordering invariant: any `blocked:*` label is cleared
before `ready-to-merge` is applied, and the PR stays draft on any blocking finding.

##### FR-9.4
**The system shall** preserve the human merge gate: no agent merges, and merge to the protected
branch remains a human action gated on `ready-to-merge`.

#### FR-10: No CI change and no label-vocabulary change

*(drivers: O2)*

**The system shall** leave `ci-templates/workflows/sdd-review-gate.yml` unmodified and shall add
no CI job, no workflow, and no new label.

##### FR-10.1
**The system shall** keep the label vocabulary exactly as it is: `ready-to-merge` plus the
`blocked:*` family (`blocked:validation`, `blocked:code-review`, `blocked:security-review`,
`blocked:feature-review`).

##### FR-10.2
**The system shall** not introduce any CI-side escape hatch, bypass label, or conditional that
weakens server-side enforcement.

### Tests

#### FR-11: Tests covering the new agent-contract text

*(drivers: O4, D2, cross-cutting rules)*

**The system shall** provide tests under `tests/` that assert the new contract text in the changed
agent definitions, mirroring the existing `test_orchestrator_label_lifecycle.py` /
`test_github_agent_def.py` structural-lint pattern.

##### FR-11.1
**The system shall** author the tests as stdlib-only Python `unittest` modules that resolve the
agent definition paths relative to the test file, so they run wherever the repository's hooks run.

##### FR-11.2
**The system shall** assert that `agents/orchestrator.md` specifies the classification step, the
`featureClass` key and its two permitted values in the state-file schema, the fail-safe default
(FR-1.4), the routing of `featureClass` to tester/validator/reviewers, and the reclassification
fallback including its arming predicate (FR-3, FR-3.5).

##### FR-11.3
**The system shall** assert that `agents/task-validator.md` defines artifact-conformance mode,
that the mode is entered only on the orchestrator's instruction, that missing unit tests are not a
FAIL in that mode, and that application-code detection in that mode forces a FAIL (FR-5.6).

##### FR-11.4
**The system shall** assert that `agents/task-tester.md` defines the no-code behaviour, prohibits
vacuous placeholder tests, and specifies the "no applicable tests" completion block.

##### FR-11.5
**The system shall** assert that `agents/code-reviewer.md` and `agents/security-reviewer.md` each
define the non-code review scope, its resolution order, the mandatory PASS-or-FAIL outcome, the
empty-scope FAIL, and the vault-changelog source (`.write-log.jsonl`) without any vault-note read.

##### FR-11.6
**The system shall** provide a regression assertion that the label gating human merge is applied
in exactly one place in `agents/orchestrator.md`, and that the non-code path introduces no second
application point, worded or named in any way (FR-9.1, FR-16).

##### FR-11.7
**The system shall** provide an assertion that `ci-templates/workflows/sdd-review-gate.yml` still
requires `ready-to-merge`, still fails on any `blocked:*` label, and contains no bypass or
exemption label.

##### FR-11.8: The suite stays green, with exactly two live-global carve-outs

*(drivers: O4, D2, cross-cutting rules. Folds amendments **A1** (requirements confirmation) and
**A2** (raised in design) into base text; no constraint either imposed is dropped.)*

**The system shall** keep the existing test suite passing, and no existing assertion is deleted or
weakened to accommodate the new track, with exactly **two** deliberate, documented exceptions —
the only two assertions in the suite that compare an in-repo file against a **live** copy under
`~/.claude/`:

1. `test_two_claude_files_byte_identical` (`tests/test_docs_updates.py`), which asserts
   byte-identity between the repository-root `CLAUDE.md` and the global copy.
2. `test_repo_and_global_copies_are_byte_identical`
   (`tests/test_orchestrator_label_lifecycle.py`), which asserts byte-identity between
   `agents/orchestrator.md` and `~/.claude/agents/orchestrator.md`.

Both pass today and both fail the moment this feature's first edit lands, because FR-1, FR-2 and
FR-3 each require editing `agents/orchestrator.md` and FR-12 requires editing `CLAUDE.md`, while
FR-12.1 and NFR-10 forbid syncing `~/.claude` before merge. The collision is unavoidable, not
hypothetical.

**The system shall** constrain both exceptions as follows; every constraint applies to each
assertion except where one is named:

- **Shall not** delete either assertion, and **shall** keep each able to fail on genuine drift —
  content the repository copy states that the global copy omits or contradicts.
- **For the `CLAUDE.md` assertion**, the surviving drift check is the class
  `test_two_claude_ownership_lines_consistent` (`tests/test_docs_updates.py`) already performs:
  comparison of the normalised Agent-Ownership invariant lines across the two copies. A global copy
  missing an Agent-Ownership invariant phrase **shall** still be caught.
- **For the `agents/orchestrator.md` assertion**, the surviving drift check **shall** compare the
  orchestrator's **invariant instruction lines** rather than raw bytes. The invariants that
  **shall** remain checked are: (a) the single-application-point rule for the merge-gating label
  together with the clear-`blocked:*`-before-set ordering; (b) the clear-**every**-recorded-
  `blocked:*`-label wording; (c) the scaffold-push-only-on-first-scaffold scoping; and (d) the
  "never runs `gh` / `git push` yourself; github-agent is the only component that does" framing. A
  readable global copy that omits or contradicts any one of these is genuine drift and **shall**
  still fail.
- The drift discriminator **shall not** be a blanket skip taken whenever the two copies differ.
- **Shall** have each assertion tolerate the "repository copy ahead, global copy not yet synced by
  `./install.sh`" state specifically, treating byte-identity as **satisfied-or-pending**.
- **Where** an assertion resolves its global path, **shall** permit deriving it from `Path.home()`
  in place of the hardcoded absolute path (`/Users/jamie.zaikov/.claude/CLAUDE.md` in
  `tests/test_docs_updates.py`; `/Users/jamie.zaikov/.claude/agents/orchestrator.md` in
  `tests/test_orchestrator_label_lifecycle.py`) — a portability defect whose correction is in scope
  for the task that reworks the assertion — and **shall** permit no other change to either
  module's scope.
- **Shall** record the carve-out's rationale in each reworked assertion itself (for example its
  docstring), citing FR-11.8 and NFR-10.
- **Shall** confine the carve-out to these two assertions: every other assertion in `tests/`, in
  these modules and all others, remains undeleted and unweakened. The other two modules
  referencing `~/.claude` (`tests/test_install_pre_push_hook.py`,
  `tests/test_sdd_init_ci_templates.py`) point `HOME` at a throwaway temporary directory, are not
  live-global checks, and **shall not** be modified.
- **If** a further live-global identity assertion is discovered or introduced, **then the system
  shall** require a fresh amendment rather than an extension of this carve-out by analogy.

**Running `./install.sh` mid-feature is not an acceptable resolution.** NFR-10 forbids resolving
the pending-sync window by writing to `~/.claude`; the operator runs the installer after merge.

*How* each assertion is reworked is a design decision; this requirement fixes only what must
remain true of it.

##### FR-11.9 *(new in attempt 2)*: the attribution rule is pinned, and the pin is proven

*(drivers: O5; steering rule 5 — prose contracts have no compiler)*

**The system shall** assert that both reviewer contracts carry the `AT-1`..`AT-6` rule (FR-6.4)
and the signal-role block (FR-6.9) **verbatim and closed** — closed meaning the assertion fails
not only when a limb is deleted or altered, but also when an exception, proviso or additional
sentence is appended to any limb.

**The system shall** prove each such pin by **mutation**: re-indent one line of the pinned text
and add one trailing space, and confirm the assertion goes RED for each mutation. A pin not shown
to go RED is not a pin.

### Documentation

#### FR-12: CLAUDE.md update (repository copy; global copy synced by the installer)

*(drivers: scope.md "In v1" — docs; folds **A1**)*

**The system shall** update the pipeline description in the repository-root `CLAUDE.md` to
describe feature classification and the non-code track — tests-optional artifact-conformance
validation and the reviewers' defined verdict for empty/non-code scope — while restating that
`ready-to-merge` still requires a real whole-feature review PASS.

##### FR-12.1
**The system shall** confine this feature's `CLAUDE.md` edit to the repository copy at the
repository root, and **shall not** have any pipeline stage write to `~/.claude/CLAUDE.md` or to
any other path under `~/.claude/` at any point during implementation.

**The system shall** treat the global copy as a derived install artifact synchronised **after the
pull request is merged**, by the operator running `./install.sh`. That installer is the audited
sync mechanism: it copies each `agents/*.md` and each `commands/*.md` into `~/.claude/agents/` and
`~/.claude/commands/` (skipping identical files via `cmp -s` and reporting each as installed,
updated or unchanged), copies the repository `CLAUDE.md` to `~/.claude/CLAUDE.md` prompting rather
than overwriting silently where the existing copy differs, and on explicit opt-in stages the hooks
and CI templates. Because it covers `agents/*.md`, the installer also propagates this feature's
changed agent definitions, which the `CLAUDE.md` edit does not.

*Rationale (A1):* having the pipeline edit `~/.claude/CLAUDE.md` during implementation would
mutate the operator's live global configuration before the pull request is reviewed or merged, and
would be an out-of-repo write invisible in the PR diff — weakening the exact audit trail this
feature exists to protect.

##### FR-12.2
**The system shall** state in `CLAUDE.md` that classification is explicit, recorded in
`.spec-state.json`, and falls back to the full code path when a non-code feature turns out to
touch application code (D2).

#### FR-13: README update

*(drivers: scope.md "In v1" — docs)*

**The system shall** update the README where it describes the pipeline stages (the five-stage
per-task pipeline and the feature review) to describe the non-code track and the classification
step.

##### FR-13.1
**The system shall** state in the README that a non-code feature reaches `ready-to-merge` through
the same audited path as a code feature, and that no bypass label exists.

### New in attempt 2

#### FR-14: The plan set cannot drift away from what `/sdd-feature` scaffolds

*(drivers: O5; §3.2 — the scaffold enumeration A5 §4.1 conceded but would not spend text on)*

**The system shall** provide a test that fails whenever the plan set enumerated in `AT-2(a)`
(FR-6.4) and the tracked artifacts `commands/sdd-feature.md` scaffolds cease to correspond, in
**either** direction: a scaffolded tracked artifact absent from the plan set, or a plan-set entry
`/sdd-feature` no longer scaffolds.

##### FR-14.1
**The system shall** derive the scaffolded set in that test from `commands/sdd-feature.md` itself
and from the repository-root `.gitignore` — never from a second hardcoded list — so that adding a
scaffolded file turns the test RED rather than silently widening what counts as produced output.

##### FR-14.2
**The system shall** prove the test discriminates, by mutation in both directions: add a
scaffolded artifact to `commands/sdd-feature.md` without touching the contracts (expect RED), and
remove one plan-set entry from a reviewer contract (expect RED).

##### FR-14.3
**The system shall** state, wherever the current membership of the plan set is recorded as a
figure, its expected value on re-derivation and the counting convention that produces it.
*(Expected on re-derivation from `commands/sdd-feature.md` at the time of writing: 7 artifacts
created, of which 6 are tracked — `.spec-state.json` is excluded by `.gitignore`'s
`**/.spec-state.json` — plus 1 modified file, the repository-root `.gitignore`. A different count
after a deliberate change to `/sdd-feature` is a required update, not a regression.)*

#### FR-15: Implementation-task commits are machine-identifiable

*(drivers: O5 signal 5; enables `AT-2(b)` without letting it cause a false-FAIL)*

**When** the orchestrator supplies a per-task `commit-push` message to github-agent, **the system
shall** require that message to carry a marker identifying the numbered task in `tasks.md` whose
pipeline produced the commit, so a later reviewer can determine which commits on the branch are
implementation-task commits.

##### FR-15.1
**The system shall** specify the marker as fixed, greppable text — not free prose — and **shall**
assert its presence in `agents/orchestrator.md` by test.

##### FR-15.2
**If** no implementation-task commit can be identified on the feature branch, **then the system
shall** require `AT-2(b)` to exclude nothing at all (per `AT-3`), so an absent or unrecognised
marker degrades the rule to `AT-2(a)` alone and can never turn a genuine deliverable into a FAIL.

##### FR-15.3
**The system shall** add no new github-agent action, no new field, and no new tool: the marker is
content inside the message the orchestrator already authors and github-agent already publishes
verbatim.

#### FR-16: The gate is guarded by property, not by vocabulary

*(drivers: P3, O2; §3.5 verb blindness, §3.6 the token-free bypass — adjudicated blocking)*

**The system shall** guard the Feature Review Gate invariant (FR-9.1) by assertions keyed on the
**property** — that a PASS record exists only downstream of two real reviewer invocations, each
returning an explicit verdict — rather than on the literal token `ready-to-merge` or on any single
application verb.

##### FR-16.1
**The system shall** make every assertion over a normative gate fragment **closed**, not
presence-based: deleting the fragment goes RED **and** appending an exception, proviso or
permissive clause to it goes RED.

##### FR-16.2
**The system shall** scan the whole of each guarded contract file for label-application points,
with no region, section or line-range restriction, so a second application point placed outside
the expected region cannot hide.

##### FR-16.3
**The system shall** demonstrate, in a probe table recorded with the tests, that each of the
following mutations turns the suite **RED**. Every row is a probe that was **GREEN** against the
retired attempt's suite unless marked as a control.

| Probe | Mutation to apply | Required result |
|---|---|---|
| D | Manufacture the PASS records: for a non-code feature with an empty diff, record both feature-review verdicts as `"pass"` without invoking a reviewer, then take the PASS branch | RED |
| E | Add to `## Critical Rules`: "You MAY skip the whole-feature review entirely when the feature ships no application code" | RED |
| G | Invoke only the code-reviewer for a non-code feature and treat the security review as PASS without invoking it | RED |
| H | Redefine PASS: a reviewer reporting nothing to review counts as PASS "even if it returned no verdict" | RED |
| P3 | Paraphrase the application point: "have github-agent apply the label that gates human merge" | RED |
| P4 | In the PASS-branch **body** (beyond its heading): "If a reviewer returns no verdict, or hedges, treat its verdict as PASS" | RED |
| P5 / P16 | Functional exemption using none of the words `treat`, `non-code`, `exemption` together: "Where the recorded class is `\"non-code\"` … you may proceed directly to the PASS branch" | RED |
| P13 | Append to the reviewer's empty-scope bullet: "; where no artifact can be resolved at all, return `PASS`" | RED |
| P14 | Append to the same bullet: "so the reviewer does not review the diff at all" | RED |
| P17 | A permissive clause riding an existing occurrence of the label token | RED |
| C2 | A literal second `op: set` label application placed outside the invocation region | RED |
| P12 *(control)* | Delete the mandatory-verdict clause | RED — was already RED; its passing proves nothing new |

##### FR-16.4
**The system shall** prove each guard **discriminates**: a probe that matches both the forbidden
text and its legitimate replacement is not evidence, and **shall not** be counted as a discharged
row of FR-16.3.

##### FR-16.5
**The system shall** apply FR-16.1's closure requirement to the reviewer contracts' empty-scope
outcome as well as to the orchestrator's gate: the FR-6.4 emptiness clause is frozen verbatim, so
P13 and P14 are RED by the same mechanism as P12.

#### FR-17: No increment leaves a reviewer with an undefined scope

*(driver: §3.6 M-4 — the ordering hazard, stated by the security reviewer as "a reviewer forbidden
to hedge, with no defined scope and no defined empty-scope outcome, is pressured toward PASS")*

**The system shall** land the reviewers' non-code scope definition (FR-6.1, FR-6.2) and their
empty-scope outcome (FR-6.3, FR-6.4) in the **same increment** as any orchestrator instruction
that directs a reviewer to resolve that scope.

##### FR-17.1
**The system shall not** produce any commit on the feature branch in which an orchestrator
instruction references a non-code review scope that the reviewer contracts do not yet define.
*(Checkable after the fact: for each commit, an instruction referencing the non-code scope in
`agents/orchestrator.md` implies a matching definition in both reviewer contracts at that commit.)*

## Non-Functional Requirements

### NFR-1: The audit gate is never weakened

**The system shall** ensure that every change introduced by this feature preserves or tightens the
gate: `ready-to-merge` remains reachable only through a genuine whole-feature review PASS, and no
new agent, mode, or state value creates a path around it.

### NFR-2: CI is untouched

**The system shall** make no modification to `ci-templates/workflows/sdd-review-gate.yml` or to
any other CI template, workflow, or hook; server-side enforcement remains exactly as strict as it
is today (O2).

### NFR-3: No new tools, no new write targets, no new agents

**The system shall** grant no agent a new tool, a new write target, or a new artifact to own, and
shall add no agent to the fleet; the change is confined to the text of existing agent contracts,
tests, and documentation.

### NFR-4: Backward compatibility for code features

**The system shall** leave the behaviour of code-bearing features bit-for-bit unchanged: same
stages, same order, same verdict formats, same labels, and no additional user prompt on the
code path.

### NFR-5: Auditability of the classification

**The system shall** make the classification and any reclassification traceable: the value, its
basis, any user override, and the tasks validated under the non-code exemption are recorded in
`.spec-state.json` and reported to the user.

### NFR-6: Contract text is machine-assertable

**The system shall** express every new behaviour as explicit, greppable instruction text in the
agent definition — named modes, named state keys, named artifact paths — concrete enough for a
stdlib structural-lint assertion, matching the existing test pattern in `tests/`.

### NFR-7: Secrets — use, don't read

**The system shall** preserve the "use, don't read" rule in non-code review: a secret found in a
reviewed document or changelog entry is reported as type plus `path:line` with the value redacted,
and no reviewer reads a denied secret store or works around a deny rule.

### NFR-8: Knowledge-vault isolation preserved

**The system shall** preserve vault isolation: no agent reads knowledge-vault notes to conduct a
non-code review; the in-repo `.write-log.jsonl` changelog is the reviewable surface, and a needed
vault fact triggers `VAULT REQUEST` through the orchestrator and vault-reader.

### NFR-9: Ownership boundaries preserved

**The system shall** preserve the framework invariant that no agent modifies another agent's
artifact; the validator and reviewers remain read-only and the tester still never modifies
implementation code.

### NFR-10: The repository copy is authoritative; the installer syncs the global copy

*(drivers: scope.md "In v1" — docs; folds **A1**)*

**Where** a document or agent definition is maintained both in this repository and under
`~/.claude`, **the system shall** treat the repository copy as authoritative and the `~/.claude`
copy as a derived install artifact, brought into sync by the operator running `./install.sh`
after merge (FR-12.1).

**While** the repository copy has been changed and `./install.sh` has not yet been run, **the
system shall** treat the difference between the two copies as a legitimate pending-sync window —
not a defect — and **shall not** resolve it by writing to `~/.claude`.

**If** the global copy contradicts the authoritative repository copy — stating a framework
invariant differently, or omitting one the repository copy carries — **then the system shall**
treat that as genuine drift and a defect, distinct from the pending-sync window above, and
detectable per FR-11.8.

### NFR-11: English and EARS

**The system shall** author all spec artifacts in English; requirements use EARS syntax with
`FR-N` / `NFR-N` numbering.

### NFR-12 *(new in attempt 2)*: Normative fragments are short, fenced, and amendable

*(driver: §6.2 item 2 — `design.md` reached 2723 lines and an amendment had to touch 55 anchored
rows)*

**Where** a statement is destined to be replicated verbatim into an agent contract, **the system
shall** keep it short, hold it in a single fenced block, and keep its rationale outside that
block, so a later amendment edits one fence rather than many anchored rows.

##### NFR-12.1
**The system shall** keep the count of separately-replicated fenced blocks introduced by this
feature small and enumerated, so each has exactly one authoritative site. *(This document defines
four: the `AT-1`..`AT-6` attribution rule (FR-6.4), the signal-roles block (FR-6.9), the
feature-review gate invariant (FR-9.1), and the reclassification arming predicate (FR-3.5).
**Expected on re-derivation: 4** — counting convention: fenced code blocks in this document whose
content a requirement instructs an implementer to replicate verbatim into an agent contract.)*

### NFR-13 *(new in attempt 2)*: Every pin is proven by mutation; every guard is proven to discriminate

*(driver: steering rule 5; three separate High-severity findings on attempt 1 shared the shape
"correct logic that nothing pinned")*

**The system shall** treat an assertion over contract prose as unproven until the pinned text has
been mutated and the assertion observed to go RED; and **shall** treat a guard as unproven until a
probe matching its legitimate replacement has been observed to stay GREEN while the forbidden text
goes RED.

##### NFR-13.1
**The system shall not** key a guard on a single verb. **Where** an action can be phrased with
more than one verb (`set` / `apply` / `add` / `attach`), the guard **shall** be shown RED against
at least two phrasings, one of which does not use the verb the guard's author had in mind.

### NFR-14 *(new in attempt 2)*: Recorded figures carry their expected re-derived value

*(driver: steering rule 1 — the dominant cost of attempt 1 was plausible recorded numbers nobody
re-checked)*

**Where** this feature records a count, a size, or a line reference in a contract, a test, a
document, or `.spec-state.json`, **the system shall** state alongside it the counting convention
and the value expected on re-derivation, and **shall not** record a bare figure.

## Acceptance Criteria

- **AC-1** — A feature whose tasks produce only vault updates (empty in-repo diff) runs the full
  five-stage pipeline, receives a genuine validator PASS and two genuine reviewer PASSes over the
  non-code review scope, and reaches `ready-to-merge` through the existing single application
  point. *(FR-1, FR-5, FR-6, FR-9; D1 shape A)*
- **AC-2** — A feature whose tasks produce only committed documentation (docs-only in-repo diff)
  reaches the same genuine PASS. *(FR-1, FR-6; D1 shape B)*
- **AC-3** — A feature classified `"non-code"` in which a task modifies application code is
  reclassified `"code"`, its exemption withdrawn, and its tests required before the task can
  complete. *(FR-3, FR-5.6, FR-4.5; D2)*
- **AC-4** — A `"non-code"` feature that produced no artifact at all receives a reviewer `FAIL`,
  not a PASS. **This criterion was undischargeable in attempt 1** because the scaffold made the
  resolved scope non-empty by construction; under `AT-2(a)` the scaffold is excluded by name, so
  the criterion now fires. *(FR-6.4)*
- **AC-5** — No reviewer can emit a non-verdict (hedge/N/A) for an empty or non-code scope.
  *(FR-6.3)*
- **AC-6** — `git diff` for this feature shows no change to
  `ci-templates/workflows/sdd-review-gate.yml`, no new workflow, and no new label name anywhere.
  *(FR-10, NFR-2)*
- **AC-7** — The label that gates human merge is applied at exactly one point in
  `agents/orchestrator.md`, verified by a whole-file, verb-agnostic, token-agnostic check that is
  shown RED against probes P3, P17 and C2. *(FR-9.1, FR-11.6, FR-16.2, FR-16.3)*
- **AC-8** — Every changed agent contract has at least one corresponding assertion under `tests/`,
  and the pre-existing test suite passes, with exactly two deliberate, documented exceptions:
  the reworked `test_two_claude_files_byte_identical` and the reworked
  `test_repo_and_global_copies_are_byte_identical`, both constrained by FR-11.8 and no third
  permitted. No other existing assertion is deleted or weakened, and
  `tests/test_install_pre_push_hook.py` and `tests/test_sdd_init_ci_templates.py` are unmodified.
  *(FR-11, FR-11.8)*
- **AC-9** — A code-bearing feature run end-to-end behaves identically to before this change.
  *(NFR-4)*
- **AC-10** — The repository-root `CLAUDE.md` and the README describe the classification step and
  the non-code track; the feature's diff and working tree contain no write to any path under
  `~/.claude/`; `tests/test_docs_updates.py` passes while the repository copy is ahead of an
  unsynced global copy yet still fails when a readable global copy omits or contradicts an
  Agent-Ownership invariant line; and `tests/test_orchestrator_label_lifecycle.py` behaves
  correspondingly for the four orchestrator invariant instruction lines named in FR-11.8.
  *(FR-12, FR-12.1, FR-13, FR-11.8, NFR-10)*
- **AC-11** *(closes Residual 1)* — A reconnaissance feature whose entire product is
  `.specs/features/<feature-name>/recon.md`, and whose task's `**Files:**` field never declares
  that file, does **not** trigger the emptiness test: `recon.md` COUNTS under `AT-1` because no
  limb of `AT-2` excludes it. *(FR-6.4)*
- **AC-12** *(closes Residual 3)* — A feature that produced nothing, one of whose tasks declares a
  plan document (for example `design.md`) in its `**Files:**` field as a file it creates or
  modifies, **still** triggers the emptiness test and receives FAIL: the declaration promotes
  nothing (`AT-4`) and the plan document is excluded by name (`AT-2(a)`). *(FR-6.4)*
- **AC-13** *(closes Residual 2)* — In a repository's first feature, `/sdd-feature`'s append to the
  repository-root `.gitignore` neither counts as produced output (`AT-2(a)`) nor triggers
  reclassification to `"code"` (FR-3.6). *(FR-3.6, FR-6.4)*
- **AC-14** — Every row of FR-16.3's probe table is demonstrated RED, and each guard is
  demonstrated to discriminate per FR-16.4. *(FR-16)*
- **AC-15** — The plan-set drift test is demonstrated RED in both directions per FR-14.2.
  *(FR-14)*
- **AC-16** — For one and the same feature state, the attribution rule yields the same COUNTED /
  EXCLUDED set in `task` mode and in `feature` mode. *(FR-6.4 `AT-6`)*
- **AC-17** — A vault-only feature whose `.write-log.jsonl` holds at least one entry passes the
  emptiness test even if that file is absent from the diff for the reviewer's mode.
  *(FR-6.4 `AT-1`)*

## Appendix A — Does A5 part 5's trilemma still bind? *(non-normative reasoning; normative text is FR-6.4)*

### A.1 What the trilemma claimed

Amendment A5 part 5 of the retired attempt concluded that any attribution rule must re-open one of
two blocking defects: **BB1**, a false-FAIL on a genuine non-code feature (which reinstates the
deadlock locked decision O1 exists to remove), or **BB2**, a false-PASS reaching `ready-to-merge`
on a feature that produced nothing. Its argument (postmortem §3.2) was: inside the feature's own
directory a reviewer has three signals — the diff, the `**Files:**` declaration, the executor's
completion summary; the summary does not exist in `feature` mode, which is the only mode where the
test runs; diff-presence alone re-admits the whole scaffold, which is in the diff for every
feature; a declaration alone rescues a feature that produced nothing. Hence a conjunction of diff
**and** declaration, and hence three disclosed residuals.

That argument depends on three constraints it never wrote down: **minimum text**, **no reading of
task prose**, and **no commit archaeology**. It also depends on one structural choice: that *the
plan* is defined as **everything under the feature's own directory**, which forced a rescue limb
for genuine in-directory deliverables and made `**Files:**` load-bearing.

### A.2 The answer, stated plainly

**No. The trilemma does not bind.** It is not a proven impossibility under locked decision O5's
five signals; it was a true statement about a narrower search space.

### A.3 Why it stops binding

The rule in FR-6.4 does not try to discriminate inside the feature's directory at all. It
discriminates **plan-and-scaffold versus everything else**, by name:

- The `**Files:**` conjunct — the single source of both BB1 and BB2 — is **deleted**, not repaired.
  With the plan set enumerated by name (`AT-2(a)`), a genuine in-directory deliverable such as
  `.specs/features/<f>/recon.md` needs no rescue limb: it is simply not in the plan set. Nothing
  has to be declared to be counted. *(This costs text — the constraint A5 would not spend.)*
- **Commit provenance** (`AT-2(b)`) supplies a second, independent exclusion that is derived rather
  than enumerated, so it still discriminates when the enumeration is wrong. *(This is commit
  archaeology — the constraint A5 forbade itself.)*
- The two remaining prose signals — the `**Files:**` field and the task body — are given a role
  that cannot hurt: **context only** (`AT-4`). They may inform the report; they may not move a file
  in or out of produced output. Residual 3, which existed purely because a declaration could
  promote a plan document, cannot arise.
- The executor's completion summary keeps no load at all (`AT-4`, `AT-6`), so nothing depends on
  the input that is missing in `feature` mode. Mode parity is a stated requirement (AC-16), not an
  accident.

### A.4 Why neither BB1 nor BB2 is reintroduced

The rule is built around one asymmetry, stated normatively as `AT-3`: **counting is the default;
exclusion requires positive evidence.** That asymmetry is what makes the two directions
independently checkable.

**BB1 (false-FAIL) is impossible except through a wrongful exclusion.** A genuine deliverable can
only be excluded by `AT-2(a)` or `AT-2(b)`.
- `AT-2(a)` excludes a closed, named list of scaffold artifacts. A deliverable in that list would
  mean the feature's only product is its own plan document — which is not a deliverable, by
  definition. FR-14 keeps the list from drifting away from `/sdd-feature`.
- `AT-2(b)` excludes only a file that **no task-marked commit touched** and that predates the
  earliest task-marked commit — that is, a file no task produced. Where markers are absent
  entirely, the limb excludes nothing (FR-15.2), so a coarse or squashed history degrades to
  `AT-2(a)` alone and still counts the deliverable.
- Indeterminate or contradictory evidence excludes nothing (`AT-3`).
Therefore a genuine task-produced artifact always COUNTS, and the FR-6.4 FAIL cannot fire on it.
Attempt 1's **Residual 1** — the undeclared in-directory deliverable — is closed (AC-11).

**BB2 (false-PASS) is impossible except through a wrongful inclusion.** For a feature that produced
nothing, every changed tracked file on the branch is either a plan-set artifact (excluded by name)
or a file no task touched (excluded by provenance). Something can only COUNT if a task-marked
commit created or modified a tracked file that is not scaffold — which is what "the tasks produced
an artifact" means. **Residual 3** — a plan document counted on its declaration alone — is closed
because declarations never promote (AC-12). **Residual 2** is closed because the `.gitignore`
scratch append is named in `AT-2(a)` and excluded from reclassification by FR-3.6 (AC-13).

Note the division of labour that keeps this honest: the emptiness test is a **floor** (did anything
get produced?), not a quality gate. Whether the produced artifact is any good is the reviewer's
ordinary substantive judgement under FR-7 and FR-8, with its ordinary severity model.

### A.5 The one residual this leaves, bounded

**Residual A** — a wrongful inclusion, i.e. the BB2 direction, requiring **two** independent
failures at once: (1) a tracked artifact created outside the task pipeline that is not in the plan
set — either because `/sdd-feature` scaffolds something the plan set does not list, or because an
agent wrote a tracked file during a planning phase; **and** (2) provenance unable to exclude it,
which requires the branch to carry no usable task markers at all.

It is bounded by two mechanical pins that fail loudly: FR-14 turns plan-set drift RED, and FR-15
plus FR-15.1 make the marker present and test-pinned. Its error direction reaches PASS on a feature
that has at least one real artifact for both reviewers to read, not on a literally empty one.

**Residual B** — a narrow false-FAIL requiring a task commit that is missing its marker *and* is
the earliest commit touching the deliverable *and* precedes every other task-marked commit. FR-15.1
pins the marker; the failure self-announces through FR-6.10's per-file COUNTED/EXCLUDED list, and
the fix is one commit-message marker plus a re-run.

Both are disclosed here rather than hidden, and both must be carried to the feature reviewer.

### A.6 How a later reader falsifies this argument

Do not take A.4 on trust. It fails if any of the following is true, and each is checkable:
1. There exists a genuine task-produced artifact matching a plan-set entry in `AT-2(a)`.
2. `AT-2(b)` can exclude a file that a task-marked commit touched.
3. Some limb of `AT-1`..`AT-6` reads an input that exists in only one reviewer mode (breaks AC-16).
4. Some signal other than `AT-1` and `AT-2` can change the COUNTED set (breaks `AT-4`).
5. `/sdd-feature` scaffolds a tracked artifact the plan set does not name, and FR-14's test is
   green (breaks A.5's first bound).

## Out of Scope

Mirroring `scope.md`'s **Deferred** list and resolved questions:

- Any change to `ci-templates/workflows/sdd-review-gate.yml`, to any other CI workflow, or to the
  label vocabulary (O2).
- A CI-side escape-hatch or bypass label of any kind — considered and rejected during scoping (O2).
- Retro-unblocking existing pull requests, including `make-squid-great-again` #2, which is a
  genuine code PR blocked correctly (O3).
- Automatic detection or auditing of vault mutations beyond what `vault-writer`'s existing
  changelog already records.
- Any new agent, tool grant, or write target (cross-cutting rule).
- Any agent-performed merge, or any weakening of the human merge gate.
- Changing how `vault-reader` / `vault-writer` operate, or reading vault notes for review purposes.
- Applying vault routing to this repository, which has no knowledge vault.
- Any write by the pipeline to `~/.claude/`, any change to `install.sh` itself, and any automation
  of the post-merge global sync.
- Any third live-global byte-identity carve-out beyond the two fixed in FR-11.8, and any
  modification of the `install.sh` test modules; a further carve-out requires a fresh amendment.

Explicitly **not** this feature's work, and not to be re-done or claimed by it:

- **Postmortem finding F2** — `agents/tasks-agent.md` Task Design Rule 5 no longer forbids non-code
  tasks. Fixed upstream on a separate chore branch and already merged (PR #8). No requirement here
  depends on re-fixing it.
- The `Edit` tool grants at line 10 of `agents/{design,requirements,tasks}-agent.md`, which are
  present and deliberately retained. Neither granting nor reverting them is in scope.

## Open Questions

- **None blocking.** O1–O5 and D1–D2 are resolved and locked in `scope.md`; O5 is discharged by
  FR-6.4, FR-6.9 and Appendix A.
- Two **disclosed residuals** (Appendix A.5) are open by design rather than unresolved: Residual A
  (bounded false-PASS requiring simultaneous plan-set drift and absent task markers) and Residual B
  (bounded false-FAIL requiring an unmarked earliest task commit). Both are bounded by FR-14 and
  FR-15, both self-announce through FR-6.10, and both must be carried to the whole-feature
  reviewer rather than being treated as closed.
- Left deliberately to **design**: the wording and placement of the contract text that carries each
  fenced block; how the reviewer's per-file COUNTED/EXCLUDED list (FR-6.10) is formatted; the exact
  shape of the task marker (FR-15.1) beyond its being fixed, greppable text; the mechanism by which
  FR-14's test derives the scaffolded set; and how each of FR-11.8's two assertions is reworked.
  Nothing about *what evidences task production* is left to design — that is settled here in full
  (FR-6.4, FR-6.9), which is the point of the restart.

## Requirement ID register

*(Counting convention: an ID is a heading line matching `^#{1,6} ` in this document containing an
`FR-`/`NFR-` token, deduplicated. Table-row and prose references are not definition sites. Note
for the re-deriver: a raw grep of heading lines returns **115** matches, not 114 — Appendix A's
own heading cites `FR-6.4`, and deduplication absorbs it. 115 raw / 114 unique is the expected
result, not a discrepancy.)*

| Group | IDs | Status |
|---|---|---|
| `FR-1` .. `FR-1.7`, `FR-2` .. `FR-2.4`, `FR-4` .. `FR-4.5`, `FR-5` .. `FR-5.9`, `FR-7` .. `FR-7.5`, `FR-8` .. `FR-8.5`, `FR-10` .. `FR-10.2`, `FR-13` .. `FR-13.1` | 46 | carried from attempt 1, text unchanged |
| `FR-3` .. `FR-3.4`, `FR-6` .. `FR-6.3`, `FR-6.5` .. `FR-6.8`, `FR-9`, `FR-9.2` .. `FR-9.4`, `FR-11` .. `FR-11.5`, `FR-11.7`, `FR-12.2` | 25 | carried, minor clarifying edits only |
| `FR-6.4` | 1 | carried, **rewritten in place** — now carries the `AT-1`..`AT-6` attribution rule |
| `FR-9.1` | 1 | carried, **rewritten in place** — now pins the gate property, not the label token |
| `FR-11.6` | 1 | carried, **rewritten in place** — verb- and token-agnostic |
| `FR-11.8`, `FR-12`, `FR-12.1` | 3 | carried, amendments **A1**/**A2** folded into base text; no constraint dropped |
| `NFR-1` .. `NFR-9`, `NFR-11` | 10 | carried from attempt 1, text unchanged |
| `NFR-10` | 1 | carried, **A1** folded into base text |
| `FR-3.5`, `FR-3.6`, `FR-6.9`, `FR-6.10`, `FR-11.9` | 5 | **new**, extending a retained parent above attempt 1's highest sub-ordinal |
| `FR-14` .. `FR-14.3`, `FR-15` .. `FR-15.3`, `FR-16` .. `FR-16.5`, `FR-17` .. `FR-17.1` | 16 | **new** top-level (FR-14+) |
| `NFR-12`, `NFR-12.1`, `NFR-13`, `NFR-13.1`, `NFR-14` | 5 | **new** top-level (NFR-12+) |
| — | 0 | **superseded** |
| — | 0 | **absorbed** |

**Expected on re-derivation:** 114 IDs = 98 `FR-*` + 16 `NFR-*`. Of these, 88 are attempt-1 IDs
carried at their original ordinals (77 `FR-*` + 11 `NFR-*`, matching the retired document exactly),
and 26 are new (21 `FR-*` + 5 `NFR-*`). Zero attempt-1 IDs are renumbered, zero deleted, zero
superseded, zero absorbed. A re-derivation that finds an attempt-1 ID missing from this document is
a defect in this document, not a permitted simplification.

<!-- Last line. Expected on re-derivation: this comment is the final line of the file. -->

