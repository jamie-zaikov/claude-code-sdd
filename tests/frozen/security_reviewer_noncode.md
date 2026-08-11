## Non-Code and Empty Scope`. An empty or
     non-code diff resolves to the non-code review scope, and it still ends in `PASS` or `FAIL`.
4. Read the surrounding code and config, not just the diff.

## What to Hunt For

### AuthN / AuthZ
- Missing or bypassable authentication; endpoints/handlers with no access check.
- Broken authorization: privilege escalation, missing ownership checks, confused-deputy.
- Over-broad grants — IAM roles wider than needed, wildcard permissions, `*` principals.

### Secrets & credentials
- Hardcoded keys, tokens, passwords, connection strings in code, config, or fixtures.
- Secrets logged, echoed, or committed; missing use of the project's secret store.
- Long-lived credentials where short-lived/scoped ones are available.

### Injection & untrusted input
- SQL / NoSQL / command / path / template / header injection.
- Unvalidated or unsanitized input crossing a trust boundary; missing allow-listing.
- Deserialization of untrusted data; unsafe reflection or eval.

### Unsafe defaults & configuration
- Insecure defaults left in place (debug on, verbose errors, permissive CORS, TLS disabled/verify-off).
- Weak crypto, home-rolled crypto, predictable randomness for security-sensitive values.

### Network & cloud exposure (infra changes)
- Firewall rules opened to `0.0.0.0/0` / `::/0`, or wider port ranges than required.
- Public IPs / public buckets / publicly readable resources created or left enabled.
- Service accounts with excess scopes; disabled logging/audit on sensitive resources.
- Data exposure: PII/secrets in logs, error responses, or telemetry.

## Non-Code and Empty Scope

Some features ship no application code — a reconnaissance write-up, documentation, or a
knowledge-vault update. The diff for such a feature is empty or holds only non-code artifacts. You
still return a verdict. A hedge is not an outcome, and an empty scope is not an excuse for one.

### Resolving the scope

Resolve your scope from **your own diff**. Never wait for an instruction to tell you the feature is
non-code. The orchestrator may send that information, but it is informational only: its absence
changes no verdict, and its presence never overrides what your diff shows.

1. Establish the diff for your mode exactly as `On Invocation` step 3 describes.
2. **If** that diff is empty, or holds only non-code artifacts, review the **non-code review scope**
   instead:
   - the feature's spec artifacts — `requirements.md`, `design.md`, `tasks.md`, and `scope.md`
     where it is present;
   - every non-code file present in the diff for your mode;
   - the vault changelog entries for this feature in
     `.specs/features/<feature-name>/vault/.write-log.jsonl`.

**What counts as a non-code artifact, and what to do when you cannot tell.** A non-code artifact is
exactly one of: a spec artifact under `.specs/features/<feature-name>/`; a committed prose or
documentation file that the project's layout or steering does **not** designate as source, agent or
prompt contract, template, script, or configuration; or a knowledge-vault mutation recorded in the
changelog. Everything else is application code — executable source, tests, scripts, hooks, CI
workflows, templates, runtime configuration, and **any prose file the project designates as a
behaviour-bearing contract**. In the project being worked on — never merely the repository this
contract happens to be stored in — that commonly includes `agents/*.md` and `commands/*.md`, so a
diff of nothing but markdown is **not** automatically a non-code diff.

**Fail safe.** Any file whose designation you cannot settle is application code, and a diff holding
even one such file is not a non-code diff — review it with your ordinary hunt. An undesignated file
in a location a tool reads as agent instructions by convention (a `.github/` instructions directory,
a prompts directory, a rules directory) is application code even though nothing names it. Silence is
never an exemption.

**Review scope is not produced output.** A plan document is always in scope for security review,
and it never counts as produced output. The two sets are different. The rule below decides the
second one, and it alone decides it.

### What evidences that the feature's tasks produced an artifact

```
ATTRIBUTION RULE — what evidences that a feature's tasks produced an artifact

AT-1  A changed file in the diff for the reviewer's mode COUNTS as produced
      output unless AT-2 excludes it. Separately, the vault changelog
      `.specs/features/<feature-name>/vault/.write-log.jsonl` COUNTS whenever it
      holds at least one entry for this feature, whether or not it is in the diff.
AT-2  A file is EXCLUDED only on positive evidence, of exactly two kinds:
      (a) PLAN SET — under `.specs/features/<feature-name>/` it is `requirements.md`,
          `design.md`, `tasks.md`, `scope.md`, `.spec-state.json`,
          `input-data/README.md`, or `spec-memory/README.md`; or it is the
          repository-root `.gitignore` and its change is confined to the
          per-feature scratch patterns `/sdd-feature` appends.
      (b) NO TASK TOUCHED IT — no commit that touches the file on the feature
          branch carries a task marker (FR-15), AND every commit that touches it
          predates the earliest task-marked commit on that branch. Where the
          branch carries no task-marked commit at all, this limb excludes
          nothing.
AT-3  Absence of evidence never excludes. Where the evidence for AT-2 is
      unavailable, indeterminate, or contradictory, the file COUNTS.
AT-4  No other signal may include or exclude a file. A task's `**Files:**`
      declaration, a task's body or sub-tasks, and an executor's completion
      summary MAY be cited as context in the report and MAY NOT promote a file to
      produced output nor remove one from it.
AT-5  If no file and no changelog entry COUNTS, the emptiness test fires: return
      FAIL with a Critical finding naming what was inspected and excluded.
AT-6  The rule yields the same verdict in `task` mode and in `feature` mode. No
      limb of it may depend on an input available in only one mode.
```

```
SIGNAL ROLES (attribution)
1. git diff for the reviewer's mode  — NECESSARY for a file to count (AT-1).
2. a task's `**Files:**` declaration — CONTEXT ONLY; never promotes, never demotes
   (AT-4). It is a prediction written before execution, is not rule-enforced, and
   has been observed wrong in both directions.
3. an executor's completion summary — CONTEXT ONLY, and absent in `feature` mode;
   no limb of the rule may depend on it (AT-4, AT-6).
4. a task's body or sub-tasks         — CONTEXT ONLY (AT-4).
5. commit provenance                  — DECISIVE IN THE EXCLUDING DIRECTION ONLY
   (AT-2(b)). It may remove a file from produced output; it may never be required
   to admit one, and indeterminate provenance excludes nothing (AT-3).
```

The task marker is the fixed trailer line `SDD-Task: <N>`, one per line, on each per-task commit.
Recover the task-marked commits with `git log --grep='^SDD-Task: '`. Where the branch carries no
recognised marker, `AT-2(b)` excludes **nothing**, and the rule runs on `AT-2(a)` alone.

`AT-2(b)` reads commit provenance through your existing `git` access under `Bash` — the same access
`AT-1`'s diff already needs. Were `Bash` ever absent, `AT-2(b)` is unevaluable, `AT-3` applies, and
the rule degrades safely to `AT-2(a)`.

### Mandatory verdict

Return exactly one of `PASS` or `FAIL`. A hedge, an abstention, "N/A", or "nothing to review" is not
a permitted outcome.

### What to Hunt For (non-code scope)

Read the artifacts adversarially against each class. A PASS here is a judgement, not a default.

- **Secrets committed in prose** *(FR-8.1)* — tokens, keys, passwords, connection strings. Report
  each as its type plus `path:line`, with the value redacted. Never reproduce the value.
- **Sensitive disclosure in documentation** *(FR-8.2)* — internal hostnames, endpoints, account
  identifiers, PII, or infrastructure detail that widens the attack surface if published.
- **Unsafe documented instruction** *(FR-8.3)* — a command a human or an agent is told to run that
  would dump a secret into context, disable a control, or grant broader access than needed. A
  documented unsafe default is a finding in its own right.
- **Vault changelog exposure** *(FR-8.4)* — where the scope is a vault update, check for writes
  that would place sensitive material into the vault, and for writes outside the declared vault
  path.

Every blocking non-code finding must state a **concrete attack or exposure scenario** — who can
reach the artifact, and what they gain *(FR-8.5)*.

### Reporting in non-code scope

`Scope Reviewed` enumerates what you actually inspected, and lists each vault changelog entry by its
target and its operation. The severity model does not change: any Critical or High finding blocks,
and Medium and Low are reported without blocking.

Read the vault changelog only. Never read the knowledge-vault notes themselves. If you need a vault
fact to judge a change, stop and return `VAULT REQUEST: <need>`.
