# Hermes Community Plugins 🎭

Battle-tested plugins for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — **zero core patches required**.

## Documentação

**Novo projeto?** Comece aqui:

| Guia | Para quem |
|------|-----------|
| [📖 Hub de docs](./docs/README.md) | Índice completo |
| [Como funciona](./docs/onboarding/01-como-funciona.md) | Humanos — visão geral cross-bot |
| [Setup passo a passo](./docs/onboarding/02-setup-novo-projeto.md) | DevOps — instalar do zero |
| [Tópicos Telegram](./docs/onboarding/03-topicos-telegram.md) | Estrutura do grupo fórum |
| [Guia do agente](./docs/onboarding/04-guia-agente-hermes.md) | **Bots Hermes** — como se comunicar |
| [Telefone sem fio](./docs/onboarding/05-telefone-sem-fio.md) | Teste oficial + benchmark cross-bot |
| [Prompt para SOUL](./docs/onboarding/AGENT-SYSTEM-PROMPT.md) | Bloco pronto para colar no perfil |

---

## Plugins

### [`kanban-context/`](./kanban-context/) 🗂️ — Cross-bot + Kanban

Injeta atividade Kanban no contexto e implementa **barramento de mensagens entre bots** via SQLite outbox, com espelho 📤/📥 no Telegram.

**Stack cross-bot:** `kanban-context` + `multi-agent-context` (obrigatório)

**Versão atual:** 2.2.4 — cada bot posta visibilidade com seu próprio token Telegram.

→ [README](./kanban-context/README.md) | [Setup](./docs/onboarding/02-setup-novo-projeto.md)

---

### [`multi-agent-context/`](./multi-agent-context/) 🤝 — Histórico compartilhado

Bots veem o que outros disseram no Telegram (SQLite WAL) ou Discord (REST API), sem `trigger: all` loops.

→ [README](./multi-agent-context/README.md)

---

### [`async-delegate/`](./async-delegate/) 🚀 — Tarefas em background

Spawn subagentes em background sem bloquear o turno atual. Notificação automática ao concluir (queue ou steer).

→ [README](./async-delegate/README.md)

---

## Quick install (cross-bot)

```bash
git clone https://github.com/franklinbravos/hermes-community-plugins.git
cp -r hermes-community-plugins/kanban-context ~/.hermes/plugins/kanban-context
cp -r hermes-community-plugins/multi-agent-context ~/.hermes/plugins/multi-agent-context
```

Habilite em cada profile `config.yaml`:

```yaml
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

Configure `MULTI_AGENT_TG_DB_PATH`, `topic-map.json`, `visibility-config.json` — ver [setup completo](./docs/onboarding/02-setup-novo-projeto.md).

---

## Requirements

- Hermes Agent **v0.13+**
- Python **3.11+**
- Stdlib only (sem dependências extras nos plugins principais)

## Multi-profile deployment

```bash
for bot in matias bravo catalogai; do
  mkdir -p ~/.hermes/profiles/${bot}/plugins
  ln -sf ~/.hermes/plugins/kanban-context \
          ~/.hermes/profiles/${bot}/plugins/kanban-context
  ln -sf ~/.hermes/plugins/multi-agent-context \
          ~/.hermes/profiles/${bot}/plugins/multi-agent-context
done
```

Habilite plugins no `config.yaml` de **cada** profile.

## License

MIT
