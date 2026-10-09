# Spec — Átomo API 04: `bfla-admin-function`

> Documento de especificação para o Claude Code implementar o **quarto átomo da série API** do projeto `atomicvulns` (Fase 1 API, "Authorization: Object & Function", milestone `v1.1`; **não** fecha a fase). Classe: **BFLA — Broken Function Level Authorization**, o **API5:2023** do OWASP API Security Top 10 (2023). É a **primeira categoria nova da série** — a pasta `API5-broken-function-level-authz/` nasce aqui. Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **Este átomo vira a página da série.** Os três primeiros (01–03) eram todos **API1 — BOLA**, e todos perguntavam sobre a **instância** — o que muda entre eles é contra o que ela é confrontada: o dono (*é este objeto seu?*, 01/02) ou o pai autorizado (*é desta loja?*, 03). É o eixo do objeto nos três. Este troca de eixo, para a capacidade, e pergunta outra coisa: *você pode invocar esta operação, qualquer que seja o objeto?* BOLA protege **instâncias**; BFLA protege **capacidades**. Tudo o que esta spec afirma sobre os átomos 01–03 foi conferido **lendo os arquivos publicados nesta fase**, não de memória (ver "Verificação factual dos átomos publicados").
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **`atoms/api/API1-broken-object-level-authz/bola-sequential-id/`, inteiro** — átomo-bandeira e referência de estilo da série: fonte da verdade do toolchain (§3.6), do bloco de auth, do padrão de `app.ts`/`Dockerfile`/`docker-compose.yml` e da forma dos seis documentos.
> 2. **`atoms/api/API1-broken-object-level-authz/bola-uuid-leaked/` e `bola-nested-resource/`, inteiros** — as outras duas voltas de BOLA. O 02 é o precedente de um átomo que **começa de premissa declarada** (o id vazado); o 03 é o precedente de um fix que **não repete** o dos anteriores. Os dois são publicados e **citáveis**.
> 3. Átomos web de A01 (`idor-numeric-id`, `bola-rest`, `idor-uuid-guessable`) — leitura opcional; todos são horizontais (IDOR/BOLA). Nenhum é vertical/BFLA, então não há gêmeo web desta classe pra creditar.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Identidade

- **ID:** `bfla-admin-function`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API5 — Broken Function Level Authorization**
- **Pasta:** `atoms/api/API5-broken-function-level-authz/bfla-admin-function/` — **primeira categoria nova da série**; a pasta `API5-*` nasce com este átomo.
- **Número sequencial (série API, conta do 01):** 04
- **Porta vulnerable:** `127.0.0.1:8204`
- **Porta fixed:** `127.0.0.1:8304`
- **Porta interna do container:** `3000` (igual a 01–03). Compose mapeia `127.0.0.1:8204:3000` e `127.0.0.1:8304:3000`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1); `ENV HOST=0.0.0.0` só dentro do container.
- **Fase / milestone:** Fase 1 API, `v1.1` (quarto átomo; **não** fecha a fase — o átomo 05 `bfla-method-based` fecha).
- **Branch de trabalho:** `atom/bfla-admin-function` — criada nesta fase a partir de `main` atualizada.
- **H1 dos READMEs (idêntico em EN e PT):** `# bfla-admin-function — Broken Function Level Authorization (BFLA)`. O título nomeia a **classe**; o slug qualifica a variante (CLAUDE.md §5). **Primeiro H1 da série que não é BOLA** — de propósito; a troca de categoria é a lição.
- **Theory primer:** ver seção "Theory primer" (URL verificada por fetch nesta fase — HTTP 200, sem redirect).

---

## A tese do átomo

> **Autenticação prova quem chama; não prova que o chamador pode executar esta função.** O servidor resolve a identidade do Bearer (token ruim → `401`) e então executa uma operação que **só admin deveria alcançar**, sem nunca verificar o **papel** do chamador. BOLA protegia a *instância* ("este pedido é seu?"); BFLA protege a *capacidade* ("você pode promover **alguém**, qualquer que seja o alvo?").

### O eixo mudou — e isso é a lição inteira

Os átomos 01–03 giravam todos em torno do **objeto**: qual pedido você consegue ler. A pergunta de auditoria deles era sobre o objeto — *"cadê o check de dono do objeto?"* (01/02), *"o objeto é do pai autorizado?"* (03). Aqui a pergunta de auditoria é outra: **"onde este endpoint confere que o chamador pode invocar esta função?"** — e a resposta, no `vulnerable/`, é *em lugar nenhum*. Não há objeto alheio sendo lido; há uma **operação privilegiada** sendo executada por quem não tem o papel pra ela. É **escalação vertical de privilégio** (ganhar uma capacidade de nível mais alto), não horizontal (ler o objeto de um par).

### O erro de leitura a combater — e ele determina o desenho

BFLA é fácil de confundir com BOLA **quando o endpoint admin devolve objetos**: o aluno vê dado alheio saindo e conclui "li o que não era meu", que é raciocínio de **objeto** — exatamente o que os três átomos anteriores ensinaram. Se este átomo tivesse uma função admin que **lê** o registro de outra pessoa, o aluno aplicaria o reflexo de BOLA e não veria a categoria nova.

Por isso **a escolha da função admin é o que determina se o átomo ensina a categoria certa**, e a escolha é dura:

> **A função admin deste átomo MUDA ESTADO e NÃO devolve dado alheio.** Promover um usuário a administrador muda o servidor; a resposta carrega só **o que a operação gravou** (o papel do alvo, `true` literal), não o registro privado de terceiro. Assim não há "dado alheio saindo" pra o aluno interpretar como leitura de objeto. O que prova o sucesso do ataque é **a função admin executar pra um não-admin** (o `200`, que só sai depois da escrita), não um corpo de resposta com PII — a mudança de estado em si é real mas inobservável pela API (ver "Estado mutável").

Registrar essa justificativa **no DIFF e no WALKTHROUGH**: a função foi escolhida *mudança de estado, não leitura* justamente pra isolar o eixo da capacidade do eixo do objeto.

### Por que API5 (Broken Function Level Authorization)

O bug **não é** "input virou código" (injection) nem "um request legítimo alcançou um objeto fora do escopo" (BOLA). É **"um request legítimo invocou uma função fora do nível de privilégio do chamador"** — o chamador não é admin e a API executou uma função admin mesmo assim. Isso é controle de acesso **no nível da função**: **API5** no OWASP API Security Top 10 **2023**. Situe nessa edição, **sem arqueologia** de edições antigas (CLAUDE.md §5). Referência OWASP em **texto simples** (`API5:2023`), **sem link** — o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (template, seção "Theory primer"). Por ser vuln de **lógica/autorização** (Trigger, não Payload), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório (ver "Walkthrough").

---

## O que este átomo acrescenta (vs. 01–03)

**Honestidade pedagógica:** 01–03 já ensinaram o núcleo de BOLA (autenticado ≠ autorizado; no 01 e no 02, o handler que chama `authenticate()` e não toma decisão de acesso nenhuma sobre o pedido; no 03, o handler que toma uma decisão de acesso de verdade — `403` pra loja que o chamador não opera — e mesmo assim busca o pedido na coleção global, sem conferir que ele pertence à loja autorizada; o fix por objeto). Este átomo **credita e não reabre** nada disso. Ele existe por quatro eixos novos:

1. **Primeira categoria nova da série.** Sai de API1 (objeto) e entra em API5 (função). A pasta `API5-*` nasce aqui. A troca de eixo — *instância* vs *capacidade* — é a razão de ser do átomo, e o contraste com os três anteriores **é** o material.
2. **Escalação VERTICAL, não horizontal.** 01–03 liam o objeto de um par (mesmo nível). Aqui o chamador **ganha um privilégio mais alto**. Primeiro átomo vertical do repo.
3. **A função MUDA ESTADO.** Primeiro átomo da série cujo **endpoint atacado escreve** — nos anteriores, o endpoint atacado era um `GET` de leitura (`GET /orders/:id` no 01 e no 02, `GET /stores/:storeId/orders/:orderId` no 03); o `POST /login`, que os três também têm, grava um token no mapa em memória, mas não é a superfície do bug. A prova não é um corpo de resposta com dado alheio; é a função admin **aceitar** a chamada de um não-admin (`200`) — a escrita é real, mas inobservável pela API (ver "Estado mutável" e "Prova de impacto"). Isso é o que mantém o átomo longe do reflexo de BOLA.
4. **O check presente é de identidade, não de papel.** O handler vulnerável *autentica* (um `401` real) — então *parece* que cuida de acesso. O que falta é a camada acima: a verificação do **papel**. É a mesma armadilha do revisor apressado dos átomos anteriores ("tem auth, tá ok"), aplicada ao eixo da função.

> **Contraste a cravar (WALKTHROUGH e DIFF):** em BOLA o handler sabia quem você era e não checava **de quem é o objeto**; em BFLA o handler sabe quem você é e não checa **o que você tem direito de fazer**. Mesma raiz (identidade conhecida, decisão de acesso ausente), eixo diferente (objeto vs operação).

---

## Feature simulada — administração de papéis (API-only, sem HTML)

**Console de administração de uma plataforma multiusuário.** A plataforma tem usuários comuns (members) e administradores. Entre as tarefas de um admin está **promover um usuário comum a administrador** — conceder o papel de admin a outra conta. Do ponto de vista do produto, "só admin promove admin"; o endpoint de promoção é uma função do console administrativo. O que o dev esqueceu foi conferir que **quem chama a função é admin**.

**API-only por natureza** (CLAUDE.md §3.3 — a série API é API-only): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`; erros via `res.sendStatus(...)` (igual a 01–03). Requests com corpo JSON no `POST /login`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl** (ver "Walkthrough").

---

## De onde vem o endpoint admin — descoberta DECLARADA, não simulada

**A descoberta do endpoint é premissa declarada do enunciado, em uma frase — não um passo do ataque.** Em BFLA do mundo real a descoberta **quase nunca é o difícil**: o caminho admin segue convenção de nomes previsível (`/admin/...`), a especificação OpenAPI costuma ser pública, e o bundle do front-end carrega caminhos de telas que o usuário comum jamais vê. Fingir que achar o endpoint é o desafio **distorceria a classe** — o trabalho do atacante em BFLA é *invocar* a função, não *encontrá-la*.

Restrição dura de design, idêntica em espírito à do átomo 02 (um bug só):

- **NADA na aplicação "revela" o endpoint como parte do ataque.** Sem endpoint de descoberta, sem índice de rotas, sem erro que confirme a existência de um caminho (isso seria **information disclosure**, um segundo bug). O endpoint simplesmente **é conhecido** — o README e o WALKTHROUGH o apresentam de saída, como um fato do ambiente.
- **O único bug é o check de papel ausente** no `POST /admin/users/:handle/promote`. A superfície não tem mais nada a mais (ver "Rotas").

**Segunda vez na série que um átomo começa de premissa declarada — e a diferença fica escrita.** No átomo 02 (`bola-uuid-leaked`, publicado) a premissa declarada — o UUID que vazou de fora — **era a própria lição** (o id não-adivinhável não conserta nada). Aqui a premissa declarada — o endpoint é conhecido — é **economia**, não lição: ela remove um passo que em BFLA real não existe, pra o átomo gastar seu tempo no que importa (a invocação sem papel). Registrar essa distinção no corpo do átomo (uma ou duas frases), creditando o 02 por nome (publicado).

**Requisito de README (EN+PT):** uma frase declara, logo na abertura, que **o caminho admin é conhecido** (convenção de nomes, OpenAPI frequentemente público, caminhos no bundle do front) e que **a descoberta não é a vulnerabilidade — a invocação sem papel é**. Texto sugerido (a Fase 2 ajusta a prosa, não o sentido):

> **EN:** *The admin path here is simply known — admin routes follow predictable names, the OpenAPI spec is often public, and the front-end bundle ships paths for screens a regular user never sees. In real BFLA, finding the endpoint is almost never the hard part, so this atom declares it rather than staging a discovery. The vulnerability is not that the path is reachable; it is that invoking the function never checks your role.*
>
> **PT:** *O caminho admin aqui é simplesmente conhecido — rotas admin seguem nomes previsíveis, a spec OpenAPI costuma ser pública, e o bundle do front-end carrega caminhos de telas que um usuário comum nunca vê. Em BFLA real, achar o endpoint quase nunca é o difícil, então este átomo o declara em vez de encenar uma descoberta. A vulnerabilidade não é o caminho ser alcançável; é a invocação da função nunca checar o seu papel.*

---

## Autenticação — token opaco, cripto-forte (mesmo mecanismo de 01–03)

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados e devolve `{ "token": "<opaco>" }`. Mapa `token → usuário` **em memória**, resolvido por lookup. **NÃO é JWT.** Os helpers de auth (imports, `TOKENS`, `issueToken`, `authenticate`) são **byte a byte** os de 01–03 (conferido: linhas 1–23 dos três `app.ts` publicados são idênticas, md5 batendo) — **copiar, não reescrever**. Token com `randomBytes(24).toString("base64url")`: um token previsível seria uma segunda vulnerabilidade e violaria "um átomo = uma vuln" (CLAUDE.md §2). O ataque **não toca** o token.

**Uma mudança estrutural obrigatória — e é a única que a classe exige.** Em 01–03, `USERS` é um `Set<string>` (a identidade é só o handle). BFLA precisa que o usuário **carregue um papel**, então `USERS` passa de `Set` a um **`Map<string, User>`** onde `User = { is_admin: boolean }`. Essa é a mudança mínima que a categoria pede (o papel tem que morar em algum lugar) — registrar no DIFF que **não é um eixo novo de bug**, é o dado que a autorização por função compara, análogo ao `order.owner` de 01/02 e ao `STORES[...].operators` de 03. Tudo o mais do bloco de auth é idêntico.

> **Por que `Map`, e não `Record` — o `Map` é o que impede uma SEGUNDA vuln (prototype pollution). Ver a seção "Store / dados".** Resumo: a função deste átomo **escreve** através de um lookup por chave-string vinda do path (`:handle`), e um objeto literal (`Record`) tem `Object.prototype` na cadeia; `Map.get()` não. A escolha de `Map` resolve o problema **estruturalmente** (não com uma guarda extra) e, de quebra, devolve o `POST /login` à forma de 01–03 (`USERS.has(user)`).

**O que a auth prova e o que NÃO prova (deixar explícito — é a lição):**

- **Autenticação prova *quem você é*.** Token ausente/ruim → `401`, no `vulnerable/` exatamente como no `fixed/`.
- **O papel (`is_admin`) é *o que você tem direito de fazer*.** No `vulnerable/`, a função admin **nunca consulta** esse papel; no `fixed/`, consulta. Essa é a única diferença entre os gêmeos.

**Usuários seedados (elenco da série — CLAUDE.md §5):**

- **`clancy`** — o **atacante** (você). Usuário **comum** (`is_admin: false`). É `clancy` que promove, sem nunca ter sido admin. (Elenco da série API: `clancy` é masculino; nos docs PT, "o atacante", "você mesmo", "dele". Como o masculino do **papel** — "o chamador", "o admin" — também é masculino, a concordância da pessoa e a do papel coincidem; não há distinção pessoa-vs-papel a manter.)
- **`alice`** — a **vítima principal** (`is_admin: false`): é a conta que `clancy` promove no exploit.
- **`bob`** — usuário comum (`is_admin: false`), com uma função só: o **alvo da promoção legítima da `carol` no `fixed/`** (o caminho positivo do fix). Fica fora do exploit de propósito, pra a promoção que passa (`carol` → `bob`) não cair no alvo que o fix acabou de recusar (`clancy` → `alice`).
- **`carol`** — a **única administradora do seed** (`is_admin: true`). Existe por um motivo estrutural: sem um admin legítimo, o `fixed/` não teria como mostrar a função **funcionando pra quem pode** (carol promove → `200`). É o caminho positivo do fix.

**Por que há um admin no seed, e por que é a `carol`.** O `fixed/` precisa provar duas coisas: que um não-admin é **recusado** (`clancy` → `403`) e que um admin **passa** (a função não quebrou). O segundo exige um admin seedado. A `carol` (já do elenco de 03 como operadora) assume o papel aqui — reuso de elenco, não personagem novo. `clancy` e `alice` ficam **comuns** de propósito: o atacante tem que ser comum pra a escalação ser escalação, e o alvo tem que ser alguém que o `clancy` **não teria direito de promover** — uma conta comum, à qual a promoção concede um papel que ela não tem. Se a `alice` já fosse admin, a promoção seria no-op e o exploit perderia o sentido. É sobre a chamada ser **ilegítima**, não sobre o efeito ser visível (pela API ele não é — ver "Estado mutável").

**Requisito de README (EN+PT) — declarar o atalho:** o login sem senha é um **atalho deliberado do laboratório, não a vulnerabilidade**, e a autenticação em si **é imposta** (token ruim → `401`). Uma frase, **sem citar átomo** (mesmo requisito de 01–03).

---

## Store / dados — usuários com papel, em memória

**Sem banco** (CLAUDE.md §3.4). Estruturas TS. O `TOKENS` cresce a cada login; o `USERS` tem o papel de cada um e **muda em runtime** quando uma promoção acontece (ver "Estado mutável").

```ts
// --- Simulated identity: an opaque, server-side token; users carry a role ---
// is_admin is the capability axis this atom is about. Promoting a user to admin is an
// admin-only function. clancy (you) is a plain member; carol is the one seeded admin,
// so the fixed build has a legitimate caller to show the function still works.
// A Map, not a plain object: Map.get() never walks the prototype chain, so a :handle of
// "__proto__" or "constructor" is just an unknown user -- never Object.prototype.
type User = { is_admin: boolean };
const USERS = new Map<string, User>([
  ["clancy", { is_admin: false }],   // attacker (you) -- a plain member
  ["alice",  { is_admin: false }],   // primary victim -- promoted in the exploit
  ["bob",    { is_admin: false }],   // target of carol's legitimate promotion in the fixed build
  ["carol",  { is_admin: true  }],   // the one legitimate administrator
]);
```

- **`is_admin: boolean` é a representação do papel** — o dado que a autorização por função compara, análogo ao `order.owner` (01/02) e ao vínculo operador→loja (03). Dado fake óbvio, sem PII (handles de login, não pessoas com nome/endereço).
- **Um admin no seed (`carol`).** O exploit no `vulnerable/` grava `is_admin: true` na `alice` e no próprio `clancy`, mas **nenhum passo lê essas escritas de volta** — no `vulnerable/` o `is_admin` é só escrito, nunca lido. Ver "Estado mutável" e "Prova de impacto".
- **Nenhum outro campo.** O usuário não tem nome, e-mail, endereço — nada que um `GET` pudesse "vazar". Isso é deliberado: **não há dado alheio pra confundir com leitura de objeto** (ver "A tese do átomo").

### Por que `Map`, e não `Record` — o `:handle` abre prototype pollution

**Decisão do mantenedor, e a razão tem que ficar escrita.** A função admin **escreve** através de um lookup por chave-string vinda do path (`USERS.get(req.params.handle)`, depois `target.is_admin = true`). Se `USERS` fosse um **objeto literal** (`Record`), esse lookup seria `USERS[req.params.handle]` — e o objeto literal traria `Object.prototype` na cadeia de protótipo, e isso abriria uma **segunda classe de vulnerabilidade** — **prototype pollution**, que tem átomo web dedicado neste repo:

- `POST /admin/users/__proto__/promote` faz `USERS["__proto__"]` devolver `Object.prototype`, que é **truthy** — a guarda `!target` **NÃO pega** — e a linha seguinte executa `Object.prototype.is_admin = true`. A partir daí **todo objeto do processo** sem `is_admin` próprio herda `true`. Não é teórico: o parâmetro é string vinda do path, e um aluno curioso tenta `__proto__` justamente por isso. (`constructor` cai na mesma armadilha: `USERS["constructor"]` é truthy e recebe a escrita.) **Validado no protótipo desta fase** (ver "Validação de typecheck e runtime").
- Isso violaria "um átomo = uma vuln" (CLAUDE.md §2) — o átomo é de BFLA, não de prototype pollution.

**Por que o risco só aparece AGORA, e não em 01–03:** o 01 faz `ORDERS[Number(req.params.id)]` — `Number("__proto__")` é `NaN` e `ORDERS[NaN]` é `undefined`; o 02 indexa por chave UUID string (`ORDERS[req.params.id]`, sem `Number()`), mas só **lê** através dela — o `vulnerable/` devolve o objeto com `res.json(order)`, o `fixed/` compara `order.owner` —, nunca escreve; o 03 só **lê** (`STORES[storeId]?.operators.includes(user) ?? false` no `operates()`, `ORDERS[Number(req.params.orderId)]` na busca do `vulnerable/`), nunca escreve através da chave. Este é o **primeiro átomo que ESCREVE através de um lookup com chave-string vinda do path**. A categoria nova (função que muda estado) trouxe o risco novo.

**A correção é `Map<string, User>`, e ela dá três ganhos — registrar os três:**

1. **`Map.get()` não percorre a cadeia de protótipo.** `USERS.get("__proto__")` e `USERS.get("constructor")` devolvem `undefined` → `404`. O problema **desaparece estruturalmente**, em vez de ser barrado por uma guarda extra que o leitor do átomo não teria como entender.
2. **`USERS.has(user)` no `POST /login` volta a ser a MESMA forma de 01–03**, eliminando o `Object.hasOwn` que seria uma divergência da série.
3. **`Map.get()` tipa como `User | undefined` sempre** (independente de `noUncheckedIndexedAccess`), então a guarda `!target` continua **exigida pelo compilador** — exatamente o que a spec afirma na seção "Anatomia".

> **Alternativa CONSIDERADA e DESCARTADA:** `Record` + `Object.hasOwn(USERS, handle)` antes da escrita. Funciona (o `hasOwn` ignora a cadeia de protótipo), mas a guarda fica **arbitrária pra quem lê** e esconde o motivo real — o leitor vê um `hasOwn` sem entender que ele está barrando prototype pollution. O `Map` torna a intenção estrutural. **Não reintroduzir o `Record`.**

---

## Rotas — superfície mínima, duas rotas, nenhuma a mais

Imports: `import express from "express";` e `import { randomBytes } from "node:crypto";`. Bootstrap (`const app = express();` + `app.use(express.json());`), `USERS`, `TOKENS`, `issueToken`, `authenticate` e o rodapé `listen` são **idênticos** entre `vulnerable/` e `fixed/`. Superfície: **duas rotas, nenhuma a mais** — `POST /login` e a função admin. **Sem** endpoint de leitura (`GET /me`, `GET /users`), **sem** demote, **sem** índice de rotas (ver "Estado mutável" e "De onde vem o endpoint").

### `POST /login` — obter o próprio token (idêntico nas duas versões)

Recebe `{ "user": "<nome>" }`, valida contra `USERS`, devolve um token opaco. Sem senha (atalho de auth). Usuário desconhecido/ausente → `400` (higiene). A checagem de membership é **`USERS.has(user)` — a MESMA forma de 01–03** (o `Map` preserva essa API; só o tipo do store mudou de `Set<string>` pra `Map<string, User>`, porque agora cada usuário carrega um papel). Nenhuma divergência da série aqui.

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

### `POST /admin/users/:handle/promote` — a rota VULNERÁVEL (a função admin)

Promove o usuário `:handle` a administrador (`is_admin = true`). Autentica (Bearer ruim → `401`), busca o alvo, muda o estado, e devolve **só o que gravou** (o papel do alvo, `true` literal) — **sem** verificar que o chamador é admin. Handler **≤ ~30 linhas** (tem ~8).

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

- **Source:** o token no `Authorization` (a identidade — que o vulnerable autentica mas não usa pra autorizar a função) + o `:handle` do alvo. **Sink conceitual:** a execução da promoção **sem** comparar o papel do chamador ao papel exigido. O bug é **o que não está lá** — não greppa; audita-se perguntando **"onde este endpoint confere que o chamador pode invocar esta função?"**.
- **A resposta NÃO é dado alheio.** `{ "handle": "alice", "is_admin": true }` é **o que o chamador acabou de causar** — o `handle` é eco do input dele, e o `is_admin:true` é o resultado determinístico da operação — idêntico tenha o alvo sido admin ou não, então o corpo não diz nada sobre o estado anterior. Não é um registro privado da alice sendo lido (ela não tem nome/endereço/nada). Isso mantém o átomo no eixo da **função/capacidade**, não no eixo do **objeto**. **Cravar no DIFF.**
- **A promoção é idempotente e muda estado.** Promover duas vezes dá o mesmo resultado; o efeito persiste em memória (ver "Estado mutável").
- **`USERS.get(req.params.handle)` → `User | undefined`** (a assinatura do `Map.get`, independente de `noUncheckedIndexedAccess`): a guarda `!target` é **exigida pelo compilador**, porque a linha seguinte faz `target.is_admin = true` (desreferencia `target`). **Validado nesta fase:** removendo a guarda, o `tsc` dá `TS18048: 'target' is possibly 'undefined'` (ver "Validação de typecheck e runtime"). Mesma dinâmica de guarda forçada que 01/02 têm com `order.owner` — e **diferente** de 03, onde nada desreferenciava e a guarda não era forçada. O `Map` (em vez de `Record`) também fecha a prototype pollution que o `:handle` abriria (ver "Por que Map").

> **Bind do servidor** (rodapé idêntico a 01–03): `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);`

---

## Fix — verificar o papel do chamador antes de executar a função

O gêmeo `fixed/` difere **APENAS por um check de papel acrescentado antes da execução** — uma guarda a mais, logo depois da autenticação. **Nenhuma outra linha muda** — `POST /login`, helpers, imports, `USERS`, o rodapé, o `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` são **idênticos**.

```ts
app.post("/admin/users/:handle/promote", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  // FIXED: function-level authorization. Promoting is an admin-only capability, so the
  // caller's ROLE is checked right after authentication -- a non-admin is refused 403
  // BEFORE the target is ever looked up, so the gate leaks nothing about who exists.
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
  const target = USERS.get(req.params.handle);
  if (!target) return res.sendStatus(404);                  // unknown target user
  target.is_admin = true;                                   // state change -- not a read
  res.json({ handle: req.params.handle, is_admin: true });  // the state delta, not third-party data
});
```

Diff mínimo (o eixo único):

```diff
   if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
-  // VULNERABLE: the caller is authenticated, but the handler never checks the caller's
-  // ROLE. Promoting a user to admin is an admin-only function; here ANY authenticated
-  // user can invoke it. Authenticated is not authorized to PERFORM this operation.
+  // FIXED: function-level authorization. Promoting is an admin-only capability, so the
+  // caller's ROLE is checked right after authentication -- a non-admin is refused 403
+  // BEFORE the target is ever looked up, so the gate leaks nothing about who exists.
+  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
   const target = USERS.get(req.params.handle);
   if (!target) return res.sendStatus(404);                  // unknown target user
```

**A leitura correta do fix (cravar no DIFF):** a operação passou a **perguntar pelo papel do chamador** — não pelo dono de um objeto. O predicado `USERS.get(caller)?.is_admin` pergunta *"quem chama é admin?"*, e **o alvo não é argumento dessa pergunta** (ela roda antes de o alvo ser buscado). É o inverso estrutural de 01/02, onde o fix acrescentava um predicado **sobre o objeto** (`order.owner !== caller`); aqui o predicado é **sobre o chamador** (`USERS.get(caller)?.is_admin`). A lição transferível: **autorização por função é uma pergunta sobre o papel de quem invoca, no mesmo nível que a autenticação — não um check opcional depois de a operação já estar em curso.**

- **A guarda de papel vem ANTES da busca do alvo.** Um não-admin recebe `403` sem que o alvo seja consultado — então o gate **não vaza** nada sobre quais handles existem. É a mesma disciplina de ordem que o 03 usa (o check do pai antes da busca do filho); creditar o 03 (publicado) por essa simetria de método.
- **`USERS.get(caller)?.is_admin`:** `caller` é um handle resolvido pelo `authenticate` (sempre uma chave de `USERS`, porque tokens só são emitidos pra usuários válidos), mas o TS não sabe disso — `USERS.get(caller)` tipa como `User | undefined` (assinatura do `Map.get`), então o `?.` é **exigido** e correto. **Validado nesta fase:** trocar por acesso direto `USERS.get(caller).is_admin` faz o `tsc` dar `TS2532: Object is possibly 'undefined'` (ver "Validação de typecheck e runtime"). Mesmo espírito do `STORES[storeId]?.operators ... ?? false` de 03. **Não** trocar por `!` (non-null assertion).

**CRAVAR no DIFF — o fix NÃO é o de 01/02 nem o de 03, e isso é o esperado.** Em 01/02 o fix acrescentava um predicado **de posse do objeto** à guarda depois da busca; em 03 o fix **movia a busca** pra dentro do escopo do pai. Aqui o fix acrescenta uma guarda **de papel do chamador** antes da busca do alvo. Três formas diferentes porque três perguntas diferentes: *é seu?* (01/02), *é desta loja?* (03), *você pode fazer isso?* (04). A lição não é "o fix é sempre X"; é **autorize a operação que você está prestes a executar, no eixo que a operação exige**.

---

## Status code do fix: `403` (não `404`) — o critério da série, aplicado a uma capacidade

O fix retorna **`403`** para um não-admin que chama a função admin — **não `404`**. Isso **não** é exceção à série nem critério novo: é o **mesmo critério** que os átomos de API1 já aplicam — *a existência do alvo é sensível?* —, aplicado a um alvo de natureza diferente. O que **não** transfere é o **argumento do oracle** (que sustenta o `404` do pedido no 01 e no 03), não o **critério**. A spec crava as duas coisas, e essa é a defesa mais forte do `403`: mostra a série coerente, em vez de cada átomo decidindo por conta própria.

**O critério é um só, e vem do 01.** O DIFF do `bola-sequential-id` fecha a discussão do status com a regra *"`404` when existence itself leaks; `403` when admitting existence is fine"*, ancorada no RFC 9110 (§15.5.4 e §15.5.5). Os três átomos de API1 chegam ao `404` do pedido por caminhos diferentes — e é aí que o alcance importa:

- **01 (`bola-sequential-id`) e 03 (`bola-nested-resource`) sustentam o argumento do oracle diretamente.** No 01 os ids são inteiros contíguos (`1001`–`1012`); no 03 os pedidos correm num contador global da plataforma, nos mesmos `1001`–`1012`. Nos dois, distinguir "existe mas não é seu" / "existe, mas em outra loja" (`403`) de "não existe" (`404`) seria um **enumeration oracle** (oráculo de enumeração): varrendo o id-space, o atacante mapearia quais pedidos existem sem ler nenhum. A existência do pedido é sensível, e o critério dá `404`.
- **02 (`bola-uuid-leaked`) chega ao mesmo `404` por herança do fix, sem id-space pra varrer.** Os ids são UUID v4. O DIFF do 02 registra que, com UUIDs, a pressão do oracle *"all but vanishes — there is no space to walk"*, e que o `404` fica porque o fix foi copiado do 01 sem mudar um caractere e é *"the conservative default that is never wrong"*. O 02 não reabre o argumento: herda-o do DIFF do 01 por referência.
- **O 03 já aplica o critério nos dois sentidos.** No mesmo handler, a loja que você não opera recebe **`403`**: o slug é nome público, a existência da loja não é sensível, e o DIFF do 03 escreve o critério por extenso (*"is the target's existence itself sensitive?"*). O `403` honesto por existência não-sensível **já é precedente da série** — não nasce aqui.
- **Em nenhum dos três o alvo da autorização é uma capacidade conhecida.** Pedido e loja são **objetos** — instâncias endereçadas por id ou slug no path.

**No 04, o mesmo critério dá `403` — porque o alvo é de outra natureza.** O alvo da autorização aqui é uma **função nomeada única** — uma capacidade, não um objeto indexado por id —, e a **existência dessa função é premissa declarada do átomo** (o endpoint é conhecido: convenção de nomes, OpenAPI, bundle do front). **Não há id-space pra varrer** nem existência sensível a esconder: esconder um endpoint que já se assume conhecido **não compra nada** e contradiz a própria premissa do átomo. Aplicado a esse alvo, o critério da série responde `403`, como respondeu pra loja do 03.

**Por que `403` é a resposta honesta e correta (ancorar no RFC 9110 — texto bruto conferido nesta fase):**

- **RFC 9110 §15.5.4 (403 Forbidden):** *"The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it."* E, decisivo pra este átomo: *"If authentication credentials were provided in the request, the server considers them insufficient to grant access."* É **exatamente** o caso — o token é válido (credencial presente), mas o **papel** é insuficiente pra a função. `403` diz a verdade: "entendi o pedido, você está autenticado, e o seu papel não basta pra esta operação".
- **O `404` do §15.5.4 é uma OPÇÃO (`MAY`) pra esconder existência** — *"An origin server that wishes to 'hide' the current existence of a forbidden target resource MAY instead respond with a status code of 404."* Essa opção serve quando a existência do recurso **é sensível**. Aqui não é (o endpoint é conhecido por premissa), então a razão pra usar o `404` não existe, e o `403` honesto é o certo.
- **O `401` (§15.5.2) é a camada de baixo**, intocada: token ausente/ruim → `401` (*"lacks valid authentication credentials"*). O átomo mantém `401` (autenticação) e `403` (autorização por função) **distintos** — é a distinção auth-vs-authz que a classe ensina, agora no eixo da função.

**A negação não vira oráculo, por construção.** O `403` é devolvido **antes** da busca do alvo, então não revela nada sobre quais handles existem — ele só revela que **o chamador não é admin**, que é um fato sobre a conta do próprio chamador (ele já sabe que é usuário comum), não um segredo. Sem id-space, sem busca antes do gate, **não há oráculo** — e por isso não há a pressão que forçou o `404` do pedido no 01 e no 03 (no 02, como visto acima, o `404` veio por herança do fix, não por pressão).

**O `404` do alvo inexistente (no `fixed/`) é ortogonal e só alcançável por admin.** Depois do gate de papel, um admin que peça um `:handle` inexistente recebe `404` (o alvo não existe). Isso não é oráculo pra não-admin: só admins passam do `403`, e saber quais usuários existem é da alçada legítima de um admin. Manter mínimo; registrar no DIFF em uma frase.

**Regra de bolso — um critério só, o da série: a existência do alvo é sensível?** Sim → **`404`**, que torna "não autorizado" indistinguível de "não existe": o pedido do 01 e do 03, onde o id-space enumerável faria do `403` um oracle. Não → **`403`** honesto: a loja do 03 (slug público) e a função admin deste átomo (capacidade conhecida por premissa, onde o que falta é **papel**, não segredo de existência). O 02 não contradiz a regra: lá a pressão do oracle quase some com UUIDs, e o `404` fica por herança do fix, como o default conservador que o próprio DIFF do 02 descreve. O RFC 9110 oferece os dois (§15.5.4); quem escolhe é a natureza do alvo, não o átomo.

---

## Padrão de prova — Trigger

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **invocar uma função legítima** com um token legítimo, sem ter o papel pra ela. Trocar nada no token, só chamar a operação. Por ser **Trigger**, o **passo de contraste é obrigatório** (CLAUDE.md §5) — ver Walkthrough, Step 2.

---

## Estado mutável — primeiro átomo da série cujo endpoint atacado escreve

Em 01–03 o **endpoint atacado** era sempre uma leitura (`GET /orders/:id` no 01 e no 02, `GET /stores/:storeId/orders/:orderId` no 03); o `POST /login` existe nos três, mas não é a superfície do bug. Este é o **primeiro átomo cujo endpoint atacado muda estado** (`POST` que promove).

- **As escritas são reais, mas nenhuma resposta do walkthrough depende do acúmulo.** Fato verificado: a sequência do walkthrough foi rodada duas vezes seguidas, contra os mesmos containers, e os status e corpos saíram idênticos. Os passos podem ser repetidos em qualquer ordem. (No `vulnerable/` nenhum papel é lido; no `fixed/` o `clancy` nunca é promovido, e a promoção da `carol` não alimenta passo nenhum.)
- **A mudança de estado no `vulnerable/` é real mas inobservável pela API.** Não há rota de leitura, e o corpo de sucesso é determinístico (`is_admin: true` literal, idêntico pra quem já era admin e pra quem não era) — de fora, o `200` não distingue nada. É consequência de uma escolha deliberada — **nenhuma rota de leitura, pra não convidar o reflexo de BOLA** (ver "A tese do átomo") —, não um defeito. A prova de que `is_admin` governa alguma coisa vem do `fixed/` (`carol` `200` vs `clancy` `403`), não de observar o flag.
- **SEM endpoint de demote.** Um "despromover" seria **outra função admin desprotegida** — superfície a mais sem lição a mais (e, no `vulnerable/`, um segundo bug do mesmo tipo). E nenhum passo precisa desfazer nada.
- **Gêmeos independentes.** Promover na porta 8204 não muda nada na 8304; o seed de cada build é próprio.
- **Requisito de README (EN+PT), a única casa da frase do restart:** uma frase diz que o estado vive em memória e que `./atom down bfla-admin-function && ./atom up bfla-admin-function` devolve o seed original (`carol` a única admin). Não repetir no WALKTHROUGH nem no DIFF.

---

## Walkthrough — estrutura e requests

Trabalhado **100% no Burp** (Repeater), `curl` como equivalente — **API-only, SEM trilha browser** (CLAUDE.md §3.3). **Sem Intruder:** a tese não é escala/enumeração (essa é a casa do `bola-sequential-id`); é a invocação sem papel, provada em requests únicos. Cada request é um bloco colável: request-line + `Authorization: Bearer <token>` + corpo JSON quando houver. Tokens são **placeholders** (`<clancy-token>`, `<carol-token>`) — variam por login; handles são **literais** (seed fixo).

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de administração serve `POST /admin/users/:handle/promote`, autentica o chamador e promove o alvo a admin sem conferir que quem chama é admin" — não um personagem. Definir todo termo não-óbvio na estreia: "BFLA (Broken Function Level Authorization)", "function-level authorization", "vertical privilege escalation", "opaque token".

### 1. Context
- API de administração de papéis; auth por Bearer token opaco; `POST /admin/users/:handle/promote` é a função "promover a admin". Isto é **BFLA** — **API5:2023** do OWASP API Security Top 10. **Contraste de abertura:** os átomos de API1 perguntavam sobre a instância — *é este objeto seu?* (01/02), *é desta loja?* (03); este pergunta sobre a capacidade: *você pode invocar esta operação?*. **A premissa declarada, em uma frase:** o caminho admin é conhecido (convenção/OpenAPI/bundle do front) — achar o endpoint não é o desafio; invocá-lo sem papel é. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar o handler vulnerable. Ele **chama `authenticate()`** (`401` em token ruim) mas **não** compara o papel do chamador ao papel exigido. O bug é **o que não está lá**. Pergunta de auditoria — **diferente** da de BOLA: não "cadê o check de dono do objeto?", mas **"cadê o check de que o chamador pode invocar esta função?"** → em lugar nenhum. Notar que ter `authenticate()` ali **engana** o revisor apressado (mesma armadilha de 01–03, eixo novo), e que a classe **não greppa**.
- Creditar o eixo: em 01–03 o handler sabia quem você era e não checava **de quem é o objeto**; aqui sabe quem você é e não checa **o que você pode fazer**.

### 3. How auth works in this lab (subseção curta)
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo), cripto-forte (`randomBytes`), mapeado ao usuário. Dois pontos: (i) a **autenticação É imposta** (token ruim → `401`); (ii) se o **papel** do chamador é checado pra autorizar a **função** é outra pergunta — e o vulnerable não checa. **Disciplina cravada:** o ataque **não toca** o token (não decodifica, não adultera) — fica válido e do `clancy` o tempo todo. O papel mora em `USERS.get(caller)?.is_admin`.

### 4. Baseline — logar como usuário comum
- `POST /login` com `{"user":"clancy"}` → `{"token":"<clancy-token>"}`. Bloco colável (request-line + `Content-Type: application/json` + corpo). `clancy` é um **usuário comum** — a API o autentica perfeitamente; ele simplesmente não é admin. (Não há `GET` de escopo pra mostrar aqui — a superfície é mínima; a única outra rota é a função admin, que o Step 1 ataca. Baseline curto é o correto pra esta classe.)
- **Requisito de walkthrough — UMA frase sobre o papel do `clancy` (obrigatória).** No ponto em que o papel dele passa a importar (aqui, ou na abertura do Step 1), uma frase registra que **o papel do `clancy` se lê no seed do `app.ts`** (`["clancy", { is_admin: false }]` — a premissa do repo: um bug por app, rápido de ler) e **se confirma pelo comportamento no `fixed/`**, onde a mesma chamada bate num `403`. Motivo: a superfície tem duas rotas e nenhum `GET`, então no `vulnerable/` a chamada do `clancy` passa de qualquer jeito e o sucesso **não distingue** "ele não era admin" de "ele já era" — sem essa frase fica um buraco visível. **Uma frase. NÃO criar rota de leitura** (`GET /me` etc.) pra confirmar o papel — superfície extra sem lição. Texto sugerido (a Fase 2 ajusta a prosa, não o sentido):

  > **EN:** *You can see clancy is an ordinary member in the seed — `["clancy", { is_admin: false }]` in `app.ts` — and the fixed build confirms it from the outside: the same call there is refused `403`. The vulnerable build never says so, because it never checks.*
  >
  > **PT:** *Dá pra ver que o `clancy` é um member comum no seed — `["clancy", { is_admin: false }]` no `app.ts` — e o `fixed/` confirma isso de fora: a mesma chamada lá leva `403`. O `vulnerable/` nunca diz isso, porque nunca checa.*

### 5. Step 1 — Invoke the admin function as a non-admin (BFLA confirmado)
- `clancy` (comum) promove a **alice**:
  ```
  POST /admin/users/alice/promote HTTP/1.1
  Host: 127.0.0.1:8204
  Authorization: Bearer <clancy-token>
  ```
  (sem corpo — o alvo vai no path). Resposta — **`200`** com `{"handle":"alice","is_admin":true}`.
- Você invocou uma **função admin** — promover uma conta a administrador — sendo um **usuário comum**, com o seu próprio token válido. O registro alterado **não é seu**, você não tem relação nenhuma com a alice, e o que explica o sucesso é que **a FUNÇÃO estava desprotegida** — não um objeto seu, não uma identidade forjada. Isso é **BFLA**, e é **escalação vertical**: você ganhou poder, não leu o dado de um par.
- **A resposta não é leitura de objeto.** O corpo diz só **o que a operação gravou** (`is_admin: true`, literal — o mesmo pra qualquer alvo) — o `handle` é o que você mesmo mandou no path. Que a alice era comum antes se lê no seed, não na resposta. Nada de nome/endereço/registro privado. Guardar essa observação: é o que separa esta classe de BOLA.
- **Indiferença ao alvo (a assinatura de BFLA):** a função aceitou `alice` sem perguntar quem você é no organograma. Ela aceitaria **qualquer alvo** — o Step 2 prova isso com o caso-limite (o próprio `clancy`). A indiferença ao alvo é o sinal de que o eixo é **a operação**, não a instância.

### 6. Step 2 — What the vuln is NOT (passo de contraste OBRIGATÓRIO — CLAUDE.md §5)
Dois requests, **o primeiro é o decisivo** (é o desenho exato pedido pelo mantenedor):

- **(1) `clancy` promove o PRÓPRIO handle** — `POST /admin/users/clancy/promote` com o `<clancy-token>` → **`200`**, `{"handle":"clancy","is_admin":true}`. **Este é o argumento decisivo.** Se a falha fosse sobre **objeto alheio** (raciocínio de BOLA), aqui **não haveria nada de errado**: o registro é dele, ele está mexendo em si mesmo. E ainda assim **a chamada não deveria ser permitida**, porque **promover é uma função de admin** — não importa de quem é o alvo. Isso separa de uma vez **"de quem é o objeto"** (irrelevante aqui) de **"quem pode invocar a função"** (o que importa). *(É também a prova da "indiferença ao alvo" prometida no Step 1: o endpoint promove um estranho e promove você mesmo, com a mesma indiferença.)*
- **(2) Sem token** no endpoint admin — `POST /admin/users/alice/promote` **sem** `Authorization` → **`401`**. A **autenticação funciona**: sem identidade, nada roda. (Token corrompido também → `401`.)

**Conclusão a escrever explicitamente:** o request (1) é inatacável sob a lente de BOLA (objeto próprio) e **mesmo assim** é a falha — logo o eixo **não é o objeto**, é a **operação**. O request (2) mostra que a autenticação está lá e funciona — logo o eixo **não é autenticação quebrada nem impersonation**. O que falta é a camada do meio: **a verificação de que o chamador tem o papel pra invocar a função**. É BFLA, não BOLA, não falha de auth.

> **Frase-âncora do WALKTHROUGH (uma casa só):** *The endpoint never cared whose account the target was, because the flaw was never about the target — it was about who is allowed to run the function at all.* / *O endpoint nunca se importou de quem era a conta-alvo, porque a falha nunca foi sobre o alvo — foi sobre quem pode rodar a função, ponto.* Mora no fim do Step 2. **Não** repetir no DIFF nem no README.

### 7. Step 3 — Impact: a role flag anyone can write (prova composta pelos DOIS gêmeos)
A prova de impacto é **composta**: cada metade é demonstrada no gêmeo onde ela é verdadeira, só com a superfície que já existe.
- **Metade `vulnerable/` — o flag é gravável por qualquer um.** Já está na mesa, sem request novo: nos Steps 1–2 o `clancy`, usuário comum, gravou `is_admin: true` na `alice` e no próprio registro — em quem ele quiser, inclusive nele.
- **O que este gêmeo NÃO consegue mostrar — e o walkthrough diz isso:** que o flag vale alguma coisa. No `vulnerable/` nenhum papel é verificado em lugar nenhum (o `is_admin` é escrito, nunca lido), então nenhuma resposta deste build muda por causa da escrita. Essa metade só é verdadeira no `fixed/`, e é demonstrada na seção do fix pelos mesmos dois requests que provam o fix.

> **Por que a versão anterior da prova caiu (registro).** Ela provava o impacto com um segundo salto dentro do `vulnerable/`: a conta que o `clancy` promoveu invocando, por sua vez, a mesma função. Mas no `vulnerable/` nenhum papel é verificado, então esse segundo salto passa com ou sem a promoção anterior — o "antes" que a demonstração exigia não existe naquele gêmeo, e o passo afirmaria uma causa que o código não tem. É a regra do template aplicada à própria spec: afirmação tem que ser verdadeira sobre o código. **Não reintroduzir.**

### 8. Why the fix works (porta 8304) — e a metade da prova que só o `fixed/` mostra
Apontar o Burp pro `fixed/` em `127.0.0.1:8304` e logar lá (cada build tem o próprio mapa de tokens):
- `clancy` (comum) promove `alice` → **`403`** (body `Forbidden`). **A função checa o papel do chamador logo depois da autenticação, antes de buscar o alvo** — a alice nunca é promovida.
- **A função ainda funciona pra quem pode:** logar como `carol` (`{"user":"carol"}` → `<carol-token>`), a admin seedada, e promover `bob` → **`200`**. O fix não quebrou a feature; só restringiu quem a invoca. Sem/ruim token ainda → `401`.
- **Os dois requests acima fecham a prova composta do Step 3.** O gate roda antes da busca do alvo, então o alvo não entra na decisão: o que separa o `200` do `403` é só o `is_admin` de quem chama. No `fixed/`, o flag **governa de fato** o acesso à função — o papel significa algo. Somado à metade do `vulnerable/`: **o flag governa a capacidade, e o flag é gravável por qualquer um.**
- **`403`, não `404`:** o não-admin recebe `403` (não um `404` que fingiria que o endpoint não existe) — o endpoint é conhecido por premissa, não há existência a esconder, e `403` diz a verdade ("você está autenticado e o seu papel não basta"). **Forward pro DIFF** pro argumento completo (RFC 9110 §15.5.4; o critério da série, e por que o oracle que sustenta o `404` do pedido no 01 e no 03 não se aplica aqui).

**O walkthrough TERMINA aqui.** Sem Intruder, sem script de automação, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5 — termina onde a falha foi mostrada e o fix explicado).

---

## Frases-âncora (uma casa só cada — CLAUDE.md §11 / template)

Nenhuma frase memorável aparece em **dois** documentos. Atribuição fixa:

- **WALKTHROUGH (uma casa):** *"The endpoint never cared whose account the target was, because the flaw was never about the target — it was about who is allowed to run the function at all."* / *"O endpoint nunca se importou de quem era a conta-alvo, porque a falha nunca foi sobre o alvo — foi sobre quem pode rodar a função, ponto."* Mora no fim do Step 2. **Não** repetir no DIFF nem no README.
- **DIFF (uma casa):** *"The fix adds no check about the target at all — it asks only whether the caller may run the function."* / *"O fix não acrescenta check nenhum sobre o alvo — ele pergunta só se o chamador pode rodar a função."* Mora na seção do fix. **Não** repetir no WALKTHROUGH nem no README.
- **Não reusar** as âncoras de 01 ("…it leaks the collection…"), 02 ("…a wall of 404s is 'didn't find'…"; "…the correction changed nothing") nem 03 ("Authorization present is not authorization sufficient — what matters is which question it answers."). Este átomo tem as suas. *(Atenção: a âncora de 03 é PRÓXIMA em espírito — "qual pergunta o check responde". Mantê-las distintas: a de 03 é sobre um check **presente** apontando pro objeto errado; as deste são sobre a **ausência** do check de papel e a indiferença ao alvo. Não colar as frases.)*

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` + `Dockerfile` em **cada** gêmeo, **self-contained, sem módulo compartilhado**; lockfile **commitado** por gêmeo. `app.ts` **difere** só pela guarda de papel acrescentada no `POST /admin/users/:handle/promote`; todo o resto é idêntico entre as versões.

**Herança de toolchain (CLAUDE.md §3.6) — lida dos arquivos publicados de 01–03 nesta fase (os seis `package.json`, os `Dockerfile` e `tsconfig.json` batem por md5):**

`tsconfig.json` (copiar — idêntico a 01–03):

```json
{
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "target": "es2024",
    "lib": ["es2024"],
    "types": ["node"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "noEmit": true
  }
}
```

- **A guarda `!target` é FORÇADA pelo compilador neste átomo** — como em 01/02 (onde `order.owner` era desreferenciado) e **diferente** de 03 (onde nada era desreferenciado e a guarda não era forçada). Aqui `USERS.get(req.params.handle)` é `User | undefined` (assinatura do `Map.get`, **independente** do `noUncheckedIndexedAccess`), e `target.is_admin = true` desreferencia `target`, então sem `if (!target)` o `tsc` dá **`TS18048: 'target' is possibly 'undefined'`** (observado nesta fase; ver "Validação de typecheck e runtime"). O mesmo `| undefined` do `Map.get` exige o `?.` em `USERS.get(caller)?.is_admin` no fix — sem ele, **`TS2532: Object is possibly 'undefined'`**. **Os docs PODEM afirmar que o compilador força a guarda `!target` e o `?.`** (ao contrário de 03), com os códigos acima. Nota: o `noUncheckedIndexedAccess` continua ligado (herança da série), mas aqui quem força as guardas é a assinatura do `Map.get`, não a flag.

`Dockerfile` (idêntico a 01–03 — copiar; base `node:24.21.0-slim`, patch exato, nunca `latest` nem a tag móvel `node:24-slim`):

```dockerfile
FROM node:24.21.0-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY tsconfig.json .
COPY app.ts .
# Bind 0.0.0.0 inside the container so Docker port-forwarding reaches Express;
# host exposure stays restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 3000
# Drop root for runtime: node:* ships a non-root `node` user. node_modules stays
# root-owned (read-only at runtime) -- tsx needs no write access there.
USER node
CMD ["npm", "start"]
```

`docker-compose.yml` (bind **só** em `127.0.0.1`, portas **8204/8304**):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8204:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8304:3000"
```

- `package.json` de cada gêmeo: `"name": "bfla-admin-function"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Entrypoint `tsx`. **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **Roda como não-root, sem `chown`** — mesma justificativa de 01–03 (validada lá). Reconfirmar no smoke test da Fase 2: build OK, container sobe como `node`, `tsx` sem erro de permissão, endpoints respondendo, imagem só com `express` + `tsx`.

---

## Dependências extras

**Nenhuma dependência nova.** Versões **exatas herdadas** de 01–03 — lidas dos seis `package.json` publicados (idênticos) e conferidas nos `package-lock.json` commitados. **NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

```json
{
  "dependencies": {
    "express": "5.2.1",
    "tsx": "4.23.13"
  },
  "devDependencies": {
    "typescript": "7.0.2",
    "@types/express": "5.0.6",
    "@types/node": "24.13.5"
  }
}
```

- Base `node:24.21.0-slim` (lida dos seis `Dockerfile`, md5 idêntico). Nenhuma divergência entre os átomos.
- Classificação por **runtime**: `tsx` em `dependencies` (entrypoint que executa); `typescript`/`@types/*` em `devDependencies` (build/checagem). `npm audit --omit=dev` cobre exatamente o que a imagem `npm ci --omit=dev` instala e roda (`express` + `tsx`). **Escopo da imagem = escopo do audit = o que roda.**
- `crypto` é **nativo** (`node:crypto`, para `randomBytes` do token) — não é dependência npm. **Nenhuma lib de autorização/RBAC, nenhum middleware de auth** — o check de papel é um `if` de uma linha. Isso respeita "só inclua a lib se serve à falha ou ao fix" (§3.6): nenhuma lib serve a nenhum dos dois.
- **Pin exato travado no `package-lock.json`** (commitado por gêmeo). Updates **manuais** (CLAUDE.md §8.7). Se algo em 01–03 parecer desatualizado, **seguir com o que está lá** — bump é decisão de corte de release, coordenada na série inteira (§3.6), não neste átomo.

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). **BFLA não tem página própria no PortSwigger** — a Web Security Academy trata a classe sob **Access control**, especificamente **vertical privilege escalation / unprotected functionality**, que é a casa conceitual de "invocar uma função que só admin deveria alcançar". A página conceitual (não a listagem de labs) é a de Access control, e **NÃO é a página de IDOR usada por 01–03** (aquela é a face de objeto/horizontal).

- **Primer (verificado por fetch NESTA fase — HTTP 200 direto, sem redirect; H1 "Access control vulnerabilities and privilege escalation"; primeira seção "What is access control?"; cobre "Vertical privilege escalation" e "Unprotected functionality" no corpo):**
  `https://portswigger.net/web-security/access-control`
  Texto do link: **"Access control vulnerabilities and privilege escalation"** — a forma como a própria PortSwigger apresenta a página (H1), preservada em **inglês** também no README PT (CLAUDE.md §7).

Formato exato EN:

```markdown
> **Theory primer:** Read [PortSwigger: Access control vulnerabilities and privilege escalation](https://portswigger.net/web-security/access-control)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato exato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: Access control vulnerabilities and privilege escalation](https://portswigger.net/web-security/access-control)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

**OWASP: sem link inline.** Os docs citam `API5:2023` em texto simples; o link canônico da categoria vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (conferido: os READMEs de 01–03 seguem isso — nenhum link da OWASP nos docs deles). A linha da categoria API5 **já existe** na tabela de Cobertura do ROADMAP (conferido nesta fase), apontando `bfla-admin-function` e `bfla-method-based`.

**Fase 2:** re-confirmar a URL do primer por fetch na geração (a PortSwigger às vezes reorganiza caminhos).

---

## Política de cross-ref (CLAUDE.md §5)

Publicação verificada **lendo `atoms/api/ROADMAP.md` e a árvore de `atoms/` NESTA fase**, não de memória: na série API, **01, 02 e 03 estão publicados** (`[x]`, pastas completas, todos API1); **04 em diante não** (04 é este; 05 `bfla-method-based` é a outra linha de API5, **não publicada**).

- **`bola-sequential-id`, `bola-uuid-leaked`, `bola-nested-resource` — citar, contrastar, creditar. A troca de categoria É a lição.** Contrastes permitidos, todos verdadeiros sobre o código:
  - **O eixo:** 01–03 protegem **instâncias** (é este objeto seu? / é desta loja?); este protege **capacidade** (você pode invocar esta operação?). BOLA = objeto; BFLA = função. É o contraste central do átomo.
  - **A pergunta de auditoria:** "cadê o check de dono do objeto?" (01/02) / "o objeto é do pai autorizado?" (03) vs **"o chamador pode invocar esta função?"** (04).
  - **A forma do fix:** predicado de posse do objeto depois da busca (01/02); mover a busca pro escopo do pai (03); **guarda de papel do chamador antes da busca** (04). Três formas, três perguntas.
  - **O status code:** um critério só na série — *a existência do alvo é sensível?* (a regra do DIFF do 01). No 01 e no 03 ele dá `404` pro pedido, pra fechar o oracle sobre id-space enumerável; o 02 mantém o mesmo `404` por herança do fix, sem id-space pra varrer; o 03 já dá `403` pra loja, cuja existência não é sensível. No 04 o alvo é capacidade conhecida, e o mesmo critério dá **`403`**. O que não transfere é o argumento do oracle, não o critério — e dizer por que **é** parte da lição.
  - **A premissa declarada:** creditar o **02** como o precedente de "átomo que começa de premissa declarada" — lá a premissa era a lição (id vazado), aqui é economia (endpoint conhecido).
  - **A ordem do check antes da busca:** creditar o **03** pela mesma disciplina de método (gate antes de materializar o alvo).
- **PROIBIDO citar qualquer átomo de API NÃO publicado** (05 em diante: `bfla-method-based`, `bopla-*`, `auth-*`, etc.) — por nome, número ou descrição. **Em particular, NÃO antecipar "BFLA por método" (atom 05)** — nada de "a próxima volta mostra o check que depende do método HTTP" ou similar. Forward reference (CLAUDE.md §5). Verificado: só 01–03 publicados.
- **Átomos web de A01** (`idor-numeric-id`, `bola-rest`, `idor-uuid-guessable`) — todos horizontais (IDOR/BOLA). **Não há gêmeo web desta classe** (vertical/BFLA) pra creditar; esta spec **não afirma nada** sobre eles além do que se puder conferir lendo o átomo na Fase 2. Se a geração quiser citar um, confere o fato lendo o arquivo — mas não é necessário.
- Termos técnicos em inglês no PT (BFLA, BOLA, IDOR, function-level authorization, object-level authorization, privilege escalation, role, token, Bearer, enumeration oracle, Trigger, payload).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API5 — Broken Function Level Authorization** | Primeira categoria nova da série. Request legítimo invocou função fora do nível de privilégio (autorização por função), não objeto fora do escopo (BOLA) nem injection. |
| Nome / classe (H1) | **Broken Function Level Authorization (BFLA)** — idêntico EN/PT | Título nomeia a classe; o slug (`bfla-admin-function`) qualifica a variante. Primeiro H1 da série que não é BOLA, de propósito. |
| Pasta nova | **`API5-broken-function-level-authz/`** | Padrão de nomenclatura de `API1-broken-object-level-authz`. Nasce com este átomo. |
| Papel na série | **Vira o eixo: instância → capacidade** | BOLA protege objeto; BFLA protege operação. O contraste com 01–03 é o material. |
| A função admin | **Promover usuário a admin** (`POST /admin/users/:handle/promote`) | Muda estado, não devolve dado alheio → isola o eixo da capacidade do eixo do objeto (evita o reflexo de BOLA). Escalação autoevidente; o impacto se prova sem endpoint novo (ver "Prova de impacto"). |
| Toolchain | **Herdado exato** de 01–03 (express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; base `node:24.21.0-slim`) | CLAUDE.md §3.6. Lido dos arquivos publicados nesta fase. Bump é decisão de release. |
| Store | **Em memória (`Map<string, User>`), sem banco** | BFLA não depende do storage. `User = { is_admin: boolean }`: o papel tem que morar em algum lugar — única mudança estrutural vs. o `Set` de 01–03. **`Map` (não `Record`)** pra o lookup-e-escrita por `:handle` não abrir prototype pollution (`__proto__`/`constructor`); `Map.get` não percorre protótipo. |
| Papel / representação | **`is_admin: boolean` por usuário** | Mínimo. Análogo ao `order.owner` (01/02) e ao vínculo operador→loja (03): o dado que a autorização compara. |
| Admin no seed | **`carol` é a única admin; `clancy`/`alice`/`bob` comuns** | O `fixed/` precisa de um admin pra mostrar a função funcionando pra quem pode. `clancy` comum pra a escalação ser escalação; `alice` comum pra a promoção ser ilegítima (se já fosse admin, seria no-op); `bob` comum como alvo da promoção legítima da `carol` no `fixed/`. `carol` reusa o elenco. |
| Token | **Opaco, `crypto.randomBytes`; NÃO JWT** — idêntico a 01–03 | Cripto-forte pra não ser 2ª vuln. O ataque não toca o token. |
| Descoberta do endpoint | **DECLARADA no enunciado, uma frase** | Em BFLA real a descoberta quase nunca é o difícil; encenar distorceria a classe. Nada na app revela rota (seria information disclosure, 2º bug). 2ª vez na série (creditar o 02: lá premissa=lição, aqui=economia). |
| Rotas | `POST /login`, `POST /admin/users/:handle/promote` (vuln) | Superfície mínima. Sem read, sem demote, sem índice de rotas. |
| O bug | **Check de papel AUSENTE** antes da função admin | Ausência de código, não payload. Autentica mas não autoriza a função. |
| Fix (eixo único) | **`if (!USERS.get(caller)?.is_admin) return 403` antes da busca** | Guarda de papel do chamador, logo depois da autenticação. Inverso de 01/02 (predicado sobre o objeto) e diferente de 03 (mover a busca). |
| Status code do fix | **`403`** (não `404`) | O alvo é uma **função conhecida** (premissa), não objeto com existência sensível; sem id-space, sem oráculo. RFC 9110 §15.5.4: credencial presente, papel insuficiente → `403` honesto. O argumento de `404` de 01–03 não transfere, e dizer por quê é lição. |
| Alvo inexistente (fixed) | **`404`**, só alcançável por admin (pós-`403`) | Ortogonal; admins podem saber quais usuários existem. Não é oráculo pra não-admin (gate antes da busca). |
| Resposta de sucesso | **`{ "handle": "<alvo>", "is_admin": true }`** | O **delta que a operação aplica** (o valor gravado, `true` literal — não um antes/depois), não dado privado de terceiro. `handle` é eco do input; o corpo é determinístico e não diz nada sobre o estado anterior do alvo. Mantém no eixo da função, longe de BOLA. |
| Corpo dos erros — `sendStatus` | **`res.sendStatus(...)` (401/403/404); sucesso via `res.json(...)`** | Igual a 01–03. |
| Estado | **Mutável; escritas reais, nenhuma resposta depende do acúmulo; sem demote** | Primeiro átomo cujo endpoint atacado escreve. Sequência do walkthrough rodada duas vezes seguidas: status e corpos idênticos, passos repetíveis em qualquer ordem. Demote seria 2ª função desprotegida (superfície sem lição). Gêmeos independentes. |
| Padrão de prova | **Trigger** (não Payload) | Não há sink; o exploit é invocar uma função legítima sem papel. → passo de contraste obrigatório. |
| Passo de contraste | **(1) `clancy` promove a si mesmo → 200 (decisivo); (2) sem token → 401** | (1) inatacável sob BOLA (objeto próprio) e mesmo assim é a falha → eixo = operação. (2) auth funciona → não é impersonation. Terceiro passo (não-admin tocando registro da alice) só entraria com rota já existente — não há; dois bastam. |
| Prova de impacto | **Composta pelos dois gêmeos:** `fixed/` — `carol` promove `bob` (`200`), `clancy` não (`403`); `vulnerable/` — `clancy` grava `is_admin` de quem quiser, inclusive o dele | O flag governa a capacidade (`fixed/`) e é gravável por qualquer um (`vulnerable/`); cada metade no gêmeo onde é verdadeira. Sem endpoint novo. A versão anterior (segundo salto dentro do `vulnerable/`) caiu: lá nenhum papel é verificado, então afirmaria uma causa que o código não tem. |
| Trilha | **100% Burp (Repeater) / curl; SEM Intruder; SEM browser** | API-only (CLAUDE.md §3.3). A tese não é escala/enumeração (casa do 01). |
| Impacto | **Escalação VERTICAL de privilégio** | Honesto: ganhar papel admin. Não é horizontal (ler objeto de par), não é RCE. Primeiro vertical do repo. |
| Theory primer | **PortSwigger Access control** (vertical priv-esc / unprotected functionality) | BFLA não tem página própria; Access control é a casa conceitual. **Diferente** da página de IDOR de 01–03. URL verificada por fetch nesta fase (200, sem redirect). |
| Cross-ref | **01–03 central (contraste de categoria); nenhum átomo de API 05+** | 01–03 publicados (citar/contrastar). 05 (`bfla-method-based`) não-publicado → proibido, inclusive antecipar BFLA por método. |

---

## Decisões que podem gerar dúvida durante implementação

- **Membership no `POST /login` — resolvida pelo `Map`.** Com `USERS` sendo `Map<string, User>`, a checagem é **`USERS.has(user)`**, exatamente como 01–03 (sem `Object.hasOwn`, sem divergência da série). `req.body?.user` é `any` (Express não tipa o body) → `Map.has(any)` aceita; `issueToken(user)` aceita `any` em parâmetro `string`. **Validado nesta fase:** `tsc --noEmit` limpo (exit 0).
- **Guarda `!target` FORÇADA pelo compilador (diferente de 03) — validado nesta fase.** `USERS.get(req.params.handle)` é `User | undefined` (assinatura do `Map.get`); `target.is_admin = true` desreferencia, então `if (!target)` é exigido. **Observado:** removendo a guarda, `tsc` dá **`TS18048: 'target' is possibly 'undefined'`**. Os docs **podem** afirmar isso (ao contrário de 03, onde a guarda não era forçada).
- **`USERS.get(caller)?.is_admin` no fix — `?.` exigido, validado nesta fase.** `caller` vem do `authenticate` (string, sempre uma chave real em runtime), mas o TS vê `USERS.get(caller)` como `User | undefined`; o `?.` é exigido. **Observado:** trocar por acesso direto `USERS.get(caller).is_admin` dá **`TS2532: Object is possibly 'undefined'`**. **Não** usar `!` (non-null assertion).
- **Tipos do Express 5 — retorno `Response` vs `void`.** Igual a 01–03: callbacks contextualmente tipados (retorno `void`), onde `return res.sendStatus(...)` **passa**. Se o gerador **anotar o retorno** do handler explicitamente, o TS reclama; a forma segura é **`res.sendStatus(401); return;`** (statement + `return` vazio), **nunca** `return res.sendStatus(...)`. Não anotar o retorno é o caminho de 01–03.
- **Corpo do `POST` da promoção.** O alvo vai no **path** (`:handle`); o corpo é vazio/ausente. O `app.use(express.json())` continua obrigatório (o `POST /login` usa o body) e idêntico a 01–03 — não removê-lo.
- **Verbo HTTP.** `POST` é o verbo natural pra a ação "promover". **NÃO** transformar a escolha do método em lição (variação por método HTTP é outra linha da categoria, não-publicada — fora do escopo; não aludir).

---

## Validação de typecheck e runtime (feita NESTA fase de planning)

Montei um protótipo local com o **toolchain EXATO** herdado de 01–03 (express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5) e o `tsconfig.json` da série (copiado byte a byte do `bola-sequential-id`), reconstruí os **dois gêmeos** a partir dos samples desta spec **já com o `Map`**, e rodei `tsc --noEmit` em cada um. Observado (não raciocinado):

**Typecheck (os números de erro são reais, do `tsc` 7.0.2):**

| Teste | Resultado observado |
|---|---|
| `vulnerable/app.ts` (Map, guarda `!target` presente) | **exit 0**, limpo |
| `fixed/app.ts` (Map, `USERS.get(caller)?.is_admin`) | **exit 0**, limpo |
| **[prova negativa]** `fixed/` com acesso direto `USERS.get(caller).is_admin` (sem `?.`) | **`TS2532: Object is possibly 'undefined'`** |
| **[prova negativa]** `vulnerable/` com a guarda `!target` removida | **`TS18048: 'target' is possibly 'undefined'`** |
| `USERS.has(user)` / `USERS.get(handle)` com `Map` | compilam limpos (dentro dos dois gêmeos exit 0) |
| `lib`/`target` da série (`es2024`) | suportam tudo que os samples usam (`Map`, `randomBytes`, Express 5) — exit 0 |

- **As duas afirmações de compilador da spec estão CORRETAS**, agora com código: a guarda `!target` é forçada (**`TS18048`**), e o `?.` no fix é exigido (**`TS2532`**). Nenhuma estava errada — mas, diferente da versão anterior desta spec, agora são **observadas**, não analogia. (A correção que o átomo 03 fez na própria pele — "a guarda não era forçada lá" — foi o motivo de validar em vez de supor.)
- **Nota de precisão:** o `| undefined` que força as duas guardas vem da **assinatura do `Map.get`**, não do `noUncheckedIndexedAccess` (que continua ligado por herança da série, mas não é o que faz o trabalho aqui).

**Runtime — prototype pollution, ANTES e DEPOIS do `Map`** (handler reproduzido com `tsx`, alvos `__proto__` e `constructor`):

| Store | `__proto__` | `Object.prototype` poluído? | `constructor` | `alice` | `nobody` |
|---|---|---|---|---|---|
| **`Record`** (design descartado) | **`200`** (guarda `!target` NÃO pega) | **SIM** — `({}).is_admin === true` no processo todo | **`200`** | `200` | `404` |
| **`Map`** (correção) | **`404`** | **não** — `({}).is_admin === undefined` | **`404`** | `200` | `404` |

- Com `Record`, `USERS["__proto__"]` devolve `Object.prototype` (truthy), a guarda passa, e `Object.prototype.is_admin = true` **polui o processo inteiro** — segunda vuln confirmada, não teórica.
- Com `Map`, `USERS.get("__proto__")` e `USERS.get("constructor")` devolvem `undefined` → `404`, e **nada** é acrescentado a `Object.prototype`. O caminho legítimo (`alice` → `200`, `nobody` → `404`) é idêntico nos dois.

A Fase 2 ainda roda `npm run typecheck` nos dois gêmeos como gate oficial (host/CI) — o acima é a validação de planning, na mesma disciplina de 01–03.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia `usuário→token`, Bearer resolve de volta; `clancy`/`alice`/`bob`/`carol` recebem tokens distintos e cripto-fortes (`randomBytes`). Bloco de auth (helpers) byte a byte o de 01–03; só `USERS` mudou de `Set<string>` pra `Map<string, User>`; membership segue `USERS.has(user)`.
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido → **`401`** no endpoint admin, nas duas versões.
3. **Vulnerable — BFLA:** `POST /admin/users/alice/promote` com o Bearer do **`clancy`** (comum) → **`200`**, `{"handle":"alice","is_admin":true}`. A escrita (`alice.is_admin = true`) é real — o `200` só sai depois dela —, mas inobservável pela API: validar pelo status, não por ler o flag. Token intacto.
4. **Vulnerable — indiferença ao alvo:** `POST /admin/users/clancy/promote` com o Bearer do `clancy` → **`200`** (o caso-limite do passo de contraste).
5. **Vulnerable — nenhum papel é lido:** no `vulnerable/app.ts` o `is_admin` só é escrito, nunca lido. Por isso a metade "o flag governa a capacidade" da prova de impacto não é demonstrável ali e mora no `fixed/` (item 8); os itens 3–4 são a metade "o flag é gravável por qualquer um".
6. **Vulnerable — alvo inexistente:** `POST /admin/users/nobody/promote` com Bearer válido → **`404`**.
7. **Fixed — o não-admin é recusado:** `POST /admin/users/alice/promote` com o Bearer do **`clancy`** (comum) → **`403`** (body `Forbidden`); `alice` **não** vira admin (o `403` sai antes da escrita).
8. **Fixed — a função funciona pra admin:** logar como `carol` (seed admin) e `POST /admin/users/bob/promote` → **`200`**. Sem/ruim token → `401`. Com o item 7, é a metade `fixed/` da prova de impacto: o que separa `200` de `403` é só o `is_admin` de quem chama.
9. **Fixed — `403` antes da busca:** um não-admin pedindo um `:handle` **inexistente** ainda recebe **`403`** (não `404`) — o gate roda antes do lookup, não vaza existência de alvo.
10. **`app.ts` DIFERE só pela guarda de papel** (`if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);` + o comentário) entre `vulnerable/` e `fixed/`. `POST /login`, helpers, imports, `USERS`, rodapé, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` **idênticos** entre as versões.
11. **Resposta não vaza dado alheio nem token:** o sucesso serializa só `{ handle, is_admin }`; nenhum campo de PII (os usuários não têm nome/endereço); nenhum token em resposta alguma. **Um bug só** (BFLA).
12. **Superfície mínima:** só `POST /login` e `POST /admin/users/:handle/promote`. **Sem** read, **sem** demote, **sem** índice de rotas, **sem** `GET /me`.
13. **Estado mutável:** escritas reais, mas nenhuma resposta do walkthrough depende do acúmulo — rodar a sequência duas vezes seguidas dá status e corpos idênticos. Gêmeos independentes (8204 não afeta 8304).
14. **API-only:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, sem render de HTML; sucesso sempre `application/json`.
15. **Bind/portas:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1`; container `ENV HOST=0.0.0.0`. **Portas 8204 (vulnerable) / 8304 (fixed)**, internas `3000`, coerentes entre `EXPOSE`, `app.listen` e o compose.
16. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README. (`clancy` é masculino no PT, e coincide com o masculino do papel — sem distinção a manter.)
17. **Theory primer:** re-confirmar por fetch a URL `https://portswigger.net/web-security/access-control` (200, sem redirect); texto do link "Access control vulnerabilities and privilege escalation", em inglês no PT. **Confirmar que NÃO é a página de IDOR de 01–03.**
18. **RFC 9110** citado como nesta spec: **§15.5.4 (403 Forbidden)** (credencial presente, insuficiente; `404` como `MAY` pra esconder existência) e, se útil, **§15.5.2 (401 Unauthorized)**. Texto bruto conferido nesta fase em `rfc-editor.org/rfc/rfc9110.txt`; **reconfirmar na geração** antes de cravar as citações.
19. **`npm audit --omit=dev` em cada gêmeo**, advisories esperados **registrados**. O átomo é vulnerável na **LÓGICA** (check de papel ausente), **não nas dependências** (idênticas a 01–03). Meta: zero advisory de runtime.
20. **`npm run typecheck` (`tsc --noEmit`, typescript 7.0.2) verde nos DOIS gêmeos** — inclusive o `vulnerable/` (vulnerável na lógica, não no tipo). Gate de **host/CI**, não do container. **Shape validado nesta fase** (ver "Validação de typecheck e runtime"): os dois gêmeos com `Map` saem exit 0; a guarda `!target` é forçada (`TS18048` sem ela); o `?.` no fix é exigido (`TS2532` sem ele); `USERS.has`/`USERS.get` compilam limpos.
21. **Prototype pollution fechada pelo `Map` — gate explícito nos DOIS gêmeos.** `POST /admin/users/__proto__/promote` e `POST /admin/users/constructor/promote` devolvem **`404`** no `vulnerable/` (com qualquer token válido); no `fixed/`, **`403`** para não-admin e **`404`** para admin. E, decisivo: **nenhuma propriedade é acrescentada a `Object.prototype`** — checar que `({}).is_admin` (ou qualquer objeto sem `is_admin` próprio) continua `undefined` depois dessas requests. (Validado em protótipo nesta fase; ver "Validação de typecheck e runtime".) **Se algum desses devolver `200` ou poluir o protótipo, a correção `Map` não foi aplicada — PARE.**
22. **Frases-âncora:** cada uma numa casa só (WALKTHROUGH: indiferença ao alvo; DIFF: o fix não checa o alvo, só o papel); **não** reusar as âncoras de 01/02/03 — em especial, manter distância da de 03 ("which question it answers").
23. **Cross-ref:** 01–03 citados/contrastados (a troca de categoria é a lição); **nenhum** átomo de API 05+; **nenhuma** antecipação de "BFLA por método".

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; toolchain herdado e lido dos arquivos de 01–03; URL do primer e seções do RFC 9110 verificadas por fetch/texto bruto nesta fase; shape TS e a prototype pollution validados em protótipo com o toolchain exato (ver "Validação de typecheck e runtime"). Resto é validação de smoke test na Fase 2.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **vira a página da série** — de objeto (API1/BOLA) pra função (API5/BFLA). Cada doc deve deixar o contraste visível: 01–03 perguntavam sobre a **instância** — *é este objeto seu?* (01/02), *é desta loja?* (03); aqui a pergunta é sobre a **capacidade**: *você pode invocar esta operação?*. Se o aluno sair achando que "li o dado de outra pessoa", o átomo falhou — por isso a função **muda estado e não devolve dado alheio**.
- **A função admin NÃO lê objeto.** Promover muda estado; a resposta é o **delta aplicado** (`{handle, is_admin:true}`, `true` literal — não revela o estado anterior), não um registro privado. Os usuários **não têm** nome/endereço — não há PII pra confundir com leitura. Se a geração sentir vontade de devolver "o registro do alvo", **PARE**: isso puxaria o átomo de volta pra BOLA.
- **O passo de contraste decisivo é o auto-promote.** `clancy` promovendo `clancy` é inatacável sob a lente de objeto (é o registro dele) e **mesmo assim** é a falha — porque o eixo é a operação. É o argumento que separa BFLA de BOLA; não cortar, não enfraquecer.
- **Descoberta é premissa, não passo.** O endpoint é conhecido (uma frase no README/Context). **NÃO** criar endpoint de descoberta, índice de rotas, nem erro que confirme existência (seria information disclosure, 2º bug). Creditar o **02** (publicado) como precedente de premissa declarada — lá era a lição, aqui é economia.
- **Fix = guarda de papel do chamador, logo depois da autenticação.** `if (!USERS.get(caller)?.is_admin) return 403`, antes da busca do alvo. **NÃO** é o predicado de posse de 01/02 nem o lookup escopado de 03 — e dizer por que o fix é diferente faz parte da lição.
- **Status `403`, não `404`.** Argumento próprio: alvo é função conhecida (sem id-space, sem oráculo); RFC 9110 §15.5.4 (credencial insuficiente). O argumento de `404` de 01–03 **não transfere** — explicar por quê. **Não** copiar `404` por reflexo da série.
- **Estado mutável:** primeiro átomo cujo endpoint atacado escreve. Escritas reais, mas nenhuma resposta depende do acúmulo — os passos repetem em qualquer ordem; **sem demote**. Gêmeos independentes.
- **Impacto honesto:** escalação **vertical** de privilégio (ganhar papel admin); **não** chamar de horizontal, **não** de RCE. A prova de impacto é **composta pelos dois gêmeos** — o flag governa a capacidade (`fixed/`), e o flag é gravável por qualquer um (`vulnerable/`) —, não um dump de dados. **Não** afirmar, dentro do `vulnerable/`, um efeito do flag: lá nenhum papel é lido.
- **Elenco:** `clancy` atacante **masculino** (concordância coincide com a do papel — "o chamador", "o admin"); `alice` vítima; `bob` alvo da promoção legítima da `carol` no `fixed/`; `carol` a admin legítima. Reuso do elenco da série; sem personagem novo.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# bfla-admin-function — Broken Function Level Authorization (BFLA)`. Headers de seção **traduzidos** no PT; termos técnicos em inglês.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série (id + classe + 1 linha), quando o mantenedor cortar a fase.
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 04 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): todos os itens do checklist acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8204` (vulnerable), `127.0.0.1:8304` (fixed). Bind **só** em `127.0.0.1`.

---

## Verificação factual dos átomos publicados (conferida LENDO os arquivos nesta fase)

A spec afirma herança e contraste com 01–03; tudo abaixo foi conferido **lendo os arquivos publicados nesta fase de planning** (não de memória):

1. **Toolchain** — os seis `package.json` (01/02/03 × vulnerable/fixed) com express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; scripts `start: tsx app.ts`, `typecheck: tsc --noEmit`; `name` por átomo, `private: true`, `type: module`.
2. **`package-lock.json`** — resolve as mesmas cinco versões; idêntico entre os gêmeos de cada átomo (lockfiles diferem só no `name`).
3. **`Dockerfile`** — **md5 idêntico nos seis**: `node:24.21.0-slim`, `npm ci --omit=dev`, `COPY tsconfig.json` + `COPY app.ts`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm","start"]`.
4. **`tsconfig.json`** — **md5 idêntico nos seis**: `nodenext`, `target/lib es2024`, `types [node]`, `strict`, `noUncheckedIndexedAccess`, `esModuleInterop`, `noEmit`.
5. **`docker-compose.yml`** — bind `127.0.0.1`; `8201/8301` (01), `8202/8302` (02), `8203/8303` (03).
6. **Bloco de auth** — linhas 1–23 dos três `app.ts` **byte-idênticas** (md5 batendo): `USERS = new Set(["clancy","alice","bob","carol"])`, `TOKENS = new Map`, `issueToken` com `randomBytes(24).toString("base64url")`, `authenticate` por `Bearer`. **Este átomo muda `USERS` de `Set<string>` pra `Map<string, User>`** — a única mudança estrutural que a classe exige; `TOKENS` continua `Map<string,string>`, e `USERS.has(user)` no `POST /login` é a mesma forma que 01–03 (o `Set` e o `Map` compartilham `.has`).
7. **Elenco** — `clancy` é o atacante (masculino) em código e docs PT ("o `clancy` faz login como ele mesmo", "você esteve autenticado como `clancy`"); `alice`/`bob`/`carol` são o resto do elenco. (No seed do 01 o `clancy` é dono do pedido `1007`, customer "Omar Haddad"; no 02 o mesmo pedido, espelhado, tem o id UUID `edec4558-0cf5-4462-aaba-308229ff6c4f`, com o comentário `was 1007` no código.)
8. **Fix de 01/02** — `if (!order || order.owner !== caller) return res.sendStatus(404);` (predicado de posse **depois** da busca); comentário `FIXED:` com "(a 403 here would be an enumeration oracle)".
9. **Fix de 03** — `const order = ordersOf(req.params.storeId).find(...)` (move a **busca** pro escopo do pai); a guarda `!order` **não** é forçada pelo tipo em 03 (nada desreferencia `order`).
10. **Status de 01–03** — os três devolvem `404` indistinguível pro pedido fora do escopo, por caminhos diferentes. **01:** pra fechar o oráculo de enumeração sobre id sequencial; o DIFF de 01 cita **RFC 9110 §15.5.4 e §15.5.5** e o precedente do GitHub, e fecha com a regra *"`404` when existence itself leaks; `403` when admitting existence is fine"*. **02:** por herança do fix do 01 — o DIFF do 02 registra que, com UUIDs, a pressão do oracle *"all but vanishes"*, e herda o argumento do 01 por referência. **03:** pelo mesmo critério do 01, que lá dá `403` pra loja (slug público) e `404` pro pedido (contador global).
11. **Trilha** — 01/02 usam Repeater + Intruder; 03 só Repeater (sem Intruder). Este átomo: **só Repeater** (sem Intruder).
12. **READMEs de 01–03** — banner de aviso; primer PortSwigger **IDOR** (`/web-security/access-control/idor`); `API1:2023` em texto simples, **sem** link OWASP; frase do login sem senha como atalho.
13. **Publicação** — `atoms/api/ROADMAP.md`: 01/02/03 `[x]`, 04 (`bfla-admin-function`) `[ ]`, 05 (`bfla-method-based`) `[ ]`; a tabela de Cobertura tem a linha **API5** apontando os dois `bfla-*`. Árvore de `atoms/api/`: só a pasta `API1-broken-object-level-authz/` existe (três átomos) — nenhuma pasta `API5-*` ainda.
14. **H1** — os três: `# <id> — Broken Object Level Authorization (BOLA)`, idêntico EN/PT. Este átomo segue a forma: `# bfla-admin-function — Broken Function Level Authorization (BFLA)`.
