# DIFF — vulnerable vs. fixed

O `vulnerable/app.ts` e o `fixed/app.ts` diferem em exatamente um lugar — a linha que grava o registro no `PATCH /users/:handle`, mais o comentário acima dela. O `POST /login`, os helpers de autenticação, a guarda de posse, o seed `USERS`, o mapa `TOKENS`, os imports, o `204` que encerra o handler, a rota `GET /admin/users` inteira, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). A mudança é uma projeção de escrita.

## O fix — uma allow-list na escrita, não o corpo da requisição

```diff
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);
-  // VULNERABLE: the ownership check above is right -- this IS your record. But the write
-  // merges the WHOLE request body into the record, so every property the body names is set,
-  // is_admin included. Authorization applies to each property written, not only to the object.
-  USERS.set(req.params.handle, { ...user, ...req.body });
+  // FIXED: the write names the one field the caller may set -- an allow-list, not the request
+  // body. is_admin is not in the list, so a body that carries it changes nothing; a field added
+  // to User later stays caller-unwritable until someone deliberately names it here.
+  USERS.set(req.params.handle, { ...user, displayName: typeof req.body?.displayName === "string" ? req.body.displayName : user.displayName });
   res.sendStatus(204);                                           // no content: nothing to echo back
```

Os dois gêmeos chamam o mesmo `USERS.set` sobre o mesmo registro-base (`...user`). O que difere é **quem decide o resto do objeto**. Na linha vulnerable, o `...req.body` deixa a requisição decidir: toda propriedade que o corpo nomeia é gravada, então `{"is_admin":true}` entra com a mesma certeza de `{"displayName":"..."}`. Na linha fixed quem decide é o handler: um campo é nomeado, e nada mais chega ao registro, qualquer que seja o que o corpo carregue.

**Leia o fix pelo que ele autoriza.** O handler já autorizava o **objeto**: a guarda de posse uma linha acima (`if (req.params.handle !== caller) return res.sendStatus(403)`) garante que este registro é o do próprio caller. O que ele nunca fez foi autorizar as **propriedades** que o write seta. O fix estende a autorização até o grão do campo no lado da escrita: ele decide, explicitamente, quais propriedades uma requisição pode mudar. É essa a face de escrita inteira de BOPLA — a autorização é devida não só ao objeto, mas a cada campo gravado nele.

> **O handler vulnerável pergunta à requisição quais propriedades escrever; o corrigido já sabe — e `is_admin` nunca esteve entre elas.**

Uma nota sobre o teste `typeof` nessa linha: o `req.body` é `any`, então sem ele um corpo como `{"displayName": {"x": 1}}` guardaria um não-string num campo tipado `string` — uma mentira sobre a forma do registro que o TypeScript não tem como pegar numa fronteira JSON. Nomear o campo **e** aceitar só o tipo dele é o mínimo honesto de "só isto pode entrar"; faz parte de nomear o campo, não é uma lição separada sobre input validation.

## Allow-list, não deny-list — falha fechado, não falha aberto

Uma allow-list não é a única projeção de escrita que barra o ataque de hoje. Uma deny-list também funcionaria *hoje*:

```ts
// CONSIDERED AND REJECTED -- a deny-list on the write: strip the known-bad field from the body.
const { is_admin, ...rest } = req.body ?? {};
USERS.set(req.params.handle, { ...user, ...rest });
```

Ela remove o `is_admin` do corpo, e a escalação do walkthrough não acontece. Mas ela **falha aberto**: no dia em que alguém acrescentar um segundo campo privilegiado ao `User` — um `is_staff`, um `plan`, um `creditBalance` —, esse campo vira gravável sozinho, porque ninguém lembrou de acrescentá-lo à deny-list. A allow-list **falha fechado**: um campo novo fica não-gravável pelo caller até alguém deliberadamente nomeá-lo no write.

A diferença não é estética — é a direção em que o erro corre. Acrescente um campo privilegiado e esqueça de mexer no handler:

| Projeção da escrita | hoje (`{"is_admin":true}`) | amanhã (`{"is_staff":true}`) |
|---|---|---|
| **spread** (`...req.body`) — o build vulnerable | grava `is_admin` | **grava também** `is_staff` |
| **deny-list** (`const {is_admin, ...rest} = req.body`) | bloqueia `is_admin` | **grava** `is_staff` (falha aberto) |
| **allow-list** (`displayName` nomeado) — o fix | bloqueia | **continua bloqueando** (falha fechado) |

Em escala, essa projeção vira um **schema de entrada** — um DTO (Data Transfer Object) de update, um validador declarativo — definindo num lugar só quais campos cada role pode escrever, em vez de um objeto literal embutido no handler. É a mesma ideia um grão maior; este átomo a mantém na linha única pra o diff ficar na lição.

## O write tem a forma da requisição, até deixar de ter

`USERS.set(req.params.handle, { ...user, ...req.body })` se lê como "atualize o registro com o que o cliente mandou", e é exatamente essa a armadilha: ele grava *tudo o que o cliente por acaso mandou*, não o que o caller tem liberação de mudar. Os dois só eram o mesmo objeto porque ninguém decidiu o contrário. O `...user` traz o registro guardado como base, e o `...req.body` despeja a requisição por cima — o último a escrever ganha, e a requisição é sempre a última. O handler corrigido desfaz esse acidente: o registro novo é montado a partir de uma lista deliberada, e uma propriedade chega ao store só se a lista a nomear.

Um comportamento que vale registrar, porque é a pergunta que um leitor atento faz de qualquer merge de objeto em Node: um corpo `{"__proto__":{"polluted":1}}` **não** polui o `Object.prototype` aqui — tanto o `JSON.parse` quanto o object spread criam a chave como own property, então ela cai como um campo inerte do registro e o protótipo global fica intocado (verificado contra o container rodando: `({}).polluted` continua `undefined`, `Object.keys({})` continua vazio, e a rota admin segue respondendo `403`).

*(Sobre os tipos: o `USERS.get(req.params.handle)` é `User | undefined` pela assinatura do próprio `Map.get`, então a guarda `if (!user)` é mantida byte-idêntica nos dois gêmeos. Ela só é **exigida pelo tipo** no build fixed, onde o `user.displayName` desreferencia o `user` dentro do ternário; no vulnerable, o `any` que o `req.body` carrega lava o tipo do objeto literal inteiro, e o compilador aceita o write mesmo sem a guarda — a mesma frouxidão que torna o bug possível também silencia a checagem sobre ele. De todo jeito a guarda é inalcançável em runtime: a guarda de posse acima dela só deixa passar o handle do próprio caller, sempre seedado.)*

## A rota admin é idêntica nos dois builds — e é esse o ponto

O `GET /admin/users` não aparece neste diff. São os mesmos bytes no `vulnerable/` e no `fixed/`:

```ts
app.get("/admin/users", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
  res.json([...USERS.keys()]);   // handles only -- no record fields in the body
});
```

Essa guarda está **correta**, e vale ser preciso sobre por quê, porque a rota é onde o exploit fica visível e seria fácil culpá-la. O predicado faz uma pergunta — *o caller é administrador?* — e a responde a partir do `USERS`, o store, não do token. No build vulnerable ele recusa o `clancy` com `403` antes do write e o admite com `200` depois dele; no fixed recusa nas duas vezes. A rota nunca mudou de opinião sobre nada: o store é que mudou por baixo dela.

Essa linha é, byte a byte, o check de role que o `bfla-admin-function` acrescenta como *fix* — o átomo cuja lição inteira é uma função privilegiada sem check de role nenhum. Aqui a função tem um, ele funciona, e o caller entra mesmo assim, porque escreveu a role que o check consulta. **A guarda que você vê está certa; o breach está a montante, no `PATCH`.** Os dois bugs dividem uma porta e nada mais: BFLA é uma função que não pergunta; isto é uma função que pergunta e recebe de volta uma role forjada. Procurar a falha neste handler não vai achar nada, e isso é de propósito.

Duas escolhas menores nessa rota, as duas deliberadas: ela é **read-only**, pra poder servir de instrumento sem alterar o que mede; e serializa **só handles** — nunca um campo de registro —, pra que provar a escalação nunca dependa de a resposta vazar coisa alguma.

## Status codes — o 204 é argumento novo; o 403 e o 401 são herdados

**O write responde `204 No Content` — nos dois gêmeos — e isso é decisão de desenho, não atalho.** A RFC 9110 (HTTP Semantics) §15.3.5 define o `204` como o servidor tendo cumprido a requisição com sucesso sem conteúdo adicional a enviar, e é explícita: "a 204 response is terminated by the end of the header section; it cannot contain content". É o único status de sucesso que **não pode** ecoar. É precisamente por isso que este átomo o usa: um corpo de resposta num write é o input do próprio atacante voltando, e confundi-lo com prova é a leitura errada mais cara desta classe. Com o `204`, os dois builds respondem de forma idêntica e nenhum conta o que guardou, então o único jeito de descobrir o efeito é ler o estado por outra rota.

Isso diverge, de propósito, do `bfla-method-based`, cujo `PATCH` responde `200` com corpo JSON — e cujo [`DIFF.pt-BR.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.pt-BR.md) deixa claro que o corpo é o input ecoado do caller e não prova nada sobre o registro guardado. Este átomo pega essa conclusão e a coloca na linha de status: se o eco não pode provar, que não haja eco.

O resto é herdado e não é re-argumentado aqui:

- **Um write alheio → `403`.** O `PATCH /users/alice` com o token do `clancy` é recusado pela guarda de posse, que compara o handle do path com o caller **antes de qualquer busca** — então não revela existência nenhuma e não é oráculo de enumeração. Mesma guarda, mesmo raciocínio do `bfla-method-based`; o [`DIFF.pt-BR.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.pt-BR.md) dele carrega o relato completo, a RFC 9110 §15.5.4 e o critério único da série para `403` vs `404`.
- **Token ausente ou inválido → `401`** com um challenge `WWW-Authenticate: Bearer` (RFC 9110 §15.5.2); o `403` não carrega challenge, porque o caller já está autenticado. Também herdado; veja o mesmo [`DIFF.pt-BR.md`](../../API5-broken-function-level-authz/bfla-method-based/DIFF.pt-BR.md).
- **O `403` de não-admin do `GET /admin/users`** é a mesma recusa honesta: credencial presente, considerada insuficiente para esta função, cuja existência é premissa e não segredo.

O único `404` do `PATCH` (`if (!user)`) é inalterado nos dois gêmeos e inalcançável em runtime, porque a guarda de posse só admite o handle do próprio caller, sempre seedado — o `PATCH /users/nobody` responde `403`, não `404`.

## Isto é BOPLA — autorização numa propriedade que você escreve

Nada do que o caller manda é parseado ou executado. Um request legítimo, sob um token legítimo, atualiza o **próprio** registro do caller — corretamente autorizado no nível do objeto — e o write aceita uma propriedade que o caller nunca teve permissão de controlar. Isso é Broken Object Property Level Authorization — o **API3:2023** do OWASP API Security Top 10 — na sua face de escrita, *mass assignment*. Ler como BOLA aponta pro lugar errado (o ownership check está presente e correto — o `PATCH /users/alice` é `403`); ler como BFLA aponta pro handler errado (o check de role da rota admin está presente e correto — ele recusou o mesmo caller minutos antes). A falha é que a autorização nunca desceu até os campos que o write seta. O impacto é **escalação de privilégio**, verificada e não presumida: nenhum administrador existe no seed, e o bug cria um. Como no resto da série, o bug mora no `app.ts` e não dá `grep`: não há string perigosa pra achar. Você o pega lendo o que cada handler grava e perguntando, de cada propriedade, *esta é uma que o caller tem permissão de setar?* — e reparando, aqui, que um ownership check correto foi silenciosamente confundido com a autorização inteira.
