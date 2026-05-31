# kanban-context 🗂️

Kanban activity injection + **cross-bot messaging** com visibilidade Telegram.

**Versão:** 2.2.4 | **Python:** 3.11+ | **Hermes:** v0.13+

## O que faz

| Feature | Descrição |
|---------|-----------|
| Kanban context | Injeta `[Recent Kanban Activity]` antes de cada LLM call |
| Cross-bot outbox | Bots se comunicam via SQLite compartilhado |
| Telegram visibility | 📤/📥 espelhados no grupo fórum (token por bot) |
| Kanban dispatch | Tasks `[Cross-Bot #N]` acordam workers |
| `/kanban-status` | Dashboard de saúde do plugin |

## Dependência

**multi-agent-context** é obrigatório para cross-bot (DB compartilhado).

## Instalação rápida

```bash
cp -r kanban-context ~/.hermes/plugins/kanban-context
```

```yaml
# config.yaml
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

→ Setup completo: [../docs/onboarding/02-setup-novo-projeto.md](../docs/onboarding/02-setup-novo-projeto.md)

## Cross-bot — uso

### Gateway (tools disponíveis)

```
crossbot_send(to_bot="bravo", subject="...", body="...")
crossbot_respond(outbox_id=71, response_text="...")
```

### Worker Kanban (terminal obrigatório)

```bash
CROSSBOT_BOT_NAME=bravo python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond 71 "OK"
```

→ Guia do agente: [../docs/onboarding/04-guia-agente-hermes.md](../docs/onboarding/04-guia-agente-hermes.md)

## Configuração

| Arquivo | Função |
|---------|--------|
| `topic-map.json` | Bot → tópico Telegram + handle |
| `visibility-config.json` | Chat ID do grupo de visibilidade |
| `crossbot_cli.py` | CLI para workers |

| Env var | Descrição |
|---------|-----------|
| `CROSSBOT_BOT_NAME` | Nome deste bot no barramento |
| `MULTI_AGENT_TG_DB_PATH` | SQLite compartilhado |
| `CROSSBOT_VISIBILITY_CHAT` | Chat ID Telegram |
| `CROSSBOT_KANBAN_BOARD` | Board dispatch (default `linkedin-content`) |

## Documentação

- [Como funciona](../docs/onboarding/01-como-funciona.md)
- [Tópicos Telegram](../docs/onboarding/03-topicos-telegram.md)
- [Debug](../docs/reference/debug-crossbot.md)
