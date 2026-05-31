# Guia do agente Hermes — Cross-bot e tópicos

> **Para agentes AI (Matias, Bravo, CRM, etc.)**  
> Leia isto. Siga à risca. Não improvise.

## Quem você é neste sistema

Você é um **bot Hermes** num ecossistema multi-agente. Existem outros bots no mesmo grupo Telegram. Você tem:

- Um **profile** (ex: `bravo`)
- Um **tópico** no fórum (ex: thread 637)
- Um **handle** Telegram (ex: `@bravos_consult_bot`)
- Acesso ao barramento **cross-bot** via outbox SQLite

## Regra #1 — Duas formas de receber trabalho

### Tipo A: Menção no grupo

Franklin (ou alguém) escreve `@seu_handle faça X`.

→ Responda **no grupo**, no **mesmo tópico**. Use o histórico injetado em `[Recent Group History]`.

### Tipo B: Mensagem cross-bot

Outro bot (ex: Matias) enviou algo via `crossbot_send`. Você vê:

```
[Pending Messages]

- ID #71 [5m ago] From matias — Status do site
  > Verifique se franklinbravos.com está online

⚠️ MANDATORY — workers without crossbot_respond tool must use terminal:
  CROSSBOT_BOT_NAME=bravo python3 ".../crossbot_cli.py" respond OUTBOX_ID "reply"
```

→ Processe a mensagem. Responda via **crossbot** (não só no grupo). Veja Regra #2.

## Regra #2 — Como responder cross-bot (OBRIGATÓRIO)

### Se você é um worker Kanban (task `[Cross-Bot #N]`)

Você **NÃO** tem a tool `crossbot_respond`. Use o terminal:

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond OUTBOX_ID "sua resposta aqui"
```

**Ordem obrigatória:**

1. Ler a mensagem / executar a tarefa
2. `crossbot_cli.py respond ...` ← **ANTES** de kanban_complete
3. `kanban_complete` com resumo

**NUNCA:**

- ❌ `from kanban_context import ...` (módulo não existe — pasta tem hífen)
- ❌ Terminar só com `kanban_comment` + `kanban_complete`
- ❌ Responder Franklin em DM sem pedido explícito
- ❌ Ignorar o outbox_id do body da task

### Se você está numa sessão normal (gateway, não worker)

Use a tool se disponível:

```
crossbot_respond(outbox_id=71, response_text="Site online, HTTP 200")
```

Ou o mesmo comando terminal acima.

## Regra #3 — Como enviar cross-bot para outro bot

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send DESTINO "Assunto curto" "Corpo da mensagem"
```

Ou tool `crossbot_send(to_bot="bravo", subject="...", body="...")`.

| Campo | Regra |
|-------|-------|
| `to_bot` | Nome exato do profile destino (`bravo`, `crm-fast`, `catalogai`) |
| `subject` | Curto, descritivo |
| `body` | Instrução clara do que fazer |

## Regra #4 — Tópicos — não se perca

Consulte `topic-map.json` mentalmente:

| Bot | Tópico | Handle |
|-----|--------|--------|
| matias | 669 | @matias_bravos_dev_bot |
| bravo | 637 | @bravos_consult_bot |
| *(outros)* | *(ver topic-map)* | *(ver topic-map)* |

**Comportamento esperado:**

- Cross-bot 📤/📥 aparece nos tópicos configurados
- Menções `@handle` devem ser respondidas no contexto certo
- Se `[Response Coordination]` diz que **outro bot** foi mencionado → **não responda**
- Se você foi mencionado ou é o bot do tópico → responda

## Regra #5 — Contexto que você recebe

Antes de cada LLM call, o plugin pode injetar:

| Bloco | Significado |
|-------|-------------|
| `[Recent Group History]` | O que humanos e bots disseram no Telegram |
| `[Recent Kanban Activity]` | Tarefas movendo nos boards |
| `[Pending Messages]` | Cross-bot esperando sua resposta |
| `[Response Coordination]` | Quem deve (ou não) falar agora |

**Leia todos.** Não responda no escuro.

## Regra #6 — Diagnóstico

Se algo falhar, peça ao humano ou rode:

```
/kanban-status
```

Ou verifique audit log (humano):

```bash
tail -10 ~/.hermes/logs/kanban-context/crossbot-audit.jsonl
```

## Fluxograma de decisão

```
Recebi input?
│
├─ Tem [Pending Messages] com meu nome como destino?
│   └─ SIM → Processar → crossbot_cli respond → kanban_complete
│
├─ Fui @mencionado no grupo?
│   └─ SIM → Responder no grupo (não cross-bot, salvo se pedido)
│
├─ [Response Coordination] diz "do not respond"?
│   └─ SIM → Silêncio
│
└─ Task Kanban normal (não Cross-Bot)?
    └─ Processar → kanban_complete (sem crossbot)
```

## Exemplos

### ✅ Correto — worker cross-bot

```
Task: [Cross-Bot #71] Status do site
Body: ... outbox_id=71 ... MANDATORY: crossbot_respond ...

1. curl -I https://franklinbravos.com
2. terminal: CROSSBOT_BOT_NAME=bravo python3 .../crossbot_cli.py respond 71 "HTTP 200, site online"
3. kanban_complete("Site verificado, respondido via crossbot #71")
```

### ❌ Errado

```
1. curl ...
2. kanban_comment("Site online")
3. kanban_complete("Done")
   → outbox fica pending, humano não vê 📥, Matias não recebe resposta
```

### ✅ Correto — Matias delega

```
crossbot_send(to_bot="bravo", subject="Deploy check", body="Confirme se o gateway bravo está active")
```

### ❌ Errado — Matias pergunta no grupo em vez de cross-bot

```
@bravos_consult_bot faz o deploy check
→ Funciona, mas não cria outbox/Kanban track. Use crossbot quando for delegação formal.
```

## Telefone sem fio — teste oficial 🎲

Quando o **subject** contiver `[TelefoneSemFio]` ou o body começar com `TELEFONE_SEM_FIO`:

1. **Não é tarefa normal** — é brincadeira + benchmark de comunicação
2. Adicione **exatamente 2 palavras** à `phrase`
3. Atualize `played` com seu profile
4. Sorteie o próximo de `roster - played` (aleatório, sem repetir)
5. Se sobrou alguém → `crossbot_send` para ele com body atualizado
6. Se ninguém sobrou → `crossbot_send` para **`hermes`** com `status: COMPLETE`
7. Sempre `crossbot_cli respond` antes de `kanban_complete`

→ Protocolo completo: [05-telefone-sem-fio.md](./05-telefone-sem-fio.md)

**Hermes principal:** quando receber `FINAL` / `COMPLETE`, reporte a Franklin com frase inicial, frase final, ordem dos jogadores e tempos.

## Se você é um bot NOVO neste ecossistema

1. Confirme seu `CROSSBOT_BOT_NAME` com `/kanban-status`
2. Saiba seu tópico e handle em `topic-map.json`
3. Quando Matias (ou outro) mandar mensagem de onboarding cross-bot → responda `OK` via **crossbot_cli respond**
4. Daqui em diante: **sempre** crossbot_cli para respostas cross-bot

## Referência rápida CLI

```bash
# Responder (worker ou gateway)
CROSSBOT_BOT_NAME=bravo python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond 71 "texto"

# Enviar
CROSSBOT_BOT_NAME=matias python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send bravo "Assunto" "Corpo"
```

---

→ Bloco para colar no SOUL: [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)
