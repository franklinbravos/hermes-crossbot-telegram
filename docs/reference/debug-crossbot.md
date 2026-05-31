# Debug Cross-Bot — Referência técnica

> **Plugin:** kanban-context v2.3.0+  
> **Para:** DevOps, Cursor, agentes que debugam sem acesso ao host.

## Arquitetura

```
Bot sender → crossbot_send()
  ├─ INSERT outbox (pending)
  ├─ CREATE kanban task → assignee = receiver
  └─ 📤 Telegram (token do sender, tópico do receiver)

Dispatcher (~60s) → worker receiver
  ├─ [Pending Messages] no pre_llm_call
  ├─ crossbot_cli.py respond (terminal — workers não têm tool)
  └─ UPDATE outbox (done) + 📥 Telegram (token do receiver)
```

**DB:** `~/.hermes/data/multi_agent_tg_shared.db`  
**Audit:** `~/.hermes/logs/kanban-context/crossbot-audit.jsonl`

## Variáveis de ambiente

```bash
# Obrigatório — MESMO path em todos os profiles
MULTI_AGENT_TG_DB_PATH=~/.hermes/data/multi_agent_tg_shared.db
CROSSBOT_BOT_NAME=bravo

# Telegram
TELEGRAM_BOT_TOKEN=...              # por profile — visibilidade (v2.3.0+)
CROSSBOT_VISIBILITY_CHAT=-100...
CROSSBOT_VISIBILITY_TOKEN=...       # fallback se profile sem token

# Kanban dispatch
CROSSBOT_KANBAN_BOARD=linkedin-content

# Debug
CROSSBOT_AUDIT_LOG=~/.hermes/logs/kanban-context/crossbot-audit.jsonl
```

## Checklist de diagnóstico

### 1. Outbox

```bash
sqlite3 ~/.hermes/data/multi_agent_tg_shared.db \
  "SELECT id, from_bot, to_bot, status, telegram_msg_id FROM outbox ORDER BY id DESC LIMIT 5;"
```

| status | Significado |
|--------|-------------|
| pending | Worker não respondeu via crossbot |
| done | OK no DB — verificar visibility |

### 2. Nomes batem?

`crossbot_send(to_bot="bravo")` → receiver precisa `CROSSBOT_BOT_NAME=bravo`

### 3. Audit log

```bash
tail -20 ~/.hermes/logs/kanban-context/crossbot-audit.jsonl
```

| event | Quando |
|-------|--------|
| `crossbot_send` | Mensagem enfileirada |
| `crossbot_respond` | Resposta gravada |
| `visibility_post` | Tentativa Telegram (ok/erro, post_as_bot) |
| `visibility_skip` | Chat/token ausente |

### 4. Worker completou Kanban mas outbox pending?

Bug clássico — worker ignorou crossbot. Verifique task body:

```bash
sqlite3 ~/.hermes/kanban/boards/linkedin-content/kanban.db \
  "SELECT title, body FROM tasks WHERE title LIKE '%Cross-Bot%' ORDER BY rowid DESC LIMIT 1;"
```

Deve conter `crossbot_cli.py respond` ou `crossbot_respond`.

### 5. Remetente errado no Telegram?

Versão < 2.3.0 usava token único. Atualize:

```bash
grep version ~/.hermes/plugins/kanban-context/plugin.yaml
# deve ser 2.3.0
```

## Bugs conhecidos (histórico)

| Bug | Status v2.3.0 |
|-----|---------------|
| telegram_msg_id NULL | ✅ Resolvido |
| Telegram 400 reply cross-bot | ✅ Resolvido (sem reply entre tokens diferentes) |
| Worker sem crossbot_respond tool | ✅ Workaround crossbot_cli.py |
| Remetente errado (sender aparece como outro bot) | ✅ Token por profile |
| Markdown parsing error | ✅ HTML parse_mode |

## Issues em aberto

| Issue | Notas |
|-------|-------|
| Worker toolset no Hermes core | Fix definitivo: PR em `_HERMES_CORE_TOOLS` |
| Board hardcoded default | Parametrizável via `CROSSBOT_KANBAN_BOARD` |

## Deploy após pull

```bash
cd hermes-community-plugins && git pull
./scripts/install.sh cross-bot
hermes gateway restart
```

**Teste recomendado:** [Telefone sem fio](../onboarding/05-telefone-sem-fio.md) — percorre todos os agentes e mede latência.

## Schema outbox

| Coluna | Uso |
|--------|-----|
| id | outbox_id |
| from_bot, to_bot | Endereçamento |
| status | pending / done |
| kanban_task_id | Task vinculada |
| telegram_msg_id | ID msg 📤 |

---

Histórico detalhado de debug: [../archive/](../archive/)
