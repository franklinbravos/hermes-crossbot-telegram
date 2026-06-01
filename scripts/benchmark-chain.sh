#!/usr/bin/env bash
# Motor unificado de benchmark cross-bot — cadeia cumulativa + monitoramento.
#
# Temas (só muda a "fantasia"; o modelo é o mesmo):
#   telefone  — telefone sem fio (+2 palavras por jogador)
#   mercado   — fui ao mercado (+1 item)
#   feira     — fui à feira (+1 item)
#
# Uso:
#   ./scripts/benchmark-chain.sh
#   BENCHMARK_THEME=telefone PHRASE="O rato roeu" ./scripts/benchmark-chain.sh
#   BENCHMARK_THEME=feira ./scripts/benchmark-chain.sh
#   LOJA=feira ./scripts/benchmark-chain.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/resolve-python.sh
source "${REPO_ROOT}/scripts/lib/resolve-python.sh"
# shellcheck source=lib/crossbot-env.sh
source "${REPO_ROOT}/scripts/lib/crossbot-env.sh"

PYTHON="$(resolve_hermes_python)"
CLI="${CROSSBOT_CLI:-${HOME}/.hermes/plugins/crossbot/crossbot_cli.py}"
TOPIC_MAP="${TOPIC_MAP:-${HOME}/.hermes/plugins/crossbot/topic-map.json}"
BENCHMARK_THEME="${BENCHMARK_THEME:-mercado}"
PHRASE="${PHRASE:-}"
FIRST_ITEM="${FIRST_ITEM:-}"
LOJA="${LOJA:-mercado}"

if [[ ! -f "$CLI" ]]; then
  CLI="${REPO_ROOT}/plugins/crossbot/crossbot_cli.py"
fi
if [[ ! -f "$TOPIC_MAP" ]]; then
  TOPIC_MAP="${REPO_ROOT}/plugins/crossbot/topic-map.json"
fi
if [[ ! -f "$CLI" ]] || [[ ! -f "$TOPIC_MAP" ]]; then
  echo "Error: crossbot CLI or topic-map missing. Run ./scripts/bootstrap.sh --yes" >&2
  exit 1
fi

# Normaliza tema
case "${BENCHMARK_THEME,,}" in
  telefone|telefone-sem-fio|phone) BENCHMARK_THEME="telefone" ;;
  feira|market-fair) BENCHMARK_THEME="feira"; LOJA="feira" ;;
  mercado|market) BENCHMARK_THEME="mercado"; LOJA="mercado" ;;
  *)
    echo "Error: BENCHMARK_THEME must be telefone, mercado, or feira (got: ${BENCHMARK_THEME})" >&2
    exit 1
    ;;
esac

ORCHESTRATOR="$(resolve_orchestrator "$TOPIC_MAP" "$PYTHON")"

readarray -t PLAYERS < <("$PYTHON" - "$TOPIC_MAP" "$ORCHESTRATOR" <<'PY'
import json, sys
path, orch = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
for name in sorted(data.get("topics", {})):
    if name != orch:
        print(name)
PY
)

if [[ ${#PLAYERS[@]} -eq 0 ]]; then
  echo "Error: no players in topic-map (excluding orchestrator=${ORCHESTRATOR})" >&2
  exit 1
fi

validate_crossbot_roster "$TOPIC_MAP" "$ORCHESTRATOR" "$PYTHON"

INCREMENT_RULE=""
THEME_LABEL=""

if [[ "$BENCHMARK_THEME" == "telefone" ]]; then
  INCREMENT_RULE="add_two_words"
  THEME_LABEL="Telefone sem fio"
  PHRASE="${PHRASE:-O rato roeu}"
  OPENING="${PHRASE}"
else
  INCREMENT_RULE="add_one_item"
  if [[ "$BENCHMARK_THEME" == "feira" ]]; then
    THEME_LABEL="Fui à feira"
    LOJA="feira"
  else
    THEME_LABEL="Fui ao mercado"
    LOJA="mercado"
  fi
  if [[ -z "$FIRST_ITEM" ]]; then
    readarray -t ITEMS <<< "$(printf '%s\n' \
      "uma maçã" "um sabão" "um pão" "um queijo" "um café" "uma banana" \
      "um tomate" "um arroz" "uma laranja" "um iogurte")"
    FIRST_ITEM="${ITEMS[$((RANDOM % ${#ITEMS[@]}))]}"
  fi
  if [[ "$FIRST_ITEM" != *" "* ]]; then
    case "$FIRST_ITEM" in
      maçã|banana|laranja|manga|uva) FIRST_ITEM="uma ${FIRST_ITEM}" ;;
      *) FIRST_ITEM="um ${FIRST_ITEM}" ;;
    esac
  fi
  if [[ "$LOJA" == "feira" ]]; then
    OPENING="Fui à feira e comprei ${FIRST_ITEM}"
  else
    OPENING="Fui ao mercado e comprei ${FIRST_ITEM}"
  fi
fi

CHAIN_ORDER="$(IFS=,; echo "${PLAYERS[*]}")"
FIRST="${PLAYERS[0]}"
NEXT_AFTER_FIRST="${PLAYERS[1]:-${ORCHESTRATOR}}"
TOTAL_STEPS="${#PLAYERS[@]}"
ROUND="$(date +%Y%m%d-%H%M)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_EPOCH="$(date +%s)"
REPORT_FILE="${HOME}/.hermes/logs/crossbot/benchmark-${ROUND}.json"
mkdir -p "$(dirname "$REPORT_FILE")"

if [[ "$INCREMENT_RULE" == "add_two_words" ]]; then
  INCREMENT_HUMAN="EXATAMENTE duas palavras novas no final"
  INCREMENT_EXAMPLE="ex: \"O rato roeu a roupa\""
else
  INCREMENT_HUMAN="EXATAMENTE um item novo no final (ex: \"e um sabão\")"
  INCREMENT_EXAMPLE=""
fi

BODY="BENCHMARK_CHAIN
round: ${ROUND}
started_at: ${STARTED_AT}
started_epoch: ${START_EPOCH}
theme: ${BENCHMARK_THEME}
theme_label: ${THEME_LABEL}
increment_rule: ${INCREMENT_RULE}
phrase: ${OPENING}
chain_order: ${CHAIN_ORDER}
orchestrator: ${ORCHESTRATOR}
step: 1
total_steps: ${TOTAL_STEPS}
played: ${ORCHESTRATOR}
next: ${FIRST}
status: IN_PROGRESS

=== SEU PAPEL (benchmark — não confunda com suporte) ===
Jogo: ${THEME_LABEL}. Isto é TESTE de comunicação entre bots, não ticket de cliente.

Destinatário desta mensagem: ${FIRST}
Se você NÃO for ${FIRST}: responda ERRO: profile errado.

Se você É ${FIRST} (jogador 1 de ${TOTAL_STEPS}):
1. Repita a frase INTEIRA em \"phrase\" — sem mudar o que já foi dito.
2. Acrescente ${INCREMENT_HUMAN}. ${INCREMENT_EXAMPLE}
3. Repasse ao próximo da fila: ${NEXT_AFTER_FIRST} (mention @ ou crossbot).
4. Copie este bloco BENCHMARK_CHAIN para o próximo, atualizando phrase, step, played, next.
5. Não mude de assunto. Não peça ajuda humana.

Demais jogadores: mesma regra (repetir + incrementar + repassar na ordem chain_order).
Último jogador (${PLAYERS[$((TOTAL_STEPS - 1))]}): envia ao coordenador ${ORCHESTRATOR} com status: COMPLETE

Coordenador ${ORCHESTRATOR}:
- Iniciou esta rodada; ao receber COMPLETE, reporta duração e sucesso 100%.
- Rode: ~/hermes-crossbot-telegram/scripts/benchmark-report.sh ${ROUND}"

echo "${THEME_LABEL} — benchmark ${ROUND} (modelo: cadeia cumulativa)"
echo "  tema:          ${BENCHMARK_THEME}"
echo "  coordenador:   ${ORCHESTRATOR}"
echo "  frase inicial: ${OPENING}"
echo "  ordem:         ${CHAIN_ORDER}"
echo "  1º jogador:    ${FIRST}"
echo "  regra:         ${INCREMENT_RULE}"
echo ""

CROSSBOT_BOT_NAME="${ORCHESTRATOR}" "$PYTHON" "$CLI" \
  send "${FIRST}" \
  "[BenchmarkChain] theme=${BENCHMARK_THEME} round=${ROUND}" \
  "${BODY}"

"$PYTHON" - "$REPORT_FILE" "$ROUND" "$STARTED_AT" "$START_EPOCH" "$ORCHESTRATOR" \
  "$CHAIN_ORDER" "$OPENING" "$BENCHMARK_THEME" "$THEME_LABEL" "$INCREMENT_RULE" <<'PY'
import json, sys
path = sys.argv[1]
data = {
    "game": "benchmark_chain",
    "round": sys.argv[2],
    "started_at": sys.argv[3],
    "started_epoch": int(sys.argv[4]),
    "orchestrator": sys.argv[5],
    "chain_order": sys.argv[6].split(","),
    "initial_phrase": sys.argv[7],
    "theme": sys.argv[8],
    "theme_label": sys.argv[9],
    "increment_rule": sys.argv[10],
    "expected_hops": len(sys.argv[6].split(",")),
    "completed_hops": 0,
    "success": None,
    "finished_at": None,
    "duration_seconds": None,
}
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY

echo "Rodada iniciada."
echo ""
echo "Monitorar:"
echo "  tail -f ~/.hermes/logs/crossbot/crossbot-audit.jsonl | grep BenchmarkChain"
echo ""

# Gravar round no state do onboarding (step 9)
"$PYTHON" -c "
import sys
sys.path.insert(0, '${REPO_ROOT}/plugins/crossbot')
try:
    import onboarding as ob
    ob.record_benchmark_round('${ROUND}')
except Exception:
    pass
" 2>/dev/null || true

echo "Relatório:"
echo "  ${REPO_ROOT}/scripts/benchmark-report.sh ${ROUND}"
echo ""
echo "Docs: docs/onboarding/05-benchmark-cadeia.md"

DEBUG_CFG="${HOME}/.hermes/plugins/crossbot/debug-mode.json"
if [[ -f "$DEBUG_CFG" ]] && grep -q '"enabled"[[:space:]]*:[[:space:]]*true' "$DEBUG_CFG" 2>/dev/null; then
  echo ""
  echo "Modo debug ON — gere o pacote factual e envie ao dev:"
  echo "  ${REPO_ROOT}/scripts/crossbot-debug-pack.sh pack -r ${ROUND}"
fi
