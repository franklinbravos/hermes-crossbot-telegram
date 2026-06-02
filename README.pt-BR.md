# Crossbot — Telegram mensagem bot-to-bot para Hermes

> **Leia também em:** [English](./README.md)

Plugin Hermes para **bots conversarem entre si no Telegram** — histórico compartilhado, outbox, Kanban, mention relay (`@colega`) e visibilidade no grupo.

**Versão:** 0.5.2 *(pré-release — v1.0 após validação em produção)*  
**Requisitos:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.13+ · Python 3.11+ · stdlib only

---

## Onboarding guiado

Instalação passo a passo **numerada** (etapas 1–10) com **validação automática** em cada gate. O agente Hermes ou um operador segue a etapa atual; **não avança** até o verificador dar OK (outbox, audit, Kanban, config).

**Como iniciar:**

```bash
git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git ~/hermes-crossbot-telegram
cd ~/hermes-crossbot-telegram
./scripts/crossbot-onboarding.sh start
./scripts/crossbot-onboarding.sh current
./scripts/crossbot-onboarding.sh verify --watch 120
./scripts/crossbot-onboarding.sh advance   # só após verify OK
```

Doc completa: [docs/onboarding/00-onboarding-guiado.md](./docs/onboarding/00-onboarding-guiado.md)

**Se travar numa etapa:**

| Situação | O que fazer |
|----------|-------------|
| Não sabe em qual etapa está | `./scripts/crossbot-onboarding.sh status` |
| Etapa não passa no verify | `./scripts/crossbot-onboarding.sh current` — ler `failure_hints`; **não pule** |
| Precisa enviar evidência ao dev | `./scripts/crossbot-debug-pack.sh pack` (ou `-r ROUND`) |
| Worker Kanban / benchmark parado | Aguardar até **180s**; verificar task `blocked` |
| Quer recomeçar | `./scripts/crossbot-onboarding.sh reset` |

**Não faça:** avançar sem `verify` OK; pedir relatório manual em vez do debug-pack; rodar `crossbot_cli` no worker Kanban (terminal costuma ser bloqueado).

Sintoma → etapa: [debug-crossbot.md](./docs/reference/debug-crossbot.md)

---

## Para o Hermes — copie e cole

Mande isso no chat do bot que tem terminal (não precisa explicar técnico):

```
Preciso que você instale o crossbot aqui no servidor — é o plugin que faz os bots conversarem entre si no Telegram.

Baixe o projeto do GitHub (franklinbravos/hermes-crossbot-telegram), rode a instalação completa e execute o onboarding guiado até a etapa 10. Não declare sucesso até crossbot-onboarding.sh status mostrar todas as etapas passed.

Se já existia a versão antiga (kanban-context ou multi-agent-context), limpe isso e deixe só o crossbot.

No final me diga se deu certo, quais bots foram configurados e se o gateway reiniciou.

bash -c 'set -euo pipefail; CB="${CROSSBOT_HOME:-$HOME/hermes-crossbot-telegram}"; if [ -d "$CB/.git" ]; then git -C "$CB" pull --ff-only; else git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git "$CB"; fi; chmod +x "$CB"/scripts/*.sh "$CB"/scripts/lib/*.sh; "$CB"/scripts/bootstrap.sh --yes --onboarding'
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
~/hermes-crossbot-telegram/scripts/fui-ao-mercado.sh
~/hermes-crossbot-telegram/scripts/benchmark-report.sh
```

→ [docs/onboarding/05-benchmark-cadeia.md](./docs/onboarding/05-benchmark-cadeia.md)

---

## Scripts

| Script | Função |
|--------|--------|
| `bootstrap.sh` | **Instalação completa** (migrate + install + configure + board + restart) |
| `install.sh` | Só copia plugin (+ migrate se `cross-bot`) |
| `auto-update.sh` | Pull + reinstall + migrate |
| `setup-auto-update-cron.sh` | Agenda cron diário |
| `configure-crossbot.sh` | topic-map + CROSSBOT_BOT_NAME |
| `benchmark-chain.sh` | Motor unificado (cadeia cumulativa) |
| `fui-ao-mercado.sh` | Benchmark tema mercado/feira (+1 item) |
| `telefone-sem-fio.sh` | Benchmark tema telefone (+2 palavras) |
| `benchmark-report.sh` | Tempo total e % sucesso |
| `crossbot-debug-pack.sh` | Modo debug — zip factual para enviar ao dev |
| `crossbot-onboarding.sh` | **Onboarding guiado** — etapas 1–10 com gates |

---

## Documentação

| Guia | Link |
|------|------|
| **Onboarding guiado (1–10)** | [00-onboarding-guiado.md](./docs/onboarding/00-onboarding-guiado.md) |
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
