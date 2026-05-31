# Workspace e mapa de colegas

> **Obrigatório** para cross-bot funcionar bem.  
> Opcional: nomes padronizados ou modelos iguais — o que importa é **estrutura + conhecimento mútuo**.

## Workspace padronizado (obrigatório)

### Requisitos

| Requisito | Por quê |
|-----------|---------|
| Grupo Telegram **Fórum** (topics on) | Separa departamentos; visibilidade cross-bot por tópico |
| **Um tópico por agente/departamento** | Operador e bots sabem onde acionar quem |
| Todos os bots **admin** no grupo | Postar 📤/📥 de visibilidade |
| `chat_id` + `thread_id` documentados | Alimentam `topic-map.json` |

### Estrutura recomendada

```
Workspace (grupo fórum)
├── Tópico Geral / Coordenação     ← orquestração, avisos humanos
├── Tópico Departamento A          ← agente A responde aqui
├── Tópico Departamento B          ← agente B responde aqui
└── ...
```

**Não** é obrigatório ter nomes como `ops` ou `agent-alpha`. Use os nomes dos **departamentos reais** (Vendas, TI, Suporte…) — o que importa é a **ligação** profile ↔ tópico no `topic-map.json`.

### Descobrir IDs

1. Poste uma mensagem de teste no tópico
2. Leia `message_thread_id` via `getUpdates` ou logs do gateway
3. `chat_id` do grupo (ex: `-1003716565637`)

---

## topic-map.json — contrato técnico

Arquivo: `~/.hermes/plugins/kanban-context/topic-map.json`

```json
{
  "chat_id": "-100XXXXXXXXXX",
  "topics": {
    "profile-vendas": 640,
    "profile-ti": 669
  },
  "handles": {
    "profile-vendas": "bot_vendas_xyz",
    "profile-ti": "bot_ti_xyz"
  }
}
```

| Campo | Deve bater com |
|-------|----------------|
| Chave em `topics` / `handles` | Nome da pasta em `~/.hermes/profiles/` |
| `CROSSBOT_BOT_NAME` no `.env` | Mesma chave |
| `crossbot_send(to_bot="...")` | Mesma chave |
| `handles` | Username Telegram **sem** `@` |

---

## Mapa de colegas (obrigatório no SOUL)

Cada agente **deve** saber:

1. **Quem sou eu** — profile, @ Telegram, meu tópico
2. **Quem são os colegas** — profile, @, tópico, função
3. **Como acionar** — menção `@` no grupo vs `crossbot_send(profile)`

### Tabela para colar no SOUL de cada agente

Preencha com dados **reais** do inventário ([02-instalar-e-adaptar](./02-instalar-e-adaptar.md#caminho-a--adaptar-ambiente-existente)):

```markdown
## Mapa do workspace

**Eu:** profile `SEU_PROFILE` · @SEU_HANDLE · tópico NOME (thread ID)

### Colegas

| Profile (crossbot) | @ Telegram | Tópico (departamento) | Acionar quando |
|--------------------|------------|------------------------|----------------|
| colega-a | @handle_a | Nome tópico A | descreva a função |
| colega-b | @handle_b | Nome tópico B | descreva a função |

### Regras de acionamento

- **Humano no grupo:** mencione @handle no tópico correto
- **Bot → bot (delegação):** `crossbot_send(to_bot="profile-colega", ...)`
- **Não responda** se `[Response Coordination]` indicar que outro colega foi mencionado
- **Cross-bot:** endereço = nome do **profile**, não o @ Telegram
```

Template editável: [../reference/mapa-colegas.template.md](../reference/mapa-colegas.template.md)

---

## Dois tipos de comunicação

| Tipo | Quando | Como |
|------|--------|------|
| **Menção @** | Humano fala com um bot no workspace | `@handle pergunta` no tópico do departamento |
| **Cross-bot** | Bot delega a outro bot | `crossbot_send(to_bot="profile-colega", ...)` ou CLI |

Cross-bot **não** substitui menção humana — são canais complementares.

---

## Visibilidade 📤/📥

| Direção | Onde aparece |
|---------|--------------|
| 📤 envio | Tópico do **destinatário** (colega que vai processar) |
| 📥 resposta | Tópico do **respondedor** |

Operador humano acompanha no workspace sem abrir DMs.

---

## Checklist — adequar agente existente

- [ ] Profile já existe em `~/.hermes/profiles/`
- [ ] `CROSSBOT_BOT_NAME` = nome da pasta
- [ ] Entrada em `topic-map.json` (topics + handles)
- [ ] Tópico criado no workspace (se ainda não existia)
- [ ] SOUL atualizado com **mapa de colegas**
- [ ] Plugins habilitados + gateway reiniciado
- [ ] Smoke test com outro profile real

## Checklist — adicionar colega novo depois

- [ ] Novo profile Hermes (ou existente descoberto)
- [ ] Novo tópico no workspace
- [ ] Atualizar `topic-map.json`
- [ ] Atualizar SOUL de **todos** os agentes (tabela de colegas)
- [ ] Smoke test + opcional telefone sem fio

→ [04-guia-agente-hermes.md](./04-guia-agente-hermes.md)
