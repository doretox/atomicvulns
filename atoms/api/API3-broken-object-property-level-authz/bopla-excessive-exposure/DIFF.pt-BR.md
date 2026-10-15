# DIFF — vulnerable vs. fixed

O `vulnerable/app.ts` e o `fixed/app.ts` diferem em exatamente um lugar — a linha que serializa a resposta no `GET /users/:handle`, mais o comentário acima dela. O `POST /login`, os helpers de autenticação, a guarda de posse, o seed `USERS`, o mapa `TOKENS`, os imports, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). O resto do handler também é: o `401`, o `403`, a busca e o `404` dela são os mesmos bytes nos dois builds. A mudança é uma projeção de resposta.

## O fix — uma allow-list, não o objeto guardado

```diff
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);
-  // VULNERABLE: the ownership check above is right -- this IS your record. But the response
-  // spreads the WHOLE stored object, so every server-side field rides along with the public
-  // one. Authorization applies to each property returned, not only to the object.
-  res.json({ handle: req.params.handle, ...user });
+  // FIXED: the response names the fields the caller may see -- an allow-list, not the stored
+  // object. A field added to User later stays server-side until someone deliberately exposes it.
+  res.json({ handle: req.params.handle, displayName: user.displayName });
```

A linha vulnerable espalha o registro inteiro (`...user`), então `displayName`, `passwordHash` e `is_admin` saem todos. A linha fixed nomeia um campo — `displayName` — então nada mais pode sair, qualquer que seja o que o registro guarde.

**Leia o fix pelo que ele autoriza.** O handler já autorizava o **objeto**: a guarda de posse uma linha acima (`if (req.params.handle !== caller) return res.sendStatus(403)`) garante que este registro é o do próprio caller. O que ele nunca fez foi autorizar as **propriedades** desse objeto. O fix estende a autorização até o grão do campo: ele decide, explicitamente, quais propriedades a resposta pode carregar. É essa a face de leitura inteira de BOPLA — a autorização é devida não só ao objeto, mas a cada campo devolvido dele.

> **`...user` serializa o objeto que o store guarda; a allow-list serializa o objeto que o chamador tem liberação de ler — BOPLA é a distância entre os dois.**

## Allow-list, não deny-list — falha fechado, não falha aberto

Uma allow-list não é a única projeção que remove os dois campos. Uma deny-list também funcionaria *hoje*:

```ts
// CONSIDERED AND REJECTED -- a deny-list (blacklist): strip the known-bad fields.
const { passwordHash, is_admin, ...safe } = user;
res.json({ handle: req.params.handle, ...safe });
```

Ela remove `passwordHash` e `is_admin`, e a resposta sai limpa. Mas ela **falha aberto**: no dia em que alguém adicionar um campo server-side novo ao `User` — um `internalNote`, um `resetToken` —, esse campo vaza sozinho, porque ninguém lembrou de acrescentá-lo à deny-list. A allow-list **falha fechado**: um campo novo fica server-side até alguém deliberadamente nomeá-lo na resposta.

A diferença não é estética — é a direção em que um erro corre. Adicione um campo e esqueça de mexer na resposta:

| Projeção | hoje (3 campos) | amanhã (+ um `internalNote` novo) |
|---|---|---|
| **spread** (`...user`) — o build vulnerable | vaza `passwordHash` + `is_admin` | **também vaza** `internalNote` |
| **deny-list** (`const {passwordHash, is_admin, ...safe} = user`) | limpo | **vaza** `internalNote` (falha aberto) |
| **allow-list** (`{ displayName }`) — o fix | limpo | **continua limpo** (falha fechado) |

Em escala essa projeção vira um **serializer** ou **DTO** (Data Transfer Object) compartilhado — um lugar só que define o shape público de cada entidade — em vez de um objeto literal embutido no handler. É a mesma ideia um grão maior; este átomo a mantém numa linha pra o diff ficar na lição.

## A resposta é o objeto guardado, até deixar de ser

O `res.json({ handle: req.params.handle, ...user })` se lê como "devolva o registro", e é exatamente essa a armadilha: ele devolve *tudo o que o registro por acaso guarda*, não o que o caller tem liberação de ler. Os dois só eram o mesmo objeto porque ninguém decidiu o contrário. O `handle` é o parâmetro de path ecoado de volta (a chave do `Map`, não um campo do `User`), e o `...user` despeja o que o `User` carrega — aqui três campos, dois deles internos. O handler fixed quebra esse acaso: a resposta agora é montada a partir de uma lista deliberada, e um campo chega ao cliente só se a lista o nomear.

*(Sobre os tipos: o `USERS.get(req.params.handle)` é `User | undefined` pela própria assinatura do `Map.get`, então a guarda `if (!user)` fica byte-idêntica nos dois gêmeos. Ela só é **forçada pelo tipo** no build fixed, onde o `user.displayName` desreferencia `user`; no build vulnerable, espalhar `User | undefined` é um no-op que o TypeScript aceita, então a guarda é higiene ali, não exigência do compilador. De todo jeito ela é inalcançável em runtime: a guarda de posse acima dela só deixa passar o handle do próprio caller, sempre seedado. Nenhum `?.` aparece em lugar nenhum — a guarda de posse é uma comparação de string.)*

## Status codes — herdados, não re-argumentados

Nada nos status codes é novo aqui, então este átomo toma o argumento emprestado em vez de repeti-lo:

- **Uma leitura alheia → `403`.** O `GET /users/alice` com o token do `clancy` é recusado pela guarda de posse, que compara o handle do path com o caller **antes de qualquer busca** — então não revela existência e não é oráculo de enumeração. É a mesma guarda, e o mesmo raciocínio, do `bfla-method-based`; o [`DIFF.pt-BR.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.pt-BR.md) dele carrega o relato completo — RFC 9110 §15.5.4 e o critério único da série pra `403` vs `404`.
- **Token ausente ou inválido → `401`** com um challenge `WWW-Authenticate: Bearer` (RFC 9110 §15.5.2); o `403` não traz nenhum, porque o caller já está autenticado. Também herdado; veja o mesmo [`DIFF.pt-BR.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.pt-BR.md) do `bfla-method-based`.

O único `404` no handler (`if (!user)`) é inalterado nos dois gêmeos e inalcançável em runtime, porque a guarda de posse só admite o handle seedado do próprio caller. Este átomo tem menos status codes alcançáveis que o `bfla-method-based` — não há escrita, não há `PATCH`, e não há caminho que alcance um registro alheio depois da guarda.

## Isto é BOPLA — autorização numa propriedade, não só num objeto

Nada que o caller manda é parseado ou executado. Um request legítimo, sob um token legítimo, lê o registro do **próprio** caller — corretamente autorizado no nível do objeto — e a resposta entrega de volta campos que o caller não pode ver. Isso é Broken Object Property Level Authorization — **API3:2023** no OWASP API Security Top 10 — na sua face de leitura, *excessive data exposure*. Ler como BOLA te aponta pro lugar errado: o check de posse object-level está presente e *correto* (o `GET /users/alice` dá `403`), e a falha não é ele estar errado, mas a autorização nunca ter descido até os campos que a resposta serializa. O impacto é **information disclosure** — recon de schema interno (um `is_admin` nomeado, um `passwordHash` nomeado) e um artefato de credencial exposto (um password hash que, num sistema real, habilita offline cracking), não privilege escalation (o `is_admin` volta `false`, e nada o escreve) e não cracking aqui (o login é passwordless e o hash é dummy). Como no resto da série, o bug mora no `app.ts` e não dá `grep`: não há string perigosa pra achar. Você o pega lendo o que cada handler devolve e perguntando, de cada campo, *este é um que o caller tem permissão de ver?* — e reparando, aqui, que um ownership check correto foi silenciosamente confundido com a autorização inteira.
