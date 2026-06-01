#!/usr/bin/env bash
# Remote bootstrap — clone crossbot and run full install (for curl | bash).
set -euo pipefail

CROSSBOT_REPO="${CROSSBOT_REPO:-https://github.com/franklinbravos/hermes-crossbot-telegram.git}"
CROSSBOT_HOME="${CROSSBOT_HOME:-${HOME}/hermes-crossbot-telegram}"

if [[ -d "${CROSSBOT_HOME}/scripts/bootstrap.sh" ]]; then
  exec "${CROSSBOT_HOME}/scripts/bootstrap.sh" "$@"
fi

echo "→ crossbot remote install → ${CROSSBOT_HOME}"
git clone "${CROSSBOT_REPO}" "${CROSSBOT_HOME}"
chmod +x "${CROSSBOT_HOME}/scripts/"*.sh "${CROSSBOT_HOME}/scripts/lib/"*.sh 2>/dev/null || true
exec "${CROSSBOT_HOME}/scripts/bootstrap.sh" "$@"
