# Walkthrough — bola-rest

## 1. Contexto

A app é uma pequena **API de pedidos** de e-commerce. Todo pedido tem um owner, um item e um valor, e você lê um via `GET /api/orders/<id>`. Os requests autenticam com um Bearer token que você pega do `POST /login`. O modelo mental do desenvolvedor é "um cliente só vê os próprios pedidos" — e o endpoint de listagem, `GET /api/orders`, faz exatamente isso. O endpoint de pedido único esqueceu.

Você vai ler o pedido de outra usuária usando **o seu próprio token, perfeitamente válido** — lendo um id que a própria API te entregou e pedindo o vizinho. Depois vai ver que o endpoint nunca checa de quem é o pedido: qualquer id que você segure, autenticado como você mesma, sempre bastou. Isto é **BOLA — Broken Object Level Authorization**, o [risco #1 do OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), e é o IDOR vestido de API — o mesmo bug de check ausente do `idor-numeric-id` e do `idor-uuid-guessable`.

Este átomo é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater**; se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra [`vulnerable/app.py`](./vulnerable/app.py). A view vulnerable é curta:

```python
@app.route("/api/orders/<int:order_id>")
def get_order(order_id):
    _authenticate()   # require a valid token (401 otherwise) -- AUTHENTICATION only
    order = ORDERS.get(order_id)
    if order is None:
        abort(404)
    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
    # checking that order["owner"] is the authenticated caller.
    return jsonify(order)
```

Leia duas vezes. Ela chama `_authenticate()`, então um token ausente ou inválido é recusado com `401`, e quando você chega no `return`, o request está *genuinamente autenticado*. Aí ela busca o pedido por id e o devolve. O bug é **o que não está lá**: nenhuma comparação entre `order["owner"]` e o caller. A função confia que "se você está logado e pediu o pedido N, você pode ver o pedido N". Essa confiança é a vulnerabilidade inteira.

Duas coisas pra internalizar desta forma:

- **Ela tem `_authenticate()`, e é exatamente isso que desarma o revisor apressado** — "tem auth no endpoint, parece ok". Mas autenticar e autorizar são perguntas diferentes. O endpoint responde *"quem é você?"* e nunca pergunta *"este pedido é seu?"*. Agora olhe o endpoint de listagem no mesmo arquivo — `GET /api/orders` filtra `ORDERS` por `owner == caller`. O desenvolvedor claramente *sabia* escopar por dono; só não fez no endpoint por id. **Essa assimetria — lista escopada, detalhe não — é a assinatura do BOLA no mundo real.**
- **Esta classe não dá `grep`.** Não tem `f"`, `|safe`, nem `eval` pra procurar. Você acha lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e aqui a resposta é em lugar nenhum.

## 3. Como funciona a "auth" deste lab

Auth de verdade (senha, hashing, session) está fora do escopo — essa cerimônia cabe num átomo de autenticação dedicado. Este lab simula com `POST /login`: manda um nome de usuário, recebe um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Não é um JWT; não tem nada codificado nele pra ler ou adulterar.

Duas coisas pra ter em mente antes de começar:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401`. Você confirma isso no Passo 3.
- **Se essa identidade autenticada é usada pra *autorizar* um objeto específico é outra pergunta** — e a `/api/orders/<id>` vulnerable não usa. Esse gap é o bug.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você não o decodifica, não o adultera, não o forja — você faz login como você mesma e usa o token exatamente como emitido. Ele fica válido e seu do começo ao fim. O alvo é o endpoint, não o token.

## 4. Exploração via Burp Suite

Aponte o Burp pra API vulnerable em `127.0.0.1:8012` e trabalhe do Repeater.

> **O token e os ids abaixo são de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu token vai diferir** — copie o seu da response do login e use no header `Authorization` o tempo todo. Os ids são estáveis (são seedados), e a cadeia é idêntica de qualquer jeito.

### Baseline — a API funcionando normalmente

Faça login como você mesma, mallory:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8012
Content-Type: application/json

{"user": "mallory"}
```

Response — `200`, um token que é seu pelo resto da sessão:

```json
{"token": "jXTGkJXWukSCs-zsD7QhkFYW1GKUMPKl"}
```

(Mostrado como `<mallory-token>` abaixo.) Agora liste os seus próprios pedidos:

```
GET /api/orders HTTP/1.1
Host: 127.0.0.1:8012
Authorization: Bearer <mallory-token>
```

Response — `200`, e repare que contém **só os seus pedidos**:

```json
[{"amount":"$29.90","id":40,"item":"Wireless mouse","owner":"mallory"},
 {"amount":"$12.99","id":42,"item":"USB-C cable","owner":"mallory"}]
```

Leia um dos seus de volta pra confirmar que a feature funciona — `GET /api/orders/40` com o seu Bearer retorna `200` e o seu pedido. A API faz o que promete.

### Passo 1 — Infira o id do vizinho

Olhe de novo a sua lista: você é dona dos pedidos **40** e **42**. Os ids são inteiros pequenos e sequenciais, e há um **buraco em 41** — um id bem no meio de dois que você possui. Os ids de pedido são uma única sequência global, então esse buraco é de um pedido de *outra pessoa*.

Não há o que adivinhar nem o que reconstruir aqui. A API te entregou os seus ids às claras, e o que falta está a um inteiro de distância. (Contraste com o `idor-uuid-guessable`, onde o id *parecia* aleatório e você tinha que reconstruí-lo a partir de um timestamp — aqui o id é só a interface.)

### Passo 2 — Leia o pedido da vítima (BOLA confirmado)

Peça o pedido 41 — o buraco — com o seu próprio token, inalterado:

```
GET /api/orders/41 HTTP/1.1
Host: 127.0.0.1:8012
Authorization: Bearer <mallory-token>
```

Response — `200`:

```json
{"amount":"$589.00","id":41,"item":"Standing desk","owner":"alice"}
```

Isso é o BOLA. Você leu o pedido da alice — o item dela, o valor dela — autenticada o tempo todo como você mesma, sem fazer nada além de pedir um id que a API te deu. Nada aqui é payload; o request é válido por toda regra de protocolo, um WAF não vê nada de errado, e a autenticação "passou". A autorização do objeto simplesmente nunca foi consultada.

(Um id que não existe — tipo `39` ou `999` — retorna `404`. Na app vulnerable o status até distingue "existe" de "não existe", mas isso pouco importa quando um acerto te entrega o objeto inteiro de qualquer forma.)

### Passo 3 — Prove que o bug é autorização ausente, não falha de auth nem id adivinhável

O exploit é rápido, e pode te enganar em direção a duas conclusões erradas. Mate as duas.

**(a) Não é falha de autenticação.** Pegue o request que acabou de funcionar — `GET /api/orders/41` com o seu Bearer, `200`, o pedido da alice — e varie só o token:

- Remova o header `Authorization` por completo → **`401`**.
- Corrompa o token (troque um caractere) → **`401`**.
- Restaure o seu token válido → **`200`**, o pedido da alice de novo.

A autenticação funciona *perfeitamente* — rejeita o token ausente e o token ruim. E mesmo assim, com o seu token genuíno, você leu o pedido da alice. Então a falha não é de autenticação: você esteve corretamente identificada como mallory o tempo todo. O que falta é autorização — estar autenticada como mallory nunca foi cruzado com o dono do pedido. **Estar autenticado não é estar autorizado.**

Contraste com o `idor-numeric-id`, onde o endpoint ignorava a identidade do caller por completo — trocar o header não mudava nada. Aqui o endpoint *lê* o token, pra autenticar; ele só joga essa identidade fora em vez de autorizar com ela. Essa é a forma mais comum e realista — e a distinção auth/authz só fica visível *porque* há autenticação real aqui, que os irmãos de header auto-declarado não tinham.

**(b) Não é sobre o id ser adivinhável.** Você não adivinhou nem reconstruiu nada — a `GET /api/orders` te entregou os seus ids e o buraco em 41 apontou direto pro alvo. Numa API REST, ids são *públicos por design*: clientes devem segurar e passar ids; é o contrato. Então a correção não é fazer o id virar UUID ou um valor aleatório — o `idor-uuid-guessable` já provou que remodelar o id é teatro. A prova está no fix (§7): a app corrigida mantém o id sequencial **intacto** e só acrescenta o ownership check. O formato do id nunca foi o problema; a object-level authorization ausente era.

Uma causa raiz embaixo das duas: não existe object-level authorization check.

## 5. Por que isto é BOLA, e por que o id nunca foi o ponto

No `idor-uuid-guessable` dissemos que remodelar o id — trocar um inteiro por um UUID — era *"obfuscation... teatro"*, que "só muda quanto custa *achar* o bug". Este átomo remove até a obscuridade: numa API o id é público por contrato — a listagem te entrega o seu, e o vizinho é o próximo inteiro. Não sobra nada pra se esconder atrás, então a autorização é a única coisa que poderia proteger o objeto. O token prova que você é você; ele não diz de quem é este pedido.

| Átomo (A01) | Objeto alcançado por… | O id é… | Check ausente |
|---|---|---|---|
| `idor-numeric-id` | trocar um id (`/notes/1` → `/notes/2`) | inteiro sequencial | ownership (a nota é sua?) |
| `idor-uuid-guessable` | reconstruir e usar o UUID | UUIDv1 reconstruível | ownership (o recibo é seu?) |
| `bola-rest` | ler o próprio id na API e pedir o vizinho | **inteiro sequencial, público por design de API** | **object-level authorization (o pedido é seu?)** |
| `path-traversal-basic` | navegar o filesystem (`notes.txt` → `../../etc/passwd`) | caminho de arquivo | confinamento (o path ficou na pasta?) |

Os três átomos de IDOR/BOLA dividem exatamente a mesma causa e o mesmo fix — checar o dono do objeto contra o caller. Diferem só no formato do id e em quanta autenticação existe em volta: o `idor-numeric-id` conta, o `idor-uuid-guessable` reconstrói, e aqui o id é simplesmente público enquanto a autenticação real deixa "authenticated ≠ authorized" impossível de ignorar. O `path-traversal-basic` é a mesma família A01 por outro eixo (confinar um caminho em vez de possuir um objeto).

## 6. Impacto

Escalação horizontal de privilégio: você leu o pedido de outra usuária do mesmo nível — o item dela, o valor, a compra. Esse é o teto honesto. **Não é RCE, e não é escalação vertical** — você não ganhou execução de código nem um papel elevado. O BOLA está no #1 do OWASP API Security Top 10 por ser onipresente e de alto impacto em APIs reais, onde objetos de pedido/conta costumam carregar PII que *encadeia* pra mais ataques — mas o achado neste átomo é a leitura cross-user em si.

## 7. Por que o fix funciona

Rode a cadeia contra a API fixed na porta **8112** (veja o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) pra mudança). Faça login como mallory lá — um token novo, porque a app fixed é um processo separado — e:

- **Leia o vizinho, `GET /api/orders/41`, com o seu token válido → `404`.** Você segura um token perfeitamente bom e ainda assim é recusada, porque a view fixed compara `order["owner"]` com o caller antes de devolver. Este único check fecha o BOLA.
- **Leia o seu próprio, `GET /api/orders/40` → `200`.** Donos continuam pegando os próprios pedidos.
- **A autenticação continua imposta** — sem token ou com token ruim ainda leva `401`.

Duas coisas que o fix deliberadamente *não* faz. Ele não remodela o id — o pedido 41 continua um inteiro sequencial simples, porque o id nunca foi o problema. E ele retorna **`404`, não `403`**. Um `403` confirmaria que o pedido existe ("está lá, mas não é pra você"); com ids sequenciais isso é um oráculo de enumeração — varra os inteiros e `403`-vs-`404` mapeia todo pedido do sistema. A app fixed retorna `404` pra não-dono *e* pra id genuinamente inexistente — indistinguíveis, então o status não vaza nada. Prove: `GET /api/orders/999` (inexistente) e `GET /api/orders/41` (existe, não é seu) voltam byte a byte idênticos. (O `idor-numeric-id` e o `idor-uuid-guessable` retornam `403`; o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) explica por que aquilo era ok pra eles e por que ids sequenciais numa API mudam a resposta aqui.)
