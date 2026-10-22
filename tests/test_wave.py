#!/usr/bin/env python3
"""Behaviour tests for tools/sdd-wave.py in real git repositories (stdlib only)."""

import contextlib
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sdd_wave", ROOT / "tools" / "sdd-wave.py")
wave = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wave)


class WaveCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("a/x.py", "x = 1\n")
        self.write("b/y.py", "y = 1\n")
        self.write("shared.py", "s = 1\n")
        self.write(".gitignore", "*.local\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        subprocess.run(["git", "-C", str(self.repo), "worktree", "prune"], capture_output=True)
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def write(self, rel, text, root=None):
        path = (root or self.repo) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_tool(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = wave.main(["-C", str(self.repo), *argv])
        return code, out.getvalue() + err.getvalue()

    def start(self, attempt="1"):
        code, out = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", attempt,
                                  "--own", "1=a/", "--own", "2=b/,tools/run.sh")
        self.assertEqual(code, 0, out)
        return {line.split()[0]: Path(line.split()[1]) for line in out.splitlines()
                if not line.startswith("base")}

    def work_and_freeze(self, wts):
        self.write("a/x.py", "x = 2\n", wts["1"])
        self.write("a/new.py", "n = 1\n", wts["1"])
        self.write("b/y.py", "y = 2\n", wts["2"])
        script = self.write("tools/run.sh", "#!/bin/sh\necho hi\n", wts["2"])
        script.chmod(0o755)
        for task in ("1", "2"):
            code, out = self.run_tool("freeze", "--task", task)
            self.assertEqual(code, 0, out)


class HappyPathTest(WaveCase):
    def test_land_writes_the_combined_candidate_without_touching_the_index(self):
        self.write("NOTES.md", "user's own untracked file\n")
        wts = self.start()
        self.work_and_freeze(wts)
        code, out = self.run_tool("land")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 2\n")
        self.assertEqual((self.repo / "b/y.py").read_text(), "y = 2\n")
        self.assertTrue(os.access(self.repo / "tools/run.sh", os.X_OK), "exec bit kept")
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "", "index untouched")
        self.assertEqual((self.repo / "NOTES.md").read_text(), "user's own untracked file\n")
        gated = wave.tree_of(self.repo)
        self.git("add", "a/x.py", "a/new.py")
        self.git("commit", "-qm", "task 1")
        code, out = self.run_tool("verify", "--gated-tree", gated)
        self.assertEqual(code, 1, "task 2's paths are not committed yet")
        self.assertIn("b/y.py", out)
        self.git("add", "b/y.py", "tools/run.sh")
        self.git("commit", "-qm", "task 2")
        self.assertEqual(self.run_tool("verify", "--gated-tree", gated), (0, "ok\n"),
                         "NOTES.md was untracked before the land and is never counted")

    def test_deletion_lands(self):
        wts = self.start()
        (wts["1"] / "a/x.py").unlink()
        self.write("b/y.py", "y = 3\n", wts["2"])
        for task in ("1", "2"):
            self.run_tool("freeze", "--task", task)
        code, out = self.run_tool("land")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.repo / "a/x.py").exists())


class OwnershipTest(WaveCase):
    def test_overlapping_ownership_is_refused(self):
        code, _ = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                                "--own", "1=a/", "--own", "2=a/sub/z.py")
        self.assertEqual(code, 2)

    def test_path_outside_ownership_blocks_freeze_until_extended(self):
        wts = self.start()
        self.write("shared.py", "s = 2\n", wts["1"])
        code, out = self.run_tool("check", "--task", "1")
        self.assertEqual(code, 1)
        self.assertIn("shared.py: outside task 1's ownership", out)
        self.assertEqual(self.run_tool("freeze", "--task", "1")[0], 1)
        self.assertEqual(self.run_tool("extend", "--task", "1", "--paths", "shared.py")[0], 0)
        self.assertEqual(self.run_tool("check", "--task", "1"), (0, "ok\n"))

    def test_path_owned_by_the_other_task_cannot_be_extended(self):
        wts = self.start()
        self.write("b/y.py", "y = 9\n", wts["1"])
        self.assertIn("owned by task 2", self.run_tool("check", "--task", "1")[1])
        self.assertEqual(self.run_tool("extend", "--task", "1", "--paths", "b/y.py")[0], 2)

    def test_lockfile_is_flagged_env_changing(self):
        wts = self.start()
        self.write("uv.lock", "x\n", wts["1"])
        self.assertIn("env-changing", self.run_tool("check", "--task", "1")[1])


class GuardTest(WaveCase):
    def test_ignored_user_file_collision_refuses_the_land(self):
        wts = self.start()
        self.write("a/conf.local", "secret local config\n")  # ignored in main
        self.write("a/conf.local", "task content\n", wts["1"])
        self.git("-C", str(wts["1"]), "add", "-f", "a/conf.local")  # the task force-adds it
        self.run_tool("freeze", "--task", "1")
        self.run_tool("freeze", "--task", "2")
        code, out = self.run_tool("land")
        self.assertEqual(code, 1, out)
        self.assertIn("a/conf.local (already on disk)", out)
        self.assertEqual((self.repo / "a/conf.local").read_text(), "secret local config\n")

    def test_stale_checkout_refuses_the_land(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.write("shared.py", "s = 5\n")
        self.git("commit", "-qam", "moved")
        self.assertEqual(self.run_tool("land")[0], 1)
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 1\n", "nothing written")

    def test_second_wave_or_dirty_checkout_or_speculation_is_refused(self):
        self.start()
        self.assertEqual(self.run_tool("start", "--feature", "f", "--tasks", "3,4", "--attempt",
                                       "1")[0], 2)
        self.run_tool("discard")
        self.write("shared.py", "dirty\n")
        self.assertEqual(self.start_code(), 2)
        self.git("checkout", "--", "shared.py")
        ovl = self.repo / ".git" / "sdd-overlap" / "task-9"
        ovl.mkdir(parents=True)
        self.assertEqual(self.start_code(), 2)

    def start_code(self):
        return self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                             "--own", "1=a/", "--own", "2=b/")[0]

    def test_frozen_refs_are_never_overwritten(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("discard")  # refs kept
        wts = self.start()  # same feature, tasks and attempt
        self.write("a/x.py", "x = 7\n", wts["1"])
        self.assertEqual(self.run_tool("freeze", "--task", "1")[0], 2)
        self.run_tool("discard")
        self.assertEqual(self.run_tool("prune", "--feature", "f"), (0, "dropped 2 ref(s)\n"))


class UnlandAndAdoptTest(WaveCase):
    def test_unland_undoes_post_land_repairs_and_keeps_them_in_a_ref(self):
        self.write("NOTES.md", "user's own untracked file\n")
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.run_tool("snapshot")
        self.write("a/x.py", "x = 3  # repair\n")
        self.write("a/helper.py", "h = 1\n")  # a file only the repair added
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 1\n")
        self.assertFalse((self.repo / "a/helper.py").exists())
        self.assertFalse((self.repo / "a/new.py").exists())
        self.assertEqual((self.repo / "NOTES.md").read_text(), "user's own untracked file\n")
        refs = self.git("for-each-ref", "--format=%(refname)", "refs/sdd-wave/f/").split()
        last = sorted(r for r in refs if "landed-" in r)[-1]
        self.assertEqual(self.git("show", f"{last}:a/helper.py"), "h = 1\n", "repair work kept")

    def test_adopt_in_sequence_after_fallback(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.run_tool("unland")
        self.assertEqual(self.run_tool("adopt", "--task", "1")[0], 0)
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 2\n")
        self.git("add", "a/x.py", "a/new.py")
        self.git("commit", "-qm", "task 1 in sequence")
        self.assertEqual(self.run_tool("adopt", "--task", "2")[0], 0)
        self.assertEqual((self.repo / "b/y.py").read_text(), "y = 2\n")

    def test_adopt_refuses_a_moved_path_and_writes_the_patch(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.write("a/x.py", "x = 99\n")  # the path changed since the base
        patch = Path(self._tmp.name) / "task-1.patch"
        code, out = self.run_tool("adopt", "--task", "1", "--patch-out", str(patch))
        self.assertEqual(code, 1, out)
        self.assertIn("a/x.py", out)
        self.assertIn("+x = 2", patch.read_text())
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 99\n", "nothing overwritten")


class ConflictTest(WaveCase):
    def test_same_path_changed_by_both_is_a_conflict_and_lands_nothing(self):
        """Ownership normally prevents it; the candidate build must still catch it."""
        def commit_with(text):
            self.write("shared.py", text)
            tree = wave.tree_of(self.repo)
            self.git("checkout", "--", "shared.py")
            return self.git("commit-tree", tree, "-p", self.base, "-m", "x").strip()
        a, b = commit_with("s = 'A'\n"), commit_with("s = 'B'\n")
        self.git("update-ref", "refs/t/a", a)
        self.git("update-ref", "refs/t/b", b)
        state = {"feature": "f", "tasks": ["1", "2"], "attempt": 1, "base": self.base,
                 "frozen": {"1": "refs/t/a", "2": "refs/t/b"}}
        with self.assertRaises(wave.Failed):
            wave.candidate(self.repo, state)
        self.assertEqual((self.repo / "shared.py").read_text(), "s = 1\n")


class SpecRevTest(unittest.TestCase):
    def test_checkbox_state_never_changes_the_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "tasks.md").write_text("- [ ] 1. Do it\n")
            before = wave.spec_rev(d)
            (d / "tasks.md").write_text("- [x] 1. Do it\n")
            (d / ".spec-state.json").write_text("{}")
            self.assertEqual(wave.spec_rev(d), before)
            (d / "tasks.md").write_text("- [x] 1. Do something else\n")
            self.assertNotEqual(wave.spec_rev(d), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
