# Scope: parallel-waves

<!-- Owned by the main session during scoping. Status: PROPOSAL rev 2 — not locked, implementation not started. -->

## One-line description
Let agents solve the approved problem with real discretion, give them a test gate that fails only
for real reasons, run two independent tasks concurrently with one honest combined gate, and make
the framework install and guard secrets on native Windows. One branch, one PR.

## Sources
- Retro proposal, lab-automation-workflows `pis4-cellario-protocols`, 2026-10-21:
  `input-data/sdd-retro-2026-10-21.md`.
- Main-session findings F1–F13 and measurements: `spec-memory/findings.md`,
  `spec-memory/supporting-data.md`.
- Independent reviews: `spec-memory/sol-reasoning-2026-10-22.md`,
  `spec-memory/astra-review-2026-10-22.md`.
- Main-session reasoning on both reviews and the Windows installer:
  `spec-memory/main-reasoning-2026-10-22.md` (supersedes F1, F2, F3, F5, F8, F11, F12, F13 where
  they conflict).
- All of the above are gitignored working files.

## Open questions resolved
- O1 Windows target → **native Windows with Git for Windows (Git Bash)**; WSL keeps working
  through `install.sh`. (user, 2026-10-22)
- O2 Packaging → **one PR** for all six mechanisms. (user, 2026-10-22)
- O3 Mutation rule → **changed**: a dangerous semantic mutation must go RED and an equivalent
  presentation change must stay GREEN; exact bytes only for parser / wire / machine / public
  interface text. Applied to steering lesson 5 on 2026-10-22. (user, 2026-10-22)
- O4 Concurrency isolation (D1) → **isolated worktrees**; never shared-checkout writes.
  (Sol, Astra, main session agree; user confirmed the reasoning)
- O5 orchestrator.md (D2) → **extract only the wave/integration procedure** into a playbook file
  with one normative definition; no broad rewrite. Brittle tests that anchor on headings are
  repaired first. (Sol, Astra, main session agree)
- O6 Sequencing → the two-task wave ships **in this feature**, not after a separate sequential
  pilot (Astra over Sol; no measured data supports deferral).
- O7 Small repairs → stay in the same attempt under the **existing convergence rule** (blocking
  findings strictly shrink, none new); no new counter or budget.

## Discrepancies reconciled
- D1 Retro F5 "full suite once per land" → with one task per land that is once per task; the
  integration unit is a **batch of ≤ 2 tasks**, one full gate per batch.
- D2 `knownRed` as a wave prerequisite → only incomplete-integration plans need it; **deferred**.
- D3 `Files:` as a contract → stays an **estimate**; active **ownership** controls concurrent
  edits, extendable by the orchestrator for unowned internal paths; conflict → serialise.
- D4 `pipelineVersion` → cannot preserve old behaviour once `install.sh` overwrites `~/.claude`;
  replaced by **opt-in for new features** and **no install while a feature depends on the old
  bundle**.
- D5 Existing contradictions fixed in this feature: AGENTS.md / CLAUDE.md say reviews follow the
  validator PASS while orchestrator.md runs them concurrently; steering lesson 7 says draft PR
  during the build while orchestrator.md is local-first.

## Mechanisms (commit order)

| # | Mechanism | Contents |
|---|---|---|
| 1 | Housekeeping + contradictions | User trailer rule wins over session attribution (orchestrator.md:489). Tool-recorded launch and finish times in status files (no birth-time check). Fix D5. |
| 2 | Test signal | `scripts/ci.sh` runs the unittest suite as one process, with a seam so `tests/test_dogfood_ci.py` does not recurse; report collected/skipped counts. Repair the brittle pins in contracts this feature edits (e.g. `test_fast_reliable_pipeline.py:71, 119-127, 339-350`, `test_pr2_pipeline.py:28-29`). Apply the O3 mutation rule to every new or repaired pin. |
| 3 | Native Windows install | `install.py` (stdlib) holds all installer logic; `install.sh` and new `install.ps1` are thin shims that find Python (`python3` / `py -3` / `python`). Same for uninstall. Hooks registered with the resolved interpreter and an absolute, quoted path (no `~`). Secret guard covers every shell tool the harness exposes on Windows (incl. PowerShell dump verbs, if a PowerShell tool exists — verify) and fails loudly when it cannot. Deny rules in the form the harness matches on Windows. `.gitattributes` forces LF for `*.md`, `*.py`, `*.sh`, hook templates. CI adds `windows-latest`: install into a temp `CLAUDE_HOME`, start each hook on a sample payload, run the suite through `ci.sh`. Prerequisites stated: Python 3.9+, Git for Windows. |
| 4 | Outcome envelope | Tasks state outcome, acceptance and hard constraints; paths and internal signatures are estimates. The executor may do a local prerequisite refactor inside the authorized subsystem (edit `task-executor.md:21-24, 58-77`, `tasks-agent.md:75-91`). Explicitly authorized isolated prototypes are evidence; their patches are retained and pass the normal gates after confirmation. Owner agents reconcile internal detail with a recorded reason; material changes (acceptance, public contract, authority, external effect, agreed risk) keep user confirmation. Probe tiers: discovery (read-only), isolated prototype, live mutation (project-level authority only). Scrub before any write; delete raw captures; keep sanitized evidence. |
| 5 | Findings + repair | One coordinator-written findings index outside `.spec-state.json` (the pis4 state file is 66,632 B, over the 64 KB cap), referencing specialist reports; one home replaces both `deferredFindings` locations and ad-hoc note keys. Route-forward of cheap Mediums; a routed finding stays open until its destination verifies closure. In-attempt repair under O7. Cosmetic exemption = equivalent presentation only; machine/instrument-read strings never. |
| 6 | Two-task wave | Two dependency-ready tasks in isolated worktrees; tests proven to import from the worktree. Ownership of shared fixtures, locks, generated files, modes, renames and deletions; an undeclared path pauses land for classification. One integrator assembles one candidate; one full gate; no task in the batch completes until the combined gate and applicable reviews pass on the candidate. Failure preserves both patches and user files and falls back to sequence. Executor/tester use read-only git; commits by explicit paths, never user files; a command denied to a subagent goes to `userApprovalNeeded`. New integration semantics in a new or extended tool (not a larger K in `sdd-overlap.py`). Extract the wave procedure per O5. |

## Out of scope / deferred
- Generic `knownRed` baseline (revisit only for a plan that lands incomplete integration).
- `parts[]`, K-way waves, a generic scheduler.
- `pipelineVersion`, file birth time.
- Level 3 (`lh_convert.py` split).
- Any change to the in-flight pis4 feature.
- A global mutating-probe authorization.

## Acceptance outcomes (draft, for requirements)
1. A routine internal refactor or a new unowned internal path completes without a user amendment;
   a material acceptance change still stops for confirmation.
2. A retained prototype patch is adopted after confirmation with no invented earlier PASS.
3. A harmless reformat passes the affected policy tests; a dangerous change to the rule fails them.
   `ci.sh` runs the full suite with no recursion and no silent collection loss.
4. On `windows-latest`, the installer completes, both secret hooks start from settings.json, and
   the suite passes; a secret dump through every exposed shell tool is blocked.
5. Two independent tasks run in isolated worktrees; one integrator produces the checked combined
   tree; a deliberate cross-task incompatibility blocks the batch, preserves both patches and user
   files, and the run continues in sequence.
6. Final review uses valid evidence for the final candidate; no unchanged full-suite rerun only
   because a new stage starts.

## Pilot measures
Active/wait time per task (from launch/finish times), full-suite count and duration, avoidable user
interruptions, false blockers vs real defects, integration failures. Compared against the current
optimized baseline, not a wholly serial one.

## Still open
- Test-file size limit: hard gate, warning, or exempt? (retro: a 507-line test file blocked one task)
