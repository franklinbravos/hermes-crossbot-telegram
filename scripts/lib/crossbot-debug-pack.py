#!/usr/bin/env python3
"""Collect crossbot debug artifacts into a shareable directory / zip.

Deterministic facts only — no LLM interpretation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _hermes_root() -> Path:
    home = os.environ.get("HERMES_HOME", "")
    if home and "/profiles/" in home:
        return Path(home.split("/profiles/")[0])
    return Path(os.environ.get("HERMES_ROOT", Path.home() / ".hermes"))


def _plugin_dir(root: Path) -> Path:
    return root / "plugins" / "crossbot"


def _debug_mode_path(root: Path) -> Path:
    return _plugin_dir(root) / "debug-mode.json"


def _db_path(root: Path) -> Path:
    for candidate in (
        os.environ.get("CROSSBOT_DB_PATH", ""),
        os.environ.get("MULTI_AGENT_TG_DB_PATH", ""),
        str(root / "data" / "crossbot.db"),
        str(root / "data" / "multi_agent_tg_shared.db"),
    ):
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return root / "data" / "crossbot.db"


def _kanban_db(root: Path) -> Path:
    board = os.environ.get("CROSSBOT_KANBAN_BOARD", "cross-bot")
    return root / "kanban" / "boards" / board / "kanban.db"


def _audit_log(root: Path) -> Path:
    raw = os.environ.get(
        "CROSSBOT_AUDIT_LOG",
        str(root / "logs" / "crossbot" / "crossbot-audit.jsonl"),
    )
    return Path(raw)


def _gateway_log(root: Path) -> Path:
    return root / "logs" / "gateway.log"


def _redact_obj(obj: Any) -> Any:
    """Mask secrets in JSON-serializable structures."""
    secret_keys = re.compile(
        r"(token|secret|password|api_key|authorization|bearer)",
        re.I,
    )
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if secret_keys.search(k) and isinstance(v, str) and len(v) > 8:
                out[k] = v[:6] + "…[REDACTED]"
            elif k == "telegram_bot_token" and isinstance(v, str):
                out[k] = v[:8] + "…[REDACTED]" if v else v
            else:
                out[k] = _redact_obj(v)
        return out
    if isinstance(obj, list):
        return [_redact_obj(x) for x in obj]
    return obj


def _read_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _plugin_version(root: Path) -> str:
    data = _read_json(_plugin_dir(root) / "plugin.yaml")
    if isinstance(data, dict):
        return str(data.get("version", "unknown"))
    text = (_plugin_dir(root) / "plugin.yaml").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"version:\s*(\S+)", text)
    return m.group(1) if m else "unknown"


def _sqlite_query(db: Path, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
    if not db.is_file():
        return []
    try:
        conn = sqlite3.connect(str(db), timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def _filter_audit_lines(lines: List[str], round_id: Optional[str]) -> List[str]:
    if not round_id:
        return lines
    kept = []
    for line in lines:
        if round_id in line:
            kept.append(line)
            continue
        for tag in (
            f"round={round_id}",
            f"round: {round_id}",
            f'"round": "{round_id}"',
        ):
            if tag in line:
                kept.append(line)
                break
    return kept


def _outbox_for_round(outbox_rows: List[Dict[str, Any]], round_id: Optional[str]) -> List[Dict[str, Any]]:
    if not round_id:
        return outbox_rows
    out = []
    for row in outbox_rows:
        subj = str(row.get("subject") or "")
        body = str(row.get("body") or "")
        if round_id in subj or round_id in body:
            out.append(row)
    return out


def _diagnose(
    *,
    round_id: Optional[str],
    outbox: List[Dict[str, Any]],
    audit_events: List[Dict[str, Any]],
    kanban_tasks: List[Dict[str, Any]],
    plugin_version: str,
) -> Dict[str, Any]:
    pending = [r for r in outbox if r.get("status") == "pending"]
    done = [r for r in outbox if r.get("status") == "done"]
    flags: List[str] = []

    if pending and not done:
        flags.append("OUTBOX_ALL_PENDING")
    if pending and done:
        flags.append("OUTBOX_PARTIAL")
    if not any(e.get("event") == "crossbot_respond" for e in audit_events):
        if outbox:
            flags.append("NO_CROSSBOT_RESPOND_IN_AUDIT")
    if not any(e.get("event") == "benchmark_relay" for e in audit_events):
        if round_id and len(outbox) == 1 and pending:
            flags.append("BENCHMARK_CHAIN_NOT_RELAYED")
    if any(e.get("event") == "visibility_post" and not e.get("ok") for e in audit_events):
        flags.append("VISIBILITY_POST_FAILED")
    complete = any("status: COMPLETE" in str(r.get("body") or "") for r in outbox)
    if round_id and done and not complete and len(outbox) >= 1:
        flags.append("BENCHMARK_NOT_COMPLETE")

    return {
        "round": round_id,
        "plugin_version": plugin_version,
        "outbox_total": len(outbox),
        "outbox_pending": len(pending),
        "outbox_done": len(done),
        "audit_events": len(audit_events),
        "kanban_tasks": len(kanban_tasks),
        "benchmark_complete_seen": complete,
        "red_flags": flags,
    }


def _write_report_md(
    path: Path,
    diag: Dict[str, Any],
    outbox: List[Dict[str, Any]],
    audit_events: List[Dict[str, Any]],
    kanban_tasks: List[Dict[str, Any]],
    paths: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Crossbot debug pack — relatório factual",
        "",
        f"- **Gerado em (UTC):** {now}",
        f"- **Host:** {socket.gethostname()}",
        f"- **Plugin crossbot:** {diag.get('plugin_version')}",
        f"- **Round filtrado:** {diag.get('round') or '(todos)'}",
        "",
        "## Resumo automático",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Outbox (total) | {diag.get('outbox_total')} |",
        f"| Outbox pending | {diag.get('outbox_pending')} |",
        f"| Outbox done | {diag.get('outbox_done')} |",
        f"| Eventos audit | {diag.get('audit_events')} |",
        f"| Tasks Kanban cross-bot | {diag.get('kanban_tasks')} |",
        f"| COMPLETE no body | {'sim' if diag.get('benchmark_complete_seen') else 'não'} |",
        "",
    ]
    flags = diag.get("red_flags") or []
    if flags:
        lines.append("## Alertas (regras automáticas)")
        lines.append("")
        for f in flags:
            lines.append(f"- `{f}`")
        lines.append("")
    else:
        lines.append("## Alertas")
        lines.append("")
        lines.append("- Nenhum alerta automático disparado.")
        lines.append("")

    lines.extend([
        "## Outbox",
        "",
    ])
    if not outbox:
        lines.append("_Nenhuma linha no filtro atual._")
    else:
        for row in outbox:
            lines.append(
                f"- **#{row.get('id')}** `{row.get('from_bot')}` → `{row.get('to_bot')}` "
                f"status=`{row.get('status')}` subject=`{str(row.get('subject') or '')[:80]}`"
            )
    lines.extend(["", "## Timeline audit (últimos eventos)", ""])
    for ev in audit_events[-30:]:
        ev_s = json.dumps(ev, ensure_ascii=False)
        if len(ev_s) > 240:
            ev_s = ev_s[:240] + "…"
        lines.append(f"- `{ev.get('event')}` — {ev_s}")
    lines.extend(["", "## Kanban (cross-bot board)", ""])
    if not kanban_tasks:
        lines.append("_Nenhuma task no filtro._")
    else:
        for t in kanban_tasks:
            lines.append(
                f"- `{t.get('id')}` assignee=`{t.get('assignee')}` status=`{t.get('status')}` "
                f"title=`{str(t.get('title') or '')[:70]}`"
            )
    lines.extend([
        "",
        "## Arquivos neste pacote",
        "",
        "Envie o `.zip` inteiro para quem for debugar — não resuma manualmente.",
        "",
        "| Arquivo | Conteúdo |",
        "|---------|----------|",
    ])
    for name, desc in [
        ("MANIFEST.json", "Metadados e paths"),
        ("REPORT.md", "Este relatório"),
        ("audit/", "JSONL bruto"),
        ("database/", "Dumps JSON de outbox / kanban"),
        ("config/", "topic-map e visibility (tokens redigidos)"),
    ]:
        lines.append(f"| `{name}` | {desc} |")
    lines.extend(["", "## Paths no host", ""])
    for k, v in sorted(paths.items()):
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_enable(args: argparse.Namespace) -> int:
    root = _hermes_root()
    path = _debug_mode_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "enabled": True,
        "enabled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auto_pack_on_benchmark": args.auto_benchmark,
        "note": "Modo debug crossbot — use crossbot-debug-pack.sh pack para gerar zip",
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Debug mode ON → {path}")
    print("  Gerar pacote: scripts/crossbot-debug-pack.sh pack")
    return 0


def cmd_disable(_args: argparse.Namespace) -> int:
    root = _hermes_root()
    path = _debug_mode_path(root)
    if path.is_file():
        path.unlink()
        print("Debug mode OFF")
    else:
        print("Debug mode já estava desligado")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    root = _hermes_root()
    path = _debug_mode_path(root)
    data = _read_json(path) if path.is_file() else None
    print(json.dumps({
        "debug_mode": bool(data and data.get("enabled")),
        "config_path": str(path),
        "config": data,
        "plugin_version": _plugin_version(root),
        "db_path": str(_db_path(root)),
        "audit_log": str(_audit_log(root)),
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    root = _hermes_root()
    round_id = (args.round or "").strip() or None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    label = f"crossbot-debug-pack-{round_id or stamp}"
    out_dir = Path(args.output).expanduser() if args.output else root / "logs" / "crossbot" / "packs" / label
    if out_dir.exists() and not args.force:
        print(f"Error: output exists: {out_dir} (use --force)", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    db = _db_path(root)
    kdb = _kanban_db(root)
    audit_path = _audit_log(root)
    plugin_ver = _plugin_version(root)

    paths = {
        "hermes_root": str(root),
        "crossbot_db": str(db),
        "kanban_db": str(kdb),
        "audit_log": str(audit_path),
        "plugin_dir": str(_plugin_dir(root)),
    }

    outbox_all = _sqlite_query(
        db,
        "SELECT id, ts, from_bot, to_bot, subject, status, response_text, "
        "completed_at, telegram_msg_id, kanban_task_id, "
        "substr(body, 1, 500) AS body_preview FROM outbox ORDER BY id ASC",
    )
    response_log = _sqlite_query(db, "SELECT * FROM response_log ORDER BY id ASC")
    outbox = _outbox_for_round(outbox_all, round_id)

    task_filter = f"%{round_id}%" if round_id else "%"
    kanban_tasks = _sqlite_query(
        kdb,
        "SELECT id, title, assignee, status, created_at, completed_at, "
        "substr(body, 1, 400) AS body_preview FROM tasks "
        "WHERE title LIKE ? OR body LIKE ? ORDER BY rowid ASC",
        (task_filter, task_filter),
    ) if round_id else _sqlite_query(
        kdb,
        "SELECT id, title, assignee, status, created_at, completed_at, "
        "substr(body, 1, 400) AS body_preview FROM tasks ORDER BY rowid DESC LIMIT 50",
    )

    task_ids = [t["id"] for t in kanban_tasks if t.get("id")]
    kanban_events: List[Dict[str, Any]] = []
    kanban_runs: List[Dict[str, Any]] = []
    if task_ids:
        placeholders = ",".join("?" * len(task_ids))
        kanban_events = _sqlite_query(
            kdb,
            f"SELECT * FROM task_events WHERE task_id IN ({placeholders}) ORDER BY id ASC",
            task_ids,
        )
        kanban_runs = _sqlite_query(
            kdb,
            f"SELECT * FROM task_runs WHERE task_id IN ({placeholders}) ORDER BY id ASC",
            task_ids,
        )

    audit_lines: List[str] = []
    if audit_path.is_file():
        audit_lines = audit_path.read_text(encoding="utf-8", errors="replace").splitlines()
    audit_filtered = _filter_audit_lines(audit_lines, round_id)
    audit_events: List[Dict[str, Any]] = []
    for line in audit_filtered:
        try:
            audit_events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    diag = _diagnose(
        round_id=round_id,
        outbox=outbox,
        audit_events=audit_events,
        kanban_tasks=kanban_tasks,
        plugin_version=plugin_ver,
    )

    (out_dir / "audit").mkdir(exist_ok=True)
    (out_dir / "database").mkdir(exist_ok=True)
    (out_dir / "config").mkdir(exist_ok=True)
    (out_dir / "benchmark").mkdir(exist_ok=True)
    (out_dir / "gateway").mkdir(exist_ok=True)

    (out_dir / "audit" / "crossbot-audit.jsonl").write_text(
        "\n".join(audit_filtered) + ("\n" if audit_filtered else ""),
        encoding="utf-8",
    )
    if round_id and audit_filtered != audit_lines:
        shutil.copy2(audit_path, out_dir / "audit" / "crossbot-audit-full.jsonl")

    (out_dir / "database" / "outbox.json").write_text(
        json.dumps(outbox if round_id else outbox_all, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "database" / "response_log.json").write_text(
        json.dumps(response_log, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "database" / "kanban-tasks.json").write_text(
        json.dumps(kanban_tasks, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "database" / "kanban-events.json").write_text(
        json.dumps(kanban_events, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "database" / "kanban-runs.json").write_text(
        json.dumps(kanban_runs, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    for name, src in (
        ("topic-map.json", _plugin_dir(root) / "topic-map.json"),
        ("visibility-config.json", _plugin_dir(root) / "visibility-config.json"),
        ("plugin.yaml", _plugin_dir(root) / "plugin.yaml"),
        ("debug-mode.json", _debug_mode_path(root)),
    ):
        if src.is_file():
            raw = _read_json(src)
            if raw is not None and name != "plugin.yaml":
                (out_dir / "config" / name).write_text(
                    json.dumps(_redact_obj(raw), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            else:
                shutil.copy2(src, out_dir / "config" / name)

    bench_dir = root / "logs" / "crossbot"
    if round_id:
        bp = bench_dir / f"benchmark-{round_id}.json"
        if bp.is_file():
            shutil.copy2(bp, out_dir / "benchmark" / bp.name)

    gw = _gateway_log(root)
    if gw.is_file():
        tail = gw.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
        keywords = re.compile(r"crossbot|kanban|dispatcher|cross-bot", re.I)
        matched = [ln for ln in tail if keywords.search(ln)]
        (out_dir / "gateway" / "gateway-tail.log").write_text(
            "\n".join(matched[-200:]) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "pack_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname": socket.gethostname(),
        "round_filter": round_id,
        "diagnosis": diag,
        "paths": paths,
        "files": sorted(str(p.relative_to(out_dir)) for p in out_dir.rglob("*") if p.is_file()),
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    _write_report_md(
        out_dir / "REPORT.md",
        diag,
        outbox if round_id else outbox_all[-20:],
        audit_events,
        kanban_tasks,
        paths,
    )

    (out_dir / "README.txt").write_text(
        "Crossbot debug pack — envie este ZIP para análise.\n"
        "Leia REPORT.md e MANIFEST.json primeiro.\n"
        "Não edite os JSON antes de enviar.\n",
        encoding="utf-8",
    )

    zip_path: Optional[Path] = None
    if args.zip or not args.no_zip:
        zip_base = out_dir if args.zip else out_dir.parent / label
        zip_file = shutil.make_archive(str(zip_base), "zip", root_dir=out_dir.parent, base_dir=out_dir.name)
        zip_path = Path(zip_file)

    print("")
    print("=" * 60)
    print("  Crossbot debug pack pronto")
    print("=" * 60)
    print(f"  Diretório: {out_dir}")
    if zip_path:
        print(f"  ZIP:       {zip_path}")
    print(f"  Round:     {round_id or '(todos)'}")
    if diag.get("red_flags"):
        print(f"  Alertas:   {', '.join(diag['red_flags'])}")
    print("")
    print("  Envie o ZIP para quem for debugar (Cursor / dev).")
    print("=" * 60)
    print("")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Crossbot debug pack collector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack", help="Coletar artefatos e gerar zip")
    p_pack.add_argument("--round", "-r", help="Filtrar por round (ex: 20260601-1608)")
    p_pack.add_argument("--output", "-o", help="Diretório de saída")
    p_pack.add_argument("--force", action="store_true", help="Sobrescrever diretório existente")
    p_pack.add_argument("--zip", metavar="PATH", help="Caminho base do zip (sem .zip)")
    p_pack.add_argument("--no-zip", action="store_true", help="Não criar zip")

    p_en = sub.add_parser("enable", help="Ativar modo debug (flag local)")
    p_en.add_argument(
        "--auto-benchmark",
        action="store_true",
        help="Sugerir pack automático após benchmark",
    )

    sub.add_parser("disable", help="Desativar modo debug")
    sub.add_parser("status", help="Status do modo debug")

    args = parser.parse_args()
    if args.cmd == "pack":
        return cmd_pack(args)
    if args.cmd == "enable":
        return cmd_enable(args)
    if args.cmd == "disable":
        return cmd_disable(args)
    if args.cmd == "status":
        return cmd_status(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
