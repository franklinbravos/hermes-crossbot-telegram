#!/usr/bin/env bash
# One-shot install + migrate + onboard crossbot for Hermes (human or autonomous agent).
#
# Usage:
#   ./scripts/bootstrap.sh [--yes] [--chat-id ID] [--orchestrator NAME] [--players a,b]
#   curl -fsSL .../bootstrap.sh | bash -s -- --yes
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CROSSBOT_REPO="${CROSSBOT_REPO:-https://github.com/franklinbravos/crossbot.git}"
CROSSBOT_HOME="${CROSSBOT_HOME:-${HOME}/crossbot}"
ASSUME_YES=false
CHAT_ID=""
ORCHESTRATOR=""
PLAYERS=""
SKIP_RESTART=false
SKIP_CONFIGURE=false
SKIP_BOARD=false
SMOKE_TEST=false
UPDATE_ONLY=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Install or update crossbot end-to-end:
  clone/pull → migrate legacy plugins → install → configure → kanban board → restart

Options:
  --yes                 Non-interactive (defaults for configure-crossbot)
  --chat-id ID          Telegram forum chat_id
  --orchestrator NAME   Orchestrator profile
  --players a,b,c       Comma-separated player profiles
  --home DIR            Clone/update directory (default: ~/crossbot)
  --repo URL            Git remote (default: github.com/franklinbravos/crossbot)
  --update-only         Pull + reinstall + migrate (skip configure if topic-map exists)
  --skip-configure      Skip configure-crossbot.sh
  --skip-board          Skip setup-crossbot-board.sh
  --skip-restart        Do not restart hermes gateway
  --smoke-test          Run telefone-sem-fio after install (needs valid topic-map)
  -h, --help            Show help

Examples:
  ./scripts/bootstrap.sh --yes
  ./scripts/bootstrap.sh --yes --orchestrator coordenador --chat-id -1001234567890
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) ASSUME_YES=true; shift ;;
    --chat-id) CHAT_ID="${2:-}"; shift 2 ;;
    --orchestrator) ORCHESTRATOR="${2:-}"; shift 2 ;;
    --players) PLAYERS="${2:-}"; shift 2 ;;
    --home) CROSSBOT_HOME="${2:-}"; shift 2 ;;
    --repo) CROSSBOT_REPO="${2:-}"; shift 2 ;;
    --update-only) UPDATE_ONLY=true; shift ;;
    --skip-configure) SKIP_CONFIGURE=true; shift ;;
    --skip-board) SKIP_BOARD=true; shift ;;
    --skip-restart) SKIP_RESTART=true; shift ;;
    --smoke-test) SMOKE_TEST=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

ensure_repo() {
  if [[ -f "${REPO_ROOT}/plugins/crossbot/plugin.yaml" ]]; then
    echo "✓ using existing repo at ${REPO_ROOT}"
    return 0
  fi

  if [[ -d "${CROSSBOT_HOME}/.git" ]]; then
    echo "→ updating ${CROSSBOT_HOME}"
    git -C "${CROSSBOT_HOME}" pull --ff-only
    REPO_ROOT="${CROSSBOT_HOME}"
    return 0
  fi

  echo "→ cloning ${CROSSBOT_REPO} → ${CROSSBOT_HOME}"
  git clone "${CROSSBOT_REPO}" "${CROSSBOT_HOME}"
  REPO_ROOT="${CROSSBOT_HOME}"
}

ensure_repo

cd "${REPO_ROOT}"
chmod +x scripts/*.sh scripts/lib/*.sh 2>/dev/null || true
# shellcheck source=lib/resolve-python.sh
source "${REPO_ROOT}/scripts/lib/resolve-python.sh"
# shellcheck source=lib/migrate-legacy.sh
source "${REPO_ROOT}/scripts/lib/migrate-legacy.sh"
PYTHON="$(resolve_hermes_python)"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Crossbot bootstrap — install + migrate + onboard        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

run_full_legacy_migration "$PYTHON"
./scripts/install.sh cross-bot

TOPIC_MAP="${HERMES_HOME:-${HOME}/.hermes}/plugins/crossbot/topic-map.json"
if [[ "$SKIP_CONFIGURE" == false ]]; then
  if [[ "$UPDATE_ONLY" == true && -f "$TOPIC_MAP" ]]; then
    echo "ℹ update-only: keeping existing topic-map.json"
  else
    cfg_args=(--yes)
    [[ -n "$ORCHESTRATOR" ]] && cfg_args+=(--orchestrator "$ORCHESTRATOR")
    [[ -n "$PLAYERS" ]] && cfg_args+=(--players "$PLAYERS")
    [[ -n "$CHAT_ID" ]] && cfg_args+=(--chat-id "$CHAT_ID")
    ./scripts/configure-crossbot.sh "${cfg_args[@]}"
  fi
else
  echo "ℹ skipped configure-crossbot (--skip-configure)"
fi

if [[ "$SKIP_BOARD" == false ]]; then
  ./scripts/setup-crossbot-board.sh || echo "⚠ setup-crossbot-board failed — fix manually if dispatch needed"
fi

if [[ "$SKIP_RESTART" == false ]] && command -v hermes >/dev/null 2>&1; then
  echo "→ restarting hermes gateway"
  hermes gateway restart || echo "⚠ hermes gateway restart failed — restart manually"
else
  echo "ℹ skipped gateway restart (hermes not in PATH or --skip-restart)"
fi

if [[ "$SMOKE_TEST" == true ]]; then
  echo "→ smoke test: telefone sem fio"
  PHRASE="${PHRASE:-O rato roeu bootstrap}" ./scripts/telefone-sem-fio.sh || \
    echo "⚠ smoke test failed — check topic-map and gateways"
fi

echo ""
echo "✅ Crossbot bootstrap finished."
echo ""
echo "Next checks:"
echo "  grep version ~/.hermes/plugins/crossbot/plugin.yaml"
echo "  tail -5 ~/.hermes/logs/crossbot/crossbot-audit.jsonl 2>/dev/null || true"
echo "  docs/onboarding/03-workspace-e-colegas.md — mapa de colegas no SOUL"
echo ""
