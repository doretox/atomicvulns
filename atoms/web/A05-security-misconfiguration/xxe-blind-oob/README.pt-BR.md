# xxe-blind-oob — Blind XXE (out-of-band)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Um lab Flask mínimo de **blind XXE**. A app é um importador de XML em lote: você dá `POST` num documento XML pra `/import`, o servidor parseia, e responde sempre o mesmo `{"status": "received"}` genérico — ele nunca ecoa nada do documento de volta. O parser resolve **entidades externas**, então um documento cujo `DOCTYPE` declara uma entidade externa apontando pra um servidor que *você* controla faz o parser alcançá-lo — uma requisição de saída que a app nunca quis fazer. Como a resposta é muda, você não consegue ler nada in-band. Então você confirma a vulnerabilidade **out-of-band**: aponta a entidade pra um listener que você controla e observa o callback chegar. E a mesma resolução de entidade externa ainda deixa você exfiltrar um arquivo do servidor por esse canal.

Este é o segundo átomo em A05 — Security Misconfiguration, e o irmão cego do `xxe-basic`. Lá, o servidor parseava seu XML **e ecoava um campo de volta** — você lia o `/etc/passwd` direto na resposta, in-band. Aqui a resposta não te diz nada. Isso **não** significa que o XXE sumiu: o parser continua resolvendo a entidade externa que você declarou e continua alcançando a rede. Só significa que você perdeu o canal pra *ler* o resultado na resposta. Então como provar que aconteceu? Você faz o parser ligar pra casa — pra um listener que você controla — e confirma **out-of-band**. Blind não quer dizer ausente; quer dizer que você confirma em outro lugar.

> **Teoria primeiro:** Leia [PortSwigger: Blind XXE](https://portswigger.net/web-security/xxe/blind)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Blind não é in-band — e não é ausência

Deixe isso claro, porque *é* a lição. Blind XXE não é um XXE mais fraco; é a **mesma** misconfiguration do parser — resolução de entidade externa ligada — menos o eco conveniente. O parser resolver sua entidade externa é a vulnerabilidade. Se a resposta reflete o resultado é um *eixo separado*: só o quão fácil é confirmar. O `xxe-basic` te dava o valor resolvido na resposta; aqui você tem a resolução e **nenhum** canal de leitura, então a detecção vai pro out-of-band. A armadilha de iniciante que este átomo isola é "sem eco, nada vaza" — falso, e o fix que decorre dela (esconder o eco) não é fix nenhum: a app já esconde tudo e continua vulnerável. O único fix é no **parser**.

## Mesmo bug do xxe-basic, canal diferente

O `xxe-basic` (átomo 18, in-band) e este átomo (blind, out-of-band) compartilham a **mesma causa-raiz** — um parser `lxml` configurado pra resolver entidades externas e carregar DTDs — e o **mesmo fix** — desligar essas duas features do parser. O que difere é o canal:

| | `xxe-basic` (in-band) | `xxe-blind-oob` (blind / out-of-band) |
|---|---|---|
| Causa | parser resolve entidades externas / DTD | a **mesma** |
| Canal | in-band — o valor volta na resposta | out-of-band — a requisição do parser pro listener |
| O que você observa | o arquivo na resposta HTTP | o hit chegando no log do listener |
| Fix | desligar resolução de entidade externa e carga de DTD | o **mesmo** |

A única diferença de config do parser que abre o canal out-of-band é uma flag só — `no_network` — coberta no [`DIFF.md`](./DIFF.md).

## Estrutura do lab — três containers

Como o átomo de SSRF out-of-band (`ssrf-blind-oob`), este é um lab multi-container. Três serviços sobem sob um `docker-compose.yml`:

- **`vulnerable`** — o importador quebrado, publicado em `127.0.0.1:8030`.
- **`fixed`** — a versão corrigida, publicada em `127.0.0.1:8130`.
- **`oob-listener`** — um sink out-of-band burro. Serve a DTD do atacante e loga toda request que recebe. É um **tripwire, não um alvo**: não guarda segredo nenhum, e alcançá-lo *já é* a prova. **Não** é publicado no host (sem entrada `ports:`); só é alcançável de dentro das redes Docker que o lab cria, e você o observa por `docker compose logs oob-listener`.

As apps `vulnerable` e `fixed` vivem em redes Docker **separadas**; as duas compartilham uma rede com o `oob-listener`. Então o listener é alcançável de cada app, mas as apps não se alcançam. Isso importa pro fix: o `fixed` **consegue** alcançar o listener na camada de rede; quando ele **não** gera callback, é o parser se recusando a resolver a entidade, não a rede bloqueando.

**Por que embarcar um listener?** Num engagement real você detectaria blind XXE com um servidor de interação externo — Burp Collaborator, `interactsh`, um catcher de DNS/HTTP que você controla na internet. Este lab é auto-contido e isolado por design (só `127.0.0.1`), então não pode depender de alcançar um terceiro. O `oob-listener` é um substituto self-hosted e air-gapped desse sink externo — o "Collaborator" que você usaria normalmente, trazido pra dentro do lab. Todo callback fica na sua máquina.

## A resposta é cega de propósito

O `{"status": "received"}` genérico não revela nada — nenhum valor parseado, nenhum erro. Essa cegueira é o traço definidor do átomo, não um acidente: se a resposta vazasse a entidade resolvida, isto seria XXE in-band (`xxe-basic`). A resposta é **byte-idêntica** na app vulnerable e na fixed, e pra um documento benigno e pro payload de ataque igualmente — então você não distingue nenhum deles pela resposta, que é exatamente por que você olha pro out-of-band.

## Como rodar

Da raiz do repo:

```bash
./atom up xxe-blind-oob
```

- App vulnerable: <http://127.0.0.1:8030/import> (`POST` XML)
- App fixed: <http://127.0.0.1:8130/import> (`POST` XML)
- OOB listener: não publicado — alcançável só pela app vulnerable ou fixed, observado por `docker compose logs oob-listener`.

Pare com `./atom down xxe-blind-oob`. Se preferir Docker puro: `cd atoms/A05-security-misconfiguration/xxe-blind-oob && docker compose up --build`.

## O que ler em seguida

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo via Burp Suite + logs (principal).
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Nota sobre a biblioteca — por que lxml, e por que pinada

O parser XML da biblioteca padrão do Python (`xml.etree.ElementTree`) **não** resolve entidades externas, então um átomo construído sobre ele não seria vulnerável. Este lab usa **`lxml`** (sobre `libxml2`), o parser terceiro popular, que *resolve* — e cujo comportamento exato é específico da versão. A app vulnerable monta o parser com `resolve_entities=True, load_dtd=True, no_network=False`; a versão pinada `lxml==5.3.0` (libxml2 2.12.9) busca a DTD externa e dispara a requisição out-of-band sob essa configuração. O comportamento foi confirmado **rodando** a versão pinada, não assumido; se você subir a versão do `lxml`, re-verifique. Veja o [`DIFF.md`](./DIFF.md) pra o raciocínio completo, incluindo por que o `defusedxml` é citado mas não usado.

## Versão corrigida

A app corrigida na porta 8130 serve o mesmo endpoint e devolve o **mesmo** `{"status": "received"}` pra qualquer entrada — a resposta nunca muda. O que muda é atrás dela: o parser é montado com `resolve_entities=False, load_dtd=False`, então a entidade externa nunca é resolvida e a DTD do atacante nunca é buscada. Repita o ataque do `WALKTHROUGH.md` contra ela: a resposta é byte-idêntica à da app vulnerable, mas o log do `oob-listener` **não** mostra hit novo — o callback nunca acontece. O fix é no **parser**, não na resposta e não na rede: o listener continua alcançável do `fixed`; o parser endurecido simplesmente nunca vai atrás dele. Veja o [`DIFF.md`](./DIFF.md).
