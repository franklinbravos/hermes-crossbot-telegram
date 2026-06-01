# Step 3a — topic-map

## Ação

```bash
./scripts/configure-crossbot.sh --yes \
  --chat-id -100XXXXXXXXXX \
  --orchestrator coordenador \
  --players agente-a,agente-b
```

## Gate

- `orchestrator` definido
- `chat_id` real (sem `X`)
- Cada bot em `topics` tem pasta em `~/.hermes/profiles/`
- `handles` preenchidos

## Falhas comuns

- Profile missing → criar profile Hermes ou corrigir nomes no mapa
