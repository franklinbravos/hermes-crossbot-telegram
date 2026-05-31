"""kanban-context — injects Kanban activity + cross-bot messaging for agents.

Two integrated features:

FEATURE 1: Kanban Activity Injection
-------------------------------------
Reads recent task_events from all kanban boards and injects them as a
``[Recent Kanban Activity]`` context block before each LLM call.

FEATURE 2: Cross-Bot Messaging
-------------------------------
Because Telegram bots cannot see messages from other bots (a hard Telegram
API limitation), this plugin implements a **cross-bot message bus** using
a shared SQLite ``outbox`` table.

HOW IT WORKS
------------
1. Bot A (sender) calls ``crossbot_send()`` with the target bot name and
   message body.  This:
   a) Writes a row to the shared ``outbox`` table (pending status)
   b) Creates a Kanban task assigned to the target bot for tracking

2. Bot B (receiver) discovers the message in one of two ways:
   - **Kanban dispatcher** picks up the new task and spawns a worker
   - **pre_llm_call hook** reads the outbox and injects pending messages
     as ``[Pending Messages]`` context

3. Bot B processes the message by calling ``crossbot_respond()``, which:
   a) Marks the outbox row as ``done``
   b) Records the response text
   c) Completes the Kanban task with a summary

This gives full transparency: every cross-bot exchange is tracked both
in the shared SQLite outbox and in the Kanban board.

Configuration via environment variables
-----------------------------------------
    KANBAN_CONTEXT_EVENT_LIMIT   — Max events to inject (default: 10)
    KANBAN_CONTEXT_LOOKBACK_H    — Lookback window in hours (default: 12)
    MULTI_AGENT_TG_DB_PATH       — Shared SQLite DB path (from multi-agent-context)
    CROSSBOT_BOT_NAME            — This bot's name for outbox addressing
                                   (default: HERMES profile name or "bot")
"""

from __future__ import annotations

import functools
import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_HERMES_HOME: Optional[Path] = None


def _hermes_home() -> Path:
    global _HERMES_HOME
    if _HERMES_HOME is None:
        try:
            from hermes_constants import get_hermes_home
            _HERMES_HOME = Path(get_hermes_home())
        except ImportError:
            _HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    return _HERMES_HOME


def _real_hermes_home() -> Path:
    """Resolve the real Hermes home directory, which may differ from
    the profile-isolated HERMES_HOME.

    Under profile isolation (profiles/<name>/), HERMES_HOME points to
    e.g. ~/.hermes/profiles/ti/, but the kanban database lives at
    the real root ~/.hermes/kanban.db (shared across all profiles).
    """
    h = _hermes_home()
    # Walk up if we're inside a profiles/<name>/ directory
    parts = h.parts
    if "/profiles/" in str(h) or (len(parts) >= 2 and parts[-2] == "profiles"):
        return h.parent.parent
    # Fallback: check if kanban.db exists in the parent
    try:
        if h.parent.joinpath("kanban.db").is_file():
            return h.parent
    except Exception:
        pass
    return h


def _kanban_db() -> Path:
    return _real_hermes_home() / "kanban.db"


def _boards_dir() -> Path:
    return _real_hermes_home() / "kanban" / "boards"


def _shared_db_path() -> str:
    """Path to the shared multi-agent SQLite DB (from multi-agent-context)."""
    return os.environ.get(
        "MULTI_AGENT_TG_DB_PATH",
        str(_hermes_home() / "data" / "multi_agent_tg_shared.db"),
    ).strip()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _event_limit() -> int:
    try:
        return int(os.environ.get("KANBAN_CONTEXT_EVENT_LIMIT", "10"))
    except (ValueError, TypeError):
        return 10


@functools.lru_cache(maxsize=1)
def _lookback_hours() -> int:
    try:
        return int(os.environ.get("KANBAN_CONTEXT_LOOKBACK_H", "12"))
    except (ValueError, TypeError):
        return 12


def _my_bot_name() -> str:
    """Return this bot's display name for outbox addressing."""
    name = os.environ.get("CROSSBOT_BOT_NAME", "").strip()
    if name:
        return name
    try:
        from hermes_cli.profiles import get_active_profile_name
        profile = get_active_profile_name()
        if profile and profile != "default":
            return profile
    except Exception:
        pass
    return os.environ.get("MULTI_AGENT_BOT_NAME", "bot")


def _clear_config_cache() -> None:
    _event_limit.cache_clear()
    _lookback_hours.cache_clear()


# ---------------------------------------------------------------------------
# Shared outbox DB — cross-bot message bus
# ---------------------------------------------------------------------------

_OUTBOX_TABLE = """\
    CREATE TABLE IF NOT EXISTS outbox (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ts              REAL    NOT NULL,
        from_bot        TEXT    NOT NULL,
        to_bot          TEXT    NOT NULL,
        subject         TEXT    DEFAULT '',
        body            TEXT    NOT NULL,
        kanban_task_id  TEXT    DEFAULT '',
        status          TEXT    DEFAULT 'pending',  -- pending | delivered | done
        response_text   TEXT    DEFAULT '',
        completed_at    REAL    DEFAULT NULL,
        telegram_msg_id INTEGER DEFAULT NULL
    )
"""

_RESPONSE_LOG_TABLE = """\
    CREATE TABLE IF NOT EXISTS response_log (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ts            REAL    NOT NULL,
        bot_name      TEXT    NOT NULL,
        chat_key      TEXT    NOT NULL,
        user_message  TEXT    NOT NULL,
        user_id       TEXT    DEFAULT '',
        responded     INTEGER DEFAULT 0,  -- 0=pending, 1=responded
        responder     TEXT    DEFAULT ''
    )
"""
_CREATE_INDEX_RL = """\
    CREATE INDEX IF NOT EXISTS idx_rl_chat_msg 
    ON response_log (chat_key, user_message)
"""


def _open_shared_db():
    """Open the shared multi-agent DB, ensuring outbox + response_log tables exist."""
    path = _shared_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(_OUTBOX_TABLE)
    conn.execute(_RESPONSE_LOG_TABLE)
    conn.execute(_CREATE_INDEX_RL)
    # Migration: add telegram_msg_id column if missing
    try:
        conn.execute("ALTER TABLE outbox ADD COLUMN telegram_msg_id INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Auto-detect @mentions and create kanban tasks
# ---------------------------------------------------------------------------

def _detect_mentions(text: str) -> List[str]:
    """Parse text for @mentions of known bots and return their profile names.

    Looks for @handles defined in topic-map.json and returns the
    corresponding bot profile names.
    """
    if not text:
        return []

    path = _get_topic_map_path()
    try:
        if not path.is_file():
            return []
        with open(path, "r") as f:
            data = json.load(f)
        handles = data.get("handles", {})
    except Exception:
        return []

    mentioned = []
    text_lower = text.lower()
    for bot_name, handle in handles.items():
        if f"@{handle.lower()}" in text_lower:
            mentioned.append(bot_name)
    return mentioned


def _auto_create_task_from_mention(
    from_bot: str,
    to_bot: str,
    message_text: str,
    telegram_msg_id: Optional[int] = None,
) -> Optional[str]:
    """Auto-create a kanban task when a @mention is detected.

    Called from the pre_llm_call hook when a message mentions another bot.
    Creates a kanban task assigned to the mentioned bot so the dispatcher
    picks it up and spawns a worker.

    Returns the kanban task ID if created, None otherwise.
    """
    # First, create an outbox entry so crossbot_respond() has an ID to use
    conn = _open_shared_db()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO outbox (id, ts, from_bot, to_bot, subject, body, kanban_task_id, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
                (None, time.time(), from_bot, to_bot, f"[Mention] @{from_bot}", message_text, None),
            )
            outbox_id = cur.lastrowid
    finally:
        conn.close()

    try:
        _kc_paths_to_try = [
            str(Path(__file__).parent.parent.parent / "hermes-agent"),
            str(Path.home() / ".hermes" / "hermes-agent"),
        ]
        for _kp in _kc_paths_to_try:
            if _kp not in sys.path:
                sys.path.insert(0, _kp)

        from hermes_cli.kanban_db import (
            create_task as _hermes_create_task,
            board_exists as _board_exists,
            create_board as _create_board,
            kanban_db_path as _kanban_db_path,
        )

        _kc_board = "linkedin-content"
        if not _board_exists(_kc_board):
            try:
                _create_board(_kc_board, display_name="Cross-Bot Messages")
            except Exception:
                pass

        # Build task body with outbox_id and instruction to respond
        _kc_body = (
            f"[AUTO-MENTION from @{from_bot}]\n"
            f"Outbox ID: {outbox_id}\n\n"
            f"{message_text}\n\n"
            f"---\n"
            f"INSTRUCTION TO WORKER:\n"
            f"1. Set CROSSBOT_BOT_NAME={to_bot} in os.environ\n"
            f"2. Process the message above\n"
            f"3. Reply by calling crossbot_respond({outbox_id}, \"your response\")\n"
            f"4. The response will appear in the Telegram group automatically\n"
            f"5. Do NOT message Franklin in DM unless explicitly asked"
        )

        _kc_db_path = _kanban_db_path(_kc_board)
        _kc_conn = sqlite3.connect(str(_kc_db_path), timeout=5)
        try:
            _task_id = _hermes_create_task(
                _kc_conn,
                title=f"[Mention] @{from_bot} → @{to_bot}",
                body=_kc_body,
                assignee=to_bot,
                created_by=from_bot,
                initial_status="running",
            )

            # Update outbox with kanban_task_id
            conn2 = _open_shared_db()
            try:
                conn2.execute(
                    "UPDATE outbox SET kanban_task_id=? WHERE id=?",
                    (_task_id, outbox_id),
                )
                conn2.commit()
            finally:
                conn2.close()

            logger.info(
                "kanban-context: auto-created task %s for @%s (mentioned by @%s, outbox #%d)",
                _task_id, to_bot, from_bot, outbox_id,
            )
            return _task_id
        finally:
            _kc_conn.close()
    except Exception as exc:
        logger.warning("kanban-context: failed to auto-create task: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Cross-bot visibility — post messages to Telegram group for human oversight
# ---------------------------------------------------------------------------

_VISIBILITY_CONFIG_FILENAME = "visibility-config.json"
_TOPIC_MAP_FILENAME = "topic-map.json"


def _get_topic_map_path() -> Path:
    """Return the path to the topic map config file."""
    return Path(__file__).parent / _TOPIC_MAP_FILENAME


def _get_topic_for_bot(bot_name: str) -> Optional[int]:
    """Return the Telegram topic/thread ID for a given bot name.

    Reads from topic-map.json. Returns None if not found.
    """
    path = _get_topic_map_path()
    try:
        if path.is_file():
            with open(path, "r") as f:
                data = json.load(f)
            topics = data.get("topics", {})
            tid = topics.get(bot_name.lower(), None)
            if tid is not None:
                return int(tid)
    except Exception as exc:
        logger.debug("topic-map: failed to read %s: %s", path, exc)
    return None


def _get_bot_handle(bot_name: str) -> str:
    """Return the Telegram handle for a given bot name.

    Reads from topic-map.json. Returns the bot_name as fallback.
    """
    path = _get_topic_map_path()
    try:
        if path.is_file():
            with open(path, "r") as f:
                data = json.load(f)
            handles = data.get("handles", {})
            return handles.get(bot_name.lower(), bot_name)
    except Exception:
        pass
    return bot_name


def _get_visibility_config_path() -> Path:
    """Return the path to the plugin's visibility config file."""
    return Path(__file__).parent / _VISIBILITY_CONFIG_FILENAME


def _read_visibility_config() -> dict:
    """Read the visibility config JSON file.

    Returns a dict with keys: telegram_bot_token, visibility_chat_id, enabled.
    If file doesn't exist or is corrupt, returns empty dict.
    """
    path = _get_visibility_config_path()
    try:
        if path.is_file():
            with open(path, "r") as f:
                return json.load(f)
    except Exception as exc:
        logger.debug("visibility-config: failed to read %s: %s", path, exc)
    return {}


def _write_visibility_config(data: dict) -> bool:
    """Write the visibility config JSON file.

    Args:
        data: dict with keys like telegram_bot_token, visibility_chat_id, enabled

    Returns True on success.
    """
    path = _get_visibility_config_path()
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("visibility-config: saved to %s", path)
        return True
    except Exception as exc:
        logger.warning("visibility-config: failed to write %s: %s", path, exc)
        return False


def _setup_visibility_config() -> bool:
    """Initialize visibility-config.json from current env vars if it doesn't exist.

    This ensures the plugin has a self-contained config that works regardless
    of which profile's env vars are loaded at call time.

    Returns True if config was created or already exists.
    """
    path = _get_visibility_config_path()
    if path.is_file():
        return True

    # Try to populate from environment
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("CROSSBOT_VISIBILITY_CHAT", "").strip()

    if token and chat:
        data = {
            "telegram_bot_token": token,
            "visibility_chat_id": chat,
            "enabled": True,
        }
        if _write_visibility_config(data):
            logger.info(
                "visibility-config: created from env vars (chat=%s, token_len=%d)",
                chat, len(token),
            )
            return True

    # No env vars — create a placeholder so the next call with env vars will work
    data = {"telegram_bot_token": "", "visibility_chat_id": "", "enabled": False}
    _write_visibility_config(data)
    return False


def _get_visibility_chat() -> Optional[str]:
    """Return the Telegram chat ID where cross-bot messages should be visible.

    Resolution order:
    1. visibility-config.json (plugin config file — works in any context)
    2. CROSSBOT_VISIBILITY_CHAT env var (profile-specific fallback)
    3. None (invisible)

    If the config file has an empty chat_id but env var has it, the config
    file is auto-updated so the next call works without env vars.
    """
    cfg = _read_visibility_config()
    chat = cfg.get("visibility_chat_id", "").strip()
    if chat:
        return chat
    # Fallback to env var
    chat = os.environ.get("CROSSBOT_VISIBILITY_CHAT", "").strip()
    if chat:
        # Auto-populate config file for future calls
        cfg["visibility_chat_id"] = chat
        _write_visibility_config(cfg)
        return chat
    return None


def _get_visibility_thread() -> Optional[str]:
    """Return the Telegram topic/message thread ID for visibility messages.

    Resolution order:
    1. visibility-config.json (plugin config file)
    2. CROSSBOT_VISIBILITY_THREAD env var (profile-specific fallback)
    3. None (main chat, no topic)

    If the config file has an empty thread_id but env var has it, the config
    file is auto-updated.
    """
    cfg = _read_visibility_config()
    thread = cfg.get("visibility_thread_id", "").strip()
    if thread:
        return thread
    # Fallback to env var
    thread = os.environ.get("CROSSBOT_VISIBILITY_THREAD", "").strip()
    if thread:
        cfg["visibility_thread_id"] = thread
        _write_visibility_config(cfg)
        return thread
    return None


def _crossbot_audit_log(event: str, **fields: Any) -> None:
    """Structured JSONL log for remote debugging. See docs/CROSSBOT-DEBUG.md."""
    try:
        log_path = os.environ.get(
            "CROSSBOT_AUDIT_LOG",
            str(_real_hermes_home() / "logs" / "kanban-context" / "crossbot-audit.jsonl"),
        ).strip()
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        entry: Dict[str, Any] = {"ts": time.time(), "event": event, "bot": _my_bot_name()}
        for key, val in fields.items():
            if key == "token" and val:
                entry["token_prefix"] = str(val)[:12] + "..."
            else:
                entry[key] = val
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("crossbot-audit: write failed: %s", exc)


def _get_visibility_token() -> Optional[str]:
    """Token for visibility posts — always the dedicated visibility bot, not the worker profile."""
    cfg = _read_visibility_config()
    token = cfg.get("telegram_bot_token", "").strip()
    if token:
        return token
    token = os.environ.get("CROSSBOT_VISIBILITY_TOKEN", "").strip()
    if token:
        return token
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None


def _get_telegram_token() -> Optional[str]:
    """Return the Telegram Bot API token for posting visibility messages.

    Resolution order:
    When CROSSBOT_BOT_NAME is set (kanban worker), ALWAYS loads from the
    profile .env first — the inherited env var belongs to the parent process
    and may have a different bot's token.
    """
    bot_name = _my_bot_name()

    # If we know which bot we are, ALWAYS load from profile .env first
    # (the inherited TELEGRAM_BOT_TOKEN may be from the parent process)
    if bot_name and bot_name != "bot":
        profile_env = _real_hermes_home() / "profiles" / bot_name / ".env"
        if profile_env.is_file():
            try:
                with open(profile_env, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass

    # Fallback: env var (for scripts outside profiles)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        return token

    # Last resort: config file
    cfg = _read_visibility_config()
    token = cfg.get("telegram_bot_token", "").strip()
    if token:
        return token
    return None


def _post_visibility_message(text: str, direction: str = "sent", thread_id: Optional[str] = None, reply_to: Optional[int] = None, outbox_id: Optional[int] = None) -> Optional[int]:
    """Post a cross-bot message to the Telegram group for human visibility.

    Uses _get_visibility_token() (not worker profile token). Retries without
    reply_to when Telegram returns 400 (bots cannot reply to other bots' msgs).
    """
    import urllib.error
    import urllib.request

    chat_id = _get_visibility_chat()
    token = _get_visibility_token()
    if not chat_id or not token:
        _crossbot_audit_log("visibility_skip", outbox_id=outbox_id, direction=direction, reason="no chat/token")
        return None

    msg_thread = thread_id or _get_visibility_thread()
    try:
        msg_thread_int = int(msg_thread) if msg_thread else None
    except (ValueError, TypeError):
        msg_thread_int = None

    try:
        reply_to_int = int(reply_to) if reply_to else None
    except (ValueError, TypeError):
        reply_to_int = None

    prefix = "📤" if direction == "sent" else "📥"
    full_text = f"{prefix} **Cross-Bot**\n\n{text}"

    attempts: List[Optional[int]] = []
    if reply_to_int is not None:
        attempts.append(reply_to_int)
    attempts.append(None)

    for reply_to_try in attempts:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": full_text,
            "parse_mode": "Markdown",
        }
        if msg_thread_int is not None:
            payload["message_thread_id"] = msg_thread_int
        if reply_to_try is not None:
            payload["reply_to_message_id"] = reply_to_try

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                msg_id = result.get("result", {}).get("message_id")
                _crossbot_audit_log(
                    "visibility_post", outbox_id=outbox_id, direction=direction, token=token,
                    chat_id=chat_id, thread_id=msg_thread_int, reply_to=reply_to_try,
                    ok=True, telegram_msg_id=msg_id,
                    attempt="with_reply" if reply_to_try else "no_reply",
                )
                logger.info(
                    "crossbot-visibility: posted outbox=%s dir=%s msg_id=%s reply_to=%s",
                    outbox_id, direction, msg_id, reply_to_try,
                )
                return msg_id
            err = str(result.get("description", "unknown"))
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode("utf-8")).get("description", str(exc))
            except Exception:
                err = str(exc)
        except Exception as exc:
            err = str(exc)

        _crossbot_audit_log(
            "visibility_post", outbox_id=outbox_id, direction=direction, token=token,
            chat_id=chat_id, thread_id=msg_thread_int, reply_to=reply_to_try,
            ok=False, error=err, attempt="with_reply" if reply_to_try else "no_reply",
        )
        if reply_to_try is None:
            logger.warning("crossbot-visibility: failed outbox=%s err=%s", outbox_id, err)
            return None
        if "reply" in err.lower() or "not found" in err.lower():
            logger.info("crossbot-visibility: reply_to=%s rejected (%s), retry without reply", reply_to_try, err)
            continue
        logger.warning("crossbot-visibility: failed outbox=%s err=%s", outbox_id, err)
        return None
    return None


def crossbot_send(
    to_bot: str,
    subject: str,
    body: str,
    kanban_task_id: str = "",
    kanban_db_path: str = "",
) -> int:
    """Send a cross-bot message via the shared outbox.

    If no kanban_task_id is provided, this function automatically creates
    a Kanban task assigned to the target bot. This triggers the Kanban
    dispatcher (~60s) to spawn a worker for the target bot, which reads
    the pending outbox via the pre_llm_call hook.

    Args:
        to_bot: Target bot profile name (e.g. 'profile_name')
        subject: Short message subject/headline
        body: Full message body
        kanban_task_id: Optional Kanban task ID for tracking.
                        If empty, one is auto-created.
        kanban_db_path: Optional explicit kanban.db path.
                        If empty, uses default path.

    Returns:
        The outbox row ID.
    """
    import uuid as _uuid
    import sqlite3 as _sqlite3
    import json as _json

    conn = _open_shared_db()
    now = time.time()
    from_bot = _my_bot_name()

    # INSERT outbox FIRST so we know the row_id for the kanban task body
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO outbox (id, ts, from_bot, to_bot, subject, body, kanban_task_id, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
                (None, now, from_bot, to_bot, subject[:200], body, None),
            )
            row_id = cur.lastrowid
    finally:
        conn.close()

    # Auto-create kanban task if not provided
    if not kanban_task_id:
        try:
            # Use Hermes kanban API to create the task
            _kc_paths_to_try = [
                str(Path(__file__).parent.parent.parent / "hermes-agent"),
                str(Path.home() / ".hermes" / "hermes-agent"),
            ]
            for _kp in _kc_paths_to_try:
                if _kp not in sys.path:
                    sys.path.insert(0, _kp)

            from hermes_cli.kanban_db import (
                create_task as _hermes_create_task,
                board_exists as _board_exists,
                create_board as _create_board,
                kanban_db_path as _kanban_db_path,
            )

            _kc_board = "linkedin-content"

            if not _board_exists(_kc_board):
                try:
                    _create_board(_kc_board, display_name="Cross-Bot Messages")
                except Exception:
                    pass

            # Build kanban task body with OUTBOX_ID + instruction
            _kc_body = (
                f"[CROSS-BOT MESSAGE #{row_id}]\n"
                f"From: {from_bot}\n"
                f"To: {to_bot}\n"
                f"Subject: {subject}\n\n"
                f"{body}\n\n"
                f"---\n"
                f"INSTRUCTION TO WORKER:\n"
                f"1. Process the message content above\n"
                f"2. Set CROSSBOT_BOT_NAME={to_bot} in os.environ before calling crossbot_respond\n"
                f"3. Reply by calling crossbot_respond({row_id}, \"your response\")\n"
                f"4. Do NOT message Franklin in DM unless explicitly asked\n"
                f"5. The crossbot_respond function is in the kanban_context plugin"
            )

            _kc_db_path = _kanban_db_path(_kc_board)
            _kc_conn = _sqlite3.connect(str(_kc_db_path), timeout=5)
            try:
                _task_id = _hermes_create_task(
                    _kc_conn,
                    title=f"[Cross-Bot] {subject[:150]}",
                    body=_kc_body,
                    assignee=to_bot,
                    created_by=from_bot,
                    initial_status="running",
                )
                kanban_task_id = _task_id
                logger.info(
                    "crossbot: created kanban task %s for '%s' in board '%s' "
                    "(outbox #%d)",
                    _task_id, to_bot, _kc_board, row_id,
                )
            finally:
                _kc_conn.close()
        except Exception as exc:
            logger.warning(
                "crossbot: failed to auto-create kanban task via Hermes API: %s",
                exc,
            )

    # Update outbox row with kanban_task_id
    conn2 = _open_shared_db()
    try:
        conn2.execute(
            "UPDATE outbox SET kanban_task_id=? WHERE id=?",
            (kanban_task_id or "", row_id),
        )
        conn2.commit()
    finally:
        conn2.close()

    logger.info(
        "crossbot: sent message #%d from '%s' to '%s' (subject='%s', kanban=%s)",
        row_id, from_bot, to_bot, subject[:60], kanban_task_id or "none",
    )

    # Post visibility message to Telegram group — in the destination bot's topic
    topic_id = _get_topic_for_bot(to_bot)
    vis_text = (
        f"**From:** {from_bot}\n"
        f"**To:** {to_bot}\n"
        f"**Subject:** {subject}\n\n"
        f"{body}\n\n"
        f"└─ *ID:* #{row_id}"
    )
    tg_msg_id = _post_visibility_message(
        vis_text, "sent",
        thread_id=str(topic_id) if topic_id else None,
        outbox_id=row_id,
    )

    # Save telegram_msg_id to outbox for reply threading
    if tg_msg_id:
        conn3 = _open_shared_db()
        try:
            conn3.execute("UPDATE outbox SET telegram_msg_id=? WHERE id=?", (tg_msg_id, row_id))
            conn3.commit()
        finally:
            conn3.close()

    return row_id


def crossbot_respond(outbox_id: int, response_text: str) -> bool:
    """Mark a message as done with the response text.

    Args:
        outbox_id: The outbox row ID from crossbot_send()
        response_text: The response/reply content

    Returns:
        True if successful, False if message not found.
    """
    conn = _open_shared_db()
    now = time.time()
    try:
        # Get original message details for visibility + telegram_msg_id for reply
        orig = conn.execute(
            "SELECT from_bot, to_bot, subject, telegram_msg_id FROM outbox WHERE id=?",
            (outbox_id,),
        ).fetchone()

        cur = conn.execute(
            "UPDATE outbox SET status='done', response_text=?, completed_at=? WHERE id=?",
            (response_text[:2000], now, outbox_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            logger.warning("crossbot: message #%d not found", outbox_id)
            return False

        logger.info("crossbot: message #%d responded (%d chars)", outbox_id, len(response_text))
        _crossbot_audit_log(
            "crossbot_respond",
            outbox_id=outbox_id,
            response_len=len(response_text),
            from_bot=orig[0] if orig else None,
            to_bot=orig[1] if orig else None,
        )

        # Post visibility message to Telegram group — reply to original message
        if orig:
            topic_id = _get_topic_for_bot(orig[1])  # orig[1] is to_bot
            reply_to = orig[3]  # orig[3] is telegram_msg_id
            vis_text = (
                f"**From:** {orig[1]}\n"
                f"**To:** {orig[0]}\n"
                f"**Subject:** {orig[2]}\n"
                f"**Response:**\n{response_text}\n\n"
                f"└─ *ID:* #{outbox_id}"
            )
            _post_visibility_message(
                vis_text, "responded",
                thread_id=str(topic_id) if topic_id else None,
                reply_to=reply_to,
                outbox_id=outbox_id,
            )

        return True
    finally:
        conn.close()


def _crossbot_send_tool(args: dict, **kwargs) -> str:
    """Hermes tool — send a cross-bot message."""
    to_bot = (args.get("to_bot") or "").strip()
    subject = (args.get("subject") or "").strip()
    body = (args.get("body") or "").strip()
    if not to_bot or not body:
        return json.dumps({"error": "to_bot and body are required"})
    outbox_id = crossbot_send(
        to_bot=to_bot,
        subject=subject or "(no subject)",
        body=body,
        kanban_task_id=(args.get("kanban_task_id") or "").strip(),
    )
    return json.dumps({
        "outbox_id": outbox_id,
        "to_bot": to_bot,
        "message": f"Cross-bot message #{outbox_id} queued for '{to_bot}'.",
    })


def _crossbot_respond_tool(args: dict, **kwargs) -> str:
    """Hermes tool — respond to a pending cross-bot message."""
    try:
        outbox_id = int(args.get("outbox_id"))
    except (TypeError, ValueError):
        return json.dumps({"error": "outbox_id must be an integer"})
    response_text = (args.get("response_text") or "").strip()
    if not response_text:
        return json.dumps({"error": "response_text is required"})
    ok = crossbot_respond(outbox_id, response_text)
    if not ok:
        return json.dumps({"error": f"outbox message #{outbox_id} not found", "ok": False})
    return json.dumps({
        "ok": True,
        "outbox_id": outbox_id,
        "message": f"Response recorded for cross-bot message #{outbox_id}.",
    })


def _fetch_pending_messages(for_bot: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all pending (undelivered) messages for *for_bot*.

    If *for_bot* is None, uses the current bot name.
    """
    target = for_bot or _my_bot_name()
    conn = _open_shared_db()
    try:
        rows = conn.execute(
            "SELECT id, from_bot, subject, body, ts, kanban_task_id "
            "FROM outbox "
            "WHERE to_bot=? AND status='pending' "
            "ORDER BY ts ASC",
            (target,),
        ).fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "from_bot": r[1],
                "subject": r[2] or "",
                "body": r[3],
                "ts": r[4],
                "kanban_task_id": r[5] or "",
            })
        return results
    finally:
        conn.close()


def crossbot_get_history(
    for_bot: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Get recent cross-bot message history for the given bot."""
    target = for_bot or _my_bot_name()
    conn = _open_shared_db()
    try:
        rows = conn.execute(
            "SELECT id, from_bot, to_bot, subject, body, status, response_text, ts, completed_at "
            "FROM outbox "
            "WHERE from_bot=? OR to_bot=? "
            "ORDER BY ts DESC LIMIT ?",
            (target, target, limit),
        ).fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "from_bot": r[1],
                "to_bot": r[2],
                "subject": r[3] or "",
                "body": r[4],
                "status": r[5],
                "response_text": r[6] or "",
                "ts": r[7],
                "completed_at": r[8],
            })
        return results
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Kanban board reading
# ---------------------------------------------------------------------------


def _iter_boards() -> List[Tuple[str, str]]:
    """Yield (db_path, board_label) pairs for all available kanban boards."""
    results: List[Tuple[str, str]] = []
    default = _kanban_db()
    if default.is_file():
        results.append((str(default), "kanban"))
    boards = _boards_dir()
    if boards.is_dir():
        for name in sorted(os.listdir(str(boards))):
            board_db = boards / name / "kanban.db"
            if board_db.is_file():
                results.append((str(board_db), name))
    return results


def _read_kanban_events() -> str:
    """Read recent task_events from all kanban boards and format as context."""
    cutoff = time.time() - _lookback_hours() * 3600
    limit = _event_limit()
    events: List[Dict[str, Any]] = []

    for db_path, board_label in _iter_boards():
        try:
            with sqlite3.connect(db_path, timeout=5) as conn:
                rows = conn.execute(
                    """
                    SELECT e.id, e.task_id, e.kind, e.payload, e.created_at,
                           t.title, t.status
                    FROM task_events e
                    LEFT JOIN tasks t ON t.id = e.task_id
                    WHERE e.created_at >= ?
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """,
                    (cutoff, limit),
                ).fetchall()
            for row in rows:
                _eid, task_id, kind, payload_json, created_at, title, task_status = row
                payload: Dict[str, Any] = {}
                if payload_json:
                    try:
                        payload = json.loads(payload_json)
                    except (json.JSONDecodeError, TypeError):
                        payload = {}
                events.append({
                    "board": board_label,
                    "task_id": task_id,
                    "kind": kind,
                    "payload": payload,
                    "ts": created_at,
                    "title": title or task_id[:16],
                    "task_status": task_status,
                })
        except Exception as exc:
            logger.warning(
                "kanban-context: error reading board '%s' (%s): %s",
                board_label, db_path, exc,
            )

    if not events:
        logger.debug(
            "kanban-context: no recent events (lookback=%dh, boards=%d)",
            _lookback_hours(), len(_iter_boards()),
        )
        return ""

    events.sort(key=lambda e: e["ts"], reverse=True)
    events = events[:limit]
    events.reverse()

    lines = ["[Recent Kanban Activity]", ""]
    for ev in events:
        when = _fmt_time(ev["ts"])
        title = ev["title"][:60]
        kind = ev["kind"]
        board = ev["board"]
        task_status = ev["task_status"] or "?"
        desc = _describe_event(kind, ev["payload"], task_status)
        lines.append(f"- [{when}] [{board}] **{title}** ({desc})")
    lines.extend(["", "[End Kanban Activity]"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pending cross-bot messages
# ---------------------------------------------------------------------------


def _read_pending_messages() -> str:
    """Read pending outbox messages for this bot and format as context."""
    pending = _fetch_pending_messages()
    if not pending:
        return ""

    lines = ["[Pending Messages]", ""]
    for msg in pending:
        when = _fmt_time(msg["ts"])
        subj = msg["subject"] or "(no subject)"
        body = msg["body"][:200]
        if len(msg["body"]) > 200:
            body += "..."
        task_ref = f" (kanban: {msg['kanban_task_id']})" if msg["kanban_task_id"] else ""
        lines.append(f"- ID #{msg['id']} [{when}] From **{msg['from_bot']}** — {subj}{task_ref}")
        lines.append(f"  > {body}")
    lines.extend([
        "",
        "⚠️ MANDATORY — call crossbot_respond BEFORE kanban_complete:",
    ])
    for msg in pending:
        lines.append(f"  crossbot_respond(outbox_id={msg['id']}, response_text=\"<reply>\")")
    lines.extend([
        "",
        "Do NOT finish with only kanban_comment or kanban_complete.",
        "",
    ])
    lines.append("[End Pending Messages]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_time(ts: float) -> str:
    elapsed = time.time() - ts
    if elapsed < 0:
        return "just now"
    if elapsed < 60:
        return "just now"
    if elapsed < 3600:
        return f"{int(elapsed // 60)}m ago"
    if elapsed < 86400:
        return f"{int(elapsed // 3600)}h ago"
    return f"{int(elapsed // 86400)}d ago"


def _describe_event(kind: str, payload: Dict[str, Any], task_status: str) -> str:
    descriptions = {
        "created": f"created → {payload.get('status', 'triage')}",
        "assigned": f"assigned to {payload.get('assignee', 'someone')}",
        "claimed": "claimed by worker",
        "completed": "completed",
        "blocked": _trunc(f"blocked: {payload.get('reason', '')}", 60),
        "unblocked": "unblocked",
        "heartbeat": _trunc(f"in progress: {payload.get('note', '')}", 60),
        "spawned": "worker spawned",
        "archived": "archived",
        "commented": f"comment by {payload.get('author', 'someone')}",
        "linked": _trunc(
            f"linked to parent={payload.get('parent', '')[:12]} "
            f"child={payload.get('child', '')[:12]}",
            60,
        ),
        "edited": "edited",
        "promoted": f"promoted → {task_status}",
    }
    return descriptions.get(kind, kind)


def _trunc(text: str, max_len: int) -> str:
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


# ---------------------------------------------------------------------------
# Auto-cleaning — lightweight self-maintenance
# ---------------------------------------------------------------------------

_CLEANUP_INTERVAL: float = 86400.0
_last_cleanup: float = 0.0


def _get_cleanup_interval() -> int:
    try:
        return max(3600, int(os.environ.get("KANBAN_CONTEXT_CLEANUP_INTERVAL", "86400")))
    except (ValueError, TypeError):
        return 86400


def _get_outbox_retention_days() -> int:
    try:
        return max(1, int(os.environ.get("KANBAN_CONTEXT_OUTBOX_RETENTION", "14")))
    except (ValueError, TypeError):
        return 14


def _get_log_retention_days() -> int:
    try:
        return max(1, int(os.environ.get("KANBAN_CONTEXT_LOG_RETENTION", "7")))
    except (ValueError, TypeError):
        return 7


def _cleanup_old_outbox() -> int:
    """Delete completed outbox messages older than retention."""
    retention = _get_outbox_retention_days()
    cutoff = time.time() - retention * 86400
    conn = _open_shared_db()
    try:
        cur = conn.execute(
            "DELETE FROM outbox WHERE status='done' AND completed_at IS NOT NULL AND completed_at < ?",
            (cutoff,),
        )
        conn.commit()
        deleted = cur.rowcount

        # Also clean old response_log entries
        cur2 = conn.execute(
            "DELETE FROM response_log WHERE ts < ?",
            (cutoff,),
        )
        conn.commit()
        rl_deleted = cur2.rowcount

        if deleted > 0 or rl_deleted > 0:
            logger.info(
                "kanban-context: cleaned %d outbox + %d response_log (retention=%dd)",
                deleted, rl_deleted, retention,
            )
        return deleted
    except Exception as exc:
        logger.warning("kanban-context: outbox cleanup failed: %s", exc)
        return 0
    finally:
        conn.close()


def _cleanup_stale_pending() -> int:
    """Mark pending messages >7d as stale (target bot likely inactive)."""
    cutoff = time.time() - 7 * 86400
    conn = _open_shared_db()
    try:
        cur = conn.execute(
            "UPDATE outbox SET status='done', response_text='[stale - abandoned]' "
            "WHERE status='pending' AND ts < ?",
            (cutoff,),
        )
        conn.commit()
        stale = cur.rowcount
        if stale > 0:
            logger.info("kanban-context: marked %d stale pending as abandoned", stale)
        return stale
    except Exception as exc:
        logger.warning("kanban-context: stale cleanup failed: %s", exc)
        return 0
    finally:
        conn.close()


def _cleanup_old_log_files() -> int:
    """Remove kanban-context log files older than retention."""
    retention = _get_log_retention_days()
    log_dir = _hermes_home() / "logs" / "kanban-context"
    if not log_dir.is_dir():
        return 0
    cutoff = time.time() - retention * 86400
    removed = 0
    try:
        for f in log_dir.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        if removed > 0:
            logger.info("kanban-context: cleaned %d old log files (retention=%dd)", removed, retention)
        return removed
    except Exception as exc:
        logger.warning("kanban-context: log cleanup failed: %s", exc)
        return 0


def run_maintenance(force: bool = False) -> None:
    """Run periodic maintenance — outbox prune, stale mark, log rotate.

    Runs at most once per CLEANUP_INTERVAL unless *force* is True.
    """
    global _last_cleanup
    now = time.time()
    interval = _get_cleanup_interval()
    if not force and (now - _last_cleanup) < interval:
        return
    _cleanup_old_outbox()
    _cleanup_stale_pending()
    _cleanup_old_log_files()
    _last_cleanup = now


# ---------------------------------------------------------------------------
# Response coordination — prevents duplicate replies in shared groups
#
# RULES:
#   1. Bot that is @mentioned MUST respond (even if others already did)
#   2. If multiple bots are @mentioned, ALL respond
#   3. If user replied to a bot's message (reply-to threading), that bot responds
#   4. If no mention/reply, the designated bot for that chat_key responds
#   5. If not mentioned, not replied-to, not assigned -> stays silent
# ---------------------------------------------------------------------------

_RESPONSE_COOLDOWN: float = 30.0  # seconds

_TOPIC_MAP: Optional[Dict[str, str]] = None  # cache for topic map


def _get_bot_mention_names() -> List[str]:
    """Return a list of identifiers this bot can be @mentioned by.

    Includes:
    - The explicit CROSSBOT_BOT_NAME (e.g. 'Matias')
    - The profile name (e.g. 'ti')
    - Any names listed in KANBAN_CONTEXT_MENTION_MAP for this bot
    """
    bot = _my_bot_name()
    names = [bot]

    # Also add the lowercased version for case-insensitive matching
    names.append(bot.lower())

    # Check mention map for @username aliases
    raw = os.environ.get("KANBAN_CONTEXT_MENTION_MAP", "").strip()
    if raw:
        for pair in raw.split(","):
            pair = pair.strip()
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            key = key.strip()
            if key == bot or key == bot.lower():
                if value.startswith("@"):
                    names.append(value)
                    names.append(value.lower())
                names.append(value)

    return names


def _get_bot_owned_chats() -> List[str]:
    """Return list of chat_keys assigned to this bot.

    Reads from KANBAN_CONTEXT_TOPIC_MAP env var.
    Format: chat_key=bot_name,chat_key=bot_name
    """
    global _TOPIC_MAP
    if _TOPIC_MAP is None:
        _TOPIC_MAP = {}
        raw = os.environ.get("KANBAN_CONTEXT_TOPIC_MAP", "").strip()
        if raw:
            for pair in raw.split(","):
                pair = pair.strip()
                if "=" not in pair:
                    continue
                chat_key, assigned = pair.split("=", 1)
                _TOPIC_MAP[chat_key.strip()] = assigned.strip()
    bot = _my_bot_name()
    return [ck for ck, ab in (_TOPIC_MAP or {}).items() if ab == bot]


def _is_bot_mentioned(user_message: str) -> bool:
    """Check if this bot is @mentioned in the user message.

    Uses word-boundary matching to avoid false positives
    (e.g. 'bravo' in '@matias_bravos_dev_bot').
    """
    if not user_message:
        return False
    msg_lower = user_message.lower()
    for name in _get_bot_mention_names():
        match = name.lower()
        # Exact mention (@username or name with word boundary)
        if match in msg_lower:
            idx = msg_lower.find(match)
            # Check char before and after for word boundary
            before = msg_lower[idx - 1] if idx > 0 else " "
            after = msg_lower[idx + len(match)] if idx + len(match) < len(msg_lower) else " "
            if (idx == 0 or before == "@" or not before.isalnum()) and \
               (idx + len(match) >= len(msg_lower) or not after.isalnum()):
                return True
    return False


def _mentioned_bots(user_message: str) -> List[str]:
    """Return list of ALL bots mentioned in the user message.

    Reads the full mention map to find which profiles are @mentioned.
    """
    mentioned: List[str] = []
    if not user_message:
        return mentioned

    msg_lower = user_message.lower()

    # Build reverse map: mention_string -> profile_name
    raw = os.environ.get("KANBAN_CONTEXT_MENTION_MAP", "").strip()
    reverse_map: Dict[str, str] = {}
    if raw:
        for pair in raw.split(","):
            pair = pair.strip()
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip().lower()
            reverse_map[value] = key
            if value.startswith("@"):
                reverse_map[value[1:]] = key  # also match without @

    # Check each known profile alias
    for mention, profile in reverse_map.items():
        if mention in msg_lower:
            mentioned.append(profile)

    return mentioned


def _is_designated_bot_for_chat(chat_key: str) -> bool:
    """Check if this bot is the designated responder for this chat_key."""
    global _TOPIC_MAP
    if _TOPIC_MAP is None:
        _get_bot_owned_chats()  # populates _TOPIC_MAP
    assigned = (_TOPIC_MAP or {}).get(chat_key)
    if not assigned:
        return False  # No explicit assignment — handled by fallback
    return assigned == _my_bot_name()


def _resolve_chat_key_from_kwargs(kwargs: dict) -> str:
    """Derive a chat_key from the hook kwargs."""
    session_id = kwargs.get("session_id", "") or ""

    parts = session_id.split(":")
    if len(parts) >= 5:
        chat_id = parts[4]
        if len(parts) > 5:
            return f"{chat_id}:{parts[5]}"
        return chat_id

    import hashlib
    return f"unknown_{hashlib.md5(session_id.encode()).hexdigest()[:12]}"


def _replied_to_bot(user_message: str) -> Optional[str]:
    """Check if the user_message is a reply to a bot's message.

    Hermes injects reply context as: [Replying to: "@bot_name text..."]
    Returns the bot name if the replied-to message was from a known bot,
    or None otherwise.
    """
    if not user_message or not user_message.startswith("[Replying to:"):
        return None

    # Build reverse map: @username -> profile_name
    raw = os.environ.get("KANBAN_CONTEXT_MENTION_MAP", "").strip()
    if not raw:
        return None

    username_to_profile: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        profile, username = pair.split("=", 1)
        username_to_profile[username.strip().lower().lstrip("@")] = profile.strip()

    # Extract the @username from: [Replying to: "@username rest..."]
    rest = user_message[len("[Replying to: "):]
    if rest.startswith('"'):
        rest = rest[1:]
    # Read until space, @, or "
    mentioned = ""
    for ch in rest:
        if ch in ('"', ' ', ']'):
            break
        mentioned += ch

    if not mentioned:
        return None

    mentioned_clean = mentioned.lower().lstrip("@")
    if mentioned_clean in username_to_profile:
        return username_to_profile[mentioned_clean]

    return None


def claim_response(user_message: str, chat_key: str) -> bool:
    """Decide whether THIS bot should respond based on coordination rules.

    Priority:
      1. If this bot is @mentioned → ALWAYS respond
      2. If other bots are @mentioned and this one ISN'T → skip
      3. If user replied to a bot's message → that bot responds
      4. If no mentions/reply → check designated topic assignment
      5. If designated → respond
      6. If not designated → skip (unless no assignment, then legacy: first-wins)

    Returns True if bot should respond, False if it should stay silent.
    """
    if not user_message or not chat_key:
        return True

    msg_trimmed = user_message[:200]
    bot = _my_bot_name()
    im_mentioned = _is_bot_mentioned(user_message)
    all_mentioned = _mentioned_bots(user_message)
    replied_to = _replied_to_bot(user_message)

    # RULE 1: I'm @mentioned → always respond
    if im_mentioned:
        logger.debug("kanban-context: claim=YES (mentioned) bot=%s", bot)
        _record_response_claim(bot, chat_key, msg_trimmed)
        return True

    # RULE 2: Other bots mentioned, I'm not → skip
    if all_mentioned:
        mentioned_str = ", ".join(all_mentioned)
        logger.info("kanban-context: claim=NO (others mentioned: %s) bot=%s", mentioned_str, bot)
        return False

    # RULE 3: User replied to a bot → that bot responds
    if replied_to:
        if replied_to == bot:
            logger.debug("kanban-context: claim=YES (replied-to) bot=%s", bot)
            _record_response_claim(bot, chat_key, msg_trimmed)
            return True
        else:
            logger.info("kanban-context: claim=NO (replied to %s) bot=%s", replied_to, bot)
            return False

    # RULE 3-5: No @mentions → check designation
    # First, check if someone already claimed this slot
    conn = _open_shared_db()
    now = time.time()
    cutoff = now - _RESPONSE_COOLDOWN
    try:
        existing = conn.execute(
            "SELECT responder FROM response_log "
            "WHERE chat_key=? AND user_message=? AND ts >= ? AND responded=1 "
            "ORDER BY ts DESC LIMIT 1",
            (chat_key, msg_trimmed, cutoff),
        ).fetchone()
    except Exception:
        existing = None
    finally:
        conn.close()

    if existing is not None:
        other = existing[0]
        # Check if other bot had explicit mention priority
        # Since we already ruled out mentions, first-claimer wins
        logger.info(
            "kanban-context: claim=NO (%s already claimed) bot=%s chat=%s",
            other, bot, chat_key,
        )
        return False

    # RULE 3: Check if this is my designated chat
    if _is_designated_bot_for_chat(chat_key):
        logger.debug(
            "kanban-context: claim=YES (designated) bot=%s chat=%s",
            bot, chat_key,
        )
        _record_response_claim(bot, chat_key, msg_trimmed)
        return True

    # RULE 5: Not my chat, no mentions → skip (strict)
    global _TOPIC_MAP
    if _TOPIC_MAP and chat_key in _TOPIC_MAP:
        # If chat IS mapped but not to me → skip
        logger.info(
            "kanban-context: claim=NO (not my topic) bot=%s chat=%s",
            bot, chat_key,
        )
        return False

    # No topic map at all → legacy fallback: first-wins (backward compat)
    logger.debug(
        "kanban-context: claim=YES (no topic map) bot=%s chat=%s",
        bot, chat_key,
    )
    _record_response_claim(bot, chat_key, msg_trimmed)
    return True


def _record_response_claim(bot: str, chat_key: str, msg_trimmed: str) -> None:
    """Record a response claim in the shared DB."""
    try:
        conn = _open_shared_db()
        conn.execute(
            "INSERT INTO response_log (ts, bot_name, chat_key, user_message, responded, responder) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (time.time(), bot, chat_key, msg_trimmed, bot),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("kanban-context: failed to record claim: %s", exc)


def _inject_response_coordination(**kwargs) -> Optional[Dict[str, str]]:
    """pre_llm_call hook — injects coordination context.

    Informs the agent if other bots have already responded, or if
    this bot should be the primary responder.
    """
    user_message = kwargs.get("user_message", "") or ""
    chat_key = _resolve_chat_key_from_kwargs(kwargs)

    if not user_message or not chat_key:
        return None

    lines = ["[Response Coordination]", ""]
    bot = _my_bot_name()

    # Check if this bot is @mentioned
    im_mentioned = _is_bot_mentioned(user_message)
    all_mentioned = _mentioned_bots(user_message)
    is_designated = _is_designated_bot_for_chat(chat_key)
    replied_to = _replied_to_bot(user_message)

    # Check other respondents
    conn = _open_shared_db()
    now = time.time()
    cutoff = now - _RESPONSE_COOLDOWN
    try:
        others = conn.execute(
            "SELECT responder, ts FROM response_log "
            "WHERE chat_key=? AND user_message=? AND ts >= ? AND responded=1 "
            "AND responder != ? "
            "ORDER BY ts DESC LIMIT 3",
            (user_message[:200], chat_key, cutoff, bot),
        ).fetchall()
    except Exception:
        others = []
    finally:
        conn.close()

    # Build context
    if im_mentioned:
        lines.append("**You were @mentioned** — you MUST respond to this message.")
    if all_mentioned:
        lines.append("Also mentioned: **" + ", ".join(all_mentioned) + "**")
    if replied_to:
        lines.append("User replied to **" + replied_to + "** — they should respond.")
    if is_designated:
        lines.append("This chat is assigned to **" + bot + "** — you are the primary responder.")
    if others:
        lines.append("")
        for responder, ts in others:
            lines.append(f"- **{responder}** responded {_fmt_time(ts)}")

    # Decision guidance
    lines.append("")
    if im_mentioned:
        lines.append("→ Respond. You were called out.")
    elif replied_to and replied_to == bot:
        lines.append("→ Respond. User replied to your message.")
    elif all_mentioned and not im_mentioned:
        lines.append("→ Skip. Others were @mentioned, not you.")
    elif is_designated:
        lines.append("→ Respond. You own this topic.")
    elif others:
        lines.append("→ Consider whether you need to add value before responding.")
    else:
        lines.append("→ Respond if you have useful input.")
    lines.append("")
    lines.append("[End Response Coordination]")

    ctx = "\n".join(lines)
    logger.debug(
        "kanban-context: coordination ctx injected bot=%s chat=%s "
        "mentioned=%s designated=%s",
        bot, chat_key, im_mentioned, is_designated,
    )
    return {"context": ctx}


# ---------------------------------------------------------------------------
# Hook callbacks
# ---------------------------------------------------------------------------


def _inject_kanban_context(**kwargs) -> Optional[Dict[str, str]]:
    """pre_llm_call hook — injects board activity + pending messages."""
    run_maintenance()
    parts = []

    # Part 1: Kanban board activity
    board_ctx = _read_kanban_events()
    if board_ctx:
        parts.append(board_ctx)

    # Part 2: Pending cross-bot messages
    pending_ctx = _read_pending_messages()
    if pending_ctx:
        parts.append(pending_ctx)

    if parts:
        combined = "\n\n".join(parts)
        logger.info(
            "kanban-context: injected %d chars (%d parts)",
            len(combined), len(parts),
        )
        return {"context": combined}
    return None


def _auto_detect_mentions(**kwargs) -> Optional[Dict[str, str]]:
    """pre_llm_call hook — detect @mentions of other bots and auto-create kanban tasks.

    When a user message mentions another bot (e.g., @bravos_consult_bot),
    this hook creates a kanban task for the mentioned bot so the dispatcher
    picks it up and spawns a worker.

    The worker then processes the task and responds directly in the group.
    """
    user_message = kwargs.get("user_message", "")
    if not user_message:
        return None

    # Detect @mentions in the user message
    mentioned_bots = _detect_mentions(user_message)
    if not mentioned_bots:
        return None

    # Get the current bot name (the one sending the message)
    from_bot = _my_bot_name()

    # Don't auto-create tasks for self-mentions
    mentioned_bots = [b for b in mentioned_bots if b != from_bot]
    if not mentioned_bots:
        return None

    # Create kanban tasks for each mentioned bot
    created_tasks = []
    for to_bot in mentioned_bots:
        task_id = _auto_create_task_from_mention(
            from_bot=from_bot,
            to_bot=to_bot,
            message_text=user_message,
        )
        if task_id:
            created_tasks.append((to_bot, task_id))

    if created_tasks:
        # Return context so the agent knows tasks were created
        lines = ["[Auto-Mention Tasks Created]"]
        for to_bot, task_id in created_tasks:
            lines.append(f"- @{to_bot}: task {task_id}")
        lines.append("")
        lines.append("The mentioned bots will process these tasks and respond in the group.")
        return {"context": "\n".join(lines)}

    return None


# ---------------------------------------------------------------------------
# Proactive validation — runs at plugin load (install-time check)
# ---------------------------------------------------------------------------


class ValidationResult:
    """Collects warnings and errors during plugin validation."""

    errors: List[str]
    warnings: List[str]

    def __init__(self) -> None:
        self.errors = []
        self.warnings = []

    def ok(self) -> bool:
        return len(self.errors) == 0

    def log(self, label: str = "kanban-context") -> None:
        for w in self.warnings:
            logger.warning("%s: ⚠️  %s", label, w)
        for e in self.errors:
            logger.error("%s: ❌ %s", label, e)
        if not self.errors and not self.warnings:
            logger.info("%s: ✅ all validations passed", label)


def _validate_python_version(vr: ValidationResult) -> None:
    """Check Python >= 3.11."""
    import sys
    if sys.version_info < (3, 11):
        vr.errors.append(
            f"Python 3.11+ required (found {sys.version_info.major}.{sys.version_info.minor}). "
            "Please upgrade your Python interpreter."
        )


def _validate_hermes_version(vr: ValidationResult) -> None:
    """Try to detect Hermes Agent version."""
    try:
        from hermes_core.version import __version__ as hv
        parts = str(hv).lstrip("v").split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        if (major, minor) < (0, 13):
            vr.warnings.append(
                f"Hermes Agent v{'.'.join(parts)} detected — plugin was built for v0.13+. "
                "If you encounter issues, consider upgrading Hermes."
            )
    except ImportError:
        vr.warnings.append(
            "Could not detect Hermes Agent version (hermes_core.version not found). "
            "Assuming compatibility — if you hit issues, check Hermes >= v0.13.0."
        )


def _validate_multi_agent_plugin(vr: ValidationResult) -> None:
    """Check that multi-agent-context plugin is installed (required dependency)."""
    plugin_dirs = _hermes_home() / "plugins"
    if not plugin_dirs.is_dir():
        vr.warnings.append(
            f"Plugin directory not found at {plugin_dirs}. "
            "Make sure multi-agent-context is installed for the shared DB."
        )
        return

    found = False
    try:
        for d in plugin_dirs.iterdir():
            if d.is_dir() and d.name == "multi-agent-context":
                found = True
                break
    except PermissionError:
        vr.warnings.append(
            f"Cannot read plugin directory {plugin_dirs} (permission). "
            "Please verify multi-agent-context is installed."
        )
        return

    if not found:
        vr.warnings.append(
            "multi-agent-context plugin not found in plugins directory. "
            "kanban-context's cross-bot messaging requires multi-agent-context "
            "for the shared SQLite database. "
            "Install it from https://github.com/franklinbravos/hermes-community-plugins"
        )


def _validate_shared_db(vr: ValidationResult) -> None:
    """Check shared DB path is writable and outbox table can be created."""
    path = _shared_db_path()
    try:
        parent = os.path.dirname(path)
        os.makedirs(parent, exist_ok=True)
        # Try to open and create the table
        conn = sqlite3.connect(path, timeout=5)
        conn.execute(_OUTBOX_TABLE)
        conn.commit()
        conn.close()
        logger.debug("kanban-context: shared DB OK at %s", path)
    except Exception as exc:
        vr.errors.append(
            f"Cannot create/open shared database at '{path}': {exc}. "
            "Check directory permissions and disk space."
        )


def _validate_kanban_db(vr: ValidationResult) -> None:
    """Check that kanban DB exists or kanban boards dir exists."""
    default = _kanban_db()
    boards = _boards_dir()

    if default.is_file():
        logger.debug("kanban-context: kanban DB found at %s", default)
        return
    if boards.is_dir():
        logger.debug("kanban-context: kanban boards dir found at %s", boards)
        return

    vr.warnings.append(
        f"No kanban database found at {default} and no boards dir at {boards}. "
        "Kanban activity injection will be empty until a board is created. "
        "Use 'hermes kanban create-board <name>' to create one."
    )


def _validate_bot_name(vr: ValidationResult) -> None:
    """Check that a bot name can be resolved."""
    name = _my_bot_name()
    if name and name != "bot":
        logger.debug("kanban-context: bot name resolved as '%s'", name)
        return

    # Only a warning — the fallback name "bot" works for single-instance setups
    vr.warnings.append(
        "No explicit bot name set (CROSSBOT_BOT_NAME). "
        "Falling back to profile name or 'bot'. "
        "For multi-bot setups, set CROSSBOT_BOT_NAME env var "
        "to each bot's unique name to enable cross-bot messaging."
    )


def _validate_env_vars(vr: ValidationResult) -> None:
    """Validate numeric env vars at load time."""
    for key, default, label in [
        ("KANBAN_CONTEXT_EVENT_LIMIT", "10", "event limit"),
        ("KANBAN_CONTEXT_LOOKBACK_H", "12", "lookback hours"),
    ]:
        raw = os.environ.get(key, default)
        try:
            val = int(raw)
            if val < 0:
                vr.warnings.append(
                    f"{key}={raw} is negative — using default ({default})."
                )
            if key == "KANBAN_CONTEXT_EVENT_LIMIT" and val > 100:
                vr.warnings.append(
                    f"{key}={val} is very high — may exceed context window."
                )
            if key == "KANBAN_CONTEXT_LOOKBACK_H" and val > 168:
                vr.warnings.append(
                    f"{key}={val} (>{168}h = 1 week) — large lookback may "
                    "produce too many events."
                )
        except (ValueError, TypeError):
            vr.warnings.append(
                f"{key}={raw} is not a valid integer — using default ({default})."
            )

    # Validate visibility config (optional, advisory only)
    vis_chat = os.environ.get("CROSSBOT_VISIBILITY_CHAT", "").strip()
    if vis_chat:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not bot_token:
            vr.warnings.append(
                "CROSSBOT_VISIBILITY_CHAT is set but TELEGRAM_BOT_TOKEN is missing. "
                "Cross-bot messages will be written to the outbox but NOT posted "
                "to the Telegram group."
            )
        else:
            logger.info(
                "kanban-context: visibility enabled — cross-bot messages will "
                "be posted to chat %s", vis_chat,
            )


def _validate_log_dir(vr: ValidationResult) -> None:
    """Ensure the kanban plugin log directory exists and is writable."""
    log_dir = _hermes_home() / "logs" / "kanban-context"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        vr.warnings.append(
            f"Cannot create log directory {log_dir}: {exc}. "
            "Plugin will still work but logs won't be persisted to disk."
        )


def run_validation() -> ValidationResult:
    """Run all validation checks and return the result."""
    vr = ValidationResult()
    _validate_python_version(vr)
    _validate_hermes_version(vr)
    _validate_multi_agent_plugin(vr)
    _validate_shared_db(vr)
    _validate_kanban_db(vr)
    _validate_bot_name(vr)
    _validate_env_vars(vr)
    _validate_log_dir(vr)
    return vr


def _get_plugin_version() -> str:
    """Read plugin version from plugin.yaml."""
    plugin_yaml = _hermes_home() / "plugins" / "kanban-context" / "plugin.yaml"
    try:
        with open(str(plugin_yaml)) as f:
            for line in f:
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "2.0.0"


# ---------------------------------------------------------------------------
# Dashboard / Status — inspectable via agent or direct call
# ---------------------------------------------------------------------------


def kanban_status() -> str:
    """Return a human-readable status report of the kanban-context plugin.

    Can be called by the agent when the user asks about bot/plugin status.
    Returns a formatted string with sections:
      - Plugin version and config
      - Bot identity
      - Boards discovered
      - Outbox statistics
      - Validation status
    """
    lines: List[str] = []
    sep = "-" * 40

    # Header
    lines.append("[Kanban-Context Status]")
    lines.append("")

    # Version & config
    lines.append(f"Plugin version: {_get_plugin_version()}")
    lines.append(f"Python:         {__import__('sys').version_info.major}.{__import__('sys').version_info.minor}")
    try:
        from hermes_core.version import __version__ as hv
        lines.append(f"Hermes Agent:   v{hv}")
    except ImportError:
        lines.append("Hermes Agent:   (unknown)")
    lines.append(sep)

    # Bot identity
    lines.append(f"Bot name:       {_my_bot_name()}")
    lines.append(f"Hermes home:    {_hermes_home()}")
    lines.append(f"Shared DB:      {_shared_db_path()}")
    lines.append(f"Kanban DB:      {_kanban_db()}")

    # Configuration
    lines.append(sep)
    lines.append(f"Event limit:    {_event_limit()} events")
    lines.append(f"Lookback:       {_lookback_hours()}h")
    lines.append(f"Cleanup:        every {_get_cleanup_interval() // 3600}h")
    lines.append(f"Outbox retain:  {_get_outbox_retention_days()}d")
    lines.append(f"Log retain:     {_get_log_retention_days()}d")
    lines.append(sep)

    # Boards discovered
    boards = _iter_boards()
    if boards:
        lines.append(f"Kanban boards:  {len(boards)} found")
        for db_path, label in boards:
            try:
                db_size = os.path.getsize(db_path) / 1024
            except OSError:
                db_size = 0.0
            lines.append(f"  - {label} ({db_size:.0f} KB)")
    else:
        lines.append("Kanban boards:  none (activity injection will be empty)")
    lines.append(sep)

    # Outbox stats
    try:
        conn = _open_shared_db()
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM outbox GROUP BY status"
        ).fetchall()
        conn.close()
        stats = {r[0]: r[1] for r in rows}
        total = sum(stats.values()) if stats else 0
        lines.append(f"Outbox total:   {total} messages")
        for status in ("pending", "done", "delivered"):
            count = stats.get(status, 0)
            if count > 0:
                lines.append(f"  - {status}: {count}")
    except Exception as exc:
        lines.append(f"Outbox:         error reading — {exc}")

    # Validation
    vr = run_validation()
    if vr.ok() and not vr.warnings:
        lines.append(sep)
        lines.append("Health:         ✅ all checks passed")
    else:
        lines.append(sep)
        lines.append(f"Health:         {'❌ errors' if vr.errors else '⚠ warnings'}")
        for w in vr.warnings[:3]:
            lines.append(f"  ⚠ {w[:80]}")
        for e in vr.errors[:3]:
            lines.append(f"  ❌ {e[:80]}")

    return "\n".join(lines)


def _handle_status_command(**kwargs) -> Optional[Dict[str, str]]:
    """pre_llm_call hook — detect /kanban-status and inject status context.

    When the user sends a message starting with /kanban-status, this
    hook replaces the normal context injection with a status report.
    """
    user_message = kwargs.get("user_message", "")
    if not user_message or not user_message.strip().startswith("/kanban-status"):
        return None

    # Return status as context so the agent can read and respond
    status = kanban_status()
    logger.info("kanban-context: status requested (size=%d chars)", len(status))
    return {"context": status}


def register(ctx) -> None:
    # Run proactive validation
    vr = run_validation()
    vr.log()

    ctx.register_tool(
        name="crossbot_send",
        handler=lambda args, **kw: _crossbot_send_tool(args, **kw),
        schema={
            "name": "crossbot_send",
            "description": (
                "Send a message to another Hermes bot profile via the shared cross-bot outbox. "
                "Returns outbox_id. Target bot receives via Kanban worker + [Pending Messages]."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to_bot": {"type": "string", "description": "Target profile name (e.g. bravo)."},
                    "subject": {"type": "string", "description": "Short subject."},
                    "body": {"type": "string", "description": "Full message body."},
                    "kanban_task_id": {"type": "string", "description": "Optional existing task ID."},
                },
                "required": ["to_bot", "body"],
            },
        },
    )
    ctx.register_tool(
        name="crossbot_respond",
        handler=lambda args, **kw: _crossbot_respond_tool(args, **kw),
        schema={
            "name": "crossbot_respond",
            "description": (
                "MANDATORY for cross-bot Kanban workers — call BEFORE kanban_complete. "
                "Marks outbox done and posts response visibility to Telegram."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "outbox_id": {"type": "integer", "description": "Outbox ID from task body or [Pending Messages]."},
                    "response_text": {"type": "string", "description": "Full reply to sender."},
                },
                "required": ["outbox_id", "response_text"],
            },
        },
    )

    ctx.register_hook("pre_llm_call", _inject_kanban_context)
    ctx.register_hook("pre_llm_call", _handle_status_command)
    ctx.register_hook("pre_llm_call", _inject_response_coordination)
    ctx.register_hook("pre_llm_call", _auto_detect_mentions)
