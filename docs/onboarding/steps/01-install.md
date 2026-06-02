# Step 1 — Instalar plugin

## Ação

```bash
cd ~/hermes-crossbot-telegram
./scripts/bootstrap.sh --yes
```

Ou só o plugin: `./scripts/install.sh cross-bot`

## Gate (verify)

- `plugin.yaml` version >= **0.6.0**
- Hooks: `pre_llm_call`, `post_llm_call`, **`post_tool_call`**
- Instruções worker **não** exigem `crossbot_cli` obrigatório

```bash
./scripts/crossbot-onboarding.sh verify
```

## Falhas comuns

- Versão antiga em `~/.hermes/plugins/crossbot` → `bootstrap.sh --yes` ou `auto-update.sh --restart`
- Hook `post_tool_call` ausente → copiar plugin do repo atual
