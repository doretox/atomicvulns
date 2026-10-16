# bopla-mass-assignment — Broken Object Property Level Authorization (BOPLA)

> ⚠️ Intentionally vulnerable. Run locally only. Never expose to the internet or a shared network.

Uma API REST mínima em TypeScript/Express para BOPLA (Broken Object Property Level Authorization), o API3:2023 do OWASP API Security Top 10, na sua **face de escrita** — o que a indústria chama de *mass assignment* (ou *auto-binding*). A autorização se aplica no nível das **propriedades** de um objeto, não só do objeto como um todo. A API deixa você atualizar o **seu próprio** perfil pelo `PATCH /users/:handle`, e confere a posse corretamente — você só escreve no registro com a chave do seu próprio handle. Mas o handler então mescla o **corpo inteiro da requisição** nesse registro, então uma chave que o formulário de perfil nunca ofereceu — `is_admin` — é gravada com a mesma facilidade da que ele ofereceu, `displayName`.

A lição é que **estar autorizado para um objeto não é estar autorizado a setar cada campo dele**. Você tem todo o direito de editar este registro — é seu — e o write ainda assim aceita uma propriedade que você nunca teve permissão de controlar. Então a pergunta de auditoria aqui é **"o write é escopado aos campos que este chamador pode setar?"**, não "de quem é o objeto?" (isso é BOLA) nem "você pode invocar esta operação?" (isso é BFLA). A prova deliberadamente **não** é a resposta do próprio write: o `PATCH` responde `204 No Content` nos **dois** builds, sem nada no corpo que se possa confundir com evidência. Quem prova a escalação é a leitura do estado por outra porta — `GET /admin/users`, uma rota admin-only **corretamente guardada**, que responde `403` antes do write e `200` depois dele.

Este é o segundo átomo no grão da **propriedade**, e o espelho do irmão `bopla-excessive-exposure`. Lá, o pecado espalhava o registro guardado **na resposta** (`...user` saindo); aqui ele espalha o corpo da requisição **no registro** (`...req.body` entrando). Mesma raiz — confiar num objeto inteiro — em duas direções, que é exatamente por que a OWASP mantém o lado da leitura e o da escrita numa categoria só.

> **Teoria primeiro:** Leia [PortSwigger: Mass assignment vulnerabilities](https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.

## Nota de stack — store em memória, sem banco

Os usuários vivem num `Map` de TypeScript, cada registro com dois campos: `displayName` (o único campo que um usuário pode editar) e `is_admin` (um flag de role interno que decide quem pode chamar a rota admin). Não há banco: mass assignment não depende da camada de armazenamento, porque o bug está em como o handler *monta o objeto que grava*, acima de qualquer store que guarde os registros. O mapa `token -> user` também é em memória.

## Estado — este átomo escreve, e a ordem importa

Diferente do irmão do lado da leitura, este átomo **muda estado**: o `PATCH /users/:handle` reescreve o registro. Isso tem duas consequências pra quem vai percorrê-lo. Primeira: os passos têm ordem — a rota admin responde `403` **antes** do write e `200` **depois** dele, e essa transição **é** a prova, então pedi-la tarde demais custa a linha de base. Segunda: nada é permanente — `./atom down bopla-mass-assignment && ./atom up bopla-mass-assignment` restaura o seed: o `is_admin` forjado volta pra `false` (a rota admin responde `403` de novo) e os tokens emitidos somem (faça login de novo). Cada gêmeo guarda o próprio seed, então um write na 8207 é invisível na 8307.

## Só API — sem HTML, sem browser

Não há templates, não há landing page, não há UI: as respostas são JSON, ou um status seco sem conteúdo. Isso é deliberado — o que está sob teste é uma API, e este átomo não modela mais nada. Você dirige tudo pelo **Burp Suite** (Repeater pra editar e reenviar um request único) ou pelo `curl`. Não há trilha browser; o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) trabalha exclusivamente do Burp.

## Autenticação simulada

O `POST /login` recebe um nome de usuário e devolve um **Bearer token opaco** — um valor aleatório que o servidor guarda e resolve de volta pro usuário, como um access token opaco de OAuth2 ou um id de sessão server-side, e explicitamente *não* um JWT (não há nada codificado dentro dele pra ler ou adulterar). Ele não pede **senha, e isso é um atalho deliberado do laboratório, não a vulnerabilidade**.

O que o atalho **não** faz é enfraquecer a autenticação. A autenticação aqui **é imposta**: token ausente, malformado ou desconhecido leva `401` com um challenge `WWW-Authenticate: Bearer`, no build vulnerable exatamente como no fixed. O token é cripto-forte (`randomBytes`), genuinamente emitido pelo servidor, e o ataque nunca o decodifica, altera ou forja — ele fica válido e seu do primeiro ao último request. Esse detalhe pesa aqui: a sua **identidade** nunca muda durante o exploit. O que muda é o **estado** que o servidor lê quando decide se você é administrador.

## Usuários e registros

Dois usuários são seedados, cada um dono de exatamente um registro — o que tem a chave do próprio handle:

- `clancy` — o atacante (você). Dono do registro `clancy`, o que ele edita no exploit.
- `alice` — existe só pra fazer do `PATCH /users/alice` um `403`, provando que o ownership check funciona. O registro dela nunca é escrito no walkthrough, e ela nunca faz login.

Cada registro guarda dois campos: `displayName` (`"Clancy Park"`, `"Alice Nguyen"` no seed) — o único campo que uma atualização de perfil deveria setar; e `is_admin` — um flag de role interno, **`false` para os dois**. **Nenhum administrador é seedado.** É esse o ponto: o único admin que este lab chega a ter é o que o bug cria.

## Três rotas, nada mais

- `POST /login` — corpo `{"user":"<nome>"}`, devolve `{"token":"<opaco>"}`; usuário desconhecido leva `400`.
- `PATCH /users/:handle` — atualiza um perfil. Um ownership check deixa você escrever só no seu próprio registro (`403` no de qualquer outro). O build **vulnerable** então mescla o corpo inteiro da requisição no registro, então `{"is_admin":true}` é gravado; o build **fixed** grava uma allow-list de um campo, então o mesmo corpo não muda nada além do display name. Os dois respondem `204 No Content`.
- `GET /admin/users` — admin-only, read-only, e **byte-idêntica nos dois builds**. Ela lê a role do chamador no store e devolve a lista de handles, ou `403` pra quem não é admin. Esta rota **não** é o bug: a guarda dela está correta, e ela é o instrumento que prova se o write pegou.

Não existe `GET /users/:handle`, nem listagem pública de usuários, nem `GET /me` — a única janela para o estado é aquela porta administrativa, e isso é de propósito: o que importa não é ver o campo, é ver o que o campo **faz**. Também não existe endpoint de promoção; nada nesta API deveria conceder a role de admin.

## Como rodar

A partir da raiz do repo:

```bash
./atom up bopla-mass-assignment
```

- API vulnerable: `http://127.0.0.1:8207`
- API fixed: `http://127.0.0.1:8307`

Não há landing page — o ponto de entrada é o `POST /login` (veja o [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md)). Pare com `./atom down bopla-mass-assignment`. Se preferir Docker cru: `cd atoms/api/API3-broken-object-property-level-authz/bopla-mass-assignment && docker compose up --build`.

## O que ler a seguir

1. [`WALKTHROUGH.pt-BR.md`](./WALKTHROUGH.pt-BR.md) — exploração passo a passo via Burp Suite (só API; sem trilha browser).
2. [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) — diff comentado entre `vulnerable/` e `fixed/`.

## Versão fixed

A API corrigida na porta 8307 serve a mesma rota de perfil contra o mesmo seed, e muda **uma linha: o que o handler grava**. Em vez de mesclar o corpo inteiro da requisição no registro, ela nomeia o único campo que o chamador pode setar — uma **allow-list** (whitelist). Repita o walkthrough contra ela e o impressionante é o quão pouco a superfície muda: o `PATCH /users/clancy` com `{"displayName":"Clancy Parked","is_admin":true}` continua respondendo `204 No Content` com corpo vazio — *a resposta idêntica* — e o seu display name é realmente atualizado. Mas o `GET /admin/users` continua respondendo `403`, porque o `is_admin` do seu corpo nunca foi gravado. Mesmo write, mesmo status, efeito morto. O ownership check e o `401` também não mudaram. O [`DIFF.pt-BR.md`](./DIFF.pt-BR.md) percorre por que uma allow-list (que falha fechado) é o fix e uma deny-list (que falha aberto) não é.
