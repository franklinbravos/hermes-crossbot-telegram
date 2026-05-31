# Telefone sem fio — Teste de comunicação cross-bot

> **Brincadeira + benchmark oficial.**  
> Use sempre que quiser validar que o cross-bot funciona e medir performance.

## O que é

O **telefone sem fio** percorre todos os agentes do ecossistema via `crossbot_send`. Cada um adiciona **exatamente duas palavras** à frase e repassa para outro agente **aleatório** que ainda não jogou na rodada. Quando não sobra ninguém, a frase volta ao **Hermes principal**, que reporta o resultado a Franklin.

Funciona como:

- ✅ Teste end-to-end (outbox → worker → crossbot_cli → próximo bot)
- ✅ Prova de identidade no Telegram (cada bot posta como si mesmo)
- ✅ Medição de latência por salto e da rodada inteira
- 🎲 Brincadeira — a frase final quase sempre fica absurda

---

## Papéis

| Papel | Profile típico | O que faz |
|-------|----------------|-----------|
| **Hermes principal** | `hermes` | Inicia a rodada, recebe o retorno final, reporta a Franklin |
| **Jogadores** | `ti`, `bravo`, `catalogai`, `crm-fast`, `dado-seguro`, `social-media` | Adicionam 2 palavras e repassam |
| **Franklin** | humano | Pede o teste e recebe o relatório final |

O orchestrador **não joga** — só abre e fecha a rodada.

### Roster padrão (jogadores)

Liste todos os profiles em `topic-map.json` **exceto** o orchestrador:

```
ti, bravo, catalogai, crm-fast, dado-seguro, social-media
```

Adicione ou remova conforme bots ativos no projeto.

---

## Formato da mensagem (contrato)

Toda mensagem de telefone sem fio usa este **subject**:

```
[TelefoneSemFio] round=<ID>
```

Exemplo: `[TelefoneSemFio] round=20260531-1430`

### Body (copie este template)

```
TELEFONE_SEM_FIO
round: 20260531-1430
started_at: 2026-05-31T14:30:00Z
phrase: A gente testa
played: ti
roster: ti,bravo,catalogai,crm-fast,dado-seguro,social-media
next: bravo
hop: 2
```

| Campo | Significado |
|-------|-------------|
| `round` | ID único da rodada (data + hora ou UUID curto) |
| `started_at` | ISO 8601 — início da rodada (não altere) |
| `phrase` | Frase acumulada até agora |
| `played` | Profiles que **já jogaram** (vírgula, sem espaços) |
| `roster` | Todos os jogadores elegíveis na rodada |
| `next` | Próximo destino (só na mensagem de repasse) |
| `hop` | Número do salto (1 = primeiro jogador, incrementa a cada repasse) |

---

## Fluxo completo

```
Franklin: "Roda telefone sem fio"
        │
        ▼
┌─────────────────┐
│ Hermes principal │  crossbot_send → primeiro jogador (aleatório)
│  phrase inicial  │  subject: [TelefoneSemFio] round=...
└────────┬────────┘
         │
         ▼
    ┌─────────┐     +2 palavras      ┌─────────┐
    │  Jogador │ ──────────────────► │ próximo │  (aleatório, não em `played`)
    │    A     │   crossbot_send      │    B    │
    └─────────┘                       └────┬────┘
         ▲                                  │
         │         ... até roster esgotado   ▼
         │                            ┌─────────┐
         └────────────────────────────│ último  │
                                      │ jogador │
                                      └────┬────┘
                                           │ crossbot_send → hermes
                                           ▼
                              ┌─────────────────┐
                              │ Hermes principal │  reporta a Franklin
                              │  frase final +   │  (Telegram + métricas)
                              │  métricas        │
                              └─────────────────┘
```

---

## Passo a passo — Hermes principal (orchestrador)

### 1. Franklin pede o teste

Exemplo: *"Roda telefone sem fio com a frase: O rato roeu"*

### 2. Montar a rodada

```bash
ROUND="20260531-1430"
PHRASE="O rato roeu"
ROSTER="ti,bravo,catalogai,crm-fast,dado-seguro,social-media"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Escolher primeiro jogador aleatório do roster
FIRST="bravo"   # exemplo — sortear de fato
```

### 3. Enviar ao primeiro jogador

```bash
CROSSBOT_BOT_NAME=hermes python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send "${FIRST}" \
  "[TelefoneSemFio] round=${ROUND}" \
  "TELEFONE_SEM_FIO
round: ${ROUND}
started_at: ${STARTED_AT}
phrase: ${PHRASE}
played: hermes
roster: ${ROSTER}
hop: 1"
```

> `played: hermes` marca o orchestrador como já "passado" para o algoritmo de sorteio dos agentes (hermes não adiciona palavras).

### 4. Aguardar retorno

O último jogador manda `crossbot_send` de volta para `hermes`. Você recebe via `[Pending Messages]` ou worker.

### 5. Reportar a Franklin

Monte o relatório:

```markdown
## Telefone sem fio — round 20260531-1430

**Frase inicial:** O rato roeu
**Frase final:** O rato roeu a roupa velha do rei de bravo catalogai social

**Ordem de jogadores:** ti → bravo → dado-seguro → catalogai → crm-fast → social-media
**Saltos:** 6
**Duração total:** 4m 12s (started_at → último crossbot_respond)
**Latência média por salto:** ~42s

**Status:** ✅ Todos responderam | outbox final #82 done
```

### 6. Medir performance (audit log)

```bash
# Filtrar eventos da rodada
grep "TelefoneSemFio\|crossbot" ~/.hermes/logs/kanban-context/crossbot-audit.jsonl | tail -30

# Timestamps no outbox
sqlite3 ~/.hermes/data/multi_agent_tg_shared.db \
  "SELECT id, from_bot, to_bot, status, created_at FROM outbox ORDER BY id DESC LIMIT 10;"
```

| Métrica | Como calcular |
|---------|---------------|
| **Duração total** | `started_at` → timestamp do último `crossbot_respond` para hermes |
| **Latência por salto** | Δ entre `crossbot_send` e worker `crossbot_respond` de cada outbox_id |
| **Taxa de sucesso** | jogadores que completaram / jogadores no roster |
| **Gargalo** | salto com maior Δ (geralmente dispatcher ~60s + worker) |

---

## Passo a passo — Cada jogador

Quando receber `[TelefoneSemFio]` no subject ou `TELEFONE_SEM_FIO` no body:

### 1. Parsear o body

Extraia: `phrase`, `played`, `roster`, `round`, `started_at`, `hop`.

### 2. Adicionar exatamente duas palavras

```
phrase: "O rato roeu"
você (bravo): adiciona "a roupa"
nova phrase: "O rato roeu a roupa"
```

Regras:

- **Exatamente 2 palavras** (não 1, não 3)
- Palavras separadas por espaço
- Pode ser criativo — é brincadeira
- Não altere o que veio antes

### 3. Atualizar `played`

Adicione **seu** profile à lista:

```
played: hermes,ti,bravo   →   você é bravo, então played: hermes,ti,bravo
```

### 4. Escolher próximo destino

```
roster: ti,bravo,catalogai,crm-fast,dado-seguro,social-media
played: hermes,ti,bravo

disponíveis = roster - played = catalogai, crm-fast, dado-seguro, social-media
próximo = sortear um aleatório → ex: dado-seguro
```

**NUNCA** repita alguém em `played`.

### 5a. Se ainda há jogadores disponíveis → repassar

```bash
CROSSBOT_BOT_NAME=bravo python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send "dado-seguro" \
  "[TelefoneSemFio] round=20260531-1430" \
  "TELEFONE_SEM_FIO
round: 20260531-1430
started_at: 2026-05-31T14:30:00Z
phrase: O rato roeu a roupa
played: hermes,ti,bravo
roster: ti,bravo,catalogai,crm-fast,dado-seguro,social-media
next: dado-seguro
hop: 3"
```

Depois: `crossbot_cli.py respond OUTBOX_ID "Repassado para dado-seguro (+2 palavras: a roupa)"`

### 5b. Se NÃO há jogadores disponíveis → voltar ao Hermes

Todos jogaram. Envie a frase final para o orchestrador:

```bash
CROSSBOT_BOT_NAME=bravo python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send "hermes" \
  "[TelefoneSemFio] round=20260531-1430 FINAL" \
  "TELEFONE_SEM_FIO
round: 20260531-1430
started_at: 2026-05-31T14:30:00Z
phrase: O rato roeu a roupa velha do rei
played: hermes,ti,bravo,catalogai,crm-fast,dado-seguro,social-media
roster: ti,bravo,catalogai,crm-fast,dado-seguro,social-media
hop: 7
status: COMPLETE"
```

Depois: `crossbot_cli.py respond ... "Rodada completa, frase devolvida ao Hermes"`

---

## Algoritmo de sorteio (pseudocódigo)

```python
def pick_next(roster: str, played: str) -> str | None:
    roster_set = set(roster.split(","))
    played_set = set(played.split(","))
    available = list(roster_set - played_set)
    if not available:
        return None  # → enviar para hermes com status COMPLETE
    return random.choice(available)
```

---

## Exemplo de rodada completa

| Hop | Bot | +2 palavras | Phrase acumulada | Envia para |
|-----|-----|-------------|------------------|------------|
| — | hermes | *(inicial)* | O rato roeu | bravo |
| 1 | bravo | a roupa | O rato roeu a roupa | dado-seguro |
| 2 | dado-seguro | velha do | O rato roeu a roupa velha do | catalogai |
| 3 | catalogai | rei de | O rato roeu a roupa velha do rei de | crm-fast |
| 4 | crm-fast | Portugal azul | ... Portugal azul | social-media |
| 5 | social-media | na praia | ... na praia | ti |
| 6 | ti | com sol | ... com sol | **hermes** (COMPLETE) |

Hermes reporta a Franklin a frase final + ordem + tempos.

---

## Checklist de sucesso

| # | Verificação | OK? |
|---|-------------|-----|
| 1 | Cada hop gerou 📤 no Telegram | |
| 2 | Cada jogador respondeu via crossbot_cli | |
| 3 | Nenhum bot repetido em `played` | |
| 4 | Frase cresceu 2 palavras por jogador | |
| 5 | Outbox final para `hermes` com `status: COMPLETE` | |
| 6 | Hermes reportou a Franklin com métricas | |
| 7 | Audit log sem erros de visibility | |

---

## Quando usar

| Situação | Use telefone sem fio? |
|----------|----------------------|
| Deploy novo plugin cross-bot | ✅ Sim |
| Validar performance / latência | ✅ Sim |
| Franklin pede teste do ecossistema | ✅ Sim |
| Tarefa real de produção | ❌ Não |

---

## Integração com docs

- Agentes: regras resumidas em [04-guia-agente-hermes.md](./04-guia-agente-hermes.md)
- SOUL: bloco em [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)
- Setup: mencionado no passo 10 de [02-setup-novo-projeto.md](./02-setup-novo-projeto.md)
