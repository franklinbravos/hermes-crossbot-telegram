# O que mandar para o Hermes

> Você **não precisa** explicar bash, plugins nem paths.  
> Copie a mensagem abaixo, cole no chat do Hermes (DevOps ou quem tiver terminal) e deixe ele resolver.

---

## Instalar o crossbot (primeira vez ou vindo da versão antiga)

**Copie e cole isto:**

```
Preciso que você instale o crossbot aqui no servidor — é o plugin que faz os bots conversarem entre si no Telegram.

Baixe o projeto do GitHub (franklinbravos/hermes-crossbot-telegram), rode a instalação completa e não pare no meio. Se já existia a versão antiga (kanban-context ou multi-agent-context), limpe isso e deixe só o crossbot.

No final me diga:
- se deu certo ou onde travou
- quais bots/profiles foram configurados
- se o gateway reiniciou

Se algo faltar (por exemplo chat do Telegram ou nomes dos bots), me pergunte — mas tente resolver sozinho o que der.

Comando para rodar:

bash -c 'set -euo pipefail; CB="${CROSSBOT_HOME:-$HOME/hermes-crossbot-telegram}"; if [ -d "$CB/.git" ]; then git -C "$CB" pull --ff-only; else git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git "$CB"; fi; chmod +x "$CB"/scripts/*.sh "$CB"/scripts/lib/*.sh; "$CB"/scripts/bootstrap.sh --yes'
```

---

## Instalar quando você já sabe o grupo e os bots

Troque os valores entre `<>` pelos seus dados reais, depois cole:

```
Instala o crossbot para mim. Já tenho estes dados do workspace:

- Grupo Telegram (chat_id): <ex: -1003716565637>
- Bot coordenador: <nome da pasta do profile, ex: coordenador>
- Outros bots que participam: <ex: vendas, suporte>

Faz a instalação completa, remove restos da versão antiga se existirem, configura o mapa de tópicos e reinicia o gateway. Me avisa quando terminar ou se precisar de alguma informação que faltou.

bash -c 'set -euo pipefail
CB="${CROSSBOT_HOME:-$HOME/hermes-crossbot-telegram}"
[ -d "$CB/.git" ] && git -C "$CB" pull --ff-only || git clone https://github.com/franklinbravos/hermes-crossbot-telegram.git "$CB"
chmod +x "$CB"/scripts/*.sh "$CB"/scripts/lib/*.sh
"$CB"/scripts/bootstrap.sh --yes \
  --chat-id "<CHAT_ID>" \
  --orchestrator "<COORDENADOR>" \
  --players "<BOT1,BOT2>"'
```

---

## Atualizar para a versão mais recente

```
Atualiza o crossbot neste servidor: puxa a versão nova do GitHub, reinstala o plugin, limpa lixo da versão antiga se aparecer, e reinicia o gateway. Me conta o que mudou e se deu algum erro.

~/hermes-crossbot-telegram/scripts/auto-update.sh --restart
```

---

## Ligar atualização automática (todo dia)

```
Quero que o crossbot se atualize sozinho todo dia de madrugada. Configura a rotina automática e me confirma que ficou agendada. Se der, roda um teste manual uma vez para ver se funciona.

~/hermes-crossbot-telegram/scripts/setup-auto-update-cron.sh
```

---

## Testar se os bots se entendem (fui ao mercado)

```
Vamos testar se os bots se falam de verdade? Inicia o jogo "fui ao mercado" com todos do time — cada um repete a frase, acrescenta um item e repassa pro próximo. No final me diz quanto tempo levou e se deu 100% de sucesso ou onde parou.

~/hermes-crossbot-telegram/scripts/fui-ao-mercado.sh

Quando terminar:
~/hermes-crossbot-telegram/scripts/benchmark-report.sh

# Debug (zip factual para enviar ao dev)
~/hermes-crossbot-telegram/scripts/crossbot-debug-pack.sh enable
~/hermes-crossbot-telegram/scripts/crossbot-debug-pack.sh pack -r <ROUND>
```

---

## Referência rápida (para humanos)

O script `bootstrap.sh` cuida de:

1. Baixar ou atualizar o código  
2. Remover plugins antigos e ajustar configs  
3. Instalar o crossbot em todos os profiles  
4. Montar o mapa de colegas (`topic-map.json`)  
5. Criar o quadro Kanban e reiniciar o Hermes  

Mais detalhes: [02-instalar-e-adaptar.md](./02-instalar-e-adaptar.md)
