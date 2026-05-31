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

## 3. COMO FAZER CADEIA AUTÔNOMA (telefone sem fio)

Quando precisar encaminhar uma mensagem para o próximo bot na cadeia,
**COPIE a instrução inteira** que recebeu, atualize:
- FRASE ATUAL: adicione suas 2 palavras
- QUEM JOGOU: adicione seu nome
- QUEM FALTA: remova seu nome
- Escolha aleatoriamente um da lista QUEM FALTA
- Se QUEM FALTA ficar vazia, envie para "ti" em vez de um agente

**Formato que FUNCIONA (validado em produção):**
```
📞 TELEFONE SEM FIO — JOGO ENTRE AGENTES

REGRAS OBRIGATÓRIAS:
1. Adicione EXATAMENTE DUAS palavras à frase abaixo
2. NÃO mude ou remova palavras existentes
3. Escolha ALEATORIAMENTE um agente da lista QUEM FALTA
4. Se QUEM FALTA estiver vazia, envie para Matias (bot: ti)
5. Use crossbot_cli.py via terminal para enviar ao próximo

FRASE ATUAL: <frase aqui>
QUEM JOGOU: [lista de quem já jogou]
QUEM FALTA: [lista de quem ainda não jogou]

SUA VEZ! Adicione 2 palavras à frase.

COMO ENVIAR AO PRÓXIMO (use terminal):
CROSSBOT_BOT_NAME=<SEU_NOME_BOT> python3 ~/.hermes/plugins/kanban-context/crossbot_cli.py send <PROXIMO_BOT> "Telefone sem fio" "<COPIE_ESTA_INSTRUÇÃO_COMPLETA>"

IMPORTANTE: COPIE TODA esta instrução no body, atualizando frase e listas.
```

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
❌ **Não mude palavras existentes** — em jogos de telefone sem fio, só adicione
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
