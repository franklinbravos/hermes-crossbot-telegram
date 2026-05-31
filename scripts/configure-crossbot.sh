#!/usr/bin/env bash
# Interactive setup: map real Hermes profiles → topic-map.json for cross-bot.
# Usage: ./scripts/configure-crossbot.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/crossbot-env.sh
source "${REPO_ROOT}/scripts/lib/crossbot-env.sh"

TOPIC_MAP="${TOPIC_MAP:-$(default_topic_map)}"
PROFILES_DIR="$(hermes_profiles_dir)"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Build topic-map.json from profiles in ${PROFILES_DIR}.

Options:
  -h, --help          Show this help
  --orchestrator NAME Pre-select orchestrator
  --players a,b,c     Comma-separated players (default: all except orchestrator)
  --chat-id ID        Telegram forum chat_id
  --yes               Accept defaults without prompts

Example:
  ./scripts/configure-crossbot.sh
  ./scripts/configure-crossbot.sh --orchestrator matias --players sofia,iago --yes
EOF
}

ORCHESTRATOR=""
PLAYERS=""
CHAT_ID=""
ASSUME_YES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --orchestrator) ORCHESTRATOR="${2:-}"; shift 2 ;;
    --players) PLAYERS="${2:-}"; shift 2 ;;
    --chat-id) CHAT_ID="${2:-}"; shift 2 ;;
    --yes) ASSUME_YES=true; shift ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

readarray -t ALL_PROFILES < <(list_hermes_profiles)

if [[ ${#ALL_PROFILES[@]} -eq 0 ]]; then
  echo "Error: no Hermes profiles in ${PROFILES_DIR}" >&2
  echo "Create profiles first (hermes -p <name> setup), then re-run." >&2
  exit 1
fi

echo "Cross-bot — configurar a partir dos profiles reais"
echo "Profiles em ${PROFILES_DIR}:"
printf '  - %s\n' "${ALL_PROFILES[@]}"
echo ""

pick_orchestrator() {
  if [[ -n "$ORCHESTRATOR" ]]; then
    profile_exists "$ORCHESTRATOR" || {
      echo "Error: --orchestrator '$ORCHESTRATOR' not in ${PROFILES_DIR}" >&2
      exit 1
    }
    echo "$ORCHESTRATOR"
    return
  fi

  echo "Quem é o orchestrator (coordena telefone sem fio e reporta ao humano)?"
  local i=1 choice
  for name in "${ALL_PROFILES[@]}"; do
    echo "  ${i}) ${name}"
    ((i++)) || true
  done
  read -r -p "Escolha [1-${#ALL_PROFILES[@]}]: " choice
  if [[ ! "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#ALL_PROFILES[@]} )); then
    echo "Error: invalid choice" >&2
    exit 1
  fi
  echo "${ALL_PROFILES[$((choice - 1))]}"
}

pick_players() {
  local orch="$1"
  if [[ -n "$PLAYERS" ]]; then
    echo "$PLAYERS"
    return
  fi

  local available=()
  local name
  for name in "${ALL_PROFILES[@]}"; do
    [[ "$name" == "$orch" ]] && continue
    available+=("$name")
  done

  if [[ ${#available[@]} -eq 0 ]]; then
    echo "Error: need at least one player besides orchestrator=${orch}" >&2
    exit 1
  fi

  local default_list
  default_list="$(IFS=,; echo "${available[*]}")"
  if $ASSUME_YES; then
    echo "$default_list"
    return
  fi

  read -r -p "Jogadores do telefone sem fio [${default_list}]: " reply
  if [[ -z "${reply// /}" ]]; then
    echo "$default_list"
  else
    echo "${reply// /}"
  fi
}

read_chat_id() {
  if [[ -n "$CHAT_ID" ]]; then
    echo "$CHAT_ID"
    return
  fi

  local existing=""
  if [[ -f "$TOPIC_MAP" ]]; then
    existing="$(python3 - "$TOPIC_MAP" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        cid = str(json.load(f).get("chat_id", "")).strip()
    if cid and cid != "-100XXXXXXXXXX":
        print(cid)
except Exception:
    pass
PY
)"
  fi

  if [[ -n "$existing" ]] && $ASSUME_YES; then
    echo "$existing"
    return
  fi

  if [[ -n "$existing" ]]; then
    read -r -p "chat_id do workspace Telegram [${existing}]: " reply
    [[ -z "${reply// /}" ]] && echo "$existing" || echo "$reply"
    return
  fi

  read -r -p "chat_id do workspace Telegram (fórum, ex: -1003716565637): " reply
  echo "$reply"
}

load_existing_field() {
  local profile="$1"
  local field="$2"
  python3 - "$TOPIC_MAP" "$profile" "$field" <<'PY'
import json, sys
path, profile, field = sys.argv[1:4]
try:
    with open(path) as f:
        data = json.load(f)
    val = (data.get(field) or {}).get(profile)
    if val is not None:
        print(val)
except Exception:
    pass
PY
}

read_thread_id() {
  local profile="$1"
  local existing
  existing="$(load_existing_field "$profile" topics 2>/dev/null || true)"
  [[ -z "$existing" ]] && existing=0
  if $ASSUME_YES; then
    echo "$existing"
    return
  fi
  read -r -p "  thread_id para ${profile} [${existing}]: " reply
  [[ -z "${reply// /}" ]] && echo "$existing" || echo "$reply"
}

read_handle() {
  local profile="$1"
  local existing
  existing="$(load_existing_field "$profile" handles 2>/dev/null || true)"
  [[ -z "$existing" ]] && existing="$profile"
  if $ASSUME_YES; then
    echo "$existing"
    return
  fi
  read -r -p "  @handle Telegram (sem @) para ${profile} [${existing}]: " reply
  [[ -z "${reply// /}" ]] && echo "$existing" || echo "$reply"
}

ensure_crossbot_bot_name() {
  local profile="$1"
  local env_file="${PROFILES_DIR}/${profile}/.env"
  [[ -f "$env_file" ]] || {
    echo "  ${profile}: no .env — add CROSSBOT_BOT_NAME=${profile} manually"
    return 0
  }

  if grep -q '^CROSSBOT_BOT_NAME=' "$env_file" 2>/dev/null; then
    local current
    current="$(grep '^CROSSBOT_BOT_NAME=' "$env_file" | tail -1 | cut -d= -f2- | tr -d "\"'")"
    if [[ "$current" == "$profile" ]]; then
      echo "  ${profile}: CROSSBOT_BOT_NAME OK"
    else
      echo "  ${profile}: CROSSBOT_BOT_NAME=${current} (expected ${profile}) — revise manualmente"
    fi
    return 0
  fi

  if $ASSUME_YES; then
    echo "CROSSBOT_BOT_NAME=${profile}" >> "$env_file"
    echo "  ${profile}: added CROSSBOT_BOT_NAME=${profile}"
    return 0
  fi

  read -r -p "  Adicionar CROSSBOT_BOT_NAME=${profile} em ${env_file}? [Y/n]: " reply
  if [[ -z "$reply" || "$reply" =~ ^[Yy]$ ]]; then
    echo "CROSSBOT_BOT_NAME=${profile}" >> "$env_file"
    echo "  ${profile}: added CROSSBOT_BOT_NAME=${profile}"
  else
    echo "  ${profile}: skipped — configure CROSSBOT_BOT_NAME manually"
  fi
}

ORCH="$(pick_orchestrator)"
PLAYER_CSV="$(pick_players "$ORCH")"
CHAT="$(read_chat_id)"

IFS=',' read -r -a PLAYER_LIST <<< "${PLAYER_CSV}"

for name in "$ORCH" "${PLAYER_LIST[@]}"; do
  profile_exists "$name" || {
    echo "Error: profile '${name}' not found in ${PROFILES_DIR}" >&2
    exit 1
  }
done

echo ""
echo "Tópicos Telegram (0 = desconhecido; visibilidade pode falhar até configurar):"

export ORCH="$ORCH" CHAT="$CHAT" PLAYER_CSV="$PLAYER_CSV"
for name in "$ORCH" "${PLAYER_LIST[@]}"; do
  export "THREAD_${name}=$(read_thread_id "$name")"
  export "HANDLE_${name}=$(read_handle "$name")"
done

mkdir -p "$(dirname "$TOPIC_MAP")"
python3 - "$TOPIC_MAP" <<'PY'
import json
import os
import sys

path = sys.argv[1]
orch = os.environ["ORCH"]
players = [p for p in os.environ.get("PLAYER_CSV", "").split(",") if p]
chat = os.environ.get("CHAT", "")

topics = {}
handles = {}
for profile in [orch] + players:
    topics[profile] = int(os.environ.get(f"THREAD_{profile}", "0") or "0")
    handles[profile] = os.environ.get(f"HANDLE_{profile}", profile)

data = {
    "comment": f"Generated by configure-crossbot.sh — orchestrator={orch}",
    "orchestrator": orch,
    "chat_id": chat,
    "topics": topics,
    "handles": handles,
}

with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY

echo ""
echo "✓ Escrito: ${TOPIC_MAP}"
echo ""
echo "Roster telefone sem fio:"
echo "  orchestrator: ${ORCH}"
echo "  jogadores:    ${PLAYER_CSV}"
echo ""
echo "CROSSBOT_BOT_NAME por profile:"
for name in "$ORCH" "${PLAYER_LIST[@]}"; do
  ensure_crossbot_bot_name "$name"
done

echo ""
echo "Próximo passo:"
echo "  PHRASE=\"O rato roeu\" ./scripts/telefone-sem-fio.sh"
echo "  (orchestrator detectado automaticamente se rodar no contexto do profile ${ORCH})"
