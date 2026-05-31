# Feature Map

> Auto-maintained index of every user-facing feature and the code path that implements it. Updated alongside the code — not after the fact.

## Async background delegation

Spawn a subagent in the background without blocking the current turn; get notified when it finishes.

**Flow:**

1. `async-delegate/__init__.py` — `register()` exposes `delegate_async` tool; agent invokes it during a turn.
2. `async-delegate/__init__.py` — `delegate_async_tool()` writes prompt/meta under `~/.hermes/async-tasks/` and starts `hermes chat` via wrapper shell script.
3. `async-delegate/__init__.py` — `_watcher_loop()` daemon detects `.done` files and calls `_inject_task_notification()`.
4. `async-delegate/__init__.py` — `_inject_task_notification()` delivers via gateway adapter (queue or steer) or `pre_llm_inject_results()` fallback adds context ping.

---

## Shared multi-agent channel context (Discord)

Agents see recent channel/thread messages when @mentioned, without `trigger: all` loops.

**Flow:**

1. `multi-agent-context/__init__.py` — `register()` hooks `pre_llm_call` → `_inject_channel_context()`.
2. `multi-agent-context/__init__.py` — `_resolve_target()` reads thread/chat IDs from `gateway.session_context`.
3. `multi-agent-context/__init__.py` — `_discord_get()` fetches messages; `_format_discord_messages()` builds `[Recent Channel/Thread History]`.
4. `multi-agent-context/__init__.py` — returns `{"context": ctx_text}` merged into the LLM call by Hermes core.

---

## Shared multi-agent group context (Telegram)

Multiple bot processes share turn history via SQLite WAL on disk.

**Flow:**

1. `multi-agent-context/__init__.py` — `post_llm_call` → `_record_telegram_turn()` → `_tg_write()` inserts user/bot rows.
2. `multi-agent-context/__init__.py` — next `pre_llm_call` → `_tg_read()` for same `chat_key`.
3. `multi-agent-context/__init__.py` — formatted `[Recent Group History]` returned as `{"context": ...}`.

---

## Kanban activity awareness

Agents see recent board events (created, blocked, completed, etc.) without explicit kanban tool calls.

**Flow:**

1. `kanban-context/__init__.py` — `pre_llm_call` → `_inject_kanban_context()` → `_read_kanban_events()`.
2. `kanban-context/__init__.py` — `_iter_boards()` discovers default `kanban.db` and `kanban/boards/*/kanban.db`.
3. `kanban-context/__init__.py` — SQL on `task_events` + `tasks`; `_describe_event()` formats lines into `[Recent Kanban Activity]`.
4. `kanban-context/__init__.py` — combined context returned to Hermes before LLM.

---

## Cross-bot messaging (Telegram)

Bots address each other via shared outbox; optional Kanban task auto-created for dispatcher pickup.

**Flow:**

1. `kanban-context/__init__.py` — caller invokes `crossbot_send()` (tool/script/agent code).
2. `kanban-context/__init__.py` — `_open_shared_db()` INSERT into `outbox`; optional Hermes `create_task()` on board `linkedin-content`.
3. `kanban-context/__init__.py` — target bot's `pre_llm_call` → `_read_pending_messages()` injects `[Pending Messages]`.
4. `kanban-context/__init__.py` — receiver calls `crossbot_respond` tool (or API); optional `_post_visibility_message()` to Telegram group.

---

## Cross-bot Hermes tools

Agents send/reply via registered tools (v2.1.4+):

**Flow:**

1. `kanban-context/__init__.py` — `register()` exposes `crossbot_send` and `crossbot_respond` tools.
2. Sender agent invokes `crossbot_send` during a turn.
3. Receiver sees `[Pending Messages]` with outbox ID in `pre_llm_call` context.
4. Receiver invokes `crossbot_respond` with `outbox_id` + `response_text`.

---

## Multi-bot response coordination

Reduces duplicate replies in shared Telegram groups using mentions, reply-to, and topic assignment.

**Flow:**

1. `kanban-context/__init__.py` — `pre_llm_call` → `_inject_response_coordination()` builds `[Response Coordination]` context.
2. `kanban-context/__init__.py` — `claim_response()` (callable API) applies rules via `_is_bot_mentioned()`, `_replied_to_bot()`, `_is_designated_bot_for_chat()`.
3. `kanban-context/__init__.py` — `_record_response_claim()` writes `response_log` in shared SQLite DB.

---

## Plugin status dashboard

User sends `/kanban-status` and agent reports health, boards, and outbox stats.

**Flow:**

1. `kanban-context/__init__.py` — `pre_llm_call` → `_handle_status_command()` detects `/kanban-status` prefix.
2. `kanban-context/__init__.py` — `kanban_status()` aggregates version, config, boards, outbox, `run_validation()`.
3. `kanban-context/__init__.py` — returns `{"context": status}` for agent to relay to user.

---
