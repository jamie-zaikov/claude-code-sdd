#!/usr/bin/env python3
"""Git-level tests for tools/sdd-park.py — park never records a stash it did not create.

Review round 2 (High): with nothing outside `.specs/` to stash, `git stash push` exits 0 and
`stash@{0}` still names the user's own older stash, which unpark would then apply onto the feature
branch. Each test runs real git in a throwaway repo. Stdlib only.

Run:
    python3 -m unittest tests.test_park -v
"""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sdd_park", ROOT / "tools" / "sdd-park.py")
park = importlib.util.module_from_spec(spec)
spec.loader.exec_module(park)


class ParkTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        for args in (("init", "-q"), ("config", "user.email", "t@example.com"),
                     ("config", "user.name", "t")):
            self.git(*args)
        self.write("app.py", "a = 1\n")
        self.write(".specs/f/.spec-state.json", "{}\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def user_stash(self):
        self.write("app.py", "a = 'user wip'\n")
        self.git("stash", "push", "-m", "user wip")
        return self.git("rev-parse", "refs/stash").strip()

    def test_nothing_to_park_with_only_specs_dirty_returns_none(self):
        user = self.user_stash()
        self.write(".specs/f/.spec-state.json", '{"x": 1}\n')  # tracked state file is dirty
        self.assertEqual(park.park(self.repo, "2"), "none")
        self.assertEqual(self.git("rev-parse", "refs/stash").strip(), user)

    def test_park_returns_its_own_stash_never_the_users(self):
        user = self.user_stash()
        self.write("app.py", "a = 2\n")
        self.write("new_mod.py", "b = 1\n")
        ref = park.park(self.repo, "3")
        self.assertNotEqual(ref, user)
        self.assertTrue(park.subject(self.repo, ref).endswith("sdd-task-3-parked"))
        self.assertEqual(park.dirty(self.repo), [])
        self.assertFalse((self.repo / "new_mod.py").exists())

    def test_park_keeps_specs_changes_in_place(self):
        self.write("app.py", "a = 2\n")
        self.write(".specs/f/.spec-state.json", '{"keep": true}\n')
        park.park(self.repo, "4")
        self.assertEqual((self.repo / ".specs/f/.spec-state.json").read_text(), '{"keep": true}\n')

    def test_unpark_restores_the_work(self):
        self.write("app.py", "a = 2\n")
        self.write("new_mod.py", "b = 1\n")
        ref = park.park(self.repo, "5")
        park.unpark(self.repo, "5", ref)
        self.assertEqual((self.repo / "app.py").read_text(), "a = 2\n")
        self.assertEqual((self.repo / "new_mod.py").read_text(), "b = 1\n")

    def test_unpark_refuses_another_tasks_or_the_users_stash(self):
        user = self.user_stash()
        with self.assertRaises(park.Refused):
            park.unpark(self.repo, "5", user)
        self.write("app.py", "a = 2\n")
        ref = park.park(self.repo, "6")
        with self.assertRaises(park.Refused):
            park.unpark(self.repo, "7", ref)

    def test_unpark_refuses_a_dirty_tree(self):
        self.write("app.py", "a = 2\n")
        ref = park.park(self.repo, "8")
        self.write("app.py", "a = 3\n")
        with self.assertRaises(park.Refused):
            park.unpark(self.repo, "8", ref)

    def test_unpark_conflict_restores_the_clean_tree(self):
        self.write("app.py", "a = 2\n")
        self.write("new_mod.py", "b = 1\n")
        ref = park.park(self.repo, "9")
        self.write("app.py", "a = 'later task'\n")
        self.git("commit", "-qam", "later task changed the same line")
        with self.assertRaises(park.ConflictError):
            park.unpark(self.repo, "9", ref)
        self.assertEqual(park.dirty(self.repo), [])
        self.assertEqual((self.repo / "app.py").read_text(), "a = 'later task'\n")

    def _patched_stash_push(self, replacement):
        """Run park with `git stash push` replaced, to reach the defence-in-depth checks."""
        real = park.git

        def fake(repo, *args, **kw):
            if args[:2] == ("stash", "push"):
                return replacement(repo, real)
            return real(repo, *args, **kw)

        park.git = fake
        self.addCleanup(setattr, park, "git", real)

    def test_park_refuses_when_stash_push_saved_nothing(self):
        # The newest stash is an EARLIER park of the same task, so its message matches: only the
        # "refs/stash must move" check can tell that this push saved nothing.
        self.write("app.py", "a = 'first park'\n")
        self.git("stash", "push", "-m", "sdd-task-10-parked")
        user = self.git("rev-parse", "refs/stash").strip()
        self.write("app.py", "a = 2\n")
        self._patched_stash_push(lambda repo, real: real(repo, "status"))  # a no-op that exits 0
        with self.assertRaisesRegex(park.Refused, "created no entry"):
            park.park(self.repo, "10")
        self.assertEqual(self.git("rev-parse", "refs/stash").strip(), user)

    def test_park_refuses_a_stash_with_the_wrong_message(self):
        self.write("app.py", "a = 2\n")
        self._patched_stash_push(
            lambda repo, real: real(repo, "stash", "push", "--include-untracked", "-m", "other"))
        with self.assertRaises(park.Refused):
            park.park(self.repo, "11")

    def test_park_refuses_when_work_is_left_behind(self):
        self.write("app.py", "a = 2\n")
        self.write("new_mod.py", "b = 1\n")  # untracked: a push without -u leaves it behind
        self._patched_stash_push(
            lambda repo, real: real(repo, "stash", "push", "-m", "sdd-task-12-parked"))
        with self.assertRaisesRegex(park.Refused, "still dirty"):
            park.park(self.repo, "12")

    def test_cli_exit_codes(self):
        self.assertEqual(park.main(["-C", str(self.repo), "park", "--task", "1"]), 0)
        self.assertEqual(park.main(["-C", str(self.repo), "unpark", "--task", "1",
                                    "--ref", "HEAD"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
