# Step 10 — Handoff

## Ação

```bash
./scripts/crossbot-debug-pack.sh pack
```

Envie o `.zip` de `~/.hermes/logs/crossbot/packs/` ao desenvolvedor.

**Não** escreva relatório manual — o zip é a evidência.

## Gate

- Zip gerado
- `MANIFEST.json` sem red_flags críticos (`OUTBOX_ALL_PENDING`, `NO_CROSSBOT_RESPOND`, `KANBAN_TASK_BLOCKED`, `VISIBILITY_CHAT_PLACEHOLDER`)

```bash
./scripts/crossbot-onboarding.sh verify
./scripts/crossbot-onboarding.sh advance   # conclui onboarding
```

## Template feedback

- Host / profiles
- Onboarding run_id
- Versão plugin
- Zip anexo
