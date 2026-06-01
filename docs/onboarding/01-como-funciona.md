# Como funciona — Cross-Bot Hermes

> Para humanos que querem entender o sistema sem ler código.

## O problema que resolvemos

No Telegram, **bots não veem mensagens de outros bots**. Num ecossistema com vários agentes (DevOps, web, CRM, etc.), cada um vive numa bolha — não conseguem conversar pela API normal do Telegram.

Além disso, operadores humanos precisam **ver** o que os bots trocam entre si, sem adivinhar pelo Kanban.

## A solução em uma frase

Um plugin unificado — **crossbot** — com histórico compartilhado, fila `outbox`, dispatch Kanban e visibilidade Telegram.

(Incorpora as funcionalidades de `multi-agent-context` e `kanban-context`; ver [ATTRIBUTION.md](../../plugins/crossbot/ATTRIBUTION.md).)

```
┌─────────────┐     outbox SQLite      ┌─────────────┐
│  Bot A      │ ─────────────────────► │  Bot B      │
│  (envia)    │   + task Kanban        │  (worker)   │
└──────┬──────┘                        └──────┬──────┘
       │                                      │
       │         Grupo Telegram               │
       └──────────► "@bot2 faz X"             │
                  ◄── resposta (reply ou ↩) ─┘
```

## Fluxo principal (v0.5 — Mention Relay, pré-release)

### 1. Bot A delega mencionando @colega

Na resposta normal ao humano, o bot escreve algo como `@bot_vendas prepara proposta para cliente X`.

| Ação | Onde | Para quê |
|------|------|----------|
| Plugin detecta @mention | hook `post_llm_call` | Sem CLI nem tool manual |
| Grava na `outbox` | SQLite compartilhado | Bot B vai ler |
| Cria task Kanban | board configurável | Dispatcher acorda worker |
| Posta 📤 no Telegram | Grupo de visibilidade | Operador humano vê o envio |

**Não é necessário** `crossbot_send` nem `crossbot_cli` para o caso comum.

### 2. Dispatcher spawna worker do Bot B

Task `[Cross-Bot #N]` assignada ao profile destino.

### 3. Worker processa

Contexto inclui `[Pending Messages]` com a mensagem do colega. Instrução curta: **responda naturalmente**.

### 4. Bot B responde naturalmente

Ao terminar o turno, o plugin chama `crossbot_respond` automaticamente — marca outbox `done` e publica no Telegram.

### 5. Visibilidade no grupo

| Direção | Quem aparece | Reply |
|---------|--------------|-------|
| 📤 envio | Bot remetente | — |
| 📥 resposta | Bot respondedor | **Reply real** se o Telegram aceitar; senão **citação simulada** (↩ @handle + blockquote) |

## Fluxo alternativo (avancado)

Para telefone-sem-fio, debug ou integrações explícitas, ainda existem:

- `crossbot_send()` / tool `crossbot_send`
- `crossbot_cli.py send|respond`

## Peças do sistema

| Peça | Função |
|------|--------|
| **outbox** | Fila SQLite entre bots |
| **Kanban task** | Acorda o bot certo |
| **topic-map.json** | Profile → tópico + handle Telegram |
| **post_llm_call** | Relay de @mention + auto-resposta do worker |
| **crossbot_cli.py** | Fallback CLI (sem tool no toolset do worker) |
| **Audit log** | `~/.hermes/logs/crossbot/crossbot-audit.jsonl` |

## Trade-offs (v0.5.0, pré-release)

| Decisão | Motivo |
|---------|--------|
| @mention como caminho principal | Fluxo natural para agentes e humanos |
| Token por profile na visibilidade | Remetente correto no Telegram |
| Reply real → citação simulada | Limitação da API Telegram entre tokens de bots |
| Workers respondem sem CLI | Plugin completa outbox no `post_llm_call` |

## Pré-requisitos humanos (obrigatórios)

| Item | Detalhe |
|------|---------|
| **Workspace** fórum Telegram com tópico por agente | [03-workspace-e-colegas.md](./03-workspace-e-colegas.md) |
| **Mapa de colegas** no SOUL de cada bot | profile, @, tópico, função |
| **`topic-map.json`** alinhado aos profiles existentes | Não exige nomes padronizados |

Não é necessário criar agentes novos se o ambiente já os tem — só **inventariar e adequar**.

→ [Onboarding — adaptar ambiente existente](./02-instalar-e-adaptar.md#caminho-a--adaptar-ambiente-existente)
