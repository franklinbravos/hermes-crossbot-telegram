#!/usr/bin/env bash
# Crossbot debug pack — coleta factual para enviar ao dev (sem achismo do agente).
#
# Uso:
#   ./scripts/crossbot-debug-pack.sh enable          # liga modo debug
#   ./scripts/crossbot-debug-pack.sh pack            # zip com tudo
#   ./scripts/crossbot-debug-pack.sh pack -r 20260601-1608
#   ./scripts/crossbot-debug-pack.sh status
#   ./scripts/crossbot-debug-pack.sh disable
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/resolve-python.sh
source "${REPO_ROOT}/scripts/lib/resolve-python.sh"
PYTHON="$(resolve_hermes_python)"
COLLECTOR="${REPO_ROOT}/scripts/lib/crossbot-debug-pack.py"

exec "$PYTHON" "$COLLECTOR" "$@"
