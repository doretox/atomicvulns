# Walkthrough — bola-uuid-leaked

## 1. Contexto

Uma pequena **API de pedidos** de e-commerce serve um pedido via `GET /orders/:id`, autenticando o caller com um Bearer token mas nunca checando de quem é o pedido. Isso é **BOLA (Broken Object Level Authorization)** — o risco #1 do OWASP API Security Top 10 (**API1:2023**), e a cara de API do IDOR (insecure direct object reference). Aqui o id do pedido é um **UUID (Universally Unique Identifier) v4** — um valor aleatório de 128 bits —, não um inteiro pequeno.

A premissa, em uma frase: **o UUID de um pedido da alice chegou até você por um canal de fora da app** — um chamado de suporte, um print, um link compartilhado — do jeito que ids circulam no mundo real. A aplicação não vaza id nenhum; você simplesmente *tem* um que não é seu. Você é o `clancy`, e é dono de exatamente um pedido. No fim, você terá lido o dado pessoal de um pedido que não é seu, usando o seu próprio token válido e um UUID que te entregaram.

Este é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar) ou, mais adiante, dirige do **Burp Intruder** (que repete um request sobre uma lista de valores). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra [`vulnerable/app.ts`](./vulnerable/app.ts). O handler vulnerable é curto:

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  const order = ORDERS[req.params.id];                      // string key (UUID) -- no Number() coercion
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                          // BOLA -- no object-level check
});
```

Leia duas vezes. Ele chama `authenticate()`, então um token ausente ou inválido é recusado com `401`, e quando você chega no `res.json`, o request está *genuinamente autenticado*. Aí ele busca o pedido por id e o devolve. O bug é **o que não está lá**: nenhuma comparação entre `order.owner` e `caller`. O handler confia que "se você está logado e pediu o pedido X, você pode ver o pedido X" — e trata ter o UUID como prova de que você pode. Não é.

Duas coisas pra internalizar desta forma:

- **Ele chama `authenticate()`, e é exatamente isso que desarma o revisor apressado** — "tem auth no endpoint, parece ok". Mas autenticar e autorizar são perguntas diferentes. Este handler *resolve* o caller — ele até guarda o resultado em `caller` — e depois não pergunta nada sobre se o pedido é dele. Agora olhe o endpoint de listagem no mesmo arquivo: `GET /orders` filtra `ORDERS` por `o.owner === caller`. O desenvolvedor claramente *sabia* escopar por dono; só não fez no endpoint por id. **Essa assimetria — lista escopada, detalhe não — é a assinatura do BOLA no mundo real.** É a forma idêntica de handler do átomo companheiro `bola-sequential-id`; a chave UUID não mudou nada do bug.
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar — sem template sink, sem `eval`, sem query concatenada. Você acha lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e aqui a resposta é em lugar nenhum.

## 3. Como funciona a auth deste lab

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Três coisas pra ter em mente antes de começar:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401`. Você confirma isso no Passo 2.
- **Se essa identidade autenticada é usada pra *autorizar* um objeto específico é outra pergunta** — e a `/orders/:id` vulnerable não usa. Esse gap é o bug.
- **O UUID é o *id do pedido*, não o token.** O ataque nunca toca o token: você não o decodifica, não o altera, não o forja — você faz login como você mesmo e manda o token exatamente como emitido. O que é um UUID aqui é o identificador de objeto no path; é esse o eixo em teste.

## 4. Baseline — capture o seu token e veja o escopo correto

Aponte o Burp pra API vulnerable em `127.0.0.1:8202` e trabalhe do Repeater.

> **O token abaixo é de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu de cada response de login e use no header `Authorization`. Os UUIDs de pedido são estáveis (cravados no seed), então esses você cola literalmente.

Faça login como você mesmo, `clancy`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8202
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<clancy-token>` abaixo):

```json
{"token": "owYzeYEn_oJ89HfQ0IRQy6tIrfxFOSXc"}
```

Agora liste os seus próprios pedidos com o seu token:

```
GET /orders HTTP/1.1
Host: 127.0.0.1:8202
Authorization: Bearer <clancy-token>
```

Response — `200`, e repare que contém **só o seu único pedido**:

```json
[{"id":"edec4558-0cf5-4462-aaba-308229ff6c4f","owner":"clancy","customer":"Omar Haddad","address":"3 Testing Blvd, Faketon","item":"Wireless mouse","amount":"$29.90"}]
```

Esse único item é a prova de que a API **sabe exatamente quem você é** e te escopa certo. Leia ele de volta pra confirmar que a feature funciona — `GET /orders/edec4558-0cf5-4462-aaba-308229ff6c4f` com o seu Bearer retorna `200` e o seu próprio pedido. E repare no que a sua lista **não** te dá: ela te entrega só o *seu* UUID, e um UUID não diz nada sobre nenhum outro. Diferente de um contador sequencial, onde ver `1007` te conta que `1006` e `1008` existem, esta lista te dá zero alavancagem sobre o id de qualquer outra pessoa. A app não oferece nada.

Um cross-check legítimo pra depois. Neste lab você também controla o login da alice, então logue como ela e leia o pedido vazado com o token **dela** — é assim que o acesso *autorizado* a ele se parece:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8202
Content-Type: application/json

{"user": "alice"}
```

```
GET /orders/376d2491-7bc1-44ea-b1f2-81cf7a34af58 HTTP/1.1
Host: 127.0.0.1:8202
Authorization: Bearer <alice-token>
```

Response — `200`, o pedido da alice. Deixe ele ao seu lado; no próximo passo o mesmo objeto volta pro *seu* token. (Numa engagement real você não teria o token da alice — só o id vazado e o seu próprio token. Este login é só o jeito do lab de mostrar o baseline autorizado.)

## 5. Passo 1 — Leia o pedido vazado (BOLA confirmado)

Te entregaram, de fora da app, o UUID de um pedido da alice: `376d2491-7bc1-44ea-b1f2-81cf7a34af58`. Você **não** o adivinhou e **não** o reconstruiu — ele *vazou* (um chamado de suporte, um print, um link compartilhado).

Peça ele com o seu próprio `<clancy-token>`, inalterado:

```
GET /orders/376d2491-7bc1-44ea-b1f2-81cf7a34af58 HTTP/1.1
Host: 127.0.0.1:8202
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"id":"376d2491-7bc1-44ea-b1f2-81cf7a34af58","owner":"alice","customer":"Alice Nguyen","address":"12 Example Ave, Springfield","item":"Mechanical keyboard","amount":"$89.00"}
```

Você leu o pedido de outra usuária — **com o nome e o endereço de entrega dela** — usando o seu próprio token válido, fornecendo um id que não é seu. Isso é o **BOLA**. Nada aqui é payload; o request é válido por toda regra de protocolo, um WAF (web application firewall) não vê nada de errado, e a autenticação "passou". A autorização do objeto simplesmente nunca foi consultada. O UUID aleatório não protegeu nada: no instante em que você *teve* um id válido, o check ausente o serviu.

Olhe o que aconteceu ao longo de dois requests. O mesmo `376d2491-…` voltou `200` pro `<alice-token>` no baseline *e* `200` pro `<clancy-token>` agora. O servidor **resolveu duas identidades diferentes corretamente** — `authenticate()` devolveu `alice` num request e `clancy` no outro — e **entregou o mesmo objeto aos dois**, porque a identidade, embora conhecida, nunca entra na decisão de acesso. É exatamente aí que o BOLA mora.

## 6. Passo 2 — O que a vuln NÃO é, e a inversão do Intruder

O exploit é um request legítimo com um token legítimo, então é fácil de ler errado. Este passo fixa a causa real e depois nomeia uma armadilha que o átomo anterior arma pra você.

**Não é identidade quebrada, e não é o formato do id.** Mande `GET /orders/376d2491-…` **sem nenhum header `Authorization`** — você leva `401`; a autenticação funciona. Mande `GET /orders` de novo com o seu `<clancy-token>` — `200`, escopado certo ao seu único pedido. Mande `GET /orders/376d2491-…` com esse mesmo `<clancy-token>` — `200`, o pedido da alice. O mesmo token dá escopo correto num handler e escopo nenhum no outro, então isso não é impersonation: você foi o `clancy` o tempo todo, e o endpoint de listagem te escopou certo. É um check que *existe* no `GET /orders` e *falta* no `GET /orders/:id`. O átomo companheiro `bola-sequential-id` percorre essa isolação auth-versus-authz request a request; o ponto que importa aqui é o que lá só se pôde *afirmar* e este átomo *demonstra*: um id não-adivinhável só tornaria a descoberta mais cara — nunca colocaria o check de volta. Aqui o id genuinamente é não-adivinhável, e a leitura aconteceu mesmo assim.

Agora a armadilha. No `bola-sequential-id` o beat de impacto era **enumeração**: manda `GET /orders/§id§` pro **Burp Intruder** (a ferramenta que repete um request substituindo um valor de uma lista), varre a faixa contígua `1001`–`1012`, e a coleção inteira sai. Tente o movimento análogo aqui — **sabendo de antemão que ninguém acha um UUID por brute force** (o espaço é ~2¹²²; isto é pra ver o que acontece, não uma tentativa séria de enumerar):

- **(a)** No Repeater, invente um UUID — digamos `ffffffff-ffff-4fff-8fff-ffffffffffff` — e mande com o seu `<clancy-token>` válido:

  ```
  GET /orders/ffffffff-ffff-4fff-8fff-ffffffffffff HTTP/1.1
  Host: 127.0.0.1:8202
  Authorization: Bearer <clancy-token>
  ```

  Response — `404`. Um token válido não conjura objetos, e a app nunca revela quais UUIDs são reais; um chute cego só erra.
- **(b)** Mande `GET /orders/§id§` pro Intruder e aponte pra uma leva de UUIDs aleatórios. Cada um volta `404` — um muro chapado deles, exatamente a imagem que o `bola-sequential-id` produziu quando você varreu o build *fixed* dele.

E aqui está a inversão, dita com todas as letras: no `bola-sequential-id`, um muro de `404` no Intruder significava a app **corrigida** (o ownership check te recusando). Aqui o mesmíssimo muro vem da app **vulnerable**, e significa só *"não achei um id real"*. O check continua ausente — alimente o endpoint com o único id real que te entregaram (`376d2491-…`) e ele serve o pedido da alice, PII e tudo. **A tela do Intruder não diz se a aplicação está corrigida — um muro de 404 é "não achei", não "não há o que achar".**

Que o id resista ao brute force pode te fazer duvidar se "UUID não-adivinhável" é defesa nenhuma — e há uma objeção justa a responder. O átomo web `idor-uuid-guessable` mostra um atacante *reconstruindo* o UUID de uma vítima e lendo o registro dela, o que parece um contra-exemplo. Não é, e a diferença é a **versão** do UUID. Aqueles ids são **UUIDv1**, que embute o timestamp e o MAC address do host e pode ser remontado a partir de metadado que a própria aplicação publica; os ids aqui são **UUIDv4**, ~122 bits de um CSPRNG (cryptographically secure pseudo-random number generator) sem nada dentro pra reconstruir. Os dois átomos provam uma tese por pontas opostas: um UUID não é automaticamente não-adivinhável (v1 dá pra remontar), e mesmo quando ele genuinamente é (v4, entregue a você de fora), o check ausente ainda serve o objeto. Aquele átomo ensina isso como uma lição entre várias e precisa do id ter *sido* reconstruível; aqui o id não-adivinhável é o ponto inteiro. De um jeito ou de outro, **o formato do id não conserta nada — adivinhável ou não.**

Então a causa é a object-level authorization ausente na rota de detalhe — não o token, não a sua identidade, não se o id dá pra adivinhar. A leitura do Passo 1 teve sucesso pelo mesmo check ausente do `bola-sequential-id`; o UUID mudou só o *custo de descoberta* (de trivial pra inviável), não o *acesso*.

## 7. Por que o fix funciona (porta 8302)

Aponte o Burp pra API fixed em `127.0.0.1:8302` e faça login lá (cada build tem o próprio mapa de tokens), e repita as leituras:

- `GET /orders/376d2491-…` (o pedido vazado) com o seu `<clancy-token>` → **`404`**. O pedido existe, mas não é seu, então a guarda de posse o recusa.
- `GET /orders/edec4558-0cf5-4462-aaba-308229ff6c4f` (o seu próprio pedido) com o seu `<clancy-token>` → `200`. Donos continuam lendo os próprios pedidos. A autenticação continua imposta: sem token ou com token ruim ainda leva `401`.
- **`404`, não algo que vaze:** o `404` de um pedido que você não possui é byte a byte o `404` de um id nunca seedado — `GET /orders/ffffffff-ffff-4fff-8fff-ffffffffffff` retorna o mesmo status, corpo e tamanho. O build fixed distingue um pedido real de um id inventado pra *ninguém*.
- **O fix deixou o id um UUID.** O patch não remodelou nada do id, porque o formato do id nunca foi o problema — o check ausente era. É a mesma guarda de um predicado que o `bola-sequential-id` usa, inalterada; o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) põe os dois fixes lado a lado.

O walkthrough termina aqui. O achado é a leitura cross-user de um id vazado; o fix é um predicado numa guarda. Não sobra nada pra exfiltrar e nenhuma variação que valha acrescentar — pra ir mais fundo na classe, a página da PortSwigger no theory primer é o lugar.
