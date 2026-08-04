# Requirements: non-code-feature-track

<!-- This file is owned by the requirements-agent. Do not edit manually during SDD workflow. -->

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
single code path — it never bypasses, weakens, or shortcuts the gate. All changes are to agent
definitions (markdown contracts), tests under `tests/`, and documentation, **all of them inside
this repository**; the corresponding copies under `~/.claude/` are synchronised after merge by
the operator running `./install.sh` (FR-12.1, NFR-10). No CI change.

This is a change to the SDD framework source repository itself. The feature being specified
governs how the pipeline handles non-code (including vault-update) features in **consumer**
projects; this repository has no knowledge vault of its own, so no vault-reader/vault-writer
routing applies to the work itself.

### Definitions used throughout

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
  source, tests, scripts, hooks, CI workflows, templates, runtime configuration, and any
  prose file the project designates as a behaviour-bearing contract (in this repository, for
  example, `agents/*.md` and `commands/*.md`).
- **Non-code feature** — a feature every one of whose tasks declares only non-code artifacts as
  its outputs.
- **`featureClass`** — the classification value recorded in `.spec-state.json`; one of `"code"`
  or `"non-code"`.
- **Non-code review scope** — the artifact set a reviewer reviews when the git diff is empty or
  contains only non-code artifacts (defined normatively in FR-6).

Each requirement is annotated with its `scope.md` driver: problem-statement items **P1** (validator
tests-required), **P2** (reviewers' undefined verdict on empty/non-code scope), **P3** (single
`ready-to-merge` application point / CI deadlock); resolved questions **O1–O4**; reconciled
discrepancies **D1–D2**.

Two further drivers appear below, both amendments made after the initial document was drafted.

**A1** — an amendment made at requirements confirmation. A1 removes the assumption that the
pipeline itself writes the global `~/.claude/CLAUDE.md`. Writing it during implementation would
mutate the operator's live global configuration before the pull request is reviewed or merged, and
would be an out-of-repo write invisible in the PR diff — weakening the exact audit trail this
feature exists to protect. A1 touches FR-11.8, FR-12/FR-12.1, NFR-10, AC-8, AC-10, and — for
consistency only — FR-7.3, the Overview, and the Out of Scope list. It changes no locked `scope.md`
decision (O1–O4, D1–D2), and no requirement is renumbered.

**A2** — an amendment made during design, raised by the design-agent and accepted by the
orchestrator under standing authority. A2 resolves a contradiction A1 left in FR-11.8: A1 confined
its byte-identity carve-out to exactly **one** assertion while simultaneously requiring that every
other assertion in `tests/` remain unweakened — but `test_repo_and_global_copies_are_byte_identical`
(`tests/test_orchestrator_label_lifecycle.py:270`) has the same construction, asserting
byte-identity between `agents/orchestrator.md` and its global copy and skipping only when the
global copy is absent or unreadable. The two copies are byte-identical at the time of this
amendment, so the assertion passes today and fails the moment this feature's first edit to
`agents/orchestrator.md` lands; FR-1, FR-2 and FR-3 each require editing that file, so the
collision is unavoidable rather than hypothetical, and A1's two clauses cannot both hold. A2
extends the carve-out to cover **both** assertions under identical constraints and **closes it at
two**; the `install.sh` test modules are unaffected, because they point `HOME` at a throwaway
temporary directory. A2 touches FR-11.8, AC-8 and AC-10, plus this preamble, the Out of Scope list,
and the Open Questions note. It changes no locked `scope.md` decision (O1–O4, D1–D2), and no
requirement is renumbered.

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

*(drivers: D2)*

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

##### FR-6.2
**The system shall** specify the scope-resolution order: attempt the existing diff
(`git diff` for `task` mode, `git diff <base>...HEAD` for `feature` mode) first; **if** that diff
is empty or contains only non-code artifacts, resolve the non-code review scope and review it.

##### FR-6.3
**The system shall** require each reviewer to emit exactly one of `PASS` or `FAIL` for a non-code
or empty scope — a hedge, an abstention, an "N/A", or a "nothing to review" is not a permitted
outcome (P2).

##### FR-6.4
**If** the resolved non-code review scope contains no artifact at all — no changed non-code file,
no spec artifact change attributable to the feature's tasks, and no vault changelog entry — **then
the system shall** require the reviewer to return `FAIL` stating that the feature produced no
reviewable output, so an empty feature can never reach `ready-to-merge`.

##### FR-6.5
**The system shall** require each reviewer's `Scope Reviewed` section to enumerate the non-code
review scope actually inspected, including the vault changelog entries by target and operation, so
the verdict is auditable.

##### FR-6.6
**The system shall** keep the existing severity model unchanged in non-code scope: any Critical or
High finding blocks; Medium and Low are reported and do not block.

##### FR-6.7
**The system shall** keep both reviewers read-only with their existing tool sets; resolving the
non-code scope shall require no new tool and no new write target.

##### FR-6.8
**The system shall** require reviewers to read the in-repo vault changelog only, never the
knowledge-vault notes themselves; **if** a reviewer needs a vault fact to judge a change, **then
the system shall** have it halt with `VAULT REQUEST: <need>` per the existing isolation rule.

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

##### FR-9.1
**The system shall** introduce no alternative path, exemption, auto-pass, or override by which a
non-code feature obtains `ready-to-merge` without a genuine whole-feature review PASS.

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
fallback (FR-3).

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
**The system shall** provide a regression assertion that `ready-to-merge` is still set in exactly
one place in `agents/orchestrator.md`, and that the non-code path introduces no second
application point (FR-9.1).

##### FR-11.7
**The system shall** provide an assertion that `ci-templates/workflows/sdd-review-gate.yml` still
requires `ready-to-merge`, still fails on any `blocked:*` label, and contains no bypass or
exemption label.

##### FR-11.8

*(drivers: O4, D2, cross-cutting rules; **A1** — amended at requirements confirmation; **A2** —
amended during design)*

**The system shall** keep the existing test suite passing, and no existing assertion is deleted or
weakened to accommodate the new track, with exactly **two** deliberate, documented exceptions:

1. `test_two_claude_files_byte_identical` in `tests/test_docs_updates.py` (lines 227–238), which
   asserts byte-identity between the repository-root `CLAUDE.md` and the global copy and skips
   only when the global file is unreadable — so it no-ops in CI but enforces locally (**A1**).
2. `test_repo_and_global_copies_are_byte_identical` at
   `tests/test_orchestrator_label_lifecycle.py:270`, which asserts byte-identity between
   `agents/orchestrator.md` and its global copy `~/.claude/agents/orchestrator.md` and skips only
   when the global copy is absent or unreadable (lines 274–279) — the same construction, and this
   feature edits `agents/orchestrator.md` (**A2**).

Both pairs of copies are byte-identical at the time of this amendment, so both assertions pass
today. Under FR-12.1 and NFR-10 the repository copy of each of these two documents legitimately
moves ahead of the unsynced global copy during this feature — and FR-1, FR-2 and FR-3 each require
editing `agents/orchestrator.md` — so both assertions would fail mid-feature and block the pipeline.

**The system shall** constrain both exceptions as follows; they are an amendment, not a licence to
gut the checks. Except where a bullet names one assertion specifically, every constraint below
applies identically to each of the two:

- **The system shall not** delete either assertion, and **shall** keep each able to fail on genuine
  drift — content the repository copy states that the global copy is missing or contradicts.
- **For the `CLAUDE.md` assertion (A1)**, the class of check that must survive is the one
  `test_two_claude_ownership_lines_consistent` (`tests/test_docs_updates.py:212`) already performs:
  comparison of the normalised Agent-Ownership invariant lines across the two copies. A global copy
  missing an Agent-Ownership invariant phrase shall still be caught.
- **For the `agents/orchestrator.md` assertion (A2)**, the surviving drift check **shall** compare
  the orchestrator's **invariant instruction lines** across the two copies rather than their raw
  bytes. The invariants that **shall** remain checked are: (a) the `ready-to-merge`
  single-application-point rule together with the clear-`blocked:*`-before-set ordering; (b) the
  clear-**every**-recorded-`blocked:*`-label wording; (c) the scaffold-push-only-on-first-scaffold
  scoping; and (d) the "never runs `gh` / `git push` yourself; github-agent is the only component
  that does" framing. A readable global copy that omits or contradicts any one of these is genuine
  drift and **shall** still fail. The drift discriminator **shall not** be a blanket skip taken
  whenever the two copies differ.
- **The system shall** have each assertion tolerate the "repository copy ahead, global copy not yet
  synced by `./install.sh`" state specifically, treating byte-identity as **satisfied-or-pending**
  rather than pass-or-fail.
- **Where** an assertion resolves its global path, **the system shall** permit deriving it from
  `Path.home()` in place of the hardcoded absolute path — `/Users/jamie.zaikov/.claude/CLAUDE.md`
  at `tests/test_docs_updates.py:35`, and `/Users/jamie.zaikov/.claude/agents/orchestrator.md` at
  `tests/test_orchestrator_label_lifecycle.py:36` — a portability defect whose correction is in
  scope for the task that reworks that assertion — and shall permit no change beyond that to either
  module's scope.
- **The system shall** record the rationale for the carve-out in each reworked assertion itself
  (for example its docstring), citing FR-11.8 and NFR-10, so a reviewer reads it as a deliberate
  amendment rather than an unexplained regression.
- **The system shall** confine the carve-out to these **two** assertions and no others: every other
  assertion in `tests/`, in these two modules and in all others, remains undeleted and unweakened.

**The carve-out is closed at two (A2).** **The system shall** treat
`test_two_claude_files_byte_identical` and `test_repo_and_global_copies_are_byte_identical` as the
**only** assertions in the suite that compare an in-repo file against a **live** global copy under
`~/.claude/`, and **shall** permit no third carve-out under this feature. This was verified at
amendment time: the four other agent definitions this feature edits — `agents/task-tester.md`,
`agents/task-validator.md`, `agents/code-reviewer.md`, `agents/security-reviewer.md` — carry no
global-copy identity assertion at all; and the only other test modules referencing `~/.claude`
(`tests/test_install_pre_push_hook.py` and `tests/test_sdd_init_ci_templates.py`) point `HOME` at a
throwaway temporary directory, so they are not live-global checks, are unaffected by the
pending-sync window, and **shall not** be modified. **If** a further live-global identity assertion
is discovered or introduced, **then the system shall** require a fresh amendment to this
requirement rather than an extension of this carve-out by analogy.

**Running `./install.sh` mid-feature is not an acceptable resolution** for either exception.
NFR-10 forbids resolving the pending-sync window by writing to `~/.claude`, and A1's rationale rules
out mutating the operator's live global configuration before the pull request is reviewed or
merged. The operator runs the installer **after merge**.

*Amendment rationale (A2):* the second assertion has the same construction and the same failure
cause as the first. A1's confinement of the carve-out to exactly one assertion, together with its
clause that no other assertion in `tests/` is weakened, cannot both hold once this feature edits
`agents/orchestrator.md`; left unamended, implementation blocks at the first orchestrator edit. A2
resolves that contradiction by extending the carve-out to the second assertion under identical
constraints, and closes it there.

*How* each assertion is reworked is a design decision; this requirement fixes only what must remain
true of it.

### Documentation

#### FR-12: CLAUDE.md update (repository copy; global copy synced by the installer)

*(drivers: scope.md "In v1" — docs; **A1** — amended at requirements confirmation)*

**The system shall** update the pipeline description in the repository-root `CLAUDE.md` to
describe feature classification and the non-code track — tests-optional artifact-conformance
validation and the reviewers' defined verdict for empty/non-code scope — while restating that
`ready-to-merge` still requires a real whole-feature review PASS.

##### FR-12.1

*(drivers: scope.md "In v1" — docs; **A1** — amended at requirements confirmation)*

**The system shall** confine this feature's `CLAUDE.md` edit to the repository copy at the
repository root, and **shall not** have any pipeline stage write to `~/.claude/CLAUDE.md` or to
any other path under `~/.claude/` at any point during implementation.

**The system shall** treat the global copy as a derived install artifact synchronised **after the
pull request is merged**, by the operator running `./install.sh`. That installer is the audited
sync mechanism: it copies each `agents/*.md` and each `commands/*.md` into `~/.claude/agents/` and
`~/.claude/commands/`, using `cmp -s` to skip files that are already identical and reporting each
file as installed, updated, or unchanged; it copies the repository `CLAUDE.md` to
`~/.claude/CLAUDE.md`, again guarded by `cmp -s`, and where an existing global copy differs it
prompts the operator to overwrite, append, or skip rather than overwriting silently; and, on
explicit opt-in, it copies the `hooks/secret-*.py` scripts into `~/.claude/hooks/` and stages the
CI templates under `~/.claude/ci-templates/`. Because it covers `agents/*.md`, the installer also
propagates the changed agent definitions (`agents/orchestrator.md`, `agents/task-tester.md`,
`agents/task-validator.md`, `agents/code-reviewer.md`, `agents/security-reviewer.md`), which this
requirement's `CLAUDE.md` edit does not.

*Amendment rationale (A1):* having the pipeline edit `~/.claude/CLAUDE.md` during implementation
would mutate the operator's live global configuration before the pull request is reviewed or
merged, and would be an out-of-repo write invisible in the PR diff — weakening the exact audit
trail this feature exists to protect.

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

*(drivers: scope.md "In v1" — docs; **A1** — amended at requirements confirmation)*

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
- **AC-4** — A "non-code" feature that produced no artifact at all receives a reviewer `FAIL`, not
  a PASS. *(FR-6.4)*
- **AC-5** — No reviewer can emit a non-verdict (hedge/N/A) for an empty or non-code scope.
  *(FR-6.3)*
- **AC-6** — `git diff` for this feature shows no change to
  `ci-templates/workflows/sdd-review-gate.yml`, no new workflow, and no new label name anywhere.
  *(FR-10, NFR-2)*
- **AC-7** — `ready-to-merge` appears as a *set* operation in exactly one place in
  `agents/orchestrator.md`, verified by a test. *(FR-9.1, FR-11.6)*
- **AC-8** — Every changed agent contract has at least one corresponding assertion under `tests/`,
  and the pre-existing test suite passes, with exactly two deliberate, documented exceptions: the
  reworked `test_two_claude_files_byte_identical` (`tests/test_docs_updates.py`) and the reworked
  `test_repo_and_global_copies_are_byte_identical`
  (`tests/test_orchestrator_label_lifecycle.py`), both constrained by FR-11.8 and no third
  permitted. No other existing assertion is deleted or weakened, and the `install.sh` test modules
  (`tests/test_install_pre_push_hook.py`, `tests/test_sdd_init_ci_templates.py`) are unmodified.
  *(FR-11, FR-11.8; A1, A2)*
- **AC-9** — A code-bearing feature run end-to-end behaves identically to before this change.
  *(NFR-4)*
- **AC-10** — The repository-root `CLAUDE.md` and the README describe the classification step and
  the non-code track; the feature's diff and working tree contain no write to
  `~/.claude/CLAUDE.md` or to any other path under `~/.claude/`; `tests/test_docs_updates.py`
  passes while the repository copy is ahead of an unsynced global copy, yet still fails when a
  readable global copy contradicts or omits an Agent-Ownership invariant line carried by the
  repository copy; and `tests/test_orchestrator_label_lifecycle.py` passes while the repository
  copy of `agents/orchestrator.md` is ahead of an unsynced global copy, yet still fails when a
  readable global copy omits or contradicts any one of the orchestrator invariant instruction
  lines named in FR-11.8 — the `ready-to-merge` single-application-point and
  clear-`blocked:*`-before-set ordering, the clear-every-recorded-`blocked:*`-label wording, the
  scaffold-push-only-on-first-scaffold scoping, or the never-runs-`gh`/`git push`-yourself
  framing. *(FR-12, FR-12.1, FR-13, FR-11.8, NFR-10; A1, A2)*

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
  of the post-merge global sync (A1).
- Any third live-global byte-identity carve-out beyond the two fixed in FR-11.8, and any
  modification of the `install.sh` test modules; a further carve-out requires a fresh amendment
  (A2).

## Open Questions

- None. All open questions (O1–O4) and both discrepancies (D1, D2) were resolved and locked in
  `scope.md` during pre-orchestrator scoping. The A1 amendment was raised and accepted at
  requirements confirmation and touches no locked decision. The A2 amendment was raised by the
  design-agent during design and accepted by the orchestrator under standing authority; it
  likewise touches no locked decision.
