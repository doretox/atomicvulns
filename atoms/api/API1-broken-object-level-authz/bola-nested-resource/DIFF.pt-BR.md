# DIFF — vulnerable vs. fixed

O `vulnerable/app.ts` e o `fixed/app.ts` diferem em exatamente um lugar — a linha que busca o pedido no `GET /stores/:storeId/orders/:orderId`, mais o comentário acima dela. O `POST /login`, o `GET /stores/:storeId/orders`, a tabela `STORES`, o `operates()`, o `ordersOf()`, o seed, os imports, o rodapé do `listen`, o `Dockerfile`, o `package.json`, o `package-lock.json` e o `tsconfig.json` são byte-idênticos entre as duas versões (e não há templates — este átomo é só API). As três guards do handler também são: o `401`, o `403` e o check de existência que retorna `404` são os mesmos bytes nos dois builds. O fix não edita uma guard sequer — ele muda o que chega na última.

## O fix — a busca do pedido entra no escopo do pai

```diff
   if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
-  // VULNERABLE: the lookup is GLOBAL. The caller operates :storeId, but order.storeId is
-  // never compared to it -- an order from ANY store comes back.
-  const order = ORDERS[Number(req.params.orderId)];
+  // FIXED: the order is looked up INSIDE the authorized store, not in the global collection --
+  // an order from another store is simply not found, the same 404 as an id that never existed.
+  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));
   if (!order) return res.sendStatus(404);
   res.json(order);
```

A linha vulnerable pede um id à coleção da plataforma inteira. A linha fixed pede um id *aos pedidos desta loja*. Em SQL o mesmo movimento é o `SELECT … WHERE id = ?` virar `SELECT … WHERE store_id = ? AND id = ?`: o filho é buscado **através** do pai, e o pai é justamente aquele que o request já autorizou.

**Não faltava informação — faltava a pergunta.** Todo pedido carrega o próprio `storeId`, e o build vulnerable até o serializava na resposta, então dava pra ver `"storeId":"meadow"` voltar de um path que dizia `harbor`. O dado necessário pra autorizar corretamente esteve dentro do objeto o tempo todo. O que o fix acrescenta não é um campo, não é um join, não é um conceito novo — é o ato de *perguntar*.

E ele pergunta com maquinário que já estava no arquivo. O predicado que faz o trabalho é `o.storeId === storeId`, e ele mora no `ordersOf()`:

```ts
function ordersOf(storeId: string): Order[] {
  return Object.values(ORDERS).filter((o) => o.storeId === storeId);   // the store's scope
}
```

Esse helper está presente no gêmeo **vulnerable** também, inalterado, e a rota de listagem logo acima já o chamava. Então o fix não inventa nada e não autoriza nada por mágica: o predicado de escopo de loja que a aplicação já tinha é finalmente aplicado na única rota que estava pulando ele.

## Não encontrado, em vez de encontrado e recusado

A consequência que vale nomear com precisão: no build fixed, o pedido de outra loja **nunca chega a se materializar**. O `find()` percorre o escopo da loja autorizada, não vê o id e devolve `undefined`. Não existe ponto nenhum do handler em que um pedido da `meadow` esteja numa variável chamada `order` enquanto o código decide o que fazer com ele.

Compare com os dois átomos companheiros. No `bola-sequential-id` e no `bola-uuid-leaked`, o `fixed/app.ts` busca o objeto na coleção global exatamente como o gêmeo vulnerable dele faz, fica com o pedido do outro usuário na mão, e *aí* o recusa na guard — `if (!order || order.owner !== caller) return res.sendStatus(404);`. Busca, depois rejeita. Aqui a ordem se inverte: escopo primeiro, e assim não sobra nada pra rejeitar.

As duas formas fecham o buraco, e a diferença importa por uma razão que vai além de gosto. Buscar-e-rejeitar joga todo o peso numa guard que um refactor futuro pode enfraquecer e um caminho de código novo pode esquecer; uma busca escopada torna o objeto errado inalcançável a partir daquele caminho de código, ponto. Sempre que a camada de dados conseguir expressar o pai — uma cláusula `WHERE`, uma relação, um handle de repositório já vinculado ao tenant —, empurrar o pai pra dentro da query é a mais durável das duas.

## A guard de existência não saiu do lugar

O `if (!order) return res.sendStatus(404);` e o `res.json(order);` são os mesmos bytes nos dois gêmeos, e isso vale uma pausa. Os dois átomos anteriores chegaram à indistinguibilidade *editando a guard* — fundindo existência e posse numa condição só, com uma saída só. Aqui a indistinguibilidade cai da busca: "não é desta loja" e "não existe em lugar nenhum" chegam à guard as duas como o mesmo `undefined`, então elas não têm como produzir respostas diferentes nem em princípio. Mesmo estado final, alcançado pelo outro lado.

## Por que este não é o fix dos átomos anteriores — e é esse o ponto

O `bola-sequential-id` corrigiu o handler dele **acrescentando um predicado à guard depois da busca**. O `bola-uuid-leaked` então copiou esse fix caractere por caractere e fez dessa identidade a tese inteira dele: mudou o tipo do id, mudou a descoberta, mudou o walkthrough, e a correção não mudou.

Este átomo quebra essa sequência de propósito. O bug dele tem outra forma — um check *presente e apontado pro pai*, em vez de um check ausente — então o reparo tem outra forma também: **mover a busca pra dentro do escopo do pai** em vez de acrescentar um segundo predicado depois dela. Três átomos seguidos com o mesmo patch seriam sinal de que o terceiro não precisava existir. A lição transferível não é "o fix é sempre um predicado numa guard". É: **autorize o objeto que você está prestes a devolver.**

Repare também no que o fix deixa em paz: o check do pai. O `operates(caller, req.params.storeId)` estava correto e continua necessário — apague ele e qualquer operador conseguiria ler os pedidos de qualquer loja pelo path da própria loja, o que é um buraco diferente e maior. O fix **acrescenta a pergunta que faltava**; ele não substitui a que já estava lá.

## Três status codes, um critério

O handler corrigido responde a três recusas diferentes com dois codes diferentes, e lido fora de contexto isso parece incoerência. Não é. Há um critério só, aplicado a dois tipos diferentes de objeto.

**O critério: a existência do alvo é, em si, sensível?** O RFC 9110 (HTTP Semantics) expõe as duas opções e deixa a escolha pro servidor. A §15.5.4 define a recusa honesta: *"The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it,"* e acrescenta que *"an origin server that wishes to 'hide' the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found)."* A §15.5.5 define o outro lado: `404` quer dizer que o servidor de origem *"did not find a current representation for the target resource or is not willing to disclose that one exists."* Recusar abertamente, ou esconder a existência — o padrão oferece os dois e pergunta de qual deles o recurso precisa.

Agora os três casos, lado a lado:

- **Uma loja que você não opera → `403`.** `GET /stores/meadow/orders/1009` com o token da dana. A existência de uma loja não é segredo: a `meadow` é uma loja, o slug dela é um nome público, e o README do átomo lista as três. Escondê-la não protegeria nada, então a resposta honesta é a certa — a loja está lá e você não a opera.
- **Uma loja que não existe → `403` também.** O `GET /stores/lagoon/orders/1009` devolve o mesmo `Forbidden`, porque o `operates()` pergunta sobre um **vínculo**, não sobre existência: "você opera esta loja?" E "não" é igualmente verdade pra uma loja que existe sem você e pra uma loja que não está lá. Como a existência de loja não é sensível, uma resposta só pras duas não custa nada e mantém o check numa linha só. Isto é o critério sendo aplicado, não uma concessão à conveniência: não há nada aqui que precise ser escondido.
- **Um pedido de outra loja → `404`.** `GET /stores/harbor/orders/1009` no build fixed. Aqui o mesmo critério sai pro outro lado, porque a existência de um *pedido* **é** sensível. Os ids são um contador global único, então um `403` pra "existe em outra loja" contra um `404` pra "não existe em lugar nenhum" entregaria ao caller um **enumeration oracle** — uma diferença nas respostas que mapeia quais objetos existem sem ler nenhum deles. Varra `1001`, `1002`, `1003`… pelo path da sua própria loja e essa divisão te desenha o volume de pedidos das outras lojas, a cadência e o crescimento. Um `404` uniforme fecha o oracle, e preserva a indistinguibilidade que os dois átomos companheiros estabeleceram: não-é-desta-loja e nunca-existiu voltam byte-idênticos, `Not Found` de um jeito ou de outro.

A mesma pergunta — *a existência é sensível?* — portanto dá `403` pro pai e `404` pro filho, porque uma loja e um pedido não são o mesmo tipo de segredo. Nenhum dos dois codes é o "certo" com o outro como concessão: o status code é uma propriedade do objeto que está sendo protegido, não um hábito do handler.

Dois detalhes seguram o argumento. **O check do pai roda antes da busca**, então um caller que não opera a loja leva `403` sem que pedido nenhum seja consultado — o `403` portanto não vaza absolutamente nada sobre pedidos, e o oracle só poderia ter existido *dentro* de uma loja que o caller opera legitimamente, que é exatamente onde o `404` o fecha. E o `404` é genuinamente uniforme: no build fixed, o `1009` (de outra loja), o `1001` (de uma terceira loja) e o `1013` (nunca seedado) voltam todos `404` com o mesmo `Not Found` de nove bytes.

O [`DIFF.pt-BR.md`](../bola-sequential-id/DIFF.pt-BR.md) do `bola-sequential-id` carrega o resto deste argumento — o precedente do repositório privado do GitHub e a regra de bolso pra escolher entre os dois codes — e ele é herdado aqui por referência, não recontado.

## O que cresceu, e por quê

Este átomo é maior que os dois antecessores, e cada linha a mais é a entidade nova: o `STORES` (as lojas e os vínculos operador-loja), o `operates()` pra perguntar sobre eles, o `ordersOf()` pra escopar por eles, e o `storeId` no pedido onde antes ficava o `owner`. Esse é o preço da variante, não decoração. Sem um pai de verdade não há nested resource, e sem um pai que valha autorizar não há check pra ser confundido com o certo.

O seed espelha os átomos anteriores **em parte, de propósito**: os mesmos doze pedidos nos ids `1001`–`1012`, os mesmos itens, valores e endereços, redistribuídos três/quatro/cinco entre as lojas, com nomes de comprador novos. Você deve reconhecer os dados e ver que só a estrutura de autorização se moveu. É um uso do espelho diferente do que o `bola-uuid-leaked` fez, onde o espelho tinha que ser total porque a identidade *era* a tese; aqui a tese é o contraste, então o espelho é parcial por decisão.

Um detalhe deliberado do seed: os compradores — `Priya Shah`, `Marcus Webb`, `Elena Ruiz`, `Theo Okafor` — não dividem nome com operador nenhum. Compradores são o público, operadores são funcionários. Um pedido cujo comprador levasse o nome de um operador sussurraria um segundo eixo de posse, pessoa-é-dona-do-pedido, e este átomo depende de o leitor aceitar que o que é dono de um pedido é a **loja**. É também por isso que todo operador de uma loja lê todos os pedidos daquela loja, e por que isso é a feature: tanto o `bob` quanto a `carol` operam a `summit`, os dois veem os cinco pedidos dela, e nenhum dos dois está explorando coisa nenhuma.

## O token é opaco, e o ataque nunca o toca

O Bearer token é uma string opaca aleatória (`randomBytes(24).toString("base64url")`) resolvida server-side pelo mapa `TOKENS` — um substituto pra um OAuth2 opaque access token ou uma session id, não um JWT. Nada no ataque inspeciona, decodifica, adultera ou forja ele: a `dana` faz login como ela mesma e manda o próprio token, inalterado, o tempo todo. É esse o ponto de um token opaco cripto-forte aqui. A identidade dela é sólida e legitimamente dela, e o check do pai lê essa identidade corretamente em todo e qualquer request — então a única coisa que sobra pra explicar a leitura cross-store é a pergunta que ninguém fez. Um token fraco ou forjável seria uma *segunda* vulnerabilidade (broken authentication); mantê-lo forte prende este átomo a exatamente um bug.

## Isto é BOLA — o check existia e apontava pra outro lugar

Nada que o caller manda é parseado ou executado. Dois ids legítimos, combinados num request legítimo sob um token legítimo, alcançam um objeto fora do escopo do caller. Isso é Broken Object Level Authorization — **API1:2023**, o risco #1 do OWASP API Security Top 10 — e é o IDOR vestido de API, a mesma classe do `bola-sequential-id` e do `bola-uuid-leaked`. O que muda é onde o gap fica. Nesses dois, a rota de detalhe não perguntava nada sobre o objeto, e a pergunta de auditoria que os encontra é "onde isto confere que o caller é dono?" Aqui essa pergunta tem resposta — o `operates()`, ali mesmo no handler, fazendo trabalho de verdade — e a resposta é a errada, porque ela é sobre o pai. Então, pra um nested resource, a pergunta de auditoria fica um grau mais afiada: **o objeto que eu estou prestes a devolver pertence ao pai que eu acabei de autorizar?** Um handler pode passar na primeira pergunta e falhar na segunda, e não vai dar `grep` de um jeito nem de outro.
