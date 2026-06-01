#!/usr/bin/env bash
# Fui ao mercado / feira — wrapper do motor unificado (tema: +1 item).
export BENCHMARK_THEME="${BENCHMARK_THEME:-mercado}"
[[ "${LOJA:-}" == "feira" ]] && export BENCHMARK_THEME=feira
exec "$(cd "$(dirname "$0")" && pwd)/benchmark-chain.sh" "$@"
