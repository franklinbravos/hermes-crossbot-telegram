# crossbot — Telegram mensagem bot-to-bot

> 🇧🇷 **Português** · 🇺🇸 [English](./README.md)

Plugin **unificado** para ecossistemas Hermes multi-agente no Telegram.

**Versão:** 0.5.2 *(pré-release — v1.0 após validação em produção)*

## O que faz

| Capacidade | Origem |
|------------|--------|
| Histórico compartilhado do grupo (SQLite) | multi-agent-context (Kaishi) |
| Outbox bot-to-bot + dispatch Kanban | kanban-context (Franklin Bravos) |
| Mention relay (`@colega` na resposta) | kanban-context (mention relay) |
| Visibilidade 📤/📥 no Telegram | kanban-context |
| Coordenação de resposta por tópico | kanban-context |

→ Atribuição completa: [ATTRIBUTION.pt-BR.md](./ATTRIBUTION.pt-BR.md)

## Instalação

```bash
./scripts/install.sh cross-bot   # instala apenas crossbot
```

Habilite em cada profile:

```yaml
plugins:
  enabled:
    - crossbot
```

## Dependências

**Hermes Core + stdlib Python** — sem pacotes pip extras.

## Configuração

| Variável | Descrição |
|----------|-----------|
| `CROSSBOT_BOT_NAME` | Profile deste bot |
| `CROSSBOT_DB_PATH` | SQLite compartilhado (default: `~/.hermes/data/crossbot.db`) |
| `CROSSBOT_VISIBILITY_CHAT` | Grupo Telegram de visibilidade |
| `CROSSBOT_VISIBILITY_TOKEN` | Token do bot para posts de visibilidade |
| `CROSSBOT_VISIBILITY_THREAD` | Topic/thread ID para posts de visibilidade |
| `CROSSBOT_KANBAN_BOARD` | Nome do board kanban (default: `cross-bot`) |
| `CROSSBOT_DISPATCHER_INTERVAL` | Intervalo do mini-dispatcher em segundos (default: `5`) |
| `CROSSBOT_DISPATCHER_ENABLED` | Habilita mini-dispatcher (default: `true`) |
| `CROSSBOT_WARMUP_ENABLED` | Habilita warmup do agente no register (default: `true`) |
| `KANBAN_CONTEXT_EVENT_LIMIT` | Máx. de eventos para injetar como contexto (default: `10`) |
| `KANBAN_CONTEXT_LOOKBACK_H` | Janela de lookback em horas (default: `12`) |
| `topic-map.json` | Profiles, handles e tópicos |

### topic-map.json

```json
{
  "orchestrator": "iago",
  "chat_id": "-1001234567890",
  "topics": {
    "bot_a": 195,
    "bot_b": 303,
    "bot_c": 14
  },
  "handles": {
    "bot_a": "bot_a_handle",
    "bot_b": "bot_b_handle",
    "bot_c": "bot_c_handle"
  }
}
```

### visibility-config.json

```json
{
  "telegram_bot_token": "",
  "visibility_chat_id": "-1001234567890",
  "enabled": true,
  "visibility_thread_id": ""
}
```

## CLI (fallback workers)

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/crossbot/crossbot_cli.py respond OUTBOX_ID "resposta"
```

## Arquitetura

```
Bot A envia → crossbot_send() → outbox (SQLite) + task kanban
                                        ↓
                      Mini-dispatcher (5s) ou Gateway dispatcher (60s)
                                        ↓
              Worker spawnado (hermes chat) → processa → responde
                                        ↓
           crossbot_respond() → fecha outbox → relay ao próximo bot
```

O plugin inclui dois mecanismos de dispatch:
1. **Mini-dispatcher** — thread daemon que polia o board a cada 5s (configurável). Ligado por padrão.
2. **Gateway dispatcher** — dispatcher nativo do Hermes (60s). O plugin tenta auto-ajustar para 10s na carga.

## Tools

| Tool | Descrição |
|------|-----------|
| `crossbot_send` | Envia mensagem para outro profile |
| `crossbot_respond` | Responde a uma mensagem pendente |
| `crossbot_purge` | Remove todos os dados do crossbot para reinstalação limpa |
| `kanban_complete` | Completa task kanban (fecha outbox automaticamente) |

## Hooks

| Hook | Função | Propósito |
|------|--------|-----------|
| `pre_llm_call` | `_inject_kanban_context` | Injeta atividade do board + mensagens pendentes |
| `pre_llm_call` | `_inject_response_coordination` | Previne respostas duplicadas |
| `pre_llm_call` | `_auto_detect_mentions` | Auto-cria tasks em @menções |
| `post_llm_call` | `_post_llm_mention_relay` | Relay de @menções nas respostas do assistente |
| `post_tool_call` | `_on_post_tool_call` | Fecha outbox automaticamente no kanban_complete |

## Documentação

- [Como funciona](../../docs/onboarding/01-como-funciona.md)
- [Debug](../../docs/reference/debug-crossbot.md)
