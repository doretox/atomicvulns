# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` e `fixed/app.ts` diferem em exatamente um lugar — a guarda que segue a busca do pedido no `GET /orders/:id`. `POST /login`, `GET /orders`, os helpers, os imports, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). A mudança é um object-level authorization check.

## O fix — existência e posse viram uma guarda só

```diff
 app.get("/orders/:id", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
   const order = ORDERS[Number(req.params.id)];
-  if (!order) return res.sendStatus(404);
-  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
-  // order.owner is the caller. Authenticated is not authorized for THIS object.
-  res.json(order);                                          // BOLA -- no object-level check
+  // FIXED: existence and ownership are ONE guard with ONE exit -- a missing order and
+  // someone else's order both hit the same sendStatus(404), so "doesn't exist" and
+  // "not yours" are byte-identical by construction (a 403 here would be an enumeration oracle).
+  if (!order || order.owner !== caller) return res.sendStatus(404);
+  res.json(order);
 });
```

O handler fixed devolve o pedido só quando ele existe **e** pertence ao caller. Esse único predicado fecha o BOLA: a classe é "o servidor devolve um objeto escopado a usuário sem checar que o caller é o dono", e a remediação é exatamente a negação disso.

## Uma guarda, uma saída — a indistinguibilidade é estrutural

Leia o que o fix de fato fez com o fluxo de controle. A versão vulnerable tinha duas saídas separadas: `if (!order) return sendStatus(404)` pra pedido inexistente, e depois `res.json(order)` pra todo o resto — inclusive o pedido de outra pessoa. O fix **funde existência e posse numa única condição** — `!order || order.owner !== caller` — compartilhando **um** `return res.sendStatus(404)`.

Essa fusão é o ponto inteiro. "Não existe" e "existe mas não é seu" agora passam pela mesma linha, retornam o mesmo status e emitem o mesmo corpo — não porque alguém lembrou de fazer as duas respostas casarem, mas **por construção**: só há um caminho de recusa, então só há uma coisa que ele pode dizer. A object-level authorization aqui é uma condição de guarda *no mesmo nível que a existência* — não um check opcional aparafusado depois de o objeto já estar na mão. Escreva como uma guarda só e o oráculo de enumeração (próxima seção) não pode existir; escreva como um segundo `if` com a própria saída `403` e você tem que lembrar de manter as duas respostas idênticas, pra sempre.

## 404, não 403 — o oráculo de enumeração

O handler fixed retorna **`404`** pra um pedido que o caller não possui — não `403` — e um id genuinamente inexistente também retorna `404`. Os dois são deliberadamente indistinguíveis, e com estes ids essa indistinguibilidade é a segunda tarefa do fix, não um capricho de estilo.

Por que não `403`? Porque os ids são **sequenciais**. Um `403` anuncia "este pedido existe, mas não é seu"; um `404` de id inexistente diz "não há nada aqui". Dê os dois a um atacante e, varrendo os inteiros contíguos `1000, 1001, 1002, …`, o par `403`-vs-`404` vira um **oráculo de enumeração** — um mapa de exatamente quais ids são reais, montado sem nunca ler o conteúdo de um pedido. Retornar `404` pra "não é seu" e pra "não existe" não vaza nada: o atacante não consegue nem saber quais ids existem. Você confirma isso contra a API fixed — `GET /orders/1001` (um pedido real que não é seu) e `GET /orders/1013` (nunca seedado) voltam byte a byte idênticos.

Este é um movimento reconhecido e amparado por padrão, não um truque:

- **Um repositório privado no GitHub retorna `404`, não `403`**, pra quem não tem acesso — justamente pra que a resposta não confirme que o repo existe. Mesmo movimento: esconder a **existência**, não só o **conteúdo**.
- **O RFC 9110 (HTTP Semantics) prevê a troca explicitamente.** Na **§15.5.4 (403 Forbidden)** ele afirma que *"an origin server that wishes to 'hide' the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found)"*, e a **§15.5.5 (404 Not Found)** confirma que um servidor pode usar `404` quando *"is not willing to disclose that one exists"*. Esconder a existência atrás de um `404` é um uso que o padrão antecipa, não um abuso dele.
- **`403` é a escolha legítima quando a existência do objeto não é sensível.** Isto é uma bifurcação real, não um certo-versus-errado: `404`-como-defesa-contra-oráculo é o correto *aqui* porque os ids são enumeráveis e a existência vaza. Num contexto onde admitir que um objeto existe é inócuo, `403` — semanticamente mais claro, "está lá e não é pra você" — é perfeitamente correto. O RFC 9110 oferece os dois; a escolha depende de **se a existência é sensível**, e ids sequenciais a tornam sensível. Regra de bolso: **`404`** quando a própria existência vaza; **`403`** quando admitir a existência é ok.

## O que o fix *não* faz — o id continua sequencial

Repare o que o diff não toca: o id. O pedido `1001` continua um inteiro contíguo simples, ainda na URL, ainda entregue aos clientes pelo endpoint de listagem. O fix **não** o troca por um UUID, não o randomiza, não o esconde. Isso é proposital, e é metade da lição.

Duas coisas estão em jogo e só uma é o bug. O **id sequencial** governa a *descoberta* — inteiros contíguos tornam os vizinhos baratos de achar. O **check ausente** governa o *acesso* — é o que deixa um não-dono ler o objeto, ponto. Um id não-adivinhável só encareceria a descoberta; nunca restauraria o check. Então remodelar o id conserta o eixo errado: o atacante que já segura um id (o endpoint de listagem te entrega um) passa reto por ele, e você fica com o mesmo BOLA atrás de um número mais comprido. A regra transferível, a mesma que os átomos web `idor-numeric-id` e `bola-rest` ensinam: **corrija o check ausente, não remodele o identificador.**

## O endpoint de listagem já escopa — a assimetria é o BOLA

O `GET /orders` é *idêntico* nas duas versões, e nas duas ele filtra certo: `Object.values(ORDERS).filter((o) => o.owner === caller)`. O desenvolvedor sabia escopar uma resposta pro dono dela — fez na coleção. Só não fez no endpoint de objeto único. Essa assimetria — **lista escopada, item não** — é exatamente como o BOLA aparece em codebases reais, e é por isso que a lista continuar correta na versão fixed não é um segundo fix: ela nunca esteve quebrada. O único bug morava no `GET /orders/:id`, e a guarda de um predicado é o reparo inteiro.

## O token é opaco, e o ataque nunca o toca

O Bearer token é uma string opaca aleatória (`randomBytes(24).toString("base64url")`) resolvida server-side pelo mapa `TOKENS` — um substituto pra um OAuth2 opaque access token ou uma session id, não um JWT. Nada no ataque inspeciona, decodifica, adultera ou forja ele; o `dana` faz login como ele mesmo e manda o próprio token, inalterado, o tempo todo. É esse o ponto de um token opaco cripto-forte aqui: ele é sólido e legitimamente dele, então a única coisa que sobra pra explicar a leitura cross-user é a autorização ausente. Um token fraco ou forjável seria uma *segunda* vulnerabilidade (broken authentication); mantê-lo forte prende este átomo a exatamente um bug. O token não é a vulnerabilidade; o endpoint é.

## Isto é BOLA — IDOR numa API, e mora no app.ts

Nada que o caller manda é parseado ou executado; um id legítimo simplesmente alcança um objeto fora do escopo do caller. Isso é Broken Object Level Authorization — **API1:2023**, o risco #1 do OWASP API Security Top 10 — e é o IDOR vestido de API, a mesma forma dos átomos web `idor-numeric-id` e `bola-rest`: troca um número, e o servidor te entrega um objeto que ele nunca checou ser seu. Como nos dois, o bug mora no `app.ts`, não em algum template (não há nenhum), e não dá `grep`: não há string perigosa pra achar. Você o pega lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e reparando, aqui, que uma chamada `authenticate()` funcionando foi silenciosamente confundida com esse check.
