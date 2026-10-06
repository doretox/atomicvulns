# Walkthrough — bfla-admin-function

## 1. Contexto

Uma API admin serve `POST /admin/users/:handle/promote`, que concede a role de admin à conta nomeada no path. Ela autentica o caller com um Bearer token e então executa a promoção sem checar se o caller é admin. Isso é **BFLA (Broken Function Level Authorization)** — o **API5:2023** do OWASP API Security Top 10. **Function-level authorization** é o check que pergunta se o caller pode invocar uma operação, para começo de conversa, sobre o que quer que ela opere; sem ele, um membro comum roda uma função de administrador, o que é **vertical privilege escalation** — alcançar uma capacidade acima do seu próprio nível de privilégio.

É aqui que a série muda de eixo. Os três átomos de API1 perguntavam sobre a **instância**: *este objeto é seu?* no `bola-sequential-id` e no `bola-uuid-leaked`, *ele pertence a esta loja?* no `bola-nested-resource`. Este átomo pergunta sobre a **capacidade**: *você pode invocar esta operação?* — e o build vulnerable nunca pergunta.

O path admin é simplesmente conhecido — rotas admin seguem nomes previsíveis, specs OpenAPI (descrições legíveis por máquina das rotas de uma API) costumam ser públicas, e bundles de front-end carregam paths de telas que um membro nunca vê —, então achar o endpoint não é o desafio; invocá-lo sem a role é. Você é o `clancy`, um membro comum. No fim, você terá rodado a função restrita a admins com o seu próprio token válido, na conta de outra pessoa e na sua.

Esta é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra o [`vulnerable/app.ts`](./vulnerable/app.ts). O handler vulnerable é curto:

```ts
app.post("/admin/users/:handle/promote", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  // VULNERABLE: the caller is authenticated, but the handler never checks the caller's
  // ROLE. Promoting a user to admin is an admin-only function; here ANY authenticated
  // user can invoke it. Authenticated is not authorized to PERFORM this operation.
  const target = USERS.get(req.params.handle);
  if (!target) return res.sendStatus(404);                  // unknown target user
  target.is_admin = true;                                   // state change -- not a read
  res.json({ handle: req.params.handle, is_admin: true });  // the state delta, not third-party data
});
```

Leia duas vezes. Ele chama `authenticate()`, então um token ausente ou inválido é recusado com `401`, e da linha seguinte em diante o request está *genuinamente autenticado* — o handler até guarda o resultado em `caller`. Aí ele busca o alvo, põe o `is_admin` dele em `true` e responde. O bug é **o que não está lá**: nada compara a role do caller com a role que esta função exige. Passada a linha do `401`, o `caller` nunca mais é lido.

- **A pergunta de auditoria é nova.** Nos átomos de API1 a pergunta era sobre o objeto: "onde isto confere que o caller é dono do pedido?" no `bola-sequential-id` e no `bola-uuid-leaked`, "onde isto confere que o pedido pertence à loja autorizada?" no `bola-nested-resource`. Aqui não há objeto sobre o qual perguntar. A pergunta é **"onde este endpoint confere que o caller pode invocar esta função?"** — e a resposta é em lugar nenhum.
- **Ele chama `authenticate()`, e é exatamente isso que desarma o revisor apressado** — "tem auth no endpoint, parece ok". É a armadilha dos átomos de API1 num eixo novo. Lá, o handler sabia quem você era e nunca amarrava o objeto a você — ao dono dele, ou à loja para a qual você estava autorizado. Aqui ele sabe quem você é e nunca checa o que você tem permissão de fazer.
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar — sem template sink, sem `eval`, sem query concatenada. Você acha lendo cada operação privilegiada e perguntando onde ela checa a role do caller.

## 3. Como funciona a auth deste lab

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Duas coisas pra ter em mente antes de começar:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401`. Você confirma isso no Passo 3.
- **Se a role do caller é checada pra autorizar a *função* é outra pergunta** — e o handler vulnerable nunca a faz. Cada usuário do seed carrega um flag de role, `is_admin`; é esse flag que o check ausente deveria ter lido.

Dá pra ver no seed que o `clancy` é membro comum — `["clancy", { is_admin: false }]` no `app.ts` —, e o build fixed confirma isso de fora: a mesma chamada lá é recusada com `403`. O build vulnerable nunca diz isso, porque nunca checa.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você não o decodifica, não o altera, não o forja — você faz login como você mesmo e manda o token exatamente como emitido. Ele fica válido e do `clancy` do começo ao fim. O alvo é a função, não o token.

## 4. Baseline — faça login como membro comum

Aponte o Burp pra API vulnerable em `127.0.0.1:8204` e trabalhe do Repeater.

> **O token abaixo é de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu da response de login para o header `Authorization`. Os handles são estáveis (seedados), então esses você cola literalmente.

Faça login como você mesmo, `clancy`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8204
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<clancy-token>` abaixo):

```json
{"token":"ylZa7AnzAM7czgZ0tjYZVGjGVN8eJw-j"}
```

Esse é o baseline inteiro. A API autentica o `clancy` perfeitamente; ele só não é admin. Não há rota de leitura pra mostrar um escopo aqui — a superfície são duas rotas, e a outra é a função admin que você chama em seguida.

## 5. Passo 1 — Rode a função admin como membro comum (BFLA confirmado)

Peça à função admin que promova a `alice`, também membro comum, com o seu próprio `<clancy-token>`, inalterado. O alvo vai no path; não há corpo:

```
POST /admin/users/alice/promote HTTP/1.1
Host: 127.0.0.1:8204
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"handle":"alice","is_admin":true}
```

Você invocou uma **função admin** — conceder a role de admin a uma conta — como **membro comum**, com o seu próprio token válido. A conta sobre a qual ela agiu não é sua, e você não tem relação nenhuma com a `alice`; o que explica o sucesso não é um objeto seu nem uma identidade forjada, e sim que **a própria função estava desprotegida**. Isso é o **BFLA**, e é privilege escalation **vertical**: você exerceu um poder acima do seu nível, em vez de ler o dado de um par. Nada aqui é payload; o request é válido por toda regra de protocolo, um WAF (web application firewall) não vê nada de errado, e a autenticação "passou".

**A response não é uma leitura de objeto.** O corpo traz só o que a operação escreveu: o `handle` é o que você pôs no path, e `is_admin: true` é um literal que o handler sempre devolve, seja qual for o alvo. Não há nome, nem endereço, nem registro privado da `alice` ali — que ela é membro comum é algo que você leu no seed, não na response. É proposital: esta função admin muda estado em vez de devolver o dado de alguém, então não volta nada que você pudesse confundir com "li o que não era meu" — o reflexo de BOLA que os átomos de API1 treinaram. A escrita é real, mas nenhuma rota lê uma role de volta, então de fora o `200` só te diz que a função rodou.

Repare no que a função nunca perguntou sobre a `alice`: nada além de se o handle existe. Ela aceitaria qualquer alvo, e o Passo 2 prova isso com o caso-limite.

## 6. Passo 2 — Promova a si mesmo: o alvo não importa

Mesmo token, mesma função; desta vez o alvo é o seu próprio handle:

```
POST /admin/users/clancy/promote HTTP/1.1
Host: 127.0.0.1:8204
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"handle":"clancy","is_admin":true}
```

O endpoint promoveu uma estranha no Passo 1 e promove você agora, com a mesma indiferença. De quem é a conta-alvo nunca entra na decisão. Essa indiferença ao alvo é a assinatura do BFLA, e o sinal de que o eixo sob ataque é **a operação**, não a instância.

## 7. Passo 3 — O que a vuln NÃO é

O exploit é um request legítimo com um token legítimo, então é fácil de ler errado. Dois passos fixam a causa real.

**(a) Não é sobre de quem é o objeto.** Leia o request do Passo 2 do jeito BOLA. Se esta falha fosse sobre alcançar um objeto fora do seu escopo, não haveria nada de errado ali: o registro é do próprio `clancy`, e ele está mexendo só em si mesmo. E mesmo assim a chamada nunca deveria ter sido permitida, porque **promover é uma função admin**, seja quem for o alvo. Aquele request é irrepreensível como acesso a objeto e ainda assim é a falha — então o eixo não é o objeto.

**(b) Não é falha de autenticação.** Mande o request do Passo 1 **sem nenhum header `Authorization`**:

```
POST /admin/users/alice/promote HTTP/1.1
Host: 127.0.0.1:8204
```

Response — **`401`**, corpo `Unauthorized`. A autenticação funciona: sem identidade, a função não roda. (Corrompa o token trocando ou acrescentando um caractere e você leva `401` também.) Você esteve autenticado como `clancy`, corretamente e sem interrupção, nos Passos 1 e 2 — isto não é identidade quebrada nem impersonation.

Segure (a) e (b) juntos. A autenticação está presente e funcionando: o servidor sabe exatamente quem está chamando. O objeto é irrelevante: a falha está igualmente presente no seu próprio registro. O que falta fica entre saber quem você é e rodar a operação — o check de que o caller tem a role que a função exige. Isso é BFLA: não é BOLA, não é autenticação quebrada.

> **O endpoint nunca se importou com de quem era a conta-alvo, porque a falha nunca foi sobre o alvo — foi sobre quem pode rodar a função, para começo de conversa.**

## 8. Por que o fix funciona (porta 8304)

Aponte o Burp pra API fixed em `127.0.0.1:8304` e faça login lá como `clancy` — cada build tem o próprio mapa de tokens e o próprio seed, então você precisa de um token novo, e nada do que você fez na 8204 passa pra cá. Depois repita a sua cadeia dos Passos 1 e 2. Ela para no primeiro request:

- `POST /admin/users/alice/promote` com o seu `<clancy-token>` → **`403`**, corpo `Forbidden`. O handler agora checa a role do caller logo depois de autenticar e recusa ali mesmo: a busca do alvo e a escrita abaixo dela nunca rodam, então a `alice` nunca é promovida.

Nada mais na cadeia passa:

- `POST /admin/users/clancy/promote` → **`403`** também. Promover a si mesmo é recusado exatamente pelo mesmo motivo, porque o alvo nunca fez parte da pergunta.
- `POST /admin/users/nobody/promote`, um handle que nunca foi seedado → **`403`**, não `404`. O check de role roda antes de o alvo ser buscado, então um não-admin não aprende nada sobre quais contas existem.

A função continua funcionando pra quem pode rodá-la. Faça login na 8304 com `{"user": "carol"}` — a `carol` é a admin do seed — e promova o `bob` com o token dela:

```
POST /admin/users/bob/promote HTTP/1.1
Host: 127.0.0.1:8304
Authorization: Bearer <carol-token>
```

Response — `200`:

```json
{"handle":"bob","is_admin":true}
```

O fix não quebrou a feature; ele restringiu quem pode invocá-la. Sem token ou com token ruim ainda leva `401`.

**`403`, não `404`.** Os átomos de API1 respondem `404` pra um pedido fora do seu escopo; aqui o não-admin leva um `403` honesto. O endpoint é conhecido por premissa, então não há existência a esconder, e o `403` diz a verdade: você está autenticado, e a sua role não basta pra esta operação. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) carrega o argumento completo — o RFC 9110 §15.5.4, o critério único da série pra escolher entre os dois, e por que o argumento do oráculo de enumeração (uma diferença nas responses que deixaria um atacante mapear quais ids existem) por trás do `404` de pedido no `bola-sequential-id` e no `bola-nested-resource` não se aplica a uma função conhecida.

## 9. Impacto — um flag de role que qualquer um escreve

O impacto é provado pelos dois builds juntos, cada um mostrando a metade que é verdadeira nele.

- **A metade vulnerable: qualquer um escreve o flag.** Ela já está na mesa, sem request novo. Nos Passos 1 e 2, o `clancy`, um membro comum, pôs `is_admin: true` na `alice` e no próprio registro — em qualquer conta que ele nomeou, ele mesmo incluído.
- **O que o build vulnerable não consegue mostrar: que o flag vale alguma coisa.** Nenhuma role é checada em lugar nenhum dele — `is_admin` é escrito e nunca lido —, então nenhuma response da 8204 muda por causa dessas escritas, e este walkthrough não finge que alguma muda.
- **A metade fixed: o flag governa a função.** Ponha lado a lado os dois requests da seção anterior: a `carol` promovendo o `bob` leva `200`, o `clancy` promovendo a `alice` leva `403`. O check de role roda antes de o alvo ser buscado, então o alvo não toma parte na decisão; a única coisa que separa o `200` do `403` é o `is_admin` do caller. No build fixed, esse flag decide quem pode rodar a função.

Junte as metades: **o flag de role é o que governa a capacidade admin, e no build vulnerable qualquer membro autenticado consegue escrevê-lo** — pra qualquer conta, a dele incluída. Essa é a vertical privilege escalation, provada sem uma única rota extra.

O walkthrough termina aqui. O achado é um membro comum rodando uma função restrita a admins com o próprio token válido, em qualquer conta que ele nomeie; o fix é um check de role, posto antes da busca do alvo. Pra ir mais fundo na classe, a página da PortSwigger no theory primer é o lugar.
