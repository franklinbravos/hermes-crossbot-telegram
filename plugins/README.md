# Plugins

Installable packages for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

> 🇺🇸 **English** · 🇧🇷 [Português](./README.pt-BR.md)

Repository: **[hermes-crossbot-telegram](https://github.com/franklinbravos/hermes-crossbot-telegram)**

## Quick Install

```bash
git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git
cd hermes-crossbot-telegram
chmod +x scripts/install.sh
./scripts/install.sh              # crossbot (recommended)
./scripts/install.sh all          # crossbot + async-delegate
./scripts/install.sh async-delegate   # single plugin
```

Target: `~/.hermes/plugins/`

## Bundles

| Bundle | Plugin | When to use |
|--------|--------|-------------|
| **cross-bot** | `crossbot` | Bots talking to each other via Telegram |
| **async-delegate** | `async-delegate` | Background async tasks (optional) |

## Enable in Hermes

```yaml
# config.yaml on each profile
plugins:
  enabled:
    - crossbot
```

Setup guide: [../docs/onboarding/02-instalar-e-adaptar.md](../docs/onboarding/02-instalar-e-adaptar.md)

## Versions

| Plugin | Version |
|--------|---------|
| crossbot | 0.5.2 |
| async-delegate | 1.1.0 |

**Note:** `crossbot` v0.5 unifies `kanban-context` + `multi-agent-context`. v1.0 is the production milestone. See [crossbot/ATTRIBUTION.md](./crossbot/ATTRIBUTION.md).
