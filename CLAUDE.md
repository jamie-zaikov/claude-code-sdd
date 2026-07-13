# Global Instructions — Spec-Driven Development

## SDD Framework

This environment uses Spec-Driven Development with multi-agent orchestration.

### Automatic Context Loading

At the start of every session:

1. If `.specs/steering/` exists in the current project, read all files in it.
2. If working on a feature, read all files in `.specs/features/<feature-name>/` including `.spec-state.json`.
3. If `.spec-state.json` exists and has a `phase` value, resume from that phase.

### Feature Workspace: input-data and spec-memory

Every scaffolded feature has two gitignored working folders alongside its spec documents (each keeps a tracked `README.md`; all other contents are ignored):

- `.specs/features/<feature-name>/input-data/` — where the **user** drops source material the feature needs: reference docs, exports, sample payloads, screenshots, config dumps. Look here first for inputs before asking the user to paste them. Read from it freely; never delete what the user dropped.
- `.specs/features/<feature-name>/spec-memory/` — where **you and every agent** write **non-functional artifacts**: anything that is not a spec document (requirements/design/tasks), not application code, and not user input. Request/email drafts, investigation notes, decision logs, ad-hoc summaries, throwaway analysis all go here.

Rule: never scatter non-functional artifacts into the repo root or working tree (e.g. a top-level `NETWORK-ACCESS-REQUEST.md`). If there is an active feature, write them under that feature's `spec-memory/`. Because both folders are gitignored, these artifacts stay out of commits and out of the repo root by default.

### Phase Gates

Requirements → Design → Tasks → [Consistency Check] → Implementation → [Feature Review] → Complete.
Each planning phase requires explicit user confirmation before advancing.
The consistency check runs automatically after tasks are confirmed — no extra user action needed,
but a FAIL blocks implementation until resolved.
Never start implementation if any prior phase is unconfirmed.

Within Implementation, every task runs a five-stage pipeline:
Execute → Test → Validate → Code Review → Security Review. The two reviews run automatically
after the validator passes; any blocking finding sends the task back to the executor on retry.
After the last task, a whole-feature review (code + security, over the full diff) runs automatically
before the feature is marked complete — a blocking finding there halts completion until resolved or
explicitly overridden. Validation checks spec conformance; the reviews hunt the bugs and security
holes a requirement-anchored check misses by construction.

### Agent Ownership

- orchestrator: coordinates lifecycle, never writes content or code
- requirements-agent: owns requirements.md exclusively
- design-agent: owns design.md exclusively
- tasks-agent: owns tasks.md exclusively
- spec-consistency-checker: read-only cross-document auditor; fires after tasks confirmed, before implementation; receives no planning context
- task-executor: implements one task at a time, worktree-isolated
- task-tester: writes tests for one task, never modifies implementation
- task-validator: validates against requirements, read-only, returns pass/fail
- code-reviewer: adversarial correctness/robustness/maintainability review, read-only, returns pass/fail; runs per task and over the whole feature diff, after the validator passes
- security-reviewer: security review (authz, secrets, injection, unsafe defaults, network/cloud exposure), read-only, returns pass/fail; runs per task and over the whole feature diff, after the validator passes
- vault-reader: read-only knowledge-vault interface; reads in isolation, returns a distilled report
- vault-writer: the only component that writes to the knowledge vault; a scribe, never an author

No agent modifies another agent's artifact.

### Knowledge-Vault Isolation

When a project keeps a curated knowledge vault (Obsidian/markdown), the vault is never read into
context directly by anyone — not the main session, the orchestrator, or the specialists. That
would flood whichever context did the reading. All access is brokered through two leaf subagents:

- Reads go through **vault-reader**, which distills its findings to a report file and returns only
  a summary plus the path. Raw notes stay in the subagent's context and are discarded.
- Writes go through **vault-writer**, the single audited choke-point for vault mutations.
- The default vault path lives in steering (`tech.md`); the invoker may override it per call.

There are two ways a vault read is triggered, by two different invokers:

- **Manual (main session).** Any time the user asks to consult a vault — e.g. "consult the lynx
  vault for the worktable variable rules" — the main session invokes vault-reader directly (it
  has the Agent tool). Resolve the named vault from steering's `Knowledge Vault` entry; if it is
  ambiguous or unset, ask. During scoping, fold the returned facts into `scope.md` (under *Open
  questions resolved* / *Sources consulted*) and cite the report path so the whole pipeline
  inherits them. Outside scoping, just surface the tl;dr and keep the report path on hand.
- **On-demand (orchestrator).** A specialist (requirements/design/tasks) that needs vault facts
  not present in its inputs does NOT guess — it halts and returns `VAULT REQUEST: <need>`. The
  orchestrator fulfils it via vault-reader and re-invokes the specialist with the report path.

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
