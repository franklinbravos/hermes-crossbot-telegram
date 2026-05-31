# Onboarding — Instalar e adaptar

> **Cenário mais comum:** o ambiente **já tem** vários agentes Hermes.  
> Você **não precisa** criar bots novos — só instalar os plugins e **adequar** o que existe.

## O que o plugin exige (e o que não exige)

| Obrigatório | Não exigido |
|-------------|-------------|
| **Workspace Telegram** tipo fórum, com **tópico por agente/departamento** | Nomes padronizados de profiles (`ops`, `bravo`, etc.) |
| **`topic-map.json`** — profile → tópico + @handle | Modelo LLM específico |
| **`CROSSBOT_BOT_NAME`** = nome da pasta do profile | Quantidade fixa de agentes |
| **Agentes conhecem os colegas** — profile, @, tópico, função | Recriar gateways ou profiles |
| **`MULTI_AGENT_TG_DB_PATH`** único para todos | |

O cross-bot endereça agentes pelo **nome do profile Hermes** (pasta em `~/.hermes/profiles/`). Use os nomes que **já existem** no seu ambiente.

---

## Escolha seu caminho

| Situação | Siga |
|----------|------|
| Já tenho vários agentes rodando | [Caminho A — Adaptar ambiente existente](#caminho-a--adaptar-ambiente-existente) |
| Projeto novo, zero agentes | [Caminho B — Do zero](#caminho-b--do-zero) |

---

## Caminho A — Adaptar ambiente existente

### A1. Inventariar o que já existe

```bash
# Profiles Hermes já instalados
ls ~/.hermes/profiles/

# Gateways ativos (systemd — ajuste se usar outro método)
systemctl list-units 'hermes-gateway-*' --no-pager 2>/dev/null || true
```

Preencha esta tabela (copie para seu runbook):

| Profile (pasta) | Gateway ativo? | @ Telegram do bot | Tópico no workspace (nome + thread_id) | Função / departamento |
|-----------------|----------------|-------------------|----------------------------------------|------------------------|
| *(ex: vendas)* | sim/não | @... | Vendas · 640 | ... |
| | | | | |

**Regra:** a coluna **Profile** vira a chave em `topic-map.json` e o valor de `CROSSBOT_BOT_NAME` no `.env` desse profile.

### A2. Instalar plugins (sem criar agentes)

```bash
git clone https://github.com/franklinbravos/hermes-community-plugins.git
cd hermes-community-plugins
chmod +x scripts/install.sh
./scripts/install.sh
```

Habilite nos `config.yaml` **de cada profile existente**:

```yaml
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

Symlink (substitua pelos profiles **reais** do inventário):

```bash
for bot in $(ls ~/.hermes/profiles/); do
  mkdir -p ~/.hermes/profiles/${bot}/plugins
  ln -sf ~/.hermes/plugins/kanban-context ~/.hermes/profiles/${bot}/plugins/kanban-context
  ln -sf ~/.hermes/plugins/multi-agent-context ~/.hermes/profiles/${bot}/plugins/multi-agent-context
done
```

### A3. Unificar banco compartilhado

Em **cada** profile `.env` (mesmo valor):

```bash
MULTI_AGENT_TG_DB_PATH=~/.hermes/data/multi_agent_tg_shared.db
CROSSBOT_BOT_NAME=<nome-exato-da-pasta-do-profile>
TELEGRAM_BOT_TOKEN=<token-deste-bot>
```

### A4. Workspace obrigatório (fórum + tópicos)

Se ainda **não** tiver:

1. Grupo Telegram → **Topics** habilitado (modo fórum)
2. Um **tópico por agente/departamento** (não misturar todos no Geral)
3. Todos os bots como **admin** com permissão de postar

→ Detalhes: [03-workspace-e-colegas.md](./03-workspace-e-colegas.md)

Se **já** tiver workspace: documente `chat_id` e cada `thread_id` na tabela do passo A1.

### A5. Montar `topic-map.json` a partir do inventário

**Recomendado — wizard interativo** (usa só profiles que existem em disco):

```bash
chmod +x scripts/configure-crossbot.sh
./scripts/configure-crossbot.sh
```

O script pergunta:
- qual profile é o **orchestrator**
- quais profiles entram no **telefone sem fio**
- `chat_id` e `thread_id` do workspace
- opcionalmente grava `CROSSBOT_BOT_NAME` no `.env` de cada profile

Modo não-interativo (CI / repeat):

```bash
./scripts/configure-crossbot.sh \
  --orchestrator matias \
  --players sofia,iago \
  --chat-id -100XXXXXXXXXX \
  --yes
```

**Manual** — edite `~/.hermes/plugins/kanban-context/topic-map.json`:

```json
{
  "chat_id": "-100XXXXXXXXXX",
  "topics": {
    "vendas": 640,
    "suporte": 641,
    "ti": 669
  },
  "handles": {
    "vendas": "meu_bot_vendas",
    "suporte": "meu_bot_suporte",
    "ti": "meu_bot_ti"
  }
}
```

- Chaves = **nomes reais** das pastas em `profiles/`
- `handles` = username Telegram **sem** `@`

Modelo: [../reference/topic-map.example.json](../reference/topic-map.example.json)

### A6. Ensinar cada agente quem são os colegas (SOUL)

Obrigatório: cada bot precisa saber **quem ele é** e **quem são os outros** — profile cross-bot, @ Telegram, tópico, quando acionar.

→ Copie e preencha: [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)  
→ Template do mapa: [../reference/mapa-colegas.template.md](../reference/mapa-colegas.template.md)

### A7. Visibilidade + Kanban board + restart

`visibility-config.json` — `chat_id` do workspace.

**Board Kanban (obrigatório para workers):** o cross-bot cria uma task no Kanban para acordar o agente destino. Sem o board, o outbox é gravado mas **ninguém processa**.

```bash
chmod +x scripts/setup-crossbot-board.sh
./scripts/setup-crossbot-board.sh
```

```bash
# ~/.hermes/.env
CROSSBOT_KANBAN_BOARD=cross-bot
```

```bash
hermes gateway restart
```

### A8. Validar

```bash
# Smoke test — use dois profiles REAIS do inventário
CROSSBOT_BOT_NAME=<profile-a> python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send <profile-b> "Smoke test" "Confirme recebimento"

# Benchmark completo (orchestrator = bot que roda o script, detectado automaticamente)
PHRASE="O rato roeu" ./scripts/telefone-sem-fio.sh
```

`/kanban-status` em qualquer agente · checklist em [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md)

---

## Caminho B — Do zero

Use só se **não** existir nenhum profile Hermes.

1. Crie profiles Hermes + bots Telegram (documentação Hermes upstream)
2. Siga os passos **A2 → A8** acima
3. Ao criar agentes, já defina **um tópico por departamento** no workspace

---

## Troubleshooting

| Sintoma | Ação |
|---------|------|
| Cross-bot não chega | `CROSSBOT_BOT_NAME` ≠ nome da pasta do profile destino |
| Task `ready` para `ops` mas não existe bot ops | `topic-map.json` ainda com placeholders — rode `./scripts/configure-crossbot.sh` |
| Bot “não conhece” colega | Atualizar SOUL + `topic-map.json` |
| Mensagem no tópico errado | Conferir `topics` no topic-map |
| Outbox pending | Worker não usou `crossbot_cli respond` |

→ [../reference/debug-crossbot.md](../reference/debug-crossbot.md)

---

## Próximos passos

| Doc | Conteúdo |
|-----|----------|
| [03-workspace-e-colegas.md](./03-workspace-e-colegas.md) | Workspace + mapa de colegas (obrigatório) |
| [04-guia-agente-hermes.md](./04-guia-agente-hermes.md) | Regras para os bots |
| [05-telefone-sem-fio.md](./05-telefone-sem-fio.md) | Teste benchmark |
