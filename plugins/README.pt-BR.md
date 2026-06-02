# Plugins

Pacotes instaláveis para [Hermes Agent](https://github.com/NousResearch/hermes-agent).

> **Leia também em:** [English](./README.md)

Repositório: **[hermes-crossbot-telegram](https://github.com/franklinbravos/hermes-crossbot-telegram)**

## Instalação rápida

```bash
git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git
cd hermes-crossbot-telegram
chmod +x scripts/install.sh
./scripts/install.sh              # crossbot (recomendado)
./scripts/install.sh all          # crossbot + async-delegate
./scripts/install.sh async-delegate   # um plugin
```

Destino: `~/.hermes/plugins/`

## Bundles

| Bundle | Plugin | Quando usar |
|--------|--------|-------------|
| **cross-bot** | `crossbot` | Bots conversando entre si no Telegram |
| **async-delegate** | `async-delegate` | Tarefas em background (opcional) |

## Habilitar no Hermes

```yaml
# config.yaml de cada profile
plugins:
  enabled:
    - crossbot
```

Setup: [../docs/onboarding/02-instalar-e-adaptar.md](../docs/onboarding/02-instalar-e-adaptar.md)

## Versões

| Plugin | Versão |
|--------|--------|
| crossbot | 0.5.2 |
| async-delegate | 1.1.0 |

**Nota:** `crossbot` v0.5 unifica `kanban-context` + `multi-agent-context`. v1.0 = milestone pós-testes. Ver [crossbot/ATTRIBUTION.pt-BR.md](./crossbot/ATTRIBUTION.pt-BR.md).
