#!/usr/bin/env bash
# Resolve Python 3.11+ for Hermes community plugin scripts.
resolve_hermes_python() {
  if [[ -n "${HERMES_PYTHON:-}" && -x "${HERMES_PYTHON}" ]]; then
    echo "${HERMES_PYTHON}"
    return 0
  fi

  local py candidates=(
    "${HOME}/.hermes/hermes-agent/venv/bin/python"
    "${HOME}/.local/bin/python3.11"
  )

  if command -v python3.11 >/dev/null 2>&1; then
    candidates+=("$(command -v python3.11)")
  fi
  if command -v python3.12 >/dev/null 2>&1; then
    candidates+=("$(command -v python3.12)")
  fi

  for py in "${candidates[@]}"; do
    if [[ -n "$py" && -x "$py" ]] && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      echo "$py"
      return 0
    fi
  done

  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo python3
    return 0
  fi

  echo "Error: Python 3.11+ required (found $(python3 --version 2>&1))" >&2
  echo "Set HERMES_PYTHON to a 3.11+ interpreter or install Hermes Agent." >&2
  return 1
}
