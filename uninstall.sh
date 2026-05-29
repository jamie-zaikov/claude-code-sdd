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
for agent in orchestrator requirements-agent design-agent tasks-agent task-executor task-tester task-validator; do
  [ -f "${CLAUDE_HOME}/agents/${agent}.md" ] && echo "    • ${agent}.md"
done
echo ""
echo "  Commands to remove:"
for cmd in sdd-init sdd-feature sdd-status sdd-resume; do
  [ -f "${CLAUDE_HOME}/commands/${cmd}.md" ] && echo "    • ${cmd}.md"
done
echo ""

read -rp "Continue? (y/N) " reply
[[ "$reply" =~ ^[Yy]$ ]] || exit 0

# Remove agents
for agent in orchestrator requirements-agent design-agent tasks-agent task-executor task-tester task-validator; do
  rm -f "${CLAUDE_HOME}/agents/${agent}.md"
done

# Remove commands
for cmd in sdd-init sdd-feature sdd-status sdd-resume; do
  rm -f "${CLAUDE_HOME}/commands/${cmd}.md"
done

echo ""
echo "Removed SDD agents and commands."
echo ""
echo "CLAUDE.md was NOT removed — review ~/.claude/CLAUDE.md manually"
echo "and remove the SDD instructions if you no longer need them."
echo ""
