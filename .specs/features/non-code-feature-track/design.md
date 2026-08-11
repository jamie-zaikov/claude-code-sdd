# Design: non-code-feature-track

<!-- Owned by design-agent. Attempt 2 (restart). Do not edit manually during SDD workflow. -->
<!-- Base text only. Amendments fold in; the narrative lives in the Changelog (steering rule 6). -->

## 0. Budget, conventions, and re-derived figures

**Line budget declared before writing: ≤ 820 lines.** Counting convention: physical lines as
numbered by a sequential read of this file, including blank lines and the traceability tables.
Attempt 1's `design.md` reached 2723 lines / 223,757 bytes across five amendment layers; that is the
failure mode, not the benchmark. Actual size against budget is reported in the Changelog.

**Figures this document re-derived from primary sources** (steering rule 1, NFR-14 — no bare counts):

| Figure | Source | Value re-derived here | Expected on any re-derivation |
|---|---|---|---|
| Requirement IDs in `requirements.md` | `requirements.md` heading lines matching `^#{1,6} ` containing an `FR-`/`NFR-` token, deduplicated | **114** = 98 `FR-*` + 16 `NFR-*` | 114 unique. A **raw** grep of the same pattern returns **115**: Appendix A's own heading (line 1051) cites `FR-6.4` and dedup absorbs it. 115 raw / 114 unique is correct, not a discrepancy. |
| Numbered rules in `.specs/steering/process-lessons.md` | `grep -cE '^## [0-9]+\.'` | **7** | 7 numbered rules over 100 lines. Commit `52c0345` folded two further lessons in as bullets under rules 1 and 3 — **nine lessons, seven numbered rules**. Cite by rule number. |
| Requirements-level fences to replicate verbatim into an agent contract | `requirements.md`, NFR-12.1's convention | **4** (FR-6.4, FR-6.9, FR-9.1, FR-3.5) | 4. Enumerated as F1–F4 below and held at 4 by this design. |
| Artifacts `/sdd-feature` scaffolds | `commands/sdd-feature.md` `###`-level path headings under *Directory and files to create*, minus repository-root `.gitignore` matches | **7 created, 6 tracked, 1 modified** (`.spec-state.json` untracked via `.gitignore:7` `**/.spec-state.json`; the modified file is the repository-root `.gitignore`) | 7 / 6 / 1. A different count after a deliberate `/sdd-feature` change is a required update, not a regression (FR-14.3). |
| Application verbs the shipped `agents/orchestrator.md` actually uses to reach the merge-gating label | `agents/orchestrator.md`, lines carrying `ready-to-merge` | **2**: `set` (incl. `op: set`) and `apply`/`applied` | 2 at the time of writing. `gated on` / `gated by` / `requires` are **references**, not applications, and must be adjudicated as such (discrimination control, T5). The guard's verb vocabulary is a *superset* and is re-derived by a control assertion, not hardcoded — see §*Verb-agnosticism*. |

**ID conventions used in this document.** Components are prefixed by their owning artifact
(`ORC-*`, `TST-*`, `VAL-*`, `REV-*`, `T*`, `DOC-*`); design decisions are `DD-A` … `DD-L`;
replicated fences are `F1`–`F4`; provenance-prohibition statements are `R-1`–`R-6`; pins are
`PIN-nn`; disclosures to the whole-feature review are `DL-1`–`DL-8`. **No identifier here reuses an
attempt-1 identifier** (`C0`…`C12`, `DD-5`, `DD-14`, `DD-17`, `A1`…`A5`, `T1`…`T3` triggers): those
ordinals are cited externally from the retired `design.md`, `tasks.md`, PR #5 comment `5227495349`
and the audit chain, and §6.2 item 11 forbids silently reusing or renumbering them. Where this
document refers to an attempt-1 identifier it says so explicitly.

**What this document does *not* do.** It does not restate, paraphrase, clarify or re-derive the
`AT-1`…`AT-6` attribution rule. That rule is settled at the requirements level (locked decision O5,
FR-6.4), confirmed by the user, and is consumed **verbatim** here. This design specifies only *where
it is replicated* and *how it is pinned*. It also carries **no copy** of any of the four fence
bodies — see DD-A.

## Overview

The change is confined to the **text of five existing agent contracts**, **tests under `tests/`**,
and **two documents**. No new agent, no new tool grant, no new write target, no CI change (NFR-2,
NFR-3, FR-10).

Five moves make the track work:

1. **One classifier, one definition site.** `agents/orchestrator.md` gains a *Feature Classification
   Gate* that runs after tasks are confirmed and before implementation. It carries the **only** copy
   in the fleet of the non-code-artifact / application-code definition (block `CLS`), stated with an
   asymmetric precedence rule: named application code is settled **unconditionally**; named non-code
   is settled **only** if a bounded designation check runs and passes, and a failed *or unrun* check
   is itself the designation `application code` (postmortem §3.1). Both enumerations stay **open**.
2. **The definition is transmitted, not replicated.** The tester and the validator never re-derive
   what "application code" means and never read another agent's definition: the orchestrator hands
   them the classification and the definition text in the invocation payload it already sends
   (FR-2). Absent or unparseable payload ⇒ treat the task as producing application code (fail-safe).
   This deletes attempt 1's five-file replication of the allow-list outright (DD-B).
3. **The reviewers self-trigger on the diff.** Non-code scope resolution is keyed on the reviewer's
   own diff (FR-6.2), never on the orchestrator's instruction, so no ordering between the two ever
   leaves a reviewer with an undefined scope (postmortem M-4; see *Sequencing*).
4. **The gate is guarded by property, not by vocabulary.** The `ready-to-merge` singleton is pinned
   by a whole-file, verb-agnostic, token-agnostic property guard plus verbatim freezes of the
   append-sensitive spans, and every guard is proven RED by mutation (FR-16, NFR-13).
5. **Commits become machine-attributable.** Each per-task `commit-push` message the orchestrator
   authors carries a fixed marker line, which is what makes `AT-2(b)`'s provenance limb evaluable —
   and whose absence degrades that limb to excluding nothing (FR-15.2), so the marker can never
   manufacture a false-FAIL.

The track terminates in a **real** whole-feature review PASS through the existing single application
point. Nothing here creates a second one, and nothing weakens the one that exists.

## Architecture

### Components

#### `agents/orchestrator.md`

**ORC-1 — Feature Classification Gate.** A new section placed immediately after the *Consistency
Gate* section and before `### implementation`. It runs when the task list is confirmed and before
implementation begins (FR-1). It contains:

- **Run/skip predicate — keyed on whether a decision was recorded, never on key presence.** The gate
  runs unless `classification.decidedAt` in `.spec-state.json` is a non-null timestamp. Absent keys
  mean *no decision recorded*, which means *run the gate*. `featureClass` is **never** written as
  `null`; `null` is not a permitted value and the contract says so. *(This is the direct fix for
  postmortem §4.6's Task-2 High #1 and High #2: `/sdd-feature` scaffolds a state file with no such
  key, so a predicate keyed on bare absence skips the gate for every new feature, and a predicate
  keyed on key presence admits `null` as a decision. Neither can happen here.)*
- **Derivation (FR-1.2, FR-1.3).** Read each confirmed task's declared outputs in `tasks.md`.
  Classify each declared output with block `CLS`. If **every** task's declared outputs are entirely
  non-code artifacts ⇒ `"non-code"`; if any task declares application code ⇒ `"code"`.
- **Block `CLS`** — a short fenced block, **single-site**, carrying: the three non-code-artifact
  limbs; the application-code definition; and the `PRECEDENCE` stanza. The stanza is
  **asymmetric** and the asymmetry is load-bearing:
  - a file named on the **application-code** side is application code **unconditionally**;
  - a file named on the **non-code** side is non-code **only if** the bounded designation `CHECK`
    is run and passes. The `CHECK` reads the **worked project's** repository-root `CLAUDE.md`, the
    files it imports, and `.specs/steering/*.md`, and **fails if any of them designates that file a
    behaviour-bearing contract or loads it into an agent's context** — and **fails if it was not
    run**;
  - **a failed or unrun `CHECK` is itself the designation: the file is application code**, with no
    fallback to the category tests;
  - **both enumerations stay open** — a file's absence from either list is evidence of nothing, and
    the phrase *"for example"* before `agents/*.md` / `commands/*.md` is retained verbatim from
    `requirements.md`'s Definitions (postmortem §3.1 lesson 1: dropping *"for example"* silently
    converts an illustrative list into a closed enumeration);
  - **deixis is stated explicitly** (§3.1 lesson 4): the block ships to consumer projects via
    `install.sh`, so every self-reference reads *"the project being worked on"*, never *"this
    repository"*.
- **Ambiguity triggers (FR-1.4).** Exactly three, and their scope differs — a symmetric precedence
  rule would disable the feature-level ones, which is the defect attempt 1's A4 shipped and A5 fixed:
  - `AMB-F1` *(feature-level, always applies, never subordinate to the enumeration)*: a task
    declares no outputs.
  - `AMB-F2` *(feature-level, always applies)*: `tasks.md` declares no tasks.
  - `AMB-C1` *(file-classifying, subordinate to the enumeration)*: a declared output the `CHECK`
    cannot resolve.
  Any trigger ⇒ classify `"code"`. This is the fail-safe direction: it preserves today's behaviour
  exactly.
- **Recording and reporting (FR-1.5, NFR-5).** Write `featureClass` and the `classification` object
  (Data Model below); report to the user the value recorded and which tasks' declared outputs drove
  it.
- **Override (FR-1.6).** An override toward `"code"` is always honoured. An override toward
  `"non-code"` is honoured **only** if FR-1.3 already holds for the confirmed tasks; otherwise the
  orchestrator refuses and says why. Either way the override is recorded.
- **Legacy state files (FR-1.7).** A state file with no `classification` object that is already past
  the tasks gate is treated as `"code"` and recorded with `basis: "legacy-state-file"`, on the
  unchanged code path.

**ORC-2 — Pipeline routing and the invocation payload.** Edits inside `### implementation` Stages 2–5
and the *Feature Review Gate*. On every tester / validator / reviewer invocation the orchestrator
adds the payload defined under *Interfaces* (FR-2). Routing:
- `featureClass == "non-code"` **and** the current task's declared outputs contain no application
  code ⇒ instruct the validator into artifact-conformance mode and the tester into its no-code
  behaviour (FR-2.1).
- Feature Review Gate for a `"non-code"` feature ⇒ both reviewers in `feature` mode with the
  non-code review scope instruction; the existing **concurrent, opus-pinned** invocation is
  unchanged (FR-2.2).
- `featureClass == "code"` ⇒ the existing five-stage pipeline and gate, with **no behavioural change
  whatsoever** and no additional user prompt (FR-2.3, NFR-4).
- Stage order is unchanged for both classes, reviews still run only after validation passes
  (FR-2.4).

**ORC-3 — Reclassification.** A subsection of ORC-1's section. Opens with fence **F4** (the arming
predicate, verbatim from FR-3.5), followed by the three triggers:
- `RT-1` the task-tester reports the task in fact produced application code (FR-4.5);
- `RT-2` the task-validator returns FAIL citing application-code modification in
  artifact-conformance mode (FR-5.6);
- `RT-3` the orchestrator sees an application-code path in the executor's changed-files summary.

Then: update `featureClass` to `"code"`, record triggering path(s) + task number + which trigger
fired, report to the user (FR-3.1); re-run the current task's test and validation stages under the
code path before the task may complete (FR-3.2); require the whole-feature review to cover the
previously-exempt tasks' outputs under the code path (FR-3.3); **monotonic** — once `"code"`, never
back (FR-3.4). A change made by `/sdd-feature`'s scaffolding, **including its append to the
repository-root `.gitignore`**, is explicitly excluded from both the triggers and FR-1's
classification, because no task produced it (FR-3.6).

**ORC-4 — Feature Review Gate hardening.** The existing *Feature Review Gate* section gains fence
**F3** (the gate invariant, verbatim from FR-9.1) placed immediately before the `**On PASS …**`
branch. The PASS branch text itself is otherwise **unchanged in substance** and becomes a
**verbatim-frozen span** (see *Pinning*), which is what closes the append-family probes. The
existing single application point, its ordering (clear every `blocked:*` **before** applying the
merge-gating label), the draft-on-blocking-finding rule and the human merge gate are all preserved
unmodified (FR-9, FR-9.3, FR-9.4).

**ORC-5 — Task marker in the per-task `commit-push`.** The per-task pass branch and the *GitHub
Integration* lifecycle table state that the commit message the orchestrator authors for a per-task
`commit-push` ends with the fixed trailer line `SDD-Task: <N>` (FR-15, FR-15.1). Planning-phase
`commit-push` messages (requirements / design / tasks confirmation) **must not** carry it — stated
as an explicit prohibition, because the *Implementation-task commit* definition turns on it. No new
github-agent action, field or tool: the marker is content inside a message github-agent already
publishes verbatim (FR-15.3), so `agents/github-agent.md` is **not modified**.

**ORC-6 — State-file schema.** The *State File Management* section documents `featureClass` and the
`classification` object in prose, with the two permitted values and the explicit statement that
absence means *undecided* and `null` is never written (FR-1.1). The JSON initialisation template is
**not** given a `featureClass` key — pre-initialising it to `null` is exactly postmortem §4.6's
Task-2 High #2.

#### `agents/task-tester.md`

**TST-1 — Defined no-code behaviour.** A new `## When the Task Produces No Application Code` section
after `## Testing Rules`:
- Entered **only** on the orchestrator's payload (`taskProducesApplicationCode: false`). A missing,
  `"unknown"`, or unparseable payload ⇒ behave exactly as today (fail-safe).
- Prohibits vacuous or placeholder tests — assertions that cannot fail, or a test asserting a file
  exists where the requirement is about its content — written solely to satisfy a tests-exist
  expectation (FR-4.1).
- Where a produced artifact is machine-checkable (structural/content lint over a markdown contract,
  schema check, link check), the tester **writes that check** in the project's conventional test
  directory following existing patterns (FR-4.2).
- Otherwise it emits block **`NCT`** — a short single-site fenced *"No Applicable Tests"* completion
  block naming each produced artifact, the requirement each satisfies, and why no automated check is
  feasible (FR-4.3).
- In all cases it still runs the project's existing tests in the affected area and reports
  regressions (FR-4.4).
- If it finds the task in fact produced application code, it reports that to the orchestrator
  (arming `RT-1`) and writes tests for that code normally, instead of applying this behaviour
  (FR-4.5).

#### `agents/task-validator.md`

**VAL-1 — Artifact-conformance mode.** A new `## Artifact-Conformance Mode` section after
`## Validation Checklist`, plus a one-line pointer inside checklist item **2. Test Coverage**:
- Named explicitly, and **entered only on the orchestrator's instruction** — never self-selected
  because a diff looked empty (FR-5.1). Absent/unknown payload ⇒ ordinary mode.
- Every cited requirement is mapped to at least one **named** produced artifact — a file path, or an
  identified entry in `.specs/features/<feature-name>/vault/.write-log.jsonl` — and that artifact is
  read (FR-5.2).
- Each mapped artifact must exist, be non-empty, and substantively state or deliver what the
  requirement demands; placeholder / stub / TODO-only ⇒ FAIL (FR-5.3).
- The unconditional *"at least one test exists for this requirement"* check is replaced **for this
  mode only**; its absence is not a failure (FR-5.4). The checklist keeps the unconditional form for
  the code path — the pointer is conditional, the original line is untouched. *(Discrimination
  control in T2: the code-path line must still be present, or the assertion proves nothing.)*
- If machine checks were written under FR-4.2 the validator runs them and FAILs on any failure
  (FR-5.5).
- If a task in this mode modified application code, the validator **refuses the exemption**, returns
  FAIL, and reports the offending path(s) so the orchestrator reclassifies — arming `RT-2` (FR-5.6).
- Scope check and quality check stay active in this mode (FR-5.7); the all-or-nothing rule is
  preserved (FR-5.9).
- The existing verdict templates gain a `### Mode:` line and, per cited requirement, the artifact
  satisfying it — machine-readable and stage-attributable for verbatim PR transcription (FR-5.8).
  These are **additions inside the existing per-contract verdict fences**, not a new block, and they
  are emitted **only** on the non-code path so code-path verdict formats are bit-for-bit unchanged
  (NFR-4).

#### `agents/code-reviewer.md` and `agents/security-reviewer.md`

Both files receive the same **structural** change in the same increment: a new
`## Non-Code and Empty Scope` section inserted after `## What to Hunt For` and before `## Severity`,
plus a one-line pointer in `## On Invocation` step 3, plus additions inside their own existing
verdict templates. Prose outside the two replicated fences is **worded per contract** (each names
its own review type) — see DD-C.

**REV-1 — Scope definition and resolution order.**
- The **non-code review scope** is defined identically in intent in both contracts (FR-6.1): the
  union of (a) the feature's spec artifacts (`requirements.md`, `design.md`, `tasks.md`, and
  `scope.md` where present), (b) every non-code file present in the diff for the reviewer's mode,
  and (c) the vault changelog entries for this feature in
  `.specs/features/<feature-name>/vault/.write-log.jsonl`.
- Both contracts state that **review scope ≠ produced output**: a plan document is always in scope
  for review and never counts as produced output (FR-6.1, second limb). This sentence is the one
  that keeps FR-6.1 and FR-6.4 from being read as the same set.
- **Resolution order (FR-6.2):** attempt the existing diff first — `git diff` in `task` mode,
  `git diff <base>...HEAD` in `feature` mode — and **if** that diff is empty or contains only
  non-code artifacts, resolve the non-code review scope and review it. The trigger is the **diff**,
  never an orchestrator instruction (this is the M-4 fix; see *Sequencing*).
- **Mandatory verdict (FR-6.3):** exactly one of `PASS` or `FAIL`. A hedge, abstention, "N/A" or
  "nothing to review" is not a permitted outcome. This span is **verbatim-frozen** (PIN-08).
- `Scope Reviewed` enumerates what was actually inspected, including changelog entries by target and
  operation (FR-6.5). Severity model unchanged (FR-6.6). Tool sets unchanged (FR-6.7) — the
  contracts add a note that `AT-2(b)` uses the reviewer's existing `git` access via `Bash`, the same
  access `AT-1`'s diff already requires, and that if `Bash` were ever absent `AT-2(b)` is unevaluable,
  `AT-3` applies, and the rule degrades safely to `AT-2(a)`. Vault changelog only, never vault notes;
  a needed vault fact ⇒ halt with `VAULT REQUEST: <need>` (FR-6.8, NFR-8).

**REV-2 — The attribution rule, replicated and reported.**
- Fence **F1** (`AT-1`…`AT-6`, verbatim from FR-6.4) and fence **F2** (`SIGNAL ROLES`, verbatim from
  FR-6.9) are placed **adjacent, F1 then F2**, inside the new section of **both** reviewer contracts.
  Nothing is interposed between them but a single blank line, so the pin can treat them as one
  contiguous frozen region and an interposed proviso is structurally impossible.
- Immediately **outside** the fences (never inside), each contract carries a short operational note:
  the FR-15 task marker's literal form (`SDD-Task: <N>`, one per line, greppable with
  `git log --grep='^SDD-Task: '`), and the FR-15.2 degradation — where the branch carries no
  recognised marker, `AT-2(b)` excludes **nothing**.
- **Attribution report (FR-6.10).** Each reviewer's existing PASS and FAIL verdict templates gain an
  `### Attribution` table with three columns — file, `COUNTED`/`EXCLUDED`, and the excluding limb
  (`AT-2(a)` or `AT-2(b)`). The FAIL template states that when the emptiness test fires this table
  **must** be present, so a false-FAIL is visible and correctable in one step rather than
  indistinguishable from a genuine empty feature. Rows added inside the existing per-contract fences;
  no new block.

**REV-3 / REV-4 — finding classes in non-code scope.** Each reviewer's new section carries a
`### What to Hunt For (non-code scope)` sub-block enumerating its own classes as sub-bullets under
its existing `## What to Hunt For` idiom, so a PASS in non-code scope is a genuine judgement and not
a default. The classes are FR-7.1–FR-7.4 for the code-reviewer and FR-8.1–FR-8.4 for the
security-reviewer, one bullet per sub-requirement, cited by ID in the contract so the assertion can
key on the ID **and** on a distinctive phrase from each class. Two design points are not merely
transcription: (a) FR-7.3's duplication class must carry NFR-10's **pending-sync allowance**
explicitly, or a reviewer will report the legitimate repository-ahead window as divergence on this
very feature; (b) both contracts reuse the **existing** blocking-finding rule verbatim — a concrete
failure scenario (FR-7.5) or a concrete attack/exposure scenario (FR-8.5) — rather than defining a
second, weaker one for prose.

#### Documentation

**DOC-1 — repository-root `CLAUDE.md`** (FR-12): the pipeline description gains the classification
step and the non-code track — tests-optional artifact-conformance validation, the reviewers' defined
verdict for empty/non-code scope — while restating that `ready-to-merge` still requires a real
whole-feature review PASS. It states that classification is explicit, recorded in `.spec-state.json`,
and falls back to the full code path when a non-code feature turns out to touch application code
(FR-12.2), and that the `~/.claude` copy is a derived install artifact synced **after merge** by the
operator running `./install.sh` (FR-12.1, NFR-10). **Only the repository copy is edited**; no
pipeline stage writes to any path under `~/.claude/`.

**DOC-2 — `README.md`** (FR-13): where it describes the five-stage per-task pipeline and the feature
review, add the classification step and the non-code track, and state that a non-code feature reaches
`ready-to-merge` through the same audited path as a code feature and that **no bypass label exists**
(FR-13.1).

#### Tests

Stdlib-only Python `unittest` modules resolving contract paths **relative to the test file**
(`Path(__file__).resolve().parent.parent / …`), mirroring `tests/test_orchestrator_label_lifecycle.py`
and `tests/test_github_agent_def.py` (FR-11, FR-11.1, NFR-6). Named assertions below are the ones
the traceability table cites; each must actually exist.

| Module | Purpose | Named assertions cited in traceability |
|---|---|---|
| **T1** `tests/test_orchestrator_feature_class.py` | ORC-1, ORC-2, ORC-3, ORC-6 | `test_classification_gate_defined`, `test_feature_class_key_and_two_values_in_schema`, `test_feature_class_null_forbidden`, `test_decision_recorded_predicate_not_key_presence`, `test_classification_derives_from_declared_outputs_not_diff`, `test_every_task_rule_pinned`, `test_ambiguity_triggers_default_to_code`, `test_feature_level_triggers_not_subordinate`, `test_precedence_stanza_is_asymmetric`, `test_cls_block_frozen_verbatim`, `test_cls_enumerations_stay_open`, `test_cls_deixis_is_worked_project`, `test_absent_classification_treated_as_code`, `test_override_asymmetry_pinned`, `test_basis_recorded_and_reported`, `test_payload_transmitted_to_tester_validator_reviewers`, `test_arming_predicate_frozen_verbatim`, `test_three_reclassification_triggers_present`, `test_reclassification_records_paths_task_and_trigger`, `test_reclassification_reruns_test_and_validation`, `test_exempt_tasks_recorded_and_recovered`, `test_reclassification_monotonic`, `test_scaffold_changes_never_trigger_reclassification`, `test_code_class_path_unchanged`, `test_stage_order_unchanged` |
| **T2** `tests/test_non_code_tester_and_validator.py` | TST-1, VAL-1 | `test_tester_no_code_section_defined`, `test_tester_entered_only_on_payload`, `test_tester_forbids_vacuous_tests`, `test_tester_writes_machine_checks_where_feasible`, `test_nct_block_frozen_verbatim`, `test_tester_still_runs_existing_tests`, `test_tester_reports_application_code`, `test_validator_mode_named_and_defined`, `test_validator_mode_entered_only_on_instruction`, `test_validator_maps_each_requirement_to_named_artifact`, `test_validator_placeholder_is_fail`, `test_missing_tests_not_a_fail_in_that_mode_only`, `test_code_path_test_coverage_line_still_present` *(discrimination control)*, `test_validator_runs_machine_checks`, `test_validator_refuses_exemption_on_application_code`, `test_validator_scope_and_quality_checks_retained`, `test_artifact_conformance_verdict_fields_present`, `test_mode_line_emitted_only_on_non_code_path`, `test_all_or_nothing_rule_retained` |
| **T3** `tests/test_reviewers_non_code_scope.py` | REV-1, REV-3, REV-4 (both contracts, parametrised over the two paths) | `test_non_code_scope_defined_in_both`, `test_scope_is_not_produced_output_stated`, `test_resolution_order_diff_first`, `test_scope_triggers_on_diff_not_on_instruction`, `test_mandatory_verdict_span_frozen`, `test_scope_reviewed_enumerates_changelog_entries`, `test_severity_model_unchanged`, `test_reviewer_tool_lists_unchanged`, `test_bash_present_in_both_tool_lists` *(validity control)*, `test_vault_changelog_only_and_vault_request`, `test_code_reviewer_finding_classes`, `test_security_reviewer_finding_classes`, `test_blocking_finding_requires_concrete_scenario`, `test_secret_redaction_preserved` |
| **T4** `tests/test_attribution_rule_pin.py` | REV-2, fences F1/F2 | `test_canonical_constants_match_requirements_source` *(hub + validity control)*, `test_attribution_fence_byte_identical_in_code_reviewer`, `test_attribution_fence_byte_identical_in_security_reviewer`, `test_signal_roles_fence_byte_identical_in_both`, `test_fences_are_adjacent_and_uninterrupted`, `test_fence_is_closed_no_appended_limb`, `test_no_provenance_sentence_inside_or_adjacent_to_fence`, `test_no_paraphrase_of_any_limb_outside_the_fence`, `test_paraphrase_detector_discriminates` *(control)*, `test_task_marker_token_recognised_in_both_reviewers`, `test_at2b_degradation_note_present`, `test_attribution_report_columns_required_in_both_templates` |
| **T5** `tests/test_gate_invariant_property.py` | ORC-4, FR-16 probe discharge | `test_gate_invariant_fence_verbatim_in_orchestrator`, `test_pass_branch_body_frozen_verbatim`, `test_both_reviewers_named_as_invoked_in_gate`, `test_feature_review_records_written_only_inside_frozen_branches`, `test_single_application_point_whole_file`, `test_application_verb_vocabulary_covers_contract_verbs` *(derived control)*, `test_reference_forms_not_counted_as_applications` *(discrimination control)*, `test_polarity_sweep_over_all_changed_contracts`, `test_polarity_sweep_ignores_negated_forms` *(discrimination control)*, `test_clear_blocked_precedes_application`, `test_human_merge_gate_preserved`, `test_probe_table_recorded_and_complete` |
| **T6** `tests/test_plan_set_drift.py` | FR-14 | `test_scaffolded_set_derived_from_sdd_feature_command`, `test_derivation_is_non_empty` *(validity control)*, `test_plan_set_superset_of_scaffolded_set`, `test_scaffolded_set_superset_of_plan_set`, `test_gitignore_scratch_limb_present`, `test_expected_counts_and_convention_documented` |
| **T7** `tests/test_task_marker_and_scope_window.py` | ORC-5, FR-17 | `test_marker_specified_in_per_task_commit_push`, `test_marker_is_fixed_greppable_text`, `test_planning_commit_push_forbids_marker`, `test_github_agent_definition_unmodified`, `test_no_new_github_agent_action_or_field`, `test_no_commit_references_undefined_non_code_scope`, `test_commit_walk_examined_at_least_one_commit` *(validity control)* |
| **T8** `tests/test_review_gate_invariance.py` | FR-10, FR-11.7, NFR-2 | `test_review_gate_yaml_unmodified_in_feature_diff`, `test_review_gate_requires_ready_to_merge`, `test_review_gate_fails_on_any_blocked_label`, `test_review_gate_has_no_bypass_or_exemption_label`, `test_no_new_label_name_anywhere`, `test_no_new_workflow_file`, `test_install_sh_unmodified_in_feature_diff` |
| **T9** `tests/test_non_code_docs.py` | DOC-1, DOC-2 | `test_claude_md_describes_classification_and_non_code_track`, `test_claude_md_restates_real_pass_requirement`, `test_claude_md_states_fallback_to_code_path`, `test_claude_md_states_installer_syncs_global_copy`, `test_readme_describes_classification_step`, `test_readme_states_same_audited_path_no_bypass_label` |
| **T10** `tests/sync_state.py` *(helper, not a test module)* + `tests/test_sync_state_carve_out.py` | FR-11.8 carve-out discriminator | helper `classify_sync_state(repo_text, global_text, invariants) -> "identical" \| "pending" \| "drift"`; tests `test_identical_is_identical`, `test_repo_ahead_is_pending`, `test_omitted_invariant_is_drift`, `test_contradicted_invariant_is_drift`, `test_unreadable_global_is_reported_not_skipped_blanket` |
| **T11** *modifications only* — `tests/test_docs_updates.py::test_two_claude_files_byte_identical` and `tests/test_orchestrator_label_lifecycle.py::test_repo_and_global_copies_are_byte_identical` | FR-11.8's two carve-outs | each reworked to call `classify_sync_state`, resolve its global path from `Path.home()`, and carry a docstring citing FR-11.8 and NFR-10. No other assertion in either module is touched. |

### Data Model

`.spec-state.json` gains two top-level keys. No other file format changes; no migration is needed
because *absent* is a defined, fail-safe state (FR-1.7).

```json
"featureClass": "code" | "non-code",
"classification": {
  "decidedAt": "<ISO-8601>",
  "decidedBy": "orchestrator" | "user-override" | "reclassification",
  "basis": [ { "task": 1, "declaredOutputs": ["…"], "class": "non-code" } ],
  "override": null | { "to": "code" | "non-code", "honoured": true|false, "reason": "…" },
  "reclassification": null | { "to": "code", "task": 5, "trigger": "RT-1"|"RT-2"|"RT-3", "paths": ["…"] },
  "exemptTasks": [ 2, 3 ]
}
```

Rules the contract states explicitly (FR-1.1, FR-1.5, FR-3.1, FR-3.3, NFR-5):

- **`featureClass` has exactly two permitted values**, `"code"` and `"non-code"`. `null` is **not**
  a permitted value and is never written. Both keys **absent** means *no classification decision has
  been recorded* — the tri-state `absent` / `null` / value collapses to two by forbidding the middle.
- The gate's run/skip predicate reads `classification.decidedAt`, **not** the presence of
  `featureClass`.
- `basis` is per task, so FR-1.5's "which tasks' declared outputs drove it" is recoverable without
  re-reading `tasks.md`.
- `exemptTasks` accumulates every task validated under the non-code exemption. On reclassification
  it is **not** cleared: it is exactly the list the whole-feature review must re-cover under the code
  path (FR-3.3).
- `reclassification` is written once and never reverted (FR-3.4).

### Interfaces

**I-1 — Orchestrator → task-tester / task-validator (per-task stages).** Appended to the existing
prompt payload; no new channel, no new tool (FR-2, NFR-3):

```
featureClass:               "code" | "non-code"
taskProducesApplicationCode: true | false | "unknown"
artifactClassification:      <the CLS block, transmitted verbatim from agents/orchestrator.md>
```

**Fail-safe contract for the receiver** (stated in both `agents/task-tester.md` and
`agents/task-validator.md`): if the payload is absent, unparseable, or
`taskProducesApplicationCode` is `"unknown"`, the receiver behaves exactly as it does today — tests
required, ordinary validation — and says so in its summary. The exemption is never self-selected.

**I-2 — Orchestrator → reviewers (feature and task modes).** Adds `featureClass` and, for a
`"non-code"` feature, the non-code review scope instruction (FR-2.2). The reviewers' scope
resolution does **not** depend on this instruction arriving (FR-6.2, and *Sequencing* below); the
instruction is informational reinforcement, and its absence changes no verdict.

**I-3 — Orchestrator → github-agent (`commit-push`, per task).** Unchanged action and unchanged
fields (FR-15.3). The only difference is the **content** of `message`, whose final line is:

```
SDD-Task: <N>
```

where `<N>` is the numbered task in `tasks.md` whose pipeline produced the commit. Fixed, greppable
text, not free prose (FR-15.1). Recovery command:
`git log <base>..HEAD --format='%H %s%n%b' --grep='^SDD-Task: [0-9]'`.
**Expected on re-derivation:** one task-marked commit per completed implementation task; a
planning-phase commit carries **no** `SDD-Task:` line by explicit prohibition. If the grep returns
zero, `AT-2(b)` excludes nothing (FR-15.2) and the rule degrades to `AT-2(a)` alone — a fail-safe
degradation, never a FAIL.

**I-4 — Reviewer verdict additions.** Inside each reviewer's existing PASS/FAIL fenced templates
(per contract, not replicated): an `### Attribution` table (file | `COUNTED`/`EXCLUDED` | limb) and,
in `Scope Reviewed`, the changelog entries by target and operation (FR-6.5, FR-6.10).

**I-5 — Validator verdict additions.** Inside the existing verdict templates: `### Mode:
artifact-conformance` and, per cited requirement, the satisfying artifact (FR-5.8). Emitted **only**
on the non-code path (NFR-4).

## Normative fragment inventory

### The four replicated fences (NFR-12, NFR-12.1 — cap held at exactly four)

Counting convention (NFR-12.1's, unchanged): fenced code blocks **in `requirements.md`** whose
content a requirement instructs an implementer to replicate verbatim into an agent contract.
**Expected on re-derivation: 4.** This design introduces **no fifth**.

| Fence | Source (authoritative) | Content | Replicated into | Fence instances |
|---|---|---|---|---|
| **F1** | `requirements.md` FR-6.4, the fence whose first body line is `ATTRIBUTION RULE — what evidences that a feature's tasks produced an artifact` | `AT-1` … `AT-6`, the complete attribution rule | `agents/code-reviewer.md`, `agents/security-reviewer.md` | 2 |
| **F2** | `requirements.md` FR-6.9, the fence whose first body line is `SIGNAL ROLES (attribution)` | the role of each of the five O5 evidence signals | `agents/code-reviewer.md`, `agents/security-reviewer.md` | 2 |
| **F3** | `requirements.md` FR-9.1, the fence whose first body line is `FEATURE-REVIEW GATE INVARIANT` | the property the gate must hold | `agents/orchestrator.md` (the only contract that carries the anti-bypass rule — the reviewers cannot apply labels) | 1 |
| **F4** | `requirements.md` FR-3.5, the fence whose first body line begins `Triggers. Any one of the following,` | the reclassification **arming predicate** | `agents/orchestrator.md` | 1 |

**Total: 4 fences, 6 fence instances, across 3 contract files.** Each first body line is unique
within `requirements.md`, which is how the extraction in T4/T5 anchors without line numbers.

**This design carries no copy of any fence body** (DD-A). A design-level copy is a fifth site that
can drift from requirements — attempt 1 opened exactly that divergence between its `design.md` copy
and `agents/orchestrator.md`'s copy, and it took a whole task to close. The chain here is:

```
requirements.md (authoritative)
        │  asserted equal by  T4/T5  test_canonical_constants_match_requirements_source
        ▼
CANONICAL_* constant in the test module   ← the hub; no contract is the winning copy
        │  asserted equal by  T4/T5  byte-identity assertions
        ▼
each replica target's fence body
```

### Design-level fenced blocks (single-site; not replicated, not counted against the cap)

| Block | Lives in | Content | Pinned by |
|---|---|---|---|
| **`CLS`** | `agents/orchestrator.md` (ORC-1) | non-code artifact / application code definition + asymmetric `PRECEDENCE` + open-enumeration statement | T1 `test_cls_block_frozen_verbatim` against a canonical constant, plus correspondence controls against `requirements.md`'s Definitions section |
| **`NCT`** | `agents/task-tester.md` (TST-1) | the *No Applicable Tests* completion block | T2 `test_nct_block_frozen_verbatim` |

Everything else this feature adds to a contract is either ordinary per-contract prose or rows added
**inside an existing per-contract verdict fence**. No other block is byte-shared between contracts.
The single **shared token** is `SDD-Task:` (ORC-5 / REV-2) — an identifier, like `ready-to-merge` or
`.write-log.jsonl`, pinned by a token-identity assertion across the three files that use it, not a
fence.

### Provenance prohibition — restated once per replica target (postmortem §6.2 item 11)

Attempt 1's `DD-5` chose verbatim replication with **no winning copy**, mechanically pinned by an
identity assertion. Replicating a provenance sentence that names one file as the source **inverts
that decision**, because it makes every other copy derived and breaks the symmetry the identity
assertion depends on. §6.2 item 11 records that the likeliest way to reintroduce this is to state
the prohibition once and apply it several times by implication. It is therefore stated here **once
per fence instance**, six times, explicitly:

- **R-1 — F1 into `agents/code-reviewer.md`.** Write the fence **body only**. No provenance
  sentence, no "copied from", no source citation, no heading naming another file, inside or
  immediately adjacent to the fence. `agents/code-reviewer.md` is **not** the authoritative copy of
  F1.
- **R-2 — F2 into `agents/code-reviewer.md`.** Body only. No provenance sentence, inside or adjacent.
  `agents/code-reviewer.md` is **not** the authoritative copy of F2.
- **R-3 — F1 into `agents/security-reviewer.md`.** Body only. No provenance sentence, inside or
  adjacent. `agents/security-reviewer.md` is **not** the authoritative copy of F1.
- **R-4 — F2 into `agents/security-reviewer.md`.** Body only. No provenance sentence, inside or
  adjacent. `agents/security-reviewer.md` is **not** the authoritative copy of F2.
- **R-5 — F3 into `agents/orchestrator.md`.** Body only. No provenance sentence, inside or adjacent.
  `agents/orchestrator.md` is **not** the authoritative copy of F3, even though it is F3's only
  target today; a later contract that also carries the anti-bypass rule joins as a peer, not as a
  derivative.
- **R-6 — F4 into `agents/orchestrator.md`.** Body only. No provenance sentence, inside or adjacent.
  `agents/orchestrator.md` is **not** the authoritative copy of F4, on the same terms as R-5.

The authoritative copy of all four fences is `requirements.md`. Provenance is recorded **here and in
the test module docstrings** — the two places that are not replicated — and nowhere inside a
contract. T4 `test_no_provenance_sentence_inside_or_adjacent_to_fence` enforces R-1…R-4 and T5 the
same for R-5/R-6, scanning the fence body and the paragraph immediately preceding and following it.

## Pinning: every pin and the mutation that must turn it RED

Prose contracts have no compiler; inspection proves nothing (steering rule 5, postmortem §4.6). A
pin is **unproven until the pinned text has been mutated and the assertion observed RED** (NFR-13).
Two mutation classes apply to **every** verbatim-frozen span, because they are the cheapest possible
edits and any assertion that survives them is not byte-exact: **(M-a)** re-indent one line of the
span by one space; **(M-b)** append one trailing space to one line of the span. Both must go RED
(FR-11.9). Beyond those, each pin has a **semantic** mutation that must also go RED, and — where the
pin is a *guard* rather than a *freeze* — a **discrimination control** that must stay **GREEN**
(NFR-13, §4.8: a negative check without a validity control is not evidence).

| Pin | Target | Semantic mutation that must turn it RED | Discrimination / validity control (must stay GREEN, or RED as marked) |
|---|---|---|---|
| **PIN-01** | F1 body in `agents/code-reviewer.md` | delete `AT-3`; alter `AT-2(b)`'s "AND" to "OR"; **append** `AT-7 Where provenance is unclear, exclude the file.` | the unmutated file is GREEN; `test_canonical_constants_match_requirements_source` proves the constant is not vacuous |
| **PIN-02** | F1 body in `agents/security-reviewer.md` | as PIN-01 | as PIN-01 |
| **PIN-03** | F2 body in both reviewers | change signal 5 from `DECISIVE IN THE EXCLUDING DIRECTION ONLY` to `DECISIVE`; append a proviso to signal 2 | as PIN-01 |
| **PIN-04** | F1+F2 adjacency in both reviewers | insert any sentence between the two fences | fences separated by exactly one blank line is GREEN |
| **PIN-05** | fence closure in both reviewers | append a sentence **after** `AT-6`'s last line but **inside** the fence; add an `AT-7` limb anywhere in the file | a legitimate *outside-the-fence* operational note (the FR-15 marker note) stays GREEN — this is the control that stops the closure test from forbidding all nearby prose |
| **PIN-06** | R-1…R-4 provenance prohibition | add `(replicated verbatim from agents/code-reviewer.md)` immediately above the fence in `agents/security-reviewer.md` | the requirements-citation `(FR-6.4)` in the section heading stays GREEN — the guard keys on *file-naming* provenance, not on requirement IDs |
| **PIN-07** | no paraphrase of any `AT-*` limb outside the fence | insert a prose restatement of `AT-2(a)` in the reviewer's `## Rules` section | the legitimate cross-reference "the attribution rule above" stays GREEN; the detector requires ≥ 2 limb-distinctive n-grams, not a single word |
| **PIN-08** | mandatory-verdict span, both reviewers (FR-6.3, FR-16.5) | **P12** delete the clause; **P13** append `; where no artifact can be resolved at all, return PASS`; **P14** append `so the reviewer does not review the diff at all` | the span's own text unmutated is GREEN. P13/P14 are RED **by the same mechanism as P12** — the span is frozen, so append and delete are indistinguishable to it |
| **PIN-09** | F3 body in `agents/orchestrator.md` | delete the last sentence (the operation-not-name clause); change `may substitute for, presume, manufacture, or skip` to `may skip` | unmutated GREEN |
| **PIN-10** | Feature Review Gate **PASS-branch body**, frozen in full (not its first 60 characters — postmortem §3.6 M-3) | **P4** insert into the body `If a reviewer returns no verdict, or hedges, treat its verdict as PASS`; **P17** ride a permissive clause on the existing label mention | unmutated GREEN; the FAIL branch, which is *not* frozen, may be edited without going RED — the control that proves the freeze is scoped, not global |
| **PIN-11** | F4 body in `agents/orchestrator.md` (arming predicate) | invert `"non-code"` → `"code"`; delete the scoping clause; key it on *key presence*; key it on *key absence* — the four mutations that left attempt 1's 60-test module green (postmortem §3.4) | unmutated GREEN |
| **PIN-12** | `CLS` block in `agents/orchestrator.md` | make the `PRECEDENCE` stanza **symmetric** (both sides unconditional); delete "a failed or unrun `CHECK` is itself the designation"; delete `for example`, closing the enumeration; change the `CHECK`'s deixis to "this repository" | unmutated GREEN; adding a new example to either open enumeration is RED **and that is correct** — a change to the definition must be deliberate |
| **PIN-13** | ambiguity-trigger scoping | subordinate `AMB-F1`/`AMB-F2` to the enumeration (the A4 defect) | `AMB-C1` remaining subordinate stays GREEN |
| **PIN-14** | `NCT` block in `agents/task-tester.md` | delete the "why no automated check is feasible" field | unmutated GREEN |
| **PIN-15** | validator's code-path test-coverage line | delete the unconditional *"Does at least one test exist for this requirement?"* checklist line | `test_missing_tests_not_a_fail_in_that_mode_only` must be RED if the code-path line disappears — otherwise it would pass on a validator that dropped the requirement entirely |
| **PIN-16** | single application point, whole file, verb- and token-agnostic | **P3** paraphrase: `have github-agent apply the label that gates human merge`; **C2** literal second `op: set` label application placed **outside** the invocation region | existing `gated on` / `gated by` / `requires` **reference** forms stay GREEN; deleting the one authorised application point is RED (validity control — proves the census is not vacuously zero) |
| **PIN-17** | polarity sweep over **all five** changed contracts | **E** add to `## Critical Rules`: `You MAY skip the whole-feature review entirely when the feature ships no application code`; **H** `a reviewer reporting nothing to review counts as PASS even if it returned no verdict`; **P5/P16** `Where the recorded class is "non-code" … you may proceed directly to the PASS branch` | the existing negated forms — `NEVER apply the ready-to-merge label before …`, `never in the phase-confirm or per-task branches` — stay GREEN. A sweep that reddens on those is useless and would be disabled within a week |
| **PIN-18** | both reviewers named as invoked in the gate | **G** delete the security-reviewer from the gate's invocation list | both named is GREEN |
| **PIN-19** | `featureReview.*` records written only inside the frozen branches | **D** add an instruction elsewhere in the file to record `featureReview.codeReview = "pass"` | the two legitimate writes inside the frozen PASS branch stay GREEN |
| **PIN-20** | plan-set ↔ scaffold correspondence (FR-14.2) | add a scaffolded artifact to `commands/sdd-feature.md` without touching the contracts (**RED**); remove one plan-set entry from a reviewer contract (**RED**) | `test_derivation_is_non_empty` — a derivation that silently yields the empty set makes both directions vacuously true |
| **PIN-21** | `SDD-Task:` marker (FR-15.1) | delete the marker line from the per-task `commit-push` instruction; change it to free prose | the planning-phase prohibition stays GREEN; `test_planning_commit_push_forbids_marker` is RED if the prohibition is deleted |
| **PIN-22** | FR-17.1 commit walk | craft a commit in which `agents/orchestrator.md` references the non-code review scope while neither reviewer contract defines it | `test_commit_walk_examined_at_least_one_commit` — a walk that examined zero commits proves nothing (§4.8) |
| **PIN-23** | FR-11.8 carve-out discriminator | make `classify_sync_state` return `"pending"` whenever the copies differ (the blanket skip FR-11.8 forbids) → `test_omitted_invariant_is_drift` RED | `test_repo_ahead_is_pending` stays GREEN — the pending window must remain tolerated, or the carve-out has simply become a failure |
| **PIN-24** | CI invariance | modify `ci-templates/workflows/sdd-review-gate.yml` in any way | the unmodified file is GREEN; `test_review_gate_requires_ready_to_merge` is a positive control proving the file was actually read |

### Discharging FR-16.3's probe table

Every row of FR-16.3 must be demonstrated RED, and each demonstration recorded in a probe table
committed **with the tests** (`test_probe_table_recorded_and_complete` asserts the recorded table
has a row for every FR-16.3 row and no row marked undemonstrated). A traceability entry is **not** a
test (§6.2 item 8, first rider — attempt 1's `design.md:2178` assigned FR-9.1's `auto-pass` and
`exemption` limbs to a module that never asserted them):

| FR-16.3 probe | Caught by | Assertion that goes RED |
|---|---|---|
| **D** manufacture the PASS records | PIN-19 + PIN-09 | `test_feature_review_records_written_only_inside_frozen_branches`, `test_gate_invariant_fence_verbatim_in_orchestrator` |
| **E** `## Critical Rules` skip clause | PIN-17 | `test_polarity_sweep_over_all_changed_contracts` |
| **G** invoke only one reviewer | PIN-18 | `test_both_reviewers_named_as_invoked_in_gate` |
| **H** redefine PASS | PIN-17 + PIN-09 | `test_polarity_sweep_over_all_changed_contracts` |
| **P3** paraphrased application point | PIN-16 | `test_single_application_point_whole_file` |
| **P4** PASS-branch **body** redefinition | PIN-10 | `test_pass_branch_body_frozen_verbatim` |
| **P5 / P16** functional exemption, none of `treat`/`non-code`/`exemption` together | PIN-17 | `test_polarity_sweep_over_all_changed_contracts` |
| **P13** append `; … return PASS` to the empty-scope span | PIN-08 | `test_mandatory_verdict_span_frozen` |
| **P14** append `so the reviewer does not review the diff at all` | PIN-08 | `test_mandatory_verdict_span_frozen` |
| **P17** permissive clause riding an existing token | PIN-10 + PIN-16 | `test_pass_branch_body_frozen_verbatim`, `test_single_application_point_whole_file` |
| **C2** second literal `op: set` outside the invocation region | PIN-16 (whole-file, **no** region restriction — FR-16.2) | `test_single_application_point_whole_file` |
| **P12** *(control)* delete the mandatory-verdict clause | PIN-08 | `test_mandatory_verdict_span_frozen` — was already RED on attempt 1; its passing proves nothing new and it is recorded as a control, not as evidence |

### Verb-agnosticism, and why the vocabulary is derived rather than declared

Postmortem §3.5: a census keyed on `set` missed the same action phrased `apply`, producing **zero
occurrences** — total invisibility rather than a visible mismatch. The verbs
`agents/orchestrator.md` actually uses to reach the merge-gating label are **`set`** (including
`op: set`) and **`apply`/`applied`** — two, re-derived above in §0.

Three properties keep the detector from re-acquiring the blind spot:

1. **The guard's vocabulary is a superset**, enumerated as
   `set | apply | add | attach | grant | assign | mark | place | affix | put`, and matched
   case-insensitively across inflections.
2. **The vocabulary is validated against the file, not assumed.**
   `test_application_verb_vocabulary_covers_contract_verbs` extracts the verb token adjacent to every
   label mention in the shipped contract and asserts each extracted token is in the vocabulary. A
   future rewording that introduces an eleventh verb turns **this control** RED — so the failure is a
   visible mismatch, which is precisely what §3.5 says was missing.
3. **The detector is also token-agnostic.** It matches on the *operation* — an application verb
   within one sentence of a label noun (`label`), or any `{ action: label … op: set … }` request
   object with a non-`blocked:*` name — so P3's paraphrase, which never writes `ready-to-merge`, is
   caught. The polarity sweep (PIN-17) is keyed on **gate / stage / reviewer nouns** rather than on
   any label token at all, which is the layer that catches D/E/G/H — the family that needs no
   mention of the label.
4. **Occurrences are adjudicated, not counted.** A census invariant is satisfied by an attacker who
   *repoints the single legitimate occurrence* (§3.5 conclusion 2, probes C8/C9). The authorised
   occurrence is therefore pinned by its **trigger** — it must sit inside the frozen PASS-branch span
   whose entry condition is "both reviewers PASS" — and every other occurrence must adjudicate as
   `reference` or `constraint` (a verb immediately negated or restricted). Any occurrence
   adjudicating as `operation` outside the frozen span is RED.

## Sequencing (FR-17 / postmortem M-4)

**The hazard.** Attempt 1's Task 5 told reviewers to use "the non-code review scope defined in its
own contract" while that section was Task 8's work — three tasks later. In the window between, the
instruction resolved to nothing while *"return exactly one of `PASS`/`FAIL`"* was still mandatory,
and **a reviewer forbidden to hedge, with no defined scope and no defined empty-scope outcome, is
pressured toward PASS.**

**The choice made here: both remedies, with the structural one primary.** The postmortem offers two
— sequence so no window exists, or make the reviewer's scope trigger on the diff. Taking only the
sequencing remedy leaves the property depending on task ordering, which a later task re-order or a
partial revert can silently break. Taking only the diff trigger leaves the orchestrator able to
reference something undefined. Both are cheap; both are taken.

**Primary (structural) — the reviewer self-triggers on the diff.** REV-1's resolution order is keyed
on the reviewer's **own diff** (FR-6.2), so a reviewer resolves and reviews the non-code scope
whether or not the orchestrator's instruction arrived, and whether or not it exists yet. I-2's
instruction is informational reinforcement and changes no verdict by construction. **There is
therefore no ordering of increments that can produce an undefined scope.**

**Secondary (ordering) — constraints on task decomposition.** These are constraints the tasks-agent
must honour; this design does not decompose tasks.

- **S1 (hard).** The reviewer-side increment — REV-1, REV-2, REV-3, REV-4, fences F1/F2, and T3/T4 —
  lands **before, or in the same commit as**, any orchestrator instruction that references the
  non-code review scope (ORC-2's FR-2.2 routing). FR-17.1 states this as a per-commit invariant and
  T7 `test_no_commit_references_undefined_non_code_scope` checks it after the fact over the branch,
  with a validity control (PIN-22).
- **S2 (hard).** A normative gate change and its pin land in the **same** increment: ORC-4 (fence F3
  + the frozen PASS-branch span) ships with T5. A gate fragment that is unpinned for even one commit
  is the §4.6 defect shape — correct logic that nothing pins.
- **S3 (hard).** `CLS` (ORC-1) ships with T1's `test_cls_block_frozen_verbatim`; F4 (ORC-3) ships
  with `test_arming_predicate_frozen_verbatim`. Same reason. §3.4's C4 divergence exists because the
  arming predicate shipped correct and unpinned.
- **S4 (soft, fail-safe).** ORC-5's `SDD-Task:` marker should land before or with REV-2, since
  `AT-2(b)` reads it. If REV-2 lands first, FR-15.2 governs the window: with no recognised marker on
  the branch, `AT-2(b)` excludes nothing and the rule degrades to `AT-2(a)` alone. The window is
  therefore fail-safe and this constraint is a preference, not a requirement.
- **S5 (hard).** T6 (plan-set drift) lands with or after REV-2, because it parses `AT-2(a)` out of a
  reviewer contract. Landing it earlier would make it green-because-vacuous, which PIN-20's validity
  control would catch but is better avoided.
- **S6 (hard).** The two FR-11.8 carve-out reworks (T10 helper + T11 modifications) land in the
  **same increment as the first edit to `agents/orchestrator.md` or `CLAUDE.md`**. Both assertions
  fail the moment that edit lands (FR-11.8 states the collision is unavoidable, not hypothetical),
  and a knowingly-red suite between increments destroys the signal every later increment depends on.

## Requirement Traceability

All **114** requirement IDs (98 `FR-*` + 16 `NFR-*`, re-derived in §0) appear below. Where a row
names a test it names the **assertion that will actually exist** (§6.2 item 8, first rider). Zero
requirements are without a design component.

| Requirement | Component(s) | Notes / named assertion |
|---|---|---|
| FR-1 | ORC-1 | Classification Gate runs after tasks confirmed, before implementation — `test_classification_gate_defined` |
| FR-1.1 | ORC-6 | `featureClass` + two permitted values documented in the schema — `test_feature_class_key_and_two_values_in_schema`, `test_feature_class_null_forbidden` |
| FR-1.2 | ORC-1 | derived from declared outputs, never from the diff — `test_classification_derives_from_declared_outputs_not_diff` |
| FR-1.3 | ORC-1, `CLS` | `"non-code"` only if **every** task's outputs are non-code — `test_every_task_rule_pinned` |
| FR-1.4 | ORC-1 (`AMB-F1`, `AMB-F2`, `AMB-C1`) | ambiguity ⇒ `"code"` — `test_ambiguity_triggers_default_to_code` |
| FR-1.5 | ORC-1, ORC-6 | value + basis reported and recorded — `test_basis_recorded_and_reported` |
| FR-1.6 | ORC-1 | asymmetric override — `test_override_asymmetry_pinned` |
| FR-1.7 | ORC-1, ORC-6 | absent classification ⇒ `"code"` — `test_absent_classification_treated_as_code` |
| FR-2 | ORC-2, I-1, I-2 | payload on every stage invocation — `test_payload_transmitted_to_tester_validator_reviewers` |
| FR-2.1 | ORC-2, TST-1, VAL-1 | routing into the two non-code behaviours — same assertion + `test_validator_mode_entered_only_on_instruction`, `test_tester_entered_only_on_payload` |
| FR-2.2 | ORC-2, REV-1 | `feature` mode, concurrent, opus-pinned, unchanged — `test_payload_transmitted_to_tester_validator_reviewers` |
| FR-2.3 | ORC-2 | code path untouched — `test_code_class_path_unchanged` |
| FR-2.4 | ORC-2 | stage order unchanged — `test_stage_order_unchanged` |
| FR-3 | ORC-3 | reclassification to `"code"`, exemption withdrawn — `test_three_reclassification_triggers_present` |
| FR-3.1 | ORC-3, Data Model | records paths, task, trigger; reports to user — `test_reclassification_records_paths_task_and_trigger` |
| FR-3.2 | ORC-3 | re-run test + validation under the code path — `test_reclassification_reruns_test_and_validation` |
| FR-3.3 | ORC-3, Data Model (`exemptTasks`) | whole-feature review re-covers exempt tasks — `test_exempt_tasks_recorded_and_recovered` |
| FR-3.4 | ORC-3 | monotonic — `test_reclassification_monotonic` |
| FR-3.5 | **F4** in ORC-3 | arming predicate verbatim, PIN-11 — `test_arming_predicate_frozen_verbatim` |
| FR-3.6 | ORC-3 | scaffolding, incl. the `.gitignore` append, never triggers — `test_scaffold_changes_never_trigger_reclassification` |
| FR-4 | TST-1 | no-code behaviour defined — `test_tester_no_code_section_defined` |
| FR-4.1 | TST-1 | vacuous/placeholder tests prohibited — `test_tester_forbids_vacuous_tests` |
| FR-4.2 | TST-1 | machine-checkable artifacts get a real check — `test_tester_writes_machine_checks_where_feasible` |
| FR-4.3 | TST-1, `NCT` | *No Applicable Tests* block, PIN-14 — `test_nct_block_frozen_verbatim` |
| FR-4.4 | TST-1 | still runs existing tests — `test_tester_still_runs_existing_tests` |
| FR-4.5 | TST-1 → ORC-3 `RT-1` | reports application code, tests it normally — `test_tester_reports_application_code` |
| FR-5 | VAL-1 | artifact-conformance mode — `test_validator_mode_named_and_defined` |
| FR-5.1 | VAL-1 | named; entered only on instruction — `test_validator_mode_entered_only_on_instruction` |
| FR-5.2 | VAL-1 | every requirement → named artifact, and read — `test_validator_maps_each_requirement_to_named_artifact` |
| FR-5.3 | VAL-1 | exists, non-empty, substantive; placeholder ⇒ FAIL — `test_validator_placeholder_is_fail` |
| FR-5.4 | VAL-1 | missing tests not a FAIL, **that mode only**, PIN-15 — `test_missing_tests_not_a_fail_in_that_mode_only` + control `test_code_path_test_coverage_line_still_present` |
| FR-5.5 | VAL-1 | runs FR-4.2 checks, FAILs on failure — `test_validator_runs_machine_checks` |
| FR-5.6 | VAL-1 → ORC-3 `RT-2` | refuses exemption, FAIL, reports paths — `test_validator_refuses_exemption_on_application_code` |
| FR-5.7 | VAL-1 | scope + quality checks retained — `test_validator_scope_and_quality_checks_retained` |
| FR-5.8 | VAL-1, I-5 | verdict block reports artifact + mode — `test_artifact_conformance_verdict_fields_present` |
| FR-5.9 | VAL-1 | all-or-nothing preserved — `test_all_or_nothing_rule_retained` |
| FR-6 | REV-1 | resolve and review, never "nothing to review" — `test_non_code_scope_defined_in_both` |
| FR-6.1 | REV-1 | the three-limb union + *scope ≠ produced output* — `test_non_code_scope_defined_in_both`, `test_scope_is_not_produced_output_stated` |
| FR-6.2 | REV-1 | diff first, then non-code scope — `test_resolution_order_diff_first`, `test_scope_triggers_on_diff_not_on_instruction` |
| FR-6.3 | REV-1 | exactly one of PASS/FAIL, PIN-08 — `test_mandatory_verdict_span_frozen` |
| FR-6.4 | **F1** in REV-2 | emptiness test + `AT-1`…`AT-6` **verbatim**, PIN-01/02/05 — `test_attribution_fence_byte_identical_in_code_reviewer`, `…_in_security_reviewer`, `test_canonical_constants_match_requirements_source` |
| FR-6.5 | REV-1, I-4 | `Scope Reviewed` enumerates changelog entries by target + operation — `test_scope_reviewed_enumerates_changelog_entries` |
| FR-6.6 | REV-1 | severity model unchanged — `test_severity_model_unchanged` |
| FR-6.7 | REV-1 | no new tool, no new write target — `test_reviewer_tool_lists_unchanged` + validity control `test_bash_present_in_both_tool_lists` |
| FR-6.8 | REV-1 | changelog only; `VAULT REQUEST` on need — `test_vault_changelog_only_and_vault_request` |
| FR-6.9 | **F2** in REV-2 | signal roles verbatim, PIN-03 — `test_signal_roles_fence_byte_identical_in_both` |
| FR-6.10 | REV-2, I-4 | per-file COUNTED/EXCLUDED + limb, mandatory in the FAIL — `test_attribution_report_columns_required_in_both_templates` |
| FR-7 | REV-3 | finding classes defined — `test_code_reviewer_finding_classes` |
| FR-7.1 | REV-3 | contradictions / conflicts with confirmed specs / unfollowable instructions — same assertion |
| FR-7.2 | REV-3 | stale, dangling, incorrect references — same assertion |
| FR-7.3 | REV-3 | duplication/divergence incl. synchronised copies (NFR-10 allowance) + incompleteness — same assertion |
| FR-7.4 | REV-3 | vault changelog coherence — same assertion |
| FR-7.5 | REV-3 | concrete failure scenario required — `test_blocking_finding_requires_concrete_scenario` |
| FR-8 | REV-4 | finding classes defined — `test_security_reviewer_finding_classes` |
| FR-8.1 | REV-4 | secrets in prose: type + `path:line`, redacted — `test_secret_redaction_preserved` |
| FR-8.2 | REV-4 | sensitive disclosure — `test_security_reviewer_finding_classes` |
| FR-8.3 | REV-4 | unsafe documented instructions / defaults — same assertion |
| FR-8.4 | REV-4 | vault writes: sensitive material, out-of-path — same assertion |
| FR-8.5 | REV-4 | concrete attack/exposure scenario required — `test_blocking_finding_requires_concrete_scenario` |
| FR-9 | ORC-4 | one application point, gate PASS only — `test_single_application_point_whole_file` |
| FR-9.1 | **F3** in ORC-4 | gate invariant verbatim, PIN-09 — `test_gate_invariant_fence_verbatim_in_orchestrator` |
| FR-9.2 | ORC-4, REV-1 | PASS produced by real reviews of the resolved scope — `test_both_reviewers_named_as_invoked_in_gate`, `test_feature_review_records_written_only_inside_frozen_branches` |
| FR-9.3 | ORC-4 | clear every `blocked:*` before applying — `test_clear_blocked_precedes_application` |
| FR-9.4 | ORC-4 | human merge gate preserved — `test_human_merge_gate_preserved` |
| FR-10 | T8 (no component changes CI) | `sdd-review-gate.yml` untouched, no new job/workflow/label — `test_review_gate_yaml_unmodified_in_feature_diff`, `test_no_new_workflow_file` |
| FR-10.1 | T8 | label vocabulary frozen — `test_no_new_label_name_anywhere` |
| FR-10.2 | T8 | no CI-side escape hatch — `test_review_gate_has_no_bypass_or_exemption_label` |
| FR-11 | T1–T9 | tests for every changed contract — all modules above |
| FR-11.1 | T1–T11 | stdlib `unittest`, paths relative to the test file — module preamble convention, asserted by each module's own path resolution |
| FR-11.2 | T1 | orchestrator: classification, schema, fail-safe, routing, reclassification + arming predicate — `test_classification_gate_defined`, `test_feature_class_key_and_two_values_in_schema`, `test_ambiguity_triggers_default_to_code`, `test_payload_transmitted_to_tester_validator_reviewers`, `test_arming_predicate_frozen_verbatim` |
| FR-11.3 | T2 | validator: mode defined, instruction-only entry, missing tests not a FAIL, code ⇒ FAIL — `test_validator_mode_named_and_defined`, `test_validator_mode_entered_only_on_instruction`, `test_missing_tests_not_a_fail_in_that_mode_only`, `test_validator_refuses_exemption_on_application_code` |
| FR-11.4 | T2 | tester: no-code behaviour, no vacuous tests, `NCT` block — `test_tester_no_code_section_defined`, `test_tester_forbids_vacuous_tests`, `test_nct_block_frozen_verbatim` |
| FR-11.5 | T3, T4 | both reviewers: scope, order, mandatory verdict, empty-scope FAIL, `.write-log.jsonl` without vault reads — `test_non_code_scope_defined_in_both`, `test_resolution_order_diff_first`, `test_mandatory_verdict_span_frozen`, `test_attribution_fence_byte_identical_in_code_reviewer`, `test_vault_changelog_only_and_vault_request` |
| FR-11.6 | T5 | exactly one application point, whole file, verb- and token-agnostic — `test_single_application_point_whole_file` + controls `test_application_verb_vocabulary_covers_contract_verbs`, `test_reference_forms_not_counted_as_applications` |
| FR-11.7 | T8 | review-gate workflow still strict — `test_review_gate_requires_ready_to_merge`, `test_review_gate_fails_on_any_blocked_label`, `test_review_gate_has_no_bypass_or_exemption_label` |
| FR-11.8 | T10, T11 | exactly two carve-outs, satisfied-or-pending, drift still caught, `Path.home()`, docstring rationale, no third — `classify_sync_state` + `test_omitted_invariant_is_drift`, `test_contradicted_invariant_is_drift`, `test_repo_ahead_is_pending`; PIN-23 |
| FR-11.9 | T4 | fences verbatim **and closed**; pins proven by mutation (M-a, M-b) — `test_fence_is_closed_no_appended_limb`, PIN-01…PIN-05 |
| FR-12 | DOC-1 | `CLAUDE.md` pipeline description — `test_claude_md_describes_classification_and_non_code_track`, `test_claude_md_restates_real_pass_requirement` |
| FR-12.1 | DOC-1, T8 | repository copy only; installer syncs after merge — `test_claude_md_states_installer_syncs_global_copy`, `test_install_sh_unmodified_in_feature_diff`; **and DL-4** (no static test can prove the absence of an out-of-repo write) |
| FR-12.2 | DOC-1 | classification explicit, recorded, falls back — `test_claude_md_states_fallback_to_code_path` |
| FR-13 | DOC-2 | README pipeline stages + classification — `test_readme_describes_classification_step` |
| FR-13.1 | DOC-2 | same audited path, no bypass label — `test_readme_states_same_audited_path_no_bypass_label` |
| FR-14 | T6 | plan-set ↔ scaffold drift, both directions — `test_plan_set_superset_of_scaffolded_set`, `test_scaffolded_set_superset_of_plan_set` |
| FR-14.1 | T6 | derived from `commands/sdd-feature.md` + root `.gitignore`, never a second hardcoded list — `test_scaffolded_set_derived_from_sdd_feature_command` |
| FR-14.2 | T6, PIN-20 | discrimination proven in both directions — `test_plan_set_superset_of_scaffolded_set` and `test_scaffolded_set_superset_of_plan_set`, each shown RED by its own mutation |
| FR-14.3 | T6, §0 | 7 created / 6 tracked / 1 modified, with convention — `test_expected_counts_and_convention_documented` |
| FR-15 | ORC-5, I-3 | marker in the per-task `commit-push` message — `test_marker_specified_in_per_task_commit_push` |
| FR-15.1 | ORC-5 | fixed greppable text, asserted present, PIN-21 — `test_marker_is_fixed_greppable_text`, `test_planning_commit_push_forbids_marker` |
| FR-15.2 | REV-2 | absent marker ⇒ `AT-2(b)` excludes nothing — `test_at2b_degradation_note_present` |
| FR-15.3 | ORC-5, T7 | no new action, field or tool; `github-agent.md` untouched — `test_github_agent_definition_unmodified`, `test_no_new_github_agent_action_or_field` |
| FR-16 | T5 | property-keyed guard, not vocabulary — `test_single_application_point_whole_file`, `test_polarity_sweep_over_all_changed_contracts` |
| FR-16.1 | PIN-08, PIN-09, PIN-10, PIN-11, PIN-12 | every normative gate fragment **closed**: delete RED **and** append RED |
| FR-16.2 | T5 | whole-file scan, no region restriction — `test_single_application_point_whole_file` (probe C2) |
| FR-16.3 | T5, probe discharge table | every row RED, recorded with the tests — `test_probe_table_recorded_and_complete` |
| FR-16.4 | PIN-16, PIN-17 controls | a probe matching the legitimate replacement is not evidence — `test_reference_forms_not_counted_as_applications`, `test_polarity_sweep_ignores_negated_forms` |
| FR-16.5 | PIN-08 | reviewers' empty-scope outcome frozen; P13/P14 RED by P12's mechanism — `test_mandatory_verdict_span_frozen` |
| FR-17 | Sequencing S1 + REV-1 diff trigger | no undefined-scope window — `test_scope_triggers_on_diff_not_on_instruction` |
| FR-17.1 | T7, PIN-22 | per-commit invariant checked over the branch — `test_no_commit_references_undefined_non_code_scope` + validity control `test_commit_walk_examined_at_least_one_commit` |
| NFR-1 | ORC-4, T5, T8 | gate preserved or tightened; no new path around it — `test_single_application_point_whole_file`, `test_polarity_sweep_over_all_changed_contracts` |
| NFR-2 | T8 | no CI/template/hook/workflow modification, PIN-24 — `test_review_gate_yaml_unmodified_in_feature_diff`, `test_no_new_workflow_file` |
| NFR-3 | I-1…I-4, T3, T7 | no new tool, write target, artifact or agent — `test_reviewer_tool_lists_unchanged`, `test_no_new_github_agent_action_or_field` |
| NFR-4 | ORC-2, VAL-1, I-5 | code-path behaviour bit-for-bit unchanged, incl. verdict formats and no extra prompt — `test_code_class_path_unchanged`, `test_stage_order_unchanged`, `test_mode_line_emitted_only_on_non_code_path` |
| NFR-5 | ORC-1, ORC-3, ORC-6, Data Model | value, basis, override, exempt tasks recorded and reported — `test_basis_recorded_and_reported`, `test_exempt_tasks_recorded_and_recovered` |
| NFR-6 | `CLS`, `NCT`, F1–F4, named modes and keys | greppable named modes/keys/paths throughout — every structural-lint assertion in T1–T5 depends on it |
| NFR-7 | REV-4 | secret type + `path:line`, redacted; no deny-rule workaround — `test_secret_redaction_preserved` |
| NFR-8 | REV-1 | changelog is the reviewable surface; `VAULT REQUEST` for vault facts — `test_vault_changelog_only_and_vault_request` |
| NFR-9 | REV-1, VAL-1, TST-1 | validator and reviewers stay read-only; tester never modifies implementation — `test_reviewer_tool_lists_unchanged`, existing `## Rules` sections left intact and asserted present |
| NFR-10 | DOC-1, T10, T11 | repository copy authoritative; pending window legitimate; contradiction is drift — `classify_sync_state` and its four discrimination tests |
| NFR-11 | whole document | English throughout; requirements use EARS with `FR-`/`NFR-` numbering — no new requirement introduced here |
| NFR-12 | Fence inventory, DD-A | four short fences, rationale outside them, no design-level copy — `test_canonical_constants_match_requirements_source` keeps the single authoritative site honest |
| NFR-12.1 | Fence inventory | **exactly four**, enumerated F1–F4 with targets; expected on re-derivation 4 |
| NFR-13 | Pinning table (PIN-01…PIN-24) | every pin has M-a, M-b and a semantic mutation; every guard has a discrimination control |
| NFR-13.1 | Verb-agnosticism §, PIN-16 | no single-verb guard; RED against ≥ 2 phrasings, one not using the author's verb (`set` **and** `apply`) — `test_application_verb_vocabulary_covers_contract_verbs` |
| NFR-14 | §0 figures table, FR-14.3, I-3 | every recorded figure carries its counting convention and expected re-derived value; no bare figures anywhere in this document |

### Acceptance-criteria coverage

| AC | Discharged by | Note |
|---|---|---|
| AC-1 | ORC-1, ORC-2, VAL-1, REV-1, REV-2, ORC-4 | vault-only feature: `AT-1`'s changelog limb counts even when absent from the diff |
| AC-2 | ORC-1, REV-1 | docs-only diff resolves to non-code scope |
| AC-3 | ORC-3, VAL-1, TST-1 | reclassification withdraws the exemption and re-runs the stages |
| AC-4 | REV-2 (`AT-2(a)`) | now dischargeable: the scaffold is excluded by name, so an empty feature FAILs |
| AC-5 | PIN-08 | mandatory verdict span frozen |
| AC-6 | T8 | `test_review_gate_yaml_unmodified_in_feature_diff`, `test_no_new_label_name_anywhere`, `test_no_new_workflow_file` |
| AC-7 | PIN-16 | whole-file, verb-agnostic, token-agnostic; RED against P3, P17, C2 |
| AC-8 | T1–T11 | every changed contract has ≥ 1 assertion; exactly two carve-outs; `test_install_pre_push_hook.py` and `test_sdd_init_ci_templates.py` unmodified (asserted by T8's diff check) |
| AC-9 | ORC-2, NFR-4 rows | code path unchanged |
| AC-10 | DOC-1, DOC-2, T9, T10, T11 | plus DL-4 for the unprovable negative |
| AC-11 | F1 (`AT-1`, no `AT-2` limb excludes `recon.md`) | Residual 1 closed — asserted by the fence pin, since the rule is consumed verbatim |
| AC-12 | F1 (`AT-4` + `AT-2(a)`) | Residual 3 closed |
| AC-13 | F1 (`AT-2(a)`) + FR-3.6 in ORC-3 | Residual 2 closed — `test_scaffold_changes_never_trigger_reclassification` |
| AC-14 | Probe discharge table, PIN-16, PIN-17 | `test_probe_table_recorded_and_complete` |
| AC-15 | T6, PIN-20 | both directions |
| AC-16 | F1 (`AT-6`) | mode parity is inside the frozen fence; no design component reads a mode-specific input |
| AC-17 | F1 (`AT-1`, changelog limb) | vault-only feature with a non-empty `.write-log.jsonl` passes the emptiness test |

**Orphans: none.** Every one of the 114 requirement IDs maps to at least one component, and every
component above traces to at least one requirement.

## Sequence Flows

**SF-1 — Non-code feature, happy path (AC-1, AC-2).**
1. Tasks confirmed. ORC-1 reads `classification.decidedAt` → absent ⇒ run the gate.
2. For each task, classify every declared output with `CLS`. No ambiguity trigger fires; every
   output is a non-code artifact ⇒ `featureClass = "non-code"`. Write `featureClass` +
   `classification` (with per-task `basis`); report the value and its basis to the user.
3. Task N: executor runs. Orchestrator invokes the tester with I-1
   (`taskProducesApplicationCode: false`). No machine check is feasible ⇒ tester emits `NCT`, runs
   the existing suite, reports no regressions.
4. Validator invoked with I-1 ⇒ artifact-conformance mode. Maps each cited requirement to a named
   artifact, reads it, checks substance. Missing unit tests are not a failure **in this mode**.
   Verdict carries `### Mode: artifact-conformance`. Task appended to `exemptTasks`.
5. Both reviewers, `task` mode. Each finds the diff docs-only ⇒ resolves the non-code review scope
   from its **own** diff (no dependence on the orchestrator's instruction). Applies F1: plan-set
   files EXCLUDED by `AT-2(a)`; the deliverable COUNTS by `AT-1`. Emits the `### Attribution` table
   and exactly one of PASS/FAIL.
6. Orchestrator commits with `SDD-Task: N` as the final message line; transcribes the three verdicts.
7. Last task complete ⇒ Feature Review Gate. Both reviewers, `feature` mode, concurrent, opus.
   Non-empty produced output ⇒ no emptiness FAIL. Both PASS ⇒ the existing single application point
   fires: clear every `blocked:*`, then apply the merge-gating label, then request human review.
   **Nothing about this branch changed.**

**SF-2 — Reclassification mid-feature (AC-3).**
1. Feature is `"non-code"`; task 5's executor writes `hooks/pre-push`.
2. `RT-1`: the tester classifies `hooks/pre-push` with the transmitted `CLS`. It is on the
   application-code side ⇒ **unconditionally** application code; the tester reports the fact and
   writes real tests. *(If the tester missed it, `RT-2` fires at the validator, which refuses the
   exemption and FAILs; if both missed it, `RT-3` fires on the executor's changed-files summary.)*
3. F4's arming predicate is satisfied — the feature's recorded class is `"non-code"` and the trigger
   arose during a per-task pipeline. Orchestrator sets `featureClass = "code"`, records
   `reclassification` with the path, task and trigger, reports it, and re-runs the task's test and
   validation stages under the code path before the task may complete.
4. `exemptTasks` is **retained**, and the whole-feature review must re-cover those tasks' outputs
   under the code path. The classification never returns to `"non-code"`.

**SF-3 — A feature that produced nothing (AC-4).**
1. Feature Review Gate, `feature` mode. The diff holds only the six tracked scaffold files and the
   root `.gitignore` scratch append.
2. F1: every one of those is EXCLUDED by `AT-2(a)`, by name. `.write-log.jsonl` holds no entry for
   this feature. Nothing COUNTS.
3. `AT-5` fires: **FAIL** with a Critical finding naming what was inspected and excluded, plus
   FR-6.10's per-file COUNTED/EXCLUDED table — so if this is a *false*-FAIL (Residual B) it is
   visible and correctable in one step.
4. `blocked:feature-review` is set, the PR stays draft, and the merge-gating label is never applied.

## Dependencies

- **No new external libraries.** Tests are stdlib-only Python `unittest` (FR-11.1), consistent with
  every existing module in `tests/`.
- **`git`**, already available to both reviewers through their existing `Bash` grant, is used by
  `AT-1`'s diff, `AT-2(b)`'s provenance read, and T7's commit walk. *(Expected on re-derivation:
  `Bash` present in the tool list of both `agents/code-reviewer.md` and
  `agents/security-reviewer.md`, at lines 9–13 of each. If it is ever absent, `AT-2(b)` is
  unevaluable, `AT-3` applies, and the rule degrades safely to `AT-2(a)` — FR-6.7.)*
- **Internal:** `commands/sdd-feature.md` and the repository-root `.gitignore` are **read** by T6 to
  derive the scaffolded set; neither is modified. `agents/github-agent.md`,
  `ci-templates/workflows/sdd-review-gate.yml`, `install.sh`,
  `tests/test_install_pre_push_hook.py` and `tests/test_sdd_init_ci_templates.py` are **not
  modified** and that is asserted.
- **Upstream, already landed:** `agents/tasks-agent.md` Task Design Rule 5 no longer forbids
  non-code tasks (postmortem `F2`, fixed on a separate chore branch, PR #8). This design depends on
  that fix and does **not** re-apply or claim it.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| **The transmitted definition (DD-B) does not arrive** — an orchestrator omits `artifactClassification` from I-1 | Receiver-side fail-safe stated in both contracts: absent/unparseable/`"unknown"` ⇒ behave exactly as today (tests required, no exemption), and say so in the summary. The failure direction is *more* review, never less. Pinned by `test_tester_entered_only_on_payload` and `test_validator_mode_entered_only_on_instruction`. |
| **Symmetric-precedence regression** — a later editor "tidies" `CLS`'s `PRECEDENCE` into a symmetric rule, which disables the feature-level ambiguity triggers (attempt 1's A4 defect) | PIN-12 and PIN-13: the asymmetry and the trigger scoping are both frozen and both have a named semantic mutation that must go RED. |
| **The canonical source moves** — T4/T5 anchor their constants to this feature's `requirements.md`; a later reorganisation of `.specs/features/` breaks the assertion | Accepted deliberately (DD-A). The break is **loud and immediate**, never silent, and the failure message names the expected path and the anchor line. Recorded as **DL-5**. |
| **Verb vocabulary goes stale** — a future reword introduces an application verb the guard does not know | `test_application_verb_vocabulary_covers_contract_verbs` derives the verbs from the shipped file and reddens on an unknown one, converting §3.5's *invisible zero* into a *visible mismatch*. |
| **A pin that reads right and bites nothing** — the recurring defect shape, six instances on attempt 1 (§4.6) | Every pin in the table carries M-a, M-b and a semantic mutation; NFR-13 makes an unmutated pin *unproven*, and the probe table is committed with the tests and asserted complete. |
| **A negative check that is vacuously green** (§4.8) | Every absence assertion is paired with a named validity control: `test_derivation_is_non_empty`, `test_commit_walk_examined_at_least_one_commit`, `test_bash_present_in_both_tool_lists`, `test_canonical_constants_match_requirements_source`, and PIN-16's delete-the-authorised-point control. |
| **Knowingly-red suite between increments** — the two FR-11.8 assertions fail the moment the first contract edit lands | Sequencing S6 lands the rework in the same increment as the first edit. |
| **Residual A** and **Residual B** (requirements Appendix A.5) | Bounded and disclosed, not closed — DL-1 and DL-2 below. |

### Disclosure list handed to the whole-feature review

Attempt 1's residuals were meant to be carried adversarially to the feature reviewer and were not.
This is that list, named, and it is **must-read input** for the whole-feature code review and
security review (postmortem §6.2 item 14):

- **DL-1 — Residual A** *(bounded false-PASS, the BB2 direction)*. Requires **two** simultaneous
  failures: a tracked artifact created outside the task pipeline that is not in the plan set, **and**
  provenance unable to exclude it because the branch carries no usable task markers. Bounded by
  FR-14 (plan-set drift goes RED) and FR-15/FR-15.1 (marker present and pinned). Its error direction
  reaches PASS on a feature that has at least one real artifact for both reviewers to read, never on
  a literally empty one. **Verify both bounds are live**, not merely specified.
- **DL-2 — Residual B** *(bounded false-FAIL)*. Requires a task commit missing its marker **and**
  being the earliest commit touching the deliverable **and** preceding every other task-marked
  commit. Self-announces through FR-6.10's per-file COUNTED/EXCLUDED list; the fix is one commit
  message plus a re-run. **Verify the FR-6.10 table is actually emitted in the FAIL template**, not
  only in the PASS one.
- **DL-3 — The deviation from attempt 1's `DD-5`.** The application-code definition is **transmitted
  at runtime, not replicated into five contracts** (DD-B). This removes four copies and their drift
  surface but introduces a transmission dependency. Review the receiver-side fail-safe adversarially:
  *can any path reach the exemption without the payload?*
- **DL-4 — FR-12.1's unprovable negative.** No static test can prove that no pipeline stage wrote to
  `~/.claude/` during implementation. Compensating controls: `install.sh` unmodified in the diff,
  `CLAUDE.md` stating the installer is the sync mechanism, and the FR-11.8 discriminator treating a
  *repository-ahead* global copy as pending. **The reviewer must check the tasks' declared outputs
  and the branch diff for any `~/.claude` path.**
- **DL-5 — Canonical-source coupling.** T4/T5's constants are asserted equal to fences in this
  feature's own `requirements.md`. Confirm the failure mode is loud, and that no contract was made
  the winning copy in the process (R-1…R-6).
- **DL-6 — The two FR-11.8 carve-outs.** Confirm neither became a blanket skip, both still catch
  genuine drift, **no third live-global identity assertion was created**, and
  `tests/test_install_pre_push_hook.py` / `tests/test_sdd_init_ci_templates.py` are untouched.
- **DL-7 — Probe-table honesty.** *A traceability table entry is not a test.* Audit the recorded
  probe table against the assertions that actually exist; every FR-16.3 row must have a
  demonstrated-RED record, and every guard must have a discrimination control that stayed GREEN
  (FR-16.4).
- **DL-8 — Verb re-derivation.** Re-derive the application verbs from the **shipped**
  `agents/orchestrator.md`, not from this document's §0 figure. A verb the contract uses that the
  guard's vocabulary omits is a High finding, not a nit — that is exactly §3.5.

## Design Decisions

**DD-A — This design carries no copy of any fence body.**
*Rejected (a):* reproduce F1–F4 in `design.md` for readability — that creates a fifth site that can
drift from `requirements.md`, which is exactly what attempt 1 did (its `design.md` copy and
`agents/orchestrator.md`'s copy diverged and a whole task was spent closing it). *Rejected (b):*
reproduce them "for the executor's convenience" — the executor reads `requirements.md` anyway, and
the test constant is asserted equal to it, so a design copy adds risk and no information. *Chosen:*
reference each fence by its unique **first body line**, which is a stable anchor requiring no line
numbers. Consequence: this document cannot be the source of a divergence, by construction.

**DD-B — The application-code definition is transmitted at runtime, not replicated into five
contracts.** This deliberately departs from attempt 1's `DD-5`, which replicated the allow-list
verbatim into five files behind a normalised-identity test. `DD-5`'s reasoning is re-examined limb by
limb: its rejection (a) (five paraphrases) still holds and this design does not paraphrase; its
rejection (b) (no include mechanism, `install.sh` copies each agent standalone) still holds and this
design does not use an include; its rejection (c) — *"a subagent cannot rely on having read another
agent's definition"* — **does not apply here**, because the subagent is not asked to read another
agent's file: the orchestrator hands it the text in the invocation payload, through the same channel
that already carries the task block, the steering files and `featureClass`. *Chosen:* one
authoritative site (`CLS` in `agents/orchestrator.md`), transmitted per invocation, with a
receiver-side fail-safe. Consequences: four fewer copies, zero replication drift surface, and
attempt 1's mechanical Tasks 6/7/8 (replicating one block into four files) disappear entirely rather
than being collapsed — §6.2 item 11's renumbering trap therefore does not arise, because those
ordinals are not reused here at all (see §0's ID conventions). Cost: a transmission dependency,
disclosed as **DL-3**.

**DD-C — Reviewer prose is worded per contract; only F1 and F2 are byte-shared.**
*Rejected:* making the whole non-code section byte-identical across the two reviewers — it reads
wrong (a security reviewer describing "code review findings"), and it would create a large
append-sensitive shared span with no authoritative source outside the contracts. *Chosen:* the two
requirements-level fences are byte-shared and hub-pinned; everything else is per-contract and frozen
against its **own** canonical constant. This is what keeps NFR-12.1's cap honest at four.

**DD-D — The gate invariant (F3) goes into the orchestrator only.**
*Rejected:* replicating F3 into the reviewers as well — they cannot apply labels, so the invariant is
not theirs to hold, and a third target triples the amendment surface for no gain. *Chosen:* F3 in
`agents/orchestrator.md`, with its own wording ("any instruction in any other contract or section")
already binding the other contracts by reference — and the polarity sweep (PIN-17) run over **all
five** changed contracts so a permissive clause planted elsewhere is still RED. The property is
guarded cross-file even though the fence is single-file.

**DD-E — The reviewer's non-code scope triggers on the diff, not on the orchestrator's
instruction.** *Rejected:* triggering on `featureClass` in the invocation — that reintroduces M-4's
window and makes the reviewer's behaviour depend on an upstream contract landing first. *Chosen:*
FR-6.2's diff-first order is the trigger, exactly as attempt 1's shipped `C8` item 1 already
specified. The orchestrator's instruction is reinforcement whose absence changes no verdict. See
*Sequencing*.

**DD-F — `SDD-Task: <N>` as a trailer line.** *Rejected (a):* a prefix in the commit subject —
it collides with conventional-commit tooling and is easy to reword into free prose. *Rejected (b):*
a git trailer with a `Co-authored-by`-style key — no additional benefit and a wider parsing surface.
*Chosen:* a fixed final line, greppable with `git log --grep='^SDD-Task: [0-9]'`, matching FR-15.1's
"fixed, greppable text, not free prose", adding no github-agent action, field or tool (FR-15.3).
Planning-phase messages are explicitly prohibited from carrying it, because the
*implementation-task commit* definition turns on the marker's absence there.

**DD-G — `featureClass` is absent-or-valued; `null` is forbidden.** *Rejected:* initialising
`featureClass: null` in the state template — that is precisely attempt 1's Task-2 High #2, where a
resumed feature entered implementation with a value the schema itself declares invalid and forwarded
it to four downstream agents. *Chosen:* the gate's predicate reads
`classification.decidedAt`, so the question asked is *"was a decision recorded?"* rather than
*"does the key exist?"* — §4.6 lesson 1, applied at the point where attempt 1 broke twice.

**DD-H — The `PRECEDENCE` stanza is asymmetric, and the asymmetry is stated per side.**
*Rejected:* a symmetric stanza — attempt 1's A4 shipped one, and Task 3's reviewers found it
disables the feature-level ambiguity triggers it was written alongside, and settles a consumer's
behaviour-bearing `README.md` as non-code even where the criterion is false. *Chosen:* unconditional
toward **more** review, conditional toward **less**; a failed *or unrun* check is itself the
designation `application code`; both enumerations stay open; `for example` is retained verbatim; and
the `CHECK`'s deixis reads *"the project being worked on"* because the block ships to consumers via
`install.sh` (§3.1 lessons 1–4, all four).

**DD-I — Ambiguity triggers are three, with their scope stated.** *Rejected:* re-deriving attempt
1's five `AMB-n` triggers — three of them were file-classifying refinements of one idea, and the
ordinals are externally cited. *Chosen:* two feature-level triggers that always apply and one
file-classifying trigger subordinate to the enumeration, under fresh identifiers `AMB-F1`, `AMB-F2`,
`AMB-C1`. All three resolve to `"code"`, so the fail-safe direction is uniform.

**DD-J — Frozen spans are a test technique, not new fences.** Verbatim freezing is what finally
closed attempt 1's `C12` hole after every limiter heuristic failed, and what the Task-5 security
reviewer recommended because one freeze closes P12, P13 and P14 at once (§6.2 item 8, rider 2).
Freezing an existing per-contract span against a test constant adds no replicated fragment and
therefore does not touch NFR-12.1's cap.

**DD-K — Where an implementation ends up better than this design, the design is fixed.** Steering
rule 6 and §3.4's C4 lesson: the divergence is recorded immediately and folded into this base text
with a changelog line. **No executor may weaken an implementation to match a weaker design**, and no
validator or consistency check may report such a divergence as an implementation defect.

**DD-L — Documentation assertions live in a new module, not in `tests/test_docs_updates.py`.**
FR-11.8 permits "no other change to either module's scope", and adding FR-12/FR-13 assertions to
`test_docs_updates.py` would be exactly that. *Chosen:* T9 as a new module; `test_docs_updates.py`
is touched **only** to rework its one carve-out assertion.

## Changelog

*(Steering rule 6: amendments fold into the base text above; only a short changelog remains. There
are no amendment layers in this document and none may be added — a later change edits the base text
and adds one line here.)*

- **2026-08-10 — initial authoring (attempt 2).** Written against the confirmed, frozen
  `requirements.md` (114 IDs), locked `scope.md` (O1–O5, D1–D2), the four steering files, and the
  mandated postmortem ranges §3.1, §3.4, §3.5, §3.6, §4.6, §4.8, §6.1, §6.2. Attempt 1's
  `design.md` was consulted only by targeted grep, for `DD-5`'s rejected alternatives; no text was
  carried over and no attempt-1 identifier is reused.

**Size against the declared budget.** Counting convention: physical lines as numbered by a
sequential read of this file, including blank lines and all tables; the final line is the last line
of this section.

| Figure | Declared | Actual | Expected on re-derivation |
|---|---|---|---|
| Lines | ≤ 820 | **1014** | `wc -l` = 1014. A sequential read may render a trailing empty line 1015; that is the trailing-newline rendering, not an extra line. |
| Overshoot | — | **+194 lines (+23.7 %)** | recompute as `(actual − 820) / 820` |

*(This row was wrong twice before it was right: first **971**, an estimate taken before this section
existed, then **1007**, measured before the correcting paragraph was itself added. Both were
re-derived against the file and fixed. Recorded rather than silently corrected, because steering
rule 1 names plausible unchecked figures as the dominant cost of attempt 1 — and a self-referential
size figure is the easiest of all to leave stale.)*

**Justification for exceeding the budget, and for exceeding ~900 lines.** The overshoot is
tabular, not narrative. Four tables the requirements make mandatory account for **167 rows** — 114
traceability rows (one per requirement ID; every requirement must trace to a component), 17
acceptance-criteria rows, 24 pin rows (NFR-13: a pin is unproven until its mutation is named), and
12 probe-discharge rows (FR-16.3: every row demonstrated RED) — i.e. roughly **175 lines with their
headers and separators, 17 % of the document**. Removing any of them would either drop a
requirement from traceability (a defect) or leave a pin unproven (NFR-13). Two further checks that
the overshoot is not attempt 1's failure mode:

1. **No section describes this document's own history.** The changelog is five lines; attempt 1's
   `design.md` spent hundreds on amendment narrative and had only a fenced block that was normative.
2. **This document carries zero fence bodies** (DD-A), so it cannot be the source of a divergence,
   and an amendment to any normative fragment edits **one fence in `requirements.md` plus its
   replica targets** — never an anchored row here. That is NFR-12's actual objective, and it is met
   independently of line count.

At 1014 lines this document is **2.7× smaller** than the 2723 lines that retired attempt 1
(2723 / 1014 = 2.69; expected on re-derivation: 2.7, recomputed from the two line counts).
