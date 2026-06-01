# crossbot — Telegram mensagem bot-to-bot

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

→ Atribuição completa: [ATTRIBUTION.md](./ATTRIBUTION.md)

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
| `topic-map.json` | Profiles, handles e tópicos |

## CLI (fallback workers)

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/crossbot/crossbot_cli.py respond OUTBOX_ID "resposta"
```

## Documentação

- [Como funciona](../../docs/onboarding/01-como-funciona.md)
- [Debug](../../docs/reference/debug-crossbot.md)
