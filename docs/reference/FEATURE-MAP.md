# Feature Map — Crossbot

> Plugin unificado: `plugins/crossbot/` (v0.5+, pré-release)  
> Origem: `kanban-context` (Franklin Bravos) + `multi-agent-context` (Kaishi)

## Histórico compartilhado Telegram

**Módulo:** `plugins/crossbot/shared_history.py`

- `post_llm_call` persiste turnos no SQLite WAL
- `pre_llm_call` injeta `[Recent Group History]`

## Histórico Discord (opcional)

**Módulo:** `plugins/crossbot/shared_history.py`

- REST via stdlib `urllib` (sem pip)
- Requer `DISCORD_BOT_TOKEN`

## Outbox bot-to-bot

**Módulo:** `plugins/crossbot/__init__.py`

- Tabela `outbox` no DB compartilhado
- Tools `crossbot_send` / `crossbot_respond`

## Mention relay

**Módulo:** `plugins/crossbot/__init__.py`

- `post_llm_call`: `@mention` na resposta → outbox + Kanban task
- Auto-resposta do worker Kanban

## CLI fallback

**Arquivo:** `plugins/crossbot/crossbot_cli.py`

- Workers sem toolset de plugin

## Kanban activity + coordenação

**Módulo:** `plugins/crossbot/__init__.py`

- `[Recent Kanban Activity]`
- `[Response Coordination]` por tópico
- `/kanban-status`
