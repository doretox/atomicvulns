# Walkthrough — bopla-mass-assignment

## 1. Contexto

Uma API de perfil serve o `PATCH /users/:handle`: ela autentica o caller com um Bearer token, confere que o registro é o do próprio caller, e o atualiza. O ownership check está certo — você só escreve no seu próprio perfil — mas o handler então mescla o **corpo inteiro da requisição** no registro guardado, então qualquer propriedade que o corpo nomear é setada, inclusive uma que o formulário de perfil nunca ofereceu: `is_admin`. Isso é **BOPLA (Broken Object Property Level Authorization)** — o **API3:2023** do OWASP API Security Top 10 —, na sua face de escrita, o que a indústria chama de **mass assignment** (também *auto-binding*): o handler liga propriedades da requisição direto no objeto interno, então a requisição acaba podendo setar campos que o dev nunca pretendeu expor. **Property-level write authorization** é o check de acesso aplicado a cada campo que uma requisição tem permissão de mudar, abaixo do objeto como um todo.

Este é o segundo átomo no grão da **propriedade**, e o espelho do primeiro. O irmão `bopla-excessive-exposure` perguntava: *a resposta devolve só os campos que você pode **ver**?* Este pergunta: *a requisição pode **setar** só os campos que você pode escrever?* Mesma raiz — confiar num objeto inteiro — apontada na direção oposta.

Uma coisa a acertar antes de começar, porque o átomo inteiro gira nisso: **o write não vai te dizer se funcionou.** O `PATCH` aqui responde `204 No Content`, nos dois builds, sem nada no corpo. Você vai provar o efeito lendo o estado em outro lugar.

Esta é uma **API — não há trilha browser.** Todo request abaixo é um bloco que você cola no **Burp Repeater** (que reenvia um request único pra você editar e observar). Se você ainda não configurou o Burp, os mesmos requests rodam no `curl`. É esse o ferramental inteiro.

## 2. Ache o bug

Abra o [`vulnerable/app.ts`](./vulnerable/app.ts). O único handler a ler é o `PATCH /users/:handle`:

```ts
app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // VULNERABLE: the ownership check above is right -- this IS your record. But the write
  // merges the WHOLE request body into the record, so every property the body names is set,
  // is_admin included. Authorization applies to each property written, not only to the object.
  USERS.set(req.params.handle, { ...user, ...req.body });
  res.sendStatus(204);                                           // no content: nothing to echo back
});
```

A assimetria é **dentro de um handler**. O ownership check (`if (req.params.handle !== caller) return res.sendStatus(403)`) está presente e correto — ele deixa você escrever só no seu próprio registro. Uma linha abaixo, o `USERS.set(req.params.handle, { ...user, ...req.body })` monta o registro novo espalhando o guardado e, por cima dele, **o corpo inteiro da requisição**. O que o corpo nomear ganha. O registro carrega dois campos — `displayName` e `is_admin` — e o corpo pode setar qualquer um dos dois. Então a pergunta de auditoria aqui não é a de BOLA — *"onde isto confere que o caller é dono do objeto?"* (confere, e passa) — nem a de BFLA — *"o caller pode invocar esta operação?"* —, é **"o write é escopado aos campos que este caller pode setar?"** A resposta: não.

- **O espelho do átomo irmão, no próprio código.** No `bopla-excessive-exposure` a linha do pecado era `res.json({ handle, ...user })` — o registro inteiro **saindo**. Aqui é `USERS.set(handle, { ...user, ...req.body })` — o corpo inteiro **entrando**. Um objeto atravessa a fronteira sem ser examinado; só a direção mudou.
- **Esta classe não dá `grep`.** Não há string perigosa pra procurar. Você acha lendo o que cada handler grava e perguntando se cada propriedade que ele pode setar é uma que o caller tem permissão de controlar.

## 3. Como funciona a auth deste lab — e a porta de admin, já guardada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — uma string aleatória que o servidor guarda num mapa `token -> user` e resolve a cada request. Ele não pede senha: isso é um atalho deliberado do laboratório, não parte do bug. O token é *opaco* — um valor sem estrutura legível, diferente de um JWT (JSON Web Token) cujo payload você poderia decodificar — então não há nada dentro dele pra inspecionar ou adulterar de qualquer forma.

Duas coisas pra ter em mente:

- **A autenticação é genuinamente imposta.** Token ausente ou inválido leva `401` com um challenge `WWW-Authenticate: Bearer`, nas três rotas.
- **A posse é checada, e passa pro seu próprio registro.** `req.params.handle === caller` deixa você escrever no registro com a chave do seu handle e recusa o de qualquer outro. Esse check está correto; não é onde o bug está.

Uma disciplina pro walkthrough inteiro: **o ataque nunca toca o token.** Você não o decodifica, não o altera, não o forja — você faz login como você mesmo e manda o token exatamente como emitido. Ele fica válido e do `clancy` do começo ao fim. A sua identidade nunca muda; o que vai mudar é o **estado** que o servidor lê quando decide o que você tem permissão de fazer.

Agora conheça o instrumento com que você vai provar as coisas. O lab tem uma rota administrativa, `GET /admin/users`, e ela confere a role do caller antes de responder. Aponte o Burp pra API vulnerable em `127.0.0.1:8207`, faça login como você mesmo, e bata nessa porta primeiro.

> **O token abaixo é de uma sessão real.** O `POST /login` gera um token aleatório novo a cada vez, então **o seu vai diferir** — copie o seu da response de login para o header `Authorization`. Os handles são estáveis (seedados), então esses você cola literalmente.

> `Método: POST · Logando como: clancy (você)`

```
POST /login HTTP/1.1
Host: 127.0.0.1:8207
Content-Type: application/json

{"user": "clancy"}
```

Response — `200`, um token que é seu pelo resto da sessão (mostrado como `<clancy-token>` abaixo):

```json
{"token":"S2_AYQTHKg0bsER7kLkXKFMCDOu8YSrw"}
```

> `Método: GET · Alvo: /admin/users · Isola: a função admin está guardada — e você não é admin`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
```

Response — **`403`**, corpo `Forbidden`.

**Leia esse `403` com atenção, porque ele é metade da lição.** A rota admin fez a pergunta certa — *este caller é administrador?* — e te recusou. A função **está** protegida, no build vulnerable, agora mesmo. Guarde esse resultado; o Passo 4 volta nele.

Uma nota de desenho, já que você está aqui: não existe rota que leia o seu próprio registro de volta. A porta de admin é a única janela para o estado, e isso é de propósito — o que importa não é ver o campo, é ver o que o campo **faz**.

## 4. Exploit — três movimentos, e o `204` não é a prova

**Movimento um — o write.** Mande a atualização de perfil que a feature oferece, e acrescente uma chave que o formulário nunca teve:

> `Método: PATCH · Alvo: clancy (seu) · Isola: um campo que o formulário de perfil nunca ofereceu entra ao lado do que ele ofereceu`

```
PATCH /users/clancy HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "Clancy Parked", "is_admin": true}
```

Response — **`204 No Content`**, e o corpo é vazio. Não `{}` — vazio: sem `Content-Type`, sem `Content-Length`, nada.

**Não leia isso como sucesso em setar o `is_admin`.** Um `204` diz que o servidor cumpriu a requisição; não diz **o que** ele gravou. O build fixed responde a este request exato com este `204` exato e não grava nada disso. Se você parar aqui, não aprendeu nada — e é essa armadilha que faz este átomo existir.

**Movimento dois — a prova.** Volte à porta que acabou de te recusar, com o mesmo token, inalterado:

> `Método: GET · Alvo: /admin/users · Isola: a porta que respondeu 403 no Passo 3 agora abre`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
```

Response — **`200`**:

```json
["clancy","alice"]
```

Mesmo request, mesmo token, mesma guarda — e a resposta oposta.

**Movimento três — nomeie o efeito.** Você forjou o `is_admin` por uma atualização de perfil, e a função privilegiada agora te aceita. Repare exatamente no que aconteceu e no que não aconteceu: a rota admin não falhou, não quebrou e não foi burlada. Ela perguntou se você é administrador, leu a resposta no store, e o store agora diz que sim — porque o `PATCH` a colocou lá. O corpo daquele `200` não é o prêmio; são dois handles que você já conhecia. O prêmio é o **status**: uma função que te recusava agora te atende.

É essa a técnica que vale guardar deste átomo, além do bug em si: **um efeito observável se prova lendo o estado por outro caminho, nunca pela resposta do próprio write.**

> **Um write que responde `204` não prova nada sobre o que escreveu — quem provou foi a porta de admin: `403` um minuto atrás, aberta agora.**

## 5. Passo — O que a vuln NÃO é

Um request legítimo, com um token legítimo, escrevendo num registro que é seu, é fácil de ler errado. Duas leituras pra desmontar com firmeza, e uma terceira que vale uma frase.

**"Isto é BOLA — escrevi em algo que não era meu."** Não é. Tente a outra conta seedada com o seu próprio token:

> `Método: PATCH · Alvo: alice (não é seu) · Isola: a posse existe e morde — você só escreve no seu próprio registro`

```
PATCH /users/alice HTTP/1.1
Host: 127.0.0.1:8207
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"is_admin": true}
```

Response — **`403`**, corpo `Forbidden`. O registro da alice fica intocado. A object-level authorization está presente e correta: você **não** escreveu no objeto de outra pessoa — escreveu no **seu**. O problema não é em qual objeto o write chegou; é **qual campo** o write aceitou. (Esta é a mesma guarda de posse que o `bfla-method-based` usa, comparada antes de qualquer busca — o [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) aponta pro argumento completo de status.)

**"Isto é BFLA — invoquei uma função admin que eu não devia."** Esta é a leitura errada a matar, e a evidência já está na sua mão. Volte ao Passo 3: essa mesma rota, com esse mesmo token, respondeu **`403`**. A guarda dela estava lá, ela fez a pergunta certa, e te recusou. Ela continua fazendo a mesma pergunta agora — nada na rota mudou entre o `403` e o `200`, e nada no build fixed a muda também, onde essa rota é **byte-idêntica**. O que mudou foi a resposta que o store dá a ela.

Mantenha os dois casos separados, porque são bugs diferentes com a mesma porta:

- Em **BFLA** — o átomo `bfla-admin-function` — a função privilegiada **não tem check de role nenhum** (ou tem o errado), e um membro comum entra andando. O fix é acrescentar o check.
- Aqui o check **existe, está correto e funciona**. Ninguém passou por cima dele. O caller o satisfez, porque o caller escreveu a própria role que ele consulta. **A guarda que você vê está certa; o breach está a montante, no `PATCH`.**

Se você for procurar o bug no `GET /admin/users`, não vai achar — não há nada errado ali.

**Uma terceira leitura errada, menor: "é só um campo ecoado de volta pra mim."** Não voltou nada — o write respondeu `204` com corpo vazio. O que foi demonstrado foi um privilégio, não um valor numa resposta.

Juntando tudo. Você está **totalmente autorizado para o objeto** (é o seu registro, e a posse aprova), e a função privilegiada está **corretamente guardada** (o `403` dela provou isso antes de você tocar em qualquer coisa) — e mesmo assim você virou administrador. A falha não é escrever em objeto alheio (não é BOLA), não é uma função desprotegida (não é BFLA), e não é um eco. É o write **aceitar propriedades demais**.

## 6. Passo — Impacto

**Escalação de privilégio, real e verificada.** O `clancy` começa como `is_admin: false`, nenhum administrador existe no seed, e uma atualização de perfil o torna um. O acesso administrativo não é inferido da resposta do write — ele é demonstrado pela rota que o recusava um minuto antes e agora responde. Num sistema real, aquela chave a mais no corpo é a distância entre uma conta comum e o console de administração.

O contraste honesto com o átomo irmão: no `bopla-excessive-exposure` o mesmo campo `is_admin` vazava **pra fora** com o valor `false`, e o impacto era reconhecimento — ninguém virava admin. Aqui o mesmo campo é escrito **pra dentro**, e o impacto é escalação verificável. Um campo, duas faces de uma categoria.

O que o impacto **não** é:

- **Não é vazamento de dados.** O `200` devolve `["clancy","alice"]` — handles, nenhum campo de registro. Nada sensível saiu do servidor; a rota admin é deliberadamente magra.
- **Não é bypass de autenticação.** O token é o mesmo token legítimo o tempo todo; nunca foi forjado, repetido nem decodificado.
- **Não é maior do que é.** O administrador deste lab consegue listar handles, e é só disso que o átomo precisa. O achado é o **acesso**, não o que está atrás da porta.

## 7. Por que o fix funciona (porta 8307)

Aponte o Burp pra API fixed em `127.0.0.1:8307` e faça login lá como `clancy` — cada build guarda o próprio mapa de tokens, então você precisa de um token novo. Então rode os **mesmos três requests**, na mesma ordem.

Primeiro a linha de base:

> `Método: GET · Alvo: /admin/users · Isola: o mesmo ponto de partida — aqui você também não é admin`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8307
Authorization: Bearer <clancy-token>
```

Response — **`403`**, corpo `Forbidden`. Igual ao build vulnerable.

Depois o write que te escalou antes:

> `Método: PATCH · Alvo: clancy (seu) · Isola: o request idêntico, a response idêntica`

```
PATCH /users/clancy HTTP/1.1
Host: 127.0.0.1:8307
Authorization: Bearer <clancy-token>
Content-Type: application/json

{"displayName": "Clancy Parked", "is_admin": true}
```

Response — **`204 No Content`**, corpo vazio. **Idêntica.** O build fixed não te dá nada pra distingui-lo: nem o status, nem o corpo, nem um header.

Depois a porta:

> `Método: GET · Alvo: /admin/users · Isola: o termômetro que não se move`

```
GET /admin/users HTTP/1.1
Host: 127.0.0.1:8307
Authorization: Bearer <clancy-token>
```

Response — **`403`**, corpo `Forbidden`.

**Mesmo write, mesmo status, efeito morto.** O handler corrigido nomeia o único campo que um caller pode setar — uma **allow-list** —, então o `displayName` que você mandou foi gravado e o `is_admin` simplesmente não fez parte do write. A feature continua funcionando; a escalação sumiu. E repare no que o fix **não** tocou: o ownership check continua respondendo `403` no `PATCH /users/alice`, token ausente ou ruim continua levando `401` com `WWW-Authenticate: Bearer`, e o `GET /admin/users` são os mesmos bytes de sempre.

A única linha entre os dois builds é o que o handler grava. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) percorre isso — por que uma allow-list (que falha fechado) é o fix e uma deny-list (que falha aberto) não é, por que o `204` é o status certo pra um write cuja resposta não deveria provar nada, e por que os outros status codes seguem o critério da série.

O walkthrough termina aqui. O achado é um flag de privilégio setado por uma atualização de perfil comum que você tinha todo o direito de fazer; o fix é uma linha, nomeando o campo que o write pode carregar.
