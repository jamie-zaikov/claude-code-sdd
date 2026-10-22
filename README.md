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
  sdd-overnight.md        # /sdd-overnight <name> [on|off|status] — unattended implementation run

tools/                    # Mechanical checks the agents run (installed to ~/.claude/tools/)
  sdd-module-size.py      # "No god files" ratchet: a file over the limit may not grow
  sdd-status.py           # Specialist status files: atomic `set`, schema/staleness `check`
  sdd-park.py             # Park/unpark a halted task's work (github-agent); never records a foreign stash
  sdd-context-pack.py     # One task's cited spec text + a NOT FOUND list, instead of the whole folder
  sdd-overlap.py          # Level 1 stage overlap: speculative worktree for task N+1 during N's reviews

hooks/                    # Secret-handling safeguards (installer opt-in — see hooks/README.md)
  secret-guard.py         # PreToolUse (Bash|PowerShell): blocks secret dumps, allows sanctioned use
  secret-redact.py        # PostToolUse (Bash|PowerShell): scrubs secret-shaped strings from output

install.py, uninstall.py  # All installer logic (stdlib Python >= 3.9), core in sdd_install/
install.sh, uninstall.sh  # Thin shims (macOS, Linux, Git Bash): find Python, run the .py
install.ps1, uninstall.ps1 # Thin shims for Windows PowerShell / pwsh
scripts/find-python.sh    # The interpreter-resolution order: python3, py -3, python

ci-templates/             # CI enforcement layer — distributed by /sdd-init, dogfooded in .github/
  workflows/
    sdd-secret-scan.yml     # Fails the check when a secret is detected in the diff
    sdd-review-gate.yml     # Requires ready-to-merge + no blocked:* label on PRs to main
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
  Opus for every planning, implementation, and review agent (the executor runs Opus on every
  attempt, first and retry alike), Sonnet only for the scribes (github-agent, vault-reader,
  vault-writer), which never author content.
- Python 3.9 or later. The installer itself is Python; the shims look for `python3`, then the
  Windows launcher `py -3`, then `python`.
- Windows (native): Windows 10 1809 or later; **Git for Windows recommended** (Claude Code's Bash
  tool is Git Bash; without it the PowerShell tool is the only shell tool). See
  [Windows](#windows).

## Install

```bash
git clone <repo-url> sdd-global
cd sdd-global
./install.sh            # or: bash install.sh
```

Or if you downloaded the archive:

```bash
tar xzf sdd-global.tar.gz
cd sdd-global
./install.sh
```

The installer will:

1. Copy all 13 agents to `<claude home>/agents/`, the slash commands to `commands/`, the
   playbooks (`playbooks/*.md`, when the checkout has them) to `playbooks/`, and the agent tools to
   `tools/`
2. Install the global CLAUDE.md
   - If you already have one, it offers to overwrite, append, or skip
3. Offer the secret-handling safeguards: `permissions.deny` rules plus the guard/redact hooks in
   `settings.json` (backup written, idempotent, verified — see [`hooks/README.md`](hooks/README.md))
4. Offer the SDD CI pre-push hook for this repository
5. Check if `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set
   - Offers to add it to your shell profile if missing
6. Print VS Code settings.json recommendations

**Destination.** `<claude home>` is `--claude-home PATH` if given, else `$CLAUDE_CONFIG_DIR`, else
`~/.claude` (on Windows `%USERPROFILE%\.claude`). `uninstall` uses the same rule.

**Non-interactive.** `./install.sh --yes` enables the safeguards and the pre-push hook, keeps a
differing CLAUDE.md, and never edits a shell profile. Override any step with `--no-hooks`,
`--no-pre-push`, `--claude-md overwrite|append|skip`, `--shell-profile`. `./install.sh --help`
lists every flag. `python3 install.py --verify` re-checks an installed copy.

**Exit status.** If you enable the safeguards and they cannot be installed and verified (no Python
3.9+, malformed `settings.json`, a failed write, a hook that fails its self-test), the installer
prints `NOT PROTECTED` and exits non-zero. It never prints a warning and then reports success.

### Windows

Prerequisites: Windows 10 1809+, Python 3.9+ (python.org installer or `winget install
Python.Python.3.12`; the `py` launcher is enough), Git for Windows recommended.

```powershell
cd sdd-global
powershell -ExecutionPolicy Bypass -File .\install.ps1
# or, from Git Bash:  ./install.sh
```

Both shims run the same `install.py`. The hooks register for `Bash|PowerShell`, in exec form with
absolute paths, so a user name with a space works.

**Known limit — agent playbooks call `python3`.** Agents and commands run their tools as
`python3 ~/.claude/tools/...` through the Bash tool (Git Bash). Git Bash often has no `python3`
(the python.org installer ships `python.exe` and `py.exe`). Make `python3` resolve in Git Bash,
for example add to `~/.bashrc`: `python3() { py -3 "$@"; }` — or create a `python3` alias of your
interpreter. Native PowerShell execution of the SDD playbooks is not supported. The pre-push hook
and `scripts/ci.sh` already fall back to `py -3` / `python` on their own.

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
5. **Classification** — right after the consistency check passes, you declare the track: a normal
   **code** feature (the default), or a **non-code** feature (a write-up, documentation, a diagram, a
   knowledge-vault update — no application code). The orchestrator records it and routes on it; it is
   never inferred. A non-code feature later found to touch application code reclassifies to code.
6. **Implementation** — per task, the pipeline depends on the track:
   - **code:** a five-stage pipeline `executor → tester → validator → code-reviewer →
     security-reviewer`. The validator checks spec conformance; the two reviewers (which run only
     after the validator passes) hunt the bugs and security holes a requirement-anchored check
     misses. Any blocking review finding sends the task back to the executor on retry.
   - **non-code:** a two-gate pipeline `executor → validator → security scan`. Prose and diagrams
     have no compiler, so the tester and the per-task code-review stage are skipped. Instead each
     task carries a finite `Acceptance:` checklist, and the validator checks exactly it (plus a
     diagram render / lint and a closed coherence rubric); the security-reviewer runs a closed,
     mechanical disclosure/secret scan. A missing unit test is not a failure here.
7. **Feature review** — runs automatically after the last task, before the feature is marked
   complete: code + security over the whole diff on the code track, or one closed-rubric coherence
   pass + the mechanical scan on the non-code track. A blocking finding halts completion until
   resolved or explicitly overridden.

Each planning phase requires your explicit confirmation; the consistency check, the classification
gate, the per-task gates, and the feature review are automatic. The state is saved to
`.spec-state.json` so you can resume anytime.

**Local-first GitHub flow.** The whole lifecycle runs locally — the branch is never pushed and no PR
is opened during the build. Only when the feature review passes does the orchestrator publish: it
pushes the branch, opens the PR **ready** (not draft) already carrying `ready-to-merge` and the
transcribed verdicts, and requests a human review. GitHub only ever sees a finished feature; the
human does the merge.

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
│   ├── sdd-resume.md
│   └── sdd-overnight.md
├── hooks/           # Secret-handling safeguards (installer opt-in)
│   ├── secret-guard.py
│   └── secret-redact.py
└── settings.json    # Machine config: permissions.deny + hook registration
```

Project-level files override global ones if they share the same name. So if a specific project needs a custom orchestrator, put it in `<project>/.claude/agents/orchestrator.md` and it takes priority.

**The main session acts as the Orchestrator — it is never spawned as a nested subagent.** The
Orchestrator file is a playbook the main session reads and follows. This is deliberate: a nested
Orchestrator, frozen inside a blocking call to a specialist that has gone quiet, cannot recover it,
and the whole chain deadlocks (specialist idle → Orchestrator idle → main session idle). Keeping
orchestration in the main loop keeps the recovery tools (`Monitor`, `TaskStop`, `SendMessage`,
`ScheduleWakeup`) at the layer that waits, so a stalled specialist is launched in the background,
watched by its ledger mtime, then killed and respawned once — resuming idempotently from disk. See
the *Execution Model* and *Specialist Execution Contract* in `agents/orchestrator.md`.

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
   strings from Bash and PowerShell output as a backstop.

Layers 1–3 ship in the agents/CLAUDE.md. **Layer 4 (hooks) and the deny list are machine config**
in `settings.json`; the installer sets them up when you opt in (or with `--yes` / `--hooks`) — see
[`hooks/README.md`](hooks/README.md) for the exact entries, the supported protection vectors and
their limits. Regex hooks stop the common dump vectors; they do not stop every exfiltration.

## GitHub integration & CI enforcement

The framework bridges the local SDD lifecycle to GitHub through a single audited choke-point and a
CI layer that re-runs the quality gates server-side.

- **`github-agent` — the remote scribe (local-first).** Built in the exact shape of `vault-writer`,
  `github-agent` is the **only** component that runs `gh` or `git push`. Invoked only by the
  orchestrator, it performs the git/remote mechanics — create/switch branches, make **local commits**
  during the build, and at the single publish point push, open the PR, transcribe existing
  validator/reviewer verdicts verbatim, and set the `ready-to-merge` label. It is a scribe, not an
  author: it never invents content, never judges quality, and **never merges**. Tokens are used,
  never read — `gh` reads `GH_TOKEN` / `GITHUB_TOKEN` by name, and a missing token triggers a
  `SECRET REQUEST` halt (same "use, don't read" discipline as the secret-handling layer above). The
  `secret-guard.py` hook additionally blocks GitHub-token dump vectors (e.g. `gh auth token`,
  `printenv GH_TOKEN`) while leaving sanctioned `gh` use untouched.

- **Local-first — the remote is touched once.** The branch stays local through the whole build; every
  planning confirmation and per-task pass is a local commit, and verdicts accumulate in `spec-memory/`
  and the commit messages. A blocking finding halts locally — no PR, so no `blocked:*` label. Only at
  the whole-feature-review PASS does the orchestrator publish: push the branch, open the PR **ready**
  (not draft) already carrying `ready-to-merge` and the transcribed verdicts, and request a human
  review. GitHub only ever sees a finished feature.

- **Human merge gate.** Merge to a protected branch (`main`) is always a **human** action — no agent
  merges. It is gated by the `ready-to-merge` label, which the orchestrator has `github-agent` apply
  **only** at the publish point, after the whole-feature review passes.

- **Three CI workflow gates** (`ci-templates/workflows/`), each its own file so a future gate slots
  in without touching the others:
  - **`sdd-secret-scan`** — runs the shared scanner (`ci-templates/scripts/sdd-secret-scan.py`) over
    the changed diff and fails the check when a secret is detected, reporting each match by type and
    `path:line`, never the value. The scanner supports an inline `pragma: allowlist secret`
    suppression (which drops only its own line) and an explicit path-exclude list for the framework's
    own pattern/fixture files, so its detection stays tight without false positives on itself.
  - **`sdd-review-gate`** — runs on pull requests to `main` and **fails unless the `ready-to-merge`
    label is present and no `blocked:*` label remains**. This is the server-side backstop to the
    human merge gate. **Branch protection on `main` must require the `sdd-review-gate` check** — the
    job's `name:` is `sdd-review-gate` so the required-check name can be pinned exactly.
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
./uninstall.sh            # Windows: powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

Removes only what the installer owns: the files it copied (recorded with their hashes in
`.sdd-install-manifest.json`; a file you changed since is kept), the two hook entries, and the deny
rules it added (rules you had before stay). It reports what it keeps: `CLAUDE.md` (remove SDD
sections manually if needed), the `settings.json` backups, and any repo pre-push hook. Same
`--claude-home` / `--yes` flags as the installer. An install made by the old `install.sh` has no
manifest; then only files identical to this checkout are removed.

## Tips

- **Start fresh sessions between phases.** The `.spec-state.json` carries progress. Don't run the whole lifecycle in one conversation — that's how you get context rot.
- **Use `/compact` aggressively.** When context fills past 50%, compress.
- **Opus for authors and judges, Sonnet for scribes.** Model tiering ships in each agent's `model:` frontmatter: Opus for requirements, design, tasks, execution, testing, validation, and review; Sonnet for github-agent, vault-reader, and vault-writer. The executor is never downgraded, so every commit in a build carries the same attribution. Override per agent by editing its frontmatter.
- **Sequential accumulation, shared checkout.** SDD tasks run strictly one executor at a time and are mutually dependent, so the task-executor runs in the shared feature-branch checkout (no `isolation: worktree`) and each task builds on the prior task's committed output. Worktree isolation only helps *parallel* agents, which this pipeline never runs — if you ever add parallel task execution, re-introduce isolation for those tasks only (and fork the worktree from the feature branch, not `main`). For manual parallel work outside the pipeline: `claude --worktree task-3-api`.
- **Never paste secrets into the chat.** Provision them via a shell `export` or a gitignored `.env`; agents reference them by env-var name and escalate with `SECRET REQUEST` when one is missing. See [Security & secret handling](#security--secret-handling).
- **Keep the knowledge vault out of the main session.** If your project has a large curated Obsidian/markdown vault, never read it into the orchestrator. Set its root under "Knowledge Vault" in `.specs/steering/tech.md`; the orchestrator brokers all access through `vault-reader` (reads → distilled report on disk) and `vault-writer` (the only writer). The bulk content lives and dies in the subagent's context, so the main session never bloats.
