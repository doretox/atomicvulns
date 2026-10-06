# Walkthrough — bola-nested-resource

## 1. Contexto

Uma API de back-office multi-loja serve `GET /stores/:storeId/orders/:orderId`. Ela checa, corretamente, que você opera a loja nomeada no path — peça uma loja que não é sua e ela responde `403` — e depois devolve o pedido sem checar que o pedido pertence àquela loja. Isso é **BOLA (Broken Object Level Authorization)** — o risco #1 do OWASP API Security Top 10 (**API1:2023**), e a cara de API do IDOR (insecure direct object reference).

O recurso é **nested**: um objeto endereçado *através do pai* no path. A loja é o **pai**, o pedido é o **filho**, e o **escopo** de uma loja é o conjunto de pedidos que pertencem a ela. As pessoas são **operadores** de uma loja — trabalham lá, não são donas dela, e todo operador de uma loja enxerga todos os pedidos daquela loja.

O seed, num fôlego só: três lojas — `harbor`, `meadow`, `summit` — e você é a `dana`, que opera a `harbor` e mais nada. Doze pedidos ficam num único contador global de id, `1001`–`1012`, divididos três, quatro e cinco entre as lojas. Cada pedido carrega o nome do comprador, o endereço de entrega, o item e o valor — o PII (personally identifiable information) que transforma isto de curiosidade em achado.

Esta é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

Dois path parameters significam duas coisas pra manter claras o tempo todo, então **todo bloco de request abaixo vem precedido de uma linha de rótulo** nomeando a loja que está no path e o pedido que está no path, e de quem é cada um. Leia o rótulo antes do request.

## 2. Ache o bug

Abra o [`vulnerable/app.ts`](./vulnerable/app.ts). O handler vulnerable tem dez linhas:

```ts
app.get("/stores/:storeId/orders/:orderId", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);                        // AUTHENTICATION
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
  // VULNERABLE: the lookup is GLOBAL. The caller operates :storeId, but order.storeId is
  // never compared to it -- an order from ANY store comes back.
  const order = ORDERS[Number(req.params.orderId)];
  if (!order) return res.sendStatus(404);
  res.json(order);
});
```

O handler toma três decisões, e só a terceira está errada. Ele autentica o caller (`401`). Ele autoriza o **pai** (`403`). Aí ele resolve o **filho** — na coleção da plataforma inteira, sem nada, em lugar nenhum, comparando a loja do pedido com a loja que acabou de ser autorizada.

- **Existe autorização aqui, e ela funciona.** O `operates(...)` é uma busca real contra uma tabela real de vínculos loja-operador, e ele responde `403` de verdade. Você vai mandar o request que prova isso no Passo 2. Este não é o handler do `bola-sequential-id` nem do `bola-uuid-leaked`, onde a rota de detalhe não carregava object-level check nenhum e nada ficava ao lado do gap pra disfarçá-lo.
- **Leia a assinatura, não o nome.** O `operates(caller, req.params.storeId)` recebe o caller e a loja. **O pedido não é argumento.** Por construção, a pergunta que este check responde não tem como ser sobre o pedido — e "este pedido pertence a esta loja?" é a pergunta que teria barrado o exploit.
- **A busca é global.** O `ORDERS[...]` é a coleção da plataforma inteira, com os doze pedidos. Agora olhe uma rota acima, o endpoint de listagem no mesmo arquivo: o `GET /stores/:storeId/orders` responde com `ordersOf(req.params.storeId)`, os pedidos da própria loja, filtrados por `o.storeId === storeId`. Quem escreveu sabia escopar uma resposta ao pai e escreveu o helper que faz exatamente isso. Só não usou ele na rota por id. **Lista escopada ao pai, detalhe lido da coleção global — essa assimetria é a assinatura do BOLA em nested resource.**
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar — sem template sink, sem `eval`, sem query concatenada. O que você está caçando é uma pergunta ausente ao lado de uma pergunta presente, o que é bem mais difícil de enxergar do que uma pergunta ausente sozinha.

## 3. Como funciona a auth deste lab

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Três camadas se empilham neste endpoint, e o átomo é sobre a terceira:

- **A autenticação** prova *quem você é*. Sem token, ou com um token ruim, você leva `401`.
- **O check do pai** prova *que você opera a loja que está no path*. Uma loja que você não opera leva `403`.
- **O escopo do filho** provaria *que o pedido pertence àquela loja*. Nada faz isso.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você faz login como você mesma e manda o token exatamente como foi emitido — sem decodificar, sem editar, sem forjar. O alvo é o endpoint, não o token.

## 4. Baseline — o seu token, a sua loja, e a cara de um acesso autorizado

Aponte o Burp pra API vulnerable em `127.0.0.1:8203` e trabalhe do Repeater.

> **O token abaixo é de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu de cada response de login e use no header `Authorization`. Os slugs de loja e os ids de pedido são estáveis (seedados), então esses você cola literalmente.

Faça login como você mesma:

> **Login como:** `dana` — você, quem opera a `harbor`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8203
Content-Type: application/json

{"user": "dana"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<dana-token>` abaixo):

```json
{"token": "RAP7MNsx1BZW1u5iFVjbWJiVU0q5ksy1"}
```

Faça login uma segunda vez como a `alice`, que opera a `meadow`, e guarde esse token também (mostrado como `<alice-token>`) — você vai precisar dele uma vez, no fim deste passo:

> **Login como:** `alice` — quem opera a `meadow`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8203
Content-Type: application/json

{"user": "alice"}
```

Agora liste os pedidos da loja que você opera:

> **Loja no path:** `harbor` (sua) · **Pedido no path:** nenhum — este bloco pede a coleção

```
GET /stores/harbor/orders HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — `200`, e repare que contém **só os três pedidos da `harbor`**:

```json
[{"id":1004,"storeId":"harbor","customer":"Elena Ruiz","address":"90 Placeholder Rd, Lakeside","item":"4K monitor","amount":"$329.00"},{"id":1008,"storeId":"harbor","customer":"Priya Shah","address":"12 Example Ave, Springfield","item":"Desk mat","amount":"$19.00"},{"id":1011,"storeId":"harbor","customer":"Marcus Webb","address":"7 Sample St, Rivertown","item":"HDMI cable","amount":"$12.99"}]
```

Ids `1004`, `1008` e `1011` — esse é o escopo inteiro da sua loja, e a API te escopou nele corretamente. Leia um deles de volta:

> **Loja no path:** `harbor` (sua) · **Pedido no path:** `1011` (um pedido da `harbor`)

```
GET /stores/harbor/orders/1011 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — `200`:

```json
{"id":1011,"storeId":"harbor","customer":"Marcus Webb","address":"7 Sample St, Rivertown","item":"HDMI cable","amount":"$12.99"}
```

Foi outra pessoa que comprou esse pedido e você acabou de ler o nome e o endereço dela — e isso está **correto**. Operadores da mesma loja legitimamente compartilham os pedidos dela: tanto o `bob` quanto a `carol` operam a `summit` e veem os mesmos cinco pedidos, e você vê todo pedido da `harbor`, quem quer que tenha comprado. Esse compartilhamento é a feature, não a falha. O que é dono de um pedido aqui é uma **loja**, não uma pessoa, então "consigo ver um pedido com o nome de um desconhecido" não é, por si só, o bug. Segure essa distinção, ou o próximo passo vai parecer a feature funcionando.

Um cross-check legítimo antes de seguir. O pedido `1009` pertence à `meadow` e a `alice` opera a `meadow`, então peça ele com o **`<alice-token>`**. É esta a cara de um acesso *autorizado* àquele pedido:

> **Loja no path:** `meadow` (da alice) · **Pedido no path:** `1009` (um pedido da `meadow`)

```
GET /stores/meadow/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <alice-token>
```

Response — `200`:

```json
{"id":1009,"storeId":"meadow","customer":"Elena Ruiz","address":"90 Placeholder Rd, Lakeside","item":"Standing desk","amount":"$589.00"}
```

Deixe ele ao seu lado; no próximo passo esse mesmíssimo objeto volta pro *seu* token, pela *sua* loja. (Numa engagement real você não teria o token da alice — o lab te dá os dois logins só pra você ver o baseline autorizado.)

## 5. Passo 1 — Leia o pedido de outra loja pela sua própria loja (BOLA confirmado)

Não há o que adivinhar aqui. A sua própria lista devolveu `1004`, `1008`, `1011`, e os ids são **um único contador global compartilhado pela plataforma inteira** — então os buracos entre os seus ids são pedidos de outras lojas, e o `1009` fica bem no meio de dois dos seus.

Peça o `1009` com o seu próprio token, inalterado, pela **sua** loja:

> **Loja no path:** `harbor` (sua) · **Pedido no path:** `1009` (um pedido da `meadow`)

```
GET /stores/harbor/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — **`200`**:

```json
{"id":1009,"storeId":"meadow","customer":"Elena Ruiz","address":"90 Placeholder Rd, Lakeside","item":"Standing desk","amount":"$589.00"}
```

Leia o corpo, depois leia a request line de novo. A resposta diz **`"storeId":"meadow"`** para um request cujo path dizia `harbor`. O dado sabia de quem era e carregava a resposta junto consigo; o handler nunca perguntou. Isso é o **BOLA**. Nada aqui é payload — o request é válido por toda regra de protocolo, um WAF (web application firewall) não vê nada de errado, a autenticação passou, e o check de loja passou também.

Agora prove que o `{storeId}` do path não está apontando pra nada. Mesmo token, mesma loja no path, um pedido da *terceira* loja:

> **Loja no path:** `harbor` (sua) · **Pedido no path:** `1001` (um pedido da `summit`)

```
GET /stores/harbor/orders/1001 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — **`200`**, um pedido da `summit`:

```json
{"id":1001,"storeId":"summit","customer":"Priya Shah","address":"12 Example Ave, Springfield","item":"Mechanical keyboard","amount":"$89.00"}
```

**Duas lojas diferentes, uma porta só.** O `harbor` do path não quer dizer "a outra loja", e não quer dizer "a loja do pedido" — ele não quer dizer absolutamente nada sobre o pedido. Ele só precisa nomear uma loja que *você* opera, pra o check te deixar passar; depois disso, qualquer um dos doze ids resolve.

E olhe o baseline e este passo lado a lado. O pedido `1009`, da `meadow`, voltou `200` pro `<alice-token>` por `/stores/meadow/...` **e** `200` pro `<dana-token>` por `/stores/harbor/...`. O servidor resolveu as duas identidades corretamente e autorizou dois pais diferentes — e então entregou o mesmo filho nas duas vezes, porque a loja autorizada nunca foi comparada com a loja do pedido.

## 6. Passo 2 — O que a vuln NÃO é

O exploit é um request legítimo, com um token legítimo, contra um endpoint que *de fato* autoriza — então a conclusão errada mais fácil de tirar é "este handler não tem autorização". Tem. Três requests, todos mandados com o mesmo `<dana-token>` inalterado, fixam qual é de fato a falha.

**Request 1 — nomeie a loja real do pedido.**

> **Loja no path:** `meadow` (**não é sua**) · **Pedido no path:** `1009` (um pedido da `meadow`)

```
GET /stores/meadow/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — **`403`**, corpo `Forbidden`. O primeiro check existe e morde. Repare no que este request pediu: o pedido `1009` sob a loja à qual ele de fato pertence — e foi recusado, porque você não opera a `meadow`.

**Request 2 — a feature, funcionando como projetada.**

> **Loja no path:** `harbor` (sua) · **Pedido no path:** `1011` (um pedido da `harbor`)

```
GET /stores/harbor/orders/1011 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — **`200`**, o pedido da `harbor`. Sua loja, pedido da sua loja: correto.

**Request 3 — o bug.**

> **Loja no path:** `harbor` (sua) · **Pedido no path:** `1009` (um pedido da `meadow`)

```
GET /stores/harbor/orders/1009 HTTP/1.1
Host: 127.0.0.1:8203
Authorization: Bearer <dana-token>
```

Response — **`200`**, o pedido da `meadow`, exatamente como no Passo 1.

Agora a conclusão, que é o átomo inteiro. **O `storeId` foi checado nos três requests.** Ele simplesmente não tem relação nenhuma com o pedido que volta. Os requests 1 e 3 passaram pelo **mesmíssimo check** — a mesma linha, a mesma busca `operates(caller, storeId)` — e ele recusou um e aprovou o outro por razões que nada têm a ver com o pedido: o request 1 até nomeou a loja real do pedido e foi recusado, enquanto o request 3 nomeou uma loja sem relação nenhuma e foi atendido. Entre o 2 e o 3 só o pedido mudou, e o veredito não. Entre o 1 e o 3 só a loja mudou, e o veredito virou. O parâmetro que é autorizado e o objeto que é entregue são independentes um do outro — e é essa independência que é o bug.

> **Autorização presente não é autorização suficiente — o que importa é qual pergunta ela responde.**

É isso que separa este átomo dos seus dois companheiros. No `bola-sequential-id` e no `bola-uuid-leaked` a pergunta faltava por completo: o handler de detalhe resolvia o caller e depois não perguntava absolutamente nada sobre o objeto, e o reparo era acrescentar a pergunta. Aqui a pergunta não faltava — ela foi **substituída por uma vizinha que passa por ela**. Um revisor lendo este handler vê um `403` logo no começo e segue em frente; o gap fica camuflado pelo check que está ao lado.

Também não é falha de autenticação. Tire o header `Authorization` de qualquer request acima e você leva `401` (corpo `Unauthorized`); troque um caractere do token e você leva `401` também. Você esteve autenticada como `dana`, corretamente e sem interrupção, do primeiro ao último request.

## 7. Por que o fix funciona (porta 8303)

Aponte o Burp pra API fixed em `127.0.0.1:8303` e faça login lá — cada build tem o próprio mapa de tokens, então você precisa de tokens novos — e então repita a cadeia:

- **O check do pai está intocado.** `GET /stores/meadow/orders/1009` com o seu `<dana-token>` → **`403`**, exatamente como na 8203. Essa linha é byte-idêntica nos dois builds; ela nunca foi a parte quebrada.
- **A feature está intocada.** `GET /stores/harbor/orders/1011` → `200`, e o `GET /stores/harbor/orders` continua devolvendo os seus três pedidos. `GET /stores/meadow/orders/1009` com o `<alice-token>` → `200`: operadores continuam lendo os pedidos da própria loja. Sem token, ainda é `401`.
- **O exploit acabou, e não deixa rastro de si mesmo.** `GET /stores/harbor/orders/1009` → **`404`**. `GET /stores/harbor/orders/1001` → **`404`**. Agora peça `GET /stores/harbor/orders/1013`, um id que nunca foi seedado — **`404`** também, com o mesmo corpo (`Not Found`) e o mesmo tamanho. De dentro da sua própria loja, um pedido que existe em outra loja e um pedido que não existe em lugar nenhum são uma única e mesma resposta, o que não te deixa nenhum **oráculo de enumeração**: nenhuma diferença nas respostas a partir da qual mapear quais ids são reais, sem ler nenhum deles.

A mudança de uma linha por trás de tudo isso: o handler fixed busca o pedido **dentro da loja autorizada** em vez de na coleção da plataforma inteira — o mesmo escopo que o endpoint de listagem, uma rota acima, já usava. Um pedido de outra loja *não é encontrado*, em vez de ser encontrado e então recusado.

Duas coisas que valem levar pro [`DIFF.pt-BR.md`](./DIFF.pt-BR.md), que trabalha as duas: por que o pai responde `403` enquanto o filho responde `404`, e por que este fix moveu a *busca* em vez de acrescentar um predicado à guarda, do jeito que os dois átomos companheiros fizeram.

O walkthrough termina aqui. O achado é a leitura cross-store e o parâmetro de loja que, no fim, não autorizava nada sobre o objeto que entregava; o fix é uma linha, na busca. Pra ir mais fundo na classe, a página da PortSwigger no theory primer é o lugar.
