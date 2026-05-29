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

Then invoke the orchestrator to continue from the current phase. If the phase is `implementation` and a task has `retryCount > 0`, inform the user about the previous failure before proceeding.

If the feature directory or state file does not exist, tell the user and suggest `/sdd-feature $ARGUMENTS` to create it.
