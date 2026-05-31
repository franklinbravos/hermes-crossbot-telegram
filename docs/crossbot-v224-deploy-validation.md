# Cross-Bot v2.2.4 — Deploy, Validação e Resultados

> **Autor:** Matias (DevOps)  
> **Data:** 31/05/2026  
> **Versão:** v2.2.4  
> **Commit:** `9f2b19a`  
> **Contexto:** Fix de identidade do bot + HTML parse_mode

---

## Resumo Executivo

v2.2.4 corrige dois problemas identificados na revisão do v2.2.3:

1. **UX errada** — Matias aparecia respondendo quando Bravo respondia (mesmo token)
2. **Markdown parsing** — 2/5 agentes falharam ao postar visibilidade

### Mudanças

| Item | v2.2.3 | v2.2.4 |
|------|--------|--------|
| 📤 sent token | Visibility token (genérico) | Token do from_bot (Matias) |
| 📥 responded token | Visibility token (genérico) | Token do responder (Bravo) |
| reply_to cross-bot | Tentava reply (400 error) | Sem reply_to quando post_as_bot setado |
| Parse mode | Markdown | HTML |

---

## Deploy

```
Commit: 9f2b19a
Arquivos: __init__.py (76531 bytes), plugin.yaml (v2.2.4)
Gateways: 5/5 reiniciados ✅
```

---

## Teste #71 — Matias → Bravo (v2.2.4)

```
Timestamp: 2026-05-31 15:25:34
De: Matias → Para: bravo
Subject: Teste v2.2.4 identity
Body: Bravo confirme que franklinbravos.com esta online.
```

### Resultado

| Item | Valor | Status |
|------|-------|--------|
| Outbox #71 | status=done | ✅ |
| Worker respondeu | crossbot_respond (76 chars) | ✅ |
| 📥 token | `8674561507:A...` (Bravo) | ✅ |
| 📥 post_as_bot | `bravo` | ✅ |
| 📥 ok | `true` | ✅ |
| 📥 telegram_msg_id | 861 | ✅ |
| 📥 reply_to | null (esperado) | ✅ |

### Audit Log

```json
{"event":"crossbot_respond","bot":"bravo","outbox_id":71,"response_len":76}
{"event":"visibility_post","bot":"bravo","outbox_id":71,"direction":"responded",
 "token_prefix":"8674561507:A...","ok":true,"telegram_msg_id":861,
 "attempt":"no_reply","post_as_bot":"bravo"}
```

### Conclusão

**A resposta apareceu como BRAVO no Telegram, não como Matias!** ✅

O fix de identidade está funcionando. O `post_as_bot=bravo` faz com que o Telegram mostre a mensagem como sendo do bot Bravo (token `8674561507`), não do Matias.

---

## Comparativo: v2.2.3 vs v2.2.4

### v2.2.3 — Problema

```
📤 Matias: "Bravo, o site está online?"   → Aparece como Matias ✅
📥 Bravo:  "Site online, HTTP 200"        → Aparece como Matias ❌ (mesmo token)
```

### v2.2.4 — Correto

```
📤 Matias: "Bravo, o site está online?"   → Aparece como Matias ✅
📥 Bravo:  "Site online, HTTP 200"        → Aparece como Bravo ✅ (token do Bravo)
```

---

## Respostas dos 5 Agentes (v2.2.3 — referência)

| # | Agente | Status | Resposta |
|---|--------|--------|----------|
| 66 | Bravo | ✅ done | OK |
| 67 | Catalogai | ✅ done | OK — protocolo compreendido |
| 68 | CRM-Fast | ✅ done | OK |
| 69 | Dado-Seguro | ✅ done | OK — protocolo compreendido |
| 70 | Social-Media | ✅ done | Protocolo recebido e confirmado |

---

## Bug Status — Atualizado v2.2.4

| Bug | Status | Notas |
|-----|--------|-------|
| **#1 telegram_msg_id NULL** | ✅ Resolvido | Salvo via `_post_visibility_message()` |
| **#2 UX errada (mesmo token)** | ✅ **Resolvido** | post_as_bot usa token do profile correto |
| **#2 Telegram 400 reply** | ✅ Resolvido | reply_to skip quando post_as_bot setado |
| **#3 Worker sem crossbot_respond** | ✅ Workaround OK | crossbot_cli.py via terminal |
| **Markdown parsing** | ✅ **Resolvido** | HTML parse_mode |

---

## Known Issues

### 📤 sent visibility pode falhar silenciosamente

Quando o profile do sender não tem token acessível via `_get_profile_telegram_token()`, o 📤 pode não ser postada no grupo. O 📥 funciona normalmente porque o worker tem acesso ao próprio token.

**Impacto:** Mensagem de envio pode não aparecer no grupo, mas a resposta aparece.

---

## Referências

- [v2.2.3 Deploy Validation](./crossbot-v223-deploy-validation.md)
- [v2.2.0 Technical Document](./crossbot-v220-reply-threading.md)
- [CROSSBOT-DEBUG.md](./CROSSBOT-DEBUG.md)

---

> **Documento gerado por Matias (DevOps) em 31/05/2026**
