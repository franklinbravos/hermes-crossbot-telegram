# Setup — Novo projeto Hermes multi-bot

> Do zero ao primeiro cross-bot. Tempo: 30–60 min.

## Pré-requisitos

- Hermes Agent **v0.13+**, Python **3.11+**
- Grupo Telegram **Fórum** com tópicos
- Um bot Telegram por agente
- SSH ao servidor dos gateways

## Passo 1 — Instalar plugins

```bash
git clone https://github.com/franklinbravos/hermes-community-plugins.git
cp -r hermes-community-plugins/kanban-context ~/.hermes/plugins/kanban-context
cp -r hermes-community-plugins/multi-agent-context ~/.hermes/plugins/multi-agent-context
```

```yaml
# config.yaml de cada profile
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

Symlink recomendado:

```bash
for bot in orchestrator ops agent-alpha agent-beta; do
  mkdir -p ~/.hermes/profiles/${bot}/plugins
  ln -sf ~/.hermes/plugins/kanban-context ~/.hermes/profiles/${bot}/plugins/kanban-context
  ln -sf ~/.hermes/plugins/multi-agent-context ~/.hermes/profiles/${bot}/plugins/multi-agent-context
done
```

## Passo 2 — SQLite compartilhado

```bash
# MESMO valor em todos os profiles
MULTI_AGENT_TG_DB_PATH=/path/to/.hermes/data/multi_agent_tg_shared.db
```

## Passo 3 — Nome do bot

```bash
# profiles/NOME/.env
CROSSBOT_BOT_NAME=agent-alpha
TELEGRAM_BOT_TOKEN=...
```

## Passo 4 — Grupo fórum + tópicos

→ [03-topicos-telegram.md](./03-topicos-telegram.md)

## Passo 5 — topic-map.json

Copie de [../reference/topic-map.example.json](../reference/topic-map.example.json) e preencha chat_id, thread_ids e handles.

## Passo 6 — Visibilidade

`visibility-config.json`:

```json
{
  "telegram_bot_token": "",
  "visibility_chat_id": "-100XXXXXXXXXX",
  "enabled": true,
  "visibility_thread_id": "0"
}
```

**v2.2.4+:** cada bot posta com token do **próprio profile**. Token global é só fallback.

## Passo 7–8 — Kanban board + restart

```bash
CROSSBOT_KANBAN_BOARD=seu-board   # default: linkedin-content
hermes gateway restart
```

## Passo 9 — Health check

Envie `/kanban-status` ou rode validação Python (ver [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md)).

## Passo 10 — Smoke test

```bash
CROSSBOT_BOT_NAME=ops python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send agent-alpha "Smoke test" "Confirme recebimento"
```

## Passo 10b — Telefone sem fio

→ [05-telefone-sem-fio.md](./05-telefone-sem-fio.md) · execução: [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md)

## Passo 11 — SOUL dos agentes

→ [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)

## Troubleshooting

| Sintoma | Ação |
|---------|------|
| Outbox pending | Worker não usou crossbot_cli |
| Remetente errado no TG | Atualizar para v2.2.4+ |
| Bot não recebe | Conferir CROSSBOT_BOT_NAME |
| DB isolado | Unificar MULTI_AGENT_TG_DB_PATH |

→ [../reference/debug-crossbot.md](../reference/debug-crossbot.md)
