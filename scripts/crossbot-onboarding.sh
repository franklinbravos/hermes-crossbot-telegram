#!/usr/bin/env bash
# Crossbot guided onboarding — etapas numeradas com gates automáticos.
#
# Uso:
#   ./scripts/crossbot-onboarding.sh start
#   ./scripts/crossbot-onboarding.sh current
#   ./scripts/crossbot-onboarding.sh verify --watch 180
#   ./scripts/crossbot-onboarding.sh advance
#   ./scripts/crossbot-onboarding.sh run-action
#   ./scripts/crossbot-onboarding.sh status
#   ./scripts/crossbot-onboarding.sh reset [--step 6]
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/resolve-python.sh
source "${REPO_ROOT}/scripts/lib/resolve-python.sh"
PYTHON="$(resolve_hermes_python)"
ENGINE="${REPO_ROOT}/scripts/lib/crossbot-onboarding.py"

exec "$PYTHON" "$ENGINE" "$@"
