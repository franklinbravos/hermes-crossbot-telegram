# Handoff — Deploy e validação cross-bot

> **Para:** agente DevOps / operador do ambiente  
> **Versão alvo:** kanban-context **2.3.0+**

Execute este documento **do início ao fim**. Ao terminar, preencha o [template de feedback](#template-de-feedback) e envie ao operador humano.

**Documentação relacionada:** [02-setup-novo-projeto.md](./02-setup-novo-projeto.md) · [05-telefone-sem-fio.md](./05-telefone-sem-fio.md) · [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)

---

## 1. Pull e deploy

```bash
cd ~/hermes-community-plugins && git pull

grep '^version:' ~/hermes-community-plugins/plugins/kanban-context/plugin.yaml
# Esperado: 2.3.0 ou superior

chmod +x scripts/install.sh
./scripts/install.sh cross-bot

hermes gateway restart
```

Reinicie **todos** os gateways dos profiles ativos.

---

## 2. Verificações pós-deploy

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

Checklist:

- [ ] Versão **2.3.0+** no output
- [ ] `MULTI_AGENT_TG_DB_PATH` idêntico em todos os profiles
- [ ] Cada profile ativo tem `TELEGRAM_BOT_TOKEN` no `.env`
- [ ] Cada profile ativo tem `CROSSBOT_BOT_NAME` = nome do profile
- [ ] `topic-map.json` preenchido com chat_id e thread_ids reais
- [ ] `visibility-config.json` com `visibility_chat_id` correto

---

## 3. Atualizar instruções dos agentes

Colar o bloco de [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md) no SOUL/instructions de **cada** profile listado em `topic-map.json`.

- [ ] Orchestrator (profile que inicia telefone sem fio)
- [ ] Demais profiles jogadores

Atualize a tabela de bots no prompt com os profiles **deste** ambiente.

---

## 4. Smoke test (cross-bot simples)

Substitua `{ORIGEM}` e `{DESTINO}` pelos profiles reais (ex: primeiro e segundo da lista):

```bash
CROSSBOT_BOT_NAME={ORIGEM} python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py \
  send {DESTINO} "Smoke test v224" "Confirme recebimento — identidade correta no Telegram"
```

**Esperado:**

| # | Verificação |
|---|-------------|
| 1 | 📤 no Telegram com nome do bot **{ORIGEM}** |
| 2 | Worker {DESTINO} responde via crossbot_cli |
| 3 | 📥 no Telegram com nome do bot **{DESTINO}** (não o remetente) |
| 4 | Outbox `status=done` |
| 5 | Audit log sem erro Markdown |

```bash
tail -10 ~/.hermes/logs/kanban-context/crossbot-audit.jsonl

sqlite3 ~/.hermes/data/multi_agent_tg_shared.db \
  "SELECT id, from_bot, to_bot, status FROM outbox ORDER BY id DESC LIMIT 3;"
```

Anote o **outbox ID** do smoke test: ___________

---

## 5. Telefone sem fio (benchmark oficial)

Leia [05-telefone-sem-fio.md](./05-telefone-sem-fio.md) antes de executar.

### Papéis neste ambiente

Preencha antes de rodar:

| Papel | Profile neste ambiente |
|-------|------------------------|
| Orchestrator | `{ORCHESTRATOR}` |
| Roster (jogadores) | `{ROSTER}` |

Exemplo de roster: `ops,web,catalog,crm,data,social` — todos em `topic-map.json` **exceto** o orchestrator.

### Orchestrator — iniciar

**Comando rápido (recomendado):**

```bash
PHRASE="O rato roeu" ./scripts/telefone-sem-fio.sh
```

Ou manualmente (ver bloco abaixo se precisar customizar roster).

### Cada jogador (automático via workers)

Regras — ver doc 05:

1. +2 palavras à `phrase`
2. Atualizar `played`
3. Sortear próximo de `roster - played`
4. Se sobrou → repassar | Se não → enviar para `{ORCHESTRATOR}` com `status: COMPLETE`
5. `crossbot_cli respond` **antes** de `kanban_complete`

### Orchestrator — reportar ao operador humano

Quando receber `status: COMPLETE`, monte o relatório usando o [template de feedback](#template-de-feedback).

Métricas:

```bash
grep TelefoneSemFio ~/.hermes/logs/kanban-context/crossbot-audit.jsonl | tail -20
```

---

## 6. Template de feedback

Copie, preencha e envie ao operador humano:

```markdown
## Handoff deploy — feedback

**Data:**
**Commit:** $(cd ~/hermes-community-plugins && git log -1 --oneline)
**Ambiente:** (descreva brevemente)

### Deploy
- [ ] git pull OK
- [ ] plugin.yaml >= 2.3.0
- [ ] Gateways reiniciados: (listar)
- [ ] /kanban-status OK

### Smoke test
- Outbox ID:
- 📤 remetente correto? (sim/não — qual bot apareceu)
- 📥 respondedor correto? (sim/não)
- Outbox status=done?

### Telefone sem fio
- Round ID:
- Frase inicial:
- Frase final:
- Ordem dos jogadores:
- Duração total:
- Latência média por salto:
- Algum bot falhou? Qual?
- Audit log OK?

### SOUL atualizado
- [ ] (listar profiles atualizados)

### Observações
(livre)
```

---

## Referências rápidas

| Item | Path |
|------|------|
| Hub docs | `docs/README.md` |
| Debug | `docs/reference/debug-crossbot.md` |
| Audit log | `~/.hermes/logs/kanban-context/crossbot-audit.jsonl` |
| Outbox DB | `~/.hermes/data/multi_agent_tg_shared.db` |
