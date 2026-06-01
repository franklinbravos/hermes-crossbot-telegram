# Handoff — Deploy e validação cross-bot

> **Redirecionamento:** use o **[onboarding guiado](./00-onboarding-guiado.md)** (etapas 1–10) em vez deste fluxo manual. Este documento permanece como referência histórica.

> **Para:** agente DevOps / operador do ambiente  
> **Versão alvo:** crossbot **0.5.2+** *(pré-release; v1.0 após validação)*

## Fluxo recomendado (substitui seções abaixo)

```bash
cd ~/hermes-crossbot-telegram && git pull
./scripts/bootstrap.sh --yes --onboarding
./scripts/crossbot-onboarding.sh current
./scripts/crossbot-onboarding.sh verify --watch 180
./scripts/crossbot-onboarding.sh advance
# repetir até step 10
./scripts/crossbot-debug-pack.sh pack
```

Doc: [00-onboarding-guiado.md](./00-onboarding-guiado.md) · steps em [steps/](./steps/)

---

## 1. Pull e deploy (legado)

```bash
cd ~/hermes-crossbot-telegram && git pull

grep '^version:' ~/hermes-crossbot-telegram/plugins/crossbot/plugin.yaml
# Esperado: 0.5.2 (pré-release)

chmod +x scripts/install.sh
./scripts/install.sh cross-bot

hermes gateway restart
```

Reinicie **todos** os gateways dos profiles ativos.

---

## 2. Inventário (ambiente existente)

Liste profiles **já instalados** — não crie agentes novos:

```bash
ls ~/.hermes/profiles/
```

- [ ] Tabela preenchida: profile · @ Telegram · tópico · função ([02-instalar-e-adaptar](./02-instalar-e-adaptar.md#caminho-a--adaptar-ambiente-existente))
- [ ] `topic-map.json` reflete os nomes **reais** das pastas
- [ ] SOUL de cada agente com [mapa de colegas](../reference/mapa-colegas.template.md)
- [ ] Workspace fórum com tópico por departamento ([03-workspace-e-colegas](./03-workspace-e-colegas.md))

---

## 3. Verificações pós-deploy

```bash
python3 -c "
import importlib.util, os
spec = importlib.util.spec_from_file_location(
    'kc', os.path.expanduser('~/.hermes/plugins/crossbot/__init__.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod.kanban_status())
"
```

Checklist:

- [ ] Versão **0.5.2+** no output
- [ ] `MULTI_AGENT_TG_DB_PATH` idêntico em todos os profiles
- [ ] Cada profile ativo tem `TELEGRAM_BOT_TOKEN` no `.env`
- [ ] Cada profile ativo tem `CROSSBOT_BOT_NAME` = nome do profile
- [ ] `topic-map.json` preenchido com chat_id e thread_ids reais
- [ ] `visibility-config.json` com `visibility_chat_id` correto

---

## 4. Atualizar instruções dos agentes

Colar o bloco de [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md) no SOUL/instructions de **cada** profile listado em `topic-map.json`.

---

## 5. Smoke test (substituído pelo onboarding step 6–9)

**Não** use `crossbot_cli` no worker Kanban — workers usam `kanban_complete`.

Onboarding step 6: `./scripts/crossbot-onboarding.sh run-action`  
Onboarding step 9: `./scripts/fui-ao-mercado.sh`

---

## Template de feedback

Use o zip de `./scripts/crossbot-debug-pack.sh pack` — não escreva relatório manual.

- Host / profiles
- Onboarding run_id (`crossbot-onboarding.sh status`)
- Versão plugin
- Zip anexo
