# ssrf-blind-oob — Blind SSRF (out-of-band)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab Flask mínimo de blind SSRF. A app é um "webhook tester": você registra uma URL e o servidor envia um test ping pra ela — uma requisição HTTP em background, disparada como efeito colateral. O resultado dessa requisição nunca é mostrado de volta. Não importa o que o servidor alcance, a resposta é sempre o mesmo `Test ping sent.` genérico. O servidor nunca valida qual URL ele foi mandado alcançar, então a mesma feature que pinga um webhook legítimo pode ser apontada pra qualquer host que a rede do servidor enxergue — você só nunca consegue ler o que volta.

Este é o segundo átomo de SSRF, e o irmão do `ssrf-basic`. Lá, o servidor buscava sua URL **e te entregava o corpo da resposta** — você lia um serviço interno direto, in-band. Aqui a resposta não te diz nada. Isso **não** quer dizer que o SSRF sumiu: o servidor continua fazendo a requisição que você pediu. Quer dizer só que você perdeu o canal pra *ler* o resultado. Então como provar que a requisição aconteceu? Você aponta o servidor pra um listener que você controla e observa o callback chegar **out-of-band**. Blind não quer dizer ausente; quer dizer que você confirma em outro lugar.

> **Teoria primeiro:** Leia [PortSwigger: Blind SSRF](https://portswigger.net/web-security/ssrf/blind)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Blind não é in-band — e não é ausente

Mantenha isso claro, porque *é* a lição. Blind SSRF não é um SSRF mais fraco; é a **mesma** capacidade de requisição server-side, menos o eco conveniente. A requisição acontecer é a vulnerabilidade. Se a resposta reflete isso é um *eixo separado* — só o quão fácil é confirmar. O `ssrf-basic` te dava requisição E leitura; aqui você tem a requisição e **nenhum** canal de leitura, então a detecção vai pro out-of-band. A armadilha de iniciante que este átomo isola é "sem output, então sem SSRF" — falso. Você vai fazer o servidor alcançar um destino que você escolheu e provar isso, sem nunca ler um byte do que ele buscou.

## Estrutura do lab — três containers

Como o `ssrf-basic`, este é um lab multi-container. Três services sobem sob um `docker-compose.yml`:

- **`vulnerable`** — o webhook tester quebrado, publicado em `127.0.0.1:8016`.
- **`fixed`** — a versão corrigida, publicada em `127.0.0.1:8116`.
- **`oob-listener`** — um sink out-of-band burro. Ele loga toda requisição que recebe e retorna `ok`. É uma **tripwire, não um alvo**: não guarda segredo nenhum, e alcançá-lo *é* a prova inteira. **Não** é publicado no host (sem entrada `ports:`); só é alcançável de dentro das redes Docker que o lab cria, e você o observa por `docker compose logs oob-listener`.

As apps `vulnerable` e `fixed` vivem em redes Docker **separadas**; ambas compartilham uma rede com o `oob-listener`. Então o listener é alcançável por cada app, mas as apps não se enxergam — a mesma isolação que o `ssrf-basic` usa. Isso importa pro fix: o `fixed` ainda alcança o listener na camada de rede; quando ele **não** produz callback, é o código da aplicação recusando, não a rede.

**Por que embarcar um listener?** Num engagement real você detectaria blind SSRF com um serviço de interação externo — Burp Collaborator, `interactsh`, um catcher de DNS/HTTP seu na internet. Este lab é auto-contido e isolado por design (só `127.0.0.1`), então não pode depender de alcançar um serviço de terceiro. O `oob-listener` é um substituto self-hosted e air-gapped desse sink externo — o "Collaborator" que você normalmente usaria, trazido pra dentro do lab.

## A resposta é cega de propósito

O `Test ping sent.` genérico não revela nada do fetch — sem corpo buscado, sem status buscado, sem erro. Essa cegueira é o traço definidor do átomo, não um acidente: se a resposta vazasse o que buscou, isso seria SSRF in-band (`ssrf-basic`), não blind. A resposta é idêntica na app vulnerable **e** na fixed — então você não consegue distinguir uma da outra pela resposta, que é exatamente por que você olha out-of-band.

Uma ressalva honesta: um side-channel de *timing* é inerente a qualquer blind SSRF — um host alcançável responde rápido, um que não responde trava até a requisição dar timeout. Isso é real, mas é grosseiro e ruidoso, e não é o canal que este átomo ensina. A prova confiável aqui é o callback out-of-band no log do listener.

## Como rodar

Da raiz do repo:

```bash
./atom up ssrf-blind-oob
```

- App vulnerable: <http://127.0.0.1:8016/>
- App fixed: <http://127.0.0.1:8116/>
- OOB listener: não publicado — alcançável só através da app vulnerable ou fixed, observado por `docker compose logs oob-listener`.

Pare com `./atom down ssrf-blind-oob`. Se preferir Docker cru: `cd atoms/A10-ssrf/ssrf-blind-oob && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo via Burp Suite + logs (principal) e browser (secundária).
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão corrigida

A app corrigida na porta 8116 serve a mesma feature e retorna o **mesmo** `Test ping sent.` pra qualquer input — a resposta nunca muda. O que muda é o que está por trás: antes de buscar, a app fixed valida o destino contra uma allowlist deny-by-default de hosts vetados, checada no host parseado (não num substring do raw URL). Replaye o ataque do `WALKTHROUGH.md` contra ela: a resposta é byte-idêntica à da app vulnerable, mas o log do `oob-listener` não mostra **nenhum** hit novo — a requisição pro destino não-vetado nunca foi enviada. O fix é uma **lista positiva**, não um blocklist de faixas "ruins": um blocklist de IPs privados impediria você de alcançar um alvo interno, mas não impediria um callback out-of-band pra um host externo, então não impediria a *detecção*; uma allowlist rejeita qualquer coisa não-vetada, interna ou externa. O controle está na aplicação, não no encanamento de rede — o listener continua alcançável a partir do `fixed`; ele só se recusa a alcançá-lo.
