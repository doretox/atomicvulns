# bopla-excessive-exposure — Broken Object Property Level Authorization (BOPLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BOPLA (Broken Object Property Level Authorization), o API3:2023 do OWASP API Security Top 10, na sua **face de leitura** — o que a indústria chama de *excessive data exposure*. A autorização se aplica no nível das **propriedades** de um objeto, não só do objeto como um todo. A API deixa você ler o **seu próprio** perfil pelo `GET /users/:handle`, e confere a posse corretamente — você só lê o registro com a chave do seu próprio handle. Mas o handler então serializa o **objeto inteiro** guardado, então dois campos server-side que você nunca deveria ver — `passwordHash` e `is_admin` — voltam na resposta ao lado do único campo público, `displayName`.

A lição é que **estar autorizado para um objeto não é estar autorizado para cada campo dele**. Você tem todo o direito a este registro — é seu — e a resposta ainda assim te entrega propriedades que você não pode ver. Então a pergunta de auditoria aqui é **"a resposta devolve só os campos que este chamador pode ver?"**, não "de quem é o objeto?" (isso é BOLA) nem "você pode invocar esta operação?" (isso é BFLA). Leia como BOLA e você procura no lugar errado: você está lendo o **seu próprio** registro, e o `GET` do registro de outra pessoa é corretamente recusado com `403`. O check de objeto está presente e funciona; a falha mora uma linha abaixo dele, na serialização.

Este é o primeiro átomo da série no grão da **propriedade**. Os três átomos de API1 — `bola-sequential-id`, `bola-uuid-leaked`, `bola-nested-resource` — giravam em torno do **objeto** (*de quem é este objeto?*). Os dois de API5 — `bfla-admin-function`, `bfla-method-based` — giravam em torno da **função/operação** (*você pode invocar isto? / a autorização cobre todos os métodos?*). Este desce um grão a mais, até o **campo**. Ele também inverte o irmão `bfla-method-based`: lá o handler `GET /users/:handle` era a *prova viva* de um ownership check correto; aqui o mesmíssimo `GET`, com a mesma guarda de posse ainda em cima, é o vulnerável — a falha é nova e mora abaixo da guarda, no que a resposta serializa.

> **Teoria primeiro:** Leia [PortSwigger: Information disclosure vulnerabilities](https://portswigger.net/web-security/information-disclosure)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os usuários vivem num `Map` de TypeScript, cada registro guardando três campos: `displayName` (público), `passwordHash` e `is_admin` (ambos server-side). Não há banco: BOPLA não depende da camada de storage, porque o bug está no que o handler *serializa* acima de qualquer store que guarde os registros — então o store fica mínimo e o vazamento fica óbvio. O mapa `token -> user` também é em memória.

## Estado — somente leitura, nada muda

Ao contrário dos dois átomos de BFLA, cujo endpoint atacado escrevia, este átomo só **lê**: o `GET /users/:handle` nunca muta nada. Todo request é idempotente e determinístico, e nenhum passo depende da ordem de outro. O mapa `token -> user` cresce a cada login, mas os perfis nunca mudam. O `./atom down bopla-excessive-exposure && ./atom up bopla-excessive-exposure` limpa os tokens emitidos (faça login de novo); os perfis seedados são os mesmos de todo jeito.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: toda resposta de sucesso é JSON. É proposital — a coisa sob teste é uma API, e este átomo não modela nada além disso. Você opera tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente no Burp. Isso importa pra lição: num app real uma UI poderia esconder esses campos da tela, mas a filtragem tem que ser server-side — o raw da resposta é o que um pentester lê, e aqui não há UI nenhuma.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pra um usuário, tipo um OAuth2 opaque access token ou uma session id server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**; e o `passwordHash` em cada registro é **dado dummy stored-side, nunca lido pelo login e não é uma credencial real**.

O que o atalho *não* faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` com um challenge `WWW-Authenticate: Bearer`, no build vulnerable exatamente como no fixed. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. O que falta não é autenticação, e nem o ownership check; é a filtragem no nível da propriedade na resposta.

## Usuários e registros

Dois usuários no seed, cada um dono de exatamente um registro — o que tem a chave do próprio handle:

- `clancy` — o atacante (você). Dono do registro `clancy`, o que você lê no exploit.
- `alice` — existe só pra fazer o `GET /users/alice` dar `403`, provando que o ownership check funciona. O registro dela nunca é lido com sucesso no walkthrough.

Cada registro guarda três campos: `displayName` (`"Clancy Park"`, `"Alice Nguyen"` no seed) — público; `passwordHash` — uma string dummy bcrypt-shaped, server-side; e `is_admin` — um flag de role interno, **`false` pros dois**. Não há role de admin neste átomo: o ponto é que os campos internos voltem *de todo jeito*, não que algum valor seja especial.

## Duas rotas, nada mais

- `POST /login` — corpo `{"user":"<name>"}`, devolve `{"token":"<opaque>"}`; usuário desconhecido leva `400`.
- `GET /users/:handle` — lê um perfil. Um ownership check devolve o registro só pro dono (`403` pro de qualquer outro). O build **vulnerable** então serializa o objeto inteiro, então a resposta inclui `passwordHash` e `is_admin`; o build **fixed** serializa uma allow-list, então devolve só `{"handle":"<handle>","displayName":"<value>"}`.

Não há `PATCH`, nem rota de listagem, nem `GET /me`. Um ponto que vale dizer com todas as letras: a self-read vulnerable é ao mesmo tempo o baseline e o exploit — você pede o seu próprio perfil, totalmente autorizado, e os campos internos já estão no corpo. A prova não precisa de segundo ator nem de segundo request.

## Como rodar

Da raiz do repo:

```bash
./atom up bopla-excessive-exposure
```

- API vulnerable: `http://127.0.0.1:8206`
- API fixed: `http://127.0.0.1:8306`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bopla-excessive-exposure`. Se preferir Docker cru: `cd atoms/api/API3-broken-object-property-level-authz/bopla-excessive-exposure && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8306 atende a mesma rota de perfil contra o mesmo seed, e muda **uma linha: o que a resposta serializa**. Em vez de espalhar o objeto inteiro guardado, o handler nomeia os campos que o chamador pode ver — uma **allow-list** (whitelist). Replay o walkthrough contra ela: o `GET /users/clancy` com o seu próprio token continua devolvendo `200`, mas o corpo agora é exatamente `{"handle":"clancy","displayName":"Clancy Park"}` — `passwordHash` e `is_admin` sumiram. O ownership check e o `401` estão inalterados: o `GET /users/alice` com o seu token continua levando `403`, e token ausente ou ruim continua levando `401`. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) trabalha o porquê de uma allow-list (que falha fechado) ser o fix e uma deny-list (que falha aberto) não ser.
