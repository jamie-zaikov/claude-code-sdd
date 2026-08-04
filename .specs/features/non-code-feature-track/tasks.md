# Tasks: non-code-feature-track

<!-- This file is owned by the tasks-agent. Do not edit manually during SDD workflow. -->

## Overview

10 top-level tasks implement the first-class non-code track: the byte-identity carve-out that makes
intermediate commits viable at all (A1/A2), four orchestrator contract edits (classification gate +
state schema, per-task routing, reclassification fallback, feature-review gate wiring), the
task-tester no-code behaviour, the task-validator artifact-conformance mode, the shared non-code
review scope in both reviewers, a CI-template lock test, and the documentation updates.

The deliverable is mostly markdown, because in this repository behaviour-bearing prose **is** the
implementation: `agents/*.md` and `commands/*.md` are classified as application code by the very
allow-list this feature installs. This feature is therefore itself `featureClass: "code"` and runs
the unchanged five-stage pipeline while building the non-code path (design Flow E).

### How to read this list

Each top-level task is one coherent design component (or a tight pair), sized for a single
Execute → Test → Validate → Code Review → Security Review pass. Every task cites the requirement IDs
it satisfies, names its design component, and lists every file it touches. The final sub-task of
each task is always its test sub-task. A traceability table at the end confirms every FR-1…FR-13 and
NFR-1…NFR-11 is covered.

### Execution environment (context, not a task)

The task-executor works in the **shared feature-branch checkout** on `feat/non-code-feature-track` —
not an isolated worktree. Tasks run sequentially, so each task inherits the committed output of every
prior task. Task N may rely on Task N-1's files existing on disk; it must not re-create them.

### The `**Files:**` field is load-bearing here

Design component C1 makes each task's `**Files:**` field the primary input to feature classification.
The fields below are exhaustive and path-precise for that reason: a task that touches a file not
listed is a task the classifier would mis-read. If an executor finds it must touch an unlisted file,
that is a signal to stop and report, not to widen silently.

### Global constraints — apply to every task without exception

1. **No task writes anywhere under `~/.claude/`, runs `./install.sh`, or modifies `install.sh`**
   (FR-12.1, NFR-10, amendment A1). The global copies are derived install artifacts; the operator
   syncs them by running `./install.sh` **after merge**. A repository copy ahead of an unsynced
   global copy is a legitimate pending-sync window, never a defect to "fix".
2. **No task modifies `ci-templates/workflows/sdd-review-gate.yml`**, any other CI workflow or
   template, or any hook (FR-10, NFR-2). Task 9 reads that file; it does not write it.
3. **No task modifies `agents/tasks-agent.md`.** Risk R9 records that its rule 5 reads as excluding
   non-code task lists; no requirement authorises changing it. It is a flagged follow-up, not scope.
4. **No task deletes or weakens any existing assertion in `tests/`**, with exactly the two carve-outs
   Task 1 implements (FR-11.8). `tests/test_install_pre_push_hook.py` and
   `tests/test_sdd_init_ci_templates.py` are **not** modified — they point `HOME` at a throwaway
   tempdir and are unaffected by the pending-sync window.
5. **No new agent, no new tool grant, no new write target, no new label** (NFR-3, FR-10.1). Every
   change is confined to the text of existing agent contracts, tests under `tests/`, and the two
   documentation files.
6. Every new test module is **stdlib-only `unittest`**, resolves paths with
   `Path(__file__).resolve().parent.parent`, and carries its own local helper copies — no new shared
   importable module (FR-11.1, C12 precedent).

### Sequencing (why the order is what it is)

- **Task 1 is first and is not negotiable.** `agents/orchestrator.md` and `CLAUDE.md` are
  byte-identical to their global copies today, so `test_repo_and_global_copies_are_byte_identical`
  (`tests/test_orchestrator_label_lifecycle.py`) and `test_two_claude_files_byte_identical`
  (`tests/test_docs_updates.py`) turn red on the **first** edit to either file and block the pipeline
  on its own suite. The rework must land before — never after — the edits it covers.
- Tasks 2–5 edit `agents/orchestrator.md` and are unblocked only once Task 1 has landed.
- Every agent-contract edit lands **in the same task as** the assertions covering it, so no committed
  test asserts text that does not yet exist.
- Task 8 carries `test_allow_list_blocks_identical` because it is the first point at which all five
  copies of the C0 allow-list block exist (orchestrator → Task 2, tester → Task 6, validator →
  Task 7, both reviewers → Task 8).
- Task 10 edits `CLAUDE.md`, which Task 1 has already made safe.

---

## Task 1: Byte-identity carve-out — rework the two live-global assertions (A1/A2)
- [ ] 1. Rework `test_two_claude_files_byte_identical` and `test_repo_and_global_copies_are_byte_identical` to satisfied-or-pending, so intermediate commits stop failing on a legitimate pending-sync window.

**Description:** Implement the A1 resolution and the A2 extension in the design. Both assertions
currently demand byte-identity with a live `~/.claude` copy and skip only when that copy is
unreadable, so both fail the instant this feature edits `CLAUDE.md` or `agents/orchestrator.md`.
Replace raw byte-identity with a three-state discriminator — `satisfied` / `pending` / `drift` —
that still FAILs on genuine drift. This is the **only** authorised carve-out in the suite and is
closed at exactly two assertions; nothing else in either module changes. **This task must land
before Tasks 2–5 (orchestrator edits) and before Task 10 (`CLAUDE.md` edit).**

**Sub-tasks:**
- [ ] 1.1. In `tests/test_docs_updates.py`, derive the global path from `Path.home()`:
  `GLOBAL_CLAUDE = Path.home() / ".claude" / "CLAUDE.md"`, replacing the hardcoded absolute. No
  environment-variable override is added — FR-11.8 permits `Path.home()` and nothing more. CI
  behaviour is unchanged (the path does not exist there, so the existing skip fires). (FR-11.8)
- [ ] 1.2. Add a module-level `claude_sync_state(repo_text, global_text, extract_invariants)` helper
  to `tests/test_docs_updates.py` returning `'satisfied' | 'pending' | 'drift'`, evaluated in order:
  (1) `satisfied` when the texts are equal; (2) `drift` when **either** (a) any invariant key
  extracted from the repository copy is missing from the global copy or differs after normalisation,
  **or** (b) any ATX heading (normalised, outside code fences) present in the global copy is absent
  from the repository copy — containment is directional, repository-only headings are the normal
  signature of a pending sync; (3) `pending` otherwise. The invariant extractor is a **parameter**,
  so the same state machine serves both assertions. (FR-11.8, NFR-10, DD-6)
- [ ] 1.3. Rework `test_two_claude_files_byte_identical` in place — same name, same
  unreadable-global skip — to call the helper with the existing `github_agent_lines()` extractor
  (keys `bullet`, `gh_line`, `invariant`) and assert
  `assertNotEqual(state, "drift", <message naming the diverging key or global-only heading>)` plus
  `assertIn(state, {"satisfied", "pending"})`, so an unhandled state can never pass silently. Do
  **not** extend the invariant set with this feature's new classification prose (DD-7). Its
  docstring must state the carve-out rationale, citing **FR-11.8** and **NFR-10**: the repository
  copy is authoritative, the global copy is a derived install artifact synced post-merge by
  `./install.sh`, the pending window is legitimate and must never be resolved by writing to
  `~/.claude/`, and genuine drift still fails. (FR-11.8, NFR-10, AC-8, AC-10)
- [ ] 1.4. In `tests/test_orchestrator_label_lifecycle.py`, derive `GLOBAL_ORCH_PATH` from
  `Path.home()` and add a local copy of the same sync-state helper (local copy, not an import —
  no new shared module). (FR-11.8, FR-11.1)
- [ ] 1.5. Add an orchestrator invariant extractor to that module pulling the file's **invariant
  instruction lines**: the `ready-to-merge` single-application-point sentence, the
  clear-`blocked:*`-before-set ordering, the clear-**every**-recorded-label wording, the
  scaffold-push-only-on-first-scaffold scoping, and the "never runs `gh` / `git push` yourself"
  framing. Rework `test_repo_and_global_copies_are_byte_identical` in place — same name, same
  absent/unreadable skip — to the same satisfied-or-pending assertion shape, with the same
  rationale docstring citing FR-11.8 and NFR-10. The drift discriminator must be a genuine content
  comparison, **never** a blanket skip taken whenever the two copies differ. (FR-11.8, NFR-10, AC-8)
- [ ] 1.6. Confirm nothing else changes: `test_two_claude_ownership_lines_consistent`,
  `test_global_required_lines_present`, and every other assertion in both modules are untouched, and
  no other test module is edited. (FR-11.8, AC-8)
- [ ] 1.7. Test: run `python3 -m unittest discover -s tests -v` and assert the full suite passes with
  the working tree as-is; then verify the discriminator by exercising the sync-state helper directly
  (in-test fixture strings, no file writes outside the repo) for all three states — equal texts →
  `satisfied`; repository copy with an added section → `pending`; a global copy missing or restating
  an invariant line, and a global copy carrying a heading the repository copy lacks → `drift`. Assert
  no write occurred anywhere under `~/.claude/`. (FR-11.8, FR-11.1, NFR-10, AC-8)

**Requirements:** FR-11, FR-11.1, FR-11.8, NFR-10, NFR-6
**Design Reference:** *A1 resolution*; *Conflict C-1* / amendment **A2**; DD-6, DD-7, DD-9; C12 (the
reworked-module row); risks R3, R6
**Files:** `tests/test_docs_updates.py` (modify — exactly three edits: the `GLOBAL_CLAUDE` constant,
the new `claude_sync_state()` helper, the reworked `test_two_claude_files_byte_identical`),
`tests/test_orchestrator_label_lifecycle.py` (modify — exactly the `GLOBAL_ORCH_PATH` constant, the
local helper + orchestrator invariant extractor, and the reworked
`test_repo_and_global_copies_are_byte_identical`)

---

## Task 2: Orchestrator — C0 allow-list + Feature Classification Gate + state schema (C0, C1, C2)
- [ ] 2. Add the normative non-code artifact allow-list, the Feature Classification Gate, and the `.spec-state.json` schema delta to `agents/orchestrator.md`.

**Description:** Insert the classification gate as a new `###` section **between** the existing
`### Consistency Gate (runs automatically after tasks confirmed, before implementation)` section and
the existing ``### `implementation` `` section, carrying the C0 allow-list block verbatim
(`agents/orchestrator.md` is its normative home), and extend the `## State File Management`
initialization block and its schema prose with `featureClass` and the `classification` object.
Depends on Task 1. Writes no label and makes no GitHub call — the gate performs no remote action.

**Sub-tasks:**
- [ ] 2.1. Add the C0 block under the exact heading
  `#### Non-code artifact allow-list (normative — identical in every agent that classifies)`, as a
  single fenced block reproducing the requirements definition unparaphrased (three NON-CODE ARTIFACT
  categories; APPLICATION CODE as everything else, naming `agents/*.md` and `commands/*.md` for this
  repository). Byte-for-byte reusable — Tasks 6, 7 and 8 replicate it verbatim. (FR-1.3, NFR-6, DD-5)
- [ ] 2.2. Add the section headed
  `### Feature Classification Gate (runs automatically after the consistency gate, before implementation)`
  in the placement above, specifying: it runs immediately after the consistency gate resolves PASS
  (including the `(d) override and proceed` path), in the **same state-file write** that sets
  `phase = "implementation"`; exactly once per feature; not re-run on resume when `featureClass` is
  already present. (FR-1, DD-1)
- [ ] 2.3. Specify the inputs: (a) the confirmed `tasks.md`, taken primarily from each task's
  **`**Files:**` field** (defined by the task template at `agents/tasks-agent.md:62`) and secondarily
  from the task body and sub-tasks where that field is absent or incomplete; (b) `design.md`, only to
  resolve outputs named by component rather than path; (c) `.specs/steering/structure.md` and
  `tech.md` for the project's designation of source/contract/template/script/configuration. State
  explicitly that the gate **never** inspects a git diff to classify, and why: at this point nothing
  has been implemented. (FR-1.2, D1)
- [ ] 2.4. Specify the per-output rule (an output is non-code iff it matches one of the three
  allow-list categories, otherwise application code) and the per-feature rule
  (`featureClass = "non-code"` iff every task declares at least one output **and** every declared
  output of every task classifies non-code; otherwise `"code"`). (FR-1.3)
- [ ] 2.5. Specify the fail-safe with enumerated ambiguity triggers so the rule is checkable: a task
  declares no outputs; an output cannot be resolved to a concrete path or to one of the three
  categories; a prose file sits inside a directory steering designates as source/contract/template;
  steering is silent and the location does not settle it. State plainly that `"code"` is the
  fail-safe direction because it preserves today's behaviour exactly. (FR-1.4, R7)
- [ ] 2.6. Specify record-and-report: write `featureClass` and the `classification` object, and
  report to the user the recorded value **and** the basis — one line per task naming its declared
  outputs and their classification. (FR-1.5, NFR-5)
- [ ] 2.7. Specify the override rule (an override toward `"code"` is always honoured; toward
  `"non-code"` only when the FR-1.3 test already holds, otherwise refuse, name the offending task's
  application-code output, and keep `"code"`; every override, accepted or refused, is recorded) and
  the legacy-state rule (absent `featureClass` → treat as `"code"`, proceed on the unchanged code
  path, no retro-classification). (FR-1.6, FR-1.7, R4)
- [ ] 2.8. In `## State File Management`, add `"featureClass": null` and the `classification` object
  (`basis`, `decidedAt`, `override`, `tasksValidatedUnderExemption`, `reclassification`) as sibling
  top-level keys after `taskStatus`, and add the schema prose documenting `featureClass`'s two
  permitted values `"code"`/`"non-code"`, its `null`-before-gate and absent-in-legacy-files states,
  and each `classification` sub-key including the `override` and `reclassification` object shapes.
  State that `featureClass` is the single source of truth and `classification` carries only
  provenance. (FR-1.1, FR-1.5, FR-1.6, FR-3.1, FR-3.3, NFR-5)
- [ ] 2.9. Confirm the section mentions no `ready-to-merge`, no label operation, and no CI reference.
  (FR-9.1, FR-10.1)
- [ ] 2.10. Test: create `tests/test_orchestrator_feature_class.py` (stdlib-only `unittest`, paths
  resolved relative to the test file) asserting: the classification-gate heading exists and its
  offset lies **between** the consistency-gate section and the `implementation` section (ordering,
  not mere presence); `featureClass` appears in the state-file JSON block; both permitted values are
  named in the schema prose; the five `classification` sub-keys are documented; the fail-safe default
  is stated with its ambiguity triggers; the text states classification derives from declared task
  outputs and explicitly disclaims deriving it from a git diff; the C0 block is present under its
  exact heading; and no `ready-to-merge` token appears anywhere in the classification-gate region.
  Run the full suite. (FR-11, FR-11.1, FR-11.2, NFR-6)

**Requirements:** FR-1, FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7, FR-11.1, FR-11.2,
NFR-5, NFR-6
**Design Reference:** C0, C1, C2; DD-1, DD-5; risks R4, R7
**Files:** `agents/orchestrator.md` (modify), `tests/test_orchestrator_feature_class.py` (new)

---

## Task 3: Orchestrator — per-task routing of `featureClass` (C3, I1)
- [ ] 3. Forward `featureClass` and `taskProducesApplicationCode` to Stages 2, 3, 4 and 5 without changing the stage order or the code path.

**Description:** Add the shared routing preamble and the stage-specific bullets inside
``### `implementation` ``. No new stage, no reordering, no new user prompt. Depends on Tasks 1 and 2
(`featureClass` must be defined and recorded before it can be routed).

**Sub-tasks:**
- [ ] 3.1. Add a short preamble immediately above **Stage 1** naming the two forwarded values:
  `featureClass` (current value from `.spec-state.json`) and `taskProducesApplicationCode`
  (`true`/`false`, derived for *this task* from its declared outputs using the C0 allow-list).
  (FR-2, I1)
- [ ] 3.2. Add the NFR-4 guard sentence once, in that preamble: where `featureClass` is `"code"`
  these two values change nothing — same stages, same order, same verdict formats, same labels, no
  additional user prompt. (FR-2.3, NFR-4)
- [ ] 3.3. Extend the **Stage 2 (task-tester)** input bullets: pass both values; where `featureClass`
  is `"non-code"` **and** `taskProducesApplicationCode` is `false`, instruct the tester to apply its
  **no-code behaviour**. (FR-2.1)
- [ ] 3.4. Extend the **Stage 3 (task-validator)** input bullets: pass both values; under the same
  condition instruct the validator to run in **artifact-conformance mode**, stating that the
  validator never selects the mode itself and the instruction is the only entry point; and append the
  task number to `classification.tasksValidatedUnderExemption` when the instruction is issued.
  (FR-2.1, FR-5.1, FR-3.3, DD-2)
- [ ] 3.5. Extend the **Stages 4 & 5 (reviewers)** input bullets: pass `featureClass`; everything else
  about the invocation is unchanged — `mode: task`, both concurrent, both Opus. (FR-2)
- [ ] 3.6. Confirm the stage order and the "reviews run only after validation passes" gate are
  untouched. (FR-2.4)
- [ ] 3.7. Test: extend `tests/test_orchestrator_feature_class.py` with assertions that routing
  bullets naming `featureClass` appear inside the Stage 2, Stage 3 and Stages 4 & 5 regions; that
  `taskProducesApplicationCode` appears in the Stage 2 and Stage 3 regions; that the
  artifact-conformance instruction and the `tasksValidatedUnderExemption` append are stated in the
  Stage 3 region; that the NFR-4 guard sentence is present; and that the stage sequence
  execute → test → validate → review still appears in order. Run the full suite. (FR-11.2, NFR-4,
  NFR-6)

**Requirements:** FR-2, FR-2.1, FR-2.3, FR-2.4, FR-3.3, FR-5.1, FR-11.2, NFR-4, NFR-6
**Design Reference:** C3; interface I1; DD-2
**Files:** `agents/orchestrator.md` (modify), `tests/test_orchestrator_feature_class.py` (modify)

---

## Task 4: Orchestrator — reclassification fallback, non-code → code (C4)
- [ ] 4. Add the monotonic reclassification subsection with its three triggers and its retry accounting.

**Description:** Add a new `####`-level subsection at the end of ``### `implementation` ``, after the
`On **fail**` bullet, headed `#### Reclassification: non-code → code (fallback, D2)`. Depends on
Tasks 1, 2 and 3 (it updates the state keys from Task 2 and reacts to the stages wired in Task 3).

**Sub-tasks:**
- [ ] 4.1. Specify the three triggers: **T1** the task-tester reports the task in fact produced
  application code; **T2** the task-validator returns FAIL citing application-code modification under
  artifact-conformance mode; **T3** the orchestrator itself sees an application-code path in the
  executor's changed-files summary. (FR-3, FR-4.5, FR-5.6)
- [ ] 4.2. Specify the actions on any trigger: set `featureClass = "code"` and populate
  `classification.reclassification` with the triggering path(s), task number, trigger source and
  timestamp; report the reclassification to the user naming the file(s) and the task. (FR-3.1, NFR-5)
- [ ] 4.3. Specify that the current task's **Stage 2 (test)** and **Stage 3 (validation)** re-run
  under the code path — tests required — before the task may be marked complete. (FR-3.2)
- [ ] 4.4. Specify that `classification.tasksValidatedUnderExemption` is kept as written — a
  permanent record, not a live flag — and that when it is non-empty and the feature has been
  reclassified, the Feature Review Gate invocation must state that those tasks' outputs are reviewed
  under the code path. (FR-3.3)
- [ ] 4.5. State monotonicity explicitly: once `featureClass` is `"code"` it is never set back to
  `"non-code"` for the remainder of the feature — not by a later artifact-only task, and not by a
  user override. (FR-3.4, FR-1.6)
- [ ] 4.6. Settle retry accounting explicitly: T2 is a genuine validator FAIL and flows through the
  **existing** `On **fail**` branch unchanged (`retryCount += 1`, `blocked:validation`, executor
  re-run); T1 and T3 are caught before a validation verdict exists, re-run stages 2–3 within the same
  attempt, and do **not** increment `retryCount` and do **not** set a label. No new label is
  introduced on any path. (FR-3.2, FR-10.1, DD-8)
- [ ] 4.7. Test: extend `tests/test_orchestrator_feature_class.py` with assertions that the
  reclassification subsection exists under its exact heading and sits inside the `implementation`
  section after the `On **fail**` bullet; that all three triggers are named; that monotonicity is
  stated; that re-running test + validation under the code path is stated; that
  `classification.reclassification` and `tasksValidatedUnderExemption` are referenced; that the
  T1/T3-do-not-increment-`retryCount` rule is stated; and that every `blocked:` label name appearing
  in the new region is drawn from the frozen five-name vocabulary. Run the full suite. (FR-11.2,
  FR-10.1, NFR-6)

**Requirements:** FR-3, FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-4.5, FR-5.6, FR-10.1, FR-11.2, NFR-5,
NFR-6
**Design Reference:** C4; DD-8; risk R4; Flow C
**Files:** `agents/orchestrator.md` (modify), `tests/test_orchestrator_feature_class.py` (modify)

---

## Task 5: Orchestrator — Feature Review Gate wiring + `ready-to-merge` singleton regression (C5)
- [ ] 5. Pass `featureClass` and the non-code scope instruction to the feature-review invocation, add the Critical Rules line, and lock the single `ready-to-merge` application point with a test.

**Description:** Add exactly one bullet to the Feature Review Gate's "Pass each:" list and one line
to `## Critical Rules`, leaving the `**On PASS (both reviewers PASS)**` branch edited **in no way**.
Then add the regression module that makes any future second application point a test failure.
Depends on Tasks 1–4. This is the task where the FR-9 invariant is at greatest risk; treat the PASS
branch as read-only.

**Sub-tasks:**
- [ ] 5.1. Add one bullet to the Feature Review Gate "Pass each:" list: pass `featureClass`; where it
  is `"non-code"`, add the **non-code review scope** instruction (the `feature`-mode diff will be
  empty or contain only non-code artifacts, so the reviewer resolves and reviews the non-code review
  scope defined in its own contract and must return exactly one of `PASS`/`FAIL`); and where
  `classification.tasksValidatedUnderExemption` is non-empty **and** the feature was reclassified,
  additionally state that those tasks' outputs are reviewed under the code path. (FR-2.2, FR-3.3)
- [ ] 5.2. Confirm the invocation stays concurrent and Opus-pinned, and that the `On PASS` branch
  retains, unedited: the `blocked:feature-review` clear preceding the single
  `label set ready-to-merge`, the "This is the **only** place `ready-to-merge` is ever applied"
  sentence, the draft-on-blocking-finding rule, and the human merge gate. Add no class-conditional
  wording anywhere in that branch. (FR-2.2, FR-9, FR-9.1, FR-9.2, FR-9.3, FR-9.4, NFR-1)
- [ ] 5.3. Add one line to `## Critical Rules`, adjacent to the existing `ready-to-merge` rule:
  never treat `featureClass: "non-code"` as an exemption from any gate — it changes which artifacts
  the tester, validator and reviewers examine, never whether they run, and never what a PASS
  requires. (FR-9.1, NFR-1, DD-10)
- [ ] 5.4. Test: create `tests/test_orchestrator_ready_to_merge_singleton.py` asserting: exactly
  **one** `ready-to-merge` *set* operation in the whole body (regex over
  `op:\s*set[^}]*ready-to-merge` plus prose `set … ready-to-merge` forms, de-duplicated by offset);
  its offset lies inside the Feature Review Gate `On PASS (both reviewers PASS)` region; the "only
  place `ready-to-merge` is ever applied" sentence survives; **no** `ready-to-merge` token appears
  anywhere in the classification-gate or reclassification regions; and every `blocked:` label name in
  the file is drawn from the frozen five-name vocabulary (`blocked:validation`,
  `blocked:code-review`, `blocked:security-review`, `blocked:feature-review`, alongside
  `ready-to-merge`). Additionally extend `tests/test_orchestrator_feature_class.py` with an assertion
  that the Feature Review Gate region names `featureClass` and the non-code review scope instruction.
  Run the full suite, including `tests/test_orchestrator_label_lifecycle.py`, and confirm every
  pre-existing assertion in it still passes. (FR-11.1, FR-11.2, FR-11.6, FR-9.1, FR-10.1, AC-7)

**Requirements:** FR-2, FR-2.2, FR-3.3, FR-9, FR-9.1, FR-9.2, FR-9.3, FR-9.4, FR-10.1, FR-11.1,
FR-11.2, FR-11.6, NFR-1, NFR-6
**Design Reference:** C5; C12 (`test_orchestrator_ready_to_merge_singleton`); DD-10; Flows A and D
**Files:** `agents/orchestrator.md` (modify),
`tests/test_orchestrator_ready_to_merge_singleton.py` (new),
`tests/test_orchestrator_feature_class.py` (modify)

---

## Task 6: `agents/task-tester.md` — no-code behaviour (C6, I2)
- [ ] 6. Define what the task-tester does when a task produces no application code, and forbid vacuous tests.

**Description:** Add a new `##`-level section between `## Testing Rules` and `## Completion Summary`
headed `## No-Code Behaviour (tasks that produce no application code)`, carrying the C0 allow-list
block verbatim, plus one added line in `## Rules`. Independent of Tasks 3–5, but the C0 block must be
copied byte-for-byte from `agents/orchestrator.md` (Task 2), so run it after Task 2.

**Sub-tasks:**
- [ ] 6.1. Specify entry: the behaviour applies when the orchestrator states
  `featureClass: non-code` and `taskProducesApplicationCode: false`. Replicate the C0 block verbatim
  under its exact heading. (FR-4, FR-2.1, DD-5)
- [ ] 6.2. Specify the prohibition with its forms enumerated: no vacuous or placeholder tests written
  to satisfy a tests-exist expectation — an assertion that cannot fail; a test asserting only that a
  file exists when the requirement is about its content; a test asserting a constant; a test with no
  assertion. State the reason: a vacuous test is worse than no test, because it converts a known gap
  into a false signal. (FR-4.1)
- [ ] 6.3. Specify the preferred path: where a produced artifact is machine-checkable, **write the
  check** in the project's conventional test directory following the project's existing test
  patterns, with the enumerated examples — a structural or content lint over a markdown contract; a
  schema or frontmatter check; a link/path-resolution check; a cross-file consistency check between
  two copies of a document. This must appear **before** the fallback in the section. (FR-4.2)
- [ ] 6.4. Specify the fallback: only if no meaningful machine check is feasible, emit the
  **"no applicable tests" completion block** in the I2 shape — retaining the existing
  `## Tester Summary: Task <N>` header, with `### Result: no applicable tests`,
  `### Artifacts Produced` (each artifact, the requirement it satisfies, and why no automated check
  is feasible), `### Machine Checks Written`, `### Existing Tests Run`, and `### Issues Found`. State
  that an empty or improvised summary is not an acceptable substitute. (FR-4.3, I2)
- [ ] 6.5. Specify that in **all** cases the tester runs the project's existing tests in the affected
  area and reports regressions, exactly as today. (FR-4.4)
- [ ] 6.6. Specify escalation: if the task in fact produced application code, report that fact to the
  orchestrator naming the path(s) — which triggers reclassification — and write tests for that code
  normally; do not apply the no-code behaviour to it. (FR-4.5)
- [ ] 6.7. Add the `## Rules` line: never write a placeholder or vacuous test to satisfy a
  tests-exist expectation; emit the "no applicable tests" block instead. Confirm the tester's
  never-modify-implementation rule is unchanged. (FR-4.1, NFR-9)
- [ ] 6.8. Test: create `tests/test_tester_no_code_behaviour.py` asserting: the section heading is
  present with the specified placement; the vacuous/placeholder prohibition appears with its
  enumerated forms; the machine-checkable preference precedes the fallback (offset ordering); the
  "no applicable tests" block is specified and names artifact + requirement + why-no-check; the
  run-existing-tests-in-all-cases rule survives; the FR-4.5 escalation is present; the new `## Rules`
  line is present; and the frontmatter `tools:` list is unchanged from the pre-change set. Run the
  full suite. (FR-11.1, FR-11.4, NFR-3, NFR-6)

**Requirements:** FR-4, FR-4.1, FR-4.2, FR-4.3, FR-4.4, FR-4.5, FR-2.1, FR-11.1, FR-11.4, NFR-3,
NFR-6, NFR-9
**Design Reference:** C6; interface I2; DD-5
**Files:** `agents/task-tester.md` (modify), `tests/test_tester_no_code_behaviour.py` (new)

---

## Task 7: `agents/task-validator.md` — artifact-conformance mode (C7, I3)
- [ ] 7. Add artifact-conformance mode, entered only on the orchestrator's instruction, with its verdict block — deleting no existing check.

**Description:** Three edits to `agents/task-validator.md`: qualify `### 2. Test Coverage` as
*(code mode)* with a conditional lead-in and add a sibling `### 2A. Artifact Conformance`; add a new
`## Artifact-Conformance Mode` section between `## Validation Checklist` and `## Verdict`, carrying
the C0 block verbatim; and add the I3 verdict variant to `## Verdict`. The three existing
`### 2. Test Coverage` checkboxes are **not deleted**, so the code path reads identically to today.
Run after Task 2 (the C0 source) and Task 3 (the instruction that enters the mode).

**Sub-tasks:**
- [ ] 7.1. Rename the heading to `### 2. Test Coverage  *(code mode)*` and add the lead-in sentence:
  in artifact-conformance mode this section is replaced by §2A below; in all other cases it applies
  unchanged. Leave all three existing checkboxes in place. (FR-5.4, NFR-4)
- [ ] 7.2. Add the sibling subsection
  `### 2A. Artifact Conformance  *(artifact-conformance mode only)*` in the checklist. (FR-5, FR-5.4)
- [ ] 7.3. Add the `## Artifact-Conformance Mode` section stating instruction-only entry in as many
  words — *never self-selected by the validator because a diff looked empty* — and carrying the C0
  block verbatim. (FR-5.1, DD-2, DD-5)
- [ ] 7.4. Specify mapping: map every cited requirement to at least one **named produced artifact** —
  a file path, or an entry in `.specs/features/<feature-name>/vault/.write-log.jsonl` identified by
  its `operation` + `target` (and `section` where present) — and **read** it. A requirement with no
  mapped artifact is a FAIL. (FR-5.2, I4)
- [ ] 7.5. Specify substance: each mapped artifact exists, is non-empty, and substantively states or
  delivers what the cited requirement demands; a placeholder, stub, TODO-only or heading-only
  artifact is a **FAIL**. For a changelog-mapped requirement, `target`, `operation` and `intent` must
  be consistent with the requirement — and the validator reads the changelog, never the vault note.
  (FR-5.3, NFR-8)
- [ ] 7.6. Specify that in this mode the absence of unit tests is **not** a failure, replacing the
  unconditional "at least one test exists for this requirement" check **for this mode only**; and
  that machine checks written under FR-4.2 are run with Bash, with any failure a FAIL. (FR-5.4,
  FR-5.5)
- [ ] 7.7. Specify code detection: if any file modified by this task is application code per the
  allow-list, **refuse the exemption**, return `FAIL`, and report the offending path(s) so the
  orchestrator reclassifies — never a silent switch to code-mode validation, because the orchestrator
  owns the classification. (FR-5.6, FR-3)
- [ ] 7.8. Specify the retained checks (§3 Scope Check and §4 Quality Check remain fully active: no
  scope creep, `.specs/steering/tech.md` conventions respected, no leftover TODOs) and cite the
  existing all-or-nothing "NEVER partially pass" rule, leaving that rule's own text untouched.
  (FR-5.7, FR-5.9)
- [ ] 7.9. Add the I3 verdict variant to `## Verdict` as an additional labelled block: the
  `## Validator Verdict: Task <N>` header and `### Result:` line keep their exact existing shape; a
  `### Mode: artifact-conformance` line is emitted **only** in this mode; per-requirement lines carry
  artifact + substantive + tests-n/a (or the machine check run); plus `### Artifacts Reviewed` and
  `### Notes`, with the FAIL variant in the same shape. The existing PASS and FAIL blocks are
  unchanged, and no `### Mode:` line is added to the code path. (FR-5.8, NFR-4, DD-4)
- [ ] 7.10. Test: create `tests/test_validator_artifact_conformance.py` asserting: the
  `## Artifact-Conformance Mode` heading is present; instruction-only entry is asserted both by the
  "never self-selected" phrasing **and** by the absence of any self-entry condition; the
  tests-absence-is-not-a-failure statement is scoped to the mode; placeholder/stub/TODO artifact →
  FAIL; application-code detection → FAIL plus reported path; the literal `.write-log.jsonl` path is
  present; the scope and quality checks are still referenced as active; the all-or-nothing rule is
  still present; the original `### 2. Test Coverage` checkboxes are still present (nothing deleted);
  the `### Mode: artifact-conformance` line appears only in the artifact-conformance verdict variant;
  and the frontmatter `tools:` list is unchanged. Run the full suite. (FR-11.1, FR-11.3, NFR-3,
  NFR-4, NFR-6)

**Requirements:** FR-5, FR-5.1, FR-5.2, FR-5.3, FR-5.4, FR-5.5, FR-5.6, FR-5.7, FR-5.8, FR-5.9,
FR-11.1, FR-11.3, NFR-3, NFR-4, NFR-6, NFR-7, NFR-8, NFR-9
**Design Reference:** C7; interfaces I3, I4; DD-2, DD-4, DD-5
**Files:** `agents/task-validator.md` (modify), `tests/test_validator_artifact_conformance.py` (new)

---

## Task 8: Both reviewers — shared non-code review scope + finding classes (C8, C9, I5)
- [ ] 8. Give `code-reviewer` and `security-reviewer` a verbatim-identical non-code review scope section and their own finding-class lists, so an empty or docs-only diff yields a real PASS or FAIL.

**Description:** Insert the same `## Non-Code Review Scope (empty or non-code diff)` section into
both reviewer files, immediately after `## On Invocation` and before `## What to Hunt For`, with
verbatim-identical text (asserted by test) and the C0 block verbatim; add a
`### Non-code scope (FR-7)` subsection to the code-reviewer's `## What to Hunt For` and a
`### Non-code scope (FR-8)` subsection to the security-reviewer's; add one `## Rules` bullet to each;
and extend the PASS/FAIL blocks with the I5 additions. Run after Tasks 2, 6 and 7 — this task's test
module also asserts that all five copies of the C0 block are identical, which is only possible once
they all exist. Neither reviewer gains a tool or a write target.

**Sub-tasks:**
- [ ] 8.1. In both files, add the shared section with identical text specifying the resolution order:
  establish the existing diff first (`git diff` for `task` mode, `git diff <base>...HEAD` for
  `feature` mode); partition the changed paths with the C0 allow-list; if the diff contains **one or
  more application-code paths**, review it exactly as today and stop — the non-code scope does not
  apply; if the diff is empty **or** contains only non-code artifacts, resolve and review the
  non-code review scope. State that the orchestrator's prompt may confirm the situation but the
  reviewer does not wait for it. (FR-6, FR-6.2, DD-2)
- [ ] 8.2. Define the scope as the union of (a) the feature's spec artifacts (`requirements.md`,
  `design.md`, `tasks.md`, and `scope.md` where present, under `.specs/features/<feature-name>/`),
  (b) every non-code file in the diff for the reviewer's mode, and (c) the vault changelog entries at
  `.specs/features/<feature-name>/vault/.write-log.jsonl`. (FR-6.1)
- [ ] 8.3. Specify changelog reading: read the JSON-lines changelog itself with `Read` (`operation`,
  `target`, `intent`, optional `section`/`bytes`); **never** open the vault note named by `target`;
  the in-repo changelog is the entire reviewable surface; a needed vault fact means halting with
  `VAULT REQUEST: <need>` for the orchestrator to fulfil through vault-reader. (FR-6.8, NFR-8)
- [ ] 8.4. Specify the mandatory verdict: exactly one of `PASS` or `FAIL`; a hedge, an abstention, an
  "N/A", a "nothing to review", or a verdict with no result line is **not a permitted outcome** —
  forbidden by name. (FR-6.3, AC-5)
- [ ] 8.5. Specify the empty-scope FAIL as a single **Critical** finding ("the feature produced no
  reviewable output"), reusing the existing severity rule and FAIL block rather than a new verdict
  kind; and state the attribution rule that makes the emptiness test able to fire at all: the
  feature's own `requirements.md`/`design.md`/`tasks.md`/`scope.md` are the **plan** and are never
  counted as output; a spec artifact counts as output only when a task declares it in that task's
  `**Files:**` field or the executor reported writing it; item (a) is therefore review context, while
  (b), (c) and any promoted (a) artifact are the reviewable output the emptiness test counts.
  (FR-6.4, AC-4, DD-3)
- [ ] 8.6. Specify that the `Scope Reviewed` section enumerates what was actually inspected, listing
  each vault changelog entry **by target and operation**; that the severity model is unchanged
  (Critical/High block, Medium/Low report only); and that resolving the scope uses only the existing
  `Read`/`Glob`/`Grep`/`Bash` tools, both reviewers remaining read-only with no new tool and no new
  write target. Replicate the C0 block verbatim. (FR-6.5, FR-6.6, FR-6.7, NFR-3, NFR-9, DD-5)
- [ ] 8.7. Extend both verdict blocks per I5: a
  `### Scope Resolution: non-code (diff empty or non-code artifacts only)` line emitted **only** when
  the non-code scope was resolved, plus the enumerated `Scope Reviewed`. The existing headers,
  `— PASS`/`— FAIL` suffixes and severity sections are unchanged, and no scope-resolution line is
  added to the code path. (FR-6.3, FR-6.5, NFR-4, DD-4)
- [ ] 8.8. Add `### Non-code scope (FR-7)` to `agents/code-reviewer.md`'s `## What to Hunt For`:
  internal contradiction / unfollowable instruction; stale or dangling references (broken paths, dead
  links, non-existent requirement or task IDs, renamed or removed artifacts); duplication, divergence
  and incompleteness — including two synchronised copies of a document where both are in scope,
  subject to the NFR-10 pending-sync allowance (a repository copy legitimately ahead of an unsynced
  installed copy is **not** a finding; an installed copy that *contradicts* the authoritative
  repository copy is) — plus placeholders and unresolved TODOs; vault-update coherence (each recorded
  write traceable to a requirement, `target`/`operation`/`intent` consistent with the stated intent).
  Add the `## Rules` bullet requiring a concrete failure scenario for every blocking non-code
  finding — the reader or downstream consumer misled and the wrong outcome that follows — and leave
  the existing "do not re-litigate requirement conformance" rule intact, citing it from the new
  section. (FR-7, FR-7.1, FR-7.2, FR-7.3, FR-7.4, FR-7.5, NFR-10, R8)
- [ ] 8.9. Add `### Non-code scope (FR-8)` to `agents/security-reviewer.md`'s `## What to Hunt For`:
  committed credential material in prose, reported as **type + `path:line` with the value redacted**,
  never reproduced (for a changelog entry, the entry's `target` plus its line number in the
  changelog); sensitive disclosure (internal hostnames, endpoints, account identifiers, PII,
  infrastructure detail); unsafe documented instructions, with a documented unsafe default a finding
  in its own right; vault-write exposure (changelog entries placing sensitive material into the
  vault, or whose `target` resolves outside the declared vault path). Add the `## Rules` bullet
  requiring a concrete attack or exposure scenario for every blocking finding. (FR-8, FR-8.1, FR-8.2,
  FR-8.3, FR-8.4, FR-8.5, NFR-7)
- [ ] 8.10. Test: create `tests/test_reviewers_non_code_scope.py`, parameterised over both reviewer
  paths, asserting for each file: the `## Non-Code Review Scope` heading with the specified
  placement; all three scope components; the literal path
  `.specs/features/<feature-name>/vault/.write-log.jsonl`; the diff-first-then-fallback resolution
  order; the mandatory `PASS`/`FAIL` with hedge / N-A / nothing-to-review explicitly forbidden; the
  empty-scope FAIL and the attribution rule; a "never read the vault note" statement plus the
  `VAULT REQUEST` escalation; the severity model restated unchanged; and the frontmatter `tools:`
  list unchanged from the pre-change set. Plus a cross-file assertion that the shared section is
  normalised-identical in both reviewers, each reviewer's own finding-class subsection asserted
  separately, and `test_allow_list_blocks_identical` asserting the C0 block is normalised-identical
  across all five agent files (`orchestrator`, `task-tester`, `task-validator`, `code-reviewer`,
  `security-reviewer`). Run the full suite. (FR-11.1, FR-11.5, NFR-3, NFR-6, NFR-8, R1)

**Requirements:** FR-6, FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-6.5, FR-6.6, FR-6.7, FR-6.8, FR-7,
FR-7.1, FR-7.2, FR-7.3, FR-7.4, FR-7.5, FR-8, FR-8.1, FR-8.2, FR-8.3, FR-8.4, FR-8.5, FR-9.2,
FR-11.1, FR-11.5, NFR-3, NFR-4, NFR-6, NFR-7, NFR-8, NFR-9, NFR-10
**Design Reference:** C8, C9; interfaces I4, I5; DD-2, DD-3, DD-4, DD-5; risks R1, R5, R8; Flows A,
B, D
**Files:** `agents/code-reviewer.md` (modify), `agents/security-reviewer.md` (modify),
`tests/test_reviewers_non_code_scope.py` (new)

---

## Task 9: CI review-gate lock test (C12 / FR-10, NFR-2)
- [ ] 9. Add a read-only regression module asserting `ci-templates/workflows/sdd-review-gate.yml` still enforces the gate and carries no bypass.

**Description:** Create `tests/test_review_gate_untouched.py`, which reads the CI template and locks
its semantics so no future change to this track can weaken server-side enforcement. The workflow file
itself is **not modified by this task or any other** — the module only reads it. Independent of Tasks
1–8; sequenced here because the invariant it locks is the one the whole feature must preserve.

**Sub-tasks:**
- [ ] 9.1. Assert the gate conditions survive: `"ready-to-merge" in labels` is present;
  `startswith("blocked:")` is present; both `sys.exit(1)` failure branches are present; the
  `github.event_name == 'pull_request'` guard is present; and `permissions:` / `contents: read` are
  unchanged. (FR-11.7, NFR-2)
- [ ] 9.2. Assert **no** token matching
  `(?i)(bypass|exempt|escape[- ]?hatch|override|skip[-_ ]?gate|non-?code|featureclass)` appears
  anywhere in the file, and that every label-shaped literal in it is drawn from the frozen five-name
  vocabulary. (FR-10, FR-10.1, FR-10.2)
- [ ] 9.3. Test: run the new module, run the full suite, and confirm
  `git diff main...HEAD -- ci-templates/ .github/ hooks/ install.sh` is empty — no CI template, no
  workflow, no hook and no installer change anywhere in this feature's diff. (FR-11.7, FR-12.1,
  NFR-2, AC-6)

**Requirements:** FR-10, FR-10.1, FR-10.2, FR-11, FR-11.1, FR-11.7, NFR-1, NFR-2, NFR-6
**Design Reference:** C12 (`test_review_gate_untouched`); AC-6
**Files:** `tests/test_review_gate_untouched.py` (new). Reads, and does **not** modify,
`ci-templates/workflows/sdd-review-gate.yml`.

---

## Task 10: Documentation — repository `CLAUDE.md` + `README.md` (C11)
- [ ] 10. Describe the classification step and the non-code track in the repository-root `CLAUDE.md` and the README, and assert the new content.

**Description:** Update the repository-root `CLAUDE.md` phase-gates section and the README's
pipeline description. **The repository copy only** — no pipeline stage writes to
`~/.claude/CLAUDE.md` or to any other path under `~/.claude/`; the operator syncs the global copy by
running `./install.sh` after merge. Done last, after the behaviour it describes exists. Depends on
Task 1 (the byte-identity carve-out) and on Tasks 2–8 for accuracy. All prose in English (NFR-11).

**Sub-tasks:**
- [ ] 10.1. In `CLAUDE.md` `### Phase Gates`, change the phase line to
  `Requirements → Design → Tasks → [Consistency Check] → [Classification] → Implementation → [Feature Review] → Complete`
  and add a paragraph stating: classification is explicit and recorded in `.spec-state.json` under
  `featureClass`; a `non-code` feature runs the same five stages, with the validator in
  artifact-conformance mode (tests optional, a placeholder artifact still FAILs) and both reviewers
  reviewing the spec artifacts, the committed docs and the vault changelog; **`ready-to-merge` still
  requires a real whole-feature review PASS and there is no bypass**. (FR-12)
- [ ] 10.2. State in that paragraph that a non-code feature which turns out to touch application code
  falls back to the full code path, with the exemption withdrawn. (FR-12.2)
- [ ] 10.3. Hold the load-bearing constraint: the edit must **not** alter the three lines
  `github_agent_lines()` extracts from `### Agent Ownership` — the `- github-agent` bullet, the "only
  component that runs `gh`/`git push`" line, and the "No agent modifies another agent's artifact"
  invariant — because `test_two_claude_ownership_lines_consistent` compares them strictly across both
  copies and is **not** carved out. Rename no existing heading (a rename false-FAILs the Task-1
  discriminator, limit L2). Write nothing under `~/.claude/`. (FR-12.1, NFR-10, DD-7)
- [ ] 10.4. In `README.md` `### Review the workflow`, insert a classification step between the
  current items 4 (consistency check) and 5 (implementation), renumbering the list, and extend the
  implementation item to note that for a `non-code` feature the validator runs artifact-conformance
  and the reviewers review the resolved non-code scope. (FR-13)
- [ ] 10.5. Add one sentence to the README stating that a non-code feature reaches `ready-to-merge`
  through the same audited path as a code feature and that no bypass label exists. Leave the
  `## GitHub integration & CI enforcement` label vocabulary untouched. (FR-13.1, FR-10.1)
- [ ] 10.6. Test: create `tests/test_docs_non_code_track.py` asserting — **reading only the
  repository copies, never anything under `~/.claude/`** — that repo `CLAUDE.md` names
  `featureClass`, carries the classification step in the phase-gate line, describes the
  artifact-conformance/tests-optional behaviour and the reviewers' non-code scope, restates that
  `ready-to-merge` still requires a real whole-feature review PASS, and states the
  fallback-to-code-path rule; and that the README describes the classification step and the non-code
  track in its pipeline description and states that no bypass label exists. Then run the full suite —
  including `tests/test_docs_updates.py` — and confirm it passes with the repository copy ahead of
  the unsynced global copy, and that `git diff` contains no write under `~/.claude/`. (FR-11.1,
  FR-12, FR-12.1, FR-12.2, FR-13, FR-13.1, NFR-10, NFR-11, AC-10)

**Requirements:** FR-12, FR-12.1, FR-12.2, FR-13, FR-13.1, FR-10.1, FR-11.1, NFR-6, NFR-10, NFR-11
**Design Reference:** C11(a), C11(b); DD-7, DD-9; A1-resolution limits L1–L4
**Files:** `CLAUDE.md` (repository root, modify), `README.md` (modify),
`tests/test_docs_non_code_track.py` (new)

---

## Requirement Coverage

| Requirement | Task(s) |
|-------------|---------|
| FR-1        | Task 2 |
| FR-1.1      | Task 2 |
| FR-1.2      | Task 2 |
| FR-1.3      | Task 2 |
| FR-1.4      | Task 2 |
| FR-1.5      | Task 2 |
| FR-1.6      | Task 2, Task 4 |
| FR-1.7      | Task 2 |
| FR-2        | Task 3, Task 5 |
| FR-2.1      | Task 3, Task 6 |
| FR-2.2      | Task 5 |
| FR-2.3      | Task 3 |
| FR-2.4      | Task 3 |
| FR-3        | Task 4, Task 7 |
| FR-3.1      | Task 2, Task 4 |
| FR-3.2      | Task 4 |
| FR-3.3      | Task 2, Task 3, Task 4, Task 5 |
| FR-3.4      | Task 4 |
| FR-4        | Task 6 |
| FR-4.1      | Task 6 |
| FR-4.2      | Task 6 |
| FR-4.3      | Task 6 |
| FR-4.4      | Task 6 |
| FR-4.5      | Task 4, Task 6 |
| FR-5        | Task 7 |
| FR-5.1      | Task 3, Task 7 |
| FR-5.2      | Task 7 |
| FR-5.3      | Task 7 |
| FR-5.4      | Task 7 |
| FR-5.5      | Task 7 |
| FR-5.6      | Task 4, Task 7 |
| FR-5.7      | Task 7 |
| FR-5.8      | Task 7 |
| FR-5.9      | Task 7 |
| FR-6        | Task 8 |
| FR-6.1      | Task 8 |
| FR-6.2      | Task 8 |
| FR-6.3      | Task 8 |
| FR-6.4      | Task 8 |
| FR-6.5      | Task 8 |
| FR-6.6      | Task 8 |
| FR-6.7      | Task 8 |
| FR-6.8      | Task 8 |
| FR-7        | Task 8 |
| FR-7.1      | Task 8 |
| FR-7.2      | Task 8 |
| FR-7.3      | Task 8 |
| FR-7.4      | Task 8 |
| FR-7.5      | Task 8 |
| FR-8        | Task 8 |
| FR-8.1      | Task 8 |
| FR-8.2      | Task 8 |
| FR-8.3      | Task 8 |
| FR-8.4      | Task 8 |
| FR-8.5      | Task 8 |
| FR-9        | Task 5 |
| FR-9.1      | Task 2, Task 5 |
| FR-9.2      | Task 5, Task 8 |
| FR-9.3      | Task 5 |
| FR-9.4      | Task 5 |
| FR-10       | Task 9 |
| FR-10.1     | Task 2, Task 4, Task 5, Task 9, Task 10 |
| FR-10.2     | Task 9 |
| FR-11       | Tasks 1–10 (every task's final test sub-task) |
| FR-11.1     | Tasks 1, 2, 5, 6, 7, 8, 9, 10 |
| FR-11.2     | Task 2, Task 3, Task 4, Task 5 |
| FR-11.3     | Task 7 |
| FR-11.4     | Task 6 |
| FR-11.5     | Task 8 |
| FR-11.6     | Task 5 |
| FR-11.7     | Task 9 |
| FR-11.8     | Task 1 |
| FR-12       | Task 10 |
| FR-12.1     | Task 10 (+ global constraint 1 on every task; asserted by sub-tasks 9.3 and 10.6) |
| FR-12.2     | Task 10 |
| FR-13       | Task 10 |
| FR-13.1     | Task 10 |
| NFR-1       | Task 5, Task 9 |
| NFR-2       | Task 9 (+ global constraint 2 on every task) |
| NFR-3       | Task 6, Task 7, Task 8 (+ global constraint 5 on every task) |
| NFR-4       | Task 3, Task 7, Task 8 |
| NFR-5       | Task 2, Task 4 |
| NFR-6       | Tasks 1–10 |
| NFR-7       | Task 7, Task 8 |
| NFR-8       | Task 7, Task 8 |
| NFR-9       | Task 6, Task 7, Task 8 |
| NFR-10      | Task 1, Task 8, Task 10 |
| NFR-11      | Task 10 (all prose authored in English; the spec artifacts keep EARS `FR-N`/`NFR-N` numbering) |

Every FR-1…FR-13 and NFR-1…NFR-11 is covered by at least one task, and every task cites at least one
requirement. No orphan tasks; no orphan requirements.

### Deliberately not tasked

- **`ci-templates/workflows/sdd-review-gate.yml`** — locked by Task 9's read-only assertions and
  modified by nothing (FR-10, NFR-2, AC-6).
- **`install.sh`, `~/.claude/`, and the post-merge global sync** — out of scope by A1; the operator
  runs `./install.sh` after merge (FR-12.1, NFR-10).
- **`agents/tasks-agent.md` rule 5** — risk R9 records that its wording reads as excluding non-code
  task lists. No requirement authorises the change, so no task edits it; it is flagged for a separate
  follow-up requirement.
- **`agents/vault-writer.md`** — C10 consumes its existing changelog contract unchanged; adding a
  field or a path would be a new write target (NFR-3).
- **AC-1, AC-2, AC-3, AC-5 and AC-9** are behavioural end-to-end scenarios over *future* features
  (design Flows A, B, C and E). They are discharged by the contract text plus the structural-lint
  assertions above, not by a runnable test of their own — no task can execute a future feature's
  pipeline. AC-4 is asserted within sub-task 8.10, and AC-6, AC-7, AC-8 and AC-10 are asserted
  directly by Tasks 9, 5, 1 and 10 respectively.
