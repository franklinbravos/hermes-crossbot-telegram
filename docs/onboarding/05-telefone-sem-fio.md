# Telefone sem fio — Teste de comunicação cross-bot

> **Brincadeira + benchmark oficial.** Use após deploy ou quando quiser medir performance.

## Comando rápido

**Antes de rodar:** configure o roster com profiles **reais** (pastas em `~/.hermes/profiles/`):

```bash
chmod +x scripts/configure-crossbot.sh scripts/telefone-sem-fio.sh
./scripts/configure-crossbot.sh
```

Na raiz do repositório (ou após `git pull`):

```bash
PHRASE="O rato roeu" ./scripts/telefone-sem-fio.sh
```

Com orchestrator explícito (só se quiser sobrescrever o bot que está iniciando):

```bash
ORCHESTRATOR=outro-profile PHRASE="GATO BONITO" ./scripts/telefone-sem-fio.sh
```

**Detecção automática do orchestrator** (quando `ORCHESTRATOR` não é passado):

1. `CROSSBOT_BOT_NAME` — bot/profile que executa o script
2. `HERMES_HOME` — profile isolado (`~/.hermes/profiles/<nome>/`)
3. `~/.hermes/active_profile` — profile sticky do Hermes
4. campo `orchestrator` no `topic-map.json` (gravado pelo `configure-crossbot.sh`)

Ou seja: se o **profile orquestrador** pedir e rodar o script no contexto dele, o orchestrator será detectado automaticamente — sem precisar passar variável.

O script lê o **roster** de `topic-map.json` (todos os profiles exceto o orchestrator detectado), sorteia o primeiro jogador e dispara o `crossbot_send`.

> **Não use placeholders** (`ops`, `agent-alpha`…) no `topic-map.json`. O assignee da task Kanban é o **nome da pasta do profile** — se não existir, o worker nunca sobe.

**Pré-requisitos:**
- `./scripts/configure-crossbot.sh` — roster alinhado ao ambiente
- `./scripts/setup-crossbot-board.sh` — board Kanban para acordar workers

**Erros comuns:**
- `topic-map lists profiles that do not exist` → rode `configure-crossbot.sh`
- `unable to open database file` → board não existe; rode `setup-crossbot-board.sh`

**Frase para pedir ao bot orchestrator no chat:**

> Roda telefone sem fio: `PHRASE="O rato roeu" ~/crossbot/scripts/telefone-sem-fio.sh`

**Acompanhar:**

```bash
tail -f ~/.hermes/logs/crossbot/crossbot-audit.jsonl | grep TelefoneSemFio
```

---

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
