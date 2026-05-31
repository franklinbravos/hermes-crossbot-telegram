#!/usr/bin/env bash
# Install Hermes community plugins into ~/.hermes/plugins/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${HERMES_PLUGINS_DIR:-${HOME}/.hermes/plugins}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [TARGET]

TARGET:
  cross-bot   Install multi-agent-context + kanban-context (default)
  all         Install every plugin in plugins/
  PLUGIN      Install one plugin by folder name (e.g. async-delegate)

Environment:
  HERMES_PLUGINS_DIR   Destination (default: ~/.hermes/plugins)

Examples:
  ./scripts/install.sh
  ./scripts/install.sh all
  ./scripts/install.sh async-delegate
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

main() {
  local target="${1:-cross-bot}"
  case "$target" in
    -h|--help|help) usage; exit 0 ;;
    cross-bot)
      install_one multi-agent-context
      install_one kanban-context
      echo ""
      echo "Cross-bot stack installed. Next: docs/onboarding/02-instalar-e-adaptar.md"
      ;;
    all)
      for dir in "${REPO_ROOT}"/plugins/*/; do
        install_one "$(basename "$dir")"
      done
      ;;
    *)
      install_one "$target"
      ;;
  esac
}

main "$@"
