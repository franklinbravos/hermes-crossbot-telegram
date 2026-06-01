#!/usr/bin/env bash
# Install a cron job for crossbot auto-update (daily 04:00 UTC).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CROSSBOT_HOME="${CROSSBOT_HOME:-${REPO_ROOT}}"
CRON_LINE="0 4 * * * CROSSBOT_HOME=${CROSSBOT_HOME} ${REPO_ROOT}/scripts/auto-update.sh --quiet --restart >> ${HOME}/.hermes/logs/crossbot/auto-update.log 2>&1"

chmod +x "${REPO_ROOT}/scripts/auto-update.sh"

mkdir -p "${HOME}/.hermes/logs/crossbot"

if crontab -l 2>/dev/null | grep -F "scripts/auto-update.sh" >/dev/null; then
  echo "✓ cron entry already exists for crossbot auto-update"
else
  (crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -
  echo "✓ installed cron: daily 04:00 UTC"
  echo "  $CRON_LINE"
fi

echo ""
echo "Manual test:"
echo "  CROSSBOT_HOME=${CROSSBOT_HOME} ${REPO_ROOT}/scripts/auto-update.sh"
echo ""
echo "Hermes Kanban (alternativa ao cron): crie task recorrente que execute:"
echo "  ${REPO_ROOT}/scripts/auto-update.sh --quiet --restart"
echo ""
echo "Ver logs:"
echo "  tail -f ~/.hermes/logs/crossbot/auto-update.log"
