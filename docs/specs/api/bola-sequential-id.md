# Spec — Átomo API 01: `bola-sequential-id`

> Documento de especificação para o Claude Code implementar o **primeiro átomo da série API** do projeto `atomicvulns` (Fase 1 API, "Authorization: Object & Function", milestone `v1.1`; **não** fecha a fase). Este átomo é **BOLA — Broken Object Level Authorization**, o **API1:2023**, item **#1** do **OWASP API Security Top 10 (2023)**. Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **Átomo-bandeira e referência de estilo da série API.** É o **primeiro átomo TypeScript/Express/`tsx` do repo** — não há átomo TS in-repo pra espelhar (todos os publicados são Python/Flask). Ele **estabelece** o padrão TS da série: forma do `app.ts`, do `package.json`/`tsconfig.json`, do `Dockerfile` Node, do WALKTHROUGH/DIFF/README. O Claude Code da Fase 2 **não deve procurar um espelho TS que não existe** — segue este spec + `CLAUDE.md` §3 (a stack é lei da série).
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **`atoms/web/A01-broken-access-control/bola-rest/` — o gêmeo web desta MESMA classe.** BOLA em Flask. Já cravou a lição-coração ("authenticated ≠ authorized"), o fix `404` indistinguível, e o "id público por design de API". **Este átomo NÃO reinventa essa lição — ele a credita e a escala.** Ver "O que este átomo acrescenta".
> 2. **`atoms/web/A01-broken-access-control/idor-numeric-id/` — o avô do arco.** Primeira formulação de "o bug é a checagem AUSENTE, não input que virou código", e do passo de contraste "o que a vuln NÃO é". Reusar o vocabulário de broken access control e o framing "não greppa por string perigosa; audita-se lendo o endpoint e perguntando 'cadê o check de dono?'".
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Identidade

- **ID:** `bola-sequential-id`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API1 — Broken Object Level Authorization**
- **Pasta:** `atoms/api/API1-broken-object-level-authz/bola-sequential-id/`
- **Número sequencial (série API, conta do 01):** 01
- **Porta vulnerable:** `127.0.0.1:8201`
- **Porta fixed:** `127.0.0.1:8301`
- **Porta interna do container:** `3000` (idiomática do Node/Express). Compose mapeia `127.0.0.1:8201:3000` (vulnerable) e `127.0.0.1:8301:3000` (fixed).
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Express); exposição host restrita a `127.0.0.1` pelo compose.
- **Fase / milestone:** Fase 1 API, `v1.1` (primeiro átomo da fase; **não** fecha a fase — release fica pra depois, fora desta spec).
- **Branch de trabalho:** `atom/bola-sequential-id` (CLAUDE.md §6). Já criada nesta fase de planning.
- **H1 dos READMEs (idêntico em EN e PT):** `# bola-sequential-id — Broken Object Level Authorization (BOLA)`. O título nomeia a **classe**; o slug qualifica a variante (CLAUDE.md §5). **Nota:** o H1 é o **mesmo** do web `bola-rest` — de propósito: é a mesma classe. O que distingue os átomos é o slug, a série e a *demonstração* (ver "O que este átomo acrescenta"). Não é conflito; não "corrigir".
- **Theory primer:** ver seção "Theory primer" (URL já verificada por fetch nesta fase).

---

## Classe de vulnerabilidade

**BOLA (Broken Object Level Authorization).** Uma API REST serve um objeto privado (um pedido) por `GET /orders/:id`, **autentica** o chamador (Bearer inválido → `401`), e ainda assim devolve o objeto **sem cruzar o dono do objeto (`order.owner`) com a identidade autenticada**. É o **API1:2023**, o #1 do OWASP API Security Top 10 — e a face de API do IDOR: mesma causa raiz (**object-level authorization ausente**), mesmo fix (cruzar dono do objeto com o chamador).

### A lição-coração

> **"Estar autenticado não é estar autorizado."**
> Um token válido prova **quem você é**; não diz nada sobre **se este objeto é seu.**

O endpoint valida o token — você está autenticado **de verdade**, como **você mesmo**, com um token **legítimo emitido pelo servidor** — e mesmo assim serve o pedido de outro usuário, porque **nunca cruza o dono do pedido com o dono do token**. A armadilha em que **dev e atacante caem:** *"o request é autenticado, logo o acesso é legítimo."* É falso.

### Dois eixos, separados o tempo todo

Manter os dois eixos **distintos** em todo o material — confundi-los é o erro didático que este átomo precisa evitar:

- **ID sequencial = condição de DESCOBERTA.** O id contíguo (`1001…1012`) é o que torna a enumeração **fácil**: sabendo um id, o atacante deduz os vizinhos. Isso governa *quão rápido* a base inteira sai.
- **Check ausente = a CAUSA.** O que **permite** a leitura cross-user é a ausência do check de dono — não o formato do id. Um id não-adivinhável só encareceria a **descoberta**; não consertaria o **check**. *(Esta é a única frase sobre id não-adivinhável que a spec autoriza: enuncie o princípio, mas **NÃO** demonstre, **NÃO** monte variante com UUID, **NÃO** aluda a nenhum outro átomo — ver "Política de cross-ref".)*

O fix age no **segundo** eixo (o check), e deixa o **primeiro** (id sequencial) **intacto** — provando que o formato do id nunca foi o problema.

### Por que API1 (Broken Object Level Authorization)

O bug **não é** "input virou código" (injection). É **"um request legítimo alcançou um objeto fora do seu escopo autorizado"** — o chamador pediu um pedido que não é dele e a API entregou. Isso é controle de acesso a objeto: **API1** no OWASP API Security Top 10 **2023**. Situe nessa edição, **sem arqueologia** de edições antigas (CLAUDE.md §5). Por ser vuln de **lógica/autorização** (Trigger, não Payload), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório (ver "Walkthrough", Step de contraste).

---

## O que este átomo acrescenta (vs. o web `bola-rest`)

**Ponto de honestidade pedagógica:** o web `bola-rest` (Flask) já é BOLA e já ensinou o núcleo — "authenticated ≠ authorized", o fix `404` indistinguível, o "id público por design". Este átomo **não finge inventar** nada disso; ele **credita `bola-rest`** e acrescenta **quatro eixos novos**, que são a razão de ele existir na série API:

1. **Stack TS/Express — o átomo-bandeira da série API.** Primeiro TypeScript/Express/`tsx` do repo. Estabelece o padrão de código, container e docs da série. Por si só isso justifica o átomo: a série API precisa de um átomo de referência de estilo, e BOLA (API1) é o começo natural do OWASP API Top 10.
2. **Escala → "a base vazou", não "um objeto vazou".** O `bola-rest` tinha 2 usuários, 3 pedidos, **uma** vítima, e parava em "3 leituras provam o bug". Aqui são **4 usuários, 12 pedidos, distribuição DESIGUAL**, o atacante dono de **exatamente 1**, e os outros 11 espalhados entre **três** vítimas. A enumeração revela **múltiplas vítimas** — o salto de "um objeto vazou" pra "a base inteira vazou".
3. **PII — o achado que dói na screenshot.** Cada pedido carrega **nome e endereço de entrega** da pessoa (fake óbvio, §8.3), além de item e valor. O `bola-rest` só tinha item+valor. O que faz o achado doer numa screenshot é o **dado pessoal**, não o `order_id`. Isso ancora o impacto real de BOLA (dados de pedido/conta carregam PII).
4. **Enumeração no Intruder — o movimento-assinatura.** O walkthrough **varre** a faixa `1001–1012` no Burp Intruder e mostra a coleção inteira saindo; depois repete a varredura contra o `fixed/` e mostra a **tela chapada** de `404` idênticos. É o beat que o `bola-rest` (Repeater-only) não tinha, e é o que torna concreto "a base vazou".

E um refinamento no **fix** (ver "Fix"): onde o `bola-rest` **acrescentou um `if`** de dono depois da busca, aqui a leitura correta é que **a própria busca passou a responder "esse pedido, deste dono"** em vez de "esse pedido" — o predicado de posse entra **na** busca. Diferença de forma que carrega a lição "o fix não é um remendo, é a operação certa".

> **Frame quotável (cravar no fechamento do WALKTHROUGH e no DIFF):** *No Flask, o `bola-rest` mostrou o bug num objeto só. Aqui, numa API de verdade, o mesmo check ausente não vaza um pedido — vaza a base: nome, endereço e compra de cada cliente, um `for` de ids de distância. O token prova que você é você; ele não diz de quem é este pedido.*

---

## Feature simulada — API REST de pedidos (API-only, sem HTML)

**Pedidos (orders).** Uma API REST de e-commerce: cada pedido tem id, dono, o nome e endereço de entrega do cliente, o item e o valor. O cliente autentica com um token e lê os seus pedidos. Do ponto de vista do dev, "o cliente só vê os pedidos dele" — mas o endpoint de detalhe esqueceu de garantir isso.

**API-only por natureza** (CLAUDE.md §3.3 — a série API é API-only): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`. Requests com corpo JSON no `POST /login`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl** (ver "Walkthrough").

---

## Autenticação — token opaco, cripto-forte

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados e devolve `{ "token": "<opaco>" }`. O servidor guarda um mapa `token → usuário` **em memória** e resolve por lookup. **NÃO é JWT** (mesma razão do `bola-rest`: um JWT puxaria o foco pra *atacar o token*, o que **não** é a lição — o ataque deste átomo **não toca** o token; ele fica válido e do próprio atacante o tempo todo).

**O token DEVE ser gerado com `crypto.randomBytes` (aleatoriedade criptográfica).** Isto é **não-negociável** e a spec crava a razão:

> Um token **previsível** aqui seria uma **SEGUNDA vulnerabilidade** no átomo (broken authentication / token forjável) e violaria "um átomo = uma vuln" (CLAUDE.md §2). O token tem que ser **sólido** justamente pra que a **única** falha em jogo seja a object-level authorization ausente. (No arco da série há espaço pra um átomo sobre token previsível — mas **não é este**, e a spec **não** o cita.)

Sugestão de geração (a Fase 2 confirma a forma idiomática): `randomBytes(24).toString("base64url")` — valor opaco url-safe, análogo ao `secrets.token_urlsafe(24)` do `bola-rest`.

**Quatro usuários seedados** (handles de login; sem senha — auth real é fora de escopo, como o `X-User-ID` self-asserted dos átomos IDOR web):

- **`dana`** — a **atacante** (você). Faz login como si mesma, obtém o próprio token, e é dona de **exatamente 1** pedido.
- **`alice`, `bob`, `carol`** — as **vítimas**. Entre as três dividem os outros **11** pedidos, de forma **desigual** (ver "Store").

**Disciplina cravada (no WALKTHROUGH e no DIFF):** o ataque deixa o token **INTACTO e VÁLIDO** — nunca é decodificado, adulterado nem forjado. O alvo é o **endpoint que serve o objeto sem checar dono**. **PROIBIDO** mencionar técnicas de ataque a token (decode, forjar, `alg:none`, trocar `sub`): não é a lição, e não há átomo de JWT/token publicado pra referenciar.

---

## Store / dados — em memória, com PII fake

**Sem banco** (CLAUDE.md §3.4 — o storage segue a superfície do bug; BOLA é uma checagem ausente acima de qualquer store; store em memória é o típico da série API). Dados em estruturas TS. O `TOKENS` cresce a cada login; restart zera (aceitável no lab; notar no README).

```ts
type Order = {
  id: number;
  owner: string;      // login handle do dono — é isto que o check de autorização compara
  customer: string;   // nome do cliente no pedido — a PII que dói na screenshot
  address: string;    // endereço de entrega — fake óbvio
  item: string;
  amount: string;
};

// Ids são um contador GLOBAL, contíguo de 1001 a 1012 — pedidos adjacentes
// pertencem a donos diferentes. dana (você) possui só o 1007; os outros 11 se
// dividem DESIGUALMENTE entre alice (6), bob (3) e carol (2).
const ORDERS: Record<number, Order> = {
  1001: { id: 1001, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Mechanical keyboard",     amount: "$89.00"  },
  1002: { id: 1002, owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Noise-cancelling headset", amount: "$199.00" },
  1003: { id: 1003, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "USB-C hub",                amount: "$42.50"  },
  1004: { id: 1004, owner: "carol", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside",  item: "4K monitor",               amount: "$329.00" },
  1005: { id: 1005, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Laptop stand",             amount: "$55.00"  },
  1006: { id: 1006, owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Webcam",                   amount: "$75.00"  },
  1007: { id: 1007, owner: "dana",  customer: "Dana Lee",     address: "3 Testing Blvd, Faketon",     item: "Wireless mouse",           amount: "$29.90"  }, // attacker (you)
  1008: { id: 1008, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Desk mat",                 amount: "$19.00"  },
  1009: { id: 1009, owner: "carol", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside",  item: "Standing desk",            amount: "$589.00" },
  1010: { id: 1010, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Monitor arm",              amount: "$120.00" },
  1011: { id: 1011, owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "HDMI cable",               amount: "$12.99"  },
  1012: { id: 1012, owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Ergonomic chair",          amount: "$420.00" },
};
```

**Contagem (confira na geração):** alice = 6 (`1001,1003,1005,1008,1010,1012`), bob = 3 (`1002,1006,1011`), carol = 2 (`1004,1009`), **dana = 1** (`1007`). Total **12**, ids contíguos `1001–1012`, atacante dona de **exatamente 1**, split **desigual** entre as **três** vítimas, e o id da dana (`1007`) **no meio** da faixa.

**Por que este desenho (todos os traços são intencionais):**

- **Atacante dona de exatamente 1 pedido** (`1007`): a `GET /orders` da dana devolve **um** item. É o mínimo que prova "a API sabe perfeitamente quem você é e te escopa certo" — e ainda assim o detalhe vaza. O id `1007` no meio revela o **esquema** (contador global de 4 dígitos, contíguo): sabendo `1007`, os vizinhos `1001…1012` são dedutíveis.
- **Split desigual 6/3/2 entre três vítimas:** a enumeração não revela **uma** vítima repetida — revela **três pessoas distintas**, cada uma com nome/endereço/compras próprios. É o que faz "a base vazou" ser literal, e o que enche a screenshot de PII variada.
- **Contador global contíguo:** traço realista de API (um `orders.id` autoincrement compartilhado entre clientes). Reforça o eixo "id sequencial = descoberta barata".
- **Dado fake óbvio (§8.3):** nomes tipo "Alice Nguyen", ruas "Example Ave / Sample St / Placeholder Rd / Testing Blvd", cidades "Springfield / Faketon". **Sem PII real, sem cartão, sem segredo.** O impacto honesto é "nome + endereço + histórico de compra de cada cliente" — grave o suficiente sem inventar dado sensível de verdade.

---

## Rotas

Imports: `import express from "express";` e `import { randomBytes } from "node:crypto";`. Constantes e helpers (`USERS`, `TOKENS`, `issueToken`, `authenticate`, `ORDERS`) **idênticos** entre `vulnerable/` e `fixed/`.

Helpers (idênticos nas duas versões):

```ts
const USERS = new Set(["dana", "alice", "bob", "carol"]); // dana = attacker (you)
const TOKENS = new Map<string, string>();                 // opaque token -> username (in-memory; NOT a JWT)

function issueToken(user: string): string {
  const token = randomBytes(24).toString("base64url");    // crypto-strong opaque token
  TOKENS.set(token, user);
  return token;
}

function authenticate(req: express.Request): string | null {
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return TOKENS.get(token) ?? null;                        // username, or null -> caller aborts 401
}
```

### `POST /login` — obter o próprio token (idêntico nas duas versões)

Recebe `{ "user": "<nome>" }`, valida contra `USERS`, devolve um token opaco recém-emitido mapeado ao usuário. Sem senha (atalho de auth fora de escopo). Usuário desconhecido/ausente → `400` (higiene, ortogonal ao bug).

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

Token **fresco a cada login** (aleatório). Logins repetidos geram tokens distintos, todos válidos → o walkthrough usa **placeholder** (`<dana-token>`).

### `GET /orders` — listar os pedidos do próprio chamador (idêntico nas duas versões — o baseline CORRETO)

Autentica e devolve **só** os pedidos do chamador. **Corretamente escopado nas duas versões** — é o endpoint que **prova que a app sabe perfeitamente quem você é**. Para a dana, devolve exatamente `[1007]`.

```ts
app.get("/orders", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);
  res.json(Object.values(ORDERS).filter((o) => o.owner === caller)); // only the caller's own
});
```

> **A assimetria lista-vs-detalhe é a assinatura do BOLA.** A **lista** filtra certo por dono nas duas versões; só o **detalhe** (`GET /orders/:id`) esquece o mesmo check no vulnerable. Não é segunda vuln — é a prova de que o dev **sabia** filtrar (fez na lista) e **omitiu** no detalhe. Esta assimetria vira o **passo de contraste** (ver Walkthrough).

### `GET /orders/:id` — a rota VULNERÁVEL

Autentica (Bearer ruim → `401`: a **autenticação funciona**, de propósito), busca o pedido pelo id, e o devolve — **sem** confrontar `order.owner` com o chamador. Handler **≤ ~30 linhas** (CLAUDE.md §2.2 — este tem ~6).

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);        // AUTHENTICATION only
  const order = ORDERS[Number(req.params.id)];
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                        // BOLA — no object-level check
});
```

- **Source:** o `:id` do path (o objeto pedido) + o token no `Authorization` (a identidade — que o vulnerable **autentica mas ignora na autorização**).
- **Sink conceitual:** o retorno do pedido **sem** comparar `order.owner` com o chamador. O bug é **o que não está lá** — não greppa por string perigosa; greppa por endpoint que devolve objeto user-scoped e pergunta **"cadê o check de dono?"**. Agravante didático: o handler **chama `authenticate()`** (logo *parece* que cuida de identidade), mas **descarta** o resultado na hora de autorizar.
- **`Number(req.params.id)`**: id não-numérico vira `NaN`, lookup falha → `404` (higiene, idêntica nas duas versões). Id inexistente (`1013`, `1000`) → `404`.

---

## Fix — o predicado de posse entra NA busca

O gêmeo `fixed/` difere **APENAS no predicado de posse** da busca do `GET /orders/:id`. **Nenhuma outra linha muda** — `POST /login`, `GET /orders`, helpers, imports, `Dockerfile`, `package.json`, `tsconfig.json` são **idênticos**.

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);
  const order = ORDERS[Number(req.params.id)];
  // FIXED: the lookup now answers "this order, of this owner" — not just "this order".
  // 404 (not 403), identical to the not-found 404 below, so "exists but not yours" is
  // indistinguishable from "doesn't exist": with sequential ids a 403 would be an oracle.
  if (!order || order.owner !== caller) return res.sendStatus(404);
  res.json(order);
});
```

Diff mínimo (o eixo único):

```diff
   const order = ORDERS[Number(req.params.id)];
-  if (!order) return res.sendStatus(404);
-  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
-  // order.owner is the caller. Authenticated is not authorized for THIS object.
-  res.json(order);                                        // BOLA — no object-level check
+  // FIXED: the lookup now answers "this order, of this owner" — not just "this order".
+  // 404 (not 403), identical to the not-found 404, so "exists but not yours" is
+  // indistinguishable from "doesn't exist": with sequential ids a 403 would be an oracle.
+  if (!order || order.owner !== caller) return res.sendStatus(404);
+  res.json(order);
```

**A leitura correta do fix (cravar no DIFF):** **não** é "acrescentou um `if`". É que a **busca passou a responder "esse pedido, deste dono"** em vez de "esse pedido". O predicado de posse (`order.owner !== caller`) entra **na mesma linha de guarda** da existência (`!order`) — as duas negações compartilham o mesmo `return res.sendStatus(404)`, então "não é seu" e "não existe" são **o mesmo código, o mesmo status, o mesmo corpo, o mesmo shape**, por construção. É a diferença de forma em relação ao web `bola-rest`, que adicionou um `if` de dono **separado** depois da busca; aqui a autorização é **a própria busca**, não um remendo posterior.

**CRAVAR no DIFF (o que o fix NÃO faz):** ele **não** troca o id sequencial por UUID, **não** o randomiza, **não** o esconde. O id permanece exatamente tão público e sequencial quanto antes. **O id ser trivial/sequencial é PARTE da lição** (eixo 1 = descoberta), e a correção é **só** a autorização por objeto (eixo 2 = causa). Trocar o id seria consertar o eixo errado.

---

## Status code do fix: `404` (não `403`) — não deixar a negação virar oráculo

O fix retorna **`404`** para pedido de não-dono, **NÃO `403`**. E o `404` de objeto alheio é **byte-idêntico** ao `404` de objeto inexistente — mesmo status, mesmo corpo, mesmo shape. **Motivo:** o fix não é só **negar** o acesso; é **não deixar a negação virar oráculo**.

- **Id SEQUENCIAL → um `403` seria um oráculo de enumeração.** `403` confirma existência ("existe, mas você não pode"); `404` de inexistente nega. Com ids contíguos, o par `403`/`404` deixaria a dana **mapear quais ids existem** varrendo `1000…9999`, mesmo sem ler o conteúdo. O `404` uniforme **não vaza existência** — a atacante não consegue nem saber quais ids existem.

**Ancorar no mundo real (obrigatório no DIFF):**

- **Repositório privado no GitHub devolve `404`, não `403`**, justamente pra não confirmar que o repo existe a quem não tem acesso. É o mesmo movimento: esconder a **existência**, não só o **conteúdo**.
- **O RFC 9110 (HTTP Semantics) prevê a troca explicitamente.** Sobre o `404`: um servidor pode responder `404` em vez de `403` **de propósito** quando não quer revelar por que o acesso foi negado — ou seja, esconder a existência é um uso **previsto** do `404`, não um abuso. (Fase 2: citar como "RFC 9110 §15.5.5 (404 Not Found) e §15.5.4 (403 Forbidden)"; **confirmar os números de seção por fetch antes de cravar** — não inventar.)
- **`403` é a escolha legítima quando a existência do objeto NÃO é sensível.** Registrar isso com honestidade: `404`-por-oráculo é a escolha **deste** átomo porque o id é enumerável e a existência vaza; num contexto onde admitir existência é inócuo, `403` (semanticamente mais claro — "existe e não é pra você") é perfeitamente correto. O RFC 9110 oferece os dois; a escolha é sobre **sensibilidade da existência**, não sobre um estar "certo" e o outro "errado".

**Regra de bolso:** **`404`** quando a **própria existência vaza** (e id sequencial faz a existência vazar); **`403`** quando admitir existência é ok.

---

## Padrão de prova — Trigger

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **trocar um id** num request legítimo, com um token legítimo. Por ser **Trigger**, o **passo de contraste é obrigatório** (CLAUDE.md §5) — ver Walkthrough, Step 3.

---

## Walkthrough — estrutura e requests

Trabalhado **100% no Burp** (Repeater + Intruder), `curl` como equivalente — **API-only, SEM trilha browser** (CLAUDE.md §3.3). Cada request é um bloco colável: request-line + `Authorization: Bearer <token>` + corpo JSON quando houver. Tokens são **placeholders** (variam por login).

**Abertura direta, sem encenação de personagem** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de pedidos serve `GET /orders/:id` autenticando o chamador mas sem checar de quem é o pedido" — não um personagem. Defina todo termo não-óbvio na estreia (ex.: "BOLA (Broken Object Level Authorization)", "enumeration oracle", "opaque token").

### 1. Context
- API REST de pedidos; auth por Bearer token opaco; `GET /orders/:id` é o "ver um pedido". Isto é **BOLA** — o **#1 do OWASP API Security Top 10 2023 (API1:2023)**. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar o handler vulnerable. Apontar que ele **chama `authenticate()`** (autentica — `401` em token ruim) mas **não** compara `order.owner` com o chamador. O bug é **o que não está lá**. Pergunta de auditoria: **"onde este endpoint confere que o pedido é do chamador?"** → em lugar nenhum. Notar que **não greppa** (ausência de código) e que ter `authenticate()` ali **engana** o revisor apressado.

### 3. How auth works in this lab (subseção curta)
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo). O token é **real, emitido pelo servidor, cripto-forte** (`randomBytes`), mapeado ao seu usuário. Dois pontos: (i) a **autenticação É imposta** (token ruim → `401`); (ii) se a identidade do token é **usada pra autorizar o objeto** é outra pergunta — e o vulnerable não usa. **Disciplina cravada:** o ataque **não toca** o token (não decodifica, não adultera) — fica válido e da dana o tempo todo.

### 4. Baseline — capturar os tokens e ver o escopo correto
- `POST /login` com `{"user":"dana"}` → `{"token":"<dana-token>"}`. Bloco colável (request-line + `Content-Type: application/json` + corpo). *(O maintainer pediu login com "as duas contas": logar também como uma vítima — ex.: `{"user":"alice"}` → `<alice-token>` — pra ter, lado a lado, o token de quem PODE ver o pedido e o de quem NÃO pode. Serve ao contraste do Step 3.)*
- `GET /orders` com `Authorization: Bearer <dana-token>` → `200`, **só** o pedido da dana (`1007`). É a prova de que a API **sabe exatamente quem você é** e te escopa certo.
- `GET /orders/1007` com o Bearer da dana → `200`, o próprio pedido. A feature faz o que promete.

### 5. Step 1 — Read another owner's order (BOLA confirmado)
- A `GET /orders` te deu o id `1007`; ids são um **contador global contíguo**, então `1001…1012` existem e são de outros clientes. **Sem adivinhar, sem reconstruir** — você leu seu id e olhou os vizinhos.
- `GET /orders/1001` com o Bearer da **dana** → `200` com o pedido da **alice** — nome, endereço de entrega, item, valor. Bloco:
  ```
  GET /orders/1001 HTTP/1.1
  Host: 127.0.0.1:8201
  Authorization: Bearer <dana-token>
  ```
- Você leu o pedido de outro usuário — **com PII** — usando **o seu próprio token válido**, só trocando o id. Isso é **BOLA**.

### 6. Step 2 — What the vuln is NOT (passo de contraste OBRIGATÓRIO — CLAUDE.md §5)
Três requests que **isolam a causa** (é o desenho exato pedido pelo mantenedor):
- **(a)** `GET /orders/1001` **SEM** o header `Authorization` → **`401`**. A autenticação **funciona** — sem identidade, nada sai.
- **(b)** `GET /orders` **COM** o Bearer da dana → **escopo correto** (`200`, só o `1007`). O **mesmo** token produz escopo perfeito aqui.
- **(c)** o mesmo `GET /orders/1001` **COM** o Bearer da dana → **`200`**, pedido da alice. O **mesmo** token produz **escopo nenhum** aqui.

**Conclusão a escrever explicitamente:** o mesmo token dá escopo **correto** em (b) e escopo **nenhum** em (c). Logo **não é identidade quebrada nem impersonation** — você esteve autenticado como dana o tempo todo, e a app te escopou certo na lista. É **um check que existe num handler (`GET /orders`) e falta no outro (`GET /orders/:id`)**. A causa é a object-level authorization ausente no detalhe — não o token, não a identidade, não o formato do id. *(Aqui cabe a ÚNICA frase autorizada sobre id: "um id não-adivinhável só tornaria a **descoberta** mais cara; não colocaria o check de volta." Sem demonstrar, sem UUID, sem citar outro átomo.)*

### 7. Step 3 — Enumerate the whole collection (Intruder)
- Mandar `GET /orders/§id§` (id como posição de payload) pro **Intruder**, payload **numbers `1001–1012`**, Bearer da dana fixo. Rodar o ataque.
- **A coleção inteira sai:** 12 respostas `200`, 11 delas de pedidos que **não são da dana** — nome, endereço e compra de **alice, bob e carol**. É o que separa "um objeto vazou" de "**a base vazou**". Uma screenshot do painel de resultados do Intruder, com a coluna de PII, é o achado.
- *(Definir "Intruder" na estreia: a ferramenta do Burp que repete um request variando um valor por uma lista — aqui, os ids.)*

### 8. Why the fix works (porta 8301) — a tela chapada
Repetir a **mesma varredura** do Intruder (`1001–1012`, Bearer da dana) contra o `fixed/` em `127.0.0.1:8301`:
- **Só o `1007`** (o pedido da dana) volta `200`. Os **outros 11 viram `404` idênticos** — mesmo status, mesmo corpo. A **tela chapada** de `404` no Intruder **é a prova do fix**.
- `GET /orders/1007` com o Bearer da dana → `200` (dono lê o próprio). Autenticação ainda `401` sem/ruim token.
- **`404`, não `403`:** o `404` de não-dono é indistinguível do `404` de id inexistente (`1013` também dá `404`) — **sem oráculo de enumeração**. (Forward pro DIFF pra a discussão completa: GitHub `404`, RFC 9110, quando `403` é legítimo.)
- **O fix manteve o id sequencial** (não virou UUID) — prova de que o formato do id nunca foi o problema.

**O walkthrough TERMINA aqui.** Sem script de exfiltração, sem automação além do Intruder, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `tsconfig.json` em **cada** gêmeo, **self-contained, sem módulo compartilhado**. `app.ts` **difere** só no predicado de posse do `GET /orders/:id`; **todo o resto é idêntico** entre as versões, incluindo `Dockerfile`, `package.json`, `tsconfig.json`.

Rodapé do `app.ts` (idêntico nas duas versões):

```ts
const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";  // default 127.0.0.1 (CLAUDE.md §8.1)
app.listen(PORT, HOST);
```

`Dockerfile` (idêntico entre as versões; base Node 24 slim, **tag pinada — nunca `latest`**):

```dockerfile
FROM node:24-slim
WORKDIR /app
COPY package.json .
RUN npm install
COPY tsconfig.json .
COPY app.ts .
# Bind 0.0.0.0 inside the container so Docker port-forwarding reaches Express;
# host exposure stays restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 3000
CMD ["npm", "start"]
```

`docker-compose.yml` (bind **só** em `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8201:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8301:3000"
```

- `package.json` de cada gêmeo tem `"type": "module"` e `"scripts": { "start": "tsx app.ts" }` (entrypoint `tsx` — roda TS direto, sem step de build).
- **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **Pin exato do patch do Node** (`node:24-slim` pina o major/variante; a Fase 2 pode pinar mais fino, ex.: `node:24.x-slim`) — **nunca** `latest` nem `node` cru.

---

## Dependências extras

```json
{
  "dependencies": { "express": "5.x" },
  "devDependencies": {
    "tsx": "<pinada>",
    "@types/express": "5.x",
    "@types/node": "24.x"
  }
}
```

- **Express 5.x** com **`@types/express` 5.x** (o mantenedor cravou a major 5). `tsx` como entrypoint. `@types/node` casando com Node 24. `crypto` é **nativo do Node** (`node:crypto`) — não é dependência de pip/npm.
- **Versões pinadas e confirmadas na geração** (CLAUDE.md §8.7 — updates manuais). **Nada** além disto (CLAUDE.md §3.6): sem ORM, sem body-parser externo (Express 5 tem `express.json()` embutido), sem lib de token (é `randomBytes` nativo).

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). BOLA é IDOR num endpoint de API — mesma classe — então a página conceitual de **IDOR** do PortSwigger é a escolha CLAUDE.md-compliant (a mesma que o web `bola-rest`/`idor-numeric-id` usam).

- **Primer (verificado por fetch NESTA fase — a página existe, H1 "Insecure direct object references (IDOR)", intro conceitual "What are IDOR?"):**
  `https://portswigger.net/web-security/access-control/idor`
  Texto do link: **"Insecure direct object references (IDOR)"** — preservado em **inglês** também no README PT (CLAUDE.md §7).

- **Referência suplementar (na descrição do README, pra ancorar "BOLA = #1 do OWASP API Top 10" — verificada por fetch NESTA fase):**
  `https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization` (título "API1:2023 Broken Object Level Authorization").
  **Nota importante pra Fase 2:** a URL antiga `owasp.org/API-Security/editions/2023/...` (a que o web `bola-rest` usou) hoje faz **308 Permanent Redirect** pra esse host `api-security.owasp.org`. Usar o **destino canônico** direto, pra não deixar um redirect no README.

Formato exato EN:

```markdown
> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato exato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

---

## Política de cross-ref (CLAUDE.md §5 — CRÍTICO nesta série)

- **NENHUM átomo da série API está publicado.** Portanto **NÃO** citar nenhum outro átomo de API — por número, nome ou descrição (`bola-uuid-leaked`, `bola-nested-resource`, `bfla-*`, etc. são **proibidos**: forward reference).
- **Cross-ref a átomos WEB publicados é bem-vindo e esperado.** Contraste **explícito** com:
  - **`bola-rest`** (web/Flask, mesma classe) — o gêmeo web; creditar o núcleo (authenticated ≠ authorized, `404` indistinguível) e contrastar o que ESTE acrescenta (escala, PII, Intruder, stack TS, fix "na busca").
  - **`idor-numeric-id`** (web/Flask) — o avô do arco; reusar "o bug é a checagem ausente" e o passo de contraste.
- **Sobre id não-adivinhável:** enunciar em **UMA frase** que reduz descoberta sem consertar o check (eixo 1 vs eixo 2). **NÃO** demonstrar, **NÃO** montar variante UUID, **NÃO** citar nenhum átomo (web ou API) que trate de UUID/id opaco — o seam onde essa variante mora na série API é átomo **não-publicado**; mantê-lo fora do frame.
- Termos técnicos (BOLA, IDOR, token, Bearer, object-level authorization, ownership check, enumeration oracle, PII, Trigger, payload) **não** se traduzem no PT (CLAUDE.md §7).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API1 — Broken Object Level Authorization** | O #1 do OWASP API Security Top 10. Request legítimo alcançou objeto fora do escopo (autorização), não injection. |
| Nome / classe (H1) | **Broken Object Level Authorization (BOLA)** — idêntico EN/PT | O título nomeia a classe; o slug (`bola-sequential-id`) qualifica a variante. Mesmo H1 do web `bola-rest` de propósito (mesma classe). |
| Papel na série | **Átomo-bandeira + referência de estilo TS/Express** | Primeiro TS do repo; estabelece o padrão da série API. Não há espelho TS in-repo. |
| Stack | **TypeScript / Express 5.x / `tsx`**, Node 24 slim pinado | Lei da série API (CLAUDE.md §3.1). |
| Store | **Em memória (`Record`/`Map`/`Set`), sem banco** | BOLA não depende do storage; store em memória é o típico da série API. |
| Token | **Opaco, `crypto.randomBytes`; NÃO JWT** | Cripto-forte pra não ser 2ª vuln. JWT puxaria foco pra atacar o token (não é a lição). O ataque não toca o token. |
| Usuários / dados | **`dana` (atacante, 1 pedido) + alice/bob/carol (vítimas)** | Atacante escopado a exatamente 1 prova "a app sabe quem você é"; três vítimas → múltiplas pessoas na enumeração. |
| Seed de ids | **`1001–1012` contíguos; split 6/3/2/1 desigual; dana=1007 no meio** | Contador global (id sequencial = descoberta barata); split desigual → "a base vazou, não um objeto". |
| PII | **nome + endereço de entrega por pedido (fake óbvio §8.3)** | O achado que dói na screenshot é o dado pessoal, não o `order_id`. Ancora o impacto real de BOLA. |
| Rotas | `POST /login`, `GET /orders` (lista escopada — correto nas 2), `GET /orders/:id` (vuln) | REST mínimo. Sem prefixo `/api` (contraste de forma com o web `bola-rest`, que usa `/api/orders`). |
| O bug | **Object-level authorization AUSENTE** em `GET /orders/:id` | Ausência de código, não payload. O endpoint autentica mas descarta a identidade na autorização. |
| Fix (eixo único) | **Predicado de posse DENTRO da busca:** `if (!order \|\| order.owner !== caller) 404` | A busca passa a responder "esse pedido, deste dono". Não "acrescentou um if" (contraste de forma com o `bola-rest`). O id sequencial fica intacto. |
| Status code do fix | **`404`** (não `403`), idêntico ao `404` de inexistente | Id sequencial → `403` viraria oráculo de enumeração. `404` esconde existência. Ancorar: GitHub repo privado `404`; RFC 9110 prevê a troca; `403` legítimo quando existência não é sensível. |
| Padrão de prova | **Trigger** (não Payload) | Não há sink; o exploit é dado legítimo (trocar id). → passo de contraste obrigatório. |
| Trilha | **100% Burp (Repeater + Intruder) / curl; SEM browser** | API-only (CLAUDE.md §3.3). Intruder é o beat de enumeração (a base vazando). |
| Impacto | **Escalação HORIZONTAL** — ler pedido+PII de outros usuários do mesmo nível | Honesto, sem overclaim. Não é RCE, não é escalação vertical. |
| Theory primer | **PortSwigger IDOR (bloco) + OWASP API1:2023 (suplementar)** | CLAUDE.md manda PortSwigger; BOLA = IDOR em API. URLs verificadas por fetch nesta fase. |

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia `usuário→token` e o Bearer resolve de volta ao usuário correto; `dana`/`alice`/`bob`/`carol` recebem tokens **distintos**; `randomBytes(...).toString("base64url")` disponível e gera tokens **distintos** entre logins.
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido/corrompido → **`401`** em `GET /orders` e `GET /orders/:id`.
3. **Vulnerable:** `GET /orders/1001` (alice) com o Bearer da **dana** → **`200`** com o pedido da alice + PII (BOLA confirmado); o token permanece **válido e intacto**.
4. **Baseline correto:** `GET /orders` com o Bearer da dana lista **só** o `1007` (**não** vaza os das vítimas); `GET /orders/1007` → `200`.
5. **Enumeração:** Intruder sobre `1001–1012` com o Bearer da dana → **12 × `200`** no vulnerable (11 de outros donos, 3 vítimas distintas).
6. **Fixed:** a **mesma** varredura → `1007` = `200`, os outros 11 = **`404` idênticos**; `1013`/`1000` (inexistentes) também `404` (indistinguível — sem oráculo); `GET /orders/1007` = `200`; sem/ruim token = `401`.
7. **`Number(req.params.id)`** aceita os ids; não-numérico → `NaN` → lookup falha → `404`.
8. **`app.ts` DIFERE só no predicado de posse** do `GET /orders/:id`. `POST /login`, `GET /orders`, helpers, imports, `Dockerfile`, `package.json`, `tsconfig.json` **idênticos** entre as versões.
9. **Nenhum vazamento de token** em resposta alguma: `order` serializado tem só `id/owner/customer/address/item/amount`; `GET /orders` não devolve pedidos nem token de outro usuário. **Um bug só** (BOLA).
10. **API-only confirmado:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, `app.ts` **sem** render de HTML; todas as respostas de sucesso em `application/json`.
11. **Bind:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1:8201`/`8301`; container `ENV HOST=0.0.0.0`.
12. **Portas:** `8201` (vulnerable) / `8301` (fixed); porta interna `3000` coerente entre `EXPOSE`, `app.listen` e o mapeamento do compose.
13. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README.
14. **Theory primer:** re-confirmar as duas URLs por fetch na geração (podem mudar); confirmar os números de seção do RFC 9110 antes de cravar no DIFF.

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; as duas URLs do primer verificadas nesta fase. Resto é validação na geração.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este é o **átomo-bandeira da série API** e o **primeiro TS do repo**. Não há espelho TS in-repo — **estabeleça** o padrão (código, container, docs) seguindo este spec + CLAUDE.md §3. Cada parágrafo do walkthrough deve poder ser lido com o web `bola-rest` aberto ao lado; a diferença ("o mesmo check ausente, mas numa API de verdade, à escala, vaza a base com PII") tem que estar visível.
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `atoms/web/A01-broken-access-control/bola-rest/` **inteiro** (gêmeo web da classe — creditar, contrastar, NÃO reinventar) e `atoms/web/A01-broken-access-control/idor-numeric-id/` (avô do arco — passo de contraste, framing A01).
- **Dois eixos, sempre separados:** id sequencial = **descoberta**; check ausente = **causa**. O fix age no eixo 2 e deixa o eixo 1 intacto. A frase sobre id não-adivinhável é **uma só**, sem demonstração, sem UUID, sem citar átomo.
- **Token cripto-forte, intocado:** `randomBytes`; o ataque **nunca** decodifica/adultera/forja o token. **PROIBIDO** mencionar técnicas de ataque a token — não é a lição e não há átomo de token publicado.
- **O handler vulnerable CHAMA `authenticate()`** mas descarta a identidade — **não** transformar isso em "falha de autenticação". A distinção auth/authz é o ponto técnico frágil; seguir o passo de contraste à risca.
- **Fix "na busca", não "um if a mais":** o predicado de posse entra na linha de guarda da existência, compartilhando o `404`. É o contraste de forma com o `bola-rest`. Cravar a leitura "a busca passou a responder 'esse pedido, deste dono'".
- **`404` (não `403`):** cravar o oráculo de enumeração (id sequencial), o âncora GitHub, o RFC 9110 (confirmar §§ por fetch), e que `403` é legítimo quando a existência não é sensível. **Não** copiar `403` por reflexo.
- **Enumeração no Intruder é o beat que distingue este átomo:** "a base vazou", não "um objeto vazou". A varredura contra o `fixed/` (tela chapada de `404`) é a prova do fix.
- **Impacto honesto:** escalação **horizontal** + exposição de **PII**; **não** chamar de RCE nem vertical. BOLA ser #1 do OWASP API Top 10 é enquadramento, não inflação.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# bola-sequential-id — Broken Object Level Authorization (BOLA)`. Headers de seção **traduzidos** no PT; termos técnicos em inglês.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série (id + classe + 1 linha), quando o mantenedor cortar a fase.
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 01 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): itens 1–14 acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8201` (vulnerable), `127.0.0.1:8301` (fixed). Bind **só** em `127.0.0.1`.
