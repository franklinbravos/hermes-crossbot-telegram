# Feature Map

> Index of user-facing features and code paths. Paths relative to repository root.

## Async background delegation

**Plugin:** `plugins/async-delegate/__init__.py`

1. `register()` — exposes `delegate_async` tool
2. `delegate_async_tool()` — writes task files, spawns `hermes chat`
3. `_watcher_loop()` — detects `.done`, calls `_inject_task_notification()`
4. `_inject_task_notification()` — queue/steer or `pre_llm_inject_results` fallback

---

## Shared multi-agent channel context (Discord)

**Plugin:** `plugins/multi-agent-context/__init__.py`

1. `pre_llm_call` → `_inject_channel_context()`
2. `_resolve_target()` — thread/chat IDs from session context
3. `_discord_get()` + `_format_discord_messages()`
4. Returns `{"context": ...}` to Hermes core

---

## Shared multi-agent group context (Telegram)

**Plugin:** `plugins/multi-agent-context/__init__.py`

1. `post_llm_call` → `_record_telegram_turn()` → `_tg_write()`
2. Next `pre_llm_call` → `_tg_read()`
3. Formatted `[Recent Group History]`

---

## Kanban activity awareness

**Plugin:** `plugins/kanban-context/__init__.py`

1. `pre_llm_call` → `_inject_kanban_context()` → `_read_kanban_events()`
2. `_iter_boards()` — default + named boards
3. SQL on `task_events` / `tasks` → `[Recent Kanban Activity]`

---

## Cross-bot messaging (Telegram)

**Plugin:** `plugins/kanban-context/__init__.py`

1. `crossbot_send()` — INSERT outbox, optional Kanban task
2. Target `pre_llm_call` → `[Pending Messages]`
3. `crossbot_respond()` or `crossbot_cli.py` — UPDATE outbox + visibility post

---

## Cross-bot CLI (workers)

**Plugin:** `plugins/kanban-context/crossbot_cli.py`

Workers without plugin tools call CLI via terminal before `kanban_complete`.

---

## Plugin status dashboard

**Plugin:** `plugins/kanban-context/__init__.py`

1. `/kanban-status` detected in `pre_llm_call`
2. `kanban_status()` — version, boards, outbox, validation

---

## Telefone sem fio (test protocol)

**Docs:** `docs/onboarding/05-telefone-sem-fio.md`  
Uses standard cross-bot flow with `[TelefoneSemFio]` subject contract.
