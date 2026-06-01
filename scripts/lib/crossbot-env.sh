#!/usr/bin/env bash
# Shared helpers: discover Hermes profiles and validate cross-bot roster.

hermes_home() {
  echo "${HERMES_HOME:-${HOME}/.hermes}"
}

hermes_root() {
  local home="${HERMES_HOME:-}"
  if [[ -n "$home" && "$home" == *"/profiles/"* ]]; then
    echo "${home%%/profiles/*}"
    return 0
  fi
  echo "${HERMES_HOME:-${HOME}/.hermes}"
}

hermes_profiles_dir() {
  echo "$(hermes_root)/profiles"
}

list_hermes_profiles() {
  local dir
  dir="$(hermes_profiles_dir)"
  if [[ ! -d "$dir" ]]; then
    return 0
  fi
  local name
  for name in "$dir"/*/; do
    [[ -d "$name" ]] || continue
    basename "$name"
  done | sort
}

profile_exists() {
  [[ -d "$(hermes_profiles_dir)/$1" ]]
}

default_topic_map() {
  echo "$(hermes_root)/plugins/crossbot/topic-map.json"
}

profile_from_hermes_home() {
  local home="${HERMES_HOME:-}"
  [[ -n "$home" ]] || return 1
  local profiles_root home_resolved root_resolved
  profiles_root="$(hermes_profiles_dir)"
  home_resolved="$(realpath "$home" 2>/dev/null || echo "$home")"
  root_resolved="$(realpath "$profiles_root" 2>/dev/null || echo "$profiles_root")"
  if [[ "$home_resolved" == "${root_resolved}/"* ]]; then
    local rel="${home_resolved#"${root_resolved}/"}"
    echo "${rel%%/*}"
    return 0
  fi
  return 1
}

read_active_profile() {
  local f
  for f in "$(hermes_root)/active_profile" "${HOME}/.hermes/active_profile"; do
    if [[ -f "$f" ]]; then
      tr -d '[:space:]' < "$f"
      return 0
    fi
  done
  return 1
}

orchestrator_from_topic_map() {
  local topic_map="${1:-$(default_topic_map)}"
  local python="${2:-python3}"
  [[ -f "$topic_map" ]] || return 1
  "$python" - "$topic_map" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    orch = str(data.get("orchestrator", "")).strip()
    if orch:
        print(orch)
except Exception:
    pass
PY
}

# Resolve who starts the round: explicit ORCHESTRATOR, else the initiating bot/profile.
resolve_orchestrator() {
  local topic_map="${1:-$(default_topic_map)}"
  local python="${2:-python3}"
  local candidate=""

  if [[ -n "${ORCHESTRATOR:-}" ]]; then
    echo "$ORCHESTRATOR"
    return 0
  fi

  if [[ -n "${CROSSBOT_BOT_NAME:-}" ]]; then
    echo "$CROSSBOT_BOT_NAME"
    return 0
  fi

  candidate="$(profile_from_hermes_home 2>/dev/null || true)"
  if [[ -n "$candidate" && "$candidate" != "default" && "$candidate" != "custom" ]]; then
    echo "$candidate"
    return 0
  fi

  candidate="$(read_active_profile 2>/dev/null || true)"
  if [[ -n "$candidate" && "$candidate" != "default" ]]; then
    echo "$candidate"
    return 0
  fi

  candidate="$(orchestrator_from_topic_map "$topic_map" "$python" 2>/dev/null || true)"
  if [[ -n "$candidate" ]]; then
    echo "$candidate"
    return 0
  fi

  echo "Error: could not detect orchestrator (initiating bot)." >&2
  echo "Run from a Hermes profile context, set CROSSBOT_BOT_NAME, or:" >&2
  echo "  ORCHESTRATOR=<profile> PHRASE=\"...\" ./scripts/telefone-sem-fio.sh" >&2
  echo "Configure defaults: ./scripts/configure-crossbot.sh" >&2
  return 1
}

validate_crossbot_roster() {
  local topic_map="${1:-$(default_topic_map)}"
  local orchestrator="${2:?orchestrator required}"
  local python="${3:-python3}"

  "$python" - "$topic_map" "$orchestrator" <<'PY'
import json
import os
import sys

path, orch = sys.argv[1], sys.argv[2]
profiles_dir = os.path.expanduser("~/.hermes/profiles")

if not os.path.isfile(path):
    print(f"Error: topic-map not found: {path}", file=sys.stderr)
    sys.exit(1)

with open(path) as f:
    data = json.load(f)

on_disk = sorted(
    name
    for name in os.listdir(profiles_dir)
    if os.path.isdir(os.path.join(profiles_dir, name))
) if os.path.isdir(profiles_dir) else []

topics = data.get("topics") or {}
players = [name for name in topics if name != orch]

if not topics:
    print("Error: topic-map.json has no entries in 'topics'.", file=sys.stderr)
    print("Run: ./scripts/configure-crossbot.sh", file=sys.stderr)
    sys.exit(1)

if orch not in topics:
    print(f"Error: orchestrator '{orch}' is not a key in topic-map.json.", file=sys.stderr)
    print(f"Keys found: {', '.join(sorted(topics))}", file=sys.stderr)
    print("Run: ./scripts/configure-crossbot.sh", file=sys.stderr)
    sys.exit(1)

if not players:
    print(f"Error: no players in topic-map (excluding orchestrator={orch}).", file=sys.stderr)
    sys.exit(1)

missing = [p for p in [orch, *players] if p not in on_disk]
if missing:
    print("Error: topic-map lists Hermes profiles that do not exist on disk:", file=sys.stderr)
    for name in missing:
        print(f"  - {name}", file=sys.stderr)
    print(f"Profiles found in {profiles_dir}: {', '.join(on_disk) or '(none)'}", file=sys.stderr)
    print("", file=sys.stderr)
    print("The telefone-sem-fio roster must use real folder names from ~/.hermes/profiles/.", file=sys.stderr)
    print("Run: ./scripts/configure-crossbot.sh", file=sys.stderr)
    sys.exit(1)

handles = data.get("handles") or {}
placeholder_handles = [
    name for name, handle in handles.items()
    if str(handle).startswith("seu_bot_")
]
if placeholder_handles:
    print("Warning: topic-map still has placeholder Telegram handles:", file=sys.stderr)
    for name in placeholder_handles:
        print(f"  - {name}: {handles[name]}", file=sys.stderr)
    print("Update handles in topic-map.json (or re-run configure-crossbot.sh).", file=sys.stderr)

chat_id = str(data.get("chat_id", "")).strip()
if not chat_id or chat_id == "-100XXXXXXXXXX":
    print("Warning: visibility chat_id is not configured in topic-map.json.", file=sys.stderr)
    print("Telegram visibility posts will be skipped until you set a real chat_id.", file=sys.stderr)
PY
}
