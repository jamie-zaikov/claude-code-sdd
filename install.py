#!/usr/bin/env python3
"""SDD Global Installer for Claude Code (stdlib only, Python >= 3.9).

Installs agents, commands, tools and CLAUDE.md into the Claude config directory, and optionally
the secret-handling safeguards (settings.json deny rules + guard/redact hooks) and the SDD CI
pre-push hook. `install.sh` (POSIX / Git Bash) and `install.ps1` (PowerShell) are thin shims
that find a Python interpreter and run this file with the same arguments.

Destination: --claude-home PATH, else $CLAUDE_CONFIG_DIR, else ~/.claude (shared with uninstall).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sdd_install import MIN_PYTHON  # noqa: E402
from sdd_install import settings as sdd_settings  # noqa: E402
from sdd_install.common import (  # noqa: E402
    InstallError, ask, copy_file, err, files_equal, info, line, load_manifest, new_manifest,
    ok, rel, resolve_claude_home, save_manifest, sha256_file, warn, yes,
)
from sdd_install.verify import check_guard, check_redact, verify_settings  # noqa: E402

HOOK_SENTINEL = "# >>> sdd-pre-push (managed) >>>"
NOT_PROTECTED = "NOT PROTECTED: the secret-handling safeguards are not installed."


def parse_args(argv):
    p = argparse.ArgumentParser(description="Install the SDD framework for Claude Code.")
    p.add_argument("--claude-home", help="destination (default: $CLAUDE_CONFIG_DIR or ~/.claude)")
    p.add_argument("-y", "--yes", action="store_true",
                   help="non-interactive: enable secret handling and the pre-push hook, keep a "
                        "differing CLAUDE.md, never edit a shell profile (flags below override)")
    p.add_argument("--hooks", dest="hooks", action="store_true", default=None,
                   help="enable the secret-handling safeguards without asking")
    p.add_argument("--no-hooks", dest="hooks", action="store_false",
                   help="skip the secret-handling safeguards")
    p.add_argument("--pre-push", dest="pre_push", action="store_true", default=None,
                   help="install the SDD CI pre-push hook without asking")
    p.add_argument("--no-pre-push", dest="pre_push", action="store_false",
                   help="skip the SDD CI pre-push hook")
    p.add_argument("--claude-md", choices=("overwrite", "append", "skip"),
                   help="what to do when an existing CLAUDE.md differs")
    p.add_argument("--shell-profile", dest="shell_profile", action="store_true", default=None,
                   help="add CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 to the shell profile")
    p.add_argument("--no-shell-profile", dest="shell_profile", action="store_false")
    p.add_argument("--verify", action="store_true",
                   help="only verify the installed safeguards (runs the exact hook commands)")
    return p.parse_args(argv)


def decide(flag, assume_yes, prompt, default_yes):
    """Explicit flag wins; --yes takes `default_yes`; otherwise ask (EOF = No)."""
    if flag is not None:
        return flag
    if assume_yes:
        return default_yes
    return yes(ask(prompt, "n"))


def hook_python() -> str:
    """The absolute interpreter the hooks run with: this interpreter, via a stable PATH name if any."""
    exe = sys.executable
    if not exe or not os.path.isfile(exe):
        raise InstallError("cannot resolve the absolute path of the running Python interpreter.")
    for name in ("python3", "python"):
        cand = shutil.which(name)
        if cand and os.path.realpath(cand) == os.path.realpath(exe):
            return os.path.abspath(cand)
    return os.path.abspath(exe)


class Installer:
    def __init__(self, args):
        self.args = args
        self.home = resolve_claude_home(args.claude_home)
        self.manifest = load_manifest(self.home) or new_manifest()
        self.protected = None  # None = not requested, True = verified, False = failed

    # ---- file copies --------------------------------------------------------
    def record(self, dest: Path) -> None:
        self.manifest["files"][rel(self.home, dest)] = sha256_file(dest)

    def install_dir(self, label: str, src_dir: Path, pattern: str, dest_dir: Path,
                    executable: bool = False) -> None:
        info(f"Installing {label}...")
        count = 0
        for src in sorted(src_dir.glob(pattern)):
            if not src.is_file():
                continue
            dest = dest_dir / src.name
            if files_equal(src, dest):
                line(f"       {src.name} (unchanged, skipped)")
            else:
                existed = dest.exists()
                copy_file(src, dest, executable=executable)
                ok(f"    {src.name} ({'updated' if existed else 'installed'})")
                count += 1
            self.record(dest)
        if count == 0:
            info(f"All {label} already up to date.")
        else:
            ok(f"{count} {label} file(s) installed/updated.")
        line()

    def install_claude_md(self) -> None:
        info("Installing global CLAUDE.md...")
        src, dest = ROOT / "CLAUDE.md", self.home / "CLAUDE.md"
        if not dest.exists():
            copy_file(src, dest)
            ok("CLAUDE.md installed.")
        elif files_equal(src, dest):
            info("CLAUDE.md already up to date.")
        else:
            warn(f"{dest} already exists and differs.")
            choice = self.args.claude_md
            if choice is None and self.args.yes:
                choice = "skip"
            if choice is None:
                line("\n  Options:\n    [o] Overwrite with SDD version\n"
                     "    [a] Append SDD instructions to existing file\n    [s] Skip (keep current file)\n")
                choice = {"o": "overwrite", "a": "append"}.get(ask("  Choice (o/a/s): ", "s").lower(), "skip")
            if choice == "overwrite":
                copy_file(src, dest)
                ok("CLAUDE.md overwritten.")
            elif choice == "append":
                with open(dest, "a", encoding="utf-8", newline="\n") as f:
                    f.write("\n---\n\n" + src.read_text(encoding="utf-8"))
                ok("SDD instructions appended to CLAUDE.md.")
            else:
                info("CLAUDE.md skipped.")
        line()

    # ---- secret handling ----------------------------------------------------
    def install_secret_handling(self) -> None:
        info("Secret-handling safeguards (deny secret reads + guard/redact hooks)...")
        line("\n  This blocks reading known secret stores (.env, ~/.aws, ~/.ssh, keys, ...)\n"
             "  and installs Bash/PowerShell hooks that stop secret dumps and redact leaked tokens.\n"
             f"  It edits {self.home / 'settings.json'} (a backup is written) and is idempotent.\n")
        if not decide(self.args.hooks, self.args.yes, "  Enable secret handling now? (y/N) ", True):
            info("Secret handling skipped. Enable later by re-running with --hooks.")
            line()
            return
        self.protected = False
        hooks_dir = self.home / "hooks"
        for name in sorted(sdd_settings.MANAGED_HOOKS.values()):
            dest = hooks_dir / name
            copy_file(ROOT / "hooks" / name, dest, executable=True)
            self.record(dest)
        ok(f"{len(sdd_settings.MANAGED_HOOKS)} hook script(s) copied to {hooks_dir}.")
        python = hook_python()
        # Prove the exact commands work BEFORE registering them, so a broken interpreter or
        # script never lands in settings.json looking like protection.
        problems = check_guard([python, str(hooks_dir / sdd_settings.GUARD)])
        problems += check_redact([python, str(hooks_dir / sdd_settings.REDACT)])
        if problems:
            raise InstallError("hook self-test failed:\n  - " + "\n  - ".join(problems))
        path = self.home / "settings.json"
        current, original_text = sdd_settings.load(path)
        new, added = sdd_settings.merge(current, python, hooks_dir)
        backup = sdd_settings.save(path, new, original_text)
        owned = self.manifest["deny_added"]
        owned.extend(r for r in added if r not in owned)
        written, _ = sdd_settings.load(path)
        problems = verify_settings(written)
        if problems:
            raise InstallError(f"{path} does not verify after writing:\n  - " + "\n  - ".join(problems))
        self.protected = True
        if backup:
            ok(f"Deny rules + hooks registered in {path} (backup: {backup.name}).")
        else:
            ok(f"Deny rules + hooks already registered in {path} (unchanged).")
        ok(f"Hooks verified: exact registered commands deny dumps and redact output (interpreter: {python}).")
        line()

    # ---- pre-push hook --------------------------------------------------------
    def install_pre_push(self) -> None:
        info("SDD CI pre-push hook (advisory local secret-scan + build/test/lint)...")
        hook_src = ROOT / "ci-templates" / "hooks" / "pre-push"
        if not hook_src.is_file():
            warn(f"Hook template not found at {hook_src} - skipping pre-push hook setup.")
            line()
            return
        line("\n  This installs an advisory git pre-push hook into THIS repository. Before a\n"
             "  push it runs the shared secret scanner and scripts/ci.sh (if present) over\n"
             "  the pushed range, mirroring the CI gates. It is idempotent and never\n"
             "  overwrites a pre-existing non-SDD hook; CI still enforces the same checks\n"
             "  server-side. Bypass locally with: git push --no-verify.\n")
        if not decide(self.args.pre_push, self.args.yes,
                      "  Install the SDD CI pre-push hook into this repository? (y/N) ", True):
            info("Pre-push hook skipped.")
            line()
            return
        self._repo_hook(hook_src)
        self._stage_templates(hook_src)
        line()

    def _repo_hook(self, hook_src: Path) -> None:
        git = shutil.which("git")
        res = None
        if git:
            res = subprocess.run([git, "-C", str(ROOT), "rev-parse", "--git-path", "hooks"],
                                 capture_output=True, text=True)
        if res is None or res.returncode != 0:
            warn("Not a git repository - cannot install the pre-push hook here; skipping repo install.")
            return
        hooks_dir = Path(res.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = ROOT / hooks_dir
        dest = hooks_dir / "pre-push"
        if not dest.exists():
            copy_file(hook_src, dest, executable=True)
            ok(f"Pre-push hook installed -> {dest}")
        elif HOOK_SENTINEL in dest.read_text(encoding="utf-8", errors="replace"):
            if files_equal(hook_src, dest):
                info("Pre-push hook already up to date (unchanged, skipped).")
            else:
                copy_file(hook_src, dest, executable=True)
                ok(f"Pre-push hook updated -> {dest}")
        else:
            warn(f"A non-SDD pre-push hook already exists at {dest} - not overwriting.")
            warn(f"To adopt the SDD hook, merge it manually from:\n  {hook_src}")
            return
        if str(dest) not in self.manifest["repo_hooks"]:
            self.manifest["repo_hooks"].append(str(dest))

    def _stage_templates(self, hook_src: Path) -> None:
        base = self.home / "ci-templates"
        wf_count = 0
        for wf in sorted((ROOT / "ci-templates" / "workflows").glob("sdd-*.yml")):
            dest = base / "workflows" / wf.name
            copy_file(wf, dest)
            self.record(dest)
            wf_count += 1
        dest = base / "hooks" / "pre-push"
        copy_file(hook_src, dest, executable=True)
        self.record(dest)
        scanner = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"
        if scanner.is_file():
            dest = base / "scripts" / scanner.name
            copy_file(scanner, dest)
            self.record(dest)
            ok(f"Templates staged in {base} ({wf_count} workflow(s) + hook + scanner) for /sdd-init.")
        else:
            warn(f"Scanner not found at {scanner} - staged {wf_count} workflow(s) + the hook template only.")

    # ---- environment hints ----------------------------------------------------
    def agent_teams(self) -> None:
        info("Checking agent teams configuration...")
        if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1":
            ok("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is set.")
            line()
            return
        warn("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is not set.")
        line("\n  Agent teams require this environment variable. Add it to your shell profile:\n"
             "    bash/zsh:   export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1\n"
             "    fish:       set -gx CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS 1\n"
             "    PowerShell: [Environment]::SetEnvironmentVariable('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS','1','User')\n")
        flag = self.args.shell_profile
        if flag is None and self.args.yes:
            flag = False
        if not decide(flag, False, "  Add to your shell profile now? (y/N) ", False):
            line()
            return
        shell = os.path.basename(os.environ.get("SHELL", ""))
        home = Path.home()
        profile = {"zsh": home / ".zshrc", "fish": home / ".config" / "fish" / "config.fish"}.get(shell)
        if shell == "bash":
            profile = home / (".bash_profile" if (home / ".bash_profile").exists() else ".bashrc")
        if profile is None:
            warn(f"Unknown shell: {shell or '(unset)'}. Add manually.")
        elif profile.exists() and "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" in profile.read_text(errors="replace"):
            info(f"Already in {profile} (but may not be set to 1).")
        else:
            stmt = ("set -gx CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS 1" if shell == "fish"
                    else "export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
            profile.parent.mkdir(parents=True, exist_ok=True)
            with open(profile, "a", encoding="utf-8") as f:
                f.write(f"\n# SDD: Enable Claude Code Agent Teams\n{stmt}\n")
            ok(f"Added to {profile}. Restart your terminal.")
        line()

    def summary(self) -> None:
        line("  VS Code: add to settings.json ->\n"
             '    { "claudeCode.useTerminal": true, "claudeCode.environmentVariables": '
             '[ { "name": "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "value": "1" } ] }\n')
        line("=" * 52 + "\n                 Setup Complete\n" + "=" * 52)
        line(f"\n  Installed to: {self.home}")
        for label, sub, prefix in (("Agents", "agents", "    - "), ("Commands", "commands", "    - /")):
            line(f"\n  {label} (available in all projects):")
            for f in sorted((self.home / sub).glob("*.md")):
                line(f"{prefix}{f.stem}")
        if self.protected:
            line("\n  Secret-handling safeguards: ENABLED and verified.")
        else:
            line("\n  Secret-handling safeguards: not enabled (declined). Re-run with --hooks to enable.")
        line("\n  Usage in any project: /sdd-init, /sdd-feature <name>, /sdd-status, /sdd-resume <name>")
        line('  Or just say: "New feature: <description>"\n')

    def run(self) -> int:
        line("\n  SDD Global Installer for Claude Code\n")
        claude = shutil.which("claude")
        if not claude:
            warn("Claude Code CLI not found in PATH. Install it first: https://claude.com/claude-code")
            if not self.args.yes and not yes(ask("Continue anyway? (y/N) ", "n")):
                return 1
        else:
            try:
                v = subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=30)
                info(f"Claude Code version: {(v.stdout.strip().splitlines() or ['unknown'])[0]}")
            except (OSError, subprocess.SubprocessError):
                info("Claude Code version: unknown")
        info(f"Target: {self.home}")
        line()
        try:
            self.install_dir("agents", ROOT / "agents", "*.md", self.home / "agents")
            self.install_dir("commands", ROOT / "commands", "*.md", self.home / "commands")
            self.install_dir("agent tools", ROOT / "tools", "*.py", self.home / "tools", executable=True)
            self.install_claude_md()
            self.install_secret_handling()
            self.install_pre_push()
        except InstallError as e:
            err(str(e))
            if self.protected is False:
                err(NOT_PROTECTED)
                err("Fix the problem above and re-run the installer; see hooks/README.md.")
            return 1
        except OSError as e:
            err(f"installation failed: {e}")
            if self.protected is False:
                err(NOT_PROTECTED)
            return 1
        finally:
            try:
                save_manifest(self.home, self.manifest)
            except OSError as e:
                warn(f"could not write the install manifest ({e}); uninstall will fall back to name matching.")
        self.agent_teams()
        self.summary()
        return 0


def verify_only(args) -> int:
    home = resolve_claude_home(args.claude_home)
    path = home / "settings.json"
    try:
        current, _ = sdd_settings.load(path)
    except InstallError as e:
        err(str(e))
        err(NOT_PROTECTED)
        return 1
    problems = verify_settings(current)
    if problems:
        for p in problems:
            err(p)
        err(NOT_PROTECTED)
        return 1
    ok(f"{path}: safeguards registered once each and verified with the exact hook commands.")
    return 0


def main(argv=None) -> int:
    if sys.version_info < MIN_PYTHON:
        err(f"Python {'.'.join(map(str, MIN_PYTHON))}+ is required. {NOT_PROTECTED}")
        return 1
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.verify:
        return verify_only(args)
    try:
        return Installer(args).run()
    except InstallError as e:
        err(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
