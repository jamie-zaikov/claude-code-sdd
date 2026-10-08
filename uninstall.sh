#!/usr/bin/env bash
set -euo pipefail

CLAUDE_HOME="${HOME}/.claude"

echo ""
echo "SDD Global Uninstaller"
echo "======================"
echo ""
echo "This will remove SDD agents, commands, and CLAUDE.md from ${CLAUDE_HOME}/"
echo ""
echo "  Agents to remove:"
for agent in orchestrator requirements-agent design-agent tasks-agent spec-consistency-checker task-executor task-tester task-validator code-reviewer security-reviewer github-agent vault-reader vault-writer; do
  [ -f "${CLAUDE_HOME}/agents/${agent}.md" ] && echo "    • ${agent}.md"
done
echo ""
echo "  Commands to remove:"
for cmd in sdd-init sdd-feature sdd-status sdd-resume sdd-overnight; do
  [ -f "${CLAUDE_HOME}/commands/${cmd}.md" ] && echo "    • ${cmd}.md"
done
echo ""

read -rp "Continue? (y/N) " reply
[[ "$reply" =~ ^[Yy]$ ]] || exit 0

# Remove agents
for agent in orchestrator requirements-agent design-agent tasks-agent spec-consistency-checker task-executor task-tester task-validator code-reviewer security-reviewer github-agent vault-reader vault-writer; do
  rm -f "${CLAUDE_HOME}/agents/${agent}.md"
done

# Remove commands
for cmd in sdd-init sdd-feature sdd-status sdd-resume sdd-overnight; do
  rm -f "${CLAUDE_HOME}/commands/${cmd}.md"
done

# Remove agent tools
rm -f "${CLAUDE_HOME}/tools/sdd-module-size.py"
rm -f "${CLAUDE_HOME}/tools/sdd-status.py"
rm -f "${CLAUDE_HOME}/tools/sdd-park.py"
rm -f "${CLAUDE_HOME}/tools/sdd-context-pack.py"
rm -f "${CLAUDE_HOME}/tools/sdd-overlap.py"

echo ""
echo "Removed SDD agents and commands."
echo ""
echo "CLAUDE.md was NOT removed — review ~/.claude/CLAUDE.md manually"
echo "and remove the SDD instructions if you no longer need them."
echo ""
