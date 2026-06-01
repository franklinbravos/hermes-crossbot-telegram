# Guia do agente Hermes — Cross-bot e workspace

> Para agentes AI em ecossistema **já existente**. Nomes de profiles vêm do ambiente — não há padrão fixo.

## O que você precisa saber sobre si e os colegas

Antes de qualquer cross-bot, você deve ter no SOUL:

| Sobre mim | Sobre cada colega |
|-----------|-------------------|
| Nome do **profile** Hermes | Profile |
| @ Telegram | @ Telegram |
| **Tópico/departamento** no workspace | Tópico onde atua |
| Função | Quando acionar |

→ Template: [../reference/mapa-colegas.template.md](../reference/mapa-colegas.template.md)

## Receber trabalho

### Menção no workspace

Operador escreve `@seu_handle` **no seu tópico** → responda ali.

### Cross-bot (mention relay)

```
[Pending Messages]
- ID #71 From profile-colega — mensagem com @mention ou delegação
```

→ **Responda naturalmente.** O plugin publica sua resposta no Telegram e fecha a outbox automaticamente. Depois chame `kanban_complete`.

## Delegar a um colega (caminho principal)

Na sua resposta, mencione o colega com `@handle` e descreva o pedido:

```
@bot_vendas prepara proposta para o cliente Acme até amanhã.
```

O plugin detecta a menção, cria outbox + task Kanban e acorda o colega. **Não** use CLI para o fluxo normal.

## Responder cross-bot

**Fluxo normal:** escreva a resposta no turno do worker — o plugin completa a outbox.

**Fallback avançado** (debug, telefone-sem-fio):

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/crossbot/crossbot_cli.py respond OUTBOX_ID "resposta"
```

**NUNCA:** `from kanban_context import ...` · só kanban_comment sem responder · DM sem pedido

## Enviar explicitamente (fallback)

Use o **profile** da tabela de colegas:

```bash
CROSSBOT_BOT_NAME=SEU_PROFILE python3 ~/.hermes/plugins/crossbot/crossbot_cli.py send PROFILE_COLEGA "Assunto" "Corpo"
```

Ou a tool `crossbot_send` quando disponível no toolset.

## Coordenação — não se perca

- `[Response Coordination]` diz que **outro** colega foi @mencionado → **silêncio**
- Você foi @mencionado ou é o bot do tópico → responda
- Dúvida sobre quem acionar → consulte mapa de colegas no SOUL

## Telefone sem fio

→ [05-fui-ao-mercado.md](./05-fui-ao-mercado.md) (benchmark — responda naturalmente; plugin publica no Telegram)

## Contexto injetado

| Bloco | Significado |
|-------|-------------|
| `[Recent Group History]` | Histórico do workspace |
| `[Pending Messages]` | Cross-bot pendente |
| `[Response Coordination]` | Quem deve falar |

→ SOUL completo: [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md) · Workspace: [03-workspace-e-colegas.md](./03-workspace-e-colegas.md)
