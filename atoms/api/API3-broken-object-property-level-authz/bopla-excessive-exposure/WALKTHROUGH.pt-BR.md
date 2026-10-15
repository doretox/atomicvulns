# Walkthrough — bopla-excessive-exposure

## 1. Contexto

Uma API de perfil serve o `GET /users/:handle`: ela autentica o caller com um Bearer token, confere que o registro é o do próprio caller, e o devolve. O ownership check está certo — você só lê o seu próprio perfil — mas o handler então serializa o **registro inteiro** guardado, então dois campos server-side voltam junto: `passwordHash` e `is_admin`. Isso é **BOPLA (Broken Object Property Level Authorization)** — o **API3:2023** do OWASP API Security Top 10 —, na sua face de leitura, o que a indústria chama de **excessive data exposure**: a resposta devolve propriedades que o caller não deveria ver. **Property-level authorization** é o check de acesso aplicado aos campos individuais de um objeto, abaixo do objeto como um todo.

Este é o primeiro átomo da série no grão da **propriedade**, e o contraste com os vizinhos é o ponto. Os três átomos de API1 faziam uma pergunta sobre o **objeto** — *este objeto é seu?* Os dois de API5 perguntavam sobre a **função** — *você pode invocar esta operação?* Este átomo pergunta sobre o **campo**: *a resposta devolve só os campos que este caller pode ver?* Aqui a resposta é não — ela devolve `displayName`, e também `passwordHash` e `is_admin`.

Não há nada a encenar nem segundo ator. Você é o `clancy`, e lê o **seu próprio** perfil — totalmente autorizado no nível do objeto — e os campos internos já estão no corpo. A "técnica" é ler o raw da resposta no Repeater, que é exatamente o reflexo que separa um pentester de quem confia na UI.

Esta é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra o [`vulnerable/app.ts`](./vulnerable/app.ts). O único handler a ler é o `GET /users/:handle`:

```ts
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // VULNERABLE: the ownership check above is right -- this IS your record. But the response
  // spreads the WHOLE stored object, so every server-side field rides along with the public
  // one. Authorization applies to each property returned, not only to the object.
  res.json({ handle: req.params.handle, ...user });
});
```

A assimetria é **dentro de um handler**, não entre dois. O ownership check (`if (req.params.handle !== caller) return res.sendStatus(403)`) está presente e correto — ele deixa você ler só o seu próprio registro. Uma linha abaixo, o `res.json({ handle: req.params.handle, ...user })` espalha o objeto inteiro guardado na resposta. O registro carrega três campos — `displayName`, `passwordHash`, `is_admin` — e o spread entrega os três. Então a pergunta de auditoria aqui não é a de BOLA — *"onde isto confere que o caller é dono do objeto?"* (confere, e passa) — nem a de BFLA — *"a autorização cobre todos os métodos?"* —, é **"a resposta devolve só os campos que este caller pode ver?"** A resposta: não.

- **O ownership check não é a falha — e isso inverte o átomo irmão.** No `bfla-method-based`, este mesmíssimo `GET` era a *prova viva* de que o ownership check funcionava. Aqui a mesma guarda continua correta e continua passando; a falha é nova e mora uma linha abaixo dela, no que é serializado.
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar — sem `eval`, sem query concatenada. Você acha lendo o que cada handler devolve e perguntando se cada campo da resposta é um que o caller tem permissão de ver.

## 3. Como funciona a auth deste lab

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Duas coisas pra ter em mente antes de começar:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401` com um challenge `WWW-Authenticate: Bearer`. Você confirma isso no Passo 5.
- **A posse é checada, e passa pro seu próprio registro.** `req.params.handle === caller` deixa você ler o registro com a chave do seu handle e recusa o de qualquer outro. Esse check está correto; não é onde o bug está.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você não o decodifica, não o altera, não o forja — você faz login como você mesmo e manda o token exatamente como emitido. Ele fica válido e do `clancy` do começo ao fim. E o `passwordHash` que a resposta vaza **não** é o que o login lê: o login não recebe senha nenhuma, e o hash é dado dummy stored-side. O alvo é o que a resposta serializa, não o token nem a senha.

## 4. Baseline = Exploit — faça login e leia o seu próprio perfil

Aponte o Burp pra API vulnerable em `127.0.0.1:8206` e trabalhe do Repeater.

> **O token abaixo é de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu da response de login para o header `Authorization`. O handle é estável (seedado), então esse você cola literalmente.

Faça login como você mesmo, `clancy`:

> `Método: POST · Logando como: clancy (você)`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8206
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<clancy-token>` abaixo):

```json
{"token":"B4s3jvY0EveEUjKJ9H_Wb8dm7tJrJtdy"}
```

Agora leia o seu próprio perfil — o registro a que você tem todo o direito:

> `Método: GET · Alvo: clancy (seu) · Isola: o seu próprio registro volta com os campos internos junto`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8206
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
{"handle":"clancy","displayName":"Clancy Park","passwordHash":"$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpasswordCLANCY","is_admin":false}
```

**Esta é a prova, e ela é auto-contida.** Você pediu o **seu próprio** perfil, totalmente autorizado, e a resposta trouxe `passwordHash` e `is_admin` — campos server-side que jamais deveriam ter saído do servidor. Não houve payload, não houve segundo ator, não houve segundo request: a leitura de baseline *é* o exploit, e o "exploit" é ler o corpo cru no Repeater. É esse o contraste honesto com o `bfla-method-based`: lá, o `200` da escrita era o seu próprio input ecoado, então não provava nada sozinho, e a prova precisou da vítima lendo o registro dela depois. Aqui a self-read prova direto — os campos vazados estão no corpo que voltou pra **você**, do registro que é **seu**.

## 5. Passo — O que a vuln NÃO é

Um request legítimo com um token legítimo é fácil de ler errado. Duas leituras pra desmontar com firmeza, e uma terceira como princípio.

**"Isto é BOLA — li dado que não era meu."** Não é. Tente a outra conta seedada com o seu próprio token:

> `Método: GET · Alvo: alice (não é seu) · Isola: o ownership check existe e morde`

```
GET /users/alice HTTP/1.1
Host: 127.0.0.1:8206
Authorization: Bearer <clancy-token>
```

Response — **`403`**, corpo `Forbidden`. A object-level authorization está presente e correta: você **não** leu o objeto de outra pessoa — leu o **seu**. O problema não é acesso a um objeto alheio; é o **conteúdo do seu próprio objeto**. (Este `403` é a mesma guarda de posse que o `bfla-method-based` usava, comparada antes de qualquer busca — o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) carrega o argumento completo de status code.)

**"Isto é crypto fraco."** Não é a lição aqui. Olhe de novo o corpo do Passo 4 — sem request novo: o que importa é que o `passwordHash` esteja **na resposta, para começo de conversa**, não quão forte é o hash. Qualquer que fosse o algoritmo, esse campo jamais deveria ter saído do servidor. Hashing fraco é outra classe; aqui o eixo é **exposição**.

Uma terceira leitura errada que vale nomear como princípio: **controle no cliente não é controle.** Num app real a UI poderia omitir esses campos da tela — mas um pentester lê o raw da resposta de qualquer jeito, então a filtragem tem que ser server-side. Não há UI nenhuma neste átomo, e é exatamente esse o ponto: a única coisa entre os campos internos e o cliente é o que o handler escolhe serializar.

Junte tudo. Você está **totalmente autorizado para o objeto** — é o seu registro, e o ownership check o aprova — e a resposta **ainda assim** te entregou campos que você não pode ver. A falha não é ler um objeto alheio (não é BOLA), não é a força do hash (não é crypto fraco), e não é a UI (não há nenhuma). É a resposta **devolver propriedades demais**.

> **Ser dono do objeto nunca foi o mesmo que ter liberação pra cada campo dele — e o corpo cru entregou todos, porque a única autorização no caminho parou no objeto.**

## 6. Passo — Impacto

Dois impactos reais, nenhum inflado:

- **Recon de schema interno.** A resposta expõe a **forma** do registro server-side — que existe um campo `is_admin`, que existe um `passwordHash`, e como eles se chamam. Mesmo com o `is_admin` voltando `false`, o atacante aprende que o campo existe e como é escrito: um mapa do modelo interno, material útil pra ataques posteriores. Isto é **information disclosure**.
- **Um artefato de credencial exposto.** O `passwordHash` é um artefato que **jamais** deveria aparecer numa resposta. Num sistema real, um hash vazado habilita **offline cracking** — adivinhar senhas contra o hash fora do servidor, sem rate limit no caminho.

O que o impacto **não** é:

- **Não é privilege escalation.** O `is_admin` volta `false`; ninguém vira admin, e nada aqui escreve o flag. O vazamento é do **campo** e do **padrão** (o objeto inteiro serializado), não de nenhum valor.
- **Não é password cracking, aqui.** O login é passwordless e o `passwordHash` é dummy — não há senha real pra quebrar. A lição é **exposição**, não a qualidade do hash; um hash mais forte ainda seria um campo que jamais deveria ter saído.

## 7. Por que o fix funciona (porta 8306)

Aponte o Burp pra API fixed em `127.0.0.1:8306` e faça login lá como `clancy` — cada build tem o próprio mapa de tokens, então você precisa de um token novo. Leia o seu perfil de novo:

> `Método: GET · Alvo: clancy (seu) · Isola: a allow-list — só os campos públicos voltam`

```
GET /users/clancy HTTP/1.1
Host: 127.0.0.1:8306
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
{"handle":"clancy","displayName":"Clancy Park"}
```

Os campos internos (`passwordHash`, `is_admin`) **sumiram**; a feature — ler o seu próprio perfil — continua funcionando. O fix trocou o spread do objeto inteiro por uma **allow-list**: a resposta nomeia os campos que o caller pode ver, então qualquer outra coisa fica server-side por padrão.

Nada mais mudou. O ownership check e o `401` estão intocados:

- `GET /users/alice` com o seu `<clancy-token>` → **`403`**, corpo `Forbidden` — igual ao build vulnerable.
- `GET /users/clancy` **sem** o header `Authorization` → **`401`**, corpo `Unauthorized`, com um header `WWW-Authenticate: Bearer`. (Corrompa o token mudando um caractere e você leva `401` também.)

A única linha entre os dois builds é o que a resposta serializa. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) trabalha isso — por que uma allow-list (que falha fechado) é o fix e uma deny-list (que falha aberto) não é, e por que esses status codes seguem o critério da série.

O walkthrough termina aqui. O achado são os campos internos voltando numa self-read que você tinha todo o direito de fazer; o fix é uma linha, nomeando os campos que a resposta pode carregar. Pra se aprofundar na classe, a página da PortSwigger do theory primer é o lugar.
