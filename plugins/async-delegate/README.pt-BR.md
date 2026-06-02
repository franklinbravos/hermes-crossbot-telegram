# async-delegate

> 🇧🇷 **Português** · 🇺🇸 [English](./README.md)

**Dispara subagentes em background sem bloquear o turno atual da conversa.**

Plugin Hermes que adiciona delegação de tarefas assíncrona — dispare um subagente para trabalhar em algo em background enquanto você continua conversando. Quando a tarefa termina, uma notificação é automaticamente injetada de volta na sessão de origem.

## Como funciona

```
┌──────────────┐      delegate_async     ┌──────────────────┐
│   Agente     │   ──────────────────►   │  Subagente       │
│   (turno)    │    retorna task_id      │  (hermes chat)   │
│              │    imediatamente        │  roda em bg      │
│              │                         └──────┬───────────┘
│  continua    │                                │
│  conversando │         .done written          │
│  normalmente │              │                  │
└──────┬───────┘              ▼                  │
       │              ┌──────────────┐           │
       │              │   Watcher    │◄──────────┘
       │              │   Thread     │  poll a cada 5s
       │              │  (daemon)    │
       │              └──────┬───────┘
       │                     │
       │   ◄─────────────────┘
       │   notificação injetada
       │   (queue ou steer)
       ▼
```

### Arquitetura

1. **Tool `delegate_async`** — O agente chama esta tool para disparar um processo `hermes chat` em background. Retorna um `task_id` imediatamente. O turno atual do agente **não** é bloqueado.
2. **Coordenação baseada em arquivos** — Cada tarefa recebe um conjunto de arquivos em `~/.hermes/async-tasks/`:
   - `async_<id>.json` — Metadados da tarefa (goal, status, routing)
   - `async_<id>.prompt` — Prompt completo do subagente
   - `async_<id>.sh` — Script bash wrapper que executa `hermes chat`
   - `async_<id>.output` — stdout do subagente (resultado)
   - `async_<id>.err` — stderr do subagente
   - `async_<id>.done` — Contém o código de saída (0 = sucesso)
3. **Thread watcher** — Uma thread daemon verifica `~/.hermes/async-tasks/` a cada 5 segundos por arquivos `.done`. Quando encontra um:
   - Lê as informações de roteamento da tarefa (qual sessão notificar)
   - Injeta uma notificação de conclusão na sessão
4. **Injeção na sessão** — Usa APIs internas do gateway para entregar a notificação:
   - Constrói um `MessageEvent` sintético com `internal=True`
   - Encontra o adaptador de plataforma correto
   - Verifica se a sessão está ocupada (agente no meio de um turno)
   - Roteia para modo queue ou steer conforme configurado
5. **Fallback: hook `pre_llm_call`** — Se a injeção do watcher falhar por qualquer motivo, um hook secundário verifica tarefas concluídas antes de cada chamada LLM e injeta um ping textual no contexto da conversa como rede de segurança.

## Modos de Injeção

### Queue (padrão)

A notificação aguarda o turno atual terminar e então é entregue como um novo turno limpo. O agente nunca é interrompido.

**Use para:** Pesquisas em background, consultas, tarefas fire-and-forget onde você só precisa do resultado eventualmente.

**Implementação:** Usa `merge_pending_message_event()` — o mesmo mecanismo que o Hermes usa para fotos. A notificação fica em `_pending_messages` até o turno atual completar, então é processada como o próximo turno.

### Steer

A notificação é intercalada no loop ativo de ferramentas do agente. O agente vê o resultado entre chamadas de ferramenta e pode ajustar sua abordagem no meio do turno — sem ser interrompido.

**Use para:** Resultados que podem mudar o que o agente está fazendo no momento. Por exemplo:

- Verificar se uma API existe antes de escrever código que a chama
- Validar um caminho de arquivo antes de editá-lo
- Confirmar uma versão de dependência antes de instalar
- Obter uma resposta rápida que condiciona a próxima tool call

**Implementação:** Usa `agent.steer()` para injetar texto no contexto do agente em execução. Faz fallback para queue se o steer falhar (sem agente rodando, agente não suporta steer).

## Tools

### `delegate_async`

```
delegate_async(goal: str, context?: str, inject_mode?: "queue"|"steer") -> JSON
```

Dispara um subagente em background. Retorna imediatamente:

```json
{
  "task_id": "async_a1b2c3d4",
  "status": "running",
  "inject_mode": "queue",
  "message": "Async task `async_a1b2c3d4` spawned in background..."
}
```

### `check_async_tasks`

```
check_async_tasks(task_id?: str) -> JSON
```

Verifica uma tarefa específica ou lista todas as tarefas. Para tarefas concluídas, inclui preview do resultado.

## Hooks

| Hook                   | Função                   | Propósito |
|------------------------|--------------------------|-----------|
| `pre_gateway_dispatch` | `capture_routing()`      | Captura referência do `GatewayRunner` + roteamento da sessão |
| `pre_llm_call`         | `pre_llm_inject_results()` | Fallback: varre tarefas concluídas antes de cada chamada LLM |
| `on_session_end`       | `cleanup_stale_tasks()`  | Remove arquivos de tarefas mais antigos que 24h |

## Configuração

### plugin.yaml

```yaml
name: async-delegate
version: "1.1.0"
description: "Async task delegation with dual-mode injection (queue/steer)"
hooks:
  - pre_gateway_dispatch
  - pre_llm_call
  - on_session_end
```

Nenhuma configuração adicional necessária. Basta copiar a pasta para `~/.hermes/plugins/` e reiniciar o gateway.

## Ciclo de Vida da Tarefa

```
running ──► completed    (.done com código de saída 0)
       ──► failed       (.done com código de saída != 0)
       ──► timeout      (sem .done após 30 minutos)
```

Arquivos de tarefas são auto-limpados após 24 horas.

## Decisões de Design

- **Baseado em arquivos, não em banco** — Tarefas são apenas JSON + arquivos de saída. Simples, depurável, sem dores de cabeça com migração.
- **Injeção na sessão, não webhooks** — Notificações passam pelo sistema interno de mensagens do gateway. Sem endpoints HTTP externos, sem complexidade de autenticação, funciona em qualquer deploy.
- **`build_session_key()` do gateway** — Chaves de sessão são construídas usando a função oficial do gateway, não construídas manualmente. Isso é crítico porque grupos usam um formato de chave diferente (`agent:main:telegram:group:{chat_id}:{thread_id}`) do que você construiria ingenuamente a partir de informações de roteamento.
- **Roteamento armazenado nos metadados da tarefa** — Cada JSON de tarefa inclui um dicionário `_routing` com platform, chat_id, thread_id etc. O watcher lê isso na conclusão para saber onde enviar a notificação, mesmo que o dicionário em memória tenha sido limpo.
- **Lookup duplo de roteamento** — Watcher verifica o dicionário `_task_routing` em memória primeiro (rápido), depois faz fallback para o campo `_routing` do JSON (sobrevive a restart do gateway).

## Changelog

### v1.1.0

- **Corrigida colisão de nome de toolset** — Renomeado de `delegation` para `async-delegation`.
- **Testado** com modos `queue` e `steer`.
- **Importante:** O nome do toolset registrado por este plugin NÃO DEVE colidir com toolsets internos do Hermes.

### v1.0.0

- Lançamento inicial.

## Limitações

- **Sem callbacks de progresso** — Subagentes executam até o fim; não há streaming de progresso ou resultados intermediários.
- **Canal único de saída** — Notificações sempre voltam para a sessão de origem. Sem roteamento para outro chat/usuário.
- **Polling, não event-driven** — Intervalo de 5s significa até 5s de atraso entre conclusão e notificação.

## Estrutura de Arquivos

```
~/.hermes/plugins/async-delegate/
├── __init__.py       # Plugin principal
├── plugin.yaml       # Metadados + hooks
├── README.md         # Documentação (EN)
└── README.pt-BR.md   # Documentação (PT)

~/.hermes/async-tasks/           # Criado automaticamente
├── async_<id>.json    # Metadados
├── async_<id>.prompt  # Prompt do subagente
├── async_<id>.sh      # Script wrapper
├── async_<id>.output  # Resultado (stdout)
├── async_<id>.err     # Erros (stderr)
└── async_<id>.done    # Marcador de código de saída
```

## Testes

### Smoke test rápido

```
# Como o agente:
delegate_async(goal="What time is it in EDT, PST, JST, and UTC? Just the 4 times.", inject_mode="queue")

# Deve retornar task_id imediatamente.
# ~10-30 segundos depois, a notificação aparece como um novo turno.
```

### Teste de pressão modo queue

Dispara uma cadeia longa de tools (10+ chamadas com 2s de espera), depois um async task ultra-curto ("say potato"). A notificação deve ficar na fila atrás do turno ativo e entregar só depois que ele completar — zero interrupção.

### Verificar logs

```bash
strings ~/.hermes/logs/agent.log | grep "async-delegate" | tail -20
```

Procure por `QUEUED notification for <task_id> behind active turn` para confirmar que o modo queue está funcionando.
