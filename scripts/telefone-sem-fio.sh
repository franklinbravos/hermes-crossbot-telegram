#!/usr/bin/env bash
# Inicia uma rodada de telefone sem fio (cross-bot benchmark).
# Uso: PHRASE="O rato roeu" ./scripts/telefone-sem-fio.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/resolve-python.sh
source "${REPO_ROOT}/scripts/lib/resolve-python.sh"
PYTHON="$(resolve_hermes_python)"
CLI="${CROSSBOT_CLI:-${HOME}/.hermes/plugins/kanban-context/crossbot_cli.py}"
TOPIC_MAP="${TOPIC_MAP:-${HOME}/.hermes/plugins/kanban-context/topic-map.json}"
ORCHESTRATOR="${CROSSBOT_BOT_NAME:-${ORCHESTRATOR:-orchestrator}}"
PHRASE="${PHRASE:-O rato roeu}"

if [[ ! -f "$CLI" ]]; then
  CLI="${REPO_ROOT}/plugins/kanban-context/crossbot_cli.py"
fi
if [[ ! -f "$TOPIC_MAP" ]]; then
  TOPIC_MAP="${REPO_ROOT}/plugins/kanban-context/topic-map.json"
fi
if [[ ! -f "$CLI" ]]; then
  echo "Error: crossbot_cli.py not found" >&2
  exit 1
fi
if [[ ! -f "$TOPIC_MAP" ]]; then
  echo "Error: topic-map.json not found" >&2
  exit 1
fi

readarray -t PLAYERS < <("$PYTHON" - "$TOPIC_MAP" "$ORCHESTRATOR" <<'PY'
import json, sys
path, orch = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
for name in data.get("topics", {}):
    if name != orch:
        print(name)
PY
)

if [[ ${#PLAYERS[@]} -eq 0 ]]; then
  echo "Error: no players in topic-map (excluding orchestrator=${ORCHESTRATOR})" >&2
  exit 1
fi

ROSTER="$(IFS=,; echo "${PLAYERS[*]}")"
FIRST="${PLAYERS[$((RANDOM % ${#PLAYERS[@]}))]}"
ROUND="$(date +%Y%m%d-%H%M)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

BODY="TELEFONE_SEM_FIO
round: ${ROUND}
started_at: ${STARTED_AT}
phrase: ${PHRASE}
played: ${ORCHESTRATOR}
roster: ${ROSTER}
hop: 1"

echo "Telefone sem fio — round ${ROUND}"
echo "  orchestrator: ${ORCHESTRATOR}"
echo "  phrase:       ${PHRASE}"
echo "  roster:       ${ROSTER}"
echo "  first player: ${FIRST}"
echo ""

CROSSBOT_BOT_NAME="${ORCHESTRATOR}" "$PYTHON" "$CLI" \
  send "${FIRST}" \
  "[TelefoneSemFio] round=${ROUND}" \
  "${BODY}"

echo ""
echo "Rodada iniciada. Acompanhe:"
echo "  tail -f ~/.hermes/logs/kanban-context/crossbot-audit.jsonl | grep TelefoneSemFio"
echo "Docs: docs/onboarding/05-telefone-sem-fio.md"
