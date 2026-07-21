#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# SDD Global Installer for Claude Code
# Installs agents, commands, and CLAUDE.md to ~/.claude/ so they're
# available in every project without per-repo setup.
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${HOME}/.claude"

# Colors (if terminal supports them)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[info]${NC}  $1"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $1"; }
err()   { echo -e "${RED}[err]${NC}   $1"; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     SDD Global Installer for Claude Code        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# --------------------------------------------------------------------------
# Preflight checks
# --------------------------------------------------------------------------

if ! command -v claude &>/dev/null; then
  warn "Claude Code CLI not found in PATH."
  warn "Install it first: curl -fsSL https://cli.claude.com/install | sh"
  echo ""
  read -rp "Continue anyway? (y/N) " reply
  [[ "$reply" =~ ^[Yy]$ ]] || exit 1
fi

if command -v claude &>/dev/null; then
  CC_VERSION=$(claude --version 2>/dev/null | head -1 || echo "unknown")
  info "Claude Code version: ${CC_VERSION}"
fi

# --------------------------------------------------------------------------
# Create directories
# --------------------------------------------------------------------------

info "Target: ${CLAUDE_HOME}"
echo ""

mkdir -p "${CLAUDE_HOME}/agents"
mkdir -p "${CLAUDE_HOME}/commands"

# --------------------------------------------------------------------------
# Install agents
# --------------------------------------------------------------------------

info "Installing agents..."

AGENT_COUNT=0
for agent_file in "${SCRIPT_DIR}/agents/"*.md; do
  [ -f "$agent_file" ] || continue
  name=$(basename "$agent_file")
  
  if [ -f "${CLAUDE_HOME}/agents/${name}" ]; then
    # Check if content differs
    if cmp -s "$agent_file" "${CLAUDE_HOME}/agents/${name}"; then
      echo "       ${name} (unchanged, skipped)"
    else
      cp "$agent_file" "${CLAUDE_HOME}/agents/${name}"
      ok "    ${name} (updated)"
      AGENT_COUNT=$((AGENT_COUNT + 1))
    fi
  else
    cp "$agent_file" "${CLAUDE_HOME}/agents/${name}"
    ok "    ${name} (installed)"
    AGENT_COUNT=$((AGENT_COUNT + 1))
  fi
done

if [ "$AGENT_COUNT" -eq 0 ]; then
  info "All agents already up to date."
else
  ok "${AGENT_COUNT} agent(s) installed/updated."
fi

echo ""

# --------------------------------------------------------------------------
# Install slash commands
# --------------------------------------------------------------------------

info "Installing slash commands..."

CMD_COUNT=0
for cmd_file in "${SCRIPT_DIR}/commands/"*.md; do
  [ -f "$cmd_file" ] || continue
  name=$(basename "$cmd_file")
  
  if [ -f "${CLAUDE_HOME}/commands/${name}" ]; then
    if cmp -s "$cmd_file" "${CLAUDE_HOME}/commands/${name}"; then
      echo "       ${name} (unchanged, skipped)"
    else
      cp "$cmd_file" "${CLAUDE_HOME}/commands/${name}"
      ok "    ${name} (updated)"
      CMD_COUNT=$((CMD_COUNT + 1))
    fi
  else
    cp "$cmd_file" "${CLAUDE_HOME}/commands/${name}"
    ok "    ${name} (installed)"
    CMD_COUNT=$((CMD_COUNT + 1))
  fi
done

if [ "$CMD_COUNT" -eq 0 ]; then
  info "All commands already up to date."
else
  ok "${CMD_COUNT} command(s) installed/updated."
fi

echo ""

# --------------------------------------------------------------------------
# Install global CLAUDE.md
# --------------------------------------------------------------------------

info "Installing global CLAUDE.md..."

if [ -f "${CLAUDE_HOME}/CLAUDE.md" ]; then
  if cmp -s "${SCRIPT_DIR}/CLAUDE.md" "${CLAUDE_HOME}/CLAUDE.md"; then
    info "CLAUDE.md already up to date."
  else
    warn "~/.claude/CLAUDE.md already exists and differs."
    echo ""
    echo "  Options:"
    echo "    [o] Overwrite with SDD version"
    echo "    [a] Append SDD instructions to existing file"
    echo "    [s] Skip (keep current file)"
    echo ""
    read -rp "  Choice (o/a/s): " choice
    case "$choice" in
      o|O)
        cp "${SCRIPT_DIR}/CLAUDE.md" "${CLAUDE_HOME}/CLAUDE.md"
        ok "CLAUDE.md overwritten."
        ;;
      a|A)
        echo "" >> "${CLAUDE_HOME}/CLAUDE.md"
        echo "---" >> "${CLAUDE_HOME}/CLAUDE.md"
        echo "" >> "${CLAUDE_HOME}/CLAUDE.md"
        cat "${SCRIPT_DIR}/CLAUDE.md" >> "${CLAUDE_HOME}/CLAUDE.md"
        ok "SDD instructions appended to CLAUDE.md."
        ;;
      *)
        info "CLAUDE.md skipped."
        ;;
    esac
  fi
else
  cp "${SCRIPT_DIR}/CLAUDE.md" "${CLAUDE_HOME}/CLAUDE.md"
  ok "CLAUDE.md installed."
fi

echo ""

# --------------------------------------------------------------------------
# Secret-handling hooks + deny rules (machine config in ~/.claude/settings.json)
# --------------------------------------------------------------------------

info "Secret-handling safeguards (deny secret reads + guard/redact hooks)..."

if ! command -v python3 &>/dev/null; then
  warn "python3 not found — skipping secret-handling setup."
  warn "The hooks require python3. Enable them later per hooks/README.md."
else
  echo ""
  echo "  This blocks reading known secret stores (.env, ~/.aws, ~/.ssh, keys, …)"
  echo "  and installs Bash hooks that stop secret dumps and redact leaked tokens."
  echo "  It edits ~/.claude/settings.json (a backup is written) and is idempotent."
  echo ""
  read -rp "  Enable secret handling now? (y/N) " reply
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    mkdir -p "${CLAUDE_HOME}/hooks"
    HOOK_COUNT=0
    for hook_file in "${SCRIPT_DIR}/hooks/"secret-*.py; do
      [ -f "$hook_file" ] || continue
      name=$(basename "$hook_file")
      cp "$hook_file" "${CLAUDE_HOME}/hooks/${name}"
      chmod +x "${CLAUDE_HOME}/hooks/${name}"
      HOOK_COUNT=$((HOOK_COUNT + 1))
    done
    ok "${HOOK_COUNT} hook script(s) copied to ${CLAUDE_HOME}/hooks/."

    if python3 - "${CLAUDE_HOME}/settings.json" <<'PYEOF'
import json, os, sys, shutil

path = sys.argv[1]
deny = [
    "Read(**/.env)", "Read(**/.env.*)", "Read(**/*.pem)", "Read(**/*.key)",
    "Read(**/id_rsa*)", "Read(**/id_ed25519*)", "Read(**/*.p12)", "Read(**/*.pfx)",
    "Read(**/credentials)", "Read(**/service-account*.json)", "Read(**/*.tfvars)",
    "Read(**/kubeconfig)", "Read(**/.netrc)",
    "Read(~/.aws/**)", "Read(~/.ssh/**)", "Read(~/.kube/**)", "Read(~/.config/gcloud/**)",
]

if os.path.exists(path):
    try:
        with open(path) as f:
            settings = json.load(f)
    except Exception as e:
        print(f"__ERROR__ existing settings.json is not valid JSON ({e}); not modifying it.")
        sys.exit(3)
    shutil.copyfile(path, path + ".bak")
else:
    settings = {}

perms = settings.setdefault("permissions", {})
existing_deny = perms.setdefault("deny", [])
for rule in deny:
    if rule not in existing_deny:
        existing_deny.append(rule)

hooks = settings.setdefault("hooks", {})

def ensure_hook(event, command):
    groups = hooks.setdefault(event, [])
    if any(command in (h.get("command", "")) for g in groups for h in g.get("hooks", [])):
        return
    groups.append({"matcher": "Bash", "hooks": [{"type": "command", "command": command}]})

ensure_hook("PreToolUse", "python3 ~/.claude/hooks/secret-guard.py")
ensure_hook("PostToolUse", "python3 ~/.claude/hooks/secret-redact.py")

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
print("__OK__")
PYEOF
    then
      ok "Deny rules + hooks registered in ${CLAUDE_HOME}/settings.json (backup: settings.json.bak)."
    else
      warn "Could not update settings.json automatically — enable manually per hooks/README.md."
    fi
  else
    info "Secret handling skipped. Enable later per hooks/README.md."
  fi
fi

echo ""

# --------------------------------------------------------------------------
# SDD CI pre-push hook (advisory local mirror of the CI gates)
# --------------------------------------------------------------------------

info "SDD CI pre-push hook (advisory local secret-scan + build/test/lint)..."

# Sentinel that marks an SDD-managed pre-push hook. Must match the first marker
# line in ci-templates/hooks/pre-push so we can detect our own hook and stay
# idempotent / non-destructive (FR-18, NFR-5).
SDD_HOOK_SENTINEL='# >>> sdd-pre-push (managed) >>>'
HOOK_SRC="${SCRIPT_DIR}/ci-templates/hooks/pre-push"
SCANNER_SRC="${SCRIPT_DIR}/ci-templates/scripts/sdd-secret-scan.py"

if ! command -v python3 &>/dev/null; then
  warn "python3 not found — skipping pre-push hook setup (the scanner needs python3)."
elif [ ! -f "$HOOK_SRC" ]; then
  warn "Hook template not found at ${HOOK_SRC} — skipping pre-push hook setup."
else
  echo ""
  echo "  This installs an advisory git pre-push hook into THIS repository. Before a"
  echo "  push it runs the shared secret scanner and scripts/ci.sh (if present) over"
  echo "  the pushed range, mirroring the CI gates. It is idempotent and never"
  echo "  overwrites a pre-existing non-SDD hook; CI still enforces the same checks"
  echo "  server-side. Bypass locally with: git push --no-verify."
  echo ""
  read -rp "  Install the SDD CI pre-push hook into this repository? (y/N) " reply
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    # (a) Install the hook into THIS repo (the FR-21 dogfood hook side, DD-4).
    #     Resolve the hooks dir from the repo install.sh lives in. git rev-parse
    #     fails (non-zero) if this is not a git repo — capture it in the `if`
    #     condition so `set -e` does not abort the installer (NFR-5).
    if ! HOOKS_DIR=$(git -C "$SCRIPT_DIR" rev-parse --git-path hooks 2>/dev/null); then
      warn "Not a git repository — cannot install the pre-push hook here; skipping repo install."
    else
      # --git-path is relative to SCRIPT_DIR (via -C); make it absolute.
      case "$HOOKS_DIR" in
        /*) : ;;
        *)  HOOKS_DIR="${SCRIPT_DIR}/${HOOKS_DIR}" ;;
      esac
      mkdir -p "$HOOKS_DIR"
      HOOK_DEST="${HOOKS_DIR}/pre-push"
      if [ ! -e "$HOOK_DEST" ]; then
        # No hook yet → install (cp -p preserves the 100755 exec bit).
        cp -p "$HOOK_SRC" "$HOOK_DEST"
        chmod +x "$HOOK_DEST"
        ok "Pre-push hook installed → ${HOOK_DEST}"
      elif grep -qF "$SDD_HOOK_SENTINEL" "$HOOK_DEST" 2>/dev/null; then
        # An SDD-managed hook is already present → idempotent update.
        if cmp -s "$HOOK_SRC" "$HOOK_DEST"; then
          info "Pre-push hook already up to date (unchanged, skipped)."
        else
          cp -p "$HOOK_SRC" "$HOOK_DEST"
          chmod +x "$HOOK_DEST"
          ok "Pre-push hook updated → ${HOOK_DEST}"
        fi
      else
        # A user's own hook exists without our sentinel → never overwrite.
        warn "A non-SDD pre-push hook already exists at ${HOOK_DEST} — not overwriting."
        warn "To adopt the SDD hook, merge it manually from:"
        warn "  ${HOOK_SRC}"
      fi
    fi

    # (b) Stage the hook template + shared scanner into ~/.claude/ so /sdd-init
    #     can distribute them downstream without a source clone (FR-21; FR-20).
    #     Runs on opt-in even when (a) skipped, so the global templates exist.
    mkdir -p "${CLAUDE_HOME}/ci-templates/hooks" "${CLAUDE_HOME}/ci-templates/scripts"
    cp -p "$HOOK_SRC" "${CLAUDE_HOME}/ci-templates/hooks/pre-push"
    chmod +x "${CLAUDE_HOME}/ci-templates/hooks/pre-push"
    if [ -f "$SCANNER_SRC" ]; then
      cp -p "$SCANNER_SRC" "${CLAUDE_HOME}/ci-templates/scripts/sdd-secret-scan.py"
      ok "Templates staged in ${CLAUDE_HOME}/ci-templates/ (hook + scanner) for /sdd-init."
    else
      warn "Scanner not found at ${SCANNER_SRC} — staged the hook template only."
    fi
  else
    info "Pre-push hook skipped."
  fi
fi

echo ""

# --------------------------------------------------------------------------
# Check environment variable
# --------------------------------------------------------------------------

info "Checking agent teams configuration..."

if [ "${CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS:-}" = "1" ]; then
  ok "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is set."
else
  warn "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is not set."
  echo ""
  echo "  Agent teams require this environment variable."
  echo "  Add one of the following to your shell profile:"
  echo ""
  echo "    # bash (~/.bashrc or ~/.bash_profile)"
  echo "    export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1"
  echo ""
  echo "    # zsh (~/.zshrc)"
  echo "    export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1"
  echo ""
  echo "    # fish (~/.config/fish/config.fish)"
  echo "    set -gx CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS 1"
  echo ""
  
  read -rp "  Add to your shell profile now? (y/N) " reply
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
      bash)
        PROFILE="${HOME}/.bashrc"
        [ -f "${HOME}/.bash_profile" ] && PROFILE="${HOME}/.bash_profile"
        ;;
      zsh)
        PROFILE="${HOME}/.zshrc"
        ;;
      fish)
        PROFILE="${HOME}/.config/fish/config.fish"
        ;;
      *)
        PROFILE=""
        warn "Unknown shell: ${SHELL_NAME}. Add manually."
        ;;
    esac
    
    if [ -n "$PROFILE" ]; then
      if grep -q "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" "$PROFILE" 2>/dev/null; then
        info "Already in ${PROFILE} (but may not be set to 1)."
      else
        echo "" >> "$PROFILE"
        echo "# SDD: Enable Claude Code Agent Teams" >> "$PROFILE"
        if [ "$SHELL_NAME" = "fish" ]; then
          echo "set -gx CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS 1" >> "$PROFILE"
        else
          echo "export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" >> "$PROFILE"
        fi
        ok "Added to ${PROFILE}. Run 'source ${PROFILE}' or restart your terminal."
      fi
    fi
  fi
fi

echo ""

# --------------------------------------------------------------------------
# VS Code settings hint
# --------------------------------------------------------------------------

info "VS Code settings recommendation:"
echo ""
echo '  Add to your VS Code settings.json:'
echo ''
echo '  {'
echo '    "claudeCode.useTerminal": true,'
echo '    "claudeCode.environmentVariables": ['
echo '      {'
echo '        "name": "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",'
echo '        "value": "1"'
echo '      }'
echo '    ]'
echo '  }'
echo ""

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

echo "╔══════════════════════════════════════════════════╗"
echo "║                 Setup Complete                   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Installed to: ${CLAUDE_HOME}/"
echo ""
echo "  Agents (available in all projects):"
for f in "${CLAUDE_HOME}/agents/"*.md; do
  [ -f "$f" ] && echo "    • $(basename "$f" .md)"
done
echo ""
echo "  Commands (available in all projects):"
for f in "${CLAUDE_HOME}/commands/"*.md; do
  [ -f "$f" ] && echo "    • /$(basename "$f" .md)"
done
echo ""
echo "  Usage in any project:"
echo "    /sdd-init              Initialize .specs/ structure"
echo "    /sdd-feature <name>    Scaffold a new feature"
echo "    /sdd-status            Show all features and progress"
echo "    /sdd-resume <name>     Resume work on a feature"
echo ""
echo "  Or just say: \"New feature: <description>\""
echo ""
