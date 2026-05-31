#!/usr/bin/env bash
# Create the Kanban board used by cross-bot worker dispatch.
set -euo pipefail

BOARD="${CROSSBOT_KANBAN_BOARD:-cross-bot}"
HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"

echo "Cross-bot Kanban board: ${BOARD}"

if command -v hermes >/dev/null 2>&1; then
  hermes kanban boards create "${BOARD}" --name "Cross-Bot Messages" 2>/dev/null || true
  echo "✓ hermes kanban boards create ${BOARD}"
else
  echo "Warning: hermes CLI not in PATH — creating directory only"
fi

mkdir -p "${HERMES_HOME}/kanban/boards/${BOARD}"
echo "✓ ${HERMES_HOME}/kanban/boards/${BOARD}/"

if [[ ! -f "${HERMES_HOME}/kanban/boards/${BOARD}/kanban.db" ]]; then
  echo ""
  echo "kanban.db ainda não existe. Rode:"
  echo "  hermes kanban boards create ${BOARD} --name \"Cross-Bot Messages\""
  echo "Ou adicione ao ~/.hermes/.env:"
  echo "  CROSSBOT_KANBAN_BOARD=${BOARD}"
  exit 1
fi

echo "✓ Board pronto para cross-bot dispatch"
