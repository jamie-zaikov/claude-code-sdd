#!/usr/bin/env python3
"""The suite-record tree hash leaves `.specs/` out, except the spec files a project declares as
test inputs (`Suite spec inputs:` in tech.md).

Found in lab-automation-workflows (cellario-pcr-protocols, 2026-10-27): the tool copied the real
index, excluded `.specs/` only from `git add`, then wrote the tree — so committed spec entries
stayed in it, and a design-only commit changed the hash and forced another full suite (about 13
minutes). The same project's tests read `design.md`, so leaving every spec file out would let a spec
edit keep a stale PASS: the opt-in list keeps those files in the hash.

Run:
    python3 -m unittest tests.test_tree_identity -v
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from tests import prose
except ImportError:  # run from inside tests/
    import prose

ROOT = Path(__file__).resolve().parent.parent
HASH = ROOT / "tools" / "sdd-tree-hash.py"
OVERLAP = ROOT / "tools" / "sdd-overlap.py"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Repo:
    def __init__(self, path: Path):
        self.path = path
        self.git("init", "-q")
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.path), *args], check=True,
                              capture_output=True, text=True).stdout

    def write(self, rel, text):
        f = self.path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def hash(self):
        proc = subprocess.run([sys.executable, str(HASH)], cwd=self.path, capture_output=True,
                              text=True)
        return proc.returncode, proc.stdout.strip()


def seeded(tmp, inputs=None):
    repo = Repo(Path(tmp))
    repo.write("src/a.py", "a = 1\n")
    repo.write(".specs/features/f/design.md", "design 1\n")
    repo.write(".specs/features/f/tasks.md", "- [ ] 1\n")
    repo.write(".specs/steering/tech.md",
               "# Tech\n" + (f"- Suite spec inputs: {inputs}\n" if inputs else ""))
    repo.commit("seed")
    return repo


class SpecsLeftOutTest(unittest.TestCase):
    def test_a_committed_spec_change_keeps_the_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = seeded(tmp)
            rc, h1 = repo.hash()
            self.assertEqual(rc, 0)
            repo.write(".specs/features/f/design.md", "design 2\n")
            repo.write(".specs/features/f/tasks.md", "- [x] 1\n")
            self.assertEqual(repo.hash()[1], h1, "an uncommitted spec edit changed the hash")
            repo.commit("spec only")
            self.assertEqual(repo.hash()[1], h1, "a committed spec edit changed the hash")
            repo.write("src/a.py", "a = 2\n")
            self.assertNotEqual(repo.hash()[1], h1, "a code edit must change the hash")

    def test_the_hash_equals_the_code_tree_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = seeded(tmp)
            code_tree = repo.git("rev-parse", "HEAD:src").strip()
            listed = repo.git("ls-tree", repo.hash()[1]).split()
            self.assertEqual(listed[-2:], [code_tree, "src"], "only src/ belongs in the tree")
            self.assertFalse((Path(tmp) / ".git" / "index.lock").exists())


class SpecInputsTest(unittest.TestCase):
    def test_a_listed_spec_file_stays_in_the_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = seeded(tmp, ".specs/features/*/design.md")
            _, h1 = repo.hash()
            repo.write(".specs/features/f/tasks.md", "- [x] 1\n")
            repo.commit("unlisted")
            self.assertEqual(repo.hash()[1], h1, "an unlisted spec file changed the hash")
            repo.write(".specs/features/f/design.md", "design 2\n")
            _, h2 = repo.hash()
            self.assertNotEqual(h2, h1, "a listed spec file did not change the hash")
            repo.commit("listed")
            self.assertEqual(repo.hash()[1], h2, "a commit alone must not change the hash")
            (Path(tmp) / ".specs/features/f/design.md").unlink()
            self.assertNotEqual(repo.hash()[1], h2, "deleting a listed file did not change the hash")

    def test_several_globs_and_a_glob_that_matches_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = seeded(tmp, "`.specs/features/*/nothing.md`, .specs/steering/tech.md")
            rc, h1 = repo.hash()
            self.assertEqual(rc, 0, "a glob that matches nothing must not fail")
            self.assertRegex(h1, r"^[0-9a-f]{40}$")
            repo.write(".specs/steering/tech.md", repo.path.joinpath(".specs/steering/tech.md")
                       .read_text() + "more\n")
            self.assertNotEqual(repo.hash()[1], h1, "the second listed glob is not in the hash")

    def test_an_entry_outside_specs_fails_closed(self):
        for bad in ("src/*.py", ".specs/../src/a.py"):
            with tempfile.TemporaryDirectory() as tmp:
                repo = seeded(tmp, bad)
                rc, out = repo.hash()
                self.assertEqual(rc, 2, bad)
                self.assertEqual(out, "", f"{bad}: a refused hash must print nothing")


class OverlapSnapshotTest(unittest.TestCase):
    """The suite record's tree is an identity, not a snapshot: overlap start must still give the
    speculative worktree the committed specs, and must refuse a record that no longer matches."""

    def overlap(self, repo, *args):
        return subprocess.run([sys.executable, str(OVERLAP), *args], cwd=repo.path,
                              capture_output=True, text=True)

    def test_start_keeps_specs_and_checks_the_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = seeded(tmp)
            repo.write("src/a.py", "a = 2\n")  # task N's uncommitted work
            _, record = repo.hash()
            stale = self.overlap(repo, "start", "--task", "2", "--tree", "0" * 40)
            self.assertEqual(stale.returncode, 2, stale.stderr)
            started = self.overlap(repo, "start", "--task", "2", "--tree", record)
            self.assertEqual(started.returncode, 0, started.stderr)
            worktree = Path(started.stdout.split()[0])
            try:
                self.assertEqual((worktree / "src/a.py").read_text(), "a = 2\n")
                self.assertTrue((worktree / ".specs/features/f/design.md").is_file(),
                                "the speculative worktree lost the committed specs")
            finally:
                self.overlap(repo, "discard", "--task", "2")


class DocsTest(unittest.TestCase):
    def test_orchestrator_names_the_spec_inputs_exception(self):
        self.assertTrue(prose.near(read("agents/orchestrator.md"), r"`\.specs/` is excluded",
                                   r"except", r"`Suite spec inputs:`", r"stay in the hash"))

    def test_steering_template_offers_the_key(self):
        self.assertTrue(prose.search(read("steering-templates/tech.md"), r"Suite spec inputs:"))


if __name__ == "__main__":
    unittest.main()
