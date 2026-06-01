# Step 3b — Visibilidade probe

## Ação

Edite `~/.hermes/plugins/crossbot/visibility-config.json`:

- `visibility_chat_id` = chat_id **real** do fórum (nunca placeholder)
- Token: `telegram_bot_token` ou `TELEGRAM_BOT_TOKEN` do orchestrator no `.env`

Opcional: envie uma mensagem de teste e confira audit:

```bash
tail -20 ~/.hermes/logs/crossbot/crossbot-audit.jsonl | grep visibility_post
```

## Gate

- Zero `visibility_post` com `ok=false` nos últimos 15 min
- Sem `chat not found` ou `-100XXXXXXXXXX` no audit recente

## Falhas comuns

- Placeholder no env no momento do send → corrigir e reiniciar gateway
