# Walkthrough — bfla-method-based

## 1. Contexto

Uma API de perfil serve duas rotas num path só: o `GET /users/:handle` lê o perfil de uma conta, e o `PATCH /users/:handle` edita o nome de exibição dela. Os dois autenticam o caller com um Bearer token, mas só o `GET` confere que o registro é seu; o `PATCH` escreve sem esse check, então qualquer usuário logado consegue editar o registro de qualquer um. Isso é **BFLA (Broken Function Level Authorization)** — o **API5:2023** do OWASP API Security Top 10. **Function-level authorization** é o check de acesso ligado a uma *operação* — um par (método, path) — e não a um objeto; **method-based BFLA** é quando esse check está presente num método de um path e ausente em outro.

Este é o segundo átomo da série nesse eixo, e o contraste com os vizinhos é o ponto todo. Os três átomos de API1 faziam uma pergunta sobre o **objeto** — *este pedido é seu?* no `bola-sequential-id` e no `bola-uuid-leaked`, *ele pertence a esta loja?* no `bola-nested-resource` — e a respondiam em toda rota que servia o objeto. O `bfla-admin-function` perguntava sobre a **função** — *você pode invocar esta operação, para começo de conversa?* — e nunca a fazia. Este átomo pergunta sobre o **método**: *a autorização cobre todos os métodos deste path?* Aqui a resposta é não — ela cobre o `GET`, não o `PATCH`.

Achar a escrita não é um desafio a encenar: você já edita o seu próprio perfil com o `PATCH /users/:handle`, então basta apontar esse mesmo `PATCH` pro handle de outra pessoa. E não há leitura cross-user legítima pra embaçar o quadro — cada conta é dona de exatamente um registro, o que tem a chave do próprio handle, então um `GET` pra um registro que não é seu é *corretamente* recusado. Você é o `clancy`. No fim, você terá editado o registro de outro usuário com o seu próprio token válido, e provado a mudança fazendo a vítima lê-la de volta.

Esta é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra o [`vulnerable/app.ts`](./vulnerable/app.ts) e leia os dois handlers de `/users/:handle` um ao lado do outro. O `GET` protege o registro com um ownership check; o `PATCH`, no mesmo path, não:

```ts
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  res.json({ handle: req.params.handle, displayName: user.displayName });
});

app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  // VULNERABLE: the GET handler on this same path guards the record with an ownership
  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
  // the path -- guarding the read left the write on the same resource wide open.
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);                               // unknown target user
  user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
  res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
});
```

Os dois autenticam do mesmo jeito, então token ausente ou inválido leva `401` em qualquer um. A assimetria é uma linha: o `GET` tem `if (req.params.handle !== caller) return 403`, e o `PATCH` não. Então a pergunta de auditoria aqui não é a de BOLA — *"onde isto confere que o caller é dono do objeto?"* — nem a do `bfla-admin-function` — *"onde isto confere a role do caller?"* —, é **"a autorização cobre todos os métodos deste path?"** A resposta: ela cobre o `GET`, e não cobre o `PATCH`.

- **O check está presente e correto — num método.** Isto não é um check ausente apontado pra lugar nenhum; o ownership check está ali no `GET`, e funciona. A brecha é que ele foi escrito pra um método e o outro ficou pelado.
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar — sem `eval`, sem query concatenada. Você acha listando os métodos que um path aceita e conferindo que cada um carrega a autorização que o recurso precisa.

## 3. Como funciona a auth deste lab

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Duas coisas pra ter em mente antes de começar:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401` nas duas rotas. Você confirma isso no Passo 2.
- **Se o registro é o do próprio caller é um check separado** — um **ownership check**, `req.params.handle === caller`. O `GET` o faz; o `PATCH` vulnerable não. É essa a única diferença entre os dois métodos.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você não o decodifica, não o altera, não o forja — você faz login como você mesmo e manda o token exatamente como emitido. Ele fica válido e do `clancy` do começo ao fim. O alvo é o método, não o token.

## 4. Baseline — faça login e veja a posse funcionar no `GET`

Aponte o Burp pra API vulnerable em `127.0.0.1:8205` e trabalhe do Repeater.

> **O token abaixo é de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu da response de login para o header `Authorization`. Os handles são estáveis (seedados), então esses você cola literalmente.

Faça login como você mesmo, `clancy`:

```
POST /login HTTP/1.1
Host: 127.0.0.1:8205
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<clancy-token>` abaixo):

```json
{"token":"B4s3jvY0EveEUjKJ9H_Wb8dm7tJrJtdy"}
```

> `Método: GET · Alvo: clancy (seu) · Isola: ler o próprio registro é permitido`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — `200`:

```json
{"handle":"clancy","displayName":"Clancy Park"}
```

Agora tente ler a outra conta seedada, a `alice`, com o mesmo token:

> `Método: GET · Alvo: alice (não é seu) · Isola: o ownership check recusa uma leitura alheia`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — **`403`**, corpo `Forbidden`. O servidor **sabe conferir posse**, e recusa: o registro da `alice` não é seu pra ler. Segure essa response — é o que vai separar esta falha dos dois sósias dela.

## 5. Passo 1 — Escreva no registro de outro usuário pelo método desprotegido (BFLA confirmado)

Mesmo token, mesmo path, mesmo registro alheio — mude só o método, de `GET` pra `PATCH`, e mande um nome de exibição novo:

> `Método: PATCH · Alvo: alice (não é seu) · Isola: a escrita não tem ownership check`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "pwned by clancy"}
```

Response — **`200`**:

```json
{"handle":"alice","displayName":"pwned by clancy"}
```

A **mesma URL** que recusou a sua *leitura* há um instante (`GET /users/alice` → `403`) aceitou a sua *escrita* (`PATCH /users/alice` → `200`). Você editou um registro que **não é seu**, com o seu próprio token válido, **mudando nada além do verbo HTTP**. O que explica o sucesso não é um objeto seu nem uma identidade forjada — é que **este método ficou desprotegido**. Isso é o **BFLA**: a autorização se aplica a um par (método, path), e guardar o `GET` nunca guardou o `PATCH`.

**Leia a response com cuidado, porque ela é uma armadilha.** O `200` prova que a autorização foi **contornada** — o servidor aceitou e rodou a escrita pra um não-dono. Ele **não** prova que o registro da `alice` mudou de forma visível: o corpo só reflete o valor que *você* mandou (`displayName` é o seu input ecoado, `handle` é o que você pôs no path). Um endpoint que ignorasse o `:handle` por completo e só devolvesse o seu input responderia idêntico. E você não consegue confirmar a mudança por outro caminho, porque o `GET /users/alice` com o seu token é `403`. A escrita é real, mas do lado do atacante ela é **inobservável pela API** — a mesma armadilha que o `bfla-admin-function` carregava. A prova da mudança vem no Passo 3, por outro caminho: a vítima lendo o próprio registro.

## 6. Passo 2 — O que a vuln NÃO é

Um request legítimo com um token legítimo é fácil de ler errado de duas formas. Nomeie as duas e desmonte cada uma, com três requests, todos mandados com o seu `<clancy-token>` inalterado.

**"Isto é o `bfla-admin-function` de novo — um endpoint sem check."** Não é:

> `Método: GET · Alvo: alice (não é seu) · Isola: AQUI tem autorização funcionando neste path`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — **`403`**. Diferente do átomo admin, onde a função atacada não tinha autorização nenhuma, este path *tem* um check funcionando — o servidor recusa uma leitura alheia. A autorização não está ausente; ela só não está em todo método.

Agora a escrita, pra contraste, mesmo alvo alheio:

> `Método: PATCH · Alvo: alice (não é seu) · Isola: mesmo path, mesmo registro, método diferente — e passa`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>

{"displayName": "again"}
```

Response — **`200`**. Entre este request e o de cima, só o **método** mudou, e o veredito virou.

**"Isto é BOLA — alcancei um objeto que não era meu."** Também não é:

> `Método: GET · Alvo: clancy (seu) · Isola: o 403 de cima era a posse funcionando, não "GET é sempre barrado"`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <clancy-token>
```

Response — **`200`**, o seu próprio registro. Então o `403` no `GET /users/alice` não era "o `GET` está barrado aqui" — era o ownership check fazendo o trabalho dele: `200` pro seu próprio registro, `403` pro de outra pessoa. A object-level authorization está **presente e correta**. Se isto fosse BOLA, esse check estaria quebrado ou ausente na leitura; não está nem um nem outro. A única coisa que falta é o mesmo check no `PATCH`.

Mais um, pra fechar a última leitura errada — a de que isto é um problema de autenticação quebrada. Tire o header por completo:

> `Método: PATCH · Alvo: alice · Token: nenhum · Isola: a autenticação é imposta — sem identidade, nada roda`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8205
```

Response — **`401`**, corpo `Unauthorized`, com um header `WWW-Authenticate: Bearer`. (Corrompa o token mudando um caractere e você leva `401` também.) Você esteve autenticado como `clancy`, de forma correta e contínua, em todos os outros requests — isto não é identidade quebrada nem impersonation.

Junte tudo. A object-level authorization está **presente, correta e aplicada — no `GET`**: ela recusa o registro alheio e serve o seu. O `PATCH` sobre o *mesmo* registro, pelo *mesmo* usuário, **nunca passa por ela**. A falha não é o ownership check estar errado (não é BOLA), nem o método não ter autorização nenhuma (não é o átomo admin) — é o check **não cobrir todos os métodos do path**. A pergunta a fazer de um path é *"a autorização está em todo método?"*, não *"de quem é o objeto?"*.

> **Uma mesma URL respondeu à leitura com segurança e à escrita escancarada — porque a autorização se prende ao par (método, path), e guardar o GET nunca guarda o PATCH.**

## 7. Passo 3 — Impacto: a vítima lê o valor plantado

O `200` do Passo 1 contornou a autorização, mas o corpo dele era o seu próprio input ecoado, e o `GET /users/alice` com o seu token é `403` — então, do seu lugar, nada confirma que o registro de fato mudou. A prova usa só o que já existe — o `GET` protegido e o `POST /login`, sem rota nova, sem mudar o seed: a única pessoa com permissão de ler o registro da `alice` é a **`alice`**. Faça login como ela (o seed já a tem — é só mais um `POST /login`):

> `Método: POST · Logando como: alice (a vítima) · Isola: obter o token da própria dona`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8205
Content-Type: application/json

{"user": "alice"}
```

Response — `200` com o token da `alice` (mostrado como `<alice-token>`). Agora faça ela ler o próprio perfil:

> `Método: GET · Alvo: alice (dela) · Token: alice · Isola: a dona lê o próprio registro e encontra o valor do atacante`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8205
Authorization: Bearer <alice-token>
```

Response — **`200`**:

```json
{"handle":"alice","displayName":"pwned by clancy"}
```

**Esta é a prova.** A `alice`, lendo o próprio registro pelo `GET` autorizado, encontra o `displayName` que o `clancy` escreveu — `"pwned by clancy"`, não o valor do seed `"Alice Nguyen"`. A escrita do Passo 1 foi real o tempo todo; ela só não era observável do lado do atacante. O mesmo `GET` protegido que foi a prova viva da autorização correta (Passos 1 e 2) agora também serve de instrumento de verificação, e o loop fecha sem uma rota a mais.

O impacto, dito com honestidade: isto é **horizontal** — um usuário comum editou o registro de outro usuário comum pelo método desprotegido, enquanto o `GET` do mesmo path recusa uma leitura alheia. Não é vertical (nenhuma role é ganha — não há admin aqui) e não é RCE. Onde o `bfla-admin-function` alcançava *acima* do nível de privilégio dele, este alcança *de lado*, até o registro de um par, por um método que ninguém guardou.

## 8. Por que o fix funciona (porta 8305)

Aponte o Burp pra API fixed em `127.0.0.1:8305` e faça login lá como `clancy` — cada build tem o próprio mapa de tokens e o próprio seed, então você precisa de um token novo, e nada do que você fez na 8205 vale aqui. Replay o exploit:

> `Método: PATCH · Alvo: alice (não é seu) · Isola: o ownership check do GET, agora também no PATCH`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8305
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "pwned by clancy"}
```

Response — **`403`**, corpo `Forbidden`. O `PATCH` agora roda o mesmo ownership check que o `GET` já tinha, logo depois de autenticar e **antes** de o registro ser buscado — então a escrita abaixo dele nunca roda, e o registro da `alice` fica intocado. Faça a `alice` lê-lo pra confirmar: o `GET /users/alice` com o token dela devolve `{"handle":"alice","displayName":"Alice Nguyen"}`, o valor do seed, porque nada foi escrito.

O fix não quebrou a feature; restringiu-a ao dono. Editar o seu **próprio** registro continua funcionando — nenhuma conta admin é necessária, porque o caminho legítimo é simplesmente você editando a si mesmo:

> `Método: PATCH · Alvo: clancy (seu) · Isola: o dono ainda consegue editar o próprio registro`

```
PATCH /users/clancy HTTP/1.1
Host: 127.0.0.1:8305
Authorization: Bearer <clancy-token>

{"displayName": "My New Name"}
```

Response — `200` com `{"handle":"clancy","displayName":"My New Name"}`. O `GET` está inalterado (`200` pro seu próprio registro, `403` pro alheio), e token ausente ou ruim continua levando `401` com o challenge `WWW-Authenticate: Bearer` dele; os `403` não trazem nenhum, porque você já estava autenticado e não há o que pedir.

**`403`, não `404`.** Um não-dono leva um `403` honesto, não um `404` que fingiria que o registro não está lá. O ownership check compara o handle do path com o caller antes de qualquer busca, então não revela existência nenhuma a esconder — diferente dos átomos de API1, onde o `404` de um pedido escondia a existência dele num espaço de ids enumerável. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) carrega o argumento completo — RFC 9110 §15.5.4 e o critério único da série pra escolher entre os dois.

O walkthrough termina aqui. O achado é um usuário comum editando o registro de outro usuário com o seu próprio token válido, num método que nunca foi guardado; o fix é um ownership check, copiado do `GET` pro `PATCH`. Pra se aprofundar na classe, a página da PortSwigger do theory primer é o lugar.
