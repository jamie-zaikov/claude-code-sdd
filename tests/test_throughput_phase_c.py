#!/usr/bin/env python3
"""Prose-contract tests for pipeline-throughput Phase C — Explore → Promote.

Phase C codifies the Explore → Promote pilot: the explorer subagent solves a hard problem inside a
scope the user grants once (`exploreAuthority`), one attempt per invocation, between tasks only;
then SDD promotes the proven solution through every normal gate. `playbooks/sdd-explore.md` is the
one normative definition, `agents/explorer.md` the explorer's side, and the orchestrator keeps the
rules that bind even without the playbook. Each pin names a rule's key words and direction
(`prose.near` refuses a negated match; a rule that really is negative puts the negation inside its
pattern), so a pin goes RED when the rule is removed or inverted and stays GREEN when it is
reworded or re-wrapped. Run:
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


class PlaybookWhenTest(Base):
    """§1 — a user choice, between tasks only, three window kinds."""

    def test_explore_is_a_user_choice(self):
        self.near(self.play, "choice", r"conversation choice", r"not a mandatory taxonomy", r"The user decides")
        self.near(self.play, "no grant", r"feature without a grant runs exactly as before")
        self.lacks(self.play, r"(may|should|must|shall) infer (it|explore)", "an agent infers Explore")
        self.near(self.play, "api", r"API-style work", r"needs no exploration")

    def test_between_tasks_only_nothing_parked(self):
        self.near(self.play, "between", r"between tasks only", r"never runs while a\s+task is in progress",
                  r"nothing is parked", window=200)
        self.near(self.play, "clean", r"main checkout is clean", r"`HEAD` is the base")
        self.lacks(self.play, r"park(s|ed)? (the|a) (running|current) task", "parks a task for Explore")

    def test_three_window_kinds(self):
        self.near(self.play, "kinds", r"`before-feature`", r"`before-task-<N>`", r"`after-task-<N>`", window=900)
        self.near(self.play, "before task", r"`before-task-<N>`", r"find how to build it",
                  r"unaffected accepted\s+baseline stays as it is", r"amendment of the affected tasks only",
                  window=300)

    def test_evaluation_window_is_evidence_only(self):
        self.near(self.play, "evaluation", r"`after-task-<N>`", r"evaluation run", r"findings are evidence",
                  r"findings index", r"material amendment", window=300)
        self.near(self.play, "never", r"evaluation never edits product code", r"never reopens or passes a task",
                  r"never\s+stands in for a gate", r"acceptance probe", window=200)
        self.lacks(self.play, r"evaluation (may|can) (edit|reopen|pass)", "evaluation acts on a task")


class PlaybookGrantTest(Base):
    """§2 — tooling gap first, one wide record, inherited rules, the explorer subagent."""

    def test_tooling_gap_is_checked_before_the_grant(self):
        self.near(self.play, "gap", r"tooling.gap", r"does not improvise a route",
                  r"narrow the objective", r"extend the path first", r"before the grant", window=400)
        self.lacks(self.play, r"check this after the grant", "gap check after the grant")

    def test_a_yes_is_recorded_silence_grants_nothing(self):
        self.near(self.play, "ask once", r"Ask once per feature", r"Asking the User", r"A yes is recorded",
                  window=400)
        self.near(self.play, "silence", r"silence or the absence of an\s+objection grants nothing")
        self.lacks(self.play, r"absence of an\s+objection,? is recorded", "silence counts as a grant")

    def test_grant_record_has_every_key(self):
        self.near(self.play, "record", r"exploreAuthority: \{", r"grantedBy: \"user\"", r"objective", r"boundary",
                  r"actionPath", r"forbidden", r"budget", r"explorer", r"decisions", window=400)

    def test_grant_is_wide_durable_and_never_widened(self):
        self.near(self.play, "wide", r"Wide and durable", r"whole feature", r"several windows", r"one budget",
                  r"valid across sessions", r"budget is spent", r"`complete`", r"user revokes it", window=300)
        self.near(self.play, "never widened", r"asked once, never inferred, and never widened by an agent")

    def test_grant_inherits_every_project_rule(self):
        self.near(self.play, "inherit", r"grant never revokes a project rule")
        self.near(self.play, "secret", r"secret handling and the\s+permission deny rules", r"stay in force")
        self.near(self.play, "safeguards", r"removes ceremony", r"not safeguards")

    def test_standing_forbidden_list_is_always_present(self):
        self.near(self.play, "standing", r"Standing forbidden list", r"always in `forbidden`", r"did not create",
                  r"publishing", r"widening a client guard", r"secret beyond\s+the existing env vars",
                  r"product code in the main checkout", r"hardware", window=300)
        self.lacks(self.play, r"forbidden list[^.]{0,80}(optional|discretion)", "forbidden list optional")

    def test_explorer_is_the_dedicated_subagent(self):
        self.near(self.play, "actor", r"explorer is the `explorer` subagent", r"clean context",
                  r"never the\s+main session and never the task-executor", window=200)
        self.near(self.play, "bound", r"allowed \*\*and\*\* bound to run live actions", r"full\s+grant in its prompt",
                  r"objective, boundary, action path, forbidden", r"budget, attempts used",
                  r"only through `actionPath` inside `boundary`", window=400)
        self.lacks(self.play, r"By default the\s+(\*\*)?main session", "main session default")
        self.lacks(self.play, r"(user|orchestrator) may name the main session", "main session option")

    def test_relation_to_the_probe_tiers(self):
        self.near(self.play, "tiers", r"Relation to the probe tiers", r"fourth, larger grant",
                  r"implies `prototypeAuthority`", r"through `actionPath` \*\*only\*\*",
                  r"neither tier 2 nor a back door into tier 3", window=400)

    def test_scope_of_the_authority(self):
        self.near(self.play, "no per-attempt", r"Inside the boundary there is no per-attempt approval")
        self.near(self.play, "uncovered", r"permission\s+the grant does not cover needs a new user decision",
                  r"recorded\s+under `exploreAuthority.decisions\[\]`", r"user's words", window=300)
        self.near(self.play, "request", r"`EXPLORE REQUEST: <permission>`", r"carries it to the user")
        self.near(self.play, "overnight grant", r"never\s+grants or widens `exploreAuthority`")
        self.near(self.play, "overnight attempt", r"overnight run starts no Explore attempt")
        self.near(self.play, "attended", r"Explore is\s+attended work")
        self.near(self.play, "narrow", r"Start narrow", r"smallest objective", r"new decision for the user")


class PlaybookWindowTest(Base):
    """§3 — one attempt per invocation, one writer per artifact, the loop's artifacts."""

    def test_one_attempt_per_invocation_main_reads_only_the_log_entry(self):
        self.near(self.play, "cadence", r"one attempt\s+per invocation", r"fresh context")
        self.near(self.play, "log only", r"reads \*\*only that\s+attempt's log entry\*\*",
                  r"never the explorer's transcript")
        self.near(self.play, "redirect", r"user\s+continues, redirects", r"next prompt", r"closes the window")
        self.lacks(self.play, r"orchestrator reads the (explorer's )?(transcript|raw output)", "main reads transcript")

    def test_one_writer_per_artifact(self):
        self.near(self.play, "writers", r"One writer per artifact", r"explorer writes the attempt log",
                  r"object ledger", r"every patch\s+and manifest", r"the brief",
                  r"orchestrator writes only the state file", r"no two explorer invocations run at once",
                  window=300)

    def test_attempt_is_defined_for_the_budget(self):
        self.near(self.play, "attempt", r"An attempt\*\* is one explorer invocation",
                  r"at least one `actionPath` command", r"ends before its first command",
                  r"does not count against the budget", window=300)

    def test_attempt_log_is_append_only(self):
        self.near(self.play, "log", r"Attempt log", r"`spec-memory/explore/log.md`", r"append-only",
                  r"one entry per invocation", window=300)
        self.near(self.play, "failed kept", r"Failed attempts are kept", r"negative tests")

    def test_patch_and_manifest_before_the_result_and_manifest_required(self):
        self.near(self.play, "patch", r"Patch and manifest before the result is logged",
                  r"`spec-memory/prototypes/<slug>.patch`", r"before\s+its log entry is written", window=300)
        self.near(self.play, "manifest", r"<slug>\.manifest\.json`", r"base commit",
                  r"path and hash, or how to rebuild", r"command", window=300)
        self.near(self.play, "contents", r"carries no untracked or binary output", r"never a credential")
        self.lacks(self.play, r"(may|can) carry untracked", "patch may carry untracked output")
        self.near(self.play, "no manifest", r"patch without a\s+manifest beside it is a reference only, never applied")
        self.near(self.play, "prose", r"only described in prose\s+cannot be adopted")
        self.lacks(self.play, r"(after|once) (its|the) (log entry|result) is (written|logged)[^.]{0,40}save",
                   "patch saved after the log")

    def test_object_ledger_records_ids_not_prefixes(self):
        self.near(self.play, "ledger", r"Object ledger", r"`spec-memory/explore/ledger.md`",
                  r"ID and type of every object", r"not just a name prefix", window=300)

    def test_evidence_hygiene_covers_command_fields(self):
        self.near(self.play, "scrub", r"Evidence hygiene", r"log, ledger, manifest, brief",
                  r"scrubbed\s+before it is written", r"`command` field", r"env var, never its value", window=400)

    def test_budget_stop_never_widens(self):
        self.near(self.play, "stop", r"Budget stop", r"budget is spent", r"stops and reports",
                  r"`explore.status: spent`", window=300)
        self.near(self.play, "widen", r"Never widen the (budget|boundary)", r"new user decision")

    def test_cleanup_is_verified_and_a_failure_stays_visible(self):
        self.near(self.play, "cleanup", r"Cleanup, verified", r"Every attempt ends with the deletion",
                  r"the user asks for", r"verified through `actionPath`", window=300)
        self.near(self.play, "visible", r"failed cleanup stays a visible open item", r"never dropped")
        self.near(self.play, "halt", r"After a stop-rule halt", r"not `done`", r"cleanup is the \*\*first action\*\*",
                  r"next explorer invocation", window=300)
        self.lacks(self.play, r"failed cleanup (is|may be|can be) (dropped|ignored|closed)", "cleanup dropped")
        self.lacks(self.play, r"keep the ones the\s+explorer judges", "explorer decides retention")

    def test_solution_brief_keeps_open_limits(self):
        self.near(self.play, "brief", r"Solution brief", r"`spec-memory/explore/solution-<window>.md`", r"`close`",
                  r"mechanisms that work", r"one line per failure\s+mechanism", r"patch and manifest path",
                  r"open\s+limits", r"never silently relaxed", r"evidence, not a spec", window=300)


class PlaybookPromoteTest(Base):
    """§4 — no extra gate, every planning agent gets the brief, units, one consumer for Prototype:."""

    def test_no_extra_gate_and_explore_never_confirms(self):
        self.near(self.play, "where accepted", r"No extra gate", r"requirements confirmation",
                  r"confirmation of the affected\s+amendment", window=300)
        self.near(self.play, "ack", r"acknowledgment of the brief alone approves no unseen design")
        self.near(self.play, "never confirms", r"Explore never confirms a planning gate")
        self.lacks(self.play, r"brief (is|counts as) (the|a) (spec|confirmation)", "brief as spec")

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

    def test_integration_units_and_one_patch_per_unit(self):
        self.near(self.play, "units", r"Integration units", r"producer with its consumer",
                  r"not one task per administrative step", window=300)
        self.near(self.play, "patch to unit", r"`\*\*Prototype:\*\* <path>`", r"one unit per patch",
                  r"`## Not adopted`", r"consistency\s+checker flags a `Prototype:` path",
                  r"patch or manifest is missing", window=400)

    def test_prototype_line_has_one_consumer_and_fails_closed(self):
        self.near(self.play, "consumer", r"`Prototype:` line has one consumer", r"passes `prototype:\s+<path>`",
                  r"both the patch and its manifest\s+exist", r"halts", r"user decides", r"overnight",
                  r"`userApprovalNeeded`", r"park", window=500)
        self.near(self.play, "gates", r"executor may adopt the\s+patch", r"every gate runs on the delivered result")

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
                  r"open ledger items", r"continue", window=300)
        self.near(self.play, "word", r"new attempt starts only on the user's word")
        self.near(self.play, "not done", r"status file not `done`", r"cleans up first")

    def test_status_vocabulary(self):
        self.near(self.play, "status", r"`idle` \| `running` \| `spent` \| `revoked` \| `closed`")
        self.near(self.play, "closed", r"`closed` when the feature reaches `complete`")

    def test_overnight_refuses_while_running(self):
        self.near(self.play, "overnight", r"refuses to start while `explore.status` is\s+`running`",
                  r"starts no Explore attempt", r"never grants or widens", window=300)

    def test_stop_rules_wait_for_the_user(self):
        self.near(self.play, "stop", r"Stop Explore", r"wait for the user", r"outside\s+`boundary` or bypasses `actionPath`",
                  r"cannot be attributed", r"cleanup cannot be verified", r"budget is spent", window=300)
        self.lacks(self.play, r"continue with the next attempt", "stop rule continues")
        self.near(self.play, "cleanup", r"explorer\s+deletes its own objects", r"first action\s+of the next invocation")
        self.near(self.play, "promote stop", r"Stop Promote", r"loses a gate", r"no verdict is reused from Explore")

    def test_amendment_count_is_a_metric_not_a_stop_rule(self):
        self.near(self.play, "metric", r"material amendments", r"diagnostic metric", r"not a stop rule")

    def test_metrics_recorded_separately(self):
        for term in (r"Explore:", r"attempts", r"setup and run", r"objects created and deleted", r"Promote:",
                     r"consistency rounds", r"full-suite runs", r"material\s+amendments with cause"):
            self.near(self.play, f"metric {term}", term)
        self.near(self.play, "separately", r"Record simulated duration", r"\*\*separately\*\*", window=200)
        self.near(self.play, "directional", r"directional, not a controlled benchmark")
        self.near(self.play, "zero", r"zero attempts while a live system is down", r"no evidence")


class ExplorerAgentTest(Base):
    """agents/explorer.md — the actor that is allowed and bound to run live actions."""

    def test_one_attempt_and_a_small_main_context(self):
        self.near(self.explorer, "one", r"run \*\*one Explore attempt\*\* and end")
        self.near(self.explorer, "main", r"never reads your transcript", r"reads only the log\s+entry")

    def test_receives_the_full_grant(self):
        self.near(self.explorer, "grant", r"The grant", r"verbatim from `exploreAuthority`",
                  r"`objective`, `boundary`, `actionPath`", r"`forbidden`", r"standing list", r"`budget`",
                  r"`decisions\[\]`", r"`attemptsUsed`", window=300)
        self.near(self.explorer, "windows", r"`before-feature`", r"`before-task-<N>`", r"`after-task-<N>`",
                  window=200)
        self.near(self.explorer, "missing", r"grant that is missing", r"is a stop", r"write nothing to a live system",
                  r"`EXPLORE REQUEST: grant missing", window=300)

    def test_live_actions_only_through_the_path_inside_the_boundary(self):
        self.near(self.explorer, "path", r"Live actions only through `actionPath`, only on objects inside `boundary`",
                  r"Never a free API\s+call", r"never a route on `forbidden`", r"never an object you did not create",
                  window=300)
        self.near(self.explorer, "uncovered", r"permission the grant does not cover is not yours to take",
                  r"`EXPLORE REQUEST:")
        self.near(self.explorer, "widen", r"Never widen `boundary`, `budget` or `actionPath` yourself")
        self.near(self.explorer, "rules", r"Every project rule stays", r"secret handling", r"permission deny rules",
                  window=300)
        self.lacks(self.explorer, r"(may|can) (take|use) a route on `forbidden`", "forbidden route allowed")

    def test_probe_code_in_a_temporary_copy_never_the_checkout(self):
        self.near(self.explorer, "copy", r"Probe code lives in a temporary copy, never in the checkout",
                  r"`git archive HEAD", r"never edit product code, specs, `tasks.md` or the state file",
                  r"read-only git only", window=400)
        self.near(self.explorer, "one attempt", r"One attempt, then end", r"Never start a second hypothesis")

    def test_confirms_nothing_and_evaluation_is_evidence(self):
        self.near(self.explorer, "nothing", r"You confirm nothing", r"No gate, no task, no amendment")
        self.near(self.explorer, "evaluation", r"`after-task-<N>` window", r"findings are evidence",
                  r"never edit\s+product code", r"never reopen or pass the task",
                  r"never stand in for a gate or the acceptance probe", window=300)

    def test_scrub_covers_every_file_and_command_fields(self):
        self.near(self.explorer, "scrub", r"Scrub before you write", r"log, ledger, manifest, brief",
                  r"no\s+hostname, address, token", r"`command` field names a secret by\s+its env var",
                  r"never its value", window=300)

    def test_attempt_order_cleanup_budget_patch_run_log(self):
        self.near(self.explorer, "cleanup first", r"Cleanup first", r"without a verified deletion is deleted now")
        self.near(self.explorer, "budget", r"`attemptsUsed >= budget`", r"write no attempt")
        self.near(self.explorer, "attempt def", r"attempt\*\* is one invocation that issues at least one `actionPath` command",
                  r"does not count against the budget", window=300)
        self.near(self.explorer, "patch first", r"Patch and manifest, before any result exists",
                  r"`spec-memory/prototypes/<slug>.patch`", r"`<slug>.manifest.json`", r"never a credential",
                  r"patch without a manifest\s+is not adoptable", window=600)
        self.near(self.explorer, "ledger", r"Record every object you create in the ledger", r"ID and type",
                  r"not just a name prefix", window=300)
        self.near(self.explorer, "own cleanup", r"Clean up your own objects",
                  r"unless the user's words in the prompt name ones to\s+keep",
                  r"verify each deletion through `actionPath`", window=300)
        self.near(self.explorer, "log", r"Log entry", r"Failed attempts are kept", window=600)

    def test_close_writes_the_brief_with_open_limits(self):
        self.near(self.explorer, "close", r"`close` invocation", r"Verify every ledger entry is deleted",
                  r"solution brief", r"open limits", r"never\s+silently relaxed", r"evidence, not a spec",
                  r"Write no new attempt", window=500)

    def test_stop_rules_clean_up_and_block(self):
        self.near(self.explorer, "stop", r"Stop rules", r"stop at once, clean up, report, wait",
                  r"outside `boundary` or bypass\s+`actionPath`", r"status `blocked`", window=400)

    def test_status_file(self):
        self.near(self.explorer, "status", r"`explore-<window>`", r"`explorer`", window=200)
        self.near(self.explorer, "other", r"Never write another agent's status\s+file")


class OrchestratorTest(Base):
    """The tiers, the pointer section, the payloads, the state keys and the Critical Rules."""

    def test_tiers_name_explore_authority(self):
        self.near(self.orch, "tiers", r"`exploreAuthority` — a fourth, larger grant", r"implies\s+`prototypeAuthority`",
                  r"through `actionPath` \*\*only\*\*", r"\*\*explorer\*\* subagent alone",
                  r"neither tier 2 nor a back door into\s+tier 3", window=300)

    def test_pointer_names_the_one_definition(self):
        self.near(self.orch, "pointer", r"Promote — `playbooks/sdd-explore.md`", r"follow it exactly",
                  r"one definition", window=300)
        self.near(self.orch, "binding", r"hold even without the playbook")
        self.near(self.orch, "actor", r"\*\*explorer\*\* subagent", r"one attempt per invocation", window=300)

    def test_explore_is_the_users_choice(self):
        self.near(self.orch, "choice", r"Explore is the user's choice", r"never inferred",
                  r"never a\s+mandatory taxonomy", r"feature without a grant runs exactly as before")

    def test_one_wide_grant_per_feature(self):
        self.near(self.orch, "grant", r"One grant per feature", r"asked once", r"tooling-gap check",
                  r"grantedBy: \"user\"", r"actionPath, forbidden, budget, explorer, decisions", r"whole feature",
                  r"survives sessions", r"never revokes a project rule", r"no agent widens it", window=300)

    def test_between_tasks_only(self):
        self.near(self.orch, "between", r"Between tasks only", r"no task is in progress", r"nothing is parked",
                  r"`after-task` evaluation never edits product code", r"never\s+reopens or passes a task",
                  r"never stands in for a gate or the acceptance probe", window=400)

    def test_no_live_action_outside_the_path_or_boundary(self):
        self.near(self.orch, "outside", r"No live action outside `actionPath` or `boundary`", r"new user decision",
                  r"`exploreAuthority.decisions\[\]`", r"never\s+improvises a route", window=300)

    def test_explorer_subagent_and_log_only(self):
        self.near(self.orch, "explorer", r"explorer is the `explorer` subagent",
                  r"never the main session, never the task-executor", r"full grant in its prompt",
                  r"one attempt per\s+invocation", r"only that attempt's log entry", r"never (its|the)\s+transcript",
                  r"redirect", window=400)
        self.lacks(self.orch, r"explorer: \"main session\"", "main session explorer")

    def test_patch_manifest_and_cleanup_rules_bind(self):
        self.near(self.orch, "patch", r"Every patch is saved with its manifest before its result is logged",
                  r"without a\s+manifest, or described only in prose, is never applied", r"deletion is verified",
                  r"cleanup is the first action", window=400)

    def test_budget_stop_binds(self):
        self.near(self.orch, "budget", r"Budget stop", r"Explore stops and reports",
                  r"never widen the (budget|boundary)")

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

    def test_state_keys_list_the_grant(self):
        self.near(self.orch, "keys", r"Keys this playbook adds", r"`exploreAuthority` and `explore`", r"`decisions\[\]`",
                  r"attemptsUsed, status, window, reason", window=300)

    def test_critical_rules(self):
        self.near(self.orch, "code", r"NEVER write or modify application code",
                  r"explorer writes probe code in a temporary copy under `exploreAuthority`, never in the checkout")
        self.near(self.orch, "explore", r"NEVER run an Explore action outside the grant's `actionPath` and `boundary`",
                  r"never open an Explore window while a task is in progress",
                  r"never grant, widen or infer `exploreAuthority` yourself",
                  r"Only the explorer subagent runs Explore actions", r"log entry, never its transcript", window=400)

    def test_retained_prototypes_rule_is_kept(self):
        self.near(self.orch, "retained", r"Retained prototypes", r"`prototype: <path>`",
                  r"never recorded as a passed\s+task", window=600)


class ExecutorTest(Base):
    def test_manifest_required_and_limits_never_relaxed(self):
        self.near(self.executor, "manifest", r"`<slug>.manifest.json`", r"read it first", r"never force")
        self.near(self.executor, "no manifest", r"no manifest beside it is a reference only", r"never apply it")
        self.near(self.executor, "limits", r"open limit the solution brief names", r"never\s+relaxed in silence",
                  r"`MATERIAL CHANGE`")


class TasksAgentTest(Base):
    def test_plan_from_the_brief_one_unit_per_patch(self):
        self.near(self.tasks, "brief", r"solution brief", r"`spec-memory/explore/solution-<window>.md`",
                  r"one integration unit", r"per mechanism",
                  r"`\*\*Prototype:\*\* spec-memory/prototypes/<slug>.patch`", r"manifest beside it",
                  r"one unit per patch, never a patch on two tasks", window=400)
        self.near(self.tasks, "not adopted", r"`## Not adopted` section", r"with the reason")
        self.near(self.tasks, "negative", r"one negative test in the unit that owns the mechanism",
                  r"not one\s+test per failed attempt")
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
                  r"each mechanism you adopt as a design\s+component", r"one unit per mechanism",
                  r"never adopt a mechanism that\s+relaxes an open limit", window=500)


class CheckerTest(Base):
    def test_checker_flags_prototype_lines(self):
        self.near(self.checker, "prototype", r"Prototype lines", r"flag it when the patch\s+file or its `<slug>.manifest.json` beside it is missing",
                  r"same path appears on two\s+tasks", r"`## Not adopted`", window=300)
        self.lacks(self.checker, r"(accept|pass) it when the patch", "checker accepts a missing patch")


class CommandsTest(Base):
    def test_resume_shows_the_grant_and_starts_nothing(self):
        self.near(self.resume, "resume", r"Explore grant", r"still valid", r"survives sessions", r"budget is spent",
                  r"`complete`", r"user revokes it", r"`explore.attemptsUsed`", r"open item",
                  r"Start no Explore attempt by yourself", window=400)
        self.lacks(self.resume, r"exploreAuthority[^.]{0,80}is void", "grant voided on resume")

    def test_overnight_refuses_while_an_explorer_runs(self):
        self.near(self.overnight, "refuse", r"`explore.status` is `running`", r"stop", window=300)
        self.near(self.overnight, "no attempt", r"overnight run starts no Explore attempt")
        self.near(self.overnight, "no grant", r"never grants or widens `exploreAuthority`")


class DocsTest(Base):
    def test_claude_md_states_the_policy(self):
        self.near(self.claude, "intro", r"Explore → Promote", r"`playbooks/sdd-explore.md`", r"never inferred",
                  r"\*\*explorer\*\* subagent", r"`exploreAuthority`", r"grants once\s+per feature", window=300)
        self.near(self.claude, "safeguards", r"no per-attempt approval, but every project safeguard",
                  r"every patch saved with its manifest", r"every created object deleted and verified", window=200)
        self.near(self.claude, "between", r"between tasks only", r"before a task", r"after a task",
                  r"one attempt per explorer\s+invocation", r"reads only each attempt's log entry",
                  r"user redirects between\s+attempts", window=300)
        self.near(self.claude, "promote", r"no extra\s+gate", r"observation, not an oracle")
        self.near(self.claude, "overnight", r"Overnight mode never grants or widens\s+`exploreAuthority`")

    def test_claude_md_lists_the_explorer(self):
        self.near(self.claude, "ownership", r"- explorer:", r"one Explore attempt per invocation", r"`exploreAuthority`",
                  r"never edits the checkout", r"never confirms a gate", window=400)

    def test_readme_lists_the_playbook_and_the_agent(self):
        self.near(self.readme, "playbook", r"sdd-explore.md", r"Explore → Promote")
        self.near(self.readme, "agent", r"explorer.md", r"One Explore attempt per invocation")
        self.near(self.readme, "count", r"14 agents")


if __name__ == "__main__":
    unittest.main(verbosity=2)
