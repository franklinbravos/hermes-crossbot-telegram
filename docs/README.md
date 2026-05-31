# Documentação — Hermes Community Plugins

Guia central para humanos e agentes Hermes que usam **multi-agent-context** + **kanban-context** (cross-bot).

## Comece aqui

| Público | Documento | O que você encontra |
|---------|-----------|---------------------|
| **Humano (DevOps / gestor)** | [Como funciona](./onboarding/01-como-funciona.md) | Visão geral em linguagem simples |
| **Humano (setup)** | [Setup passo a passo](./onboarding/02-setup-novo-projeto.md) | Instalar do zero em um projeto novo |
| **Humano (Telegram)** | [Tópicos e grupo](./onboarding/03-topicos-telegram.md) | Fórum, topic-map, visibilidade |
| **Agente Hermes (bot)** | [Guia do agente](./onboarding/04-guia-agente-hermes.md) | Regras de comunicação — **leia isto** |
| **Teste cross-bot** | [Telefone sem fio](./onboarding/05-telefone-sem-fio.md) | Brincadeira + benchmark oficial |
| **Copiar para SOUL/instructions** | [Prompt do agente](./onboarding/AGENT-SYSTEM-PROMPT.md) | Bloco pronto para colar no perfil |

## Referência técnica

| Documento | Conteúdo |
|-----------|----------|
| [Feature Map](./reference/FEATURE-MAP.md) | Fluxos end-to-end ligados ao código |
| [Debug cross-bot](./reference/debug-crossbot.md) | Checklist, env vars, audit log |
| [topic-map.example.json](./reference/topic-map.example.json) | Modelo de mapeamento bot → tópico |

## Plugins

| Plugin | README |
|--------|--------|
| kanban-context | [../kanban-context/README.md](../kanban-context/README.md) |
| multi-agent-context | [../multi-agent-context/README.md](../multi-agent-context/README.md) |
| async-delegate | [../async-delegate/README.md](../async-delegate/README.md) |

## Arquivo (histórico de debug)

Relatórios de sessões de teste e sagas técnicas — **não use como guia operacional**:

- [archive/crossbot-v220-reply-threading.md](./archive/crossbot-v220-reply-threading.md)
- [archive/crossbot-v223-deploy-validation.md](./archive/crossbot-v223-deploy-validation.md)

---

**Versão atual do cross-bot:** kanban-context **v2.2.4**  
**Repositório:** [franklinbravos/hermes-community-plugins](https://github.com/franklinbravos/hermes-community-plugins)
