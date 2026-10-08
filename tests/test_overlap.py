#!/usr/bin/env python3
"""Git-level tests for tools/sdd-overlap.py — Level 1 stage overlap (task N+1 runs during N's reviews).

Run:
    python3 -m unittest tests.test_overlap -v
"""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sdd_overlap", ROOT / "tools" / "sdd-overlap.py")
ov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ov)


class OverlapTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name).resolve()
        for args in (("init", "-q"), ("config", "user.email", "t@example.com"),
                     ("config", "user.name", "t")):
            self.git(*args)
        self.write("src/a.py", "a = 1\n")
        self.write(".specs/f/.spec-state.json", "{}\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        # Task N's finished work, not yet committed (its reviews are running).
        self.write("src/n.py", "n = 1\n")
        self.write("src/a.py", "a = 2\n")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def write(self, rel, text, root=None):
        path = (root or self.repo) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def start(self, task="2"):
        path, base = ov.start(self.repo, task, None).split()
        return Path(path), base

    def commit_task_n(self):
        self.write(".specs/f/.spec-state.json", '{"n": "complete"}\n')  # state file stays dirty
        self.git("add", "src")
        self.git("commit", "-qm", "Task N")

    def test_land_moves_the_work_into_the_main_checkout(self):
        wt, base = self.start()
        self.assertEqual((wt / "src" / "n.py").read_text(), "n = 1\n")  # N's work is the base
        self.write("src/m.py", "m = 1\n", root=wt)
        self.write("src/n.py", "n = 1\nn_plus = 2\n", root=wt)
        self.commit_task_n()
        ov.land(self.repo, "2", base)
        self.assertEqual((self.repo / "src" / "m.py").read_text(), "m = 1\n")
        self.assertEqual((self.repo / "src" / "n.py").read_text(), "n = 1\nn_plus = 2\n")
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")  # unstaged
        self.assertEqual((self.repo / ".specs/f/.spec-state.json").read_text(), '{"n": "complete"}\n')
        self.assertFalse(wt.exists())
        self.assertEqual(ov.existing(self.repo), [])

    def test_land_refuses_when_task_n_changed_after_the_snapshot(self):
        wt, base = self.start()
        self.write("src/m.py", "m = 1\n", root=wt)
        self.write("src/n.py", "n = 'fixed in a fix round'\n")
        self.commit_task_n()
        with self.assertRaises(ov.Stale):
            ov.land(self.repo, "2", base)
        self.assertFalse((self.repo / "src" / "m.py").exists())
        ov.discard(self.repo, "2")
        self.assertFalse(wt.exists())

    def test_land_refuses_before_task_n_is_committed(self):
        _, base = self.start()
        with self.assertRaises(ov.Refused):
            ov.land(self.repo, "2", base)

    def test_only_one_speculation_at_a_time(self):
        self.start("2")
        with self.assertRaises(ov.Refused):
            self.start("3")

    def test_start_accepts_the_suite_record_tree(self):
        tree = ov.tree_of(self.repo)
        path, base = ov.start(self.repo, "2", tree).split()
        self.assertEqual(self.git("rev-parse", f"{base}^{{tree}}").strip(), tree)
        ov.discard(self.repo, "2")
        with self.assertRaises(ov.Refused):
            ov.start(self.repo, "3", "0" * 40)

    # --- review round 1 ---
    def test_an_untracked_user_file_never_blocks_the_land(self):
        self.write("AGENTS.md", "user's own untracked file\n")
        wt, base = self.start()
        self.write("src/m.py", "m = 1\n", root=wt)
        self.commit_task_n()
        ov.land(self.repo, "2", base)
        self.assertEqual((self.repo / "src" / "m.py").read_text(), "m = 1\n")
        self.assertEqual((self.repo / "AGENTS.md").read_text(), "user's own untracked file\n")

    def test_an_orphaned_directory_is_discarded_and_unblocks_start(self):
        wt, _ = self.start()
        self.git("worktree", "remove", "--force", str(wt))
        wt.mkdir(parents=True)
        (wt / "stray.py").write_text("written by a live executor after removal\n")
        with self.assertRaises(ov.Refused):
            self.start("3")
        ov.discard(self.repo, "2")
        self.assertFalse(wt.exists())
        self.start("3")

    def test_snapshot_never_includes_specs_changes(self):
        self.write(".specs/f/.spec-state.json", '{"dirty": true}\n')
        wt, _ = self.start()
        self.assertEqual((wt / ".specs/f/.spec-state.json").read_text(), "{}\n")

    def test_main_checkout_is_untouched_by_start_and_discard(self):
        before = self.git("status", "--porcelain")
        self.start()
        ov.discard(self.repo, "2")
        self.assertEqual(self.git("status", "--porcelain"), before)

    def test_cli_exit_codes(self):
        self.assertEqual(ov.main(["-C", str(self.repo), "start", "--task", "2"]), 0)
        base = self.git("rev-parse", "HEAD").strip()
        self.write("src/n.py", "changed\n")
        self.git("add", "src")
        self.git("commit", "-qm", "Task N, different content")
        self.assertEqual(ov.main(["-C", str(self.repo), "land", "--task", "2", "--base", base]), 1)
        self.assertEqual(ov.main(["-C", str(self.repo), "discard", "--task", "2"]), 0)
        self.assertEqual(ov.main(["-C", str(self.repo), "land", "--task", "9", "--base", base]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
