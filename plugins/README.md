# Plugins

Pacotes instaláveis para [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Instalação rápida

```bash
git clone https://github.com/franklinbravos/hermes-community-plugins.git
cd hermes-community-plugins
chmod +x scripts/install.sh
./scripts/install.sh              # stack cross-bot (recomendado)
./scripts/install.sh all          # todos os plugins
./scripts/install.sh async-delegate   # um plugin
```

Destino padrão: `~/.hermes/plugins/`

## Bundles

| Bundle | Plugins | Quando usar |
|--------|---------|-------------|
| **cross-bot** | `multi-agent-context` + `kanban-context` | Bots conversando entre si no Telegram |
| **async-delegate** | `async-delegate` | Tarefas em background (opcional) |

## Habilitar no Hermes

```yaml
# config.yaml de cada profile
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

Setup completo: [../docs/onboarding/02-setup-novo-projeto.md](../docs/onboarding/02-setup-novo-projeto.md)

## Versões

| Plugin | Versão |
|--------|--------|
| kanban-context | 2.3.0 |
| multi-agent-context | 2.0.0 |
| async-delegate | 1.1.0 |

Repositório: ver [VERSION](../VERSION) na raiz.
