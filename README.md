# Crossbot — Telegram bot-to-bot messaging for Hermes

> 🇺🇸 **English** · 🇧🇷 [Português](./README.pt-BR.md)

A Hermes plugin for **bots to talk to each other on Telegram** — shared history, outbox, Kanban, mention relay (`@colleague`), and group visibility.

**Version:** 0.6.0  
**Requirements:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.13+ · Python 3.11+ · stdlib only

---

## Guided Onboarding

Step-by-step **numbered** installation (steps 1–10) with **automatic validation** at each gate. The Hermes agent or an operator follows the current step; it **does not advance** until the verifier gives OK (outbox, audit, Kanban, config).

**How to start:**

```bash
git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git ~/hermes-crossbot-telegram
cd ~/hermes-crossbot-telegram
./scripts/crossbot-onboarding.sh start
./scripts/crossbot-onboarding.sh current
./scripts/crossbot-onboarding.sh verify --watch 120
./scripts/crossbot-onboarding.sh advance   # only after verify OK
```

Full docs: [docs/onboarding/00-onboarding-guiado.md](./docs/onboarding/00-onboarding-guiado.md)

**If stuck on a step:**

| Situation | What to do |
|-----------|------------|
| Don't know which step | `./scripts/crossbot-onboarding.sh status` |
| Step won't pass verify | `./scripts/crossbot-onboarding.sh current` — read `failure_hints`; **do not skip** |
| Need to send evidence to dev | `./scripts/crossbot-debug-pack.sh pack` (or `-r ROUND`) |
| Kanban worker / benchmark stuck | Wait up to **180s**; check task `blocked` |
| Want to restart | `./scripts/crossbot-onboarding.sh reset` |

**Do not:** advance without `verify` OK; ask for a manual report instead of debug-pack; run `crossbot_cli` inside a Kanban worker (terminal is usually blocked).

Symptom → step: [debug-crossbot.md](./docs/reference/debug-crossbot.md)

---

## For Hermes — copy and paste

Send this to the bot that has terminal access (no need to explain the technical details):

```
I need you to install crossbot on this server — it's the plugin that lets bots talk to each other on Telegram.

Clone the project from GitHub (franklinbravos/hermes-crossbot-telegram), run the full installation, and execute the guided onboarding through step 10. Do not declare success until crossbot-onboarding.sh status shows all steps passed.

If an older version already exists (kanban-context or multi-agent-context), clean it up and keep only crossbot.

When done, tell me whether it succeeded, which bots were configured, and whether the gateway restarted.

bash -c 'set -euo pipefail; CB="${CROSSBOT_HOME:-$HOME/hermes-crossbot-telegram}"; if [ -d "$CB/.git" ]; then git -C "$CB" pull --ff-only; else git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git "$CB"; fi; chmod +x "$CB"/scripts/*.sh "$CB"/scripts/lib/*.sh; "$CB"/scripts/bootstrap.sh --yes --onboarding'
```

More ready-to-use messages (update, test, auto-update): [HERMES-INSTALL-PROMPT.md](./docs/onboarding/HERMES-INSTALL-PROMPT.md)

---

## Manual installation (terminal)

```bash
git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git ~/hermes-crossbot-telegram
cd ~/hermes-crossbot-telegram
./scripts/bootstrap.sh --yes
```

With known chat_id and roster:

```bash
./scripts/bootstrap.sh --yes \
  --chat-id -100XXXXXXXXXX \
  --orchestrator coordinator \
  --players agent-a,agent-b
```

---

## Auto-update

```bash
~/hermes-crossbot-telegram/scripts/setup-auto-update-cron.sh   # daily cron
~/hermes-crossbot-telegram/scripts/auto-update.sh --restart    # manual
```

Auto-update does `git pull`, reinstalls the plugin, migrates legacy data, and optionally restarts the gateway. Logs: `~/.hermes/logs/crossbot/auto-update.log`.

---

## What it does

| Problem | Crossbot solution |
|---------|-------------------|
| Bots can't see other bots' messages | SQLite outbox + Kanban |
| Operator can't see bot-to-bot exchanges | 📤/📥 mirror on Telegram |
| Complex delegation | Mention `@handle_colleague` in reply |
| Two legacy plugins | **One plugin** — `crossbot` |

Incorporates **kanban-context** (Franklin Bravos) and **multi-agent-context** (Kaishi). → [ATTRIBUTION.md](./plugins/crossbot/ATTRIBUTION.md)

---

## Testing

```bash
~/hermes-crossbot-telegram/scripts/fui-ao-mercado.sh
~/hermes-crossbot-telegram/scripts/benchmark-report.sh
```

→ [docs/onboarding/05-benchmark-cadeia.md](./docs/onboarding/05-benchmark-cadeia.md)

---

## Scripts

| Script | Function |
|--------|----------|
| `bootstrap.sh` | **Full installation** (migrate + install + configure + board + restart) |
| `install.sh` | Copy plugin only (+ migrate if `cross-bot`) |
| `auto-update.sh` | Pull + reinstall + migrate |
| `setup-auto-update-cron.sh` | Schedule daily cron |
| `configure-crossbot.sh` | topic-map + CROSSBOT_BOT_NAME |
| `benchmark-chain.sh` | Unified engine (cumulative chain) |
| `fui-ao-mercado.sh` | Market theme benchmark (+1 item) |
| `telefone-sem-fio.sh` | Telephone theme benchmark (+2 words) |
| `benchmark-report.sh` | Total time and success rate |
| `crossbot-debug-pack.sh` | Debug mode — factual zip for dev |
| `crossbot-onboarding.sh` | **Guided onboarding** — steps 1–10 with gates |

---

## Documentation

| Guide | Link |
|-------|------|
| **Guided onboarding (1–10)** | [00-onboarding-guiado.md](./docs/onboarding/00-onboarding-guiado.md) |
| Installation (copy to Hermes) | [HERMES-INSTALL-PROMPT.md](./docs/onboarding/HERMES-INSTALL-PROMPT.md) |
| Install and customize | [02-instalar-e-adaptar.md](./docs/onboarding/02-instalar-e-adaptar.md) |
| Workspace and colleagues | [03-workspace-e-colegas.md](./docs/onboarding/03-workspace-e-colegas.md) |
| Debug | [debug-crossbot.md](./docs/reference/debug-crossbot.md) |
| Hub | [docs/README.md](./docs/README.md) |

---

## Migration from legacy plugins

**bootstrap** and **install.sh cross-bot** automatically remove:

- `~/.hermes/plugins/kanban-context` and `multi-agent-context`
- Legacy symlinks in `profiles/*/plugins/`
- Legacy entries in `config.yaml` → replaced by `crossbot`
- `.env`: adds `CROSSBOT_BOT_NAME` and `CROSSBOT_DB_PATH` if missing

Old repo `hermes-community-plugins` → rename remote to `hermes-crossbot-telegram` or clone fresh into `~/hermes-crossbot-telegram`.

---

## License

MIT
