# Telefone sem fio — Teste de comunicação cross-bot

> **Brincadeira + benchmark oficial.** Use após deploy ou quando quiser medir performance.

## O que é

Percorre todos os agentes via `crossbot_send`. Cada um adiciona **duas palavras** e repassa para outro **aleatório** que ainda não jogou. Quando o roster esgota, a frase volta ao **orchestrator**, que reporta ao operador humano.

- Teste end-to-end (outbox → worker → CLI → próximo bot)
- Prova identidade no Telegram (token por profile)
- Mede latência por salto e da rodada

## Papéis

| Papel | Profile | Função |
|-------|---------|--------|
| **Orchestrator** | ex: `orchestrator` | Inicia, recebe final, reporta |
| **Jogadores** | todos em `topic-map.json` exceto orchestrator | +2 palavras e repassam |
| **Operador humano** | — | Pede o teste e recebe relatório |

### Roster

```
# Exemplo — substitua pelos profiles do seu topic-map.json
ops, agent-alpha, agent-beta, agent-gamma
```

## Formato da mensagem

**Subject:** `[TelefoneSemFio] round=<ID>`

**Body:**

```
TELEFONE_SEM_FIO
round: 20260531-1430
started_at: 2026-05-31T14:30:00Z
phrase: O rato roeu
played: orchestrator
roster: ops,agent-alpha,agent-beta,agent-gamma
next: agent-alpha
hop: 1
```

| Campo | Significado |
|-------|-------------|
| `round` | ID único da rodada |
| `started_at` | ISO 8601 — não altere |
| `phrase` | Frase acumulada |
| `played` | Profiles que já jogaram (vírgula, sem espaços) |
| `roster` | Todos os jogadores |
| `hop` | Número do salto |

## Fluxo

```
Operador: "Roda telefone sem fio"
    → Orchestrator envia ao 1º jogador (sorteado)
    → Cada jogador: +2 palavras → sorteia próximo (não em played)
    → Último jogador → orchestrator com status: COMPLETE
    → Orchestrator reporta frase final + métricas
```

## Orchestrator — iniciar

Ver comandos completos em [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md#5-telefone-sem-fio-benchmark-oficial).

Resumo:

1. Definir `ROUND`, `PHRASE`, `ROSTER`, sortear `FIRST`
2. `crossbot_send` para `FIRST` com body `TELEFONE_SEM_FIO`
3. `played` inicial = orchestrator

## Cada jogador

1. +**exatamente 2 palavras** à `phrase`
2. Adicionar seu profile em `played`
3. `disponíveis = roster - played` → sortear um
4. Se sobrou → `crossbot_send` para ele | Se não → `crossbot_send` para orchestrator com `status: COMPLETE`
5. `crossbot_cli respond` **antes** de `kanban_complete`

**Subject final:** `[TelefoneSemFio] round=ID FINAL`

## Relatório ao operador

```markdown
## Telefone sem fio — round ID

**Frase inicial:** ...
**Frase final:** ...
**Ordem:** ops → agent-alpha → ...
**Duração total:** Xm Ys
**Latência média/salto:** ~Xs
**Status:** ✅ ou ❌
```

Métricas: audit log + `started_at` vs último `crossbot_respond`.

## Checklist

- [ ] Cada hop gerou 📤/📥
- [ ] Nenhum bot repetido em `played`
- [ ] +2 palavras por jogador
- [ ] Outbox final `done`
- [ ] Orchestrator reportou métricas

## Quando usar

| Situação | Usar? |
|----------|-------|
| Deploy / upgrade cross-bot | ✅ |
| Bot novo no roster | ✅ |
| Medir latência | ✅ |
| Tarefa de produção | ❌ |

→ Deploy completo: [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md)
