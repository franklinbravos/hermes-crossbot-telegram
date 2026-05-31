# Cross-Bot Telegram — Documento Técnico de Debug

> **Repo:** [franklinbravos/hermes-community-plugins](https://github.com/franklinbravos/hermes-community-plugins)  
> **Plugin:** `kanban-context` v2.2.0+ (base Matias) / v2.2.1 (visibility token + audit log)  
> **Objetivo:** Bots Hermes conversam via outbox SQLite; humanos veem espelho no Telegram.  
> **Para:** Cursor / agentes AI que debugam o ambiente real (sem acesso ao Hermes host).

---

## Arquitetura resumida

```
Bot Matias (sender)
  └─ crossbot_send(to_bot="bravo", ...)
       ├─ INSERT outbox #N (pending)
       ├─ CREATE kanban task [Cross-Bot #N] → assignee bravo
       └─ 📤 Telegram visibility (token dedicado ou profile)

Kanban dispatcher (~60s)
  └─ spawn worker Bot Bravo

Worker Bravo
  ├─ lê task body com "MANDATORY: crossbot_respond(outbox_id=N)"
  ├─ [Pending Messages] no pre_llm_call
  ├─ tools disponíveis: crossbot_respond, crossbot_send, kanban_*
  └─ DEVE chamar crossbot_respond → UPDATE outbox + 📥 visibility
```

**DB compartilhado:** `~/.hermes/data/multi_agent_tg_shared.db`  
Tabelas: `outbox`, `response_log`, `messages` (multi-agent-context)

---

## Bugs encontrados (sessão Matias)

### Bug 1 — Telegram: reply entre bots diferentes

**Sintoma:** `crossbot_respond()` roda, outbox vira `done`, mas 📥 não aparece no grupo.

**Causa raiz:**
```
HTTP 400: Bad Request: message to be replied not found
```

- Mensagem #833 enviada pelo bot **Matias** (`8829691160:...`)
- Worker **Bravo** tentava `reply_to_message_id=833` com token **Bravo** (`8674561507:...`)
- Telegram **não permite** bot A fazer reply em mensagem enviada por bot B

**Correção v2.1.5:**
1. `_post_visibility_message()` tenta `reply_to` → se 400, **retry sem reply**
2. Env `CROSSBOT_VISIBILITY_TOKEN` — **um bot dedicado** posta 📤 e 📥
3. `reply_to` só usado quando `CROSSBOT_VISIBILITY_TOKEN` está definido (mesmo token no send e respond)
4. `CROSSBOT_VISIBILITY_THREAD_ID` — força tópico do fórum Telegram

### Bug 2 — Worker não chama crossbot_respond

**Sintoma:** Outbox #52 ficou `pending`; worker usou `kanban_comment` + `kanban_complete` em vez de `crossbot_respond`.

**Causa:** Tools já registradas, mas LLM do worker ignorou instrução no body.

**Correção v2.1.5:**
1. Outbox inserido **antes** da task Kanban → body inclui `outbox_id` explícito
2. Task title: `[Cross-Bot #52] ...`
3. Body worker com bloco `MANDATORY BEFORE TASK COMPLETE`
4. `[Pending Messages]` reforça: chamar `crossbot_respond` **antes** de `kanban_complete`
5. Tool description enfatiza ordem obrigatória

### Bug 3 — DB isolado por profile (fix anterior v2.1.4)

Cada profile usava `profiles/{nome}/data/multi_agent_tg_shared.db` separado.  
Fix: default path usa `_real_hermes_home()` → `~/.hermes/data/...`

### Bug 4 — outbox_id ausente no contexto (fix v2.1.4)

`[Pending Messages]` não mostrava ID → agente não sabia qual `outbox_id` passar.

---

## Variáveis de ambiente (todas os profiles)

```bash
# Obrigatório multi-bot
MULTI_AGENT_TG_DB_PATH=/root/.hermes/data/multi_agent_tg_shared.db
CROSSBOT_BOT_NAME=bravo          # nome EXATO do profile deste bot

# Visibilidade Telegram
CROSSBOT_VISIBILITY_CHAT=-1003716565637
CROSSBOT_VISIBILITY_THREAD_ID=12345   # ID do tópico (forum groups)
CROSSBOT_VISIBILITY_TOKEN=8829691160:AAEK...  # bot dedicado — RECOMENDADO

# Fallback se não usar token dedicado
TELEGRAM_BOT_TOKEN=...

# Board Kanban para dispatch (default linkedin-content)
CROSSBOT_KANBAN_BOARD=linkedin-content

# Log de auditoria (para Cursor debugar)
CROSSBOT_AUDIT_LOG=/root/.hermes/logs/kanban-context/crossbot-audit.jsonl
```

### Config recomendada (Matias + Bravo)

| Profile | CROSSBOT_BOT_NAME | CROSSBOT_VISIBILITY_TOKEN |
|---------|-------------------|---------------------------|
| matias  | matias            | token do Matias (bot dedicado) |
| bravo   | bravo             | **mesmo** token do Matias |

Assim 📤 e 📥 usam o **mesmo bot** → `reply_to` funciona quando desejado.

---

## Log de auditoria (novo v2.1.5)

**Arquivo:** `~/.hermes/logs/kanban-context/crossbot-audit.jsonl`

Cada linha = JSON com eventos:

| event | Quando |
|-------|--------|
| `crossbot_send` | Mensagem enfileirada |
| `crossbot_respond` | Resposta gravada no outbox |
| `visibility_post` | Tentativa Telegram (ok/erro, reply_to, thread_id) |
| `visibility_skip` | Chat/token ausente |
| `kanban_task_failed` | Falha ao criar task |

**Exemplo — reply rejeitado:**
```json
{"ts": 1717171717.0, "event": "visibility_post", "bot": "bravo", "outbox_id": 52, "direction": "responded", "token_prefix": "8674561507:A...", "chat_id": "-1003716565637", "thread_id": 42, "reply_to": 836, "ok": false, "error": "Bad Request: message to be replied not found", "attempt": "with_reply"}
{"ts": 1717171717.1, "event": "visibility_post", "bot": "bravo", "outbox_id": 52, "direction": "responded", "ok": true, "telegram_msg_id": 837, "attempt": "no_reply"}
```

**Como usar no Cursor:** peça ao usuário para colar as últimas 20 linhas deste arquivo.

---

## Checklist de diagnóstico

### 1. Outbox no DB
```bash
sqlite3 ~/.hermes/data/multi_agent_tg_shared.db \
  "SELECT id, from_bot, to_bot, status, kanban_task_id, telegram_msg_id FROM outbox ORDER BY id DESC LIMIT 5;"
```

| status | Significado |
|--------|-------------|
| pending | Worker não chamou crossbot_respond |
| done | OK no DB — verificar visibility log |

### 2. Nome do bot bate?
```bash
# Sender usa to_bot="bravo"
# Receiver precisa CROSSBOT_BOT_NAME=bravo (ou profile name = bravo)
```

### 3. Tools no worker?
Envie `/kanban-status` ou verifique logs gateway na carga do plugin:
```
kanban-context: ✅ all validations passed
```

Tools registradas: `crossbot_send`, `crossbot_respond`

### 4. Visibility falhou silenciosamente?
```bash
tail -20 ~/.hermes/logs/kanban-context/crossbot-audit.jsonl
```

### 5. Worker completou Kanban mas não outbox?
Sintoma clássico do Bug 2. Verifique task body no board:
```bash
sqlite3 ~/.hermes/kanban/boards/linkedin-content/kanban.db \
  "SELECT id, title, body FROM tasks WHERE title LIKE '%Cross-Bot%' ORDER BY rowid DESC LIMIT 1;"
```

Deve conter: `MANDATORY: crossbot_respond(outbox_id=N`

---

## Schema outbox (v2.1.5)

| Coluna | Tipo | Uso |
|--------|------|-----|
| id | INTEGER | outbox_id |
| from_bot, to_bot | TEXT | Endereçamento |
| status | pending/done | Estado |
| kanban_task_id | TEXT | Task vinculada |
| telegram_msg_id | INTEGER | ID msg 📤 (para reply opcional) |
| telegram_thread_id | INTEGER | Tópico Telegram |

Migração automática em `_ensure_outbox_columns()` na carga do plugin.

---

## Fluxo de deploy após pull

```bash
cd hermes-community-plugins && git pull
cp -r kanban-context ~/.hermes/plugins/kanban-context
cp -r multi-agent-context ~/.hermes/plugins/multi-agent-context

# Em CADA profile .env — adicionar CROSSBOT_VISIBILITY_TOKEN
hermes gateway restart
```

Teste:
1. Matias envia cross-bot para Bravo
2. Verificar 📤 no Telegram + linha `crossbot_send` no audit log
3. Aguardar worker Bravo (~60s)
4. Verificar outbox `done` + 📥 no Telegram + `crossbot_respond` no audit log

---

## Issues em aberto

| Issue | Status |
|-------|--------|
| Board `linkedin-content` hardcoded | Parametrizado via `CROSSBOT_KANBAN_BOARD` |
| Import `plugins.kanban_context` vs pasta `kanban-context` | Depende loader Hermes |
| `claim_response()` sem tool | API manual only |
| Worker toolset restriction | Se Hermes filtrar tools no worker, verificar config toolsets |

---

## Histórico de versões

| Versão | Mudanças |
|--------|----------|
| 2.1.4 | Tools crossbot_*, outbox ID no contexto, DB path real home |
| 2.1.5 | Visibility retry sem reply, CROSSBOT_VISIBILITY_TOKEN, audit log JSONL, worker body mandatório, telegram_msg_id |

---

## Tags Obsidian

#hermes #crossbot #kanban-context #telegram #debug #franklinbravos
