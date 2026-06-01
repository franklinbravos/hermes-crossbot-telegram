#!/usr/bin/env bash
# Auto-update crossbot from git (for cron / Hermes scheduled tasks).
#
# Usage:
#   ./scripts/auto-update.sh [--quiet] [--restart]
#   ./scripts/setup-auto-update-cron.sh   # install daily cron
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CROSSBOT_HOME="${CROSSBOT_HOME:-${REPO_ROOT}}"
QUIET=false
RESTART=false
LOG_DIR="${HOME}/.hermes/logs/crossbot"
LOG_FILE="${LOG_DIR}/auto-update.log"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet) QUIET=true; shift ;;
    --restart) RESTART=true; shift ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--quiet] [--restart]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

log() {
  local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
  mkdir -p "$LOG_DIR"
  echo "$msg" >> "$LOG_FILE"
  $QUIET || echo "$msg"
}

if [[ ! -d "${CROSSBOT_HOME}/.git" ]]; then
  log "ERROR: not a git repo: ${CROSSBOT_HOME}"
  exit 1
fi

cd "${CROSSBOT_HOME}"
chmod +x scripts/*.sh scripts/lib/*.sh 2>/dev/null || true

BEFORE="$(git rev-parse HEAD)"
git fetch origin 2>>"$LOG_FILE" || { log "ERROR: git fetch failed"; exit 1; }

UPSTREAM="$(git rev-parse @{u} 2>/dev/null || git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null || true)"
if [[ -z "$UPSTREAM" ]]; then
  log "WARN: no upstream branch — skip pull"
  exit 0
fi

if [[ "$BEFORE" == "$UPSTREAM" ]]; then
  log "OK: already up to date ($BEFORE)"
  exit 0
fi

log "UPDATE: $BEFORE → $UPSTREAM"
git pull --ff-only 2>>"$LOG_FILE" || { log "ERROR: git pull failed"; exit 1; }

export CROSSBOT_HOME="$REPO_ROOT"
./scripts/bootstrap.sh --yes --update-only --skip-restart

if $RESTART && command -v hermes >/dev/null 2>&1; then
  log "RESTART: hermes gateway"
  hermes gateway restart >>"$LOG_FILE" 2>&1 || log "WARN: gateway restart failed"
fi

log "DONE: crossbot updated to $(git rev-parse --short HEAD)"
