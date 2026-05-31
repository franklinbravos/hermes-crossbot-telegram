# Hermes Community Plugins 🎭

Battle-tested plugins for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — **zero core patches required**.

**Versão do repositório:** 2.3.0 · **Cross-bot:** kanban-context 2.3.0

## Instalação (1 comando)

```bash
git clone https://github.com/franklinbravos/hermes-community-plugins.git
cd hermes-community-plugins
./scripts/install.sh          # stack cross-bot (recomendado)
# ./scripts/install.sh all    # todos os plugins
```

Habilite em cada profile `config.yaml`:

```yaml
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

→ Setup completo: [docs/onboarding/02-setup-novo-projeto.md](./docs/onboarding/02-setup-novo-projeto.md)  
→ Handoff operador: [docs/onboarding/HANDOFF-DEPLOY.md](./docs/onboarding/HANDOFF-DEPLOY.md)

**Teste cross-bot (telefone sem fio):**

```bash
PHRASE="O rato roeu" ./scripts/telefone-sem-fio.sh
```

## Estrutura

```
plugins/           ← pacotes instaláveis
  kanban-context/      cross-bot + Kanban
  multi-agent-context/ histórico compartilhado (obrigatório p/ cross-bot)
  async-delegate/      tarefas background (opcional)
scripts/
  install.sh         ← instalador
docs/
  onboarding/        ← guias passo a passo
  reference/         ← debug, feature map
  archive/           ← changelog histórico
```

## Documentação

| Guia | Link |
|------|------|
| Hub | [docs/README.md](./docs/README.md) |
| Como funciona | [01-como-funciona.md](./docs/onboarding/01-como-funciona.md) |
| Guia do agente | [04-guia-agente-hermes.md](./docs/onboarding/04-guia-agente-hermes.md) |
| Telefone sem fio | [05-telefone-sem-fio.md](./docs/onboarding/05-telefone-sem-fio.md) · `./scripts/telefone-sem-fio.sh` |

## Plugins

| Plugin | Descrição | README |
|--------|-----------|--------|
| **kanban-context** | Cross-bot + Kanban + visibilidade Telegram | [plugins/kanban-context/](./plugins/kanban-context/) |
| **multi-agent-context** | Histórico Discord/Telegram compartilhado | [plugins/multi-agent-context/](./plugins/multi-agent-context/) |
| **async-delegate** | Subagentes em background | [plugins/async-delegate/](./plugins/async-delegate/) |

## Multi-profile

```bash
for bot in orchestrator ops agent-alpha; do
  mkdir -p ~/.hermes/profiles/${bot}/plugins
  ln -sf ~/.hermes/plugins/kanban-context ~/.hermes/profiles/${bot}/plugins/kanban-context
  ln -sf ~/.hermes/plugins/multi-agent-context ~/.hermes/profiles/${bot}/plugins/multi-agent-context
done
```

## Requirements

- Hermes Agent **v0.13+** · Python **3.11+** · stdlib only (plugins principais)

## License

MIT
