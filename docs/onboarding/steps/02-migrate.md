# Step 2 — Migrar legado

## Ação

O `bootstrap.sh` remove automaticamente `kanban-context` e `multi-agent-context`.

Confirme:

```bash
ls ~/.hermes/plugins/   # só crossbot (sem legado)
```

## Gate

```bash
./scripts/crossbot-onboarding.sh verify
```

## Falhas comuns

- Pastas legadas ainda presentes → `./scripts/bootstrap.sh --yes` novamente
