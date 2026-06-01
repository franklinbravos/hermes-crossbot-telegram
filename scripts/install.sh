#!/usr/bin/env bash
# Install Hermes crossbot plugin into ~/.hermes/plugins/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${HERMES_PLUGINS_DIR:-${HOME}/.hermes/plugins}"
# shellcheck source=lib/migrate-legacy.sh
source "${REPO_ROOT}/scripts/lib/migrate-legacy.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [TARGET]

TARGET:
  cross-bot   Install crossbot + migrate legacy (default)
  migrate     Legacy cleanup only (plugins + config.yaml + .env)
  all         Install every plugin in plugins/
  PLUGIN      Install one plugin by folder name (e.g. async-delegate)

Environment:
  HERMES_PLUGINS_DIR   Destination (default: ~/.hermes/plugins)

Examples:
  ./scripts/install.sh
  ./scripts/install.sh migrate
  ./scripts/bootstrap.sh --yes    # full onboarding (recommended)
EOF
}

install_one() {
  local name="$1"
  local src="${REPO_ROOT}/plugins/${name}"
  if [[ ! -d "$src" ]]; then
    echo "Error: plugin not found: ${src}" >&2
    exit 1
  fi
  mkdir -p "$DEST"
  rm -rf "${DEST}/${name}"
  cp -r "$src" "${DEST}/${name}"
  echo "✓ ${name} → ${DEST}/${name}"
}

sync_crossbot_profile_plugins() {
  local profiles_root="${HERMES_HOME:-${HOME}/.hermes}/profiles"
  [[ -d "$profiles_root" ]] || return 0
  local profile_dir legacy
  for profile_dir in "${profiles_root}"/*/; do
    [[ -d "$profile_dir" ]] || continue
    mkdir -p "${profile_dir}/plugins"
    for legacy in kanban-context multi-agent-context; do
      rm -rf "${profile_dir}/plugins/${legacy}"
    done
    rm -rf "${profile_dir}/plugins/crossbot"
    ln -sf "${DEST}/crossbot" "${profile_dir}/plugins/crossbot"
  done
  echo "✓ profile plugin symlinks → ${DEST}/crossbot"
}

install_crossbot_stack() {
  run_full_legacy_migration
  install_one crossbot
  migrate_legacy_plugin_dirs "$DEST"
  sync_crossbot_profile_plugins
  echo ""
  echo "Crossbot installed."
  echo "  Full onboarding: ./scripts/bootstrap.sh --yes"
}

main() {
  local target="${1:-cross-bot}"
  case "$target" in
    -h|--help|help) usage; exit 0 ;;
    cross-bot) install_crossbot_stack ;;
    migrate) run_full_legacy_migration ;;
    all)
      for dir in "${REPO_ROOT}"/plugins/*/; do
        install_one "$(basename "$dir")"
      done
      migrate_legacy_plugin_dirs "$DEST"
      ;;
    *)
      install_one "$target"
      ;;
  esac
}

main "$@"
