# SDD Global — Spec-Driven Development for Claude Code

Install once, use in every project. Kiro-style SDD workflow for Claude Code's terminal mode in VS Code.

## What's Included

```
agents/
  orchestrator.md             # Lifecycle coordinator — the only user-invocable agent
  requirements-agent.md       # Owns requirements.md, EARS syntax
  design-agent.md             # Owns design.md, requirement traceability
  tasks-agent.md              # Owns tasks.md, hierarchical task breakdown
  spec-consistency-checker.md # Read-only cross-document auditor, runs before implementation
  task-executor.md            # Implements one task, in the shared feature-branch checkout
  task-tester.md              # Writes tests for one task
  task-validator.md           # Validates implementation + tests against requirements, pass/fail
  code-reviewer.md            # Adversarial correctness/robustness review, per task + whole feature
  security-reviewer.md        # Security review (authz, secrets, injection, cloud exposure)
  vault-reader.md             # Read-only knowledge-vault interface, distills to a report
  vault-writer.md             # The only writer to the knowledge vault, audited choke-point
  github-agent.md             # The only writer to the remote (branches/PRs/labels), audited choke-point

commands/
  sdd-init.md             # /sdd-init — scaffold .specs/ in any project
  sdd-feature.md          # /sdd-feature <name> — create a new feature spec
  sdd-status.md           # /sdd-status — show progress across all features
  sdd-resume.md           # /sdd-resume <name> — resume work on a feature

hooks/                    # Secret-handling safeguards (installed manually — see hooks/README.md)
  secret-guard.py         # PreToolUse: blocks secret dumps, allows sanctioned use
  secret-redact.py        # PostToolUse: scrubs secret-shaped strings from Bash output

ci-templates/             # CI enforcement layer — distributed by /sdd-init, dogfooded in .github/
  workflows/
    sdd-secret-scan.yml     # Fails the check when a secret is detected in the diff
    sdd-build-test-lint.yml # Runs the project's build/test/lint entrypoint
  scripts/
    sdd-secret-scan.py      # Shared scanner — same code the pre-push hook runs locally
  hooks/
    pre-push                # Advisory local fast-feedback hook (mirrors the CI gates)

CLAUDE.md                 # Global instructions loaded in every session

steering-templates/       # Reference copies of default steering files
  product.md
  tech.md
  structure.md
```

## Requirements

- Claude Code v2.1.32 or later (`claude --version`)
- VS Code with the Claude Code extension (by Anthropic)
- Opus 4.6 or later (for agent team orchestration). Agents are model-tiered via `model:` frontmatter:
  Opus for planning (requirements, design) and for review (code-reviewer, security-reviewer — never
  downgraded, since a missed defect is a silent failure), Sonnet for the rest. The task-executor
  escalates to Opus automatically on a retry after a validator failure.
- Python 3 on `PATH` — only if you enable the secret-handling hooks (see below).

## Install

```bash
git clone <repo-url> sdd-global
cd sdd-global
chmod +x install.sh
./install.sh
```

Or if you downloaded the archive:

```bash
tar xzf sdd-global.tar.gz
cd sdd-global
chmod +x install.sh
./install.sh
```

The installer will:

1. Copy all 13 agents to `~/.claude/agents/`
2. Copy all 4 slash commands to `~/.claude/commands/`
3. Install the global CLAUDE.md to `~/.claude/CLAUDE.md`
   - If you already have one, it offers to overwrite, append, or skip
4. Check if `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set
   - Offers to add it to your shell profile if missing
5. Print VS Code settings.json recommendations

> The installer does **not** set up the secret-handling hooks or `permissions.deny` rules — those
> are machine-level config in `~/.claude/settings.json`. Enable them separately following
> [`hooks/README.md`](hooks/README.md). See [Security & secret handling](#security--secret-handling).

## After Install

### 1. Set your VS Code settings

Open VS Code settings (Cmd+, or Ctrl+,) and add:

```json
{
  "claudeCode.useTerminal": true,
  "claudeCode.environmentVariables": [
    {
      "name": "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
      "value": "1"
    }
  ]
}
```

### 2. Restart your terminal

Source your shell profile or open a new terminal so the environment variable takes effect:

```bash
source ~/.zshrc    # or ~/.bashrc, depending on your shell
```

### 3. Verify

```bash
claude --version
# v2.1.32 or later

echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
# 1
```

## Usage

### First time in a new project

```
claude
> /sdd-init
```

This creates `.specs/steering/` with template files and `.specs/features/` for your specs. Fill in the steering templates with your project's context.

### Start a feature

```
> /sdd-feature user-auth
```

Or just say:

```
> New feature: user authentication with email and OAuth
```

### Review the workflow

The orchestrator walks you through:

1. **Requirements** — clarifying questions, then EARS-format requirements → you confirm
2. **Design** — architecture with requirement traceability → you confirm
3. **Tasks** — hierarchical task list with testing sub-tasks → you confirm
4. **Consistency check** — runs automatically after tasks are confirmed. An independent, read-only
   auditor cross-checks requirements ↔ design ↔ tasks ↔ steering. A FAIL blocks implementation
   until the flagged issues are resolved; no extra action needed on PASS.
5. **Feature classification** — runs automatically after tasks are confirmed, before
   implementation. The orchestrator classifies the feature as code-bearing or non-code from what its
   tasks declare they will produce, and records it in `.spec-state.json`. On the non-code track the
   tester writes a machine check where one is feasible and otherwise states why none is, the
   validator switches to artifact-conformance mode where a missing unit test is not a failure, and
   both reviewers get a defined verdict for an empty or non-code scope instead of hedging. A
   non-code feature reaches `ready-to-merge` through the **same audited path** as a code feature —
   a real whole-feature review PASS — and **no bypass label exists**. A feature that turns out to
   touch application code falls back to the full code path.
6. **Implementation** — per task, a five-stage pipeline:
   `executor → tester → validator → code-reviewer → security-reviewer`. The validator checks spec
   conformance; the two reviewers (which run only after the validator passes) hunt the bugs and
   security holes a requirement-anchored check misses by construction. Any blocking review finding
   sends the task back to the executor on retry.
7. **Feature review** — runs automatically after the last task, before the feature is marked
   complete. The code-reviewer and security-reviewer review the whole feature diff for
   composition-level issues (integration seams, dead code, cross-task exposure) no per-task pass can
   see. A blocking finding halts completion until resolved or explicitly overridden.

Each planning phase requires your explicit confirmation; the consistency check, the per-task
reviews, and the feature review are automatic gates. The state is saved to `.spec-state.json` so you can resume anytime.

### Resume work

```
> /sdd-resume user-auth
```

Or in a new session:

```
> Resume feature: user-auth
```

### Check progress

```
> /sdd-status
```

## How It Works

Everything installs to `~/.claude/`:

```
~/.claude/
├── CLAUDE.md        # Global — loaded in every session
├── agents/          # Global — available in every project
│   ├── orchestrator.md
│   ├── requirements-agent.md
│   ├── design-agent.md
│   ├── tasks-agent.md
│   ├── spec-consistency-checker.md
│   ├── task-executor.md
│   ├── task-tester.md
│   ├── task-validator.md
│   ├── code-reviewer.md
│   ├── security-reviewer.md
│   ├── vault-reader.md
│   ├── vault-writer.md
│   └── github-agent.md
├── commands/        # Global — available in every project
│   ├── sdd-init.md
│   ├── sdd-feature.md
│   ├── sdd-status.md
│   └── sdd-resume.md
├── hooks/           # Secret-handling safeguards (manual install)
│   ├── secret-guard.py
│   └── secret-redact.py
└── settings.json    # Machine config: permissions.deny + hook registration
```

Project-level files override global ones if they share the same name. So if a specific project needs a custom orchestrator, put it in `<project>/.claude/agents/orchestrator.md` and it takes priority.

Per-project artifacts live in the project repo:

```
<project>/
├── CLAUDE.md               # Project-specific (optional, additive to global)
└── .specs/
    ├── steering/
    │   ├── product.md      # Product context
    │   ├── tech.md         # Stack and conventions
    │   └── structure.md    # Codebase layout
    └── features/
        └── <feature-name>/
            ├── requirements.md
            ├── design.md
            ├── tasks.md
            └── .spec-state.json  # gitignored
```

## Security & secret handling

Agents run with real tools, so a secret they read (a `.env`, an API key, a private key) would
otherwise persist forever in the transcript. The framework treats secret **values** like the
knowledge vault — they never enter context — while still letting agents **use** secrets to do real
work (ssh, authenticated curl, API calls). Four layers, all enforced globally for the main session
**and every subagent**:

1. **Deny reads** — `permissions.deny` in `~/.claude/settings.json` blocks reading known secret
   stores (`.env`, `~/.aws`, `~/.ssh`, `~/.kube`, `~/.config/gcloud`, `service-account*.json`,
   `*.tfvars`, `kubeconfig`, `*.pem`/`*.key`, `.netrc`).
2. **Use, don't read** — agents reference secrets by env-var name (`$TOKEN`, `os.environ`,
   `python-dotenv`) or let a binary read the key (`ssh -i`, `curl --cert`), so the value flows
   through the process, never the transcript. This is the "Secret Handling" section in `CLAUDE.md`
   and in each agent.
3. **`SECRET REQUEST` escalation** — when an agent needs a secret it can't get safely, it halts and
   returns `SECRET REQUEST: <need>` (mirroring `VAULT REQUEST`) rather than guessing or working
   around a block. The operator provisions the env var (shell `export` or a gitignored `.env`) and
   the agent is re-invoked.
4. **Hooks** (`hooks/`) — `secret-guard.py` (PreToolUse) blocks secret *dumps* like `printenv` and
   `cat .env` while allowing sanctioned use; `secret-redact.py` (PostToolUse) scrubs secret-shaped
   strings from Bash output as a backstop.

Layers 1–3 ship in the agents/CLAUDE.md and are installed by `install.sh`. **Layer 4 (hooks) and
the deny list are machine config and must be enabled manually** — see [`hooks/README.md`](hooks/README.md)
for the exact `settings.json` block.

## GitHub integration & CI enforcement

The framework bridges the local SDD lifecycle to GitHub through a single audited choke-point and a
CI layer that re-runs the quality gates server-side.

- **`github-agent` — the remote scribe.** Built in the exact shape of `vault-writer`, `github-agent`
  is the **only** component that runs `gh` or `git push`. Invoked only by the orchestrator, it
  performs the remote mechanics — create/switch branches, commit and push to a feature branch, open
  and update pull requests (as **draft** during active development), transcribe existing
  validator/reviewer verdicts verbatim into PR comments, and set/clear labels. It is a scribe, not
  an author: it never invents content, never judges quality, and **never merges**. Tokens are used,
  never read — `gh` reads `GH_TOKEN` / `GITHUB_TOKEN` by name, and a missing token triggers a
  `SECRET REQUEST` halt (same "use, don't read" discipline as the secret-handling layer above). The
  `secret-guard.py` hook additionally blocks GitHub-token dump vectors (e.g. `gh auth token`,
  `printenv GH_TOKEN`) while leaving sanctioned `gh` use untouched.

- **Human merge gate.** Merge to a protected branch (`main`) is always a **human** action — no agent
  merges. It is gated by the `ready-to-merge` label, which the orchestrator has `github-agent` apply
  **only** after a whole-feature review passes. A blocking finding at any pipeline stage sets a
  `blocked:<stage>` label (`blocked:validation`, `blocked:code-review`, `blocked:security-review`,
  `blocked:feature-review`) and keeps the PR in draft; the label is cleared when the finding is
  resolved.

- **Three CI workflow gates** (`ci-templates/workflows/`), each its own file so a future gate slots
  in without touching the others:
  - **`sdd-secret-scan`** — runs the shared scanner (`ci-templates/scripts/sdd-secret-scan.py`) over
    the changed diff and fails the check when a secret is detected, reporting each match by type and
    `path:line`, never the value. The scanner supports an inline `pragma: allowlist secret`
    suppression (which drops only its own line) and an explicit path-exclude list for the framework's
    own pattern/fixture files, so its detection stays tight without false positives on itself.
  - **`sdd-build-test-lint`** — runs the project's build/test/lint entrypoint (`scripts/ci.sh` if
    present) and fails on any failure.

- **Pre-push hook.** `ci-templates/hooks/pre-push` runs the **same** secret scanner and
  build/test/lint entrypoint locally before a push and blocks the push (non-zero exit) on failure,
  naming the failing check. It is the advisory fast-feedback layer; **CI mirrors — never replaces —
  the local gates**: even if the hook is absent or bypassed with `--no-verify`, the identical checks
  run in CI as the mandatory backstop.

- **Distribution & dogfood.** `/sdd-init` drops the workflow templates into a downstream project's
  `.github/workflows/` and makes the pre-push hook available, appending missing files without
  overwriting existing ones (idempotent, non-destructive). `install.sh` optionally installs the
  pre-push hook into the current repo. This repository dogfoods the same layer in its own
  [`.github/`](.github/).

## Uninstall

```bash
cd sdd-global
chmod +x uninstall.sh
./uninstall.sh
```

Removes agents and commands. Leaves `~/.claude/CLAUDE.md` intact (remove SDD sections manually if needed).

## Tips

- **Start fresh sessions between phases.** The `.spec-state.json` carries progress. Don't run the whole lifecycle in one conversation — that's how you get context rot.
- **Use `/compact` aggressively.** When context fills past 50%, compress.
- **Opus for planning, Sonnet for execution.** Model tiering ships in each agent's `model:` frontmatter: Opus for requirements/design, Sonnet for tasks/execution/validation. The task-executor auto-escalates to Opus on a retry after a validator failure. Override per agent by editing its frontmatter.
- **Sequential accumulation, shared checkout.** SDD tasks run strictly one executor at a time and are mutually dependent, so the task-executor runs in the shared feature-branch checkout (no `isolation: worktree`) and each task builds on the prior task's committed output. Worktree isolation only helps *parallel* agents, which this pipeline never runs — if you ever add parallel task execution, re-introduce isolation for those tasks only (and fork the worktree from the feature branch, not `main`). For manual parallel work outside the pipeline: `claude --worktree task-3-api`.
- **Never paste secrets into the chat.** Provision them via a shell `export` or a gitignored `.env`; agents reference them by env-var name and escalate with `SECRET REQUEST` when one is missing. See [Security & secret handling](#security--secret-handling).
- **Keep the knowledge vault out of the main session.** If your project has a large curated Obsidian/markdown vault, never read it into the orchestrator. Set its root under "Knowledge Vault" in `.specs/steering/tech.md`; the orchestrator brokers all access through `vault-reader` (reads → distilled report on disk) and `vault-writer` (the only writer). The bulk content lives and dies in the subagent's context, so the main session never bloats.
