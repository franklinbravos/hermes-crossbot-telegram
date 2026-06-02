"""Async Delegate — spawn background subagents without blocking the current turn.

Gives the agent two new tools:
  - delegate_async: Fire-and-forget task spawn (returns task_id immediately)
  - check_async_tasks: Poll task status / list all tasks

Plus a pre_gateway_dispatch hook that captures session routing info,
and a background thread that injects completion notifications into
the SAME session when tasks finish — no webhook needed.

Injection modes:
  - "queue" (default): notification queued behind current turn, no interrupt.
    Use for background research, fire-and-forget tasks.
  - "steer": notification interleaved into agent's tool loop without interrupting.
    Use when the result may change what the agent is doing mid-turn.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TASKS_DIR = Path.home() / ".hermes" / "async-tasks"
MAX_OUTPUT_CHARS = 8000
TASK_TIMEOUT_SECS = 1800
CLEANUP_MAX_AGE_SECS = 86400
DEFAULT_INJECT_MODE = "queue"
WATCHER_POLL_SECS = 5
CLEANUP_INTERVAL_SECS = 300
INJECT_TIMEOUT_SECS = 15
PRE_LLM_THROTTLE = 5
ASYNC_DEFAULT_TOOLSETS = "web,terminal,file,browser,vision"

_gateway_runner: Any = None
_gateway_loop: Any = None
_task_routing: Dict[str, dict] = {}
_routing_lock = threading.Lock()
_watcher_thread: Optional[threading.Thread] = None
_watcher_stop = threading.Event()
_running_procs: Dict[str, subprocess.Popen] = {}
_running_procs_lock = threading.Lock()

_last_cleanup: float = 0
_processed_tasks: set = set()
_pre_llm_counter: int = 0


def _meta_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.json"


def _output_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.output"


def _done_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.done"


def _err_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.err"


def _read_meta(task_id: str) -> Optional[dict]:
    p = _meta_path(task_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_meta(task_id: str, meta: dict) -> None:
    _meta_path(task_id).write_text(json.dumps(meta, indent=2))


def _find_hermes() -> str:
    hermes = shutil.which("hermes")
    if hermes:
        return hermes
    hermes_env = os.environ.get("HERMES_BIN_PATH", "")
    if hermes_env and Path(hermes_env).exists():
        return hermes_env
    for candidate in [
        "/root/.local/bin/hermes",
        "/usr/local/bin/hermes",
        os.path.expanduser("~/.local/bin/hermes"),
    ]:
        if Path(candidate).exists():
            return candidate
    return "hermes"


def _cleanup_old_tasks(now: float) -> None:
    if not TASKS_DIR.exists():
        return
    for meta_file in list(TASKS_DIR.glob("async_*.json")):
        try:
            meta = json.loads(meta_file.read_text())
            task_id = meta.get("task_id", "")
            age = now - meta.get("spawned_at", 0)
            if age > CLEANUP_MAX_AGE_SECS:
                for p in [
                    _meta_path(task_id),
                    _output_path(task_id),
                    _done_path(task_id),
                    _err_path(task_id),
                    TASKS_DIR / f"{task_id}.prompt",
                    TASKS_DIR / f"{task_id}.sh",
                ]:
                    p.unlink(missing_ok=True)
                with _running_procs_lock:
                    _running_procs.pop(task_id, None)
                logger.info("async-delegate: cleaned up stale task %s", task_id)
        except Exception:
            continue


def _reap_timed_out_procs() -> None:
    now = time.time()
    with _running_procs_lock:
        for task_id, proc in list(_running_procs.items()):
            meta = _read_meta(task_id)
            if meta and meta.get("status") == "timeout":
                try:
                    proc.kill()
                    logger.info("async-delegate: killed timed-out process %s (PID %d)", task_id, proc.pid)
                except Exception:
                    pass
                _running_procs.pop(task_id, None)


def _inject_task_notification(task_id: str, meta: dict, exit_code: str) -> None:
    global _gateway_runner

    if not _gateway_runner:
        logger.warning("async-delegate: no gateway_runner captured, cannot inject")
        return

    routing = meta.get("_routing")
    if not routing:
        logger.warning("async-delegate: task %s has no routing info, cannot inject", task_id)
        return

    platform_str = routing.get("platform", "")
    chat_id = routing.get("chat_id", "")
    thread_id = routing.get("thread_id")
    user_id = routing.get("user_id")
    user_name = routing.get("user_name")
    inject_mode = meta.get("inject_mode", DEFAULT_INJECT_MODE)

    if not platform_str or not chat_id:
        logger.warning("async-delegate: task %s missing platform/chat_id in routing", task_id)
        return

    status_label = "Completed" if exit_code == "0" else "Failed (exit %s)".format(exit_code)
    out_file = _output_path(task_id)
    goal = (meta.get("goal", "unknown") or "")[:100]

    synth_text = (
        "[Async Task Done: %s] %s — "
        "Goal: %s — "
        "Result file: %s"
    ) % (task_id, status_label, goal, out_file)

    logger.info(
        "async-delegate: injecting notification for %s (mode=%s) into %s chat=%s thread=%s",
        task_id, inject_mode, platform_str, chat_id, thread_id,
    )

    try:
        from gateway.session import SessionSource, build_session_key
        from gateway.platforms.base import MessageEvent, MessageType, merge_pending_message_event
        from gateway.config import Platform

        # Resolve source from stored routing
        source_data = routing.get("_source")
        if source_data:
            source = SessionSource(**source_data)
        else:
            platform_enum = None
            try:
                platform_enum = Platform(platform_str)
            except ValueError:
                for p in Platform:
                    if p.value == platform_str:
                        platform_enum = p
                        break
            if not platform_enum:
                logger.error("async-delegate: unknown platform '%s'", platform_str)
                return
            source = SessionSource(
                platform=platform_enum,
                chat_id=chat_id,
                chat_type=routing.get("chat_type", "group"),
                user_id=user_id,
                user_name=user_name or "system",
                thread_id=thread_id,
            )

        synth_event = MessageEvent(
            text=synth_text,
            message_type=MessageType.TEXT,
            source=source,
            internal=True,
        )

        adapter = None
        for p, a in _gateway_runner.adapters.items():
            p_val = p.value if hasattr(p, "value") else str(p)
            if p_val == platform_str:
                adapter = a
                break

        if not adapter:
            logger.error("async-delegate: no adapter found for platform '%s'", platform_str)
            return

        loop = _gateway_loop
        if not loop:
            logger.error("async-delegate: no event loop available for injection")
            return

        try:
            session_key = build_session_key(source)
        except Exception:
            session_key = routing.get("session_key", "")
        if not session_key:
            logger.error("async-delegate: could not build session_key for %s", task_id)
            return

        if inject_mode == "steer":
            running_agent = _gateway_runner._running_agents.get(session_key) if hasattr(_gateway_runner, "_running_agents") else None
            if running_agent and hasattr(running_agent, "steer"):
                result_preview = ""
                out_path = _output_path(task_id)
                if out_path.exists():
                    try:
                        result_preview = out_path.read_text()[:2000]
                    except Exception:
                        pass

                steer_text = (
                    "[Async Task Done: %s] %s\n"
                    "Goal: %s\n"
                    "Result file: %s\n"
                ) % (task_id, status_label, goal, out_file)
                if result_preview:
                    steer_text += "Preview:\n%s\n" % result_preview
                steer_text += "— Process this result and incorporate it into your current work."

                steered = bool(running_agent.steer(steer_text))
                if steered:
                    logger.info("async-delegate: steered notification for %s into running agent", task_id)
                    return
                logger.warning("async-delegate: steer() failed for %s, falling back to queue", task_id)
            else:
                logger.info("async-delegate: no running agent for steer, falling back to queue for %s", task_id)

        async def _async_inject():
            is_busy = False
            try:
                is_busy = session_key in adapter._active_sessions
            except Exception:
                pass
            if is_busy:
                try:
                    merge_pending_message_event(adapter._pending_messages, session_key, synth_event)
                    logger.info("async-delegate: queued notification for %s behind active turn", task_id)
                except Exception:
                    await adapter.handle_message(synth_event)
                    logger.info("async-delegate: delivered notification for %s as new turn (fallback)", task_id)
            else:
                await adapter.handle_message(synth_event)
                logger.info("async-delegate: delivered notification for %s as new turn", task_id)

        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(_async_inject(), loop)
            try:
                future.result(timeout=INJECT_TIMEOUT_SECS)
            except TimeoutError:
                logger.warning("async-delegate: injection timed out for %s (gateway loop busy)", task_id)
            except Exception as e:
                logger.error("async-delegate: injection future failed for %s: %s", task_id, e)
        else:
            logger.warning("async-delegate: gateway loop not running, cannot inject %s", task_id)

    except Exception as e:
        logger.error("async-delegate: injection failed for %s: %s", task_id, e)


def _watcher_loop() -> None:
    global _last_cleanup
    logger.info("async-delegate: watcher thread started")

    while not _watcher_stop.is_set():
        try:
            now = time.time()

            if now - _last_cleanup > CLEANUP_INTERVAL_SECS:
                _cleanup_old_tasks(now)
                _reap_timed_out_procs()
                _last_cleanup = now

            if not TASKS_DIR.exists():
                _watcher_stop.wait(WATCHER_POLL_SECS)
                continue

            for done_file in list(TASKS_DIR.glob("async_*.done")):
                task_id = done_file.stem
                meta = _read_meta(task_id)
                if not meta:
                    continue
                if meta.get("status") != "running":
                    continue

                with _routing_lock:
                    routing = _task_routing.get(task_id)
                if not routing:
                    routing = meta.get("_routing")
                    if routing:
                        logger.info("async-delegate: watcher using _routing from JSON for %s", task_id)
                if not routing:
                    logger.warning("async-delegate: watcher skipping %s — no routing info", task_id)
                    continue

                exit_code = done_file.read_text().strip()
                meta["status"] = "completed" if exit_code == "0" else "failed"
                meta["exit_code"] = exit_code
                meta["completed_at"] = now
                _write_meta(task_id, meta)

                _inject_task_notification(task_id, meta, exit_code)

                with _routing_lock:
                    _task_routing.pop(task_id, None)
                with _running_procs_lock:
                    _running_procs.pop(task_id, None)

        except Exception as e:
            logger.error("async-delegate: watcher error: %s", e)

        _watcher_stop.wait(WATCHER_POLL_SECS)

    logger.info("async-delegate: watcher thread stopped")


def _ensure_watcher() -> None:
    global _watcher_thread
    if _watcher_thread and _watcher_thread.is_alive():
        return
    _watcher_stop.clear()
    _watcher_thread = threading.Thread(
        target=_watcher_loop,
        name="async-delegate-watcher",
        daemon=True,
    )
    _watcher_thread.start()


def _stop_watcher() -> None:
    if _watcher_thread and _watcher_thread.is_alive():
        _watcher_stop.set()
        _watcher_thread.join(timeout=3)
        logger.info("async-delegate: watcher thread stopped")


def delegate_async_tool(
    goal: str,
    context: str = "",
    inject_mode: str = DEFAULT_INJECT_MODE,
    toolsets: str = "",
    routing: Optional[Dict[str, str]] = None,
) -> str:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    if inject_mode not in ("queue", "steer"):
        inject_mode = DEFAULT_INJECT_MODE

    resolved_toolsets = toolsets.strip() if toolsets.strip() else ASYNC_DEFAULT_TOOLSETS

    task_id = "async_%s" % uuid.uuid4().hex[:8]

    prompt = goal
    if context:
        prompt = "%s\n\nAdditional context:\n%s" % (goal, context)
    prompt += (
        "\n\nIMPORTANT: Do NOT use the delegate_async or delegate_task tool. "
        "Complete this task yourself using your own tools."
    )

    meta: Dict[str, Any] = {
        "task_id": task_id,
        "goal": goal[:500],
        "status": "running",
        "spawned_at": time.time(),
        "inject_mode": inject_mode,
        "toolsets": resolved_toolsets,
    }

    prompt_file = TASKS_DIR / "%s.prompt" % task_id
    prompt_file.write_text(prompt)

    out_file = _output_path(task_id)
    done_file = _done_path(task_id)
    err_file = _err_path(task_id)
    hermes_bin = _find_hermes()

    wrapper_script = TASKS_DIR / "%s.sh" % task_id
    wrapper_script.write_text(
        '#!/bin/bash\n'
        'PROMPT=$(cat "%s")\n'
        '"%s" chat -q "$PROMPT" -Q -t "%s" >"%s" 2>"%s"\n'
        'echo $? >"%s"\n'
    ) % (prompt_file, hermes_bin, resolved_toolsets, out_file, err_file, done_file)
    wrapper_script.chmod(0o755)

    try:
        proc = subprocess.Popen(
            ["bash", str(wrapper_script)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        meta["pid"] = proc.pid
        with _running_procs_lock:
            _running_procs[task_id] = proc
    except OSError as e:
        meta["status"] = "failed"
        meta["error"] = "failed to spawn subprocess: %s" % e
        _write_meta(task_id, meta)
        return json.dumps({
            "task_id": task_id,
            "status": "failed",
            "error": meta["error"],
        })

    if routing:
        meta["_routing"] = routing
        with _routing_lock:
            _task_routing[task_id] = routing

    _write_meta(task_id, meta)

    logger.info("async-delegate: spawned %s (PID %d, mode=%s)", task_id, proc.pid, inject_mode)

    return json.dumps({
        "task_id": task_id,
        "status": "running",
        "inject_mode": inject_mode,
        "toolsets": resolved_toolsets,
        "message": (
            "Async task `%s` spawned in background (mode: %s, toolsets: %s). "
            "I will be notified when it completes and can process the results. "
            "You can continue chatting with me in the meantime!"
        ) % (task_id, inject_mode, resolved_toolsets),
    })


def check_async_tasks_tool(task_id: str = "") -> str:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    if task_id:
        meta = _read_meta(task_id)
        if meta is None:
            return json.dumps({"error": "Task %s not found" % task_id})

        _refresh_status(task_id, meta)
        _write_meta(task_id, meta)

        if meta.get("status") in ("completed", "failed"):
            out = _output_path(task_id)
            if out.exists():
                meta["result"] = out.read_text()[:MAX_OUTPUT_CHARS]

        return json.dumps(meta, indent=2)

    tasks = []
    for meta_file in sorted(TASKS_DIR.glob("async_*.json")):
        try:
            meta = json.loads(meta_file.read_text())
            _refresh_status(meta["task_id"], meta)
            tasks.append({
                "task_id": meta["task_id"],
                "goal": (meta.get("goal", "") or "")[:100],
                "status": meta.get("status", "unknown"),
                "inject_mode": meta.get("inject_mode", DEFAULT_INJECT_MODE),
                "spawned_at": meta.get("spawned_at"),
            })
        except Exception:
            continue

    return json.dumps({"tasks": tasks, "count": len(tasks)}, indent=2)


def _refresh_status(task_id: str, meta: dict) -> None:
    if meta.get("status") != "running":
        return

    done_file = _done_path(task_id)
    if done_file.exists():
        exit_code = done_file.read_text().strip()
        meta["status"] = "completed" if exit_code == "0" else "failed"
        meta["exit_code"] = exit_code
        meta["completed_at"] = time.time()
        return

    elapsed = time.time() - meta.get("spawned_at", 0)
    if elapsed > TASK_TIMEOUT_SECS:
        meta["status"] = "timeout"
        meta["completed_at"] = time.time()
        logger.warning("async-delegate: task %s timed out after %ds", task_id, int(elapsed))


def capture_routing(**kwargs) -> Optional[Dict[str, str]]:
    global _gateway_runner

    event = kwargs.get("event")
    gateway = kwargs.get("gateway")

    global _gateway_runner, _gateway_loop
    if gateway and not _gateway_runner:
        _gateway_runner = gateway
        try:
            _gateway_loop = asyncio.get_running_loop()
            logger.info("async-delegate: captured GatewayRunner + event loop")
        except RuntimeError:
            logger.info("async-delegate: captured GatewayRunner (no running loop at boot)")
        _ensure_watcher()

    if not event:
        return None

    source = getattr(event, "source", None)
    if not source:
        return None

    source_dict = {
        "platform": source.platform.value if hasattr(source.platform, "value") else str(source.platform),
        "chat_id": source.chat_id or "",
        "chat_type": source.chat_type or "dm",
        "user_id": source.user_id,
        "user_name": source.user_name,
        "thread_id": source.thread_id,
    }

    routing: Dict[str, str] = {
        "platform": source_dict["platform"],
        "chat_id": source_dict["chat_id"],
        "chat_type": source_dict["chat_type"],
        "thread_id": source_dict["thread_id"],
        "user_id": source_dict["user_id"] or "",
        "user_name": source_dict["user_name"] or "",
        "_source": source_dict,
    }

    with _routing_lock:
        _task_routing["_latest"] = routing

    return None


def pre_llm_inject_results(**kwargs) -> Optional[Dict[str, str]]:
    global _pre_llm_counter
    _pre_llm_counter += 1
    if _pre_llm_counter % PRE_LLM_THROTTLE != 0:
        return None

    if not TASKS_DIR.exists():
        return None

    if not list(TASKS_DIR.glob("async_*.json")):
        return None

    now = time.time()
    completed_results: List[str] = []

    for meta_file in list(TASKS_DIR.glob("async_*.json")):
        try:
            meta = json.loads(meta_file.read_text())
            task_id = meta.get("task_id", "")

            if task_id in _processed_tasks:
                continue

            if meta.get("status") != "running":
                _processed_tasks.add(task_id)
                continue

            done_file = _done_path(task_id)
            if not done_file.exists():
                if now - meta.get("spawned_at", 0) > TASK_TIMEOUT_SECS:
                    meta["status"] = "timeout"
                    meta["completed_at"] = now
                    _write_meta(task_id, meta)
                    completed_results.append(
                        "[Async Task Timed Out: %s] "
                        "Goal: %s "
                        "(ran >%dmin)"
                    ) % (task_id, (meta.get("goal", "unknown") or "")[:100], TASK_TIMEOUT_SECS // 60)
                    _processed_tasks.add(task_id)
                continue

            exit_code = done_file.read_text().strip()
            meta["status"] = "completed" if exit_code == "0" else "failed"
            meta["exit_code"] = exit_code
            meta["completed_at"] = now
            _write_meta(task_id, meta)
            _processed_tasks.add(task_id)

            status_label = "Completed" if exit_code == "0" else "Failed (exit %s)".format(exit_code)

            result_text = (
                "[Async Task Done: %s] "
                "%s — "
                "Goal: %s — "
                "Result file: %s"
            ) % (task_id, status_label, (meta.get("goal", "unknown") or "")[:100], _output_path(task_id))

            completed_results.append(result_text)
            logger.info("async-delegate: %s completed (exit=%s) via pre_llm fallback", task_id, exit_code)

        except Exception as e:
            logger.warning("async-delegate: error in pre_llm hook: %s", e)
            continue

    if not completed_results:
        return None

    ping_lines = "\n".join(completed_results)
    context = (
        "[Async Delegate — Tasks Done]\n"
        "One or more background tasks finished. Read result files with read_file if needed.\n"
        "%s\n"
    ) % ping_lines
    return {"context": context}


def cleanup_stale_tasks(**kwargs) -> None:
    _cleanup_old_tasks(time.time())


def register(ctx) -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_watcher()

    _routing_for_spawn: List[Optional[Dict[str, str]]] = [None]

    ctx.register_tool(
        name="delegate_async",
        handler=lambda args, **kw: delegate_async_tool(
            goal=args.get("goal", ""),
            context=args.get("context", ""),
            inject_mode=args.get("inject_mode", DEFAULT_INJECT_MODE),
            toolsets=args.get("toolsets", ""),
            routing=_routing_for_spawn[0],
        ),
        schema={
            "name": "delegate_async",
            "description": (
                "Spawn a background subagent to work on a task ASYNCHRONOUSLY. "
                "Returns immediately with a task_id — you are NOT blocked and can continue "
                "the conversation normally. When the task completes, a notification is "
                "automatically injected into this session so you can process results.\n\n"
                "INJECTION MODES:\n"
                "- \"queue\" (default): notification waits for current turn to finish.\n"
                "- \"steer\": notification interleaved into current tool loop."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "What the subagent should accomplish.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional background information.",
                    },
                    "inject_mode": {
                        "type": "string",
                        "enum": ["queue", "steer"],
                        "description": "queue=wait for turn end, steer=interleave mid-turn",
                        "default": DEFAULT_INJECT_MODE,
                    },
                    "toolsets": {
                        "type": "string",
                        "description": "Comma-separated toolsets. Default: web,terminal,file,browser,vision",
                        "default": "",
                    },
                },
                "required": ["goal"],
            },
        },
        toolset="async-delegation",
        description="Spawn a background subagent asynchronously.",
        emoji="🚀",
        check_fn=lambda: True,
    )

    ctx.register_tool(
        name="check_async_tasks",
        handler=lambda args, **kw: check_async_tasks_tool(
            task_id=args.get("task_id", ""),
        ),
        schema={
            "name": "check_async_tasks",
            "description": "Check status of async delegated tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Specific task ID, or empty to list all.",
                    },
                },
                "required": [],
            },
        },
        toolset="async-delegation",
        description="Check status of async delegated tasks.",
        emoji="📋",
        check_fn=lambda: True,
    )

    class _RoutingCapture:
        def __call__(self, **kw) -> Optional[Dict[str, str]]:
            with _routing_lock:
                latest = _task_routing.get("_latest")
                if latest:
                    _routing_for_spawn[0] = latest
            return capture_routing(**kw)

    ctx.register_hook("pre_gateway_dispatch", _RoutingCapture())
    ctx.register_hook("pre_llm_call", pre_llm_inject_results)
    ctx.register_hook("on_session_end", cleanup_stale_tasks)

    logger.info("async-delegate plugin registered (v7 — dual-mode injection: queue + steer)")
