# Crossbot — Telegram mensagem bot-to-bot para Hermes

Plugin Hermes para **bots conversarem entre si no Telegram** — histórico compartilhado, outbox, Kanban, mention relay (`@colega`) e visibilidade no grupo.

**Versão:** 0.5.0 *(pré-release — v1.0 após validação em produção)*  
**Requisitos:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.13+ · Python 3.11+ · stdlib only

---

## Para o Hermes — copie e cole

Mande isso no chat do bot que tem terminal (não precisa explicar técnico):

```
Preciso que você instale o crossbot aqui no servidor — é o plugin que faz os bots conversarem entre si no Telegram.

Baixe o projeto do GitHub (franklinbravos/hermes-crossbot-telegram), rode a instalação completa e não pare no meio. Se já existia a versão antiga (kanban-context ou multi-agent-context), limpe isso e deixe só o crossbot.

No final me diga se deu certo, quais bots foram configurados e se o gateway reiniciou.

bash -c 'set -euo pipefail; CB="${CROSSBOT_HOME:-$HOME/hermes-crossbot-telegram}"; if [ -d "$CB/.git" ]; then git -C "$CB" pull --ff-only; else git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git "$CB"; fi; chmod +x "$CB"/scripts/*.sh "$CB"/scripts/lib/*.sh; "$CB"/scripts/bootstrap.sh --yes'
```

Mais mensagens prontas (atualizar, teste, auto-update): [HERMES-INSTALL-PROMPT.md](./docs/onboarding/HERMES-INSTALL-PROMPT.md)

---

## Instalação manual (terminal)

```bash
git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git ~/hermes-crossbot-telegram
cd ~/hermes-crossbot-telegram
./scripts/bootstrap.sh --yes
```

Com chat_id e roster conhecidos:

```bash
./scripts/bootstrap.sh --yes \
  --chat-id -100XXXXXXXXXX \
  --orchestrator coordenador \
  --players agente-a,agente-b
```

---

## Auto-atualização

```bash
~/hermes-crossbot-telegram/scripts/setup-auto-update-cron.sh   # cron diário
~/hermes-crossbot-telegram/scripts/auto-update.sh --restart    # manual
```

O auto-update faz `git pull`, reinstala o plugin, migra legado e opcionalmente reinicia o gateway. Logs: `~/.hermes/logs/crossbot/auto-update.log`.

---

## O que é

| Problema | Solução crossbot |
|----------|------------------|
| Bots não veem mensagens de outros bots | Outbox SQLite + Kanban |
| Operador não vê trocas entre bots | Espelho 📤/📥 no Telegram |
| Delegação complexa | Mencione `@handle_colega` na resposta |
| Dois plugins antigos | **Um plugin** — `crossbot` |

Incorpora **kanban-context** (Franklin Bravos) e **multi-agent-context** (Kaishi). → [ATTRIBUTION.md](./plugins/crossbot/ATTRIBUTION.md)

---

## Teste

```bash
PHRASE="O rato roeu" ~/hermes-crossbot-telegram/scripts/telefone-sem-fio.sh
```

→ [docs/onboarding/05-telefone-sem-fio.md](./docs/onboarding/05-telefone-sem-fio.md)

---

## Scripts

| Script | Função |
|--------|--------|
| `bootstrap.sh` | **Instalação completa** (migrate + install + configure + board + restart) |
| `install.sh` | Só copia plugin (+ migrate se `cross-bot`) |
| `auto-update.sh` | Pull + reinstall + migrate |
| `setup-auto-update-cron.sh` | Agenda cron diário |
| `configure-crossbot.sh` | topic-map + CROSSBOT_BOT_NAME |
| `telefone-sem-fio.sh` | Benchmark cross-bot |

---

## Documentação

| Guia | Link |
|------|------|
| Instalação (copiar pro Hermes) | [HERMES-INSTALL-PROMPT.md](./docs/onboarding/HERMES-INSTALL-PROMPT.md) |
| Instalar e adaptar | [02-instalar-e-adaptar.md](./docs/onboarding/02-instalar-e-adaptar.md) |
| Workspace e colegas | [03-workspace-e-colegas.md](./docs/onboarding/03-workspace-e-colegas.md) |
| Debug | [debug-crossbot.md](./docs/reference/debug-crossbot.md) |
| Hub | [docs/README.md](./docs/README.md) |

---

## Migração desde plugins antigos

O **bootstrap** e o **install.sh cross-bot** removem automaticamente:

- `~/.hermes/plugins/kanban-context` e `multi-agent-context`
- Symlinks legados em `profiles/*/plugins/`
- Entradas legadas em `config.yaml` → substituídas por `crossbot`
- `.env`: adiciona `CROSSBOT_BOT_NAME` e `CROSSBOT_DB_PATH` se faltarem

Repo antigo `hermes-community-plugins` → renomeie remote para `hermes-crossbot-telegram` ou clone fresh em `~/hermes-crossbot-telegram`.

---

## Licença

MIT
