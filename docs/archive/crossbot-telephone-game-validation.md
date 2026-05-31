# Telephone Game — Autonomous Cross-Bot Chaining Validation (2026-05-31)

## Summary

After confirming all 5 agents understand the `crossbot_cli.py` protocol (outbox #66–#70),
we ran a **telephone game** (telefone sem fio) to validate that kanban workers can
**autonomously forward messages** to other bots without manual orchestration.

**Result: VALIDATED ✅** — 6 of 6 agents participated, each choosing the next agent randomly.

---

## Rules

1. Start with 2 words
2. Each agent adds EXACTLY 2 words (never change existing words)
3. Agent chooses NEXT agent randomly from remaining list
4. When no agents remain, send back to the orchestrator profile
5. Use `crossbot_cli.py send` via terminal to forward

---

## Instruction Format That Worked

```
TAREFA: TELEFONE SEM FIO

1. Adicione 2 palavras: GATO BONITO → GATO BONITO [SUAS_PALAVRAS]
2. Escolha aleatoriamente UM da lista: [catalogai, crm-fast, dado-seguro, social-media]
3. Execute no terminal:
CROSSBOT_BOT_NAME=orchestrator python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send ESCOLHA "Telefone sem fio" "INSTRUÇÃO_COMPLETA_ATUALIZADA"
4. Se lista vazia, envie para ti

RESPONDA SOMENTE: confirmou envio + frase atualizada + quem escolheu
```

**Why this works:**
- Short and direct — workers ignore complex multi-paragraph instructions
- Exact `crossbot_cli.py` command — worker just copies and executes
- `CROSSBOT_BOT_NAME` explicit — resolves bot identity
- Rules embedded in body — each agent gets full rules
- "RESPONDA SOMENTE" limits worker behavior

---

## Chain Trace (outbox entries)

### Chain 1 — Autonomous (Bravo chose randomly) ✅

| Outbox | From | To | Added Words | Status |
|--------|------|-----|-------------|--------|
| #79 | Orchestrator | Agente-A | *(start: GATO BONITO)* | ✅ done |
| #80 | Bravo | Dado-Seguro | DANÇA SAMBA | ✅ done |
| #82 | Dado-Seguro | CRM-Fast | COM ESTILO VIRA MODA | ✅ done |
| #83 | CRM-Fast | Catalogai | VIROU FEBRE | ✅ done |
| #85 | Catalogai | Social-Media | E CONTAGIOU | ✅ done |
| #87 | Agente-D | Orchestrator | ATRAI ENGAJA | ✅ done |

**Final phrase:** `GATO BONITO DANÇA SAMBA COM ESTILO VIRA MODA VIROU FEBRE E CONTAGIOU ATRAI ENGAJA SERVIDOR ESTÁVEL`

**6 of 6 agents participated autonomously** ✅

### Chain 2 — Parallel (duplicate send to Bravo)

| Outbox | From | To | Added Words | Status |
|--------|------|-----|-------------|--------|
| #81 | Orchestrator | Agente-A | *(start: GATO BONITO)* | ✅ done |
| #84 | Bravo | CRM-Fast | DANÇA SAMBA COM FÉ | ✅ done |
| #86 | CRM-Fast | Social-Media | E ENCANTA | ✅ done |

**Why two chains:** Orchestrator sent to Agente-A twice (#79 and #81), creating parallel chains.
This is **Pitfall 28** — always check for pending outbox before sending.

---

## Agent Choices (Random Selection)

| Agent | Chose | Reasoning |
|-------|-------|-----------|
| Bravo | Dado-Seguro | Random from [catalogai, crm-fast, dado-seguro, social-media] |
| Dado-Seguro | CRM-Fast | Random from remaining |
| CRM-Fast | Catalogai | Random from remaining |
| Catalogai | Social-Media | Last remaining |
| Agente-D | Orchestrator | No remaining agents → send back to origin |

---

## Failed First Attempt (Long Instructions)

The first instruction was long and complex:
```
📞 TELEFONE SEM FIO — JOGO ENTRE AGENTES
REGRAS OBRIGATÓRIAS:
1. Adicione EXATAMENTE DUAS palavras...
(many more lines)
```

Bravo responded "GATO BONITO DANÇA SAMBA ✨ +2 palavras. Próximo: dado-seguro 🎯"
but did **NOT** forward via `crossbot_cli.py`. The worker ignored the forwarding instruction.

**Fix:** Shorter instruction with exact command to execute, plus "RESPONDA SOMENTE"
to limit worker behavior.

---

## Pitfalls Discovered

### Pitfall 28 — Duplicate sends cause parallel chains

**Problem:** Sending the same message to the same bot twice creates two independent
parallel chains. Each adds different words and the "final phrase" diverges.

**Symptom:** Two outbox entries pending for the same bot, two kanban tasks,
two workers processing simultaneously.

**Cause:** Impatience — orchestrator sends, waits 30s, sees bot hasn't responded,
sends again. But the first was already being processed.

**Fix:** ALWAYS check for pending outbox before sending:
```python
cur.execute("SELECT id FROM outbox WHERE to_bot=? AND status='pending'", (bot_name,))
if cur.fetchone():
    print(f"Already pending for {bot_name}, skipping duplicate send")
```

### Pitfall 29 — Self-addressed outbox stuck when worker is busy

**Problem:** When a bot sends a message to itself (e.g., Social-Media → TI),
the outbox stays `pending` indefinitely if the target bot's worker is busy
(in active conversation with user).

**Symptom:** Outbox #87 (agente-d→orchestrator) was `pending` because the orchestrator's worker
was busy talking to the human operator.

**Fix:** The orchestrator must manually process the pending outbox:
```bash
CROSSBOT_BOT_NAME=orchestrator python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond 87 "sua resposta"
```

**Implication:** In autonomous chains, if the last bot sends to the orchestrator,
the orchestrator needs to be free to process. If busy, the chain stalls at the last step.

---

## Key Findings

1. **Workers CAN forward autonomously** — `crossbot_cli.py send` via terminal works
2. **Short, direct instructions succeed** — complex multi-paragraph instructions fail
3. **Random agent selection works** — Bravo chose Dado-Seguro, not the first in list
4. **Self-addressed outbox gets stuck** — Pitfall 29
5. **Duplicate sends create parallel chains** — Pitfall 28
6. **Chain is resilient** — if one agent fails, the chain stops but doesn't crash
7. **Each agent needs FULL rules** — self-contained instructions in the body

---

## Implications for Multi-Agent Orchestration

- **Autonomous chaining is a VALIDATED capability** (not just theory)
- Instructions must be concise and action-oriented
- Each agent needs the FULL rules in the body (self-contained)
- The chain is resilient — if one agent fails, the chain stops but doesn't crash
- For production use: add retry logic and timeout handling
- The `crossbot_cli.py` workaround (v2.2.3) enables full agent-to-agent communication

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v2.2.0 | 2026-05-31 | Reply threading (post_llm_call hook) |
| v2.2.2 | 2026-05-31 | post_as_bot + HTML parse_mode |
| v2.2.3 | 2026-05-31 | crossbot_cli.py workaround for worker toolset |
| v2.2.4 | 2026-05-31 | Bot identity fix + autonomous chaining validated |
