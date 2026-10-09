# DIFF — vulnerable vs. fixed

`vulnerable/app.ts` e `fixed/app.ts` diferem em exatamente um lugar — a guarda que segue a busca do pedido no `GET /orders/:id`. `POST /login`, `GET /orders`, os helpers, os imports, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). A mudança é um object-level authorization check.

## O fix — existência e posse viram uma guarda só

```diff
 app.get("/orders/:id", (req, res) => {
   const caller = authenticate(req);
   if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
   const order = ORDERS[req.params.id];                      // string key (UUID) -- no Number() coercion
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

## Os dois fixes, lado a lado — a correção é id-agnóstica

A razão inteira de este átomo existir é uma prova por identidade com o `bola-sequential-id`: mesmo seed, mesma superfície, mesmo fix, mudando só o tipo do identificador (um inteiro sequencial lá, um UUID aleatório aqui). Ponha as duas guardas fixed lado a lado e a linha acrescentada são os mesmos bytes:

```
# bola-sequential-id  (fixed/app.ts)                 # bola-uuid-leaked  (fixed/app.ts)
  const order = ORDERS[Number(req.params.id)];          const order = ORDERS[req.params.id];
  if (!order || order.owner !== caller) ... 404;        if (!order || order.owner !== caller) ... 404;
```

A única linha que difere é a *busca* acima da guarda — `Number(req.params.id)` vira `req.params.id`, porque uma chave UUID não precisa de coerção numérica — e essa linha é idêntica entre o `vulnerable/` e o `fixed/` *deste próprio átomo*, logo não faz parte do fix. O fix em si — o predicado de posse, a saída `sendStatus(404)` compartilhada, comentário e tudo — é copiado do `bola-sequential-id` sem mudar um caractere.

É esse o ponto, e vale dizer sem rodeio: **mudou o tipo do id, mudou a descoberta, mudou o walkthrough inteiro; a correção não mudou nada.** Se o formato do id fosse a causa do bug, o fix teria que mudar junto. Não mudou — o ownership check não sabe nem se importa se o id é `1007` ou `edec4558-…`.

## Uma guarda, uma saída — a indistinguibilidade é estrutural

Existência e posse passam por uma única condição — `!order || order.owner !== caller` — compartilhando **um** `return res.sendStatus(404)`. "Não existe" e "existe mas não é seu" batem na mesma linha, retornam o mesmo status e emitem o mesmo corpo — não porque alguém lembrou de fazer as duas respostas casarem, mas **por construção**: só há um caminho de recusa, então só há uma coisa que ele pode dizer. O [`DIFF.pt-BR.md`](../bola-sequential-id/DIFF.pt-BR.md) do `bola-sequential-id` trabalha por completo por que uma-guarda-uma-saída importa; este átomo herda essa estrutura verbatim em vez de re-derivá-la.

## 404, não 403

O handler fixed retorna **`404`** pra um pedido que o caller não possui, byte a byte idêntico ao `404` de um id nunca seedado — você confirma isso contra a API fixed, onde um pedido real que não é seu e um UUID inventado voltam com o mesmo status, corpo e tamanho. O argumento completo de escolher `404` em vez de `403` — o precedente do repositório privado do GitHub, o RFC 9110, e quando `403` é a escolha legítima — mora no [`DIFF.pt-BR.md`](../bola-sequential-id/DIFF.pt-BR.md) do `bola-sequential-id`; aqui ele é herdado por referência, não reaberto.

Uma nuance honesta, e ela corta *a favor* da tese. No `bola-sequential-id` o `404` fazia dupla função: com ids inteiros contíguos, um `403` seria um oráculo de enumeração (varra os números, e o par `403`-vs-`404` mapeia quais ids existem). Com UUIDs aleatórios essa pressão quase some — não há espaço pra varrer. Ainda assim o build fixed mantém `404` inalterado, porque o fix foi copiado por inteiro e `404` é o default conservador que nunca está errado. A remediação não se curvou ao formato do id — o que é, mais uma vez, a lição inteira.

## O que o fix *não* faz — o id continua um UUID

Repare o que o diff não toca: o id. Ele **não** troca o UUID por nada, não o remodela, não acrescenta uma segunda camada de obscuridade. Duas coisas estão em jogo e só uma é o bug. O **formato do id** governa a *descoberta* — quão caro é obter um id válido. O **check ausente** governa o *acesso* — se um não-dono que tem um id consegue lê-lo. Um id mais forte só encarece a descoberta; nunca restaura o check. Então remodelar o id conserta o eixo errado: o atacante que já tem um (um vazamento, um link compartilhado, uma linha de log) passa reto por ele, e você fica com o mesmo BOLA atrás de um identificador mais comprido.

O átomo web `idor-uuid-guessable` faz a metade complementar deste ponto pela direção oposta: os ids dele são **UUIDv1**, que carregam um timestamp e o MAC do host e podem ser reconstruídos a partir de metadado que a app publica — prova de que "não-adivinhável" nunca foi automaticamente verdade pra um UUID. Este átomo segura o id genuinamente fora de alcance (um **UUIDv4**, entregue de fora) e mostra que a falha sobrevive de qualquer forma. Adivinhável ou não, o formato do identificador não é o controle de acesso. A regra transferível que os átomos web `idor-numeric-id` e `bola-rest` ensinam vale aqui inalterada: **corrija o check ausente, não remodele o identificador.**

## O seed espelhado é deliberado — e não é um corpus de enumeração

Os doze pedidos, quatro usuários, split desigual 6/3/2/1, e cada nome, endereço, item e valor são copiados do `bola-sequential-id` objeto a objeto; só o tipo do id mudou. Isso é deliberado, não preguiça. A tese é um experimento controlado, e um experimento controlado muda **uma** variável: se o seed também diferisse, duas coisas teriam se movido (o id *e* os dados) e a comparação não provaria nada. Manter os dados fixos e variar só o identificador é o que isola o formato do id como a coisa em teste.

Uma consequência a dizer com todas as letras, pra o espelho não ser mal lido: os doze pedidos estão aqui **por espelhamento, não porque um corpus maior ajude um atacante**. Com UUIDs o tamanho do corpus é irrelevante — o espaço de busca é o mesmo quer o store tenha dois objetos ou dois milhões, porque você não consegue varrer ~2¹²² de aleatoriedade. No `bola-sequential-id`, doze ids contíguos eram um alvo de enumeração; aqui, doze UUIDs são doze agulhas num palheiro astronomicamente grande. Mais pedidos não os tornariam mais fáceis de achar.

## O endpoint de listagem já escopa — a assimetria é o BOLA

O `GET /orders` é *idêntico* nas duas versões, e nas duas ele filtra certo: `Object.values(ORDERS).filter((o) => o.owner === caller)`. O desenvolvedor sabia escopar uma resposta pro dono dela — fez na coleção. Só não fez no endpoint de objeto único. Essa assimetria — **lista escopada, item não** — é exatamente como o BOLA aparece em codebases reais, e é por isso que a lista continuar correta na versão fixed não é um segundo fix: ela nunca esteve quebrada. É também por isso que a lista do `GET /orders` pode devolver com segurança o id do próprio caller: te mostrar o *seu* UUID não vaza nada sobre o de mais ninguém, então o store nunca dá ao atacante um ponto de apoio. O único bug morava no `GET /orders/:id`, e a guarda de um predicado é o reparo inteiro.

## O token é opaco, e o ataque nunca o toca

O Bearer token é uma string opaca aleatória (`randomBytes(24).toString("base64url")`) resolvida server-side pelo mapa `TOKENS` — um substituto pra um OAuth2 opaque access token ou uma session id, não um JWT. Nada no ataque inspeciona, decodifica, adultera ou forja ele; o `clancy` faz login como ele mesmo e manda o próprio token, inalterado, o tempo todo. Mantenha os dois eixos separados: o valor que virou UUID é o **id do pedido**, não o token. Um token fraco ou forjável seria uma *segunda* vulnerabilidade (broken authentication); mantê-lo cripto-forte prende este átomo a exatamente um bug. O token não é a vulnerabilidade; o endpoint é.

## Isto é BOLA — IDOR numa API, e mora no app.ts

Nada que o caller manda é parseado ou executado; um id legítimo simplesmente alcança um objeto fora do escopo do caller. Isso é Broken Object Level Authorization — **API1:2023**, o risco #1 do OWASP API Security Top 10 — e é o IDOR vestido de API, a mesma forma dos átomos web `idor-numeric-id` e `bola-rest` e a mesma classe do átomo de API `bola-sequential-id`: forneça um id, e o servidor te entrega um objeto que ele nunca checou ser seu. Como em todos eles, o bug mora no `app.ts`, não em algum template (não há nenhum), e não dá `grep`: não há string perigosa pra achar. Você o pega lendo cada endpoint que retorna um objeto escopado a usuário e perguntando "onde isto confere que o caller é dono?" — e reparando, aqui, que uma chamada `authenticate()` funcionando foi silenciosamente confundida com esse check.
