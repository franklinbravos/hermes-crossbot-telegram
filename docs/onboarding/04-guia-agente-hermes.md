# Guia do agente Hermes — Cross-bot e tópicos

> Para agentes AI no ecossistema multi-bot. Siga à risca.

## Identidade

Você tem um **profile**, **tópico** Telegram, **handle** e acesso ao barramento cross-bot via outbox SQLite.

## Receber trabalho

### Menção no grupo

Operador escreve `@seu_handle ...` → responda no mesmo tópico.

### Cross-bot

```
[Pending Messages]
- ID #71 From ops — Assunto
  > corpo da mensagem
```

→ Processe e responda via crossbot (não só no grupo).

## Responder cross-bot (OBRIGATÓRIO)

Workers Kanban **não** têm tool `crossbot_respond`:

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond OUTBOX_ID "resposta"
```

Ordem: processar → **respond** → kanban_complete

**NUNCA:** `from kanban_context import ...` · só kanban_comment · DM sem pedido

## Enviar cross-bot

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send DESTINO "Assunto" "Corpo"
```

## Telefone sem fio

Subject `[TelefoneSemFio]` ou body `TELEFONE_SEM_FIO`:

1. +2 palavras à phrase
2. Atualize played
3. Sorteie próximo (roster - played)
4. Repasse ou devolva ao orchestrator com `status: COMPLETE`
5. crossbot_cli respond antes de kanban_complete

→ [05-telefone-sem-fio.md](./05-telefone-sem-fio.md)

## Contexto injetado

| Bloco | Significado |
|-------|-------------|
| `[Recent Group History]` | Histórico Telegram |
| `[Recent Kanban Activity]` | Boards |
| `[Pending Messages]` | Cross-bot pendente |
| `[Response Coordination]` | Quem deve falar |

## Fluxograma

```
[Pending Messages]? → crossbot_cli respond → kanban_complete
@mention?           → responder no grupo
Response Coord "don't respond"? → silêncio
Task normal?        → kanban_complete
```

→ SOUL: [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)
