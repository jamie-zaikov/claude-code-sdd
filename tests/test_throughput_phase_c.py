#!/usr/bin/env python3
"""Prose-contract tests for pipeline-throughput Phase C — Explore → Promote (round 3).

Phase C codifies the Explore → Promote pilot: the explorer subagent solves a hard problem inside a
scope the user grants once (`exploreAuthority`), one invocation at a time, between tasks only; then
SDD promotes the proven solution through every normal gate. `playbooks/sdd-explore.md` is the one
normative definition, `agents/explorer.md` the explorer's side, and the orchestrator keeps the rules
that bind even without the playbook. Each pin names a rule's key words and direction as separate
terms (`prose.near` refuses a negated match; a rule that really is negative puts the negation inside
its pattern), never a whole sentence with its punctuation, so a pin goes RED when the rule is
removed or inverted and stays GREEN when it is reworded, re-ordered inside a list, or re-wrapped.
Run:
    python3 -m unittest tests.test_throughput_phase_c -v
"""

import unittest
from pathlib import Path

try:
    from tests import prose
except ImportError:  # run from inside tests/
    import prose

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = read("playbooks/sdd-explore.md")
        cls.explorer = read("agents/explorer.md")
        cls.orch = read("agents/orchestrator.md")
        cls.executor = read("agents/task-executor.md")
        cls.tasks = read("agents/tasks-agent.md")
        cls.reqs = read("agents/requirements-agent.md")
        cls.design = read("agents/design-agent.md")
        cls.checker = read("agents/spec-consistency-checker.md")
        cls.waves = read("playbooks/sdd-waves.md")
        cls.resume = read("commands/sdd-resume.md")
        cls.overnight = read("commands/sdd-overnight.md")
        cls.claude = read("CLAUDE.md")
        cls.readme = read("README.md")

    def near(self, text, label, *terms, window=160):
        if not prose.near(text, *terms, window=window):
            self.fail(f"{label}: missing {' … '.join(terms)}")

    def lacks(self, text, pat, label):
        if prose.search(text, pat):
            self.fail(f"{label}: forbidden /{pat}/ present")


class PlaybookScopeAndWhenTest(Base):
    """Honest scope, §1 — a user choice, between tasks only, three window kinds, window entry."""

    def test_honest_scope(self):
        self.near(self.play, "checkpoint", r"Honest scope", r"attended", r"checkpoint-only", window=200)
        self.near(self.play, "mid-task", r"does not solve mid-task discovery", r"discovery and prototype tiers",
                  window=200)
        self.near(self.play, "not a scheduler", r"not a scheduler")
        self.lacks(self.play, r"solves (the )?mid-task discovery", "claims mid-task discovery")

    def test_explore_is_a_user_choice(self):
        self.near(self.play, "choice", r"conversation choice", r"not a mandatory taxonomy", r"The user decides")
        self.near(self.play, "no grant", r"feature without a grant runs exactly as before")
        self.lacks(self.play, r"(may|should|must|shall) infer (it|explore)", "an agent infers Explore")

    def test_between_tasks_only_nothing_parked(self):
        self.near(self.play, "between", r"between tasks only", r"never runs while a\s+task is in progress",
                  r"nothing is parked", window=200)
        self.lacks(self.play, r"park(s|ed)? (the|a) (running|current) task", "parks a task for Explore")

    def test_exactly_three_window_kinds(self):
        self.near(self.play, "kinds", r"Three window kinds, and no other")
        for kind in (r"`before-feature`", r"`before-task-<N>`", r"`after-task-<N>`"):
            self.near(self.play, f"kind {kind}", kind)
        self.lacks(self.play, r"`during-task-<N>`", "a fourth window kind")
        self.lacks(self.play, r"(Four|4) window kinds", "four window kinds")

    def test_before_task_result_follows_the_effect_rule(self):
        self.near(self.play, "effect", r"`before-task-<N>`", r"unaffected accepted\s+baseline stays as it is",
                  r"effect-based rule", r"recorded decision", r"material\s+amendment", window=300)

    def test_evaluation_window_is_evidence_only(self):
        self.near(self.play, "evaluation", r"`after-task-<N>`", r"evaluation run", r"findings are evidence",
                  r"findings index", r"material amendment", window=300)
        for term in (r"evaluation never edits product code", r"never reopens or passes a task",
                     r"never\s+stands in for a gate or for the acceptance probe"):
            self.near(self.play, f"never {term}", term)
        self.near(self.play, "no patch", r"no-change evaluation needs no patch")
        self.lacks(self.play, r"evaluation (may|can) (edit|reopen|pass)", "evaluation acts on a task")

    def test_window_entry_is_mechanical_against_phase_b_state(self):
        self.near(self.play, "entry", r"Window entry", r"mechanical", window=100)
        for cond in (r"no task\s+is `in_progress`", r"clean outside `.specs/`", r"no wave exists",
                     r"no Level 1\s+speculation exists", r"no specialist writer is live"):
            self.near(self.play, f"entry {cond}", r"A window opens only when all hold", cond, window=400)
        self.near(self.play, "no launches", r"While a window is open", r"no task, Level 1\s+overlap or wave launches",
                  window=200)
        self.near(self.play, "before overlap", r"`before-task-<N>` window is requested before task N could start",
                  r"do not start N's overlap", window=200)
        self.lacks(self.play, r"(may|can) open while a (wave|speculation)", "window during a wave")

    def test_provisional_commits(self):
        self.near(self.play, "provisional", r"Provisional commits", r"`awaiting_candidate`", r"`window.provisional`",
                  r"never completes them", r"never replaces their\s+full suite", r"needs no extra full suite to open",
                  r"re-assessed", window=400)
        self.lacks(self.play, r"(Explore|window) (completes|may complete) (them|an `awaiting_candidate`)",
                   "Explore completes a candidate")


class PlaybookGrantTest(Base):
    """§2 — tooling gap first, one wide record, inherited rules, the explorer subagent, the authority."""

    def test_tooling_gap_is_checked_before_the_grant_and_the_user_chooses(self):
        self.near(self.play, "gap", r"tooling.gap", r"does not improvise a route", r"narrow the objective",
                  r"extend the path first", window=400)
        self.near(self.play, "user chooses", r"the user chooses", r"never the agent")
        self.near(self.play, "before", r"before\s+the grant, not after")
        self.lacks(self.play, r"choose the faster option", "agent picks the gap option")

    def test_a_yes_is_recorded_silence_grants_nothing(self):
        self.near(self.play, "ask once", r"Ask once per feature", r"Asking the User", window=200)
        self.near(self.play, "yes", r"A yes is recorded")
        self.near(self.play, "silence", r"silence or the absence of an\s+objection", r"grants nothing")
        self.lacks(self.play, r"absence of an\s+objection,? is recorded", "silence counts as a grant")

    def test_grant_record_has_every_key(self):
        self.near(self.play, "record", r"exploreAuthority: \{", r"grantedBy: \"user\"", r"objective", r"boundary",
                  r"actionPath", r"reconcile", r"forbidden", r"budget", r"cadence", r"explorer", r"decisions",
                  window=400)
        self.near(self.play, "attempts only", r"budget,", r"attempts only in this release", window=100)
        self.lacks(self.play, r"N attempts or H hours", "hours budget offered")
        self.near(self.play, "cadence values", r"\"step\" \(default\)", r"\"continuous\", upTo: N", window=100)

    def test_grant_is_wide_durable_and_never_widened(self):
        self.near(self.play, "wide", r"Wide and durable", r"whole feature", r"several windows", r"one budget",
                  r"valid across sessions", r"budget is spent", r"`complete`", r"user revokes it", window=300)
        self.near(self.play, "never widened", r"never widened by an agent")

    def test_grant_inherits_every_project_rule(self):
        self.near(self.play, "inherit", r"grant never revokes a project rule")
        self.near(self.play, "secret", r"secret handling and the\s+permission deny rules", r"stay in force")
        self.near(self.play, "safeguards", r"removes ceremony", r"not safeguards")

    def test_standing_forbidden_list_is_always_present(self):
        self.near(self.play, "standing", r"Standing forbidden list", r"always in `forbidden`", window=60)
        for item in (r"did not create", r"publishing", r"widening a client guard", r"secret beyond\s+the existing env vars",
                     r"product code in the main checkout", r"hardware"):
            self.near(self.play, f"forbidden {item}", r"Standing forbidden list", item, window=400)
        self.lacks(self.play, r"forbidden list[^.]{0,80}(optional|discretion)", "forbidden list optional")

    def test_explorer_is_the_dedicated_subagent(self):
        self.near(self.play, "actor", r"explorer is the `explorer` subagent", r"clean context", window=120)
        self.near(self.play, "never main", r"never the\s+main session")
        self.near(self.play, "never executor", r"never the task-executor")
        self.near(self.play, "bound", r"allowed \*\*and\*\* bound to run live actions")
        self.near(self.play, "full grant", r"full\s+grant in its prompt")
        for item in (r"objective", r"boundary", r"forbidden", r"standing list", r"budget", r"attempts used",
                     r"cadence", r"recorded decisions"):
            self.near(self.play, f"grant item {item}", r"full\s+grant in its prompt", item, window=300)
        self.near(self.play, "only path", r"only through\s+`actionPath` inside `boundary`")
        self.lacks(self.play, r"By default the\s+(\*\*)?main session", "main session default")
        self.lacks(self.play, r"(user|orchestrator) may name the main session", "main session option")

    def test_relation_to_the_probe_tiers(self):
        self.near(self.play, "tiers", r"Relation to the probe tiers", r"fourth, larger grant",
                  r"implies `prototypeAuthority`", r"through `actionPath` \*\*only\*\*",
                  r"neither tier 2 nor a back door into tier 3", window=400)

    def test_what_the_authority_means(self):
        self.near(self.play, "durable", r"authority is durable", r"no new permission grant is asked per\s+attempt",
                  window=100)
        self.near(self.play, "advances", r"one requested attempt, or one requested bounded sequence, at\s+a time")
        self.lacks(self.play, r"no per-attempt approval", "the old ambiguous phrase")
        self.near(self.play, "uncovered", r"permission the grant does not cover needs a new user decision",
                  r"`exploreAuthority.decisions\[\]`", r"user's\s+words", window=300)
        self.near(self.play, "request", r"`EXPLORE REQUEST: <permission>`", r"carry it to the\s+user", window=100)
        self.near(self.play, "no denial laundering", r"`decisions\[\]` entry never covers a hook block or a `permissions.deny` result",
                  r"never re-run under a recorded decision", window=200)
        self.near(self.play, "overnight grant", r"Overnight mode never grants or widens `exploreAuthority`")
        self.near(self.play, "overnight attempt", r"overnight run starts no Explore\s+attempt")
        self.near(self.play, "attended", r"Explore is attended work")
        self.near(self.play, "narrow", r"Start narrow", r"smallest objective", r"new decision for the user")


class PlaybookWindowTest(Base):
    """§3 — numbering, cadence, reservation, recovery, one writer, the artifacts."""

    def test_status_file_uses_the_invocation_number(self):
        self.near(self.play, "invocation", r"invocation number", r"`invocations\[\"explore-<window>/explorer\"\]`",
                  r"names its status file", window=200)
        self.near(self.play, "attempt id", r"attempt id", r"separate counter", r"only in\s+the log heading and the summary",
                  window=120)
        self.near(self.play, "each adds one", r"`attempt`, a `recover`, a `close` and a respawn each take a new\s+invocation number")
        self.near(self.play, "recover reuses", r"`recover` reuses the attempt id")

    def test_step_cadence_reads_only_the_log_entry(self):
        self.near(self.play, "step", r"`step` \(default\)", r"only that\s+attempt's log entry",
                  r"never the\s+explorer's transcript", r"next attempt starts only on\s+the user's word", window=300)
        self.lacks(self.play, r"orchestrator reads the (explorer's )?(transcript|raw output)", "main reads transcript")

    def test_continuous_cadence_is_bounded_with_mandatory_stops(self):
        self.near(self.play, "continuous", r"`continuous, upTo: N`", r"user asked, in the grant", r"bounded sequence",
                  r"never past the budget", window=300)
        self.near(self.play, "report", r"after every\s+attempt you still give the short report", r"steering")
        self.near(self.play, "stops", r"mandatory stop", r"waits for the user", window=80)
        for stop in (r"boundary or authority change", r"budget or `upTo` reached", r"unknown action outcome",
                     r"open cleanup", r"material decision"):
            self.near(self.play, f"stop {stop}", r"mandatory stop", stop, window=300)
        self.near(self.play, "silence", r"Silence never creates\s+or extends a continuous request")
        self.near(self.play, "overnight", r"Overnight still\s+starts no attempt")
        self.lacks(self.play, r"silence (extends|creates|renews)", "silence extends a sequence")

    def test_attempt_is_reserved_before_dispatch_and_never_freed_by_a_crash(self):
        self.near(self.play, "attempt def", r"An attempt", r"one explorer invocation that issues\s+at least one `actionPath` command",
                  window=60)
        self.near(self.play, "reserve", r"Before", r"each `attempt` launch you reserve", r"`explore.attempts\[\]`",
                  r"\"reserved\"", window=200)
        self.near(self.play, "count", r"`attemptsUsed` counts every entry that is not `released`")
        self.near(self.play, "never freed", r"crash, a kill or a\s+lost result never frees the slot")
        self.near(self.play, "release", r"Only the explorer's written evidence of a setup failure before\s+its first command",
                  r"`released`", window=100)
        self.near(self.play, "uncertain", r"outcome is uncertain", r"`recover` invocation under the same id",
                  r"before any new\s+hypothesis", window=120)
        self.lacks(self.play, r"(?<!never )(?<!never\n)(frees|releases) the slot", "crash frees the slot")

    def test_recovery_is_never_exploration(self):
        self.near(self.play, "recover", r"Recovery is never exploration", r"respawn", r"`recover` invocation",
                  r"no hypothesis", window=600)
        self.near(self.play, "reconcile", r"`reconcile` command", r"recorded ID or ownership", r"never by a name prefix",
                  r"unknown outcome is never re-issued", window=200)
        self.near(self.play, "next attempt", r"next `attempt`\s+needs the user's word", r"active continuous request")
        self.near(self.play, "none", r"`reconcile` is\s+`none` stops on an uncertain outcome")
        self.lacks(self.play, r"respawn[^.]{0,80}(new|next) hypothesis", "respawn runs a hypothesis")

    def test_one_writer_per_artifact(self):
        self.near(self.play, "writers", r"One writer", r"explorer writes the attempt log", r"object ledger",
                  r"every patch\s+and manifest", r"the brief", r"you write only the state file", window=300)
        self.near(self.play, "one at once", r"no two explorer invocations run at once")

    def test_killed_explorer_is_read_from_the_stub(self):
        self.near(self.play, "killed", r"Killed before its entry", r"report from the stub", r"ledger",
                  r"status file's last `step`", r"never from its transcript", r"next invocation is a `recover`",
                  window=300)

    def test_attempt_log_is_append_only_with_a_stub(self):
        self.near(self.play, "log", r"Attempt log", r"`spec-memory/explore/log.md`", r"append-only",
                  r"reservation stub", r"`commands\s+issued`", window=300)
        self.near(self.play, "failed kept", r"Failed attempts are kept", r"negative tests")

    def test_patch_and_manifest_before_the_result_and_manifest_required(self):
        self.near(self.play, "patch", r"Patch and manifest before the result is logged",
                  r"`spec-memory/prototypes/<slug>.patch`", r"before\s+its log entry is completed", window=300)
        self.near(self.play, "manifest", r"<slug>\.manifest\.json`", r"base commit", r"path and hash, or how to rebuild",
                  r"command", window=300)
        self.near(self.play, "contents", r"carries no untracked or binary output", r"never a credential")
        self.lacks(self.play, r"(may|can) carry untracked", "patch may carry untracked output")
        self.near(self.play, "no manifest", r"patch without a\s+manifest beside it is a reference only", r"never applied")
        self.near(self.play, "prose", r"only described in prose\s+cannot be adopted")
        self.near(self.play, "no patch", r"no-change evaluation writes no patch")

    def test_object_ledger_has_states(self):
        self.near(self.play, "ledger", r"Object ledger", r"`spec-memory/explore/ledger.md`", r"ID and type of every object",
                  r"not just a name prefix", window=300)
        self.near(self.play, "states", r"`open`", r"`deleted-verified`", r"`retained-by-user`", r"user's decision recorded",
                  window=120)
        self.near(self.play, "targets", r"Cleanup targets `open` objects only")
        self.near(self.play, "retained", r"retained object is\s+never deleted", r"never repeats the retention")

    def test_evidence_hygiene_covers_command_fields(self):
        self.near(self.play, "scrub", r"Evidence hygiene", r"log, ledger, manifest, brief", r"scrubbed\s+before it is written",
                  r"`command` field", r"env var, never its value", window=400)
        self.near(self.play, "raw", r"Raw captures are deleted the same turn")

    def test_budget_stop_never_widens(self):
        self.near(self.play, "stop", r"Budget stop", r"budget is spent", r"stops and reports", r"`explore.status: spent`",
                  window=300)
        self.near(self.play, "widen", r"Never widen the (budget|boundary)", r"new user decision")

    def test_cleanup_targets_open_objects_and_separates_retained_from_unresolved(self):
        self.near(self.play, "cleanup", r"Cleanup, verified", r"deletion of the `open` objects", r"verified through `actionPath`",
                  r"user asks to keep", r"`retained-by-user`", window=300)
        self.near(self.play, "separate", r"separates\s+\*\*retained\*\* from \*\*unresolved\*\*", r"every progress line")
        self.near(self.play, "visible", r"unresolved object stays a\s+visible open item", r"never dropped")
        self.near(self.play, "halt", r"After a\s+stop-rule halt", r"not `done`", r"first action", r"`recover`", window=300)
        self.lacks(self.play, r"(failed cleanup|unresolved object) (is|may be|can be) (dropped|ignored|closed)", "cleanup dropped")
        self.lacks(self.play, r"keep the ones the\s+explorer judges", "explorer decides retention")

    def test_missing_evidence_is_a_stop(self):
        self.near(self.play, "missing", r"Missing evidence is a stop", r"`attemptsUsed > 0`", r"log or\s+the ledger file is missing",
                  r"cleanup cannot be verified", r"start no attempt", r"declares the boundary\s+clean", window=400)
        self.lacks(self.play, r"ledger[^.]{0,60}missing[^.]{0,60}continue", "missing ledger continues")

    def test_solution_brief_keeps_open_limits_and_closes_the_window(self):
        self.near(self.play, "brief", r"Solution brief", r"`spec-memory/explore/solution-<window>.md`", r"`close`",
                  r"mechanisms that work", r"one line per failure\s+mechanism", r"patch and manifest path",
                  r"open\s+limits", r"never silently relaxed", r"provisional commits", r"evidence, not a spec",
                  window=300)
        self.near(self.play, "close window", r"Closing the window\s+sets `window.closedAt` and `explore.status: closed`")


class PlaybookPromoteTest(Base):
    """§4 — no extra gate, the effect decides, Phase B's candidate stays the unit."""

    def test_no_extra_gate_and_explore_never_confirms(self):
        self.near(self.play, "where accepted", r"No extra gate", r"requirements confirmation",
                  r"confirmation of the affected\s+amendment", window=300)
        self.near(self.play, "ack", r"acknowledgment of the brief alone approves no unseen design")
        self.near(self.play, "never confirms", r"Explore never confirms a planning gate")
        self.lacks(self.play, r"brief (is|counts as) (the|a) (spec|confirmation)", "brief as spec")

    def test_the_effect_decides_decision_or_amendment(self):
        self.near(self.play, "effect", r"The effect decides", r"method the confirmed text\s+already permits",
                  r"recorded decision", r"`spec-memory/decisions.md`", r"not an amendment", window=300)
        self.near(self.play, "material", r"changes acceptance, a `Contract:`, authority", r"material amendment", window=120)
        self.lacks(self.play, r"every (discovery|result) (is|needs|becomes) (a|an) (material )?amendment", "all amendments")

    def test_the_existing_planning_path_with_every_gate(self):
        self.near(self.play, "path", r"existing planning path, every gate", r"Requirements", r"design", r"tasks",
                  r"consistency check", r"classification", r"implementation", r"security-reviewer",
                  r"feature review", window=200)
        self.near(self.play, "amendment", r"only the affected amendment", r"unchanged accepted work is not rewritten")

    def test_brief_reaches_every_planning_agent_as_evidence(self):
        self.near(self.play, "agents", r"brief goes to every planning agent as evidence", r"requirements-agent",
                  r"design-agent", r"tasks-agent", window=200)
        self.near(self.play, "intent", r"intended behaviour and constraints",
                  r"deviations the user accepts\s+at the requirements confirmation",
                  r"not from whatever the experiment produced", window=300)
        self.near(self.play, "limits", r"open limit", r"requirement or an explicitly accepted deviation",
                  r"never dropped\s+in silence")

    def test_phase_b_candidate_stays_the_unit(self):
        self.near(self.play, "unit", r"Phase B's candidate stays the unit", r"integration units",
                  r"not one task per administrative step", r"not one unit per mechanism or per patch",
                  r"traceability", r"several\s+may map to one coherent candidate", window=400)
        self.near(self.play, "owner", r"`\*\*Prototype:\*\* <path>`", r"one owning task applies a patch, never two",
                  r"`## Not adopted`", r"consistency checker\s+flags a `Prototype:` path", window=400)
        self.lacks(self.play, r"one (integration )?unit per (mechanism|patch)[^.]{0,20}(\.|;)", "one unit per patch rule")

    def test_prototype_line_has_one_consumer_and_fails_closed(self):
        self.near(self.play, "consumer", r"`Prototype:` line", r"(one|a single) consumer", window=60)
        self.near(self.play, "pass", r"pass `prototype: <path>`", r"both the patch and its manifest exist", window=200)
        self.near(self.play, "missing", r"either file is missing", r"task halts", r"user decides", r"`userApprovalNeeded`",
                  r"park", window=300)
        self.near(self.play, "gates", r"executor may adopt the patch", r"every gate runs on the delivered result")

    def test_a_run_is_an_observation_not_an_oracle(self):
        self.near(self.play, "oracle", r"A run is an observation, not an oracle", r"completion, not correctness",
                  r"Reviewed observations become regression fixtures",
                  r"independent invariants and accepted constraints", r"decide correctness", window=400)
        self.near(self.play, "hardware", r"Simulator evidence never stands for hardware")
        self.lacks(self.play, r"run (becomes|is) the (golden|acceptance oracle|oracle)", "run becomes oracle")

    def test_one_negative_test_per_failure_mechanism(self):
        self.near(self.play, "negative", r"One representative test per distinct failure mechanism",
                  r"not one per failed attempt")

    def test_acceptance_probe_stays_user_authored(self):
        self.near(self.play, "probe", r"acceptance probe stays user-authored", r"Run evidence never replaces")


class PlaybookSessionsStopMetricsTest(Base):
    """§5–§7 — resume, status words, overnight, stop rules, metrics."""

    def test_grant_survives_resume_without_a_new_attempt(self):
        self.near(self.play, "resume", r"grant survives a session", r"show the user the grant", r"attempts used",
                  r"retained and open ledger items", r"continue", window=300)
        self.near(self.play, "word", r"new attempt starts only on the user's word")
        self.near(self.play, "sequence", r"sequence never survives a session by itself")
        self.near(self.play, "recover", r"status file not `done`", r"`reserved`/`uncertain` attempt", r"`recover`",
                  window=120)

    def test_status_vocabulary_distinguishes_closed_window_from_idle(self):
        self.near(self.play, "status", r"`closed` \| `idle` \| `running` \| `spent` \| `revoked`")
        self.near(self.play, "closed", r"`closed`\s+means no window is open", r"between windows", r"`complete`", window=160)
        self.near(self.play, "idle", r"`idle` is the interval between invocations inside an open window")
        self.near(self.play, "setter", r"`closed` when a window closes and at `complete`")

    def test_overnight_refuses_while_a_window_is_open(self):
        self.near(self.play, "overnight", r"refuses to start while `explore.status` is `idle` or\s+`running`")
        self.near(self.play, "no attempt", r"overnight run starts no Explore attempt")
        self.near(self.play, "no grant", r"never grants or\s+widens the authority")

    def test_stop_rules_wait_for_the_user(self):
        self.near(self.play, "stop", r"Stop Explore", r"wait for the user", window=60)
        for case in (r"outside\s+`boundary` or bypasses `actionPath`", r"cannot be attributed",
                     r"cleanup cannot be verified", r"missing log or ledger", r"`reconcile` is `none`",
                     r"budget is spent"):
            self.near(self.play, f"stop case {case}", r"wait for the user", case, window=400)
        self.lacks(self.play, r"continue with the next attempt", "stop rule continues")
        self.near(self.play, "cleanup", r"explorer deletes its own\s+`open` objects", r"first action of the\s+next invocation")
        self.near(self.play, "promote stop", r"Stop Promote", r"loses a gate", r"no verdict is reused from Explore")

    def test_amendment_count_is_a_metric_not_a_stop_rule(self):
        self.near(self.play, "metric", r"material amendments", r"diagnostic metric", r"not a stop rule")

    def test_metrics_recorded_separately(self):
        for term in (r"Explore:", r"attempts", r"setup and run", r"objects created and deleted", r"user wait",
                     r"Promote:", r"consistency rounds", r"full-suite runs", r"material\s+amendments with cause"):
            self.near(self.play, f"metric {term}", term)
        self.near(self.play, "separately", r"Record\s+simulated duration", r"\*\*separately\*\*", window=200)
        self.near(self.play, "directional", r"directional, not a controlled benchmark")
        self.near(self.play, "pilot itself", r"Measure the specialist-based\s+pilot itself",
                  r"main-session attempt does not stand for it")


class ExplorerAgentTest(Base):
    """agents/explorer.md — the actor that is allowed and bound to run live actions."""

    def test_one_invocation_and_a_small_main_context(self):
        self.near(self.explorer, "one", r"run \*\*one Explore invocation\*\*", r"(then|and) end", window=20)
        self.near(self.explorer, "main", r"never reads your transcript", r"reads only the log\s+entry")
        self.near(self.explorer, "killed", r"if you were killed", r"log stub", r"ledger", r"status file", window=80)

    def test_receives_the_full_grant(self):
        self.near(self.explorer, "grant", r"The grant", r"verbatim from `exploreAuthority`", window=40)
        for item in (r"`objective`, `boundary`, `actionPath`", r"`reconcile`", r"`forbidden`", r"standing list",
                     r"`budget`", r"`cadence`", r"`decisions\[\]`", r"`attemptsUsed`"):
            self.near(self.explorer, f"grant item {item}", r"verbatim from `exploreAuthority`", item, window=500)
        self.near(self.explorer, "windows", r"`before-feature`", r"`before-task-<N>`", r"`after-task-<N>`", window=200)
        self.near(self.explorer, "provisional", r"`awaiting_candidate` tasks that HEAD holds", r"provisional")
        self.near(self.explorer, "kinds", r"`attempt`", r"attempt id", r"`recover`", r"same attempt id, no new hypothesis",
                  r"`close`", r"invocation number", window=300)
        self.near(self.explorer, "missing", r"grant that is missing", r"is a stop", r"write nothing to a live system",
                  r"`EXPLORE REQUEST: grant missing", window=300)

    def test_live_actions_only_through_the_path_inside_the_boundary(self):
        self.near(self.explorer, "path", r"Live actions go only through `actionPath`")
        self.near(self.explorer, "boundary", r"only on objects inside `boundary`")
        for term in (r"Never a\s+free API call", r"never a route on `forbidden`", r"never an object you did not create"):
            self.near(self.explorer, f"never {term}", term)
        self.near(self.explorer, "proof", r"recorded ID is the proof of creation", r"name prefix is never proof of ownership")
        self.lacks(self.explorer, r"(judge|prove) (it )?by the name prefix", "prefix proves ownership")
        self.near(self.explorer, "uncovered", r"permission\s+the grant does not cover is not yours to take",
                  r"`EXPLORE REQUEST:")
        self.near(self.explorer, "widen", r"Never widen\s+`boundary`, `budget` or `actionPath` yourself")
        self.near(self.explorer, "rules", r"Every project rule stays", r"secret handling", r"permission deny rules",
                  window=300)
        self.near(self.explorer, "denial", r"hook block or a deny\s+result is a security denial", r"never rephrase",
                  r"no `decisions\[\]` entry ever covers it", window=200)
        self.lacks(self.explorer, r"(may|can) (take|use) a route on `forbidden`", "forbidden route allowed")

    def test_probe_code_in_a_temporary_copy_and_a_closed_write_perimeter(self):
        self.near(self.explorer, "copy", r"Probe code lives in a temporary copy, never in the checkout",
                  r"`git archive HEAD", r"read-only git only", window=400)
        self.near(self.explorer, "perimeter", r"Closed write perimeter", r"write exactly these files and nothing else",
                  r"attempt log", r"object ledger", r"`spec-memory/prototypes/`", r"the brief", r"status file", window=400)
        for never in (r"Never the findings index \(`spec-memory/findings.jsonl`\)", r"never the state file",
                      r"never a\s+context pack or `spec-memory/decisions.md`", r"never a spec",
                      r"never product code in the checkout"):
            self.near(self.explorer, f"perimeter {never}", never)
        self.lacks(self.explorer, r"append(s)? (them|it|a finding) (yourself|itself|directly) into the findings", "explorer writes findings")
        self.near(self.explorer, "one invocation", r"One invocation, then end", r"Never start a second hypothesis")
        self.near(self.explorer, "never ask", r"Never ask the\s+user", r"orchestrator relays")
        self.lacks(self.explorer, r"Ask the user directly", "explorer asks the user")

    def test_confirms_nothing_and_evaluation_is_evidence(self):
        self.near(self.explorer, "nothing", r"You confirm nothing", r"No gate, no task, no amendment")
        self.near(self.explorer, "evaluation", r"`after-task-<N>` window", r"findings are evidence", window=120)
        for term in (r"never edit\s+product code", r"never reopen or pass the task",
                     r"never stand in for a gate or the acceptance\s+probe"):
            self.near(self.explorer, f"eval {term}", term)
        self.near(self.explorer, "provisional", r"`awaiting_candidate`\) commit is an intermediate baseline",
                  r"never treat a simulation result as its full suite")

    def test_scrub_covers_every_file_and_command_fields(self):
        self.near(self.explorer, "scrub", r"Scrub before you write", r"log, ledger, manifest, brief",
                  r"no\s+hostname, address, token", r"`command` field names a secret by\s+its env var", r"never its value",
                  window=300)
        self.near(self.explorer, "raw", r"Delete raw captures the same turn")
        self.lacks(self.explorer, r"Keep raw captures", "raw captures kept")

    def test_object_states(self):
        for state in (r"`open`", r"`deleted-verified`", r"`retained-by-user`"):
            self.near(self.explorer, f"state {state}", r"Object states", state, window=300)
        self.near(self.explorer, "decision", r"`retained-by-user`", r"decision recorded", window=200)
        self.near(self.explorer, "targets", r"Cleanup targets `open` objects only")
        self.near(self.explorer, "retained", r"`retained-by-user` object is never\s+deleted", r"never asked about again")
        self.near(self.explorer, "open cleanup", r"`open` objects at the end of any invocation", r"open\s+cleanup",
                  r"never silently dropped", window=200)

    def test_attempt_order_stub_cleanup_budget_patch_run_log(self):
        self.near(self.explorer, "read log", r"read the attempt log in full", r"memory of earlier attempts")
        self.near(self.explorer, "missing", r"`attemptsUsed > 0` and the log or the ledger file is\s+missing",
                  r"cleanup cannot be verified", r"write no live action", r"`blocked`", window=200)
        self.near(self.explorer, "stub", r"Reservation stub", r"before anything else", r"`commands issued: none`",
                  r"on-disk reservation", r"killed", window=300)
        self.near(self.explorer, "cleanup first", r"Cleanup first", r"Every `open` object", r"deleted now",
                  r"`retained-by-user` objects are left alone", window=200)
        self.lacks(self.explorer, r"Any ledger entry without a verified deletion is deleted", "unconditional delete")
        self.near(self.explorer, "budget", r"orchestrator reserved your attempt id before it launched you",
                  r"`attemptsUsed >= budget`", r"`budget spent`", window=300)
        self.near(self.explorer, "attempt def", r"An attempt", r"issues at least one\s+`actionPath` command", window=40)
        self.near(self.explorer, "release", r"`released: setup failure before the first command`",
                  r"does not\s+count against the budget", r"Only that written evidence releases a slot", window=200)
        self.near(self.explorer, "patch first", r"Patch and manifest", r"before any result exists",
                  r"`spec-memory/prototypes/<slug>.patch`", r"`<slug>.manifest.json`", r"never a credential",
                  r"patch without a manifest\s+is not adoptable", window=600)
        self.near(self.explorer, "no patch", r"no-change evaluation writes no patch")
        self.near(self.explorer, "point of no return", r"Point of no return", r"before the first `actionPath` command",
                  r"`commands issued: yes`", r"counted whatever happens", window=200)
        self.near(self.explorer, "ledger", r"Record every\s+object you create in the ledger as `open`", r"ID and type",
                  window=100)
        self.near(self.explorer, "own cleanup", r"Clean up your own objects", r"every `open` object of this attempt",
                  r"verify each\s+deletion through `actionPath`", r"`retained-by-user` with that decision recorded",
                  window=300)
        self.near(self.explorer, "log", r"Complete the log entry", r"next\s+discriminating question", r"`counted: yes`",
                  r"Failed attempts are kept", window=400)

    def test_recover_settles_and_never_explores(self):
        self.near(self.explorer, "recover", r"`recover` invocation", r"settle, never explore", window=40)
        self.near(self.explorer, "same id", r"same attempt id", r"uncertain attempt", window=60)
        self.near(self.explorer, "released", r"`commands issued: none`", r"`released: setup failure", window=80)
        self.near(self.explorer, "reconcile", r"run `reconcile`", r"recorded ID or ownership", r"ledger lacks as `open`",
                  r"lost", window=200)
        self.near(self.explorer, "never", r"Never re-issue a create whose outcome is unknown",
                  r"never judge\s+ownership by a name prefix")
        self.near(self.explorer, "none", r"`reconcile` is `none`", r"`blocked`", r"user settles it", window=120)
        self.near(self.explorer, "no hypothesis", r"No new hypothesis\*\* in a\s+recovery, whatever the cadence")
        self.lacks(self.explorer, r"recover(y)?[^.]{0,80}(then|and) (run|start) (a|the next) hypothesis", "recovery explores")

    def test_close_writes_the_brief_with_open_limits(self):
        self.near(self.explorer, "close", r"`close` invocation", r"Check every ledger row", r"retained objects",
                  r"solution brief", r"open\s+limits", r"never silently relaxed", r"provisional\s+commits",
                  r"evidence, not a spec", r"Write no new\s+attempt", window=500)
        self.near(self.explorer, "no change", r"evaluation with no change has none")

    def test_stop_rules_clean_up_and_block(self):
        self.near(self.explorer, "stop", r"Stop rules", r"clean up", r"report", r"wait", window=40)
        self.near(self.explorer, "cases", r"outside `boundary` or bypass\s+`actionPath`", r"cannot be attributed",
                  r"deletion cannot be verified", window=200)
        self.near(self.explorer, "block", r"`stopped: <reason>`", r"status `blocked`", window=80)

    def test_secret_handling_section(self):
        self.near(self.explorer, "section", r"## Secret Handling", r"Use, don't read", r"Never expose a value",
                  r"Escalate when blocked", r"`SECRET REQUEST:", window=800)
        self.near(self.explorer, "never in files", r"never into a log, ledger or manifest")

    def test_status_file_uses_the_invocation_number(self):
        self.near(self.explorer, "task", r"`<task>` is `explore-<window>`")
        self.near(self.explorer, "attempt", r"`<attempt>` is the \*\*invocation number\*\*",
                  r"`invocations\[\"explore-<window>/explorer\"\]`", r"never\*\* the Explore attempt id",
                  r"only in the log heading\s+and your summary", window=400)
        self.near(self.explorer, "adds one", r"an attempt, a recovery, a close and a\s+respawn each add one")
        self.lacks(self.explorer, r"`<attempt>` (is|the) (the )?(Explore )?attempt number", "status attempt = Explore attempt")
        self.near(self.explorer, "other", r"Never write another agent's status file")


class OrchestratorTest(Base):
    """The contract vocabulary, the tiers, the pointer rules, the payloads, state keys, Critical Rules."""

    def test_contract_names_the_explorer_task_and_invocation_numbering(self):
        contract = self.orch[self.orch.index("## Specialist Execution Contract"):self.orch.index("## Asking the User")]
        self.near(contract, "task", r"`explore-<window>` for the explorer")
        self.near(contract, "numbering", r"for the explorer every `attempt`,\s+`recover` and `close` invocation adds one",
                  r"never the Explore attempt id")

    def test_tiers_name_explore_authority(self):
        self.near(self.orch, "tiers", r"`exploreAuthority` — a fourth, larger grant", r"implies\s+`prototypeAuthority`",
                  r"through `actionPath` \*\*only\*\*", r"\*\*explorer\*\* subagent alone",
                  r"neither tier 2 nor a back door into\s+tier 3", window=300)

    def test_pointer_names_the_one_definition_and_the_scope(self):
        self.near(self.orch, "pointer", r"Promote — `playbooks/sdd-explore.md`", r"follow it exactly", r"one definition",
                  window=300)
        self.near(self.orch, "binding", r"hold even without the playbook")
        self.near(self.orch, "summary", r"no new permission grant per attempt", r"every project\s+safeguard", window=60)
        self.lacks(self.orch[self.orch.index("#### Explore"):], r"no per-attempt approval", "old phrase in the pointer")
        self.near(self.orch, "scope", r"checkpoint-only \(between tasks\)", r"not a scheduler")

    def test_explore_is_the_users_choice(self):
        self.near(self.orch, "choice", r"Explore is the user's choice", r"never inferred",
                  r"never a\s+mandatory taxonomy", r"feature without a grant runs exactly as before")

    def test_one_wide_grant_per_feature(self):
        self.near(self.orch, "grant", r"One grant per feature", r"asked once", r"tooling-gap check",
                  r"grantedBy: \"user\"", r"reconcile, forbidden, budget, cadence, explorer, decisions", r"whole\s+feature",
                  r"budget of attempts", r"survives sessions", r"never revokes a project rule", r"no agent widens it",
                  window=300)

    def test_between_tasks_only_with_the_phase_b_boundary(self):
        self.near(self.orch, "between", r"Between tasks only", r"no task is in progress", r"checkout is clean",
                  r"no wave or Level 1 speculation exists", r"no specialist writer is live", r"nothing is parked",
                  r"no task, overlap or wave launches until the window closes", window=400)
        for term in (r"evaluation never edits product code", r"never\s+reopens or passes a task",
                     r"never stands in for a\s+gate or the acceptance probe", r"never completes it",
                     r"never replaces its full suite"):
            self.near(self.orch, f"between {term}", term)
        self.near(self.orch, "provisional", r"`awaiting_candidate` commit it uses is provisional")

    def test_level_one_and_waves_yield_to_a_window(self):
        self.near(self.orch, "level 1", r"start task N\+1's executor speculatively", r"no Explore window is open or requested",
                  r"`before-task-<N\+1>`", r"`after-task-<N>`", window=500)
        self.near(self.waves, "waves", r"no Explore window is open")

    def test_no_live_action_outside_the_path_or_boundary(self):
        self.near(self.orch, "outside", r"No live action outside `actionPath` or `boundary`", r"new user decision",
                  r"`exploreAuthority.decisions\[\]`", window=200)
        self.near(self.orch, "denial", r"`decisions\[\]` entry\s+never covers a hook block or a deny result")
        self.near(self.orch, "route", r"never improvises a route")

    def test_explorer_subagent_cadence_and_log_only(self):
        self.near(self.orch, "explorer", r"explorer is the `explorer` subagent", r"never the main session", window=60)
        self.near(self.orch, "never executor", r"never the task-executor")
        self.near(self.orch, "prompt", r"full grant in its prompt", r"one invocation at a\s+time",
                  r"only that attempt's log entry", r"never (its|the)\s+transcript", window=300)
        self.near(self.orch, "step", r"`step`", r"next attempt starts only on the\s+user's word", window=60)
        self.near(self.orch, "continuous", r"`continuous, upTo: N`", r"bounded sequence the user asked for",
                  r"report after\s+every attempt", r"mandatory stop", window=200)
        for stop in (r"boundary or authority change", r"the budget", r"unknown\s+outcome", r"open cleanup",
                     r"material decision"):
            self.near(self.orch, f"stop {stop}", r"mandatory stop", stop, window=200)
        self.near(self.orch, "silence", r"silence never creates or extends a sequence")
        self.lacks(self.orch, r"explorer: \"main session\"", "main session explorer")

    def test_reservation_and_recovery_bind(self):
        self.near(self.orch, "reserve", r"attempt is reserved before dispatch", r"`explore.attempts\[\]`",
                  r"same id on recovery", window=100)
        self.near(self.orch, "never freed", r"crash\s+or a lost result never frees the slot",
                  r"only written evidence of a setup failure before the first\s+command releases it")
        self.near(self.orch, "recovery", r"respawn is recovery only", r"`recover` invocation", r"`reconcile` command",
                  r"never by a name prefix", r"never a blind\s+re-create", r"never runs a new hypothesis", window=300)

    def test_patch_manifest_states_and_missing_ledger_bind(self):
        self.near(self.orch, "patch", r"Every patch is saved with its manifest before its result is logged",
                  r"without a\s+manifest, or described only in prose, is never applied", window=200)
        self.near(self.orch, "states", r"`open`, `deleted-verified`, `retained-by-user`", r"cleanup targets `open` objects\s+only",
                  r"first action of the next invocation", window=200)
        self.near(self.orch, "missing", r"`attemptsUsed > 0` and a missing log or ledger is a stop", r"ask the user before any attempt")

    def test_budget_stop_binds(self):
        self.near(self.orch, "budget", r"Budget stop", r"Explore stops and reports", r"never widen the (budget|boundary)")

    def test_explore_never_confirms_a_planning_gate(self):
        self.near(self.orch, "gate", r"Explore never confirms a planning gate", r"evidence, not a spec",
                  r"requirements or amendment confirmation", r"`prototype: <path>`",
                  r"every gate\s+runs on the delivered result", window=400)

    def test_overnight_never_grants_or_widens(self):
        self.near(self.orch, "overnight grant", r"never grants or widens `exploreAuthority`")
        self.near(self.orch, "overnight attempt", r"overnight run starts no\s+Explore attempt")

    def test_session_start_shows_the_grant(self):
        self.near(self.orch, "resume", r"Explore grant on resume", r"show the user the grant", r"`explore.attemptsUsed`",
                  r"open ledger items", r"new attempt starts only on the user's word", window=300)

    def test_planning_payloads_carry_the_brief(self):
        for agent in ("requirements-agent", "design-agent", "tasks-agent"):
            self.near(self.orch, agent, rf"Delegate to the \*\*{agent}\*\*", r"solution brief path",
                      r"evidence, not a spec", window=400)

    def test_stage_one_passes_prototype_only_with_its_manifest(self):
        self.near(self.orch, "stage 1", r"Stage 1 — Execution", r"`prototype: <path>` when the task block has a `\*\*Prototype:\*\*` line",
                  r"both the patch and its\s+`.manifest.json` exist", r"halts", r"user decides", r"`userApprovalNeeded`",
                  r"park", r"Never pass a patch without its manifest", window=500)

    def test_complete_closes_the_grant(self):
        section = self.orch[self.orch.index("### `complete`"):self.orch.index("## Vault Access")]
        self.near(section, "closed", r"`explore.status: closed`", r"`window.closedAt`", r"`retained-by-user` or unresolved",
                  r"grant ends with the feature", window=200)

    def test_state_keys_list_the_grant(self):
        self.near(self.orch, "keys", r"Keys this playbook adds", r"`exploreAuthority` and `explore`", r"`decisions\[\]`",
                  r"attemptsUsed, attempts\[\], status, window, reason", window=300)

    def test_critical_rules(self):
        self.near(self.orch, "code", r"NEVER write or modify application code",
                  r"explorer writes probe code in a temporary copy under `exploreAuthority`, never in the checkout")
        self.near(self.orch, "explore", r"NEVER run an Explore action outside the grant's `actionPath` and `boundary`",
                  r"never open an Explore window while a task is in progress", r"wave, a speculation or a specialist writer is live",
                  r"never run a new hypothesis on a respawn", r"never grant, widen or infer `exploreAuthority` yourself",
                  r"Only the explorer subagent runs Explore actions", r"log entry, never its transcript", window=400)

    def test_retained_prototypes_rule_is_kept(self):
        self.near(self.orch, "retained", r"Retained prototypes", r"`prototype: <path>`", r"never recorded as a passed\s+task",
                  window=600)


class ExecutorTest(Base):
    def test_manifest_required_and_limits_never_relaxed(self):
        self.near(self.executor, "manifest", r"`<slug>.manifest.json`", r"read it first", r"never force")
        self.near(self.executor, "no manifest", r"no manifest beside it is a reference only", r"never apply it")
        self.near(self.executor, "limits", r"open limit the solution brief names", r"never\s+relaxed in silence",
                  r"`MATERIAL CHANGE`")


class TasksAgentTest(Base):
    def test_plan_from_the_brief_candidate_stays_the_unit(self):
        self.near(self.tasks, "brief", r"solution brief", r"`spec-memory/explore/solution-<window>.md`", window=60)
        self.near(self.tasks, "unit", r"integration unit", r"stays the unit", r"several mechanisms and retained patches may map to one coherent unit",
                  r"traceability, not a task boundary", window=300)
        self.near(self.tasks, "owner", r"\*\*one\*\* task\s+block that applies it",
                  r"`\*\*Prototype:\*\* spec-memory/prototypes/<slug>.patch`", r"manifest beside it",
                  r"one owning task per patch, never a patch on two tasks", window=300)
        self.lacks(self.tasks, r"one (integration )?unit (\(rule\s+1a\) )?per\s+mechanism", "one unit per mechanism")
        self.near(self.tasks, "not adopted", r"`## Not adopted` section", r"with the reason")
        self.near(self.tasks, "negative", r"one negative test in the unit that owns the mechanism", r"not one\s+test per failed attempt")
        self.near(self.tasks, "evidence", r"brief is evidence, not a spec", r"confirmed requirements and\s+design decide")

    def test_template_has_the_prototype_line(self):
        # A template field, not a rule: a raw presence check (the fenced block's backtick parity
        # defeats the negation heuristic of `near` here).
        self.assertTrue(prose.search(self.tasks, r"\*\*Prototype:\*\* <Optional[^>]*retained Explore patch this task adopts"),
                        "template: Prototype line missing")


class RequirementsAgentTest(Base):
    def test_requirements_come_from_intent_and_keep_open_limits(self):
        self.near(self.reqs, "brief", r"solution brief", r"evidence, not a spec", r"intended behaviour and constraints",
                  r"the user accepts at the requirements confirmation", r"not from whatever the experiment produced",
                  window=400)
        self.near(self.reqs, "limits", r"Every open limit", r"requirement or as a proposed", r"deviation",
                  r"none is dropped in silence", window=200)
        self.lacks(self.reqs, r"deviations the\s+evidence supports", "evidence accepts deviations")


class DesignAgentTest(Base):
    def test_design_receives_the_brief_as_evidence(self):
        self.near(self.design, "brief", r"solution brief", r"evidence, not a spec", r"confirmed\s+requirements decide",
                  r"each mechanism you adopt in a design\s+component", r"several mechanisms may share one component",
                  r"never adopt a mechanism that\s+relaxes an open limit", window=500)
        self.lacks(self.design, r"one unit per mechanism", "one unit per mechanism")


class CheckerTest(Base):
    def test_checker_flags_prototype_lines(self):
        self.near(self.checker, "prototype", r"Prototype lines", r"flag it when the patch\s+file or its `<slug>.manifest.json` beside it is missing",
                  r"same path appears on two\s+tasks", r"`## Not adopted`", window=300)
        self.lacks(self.checker, r"(accept|pass) it when the patch", "checker accepts a missing patch")


class CommandsTest(Base):
    def test_resume_shows_the_grant_and_starts_nothing(self):
        self.near(self.resume, "resume", r"Explore grant", r"still valid", r"survives sessions", r"budget is spent",
                  r"`complete`", r"user revokes it", r"cadence", r"`explore.attemptsUsed`", r"`retained-by-user` and `open` item",
                  window=400)
        self.near(self.resume, "missing", r"log or the ledger file is missing", r"cleanup cannot be verified",
                  r"stop and ask the user before any attempt", window=120)
        self.near(self.resume, "recover", r"not `done`", r"`reserved`/`uncertain` attempt", r"`recover`", r"no hypothesis",
                  window=200)
        self.near(self.resume, "word", r"Start no Explore attempt by yourself", r"only on the user's word",
                  r"continuous sequence never survives a session by itself", window=200)
        self.lacks(self.resume, r"exploreAuthority[^.]{0,80}is void", "grant voided on resume")

    def test_overnight_refuses_while_a_window_is_open(self):
        self.near(self.overnight, "refuse", r"`explore.status` is `idle` or `running`", r"stop", window=120)
        self.near(self.overnight, "no attempt", r"overnight run starts no Explore attempt")
        self.near(self.overnight, "no grant", r"never grants or widens `exploreAuthority`")


class DocsTest(Base):
    def test_claude_md_states_the_policy(self):
        self.near(self.claude, "intro", r"Explore → Promote", r"`playbooks/sdd-explore.md`", r"never inferred",
                  r"\*\*explorer\*\* subagent", r"`exploreAuthority`", r"grants once\s+per feature", window=300)
        self.near(self.claude, "safeguards", r"no new permission grant per attempt", r"every project safeguard",
                  r"every\s+patch saved with its manifest", r"every created object deleted and verified", window=200)
        self.lacks(self.claude, r"no per-attempt approval", "old ambiguous phrase")
        self.near(self.claude, "cadence", r"authority is durable", r"one requested attempt, or one requested\s+bounded sequence",
                  r"`cadence: continuous, upTo: N`", r"silence never extends it", window=300)
        self.near(self.claude, "between", r"checkpoint-only", r"between tasks", r"before a task", r"after a task",
                  r"one attempt per explorer invocation", r"reads only each\s+attempt's log entry", r"respawn is recovery only",
                  r"user redirects between attempts", window=300)
        self.near(self.claude, "promote", r"no extra\s+gate", r"observation, not an oracle")
        self.near(self.claude, "overnight", r"Overnight mode never grants or widens `exploreAuthority`")

    def test_claude_md_lists_the_explorer(self):
        self.near(self.claude, "ownership", r"- explorer:", r"one Explore attempt per invocation", r"`exploreAuthority`",
                  r"never edits the checkout", r"never confirms a gate", window=400)

    def test_readme_lists_the_playbook_and_the_agent(self):
        self.near(self.readme, "playbook", r"sdd-explore.md", r"Explore → Promote")
        self.near(self.readme, "agent", r"explorer.md", r"One Explore attempt per invocation")
        self.near(self.readme, "count", r"14 agents")


if __name__ == "__main__":
    unittest.main(verbosity=2)
