# Debug Cross-Bot — Referência técnica

> **Plugin:** crossbot v0.5.0+ *(pré-release)*  
> **Para:** DevOps, Cursor, agentes que debugam sem acesso ao host.

## Arquitetura (v0.5 — Mention Relay, pré-release)

```
Bot sender → resposta com @colega (post_llm_call)
  ├─ INSERT outbox (pending) + source_message_text
  ├─ CREATE kanban task → assignee = receiver
  └─ 📤 Telegram (token do sender, tópico do receiver)

Dispatcher (~60s) → worker receiver
  ├─ [Pending Messages] no pre_llm_call
  ├─ Bot responde naturalmente (sem crossbot_cli obrigatório)
  └─ post_llm_call → crossbot_respond automático
        ├─ UPDATE outbox (done)
        └─ 📥 Telegram: reply_to real → fallback citação ↩
```

**Fluxo explícito (fallback):** `crossbot_send()` → mesmo pipeline de worker + auto-respond.

**DB:** `~/.hermes/data/multi_agent_tg_shared.db`  
**Audit:** `~/.hermes/logs/crossbot/crossbot-audit.jsonl`

## Variáveis de ambiente

```bash
# Obrigatório — MESMO path em todos os profiles
MULTI_AGENT_TG_DB_PATH=~/.hermes/data/multi_agent_tg_shared.db
CROSSBOT_BOT_NAME=agente-a

# Telegram
TELEGRAM_BOT_TOKEN=...              # por profile — visibilidade
CROSSBOT_VISIBILITY_CHAT=-100...
CROSSBOT_VISIBILITY_TOKEN=...       # fallback se profile sem token

# Kanban dispatch
CROSSBOT_KANBAN_BOARD=cross-bot   # default; board must exist — see setup-crossbot-board.sh

# Mention relay
CROSSBOT_MENTION_DEDUP_SECONDS=60  # evita tasks duplicadas por menção repetida

# Debug
CROSSBOT_AUDIT_LOG=~/.hermes/logs/crossbot/crossbot-audit.jsonl
```

## Checklist de diagnóstico

### 1. Outbox

```bash
sqlite3 ~/.hermes/data/multi_agent_tg_shared.db \
  "SELECT id, from_bot, to_bot, status, source_telegram_msg_id, telegram_msg_id \
   FROM outbox ORDER BY id DESC LIMIT 5;"
```

| status | Significado |
|--------|-------------|
| pending | Worker não completou turno ou auto-respond falhou |
| done | OK no DB — verificar visibility |

### 2. Handles batem?

Menção `@bot_vendas` → `handles` em `topic-map.json` deve mapear para o profile correto.

### 3. Audit log

```bash
tail -20 ~/.hermes/logs/crossbot/crossbot-audit.jsonl
```

| event | Quando |
|-------|--------|
| `mention_relay` | Menção detectada → outbox + task |
| `crossbot_send` | Mensagem enfileirada (tool/CLI) |
| `crossbot_respond` | Resposta gravada |
| `visibility_post` | Tentativa Telegram (`attempt=reply\|citation\|plain`) |
| `visibility_skip` | Chat/token ausente |

### 4. Worker completou Kanban mas outbox pending?

Verifique se o worker rodou com `HERMES_KANBAN_TASK` setado e se havia exatamente uma outbox pending. Auto-respond exige sessão worker + outbox `pending`.

### 5. Reply falhou mas resposta apareceu?

Esperado entre tokens de bots diferentes. Audit deve mostrar `attempt=citation` após `attempt=reply` rejeitado.

### 6. Versão instalada

```bash
grep version ~/.hermes/plugins/crossbot/plugin.yaml
# deve ser 0.5.0
grep hooks ~/.hermes/plugins/crossbot/plugin.yaml
# deve listar pre_llm_call e post_llm_call
```

## Reply real — melhoria futura (Hermes core)

O plugin já aceita estes kwargs no `post_llm_call` (forward-compatible):

- `sent_message_id`
- `last_sent_message_id`
- `telegram_message_id`

Também lê `HERMES_SESSION_LAST_SENT_MESSAGE_ID` e correlaciona via `messages.telegram_msg_id` no DB compartilhado do **crossbot** (`shared_history.py`).

**PR opcional no Hermes:** expor `sent_message_id` no `post_llm_call` após enviar a mensagem ao Telegram — torna `source_telegram_msg_id` confiável para reply real.

## Bugs conhecidos (histórico)

| Bug | Status v0.5.0 |
|-----|---------------|
| telegram_msg_id NULL | ✅ Mitigado (citation fallback) |
| Telegram 400 reply cross-bot | ✅ Try reply → citation |
| Worker sem crossbot_respond tool | ✅ Auto-respond no post_llm_call |
| Remetente errado (sender aparece como outro bot) | ✅ Token por profile |
| Markdown parsing error | ✅ HTML parse_mode |
| Menção duplicada cria várias tasks | ✅ Dedup 60s |

## Issues em aberto

| Issue | Notas |
|-------|-------|
| Worker toolset no Hermes core | Fix definitivo: PR em `_HERMES_CORE_TOOLS` |
| `unable to open database file` | Rode `./scripts/setup-crossbot-board.sh` |
| `unsupported operand type(s) for \|` (Python 3.8) | v2.3.2+ usa `hermes kanban create` via CLI |

## Deploy após pull

```bash
cd ~/crossbot && ./scripts/auto-update.sh --restart
# ou primeira vez / onboarding completo:
cd ~/crossbot && ./scripts/bootstrap.sh --yes --update-only
```

**Cron:** `./scripts/setup-auto-update-cron.sh`

**Teste recomendado:** peça ao bot A que `@mencione` o bot B numa conversa normal; confirme task Kanban + resposta no Telegram.

**Benchmark avançado:** [Telefone sem fio](../onboarding/05-telefone-sem-fio.md)

## Schema outbox

| Coluna | Uso |
|--------|-----|
| id | outbox_id |
| from_bot, to_bot | Endereçamento |
| status | pending / done |
| kanban_task_id | Task vinculada |
| telegram_msg_id | ID msg 📤 (visibilidade envio) |
| source_telegram_msg_id | ID msg do bot remetente (para reply) |
| source_message_text | Texto original (citação fallback) |

---

Histórico detalhado de debug: [../archive/](../archive/)
