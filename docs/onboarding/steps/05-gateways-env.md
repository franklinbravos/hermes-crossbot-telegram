# Step 5 — Gateways e env

## Ação

```bash
hermes gateway restart
# reinicie todos os profiles do topic-map
```

Checklist por profile em `~/.hermes/profiles/<nome>/.env`:

- `CROSSBOT_BOT_NAME=<nome da pasta>`
- `MULTI_AGENT_TG_DB_PATH` ou `CROSSBOT_DB_PATH` **idêntico** em todos
- `TELEGRAM_BOT_TOKEN` presente

SOUL: [AGENT-SYSTEM-PROMPT.md](../AGENT-SYSTEM-PROMPT.md)

## Gate

```bash
./scripts/crossbot-onboarding.sh verify
```

## Falhas comuns

- `CROSSBOT_BOT_NAME` ≠ nome da pasta
- DB paths diferentes entre profiles
