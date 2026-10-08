#!/usr/bin/env python3
"""Unit tests for tools/sdd-module-size.py — the mechanical "no god files" ratchet.

Each test builds a throwaway git repo, so the check runs against real `git diff` / `git show`
output. Stdlib only.

Run:
    python3 -m unittest tests.test_module_size -v
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "sdd-module-size.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("sdd_module_size", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = load_tool()


def lines(n):
    return "".join(f"x{i} = {i}\n" for i in range(n))


class RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def run_tool(self, *extra):
        return tool.main(["-C", str(self.repo), *extra])


class RatchetTest(RepoCase):
    def setUp(self):
        super().setUp()
        self.write("small.py", lines(10))
        self.write("god.py", lines(30))
        self.commit()

    def test_new_file_over_limit_violates(self):
        self.write("new.py", lines(21))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [("new.py", 0, 21)])

    def test_file_crossing_limit_violates(self):
        self.write("small.py", lines(21))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [("small.py", 10, 21)])

    def test_god_file_that_grows_violates(self):
        self.write("god.py", lines(31))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [("god.py", 30, 31)])

    def test_god_file_that_holds_or_shrinks_is_ok(self):
        self.write("god.py", lines(30).replace("x0 = 0", "x0 = 99"))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [])
        self.write("god.py", lines(12))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [])

    def test_file_at_the_limit_is_ok(self):
        self.write("small.py", lines(20))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [])

    def test_non_code_suffix_is_never_checked(self):
        self.write("notes.md", lines(500))
        self.write("data.json", lines(500))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [])

    def test_exempt_glob_skips_a_file(self):
        self.write("gen/big_pb2.py", lines(50))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, ["gen/*"]), [])

    def test_exit_codes(self):
        self.assertEqual(self.run_tool("--limit", "20"), 0)
        self.write("new.py", lines(21))
        self.assertEqual(self.run_tool("--limit", "20"), 1)
        self.assertEqual(self.run_tool("--base", "no-such-ref"), 2)


class RoundTwoTest(RepoCase):
    """Review round 2: renames, merge-base, quoted paths, and the CLI options."""

    def setUp(self):
        super().setUp()
        self.write("big.py", lines(30))
        self.write("small.py", lines(5))
        self.commit()

    def test_git_mv_of_a_god_file_is_not_new(self):
        self.git("mv", "big.py", "core.py")
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [])

    def test_unstaged_move_of_a_god_file_is_not_new(self):
        (self.repo / "big.py").rename(self.repo / "pkg_core.py")
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [])

    def test_renamed_god_file_that_grows_still_violates(self):
        self.git("mv", "big.py", "core.py")
        self.write("core.py", lines(31))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [("core.py", 30, 31)])

    def test_non_ascii_path_is_checked(self):
        self.write("caf\u00e9.py", lines(21))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [("caf\u00e9.py", 0, 21)])

    def test_merge_base_ignores_changes_on_the_base_branch(self):
        self.git("branch", "-M", "main")
        self.git("checkout", "-q", "-b", "feature")
        self.write("small.py", lines(6))
        self.git("commit", "-qam", "feature work")
        self.git("checkout", "-q", "main")
        self.write("big.py", lines(10))  # main splits the god file after the branch point
        self.git("commit", "-qam", "split on main")
        self.git("checkout", "-q", "feature")
        self.assertEqual(self.run_tool("--base", "main", "--limit", "20"), 1)  # tip: wrongly blamed
        self.assertEqual(self.run_tool("--base", "main", "--merge-base", "--limit", "20"), 0)

    def test_paths_filter_ignores_unrelated_scratch_files(self):
        self.write("scratch.py", lines(99))
        self.write("small.py", lines(6))
        self.assertEqual(self.run_tool("--limit", "20", str(self.repo / "small.py")), 0)
        self.assertEqual(self.run_tool("--limit", "20"), 1)

    def test_waiver_reports_but_does_not_fail(self):
        self.write("big.py", lines(31))
        self.assertEqual(self.run_tool("--limit", "20", "--waive", "big.py"), 0)
        self.assertEqual(self.run_tool("--limit", "20"), 1)

    def test_limit_zero_is_honoured(self):
        self.write("small.py", lines(6))
        self.assertEqual(self.run_tool("--limit", "0"), 1)

    def test_root_file_matches_double_star_glob(self):
        self.write("foo_pb2.py", lines(99))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, ["**/*_pb2.py"]), [])

    def test_bold_steering_line_is_read(self):
        self.write(".specs/steering/tech.md", "- **Module size limit:** 7 lines\n")
        self.assertEqual(tool.steering_config(self.repo)[0], 7)


class RoundThreeTest(RepoCase):
    """Review round 3: path forms in task mode, type changes, untracked data files."""

    def setUp(self):
        super().setUp()
        self.write("src/seed.py", lines(1))
        self.commit()
        self.write("src/big.py", lines(30))

    def in_dir(self, rel, *argv):
        import os
        old = os.getcwd()
        os.chdir(self.repo / rel)
        try:
            return tool.main(list(argv))
        finally:
            os.chdir(old)

    def test_every_path_form_is_checked(self):
        for form in ("src/big.py", "./src/big.py", str(self.repo / "src" / "big.py")):
            self.assertEqual(self.in_dir(".", "--limit", "20", form), 1, form)
        self.assertEqual(self.in_dir("src", "--limit", "20", "big.py"), 1, "subdir-relative")

    def test_path_outside_the_repo_is_an_error(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(self.in_dir(".", "--limit", "20", other + "/x.py"), 2)

    def test_unchanged_path_warns_and_is_not_silently_passed(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.in_dir(".", "--limit", "20", "src/seed.py")
        self.assertIn("not in the changed set", err.getvalue())

    def test_symlink_replaced_by_a_big_file_is_checked(self):
        (self.repo / "src" / "big.py").unlink()
        (self.repo / "link.py").symlink_to("src/seed.py")
        self.commit()
        (self.repo / "link.py").unlink()
        self.write("link.py", lines(30))
        self.assertEqual(tool.check(self.repo, "HEAD", 20, []), [("link.py", 1, 30)])

    def test_untracked_data_file_is_never_hashed(self):
        self.write("dump.csv", "x" * 1000 + "\n")
        tool.check(self.repo, "HEAD", 20, [])
        objects = subprocess.run(["git", "-C", str(self.repo), "cat-file", "--batch-all-objects",
                                  "--batch-check"], capture_output=True, text=True).stdout
        blob = subprocess.run(["git", "-C", str(self.repo), "hash-object", "dump.csv"],
                              capture_output=True, text=True).stdout.strip()
        self.assertNotIn(blob, objects, "an untracked data file was written into .git/objects")


class SteeringConfigTest(RepoCase):
    def test_limit_and_exempt_come_from_tech_md(self):
        self.write(".specs/steering/tech.md",
                   "## Modularity\n- Module size limit: 15 lines\n- Module size exempt: `vendor/*`, legacy.py\n")
        self.write("seed.py", lines(1))
        self.commit()
        self.write("a.py", lines(16))
        self.write("vendor/b.py", lines(99))
        self.write("legacy.py", lines(99))
        self.assertEqual(self.run_tool(), 1)
        limit, exempt = tool.steering_config(self.repo)
        self.assertEqual(limit, 15)
        self.assertEqual(exempt, ["vendor/*", "legacy.py"])
        self.write("a.py", lines(15))
        self.assertEqual(self.run_tool(), 0)

    def test_default_limit_without_steering(self):
        self.write("seed.py", lines(1))
        self.commit()
        self.write("a.py", lines(tool.DEFAULT_LIMIT))
        self.assertEqual(self.run_tool(), 0)
        self.write("a.py", lines(tool.DEFAULT_LIMIT + 1))
        self.assertEqual(self.run_tool(), 1)


class CliTest(unittest.TestCase):
    def test_script_compiles_and_runs_help(self):
        proc = subprocess.run([sys.executable, str(TOOL), "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
