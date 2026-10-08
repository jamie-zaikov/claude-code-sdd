---
description: "Switch an SDD feature into overnight mode (unattended implementation), or turn it off / show its status"
arguments:
  - name: feature-name
    description: "Name of the feature (matches directory under .specs/features/), optionally followed by on | off | status (default: on)"
    required: true
---

Overnight mode is defined in the Orchestrator playbook (`~/.claude/agents/orchestrator.md`, or the
project copy under `.claude/agents/` if present), section **`implementation` → Overnight mode**.
This command is the one switch for it, so every run starts, behaves, and ends the same way. **Act as
the Orchestrator in this main session** — never spawn it as a nested subagent.

Parse `$ARGUMENTS` as `<feature-name> [on|off|status]`; the mode defaults to `on`. Read
`.specs/features/<feature-name>/.spec-state.json` and all files in `.specs/steering/`. If the state
file does not exist, stop and suggest `/sdd-feature <feature-name>`.

## `status`

Report, from the state file only: whether `overnightAuthorization` is set (and its `grantedAt`), the
phase, tasks `completed`/`total`, tasks `deferred`, the count of `userApprovalNeeded` entries, and
the last `preflight.ranAt` with its open gaps. Change nothing.

## `on`

Run these steps in order. Stop at the first step that fails and tell the user why. A halted task is
**parked** (its changes stashed by github-agent, the tree left clean) before any later task starts,
and a later task runs only when its `Depends:` line allows it — both per the playbook.

1. **Phase check.** The phase must be `implementation`, with `confirmed.requirements`,
   `confirmed.design`, and `confirmed.tasks` all true — each confirmed **by the user** — and
   `classification.decidedAt` set. (A `feature-review` phase whose findings re-opened tasks counts as
   `implementation`.) Overnight mode never confirms a planning gate. If a gate is open, stop and
   name it.
2. **Preflight.** Run the playbook's **Preflight** in full (tools and repo setup, credentials by name
   only, inputs, permissions) and record `preflight: { ranAt, gaps: [...] }`. If a gap blocks a
   remaining task, list each gap with the exact fix (the command to run, the env var to export, the
   permission to allow), and stop. Do not start until the user has fixed them and runs this command
   again.
3. **Authorize.** Write `overnightAuthorization: { grantedAt, scope: "implementation", grantedBy:
   "user", quote: "<the user's words that asked for the run>" }` to the state file.
4. **Confirm the plan in one message**, then start without waiting: the next task, the tasks that
   will run, the tasks already `deferred`, and the stop conditions below.
5. **Run.** Follow the playbook's per-task pipeline task after task, with every overnight rule
   applied: never call AskUserQuestion; on an open decision choose the fail-closed, reversible
   option and record it under `userApprovalNeeded`; mark a blocked task `deferred` and continue with
   the next task that does not depend on it; never self-confirm a planning gate or an amendment.
   Drive each specialist by the *Specialist Execution Contract* — act on its completion notice, and
   keep one `ScheduleWakeup` fallback of 1800 s or more as the heartbeat, never a short poll. This
   is deliberate: a completion notice wakes the run at once, so the heartbeat only bounds a silent
   death — such a stall can cost up to one heartbeat before the nudge/respawn steps run.
6. **Stop** when no runnable task remains (the playbook's *The end of the run* rule: when every
   task is complete, the Feature Review Gate runs once and **never publishes**), when the user asks to stop or to take over, or on `off`.
   A user message that only answers a `userApprovalNeeded` entry does not stop the run: record the
   answer, mark that entry resolved, and un-defer the tasks that waited on it. Then write
   `spec-memory/overnight-summary.md` with the playbook's **Overnight summary template**, clear
   `overnightAuthorization`, and report the summary's *Needs you* section to the user.

## `off`

Let the stage that is running finish; start no new task. Then do step 6 of `on`.
