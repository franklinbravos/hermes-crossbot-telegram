# Guia do agente Hermes — Cross-bot e workspace

> Para agentes AI em ecossistema **já existente**. Nomes de profiles vêm do ambiente — não há padrão fixo.

## O que você precisa saber sobre si e os colegas

Antes de qualquer cross-bot, você deve ter no SOUL:

| Sobre mim | Sobre cada colega |
|-----------|-------------------|
| Nome do **profile** Hermes | Profile (endereço cross-bot) |
| @ Telegram | @ Telegram |
| **Tópico/departamento** no workspace | Tópico onde atua |
| Função | Quando acionar |

→ Template: [../reference/mapa-colegas.template.md](../reference/mapa-colegas.template.md)

**Cross-bot usa o profile**, não o @: `send vendas`, não `send @bot_vendas`.

## Receber trabalho

### Menção no workspace

Operador escreve `@seu_handle` **no seu tópico** → responda ali.

### Cross-bot

```
[Pending Messages]
- ID #71 From profile-colega — Assunto
```

→ `crossbot_cli respond` antes de `kanban_complete`.

## Responder cross-bot (OBRIGATÓRIO)

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond OUTBOX_ID "resposta"
```

**NUNCA:** `from kanban_context import ...` · só kanban_comment · DM sem pedido

## Enviar a um colega

Use o **profile** da tabela de colegas:

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send PROFILE_COLEGA "Assunto" "Corpo"
```

## Coordenação — não se perca

- `[Response Coordination]` diz que **outro** colega foi @mencionado → **silêncio**
- Você foi @mencionado ou é o bot do tópico → responda
- Dúvida sobre quem acionar → consulte mapa de colegas no SOUL

## Telefone sem fio

→ [05-telefone-sem-fio.md](./05-telefone-sem-fio.md)

## Contexto injetado

| Bloco | Significado |
|-------|-------------|
| `[Recent Group History]` | Histórico do workspace |
| `[Pending Messages]` | Cross-bot pendente |
| `[Response Coordination]` | Quem deve falar |

→ SOUL completo: [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md) · Workspace: [03-workspace-e-colegas.md](./03-workspace-e-colegas.md)
