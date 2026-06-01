#!/usr/bin/env bash
# Telefone sem fio — wrapper do motor unificado (tema: +2 palavras).
export BENCHMARK_THEME=telefone
exec "$(cd "$(dirname "$0")" && pwd)/benchmark-chain.sh" "$@"
