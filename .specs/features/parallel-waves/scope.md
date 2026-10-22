# Scope: parallel-waves

<!-- Owned by the main session during scoping. Status: PROPOSAL — not locked, implementation not started. -->

## One-line description
Bundle the pis4-cellario-protocols retro adjustments into one change: parallel task waves in
isolated worktrees, a test-state model (`knownRed`, scoped per-task runs, a full suite at each wave
land), one findings ledger outside the state file, closed rules for when the user is asked, and
two housekeeping fixes. This is the roadmap's "Level 2" item.

## Source
- Proposal from the `sdd-retro` agent, lab-automation-workflows session, 2026-10-21 (10 ranked
  adjustments). Report copied to `input-data/sdd-retro-2026-10-21.md` (gitignored).
- Main-session analysis: `spec-memory/findings.md` (F1–F13). Measurements:
  `spec-memory/supporting-data.md`. Both gitignored.

## Mechanisms and commit order

One branch (`feat/parallel-waves`), one PR, commits in dependency order:

| # | Mechanism | Retro items | Change |
|---|---|---|---|
| 1 | Housekeeping | 9, 10 | User trailer rule wins over session attribution (orchestrator.md:489). `startedAt` in status files, recorded by the orchestrator at launch; `sdd-status.py` cross-checks with file birth time. |
| 2 | Findings ledger | 3, 5, 6a, cosmetic | `spec-memory/findings.jsonl` (id, severity, source task, `path:line`, `routedTo`, status) replaces both `deferredFindings` homes and the ad-hoc note keys; the state file keeps counts + path. Route-forward of cheap Mediums. Closed trivial-fix lane (no `retryCount` bump). Cosmetic rule for human prose only. |
| 3 | Test-state model | 2, 4 | `knownRed[] {test, cause, owner, recordedAt}` + failing-id baseline; gates block only if the red set grows. Scoped suite per task (touched + neighbour tests, keyed by tree hash). Full suite at each wave land and at Feature Review. Feature Review requires `knownRed == []`. |
| 4 | When to ask the user | 2c, 6, 7 | Mechanical amendment class (owner agent edits, one-line user ack, consistency delta). Attended mode uses the overnight decision-vs-amendment test. Probe lane: not tasks, read-only by default, scrub at write, delete same turn; mutating authority project-level only. |
| 5 | Parallel waves | 1, 1b, 8 | tasks-agent emits `Wave:` and `Owns:` (shared fixtures, locks, generated files); `Files:` becomes a contract. Orchestrator runs a wave in K worktrees (generalised `sdd-overlap.py`), lands serially, checks actual diff ⊆ `Files:` ∪ `Owns:`, runs the full suite after each land. Forbidden-git list in executor/tester. Explicit-path commits; never user files. A command denied to a subagent goes to `userApprovalNeeded`. Task `parts[]`; a pin bump lists every fixture that embeds the pin. |

## Roll-out
- A `pipelineVersion` key set at the Classification Gate selects the new rules; earlier features
  keep the old rules. A tasks.md without `Wave:` lines runs sequentially as today.
- Pilot on the next lab-automation-workflows feature, not on pis4 (in flight).

## Verification (per the prose-repo rule)
- Every new rule gets a test that goes RED when the rule is mutated.
- Full suite as one `python3 -m unittest` process.
- One independent adversarial review over the whole diff before the PR.
- `./install.sh` only after merge.

## Open decisions (block implementation)
- **D1.** Waves in worktrees (recommended — removes the shared-tree incidents structurally) or in
  the shared checkout (the retro's method — faster setup, relies on rules only).
- **D2.** Split orchestrator.md (825 lines, +~150 from this bundle) into playbook files read at
  implementation entry (recommended), or grow it.

## Out of scope
- Level 3 (`lh_convert.py` split for cellario).
- Any change to the pis4 feature in flight.
- Global mutating-probe authorization.
