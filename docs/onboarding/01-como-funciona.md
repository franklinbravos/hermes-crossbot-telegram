# Como funciona — Cross-Bot Hermes

> Para humanos que querem entender o sistema sem ler código.

## O problema que resolvemos

No Telegram, **bots não veem mensagens de outros bots**. Se você tem Matias (DevOps), Bravo (site), CRM-Fast etc., cada um vive numa bolha — não conseguem conversar pela API normal do Telegram.

Além disso, humanos precisam **ver** o que os bots estão trocando entre si, sem adivinhar pelo Kanban.

## A solução em uma frase

Dois plugins trabalham juntos:

1. **multi-agent-context** — banco SQLite compartilhado com histórico do grupo
2. **kanban-context** — fila de mensagens (`outbox`) + espelho no Telegram + dispatch via Kanban

```
┌─────────────┐     outbox SQLite      ┌─────────────┐
│   Matias    │ ─────────────────────► │    Bravo    │
│  (envia)    │   + task Kanban        │  (worker)   │
└──────┬──────┘                        └──────┬──────┘
       │                                      │
       │         Grupo Telegram               │
       └──────────► 📤 Matias enviou          │
                  ◄── 📥 Bravo respondeu ─────┘
                         (cada um com seu bot)
```

## Fluxo completo (passo a passo)

### 1. Matias envia uma mensagem cross-bot

Matias chama `crossbot_send(to_bot="bravo", subject="...", body="...")`.

O plugin faz três coisas:

| Ação | Onde | Para quê |
|------|------|----------|
| Grava na `outbox` | `~/.hermes/data/multi_agent_tg_shared.db` | Bravo vai ler isto |
| Cria task no Kanban | board `linkedin-content` (configurável) | Dispatcher acorda o worker do Bravo |
| Posta 📤 no Telegram | Grupo de visibilidade, tópico do Bravo | Você vê que Matias pediu algo |

### 2. Dispatcher Kanban spawna o worker

A cada ~60 segundos o dispatcher olha o board. Vê uma task `[Cross-Bot #N]` assignada ao `bravo` e inicia uma sessão worker isolada.

O body da task contém a mensagem **e** instruções obrigatórias de como responder.

### 3. Worker do Bravo processa

O worker recebe no contexto:

```
[Pending Messages]
- ID #66 [2m ago] From matias — Status do site
  > O site está no ar?
```

Ele lê, executa (curl, verificação, etc.) e **deve responder antes** de `kanban_complete`.

### 4. Bravo responde

Via terminal (workers não têm a tool `crossbot_respond`):

```bash
CROSSBOT_BOT_NAME=bravo python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond 66 "Site online, HTTP 200"
```

O plugin:

- Marca outbox como `done`
- Posta 📥 no Telegram **com o token do Bravo** — aparece como Bravo, não Matias

### 5. Você acompanha no grupo

Cada bot posta no **seu tópico** do fórum Telegram (configurado em `topic-map.json`):

| Direção | Quem aparece no Telegram | Onde |
|---------|--------------------------|------|
| 📤 envio | Bot remetente (ex: Matias) | Tópico do destinatário |
| 📥 resposta | Bot respondedor (ex: Bravo) | Tópico do respondedor |

## O que cada peça faz

| Peça | Função |
|------|--------|
| **outbox** | Fila de mensagens entre bots (SQLite) |
| **Kanban task** | Acorda o bot certo via worker |
| **topic-map.json** | Mapeia `bravo` → tópico 637, handle `@bravos_consult_bot` |
| **visibility-config.json** | Chat ID do grupo, token fallback |
| **crossbot_cli.py** | CLI para workers responderem (workaround Bug Hermes #3) |
| **Audit log** | `~/.hermes/logs/kanban-context/crossbot-audit.jsonl` |

## O que NÃO é cross-bot

| Situação | Comportamento |
|----------|---------------|
| Você manda `@Bravo o site está no ar?` no grupo | Bravo responde no chat normal — **não** passa pela outbox |
| Bot A comenta no Kanban | Atividade Kanban injetada no contexto — **não** é mensagem cross-bot |
| DM entre bot e Franklin | Canal separado — cross-bot é **bot → bot** via outbox |

## Trade-offs importantes (v2.2.4)

| Decisão | Por quê |
|---------|---------|
| Cada bot posta com **seu próprio token** | Telegram mostra o remetente correto (Bravo ≠ Matias) |
| Sem `reply_to` entre bots diferentes | API Telegram não permite bot A citar mensagem de bot B |
| Workers usam **terminal + crossbot_cli** | Hermes core não expõe tools de plugin nos workers Kanban |

## Próximo passo

→ [Setup passo a passo](./02-setup-novo-projeto.md) para instalar em um projeto novo.
