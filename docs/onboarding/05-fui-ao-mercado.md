# Fui ao mercado — benchmark cross-bot

> **Modelo unificado:** [05-benchmark-cadeia.md](./05-benchmark-cadeia.md) — mesmo motor para mercado, feira e telefone sem fio.

> Brincadeira clássica + teste oficial. Mede se **todos os bots** repetem a frase, somam um item e repassam **sem confundir o papel**.

## Chamar de forma natural (boot / chat)

Não precisa citar script. Diga ao **coordenador** (orchestrator):

```
Vamos testar se os bots se falam? Joga "fui ao mercado" com todo mundo do time.
```

Ou:

```
Inicia o teste da feira — quero ver se a frase chega completa no final e quanto tempo leva.
```

O coordenador roda o script (ou o Hermes executa):

```bash
~/hermes-crossbot-telegram/scripts/fui-ao-mercado.sh
```

Variante feira:

```bash
LOJA=feira ./scripts/fui-ao-mercado.sh
```

---

## O jogo

1. O **coordenador** abre: *"Fui ao mercado e comprei uma maçã"* (item sorteado).
2. Cada **jogador**, na ordem fixa do roster, deve:
   - repetir a frase **inteira**;
   - acrescentar **só um** item no final;
   - repassar ao próximo da fila.
3. O **último jogador** devolve ao coordenador com `status: COMPLETE`.
4. O **coordenador** reporta ao humano: duração, sucesso 100% ou onde parou.

Exemplo de evolução:

```
Fui ao mercado e comprei uma maçã
Fui ao mercado e comprei uma maçã e um sabão
Fui ao mercado e comprei uma maçã e um sabão e um pão
…
```

---

## Papéis (para não confundir)

| Quem | O que faz | O que **não** faz |
|------|-----------|-------------------|
| **Coordenador** | Inicia a rodada; ao receber COMPLETE, manda relatório com tempo | Não entra no meio da lista como jogador |
| **Jogador N** | Repete frase + 1 item + repassa ao próximo | Não muda assunto, não abre ticket, não pula colega |
| **Humano** | Pede o teste; lê o relatório | Não precisa digitar bash se o Hermes executa |

Cada mensagem do benchmark traz um bloco **=== SEU PAPEL ===** — só siga isso.

---

## Comandos

```bash
chmod +x scripts/configure-crossbot.sh scripts/fui-ao-mercado.sh scripts/benchmark-report.sh
./scripts/configure-crossbot.sh
./scripts/setup-crossbot-board.sh
./scripts/fui-ao-mercado.sh
```

**Relatório (tempo + sucesso):**

```bash
./scripts/benchmark-report.sh              # última rodada
./scripts/benchmark-report.sh 20260531-1430
```

Saída esperada:

```
  Duração total:    2m 34s
  Sucesso:          ✅ 100%
```

JSON salvo em: `~/.hermes/logs/crossbot/benchmark-<ROUND>.json`

**Acompanhar ao vivo:**

```bash
tail -f ~/.hermes/logs/crossbot/crossbot-audit.jsonl | grep FuiAoMercado
```

---

## Formato técnico (referência)

**Subject:** `[FuiAoMercado] round=<ID>`

Campos no body:

| Campo | Significado |
|-------|-------------|
| `round` | ID da rodada |
| `started_at` / `started_epoch` | Início (para duração) |
| `phrase` | Frase acumulada |
| `chain_order` | Ordem fixa dos jogadores |
| `step` / `total_steps` | Passo atual |
| `next` | Próximo profile |
| `played` | Quem já jogou |
| `status` | `IN_PROGRESS` ou `COMPLETE` |

---

## Relatório ao humano (template)

```markdown
## Fui ao mercado — round 20260531-1430

**Frase inicial:** Fui ao mercado e comprei uma maçã
**Frase final:** …
**Ordem:** agente-a → agente-b → agente-c → coordenador
**Duração total:** 2m 34s
**Sucesso:** ✅ 100% (3/3 saltos) ou ❌ parou em agente-b
**Problema (se houver):** frase truncada / profile errado / outbox pending
```

Gere automaticamente: `./scripts/benchmark-report.sh <ROUND>`

---

## Checklist

- [ ] Cada jogador repetiu a frase **sem alterar** palavras anteriores
- [ ] Cada um acrescentou **exatamente um** item
- [ ] Ordem respeitada (`chain_order`)
- [ ] Ninguém tratou como suporte ao cliente
- [ ] Coordenador reportou tempo e % sucesso

---

## Quando usar

| Situação | Usar? |
|----------|-------|
| Deploy / upgrade crossbot | ✅ |
| Bot novo no roster | ✅ |
| Medir latência da cadeia | ✅ |
| Tarefa real de produção | ❌ |

→ Deploy: [HANDOFF-DEPLOY.md](./HANDOFF-DEPLOY.md)  
→ Legado: [05-telefone-sem-fio.md](./05-telefone-sem-fio.md) (redireciona aqui)
