# Onboarding guiado — Crossbot

Instalação **numerada** (etapas 1–10) com **validação automática** em cada gate. Não avance sem `verify` OK.

## Comandos

```bash
cd ~/hermes-crossbot-telegram
./scripts/crossbot-onboarding.sh start
./scripts/crossbot-onboarding.sh current
./scripts/crossbot-onboarding.sh verify
./scripts/crossbot-onboarding.sh verify --watch 180   # step 7 — aguardar worker
./scripts/crossbot-onboarding.sh advance
./scripts/crossbot-onboarding.sh status
./scripts/crossbot-onboarding.sh run-action          # step 6 — ping automático
./scripts/crossbot-onboarding.sh reset [--step 6]
```

Estado: `~/.hermes/data/crossbot-onboarding.json`  
Manifesto: `plugins/crossbot/onboarding-manifest.json`

## Etapas

| Step | Nome | Doc |
|------|------|-----|
| 1 | Instalar plugin | [steps/01-install.md](./steps/01-install.md) |
| 2 | Migrar legado | [steps/02-migrate.md](./steps/02-migrate.md) |
| 3a | topic-map | [steps/03a-topic-map.md](./steps/03a-topic-map.md) |
| 3b | Visibilidade probe | [steps/03b-visibility-probe.md](./steps/03b-visibility-probe.md) |
| 4 | Board Kanban | [steps/04-kanban-board.md](./steps/04-kanban-board.md) |
| 5 | Gateways e env | [steps/05-gateways-env.md](./steps/05-gateways-env.md) |
| 6 | Ping bot1 | [steps/06-ping-bot1.md](./steps/06-ping-bot1.md) |
| 7 | Resposta bot1 | [steps/07-bot1-respond.md](./steps/07-bot1-respond.md) |
| 8 | Ping bot2 | [steps/08-ping-bot2.md](./steps/08-ping-bot2.md) |
| 9 | Benchmark cadeia | [steps/09-benchmark.md](./steps/09-benchmark.md) |
| 10 | Handoff | [steps/10-handoff.md](./steps/10-handoff.md) |

## Fluxo (agente ou humano)

1. `start` → etapa 1  
2. Ler `current` → executar `action_hint`  
3. `verify` (com `--watch` quando indicado)  
4. Se `passed`: `advance`  
5. Repetir até step 10  

**Proibido:** pular etapas; declarar sucesso sem `status` com todas passed; usar `crossbot_cli` no worker Kanban.

## Se travar

| Situação | Ação |
|----------|------|
| Não sabe a etapa | `./scripts/crossbot-onboarding.sh status` |
| Verify falhou | `current` → ler `failure_hints`; não avançar |
| Evidência para dev | `./scripts/crossbot-debug-pack.sh pack` |
| Worker parado | `verify --watch 180` (dispatcher ~60s) |
| Recomeçar | `reset` ou `reset --step N` |

Referência técnica: [debug-crossbot.md](../reference/debug-crossbot.md)

Docs legadas (contexto): [02-instalar-e-adaptar.md](./02-instalar-e-adaptar.md) · [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md) (redireciona para aqui)
