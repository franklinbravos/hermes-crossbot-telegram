# Atribuição — plugin crossbot

> 🇧🇷 **Português** · 🇺🇸 [English](./ATTRIBUTION.md)

O **crossbot** unifica funcionalidades que existiam como plugins separados neste repositório.

## Componentes incorporados

| Módulo original | Autor | Função no crossbot |
|-----------------|-------|---------------------|
| **kanban-context** | Franklin Bravos (@franklinbravos) | Outbox bot-to-bot, Kanban dispatch, mention relay, visibilidade Telegram, coordenação de resposta |
| **multi-agent-context** | Kaishi (@kaishi00) | Histórico compartilhado Telegram (SQLite) e Discord (REST) — `shared_history.py` |

## Nome e versão

- **Repositório:** [github.com/franklinbravos/hermes-crossbot-telegram](https://github.com/franklinbravos/hermes-crossbot-telegram) *(antes `hermes-community-plugins`)*
- **Plugin:** `crossbot` v0.5.2 *(pré-release)*
- **v1.0:** reservada para quando mention relay + visibilidade estiverem validados em produção
- **Dependências:** Hermes Core + biblioteca padrão Python (sem `pip install` extra)

## Migração desde v2.x

| Antes (plugins separados) | Depois (crossbot) |
|------------|-------------|
| `multi-agent-context` + `kanban-context` | apenas `crossbot` |
| `~/.hermes/plugins/kanban-context/` | `~/.hermes/plugins/crossbot/` |
| `MULTI_AGENT_TG_DB_PATH` | `CROSSBOT_DB_PATH` (alias legado aceito) |
| DB default `multi_agent_tg_shared.db` | `crossbot.db` (usa DB legado se existir) |
| Logs `~/.hermes/logs/kanban-context/` | `~/.hermes/logs/crossbot/` |

Em `config.yaml` de cada profile:

```yaml
plugins:
  enabled:
    - crossbot
```

Remova `kanban-context` e `multi-agent-context` da lista `enabled`.
