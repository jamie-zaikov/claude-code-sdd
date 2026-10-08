---
description: "Show the status of all SDD features in the current project"
---

Scan `.specs/features/` for all subdirectories. For each one that contains a `.spec-state.json`, read the state file and report:

- Feature name
- Current phase (requirements / design / tasks / implementation / complete)
- Confirmation status (which phases are confirmed)
- Implementation progress (N of M tasks complete, current task, retry count)
- Live specialists: run `python3 ~/.claude/tools/sdd-status.py check --feature-dir .specs/features/<name>` and list each status file whose state is not `done` (agent, task, state, step, age). Read the status files, never the ledgers.
- Overnight: whether `overnightAuthorization` is set, the `deferred` task count, and the `userApprovalNeeded` count

Present as a summary table. If no features exist, tell the user to run `/sdd-init` first and then `/sdd-feature <name>` to create one.
