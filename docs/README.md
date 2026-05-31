# Documentação — Hermes Community Plugins

Guia para operadores humanos e agentes Hermes (**multi-agent-context** + **kanban-context**).

## Handoff de deploy (operador / DevOps)

**Frase para enviar ao agente operador:**

> Execute `docs/onboarding/HANDOFF-DEPLOY.md` do início ao fim e me envie o feedback do template final.

Documento: **[HANDOFF-DEPLOY.md](./onboarding/HANDOFF-DEPLOY.md)** — pull, deploy, smoke test, telefone sem fio, template de retorno.

---

## Onboarding

| Público | Documento |
|---------|-----------|
| Visão geral | [Como funciona](./onboarding/01-como-funciona.md) |
| Setup do zero | [Setup passo a passo](./onboarding/02-setup-novo-projeto.md) |
| Tópicos Telegram | [Tópicos e grupo](./onboarding/03-topicos-telegram.md) |
| Agentes AI | [Guia do agente](./onboarding/04-guia-agente-hermes.md) |
| Teste benchmark | [Telefone sem fio](./onboarding/05-telefone-sem-fio.md) |
| SOUL / prompt | [AGENT-SYSTEM-PROMPT.md](./onboarding/AGENT-SYSTEM-PROMPT.md) |

## Referência

| Documento | Conteúdo |
|-----------|----------|
| [Feature Map](./reference/FEATURE-MAP.md) | Fluxos ↔ código |
| [Debug cross-bot](./reference/debug-crossbot.md) | Checklist, env vars |
| [topic-map.example.json](./reference/topic-map.example.json) | Modelo de config |

## Plugins

| Plugin | README |
|--------|--------|
| kanban-context | [../kanban-context/README.md](../kanban-context/README.md) |
| multi-agent-context | [../multi-agent-context/README.md](../multi-agent-context/README.md) |
| async-delegate | [../async-delegate/README.md](../async-delegate/README.md) |

## Arquivo

Relatórios históricos de sessões — **não operacional**: [archive/](./archive/)

---

**Cross-bot:** kanban-context **v2.2.4+**
