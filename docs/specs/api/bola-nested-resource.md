# Spec — Átomo API 03: `bola-nested-resource`

> Documento de especificação para o Claude Code implementar o **terceiro átomo da série API** do projeto `atomicvulns` (Fase 1 API, "Authorization: Object & Function", milestone `v1.1`; **não** fecha a fase). Classe: **BOLA — Broken Object Level Authorization**, **API1:2023** do OWASP API Security Top 10 (2023) — a mesma classe dos átomos 01 e 02, de propósito. Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **Este átomo não espelha os anteriores — ele inverte a premissa deles.** Em `bola-sequential-id` (01) e `bola-uuid-leaked` (02) o handler de detalhe não tinha check de autorização nenhum: erro de omissão. Aqui o check **existe, funciona e rejeita de verdade** — e é justamente ele que produz a falsa sensação de cobertura. Tudo o que esta spec afirma sobre os átomos 01 e 02 foi conferido **lendo os arquivos publicados nesta fase**, não de memória (ver "Verificação factual dos átomos 01 e 02").
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo publicado em `main`:**
> 1. **`atoms/api/API1-broken-object-level-authz/bola-sequential-id/`, inteiro** — átomo de referência da série: fonte da verdade do toolchain (§3.6), do bloco de auth, do seed e do argumento `404`/RFC 9110 no DIFF.
> 2. **`atoms/api/API1-broken-object-level-authz/bola-uuid-leaked/`, inteiro** — a tese de identidade do fix ("a correção não mudou nada") que este átomo **deliberadamente não repete**.
> 3. Átomos web de A01 (`idor-numeric-id`, `bola-rest`, `idor-uuid-guessable`) — leitura opcional. Citá-los é permitido; cada fato citado se confere lendo o átomo na hora.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF — isso é a Fase 2. Nada de alterar `CLAUDE.md` ou `ROADMAP.md`.

---

## Identidade

- **ID:** `bola-nested-resource`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API1 — Broken Object Level Authorization**
- **Pasta:** `atoms/api/API1-broken-object-level-authz/bola-nested-resource/`
- **Número sequencial (série API):** 03
- **Porta vulnerable:** `127.0.0.1:8203`
- **Porta fixed:** `127.0.0.1:8303`
- **Porta interna do container:** `3000` (igual a 01/02). Compose mapeia `127.0.0.1:8203:3000` e `127.0.0.1:8303:3000`.
- **Bind:** **somente** `127.0.0.1` no compose (CLAUDE.md §8.1); `ENV HOST=0.0.0.0` só dentro do container.
- **Fase / milestone:** Fase 1 API, `v1.1` (terceiro átomo; **não** fecha a fase).
- **Branch de trabalho:** `atom/bola-nested-resource` — criada nesta fase a partir de `main`.
- **H1 dos READMEs (idêntico em EN e PT):** `# bola-nested-resource — Broken Object Level Authorization (BOLA)`. Mesmo nome de classe de 01/02, de propósito; o slug qualifica a variante.
- **Theory primer:** ver seção "Theory primer" (URL verificada por fetch nesta fase).

---

## A tese do átomo

> **Autorização presente não é autorização suficiente — o que importa é qual pergunta ela responde.**

O handler vulnerável tem **três** decisões, e só uma delas está errada:

1. **Autenticação** — Bearer inválido → `401`. Funciona.
2. **Autorização no pai** — "a chamadora é operadora da loja `{storeId}`?" Se não → `403`. **Funciona e rejeita de verdade.**
3. **Escopo do filho** — o pedido `{orderId}` é buscado na **coleção global** e devolvido, **sem nunca consultar o `storeId` do pedido**. É aqui que mora o bug.

O desenvolvedor vê autorização no handler — há até um `403` explícito — e não percebe que ela responde a pergunta **"você opera esta loja?"**, quando a pergunta que importa é **"este pedido é desta loja?"**. As duas perguntas têm o mesmo sujeito aparente (a loja do path), por isso parecem a mesma. Não são.

**Não faltava informação, faltava a pergunta.** O pedido **carrega** o próprio `storeId` — o dado necessário para autorizar corretamente está no objeto, e a resposta JSON até o exibe (`"storeId":"meadow"` num request feito por `/stores/harbor/...`). O handler só não pergunta. Isso é algo que os átomos 01 e 02 não podiam dizer: lá também faltava a pergunta, mas não havia autorização nenhuma no handler para ser confundida com ela. *(Frase-âncora do DIFF — ver "Frases-âncora".)*

Consequências que amarram a spec inteira:

- **O check do pai é GENUÍNO** e aparece mordendo no walkthrough (`403`). Sem isso o átomo vira repetição do 01 com um parâmetro a mais.
- **O fix não é o de 01/02.** Lá se acrescentava o predicado de posse à guarda depois da busca; aqui a **busca** passa a acontecer **dentro do escopo do pai**. A tese de identidade do 02 (fix byte a byte igual) **não se repete** — três átomos com o mesmo fix seria sinal de que o terceiro não precisava existir.
- **Dois status codes, um critério:** `403` no pai, `404` no filho — ver "Dois status codes, um critério".

---

## Classe de vulnerabilidade

**BOLA (Broken Object Level Authorization) em recurso aninhado.** Um *nested resource* (recurso aninhado) é um objeto endereçado **através do pai** no path — aqui, `GET /stores/{storeId}/orders/{orderId}`: o pedido (filho) é pedido "dentro" de uma loja (pai). O BOLA aninhado acontece quando a API autoriza o **pai** e entrega o **filho** sem conferir que o filho pertence àquele pai. É **API1:2023**, o #1 do OWASP API Security Top 10 — mesma classe de 01/02; a variante é a forma do erro: não um check ausente, mas um check **presente e mal endereçado**.

**Por que API1:** um request legítimo alcança um objeto fora do escopo autorizado — o chamador pediu um pedido que não é da loja que ele opera, e a API entregou. Controle de acesso a objeto, não injection. Situe na edição 2023, **sem arqueologia** (CLAUDE.md §5). Referência OWASP em **texto simples** (`API1:2023`), **sem link** — o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (template, seção "Theory primer").

---

## O que este átomo acrescenta (vs. 01 e 02)

**Honestidade pedagógica:** 01 e 02 já ensinaram o núcleo de BOLA (autenticado ≠ autorizado; fix `404` indistinguível; o formato do id não é a causa). Este átomo **credita e não reabre** nada disso. Ele existe por cinco eixos novos:

1. **Check presente, não ausente.** Primeiro átomo da série em que a autorização **existe e funciona** no handler vulnerável. A falha é de **endereçamento** (a pergunta errada), não de **omissão**.
2. **O dado carrega a resposta.** O pedido tem `storeId`; o bug é visível no próprio corpo da resposta (`storeId` do objeto ≠ `storeId` do path). "Não faltava informação, faltava a pergunta."
3. **O fix muda a busca, não a guarda.** A guarda de existência (`if (!order) return res.sendStatus(404);`) é **byte-idêntica** entre os gêmeos; o que muda é **onde** a busca procura. Contraste verdadeiro sobre o código: em 01/02 o `fixed/` **busca** o pedido alheio e **depois** o recusa; aqui o `fixed/` **nunca encontra** o pedido de outra loja.
4. **Dois status codes, motivos opostos, um critério.** `403` (existência da loja não é sensível) e `404` (existência do pedido é) no mesmo handler.
5. **Primeiro recurso aninhado do repo.** Verificado nesta fase: nenhuma rota publicada (web ou API) tem dois parâmetros de path.

> **O átomo cresce em relação ao 02** — e o crescimento é **só** a entidade nova: `STORES` (loja + vínculo operador→loja), o helper `operates()` e o helper `ordersOf()`. O pedido troca `owner` por `storeId`. Registrar no DIFF que o crescimento é o preço da variante (sem um pai de verdade não há recurso aninhado), não enfeite.

---

## Feature simulada — back-office de lojas (API-only)

**Back-office multi-loja.** Uma plataforma hospeda várias lojas; esta é a API que os **operadores** usam. O operador faz login, lista os pedidos da loja onde trabalha e abre um pedido pelo id. Do ponto de vista do dev, "o operador só vê pedidos da loja dele" — e o handler até confere que ele opera a loja do path. Só esqueceu de conferir que o pedido é daquela loja.

**API-only por natureza** (CLAUDE.md §3.3): sem `templates/`, sem HTML, sem browser. Respostas `application/json` via `res.json(...)`; erros via `res.sendStatus(...)` (igual a 01/02). Trilha 100% Burp/curl.

### Pai = loja, não o usuário (descartado de propósito)

O ROADMAP descreve o átomo com `/users/{id}/orders/{oid}`. O design fechado com o mantenedor **descarta o usuário como pai**, e a spec registra o motivo: com o usuário como pai, "o pai é meu?" é quase tautológico (`{id} === caller`), e a falha pareceria o átomo 01 com um parâmetro a mais. Com a **loja** como pai, pessoas são **operadoras** — trabalham lá, não *são* a loja —, e essa distância é o que faz "o pai é meu?" ser uma pergunta com conteúdo, respondida por um lookup de verdade (`STORES[storeId].operators`).

> **Divergência a resolver fora desta spec:** a linha do átomo 03 no `atoms/api/ROADMAP.md` ainda diz `/users/{id}/orders/{oid}`. Proposta ao mantenedor: corrigir a linha num commit próprio (`docs(roadmap): ...`), como foi feito para o átomo 02. **Não** alterada nesta fase (CLAUDE.md §10.2).

### Compartilhar dentro da loja é a feature, não a falha

**Requisito de walkthrough (uma frase, obrigatória):** operadores da **mesma** loja compartilham os pedidos dela **legitimamente** — isso é a feature. Sem essa frase o aluno, vindo de 01/02 (onde ler um pedido com o nome de outra pessoa **era** o bug), confunde compartilhamento com bug. No seed, `summit` tem dois operadores (`bob` e `carol`) que veem os mesmos cinco pedidos; e a própria `dana` vê todos os pedidos da `harbor`, comprados por outras pessoas. Texto sugerido (a Fase 2 ajusta a prosa, não o sentido):

> **EN:** *Operators of the same store legitimately share its orders — `bob` and `carol` both operate `summit` and see the same five orders, and you see every `harbor` order, whoever bought it. That sharing is the feature, not the flaw.*
>
> **PT:** *Operadores da mesma loja compartilham os pedidos dela legitimamente — `bob` e `carol` operam a `summit` e veem os mesmos cinco pedidos, e você vê todo pedido da `harbor`, seja quem for que comprou. Esse compartilhamento é a feature, não a falha.*

Lugar: no Baseline, logo depois que a `dana` lê o pedido `1011` da própria loja.

---

## Autenticação — idêntica aos átomos 01 e 02

`POST /login` recebe `{ "user": "<nome>" }` e devolve `{ "token": "<opaco>" }`; mapa `token → usuário` em memória; **NÃO é JWT**. O bloco de auth (imports, `USERS`, `TOKENS`, `issueToken`, `authenticate`) é **byte a byte** o de 01/02 (conferido: linhas 1–23 dos dois `app.ts` publicados são idênticas) — **copiar, não reescrever**. Token com `randomBytes(24).toString("base64url")`: um token previsível seria uma segunda vulnerabilidade e violaria "um átomo = uma vuln" (CLAUDE.md §2). O ataque **não toca** o token.

**Usuários seedados (mesmo elenco de 01/02; agora operadores):**

- **`dana`** — a **atacante** (você). Operadora de **exatamente uma** loja: `harbor`. Nos docs PT, `dana` é **feminino** (CLAUDE.md §5: "a atacante", "você mesma", "a loja dela"); o masculino genérico vale pro **papel** ("o operador").
- **`alice`** — a **vítima principal**: operadora da `meadow`, a loja cujo pedido o walkthrough lê.
- **`bob`** e **`carol`** — operadores da `summit` (o exemplo de loja com dois operadores).

**Três camadas, separadas o tempo todo:** autenticação prova **quem você é** (`401`); o check do pai prova **que você opera a loja do path** (`403`); **nada** prova que o pedido é daquela loja. O átomo é sobre a terceira.

**Requisito de README (EN+PT) — declarar o atalho:** o login sem senha é **atalho deliberado do laboratório, não a vulnerabilidade**, e a autenticação é imposta (token ruim → `401`). Uma frase, sem citar átomo — mesmo requisito de 01/02.

---

## Store / dados — lojas, operadores, pedidos

Em memória (CLAUDE.md §3.4), sem banco. Restart zera os tokens (notar no README, como 01/02).

### Lojas e o vínculo operador→loja

```ts
// --- Stores: the parent resource ---
// People are OPERATORS of a store -- they work there; they are not the store. Every
// operator of a store legitimately sees all of that store's orders (that is the feature).
const STORES: Record<string, { operators: string[] }> = {
  harbor: { operators: ["dana"] },          // dana (you) operates exactly one store
  meadow: { operators: ["alice"] },
  summit: { operators: ["bob", "carol"] },
};

function operates(user: string, storeId: string): boolean {
  // The parent check: "does this user operate this store?"
  return STORES[storeId]?.operators.includes(user) ?? false;
}
```

- **`operates(user, storeId)` é o check do pai, com nome de pergunta.** O ponto didático está na **assinatura**: os argumentos são a chamadora e a loja. **O pedido não é argumento** — a pergunta, por construção, não pode ser sobre o pedido. O WALKTHROUGH ("Spot the bug") e o DIFF apontam isso; é verdadeiro sobre o código, sem adjetivo.
- **Ids de loja são slugs** (`harbor`, `meadow`, `summit`) e ids de pedido são inteiros (`1001`…). Escolha de **clareza**, não lição: com dois parâmetros no path, formatos distintos impedem o aluno de trocar um pelo outro (`/stores/harbor/orders/1009` não tem ambiguidade). Não promover a contraste pedagógico.
- **A existência das lojas é pública:** os três slugs estão no README, como nomes de estabelecimento. É isso que sustenta o `403` do pai (ver "Dois status codes").

### Pedidos — os doze dos átomos anteriores, redistribuídos

```ts
// --- In-memory store (no database) ---
type Order = {
  id: number;
  storeId: string;    // the store this order belongs to -- the data needed to authorize is right here
  customer: string;   // buyer's name on the order -- the PII (buyers never log in to this API)
  address: string;    // delivery address -- obviously fake
  item: string;
  amount: string;
};

// Order ids are ONE global counter shared by every store (1001..1012), so a store's own
// ids have gaps -- the gaps are other stores' orders. Same twelve orders as the previous
// atoms, redistributed across three stores: harbor 3, meadow 4, summit 5.
const ORDERS: Record<number, Order> = {
  1001: { id: 1001, storeId: "summit", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Mechanical keyboard",     amount: "$89.00"  },
  1002: { id: 1002, storeId: "meadow", customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Noise-cancelling headset", amount: "$199.00" },
  1003: { id: 1003, storeId: "summit", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "USB-C hub",                amount: "$42.50"  },
  1004: { id: 1004, storeId: "harbor", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "4K monitor",               amount: "$329.00" },
  1005: { id: 1005, storeId: "summit", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Laptop stand",             amount: "$55.00"  },
  1006: { id: 1006, storeId: "meadow", customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Webcam",                   amount: "$75.00"  },
  1007: { id: 1007, storeId: "meadow", customer: "Dana Lee",     address: "3 Testing Blvd, Faketon",     item: "Wireless mouse",           amount: "$29.90"  },
  1008: { id: 1008, storeId: "harbor", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Desk mat",                 amount: "$19.00"  },
  1009: { id: 1009, storeId: "meadow", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "Standing desk",            amount: "$589.00" },
  1010: { id: 1010, storeId: "summit", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Monitor arm",              amount: "$120.00" },
  1011: { id: 1011, storeId: "harbor", customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "HDMI cable",               amount: "$12.99"  },
  1012: { id: 1012, storeId: "summit", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Ergonomic chair",          amount: "$420.00" },
};

function ordersOf(storeId: string): Order[] {
  return Object.values(ORDERS).filter((o) => o.storeId === storeId);   // the store's scope
}
```

**Contagem (confira na geração):**

| Loja | Operadores | Pedidos | Compradores (`customer`) |
|---|---|---|---|
| `harbor` | `dana` | `1004`, `1008`, `1011` (3) | Carol Dias, Alice Nguyen, Bob Carter |
| `meadow` | `alice` | `1002`, `1006`, `1007`, `1009` (4) | Bob Carter ×2, Dana Lee, Carol Dias |
| `summit` | `bob`, `carol` | `1001`, `1003`, `1005`, `1010`, `1012` (5) | Alice Nguyen ×5 |

Total **12**, ids contíguos `1001–1012` num **contador global**. `id`, `customer`, `address`, `item` e `amount` de cada pedido são **idênticos** ao seed de 01 (conferido); só `owner` virou `storeId`.

**Pedidos em destaque no walkthrough:** `1011` (harbor — o pedido "da própria loja"), `1009` (meadow — o pedido alheio principal, Standing desk $589.00) e `1001` (summit — o segundo pedido alheio, Mechanical keyboard, o mesmo objeto que 01 e 02 liam).

### Por que este desenho (todos os traços são intencionais)

- **Três lojas, não duas.** O exploit precisa mostrar que o `orderId` não tem escopo **nenhum**: a `dana` lê pedidos da `meadow` **e** da `summit` pelo mesmo `/stores/harbor/...`. Com duas lojas o aluno pode inferir um vínculo entre a loja do path e a loja do pedido ("a outra loja") que não existe. Com três, fica claro que o `storeId` do path só decide se o check passa — não tem relação nenhuma com o pedido que volta.
- **Contador global de ids.** É o traço realista (um `orders.id` autoincrement compartilhado pela plataforma) **e** o que torna a busca global natural: um id globalmente único é exatamente o que "permite" ao handler pular o pai. Também dá a descoberta sem adivinhação: a lista da `harbor` devolve `1004, 1008, 1011`, e as lacunas (`1009`, `1010`, …) são pedidos de outras lojas — o `1009` está literalmente entre dois ids da própria `dana`.
- **Ids inteiros de 01, não UUIDs de 02.** O 02 já fechou que o formato do id não é a causa; este átomo não reabre esse eixo. Inteiros mantêm os paths de dois parâmetros legíveis.
- **Regra de distribuição: nenhuma loja tem pedido cujo comprador tem o nome de um operador dela.** Evita a leitura "o operador está lendo a própria compra" — que é exatamente o reflexo usuário-como-dono de 01/02 que este átomo quer quebrar. Conferir na geração: `harbor` sem Dana Lee; `meadow` sem Alice Nguyen; `summit` sem Bob Carter nem Carol Dias.
- **Espelhamento parcial, deliberado.** Os doze pedidos são os mesmos (itens, valores, nomes, endereços) para o aluno reconhecer o dado e perceber que **só a estrutura de autorização mudou**; a redistribuição é o que a nova entidade exige. Registrar no DIFF, em uma frase, que o espelhamento é parcial de propósito — diferente do 02, onde o espelhamento total era a prova.

### `customer` é o comprador, não um login

Os quatro nomes de comprador (Alice Nguyen, Bob Carter, Carol Dias, Dana Lee) são os mesmos quatro do seed herdado, e os logins são os mesmos quatro handles. **Neste átomo, compradores não fazem login** — todo login é um operador de loja — e **nenhuma decisão de autorização lê `customer`**. `customer`/`address` são só a PII que dói na screenshot. O README e o WALKTHROUGH (na primeira resposta que mostra um pedido) dizem isso em uma frase. Texto sugerido:

> **EN:** *`customer` is the buyer on the order — the same fake buyers as the previous atoms' seed. Buyers never log in to this API; every login is a store operator, and no authorization decision here reads `customer`.*
>
> **PT:** *`customer` é o comprador do pedido — os mesmos compradores fake do seed dos átomos anteriores. Compradores nunca fazem login nesta API; todo login é um operador de loja, e nenhuma decisão de autorização aqui lê `customer`.*

**Disciplina de redação (docs):** pedido se nomeia sempre por **loja + id** ("o pedido `1009` da `meadow`"), **nunca** por pessoa ("o pedido da alice"). A `alice` é vítima como **operadora da `meadow`**, não como compradora.

---

## Rotas

Imports: `import express from "express";` e `import { randomBytes } from "node:crypto";`. Bootstrap (`const app = express();` + `app.use(express.json());`), `USERS`, `TOKENS`, `issueToken`, `authenticate`, `STORES`, `operates`, `Order`, `ORDERS`, `ordersOf` e o rodapé `listen` são **idênticos** entre `vulnerable/` e `fixed/`. Superfície: **três rotas, nenhuma a mais.**

### `POST /login` — idêntica a 01/02 (copiar)

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

### `GET /stores/:storeId/orders` — listar os pedidos da loja (idêntica nas duas versões — o baseline CORRETO)

```ts
app.get("/stores/:storeId/orders", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);
  res.json(ordersOf(req.params.storeId));   // correctly scoped: only this store's orders
});
```

> **A assimetria lista-vs-detalhe continua sendo assinatura de BOLA** — com uma forma nova: a lista **lê do escopo da loja** (`ordersOf`); o detalhe vulnerável **lê da coleção global** (`ORDERS`). O helper de escopo existe no gêmeo vulnerável e é usado uma rota acima. O fix não inventa nada: usa no detalhe o escopo que a lista já usava.

### `GET /stores/:storeId/orders/:orderId` — a rota VULNERÁVEL

Handler **≤ ~30 linhas** (tem 10, contando abertura e fechamento).

```ts
app.get("/stores/:storeId/orders/:orderId", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);                        // AUTHENTICATION
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
  // VULNERABLE: the lookup is GLOBAL. The caller operates :storeId, but order.storeId is
  // never compared to it -- an order from ANY store comes back.
  const order = ORDERS[Number(req.params.orderId)];
  if (!order) return res.sendStatus(404);
  res.json(order);
});
```

- **Source:** os dois parâmetros do path + o token. **Sink conceitual:** a busca global — o pedido é devolvido sem que `order.storeId` seja comparado ao `storeId` autorizado.
- **O bug é o que não está lá, ao lado do que está.** O revisor apressado vê `operates(...)` e o `403` e conclui "tem autorização". Tem — para a loja. A pergunta de auditoria deste átomo: **"o objeto devolvido pertence ao pai que foi autorizado?"**
- **`if (!order) return res.sendStatus(404);` e `res.json(order);` sem comentário de linha**, para serem **byte-idênticos** entre os gêmeos (ver "Fix").
- **`Number(req.params.orderId)`:** não-numérico → `NaN` → `404` (idêntico nas duas versões). Id inexistente (`1013`) → `404`.

> **Rodapé (idêntico a 01/02):** `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);`

---

## Fix — buscar o filho dentro do escopo do pai

O `fixed/` difere **APENAS na linha da busca** (e no comentário acima dela). **Nenhuma outra linha muda** — nem o check do pai, nem a guarda de existência, nem o `res.json`.

```ts
app.get("/stores/:storeId/orders/:orderId", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);                        // AUTHENTICATION
  if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
  // FIXED: the order is looked up INSIDE the authorized store, not in the global collection --
  // an order from another store is simply not found, the same 404 as an id that never existed.
  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));
  if (!order) return res.sendStatus(404);
  res.json(order);
});
```

Diff mínimo (o eixo único):

```diff
   if (!operates(caller, req.params.storeId)) return res.sendStatus(403);  // parent check: real, and it bites
-  // VULNERABLE: the lookup is GLOBAL. The caller operates :storeId, but order.storeId is
-  // never compared to it -- an order from ANY store comes back.
-  const order = ORDERS[Number(req.params.orderId)];
+  // FIXED: the order is looked up INSIDE the authorized store, not in the global collection --
+  // an order from another store is simply not found, the same 404 as an id that never existed.
+  const order = ordersOf(req.params.storeId).find((o) => o.id === Number(req.params.orderId));
   if (!order) return res.sendStatus(404);
   res.json(order);
```

**A leitura correta do fix (cravar no DIFF):** o fix muda **onde a busca procura** — da coleção global para os pedidos da loja autorizada. É o equivalente em memória de trocar `SELECT … WHERE id = ?` por `SELECT … WHERE store_id = ? AND id = ?`: o filho é buscado **através** do pai. Consequências, todas verdadeiras sobre o código:

- **A guarda de existência é a mesma linha nos dois gêmeos.** "Não é desta loja" e "não existe" caem no **mesmo** `if (!order)` porque, no `fixed/`, um pedido de outra loja **não é encontrado** — não é encontrado e depois recusado. Indistinguibilidade por construção, sem tocar na guarda.
- **O pedido alheio nunca é materializado** no `fixed/`. Em 01/02, o `fixed/` busca o pedido alheio e **depois** o recusa na guarda (`!order || order.owner !== caller`); aqui a busca simplesmente não o alcança.
- **O check do pai não mudou** — continua certo, continua necessário (sem ele, qualquer operador leria qualquer loja pelo próprio path). O fix **acrescenta a pergunta que faltava**, não substitui a que existia.

**Limite da redação (template — "a leitura correta tem que ser VERDADEIRA"):** o predicado `o.storeId === storeId` existe — mora em `ordersOf`, o mesmo helper da lista. O DIFF **não** pode dizer "sem nenhum predicado" nem "a busca autoriza sozinha, magicamente". O que pode e deve dizer: o predicado de loja entrou **na busca**, não numa guarda depois dela, e é o **mesmo** escopo que a lista já aplicava.

**CRAVAR no DIFF — o fix NÃO é o dos átomos anteriores, e isso é deliberado.** Em 01 e 02 o fix era **acrescentar o predicado de posse** à guarda (`if (!order || order.owner !== caller) … 404`) — e o 02 fez questão de que fosse byte a byte o mesmo, porque a tese dele era identidade. Aqui a tese é outra, então o fix é outro: **buscar o filho dentro do escopo do pai em vez de buscá-lo global**. Escrever explicitamente que a tese de identidade do 02 **não se repete** aqui, e por quê: três átomos com o mesmo fix seria sinal de que o terceiro não precisava existir.

---

## Dois status codes, um critério — `403` no pai, `404` no filho

O handler corrigido responde `403` quando a chamadora não opera a loja e `404` quando o pedido não está na loja. **Isso é material central do DIFF** — e, mal escrito, lê como incoerência. Por isso a restrição de redação abaixo é dura.

**RFC 9110 (HTTP Semantics) — seções CONFIRMADAS por fetch nesta fase** (texto bruto em `rfc-editor.org/rfc/rfc9110.txt`, HTTP 200):

- **§15.5.4 — 403 Forbidden:** *"The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it."* … *"An origin server that wishes to "hide" the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found)."*
- **§15.5.5 — 404 Not Found:** *"… the origin server did not find a current representation for the target resource or is not willing to disclose that one exists."*
- (Seção-mãe: §15.5 — Client Error 4xx.) São as mesmas seções que o DIFF do `bola-sequential-id` já cita.

**O critério é um só: a existência do objeto é sensível?** O RFC oferece `403` como resposta honesta e o `404` como opção (`MAY`) para quem quer esconder existência. Aplicado duas vezes, dá respostas diferentes porque os objetos são diferentes:

- **Loja → `403`.** A existência de uma loja não é segredo: loja é estabelecimento, o slug é nome público (está no README). Esconder que a `meadow` existe não protege nada; `403` diz a verdade — "a loja existe e você não opera ela".
- **Pedido → `404`.** A existência de um pedido **é** sensível: com um contador global, um `403`-vs-`404` para "existe em outra loja" vs "não existe" viraria um enumeration oracle (oráculo de enumeração) — varrendo ids pelo próprio path, a operadora mapearia quais pedidos existem nas outras lojas (volume de vendas, cadência). O `404` preserva a indistinguibilidade que 01 e 02 estabeleceram: no `fixed/`, "não é desta loja" e "não existe" são idênticos.

**RESTRIÇÃO DE REDAÇÃO (DIFF):** os dois status se justificam **lado a lado, na mesma seção**, com o critério nomeado **uma vez** antes dos dois casos ("a existência do alvo é sensível?") e a conclusão explícita de que **o mesmo critério produz respostas diferentes porque os objetos são diferentes**. Proibido justificar o `403` numa seção e o `404` noutra; proibido apresentar um como "certo" e o outro como "concessão". O precedente do GitHub (repo privado → `404`) e a regra de bolso já estão no DIFF do `bola-sequential-id` — **referenciar**, não recontar.

**Dois detalhes que sustentam o argumento (registrar no DIFF, curto):**

- **Ordem dos checks:** o check do pai vem **antes** da busca. Uma chamadora que não opera a loja recebe `403` sem que o pedido seja consultado — então o `403` não vaza nada sobre pedidos, e o oráculo só poderia existir **dentro** de uma loja que ela opera, que é exatamente onde o `404` o fecha.
- **Loja inexistente → `403` também** (`operates()` devolve `false`). A pergunta "você opera esta loja?" tem resposta "não" para uma loja que não existe; como a existência de loja não é sensível, uniformizar não custa nada e mantém o check em uma linha. Não criar um `404` separado para loja.

---

## Padrão de prova — Trigger

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **combinar dois ids legítimos** — a loja que a atacante opera e um pedido de outra loja — num request legítimo, com token legítimo. Por ser Trigger, o **passo de contraste é obrigatório** (CLAUDE.md §5) — e aqui ele desmonta o mal-entendido mais provável: "não há autorização nenhuma no handler".

---

## Walkthrough — estrutura e requests

**100% Burp (Repeater), `curl` como equivalente — API-only, SEM browser** (CLAUDE.md §3.3). Tokens são placeholders (`<dana-token>`, `<alice-token>`); lojas e pedidos são **literais** (seed fixo). **Sem Intruder:** a tese deste átomo é qual pergunta o check responde, não escala — o beat de enumeração é a casa do `bola-sequential-id`.

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de back-office multi-loja serve `GET /stores/:storeId/orders/:orderId`; ela confere, corretamente, que você opera a loja do path, e devolve o pedido sem conferir que ele é daquela loja". Definir na estreia: "nested resource", "parent/child", "scope", "operator", "enumeration oracle".

**REQUISITO DE CLAREZA — rótulo em todo bloco.** Com dois parâmetros é fácil o aluno se perder. **Todo** bloco de request no WALKTHROUGH (EN e PT) é precedido de uma linha de rótulo que diz qual loja e qual pedido estão em jogo, e de quem é cada um. Formato:

> **EN:** `Store in the path: harbor (yours) · Order in the path: 1009 (a meadow order)`
>
> **PT:** `Loja no path: harbor (sua) · Pedido no path: 1009 (pedido da meadow)`

Blocos só de loja (a listagem) rotulam só a loja; o `POST /login` rotula quem está logando.

### 1. Context

API de back-office de lojas; auth por Bearer opaco; o recurso é **aninhado** (pedido dentro de loja). BOLA, **API1:2023**. O seed em uma frase: três lojas, a `dana` opera só a `harbor`; doze pedidos num contador global. Trilha 100% Burp/curl.

### 2. Spot the bug

Mostrar o handler vulnerável. Três linhas de decisão: `authenticate` (`401`), `operates` (`403`), a busca global. Apontar:

- **Há autorização, e ela funciona.** Não é o handler de 01/02.
- **Leia a assinatura:** `operates(caller, req.params.storeId)` — os argumentos são a chamadora e a loja; **o pedido não é argumento**. A pergunta não pode ser sobre o pedido.
- **A busca é global:** `ORDERS[...]`, enquanto a lista, uma rota acima, lê de `ordersOf(storeId)`. O dev sabia escopar pelo pai; não fez no detalhe.
- Não greppa: não há string perigosa — há uma pergunta faltando ao lado de uma que existe.

### 3. How auth works in this lab (subseção curta)

Token opaco via `POST /login`, sem senha (atalho), cripto-forte. Três camadas: autenticação (`401`), check do pai (`403`), escopo do filho (ausente). O ataque não toca o token.

### 4. Baseline — tokens, a própria loja, e o acesso autorizado

- `POST /login` `{"user":"dana"}` → `<dana-token>`; `POST /login` `{"user":"alice"}` → `<alice-token>`.
- `GET /stores/harbor/orders` com `<dana-token>` → `200`, **três** pedidos: `1004`, `1008`, `1011`. A API sabe que você opera a `harbor` e te escopa certo. *(Rótulo: loja `harbor`, sua.)* Aqui entra a frase do `customer` (comprador, não login).
- `GET /stores/harbor/orders/1011` com `<dana-token>` → `200`, HDMI cable, comprador Bob Carter, `"storeId":"harbor"`. *(Rótulo: loja `harbor` (sua) · pedido `1011` (da `harbor`).)* Aqui entra a **frase obrigatória do compartilhamento**: o pedido foi comprado por outra pessoa e você o vê — porque é da sua loja. É a feature.
- `GET /stores/meadow/orders/1009` com `<alice-token>` → `200`, Standing desk, `"storeId":"meadow"`. *(Rótulo: loja `meadow` (da alice) · pedido `1009` (da `meadow`).)* **É assim que o acesso autorizado ao `1009` se parece.** (No mundo real você não teria o token da alice; no lab você controla os dois logins só para ver o baseline.)

### 5. Step 1 — Read another store's order through your own store (BOLA confirmado)

- **Descoberta sem adivinhação:** a sua lista trouxe `1004, 1008, 1011`. Os ids são um contador global da plataforma, então as lacunas são pedidos de outras lojas — o `1009` está entre dois ids seus.
- `GET /stores/harbor/orders/1009` com `<dana-token>` → **`200`**, o pedido da `meadow`. *(Rótulo: loja `harbor` (sua) · pedido `1009` (da `meadow`).)* Apontar o corpo: **`"storeId":"meadow"`** num request que diz `harbor` no path. O dado sabe de quem é; o handler não perguntou.
- `GET /stores/harbor/orders/1001` com `<dana-token>` → **`200`**, o pedido da `summit`. *(Rótulo: loja `harbor` (sua) · pedido `1001` (da `summit`).)* **Duas lojas diferentes, a mesma porta.** O `storeId` do path não aponta para "a outra loja" — não aponta para nada: ele só precisa ser uma loja que você opera.
- **Mesmo objeto, dois chamadores, dois pais:** o `1009` voltou `200` para a `alice` por `/stores/meadow/...` e para a `dana` por `/stores/harbor/...`. O servidor resolveu as duas identidades e autorizou **duas lojas diferentes** — e entregou o mesmo objeto, porque a loja autorizada nunca foi comparada à loja do pedido.
- Bloco exemplo:
  ```
  GET /stores/harbor/orders/1009 HTTP/1.1
  Host: 127.0.0.1:8203
  Authorization: Bearer <dana-token>
  ```

### 6. Step 2 — What the vuln is NOT (passo de contraste OBRIGATÓRIO — três requests, NESTA ordem)

O mal-entendido a desmontar: "o handler não tem autorização". Tem. Três requests com o **mesmo** `<dana-token>`:

1. `GET /stores/meadow/orders/1009` → **`403`**. *(Rótulo: loja `meadow` (**não é sua**) · pedido `1009` (da `meadow`).)* **O primeiro check existe e morde.** Note que este request nomeou a loja **verdadeira** do pedido — e foi recusado, porque você não opera a `meadow`.
2. `GET /stores/harbor/orders/1011` → **`200`**. *(Rótulo: loja `harbor` (sua) · pedido `1011` (da `harbor`).)* A feature funcionando como projetada.
3. `GET /stores/harbor/orders/1009` → **`200`**. *(Rótulo: loja `harbor` (sua) · pedido `1009` (da `meadow`).)* O bug.

> **Escolha de detalhe:** o request 1 usa o **mesmo** pedido do request 3 (`1009`) — dentro de "um pedido qualquer", segurar o pedido fixo faz com que entre 1 e 3 **só a loja** varie. Entre 2 e 3 **só o pedido** varia. É um experimento controlado de dois eixos.

**Conclusão obrigatória a escrever (texto sugerido):**

> **EN:** *`storeId` was checked on all three requests. It simply has no relationship to the order that comes back. Requests 1 and 3 went through the very same check — one was refused, the other approved, for reasons that have nothing to do with the order: request 1 even named the order's real store and was refused; request 3 named an unrelated store and was served. Between 2 and 3 only the order changed, and the verdict didn't; between 1 and 3 only the store changed, and the verdict flipped. The authorized parameter and the delivered object are independent — and that independence is the bug.*
>
> **PT:** *O `storeId` foi checado nas três requests. Ele simplesmente não tem relação nenhuma com o pedido que volta. As requests 1 e 3 passaram pelo mesmo check — uma foi recusada, a outra aprovada, por motivos que nada têm a ver com o pedido: a request 1 até nomeou a loja verdadeira do pedido e foi recusada; a request 3 nomeou uma loja sem relação e foi servida. Entre 2 e 3 só o pedido mudou, e o veredito não; entre 1 e 3 só a loja mudou, e o veredito virou. O parâmetro autorizado e o objeto entregue são independentes — e essa independência é o bug.*

Logo depois, a **frase-âncora do WALKTHROUGH** (uma casa só): *"Authorization present is not authorization sufficient — what matters is which question it answers."* / *"Autorização presente não é autorização suficiente — o que importa é qual pergunta ela responde."* É aqui que ela deixa de ser slogan e vira observação.

Contraste com 01/02 (uma ou duas frases, creditando): lá a pergunta faltava por inteiro; aqui ela foi substituída por uma vizinha que passa por ela.

### 7. Why the fix works (porta 8303)

Logar de novo no `fixed/` (cada build tem o próprio mapa de tokens) e repetir:

- `GET /stores/meadow/orders/1009` (dana) → **`403`**, igual — o check do pai é a mesma linha nos dois gêmeos.
- `GET /stores/harbor/orders/1011` (dana) → `200` — a feature intacta.
- `GET /stores/harbor/orders/1009` e `GET /stores/harbor/orders/1001` (dana) → **`404`**, byte a byte o `404` de `GET /stores/harbor/orders/1013` (nunca seedado) — mesmo status, mesmo corpo, mesmo tamanho.
- `GET /stores/meadow/orders/1009` (alice) → `200` — operadores continuam lendo a própria loja. Sem token → `401`.
- **Forward pro DIFF:** por que `403` na loja e `404` no pedido, e por que o fix mudou a busca e não a guarda.

**O walkthrough TERMINA aqui.** Sem Intruder, sem exercícios/variações, sem trilha browser (CLAUDE.md §5).

---

## Frases-âncora (uma casa só cada)

- **WALKTHROUGH:** *"Authorization present is not authorization sufficient — what matters is which question it answers."* (fim do Step 2). O README descreve a lição **com outras palavras**, sem reproduzir a frase.
- **DIFF:** *"No information was missing — the question was."* / *"Não faltava informação — faltava a pergunta."* (na seção do fix, junto do `storeId` que o pedido carrega).
- **Não reusar** as âncoras de 01 ("…it leaks the collection…") e de 02 ("…a wall of 404s is 'didn't find'…"; "…the correction changed nothing").

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` + `Dockerfile` em cada gêmeo, self-contained, sem módulo compartilhado; lockfile commitado por gêmeo. `app.ts` difere **só** na linha da busca do `GET /stores/:storeId/orders/:orderId` (e no comentário dela); todo o resto é idêntico entre as versões.

**Herança de toolchain (CLAUDE.md §3.6) — lida dos arquivos publicados de 01 e 02 nesta fase, os quatro gêmeos idênticos:**

`tsconfig.json` (copiar):

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

- **Atenção — diferença real em relação a 01/02:** aqui o `noUncheckedIndexedAccess` **não** torna a guarda `!order` obrigatória pelo compilador. Nada desreferencia `order` depois da busca (não há `order.owner` na guarda), e `res.json` aceita `undefined`. **Verificado nesta fase:** removendo a guarda, `tsc --noEmit` passa nos dois gêmeos. A guarda é exigida pelo **comportamento** (o `404`), não pelo tipo. **Os docs NÃO podem afirmar** que o compilador força a guarda neste átomo.

`Dockerfile` (idêntico a 01/02 — copiar):

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

`docker-compose.yml`:

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8203:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8303:3000"
```

- `package.json` de cada gêmeo: `"name": "bola-nested-resource"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Resto idêntico a 01/02.
- `npm ci --omit=dev` (nunca `npm install`); `USER node` no fim, **sem `chown`**; sem `templates/`, sem `apt`, sem banco.

---

## Dependências extras

**Nenhuma dependência nova.** Versões **exatas herdadas** de 01/02 — lidas de `vulnerable/package.json` e `fixed/package.json` dos dois átomos (quatro arquivos idênticos) e conferidas nos `package-lock.json` commitados. **NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

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

- Base `node:24.21.0-slim` (lida dos quatro `Dockerfile`). Nenhuma divergência encontrada entre os átomos.
- Classificação por runtime: `tsx` em `dependencies`; `typescript`/`@types/*` em `devDependencies`. `npm audit --omit=dev` cobre exatamente o que a imagem roda.
- `crypto` é nativo (`node:crypto`). Nenhuma lib de roteamento aninhado, ORM ou query builder: o escopo é um `filter` + `find`.
- **Nota sobre o template:** a seção "Dependências extras" do template ainda menciona resolver versões "via `npm view`". Na série, a regra vigente é a herança do CLAUDE.md §3.6 (mesmo procedimento da spec do 02); bump é decisão de corte de release.

---

## Theory primer

Mesma página de 01/02 — BOLA é IDOR num endpoint de API, e o recurso aninhado não muda a classe.

- **Primer (verificado por fetch NESTA fase — HTTP 200 direto, sem redirect; H1 "Insecure direct object references (IDOR)"; primeira seção "What are insecure direct object references (IDOR)?"):**
  `https://portswigger.net/web-security/access-control/idor`
  Texto do link: **"Insecure direct object references (IDOR)"**, em inglês também no README PT.

Formato EN:

```markdown
> **Theory primer:** Read [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

**OWASP: sem link inline.** Os docs citam `API1:2023` em texto simples; o link vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (conferido: os READMEs de 01/02 já seguem isso — nenhum link da OWASP nos docs deles).

---

## Política de cross-ref (CLAUDE.md §5)

Publicação verificada **lendo o `atoms/api/ROADMAP.md` e a árvore de `atoms/` nesta fase**: na série API, **01 e 02 estão publicados** (`[x]`, pastas completas); 03 em diante não.

- **`bola-sequential-id` e `bola-uuid-leaked` — citar, contrastar, creditar.** Contrastes permitidos, todos verdadeiros sobre o código: (i) lá o detalhe não tinha check nenhum, aqui tem um que funciona; (ii) lá o fix acrescentava o predicado de posse à guarda depois da busca, aqui o fix muda a busca e a guarda fica intacta; (iii) o argumento `404`/GitHub/RFC está no DIFF do 01 — referenciar; (iv) a tese de identidade do 02 não se repete, de propósito.
- **Átomos web publicados** (`idor-numeric-id`, `bola-rest`, `idor-uuid-guessable`) — bem-vindos, mas esta spec **não afirma nada** sobre eles além de: nenhuma rota publicada no repo tem dois parâmetros de path. Qualquer outra citação se confere lendo o átomo na Fase 2.
- **PROIBIDO citar átomo de API não publicado** (04 em diante: `bfla-*`, `bopla-*`, etc.) — por nome, número ou descrição. Em particular, **não** antecipar "autorização por função" como próximo passo.
- Termos técnicos em inglês no PT (BOLA, IDOR, nested resource, parent, child, scope, token, Bearer, enumeration oracle, PII, Trigger, payload).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria / H1 | **API1 — BOLA**; H1 idêntico EN/PT | Mesma classe de 01/02; o slug qualifica a variante. |
| Tese | **Check presente ≠ check suficiente** | O que 01/02 não podiam mostrar: autorização que funciona e responde a pergunta errada. |
| Pai | **Loja**, não usuário | Usuário-como-pai deixa "o pai é meu?" tautológico; pareceria o 01 com um parâmetro a mais. |
| Topologia | **3 lojas**; `dana` opera só `harbor` | Com 2 lojas o aluno infere um vínculo inexistente entre path e pedido. |
| Operadores | `harbor`: dana · `meadow`: alice · `summit`: bob + carol | alice = vítima principal (a loja do pedido em destaque); summit = exemplo de compartilhamento legítimo. |
| Seed | **Os 12 pedidos de 01**, `owner` → `storeId`, redistribuídos 3/4/5 | Espelhamento parcial deliberado; nenhum pedido novo; regra "comprador ≠ operador da loja". |
| Ids | Pedido: **inteiro global `1001–1012`**; loja: **slug** | Contador global torna a busca global natural e a descoberta trivial (lacunas); formatos distintos evitam confundir os dois parâmetros. |
| Rotas | `POST /login`, `GET /stores/:storeId/orders` (correta nas 2), `GET /stores/:storeId/orders/:orderId` (vuln) | Superfície mínima; a lista prova que o escopo pelo pai era conhecido. |
| Check do pai | **`operates(caller, storeId)` → `403`**, idêntico nas 2 | Genuíno e visível; a assinatura mostra que o pedido não é argumento. |
| O bug | **Busca global** do filho, sem comparar `order.storeId` | Não faltava informação, faltava a pergunta. |
| Fix | **`ordersOf(storeId).find(...)`** no lugar de `ORDERS[...]` | Muda a busca, não a guarda; deliberadamente diferente do fix de 01/02. |
| Status | **`403` loja / `404` pedido** | Um critério (existência sensível?), dois objetos. RFC 9110 §15.5.4/§15.5.5 confirmados. |
| Loja inexistente | **`403`** | A resposta a "você opera?" é "não"; existência de loja não é sensível; check em uma linha. |
| Erros | `res.sendStatus(...)`; sucesso `res.json(...)` | Igual a 01/02; `404` byte-idêntico por construção. |
| Prova | **Trigger**; contraste 403 → 200 → 200 | Desmonta "não há autorização no handler". |
| Trilha | **Repeater/curl; sem Intruder; sem browser** | A tese não é escala; enumeração é a casa do 01. |
| Toolchain | **Herdado exato** (express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; `node:24.21.0-slim`) | CLAUDE.md §3.6; nenhuma dependência nova. |
| Primer | **PortSwigger IDOR**; OWASP em texto simples | Igual a 01/02; link OWASP centralizado no ROADMAP. |
| Impacto | **Escalação horizontal entre lojas** + PII de compradores | Honesto: não é vertical, não é RCE. |

---

## Decisões que podem gerar dúvida durante implementação

- **Tipos dos dois parâmetros — VALIDADO nesta fase.** Com `@types/express` 5.0.6, `req.params.storeId` e `req.params.orderId` tipam como `string` (inferência de route params), então `operates(caller, req.params.storeId)` e `ordersOf(req.params.storeId)` compilam sem `String(...)` nem `?? ""`. `tsc --noEmit` (typescript 7.0.2, tsconfig da série) limpo nos dois gêmeos, contra um sample com o mesmo código desta spec.
- **`STORES[storeId]?.operators.includes(user) ?? false`** — o `?.` é exigido pelo `noUncheckedIndexedAccess` (loja pode não existir); o `?? false` fecha em `boolean`. Não trocar por `!` (non-null assertion).
- **A guarda `!order` não é forçada pelo tipo** (ver "Anatomia"). Mantê-la; não escrever o contrário nos docs.
- **Express 5 — `Response` vs `void`:** igual a 01/02. Não anotar o retorno do handler; se anotar, usar `res.sendStatus(...); return;`.
- **Não montar o handler com `express.Router({ mergeParams: true })`** nem sub-router: rota plana com os dois parâmetros, para o aluno ler tudo num bloco.
- **Não adicionar endpoint de loja** (`GET /stores`, `GET /stores/:storeId`) nem `/me`: os slugs e a topologia estão no README. Um endpoint a mais é superfície a mais.
- **Comportamento validado nesta fase** (sample rodado localmente com o toolchain exato, fora do container): vulnerable — `meadow/1009` (dana) `403`, `harbor/1011` `200`, `harbor/1009` `200` com `"storeId":"meadow"`, `harbor/1001` `200` com `"storeId":"summit"`, `harbor/1013` `404`, loja inexistente `403`, sem token `401`; fixed — `harbor/1009` e `harbor/1001` `404` com corpo `Not Found` (9 bytes), idêntico a `harbor/1013`; `meadow/1009` (alice) `200` nos dois.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **Auth:** `POST /login` emite tokens distintos, cripto-fortes; bloco de auth byte a byte o de 01/02.
2. **`401`** sem Bearer ou com Bearer inválido nas duas rotas de loja.
3. **Check do pai morde nas duas versões:** `GET /stores/meadow/orders/1009` e `GET /stores/meadow/orders` com o token da dana → `403`.
4. **Vulnerable:** `harbor/1011` → `200`; `harbor/1009` → `200` com `"storeId":"meadow"`; `harbor/1001` → `200` com `"storeId":"summit"`.
5. **Baseline autorizado:** `meadow/1009` com o token da alice → `200` nas duas versões.
6. **Lista:** `GET /stores/harbor/orders` (dana) → exatamente `1004`, `1008`, `1011` nas duas versões.
7. **Fixed:** `harbor/1009` e `harbor/1001` → `404` **byte-idênticos** ao de `harbor/1013`; `harbor/1011` → `200`; loja inexistente → `403`.
8. **Diff entre gêmeos:** só o comentário + a linha da busca; `if (!order) return res.sendStatus(404);` e `res.json(order);` idênticos; `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` idênticos.
9. **Seed:** 12 pedidos, dados de 01 intactos, split 3/4/5, regra comprador ≠ operador da loja.
10. **Um bug só:** nenhum token em resposta; pedido serializado só com `id/storeId/customer/address/item/amount`; nenhuma rota extra.
11. **API-only:** sem `templates/`, sem HTML; sucesso sempre JSON.
12. **Bind/portas:** `127.0.0.1:8203`/`8303` → `3000`; `app.listen` default `127.0.0.1`; `ENV HOST=0.0.0.0` só no container.
13. **Container não-root:** sobe como `node`, `tsx` sem erro de permissão, imagem só com `express` + `tsx`.
14. **`npm audit --omit=dev`** por gêmeo, advisories registrados — o átomo é vulnerável na **lógica**, não nas dependências.
15. **`npm run typecheck`** verde nos dois gêmeos (host/CI, não container).
16. **Docs EN+PT sincronizados**; nenhum header PT byte-idêntico ao EN (exceto o h1 do README); banner em todo README; `dana` feminino no PT.
17. **Rótulo loja/pedido em todo bloco** do WALKTHROUGH (EN e PT).
18. **Frase do compartilhamento**, **frase do `customer`** e **conclusão do Step 2** presentes; **403 e 404 justificados lado a lado** no DIFF, com o critério nomeado uma vez.
19. **Frases-âncora** numa casa só; âncoras de 01/02 não reusadas.
20. **Primer** re-verificado por fetch; **RFC 9110 §15.5.4/§15.5.5** citados como nesta spec; OWASP sem link.
21. **Cross-ref:** nenhum átomo de API 04+; nenhuma afirmação sobre átomo web sem leitura do átomo; nenhuma afirmação de que o compilador força a guarda `!order`.

**Bloqueante remanescente:** nenhum. Pontos para o mantenedor revisar estão marcados em "Notas específicas".

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é sobre **qual pergunta** o check responde. Cada doc precisa deixar o check do pai **visível e respeitável** antes de mostrar o bug — se o aluno sair achando que "faltava autorização", o átomo falhou.
- **A afirmação é o código.** O fix muda a busca; a guarda não muda. Se a geração improvisar outra forma (um `if (order.storeId !== storeId)` depois da busca, um `403` no filho), a tese do átomo cai. **PARE e pergunte.**
- **Pedido se nomeia por loja + id**, nunca por pessoa. A `alice` é vítima como operadora da `meadow`.
- **Não reabrir o eixo do formato do id** (fechado pelo 02) nem o argumento completo do `404` (está no DIFF do 01 — referenciar).
- **ROADMAP (`atoms/api/ROADMAP.md`):** marcar o átomo 03 como `[x]` só após geração + validação (proposta ao mantenedor, CLAUDE.md §10.4). **Divergência pendente:** a linha do átomo 03 ainda descreve `/users/{id}/orders/{oid}` (usuário como pai) — propor ao mantenedor a correção num commit próprio antes ou junto da geração.
- **CHANGELOG.md (Fase 2):** linha em `[Unreleased] / Added` no padrão da série.
- **Para o mantenedor revisar (decisões de detalhe desta spec):** (i) nomes de comprador = handles dos operadores (herança do seed) — tratado com a frase do `customer`, a regra de distribuição e a disciplina "loja + id"; (ii) slugs de loja `harbor`/`meadow`/`summit`; (iii) `bob` + `carol` como a loja com dois operadores; (iv) request 1 do contraste usando o mesmo pedido do request 3; (v) sem Intruder; (vi) loja inexistente → `403`.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): o checklist acima. Se as portas não forem alcançáveis do sandbox, validar via `docker exec`.

---

## Verificação factual dos átomos 01 e 02 (conferida LENDO os arquivos nesta fase)

1. **`package.json`** — os quatro gêmeos (01 e 02, `vulnerable/` e `fixed/`) com express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; scripts `start: tsx app.ts`, `typecheck: tsc --noEmit`.
2. **`package-lock.json`** — resolve as mesmas cinco versões; idêntico entre os gêmeos de cada átomo.
3. **`Dockerfile`** — idêntico nos quatro: `node:24.21.0-slim`, `npm ci --omit=dev`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm", "start"]`.
4. **`tsconfig.json`** — idêntico nos quatro (flags listadas em "Anatomia").
5. **`docker-compose.yml`** — bind `127.0.0.1`, `8201/8301:3000` (01) e `8202/8302:3000` (02).
6. **Bloco de auth** — linhas 1–23 dos `app.ts` de 01 e 02 byte-idênticas (`USERS`, `TOKENS`, `issueToken` com `randomBytes(24).toString("base64url")`, `authenticate`).
7. **Seed** — doze pedidos `1001–1012`; `customer`/`address`/`item`/`amount` idênticos entre 01 e 02 (e reproduzidos acima).
8. **Handler vulnerável de 01/02** — só `authenticate()` + `404` de existência; **nenhum** check de autorização (omissão).
9. **Fix de 01/02** — a mesma guarda byte a byte, `if (!order || order.owner !== caller) return res.sendStatus(404);`, com o comentário `FIXED:` — predicado acrescentado **depois** da busca.
10. **Gêmeos de 01/02** — `app.ts` difere só nessa região; demais arquivos idênticos.
11. **Lista de 01/02** — `GET /orders` filtra `o.owner === caller` nas duas versões.
12. **DIFF do 01** — cita RFC 9110 §15.5.4 e §15.5.5, o precedente do GitHub, e `403` legítimo quando a existência não é sensível; o DIFF do 02 herda por referência.
13. **Frases-âncora publicadas** — "leaks the collection" (WALKTHROUGH do 01), "didn't find" (WALKTHROUGH do 02), "the correction changed nothing" (DIFF do 02).
14. **READMEs de 01/02** — banner, primer PortSwigger IDOR, `API1:2023` em texto simples, **nenhum** link da OWASP, frase do login sem senha como atalho.
15. **WALKTHROUGH de 01/02** — baseline com o login da alice como device de "mesmo objeto, dois chamadores"; passo de contraste separando `401`, lista escopada e detalhe sem escopo.
16. **Docs PT de 01/02** — headers traduzidos (só o h1 do README idêntico); `dana` no feminino ("você mesma", "a `dana`").
17. **Rotas do repo** — nenhuma rota publicada (web ou API) com dois parâmetros de path; `bola-rest` usa `/api/orders/<int:order_id>`.
