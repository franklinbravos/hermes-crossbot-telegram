# kanban-context 🗂️

Kanban activity injection + **cross-bot messaging** com visibilidade Telegram.

**Versão:** 2.3.0 | **Python:** 3.11+ | **Hermes:** v0.13+

## Instalação

```bash
# Na raiz do repositório
./scripts/install.sh cross-bot
```

Ou manualmente: `cp -r plugins/kanban-context ~/.hermes/plugins/kanban-context`

## Dependência

**multi-agent-context** é obrigatório para cross-bot.

## Cross-bot — worker

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond OUTBOX_ID "OK"
```

## Configuração

| Arquivo | Função |
|---------|--------|
| `topic-map.json` | Profile → tópico Telegram |
| `visibility-config.json` | Chat ID do grupo |
| `crossbot_cli.py` | CLI para workers Kanban |

## Documentação

- [Setup](../../docs/onboarding/02-setup-novo-projeto.md)
- [Guia do agente](../../docs/onboarding/04-guia-agente-hermes.md)
- [Debug](../../docs/reference/debug-crossbot.md)
