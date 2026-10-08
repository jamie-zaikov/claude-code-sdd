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

**Stale overnight authorization.** If the state file has `overnightAuthorization` set, it is void — only `/sdd-overnight <feature> on` grants one. Clear it, tell the user, and show the latest `spec-memory/overnight-summary.md` *Needs you* section if one exists. List every `deferred` task with its `deferredBy` and `parkedRef` before you continue; a deferred task is not pending.

If the feature directory or state file does not exist, tell the user and suggest `/sdd-feature $ARGUMENTS` to create it.
