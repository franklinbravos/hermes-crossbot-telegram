# Step 9 — Benchmark cadeia

## Ação

```bash
./scripts/fui-ao-mercado.sh
# aguardar cadeia completar
./scripts/benchmark-report.sh
```

## Gate

```bash
./scripts/crossbot-onboarding.sh verify
```

- `benchmark-<round>.json` com `success=true`
- COMPLETE visto na cadeia

Se falhar:

```bash
./scripts/crossbot-debug-pack.sh pack -r <ROUND>
```

## Falhas comuns

- Mesmas do step 7 em cada hop
- Pending acumulados de rounds antigos → ignorar ou limpar DB
