# Global Instructions — Spec-Driven Development

## SDD Framework

This environment uses Spec-Driven Development with multi-agent orchestration.

### Automatic Context Loading

At the start of every session:

1. If `.specs/steering/` exists in the current project, read all files in it.
2. If working on a feature, read all files in `.specs/features/<feature-name>/` including `.spec-state.json`.
3. If `.spec-state.json` exists and has a `phase` value, resume from that phase.

### Phase Gates

Requirements → Design → Tasks → [Consistency Check] → Implementation.
Each phase requires explicit user confirmation before advancing.
The consistency check runs automatically after tasks are confirmed — no extra user action needed,
but a FAIL blocks implementation until resolved.
Never start implementation if any prior phase is unconfirmed.

### Agent Ownership

- orchestrator: coordinates lifecycle, never writes content or code
- requirements-agent: owns requirements.md exclusively
- design-agent: owns design.md exclusively
- tasks-agent: owns tasks.md exclusively
- spec-consistency-checker: read-only cross-document auditor; fires after tasks confirmed, before implementation; receives no planning context
- task-executor: implements one task at a time, worktree-isolated
- task-tester: writes tests for one task, never modifies implementation
- task-validator: validates against requirements, read-only, returns pass/fail

No agent modifies another agent's artifact.

### Key Commands

- Start a feature: "New feature: <description>"
- Resume work: "Resume feature: <feature-name>"
- Initialize project structure: `/sdd-init`
- Scaffold a new feature: `/sdd-feature <feature-name>`

### Feature Completion

When all implementation tasks for a feature are complete, ask the user:
> "Feature complete. Would you like to review the results, or run `/clear` to start fresh for the next feature?"

### Writing Rules

- All spec artifacts are written in English.
- Requirements use EARS syntax (FR-N, NFR-N).
- Every task references at least one requirement.
- Every requirement traces to at least one design component.
