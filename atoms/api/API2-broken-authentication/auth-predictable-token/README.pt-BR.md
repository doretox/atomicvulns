# auth-predictable-token — Broken Authentication

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para **Broken Authentication**, o API2:2023 do OWASP API Security Top 10. A API deixa você ler o **seu próprio** perfil de conta pelo `GET /users/:handle`, atrás de uma guarda de posse — você só vê o registro com a chave do seu próprio handle, e pedir o de qualquer outro dá `403`. A autenticação é por Bearer token, emitido no `POST /login`. A falha está no token em si: ele não é um valor aleatório, é **o seu nome de usuário, codificado em base64url**. base64url é codificação reversível, não um segredo — então qualquer um que saiba o handle de outra pessoa reconstrói o token dela só a partir do nome e se autentica **como ela**.

Os sete primeiros átomos desta série fizeram, cada um, uma pergunta de **authorization** — *você pode fazer isto?* — e confiaram no token pra dizer quem "você" é. Este átomo vira o holofote pra dentro dessa premissa e faz a pergunta anterior: **você é mesmo quem diz ser?** Essa é a diferença entre **authentication** (provar *quem você é*) e **authorization** (provar *que você pode*). O alvo é o único mecanismo que os sete anteriores deixaram intocado de propósito — o token — e a pergunta de auditoria é **"o token é imprevisível pra quem não o recebeu?"** Aqui não é: o token *é* o nome.

Repare bem onde o bug **não** está. A guarda de posse do `GET /users/:handle` está correta — o `clancy`, com o próprio token, pedindo `GET /users/alice`, leva `403`. Isto **não** é um check de autorização ausente (isso seria BOLA), e você **não** rouba um token (não há nada a interceptar). Você **forja uma identidade**: constrói o token da `alice` a partir do handle público dela, manda o mesmo request com ele, e a guarda de posse — fazendo exatamente o seu trabalho — te aprova, porque o `caller` com que ela compara agora é a `alice`. A guarda que você vê está certa; a mentira entra uma camada acima, em como o token é resolvido.

> **Teoria primeiro:** Leia [PortSwigger: Authentication vulnerabilities](https://portswigger.net/web-security/authentication)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os usuários vivem num `Map` do TypeScript, cada registro com dois campos: `displayName` e `email` — o dado privado de conta que este átomo protege. Não há banco: um token previsível não depende da camada de armazenamento, porque o bug está em como o login *emite* o token e como a authentication *resolve* ele, acima de qualquer store que guarde os usuários. No build fixed um segundo mapa `token -> user` vive em memória também; o build vulnerable não guarda mapa nenhum (não tem o que guardar — ele só decodifica).

## Estado — o átomo só lê; os tokens são a única parte móvel

Este átomo **lê**: o `GET /users/:handle` nunca muda um registro de usuário, então os passos não têm ordem a respeitar e nada a zerar entre eles. A única parte móvel é o token, e os dois builds o tratam diferente no restart. `./atom down auth-predictable-token && ./atom up auth-predictable-token` esvazia o mapa de tokens do build fixed, então todo token emitido vira `401` — logue de novo. O build vulnerable **não tem estado de token pra limpar**: `base64url("alice")` é um token válido antes do restart e depois dele, pra sempre, porque nada no servidor o sustenta. Um token que o servidor nunca registrou é um que ele nunca consegue revogar.

## Só API — sem HTML, sem browser

Não há templates, página de entrada, nem UI: as respostas são JSON, ou um status seco sem conteúdo. Isso é deliberado — o que está sob teste é uma API, e este átomo não modela mais nada. Você dirige tudo pelo **Burp Suite** (Repeater pra editar e reenviar um único request) ou pelo `curl`, mais a ferramenta de linha de comando `base64` pra ler e construir tokens. Não há trilha browser; o [`WALKTHROUGH.md`](./WALKTHROUGH.md) trabalha exclusivamente do Burp.

## Autenticação simulada — e é aqui que o bug vive

`POST /login` recebe um username e devolve um Bearer token. Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade** — não confunda os dois. O login passwordless é cenário; a falha é o **formato do token que o login devolve**. No build vulnerable, `issueToken("clancy")` é `Buffer.from("clancy").toString("base64url")` — o nome, codificado, sem aleatoriedade e sem nada guardado. A authentication então *decodifica* o token e confia no nome que ele soletra. Então a authentication aqui **não** prova quem você é: qualquer um que soletre um handle apresenta o token daquele handle.

Contraste com todos os átomos anteriores da série, onde o token era cripto-forte (`randomBytes`), emitido pelo servidor, e o ataque nunca o tocava. Aqui o ataque é *só* o token. O build fixed restaura o token real da série: um valor aleatório e opaco que o servidor guarda no login e resolve por lookup, sem identidade nenhuma dentro dele pra forjar.

## Usuários e registros

Dois usuários são seedados, cada um dono de exatamente um registro — o da chave do próprio handle:

- `clancy` — o atacante (você). Você loga como `clancy`, lê o próprio perfil pro baseline, e então forja a `alice`.
- `alice` — a vítima impersonada. O token dela **nunca é emitido pra você**; você o constrói a partir do handle dela. Ela nunca loga.

Cada registro tem `displayName` (`"Clancy Park"`, `"Alice Nguyen"` no seed) e `email` — `clancy@mail.example` e `alice@secret.example`, domínios `.example` reservados, sem dado real. O `email` é o dado privado: o dono pode lê-lo, ninguém mais devia alcançá-lo, e o email da `alice` chegando na *sua* resposta é a prova. **Não há `is_admin` nem senha** nesses registros — este átomo é sobre *quem é o chamador*, não que papel ele tem.

## Duas rotas, nada mais

- `POST /login` — body `{"user":"<nome>"}`, devolve `{"token":"<token>"}`; usuário desconhecido leva `400`. O handler é byte-idêntico nos dois builds; só o `issueToken` que ele chama difere.
- `GET /users/:handle` — ler um perfil. Autentica o chamador, confere a posse (`403` pro registro de qualquer outro), e devolve `{"handle", "displayName", "email"}`. Esta rota é **byte-idêntica nos dois builds**: a guarda de posse está correta, e **não** é o bug. O que difere entre os builds é só quem o `authenticate` diz que o chamador é.

Não há `GET /me`, nem rota admin, nem `PATCH`, nem listagem de usuários. Duas rotas é a superfície inteira: uma pra pegar um token, uma pra ler um perfil atrás de uma guarda de posse correta.

## Como rodar

Da raiz do repo:

```bash
./atom up auth-predictable-token
```

- API vulnerable: `http://127.0.0.1:8208`
- API fixed: `http://127.0.0.1:8308`

Não há página de entrada — o ponto de partida é o `POST /login` (ver [`WALKTHROUGH.md`](./WALKTHROUGH.md)). Pare com `./atom down auth-predictable-token`. Se preferir Docker cru: `cd atoms/api/API2-broken-authentication/auth-predictable-token && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.md`](./WALKTHROUGH.md) — exploração passo a passo via Burp Suite (API-only; sem trilha browser).
2. [`DIFF.md`](./DIFF.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8308 serve a mesma rota de perfil contra o mesmo seed, e muda o **bloco de autenticação**: o login emite um token aleatório e opaco (`randomBytes(24)`) e **guarda** o vínculo `token -> user`, e o `authenticate` o resolve por **lookup** em vez de decodificá-lo. Reproduza o walkthrough contra ela e a forja morre na porta: `base64url("alice")` agora responde `401`, porque essa string nunca foi emitida e o servidor não a reconhece — o token não diz mais quem você é, só o registro do servidor diz. O seu self-read continua `200`, o `403` de posse e o `401` de token ausente não mudam. O [`DIFF.md`](./DIFF.md) trabalha por que a identidade não pode viajar dentro do token de jeito nenhum — e por que *assinar* o token (o quase-fix tentador) resolve o problema errado.
