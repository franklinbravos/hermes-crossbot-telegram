# Attribution — crossbot plugin

> 🇺🇸 **English** · 🇧🇷 [Português](./ATTRIBUTION.pt-BR.md)

The **crossbot** plugin unifies features that previously existed as separate plugins in this repository.

## Incorporated Components

| Original module | Author | Role in crossbot |
|-----------------|--------|------------------|
| **kanban-context** | Franklin Bravos (@franklinbravos) | Bot-to-bot outbox, Kanban dispatch, mention relay, Telegram visibility, response coordination |
| **multi-agent-context** | Kaishi (@kaishi00) | Shared Telegram history (SQLite) and Discord (REST) — `shared_history.py` |

## Name and Version

- **Repository:** [github.com/franklinbravos/hermes-crossbot-telegram](https://github.com/franklinbravos/hermes-crossbot-telegram) *(formerly `hermes-community-plugins`)*
- **Plugin:** `crossbot` v0.6.0
- **v1.0:** reserved for when mention relay + visibility are validated in production
- **Dependencies:** Hermes Core + Python standard library (no `pip install` extras)

## Migration from v2.x

| Before (separate plugins) | After (crossbot) |
|---------------------------|------------------|
| `multi-agent-context` + `kanban-context` | `crossbot` only |
| `~/.hermes/plugins/kanban-context/` | `~/.hermes/plugins/crossbot/` |
| `MULTI_AGENT_TG_DB_PATH` | `CROSSBOT_DB_PATH` (legacy alias accepted) |
| Default DB `multi_agent_tg_shared.db` | `crossbot.db` (uses legacy DB if exists) |
| Logs `~/.hermes/logs/kanban-context/` | `~/.hermes/logs/crossbot/` |

In each profile's `config.yaml`:

```yaml
plugins:
  enabled:
    - crossbot
```

Remove `kanban-context` and `multi-agent-context` from the `enabled` list.
