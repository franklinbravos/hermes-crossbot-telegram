# Benchmark de cadeia cumulativa (Crossbot)

Um **único motor** para três nomes de brincadeira:

| Nome | Tema (`BENCHMARK_THEME`) | Regra de incremento |
|------|--------------------------|---------------------|
| Telefone sem fio | `telefone` | +2 palavras por jogador |
| Fui ao mercado | `mercado` | +1 item por jogador |
| Fui à feira | `feira` | +1 item por jogador |

O protocolo é sempre o mesmo: **repetir a frase inteira, somar, repassar na ordem fixa**, monitorar tempo e taxa de sucesso.

## Iniciar

```bash
# Mercado (padrão)
~/hermes-crossbot-telegram/scripts/fui-ao-mercado.sh

# Feira
LOJA=feira ~/hermes-crossbot-telegram/scripts/fui-ao-mercado.sh

# Telefone sem fio
~/hermes-crossbot-telegram/scripts/telefone-sem-fio.sh

# Motor direto
BENCHMARK_THEME=telefone PHRASE="O rato roeu" ~/hermes-crossbot-telegram/scripts/benchmark-chain.sh
```

## Monitorar

```bash
tail -f ~/.hermes/logs/crossbot/crossbot-audit.jsonl | grep BenchmarkChain
```

## Relatório

```bash
~/hermes-crossbot-telegram/scripts/benchmark-report.sh
# ou com round específico:
~/hermes-crossbot-telegram/scripts/benchmark-report.sh 20260531-1430
```

Marcador no corpo da mensagem: `BENCHMARK_CHAIN`. Assunto: `[BenchmarkChain] theme=... round=...`.

## Para o Hermes (linguagem natural)

- *"Joga telefone sem fio"* → `telefone-sem-fio.sh`
- *"Joga fui ao mercado"* → `fui-ao-mercado.sh`
- *"Joga fui à feira"* → `LOJA=feira fui-ao-mercado.sh`

Todos usam o mesmo modelo; só muda o tema e a regra de incremento.
