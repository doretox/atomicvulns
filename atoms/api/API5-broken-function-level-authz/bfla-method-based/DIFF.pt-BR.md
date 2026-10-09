# DIFF — vulnerable vs. fixed

O `vulnerable/app.ts` e o `fixed/app.ts` diferem em exatamente um lugar — uma guarda inserida no `PATCH /users/:handle`, entre o check de autenticação e a busca do registro, mais o comentário acima dela. O `POST /login`, o `GET /users/:handle`, o seed `USERS`, o mapa `TOKENS`, os helpers, os imports, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). O resto do handler `PATCH` também é: o `401`, a busca, o `404` dela, a escrita e a resposta são os mesmos bytes nos dois builds. A mudança é um ownership check, acrescentado ao método que estava sem ele.

## O fix — o ownership check do `GET`, agora também no `PATCH`

```diff
 app.patch("/users/:handle", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
-  // VULNERABLE: the GET handler on this same path guards the record with an ownership
-  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
-  // the path -- guarding the read left the write on the same resource wide open.
+  // FIXED: the same ownership check the GET handler already has, now on PATCH too --
+  // authorization covers every method of the path, not just the one the dev remembered.
+  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);                               // unknown target user
   user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
   res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
 });
```

O `PATCH` fixed escreve só quando o registro é o do próprio caller. Nada de novo foi inventado pra tomar essa decisão: a guarda que ele acrescenta é **byte-idêntica** à que o `GET /users/:handle` já carrega —

```ts
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
```

— a mesma linha, agora no método de onde ela faltava. A autorização nunca foi propriedade do *path*; é propriedade de cada par **(método, path)**, e o build vulnerable a tinha escrito pra um método e deixado o outro pelado. **O fix não inventa nada: ele leva a guarda de posse do handler `GET` para o handler `PATCH`, pra que a pergunta que a leitura já fazia seja finalmente feita pela escrita.**

**Leia o predicado pelo que ele pergunta.** O `req.params.handle !== caller` compara duas coisas — o handle no path e o `caller`, a identidade que o `authenticate()` acabou de resolver a partir do token — e é uma comparação de string simples, não uma busca: o registro nunca é consultado pra tomar a decisão. A guarda fica na linha acima de `const user = USERS.get(req.params.handle)`, então, quando ela roda, o registro ainda não foi buscado. Essa ordem faz parte do fix, e é a mesma disciplina que o `bola-nested-resource` usa — lá, o `operates()` checa a loja pai antes de qualquer pedido ser buscado; aqui, a posse é checada antes de qualquer registro ser.

## Quatro fixes, quatro perguntas

Os dois átomos de posse de API1, o de nested resource e o de função admin corrigiram seus handlers de três formas; este átomo reusa o *conteúdo* da primeira forma num eixo novo. Lado a lado, cada linha tirada do `fixed/app.ts` do próprio átomo:

```ts
// bola-sequential-id, bola-uuid-leaked — a predicate on the object, AFTER the lookup
  if (!order || order.owner !== caller) return res.sendStatus(404);

// bola-nested-resource — the lookup itself, moved INTO the authorized parent's scope
  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));

// bfla-admin-function — a guard on the caller's role, BEFORE the lookup
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);

// bfla-method-based — the GET handler's ownership guard, now on the PATCH it was missing from
  if (req.params.handle !== caller) return res.sendStatus(403);
```

- **O `bola-sequential-id` e o `bola-uuid-leaked`** perguntam *este objeto é seu?* O handler fixed busca o pedido na coleção global exatamente como o gêmeo vulnerable dele faz, e então o recusa a menos que o `order.owner` seja o caller — um predicado de posse, acrescentado à guarda depois da busca.
- **O `bola-nested-resource`** pergunta *ele pertence a esta loja?* O fix dele não acrescenta predicado a guarda nenhuma; ele move a busca pra dentro do `ordersOf(req.params.storeId)`, o escopo da loja que o request já autorizou, então o pedido de outra loja nunca é encontrado.
- **O `bfla-admin-function`** pergunta *você pode invocar esta operação?* O fix dele acrescenta uma guarda sobre a **role** do caller, antes da busca, e nenhum campo do alvo entra na decisão.
- **Este átomo** faz uma pergunta que não é nem só sobre o objeto nem sobre a role: *a autorização está em todo método deste path?* O fix dele responde copiando o ownership check do `GET` pro `PATCH`.

O conteúdo do check deste átomo é object-level — o mesmo *"este registro é meu?"* que os átomos de API1 ensinaram, e a razão de o fix comparar um handle com o caller em vez de ler uma role. Mas a *brecha* que ele fecha não é uma brecha object-level; é um **método** deixado sem cobertura. Nenhum dos quatro é *o* fix de autorização: cada um responde à própria pergunta. O que se transfere é o método — autorize a operação que você está prestes a rodar, no eixo que essa operação exige — e a pergunta de auditoria que pega esta: *todo método deste path carrega a autorização que o recurso precisa?*

## A resposta não é dado de terceiros

O `res.json({ handle: req.params.handle, displayName: user.displayName })` parece devolver o registro, mas numa escrita ele reflete só o que o caller acabou de mandar: o `handle` é o parâmetro de path ecoado de volta, e o `user.displayName` foi posto, uma linha antes, em `req.body?.displayName` — o próprio input do atacante. Então o `200` do Passo 1 do walkthrough prova exatamente uma coisa: o **bypass** — o servidor aceitou e rodou a escrita pra um não-dono. Ele **não** prova que o registro guardado da `alice` mudou de alguma forma específica; um endpoint que ignorasse o `:handle` e ecoasse o corpo de volta responderia idêntico. A prova de que a escrita pegou vem não desta resposta, mas da vítima lendo o próprio registro (próxima seção).

Isso importa porque mantém a classe clara. Um `PATCH` que respondesse com o dado *anterior* do alvo entregaria ao atacante um registro alheio na resposta — e essa leitura, *"recebi de volta um dado que não era meu"*, é BOLA, o eixo errado. Aqui nada da `alice` volta que o atacante não tenha mandado, então a única coisa que o `200` pode significar é que um método rodou que deveria tê-lo recusado.

## A escrita é real, e a vítima consegue mostrá-la

O `user.displayName = req.body?.displayName ?? user.displayName` muta de verdade a entrada do registro no `Map`, e a mudança vale enquanto o processo estiver rodando. Mas o atacante não consegue vê-la pela API: a resposta do `PATCH` só ecoa o input dele, e o `GET /users/:handle` recusa com `403` um registro que não é o dele. Não há rota que devolva o registro de outro usuário pra ele — o que é exatamente certo, já que essa leitura é justo a coisa que o `GET` protege corretamente.

A única conta que *consegue* ler o registro da `alice` é a `alice`. Logada como ela mesma, o `GET /users/alice` devolve `200` com o `displayName` que o atacante plantou — no build vulnerable, `"pwned by clancy"` em vez do seed `"Alice Nguyen"`; no build fixed, ainda `"Alice Nguyen"`, porque a escrita foi recusada antes de rodar. O mesmo `GET` protegido que prova que o ownership check funciona é também o instrumento que prova que a escrita aconteceu. Cada gêmeo tem o próprio seed, então uma edição na 8205 é invisível na 8305.

*(Sobre os tipos: o `USERS.get(req.params.handle)` é `User | undefined` pela própria assinatura do `Map.get` — não pelo `noUncheckedIndexedAccess`, que está ligado mas não é o que força isso — então a guarda `if (!user)` é obrigatória nos dois gêmeos; remova-a e o `user.displayName` falha com `TS18048: 'user' is possibly 'undefined'`. A guarda de posse acrescentada não precisa desse cuidado: `req.params.handle !== caller` é uma comparação de string, sem `Map.get` e portanto sem `?.`, diferente da guarda de role do `bfla-admin-function`.)*

## 403, não 404 — um critério, um check antes da busca

Um não-dono leva **`403`** do `PATCH` fixed, e o `GET` responde a uma leitura alheia do mesmo jeito — não o `404` que os três átomos de API1 devolvem pra um pedido fora do escopo do caller. Isso não é exceção à série; é o critério único da série aplicado a um check de outra forma.

**O critério.** O [`DIFF.pt-BR.md`](../../API1-broken-object-level-authz/bola-sequential-id/DIFF.pt-BR.md) do `bola-sequential-id` fecha a discussão de status code com uma regra de bolso — *`404` quando a própria existência vaza; `403` quando admitir a existência é ok* — e o [`DIFF.pt-BR.md`](../../API1-broken-object-level-authz/bola-nested-resource/DIFF.pt-BR.md) do `bola-nested-resource` a põe como pergunta: *a existência do alvo é, em si, sensível?* O RFC 9110 (HTTP Semantics) prevê as duas respostas na §15.5.4 (403 Forbidden):

> The 403 (Forbidden) status code indicates that the server understood
> the request but refuses to fulfill it. […]
>
> If authentication credentials were provided in the request, the
> server considers them insufficient to grant access. […]
>
> An origin server that wishes to "hide" the current existence of a
> forbidden target resource MAY instead respond with a status code of
> 404 (Not Found).

O `404` é um `MAY`: uma opção pra um servidor que tem uma existência que valha a pena esconder, não um default.

**Por que o `404` não se transfere aqui.** No `bola-sequential-id` e no `bola-nested-resource` o ownership check roda *depois* da busca, sobre um pedido tirado de um espaço de ids enumerável e contíguo (`1001`–`1012`); lá, um `403` pra "existe, mas não é seu" ao lado de um `404` pra "não existe" seria um oráculo de enumeração — uma diferença nas respostas que mapeia quais ids existem sem ler nenhum deles —, então o critério dá `404`. (O `bola-uuid-leaked` mantém esse `404` por herdar o fix, com o espaço de ids dele já não varrível.) O check deste átomo é de outra forma: o `req.params.handle !== caller` roda *antes* de qualquer busca e compara o handle do path com o do próprio caller. Ele dispara idêntico pra um registro que existe e pra um que nunca foi seedado — os dois são simplesmente "não é seu" —, então ele nunca consulta, e nunca revela, se o alvo existe. Não há oráculo a fechar, e nada a esconder atrás de um `404`. Pelo mesmo critério, a resposta honesta é `403`.

E o `403` é honesto nos termos do próprio RFC: credenciais *foram* fornecidas — um token válido, genuinamente do caller — e o servidor as considera insuficientes pra este registro, que é exatamente a segunda frase citada. O `401` fica onde estava, pra token ausente ou inválido; pelo §15.5.2, o servidor que gera um `401` *"MUST send a WWW-Authenticate header field … containing at least one challenge"* — aqui `Bearer` — e o `403` não traz nenhum, porque o caller já está autenticado e não há o que pedir. O único `404` que sobra no código — o `if (!user)` pra um alvo desconhecido — é inalterado nos dois gêmeos, mas no build fixed ele fica atrás da guarda de posse, que só o handle do próprio caller (sempre seedado) atravessa, então ele não consegue disparar lá; o build vulnerable, sem a guarda, é o único lugar onde o `PATCH /users/nobody` chega a esse `404`.

**Regra de bolso — um critério só, o da série: a existência do alvo é sensível (ou sequer revelada)?** Sim → **`404`**, que torna "não autorizado" indistinguível de "não existe": o pedido no `bola-sequential-id` e no `bola-nested-resource`, onde um espaço de ids enumerável transformaria um `403` em oráculo. Não → um **`403`** honesto: a loja no `bola-nested-resource` (um slug público), a função admin no `bfla-admin-function` (uma capacidade conhecida), e aqui, onde o check compara identidades antes de qualquer busca e por isso não revela existência nenhuma. O RFC 9110 oferece os dois; quem escolhe é a forma do check — o que ele lê, e quando —, não o átomo.

## Isto é BFLA — autorização num método, não num path

Nada que o caller manda é parseado ou executado. Um request legítimo, sob um token legítimo, escreve num registro por um método que nunca checou se o registro era do caller — enquanto o `GET` no mesmíssimo path checa exatamente isso e recusa. Isso é Broken Function Level Authorization — **API5:2023** no OWASP API Security Top 10 — na forma method-based, e o impacto é **horizontal**: um usuário comum editando o registro de um par, onde o `bfla-admin-function` mostrou o tipo vertical, um usuário comum alcançando a capacidade de um admin. Ler como BOLA te aponta pro lugar errado: o ownership check object-level está presente e *correto* no `GET`, e a falha não é ele estar errado, mas ele não cobrir o `PATCH`. Como no resto da série, o bug mora no `app.ts` e não dá `grep`: não há string perigosa pra achar. Você o pega listando os métodos que um path aceita e perguntando, de cada um, *isto carrega a autorização que o recurso precisa?* — e reparando, aqui, que a leitura carregava e a escrita não.
