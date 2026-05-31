# Como funciona — Cross-Bot Hermes

> Para humanos que querem entender o sistema sem ler código.

## O problema que resolvemos

No Telegram, **bots não veem mensagens de outros bots**. Num ecossistema com vários agentes (DevOps, web, CRM, etc.), cada um vive numa bolha — não conseguem conversar pela API normal do Telegram.

Além disso, operadores humanos precisam **ver** o que os bots trocam entre si, sem adivinhar pelo Kanban.

## A solução em uma frase

Dois plugins trabalham juntos:

1. **multi-agent-context** — banco SQLite compartilhado com histórico do grupo
2. **kanban-context** — fila de mensagens (`outbox`) + espelho no Telegram + dispatch via Kanban

```
┌─────────────┐     outbox SQLite      ┌─────────────┐
│  Bot A      │ ─────────────────────► │  Bot B      │
│  (envia)    │   + task Kanban        │  (worker)   │
└──────┬──────┘                        └──────┬──────┘
       │                                      │
       │         Grupo Telegram               │
       └──────────► 📤 Bot A enviou           │
                  ◄── 📥 Bot B respondeu ─────┘
                         (cada um com seu bot)
```

## Fluxo completo

### 1. Bot A envia mensagem cross-bot

Chama `crossbot_send(to_bot="agent-beta", subject="...", body="...")`.

| Ação | Onde | Para quê |
|------|------|----------|
| Grava na `outbox` | SQLite compartilhado | Bot B vai ler |
| Cria task Kanban | board configurável | Dispatcher acorda worker |
| Posta 📤 no Telegram | Grupo de visibilidade | Operador humano vê o envio |

### 2. Dispatcher spawna worker do Bot B

Task `[Cross-Bot #N]` assignada ao profile destino.

### 3. Worker processa

Contexto inclui `[Pending Messages]` com outbox_id e instruções.

### 4. Bot B responde

```bash
CROSSBOT_BOT_NAME=agent-beta python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond N "resposta"
```

Marca outbox `done` e posta 📥 com **token do Bot B**.

### 5. Visibilidade no grupo

| Direção | Quem aparece | Onde |
|---------|--------------|------|
| 📤 envio | Bot remetente | Tópico do destinatário |
| 📥 resposta | Bot respondedor | Tópico do respondedor |

## Peças do sistema

| Peça | Função |
|------|--------|
| **outbox** | Fila SQLite entre bots |
| **Kanban task** | Acorda o bot certo |
| **topic-map.json** | Profile → tópico + handle Telegram |
| **crossbot_cli.py** | CLI para workers (sem tool no toolset) |
| **Audit log** | `~/.hermes/logs/kanban-context/crossbot-audit.jsonl` |

## Trade-offs (v2.3.0+)

| Decisão | Motivo |
|---------|--------|
| Token por profile na visibilidade | Remetente correto no Telegram |
| Sem `reply_to` entre bots diferentes | Limitação da API Telegram |
| Workers usam terminal + CLI | Hermes core não herda tools de plugin |

→ [Setup passo a passo](./02-setup-novo-projeto.md)
