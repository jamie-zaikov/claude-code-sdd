# Design: non-code-feature-track

<!-- This file is owned by the design-agent. Do not edit manually during SDD workflow. -->

## Overview

This feature adds a **first-class non-code track** to the SDD pipeline. The change is made entirely
in prose contracts (`agents/*.md`), tests (`tests/*.py`), and documentation (`CLAUDE.md`,
`README.md`) inside this repository. No CI template change, no new agent, no new tool grant, no new
write target, no new label.

The design has five moving parts:

1. **A classification gate** in `agents/orchestrator.md` that runs once, after the consistency gate
   passes and before `phase` becomes `implementation`. It reads the confirmed `tasks.md`, classifies
   the feature `code` or `non-code` from the outputs the tasks *declare they will produce*, records
   the value and its basis in `.spec-state.json`, and reports both to the user. Ambiguity resolves to
   `code`.
2. **Routing**: the orchestrator forwards `featureClass` (and, per task, whether that task's declared
   outputs contain application code) to the tester, the validator and both reviewers. On the `code`
   path the forwarded values change nothing — every stage behaves exactly as today.
3. **Two new agent modes**: `task-tester` gains a defined *no-code behaviour*; `task-validator` gains
   an *artifact-conformance mode* entered only on the orchestrator's instruction, in which missing
   unit tests are not a FAIL but a placeholder artifact is.
4. **A shared non-code review scope** in both reviewers: when the diff for the reviewer's mode is
   empty or contains only non-code artifacts, the reviewer resolves and reviews the union of the
   feature's spec artifacts, the non-code files in the diff, and the vault changelog at
   `.specs/features/<feature-name>/vault/.write-log.jsonl` — then emits exactly one of `PASS` or
   `FAIL`. An empty resolved scope is a `FAIL`.
5. **A monotonic fallback**: any evidence that a task in a `non-code` feature touched application
   code reclassifies the feature to `code`, withdraws the exemption, and re-runs the task's test and
   validation stages under the code path.

The `ready-to-merge` application point in `agents/orchestrator.md` is **not touched**. A non-code
feature reaches it by producing two genuine reviewer PASSes over a real artifact set, through the one
existing branch.

### Structural note: this repository's "code" is prose

Requirements classify `agents/*.md` and `commands/*.md` as **application code** — behaviour-bearing
prose contracts. That classification is load-bearing here: it is precisely why *this* feature is
code-bearing (it edits five agent contracts and adds Python tests) and therefore runs the unchanged
code path while building the non-code path. The design must not weaken that definition to make its
own life easier; see R2 in *Risks*.

### Bootstrapping / ordering hazard (read before sequencing tasks)

The artifacts this feature edits are the same artifacts that govern the pipeline running it. Two
consequences:

- **Contract swap mid-flight.** The live fleet resolves agent definitions from `~/.claude/agents/`,
  not from this repository's `agents/`. FR-12.1 and NFR-10 forbid the pipeline writing anywhere under
  `~/.claude/` during implementation. That prohibition is not only an audit rule: it is the mechanism
  that keeps the running fleet on a single, coherent contract version for the whole feature. If the
  pipeline synced agent files mid-feature, task N+1 could run with a tester that knows the no-code
  behaviour and an orchestrator that does not yet pass `featureClass` — an internally inconsistent
  fleet, and a behavioural change invisible in the PR diff. The design therefore treats the
  repository copies as **inert until `./install.sh` runs post-merge**, and no task may run the
  installer or write to `~/.claude/`.
- **Intermediate-commit breakage.** Every repo-vs-global byte-identity assertion in `tests/` starts
  failing the moment its repository-side file is edited. This constrains task order (see *Sequencing
  constraints*) and produces one genuine requirements conflict (see *Conflict C-1*).

## Architecture

### Components

Component IDs are referenced by the traceability table.

---

#### C0 — Non-code artifact allow-list (normative block, replicated verbatim)

The allow-list is needed by five agents (orchestrator, tester, validator, both reviewers). Agent
contracts have no include mechanism — each `.md` is installed standalone — so the block is
**replicated verbatim** into all five files under an identical heading, and a test asserts the five
copies are normalised-identical (C12 / `test_allow_list_blocks_identical`).

Heading (exact, in all five files):

```
#### Non-code artifact allow-list (normative — identical in every agent that classifies)
```

Body: a single fenced block whose content is the definition from `requirements.md`, unparaphrased:

```
NON-CODE ARTIFACT — exactly one of:
  1. a spec artifact under .specs/features/<feature-name>/
     (requirements.md, design.md, tasks.md, scope.md, .spec-state.json)
  2. a committed prose/documentation file that the project's layout or steering does NOT
     designate as source, agent/prompt contract, template, script, or configuration
  3. a knowledge-vault mutation recorded by vault-writer in
     .specs/features/<feature-name>/vault/.write-log.jsonl

APPLICATION CODE — anything else: executable source, tests, scripts, hooks, CI workflows,
  templates, runtime configuration, and any prose file the project designates as a
  behaviour-bearing contract (in this repository: agents/*.md and commands/*.md).
```

---

#### C1 — `agents/orchestrator.md`: Feature Classification Gate

**Placement.** A new `###`-level section inserted **between** the existing
`### Consistency Gate (runs automatically after tasks confirmed, before implementation)` section and
the existing ``### `implementation` `` section.

**Heading (exact anchor):**

```
### Feature Classification Gate (runs automatically after the consistency gate, before implementation)
```

**Contract text — required content and intent:**

1. *When it runs.* Immediately after the consistency gate resolves PASS (including the `(d) override
   and proceed` path), in the **same state-file write** that sets `phase = "implementation"`. It runs
   exactly once per feature. On resume, if `featureClass` is already present, it is not re-run.
2. *Inputs.* (a) the confirmed `tasks.md` — every task's declared outputs, taken primarily from the
   task's **`**Files:**` field**, which the task template already defines at `agents/tasks-agent.md:62`
   as `**Files:** <Expected files to create or modify>`, and secondarily from the task body and its
   sub-tasks where the field is absent or incomplete. Naming the existing template field explicitly is
   what makes this procedure implementable **with no change to `agents/tasks-agent.md`** — the
   classification input already exists in every conformant task list. (b) `design.md`, used only to resolve a
   task whose outputs are named by component rather than by path; (c) `.specs/steering/structure.md`
   and `tech.md` for the project's designation of what is source, contract, template, script, or
   configuration. It **never** inspects a git diff to classify (D1, FR-1.2) — at this point in the
   lifecycle nothing has been implemented, which is the structural reason the rule holds.
3. *The allow-list.* C0's block appears verbatim here; this file is its normative home.
4. *Per-output rule.* An output is non-code iff it matches one of the three allow-list categories;
   otherwise it is application code.
5. *Per-feature rule.* `featureClass = "non-code"` iff **every** task declares at least one output
   **and** every declared output of every task classifies non-code. Otherwise `"code"` (FR-1.3).
6. *Fail-safe (FR-1.4).* Classify `"code"` whenever the answer is not unambiguous. The contract
   enumerates the ambiguity triggers so the rule is checkable rather than a mood: a task declares no
   outputs at all; an output cannot be resolved to a concrete path or to one of the three categories;
   a prose file sits inside a directory that steering designates as source/contract/template; or
   steering is silent and the file's location does not settle it. The text states plainly that
   `"code"` is the fail-safe direction because it preserves today's behaviour exactly.
7. *Record + report (FR-1.5, NFR-5).* Write `featureClass` and the `classification` object (C2) to
   `.spec-state.json`; report to the user the recorded value **and** the basis — one line per task
   naming its declared outputs and their classification.
8. *Override (FR-1.6).* An override toward `"code"` is always honoured. An override toward
   `"non-code"` is honoured **only** if the FR-1.3 test already holds for the confirmed tasks;
   otherwise the orchestrator refuses, states which task's declared output is application code, and
   keeps `"code"`. Every override — accepted or refused — is recorded (C2).
9. *Legacy state (FR-1.7).* If `featureClass` is absent from an existing state file, treat the
   feature as `"code"` and proceed on the unchanged code path. Do not retro-classify.

**Explicitly absent from this section:** any mention of `ready-to-merge`, any label operation, any CI
reference. The classification gate performs no GitHub action.

---

#### C2 — `agents/orchestrator.md`: `.spec-state.json` schema delta

**Placement.** The `## State File Management` section: the initialization JSON block and the prose
paragraph following it.

**Delta to the initialization block** — two new sibling top-level keys, added after `taskStatus`:

```json
  "featureClass": null,
  "classification": {
    "basis": null,
    "decidedAt": null,
    "override": null,
    "tasksValidatedUnderExemption": [],
    "reclassification": null
  },
```

**Schema prose added under the block** (this is the text FR-1.1 requires and C12 asserts):

- `featureClass` — the feature classification. Permitted values: `"code"` or `"non-code"`. `null`
  before the classification gate has run. Absent in a state file written before this change; read it
  with a default of `"code"` (FR-1.7).
- `classification.basis` — a human-readable string recording which tasks' declared outputs drove the
  value (FR-1.5).
- `classification.decidedAt` — ISO-8601 timestamp of the classification gate.
- `classification.override` — `null`, or
  `{ "by": "user", "requested": "code"|"non-code", "accepted": true|false, "reason": "<one line>" }`
  (FR-1.6).
- `classification.tasksValidatedUnderExemption` — array of task numbers whose validation ran in
  artifact-conformance mode (FR-3.3).
- `classification.reclassification` — `null`, or
  `{ "from": "non-code", "to": "code", "task": <N>, "paths": ["<path>", ...],
  "trigger": "tester"|"validator"|"orchestrator", "at": "<iso8601>" }` (FR-3.1).

The value lives in exactly one place — `featureClass` — so there is a single source of truth; the
`classification` object carries only provenance.

---

#### C3 — `agents/orchestrator.md`: per-task routing

**Placement.** Inside ``### `implementation` ``, in the existing Stage 2, Stage 3, and Stages 4 & 5
input bullet lists. No new stage, no reordering (FR-2.4).

**Delta.** A short shared preamble is added immediately above **Stage 1**, naming the two values
forwarded to every stage:

- `featureClass` — the current value from `.spec-state.json`.
- `taskProducesApplicationCode` — `true`/`false`, derived for *this task* from its declared outputs
  using the C0 allow-list.

Stage-specific additions, one bullet each:

- **Stage 2 (task-tester)** — "…plus `featureClass` and `taskProducesApplicationCode`. **Where**
  `featureClass` is `"non-code"` **and** `taskProducesApplicationCode` is `false`, instruct the tester
  to apply its **no-code behaviour**" (FR-2.1).
- **Stage 3 (task-validator)** — "…plus `featureClass` and `taskProducesApplicationCode`. **Where**
  `featureClass` is `"non-code"` **and** `taskProducesApplicationCode` is `false`, instruct the
  validator to run in **artifact-conformance mode**. The validator never selects this mode itself;
  the instruction is the only entry point (FR-5.1). When you issue it, append the task number to
  `classification.tasksValidatedUnderExemption`."
- **Stages 4 & 5 (reviewers)** — "…plus `featureClass`. Everything else about the invocation is
  unchanged: `mode: task`, both concurrent, both Opus."

**NFR-4 guard sentence**, stated once in the preamble: *"Where `featureClass` is `\"code\"`, these two
values change nothing — every stage runs exactly as it does today: same stages, same order, same
verdict formats, same labels, no additional user prompt."* (FR-2.3.)

---

#### C4 — `agents/orchestrator.md`: reclassification fallback

**Placement.** A new `####`-level subsection at the end of ``### `implementation` ``, after the
`On **fail**` bullet.

**Heading (exact anchor):**

```
#### Reclassification: non-code → code (fallback, D2)
```

**Contract text.**

*Triggers* — any one of:

- **T1** the task-tester reports that the task in fact produced application code (FR-4.5);
- **T2** the task-validator returns FAIL citing application-code modification under
  artifact-conformance mode (FR-5.6);
- **T3** the orchestrator itself sees an application-code path in the executor's changed-files
  summary.

*Actions on any trigger:*

1. Set `featureClass = "code"` in `.spec-state.json` and populate `classification.reclassification`
   with the triggering path(s), the task number, the trigger source and the timestamp (FR-3.1).
2. Report the reclassification to the user, naming the file(s) and the task (FR-3.1, NFR-5).
3. Re-run the current task's **Stage 2 (test)** and **Stage 3 (validation)** under the code path —
   tests required — before the task may be marked complete (FR-3.2).
4. Keep `classification.tasksValidatedUnderExemption` as written. It is a permanent record, not a
   live flag. When it is non-empty and the feature has been reclassified, the Feature Review Gate
   invocation must state that those tasks' outputs are to be reviewed under the code path (FR-3.3).
5. **Monotonic** (FR-3.4): once `featureClass` is `"code"` it is never set back to `"non-code"` for
   the remainder of the feature — not by a later task producing only artifacts, and not by a user
   override.

*Retry accounting (an ambiguity the contract must settle explicitly).* T2 is a genuine validator FAIL
and flows through the **existing** `On **fail**` branch unchanged: `retryCount += 1`,
`blocked:validation` set, executor re-run. T1 and T3 are caught **before** a validation verdict
exists; they re-run stages 2–3 within the same attempt and do **not** increment `retryCount` and do
**not** set a label. No new label is introduced on any path (FR-10.1).

---

#### C5 — `agents/orchestrator.md`: Feature Review Gate

**Placement.** The existing
``### Feature Review Gate (runs automatically after the last task completes, before `complete`)``
section, invocation bullets only.

**Delta — one added bullet in the "Pass each:" list:**

> - `featureClass`. **Where** it is `"non-code"`, add the **non-code review scope** instruction: the
>   diff for `feature` mode will be empty or contain only non-code artifacts, so the reviewer resolves
>   and reviews the non-code review scope defined in its own contract, and must return exactly one of
>   `PASS`/`FAIL`. **Where** `classification.tasksValidatedUnderExemption` is non-empty **and** the
>   feature was reclassified, additionally state that those tasks' outputs are to be reviewed under
>   the code path (FR-3.3).

The invocation stays concurrent and Opus-pinned (FR-2.2).

**Hard constraint held: the `**On PASS (both reviewers PASS)**` branch is edited in no way.** It
retains the single `label set ready-to-merge` operation, the preceding `blocked:feature-review` clear,
and the "This is the **only** place `ready-to-merge` is ever applied" sentence. No class-conditional
wording is added anywhere in that branch — a non-code feature reaches it by the same condition (both
reviewers PASS) as a code feature (FR-9, FR-9.1, FR-9.2, FR-9.3, NFR-1).

**One added line in `## Critical Rules`**, adjacent to the existing `ready-to-merge` rule:

> - NEVER treat `featureClass: "non-code"` as an exemption from any gate. It changes which artifacts
>   the tester, validator and reviewers examine — never whether they run, and never what a PASS
>   requires.

---

#### C6 — `agents/task-tester.md`: no-code behaviour

**Placement.** A new `##`-level section between `## Testing Rules` and `## Completion Summary`, plus
one added rule in `## Rules`.

**Heading (exact anchor):**

```
## No-Code Behaviour (tasks that produce no application code)
```

**Contract text:**

1. *Entry.* Applies when the orchestrator states `featureClass: non-code` and
   `taskProducesApplicationCode: false`. Carries C0's allow-list block verbatim.
2. *Prohibition (FR-4.1).* Do **not** write vacuous or placeholder tests to satisfy the tests-exist
   expectation. Named and forbidden: an assertion that cannot fail; a test asserting only that a file
   exists when the requirement is about its content; a test asserting a constant; a test with no
   assertion. The contract states the reason: a vacuous test is worse than no test, because it
   converts a known gap into a false signal.
3. *Preferred path (FR-4.2).* Where a produced artifact is machine-checkable, **write the check** in
   the project's conventional test directory following the project's existing test patterns.
   Enumerated examples: a structural or content lint over a markdown contract; a schema or frontmatter
   check; a link/path-resolution check; a cross-file consistency check between two copies of a
   document.
4. *Fallback (FR-4.3).* Only if no meaningful machine check is feasible, emit the **"no applicable
   tests" completion block** (I2) naming each produced artifact, the requirement it satisfies, and why
   no automated check is feasible. The contract states that an empty or improvised summary is not an
   acceptable substitute — the outcome must be explicit and auditable.
5. *Always (FR-4.4).* Run the project's existing tests in the affected area and report regressions, in
   every case, exactly as today.
6. *Escalation (FR-4.5).* If the task in fact produced application code, report that fact to the
   orchestrator — naming the path(s), which triggers reclassification — and write tests for that code
   normally. Do not apply the no-code behaviour to it.

**Added `## Rules` line:** `NEVER write a placeholder or vacuous test to satisfy a tests-exist
expectation; emit the "no applicable tests" block instead.`

---

#### C7 — `agents/task-validator.md`: artifact-conformance mode

**Placement.** Three edits.

**(a) `## Validation Checklist` → `### 2. Test Coverage`** (current lines 38–41). The three checkboxes
are **not deleted**; the heading gains a mode qualifier and a conditional lead-in, so the code path
reads identically to today:

```
### 2. Test Coverage  *(code mode)*
```

with a lead-in sentence: *"In artifact-conformance mode this section is replaced by §2A below; in all
other cases it applies unchanged."* A new sibling subsection follows:

```
### 2A. Artifact Conformance  *(artifact-conformance mode only)*
```

**(b) A new `##`-level section** between `## Validation Checklist` and `## Verdict`:

```
## Artifact-Conformance Mode
```

Contract text:

1. *Entry is instruction-only (FR-5.1).* The mode is entered **only** when the orchestrator's prompt
   states it. The contract says in as many words: *never self-selected by the validator because a diff
   looked empty.* Carries C0's allow-list block verbatim.
2. *Mapping (FR-5.2).* Map every cited requirement to at least one **named produced artifact** — a
   file path, or an identified entry in `.specs/features/<feature-name>/vault/.write-log.jsonl`
   (identified by its `operation` + `target`, and `section` where present) — and **read** that
   artifact. A requirement with no mapped artifact is a FAIL.
3. *Substance (FR-5.3).* For each mapped artifact: it exists, it is non-empty, and it substantively
   states or delivers what the cited requirement demands. A placeholder, stub, TODO-only, or
   heading-only artifact is a **FAIL**. For a changelog-mapped requirement, the entry's `target`,
   `operation` and `intent` must be consistent with the requirement (the validator reads the
   changelog, never the vault note — NFR-8).
4. *Tests (FR-5.4).* In this mode the absence of unit tests is **not** a failure. This replaces the
   unconditional "at least one test exists for this requirement" check **for this mode only**; §2 is
   unchanged everywhere else.
5. *Machine checks (FR-5.5).* If checks were written for the artifacts (FR-4.2), run them with Bash
   and **FAIL if any check fails**.
6. *Code detection (FR-5.6).* If any file modified by this task is application code per the
   allow-list, **refuse the exemption**, return `FAIL`, and report the offending path(s) so the
   orchestrator reclassifies (FR-3). The contract states that the correct response is a FAIL and a
   report — never a silent switch to code-mode validation, because the orchestrator owns the
   classification.
7. *Retained checks (FR-5.7).* §3 Scope Check and §4 Quality Check remain fully active: no scope
   creep, conventions in `.specs/steering/tech.md` respected, no leftover TODOs.
8. *All-or-nothing (FR-5.9).* Unchanged: if any cited requirement fails, the whole task fails. The
   existing `## Rules` line "NEVER partially pass" is left untouched and is cited from this section.

**(c) `## Verdict`** gains the artifact-conformance verdict block (I3) as an additional labelled
variant. The existing PASS and FAIL blocks are unchanged.

---

#### C8 / C9 — `agents/code-reviewer.md` and `agents/security-reviewer.md`

Both files receive the **same** new section, with verbatim-identical scope-resolution text (asserted
by C12), and each receives its own finding-class list.

**(a) Shared section — placement:** immediately after `## On Invocation`, before `## What to Hunt For`,
in both files.

**Heading (exact anchor, both files):**

```
## Non-Code Review Scope (empty or non-code diff)
```

Contract text (identical in both files):

1. *Trigger is the diff, not the instruction (FR-6.2).* Resolution order: establish the existing diff
   first — `git diff` for `task` mode, `git diff <base>...HEAD` for `feature` mode. Partition the
   changed paths with the C0 allow-list. **If** the diff contains **one or more application-code
   paths**, review it exactly as today and stop here — the non-code scope does not apply. **If** the
   diff is empty **or** contains only non-code artifacts, resolve the non-code review scope and review
   it. The orchestrator may confirm the situation in its prompt; the reviewer does not wait for it.
2. *The scope (FR-6.1)* — the union of:
   - (a) the feature's spec artifacts: `requirements.md`, `design.md`, `tasks.md`, and `scope.md`
     where present, under `.specs/features/<feature-name>/`;
   - (b) every non-code file present in the diff for the reviewer's mode;
   - (c) the vault changelog entries for this feature in
     `.specs/features/<feature-name>/vault/.write-log.jsonl`.
3. *Reading the changelog (FR-6.8, NFR-8).* Read the changelog file itself with `Read`. It is
   JSON-lines; each line carries `operation`, `target`, `intent`, and optionally `section` and
   `bytes`. **Never open the vault note named by `target`.** The in-repo changelog is the entire
   reviewable surface. If judging a change genuinely requires a fact from the vault, halt and return
   `VAULT REQUEST: <need>`; the orchestrator fulfils it through vault-reader.
4. *Mandatory verdict (FR-6.3).* Emit exactly one of `PASS` or `FAIL`. A hedge, an abstention, an
   "N/A", a "nothing to review", or a verdict with no result line is **not a permitted outcome**.
5. *Empty scope is a FAIL (FR-6.4).* If the resolved scope contains no artifact at all — no changed
   non-code file, no spec artifact attributable to the feature's tasks, and no changelog entry —
   return `FAIL` with a single **Critical** finding: *"the feature produced no reviewable output."*
   Modelling it as a Critical finding, rather than as a new verdict kind, means it flows through the
   existing severity rule and the existing FAIL block with no new mechanism.

   **Attribution rule — what counts as "attributable to the feature's tasks".** Without this rule the
   emptiness test can never fire: every feature always has a `requirements.md`, a `design.md` and a
   `tasks.md`, so a literal reading of (a) makes the resolved scope non-empty by construction and
   **AC-4 becomes undischargeable**. The rule:

   - The feature's own `requirements.md`, `design.md`, `tasks.md` and `scope.md` are the **plan**, and
     the plan is never counted as output. Their presence alone never rescues a feature from the
     emptiness test.
   - A spec artifact counts as **output** only when a task declares it in that task's `**Files:**`
     field (the field the task template already defines at `agents/tasks-agent.md:62`), or the
     executor reported writing it in its completion summary.
   - Item (a) of the scope union is therefore *review context* — always read, so a reviewer can judge
     intent — while items (b) and (c), plus any (a) artifact promoted to output by the rule above, are
     the **reviewable output** that the emptiness test in FR-6.4 actually counts.

   This keeps the two roles distinct: the reviewer still reads the plan to judge whether the output
   matches it, but a feature that produced nothing but its own plan is correctly a FAIL.
6. *Scope enumeration (FR-6.5).* The `Scope Reviewed` section must enumerate what was actually
   inspected, and must list each vault changelog entry **by target and operation**.
7. *Severity unchanged (FR-6.6).* Critical or High blocks; Medium and Low are reported and do not
   block.
8. *No new capability (FR-6.7, NFR-3, NFR-9).* Resolving this scope uses only the existing
   `Read`/`Glob`/`Grep`/`Bash` tools. Both reviewers remain read-only; neither gains a tool or a write
   target.

**(b) `agents/code-reviewer.md` — finding classes.** A new `###`-level subsection inside
`## What to Hunt For`:

```
### Non-code scope (FR-7)
```

- **Internal contradiction / unfollowable instruction (FR-7.1)** — statements that contradict each
  other within an artifact, statements that conflict with the confirmed `requirements.md` or
  `design.md`, and instructions that cannot be followed as written (a missing step, a mode or field
  named but never defined, an input required but never produced).
- **Stale or dangling references (FR-7.2)** — broken file paths, dead links, cited requirement or task
  IDs that do not exist, references to renamed or removed artifacts.
- **Duplication / divergence / incompleteness (FR-7.3)** — content duplicated or divergent across the
  reviewed artifacts, **including two synchronised copies of a document where the project keeps such
  copies and both copies are within the reviewed scope**, subject to the pending-sync allowance in
  NFR-10 — a repository copy legitimately ahead of an unsynced installed copy is **not** a finding; an
  installed copy that *contradicts* the authoritative repository copy is. Plus placeholders and
  unresolved TODOs.
- **Vault-update coherence (FR-7.4)** — each recorded write traceable to a requirement; `target`,
  `operation` and `intent` consistent with the stated intent.
- **Blocking findings need a scenario (FR-7.5)** — name the reader or downstream consumer who is
  misled and the wrong outcome that follows. Mirrors the existing rule: *"this looks fragile" is not a
  finding.* Added as a bullet in the reviewer's `## Rules`.

**(c) `agents/security-reviewer.md` — finding classes.** A new `###`-level subsection inside
`## What to Hunt For`:

```
### Non-code scope (FR-8)
```

- **Committed credential material in prose (FR-8.1)** — tokens, keys, passwords, connection strings.
  Report as **type + `path:line` with the value redacted**, never reproduced (NFR-7). For a changelog
  entry, report the entry's `target` plus its line number in the changelog.
- **Sensitive disclosure (FR-8.2)** — internal hostnames, endpoints, account identifiers, PII, or
  infrastructure detail that widens the attack surface if published.
- **Unsafe documented instructions (FR-8.3)** — commands documented for a human or an agent to follow
  that would dump a secret into context, disable a control, or grant broader access than needed. A
  documented unsafe default is a finding in its own right, even if no code implements it yet.
- **Vault-write exposure (FR-8.4)** — changelog entries that would place sensitive material into the
  vault, and entries whose `target` resolves outside the declared vault path.
- **Blocking findings need a scenario (FR-8.5)** — who can reach the artifact and what they gain.
  Added as a bullet in the reviewer's `## Rules`.

---

#### C10 — `agents/vault-writer.md` (unchanged; consumed interface)

**No change.** The changelog path and record shape that the validator and both reviewers now read are
already specified in `## Changelog` (`agents/vault-writer.md:56–64`). This design deliberately
consumes that contract as-is: adding a field or a path would be a new write target and would violate
NFR-3 and the scope's *Deferred* list. See I4 for the record shape as consumed.

---

#### C11 — Documentation

**(a) Repository-root `CLAUDE.md`** (FR-12, FR-12.1, FR-12.2). Edited **only** in the repository; no
pipeline stage writes to `~/.claude/CLAUDE.md` or to any path under `~/.claude/` (FR-12.1, NFR-10).

- Section `### Phase Gates`: the phase line becomes
  `Requirements → Design → Tasks → [Consistency Check] → [Classification] → Implementation → [Feature Review] → Complete`,
  followed by a new paragraph stating: classification is explicit and recorded in `.spec-state.json`
  under `featureClass`; a `non-code` feature runs the same five stages, with the validator in
  artifact-conformance mode (tests optional, a placeholder artifact still FAILs) and both reviewers
  reviewing the spec artifacts, the committed docs and the vault changelog; **`ready-to-merge` still
  requires a real whole-feature review PASS and there is no bypass**; and a non-code feature that
  turns out to touch application code falls back to the full code path (FR-12.2).
- **Constraint (load-bearing).** The edit must **not** alter the three lines that
  `github_agent_lines()` extracts from the `### Agent Ownership` section — the `- github-agent`
  bullet, the "only component that runs `gh`/`git push`" line, and the "No agent modifies another
  agent's artifact" invariant. `test_two_claude_ownership_lines_consistent` compares those three lines
  strictly across the two copies, is **not** carved out by FR-11.8, and would fail during the
  legitimate pending-sync window if any of them changed. Keeping the edit outside those three lines is
  what lets that assertion keep enforcing at full strength (see the A1 resolution).

**(b) `README.md`** (FR-13, FR-13.1). Section `### Review the workflow`: insert a classification step
between the current items 4 (consistency check) and 5 (implementation), renumbering; and extend item 5
to note that for a `non-code` feature the validator runs artifact-conformance and the reviewers review
the resolved non-code scope. Add one sentence stating that **a non-code feature reaches
`ready-to-merge` through the same audited path as a code feature, and no bypass label exists**
(FR-13.1). The `## GitHub integration & CI enforcement` section's label vocabulary is left untouched.

---

#### C12 — Tests (`tests/`)

Seven modules — six new, one confined rework. All follow the established pattern: a module docstring
naming the covered FRs and the run command; paths resolved with
`Path(__file__).resolve().parent.parent`; stdlib-only `unittest`; `split_frontmatter` /
`region_between` / `extract_section` helpers copied locally (each existing module carries its own
copies — no shared helper module is introduced, matching precedent and avoiding a new importable
surface).

| Module | Target | Key assertions | Covers |
|---|---|---|---|
| `tests/test_orchestrator_feature_class.py` | `agents/orchestrator.md` | Classification-gate heading exists and sits **between** the consistency-gate section and the `implementation` section (offset ordering, not mere presence); `featureClass` appears in the state-file JSON block; both permitted values `"code"`/`"non-code"` are named in the schema prose; the fail-safe default is stated (ambiguous / cannot be determined → `code`); classification derives from declared task outputs and the text explicitly disclaims deriving it from a git diff; the five `classification` sub-keys are documented; routing bullets naming `featureClass` appear in the Stage 2, Stage 3, Stages 4 & 5 and Feature Review Gate regions; the NFR-4 guard sentence is present; the reclassification subsection exists, names all three triggers, states monotonicity, and states re-running test + validation | FR-11.2, FR-1.x, FR-2.x, FR-3.x, NFR-5, NFR-6 |
| `tests/test_orchestrator_ready_to_merge_singleton.py` | `agents/orchestrator.md` | Exactly **one** `ready-to-merge` *set* operation in the whole body (regex over `op:\s*set[^}]*ready-to-merge` plus prose `set … ready-to-merge` forms, de-duplicated by offset), and its offset lies inside the Feature Review Gate `On PASS (both reviewers PASS)` region; the "only place `ready-to-merge` is ever applied" sentence survives; **no** `ready-to-merge` token anywhere in the classification-gate or reclassification regions; every `blocked:` label name in the file is drawn from the frozen five-name vocabulary | FR-11.6, FR-9.1, FR-10.1, AC-7 |
| `tests/test_validator_artifact_conformance.py` | `agents/task-validator.md` | `## Artifact-Conformance Mode` heading present; instruction-only entry asserted by the "never self-selected" phrasing **and** by the absence of any self-entry condition; "absence of unit tests is not a failure" scoped to the mode; placeholder/stub/TODO artifact → FAIL; application-code detection → FAIL + reported path (FR-5.6); the literal `.write-log.jsonl` path present; scope and quality checks still referenced as active; the all-or-nothing rule still present; the original `### 2. Test Coverage` checkboxes still present (nothing deleted) | FR-11.3, FR-5.x |
| `tests/test_tester_no_code_behaviour.py` | `agents/task-tester.md` | No-code section heading present; vacuous/placeholder tests prohibited with the enumerated forms; the "no applicable tests" block is specified and names artifact + requirement + why-no-check; the machine-checkable preference precedes the fallback (offset ordering); "run existing tests in all cases" survives; the FR-4.5 escalation present | FR-11.4, FR-4.x |
| `tests/test_reviewers_non_code_scope.py` | both reviewer files, parameterised over the two paths | For each file: the `## Non-Code Review Scope` heading; all three scope components; the literal path `.specs/features/<feature-name>/vault/.write-log.jsonl`; resolution order stated as diff-first-then-fallback; mandatory `PASS`/`FAIL` with hedge/N-A/nothing-to-review explicitly forbidden; the empty-scope FAIL; a "never read the vault note" statement plus the `VAULT REQUEST` escalation; the severity model restated unchanged; the frontmatter `tools:` list **unchanged** from the pre-change set (NFR-3 regression). Plus a cross-file assertion that the shared section is normalised-identical in both reviewers, and `test_allow_list_blocks_identical` asserting the C0 block is normalised-identical across all five agent files. Each reviewer's own finding-class subsection asserted separately | FR-11.5, FR-6.x, FR-7.x, FR-8.x, NFR-3, NFR-8 |
| `tests/test_review_gate_untouched.py` | `ci-templates/workflows/sdd-review-gate.yml` (**read-only**) | `"ready-to-merge" in labels` present; `startswith("blocked:")` present; both `sys.exit(1)` failure branches present; the `github.event_name == 'pull_request'` guard present; `permissions:`/`contents: read` unchanged; **no** token matching `(?i)(bypass|exempt|escape[- ]?hatch|override|skip[-_ ]?gate|non-?code|featureclass)` anywhere in the file; every label-shaped literal drawn from the frozen five-name vocabulary | FR-11.7, FR-10, FR-10.2, NFR-2, AC-6 |
| `tests/test_docs_non_code_track.py` | repo-root `CLAUDE.md`, `README.md` | Repo `CLAUDE.md` names `featureClass`, the classification step in the phase-gate line, the artifact-conformance/tests-optional behaviour, the reviewers' non-code scope, the "still requires a real whole-feature review PASS" restatement, and the fallback-to-code-path sentence; README describes the classification step, the non-code track in the pipeline description, and states no bypass label exists. **Reads only the repository copies** — never touches `~/.claude/` | FR-12, FR-12.2, FR-13, FR-13.1, AC-10 |
| `tests/test_docs_updates.py` **(reworked — the single carve-out)** | see the A1 resolution below | Three edits only: the `GLOBAL_CLAUDE` constant, the new `claude_sync_state()` helper, the reworked `test_two_claude_files_byte_identical` | FR-11.8, NFR-10, AC-8, AC-10 |

Every changed agent contract therefore has at least one corresponding assertion module (AC-8).

---

### Data Model

The only persisted structure this feature adds is the `.spec-state.json` delta specified in **C2**. No
database, no migration. Existing state files without `featureClass` are read with a `"code"` default
and are never rewritten retroactively (FR-1.7).

---

### Interfaces

#### I1 — Orchestrator → stage invocation fields

Two new fields, added to the free-form prompt payload the orchestrator already passes:

```
featureClass:                 "code" | "non-code"
taskProducesApplicationCode:  true | false        # task stages only (Stages 2 & 3)
```

`featureClass` is passed to the tester, the validator and both reviewers, in both `task` and `feature`
mode. On the `code` path both are inert. No field is removed; no existing field changes meaning.

#### I2 — Tester "no applicable tests" completion block (FR-4.3)

Emitted **only** in the no-code case; the existing `## Tester Summary: Task <N>` header is retained so
nothing downstream needs to change.

```
## Tester Summary: Task <N>

### Result: no applicable tests

### Artifacts Produced
- `path/to/artifact.md` — satisfies FR-x — no automated check feasible because <reason>
- vault changelog entry `update workspace-management.md § Variables` — satisfies FR-y — <reason>

### Machine Checks Written
- `tests/test_x.py::test_y` — covers FR-z: <what it verifies>
(or: none)

### Existing Tests Run
- <suite / affected area>: PASS / FAIL (details if fail)

### Issues Found
<Any problems discovered — do not fix, just report>
```

#### I3 — Validator artifact-conformance verdict block (FR-5.8)

Machine-readable and stage-attributable for verbatim PR transcription: the
`## Validator Verdict: Task <N>` header and the `### Result:` line keep their exact existing shape, so
the orchestrator's relay and any parser see the same structure. The `### Mode:` line is emitted **only**
in artifact-conformance mode — the code-path verdict keeps precisely the format it has today (NFR-4).

```
## Validator Verdict: Task <N>

### Result: PASS
### Mode: artifact-conformance

### Requirements Validated
- FR-1: Artifact `path/to/doc.md` ✓ | Substantive ✓ | Tests: n/a (no application code)
- FR-2: Artifact changelog entry `update notes/foo.md § Variables` ✓ | Substantive ✓ | Tests: n/a
- FR-3: Artifact `docs/recon.md` ✓ | Machine check `tests/test_recon.py::test_links` ✓

### Artifacts Reviewed
- `path/to/doc.md` — exists, non-empty, substantive
- `.specs/features/<feature-name>/vault/.write-log.jsonl` — entry 2 of 3

### Notes
<Any minor observations that don't block the pass>
```

The FAIL variant is the existing FAIL block with the same `### Mode: artifact-conformance` line and
per-requirement lines in the same `Artifact … | Substantive ✗` shape.

#### I4 — Vault changelog record (consumed, unchanged)

Produced by `vault-writer` at `.specs/features/<feature-name>/vault/.write-log.jsonl`, one JSON object
per line:

```json
{"operation":"update","target":"workspace-management.md","section":"Variables","intent":"record resolved variable naming rule","bytes":412}
```

Fields consumed by the validator (FR-5.2) and both reviewers (FR-6.1, FR-6.5, FR-7.4, FR-8.4):
`operation`, `target`, `section` (optional), `intent`, `bytes` (optional). Consumers read this file and
**never** the note at `target`. A missing or empty changelog is not an error in itself — it contributes
nothing to the resolved scope, which may then be empty and trigger the FR-6.4 FAIL.

#### I5 — Reviewer non-code verdict block (FR-6.3, FR-6.5)

Existing header, existing `— PASS`/`— FAIL` suffix, existing severity sections. One added line, emitted
**only** when the non-code scope was resolved, plus an enumerated `Scope Reviewed`:

```
## Code Review: <task N | feature> — PASS
### Scope Resolution: non-code (diff empty or non-code artifacts only)

### Scope Reviewed
- spec artifacts: `.specs/features/<f>/requirements.md`, `design.md`, `tasks.md`, `scope.md`
- non-code files in diff: `docs/recon-foo.md`
- vault changelog (`.specs/features/<f>/vault/.write-log.jsonl`), 3 entries:
  - `update` → `workspace-management.md` § Variables
  - `append` → `decisions.md` § 2026-08
  - `create` → `recon/foo.md`

### Findings (non-blocking)
- [Low] `docs/recon-foo.md:42` — <nit>
(or: none)

### Notes
<...>
```

The security-reviewer's block is identical in shape under its own
`## Security Review: <task N | feature> — PASS|FAIL` header.

---

## A1 resolution: reworking `test_two_claude_files_byte_identical`

### The situation

`tests/test_docs_updates.py:35` hardcodes
`GLOBAL_CLAUDE = Path("/Users/jamie.zaikov/.claude/CLAUDE.md")`.
`test_two_claude_files_byte_identical` (lines 227–238) asserts `repo_text == global_text`, skipping
only when the global file is unreadable. It therefore no-ops in CI and enforces locally. FR-12 edits
the repository copy; FR-12.1 forbids writing the global copy. The assertion fails mid-feature.

### The rework

**Path derivation** (the one permitted change beyond the assertion itself, FR-11.8):

```python
GLOBAL_CLAUDE = Path.home() / ".claude" / "CLAUDE.md"
```

A strict improvement: it fixes a portability defect and preserves CI behaviour exactly (in CI
`$HOME/.claude/CLAUDE.md` does not exist → the existing skip fires, as today). No environment-variable
override is added — FR-11.8 permits nothing beyond `Path.home()`.

**A new module-level helper** in the same module (no new file, no new importable surface, so the
carve-out stays confined):

```python
def claude_sync_state(repo_text, global_text):
    """Classify the repo↔global CLAUDE.md relationship: 'satisfied' | 'pending' | 'drift'."""
```

**The three-state discriminator**, evaluated in order:

1. **`satisfied`** — `repo_text == global_text`. Byte-identity holds; nothing to decide.
2. **`drift`** — byte-identity does not hold **and either** of the following is true:
   - **(a) Invariant divergence.** For each key that `github_agent_lines()` extracts from the
     repository copy's `Agent Ownership` section (`bullet`, `gh_line`, `invariant`), the global copy
     must carry that key and its **normalised** value must be equal. A key missing from the global
     copy, or present with a different normalised value, is drift. This is exactly the class of check
     FR-11.8 names as the one that must survive, and exactly NFR-10's definition of genuine drift: the
     global copy *stating a framework invariant differently, or omitting one the repository copy
     carries*.
   - **(b) Heading provenance.** Every ATX heading in the global copy (normalised text, outside code
     fences) must also appear in the repository copy. A heading present **only** in the global copy
     means the global copy carries structural content of unknown provenance — a hand-edit, a different
     lineage, or a fork — which is not a "behind" state and is not resolved by running the installer.
     Containment is directional: headings that exist only in the *repository* copy are the normal
     signature of a pending sync and are fine.
3. **`pending`** — otherwise. Byte-identity does not hold, every invariant the repository copy carries
   is carried identically by the global copy, and the global copy introduces no heading the repository
   copy lacks. This is the legitimate "repository ahead, `./install.sh` not yet run" window that NFR-10
   declares is *not* a defect.

**The reworked assertion** keeps its name and keeps the existing unreadable-global skip, and asserts:

```python
self.assertNotEqual(state, "drift", <message naming the diverging invariant key or heading>)
self.assertIn(state, {"satisfied", "pending"})
```

so an unhandled state can never pass silently. The failure message names *which* invariant key differs
(with both values) or *which* global-only heading was found, so a genuine drift report is actionable
rather than a bare "not byte-identical".

**Docstring** (FR-11.8's rationale-in-code requirement) states, in the assertion itself: that
byte-identity is deliberately relaxed to **satisfied-or-pending** under **FR-11.8** and **NFR-10**;
that the repository copy is authoritative and the global copy is a derived install artifact synced by
the operator running `./install.sh` after merge; that the pending window is legitimate and must not be
resolved by writing to `~/.claude/`; and that genuine drift — an invariant stated differently or
omitted — still fails. A reviewer reads it as a deliberate amendment, not an unexplained regression.

### What deliberately does **not** change

`test_two_claude_ownership_lines_consistent` (line 212) is **untouched** and keeps asserting strict
normalised equality of the three invariant lines. It survives the pending window only because C11
constrains the `CLAUDE.md` edit to leave those three lines alone. That is why the discriminator's
invariant set is exactly those three keys and **not** extended with this feature's new classification
prose: new content in the repository copy is the definition of "pending", so promoting it to an
invariant would make every pending window read as drift and defeat the amendment.
`test_global_required_lines_present` and every other assertion in this module and in all other modules
are likewise untouched.

### Honest limits of the discriminator

- **L1 — prose-only hand-edits to the global copy are invisible.** A change made directly in
  `~/.claude/CLAUDE.md`, inside an existing section, touching none of the three invariant lines and
  adding no heading, classifies as `pending`. The check is not a two-way merge detector. The
  mitigation is structural, not test-side: NFR-10 declares the repository copy authoritative, and
  `install.sh` prompts before overwriting a differing global copy, so such an edit is by definition
  non-authoritative and is resolved at the next sync.
- **L2 — a heading *renamed* in the repository copy produces a false `drift`.** The old heading exists
  only in the global copy, so rule 2(b) fires. This errs toward FAIL, which is the safe direction; the
  message names the heading, and the sanctioned resolution (`./install.sh`, post-merge) clears it.
  This feature's `CLAUDE.md` edit renames no heading.
- **L3 — non-invariant staleness is tolerated by construction.** A global copy that is an old revision
  whose three invariant lines happen to match reads as `pending` indefinitely. That is the deliberate
  price of the amendment: FR-11.8 asks for tolerance of exactly this shape and names the invariant
  lines as the floor.
- **L4 — local-only signal.** In CI the global copy is absent and the assertion skips, exactly as
  today. Nothing about this rework makes CI stricter or looser (NFR-2).

### Conflict C-1 — a second byte-identity assertion FR-11.8 does not cover

`tests/test_orchestrator_label_lifecycle.py:270`, `test_repo_and_global_copies_are_byte_identical`,
asserts byte-identity between `agents/orchestrator.md` and `~/.claude/agents/orchestrator.md`, and
skips only if the global copy is absent or unreadable. **This feature edits `agents/orchestrator.md`
(C1–C5).** The instant the first orchestrator edit lands, that assertion fails locally for exactly the
reason FR-11.8 carves out for `CLAUDE.md` — a legitimate pending-sync window — yet FR-11.8's final
bullet confines the carve-out to `test_two_claude_files_byte_identical` and states that *"every other
assertion in `tests/`, in this module and in all others, remains undeleted and unweakened."*

The two clauses cannot both hold while `agents/orchestrator.md` is edited. This design does **not**
paper over it: it is a genuine requirements-level conflict introduced by A1, and it was escalated for a
requirements decision rather than resolved unilaterally here.

**Resolved by amendment A2.** The conflict was independently confirmed in the main session — `cmp`
shows `agents/orchestrator.md` and `~/.claude/agents/orchestrator.md` byte-identical today, so the
assertion passes now and turns red on this feature's first orchestrator edit, which C1–C5 all require.
A2 extends FR-11.8's carve-out to `test_repo_and_global_copies_are_byte_identical` on exactly A1's
terms:

- not deleted, and still able to fail on genuine drift;
- the surviving drift check is the orchestrator's **invariant instruction lines** rather than its raw
  bytes — the `ready-to-merge` single-application-point and clear-`blocked:*`-before-set ordering, the
  clear-**every**-recorded-label wording, the scaffold-push-only-on-first-scaffold scoping, and the
  "never runs `gh` / `git push` yourself" framing;
- byte-identity becomes **satisfied-or-pending** for the "repository ahead, global not yet synced"
  state specifically;
- the global path may be derived from `Path.home()` in place of the hardcoded absolute at
  `tests/test_orchestrator_label_lifecycle.py:35`, and nothing else in that module changes;
- the rationale lives in the reworked assertion's own docstring, citing FR-11.8 and NFR-10.

This is a small mechanical application of the existing mechanism, exactly as this design anticipated:
`claude_sync_state()` is a pure two-string function whose invariant-extraction callable is a
parameter, so the orchestrator assertion supplies a different extractor and reuses the same state
machine.

**The carve-out is closed at two.** A2 states normatively that `test_two_claude_files_byte_identical`
(A1) and `test_repo_and_global_copies_are_byte_identical` (A2) are the only live-global byte-identity
assertions in the suite. This was verified by inspecting every test that references `~/.claude`: the
four other agent definitions this feature edits — `task-tester`, `task-validator`, `code-reviewer`,
`security-reviewer` — have no global-copy identity assertion, and `tests/test_install_pre_push_hook.py`
points `HOME` at a throwaway tempdir, so it is not a live-global check. A third carve-out requires a
fresh amendment.

**Rejected fix:** running `./install.sh` mid-feature to close the window. NFR-10 forbids resolving the
pending-sync window by writing to `~/.claude`, and A1's rationale rules out mutating live global
configuration before review or merge. The operator runs the installer after merge.

---

## Requirement Traceability

| Requirement | Component(s) | Notes |
|---|---|---|
| FR-1 | C1 | Classification gate runs after tasks confirmed (post-consistency-gate), before implementation |
| FR-1.1 | C1, C2 | `featureClass` key + two permitted values documented in the state-file schema |
| FR-1.2 | C1 | Derived from declared task outputs; contract explicitly disclaims deriving from a git diff (D1) |
| FR-1.3 | C1, C0 | `non-code` only when every task's declared outputs are all in the allow-list |
| FR-1.4 | C1 | Enumerated ambiguity triggers → fail-safe `code` |
| FR-1.5 | C1, C2 | Value + per-task basis reported to the user and written to `classification.basis` |
| FR-1.6 | C1, C2 | Override toward `code` always honoured; toward `non-code` only if FR-1.3 holds; recorded in `classification.override` |
| FR-1.7 | C1, C2 | Absent key read with a `"code"` default; no retro-classification |
| FR-2 | C3, C5, I1 | `featureClass` + `taskProducesApplicationCode` forwarded to all four stages |
| FR-2.1 | C3 | Non-code + no-code task → validator artifact-conformance, tester no-code behaviour |
| FR-2.2 | C5 | Feature Review Gate passes the non-code scope instruction; concurrent, Opus-pinned invocation unchanged |
| FR-2.3 | C3 | Explicit NFR-4 guard sentence: on the `code` path nothing changes |
| FR-2.4 | C3, C4 | Stage order preserved; reviews still gated on validation passing |
| FR-3 | C4 | Reclassification section, three triggers, full code path applied |
| FR-3.1 | C4, C2 | `featureClass` updated; `classification.reclassification` records paths, task, trigger; reported to user |
| FR-3.2 | C4 | Stages 2–3 re-run under the code path before the task may complete |
| FR-3.3 | C2, C3, C5 | `tasksValidatedUnderExemption` appended at instruction time; Feature Review Gate told to cover them under the code path |
| FR-3.4 | C4 | Monotonicity stated explicitly; no override can reverse it |
| FR-4 | C6 | `## No-Code Behaviour` section defines the outcome |
| FR-4.1 | C6 | Vacuous/placeholder tests prohibited, forms enumerated, reason stated |
| FR-4.2 | C6 | Machine-checkable artifacts get a real check in the conventional test directory |
| FR-4.3 | C6, I2 | "No applicable tests" block: artifact, requirement, why-no-check |
| FR-4.4 | C6 | Existing tests in the affected area always run and regressions reported |
| FR-4.5 | C6, C4 | Tester escalates discovered application code (trigger T1) and tests it normally |
| FR-5 | C7 | Artifact-conformance mode validates produced artifacts against cited requirements |
| FR-5.1 | C7, C3 | Named mode, entered only on the orchestrator's instruction, never self-selected |
| FR-5.2 | C7, I4 | Every cited requirement mapped to a named artifact or identified changelog entry, and read |
| FR-5.3 | C7 | Exists, non-empty, substantive; placeholder/stub/TODO-only → FAIL |
| FR-5.4 | C7 | §2 Test Coverage replaced by §2A for this mode only; missing tests not a FAIL |
| FR-5.5 | C7 | Machine checks from FR-4.2 are run; any failure → FAIL |
| FR-5.6 | C7, C4 | Application code detected → refuse exemption, FAIL, report paths (trigger T2) |
| FR-5.7 | C7 | §3 Scope Check and §4 Quality Check remain active |
| FR-5.8 | I3 | Per-requirement artifact + mode; machine-readable, stage-attributable |
| FR-5.9 | C7 | Existing "NEVER partially pass" rule retained and cited |
| FR-6 | C8, C9 | Shared `## Non-Code Review Scope` section in both reviewers |
| FR-6.1 | C8, C9 | Union of spec artifacts, non-code files in diff, changelog entries |
| FR-6.2 | C8, C9 | Diff first (mode-appropriate), fallback on empty/non-code-only |
| FR-6.3 | C8, C9, I5 | Exactly one of PASS/FAIL; hedge/abstention/N-A/nothing-to-review forbidden by name |
| FR-6.4 | C8, C9 | Empty resolved scope → FAIL as a Critical "no reviewable output" finding |
| FR-6.5 | C8, C9, I5 | `Scope Reviewed` enumerates the scope; changelog entries by target and operation |
| FR-6.6 | C8, C9 | Severity model restated unchanged |
| FR-6.7 | C8, C9, C12 | No new tool; frontmatter `tools:` asserted unchanged |
| FR-6.8 | C8, C9, I4 | Changelog only, never the vault note; `VAULT REQUEST` escalation |
| FR-7 | C8 | `### Non-code scope (FR-7)` finding classes |
| FR-7.1 | C8 | Contradictions, conflicts with confirmed specs, unfollowable instructions |
| FR-7.2 | C8 | Broken paths, dead links, non-existent requirement/task IDs, renamed artifacts |
| FR-7.3 | C8, C11 | Duplication/divergence incl. two synchronised copies, subject to the NFR-10 pending-sync allowance; incompleteness |
| FR-7.4 | C8, I4 | Changelog coherence: each write traceable to a requirement; target/operation vs intent |
| FR-7.5 | C8 | Concrete failure scenario required for every blocking non-code finding |
| FR-8 | C9 | `### Non-code scope (FR-8)` finding classes |
| FR-8.1 | C9 | Credential material in prose → type + `path:line`, value redacted |
| FR-8.2 | C9 | Sensitive disclosure: hostnames, endpoints, account IDs, PII, infra detail |
| FR-8.3 | C9 | Unsafe documented instructions; a documented unsafe default is a finding in itself |
| FR-8.4 | C9, I4 | Changelog writes placing sensitive material in the vault, or targeting outside the vault path |
| FR-8.5 | C9 | Concrete attack/exposure scenario required for every blocking finding |
| FR-9 | C5 | Feature Review Gate PASS branch untouched; the single application point serves both classes |
| FR-9.1 | C5, C12 | No alternative path/exemption/auto-pass; asserted by `test_orchestrator_ready_to_merge_singleton` |
| FR-9.2 | C5, C8, C9 | The PASS comes from both reviewers actually reviewing the resolved scope |
| FR-9.3 | C5 | Existing clear-before-set ordering and draft-on-blocking rules untouched |
| FR-9.4 | C5 | Human merge gate text untouched |
| FR-10 | C12 (`test_review_gate_untouched`) | CI template unmodified; no new job, workflow, or label |
| FR-10.1 | C4, C5, C12 | Label vocabulary frozen at five names; reclassification adds none |
| FR-10.2 | C12 | Bypass/exemption/escape-hatch tokens asserted absent from the CI template |
| FR-11 | C12 | Seven modules mirroring the existing structural-lint pattern |
| FR-11.1 | C12 | Stdlib-only `unittest`; paths resolved relative to the test file |
| FR-11.2 | C12 (`test_orchestrator_feature_class`) | Classification step, schema key + values, fail-safe, routing, reclassification |
| FR-11.3 | C12 (`test_validator_artifact_conformance`) | Mode defined, instruction-only, tests-not-a-FAIL, code → FAIL |
| FR-11.4 | C12 (`test_tester_no_code_behaviour`) | No-code behaviour, vacuous-test prohibition, "no applicable tests" block |
| FR-11.5 | C12 (`test_reviewers_non_code_scope`) | Both reviewers: scope, order, mandatory verdict, empty-scope FAIL, changelog source, no vault read |
| FR-11.6 | C12 (`test_orchestrator_ready_to_merge_singleton`) | Exactly one set operation, located in the PASS branch, none in the new regions |
| FR-11.7 | C12 (`test_review_gate_untouched`) | Required label, `blocked:*` failure, no bypass label |
| FR-11.8 | A1 resolution (`test_docs_updates.py` rework) | `Path.home()`; `claude_sync_state()`; satisfied-or-pending; drift still FAILs; rationale in the docstring. **See Conflict C-1** |
| FR-12 | C11(a) | Repo-root `CLAUDE.md` pipeline description: classification + non-code track + real-PASS restatement |
| FR-12.1 | C11(a) + a global constraint on every task | Repository copy only; **no** pipeline write anywhere under `~/.claude/`; installer syncs post-merge |
| FR-12.2 | C11(a) | Classification is explicit, recorded in `.spec-state.json`, and falls back to the code path |
| FR-13 | C11(b) | README pipeline-stage description gains the classification step and the non-code track |
| FR-13.1 | C11(b) | README states same audited path, no bypass label |
| NFR-1 | C5, C4, C12 | Gate preserved or tightened; no new path around `ready-to-merge`; empty-output features FAIL |
| NFR-2 | C12 (`test_review_gate_untouched`) | No CI/template/hook modification; the assertion locks the file's semantics |
| NFR-3 | C0–C9, C12 | No new agent, tool, write target, or owned artifact; reviewer `tools:` frontmatter asserted unchanged |
| NFR-4 | C3, I1, I3, I5 | `code`-path behaviour identical: mode/scope-resolution lines emitted only on the non-code path; no new prompt |
| NFR-5 | C1, C2, C4 | Value, basis, override, exemptions and reclassification recorded and reported |
| NFR-6 | C0–C9, C12 | Named modes, named state keys, named artifact paths — every new behaviour greppable |
| NFR-7 | C7, C9 | Secrets reported as type + `path:line`, redacted; no denied-store read, no workaround |
| NFR-8 | C7, C8, C9, I4 | Changelog is the only vault-facing surface; `VAULT REQUEST` for anything more |
| NFR-9 | C6, C7, C8, C9 | Validator and reviewers stay read-only; tester still never modifies implementation |
| NFR-10 | C11(a), A1 resolution | Repository copy authoritative; pending-sync window legitimate and never resolved by writing to `~/.claude/` |
| NFR-11 | This document, C11 | All artifacts authored in English; requirements keep EARS `FR-N`/`NFR-N` numbering |

No orphan requirements: every FR and NFR above maps to at least one component, and every component
C0–C12 and interface I1–I5 is cited by at least one requirement.

**Acceptance-criteria coverage:** AC-1 → Flow A; AC-2 → Flow B; AC-3 → Flow C; AC-4 → Flow D; AC-5 →
C8/C9 §4 and `test_reviewers_non_code_scope`; AC-6 → `test_review_gate_untouched`; AC-7 →
`test_orchestrator_ready_to_merge_singleton`; AC-8 → the C12 module table plus the single carve-out;
AC-9 → Flow E; AC-10 → C11 + `test_docs_non_code_track` + the A1 rework.

---

## Sequence Flows

### Flow A — Vault-update feature (empty in-repo diff) reaches `ready-to-merge` (AC-1)

1. Tasks confirmed → consistency gate PASS.
2. **Classification gate**: every task declares only `vault-writer` mutations and spec artifacts → all
   outputs in allow-list categories 1 and 3 → `featureClass = "non-code"`, basis recorded, reported to
   the user. `phase = "implementation"`.
3. Task 1 — Stage 1: the executor authors content; the orchestrator routes the vault write through
   `vault-writer`, which appends a line to `.../vault/.write-log.jsonl`.
4. Stage 2 tester: `featureClass = non-code`, `taskProducesApplicationCode = false` → no-code
   behaviour. No machine check is feasible for a vault note → emits the "no applicable tests" block
   (I2); runs existing tests in the affected area (none affected) and reports.
5. Stage 3 validator: instructed into artifact-conformance mode; the task number is appended to
   `tasksValidatedUnderExemption`. It maps each cited requirement to a changelog entry, reads the
   changelog, confirms `target`/`operation`/`intent` deliver what the requirement demands → `PASS` with
   the I3 block.
6. Stages 4–5: both reviewers find the `task`-mode diff empty → resolve the non-code scope → review the
   spec artifacts and the changelog entries → `PASS` each, with `Scope Reviewed` enumerating the
   entries by target and operation.
7. The per-task pass branch runs unchanged: commit-push, verbatim three-verdict comment, any
   `blocked:*` cleared.
8. After the last task, the **Feature Review Gate**: both reviewers in `feature` mode with the non-code
   scope instruction; `git diff main...HEAD` is spec-only → non-code scope resolved and reviewed → both
   `PASS`.
9. The existing PASS branch: clear `blocked:feature-review` if set, then the single
   `label set ready-to-merge`, then `request-review`. `phase = complete`. CI's review gate passes
   because a real label backed by a real PASS is present.

### Flow B — Docs-only feature (AC-2)

Identical to Flow A except: the diff is non-empty but contains only allow-list category-2 files;
step 4's tester finds a machine check *is* feasible (a link/path lint over the write-up) and writes it
in `tests/` per FR-4.2; step 5's validator runs that check (FR-5.5) and maps each requirement to a file
path rather than a changelog entry; step 6's `Scope Reviewed` lists the changed docs and reports "vault
changelog: absent".

### Flow C — Reclassification (AC-3)

1. The feature is `non-code`. Task 3's executor, fixing a documented instruction, also edits
   `agents/task-executor.md` — application code by the C0 allow-list.
2. Stage 2 tester detects the code path in the executor's summary → reports it (T1) **and** writes tests
   for the change normally.
3. The orchestrator's reclassification subsection fires: `featureClass = "code"`,
   `classification.reclassification` records `agents/task-executor.md`, task 3, trigger `tester`;
   reported to the user. `retryCount` is **not** incremented (T1 path).
4. Stages 2–3 re-run under the code path: tests are now required; the validator runs in normal mode and
   fails the task if coverage is missing.
5. (Had the tester missed it, the validator would catch it in artifact-conformance mode → FAIL +
   offending paths (T2) → the existing fail branch: `retryCount += 1`, `blocked:validation`, executor
   retry on Opus.)
6. All later tasks run the code path. The Feature Review Gate is told that the tasks recorded in
   `tasksValidatedUnderExemption` are to be reviewed under the code path (FR-3.3). Monotonic: the
   feature never returns to `non-code`.

### Flow D — A feature that produced nothing (AC-4)

Feature Review Gate, `feature` mode. The reviewer's diff is empty; the resolved non-code scope has no
changed non-code file, no spec artifact attributable to the tasks, and no changelog entry → `FAIL` with
a single Critical "the feature produced no reviewable output" finding. The existing FAIL branch sets
`blocked:feature-review`, keeps the PR draft, and `ready-to-merge` is never applied. CI keeps failing
the PR, correctly.

### Flow E — A code-bearing feature (AC-9, NFR-4)

The classification gate records `featureClass = "code"` — this feature itself takes this path, since it
edits `agents/*.md` and adds tests. Every stage receives the value and ignores it. The tester writes
tests as today; the validator runs §1–§4 with §2 intact and emits today's verdict block with **no**
`### Mode:` line; both reviewers find application code in the diff, stop at step 1 of the scope
resolution, and emit today's verdict block with **no** `### Scope Resolution:` line. Same stages, same
order, same formats, same labels, no extra prompt.

---

## Dependencies

- **Existing, unchanged, consumed:** `agents/vault-writer.md`'s changelog contract (I4);
  `ci-templates/workflows/sdd-review-gate.yml` (read-only, asserted unmodified); `install.sh` (the
  post-merge sync mechanism named by FR-12.1 — **not modified by this feature and not run by any
  task**); `agents/github-agent.md` (unchanged — the label vocabulary and the choke-point are
  untouched).
- **Runtime:** the Python 3 standard library only, for the new tests. No new package, no new test
  framework, no new configuration file.
- **Internal patterns reused:** the structural-lint style of `tests/test_github_agent_def.py`
  (frontmatter split) and `tests/test_orchestrator_label_lifecycle.py` (`region_between` ordering
  assertions); the `github_agent_lines()` / `extract_section()` helpers already in
  `tests/test_docs_updates.py`.

### Sequencing constraints (for the tasks-agent)

These are ordering facts, not task definitions:

1. The **`tests/test_docs_updates.py` rework must land before the `CLAUDE.md` edit.** Otherwise the
   intermediate commit fails locally and the per-task pipeline blocks on its own test suite.
1a. Symmetrically, and now required by **A2**: the **`tests/test_orchestrator_label_lifecycle.py`
   rework must land before — or in the same task as — the first edit to `agents/orchestrator.md`**
   (C1–C5). `cmp` confirms the repository and global copies are byte-identical today, so that
   assertion turns red on the first orchestrator edit and blocks the pipeline exactly as the
   `CLAUDE.md` case would. Never sequence the rework after the edit.
2. The **five agent-contract edits should land before their assertion modules**, or in the same task,
   so no committed test asserts text that does not yet exist.
3. **No task may write to `~/.claude/`, run `./install.sh`, or modify `install.sh`** (FR-12.1, Out of
   Scope). The global sync is a post-merge operator action.
4. **No task may modify `ci-templates/workflows/sdd-review-gate.yml`** (FR-10, NFR-2). The earlier
   prohibition on touching `tests/test_orchestrator_label_lifecycle.py` is **lifted by A2**, which
   authorises reworking exactly one assertion in that module —
   `test_repo_and_global_copies_are_byte_identical` — under the constraints in Conflict C-1 above.
   Every other assertion in that module remains undeleted and unweakened.

---

## Risks and Mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | The C0 allow-list is replicated in five files and drifts as they are edited independently | `test_allow_list_blocks_identical` asserts all five copies are normalised-identical; `agents/orchestrator.md` is declared the normative home in every copy's heading |
| R2 | The changed orchestrator contract governs this feature's own run mid-flight, producing an internally inconsistent fleet | The live fleet reads `~/.claude/agents/`; FR-12.1 forbids any pipeline write there, so the repository edits are inert until the operator runs `./install.sh` post-merge. Sequencing constraint 3 makes this an explicit task-level prohibition rather than an assumption |
| R3 | Repo-vs-global byte-identity assertions fail on intermediate commits and block the pipeline | Resolved for `CLAUDE.md` by the A1 rework, and for `agents/orchestrator.md` by the **A2** amendment (Conflict C-1), which extends the identical satisfied-or-pending treatment to `test_repo_and_global_copies_are_byte_identical`. A2 also closes the carve-out at exactly two: no other agent definition this feature edits carries a live-global identity assertion, so no third exemption is permitted without a further amendment |
| R9 | `agents/tasks-agent.md:80` rule 5 — *"No non-coding tasks… Only include tasks that produce code or tests"* — reads as a prohibition on the very task lists this feature's non-code track depends on, so a tasks-agent obeying it literally would never emit one | **No file change, by design** — no FR authorises editing `agents/tasks-agent.md`, and widening scope at design time is the failure mode this pipeline exists to prevent. The composition argument is that rule 5 excludes tasks *no coding agent can perform* (deploy, user testing, review-by-human), not tasks whose deliverable happens to be prose: a task that writes a recon document or drives `vault-writer` **is** work an agent performs end-to-end. Rule 4's mandatory testing sub-task is discharged by the FR-4.3 "no applicable tests" block, which is an auditable outcome, not a skipped step. Flagged as a candidate for a **separate follow-up requirement** to reword rule 5; until then a non-code task list depends on that reading being applied |
| R4 | Tests-optional becomes a loophole: a feature is mis-declared `non-code` to skip testing | Three independent barriers: classification derives from declared outputs and defaults to `code` on any ambiguity (FR-1.4); an override toward `non-code` is refused unless FR-1.3 already holds (FR-1.6); and the tester and the validator each independently detect application code at execution time and force reclassification (T1/T2), which is monotonic |
| R5 | A non-code reviewer PASS degenerates into a rubber stamp — the failure mode the whole feature exists to fix | The reviewers get an enumerated finding-class list (FR-7, FR-8), a mandatory concrete-scenario rule for every blocking finding, a mandatory enumerated `Scope Reviewed`, and an empty-scope FAIL. A PASS is a positive statement about a named artifact set, not a default |
| R6 | The A1 discriminator false-FAILs on a heading rename in the repository copy (L2) | Errs toward FAIL, never toward silently accepting drift; the message names the heading; the resolution is the sanctioned `./install.sh` |
| R7 | `tasks.md` states outputs too vaguely to classify | The ambiguity triggers are enumerated in C1 and all resolve to `code`. A vague task list therefore costs nothing worse than today's behaviour |
| R8 | Both reviewers now read `.specs/` spec artifacts as review scope, risking re-litigation of requirements | The code-reviewer's existing rule ("do not re-litigate requirement conformance — that is the validator's job") is left intact and is cited from the new section; the non-code finding classes are about internal coherence, references and completeness, not about whether the requirements are the right ones |

---

## Design Decisions

**DD-1 — Classify at the consistency-gate exit, not at tasks-confirmation.**
FR-1 permits anywhere in the window "after tasks confirmed, before implementation". Classifying at the
consistency gate's PASS means the classifier reads a task list that has already been audited for
internal consistency, and it folds into an existing state write and an existing user report — no new
prompt, no new state transition (NFR-4). *Rejected:* classifying at the `tasks` confirmation, which
would classify a task list the consistency checker might send back for rework, requiring
re-classification and a second user report.

**DD-2 — The validator's mode is instruction-only; the reviewers' scope is diff-triggered.**
This asymmetry is deliberate and is mandated by two different requirements. FR-5.1 forbids the
validator self-selecting artifact-conformance because a diff looked empty — a validator that granted
itself a tests-optional exemption on observing an empty diff would be precisely the loophole D2 warns
about. FR-6.2, by contrast, makes the reviewers key on the diff, because a reviewer facing an empty
diff must still return a verdict even if the orchestrator's prompt said nothing about it (P2). The
orchestrator's non-code instruction to a reviewer is therefore confirmatory, not enabling — which also
means a stale or missing instruction can never turn a reviewer's PASS into a default.

**DD-3 — Empty scope is a Critical finding, not a new verdict kind.**
FR-6.4 requires a FAIL for an empty scope. Modelling it as a Critical finding reuses the existing
severity → verdict rule (FR-6.6) and the existing FAIL block verbatim. *Rejected:* a third verdict
value (`EMPTY`/`NO-OUTPUT`), which would require the orchestrator, the github-agent transcription path,
and the label logic all to learn a new value — new mechanism for no gain, and an invitation for the new
value to be treated as "not a FAIL".

**DD-4 — Non-code-only verdict lines, to keep NFR-4 literal.**
`### Mode:` (validator) and `### Scope Resolution:` (reviewers) are emitted **only** on the non-code
path. NFR-4 says code-feature behaviour is unchanged including "same verdict formats"; adding a
`### Mode: code` line to every code-path verdict would violate that literally, and those verdicts are
transcribed verbatim into PR comments where the change would be visible. *Rejected:* an always-present
mode line — tidier, but it breaks the stated invariant.

**DD-5 — Replicate the allow-list verbatim across five files, guarded by an identity test.**
*Rejected (a):* paraphrasing the definition per agent — five paraphrases of a load-bearing definition
are five ways to disagree about what "application code" means, and disagreement between the tester's
and the validator's copies is exactly what triggers spurious reclassification. *Rejected (b):* a shared
`.md` fragment included by reference — there is no include mechanism; `install.sh` copies each agent
file standalone into `~/.claude/agents/`, so a fragment would not be installed and the contract would
be incomplete at runtime. *Rejected (c):* pointing the other four agents at the orchestrator's copy — a
subagent cannot rely on having read another agent's definition. Verbatim replication plus a
normalised-identity assertion gives one definition with mechanical drift protection.

**DD-6 — The A1 discriminator is invariant-equality plus heading-provenance.**
*Rejected (a) — mtime ordering* ("global older than repo ⇒ pending"): mtime is not content evidence,
`git clone`/`checkout` rewrites repository mtimes arbitrarily, and a *stale-and-wrong* global copy is
also older — so the test would classify genuine drift as pending, the one outcome FR-11.8 forbids.
*Rejected (b) — line-set containment* ("every global line appears in the repository copy"): sound in
direction but far too strict — any reworded paragraph leaves the old wording in the global copy and
reads as drift, and FR-12's whole job is rewording an existing paragraph. It would false-FAIL on the
very change it must tolerate. *Rejected (c) — a git-based comparison* (is the global copy an ancestor
blob?): the global copy is not in a repository and has no history, and the repository's history does
not contain the installed file. *Chosen:* the invariant set is exactly what NFR-10 defines as drift and
exactly what FR-11.8 names as the class that must survive, and heading-provenance adds a cheap
directional signal that catches "the global copy has content of unknown origin" without tripping on
prose edits. Limits L1–L4 are stated rather than hidden.

**DD-7 — The invariant set is *not* extended with this feature's new content.**
Adding the new classification prose to the cross-copy invariant set would make every pending window
read as drift, inverting the amendment. New content in the repository copy is the *definition* of
pending. The floor stays at the three Agent-Ownership lines FR-11.8 names — and C11 constrains the
`CLAUDE.md` edit to leave those three lines untouched, which is what lets the untouched
`test_two_claude_ownership_lines_consistent` keep enforcing at full strength through the window.

**DD-8 — Reclassification splits retry accounting by trigger.**
T2 (validator FAIL) is a real failure and takes the existing fail branch, labels and all. T1/T3 are
detected before a verdict exists and re-run stages 2–3 within the same attempt. *Rejected:* treating
every reclassification as a retry, which would burn the two-retry budget on a bookkeeping event and set
`blocked:validation` for a task that never failed validation.

**DD-9 — New-content doc assertions go in a new module, not in `test_docs_updates.py`.**
FR-11.8 permits "no change beyond that" to the reworked module. Confining `tests/test_docs_updates.py`
to exactly three edits — the `GLOBAL_CLAUDE` constant, the new `claude_sync_state()` helper, and the
reworked assertion — keeps the carve-out demonstrably minimal and reviewable as a deliberate amendment.
FR-12/FR-13 content assertions live in `tests/test_docs_non_code_track.py`.

**DD-10 — Rejected outright: making `ready-to-merge` class-conditional.**
The obvious shortcut — "if `featureClass == non-code`, apply `ready-to-merge` after validation" — was
never on the table, and neither was a CI-side escape hatch (rejected in scoping, O2). The invariant
this feature protects is that exactly one branch applies the label and only a genuine whole-feature
review PASS reaches it. The entire design is arranged so that a non-code feature *earns* that PASS
rather than being routed around it, and `test_orchestrator_ready_to_merge_singleton` makes any future
second application point a test failure.

**DD-11 — Rejected: auto-detecting vault mutations by scanning the vault.**
The scope's *Deferred* list rules out vault auditing beyond `vault-writer`'s changelog, and NFR-8
forbids reading vault notes for review. The changelog is therefore the entire vault-facing surface, and
its completeness is `vault-writer`'s responsibility (`ALWAYS record the write to the changelog`), not
the reviewers'. A reviewer that needs more halts with `VAULT REQUEST`.
