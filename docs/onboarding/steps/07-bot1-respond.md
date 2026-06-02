# Step 7 — Resposta bot1

## Ação

**Nada no terminal do worker.** O dispatcher Kanban (~60s) spawna o worker do 1º jogador.

Worker deve usar **`kanban_complete(summary=..., metadata=...)`** — o hook `post_tool_call` fecha o outbox.

**NÃO** use `crossbot_cli` no worker — Tirith/security scan bloqueia terminal.

## Gate

```bash
./scripts/crossbot-onboarding.sh verify --watch 180
```

- **PASS:** outbox `done` + audit `crossbot_respond`
- **FAIL:** `WORKER_TERMINAL_BLOCKED` (task blocked + Security scan)
- **FAIL:** `KANBAN_DONE_OUTBOX_PENDING` (plugin < 0.6.0 ou hook ausente)

## Falhas comuns

| Flag | Causa |
|------|-------|
| WORKER_TERMINAL_BLOCKED | Worker tentou terminal |
| KANBAN_DONE_OUTBOX_PENDING | Atualizar plugin 0.6.0+ |
| OUTBOX_ALL_PENDING | Worker não completou — aguardar mais |

Debug: `./scripts/crossbot-debug-pack.sh pack`
