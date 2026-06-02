#!/usr/bin/env python3
"""Crossbot guided onboarding — state machine, verifiers, agent context."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STATE_VERSION = 1
MIN_PLUGIN_VERSION = (0, 5, 2)


def hermes_root() -> Path:
    home = os.environ.get("HERMES_HOME", "")
    if home and "/profiles/" in home:
        return Path(home.split("/profiles/")[0])
    return Path(os.environ.get("HERMES_ROOT", Path.home() / ".hermes"))


def plugin_dir(root: Optional[Path] = None) -> Path:
    return (root or hermes_root()) / "plugins" / "crossbot"


def state_path(root: Optional[Path] = None) -> Path:
    return (root or hermes_root()) / "data" / "crossbot-onboarding.json"


def manifest_path(root: Optional[Path] = None) -> Path:
    installed = plugin_dir(root) / "onboarding-manifest.json"
    if installed.is_file():
        return installed
    bundled = Path(__file__).resolve().parent / "onboarding-manifest.json"
    return bundled


def db_path(root: Optional[Path] = None) -> Path:
    root = root or hermes_root()
    for candidate in (
        os.environ.get("CROSSBOT_DB_PATH", ""),
        os.environ.get("MULTI_AGENT_TG_DB_PATH", ""),
        str(root / "data" / "crossbot.db"),
        str(root / "data" / "multi_agent_tg_shared.db"),
    ):
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return root / "data" / "crossbot.db"


def kanban_db(root: Optional[Path] = None) -> Path:
    root = root or hermes_root()
    board = os.environ.get("CROSSBOT_KANBAN_BOARD", "cross-bot")
    return root / "kanban" / "boards" / board / "kanban.db"


def audit_log_path(root: Optional[Path] = None) -> Path:
    root = root or hermes_root()
    raw = os.environ.get(
        "CROSSBOT_AUDIT_LOG",
        str(root / "logs" / "crossbot" / "crossbot-audit.jsonl"),
    )
    return Path(raw)


def load_manifest(root: Optional[Path] = None) -> Dict[str, Any]:
    path = manifest_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"onboarding manifest missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = state_path(root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_state(state: Dict[str, Any], root: Optional[Path] = None) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_active(root: Optional[Path] = None) -> bool:
    st = load_state(root)
    return bool(st and st.get("active"))


def step_order(manifest: Optional[Dict[str, Any]] = None) -> List[str]:
    manifest = manifest or load_manifest()
    return list(manifest.get("step_order") or [])


def _parse_version(v: str) -> Tuple[int, ...]:
    parts = re.findall(r"\d+", str(v))
    return tuple(int(p) for p in parts[:3]) if parts else (0, 0, 0)


def _read_plugin_yaml(root: Path) -> str:
    p = plugin_dir(root) / "plugin.yaml"
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def _plugin_version(root: Path) -> str:
    m = re.search(r"version:\s*(\S+)", _read_plugin_yaml(root))
    return m.group(1) if m else "0"


def _plugin_hooks(root: Path) -> List[str]:
    hooks: List[str] = []
    for line in _read_plugin_yaml(root).splitlines():
        m = re.match(r"\s*-\s*(\S+)", line)
        if m and "hook" not in line.lower():
            hooks.append(m.group(1))
    return hooks


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _topic_map(root: Path) -> Dict[str, Any]:
    data = _read_json(plugin_dir(root) / "topic-map.json")
    return data if isinstance(data, dict) else {}


def _visibility_config(root: Path) -> Dict[str, Any]:
    data = _read_json(plugin_dir(root) / "visibility-config.json")
    return data if isinstance(data, dict) else {}


def _sqlite_query(db: Path, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
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


def _read_audit_events(root: Path, since_ts: Optional[float] = None) -> List[Dict[str, Any]]:
    path = audit_log_path(root)
    if not path.is_file():
        return []
    events: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since_ts and float(ev.get("ts") or 0) < since_ts:
            continue
        events.append(ev)
    return events


def _audit_for_outbox(root: Path, outbox_id: int) -> List[Dict[str, Any]]:
    return [
        ev for ev in _read_audit_events(root)
        if ev.get("outbox_id") == outbox_id
    ]


def _first_player(root: Path) -> str:
    tm = _topic_map(root)
    orch = str(tm.get("orchestrator") or "").strip()
    topics = tm.get("topics") or {}
    if not isinstance(topics, dict):
        return ""
    for name in sorted(topics.keys()):
        if name != orch:
            return name
    return ""


def _second_player(root: Path) -> str:
    tm = _topic_map(root)
    orch = str(tm.get("orchestrator") or "").strip()
    players = [n for n in sorted((tm.get("topics") or {}).keys()) if n != orch]
    return players[1] if len(players) > 1 else ""


def _verify_result(
    passed: bool,
    flags: Optional[List[str]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    message: str = "",
) -> Dict[str, Any]:
    return {
        "passed": passed,
        "status": "passed" if passed else "failed",
        "flags": flags or [],
        "evidence": evidence or {},
        "message": message,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def verify_step(step_id: str, state: Dict[str, Any], root: Optional[Path] = None) -> Dict[str, Any]:
    root = root or hermes_root()
    manifest = load_manifest(root)
    step = (manifest.get("steps") or {}).get(step_id) or {}
    verifier = step.get("verifier") or ""

    if verifier == "plugin_install":
        ver = _parse_version(_plugin_version(root))
        hooks = _plugin_hooks(root)
        init_py = (plugin_dir(root) / "__init__.py").read_text(encoding="utf-8", errors="replace")
        bad_cli = bool(
            re.search(r"OBRIGATÓRIO[^\n]*crossbot_cli", init_py, re.I)
            or "crossbot_cli respond" in init_py.lower()
        )
        flags = []
        if ver < MIN_PLUGIN_VERSION:
            flags.append("PLUGIN_VERSION_TOO_OLD")
        if "post_tool_call" not in hooks:
            flags.append("MISSING_POST_TOOL_CALL_HOOK")
        if "pre_llm_call" not in hooks:
            flags.append("MISSING_PRE_LLM_CALL_HOOK")
        if bad_cli:
            flags.append("WORKER_INSTRUCTIONS_REQUIRE_CLI")
        passed = not flags
        return _verify_result(
            passed, flags,
            {"version": _plugin_version(root), "hooks": hooks},
            "Plugin install OK" if passed else "Atualize crossbot >= 0.6.0",
        )

    if verifier == "legacy_migrate":
        legacy = [
            plugin_dir(root).parent / "kanban-context",
            plugin_dir(root).parent / "multi-agent-context",
        ]
        found = [str(p) for p in legacy if p.is_dir()]
        passed = len(found) == 0
        return _verify_result(
            passed,
            ["LEGACY_PLUGINS_PRESENT"] if not passed else [],
            {"legacy_dirs": found},
        )

    if verifier == "topic_map":
        tm = _topic_map(root)
        orch = str(tm.get("orchestrator") or "").strip()
        topics = tm.get("topics") or {}
        handles = tm.get("handles") or {}
        chat_id = str(tm.get("chat_id") or "").strip()
        flags = []
        profiles = root / "profiles"
        if not orch:
            flags.append("NO_ORCHESTRATOR")
        if not chat_id or "X" in chat_id.upper():
            flags.append("INVALID_CHAT_ID")
        if not isinstance(topics, dict) or len(topics) < 2:
            flags.append("INSUFFICIENT_TOPICS")
        for name in topics:
            if not (profiles / name).is_dir():
                flags.append(f"PROFILE_MISSING:{name}")
        if not handles:
            flags.append("NO_HANDLES")
        passed = not flags
        return _verify_result(passed, flags, {"orchestrator": orch, "topics": list(topics.keys())})

    if verifier == "visibility_probe":
        vis = _visibility_config(root)
        chat = str(vis.get("visibility_chat_id") or "").strip()
        flags = []
        if not chat or "X" in chat.upper() or "placeholder" in chat.lower():
            flags.append("VISIBILITY_CHAT_PLACEHOLDER")
        cutoff = time.time() - 900
        for ev in _read_audit_events(root, since_ts=cutoff):
            if ev.get("event") != "visibility_post":
                continue
            cid = str(ev.get("chat_id") or "")
            if not ev.get("ok") or "X" in cid.upper() or "not found" in str(ev.get("error") or "").lower():
                flags.append("VISIBILITY_CHAT_PLACEHOLDER")
                break
        tm = _topic_map(root)
        orch = str(tm.get("orchestrator") or "")
        token_ok = bool(str(vis.get("telegram_bot_token") or "").strip())
        if not token_ok and orch:
            env_path = root / "profiles" / orch / ".env"
            if env_path.is_file() and "TELEGRAM_BOT_TOKEN=" in env_path.read_text():
                token_ok = True
        if not token_ok:
            flags.append("NO_VISIBILITY_TOKEN")
        passed = not flags
        return _verify_result(passed, flags, {"visibility_chat_id": chat})

    if verifier == "kanban_board":
        kdb = kanban_db(root)
        passed = kdb.is_file()
        return _verify_result(passed, [] if passed else ["KANBAN_BOARD_MISSING"], {"path": str(kdb)})

    if verifier == "gateways_env":
        tm = _topic_map(root)
        topics = tm.get("topics") or {}
        flags = []
        db_refs: set = set()
        for name in topics:
            env_f = root / "profiles" / name / ".env"
            if not env_f.is_file():
                flags.append(f"ENV_MISSING:{name}")
                continue
            text = env_f.read_text(encoding="utf-8", errors="replace")
            bot_name = ""
            for line in text.splitlines():
                if line.startswith("CROSSBOT_BOT_NAME="):
                    bot_name = line.split("=", 1)[1].strip().strip('"').strip("'")
                if "CROSSBOT_DB_PATH=" in line or "MULTI_AGENT_TG_DB_PATH=" in line:
                    db_refs.add(line.strip())
            if bot_name and bot_name != name:
                flags.append(f"CROSSBOT_BOT_NAME_MISMATCH:{name}")
        if len(db_refs) > 1:
            flags.append("DB_PATH_INCONSISTENT")
        passed = not any(f.startswith("ENV_MISSING") or "MISMATCH" in f for f in flags)
        return _verify_result(passed, flags, {"profiles_checked": list(topics.keys())})

    if verifier == "ping_bot1":
        ev = state.get("evidence") or {}
        oid = ev.get("ping_outbox_id")
        if not oid:
            return _verify_result(False, ["NO_PING_SENT"], {}, "Rode: crossbot-onboarding.sh run-action")
        rows = _sqlite_query(db_path(root), "SELECT * FROM outbox WHERE id=?", (oid,))
        if not rows:
            return _verify_result(False, ["OUTBOX_NOT_FOUND"], {}, f"outbox #{oid} missing")
        row = rows[0]
        tm = _topic_map(root)
        to_bot = row.get("to_bot")
        expected_thread = (tm.get("topics") or {}).get(to_bot)
        flags = []
        audit = _audit_for_outbox(root, int(oid))
        vis = [e for e in audit if e.get("event") == "visibility_post"]
        if not vis or not any(e.get("ok") for e in vis):
            flags.append("VISIBILITY_POST_FAILED")
        else:
            last = vis[-1]
            if str(last.get("chat_id")) != str(tm.get("chat_id")):
                flags.append("CHAT_ID_MISMATCH")
            if expected_thread is not None and int(last.get("thread_id") or 0) != int(expected_thread):
                flags.append("THREAD_ID_MISMATCH")
        if not row.get("kanban_task_id"):
            flags.append("NO_KANBAN_TASK")
        passed = not flags
        return _verify_result(passed, flags, {"outbox": row, "audit": vis[-1] if vis else {}})

    if verifier == "bot1_respond":
        ev = state.get("evidence") or {}
        oid = ev.get("ping_outbox_id")
        if not oid:
            return _verify_result(False, ["NO_PING_OUTBOX"], {})
        rows = _sqlite_query(db_path(root), "SELECT * FROM outbox WHERE id=?", (oid,))
        if not rows:
            return _verify_result(False, ["OUTBOX_NOT_FOUND"], {})
        row = rows[0]
        task_id = row.get("kanban_task_id") or ""
        flags = []
        if task_id:
            tasks = _sqlite_query(
                kanban_db(root),
                "SELECT id, status, body FROM tasks WHERE id=?",
                (task_id,),
            )
            if tasks:
                t = tasks[0]
                body = str(t.get("body") or "")
                if t.get("status") == "blocked":
                    events = _sqlite_query(
                        kanban_db(root),
                        "SELECT payload FROM task_events WHERE task_id=? AND kind='blocked' ORDER BY id DESC LIMIT 1",
                        (task_id,),
                    )
                    reason = events[0].get("payload", "") if events else ""
                    if "Security scan" in reason or "pending_approval" in reason:
                        flags.append("WORKER_TERMINAL_BLOCKED")
                    else:
                        flags.append("KANBAN_TASK_BLOCKED")
                if t.get("status") == "done" and row.get("status") == "pending":
                    flags.append("KANBAN_DONE_OUTBOX_PENDING")
                if "crossbot_cli" in body and "OBRIGATÓRIO" in body:
                    flags.append("WORKER_INSTRUCTIONS_REQUIRE_CLI")
        audit = _audit_for_outbox(root, int(oid))
        if row.get("status") != "done":
            if "WORKER_TERMINAL_BLOCKED" not in flags and "KANBAN_TASK_BLOCKED" not in flags:
                flags.append("OUTBOX_ALL_PENDING")
        elif not any(e.get("event") == "crossbot_respond" for e in audit):
            flags.append("NO_CROSSBOT_RESPOND_IN_AUDIT")
        passed = row.get("status") == "done" and not flags
        return _verify_result(passed, flags, {"outbox_status": row.get("status")})

    if verifier == "ping_bot2":
        ev = state.get("evidence") or {}
        oid = ev.get("ping_outbox_id")
        flags = []
        relay = [e for e in _read_audit_events(root) if e.get("event") == "benchmark_relay"]
        second = _sqlite_query(
            db_path(root),
            "SELECT id FROM outbox WHERE id > ? ORDER BY id ASC LIMIT 5",
            (oid or 0,),
        )
        if not relay and len(second) < 1:
            flags.append("BENCHMARK_CHAIN_NOT_RELAYED")
        passed = not flags
        return _verify_result(passed, flags, {"relay_count": len(relay), "extra_outbox": second})

    if verifier == "benchmark_chain":
        ev = state.get("evidence") or {}
        round_id = ev.get("benchmark_round") or ""
        flags = []
        if round_id:
            bench = root / "logs" / "crossbot" / f"benchmark-{round_id}.json"
            if bench.is_file():
                data = _read_json(bench)
                if not data or not data.get("success"):
                    flags.append("BENCHMARK_INCOMPLETE")
            else:
                flags.append("BENCHMARK_REPORT_MISSING")
        else:
            flags.append("NO_BENCHMARK_ROUND")
        passed = not flags
        return _verify_result(passed, flags, {"round": round_id})

    if verifier == "handoff":
        packs = sorted((root / "logs" / "crossbot" / "packs").glob("*.zip"), reverse=True)
        passed = bool(packs)
        flags = [] if passed else ["NO_DEBUG_PACK"]
        return _verify_result(passed, flags, {"latest_pack": str(packs[0]) if packs else ""})

    return _verify_result(False, ["UNKNOWN_VERIFIER"], {"verifier": verifier})


def run_action(step_id: str, state: Dict[str, Any], root: Optional[Path] = None) -> Dict[str, Any]:
    root = root or hermes_root()
    if step_id == "6":
        import importlib.util

        tm = _topic_map(root)
        orch = str(tm.get("orchestrator") or os.environ.get("CROSSBOT_BOT_NAME") or "")
        first = _first_player(root)
        if not orch or not first:
            return {"ok": False, "error": "orchestrator or first player missing in topic-map"}
        init_path = plugin_dir(root) / "__init__.py"
        spec = importlib.util.spec_from_file_location("crossbot_plugin", init_path)
        if not spec or not spec.loader:
            return {"ok": False, "error": "cannot load crossbot plugin"}
        mod = importlib.util.module_from_spec(spec)
        os.environ.setdefault("CROSSBOT_BOT_NAME", orch)
        spec.loader.exec_module(mod)
        body = (
            f"ONBOARDING_PING\nrun_id: {state.get('onboarding_run_id')}\n"
            f"step: 6\nConfirm receipt in natural language."
        )
        oid = mod.crossbot_send(
            to_bot=first,
            subject=f"[Onboarding] step6 ping run={state.get('onboarding_run_id')}",
            body=body,
        )
        state.setdefault("evidence", {})["ping_outbox_id"] = oid
        state.setdefault("evidence", {})["ping_to_bot"] = first
        save_state(state, root)
        return {"ok": True, "outbox_id": oid, "to_bot": first}

    if step_id == "9":
        return {
            "ok": True,
            "hint": "Run: ./scripts/fui-ao-mercado.sh then ./scripts/benchmark-report.sh",
        }

    if step_id == "10":
        return {"ok": True, "hint": "Run: ./scripts/crossbot-debug-pack.sh pack"}

    step = load_manifest(root)["steps"].get(step_id) or {}
    return {"ok": True, "hint": step.get("action_hint", "")}


def cmd_start(root: Optional[Path] = None) -> Dict[str, Any]:
    root = root or hermes_root()
    manifest = load_manifest(root)
    order = step_order(manifest)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    state = {
        "version": STATE_VERSION,
        "active": True,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "onboarding_run_id": run_id,
        "current_step": order[0] if order else "1",
        "passed_steps": [],
        "evidence": {},
        "steps": {},
    }
    save_state(state, root)
    return state


def cmd_reset(step: Optional[str] = None, root: Optional[Path] = None) -> Dict[str, Any]:
    path = state_path(root)
    if path.is_file():
        path.unlink()
    if step:
        st = cmd_start(root)
        st["current_step"] = step
        save_state(st, root)
        return st
    return cmd_start(root)


def cmd_status(root: Optional[Path] = None) -> Dict[str, Any]:
    st = load_state(root)
    if not st:
        return {"active": False, "message": "Onboarding not started. Run: crossbot-onboarding.sh start"}
    manifest = load_manifest(root)
    order = step_order(manifest)
    cur = st.get("current_step")
    idx = order.index(cur) if cur in order else 0
    return {
        "active": st.get("active", True),
        "onboarding_run_id": st.get("onboarding_run_id"),
        "current_step": cur,
        "step_index": f"{idx + 1}/{len(order)}",
        "passed_steps": st.get("passed_steps") or [],
        "evidence": st.get("evidence") or {},
        "last_verify": (st.get("steps") or {}).get(cur, {}).get("last_verify"),
    }


def cmd_current(root: Optional[Path] = None) -> Dict[str, Any]:
    st = load_state(root)
    if not st:
        return {"error": "not_started"}
    manifest = load_manifest(root)
    cur = st.get("current_step")
    step = (manifest.get("steps") or {}).get(cur) or {}
    order = step_order(manifest)
    idx = order.index(cur) if cur in order else 0
    last = (st.get("steps") or {}).get(cur, {}).get("last_verify")
    return {
        "step": cur,
        "step_index": f"{idx + 1}/{len(order)}",
        "title": step.get("title"),
        "doc_path": step.get("doc_path"),
        "action_hint": step.get("action_hint"),
        "failure_hints": step.get("failure_hints") or [],
        "last_verify": last,
        "do_not": [
            "Não avance sem verify passed",
            "Não use crossbot_cli no worker Kanban",
            "Use crossbot-debug-pack.sh para evidências",
        ],
    }


def cmd_verify(
    watch: int = 0,
    step: Optional[str] = None,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    st = load_state(root)
    if not st:
        return {"error": "not_started"}
    cur = step or st.get("current_step")
    deadline = time.time() + watch if watch > 0 else time.time()
    result: Dict[str, Any] = {}
    while True:
        result = verify_step(cur, st, root)
        st.setdefault("steps", {})[cur] = {
            "last_verify": result,
            "verify_attempts": st.get("steps", {}).get(cur, {}).get("verify_attempts", 0) + 1,
        }
        save_state(st, root)
        if result.get("passed") or time.time() >= deadline:
            break
        if watch > 0:
            time.sleep(5)
        else:
            break
    result["step"] = cur
    if not result.get("passed"):
        result["debug_hint"] = "./scripts/crossbot-debug-pack.sh pack"
    return result


def cmd_advance(root: Optional[Path] = None) -> Dict[str, Any]:
    st = load_state(root)
    if not st:
        return {"error": "not_started"}
    manifest = load_manifest(root)
    order = step_order(manifest)
    cur = st.get("current_step")
    last = (st.get("steps") or {}).get(cur, {}).get("last_verify")
    if not last or not last.get("passed"):
        return {
            "error": "verify_failed",
            "message": "Rode verify antes de advance",
            "last_verify": last,
        }
    passed = st.setdefault("passed_steps", [])
    if cur not in passed:
        passed.append(cur)
    idx = order.index(cur) if cur in order else -1
    if idx < 0 or idx >= len(order) - 1:
        st["active"] = False
        st["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        save_state(st, root)
        return {"completed": True, "message": "Onboarding concluído"}
    nxt = order[idx + 1]
    st["current_step"] = nxt
    save_state(st, root)
    return {"advanced_to": nxt, "passed_step": cur}


def inject_onboarding_context(**kwargs: Any) -> Optional[Dict[str, str]]:
    if not is_active():
        return None
    cur = cmd_current()
    if cur.get("error"):
        return None
    lines = [
        f"[Crossbot Onboarding — step {cur.get('step_index')}: {cur.get('title')}]",
        f"Ação: {cur.get('action_hint')}",
        f"Doc: {cur.get('doc_path')}",
    ]
    lv = cur.get("last_verify")
    if lv and not lv.get("passed"):
        lines.append(f"Último verify FALHOU: flags={lv.get('flags')}")
        for h in cur.get("failure_hints") or []:
            lines.append(f"  - {h}")
        lines.append("Rode: crossbot-onboarding.sh verify --watch 180")
    lines.append("PROIBIDO: pular etapas ou declarar sucesso sem verify passed + advance.")
    return {"context": "\n".join(lines)}


def tool_status(**kwargs: Any) -> str:
    return json.dumps(cmd_status(), indent=2, ensure_ascii=False)


def tool_verify(**kwargs: Any) -> str:
    watch = int(kwargs.get("watch_seconds") or 0)
    return json.dumps(cmd_verify(watch=watch), indent=2, ensure_ascii=False)


def tool_advance(**kwargs: Any) -> str:
    return json.dumps(cmd_advance(), indent=2, ensure_ascii=False)


def record_benchmark_round(round_id: str, root: Optional[Path] = None) -> None:
    st = load_state(root)
    if not st:
        return
    st.setdefault("evidence", {})["benchmark_round"] = round_id
    save_state(st, root or hermes_root())
