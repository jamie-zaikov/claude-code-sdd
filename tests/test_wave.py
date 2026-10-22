#!/usr/bin/env python3
"""Behaviour tests for tools/sdd-wave.py in real git repositories (stdlib only)."""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
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


class SecurityGuardTest(WaveCase):
    def test_symlink_in_a_task_is_never_wave_safe(self):
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        (outside / "victim.txt").write_text("precious\n")
        wts = self.start()
        (wts["1"] / "a").mkdir(exist_ok=True)
        os.symlink(str(outside), wts["1"] / "a" / "link")
        self.assertIn("symlink (never wave-safe)", self.run_tool("check", "--task", "1")[1])
        self.assertEqual(self.run_tool("freeze", "--task", "1")[0], 1)

    def test_land_never_writes_through_a_symlinked_parent(self):
        """Reviewer repro: a link created by one task, a file under it from the other."""
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        (outside / "victim.txt").write_text("precious\n")
        link = self.repo / "a" / "sub"
        os.symlink(str(outside), link)  # an untracked link already in the checkout
        wts = self.start()
        self.write("a/sub/victim.txt", "attacker\n", wts["1"])
        self.run_tool("freeze", "--task", "1")
        self.run_tool("freeze", "--task", "2")
        code, out = self.run_tool("land")
        self.assertNotEqual(code, 0, out)
        self.assertEqual((outside / "victim.txt").read_text(), "precious\n")

    def test_safe_target_refuses_symlinked_parents_and_escapes(self):
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        os.symlink(str(outside), self.repo / "a" / "sub")
        for bad in ("a/sub/victim.txt", "../escape.txt", "/etc/x", "a/./b", "a//b"):
            with self.subTest(path=bad), self.assertRaises(wave.Failed):
                wave.safe_target(self.repo, bad)
        self.assertEqual(wave.safe_target(self.repo, "a/ok.py"), self.repo / "a" / "ok.py")
        os.symlink(str(self.repo / "b"), self.repo / "a" / "inner")  # a link that stays inside
        with self.assertRaises(wave.Failed):
            wave.safe_target(self.repo, "a/inner/y.py")  # any symlinked parent is refused

    def test_symlink_entries_are_refused_at_land_time(self):
        self.assertTrue(wave.unsafe_items([("A", "120000", "a/link")]))

    def test_case_colliding_paths_are_refused(self):
        items = [("A", "100644", "lib/Foo/x.py"), ("A", "100644", "lib/foo/y.py")]
        self.assertTrue(wave.unsafe_items(items))
        self.assertFalse(wave.unsafe_items([("A", "100644", "lib/foo/x.py"),
                                            ("A", "100644", "lib/foo/y.py")]))

    def test_owned_path_without_slash_still_covers_its_children(self):
        code, _ = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                                "--own", "1=lib/foo", "--own", "2=lib/foo/x.py")
        self.assertEqual(code, 2)

    def test_extend_refuses_a_prefix_of_the_other_tasks_path(self):
        self.start()
        self.assertEqual(self.run_tool("extend", "--task", "1", "--paths", "b")[0], 2)
        self.assertEqual(self.run_tool("extend", "--task", "1", "--paths", "tools")[0], 2)

    def test_unsafe_ids_are_refused(self):
        self.assertEqual(self.run_tool("prune", "--feature", "*")[0], 2)
        self.assertEqual(self.run_tool("start", "--feature", "../x", "--tasks", "1,2",
                                       "--attempt", "1")[0], 2)


class UserFileSafetyTest(WaveCase):
    def test_unland_keeps_user_files_written_after_the_land(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.write("USER-NOTES.md", "written after the land\n")
        self.write("shared.py", "s = 'user edit'\n")  # tracked, outside both tasks' ownership
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.repo / "USER-NOTES.md").read_text(), "written after the land\n")
        self.assertEqual((self.repo / "shared.py").read_text(), "s = 'user edit'\n")
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 1\n", "owned paths restored")
        refs = self.git("for-each-ref", "--format=%(refname)", "refs/sdd-wave/f/").split()
        snap = sorted(r for r in refs if "landed-" in r)[-1]
        self.assertNotIn("USER-NOTES.md", self.git("ls-tree", "-r", "--name-only", snap),
                         "user files never enter a wave ref")

    def test_discard_refuses_while_landed(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.assertEqual(self.run_tool("discard")[0], 2)
        self.run_tool("unland")
        self.assertEqual(self.run_tool("discard")[0], 0)


class RoundTwoTest(WaveCase):
    def mktree_commit(self, files):
        """A commit on base whose tree adds `files` (path -> (mode, content)) with no disk writes."""
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(self._tmp.name) / "idx"))
        subprocess.run(["git", "-C", str(self.repo), "read-tree", self.base], env=env, check=True)
        for path, (mode, content) in files.items():
            blob = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
                                  input=content.encode(), capture_output=True, check=True).stdout.decode().strip()
            subprocess.run(["git", "-C", str(self.repo), "update-index", "--add", "--cacheinfo",
                            f"{mode},{blob},{path}"], env=env, check=True)
        tree = subprocess.run(["git", "-C", str(self.repo), "write-tree"], env=env,
                              capture_output=True, check=True, text=True).stdout.strip()
        os.remove(Path(self._tmp.name) / "idx")
        return self.git("commit-tree", tree, "-p", self.base, "-m", "x").strip()

    def crafted_wave(self, a_files, b_files):
        self.start()
        state = wave.load(self.repo)
        for task, files in (("1", a_files), ("2", b_files)):
            ref = f"refs/t/{task}"
            self.git("update-ref", ref, self.mktree_commit(files))
            state["frozen"][task] = ref
        wave.save(self.repo, state)

    def test_refused_write_lands_nothing_and_never_wedges(self):
        """Reviewer H1: the victim does not exist yet, so collisions() alone misses it."""
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        os.symlink(str(outside), self.repo / "a" / "sub")
        self.crafted_wave({"a/aa.py": ("100644", "x\n"), "a/sub/new.txt": ("100644", "y\n")},
                          {"b/bb.py": ("100644", "z\n")})
        code, out = self.run_tool("land")
        self.assertEqual(code, 1, out)
        self.assertIn("nothing written", out)
        self.assertFalse((self.repo / "a/aa.py").exists(), "no partial land")
        self.assertFalse((outside / "new.txt").exists())
        self.assertEqual(wave.load(self.repo)["phase"], "started")
        self.assertEqual(self.run_tool("discard")[0], 0, "never wedged")

    def test_case_colliding_candidate_is_refused_at_land(self):
        self.crafted_wave({"Lib/a.py": ("100644", "a\n")}, {"lib/b.py": ("100644", "b\n")})
        code, out = self.run_tool("land")
        self.assertEqual(code, 1, out)
        self.assertIn("case-collides", out)

    def test_symlink_in_frozen_work_is_refused_at_adopt(self):
        self.crafted_wave({"a/link": ("120000", "/etc")}, {"b/bb.py": ("100644", "z\n")})
        self.assertEqual(self.run_tool("adopt", "--task", "1")[0], 1)
        self.assertFalse((self.repo / "a/link").is_symlink())

    def test_discard_refuses_while_landing(self):
        self.start()
        state = wave.load(self.repo)
        state["phase"] = "landing"
        wave.save(self.repo, state)
        self.assertEqual(self.run_tool("discard")[0], 2)

    def test_ownership_entries_must_be_plain_paths(self):
        for bad in (".", "..", "./a", "/abs", "a/../b", "a/*", ""):
            with self.subTest(entry=bad):
                code, _ = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                                        "--own", f"1=a/,{bad}" if bad else "1=a/,", "--own", "2=b/")
                if bad:
                    self.assertEqual(code, 2)
                self.run_tool("discard")
        self.start()
        self.assertEqual(self.run_tool("extend", "--task", "1", "--paths", ".")[0], 2)

    def test_owned_prefix_has_a_slash_boundary(self):
        state = {"own": {"1": ["a"]}, "casefold": False}
        self.assertTrue(wave.owned(state, "1", "a/x.py"))
        self.assertFalse(wave.owned(state, "1", "ab.py"))

    def test_owned_path_missing_everywhere_does_not_break_snapshot(self):
        code, _ = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                                "--own", "1=a/,docs/new.md", "--own", "2=b/,tools/run.sh")
        self.assertEqual(code, 0)
        root = self.repo / ".git" / "sdd-wave"
        self.write("a/x.py", "x = 2\n", root / "task-1")
        self.write("b/y.py", "y = 2\n", root / "task-2")
        self.run_tool("freeze", "--task", "1")
        self.run_tool("freeze", "--task", "2")
        self.assertEqual(self.run_tool("land")[0], 0)
        self.assertEqual(self.run_tool("snapshot")[0], 0)
        self.assertEqual(self.run_tool("unland")[0], 0)

    def test_pre_land_untracked_file_inside_ownership_survives_unland(self):
        self.write("a/notes.txt", "user file under an owned dir\n")
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertEqual((self.repo / "a/notes.txt").read_text(), "user file under an owned dir\n")

    def test_strays_lists_changes_outside_ownership(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.assertEqual(self.run_tool("strays"), (0, "ok\n"))
        self.write("shared.py", "s = 'repair went out of scope'\n")
        code, out = self.run_tool("strays")
        self.assertEqual(code, 1)
        self.assertIn("shared.py", out)

    @unittest.skipUnless(sys.platform == "darwin" or os.name == "nt", "needs a case-insensitive FS")
    def test_case_differing_ownership_on_a_casefold_repo(self):
        if self.git("config", "--bool", "core.ignorecase").strip() != "true":
            self.skipTest("repository is case-sensitive")
        code, _ = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                                "--own", "1=A/", "--own", "2=b/")
        self.assertEqual(code, 0)
        root = self.repo / ".git" / "sdd-wave"
        self.write("a/x.py", "x = 2\n", root / "task-1")
        self.write("b/y.py", "y = 2\n", root / "task-2")
        self.run_tool("freeze", "--task", "1")
        self.run_tool("freeze", "--task", "2")
        self.run_tool("land")
        self.write("a/repair.py", "r = 1\n")  # a repair file under the owned dir
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertFalse((self.repo / "a/repair.py").exists())


class RoundThreeTest(WaveCase):
    def own_start(self, own1, own2="b/"):
        code, out = self.run_tool("start", "--feature", "f", "--tasks", "1,2", "--attempt", "1",
                                  "--own", f"1={own1}", "--own", f"2={own2}")
        self.assertEqual(code, 0, out)
        return self.repo / ".git" / "sdd-wave"

    def land_new_package(self, root):
        self.write("newpkg/m.py", "m = 1\n", root / "task-1")
        self.write("b/y.py", "y = 2\n", root / "task-2")
        for task in ("1", "2"):
            self.assertEqual(self.run_tool("freeze", "--task", task)[0], 0)
        self.assertEqual(self.run_tool("land")[0], 0)

    def test_new_directory_unlands_cleanly_and_never_wedges(self):
        """Reviewer H1: the unland leaves an empty owned dir; the next snapshot must not fail."""
        # Run with the repository's own core.ignorecase: git sets it from the filesystem, and forcing
        # `false` on a case-insensitive one is a misconfiguration. macOS/Windows cover `true`
        # (where the reviewer's H1 reproduced), Linux covers `false`.
        # Linux git never writes core.ignorecase: `git config` exits 1 there, which means false.
        icase = subprocess.run(["git", "-C", str(self.repo), "config", "--bool", "core.ignorecase"],
                               capture_output=True, text=True).stdout.strip() or "false"
        for icase in (icase,):
            with self.subTest(ignorecase=icase):
                root = self.own_start("a/,newpkg/")
                self.land_new_package(root)
                code, out = self.run_tool("unland")
                self.assertEqual(code, 0, out)
                self.assertEqual(wave.load(self.repo)["phase"], "started")
                self.assertFalse((self.repo / "newpkg/m.py").exists())
                self.assertEqual(self.run_tool("discard")[0], 0)
                self.run_tool("prune", "--feature", "f")

    def test_wholly_ignored_owned_dir_never_wedges(self):
        root = self.own_start("a/,build.local/")
        self.write("a/x.py", "x = 2\n", root / "task-1")
        self.write("b/y.py", "y = 2\n", root / "task-2")
        self.write("build.local/out.txt", "ignored build output\n")
        for task in ("1", "2"):
            self.run_tool("freeze", "--task", task)
        self.run_tool("land")
        self.assertEqual(self.run_tool("snapshot")[0], 0)
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertEqual((self.repo / "build.local/out.txt").read_text(), "ignored build output\n")

    def test_bracket_route_paths_are_valid_ownership(self):
        self.own_start("app/[id]/page.tsx,a/")
        self.assertTrue(wave.valid_owned("src/(group)/x.ts"))
        self.assertFalse(wave.valid_owned("a\\b.py"), "backslash is never a POSIX path")

    def test_strays_ignores_pre_land_untracked_files_and_needs_a_land(self):
        self.write("USER.md", "mine, from before\n")
        wts = self.start()
        self.assertEqual(self.run_tool("strays")[0], 2, "not meaningful before the land")
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.assertEqual(self.run_tool("strays"), (0, "ok\n"))

    def test_owned_path_swapped_for_a_symlink_is_restored_not_followed(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        os.rename(self.repo / "a", self.repo / "a_moved")  # the user swaps the owned dir for a link
        os.symlink(str(outside), self.repo / "a")
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertEqual(wave.load(self.repo)["phase"], "started", "never wedged")
        self.assertEqual(list(outside.iterdir()), [], "nothing written through")
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 1\n", "owned path back at base")
        self.assertTrue((self.repo / "a_moved").is_dir(), "the user's moved dir is untouched")

    def test_unland_reports_a_refused_path_and_still_finishes(self):
        """A parent that NEITHER task owns becomes a symlink: the owned path under it is skipped."""
        root = self.own_start("a/sub/", "b/")
        self.write("a/sub/z.py", "z = 1\n", root / "task-1")
        self.write("b/y.py", "y = 2\n", root / "task-2")
        for task in ("1", "2"):
            self.run_tool("freeze", "--task", task)
        self.assertEqual(self.run_tool("land")[0], 0)
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        os.rename(self.repo / "a", self.repo / "a_moved")
        os.symlink(str(outside), self.repo / "a")
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertIn("skipped (refused, never written)", out)
        self.assertEqual(wave.load(self.repo)["phase"], "started", "never wedged")
        self.assertEqual(list(outside.iterdir()), [], "nothing written through")


class RoundFourTest(WaveCase):
    def test_clean_filter_on_an_untouched_owned_file_is_never_rewritten(self):
        """Reviewer H1: hashing without filters made an untouched filtered file look modified."""
        self.git("config", "filter.upper.clean", "tr a-z A-Z")
        self.git("config", "filter.upper.smudge", "cat")
        self.write(".gitattributes", "a/f.txt filter=upper\n")
        self.write("a/f.txt", "abc\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "filtered file")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write("a/f.txt", "abc\n")  # on disk the smudged form, as a checkout leaves it
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertEqual((self.repo / "a/f.txt").read_text(), "abc\n", "user file rewritten")

    def test_submodule_under_an_owned_dir_never_wedges(self):
        sub = Path(self._tmp.name) / "subrepo"
        sub.mkdir()
        run = lambda *a: subprocess.run(["git", "-C", str(sub), *a], check=True, capture_output=True)
        run("init", "-q")
        run("-c", "user.email=t@e", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "s")
        commit = subprocess.run(["git", "-C", str(sub), "rev-parse", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
        self.git("update-index", "--add", "--cacheinfo", f"160000,{commit},a/mod")
        self.git("commit", "-qm", "gitlink")
        (self.repo / "a" / "mod").mkdir()  # an unpopulated submodule: an empty directory
        self.base = self.git("rev-parse", "HEAD").strip()
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertEqual(wave.load(self.repo)["phase"], "started")

    @unittest.skipIf(os.name == "nt", "Windows file names cannot contain a newline")
    def test_newline_in_an_owned_file_name_never_wedges(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.write("a/odd\nname.py", "o = 1\n")
        self.assertEqual(self.run_tool("snapshot")[0], 0)
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertFalse((self.repo / "a/odd\nname.py").exists())

    def test_a_staged_new_owned_file_is_still_unlanded(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        self.write("a/staged.py", "s = 1\n")
        self.git("add", "a/staged.py")  # a repair that staged it
        self.assertEqual(self.run_tool("unland")[0], 0)
        self.assertFalse((self.repo / "a/staged.py").exists())


class RoundFiveTest(WaveCase):
    def test_file_turned_into_a_package_is_restored(self):
        """Reviewer H1: a repair replaces a/x.py with a/x.py/in.py; unland must not wedge."""
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        (self.repo / "a/x.py").unlink()
        self.write("a/x.py/in.py", "pkg = 1\n")
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.repo / "a/x.py").read_text(), "x = 1\n")
        self.assertEqual(wave.load(self.repo)["phase"], "started")

    def test_directory_turned_into_a_file_is_restored(self):
        self.write("a/d/f.py", "f = 1\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "dir")
        self.base = self.git("rev-parse", "HEAD").strip()
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        (self.repo / "a/d/f.py").unlink()
        (self.repo / "a/d").rmdir()
        self.write("a/d", "now a file\n")
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.repo / "a/d/f.py").read_text(), "f = 1\n")

    def test_package_holding_a_user_file_is_skipped_not_wedged(self):
        wts = self.start()
        self.work_and_freeze(wts)
        self.run_tool("land")
        (self.repo / "a/x.py").unlink()
        self.write("a/x.py/in.py", "pkg = 1\n")
        self.write("a/x.py/notes.local", "an ignored user file\n")
        code, out = self.run_tool("unland")
        self.assertEqual(code, 0, out)
        self.assertIn("skipped", out)
        self.assertEqual((self.repo / "a/x.py/notes.local").read_text(), "an ignored user file\n")
        self.assertEqual(wave.load(self.repo)["phase"], "started")


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
