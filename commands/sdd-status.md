---
description: "Show the status of all SDD features in the current project"
---

Scan `.specs/features/` for all subdirectories. For each one that contains a `.spec-state.json`, read the state file and report:

- Feature name
- Current phase (requirements / design / tasks / implementation / complete)
- Confirmation status (which phases are confirmed)
- Implementation progress (N of M tasks complete, current task, retry count)

Present as a summary table. If no features exist, tell the user to run `/sdd-init` first and then `/sdd-feature <name>` to create one.
