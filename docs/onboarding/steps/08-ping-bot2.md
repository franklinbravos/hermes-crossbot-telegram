# Step 8 — Ping bot2 / 2º salto

## Ação

Após step 7, o plugin pode fazer **benchmark_relay** automaticamente. Se não:

- Envie manualmente ao 2º jogador via orchestrator, ou
- Confirme relay no audit

## Gate

```bash
./scripts/crossbot-onboarding.sh verify --watch 120
```

Audit com `benchmark_relay` **ou** segundo outbox para bot2.

## Falhas comuns

- Gateway do 2º jogador parado → step 5
