# Setup — Novo projeto Hermes multi-bot

> Checklist completo do zero até o primeiro cross-bot funcionando.  
> Tempo estimado: 30–60 min (depende de quantos bots).

## Pré-requisitos

- [ ] Hermes Agent **v0.13+** instalado
- [ ] Python **3.11+**
- [ ] Grupo Telegram tipo **Fórum** (topics habilitados)
- [ ] Um bot Telegram por agente (token `@BotFather` para cada)
- [ ] Acesso SSH ao servidor onde rodam os gateways

---

## Passo 1 — Clonar e instalar plugins

```bash
git clone https://github.com/franklinbravos/hermes-community-plugins.git
cd hermes-community-plugins

# Copiar plugins para o Hermes global
cp -r kanban-context ~/.hermes/plugins/kanban-context
cp -r multi-agent-context ~/.hermes/plugins/multi-agent-context
```

Habilite em **cada** profile `config.yaml`:

```yaml
plugins:
  enabled:
    - multi-agent-context
    - kanban-context
```

> **Symlink por profile (recomendado em multi-bot):**
> ```bash
> for bot in matias bravo catalogai; do
>   mkdir -p ~/.hermes/profiles/${bot}/plugins
>   ln -sf ~/.hermes/plugins/kanban-context \
>           ~/.hermes/profiles/${bot}/plugins/kanban-context
>   ln -sf ~/.hermes/plugins/multi-agent-context \
>           ~/.hermes/profiles/${bot}/plugins/multi-agent-context
> done
> ```

---

## Passo 2 — Banco compartilhado (crítico)

Todos os bots **devem** apontar para o **mesmo** SQLite:

```bash
# ~/.hermes/.env  (ou em cada profile .env — MESMO valor)
MULTI_AGENT_TG_DB_PATH=/home/SEU_USER/.hermes/data/multi_agent_tg_shared.db
```

Verifique:

```bash
mkdir -p ~/.hermes/data
sqlite3 ~/.hermes/data/multi_agent_tg_shared.db ".tables"
# Deve listar: outbox, messages, response_log (após primeiro uso)
```

---

## Passo 3 — Nome do bot em cada profile

Em `~/.hermes/profiles/NOME/.env`:

```bash
CROSSBOT_BOT_NAME=bravo    # DEVE bater com o nome do profile e topic-map
TELEGRAM_BOT_TOKEN=123456:ABC...
```

O `crossbot_send(to_bot="bravo")` só entrega se o receiver tiver `CROSSBOT_BOT_NAME=bravo`.

---

## Passo 4 — Grupo Telegram e tópicos

1. Crie um grupo **Fórum** no Telegram
2. Adicione **todos** os bots como administradores (permissão de postar)
3. Crie um tópico por agente (Matias, Bravo, CRM, etc.)
4. Anote o **chat_id** (ex: `-1003716565637`) e o **message_thread_id** de cada tópico

→ Detalhes: [03-topicos-telegram.md](./03-topicos-telegram.md)

---

## Passo 5 — Configurar topic-map.json

Edite `~/.hermes/plugins/kanban-context/topic-map.json`:

```json
{
  "chat_id": "-100SEU_CHAT_ID",
  "topics": {
    "matias": 669,
    "bravo": 637
  },
  "handles": {
    "matias": "matias_bravos_dev_bot",
    "bravo": "bravos_consult_bot"
  }
}
```

| Campo | Regra |
|-------|-------|
| Chave em `topics` | Nome do **profile** Hermes (lowercase) |
| Valor | `message_thread_id` do tópico no fórum |
| `handles` | Username do bot **sem** `@` |

Modelo completo: [../reference/topic-map.example.json](../reference/topic-map.example.json)

---

## Passo 6 — Visibilidade no Telegram

Edite `~/.hermes/plugins/kanban-context/visibility-config.json`:

```json
{
  "telegram_bot_token": "",
  "visibility_chat_id": "-100SEU_CHAT_ID",
  "enabled": true,
  "visibility_thread_id": "669"
}
```

Variáveis de ambiente (fallback):

```bash
# ~/.hermes/.env
CROSSBOT_VISIBILITY_CHAT=-100SEU_CHAT_ID
CROSSBOT_VISIBILITY_TOKEN=          # opcional — fallback se profile sem token
CROSSBOT_KANBAN_BOARD=linkedin-content
```

> **v2.2.4:** Cada bot posta com o token do **próprio profile** (`profiles/bravo/.env`). O `CROSSBOT_VISIBILITY_TOKEN` só entra se o profile não tiver `TELEGRAM_BOT_TOKEN`.

---

## Passo 7 — Board Kanban

O cross-bot usa um board para dispatch. Default: `linkedin-content`.

```bash
# Verificar se existe
ls ~/.hermes/kanban/boards/linkedin-content/kanban.db
```

Ou defina outro:

```bash
CROSSBOT_KANBAN_BOARD=seu-board
```

---

## Passo 8 — Reiniciar gateways

```bash
hermes gateway restart
# ou por profile:
systemctl restart hermes-gateway-bravo
```

Verifique nos logs:

```
kanban-context: ✅ all validations passed
multi-agent-context: registered pre_llm_call + post_llm_call
```

---

## Passo 9 — Health check

Envie para qualquer bot no Telegram:

```
/kanban-status
```

Deve retornar versão **2.2.4**, boards, outbox stats, validações.

Ou via terminal:

```bash
python3 -c "
import importlib.util, os
spec = importlib.util.spec_from_file_location(
    'kc', os.path.expanduser('~/.hermes/plugins/kanban-context/__init__.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod.kanban_status())
"
```

---

## Passo 10 — Teste cross-bot (smoke test)

Do bot **ti/Matias** (ou via CLI):

```bash
CROSSBOT_BOT_NAME=ti python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send bravo "Teste setup" "Confirme que recebeu esta mensagem"
```

**Verificar:**

| # | O quê | Esperado |
|---|-------|----------|
| 1 | 📤 no Telegram | Aparece como **ti**, no tópico do Bravo |
| 2 | Outbox | `sqlite3 ... "SELECT id,status FROM outbox ORDER BY id DESC LIMIT 1;"` → `pending` |
| 3 | Kanban | Task `[Cross-Bot #N]` assignada ao bravo |
| 4 | ~60s depois | Worker Bravo spawna |
| 5 | Worker responde | `crossbot_cli.py respond N "OK"` |
| 6 | 📥 no Telegram | Aparece como **Bravo**, no tópico do Bravo |
| 7 | Outbox | `status=done` |
| 8 | Audit log | `tail -5 ~/.hermes/logs/kanban-context/crossbot-audit.jsonl` |

---

## Passo 10b — Telefone sem fio (teste completo + benchmark)

Depois do smoke test, rode o **telefone sem fio** — percorre **todos** os agentes, mede latência e prova a cadeia inteira.

Peça ao Hermes principal (`hermes`):

> "Roda telefone sem fio com a frase: O rato roeu"

→ Protocolo completo: [05-telefone-sem-fio.md](./05-telefone-sem-fio.md)

Este é o teste oficial de performance e brincadeira do ecossistema. Use após todo deploy.

---

## Passo 11 — Instruir os agentes

Cole o conteúdo de [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md) no SOUL/instructions de **cada** bot.

→ Guia detalhado: [04-guia-agente-hermes.md](./04-guia-agente-hermes.md)

---

## Troubleshooting rápido

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| Outbox fica `pending` | Worker não chamou `crossbot_respond` / CLI | Ver body da task Kanban |
| Resposta como Matias | Versão < 2.2.4 | `git pull` + redeploy plugin |
| Mensagem não aparece no grupo | `visibility-config` ou chat_id errado | `/kanban-status` + audit log |
| Bot não recebe mensagem | `CROSSBOT_BOT_NAME` ≠ `to_bot` | Conferir nomes |
| DB vazio no receiver | Paths diferentes por profile | Unificar `MULTI_AGENT_TG_DB_PATH` |

→ Checklist completo: [../reference/debug-crossbot.md](../reference/debug-crossbot.md)

---

## Variáveis de ambiente — referência

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `MULTI_AGENT_TG_DB_PATH` | ✅ | Caminho único do SQLite compartilhado |
| `CROSSBOT_BOT_NAME` | ✅ | Nome deste bot no barramento |
| `TELEGRAM_BOT_TOKEN` | ✅ | Token do bot deste profile |
| `CROSSBOT_VISIBILITY_CHAT` | ✅ | Chat ID do grupo fórum |
| `CROSSBOT_KANBAN_BOARD` | — | Board dispatch (default `linkedin-content`) |
| `KANBAN_CONTEXT_EVENT_LIMIT` | — | Eventos Kanban no contexto (default 10) |
| `CROSSBOT_AUDIT_LOG` | — | Caminho do JSONL de auditoria |
