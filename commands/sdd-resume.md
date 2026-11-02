---
description: "Resume SDD work on a feature from where it left off"
arguments:
  - name: feature-name
    description: "Name of the feature to resume (matches directory under .specs/features/)"
    required: true
---

Read `.specs/features/$ARGUMENTS/.spec-state.json` and all files in `.specs/steering/`.

Report to the user:
- Feature name
- Current phase
- Which phases are confirmed
- If in implementation: which task is current, how many complete, any pending retries

Then **act as the Orchestrator in this main session** to continue from the current phase: read the Orchestrator playbook (`~/.claude/agents/orchestrator.md`, or the project copy under `.claude/agents/` if present) and follow it directly. Do **not** spawn the Orchestrator as a nested subagent — the main session must keep the background and recovery tools so a stalled specialist can be detected and respawned (see the playbook's *Execution Model* and *Specialist Execution Contract*). If the phase is `implementation` and a task has `retryCount > 0`, inform the user about the previous failure before proceeding.

**Read the status files first.** Run `python3 ~/.claude/tools/sdd-status.py check --feature-dir .specs/features/<feature-name>` (it shows the newest attempt per task and agent) and report every file whose state is not `done` — the specialists that were mid-step when the last session ended. Continue numbering from `invocations` in the state file, never from 1. A `done` file whose result is not yet in `.spec-state.json` is finished work: take its result from `summaryPath`, never re-run it.

**Pending publish.** If `publishPending` is set, follow the playbook's *Acting on `publishPending`* rule: ask to publish when `HEAD` still equals `featureReview.reviewedHead`; otherwise re-run the Feature Review Gate.

**Explore grant.** If the state file has `exploreAuthority` set, it is still valid (it survives sessions until its budget is spent, the feature is `complete`, or the user revokes it): show the grant's objective, boundary, budget and cadence, the attempts used of the budget (`explore.attemptsUsed` of `exploreAuthority.budget` — it includes `reserved` and `uncertain` entries; list each such entry in `explore.attempts[]` by id), and every `retained-by-user` and `open` item in `spec-memory/explore/ledger.md`. If `explore.attemptsUsed > 0` and the log or the ledger file is missing, a cleanup cannot be verified: stop and ask the user before any attempt. An explorer status file that is not `done`, or a `reserved`/`uncertain` attempt, means the next explorer invocation is a `recover` (cleanup and reconciliation, no hypothesis). Start no Explore attempt by yourself — a new attempt starts only on the user's word; a continuous sequence never survives a session by itself (`playbooks/sdd-explore.md` §5).

**Stale overnight authorization.** If the state file has `overnightAuthorization` set, it is void — only a run started in the current session, through `/sdd-overnight <feature> on` or the user's own words followed by its exact steps, holds one. Clear it, tell the user, and show the latest `spec-memory/overnight-summary.md` *Needs you* section if one exists. List every `deferred` task with its `deferredBy` and `parkedRef` before you continue; a deferred task is not pending.

If the feature directory or state file does not exist, tell the user and suggest `/sdd-feature $ARGUMENTS` to create it.
