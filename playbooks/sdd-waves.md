# SDD playbook — two-task waves

The orchestrator reads this file when `tech.md` declares `Task waves: 2` and two tasks are
eligible. It is the one normative definition of the wave procedure; `agents/orchestrator.md` links
here. The mechanics live in `~/.claude/tools/sdd-wave.py`; every mutating step runs through
**github-agent** (`wave-*` actions), and the read-only steps (`check`, `status`, `spec-rev`) the
orchestrator runs directly.

## 1. Eligibility — mechanical, never a question

Run a wave of tasks A < B (tasks.md order) only when **all** hold; otherwise run them in sequence:

1. `tech.md` declares `Task waves: 2`. Absent means off.
2. Code track; neither task mutates a live system; neither is `deferred`.
3. Both are dependency-ready (every task each `Depends:` line names is `complete`), and neither
   depends on the other. A task without a `Depends:` line depends on every earlier task, so it is
   never in a wave as task B.
4. Their declared sets are disjoint: `Files:` ∪ `Shared:` of A against those of B, as paths and
   directory prefixes (`dir/` covers everything under it).
5. Neither task changes the shared environment: no manifest or lockfile on its `Files:`/`Shared:`
   (`pyproject.toml`, `requirements*.txt`, `*.lock`, `package.json`, `go.mod`, `Cargo.toml`, …),
   no install step, no regenerated ignored artifact the tests read. Tests that use a shared external
   resource (database, port, device, a cache outside the worktree) are ineligible unless `tech.md`
   says `Wave-isolated tests: yes`.
6. The main checkout is clean outside `.specs/`, no Level 1 speculation exists, and no wave exists.

While a wave exists: **no Level 1 speculation starts, and no wave task is parked with `park`** —
a halt inside a wave goes to the fallback (§6), and the sequential run parks normally if it must.

## 2. Start

github-agent `wave-start` → `sdd-wave.py start --feature <f> --tasks A,B --attempt <k>
--own A=<A's Files ∪ Shared> --own B=<B's>` (each entry a plain repo-relative path or directory —
expand any glob or `{a,b}` group from tasks.md into plain paths or their common directory), where `k` is one more than the larger `retryCount` of
the two. Record `wave: { tasks, base, attempt }` in the state file. On resume, read
`sdd-wave.py status` before anything else.

## 3. Execute and test in isolation

0. **Per-task preparation, as in the sequential pipeline:** for each task build its context pack,
   list its routed findings (`sdd-findings.py list --routed-to <N>`), pass its `prototype:` patch if
   one exists, and record the launch in the timing ledger. After each executor returns, apply the
   `MATERIAL CHANGE` check and the RT-3 / classification payload step before its tester runs. Each
   task keeps its own `retryCount`, `attemptTrees` and in-attempt repair rounds
   (`sdd-findings.py round --attempt <that task's retryCount>`); the wave attempt `k` only names refs.
1. Launch both **task-executors** in one message with `worktree: <path>` and `wave: true`. Each
   writes only under its own worktree; targeted tests run with the worktree first on the import
   path (`PYTHONPATH=<worktree>`), or are skipped and said so.
2. After each executor returns, run `sdd-wave.py check --task <N>`. An undeclared path pauses that
   task: if it is unowned and internal to the approved intent, github-agent `wave-extend` and go on
   (record it as an internal reconciliation); if the other task owns it, it is a submodule, or it
   changes the environment, go to the fallback (§6). Never an amendment by itself.
3. Launch both **task-testers** in one message, same worktree rule. Testers remove non-ignored
   junk they create (`.pytest_cache`, coverage output) or the next `check` flags it.
4. **Freeze** each task once its executor and tester have both reported `state: done` (no writer
   may still run): github-agent `wave-freeze --task <N>`. A frozen task is never written again.

## 4. Land and the combined gate

1. github-agent `wave-land`. It builds the candidate from base + A + B (exit 1 on a conflict, a
   stale checkout, or a collision with any file on disk — ignored files included) and writes it into
   the main checkout as uncommitted changes. From here the candidate is ordinary uncommitted work.
2. **Suite, once.** Launch the task-tester of A with `mode: suite-only`: it writes nothing, runs
   the full suite once, and records the tree hash before and after; a different hash voids the
   run. That is the batch's one suite record.
3. **Gates, concurrently, in one message:** task-validator A and B; code-reviewer A and B and
   security-reviewer A and B in `mode: task`, each over its own frozen diff
   (`git diff <base> <refs .../task-<N>>`) with the other task's diff as seam context. All read the
   same tree and share the one suite record. Isolated results from §3 are early evidence only; no
   verdict comes from a worktree.
4. **Evidence record** `spec-memory/waves/<A>-<B>-a<k>.json`: base, both refs, the candidate tree
   hash (`sdd-tree-hash.py`), the spec revision (`sdd-wave.py spec-rev` — blind to checkbox state
   and the state file), the suite command, result and counts, and every verdict.

## 5. Pass, repair, commit

- **Both pass every gate** → github-agent `commit` task A by its explicit paths, then task B by
  its explicit paths (each message ends `SDD-Task: <N>`). Then `wave-verify --gated-tree <the
  candidate tree hash the gates judged>`: exit 1 means a gated path is not in HEAD — halt and report;
  never mark the tasks complete. Then mark both complete and github-agent `wave-discard`.
- **A blocking result** → in-attempt repair (playbook *In-attempt repair*), **one task at a time**,
  never two repair executors at once. Before each repair write, github-agent `wave-snapshot`. The
  repair executor writes only paths its task owns; after each repair run `sdd-wave.py strays` — any
  path it lists is outside both tasks' ownership — a repair out of scope, or a file the user or a
  test run left behind: report it to the user (never touch it) and fall back (§6). After each repair: the suite runs once more
  (`mode: suite-only`), the repaired task's validator re-runs in full, and **all** reviewers of
  both tasks re-run in `mode: delta` over the repair diff (the other task's reviewers judged it as
  seam context). The other task's validator re-runs when the repair touched its requirements' scope
  or the suite result changed; otherwise its verdict is reused with the reason recorded.
- **`STOP`, ineligible repair, or any halt** → the failing task's attempt counts as failed
  (`retryCount += 1`, `blockingHistory` kept, every finding stays in the index) and the wave falls
  back (§6). The task that passed keeps no verdict: it re-gates in sequence.

## 6. Fallback to sequence — never a promise of success

1. Stop writers: wait for completion notices, or `TaskStop` and confirm the stop.
2. If landed: github-agent `wave-unland` (it snapshots first, so repair work is kept in a ref,
   and it restores every path the candidate or a repair touched; files that were untracked before
   the land are never touched).
3. Run A through the normal sequential pipeline. Before its Stage 1, github-agent `wave-adopt
   --task A --patch-out spec-memory/waves/task-A.patch`: on success A's frozen work is in the
   checkout and the executor adapts it; on exit 1 the executor gets the patch file as reference.
   The confirmed task list already authorizes adopting the task's own frozen work. Then B the same,
   on top of A. Every gate runs on what is delivered.
4. github-agent `wave-discard` (refs kept). Record the reason in the evidence record and under
   *Incidents* in the progress report (and the overnight summary). A sequential run can still expose the real incompatibility as a normal failure.

At feature completion github-agent `wave-prune --feature <f>` drops the feature's wave refs.
