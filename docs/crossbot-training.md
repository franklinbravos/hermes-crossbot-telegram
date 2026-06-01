# 📞 Treinamento: Comunicação Bot-a-Bot via Crossbot

## Visão Geral

Cada bot do ecossistema Franklin Bravos pode enviar mensagens para outros bots
e receber mensagens deles. Tudo acontece via o plugin kanban-context.

**Bots disponíveis:** bravo, catalogai, crm-fast, dado-seguro, social-media, ti

---

## 1. COMO RECEBER uma mensagem de outro bot

Quando outro bot te envia uma mensagem, o Hermes cria uma **kanban task** pra você.
O worker lê a task e processa.

**Na task body, você vai ver:**
```
[CROSS-BOT MESSAGE #XX]
From: nome_do_remetente
To: seu_nome
Subject: assunto

<corpo da mensagem>

---
INSTRUCTION TO WORKER:
1. Process the message content above
2. Reply by calling crossbot_respond(XX, "your response")
...
```

**Para responder:** use o `crossbot_cli.py` via terminal:
```bash
CROSSBOT_BOT_NAME=SEU_BOT_NAME python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond XX "sua resposta aqui"
```

**IMPORTANTE:**
- Substitua `SEU_BOT_NAME` pelo seu nome de bot (ex: `bravos_consult_bot`)
- Substitua `XX` pelo número do outbox (vem na task body)
- Responda ANTES de marcar a task como done

---

## 2. COMO ENVIAR uma mensagem para outro bot

```bash
CROSSBOT_BOT_NAME=SEU_BOT_NAME python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send DESTINATARIO "Assunto" "Corpo da mensagem"
```

**Exemplo:**
```bash
CROSSBOT_BOT_NAME=bravos_consult_bot python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send catalogai "Verificar pedido" "Catalogai, verifique o status do pedido #12345 e me retorne."
```

**Destinatários válidos:** bravo, catalogai, crm-fast, dado-seguro, social-media, ti

---

## 3. BENCHMARK — Fui ao mercado / Fui à feira

Brincadeira em cadeia: cada bot **repete a frase inteira** e acrescenta **um item**.

**Chamada natural (boot):** *"Joga fui ao mercado com o time."*

**Papéis — não confunda:**
- **Coordenador:** inicia e, no fim, reporta tempo + sucesso 100%
- **Jogador:** só repete + 1 item + repassa ao próximo da fila
- **Não** trate como suporte, ticket ou tarefa de cliente

**Formato no body da mensagem (FUI_AO_MERCADO):**
```
phrase: Fui ao mercado e comprei uma maçã e um sabão
chain_order: bot-a,bot-b,bot-c
step: 2
next: bot-c
status: IN_PROGRESS
```

**Sua vez:**
1. Leia `phrase` — repita **sem mudar** palavras existentes
2. Acrescente **um** item: `… e um pão`
3. Repasse ao `next` (mention @ ou crossbot)
4. Atualize step, played, phrase no body para o próximo

**Último jogador:** envia ao coordenador com `status: COMPLETE`

**Relatório:** `~/hermes-crossbot-telegram/scripts/benchmark-report.sh <ROUND>`

❌ Não mude palavras já ditas  
❌ Não pule colegas da `chain_order`  
❌ Não invente outra missão

---

## 4. NOMES DE BOT (para CROSSBOT_BOT_NAME)

| Profile | CROSSBOT_BOT_NAME |
|---------|-------------------|
| ti | matias_bravos_dev_bot |
| bravo | bravos_consult_bot |
| catalogai | catalogai_agent_bot |
| crm-fast | CRM_fast_combr_bot |
| dado-seguro | DadoSeguroBot |
| social-media | SocialMediaBravosBot |

---

## 5. ERROS COMUNS (NÃO FAÇA)

❌ **Não use o literal "ESCOLHA" como destinatário** — é um placeholder, substitua pelo nome real do bot
❌ **Não trunque o body** — quando encaminhar, COPIE a instrução inteira
❌ **Não mude palavras existentes** — em *fui ao mercado*, só acrescente um item no final
❌ **Não responda sem usar crossbot_cli.py** — responder normalmente não registra no outbox
❌ **Não use @mentions em mensagens cross-bot** — causa HTTP 400
❌ **Não tente importar kanban_context diretamente** — use o crossbot_cli.py via terminal
❌ **Não use formato curto** — instruções curtas fazem workers ignorarem o encaminhamento

---

## 6. FLUXO COMPLETO (exemplo)

1. **Matias** envia pro **Bravo**: "Verifique o site franklinbravos.com"
2. **Bravo** recebe kanban task com outbox_id
3. **Bravo** processa e responde via `crossbot_cli.py respond XX "Site online, HTTP 200"`
4. A resposta aparece no tópico do Bravo no grupo Telegram
5. **Bravo** pode também enviar pro **Catalogai**: `crossbot_cli.py send catalogai "Verificar" "Catalogai, analise o SEO do site"`
6. **Catalogai** recebe e processa

---

## 7. VALIDAÇÃO — Telephone Game (2026-05-31)

### Jogo 1 — "GATO BONITO"
```
Matias → Bravo → Dado-Seguro → CRM-Fast → Catalogai → Social-Media → TI
GATO BONITO → +DANÇA SAMBA → +COM ESTILO VIRA MODA → +VIROU FEBRE → +E CONTAGIOU → +ATRAI ENGAJA → +SERVIDOR ESTÁVEL
```

### Jogo 2 — "O REI RUEU"
```
Matias → Bravo → Catalogai → Social-Media → CRM-Fast → Dado-Seguro → TI
O REI RUEU → +COM RAIVA → +E GRITOU → +E ORDENOU → +QUE PRENDESSEM → +O BANDIDO → +MALVADO
```

**6 de 6 agentes participaram autonomamente em ambos os jogos!** ✅

---

## 8. REFERÊNCIA RÁPIDA

**Receber + responder:**
```bash
CROSSBOT_BOT_NAME=SEU_NOME python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py respond OUTBOX_ID "resposta"
```

**Enviar para outro bot:**
```bash
CROSSBOT_BOT_NAME=SEU_NOME python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send DESTINATARIO "Assunto" "Mensagem"
```

**Pronto! Agora você sabe se comunicar com qualquer bot do ecossistema.** 🚀
