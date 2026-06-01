# Telefone sem fio (legado)

> **Modelo unificado:** [05-benchmark-cadeia.md](./05-benchmark-cadeia.md)

*Telefone sem fio*, *fui ao mercado* e *fui à feira* usam o **mesmo motor** (`benchmark-chain.sh`). Só muda o tema:

| Script | Tema | Incremento |
|--------|------|------------|
| `telefone-sem-fio.sh` | telefone | +2 palavras |
| `fui-ao-mercado.sh` | mercado / feira | +1 item |

```bash
./scripts/telefone-sem-fio.sh
PHRASE="O rato roeu" ./scripts/telefone-sem-fio.sh
./scripts/benchmark-report.sh
```
