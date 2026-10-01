# bola-nested-resource — Broken Object Level Authorization (BOLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BOLA (Broken Object Level Authorization) — o nome que a área de API security dá a um IDOR (insecure direct object reference) que vive num endpoint REST, e o API1:2023, o risco #1 do OWASP API Security Top 10. Esta aqui serve um **nested resource**: um objeto endereçado *através do pai* no path, aqui `GET /stores/:storeId/orders/:orderId` — um pedido (o filho) solicitado dentro de uma loja (o pai). O endpoint autentica o Bearer token e então faz uma coisa que os dois átomos companheiros desta categoria nunca fizeram: ele **checa autorização**. Ele pergunta se o caller opera a loja nomeada no path, e responde `403` quando não opera. Depois busca o pedido na coleção da plataforma inteira e o devolve, sem nunca comparar a loja do próprio pedido com a loja que ele acabou de autorizar.

Então a lição aqui não é que faltou autorização. É que **um check pode ser real, pode recusar requests de verdade, e ainda assim guardar a coisa errada**. Duas perguntas parecem uma só quando as duas têm uma loja por sujeito: *"você opera esta loja?"* e *"este pedido pertence a esta loja?"*. O handler responde a primeira e nunca faz a segunda. E nada foi escondido dele: todo pedido carrega o próprio `storeId`, e dá pra ver o descasamento voltar no corpo da resposta — `"storeId":"meadow"` num request cujo path dizia `harbor`.

Isso inverte a premissa dos outros dois. O `bola-sequential-id` e o `bola-uuid-leaked` põem os dois o bug num handler de detalhe **sem check nenhum** de object level — uma omissão, sem nada ao lado dela que um revisor pudesse confundir com autorização. Aqui a omissão tem companhia: um `403` genuíno fica imediatamente acima da busca defeituosa e faz o handler parecer coberto. É também o primeiro nested resource do repo — nenhuma outra rota publicada, web ou API, recebe dois path parameters.

> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — dados em memória, sem banco

Lojas e pedidos vivem em `Record`s simples de TypeScript, não num banco. BOLA não depende da camada de persistência: o bug é uma pergunta de autorização que o handler nunca faz, e ela fica *acima* de qualquer persistência que você escolher — então a camada de dados fica mínima e a pergunta que falta fica óbvia. O mapa `token -> user` também é em memória — reinicie o container e todo token emitido desaparece, então faça login de novo e continue.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: toda resposta de sucesso é JSON. É proposital — BOLA vive em APIs REST, e este átomo modela uma. Você opera tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente no Burp.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pra um usuário, tipo um OAuth2 opaque access token ou uma session id server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**: lidar com senha multiplicaria o código e ensinaria outra lição.

O que o atalho *não* faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` em todo endpoint protegido. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. E o check de loja também não é enfeite: peça uma loja que você não opera e você leva `403`, no build vulnerable exatamente como no fixed. O que falta é a terceira coisa — qualquer check de que o pedido que você pediu pertence à loja que foi autorizada.

## Lojas, operadores e pedidos

Aqui as pessoas são **operadores** de uma loja: elas trabalham lá, elas não são a loja. Três lojas no seed, e os slugs delas são nomes públicos, nada mais secretos que a placa na fachada:

| Loja | Operadores | Pedidos |
|---|---|---|
| `harbor` | `dana` — a atacante (você) | `1004`, `1008`, `1011` |
| `meadow` | `alice` | `1002`, `1006`, `1007`, `1009` |
| `summit` | `bob`, `carol` | `1001`, `1003`, `1005`, `1010`, `1012` |

Os doze ids de pedido vão de `1001` a `1012` num **único contador global compartilhado pela plataforma inteira**, então os ids de uma loja isolada têm buracos — e os buracos são pedidos de outras lojas. Cada pedido carrega o nome do comprador, o endereço de entrega, o item e o valor. Compradores são o público (`Priya Shah`, `Marcus Webb`, `Elena Ruiz`, `Theo Okafor`); operadores são funcionários; os dois conjuntos nunca se cruzam.

**Operadores da mesma loja legitimamente compartilham os pedidos dela** — tanto o `bob` quanto a `carol` operam a `summit` e veem os mesmos cinco pedidos, e você vê todo pedido da `harbor`, quem quer que tenha comprado. Esse compartilhamento é a feature, não a falha. O que *não* é a feature é ler o pedido `1009`, da `meadow`, por `/stores/harbor/...`.

## Como rodar

Da raiz do repo:

```bash
./atom up bola-nested-resource
```

- API vulnerable: `http://127.0.0.1:8203`
- API fixed: `http://127.0.0.1:8303`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bola-nested-resource`. Se preferir Docker cru: `cd atoms/api/API1-broken-object-level-authz/bola-nested-resource && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8303 atende a mesma feature de back-office contra o mesmo seed, e muda **uma linha: onde o pedido é buscado**. Em vez de procurar na coleção da plataforma inteira, o handler procura nos pedidos da própria loja autorizada — o mesmo escopo que o endpoint de listagem, uma rota acima, já usava. Replay o walkthrough contra ela: os pedidos da própria `harbor` continuam devolvendo `200`, uma loja que você não opera continua devolvendo `403`, e o pedido `1009` pedido por `harbor` agora devolve **`404`** — exatamente o mesmo `404` de um id que nunca foi seedado. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) trabalha por que o pai responde `403` enquanto o filho responde `404`, e por que o fix moveu a busca em vez de acrescentar um predicado à guarda.
