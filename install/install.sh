#!/usr/bin/env bash
# Cross-agent installer for blender-programmatic-studio (macOS / Linux)
# Usage:
#   ./install/install.sh                          # Installs for Antigravity + Claude + universal .agents/skills
#   ./install/install.sh --agent antigravity|claude|agents|all
#   ./install/install.sh --project /path/to/repo  # Installs into project-local .agents/skills/
#   ./install/install.sh --uninstall

set -euo pipefail

SKILL_NAME="blender-programmatic-studio"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENT="all"
PROJECT_DIR=""
UNINSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="${2:-all}"; shift 2 ;;
    --project) PROJECT_DIR="${2:-}"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--agent antigravity|claude|agents|all] [--project DIR] [--uninstall]"
      echo "  antigravity -> ~/.gemini/config/skills/$SKILL_NAME"
      echo "  claude      -> ~/.claude/skills/$SKILL_NAME"
      echo "  agents      -> ~/.agents/skills/$SKILL_NAME (Codex, OpenCode, Gemini CLI, Copilot, Cursor)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

TARGETS=()
if [[ -n "$PROJECT_DIR" ]]; then
  TARGETS+=("$PROJECT_DIR/.agents/skills/$SKILL_NAME")
else
  case "$AGENT" in
    antigravity) TARGETS+=("$HOME/.gemini/config/skills/$SKILL_NAME") ;;
    claude)      TARGETS+=("$HOME/.claude/skills/$SKILL_NAME") ;;
    agents|codex|opencode|gemini|copilot|cursor) TARGETS+=("$HOME/.agents/skills/$SKILL_NAME") ;;
    all)
      TARGETS+=(
        "$HOME/.gemini/config/skills/$SKILL_NAME"
        "$HOME/.claude/skills/$SKILL_NAME"
        "$HOME/.agents/skills/$SKILL_NAME"
      )
      ;;
    *) echo "Unsupported --agent: $AGENT"; exit 1 ;;
  esac
fi

copy_skill() {
  local dst="$1"
  if [[ "$dst" == "$REPO_ROOT" ]]; then
    echo "[SKIP] Destination is source repo: $dst"
    return
  fi
  rm -rf "$dst"
  mkdir -p "$dst"
  for item in SKILL.md README.md README_zh.md LICENSE CHANGELOG.md AGENTS.md CLAUDE.md adapters assets examples references scripts tests; do
    if [[ -e "$REPO_ROOT/$item" ]]; then
      cp -R "$REPO_ROOT/$item" "$dst/$item"
    fi
  done
  find "$dst" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  echo "[INSTALLED] $dst"
}

for dst in "${TARGETS[@]}"; do
  if [[ "$UNINSTALL" -eq 1 ]]; then
    if [[ "$dst" == "$REPO_ROOT" ]]; then
      echo "[SKIP] Refusing to delete source repo: $dst"
    elif [[ -d "$dst" ]]; then
      rm -rf "$dst"
      echo "[UNINSTALLED] $dst"
    else
      echo "[NOT_FOUND] $dst"
    fi
  else
    copy_skill "$dst"
  fi
done
