# multi-agent-context 🤝

Injeta histórico compartilhado de canal/grupo no contexto do agente — para bots **ouvirem** uns aos outros sem loop infinito.

**Versão:** 2.0+ | **Python:** 3.11+

## O que faz

| Plataforma | Mecanismo |
|------------|-----------|
| **Discord** | REST API — busca últimas N mensagens do canal/thread |
| **Telegram** | SQLite WAL compartilhado — cada bot grava e lê turns |

Resultado: agente vê `[Recent Group History]` ou `[Recent Channel History]` no `pre_llm_call`, mas só **responde** quando trigger normal (menção, keyword, etc.).

## Por que é obrigatório para cross-bot

O **kanban-context** usa o mesmo SQLite (`multi_agent_tg_shared.db`) para a tabela `outbox`. Sem este plugin, cada profile teria DB isolado e mensagens cross-bot não chegariam.

## Instalação

```bash
cp -r multi-agent-context ~/.hermes/plugins/multi-agent-context
```

```yaml
plugins:
  enabled:
    - multi-agent-context
```

## Configuração

| Variável | Default | Descrição |
|----------|---------|-----------|
| `MULTI_AGENT_TG_DB_PATH` | `~/.hermes/data/multi_agent_tg_shared.db` | **Crítico:** mesmo path em todos os profiles |
| `MULTI_AGENT_HISTORY_COUNT` | `20` | Mensagens injetadas no contexto |
| `MULTI_AGENT_BOT_NAME` | *(profile)* | Nome deste bot no histórico Telegram |
| `DISCORD_BOT_TOKEN` | auto | Discord (se usar) |

## Hooks

| Hook | Plataforma | Função |
|------|------------|--------|
| `pre_llm_call` | Discord + Telegram | Injeta histórico |
| `post_llm_call` | Telegram | Persiste turn no SQLite |

## Documentação

- [Setup novo projeto](../docs/onboarding/02-setup-novo-projeto.md)
- [Tópicos e comunicação](../docs/onboarding/03-topicos-telegram.md)
