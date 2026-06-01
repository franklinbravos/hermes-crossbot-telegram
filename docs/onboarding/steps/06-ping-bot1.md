# Step 6 — Ping bot1

## Ação

```bash
./scripts/crossbot-onboarding.sh run-action
```

Dispara `crossbot_send` do orchestrator ao 1º jogador com corpo `ONBOARDING_PING`.

## Gate

- `visibility_post` com `ok=true` no audit
- `chat_id` == topic-map.chat_id
- `thread_id` == topic-map.topics[to_bot]
- Outbox com `kanban_task_id`

```bash
./scripts/crossbot-onboarding.sh verify
```

## Falhas comuns

- Visibility falhou → voltar step 3b
- Thread errado → revisar topic-map
