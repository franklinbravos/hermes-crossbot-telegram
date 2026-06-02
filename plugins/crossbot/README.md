# crossbot — Telegram bot-to-bot messaging

> 🇺🇸 **English** · 🇧🇷 [Português](./README.pt-BR.md)

**Unified plugin** for multi-agent Hermes ecosystems on Telegram.

**Version:** 0.5.2 *(pre-release — v1.0 after production validation)*

## What it does

| Feature | Origin |
|---------|--------|
| Shared group history (SQLite) | multi-agent-context (Kaishi) |
| Bot-to-bot outbox + Kanban dispatch | kanban-context (Franklin Bravos) |
| Mention relay (`@colleague` in reply) | kanban-context (mention relay) |
| Visibility 📤/📥 on Telegram | kanban-context |
| Topic-based response coordination | kanban-context |

→ Full attribution: [ATTRIBUTION.md](./ATTRIBUTION.md)

## Installation

```bash
./scripts/install.sh cross-bot   # installs crossbot only
```

Enable in each profile:

```yaml
plugins:
  enabled:
    - crossbot
```

## Dependencies

**Hermes Core + Python stdlib** — no extra pip packages.

## Configuration

| Variable | Description |
|----------|-------------|
| `CROSSBOT_BOT_NAME` | This bot's profile name |
| `CROSSBOT_DB_PATH` | Shared SQLite path (default: `~/.hermes/data/crossbot.db`) |
| `CROSSBOT_VISIBILITY_CHAT` | Telegram group for visibility posts |
| `CROSSBOT_VISIBILITY_TOKEN` | Bot token for visibility posts (separate from main) |
| `CROSSBOT_VISIBILITY_THREAD` | Topic/thread ID for visibility posts |
| `CROSSBOT_KANBAN_BOARD` | Kanban board name (default: `cross-bot`) |
| `CROSSBOT_DISPATCHER_INTERVAL` | Mini-dispatcher poll interval in seconds (default: `5`) |
| `CROSSBOT_DISPATCHER_ENABLED` | Enable mini-dispatcher daemon (default: `true`) |
| `CROSSBOT_WARMUP_ENABLED` | Enable agent warmup on register (default: `true`) |
| `KANBAN_CONTEXT_EVENT_LIMIT` | Max events to inject as context (default: `10`) |
| `KANBAN_CONTEXT_LOOKBACK_H` | Event lookback window in hours (default: `12`) |
| `topic-map.json` | Profiles, handles and topic mappings |

### topic-map.json

```json
{
  "orchestrator": "iago",
  "chat_id": "-1001234567890",
  "topics": {
    "bot_a": 195,
    "bot_b": 303,
    "bot_c": 14
  },
  "handles": {
    "bot_a": "bot_a_handle",
    "bot_b": "bot_b_handle",
    "bot_c": "bot_c_handle"
  }
}
```

### visibility-config.json

```json
{
  "telegram_bot_token": "",
  "visibility_chat_id": "-1001234567890",
  "enabled": true,
  "visibility_thread_id": ""
}
```

## CLI (fallback for workers)

```bash
CROSSBOT_BOT_NAME=YOUR_PROFILE python3 ~/.hermes/plugins/crossbot/crossbot_cli.py respond OUTBOX_ID "response text"
```

## Architecture

```
Bot A sends → crossbot_send() → outbox (SQLite) + kanban task
                                        ↓
                             Mini-dispatcher (5s poll) or Gateway dispatcher (60s)
                                        ↓
                             Worker spawned (hermes chat) → processes → responds
                                        ↓
                             crossbot_respond() → closes outbox → relays to next bot
```

The plugin includes two dispatch mechanisms:
1. **Mini-dispatcher** — a daemon thread that polls the cross-bot kanban board every 5 seconds (configurable). Enabled by default.
2. **Gateway dispatcher** — the Hermes built-in dispatcher (default 60s interval). The plugin attempts to auto-tune this to 10s on load.

## Tools

| Tool | Description |
|------|-------------|
| `crossbot_send` | Send a message to another bot profile |
| `crossbot_respond` | Respond to a pending cross-bot message |
| `crossbot_purge` | Remove all crossbot data for clean reinstall |
| `kanban_complete` | Complete a kanban task (auto-closes outbox) |

## Hooks

| Hook | Function | Purpose |
|------|----------|---------|
| `pre_llm_call` | `_inject_kanban_context` | Injects board activity + pending messages |
| `pre_llm_call` | `_inject_response_coordination` | Prevents duplicate responses |
| `pre_llm_call` | `_auto_detect_mentions` | Auto-creates tasks on @mentions |
| `post_llm_call` | `_post_llm_mention_relay` | Relays @mentions in assistant replies |
| `post_tool_call` | `_on_post_tool_call` | Auto-closes outbox on kanban_complete |

## Documentation

- [How it works](../../docs/onboarding/01-como-funciona.md)
- [Debug](../../docs/reference/debug-crossbot.md)
