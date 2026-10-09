# DIFF — vulnerable vs. fixed

O `vulnerable/app.ts` e o `fixed/app.ts` diferem em exatamente um lugar — uma guarda inserida no `POST /admin/users/:handle/promote`, entre o check de autenticação e a busca do alvo, mais o comentário acima dela. O `POST /login`, o seed `USERS`, o mapa `TOKENS`, os helpers, os imports, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). O resto do handler também é: o `401`, a busca do alvo, o `404` dela, a escrita e a resposta são os mesmos bytes nos dois builds. A mudança é um function-level authorization check.

## O fix — a role do caller é checada logo depois da autenticação, antes da busca do alvo

```diff
 app.post("/admin/users/:handle/promote", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
-  // VULNERABLE: the caller is authenticated, but the handler never checks the caller's
-  // ROLE. Promoting a user to admin is an admin-only function; here ANY authenticated
-  // user can invoke it. Authenticated is not authorized to PERFORM this operation.
+  // FIXED: function-level authorization. Promoting is an admin-only capability, so the
+  // caller's ROLE is checked right after authentication -- a non-admin is refused 403
+  // BEFORE the target is ever looked up, so the gate leaks nothing about who exists.
+  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
   const target = USERS.get(req.params.handle);
   if (!target) return res.sendStatus(404);                  // unknown target user
   target.is_admin = true;                                   // state change -- not a read
   res.json({ handle: req.params.handle, is_admin: true });  // the state delta, not third-party data
 });
```

O handler fixed executa a promoção só quando o caller é administrador. Tudo de que essa decisão precisa já estava no build vulnerable: o `caller` guardava o handle autenticado, e todo usuário do seed já carregava um flag `is_admin`. O handler vulnerable simplesmente nunca consultou nenhum dos dois antes de agir.

**Leia o predicado pelo que ele pergunta.** O `USERS.get(caller)?.is_admin` faz uma pergunta só — *o caller é admin?* — e o único dado de que ela depende é o `caller`, a identidade que o `authenticate()` acabou de resolver a partir do token. O alvo não é argumento dessa pergunta, e nem poderia ser: a guarda fica na linha acima de `const target = USERS.get(req.params.handle)`, então, quando a decisão é tomada, o alvo ainda não foi buscado. Quer o `:handle` nomeie a `alice`, o próprio caller ou uma conta que nunca foi seedada, a guarda recebe o mesmo dado e dá a mesma resposta. **O fix não acrescenta check nenhum sobre o alvo — ele só pergunta se o caller pode rodar a função.**

A posição faz parte do fix. A function-level authorization fica logo ao lado da autenticação, na linha seguinte a ela, e não como um acréscimo de última hora, com a operação já em andamento: a primeira guarda estabelece quem está chamando, a segunda se esse caller pode invocar esta função, e só então o handler toca na conta sobre a qual opera. É a mesma disciplina de ordem que o `bola-nested-resource` usa — lá, o `operates()` checa a loja pai antes de qualquer pedido ser buscado; aqui, o check de role roda antes de qualquer usuário ser.

**O compilador exige o `?.`.** O `Map.get` é declarado como retornando `V | undefined`, então o `USERS.get(caller)` tem tipo `User | undefined` mesmo que, em runtime, o `caller` seja sempre um handle seedado (o `POST /login` só emite token pra usuário que está no `USERS`). O `?.` é, portanto, obrigatório: troque-o por um `.` simples e o `tsc` acusa `TS2532: Object is possibly 'undefined'`. A mesma assinatura dá ao `target` o tipo `User | undefined`, e é por isso que a guarda `if (!target)`, inalterada, é obrigatória nos dois gêmeos — remova-a e o `target.is_admin = true` falha com `TS18048: 'target' is possibly 'undefined'`. Os dois erros vêm da assinatura do `Map.get`, não do `noUncheckedIndexedAccess`: o flag continua ligado, herdado da série, mas desligá-lo não muda nenhum dos dois erros. E, se o `?.` algum dia fizer curto-circuito, `!undefined` é `true` e a guarda recusa — o check é fail-closed.

## Três perguntas, três fixes

Os três átomos de API1 corrigiram seus handlers de duas formas; este átomo acrescenta uma terceira. Lado a lado, cada linha tirada do `fixed/app.ts` do próprio átomo:

```ts
// bola-sequential-id, bola-uuid-leaked — a predicate on the object, AFTER the lookup
  if (!order || order.owner !== caller) return res.sendStatus(404);

// bola-nested-resource — the lookup itself, moved INTO the authorized parent's scope
  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));

// bfla-admin-function — a guard on the caller's role, BEFORE the lookup
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
```

- **O `bola-sequential-id` e o `bola-uuid-leaked`** perguntam *este objeto é seu?* O handler fixed busca o pedido na coleção global exatamente como o gêmeo vulnerable dele faz, e então o recusa a menos que o `order.owner` seja o caller — um predicado de posse, acrescentado à guarda depois da busca.
- **O `bola-nested-resource`** pergunta *ele pertence a esta loja?* O fix dele não acrescenta predicado a guarda nenhuma; ele move a busca pra dentro do `ordersOf(req.params.storeId)`, o escopo da loja que o request já autorizou, então o pedido de outra loja nunca é encontrado.
- **Este átomo** pergunta *você pode invocar esta operação?* O fix dele acrescenta uma guarda sobre a role do caller, antes da busca.

Depois da busca, dentro dela, antes dela. Nas duas formas de API1 o check é feito contra o pedido — o `owner` dele, ou o `storeId` pelo qual o `ordersOf()` filtra. Aqui nenhum campo do alvo é consultado, porque a pergunta não é sobre o alvo. Nenhum dos três é *o* fix de autorização; cada um é o fix da própria pergunta. O que se transfere é o método: autorize a operação que você está prestes a rodar, no eixo que essa operação exige — o dono do objeto, o pai do objeto ou a role do caller.

## A resposta não é dado de terceiros

O `res.json({ handle: req.params.handle, is_admin: true })` é montado a partir de duas coisas, e nenhuma delas é lida do alvo: o `handle` é o parâmetro de path que o caller mandou, ecoado de volta, e o `is_admin: true` é um literal no código-fonte. O usuário que o handler buscou é escrito — `target.is_admin = true` — e nunca serializado. Compare com o `res.json(order)` dos átomos de API1, onde a resposta *era* o registro guardado: nome do comprador, endereço de entrega, item, valor. Aqui não existe registro desses pra devolver; um usuário do seed carrega um campo, `is_admin`, e nada mais.

Isso é deliberado, e é o que mantém o átomo no eixo dele. Uma função admin que devolvesse o registro de outra pessoa convidaria a leitura de BOLA — *vi um dado que não era meu* — e a classe seria arquivada no lugar errado. Uma função que muda estado e responde só com o que o próprio caller mandou e uma constante deixa uma única explicação pro `200`: a função rodou pra um caller que não deveria ter conseguido rodá-la.

## A escrita é real, e a API não consegue mostrá-la

O `target.is_admin = true` muta de verdade a entrada do usuário no `Map`, e a mudança vale enquanto o processo estiver rodando. Nada na API a lê de volta. A superfície são duas rotas, o `POST /login` e a função admin, e nenhuma das duas devolve uma role. E o corpo de sucesso é determinístico: os mesmos bytes quer o alvo fosse membro comum, quer já fosse admin — promova a `alice` duas vezes e as duas respostas saem byte a byte idênticas. De fora, um `200` só diz que a função rodou.

No build vulnerable, o `is_admin` é escrito e nunca lido. No build fixed ele tem exatamente um leitor, a guarda acrescentada — então a evidência de que o flag governa alguma coisa vem do comportamento do gêmeo fixed (a `carol` leva `200`, o `clancy` leva `403`), nunca de observar o flag pela API.

## 403, não 404 — um critério, outro tipo de alvo

O handler fixed recusa um não-admin com **`403`**, onde os três átomos de API1 respondem `404` pra um pedido fora do escopo do caller. Isso não é exceção à série, e não é regra nova. É o critério único da série, aplicado a um alvo de outro tipo.

**O critério.** O [`DIFF.pt-BR.md`](../../API1-broken-object-level-authz/bola-sequential-id/DIFF.pt-BR.md) do `bola-sequential-id` fecha a discussão de status code com uma regra de bolso — *`404` quando a própria existência vaza; `403` quando admitir a existência é ok* — e o [`DIFF.pt-BR.md`](../../API1-broken-object-level-authz/bola-nested-resource/DIFF.pt-BR.md) do `bola-nested-resource` põe a mesma regra como pergunta: *a existência do alvo é, em si, sensível?* O RFC 9110 (HTTP Semantics) prevê as duas respostas na §15.5.4 (403 Forbidden):

> The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it. […]
>
> If authentication credentials were provided in the request, the server considers them insufficient to grant access. […]
>
> An origin server that wishes to "hide" the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found).

O `404` é um `MAY`: uma opção pra um servidor que tem uma existência que valha a pena esconder, não um default.

**De que lado caem os átomos de API1.**

- **No `bola-sequential-id` e no `bola-nested-resource`, a existência de um pedido é sensível.** Os ids de pedido são inteiros contíguos, `1001`–`1012` — no `bola-nested-resource`, um contador global único compartilhado por todas as lojas. Um `403` pra "existe, mas não é seu" (ou "existe, mas em outra loja") ao lado de um `404` pra "não existe" seria um oráculo de enumeração: uma diferença nas respostas que mapeia quais ids existem sem ler nenhum deles. O critério dá `404`.
- **O `bola-uuid-leaked` mantém o mesmo `404` por herdar o fix, não por pressão nova.** Os ids dele são UUIDs aleatórios, a pressão de oráculo *"quase some"*, e o DIFF dele mantém o `404` como *"o default conservador que nunca está errado."*
- **O `bola-nested-resource` também aplica o critério no outro sentido.** No mesmo handler, o slug de uma loja é um nome público, a existência dela não é sensível, e uma loja que você não opera leva `403`. O `403` honesto já é precedente da série.
- **Nos três, o alvo da autorização é um objeto** — um pedido ou uma loja, uma instância endereçada por um id ou um slug no path.

**Aqui o alvo é uma capacidade.** O que a guarda protege é uma função única e nomeada, não uma instância num espaço de ids, e a existência dessa função é premissa deste átomo: o path admin é simplesmente conhecido — nomes previsíveis, uma spec OpenAPI que costuma ser pública, um bundle de front-end que o carrega. Não há espaço de ids pra varrer nem existência a esconder; um `404` não esconderia nada que o atacante já não tenha, e contradiria a premissa de que o átomo parte. O critério, portanto, dá `403`, como deu pra loja.

E o `403` é a resposta honesta nos termos do próprio RFC. Credenciais *foram* fornecidas — um token válido, genuinamente do `clancy` — e o servidor as considera insuficientes pra esta função, que é exatamente o caso que a segunda frase citada descreve. O `401` fica onde estava, pra token ausente ou inválido, então os dois codes mantêm autenticação e function-level authorization separadas.

**A recusa não é um oráculo, por construção.** A guarda roda antes da busca do alvo, então um não-admin leva o mesmo `403` quer o alvo seja a `alice`, ele mesmo ou um handle que nunca foi seedado. Ela revela um fato — que o caller não é admin — e esse é um fato sobre a própria conta dele, que ele já conhece. O `404` de handle desconhecido sobrevive ao fix, mas só depois da guarda, então só um admin consegue chegar a ele — e saber quais contas existem é, legitimamente, assunto de admin.

**Regra de bolso — um critério só, o da série: a existência do alvo é sensível?** Sim → **`404`**, que torna "não autorizado" indistinguível de "não existe": o pedido no `bola-sequential-id` e no `bola-nested-resource`, onde um espaço de ids enumerável transformaria um `403` em oráculo. Não → um **`403`** honesto: a loja no `bola-nested-resource`, e a função admin aqui, onde o que falta ao caller é uma role, não o conhecimento de um segredo. O `bola-uuid-leaked` não contradiz a regra — com UUIDs a pressão de oráculo quase sumiu, e o `404` ficou como o default conservador herdado. O RFC 9110 oferece os dois; quem escolhe é a natureza do alvo, não o átomo.

## Isto é BFLA — autenticado, nunca autorizado pra função

Nada que o caller manda é parseado ou executado. Um request legítimo, sob um token legítimo, invoca uma função acima do nível de privilégio do caller. Isso é Broken Function Level Authorization — **API5:2023** no OWASP API Security Top 10 — e o impacto é vertical privilege escalation: um membro comum exercendo a capacidade de um administrador, onde os átomos de API1 mostraram o tipo horizontal. Mesma raiz do BOLA, eixo diferente: lá, o handler sabia quem você era e nunca checava o pedido contra o dono dele ou contra a loja autorizada dele; aqui, ele sabe quem você é e nunca checa o que você pode fazer. O token opaco e cripto-forte sai intocado tanto do ataque quanto do fix — o `authenticate()` e o `401` dele são os mesmos bytes nos dois gêmeos, porque o bug nunca esteve ali. E, como nos átomos de API1, o bug mora no `app.ts` e não dá `grep`: não há string perigosa pra achar. Você o pega lendo cada operação privilegiada e perguntando *onde este endpoint confere que o caller pode invocar esta função?* — e reparando, aqui, que um check de autenticação funcionando estava ocupando o lugar de um check de autorização que ninguém escreveu.
