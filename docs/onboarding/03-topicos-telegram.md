# Tópicos Telegram — Estrutura e comunicação

## Por que fórum com tópicos

Vários agentes postam visibilidade cross-bot no mesmo grupo. Tópicos separam por agente:

```
Grupo Fórum
├── Tópico ops (coordenação)
├── Tópico agent-alpha
├── Tópico agent-beta
└── ...
```

## topic-map.json

```json
{
  "chat_id": "-100XXXXXXXXXX",
  "topics": {
    "ops": 669,
    "agent-alpha": 637
  },
  "handles": {
    "ops": "seu_bot_ops",
    "agent-alpha": "seu_bot_alpha"
  }
}
```

| Campo | Regra |
|-------|-------|
| Chave | Nome do **profile** Hermes |
| `topics` | `message_thread_id` do fórum |
| `handles` | Username **sem** `@` |

Modelo: [../reference/topic-map.example.json](../reference/topic-map.example.json)

## Dois tipos de comunicação

### A) Menção @bot

Operador humano menciona um bot → resposta no grupo. Usa histórico injetado, **não** outbox.

### B) Cross-bot

Bot A chama `crossbot_send(to_bot="agent-beta")` → outbox → worker → 📤/📥 no Telegram.

## Coordenação multi-bot

Plugin injeta `[Response Coordination]`:

- Responda se **foi @mencionado** ou é bot do tópico
- **Não responda** se outro bot foi mencionado

## Checklist — bot novo

- [ ] Profile + `.env` (token, CROSSBOT_BOT_NAME)
- [ ] Tópico no fórum
- [ ] Entrada em topic-map.json
- [ ] Bot admin no grupo
- [ ] Plugins habilitados + restart
- [ ] Smoke test cross-bot
- [ ] SOUL com [AGENT-SYSTEM-PROMPT.md](./AGENT-SYSTEM-PROMPT.md)

→ [04-guia-agente-hermes.md](./04-guia-agente-hermes.md)
