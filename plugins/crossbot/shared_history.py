"""Shared channel/group history — merged from multi-agent-context (Kaishi).

Telegram: SQLite WAL shared DB across Hermes processes.
Discord: optional REST history via stdlib urllib (no pip deps).

Original plugin: multi-agent-context · Author: Kaishi (@kaishi00)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_BOT_TOKEN: Optional[str] = None
_SELF_BOT_ID: Optional[str] = None
_discord_cache: Dict[str, Tuple[float, str]] = {}
_CACHE_TTL: float = 10.0
_TG_DB_TTL_HOURS: float = 48.0


def _history_count() -> int:
    try:
        return int(os.environ.get("MULTI_AGENT_HISTORY_COUNT", "20"))
    except ValueError:
        return 20


def _hermes_home_default() -> str:
    return os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))


def shared_db_path() -> str:
    """Shared SQLite path (outbox + group history). Legacy env vars supported."""
    for key in ("CROSSBOT_DB_PATH", "MULTI_AGENT_TG_DB_PATH"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    home = _hermes_home_default()
    legacy = os.path.join(home, "data", "multi_agent_tg_shared.db")
    primary = os.path.join(home, "data", "crossbot.db")
    if os.path.isfile(legacy) and not os.path.isfile(primary):
        return legacy
    return primary


def _load_discord_config() -> bool:
    global _BOT_TOKEN
    _BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not _BOT_TOKEN:
        logger.debug("crossbot: DISCORD_BOT_TOKEN not set, skipping Discord history")
        return False
    return True


def _discord_get(endpoint: str) -> Optional[dict]:
    url = f"https://discord.com/api/v10/{endpoint}"
    headers = {
        "Authorization": f"Bot {_BOT_TOKEN}",
        "User-Agent": "HermesCrossbot/0.5",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry_after = float(exc.headers.get("Retry-After", "1"))
            time.sleep(min(retry_after, 2))
            req2 = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req2, timeout=5) as resp2:
                    return json.loads(resp2.read().decode("utf-8"))
            except urllib.error.HTTPError as exc2:
                logger.warning("crossbot: Discord API %s → %d after retry", endpoint, exc2.code)
        else:
            logger.warning("crossbot: Discord API %s → %d", endpoint, exc.code)
    except Exception as exc:
        logger.warning("crossbot: Discord API request failed: %s", exc)
    return None


def _get_discord_bot_user_id() -> Optional[str]:
    global _SELF_BOT_ID
    if _SELF_BOT_ID:
        return _SELF_BOT_ID
    resp = _discord_get("users/@me")
    if resp and resp.get("id"):
        _SELF_BOT_ID = str(resp["id"])
        return _SELF_BOT_ID
    return None


def _resolve_target(**kwargs) -> Tuple[Optional[str], bool]:
    try:
        from gateway.session_context import get_session_env
        thread_id = get_session_env("HERMES_SESSION_THREAD_ID")
        if thread_id:
            return thread_id, True
        chat_id = get_session_env("HERMES_SESSION_CHAT_ID")
        if chat_id:
            return chat_id, False
    except ImportError:
        pass
    return None, False


def _format_discord_messages(messages: List[dict], self_bot_id: Optional[str], label: str) -> str:
    lines: List[str] = [f"[Recent {label} History]", ""]
    for msg in reversed(messages):
        author = msg.get("author", {})
        author_id = str(author.get("id", ""))
        content = msg.get("content", "").strip()
        if author_id == self_bot_id or not content or msg.get("type", 0) > 3:
            continue
        display = author.get("global_name") or author.get("username") or f"User-{author_id[:6]}"
        content = re.sub(r"<@!?(\d+)>", r"@<\1>", content)
        content = re.sub(r"<@&(\d+)>", r"@<role:\1>", content)
        content = re.sub(r"<#(\d+)>", r"#<\1>", content)
        if len(content) > 500:
            content = content[:497] + "..."
        lines.append(f"**{display}**: {content}")
    if len(lines) <= 2:
        return ""
    lines.extend(["", f"[End {label} History]"])
    return "\n".join(lines)


def _tg_open_db():
    import sqlite3
    conn = sqlite3.connect(shared_db_path(), timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            ts    REAL    NOT NULL,
            chat_key TEXT NOT NULL,
            sender   TEXT NOT NULL,
            text     TEXT NOT NULL
        )
    """)
    try:
        conn.execute(
            "ALTER TABLE messages ADD COLUMN telegram_msg_id INTEGER DEFAULT NULL"
        )
    except Exception:
        pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ck_ts ON messages (chat_key, ts)")
    conn.commit()
    return conn


def _tg_chat_key(session_id: str) -> str:
    parts = session_id.split(":")
    if len(parts) >= 5:
        chat_id = parts[4]
        if len(parts) > 5:
            return f"{chat_id}:{parts[5]}"
        return chat_id
    try:
        from gateway.session_context import get_session_env
        thread_id = get_session_env("HERMES_SESSION_THREAD_ID")
        if thread_id:
            chat_id = get_session_env("HERMES_SESSION_CHAT_ID")
            if chat_id:
                return f"{chat_id}:{thread_id}"
            return str(thread_id)
        chat_id = get_session_env("HERMES_SESSION_CHAT_ID")
        if chat_id:
            return str(chat_id)
    except ImportError:
        pass
    return session_id


def _tg_bot_name(session_id: str) -> str:
    name = os.environ.get("MULTI_AGENT_BOT_NAME", "").strip()
    if name:
        return name
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
    return "Bot"


def _resolve_assistant_telegram_msg_id(kwargs: dict) -> Optional[int]:
    for key in ("sent_message_id", "last_sent_message_id", "telegram_message_id"):
        raw = kwargs.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    try:
        from gateway.session_context import get_session_env
        raw = get_session_env("HERMES_SESSION_LAST_SENT_MESSAGE_ID")
        if raw:
            return int(raw)
    except Exception:
        pass
    return None


def _tg_write(
    session_id: str,
    user_message: str,
    assistant_response: str,
    assistant_msg_id: Optional[int] = None,
) -> None:
    try:
        chat_key = _tg_chat_key(session_id)
        bot_name = _tg_bot_name(session_id)
        now = time.time()
        conn = _tg_open_db()
        with conn:
            if user_message and user_message.strip():
                conn.execute(
                    "INSERT INTO messages (ts, chat_key, sender, text) VALUES (?,?,?,?)",
                    (now, chat_key, "user", user_message.strip()[:1000]),
                )
            if assistant_response and assistant_response.strip():
                conn.execute(
                    "INSERT INTO messages "
                    "(ts, chat_key, sender, text, telegram_msg_id) VALUES (?,?,?,?,?)",
                    (
                        now + 0.001,
                        chat_key,
                        bot_name,
                        assistant_response.strip()[:1000],
                        assistant_msg_id,
                    ),
                )
            cutoff = now - _TG_DB_TTL_HOURS * 3600
            conn.execute("DELETE FROM messages WHERE ts < ?", (cutoff,))
        conn.close()
        logger.debug(
            "crossbot: [tg] wrote turn chat_key=%s bot=%s", chat_key, bot_name,
        )
    except Exception as exc:
        logger.warning("crossbot: [tg] DB write failed: %s", exc)


def _tg_read(session_id: str) -> str:
    try:
        chat_key = _tg_chat_key(session_id)
        limit = _history_count()
        conn = _tg_open_db()
        rows = conn.execute(
            "SELECT sender, text FROM ("
            "  SELECT sender, text, ts FROM messages WHERE chat_key=?"
            "  ORDER BY ts DESC LIMIT ?"
            ") ORDER BY ts ASC",
            (chat_key, limit),
        ).fetchall()
        conn.close()
        if not rows:
            return ""
        lines = ["[Recent Group History]", ""]
        for sender, text in rows:
            if len(text) > 500:
                text = text[:497] + "..."
            lines.append(f"**{sender}**: {text}")
        lines.extend(["", "[End Group History]"])
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("crossbot: [tg] DB read failed: %s", exc)
        return ""


def record_telegram_turn(**kwargs) -> None:
    """post_llm_call — persist Telegram turn to shared SQLite."""
    if kwargs.get("platform", "") != "telegram":
        return
    session_id = kwargs.get("session_id", "")
    if not session_id:
        return
    assistant_msg_id = _resolve_assistant_telegram_msg_id(kwargs)
    _tg_write(
        session_id,
        kwargs.get("user_message", "") or "",
        kwargs.get("assistant_response", "") or "",
        assistant_msg_id,
    )


def inject_channel_context(**kwargs) -> Optional[dict]:
    """pre_llm_call — inject shared Discord/Telegram history."""
    platform = kwargs.get("platform", "")

    if platform == "discord":
        if not _load_discord_config():
            return None
        target_id, is_thread = _resolve_target(**kwargs)
        if not target_id:
            return None
        label = "Thread" if is_thread else "Channel"
        now = time.time()
        cached = _discord_cache.get(target_id)
        if cached and (now - cached[0]) < _CACHE_TTL:
            ctx_text = cached[1]
            return {"context": ctx_text} if ctx_text else None
        bot_id = _get_discord_bot_user_id()
        messages = _discord_get(f"channels/{target_id}/messages?limit={_history_count()}")
        msgs = messages if isinstance(messages, list) else []
        ctx_text = _format_discord_messages(msgs, bot_id, label)
        _discord_cache[target_id] = (now, ctx_text)
        if ctx_text:
            logger.info(
                "crossbot: [discord] injected %d chars of %s %s history",
                len(ctx_text), label.lower(), target_id,
            )
            return {"context": ctx_text}
        return None

    if platform == "telegram":
        session_id = kwargs.get("session_id", "")
        if not session_id:
            return None
        ctx_text = _tg_read(session_id)
        if ctx_text:
            logger.info(
                "crossbot: [tg] injected %d chars of history (session=%s)",
                len(ctx_text), session_id,
            )
            return {"context": ctx_text}
        return None

    return None
