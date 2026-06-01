#!/usr/bin/env bash
# Relatório do benchmark de cadeia cumulativa (telefone / mercado / feira).
# Uso: ./scripts/benchmark-report.sh [ROUND_ID]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/resolve-python.sh
source "${REPO_ROOT}/scripts/lib/resolve-python.sh"
PYTHON="$(resolve_hermes_python)"

ROUND="${1:-}"
AUDIT="${CROSSBOT_AUDIT_LOG:-${HOME}/.hermes/logs/crossbot/crossbot-audit.jsonl}"
BENCH_DIR="${HOME}/.hermes/logs/crossbot"
DB="${CROSSBOT_DB_PATH:-${MULTI_AGENT_TG_DB_PATH:-${HOME}/.hermes/data/crossbot.db}}"
[[ -f "$DB" ]] || DB="${HOME}/.hermes/data/multi_agent_tg_shared.db"

if [[ -z "$ROUND" ]]; then
  ROUND="$(ls -t "${BENCH_DIR}"/benchmark-*.json 2>/dev/null | head -1)"
  ROUND="$(basename "$ROUND" .json | sed 's/^benchmark-//')"
fi

if [[ -z "$ROUND" ]]; then
  echo "Usage: $(basename "$0") ROUND_ID" >&2
  echo "Example: $(basename "$0") 20260531-1430" >&2
  exit 1
fi

REPORT_JSON="${BENCH_DIR}/benchmark-${ROUND}.json"

"$PYTHON" - "$ROUND" "$AUDIT" "$DB" "$REPORT_JSON" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

round_id, audit_path, db_path, report_path = sys.argv[1:5]
tags = (
    f"BenchmarkChain] round={round_id}",
    f"FuiAoMercado] round={round_id}",
    f"TelefoneSemFio] round={round_id}",
)

bench = {}
rp = Path(report_path)
if rp.is_file():
    bench = json.loads(rp.read_text())

started_at = bench.get("started_at", "")
started_epoch = bench.get("started_epoch")
chain = bench.get("chain_order", [])
theme = bench.get("theme", "mercado")
theme_label = bench.get("theme_label") or {
    "telefone": "Telefone sem fio",
    "feira": "Fui à feira",
    "mercado": "Fui ao mercado",
}.get(theme, "Benchmark cadeia")

hops = []
if Path(audit_path).is_file():
    for line in Path(audit_path).read_text().splitlines():
        if not any(t in line for t in tags) and round_id not in line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("event") in ("crossbot_send", "crossbot_respond", "mention_relay"):
            hops.append({
                "ts": ev.get("ts"),
                "event": ev.get("event"),
                "from_bot": ev.get("from_bot"),
                "to_bot": ev.get("to_bot"),
                "outbox_id": ev.get("outbox_id"),
            })

outbox_rows = []
try:
    import sqlite3
    conn = sqlite3.connect(db_path, timeout=5)
    rows = conn.execute(
        "SELECT id, from_bot, to_bot, status, body, response_text, ts, completed_at "
        "FROM outbox WHERE body LIKE ? OR subject LIKE ? ORDER BY id ASC",
        (f"%round: {round_id}%", f"%round={round_id}%"),
    ).fetchall()
    conn.close()
    for r in rows:
        outbox_rows.append({
            "id": r[0], "from_bot": r[1], "to_bot": r[2], "status": r[3],
            "body": (r[4] or "")[:200], "response": (r[5] or "")[:120],
            "ts": r[6], "completed_at": r[7],
        })
except Exception as exc:
    outbox_rows = [{"error": str(exc)}]

complete = any("status: COMPLETE" in (r.get("body") or "") for r in outbox_rows if isinstance(r, dict))
done_count = sum(1 for r in outbox_rows if isinstance(r, dict) and r.get("status") == "done")
expected = bench.get("expected_hops") or len(chain)
success_rate = (done_count / expected * 100) if expected else 0

finished_epoch = None
if outbox_rows and isinstance(outbox_rows[-1], dict):
    finished_epoch = outbox_rows[-1].get("completed_at") or outbox_rows[-1].get("ts")

duration = None
if started_epoch and finished_epoch:
    try:
        duration = round(float(finished_epoch) - float(started_epoch), 1)
    except (TypeError, ValueError):
        pass

all_done = done_count >= expected and complete
success = all_done and success_rate >= 100

bench.update({
    "completed_hops": done_count,
    "expected_hops": expected,
    "success_rate_pct": round(success_rate, 1),
    "success": success,
    "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if success or complete else None,
    "duration_seconds": duration,
    "outbox_count": len(outbox_rows),
    "complete_flag_seen": complete,
})

rp.parent.mkdir(parents=True, exist_ok=True)
rp.write_text(json.dumps(bench, indent=2, ensure_ascii=False) + "\n")

print("")
print("=" * 60)
print(f"  {theme_label} — relatório  round {round_id}")
print("=" * 60)
print(f"  Tema:             {theme}")
print(f"  Início:           {started_at or '(desconhecido)'}")
if duration is not None:
    mins, secs = divmod(int(duration), 60)
    print(f"  Duração total:    {mins}m {secs}s ({duration}s)")
else:
    print("  Duração total:    (ainda em andamento ou sem timestamps)")
print(f"  Saltos esperados: {expected}")
print(f"  Outbox concluídos:{done_count}")
print(f"  Sucesso:          {'✅ 100%' if success else '❌ incompleto'} ({bench['success_rate_pct']}%)")
print(f"  COMPLETE visto:   {'sim' if complete else 'não'}")
print(f"  Frase inicial:    {bench.get('initial_phrase', '')}")
if outbox_rows:
    last = outbox_rows[-1]
    if isinstance(last, dict) and last.get("response"):
        print(f"  Última resposta:  {last['response'][:100]}...")
print("")
print(f"  JSON: {report_path}")
print("=" * 60)
print("")

sys.exit(0 if success else 1)
PY
