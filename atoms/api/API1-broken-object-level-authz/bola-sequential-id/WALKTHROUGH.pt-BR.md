# Walkthrough — bola-sequential-id

## 1. Contexto

Uma pequena **API de pedidos** de e-commerce serve um pedido via `GET /orders/:id`, autenticando o caller com um Bearer token mas nunca checando de quem é o pedido. Isso é **BOLA (Broken Object Level Authorization)** — o risco #1 do OWASP API Security Top 10 (**API1:2023**), e a cara de API do IDOR (insecure direct object reference): o mesmo bug de check ausente dos átomos web `idor-numeric-id` e `bola-rest`, agora em TypeScript/Express à escala de uma coleção de verdade.

Cada pedido carrega o nome do cliente, o endereço de entrega, o item e o valor. Você é o `dana`, e é dono de exatamente um pedido. No fim, você terá lido o dado pessoal dos onze pedidos que não são seus, usando o seu próprio token válido e trocando nada além do id.

Este é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar) ou, mais adiante, dirige do **Burp Intruder** (que repete um request sobre uma lista de valores). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra [`vulnerable/app.ts`](./vulnerable/app.ts). O handler vulnerable é curto:

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  const order = ORDERS[Number(req.params.id)];
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                          // BOLA -- no object-level check
});
```

Leia duas vezes. Ele chama `authenticate()`, então um token ausente ou inválido é recusado com `401`, e quando você chega no `res.json`, o request está *genuinamente autenticado*. Aí ele busca o pedido por id e o devolve. O bug é **o que não está lá**: nenhuma comparação entre `order.owner` e `caller`. O handler confia que "se você está logado e pediu o pedido N, você pode ver o pedido N".

Duas coisas pra internalizar desta forma:

- **Ele chama `authenticate()`, e é exatamente isso que desarma o revisor apressado** — "tem auth no endpoint, parece ok". Mas autenticar e autorizar são perguntas diferentes. Este handler *resolve* o caller — ele até guarda o resultado em `caller` — e depois não pergunta nada sobre se o pedido é dele. Agora olhe o endpoint de listagem no mesmo arquivo: `GET /orders` filtra `ORDERS` por `o.owner === caller`. O desenvolvedor claramente *sabia* escopar por dono; só não fez no endpoint por id. **Essa assimetria — lista escopada, detalhe não — é a assinatura do BOLA no mundo real.**
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar — sem template sink, sem `eval`, sem query concatenada. Você acha lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e aqui a resposta é em lugar nenhum.

## 3. Como funciona a auth deste lab

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Duas coisas pra ter em mente antes de começar:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401`. Você confirma isso no Passo 2.
- **Se essa identidade autenticada é usada pra *autorizar* um objeto específico é outra pergunta** — e a `/orders/:id` vulnerable não usa. Esse gap é o bug.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você não o decodifica, não o altera, não o forja — você faz login como você mesmo e manda o token exatamente como emitido. Ele fica válido e seu do começo ao fim. O alvo é o endpoint, não o token.

## 4. Baseline — capture o seu token e veja o escopo correto

Aponte o Burp pra API vulnerable em `127.0.0.1:8201` e trabalhe do Repeater.

> **Os tokens abaixo são de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu de cada response de login e use no header `Authorization`. Os ids são estáveis (seedados), e a cadeia é idêntica de qualquer jeito.

Faça login como você mesmo, `dana`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8201
Content-Type: application/json

{"user": "dana"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<dana-token>` abaixo):

```json
{"token": "CtzOeigH7E6XnvXbLY15XzHXUKb-eGsa"}
```

Faça login uma segunda vez como uma vítima, `alice`, e guarde esse token também (mostrado como `<alice-token>`) — você vai precisar dele uma vez, no próximo passo:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8201
Content-Type: application/json

{"user": "alice"}
```

Agora liste os seus próprios pedidos com o seu token:

```
GET /orders HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <dana-token>
```

Response — `200`, e repare que contém **só o seu único pedido**:

```json
[{"id":1007,"owner":"dana","customer":"Dana Lee","address":"3 Testing Blvd, Faketon","item":"Wireless mouse","amount":"$29.90"}]
```

Esse único item é a prova de que a API **sabe exatamente quem você é** e te escopa certo. Leia ele de volta pra confirmar que a feature funciona — `GET /orders/1007` com o seu Bearer retorna `200` e o seu próprio pedido.

Por fim, um cross-check legítimo pra depois. Peça o pedido `1001` com o **`<alice-token>`** — a alice é dona dele, então é assim que o acesso *autorizado* a `1001` se parece:

```
GET /orders/1001 HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <alice-token>
```

Response — `200`, o pedido da alice. Deixe ele ao seu lado; no próximo passo o mesmo objeto volta pro *seu* token.

## 5. Passo 1 — Leia o pedido de outro dono (BOLA confirmado)

A sua própria lista te entregou o id `1007`. Os ids são um único **contador global e contíguo**, então `1001`…`1012` todos existem e são de outros clientes. Não há o que adivinhar nem o que reconstruir — você leu o seu id e olhou os vizinhos.

Peça o `1001` com o seu próprio `<dana-token>`, inalterado:

```
GET /orders/1001 HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <dana-token>
```

Response — `200`:

```json
{"id":1001,"owner":"alice","customer":"Alice Nguyen","address":"12 Example Ave, Springfield","item":"Mechanical keyboard","amount":"$89.00"}
```

Você leu o pedido de outra usuária — **com o nome e o endereço de entrega dela** — usando o seu próprio token válido, trocando só o id. Isso é o **BOLA**. Nada aqui é payload; o request é válido por toda regra de protocolo, um WAF (web application firewall) não vê nada de errado, e a autenticação "passou". A autorização do objeto simplesmente nunca foi consultada.

Olhe o que aconteceu ao longo de dois requests. O mesmo `1001` voltou `200` pro `<alice-token>` no baseline *e* `200` pro `<dana-token>` agora. O servidor **resolveu duas identidades diferentes corretamente** — `authenticate()` devolveu `alice` num request e `dana` no outro — e **entregou o mesmo objeto aos dois**, porque a identidade, embora conhecida, nunca entra na decisão de acesso. É exatamente aí que o BOLA mora.

## 6. Passo 2 — O que a vuln NÃO é

O exploit é um request legítimo com um token legítimo, então é fácil de ler errado. Três requests fixam a causa real isolando o que ela *não* é.

**(a) Não é falha de autenticação.** Mande `GET /orders/1001` **sem nenhum header `Authorization`**:

```
GET /orders/1001 HTTP/1.1
Host: 127.0.0.1:8201
```

Response — **`401`**. A autenticação funciona: sem identidade, nada sai. (Corrompa o token trocando um caractere e você leva `401` também.)

**(b) O mesmo token escopa certo em outro lugar.** Mande `GET /orders` com o seu `<dana-token>` de novo — `200`, só o pedido `1007`. O mesmíssimo token que acabou de ler o pedido da alice produz uma resposta perfeitamente escopada aqui.

**(c) O mesmo token não recebe escopo nenhum na rota de detalhe.** Mande `GET /orders/1001` com esse mesmo `<dana-token>` — `200`, o pedido da alice, exatamente como no Passo 1.

Ponha (b) e (c) lado a lado: **o mesmo token dá escopo correto num handler e escopo nenhum no outro.** Então isso não é identidade quebrada nem impersonation — você esteve autenticado como `dana` o tempo todo, e o endpoint de listagem te escopou certo. É um check que *existe* no `GET /orders` e *falta* no `GET /orders/:id`. A causa é a object-level authorization ausente na rota de detalhe — não o token, não a sua identidade, não o formato do id. (Um id não-adivinhável só tornaria a descoberta mais cara; não colocaria o check de volta.)

Contraste com o átomo web `idor-numeric-id`, onde o endpoint ignorava a identidade asserida do caller por completo — não havia autenticação real ali. Aqui o endpoint *autentica*, resolvendo uma identidade genuína, e depois a joga fora na hora de autorizar. Essa é a forma mais comum e realista, e a distinção auth-versus-authz só fica assim de nítida *porque* a autenticação embaixo é real.

## 7. Passo 3 — Enumere a coleção inteira (Intruder)

Uma leitura cross-user é um achado; a coleção é o impacto. Mande `GET /orders/1001` pro **Burp Intruder** — a ferramenta que repete um request substituindo um valor de uma lista, aqui o id. Marque o id como a posição de payload:

```
GET /orders/§1001§ HTTP/1.1
Host: 127.0.0.1:8201
Authorization: Bearer <dana-token>
```

Ponha o payload type em **Numbers**, range `1001`–`1012`, passo `1`, e inicie o ataque. O seu `<dana-token>` fica fixo em todo request.

**A coleção inteira volta:** doze responses `200`, onze delas de pedidos que não são seus — os nomes, endereços e compras de **alice, bob e carol**. É o salto de "um objeto vazou" pra "**a coleção vazou**": um único check ausente, repetido sobre uma faixa contígua de ids, esvazia o banco do dado pessoal de todo mundo. Uma screenshot da tabela de resultados do Intruder, com os campos de cliente e endereço à vista, é o achado.

## 8. Por que o fix funciona — a parede chapada de 404s

Repita a **mesma varredura do Intruder** — Numbers `1001`–`1012`, o seu `<dana-token>` — contra a API fixed em `127.0.0.1:8301`:

- **Só o `1007` volta `200`** (o seu próprio pedido). Os outros onze são todos **`404`**, idênticos entre si — mesmo status, mesmo corpo. Essa **parede chapada de `404`** na tabela do Intruder é a prova de que o fix funciona: onde a varredura vulnerable vazou onze clientes, esta não vaza nada.
- `GET /orders/1007` com o seu `<dana-token>` ainda retorna `200` — donos continuam lendo os próprios pedidos. A autenticação continua imposta: sem token ou com token ruim ainda leva `401`.
- **`404`, não `403`:** o `404` de um pedido que você não possui é byte a byte o `404` de um id nunca seedado — `GET /orders/1013` retorna a mesma coisa. Então não há **oráculo de enumeração**: um atacante não consegue nem saber quais ids são reais. (O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) carrega o argumento completo — o precedente do GitHub, o RFC 9110, e quando `403` é a escolha legítima.)
- **O fix deixou o id sequencial.** O pedido `1001` continua um inteiro contíguo simples; o patch não remodelou nada do id, porque o formato do id nunca foi o problema — o check ausente era.

> O mesmo check ausente não vaza um pedido: vaza a coleção — o nome, o endereço e a compra de cada cliente. O token prova que você é você; não diz de quem é este pedido.

O walkthrough termina aqui. O achado é a leitura cross-user e a enumeração que a escala; o fix é um predicado numa guarda. Não sobra nada pra exfiltrar e nenhuma variação que valha acrescentar — pra ir mais fundo na classe, a página da PortSwigger no theory primer é o lugar.
