#!/usr/bin/env bash
# Migrate from kanban-context + multi-agent-context to unified crossbot plugin.

migrate_legacy_plugin_dirs() {
  local dest="${1:-${HERMES_PLUGINS_DIR:-${HOME}/.hermes/plugins}}"
  local legacy
  for legacy in kanban-context multi-agent-context; do
    if [[ -d "${dest}/${legacy}" ]]; then
      rm -rf "${dest}/${legacy}"
      echo "✓ removed legacy global plugin: ${legacy}"
    fi
  done

  local profiles_root="${HERMES_HOME:-${HOME}/.hermes}/profiles"
  [[ -d "$profiles_root" ]] || return 0

  local profile_dir
  for profile_dir in "${profiles_root}"/*/; do
    [[ -d "$profile_dir" ]] || continue
    for legacy in kanban-context multi-agent-context; do
      if [[ -e "${profile_dir}/plugins/${legacy}" ]]; then
        rm -rf "${profile_dir}/plugins/${legacy}"
        echo "✓ removed legacy profile plugin: $(basename "$profile_dir")/${legacy}"
      fi
    done
  done
}

migrate_profile_configs() {
  local profiles_root="${HERMES_HOME:-${HOME}/.hermes}/profiles"
  local python="${1:-python3}"
  [[ -d "$profiles_root" ]] || {
    echo "ℹ no profiles dir — skip config.yaml migration"
    return 0
  }

  "$python" - "$profiles_root" <<'PY'
import re
import sys
from pathlib import Path

profiles_root = Path(sys.argv[1])
LEGACY = {"kanban-context", "multi-agent-context"}


def migrate_file(cfg: Path) -> bool:
    text = cfg.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]
        if re.match(r"^plugins:\s*$", line.strip()):
            out.append(line)
            i += 1
            if i < len(lines) and re.match(r"^(\s*)enabled:\s*$", lines[i]):
                indent = re.match(r"^(\s*)", lines[i]).group(1)
                out.append(lines[i])
                i += 1
                items: list[str] = []
                while i < len(lines):
                    m = re.match(r"^(\s*)-\s*(.+?)\s*$", lines[i])
                    if not m or len(m.group(1)) <= len(indent):
                        break
                    name = m.group(2).strip().strip("'\"")
                    if name not in LEGACY:
                        items.append(name)
                    else:
                        changed = True
                    i += 1
                if "crossbot" not in items:
                    items.append("crossbot")
                    changed = True
                for name in items:
                    out.append(f"{indent}  - {name}")
                continue
        out.append(line)
        i += 1

    new_text = "\n".join(out)
    if text.endswith("\n"):
        new_text += "\n"
    if changed:
        cfg.write_text(new_text, encoding="utf-8")
    return changed


count = 0
for profile_dir in sorted(profiles_root.iterdir()):
    if not profile_dir.is_dir():
        continue
    cfg = profile_dir / "config.yaml"
    if cfg.is_file() and migrate_file(cfg):
        print(f"✓ migrated config.yaml: {profile_dir.name}")
        count += 1

if count == 0:
    print("ℹ config.yaml: no legacy plugin entries found")
PY
}

migrate_profile_env_files() {
  local profiles_root="${HERMES_HOME:-${HOME}/.hermes}/profiles"
  [[ -d "$profiles_root" ]] || return 0

  local profile_dir env_file profile_name db_path
  db_path="${CROSSBOT_DB_PATH:-${HOME}/.hermes/data/crossbot.db}"

  for profile_dir in "${profiles_root}"/*/; do
    [[ -d "$profile_dir" ]] || continue
    profile_name="$(basename "$profile_dir")"
    env_file="${profile_dir}/.env"
    [[ -f "$env_file" ]] || continue

    if ! grep -q '^CROSSBOT_BOT_NAME=' "$env_file" 2>/dev/null; then
      echo "CROSSBOT_BOT_NAME=${profile_name}" >> "$env_file"
      echo "✓ ${profile_name}: added CROSSBOT_BOT_NAME"
    fi

    if grep -q '^MULTI_AGENT_TG_DB_PATH=' "$env_file" 2>/dev/null \
      && ! grep -q '^CROSSBOT_DB_PATH=' "$env_file" 2>/dev/null; then
      legacy_db="$(grep '^MULTI_AGENT_TG_DB_PATH=' "$env_file" | tail -1 | cut -d= -f2- | tr -d "\"'")"
      echo "CROSSBOT_DB_PATH=${legacy_db}" >> "$env_file"
      echo "✓ ${profile_name}: aliased CROSSBOT_DB_PATH from MULTI_AGENT_TG_DB_PATH"
    elif ! grep -q '^CROSSBOT_DB_PATH=' "$env_file" 2>/dev/null \
      && ! grep -q '^MULTI_AGENT_TG_DB_PATH=' "$env_file" 2>/dev/null; then
      echo "CROSSBOT_DB_PATH=${db_path}" >> "$env_file"
      echo "✓ ${profile_name}: added CROSSBOT_DB_PATH"
    fi
  done
}

run_full_legacy_migration() {
  local python="${1:-python3}"
  echo "=== Crossbot legacy migration ==="
  migrate_legacy_plugin_dirs
  migrate_profile_configs "$python"
  migrate_profile_env_files
  echo "=== Migration complete ==="
}
