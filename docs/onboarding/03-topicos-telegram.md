# Tópicos Telegram — Estrutura e comunicação

> Como organizar o grupo fórum para que humanos e bots não se percam.

## Por que usar fórum com tópicos

Num grupo Hermes multi-bot, **vários agentes** postam visibilidade cross-bot e respondem menções. Sem tópicos, tudo vira um feed caótico.

Com fórum:

```
Grupo "Workspace - Hermes"
├── 📌 Geral (tópico 669)     ← Matias / TI / coordenação
├── 📌 Bravo (637)            ← tudo do bot Bravo
├── 📌 Catalogai (638)
├── 📌 CRM-Fast (640)
└── ...
```

Cada mensagem cross-bot vai para o **tópico do bot envolvido** — fácil de filtrar.

## Mapa mental

```
                    ┌─────────────────────────┐
                    │   Grupo Fórum Telegram   │
                    │   chat_id: -100...       │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   Tópico Matias            Tópico Bravo           Tópico CRM
   thread_id: 669           thread_id: 637         thread_id: 640
        │                       │                       │
   @matias_bravos_dev_bot  @bravos_consult_bot    @CRM_fast_combr_bot
        │                       │                       │
   profile: matias          profile: bravo         profile: crm-fast
```

## topic-map.json — contrato entre Telegram e Hermes

Arquivo: `~/.hermes/plugins/kanban-context/topic-map.json`

```json
{
  "comment": "Mapeamento bot → tópico e handle",
  "chat_id": "-1003716565637",
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

### Regras de ouro

| Regra | Exemplo |
|-------|---------|
| Chave = nome do **profile** Hermes | `"bravo"` → `profiles/bravo/` |
| `topics[bot]` = ID numérico do tópico | Copie do Telegram (DevTools ou bot getUpdates) |
| `handles[bot]` = username **sem** `@` | `bravos_consult_bot` |
| Todo bot novo precisa de **entrada aqui** | Sem entrada → posta no thread default ou falha |

### Como descobrir thread_id

1. Poste uma mensagem no tópico desejado
2. Use `getUpdates` na API do bot ou logs do gateway
3. Campo: `message.message_thread_id`

## Dois tipos de comunicação no grupo

### A) Menção normal (@bot)

```
Franklin: @bravos_consult_bot o site está no ar?
Bravo: Sim, HTTP 200 ✅
```

- Fluxo: Telegram → gateway Bravo → LLM → resposta no **mesmo tópico**
- **Não** usa outbox cross-bot
- `multi-agent-context` injeta histórico do grupo no contexto

### B) Cross-bot (bot → bot)

```
Matias (internamente): crossbot_send(to_bot="bravo", ...)
  → 📤 aparece no tópico 637 (Bravo)
  → Worker Bravo processa
  → 📥 resposta aparece no tópico 637 como @bravos_consult_bot
```

- Fluxo: outbox → Kanban worker → crossbot_cli respond
- Humanos veem espelho 📤/📥
- Remetente correto no Telegram (v2.2.4)

## Quando usar cada um

| Situação | Use |
|----------|-----|
| Franklin pergunta algo a um bot | Menção `@bot` |
| Matias delega tarefa ao Bravo | `crossbot_send` |
| Bot precisa de outro bot sem humano no meio | `crossbot_send` |
| Resposta a mensagem cross-bot | `crossbot_cli respond` (worker) |

## Coordenação multi-bot (evitar todos responderem)

O plugin injeta `[Response Coordination]` no contexto quando vários bots estão no mesmo grupo:

- Só responde quem foi **@mencionado**
- Ou quem recebeu **reply** direto
- Ou quem é o bot **designado** para aquele tópico (via topic-map)

**Para humanos:** mencione sempre o bot certo. Evite perguntas abertas tipo "alguém pode verificar?" sem @.

**Para bots:** siga [04-guia-agente-hermes.md](./04-guia-agente-hermes.md) — não responda se outro bot foi mencionado.

## Visibilidade cross-bot — o que aparece

### 📤 Envio (remetente posta)

```
📤 @matias_bravos_dev_bot

From: matias
To: bravo
Subject: Status do site

O site está no ar?

└ outbox #71
```

Postado no **tópico do destinatário** (Bravo = 637).

### 📥 Resposta (respondedor posta)

```
📥 @bravos_consult_bot

Re: Status do site
Para @matias_bravos_dev_bot

Site online, HTTP 200

└ outbox #71
```

Postado no **tópico do respondedor**.

## Checklist ao adicionar bot novo

- [ ] Criar profile Hermes (`profiles/novo-bot/`)
- [ ] Token Telegram no `.env` do profile
- [ ] `CROSSBOT_BOT_NAME=novo-bot`
- [ ] Criar tópico no fórum Telegram
- [ ] Adicionar entrada em `topic-map.json` (topics + handles)
- [ ] Adicionar bot ao grupo como admin
- [ ] Habilitar plugins no `config.yaml`
- [ ] Reiniciar gateway
- [ ] Teste: `crossbot_send` de Matias → novo-bot
- [ ] Colar [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md) no SOUL

## Próximo passo

→ [Guia do agente Hermes](./04-guia-agente-hermes.md) — regras que cada bot deve seguir.
