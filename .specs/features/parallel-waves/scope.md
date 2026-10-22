# Scope: parallel-waves

<!-- Owned by the main session during scoping. Status: PROPOSAL rev 3 — not locked, implementation not started. -->

## One-line description
Let agents solve the approved problem with real discretion, give them a test gate whose blockers
name a real violated property, run two independent tasks concurrently with one honest combined
gate, and make the framework install and guard secrets on native Windows with Git Bash. One branch,
one PR.

## Sources
- Retro proposal, lab-automation-workflows `pis4-cellario-protocols`, 2026-10-21:
  `input-data/sdd-retro-2026-10-21.md`.
- Main-session findings F1–F13 and measurements: `spec-memory/findings.md`,
  `spec-memory/supporting-data.md` (historical figures from that run, measured 2026-10-22).
- Independent reviews: `spec-memory/sol-reasoning-2026-10-22.md`,
  `spec-memory/astra-review-2026-10-22.md`, `spec-memory/astra-review-claude-updates-2026-10-22.md`.
- Main-session reasoning: `spec-memory/main-reasoning-2026-10-22.md` (its §5–6 are superseded by
  this scope).
- All of the above are gitignored working files.

## Open questions resolved
- O1 Windows target → **native Windows with Git for Windows (Git Bash)**. This does not promise
  native PowerShell execution of SDD playbooks. WSL keeps working through the POSIX path.
  (user, 2026-10-22)
- O2 Packaging → **one PR**. Mechanisms keep separate acceptance and commits; only real
  dependencies order them (see *Dependencies*). (user, 2026-10-22)
- O3 Mutation rule → a dangerous semantic mutation must go RED and an equivalent presentation
  change must stay GREEN; exact bytes only for parser / wire / machine / public-interface text.
  Applied to steering lesson 5 on 2026-10-22. (user, 2026-10-22)
- O4 Concurrency isolation → **isolated worktrees**; never shared-checkout writes. (Sol, Astra,
  main session; user confirmed)
- O5 orchestrator.md → extract only the wave/integration procedure into a playbook file with one
  normative definition; repair heading-anchored tests first. (Sol, Astra, main session)
- O6 Sequencing → the two-task wave ships in this feature (Astra over Sol).
- O7 Small repairs → in-attempt repair bounded by **strict shrink of a stable blocking set**; no new
  counter (definition in mechanism 5; accepted by Astra follow-up).
- O8 Test-file size → **warning only** for test files; the module-size limit stays enforced for
  non-test source files. Correctness and maintainability concerns about a large test file remain
  reviewable as normal findings. (user, 2026-10-22)

## Discrepancies reconciled
- D1 Retro "full suite once per land" → with one task per land that is once per task; the
  integration unit is a **batch of ≤ 2 tasks**.
- D2 `knownRed` as a wave prerequisite → only incomplete-integration plans need it; **deferred**.
- D3 `Files:` as a contract → stays an **estimate**; active **ownership** controls concurrent edits.
- D4 `pipelineVersion` → cannot preserve old behaviour once `~/.claude` is overwritten; replaced
  by **opt-in for new features** and **no install while a feature depends on the old bundle**.
- D5 Existing contradictions fixed here: AGENTS.md / CLAUDE.md say reviews follow the validator
  PASS while orchestrator.md runs them concurrently (one consistent order everywhere); steering
  lesson 7 says draft PR during the build while orchestrator.md is local-first.
- D6 The existing retry rule (orchestrator.md ~490–492) counts a validator FAIL as **one** blocking
  event. In-attempt repair must compare individual defect identities, not that scalar.
- D7 The final-review full-suite wording must change with the batch rule, or it still demands a
  redundant run.

## Mechanisms

| # | Mechanism | Contents |
|---|---|---|
| 1 | Housekeeping + contradictions | User trailer rule wins over session attribution (orchestrator.md:489). Tool-recorded launch and finish times per invocation (elapsed time only; no active/wait split claimed; no birth-time check). Fix D5. |
| 2 | Test signal | `scripts/ci.sh` runs the unittest suite as one process, with a seam so `tests/test_dogfood_ci.py` does not recurse; report collected/skipped counts and a clear reason per blocker. Repair the brittle pins in contracts this feature edits (e.g. `test_fast_reliable_pipeline.py:71, 119-127, 339-350`, `test_pr2_pipeline.py:28-29`). O3 applies to every new or repaired pin. `sdd-module-size.py`: test files produce a warning, never a blocking violation (O8); non-test files unchanged. |
| 3 | Native Windows install | See *Windows acceptance*. Proposed design (not an acceptance condition): a stdlib Python installer core with thin `install.sh` / `install.ps1` shims, shared by uninstall. One interpreter-resolution policy for every installed entrypoint (secret hooks, `ci.sh`, pre-push hook, tool invocations in playbooks), not only the hooks. `.gitattributes` forcing LF for `*.md`, `*.py`, `*.sh`, hook templates. Windows CI keeps the `sdd-build-test-lint` required-check contract (or changes it deliberately) and does not push a repo-specific Windows policy into downstream templates by accident. |
| 4 | Outcome envelope | Tasks state outcome, acceptance and hard constraints; paths and internal signatures are estimates. The executor may do a local prerequisite refactor inside the authorized subsystem (edit `task-executor.md:21-24, 58-77`, `tasks-agent.md:75-91`). Prototype authority is granted once, within a stated local-resource and data boundary; prototype patches are retained and pass the normal gates after confirmation; no earlier PASS is invented. Owner agents reconcile internal detail with a recorded reason; material changes (acceptance, public contract that is an approved constraint, authority, external effect, agreed risk) keep user confirmation. Probe tiers: discovery (read-only), isolated prototype, live mutation (project-level authority only). Scrub before any write; delete raw captures; keep sanitized evidence. |
| 5 | Findings + repair | One coordinator-written findings index outside `.spec-state.json`, referencing specialist reports; one home replaces both `deferredFindings` locations and ad-hoc note keys (historical trigger: the pis4 state file measured 66,632 B on 2026-10-22, over the 64 KB cap). Route-forward of cheap Mediums; a routed finding stays open until its destination verifies closure. **In-attempt repair:** (a) at the first blocking result, record the blocking set with stable identities (stage + requirement/defect identity, not line numbers) and its evidence; (b) apply one localized correction, re-run the failed check and every check whose evidence it invalidates; (c) continue only if the new set is a strict subset of the previous one with no new or reopened blocker; (d) the comparison does not restart when checker, invocation or wording changes; a blocker leaves the set only by being fixed, or by an independent decision that it was invalid — never by deferral, severity reduction, weakened acceptance or altered tests; (e) unchanged/larger set, new blocker, uncertain cause or grown scope → existing retry policy; (f) repairs stay in the attempt and finding history; `retryCount` and earlier failure evidence are never reset; liveness/recovery rules still apply. Cosmetic exemption = equivalent presentation only; machine/instrument-read strings never. |
| 6 | Two-task wave | See *Combined-candidate rule*. Ownership of shared fixtures, locks, generated files, modes, renames and deletions; the orchestrator can extend ownership to unowned internal paths within approved intent; an undeclared path pauses land for classification; conflict → serialise. Tests proven to import from the worktree candidate. Executor/tester use read-only git; commits by explicit paths, never user files. See *Permission rule*. New integration semantics in a new or extended tool (not a larger K in `sdd-overlap.py`). Extract the wave procedure per O5. |

## Dependencies (inside the one PR)
- 1, 2, 3 and 4 are independent of each other once their shared contracts are agreed. 3's
  Windows CI uses 2's authoritative entrypoint, but 3's installer work does not wait for 2.
- 6 depends on 4 (ownership and discretion), 5 (finding identity, repair) and the evidence record
  in the combined-candidate rule.

## Windows acceptance
1. Install, reinstall and uninstall target an isolated destination through a real override shared
   by install and uninstall (today `install.sh:11`, `uninstall.sh:4` hard-code it from HOME); a
   test can never touch the user's installation; a path with spaces works.
2. Settings: unrelated user settings and hooks are preserved; managed entries are replaced by
   identity, not duplicated (an old `python3 ~/...` entry and a new absolute entry never coexist);
   a recoverable backup exists; reinstall is idempotent; malformed settings or a failed write fail
   safely with no false success; a controlled recovery case is tested.
3. Uninstall removes only entries this installer owns, preserves user changes, and reports any
   configuration it keeps.
4. The **exact command string from generated settings** runs through the shell that actually runs
   hook commands, with realistic payloads. Invoking the Python file with an argv list is not proof.
5. For the supported harness version, the shell tool names, matcher behaviour, deny-rule path forms
   and blocking outcome are verified with harmless synthetic secret fixtures, including the declared
   dump vectors and legitimate secret-use negatives. If a PowerShell tool exists, it is covered.
6. If a required protection cannot be installed or verified for a supported shell, the
   installation is reported **not protected** — an actionable failure, not a warning followed by
   success. Docs state the supported protection vectors and their limits; no claim that regex hooks
   stop every exfiltration.
7. The authoritative suite and focused worktree / integration / recovery checks run on Windows with
   Git Bash, including candidate import resolution and worktree cleanup after a stopped child; file
   locking, path case/separators and file modes are test cases, not assumptions.
8. The declared Python minimum is verified in CI, not assumed.
9. Any item that cannot be verified (e.g. no harness evidence) is reported **unverified**, never as
   a simulated PASS.

## Combined-candidate rule
- Both tasks are dependency-ready. Both outputs are frozen before assembly. One actor integrates;
  no executor or tester mutates the candidate while its gate and reviews run.
- An evidence record names the combined candidate, the relevant spec revision, the command /
  selection / result, and relevant runtime inputs (a code-tree hash alone excludes `.specs/` and
  ignored inputs).
- Isolated results are early evidence, not PASS on the combined tree. Affected task validation and
  review are performed or refreshed on the candidate; unaffected inspection may be reused with an
  explicit relevance decision; reviewers share one valid suite result.
- A changed candidate or relevant input invalidates affected evidence. "One full gate per batch"
  means one reusable result for an unchanged final candidate: a repair reruns it; a new stage alone
  does not. The final-review wording follows (D7).
- No task in the batch completes until the combined gate and applicable reviews pass.
- Integration failure: stop writers, keep both patches and their bases, restore the integration
  workspace safely, transfer ownership, continue in sequence. Sequence can still expose a real
  incompatibility; fallback never promises success or erases the failure.

## Permission rule
Replaces "a command denied to a subagent goes to `userApprovalNeeded`":
- A real policy or security denial is never bypassed through another actor or an equivalent tool.
- A normal harness approval request follows the harness's own escalation path; an existing
  authorization stays valid.
- A missing tool or a transient execution error is not a denial; an authorized actor may perform
  the operation through the proper path when that does not evade a restriction. Git mutations still
  belong to github-agent.

## Out of scope / deferred
- Generic `knownRed` baseline (revisit only for a plan that lands incomplete integration).
- `parts[]`, K-way waves, a generic scheduler.
- `pipelineVersion`, file birth time, an active/wait time split.
- Native PowerShell execution of SDD playbooks; removal of every POSIX dependency.
- Level 3 (`lh_convert.py` split). Any change to the in-flight pis4 feature. A global
  mutating-probe authorization.

## Acceptance outcomes (draft, for requirements)
1. A routine internal refactor or a new unowned internal path completes without a user amendment;
   a material acceptance change still stops for confirmation.
2. A retained prototype patch is adopted after confirmation with no invented earlier PASS.
3. Sampled harmless reformats pass the affected policy tests; sampled dangerous mutations fail
   them; every remaining blocker states the violated property. `ci.sh` runs the full suite with no
   recursion and no silent collection loss.
4. A test file over the module-size limit produces a warning and does not block; a non-test source
   file over it still blocks.
5. In-attempt repair ends in finite steps by the strict-shrink rule and never resets `retryCount`
   or failure evidence.
6. The Windows acceptance list passes on `windows-latest` with Git Bash, or each unmet item is
   reported unverified / not protected.
7. Two independent tasks run in isolated worktrees; one integrator produces the checked combined
   candidate; a deliberate cross-task incompatibility blocks the batch, preserves both patches and
   user files, and the run continues in sequence.
8. Final review uses valid evidence for the final candidate; no unchanged full-suite rerun only
   because a new stage starts.

## Pilot measures
Elapsed time per invocation (launch/finish), full-suite count and duration, avoidable user
interruptions, false blockers vs real defects, integration failures. Compared against the current
optimized baseline, not a wholly serial one.
