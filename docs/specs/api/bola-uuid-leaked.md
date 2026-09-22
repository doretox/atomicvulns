# Spec — Átomo API 02: `bola-uuid-leaked`

> Documento de especificação para o Claude Code implementar o **segundo átomo da série API** do projeto `atomicvulns` (Fase 1 API, "Authorization: Object & Function", milestone `v1.1`; **não** fecha a fase). Este átomo é **BOLA — Broken Object Level Authorization**, o **API1:2023**, item **#1** do **OWASP API Security Top 10 (2023)** — a **mesma classe** do átomo 01, de propósito. Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **Este átomo espelha o átomo 01 (`bola-sequential-id`) deliberadamente.** A tese só existe pela identidade: mesmo seed, mesmo fix, mesma superfície — **muda só o tipo do identificador** (id sequencial → UUID). Tudo o que a spec afirma ser "idêntico ao 01" foi **conferido lendo os arquivos do 01 agora**, não de memória (ver "Verificação factual do átomo 01").
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **`atoms/api/API1-broken-object-level-authz/bola-sequential-id/` — o átomo-bandeira e referência de estilo da série API, INTEIRO.** Os dois `app.ts`, os dois `package.json`, o `tsconfig.json`, o `Dockerfile`, o `docker-compose.yml` e os seis documentos. É a **fonte da verdade do toolchain** (§3.6 — herança) e do **fix** que este átomo replica byte a byte na região da guarda.
> 2. **`atoms/web/A01-broken-access-control/idor-numeric-id/` e `bola-rest/`** — o avô do arco e o gêmeo web da classe. Reusar o framing "o bug é a checagem AUSENTE, não o id" e o passo de contraste "o que a vuln NÃO é".
> 3. **`atoms/web/A01-broken-access-control/idor-uuid-guessable/` — RELER INTEIRO (`README.md`, `vulnerable/app.py`, `WALKTHROUGH.md`).** É o átomo web de IDOR com UUID, e o mantenedor **fechou: cita** (cross-ref obrigatório, escopo apertado). **Ver "Política de cross-ref"** para as quatro partes da citação (complementaridade, proteção do passo de contraste, justificar a existência deste átomo) e o **LIMITE DURO**: cita-se **só** pela lição do formato do id; o **fix/status dele é off-limits em qualquer doc deste átomo**. Confirmar cada fato lendo os arquivos, não de memória.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Identidade

- **ID:** `bola-uuid-leaked`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API1 — Broken Object Level Authorization**
- **Pasta:** `atoms/api/API1-broken-object-level-authz/bola-uuid-leaked/`
- **Número sequencial (série API, conta do 01):** 02
- **Porta vulnerable:** `127.0.0.1:8202`
- **Porta fixed:** `127.0.0.1:8302`
- **Porta interna do container:** `3000` (idiomática do Node/Express, igual ao 01). Compose mapeia `127.0.0.1:8202:3000` (vulnerable) e `127.0.0.1:8302:3000` (fixed).
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Express); exposição host restrita a `127.0.0.1` pelo compose.
- **Fase / milestone:** Fase 1 API, `v1.1` (segundo átomo da fase; **não** fecha a fase).
- **Branch de trabalho:** `atom/bola-uuid-leaked` (CLAUDE.md §6). Já criada nesta fase de planning.
- **H1 dos READMEs (idêntico em EN e PT):** `# bola-uuid-leaked — Broken Object Level Authorization (BOLA)`. O título nomeia a **classe**; o slug qualifica a variante (CLAUDE.md §5). **Nota:** o H1 é o **mesmo** do `bola-sequential-id` (e do web `bola-rest`) — de propósito: é a mesma classe. O que distingue os átomos é o slug e a *demonstração*. Não é conflito; não "corrigir".
- **Theory primer:** ver seção "Theory primer" (URL do primer verificada por fetch nesta fase — HTTP 200 direto).

---

## A tese do átomo — prova por identidade

Este átomo tem **uma tese**, e todo o resto serve a ela:

> **O formato do id NÃO é a causa do BOLA.** O átomo 01 (`bola-sequential-id`) mostrou que um id sequencial torna a *descoberta* trivial. Este mostra que trocar o id por um **UUID não-adivinhável não conserta nada**: a mesma falha continua inteira. A prova é por **IDENTIDADE** — mesmo seed, mesmo fix, mesma superfície — variando **um único eixo**: o tipo do identificador.

Consequências que amarram a spec inteira (todas obrigatórias):

- **O seed é o do 01, objeto a objeto** — as mesmas quatro pessoas, os mesmos doze pedidos, os mesmos itens/valores/nomes/endereços. A única diferença: onde o 01 tem os inteiros `1001…1012`, aqui há doze **UUID v4 fixos**. (Ver "Store".)
- **O fix é o do 01, byte a byte na região da guarda** — o mesmo predicado de posse, a mesma saída `sendStatus(404)` compartilhada. Se a geração improvisar outra forma, **a prova cai**. (Ver "Fix".)
- **A descoberta muda, o walkthrough muda, o fix NÃO muda.** Com UUID não há enumeração possível; o id chega ao atacante **de fora da aplicação**. O walkthrough inteiro é reescrito em torno disso — e ainda assim o `fixed/` é o mesmo. É essa assimetria (tudo mudou, menos a correção) que **é** a lição.

Se o formato do id fosse a causa, o fix teria que ser diferente entre os dois átomos. Ele não é. **A afirmação É o código, sem adjetivo.**

---

## Classe de vulnerabilidade

**BOLA (Broken Object Level Authorization).** Uma API REST serve um objeto privado (um pedido) por `GET /orders/:id`, **autentica** o chamador (Bearer inválido → `401`), e ainda assim devolve o objeto **sem cruzar o dono do objeto (`order.owner`) com a identidade autenticada**. É o **API1:2023**, o #1 do OWASP API Security Top 10 — e a face de API do IDOR: mesma causa raiz (**object-level authorization ausente**), mesmo fix (cruzar dono do objeto com o chamador). Idêntico ao `bola-sequential-id` na classe; o que muda é a **variante do identificador**.

### A lição-coração (creditada ao `bola-sequential-id`, não reinventada)

> **"Estar autenticado não é estar autorizado."**
> Um token válido prova **quem você é**; não diz nada sobre **se este objeto é seu.**

O `bola-sequential-id` já cravou essa lição em profundidade (auth ≠ authz, o handler que chama `authenticate()` e descarta a identidade, a assimetria lista-vs-detalhe). **Este átomo credita e reusa** — não reabre o argumento; ele o aplica a um segundo eixo (o formato do id).

### Dois eixos, separados o tempo todo — agora com o eixo 1 "consertado" e o bug intacto

Os mesmos dois eixos do 01, mantidos **distintos**:

- **Formato do id = eixo da DESCOBERTA.** No 01, o id contíguo tornava a enumeração fácil. Aqui o id é um **UUID v4** (128 bits, ~122 de aleatoriedade): a enumeração é **inviável**. O eixo da descoberta foi, na prática, "consertado" pelo formato do id — e **o bug continua inteiro**.
- **Check ausente = a CAUSA.** O que **permite** a leitura cross-user continua sendo a ausência do check de dono — não o formato do id. Um id não-adivinhável só encareceu (aqui, quase eliminou) a **descoberta**; não colocou o **check** de volta. O atacante que **obtém** um id (aqui, por um vazamento de fora da app) passa reto pela dificuldade de descoberta e cai no mesmo BOLA.

O 01 fixou o eixo 2 (o check) e deixou o eixo 1 (id sequencial) intacto, provando que o formato nunca foi o problema. Este átomo faz o **experimento espelhado**: melhora o eixo 1 ao máximo (UUID) **sem** tocar o eixo 2 — e mostra que o bug sobrevive. Duas metades da mesma prova.

### Por que API1 (Broken Object Level Authorization)

O bug **não é** "input virou código" (injection). É **"um request legítimo alcançou um objeto fora do seu escopo autorizado"** — o chamador pediu um pedido que não é dele e a API entregou. Isso é controle de acesso a objeto: **API1** no OWASP API Security Top 10 **2023**. Situe nessa edição, **sem arqueologia** de edições antigas (CLAUDE.md §5). Por ser vuln de **lógica/autorização** (Trigger, não Payload), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório (ver "Walkthrough", Step de contraste).

---

## O que este átomo acrescenta (vs. `bola-sequential-id`)

**Ponto de honestidade pedagógica:** o `bola-sequential-id` já é BOLA, já ensinou o núcleo, já tem PII no seed e já tem o beat de enumeração no Intruder. Este átomo **não finge inventar** a classe; ele isola **um** eixo que o 01 deixou enunciado mas não demonstrado, e é essa a razão de existir:

1. **Isola o formato do id como NÃO-causa — por demonstração, não por frase.** O 01 tinha permissão pra dizer numa única frase ("um id não-adivinhável só encareceria a descoberta") mas **proibição** de demonstrar (a variante UUID era átomo não-publicado — este). Agora a demonstração é o átomo inteiro: o id vira UUID, a enumeração morre, e o BOLA continua.
2. **Troca "a base vazou" por "o id vazou de fora."** O 01 mostrava impacto por **enumeração** (varrer `1001–1012` esvazia o banco). Aqui a enumeração é inviável; o vetor é o **id que circula fora da app** (chamada de suporte, print, link compartilhado). O impacto continua real — **qualquer id vazado → o objeto inteiro com PII** — mas a mecânica de descoberta é oposta, e o walkthrough ensina a **não confundir "não consigo enumerar" com "está seguro"**.
3. **Nomeia a inversão do sinal do Intruder.** No 01, um muro de `404` no Intruder era a **prova do fix**. Aqui, o **mesmo muro de `404`** — contra a app **vulnerable** — significa só "o atacante não achou". Mesma imagem, conclusão oposta. É o beat-assinatura deste átomo (ver "Walkthrough", passo de contraste).
4. **Prova que o fix é id-agnóstico.** O `fixed/` é o do 01 na região da guarda, byte a byte. O DIFF põe os dois fixes lado a lado. É a forma mais forte de dizer "o formato do id nunca foi o problema": a correção não sabe nem se importa se o id é inteiro ou UUID.

---

## Feature simulada — API REST de pedidos (API-only, sem HTML)

**Pedidos (orders).** A **mesma** feature do `bola-sequential-id`: uma API REST de e-commerce onde cada pedido tem id, dono, o nome e endereço de entrega do cliente, o item e o valor. O cliente autentica com um token e lê os seus pedidos. Do ponto de vista do dev, "o cliente só vê os pedidos dele" — mas o endpoint de detalhe esqueceu de garantir isso. A única diferença visível ao cliente: o id de um pedido agora é um **UUID** (`edec4558-…`) em vez de um inteiro (`1007`).

**API-only por natureza** (CLAUDE.md §3.3): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`. Requests com corpo JSON no `POST /login`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl** (ver "Walkthrough").

---

## Autenticação — token opaco, cripto-forte (idêntica ao `bola-sequential-id`)

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados e devolve `{ "token": "<opaco>" }`. Mapa `token → usuário` **em memória**, resolvido por lookup. **NÃO é JWT.** Bloco de auth (imports, `USERS`, `TOKENS`, `issueToken`, `authenticate`) **idêntico byte a byte** ao do `bola-sequential-id` — copiar, não reescrever.

**O token DEVE ser gerado com `crypto.randomBytes` (aleatoriedade criptográfica)**, exatamente como no 01: `randomBytes(24).toString("base64url")`. Não-negociável, pela mesma razão do 01:

> Um token **previsível** seria uma **SEGUNDA vulnerabilidade** (broken authentication / token forjável) e violaria "um átomo = uma vuln" (CLAUDE.md §2). O token tem que ser **sólido** pra que a **única** falha em jogo seja a object-level authorization ausente. O ataque **não toca** o token — nunca decodifica, adultera nem forja; ele fica válido e da própria `dana` o tempo todo.

**Nota — o UUID é do OBJETO, não do token.** Deixar explícito na spec e nos docs pra não confundir os dois eixos: o **identificador de pedido** virou UUID; o **token** continua o mesmo valor opaco `randomBytes` do 01. O átomo é sobre id de objeto, não sobre token. **PROIBIDO** mencionar técnicas de ataque a token (decode, forjar, `alg:none`, trocar `sub`).

**Quatro usuários seedados** (idênticos ao 01; handles de login; sem senha):

- **`dana`** — a **atacante** (você). Faz login como si mesma, obtém o próprio token, e é dona de **exatamente 1** pedido. (Nos docs PT, `dana` é **feminino** — CLAUDE.md §5: "a atacante", "você mesma", "dela"; o masculino genérico vale pro **papel** — "o dono" — não pra ela.)
- **`alice`, `bob`, `carol`** — as **vítimas**. Entre as três dividem os outros **11** pedidos, de forma **desigual** (ver "Store").

**Requisito de README (EN+PT) — declarar o atalho:** o README **diz explicitamente** que o login sem senha é um **atalho deliberado do laboratório, não a vulnerabilidade**, e que a autenticação em si **é imposta** (token ruim → `401`). Uma frase, **sem citar átomo**. (Mesmo requisito do 01.)

---

## Store / dados — em memória, PII fake, **ids UUID v4 FIXOS**

**Sem banco** (CLAUDE.md §3.4). O `type Order` muda **um** campo em relação ao 01: `id` passa de `number` para `string`. O `Record` passa a ser chaveado por `string`. O resto do objeto é **idêntico** ao 01.

```ts
type Order = {
  id: string;         // UUID v4 (was number in bola-sequential-id) — the ONLY type change
  owner: string;      // login handle of the owner -- what an authorization check compares
  customer: string;   // customer name on the order -- the PII
  address: string;    // delivery address -- obviously fake
  item: string;
  amount: string;
};
```

**Os UUIDs são FIXOS, cravados no código, NUNCA gerados a cada boot.** Isto é obrigatório: o walkthrough precisa **citar o id literalmente** (o UUID vazado da alice, o UUID da própria dana). Um seed gerado em runtime (`crypto.randomUUID()` no boot) quebraria o walkthrough e a premissa do vazamento. **Não** importar lib de UUID, **não** gerar no boot — são **string literals**. (Ver "Dependências extras".)

O seed abaixo é o **espelho objeto-a-objeto** do `bola-sequential-id`: o que era `1001` continua a mesma compra da alice, o que era `1007` continua o pedido da dana, etc. Os doze UUIDs v4 abaixo foram gerados nesta fase de planning e são **canônicos** — a Fase 2 usa **exatamente** estes (não regenerar):

```ts
// Object ids are fixed UUID v4 strings, hardcoded (never generated at boot) so the
// walkthrough can cite them literally. Unlike bola-sequential-id's 1001..1012 counter,
// nothing about one id reveals another -- the id space is not walkable. Same twelve
// orders, same owners/data as bola-sequential-id; ONLY the id type changed.
const ORDERS: Record<string, Order> = {
  "376d2491-7bc1-44ea-b1f2-81cf7a34af58": { id: "376d2491-7bc1-44ea-b1f2-81cf7a34af58", owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Mechanical keyboard",     amount: "$89.00"  }, // was 1001 -- LEAKED to dana in the walkthrough
  "3ee14e8a-ff76-495f-9e1f-d282ae469916": { id: "3ee14e8a-ff76-495f-9e1f-d282ae469916", owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Noise-cancelling headset", amount: "$199.00" }, // was 1002
  "04320e8a-75d1-4c5b-ae31-abfe1ffb212b": { id: "04320e8a-75d1-4c5b-ae31-abfe1ffb212b", owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "USB-C hub",                amount: "$42.50"  }, // was 1003
  "bd840141-342e-4d8f-9c62-46e2dace56ef": { id: "bd840141-342e-4d8f-9c62-46e2dace56ef", owner: "carol", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "4K monitor",               amount: "$329.00" }, // was 1004
  "faba81a1-83bf-4031-bd4a-c5cb1fe503f9": { id: "faba81a1-83bf-4031-bd4a-c5cb1fe503f9", owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Laptop stand",             amount: "$55.00"  }, // was 1005
  "e1df436b-566f-4640-8a07-b07a382bf940": { id: "e1df436b-566f-4640-8a07-b07a382bf940", owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "Webcam",                   amount: "$75.00"  }, // was 1006
  "edec4558-0cf5-4462-aaba-308229ff6c4f": { id: "edec4558-0cf5-4462-aaba-308229ff6c4f", owner: "dana",  customer: "Dana Lee",     address: "3 Testing Blvd, Faketon",     item: "Wireless mouse",           amount: "$29.90"  }, // was 1007 -- attacker (you)
  "21f0ebc8-15c8-424e-80e5-3c5aa0cf8b9b": { id: "21f0ebc8-15c8-424e-80e5-3c5aa0cf8b9b", owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Desk mat",                 amount: "$19.00"  }, // was 1008
  "bf587c3c-b25f-4533-ba15-21d3b8d21baa": { id: "bf587c3c-b25f-4533-ba15-21d3b8d21baa", owner: "carol", customer: "Carol Dias",   address: "90 Placeholder Rd, Lakeside", item: "Standing desk",            amount: "$589.00" }, // was 1009
  "d17f8d55-bf75-45e3-a312-856293086997": { id: "d17f8d55-bf75-45e3-a312-856293086997", owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Monitor arm",              amount: "$120.00" }, // was 1010
  "93e1f9e0-277e-4c5b-a1fc-4acff50cb828": { id: "93e1f9e0-277e-4c5b-a1fc-4acff50cb828", owner: "bob",   customer: "Bob Carter",   address: "7 Sample St, Rivertown",      item: "HDMI cable",               amount: "$12.99"  }, // was 1011
  "0b089ce7-756c-467b-98e0-f5facd72f561": { id: "0b089ce7-756c-467b-98e0-f5facd72f561", owner: "alice", customer: "Alice Nguyen", address: "12 Example Ave, Springfield", item: "Ergonomic chair",          amount: "$420.00" }, // was 1012
};
```

**Contagem (confira na geração — idêntica ao 01):** alice = 6, bob = 3, carol = 2, **dana = 1**. Total **12**. Atacante dona de **exatamente 1** (`edec4558-…`, era `1007`). O UUID vazado no walkthrough é o da alice `376d2491-…` (era `1001`, o Mechanical keyboard — o **mesmo objeto** que o Step 1 do 01 lia).

### O espelhamento é deliberado e didático (tem que aparecer no DIFF)

Registre na spec e **crave no DIFF**: o seed é cópia do `bola-sequential-id` **de propósito**, não por preguiça. A tese é uma prova por identidade — se o seed divergisse (outras pessoas, outros valores, outra distribuição), teríamos **duas** variáveis mudando (id **e** dados) e a comparação perderia o sentido. Mantendo tudo igual e variando **só o tipo do id**, o átomo isola exatamente uma coisa. O DIFF deve dizer isso com todas as letras.

### Os doze pedidos NÃO servem à enumeração — dizer isso explicitamente

Registre também (no DIFF e/ou no walkthrough): os doze pedidos ficam aqui **por espelhamento do 01**, **não** porque o corpus grande sirva a alguma coisa. Com UUID, **o tamanho do corpus é irrelevante**: o espaço de busca é o mesmo com dois objetos ou dois milhões — ~2¹²² ou mais. No 01, doze ids contíguos eram um alvo de enumeração; aqui, doze UUIDs são doze agulhas num palheiro astronômico. **Dizer isso explicitamente** pro aluno não inferir que "mais pedidos = mais fácil de varrer" — é o contrário do que o formato do id agora permite.

---

## De onde vem o id — de FORA da aplicação (restrição dura: um bug só)

**A única falha do átomo é o check de posse ausente no `GET /orders/:id`.** Isto é uma **restrição dura de design**:

- **NADA na aplicação vaza id de objeto alheio.** Sem endpoint de busca, sem listagem larga, sem campo extra em resposta, sem endpoint de "dica", sem andaime. O `GET /orders` da dana devolve **só** o pedido dela — e o UUID dela **não revela nada** sobre os outros (ao contrário do `1007` do 01, que denunciava o esquema contíguo). O app dá ao atacante **zero** alavancagem de descoberta.
- **O id chega de FORA.** O walkthrough declara a premissa em **uma frase**: o UUID de um pedido da alice chegou às mãos da atacante por um **canal do mundo real** — chamada de suporte, print de tela, link compartilhado —, e ids circulam assim. **Sem artefato no repo, sem ticket fake, sem cerimônia.** Só a frase, e o UUID literal do seed.
- **Consequência já cravada acima:** por isso os UUIDs do seed são **fixos** (o walkthrough cita `376d2491-…` literalmente).

> **Guardrail pra Fase 2:** se durante a geração surgir a tentação de criar uma **fonte de ids dentro da app** (um endpoint que lista tudo, um campo que vaza o id de outro, um "search") pra o atacante "achar" o UUID — **PARE**. É sinal de que a premissa foi mal encodada. O id vem **de fora**; dentro da app existe só o check ausente. Um segundo vetor seria um segundo bug e violaria "um átomo = uma vuln" (CLAUDE.md §2).

**Requisito de README (EN+PT) — definir "leaked" na ABERTURA (E2):** o slug diz `bola-uuid-leaked`, mas **nada na app vaza**. Quem lê o índice do repo espera vazamento pela app; isso tem que ser desfeito na **primeira coisa que a pessoa lê** (o parágrafo de abertura do README, após o H1 e o banner), **antes de qualquer passo** — não no meio do walkthrough. Uma frase define o que "leaked" significa aqui, com a **mesma definição** que a linha do átomo 02 no `atoms/api/ROADMAP.md` passou a usar (ler a linha e manter as duas coerentes), e **sem citar átomo nenhum**. Texto sugerido (Fase 2 pode ajustar a prosa, não o sentido):

> **EN:** *Here "leaked" means the order's UUID reached the attacker through a channel outside the application — a support call, a screenshot, a shared link — the way ids circulate in the real world. The application itself leaks no id; the only bug is the missing ownership check on `GET /orders/:id`.*
>
> **PT:** *Aqui "leaked" quer dizer que o UUID do pedido chegou ao atacante por um canal de fora da aplicação — um chamado de suporte, um print, um link compartilhado — do jeito que ids circulam no mundo real. A aplicação em si não vaza id nenhum; o único bug é o check de posse ausente no `GET /orders/:id`.*

(Termo `leaked` em inglês também no PT — CLAUDE.md §7. `attacker`/`atacante` aqui é o **papel**, masculino genérico OK; não é a `dana` em concordância.)

---

## Rotas

Superfície **idêntica ao `bola-sequential-id`**, só leitura: `POST /login`, `GET /orders` (correto nos dois gêmeos, escopado ao dono), `GET /orders/:id` (o vulnerável). **Nenhum endpoint a mais.** Imports, bootstrap (`const app = express()` + `app.use(express.json())`), constantes e helpers **idênticos** entre `vulnerable/` e `fixed/` — e idênticos ao 01, exceto o tipo do `ORDERS` (agora `Record<string, Order>`) e o seed.

`POST /login` e `GET /orders` são **byte a byte os do 01** (o `filter((o) => o.owner === caller)` funciona igual, comparando `owner` a `caller` — ambos strings de username, independentes do tipo do id). Copiar do 01.

### `GET /orders/:id` — a rota VULNERÁVEL

Autentica (Bearer ruim → `401`), busca o pedido pelo id, e o devolve — **sem** confrontar `order.owner` com o chamador. Handler **≤ ~30 linhas** (tem ~6). A **única** diferença de código em relação ao handler vulnerable do 01 é a linha da busca: **sem `Number()`**, porque a chave agora é uma string (o UUID).

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);          // AUTHENTICATION only
  const order = ORDERS[req.params.id];                       // string key (UUID) -- no Number() coercion
  if (!order) return res.sendStatus(404);
  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
  // order.owner is the caller. Authenticated is not authorized for THIS object.
  res.json(order);                                          // BOLA -- no object-level check
});
```

- **Diferença vs. 01, e ela NÃO é a lição:** `ORDERS[req.params.id]` no lugar de `ORDERS[Number(req.params.id)]`. É consequência mecânica do id ser string (um `Number("376d2491-…")` daria `NaN`), **não** um eixo pedagógico. E é **idêntica** entre o `vulnerable/` e o `fixed/` deste átomo — logo **não** faz parte do fix. Tratar como escolha mínima/mecânica, jamais como contraste didático (template, "Notas específicas": diferença cosmética não vira lição).
- **Higiene de id inexistente/inválido:** qualquer string que não seja um dos doze UUIDs seedados → `ORDERS[...]` é `undefined` → `404`. UUID inventado → `404`. String malformada → `404`. (Idêntico em comportamento ao 01, sem o passo do `NaN`.)
- **`Number(req.params.id)` NÃO se usa aqui** — foi validado nesta fase que a busca direta por string tipa limpo (ver "Decisões que podem gerar dúvida").

> **Bind do servidor** (rodapé idêntico ao 01): `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);`

---

## Fix — posse e existência viram a mesma guarda (o fix do 01, herdado)

O gêmeo `fixed/` difere do `vulnerable/` **APENAS no predicado de posse** acrescentado à guarda que segue a busca no `GET /orders/:id`. **Nenhuma outra linha muda.** E a região do fix é **byte a byte a do `bola-sequential-id`** — mesmo comentário, mesma condição, mesma saída:

```ts
app.get("/orders/:id", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.sendStatus(401);
  const order = ORDERS[req.params.id];
  // FIXED: existence and ownership are ONE guard with ONE exit -- a missing order and
  // someone else's order both hit the same sendStatus(404), so "doesn't exist" and
  // "not yours" are byte-identical by construction (a 403 here would be an enumeration oracle).
  if (!order || order.owner !== caller) return res.sendStatus(404);
  res.json(order);
});
```

Diff mínimo (o eixo único, dentro deste átomo):

```diff
   const order = ORDERS[req.params.id];
-  if (!order) return res.sendStatus(404);
-  // VULNERABLE: authenticated, but the order is returned WITHOUT checking that
-  // order.owner is the caller. Authenticated is not authorized for THIS object.
-  res.json(order);                                          // BOLA -- no object-level check
+  // FIXED: existence and ownership are ONE guard with ONE exit -- a missing order and
+  // someone else's order both hit the same sendStatus(404), so "doesn't exist" and
+  // "not yours" are byte-identical by construction (a 403 here would be an enumeration oracle).
+  if (!order || order.owner !== caller) return res.sendStatus(404);
+  res.json(order);
```

**A leitura correta do fix (cravar no DIFF — creditar o 01, não reinventar):** posse e existência viram a **MESMA guarda, com a MESMA saída**. `!order` e `order.owner !== caller` compartilham um único `return res.sendStatus(404)`. "Não existe" e "não é seu" são o mesmo código, o mesmo status e o mesmo corpo **POR CONSTRUÇÃO**. A leitura completa desse mecanismo já está no DIFF do `bola-sequential-id`; **aqui referencia-se**, o átomo não a reescreve do zero.

**Comentário do `fixed/` herdado verbatim — de propósito.** O comentário inclui o parêntese "(a 403 here would be an enumeration oracle)", que era mais afiado para ids sequenciais. Mantê-lo **byte a byte** é deliberado e serve à tese: o fix foi **copiado sem mudar um caractere**, porque ele genuinamente não depende do formato do id. O DIFF trata dessa nuance em prosa (ver "Status code do fix"), sem editar o comentário compartilhado.

### Os dois fixes lado a lado (o centro do DIFF deste átomo)

O DIFF de `bola-uuid-leaked` tem uma seção que **põe os dois fixes lado a lado** — o `+` do `bola-sequential-id` e o `+` deste — e mostra que a **região do fix é idêntica**:

```diff
# bola-sequential-id  (fixed/app.ts)          # bola-uuid-leaked  (fixed/app.ts)
+ if (!order || order.owner !== caller) ...    + if (!order || order.owner !== caller) ...
```

(A única linha de contexto que difere entre os dois átomos é a busca — `ORDERS[Number(req.params.id)]` vs `ORDERS[req.params.id]` — e ela **não** é o fix: é a mesma nos dois gêmeos deste átomo.)

**Conclusão a escrever no DIFF, explicitamente:** mudou o **tipo do id**, mudou a **descoberta**, mudou o **walkthrough inteiro** — e a **correção não mudou nada**. Se o formato do id fosse a causa, o fix teria que ser diferente; ele é o mesmo predicado, a mesma saída. A correção não sabe nem se importa se o id é `1007` ou `edec4558-…`. Essa é a prova.

---

## Status code do fix: `404` — herdado do `bola-sequential-id`, não reinventado

O fix retorna **`404`** para pedido de não-dono, byte-idêntico ao `404` de pedido inexistente — **exatamente como no `bola-sequential-id`**. A escolha e a justificativa são **as do 01**; o átomo **referencia**, não reconstrói (CLAUDE.md/tarefa: "mesma justificativa; não reinvente o argumento, referencie"). O DIFF manda o aluno ao DIFF do `bola-sequential-id` para o argumento completo (precedente do GitHub, RFC 9110 §15.5.4/§15.5.5, e quando `403` é legítimo).

**Nuance obrigatória (curta, a favor da tese — NÃO reabrir a decisão):** com id **sequencial**, o `404` era **forçado** (um `403` viraria oráculo de enumeração ao varrer inteiros). Com **UUID**, essa pressão relaxa — o espaço não é varrível, então a metade "sequencial" daquele argumento não se aplica aqui. Mas o `fixed/` **mantém `404`**, e isso é o ponto: o `404` é o default conservador que **nunca está errado** (o RFC 9110 prevê esconder existência em geral), e mantê-lo **inalterado** é precisamente a tese — **a correção não se curva ao formato do id**. Escrever assim, a favor da identidade; **não** propor `403` como alternativa deste átomo (design fechado). Essa reflexão é **interna à spec**; nos docs do átomo, o argumento do `404` é **herdado do `bola-sequential-id` por referência e não se reabre**. **NÃO** comparar com o status de fix de nenhum outro átomo — ver o **LIMITE DURO** na "Política de cross-ref" (o fix/status do `idor-uuid-guessable` é off-limits em qualquer doc deste átomo; nada de "lá é 403, aqui é 404").

---

## Padrão de prova — Trigger

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **usar um id legítimo** (vazado de fora) num request legítimo, com um token legítimo. Por ser **Trigger**, o **passo de contraste é obrigatório** (CLAUDE.md §5) — ver Walkthrough, passo de contraste.

---

## Walkthrough — estrutura e requests

Trabalhado **100% no Burp** (Repeater + Intruder), `curl` como equivalente — **API-only, SEM trilha browser** (CLAUDE.md §3.3). Cada request é um bloco colável: request-line + `Authorization: Bearer <token>` + corpo JSON quando houver. Tokens são **placeholders** (`<dana-token>`, `<alice-token>`) — variam por login; os **UUIDs de pedido são literais** (fixos no seed).

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de pedidos serve `GET /orders/:id` autenticando o chamador mas sem checar de quem é o pedido; aqui o id é um UUID" — não um personagem. Defina todo termo não-óbvio na estreia (ex.: "BOLA (Broken Object Level Authorization)", "UUID (Universally Unique Identifier)", "opaque token").

### 1. Context
- API REST de pedidos; auth por Bearer token opaco; `GET /orders/:id` é o "ver um pedido". Isto é **BOLA** — **API1:2023**. Mesma classe do `bola-sequential-id`; aqui o id do pedido é um **UUID v4**, não um inteiro. **A premissa, em uma frase:** o UUID de um pedido da alice chegou às suas mãos por um canal do mundo real (chamada de suporte, print, link compartilhado) — ids circulam assim. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar o handler vulnerable. **Idêntico ao do 01** exceto a busca por string (`ORDERS[req.params.id]`, sem `Number()`). Ele **chama `authenticate()`** (`401` em token ruim) mas **não** compara `order.owner` com o chamador. O bug é **o que não está lá**. Assimetria lista-vs-detalhe: `GET /orders` filtra por dono, `GET /orders/:id` não. Notar que **não greppa** e que ter `authenticate()` ali **engana** o revisor apressado. (Creditar o `bola-sequential-id`: é o mesmo handler, o UUID não mudou o bug.)

### 3. How auth works in this lab (subseção curta)
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo). Token **real, cripto-forte** (`randomBytes`), mapeado ao usuário. (i) a **autenticação É imposta** (token ruim → `401`); (ii) usar a identidade pra **autorizar o objeto** é outra pergunta — e o vulnerable não usa. **Disciplina cravada:** o ataque **não toca** o token. **E o eixo certo:** o que virou UUID foi o **id do pedido**, não o token — não confundir.

### 4. Baseline — capturar o token e ver o escopo correto
- `POST /login` `{"user":"dana"}` → `{"token":"<dana-token>"}`. Bloco colável.
- `GET /orders` com `Authorization: Bearer <dana-token>` → `200`, **só** o pedido da dana (o UUID `edec4558-…`). Prova que a API **sabe exatamente quem você é** e te escopa certo. **Ponto novo a cravar:** a sua lista te dá **só o seu** UUID — e um UUID **não revela nada** sobre os outros (diferente do `1007` do `bola-sequential-id`, que denunciava a faixa contígua). O app **não te dá pista nenhuma** dos ids alheios.
- `GET /orders/edec4558-...` com o Bearer da dana → `200`, o próprio pedido. A feature faz o que promete.
- **Baseline de acesso autorizado (device de contraste, como no 01):** logar como `alice` (`{"user":"alice"}` → `<alice-token>`) e pedir o UUID vazado com o **token da alice** → `200`, o pedido dela. **É assim que o acesso autorizado a `376d2491-…` se parece.** (No mundo real você não teria o token da alice — só o id vazado e o seu próprio token; no lab você controla os dois logins, e este é só o device pra o contraste "mesmo objeto, dois chamadores".)

### 5. Step 1 — Read the leaked order (BOLA confirmado)
- **Premissa aplicada:** você recebeu de fora o UUID de um pedido da alice: `376d2491-7bc1-44ea-b1f2-81cf7a34af58`. Você **não** o adivinhou nem o reconstruiu — ele **vazou** (suporte/print/link).
- `GET /orders/376d2491-7bc1-44ea-b1f2-81cf7a34af58` com o Bearer da **dana** → `200` com o pedido da **alice** — nome, endereço de entrega, item, valor. Bloco:
  ```
  GET /orders/376d2491-7bc1-44ea-b1f2-81cf7a34af58 HTTP/1.1
  Host: 127.0.0.1:8202
  Authorization: Bearer <dana-token>
  ```
- Você leu o pedido de outra usuária — **com PII** — usando **o seu próprio token válido**, só usando um id que não é seu. Isso é **BOLA**. O UUID não te protegeu de nada: assim que a atacante **tem** o id, o check ausente entrega o objeto.
- **Mesmo objeto, dois chamadores, os dois `200`:** o `376d2491-…` que a **alice** leu legitimamente no baseline volta `200` também pra **dana**. O servidor **resolve corretamente duas identidades diferentes** e **entrega o mesmo objeto às duas** — porque a identidade, embora conhecida, **nunca entra na decisão de acesso**. É aí que mora o BOLA. (Mesma prova do 01 — creditar.)

### 6. Step 2 — What the vuln is NOT, and the Intruder inversion (passo de contraste OBRIGATÓRIO — CLAUDE.md §5)

Duas metades. A primeira isola a causa (auth ≠ id); a segunda nomeia a inversão do sinal do Intruder.

**Metade A — não é identidade quebrada, e não é o formato do id (creditar o `bola-sequential-id`):**
- `GET /orders/376d2491-…` **SEM** `Authorization` → **`401`**. A autenticação **funciona**.
- `GET /orders` **COM** o Bearer da dana → escopo correto (só o pedido dela). O **mesmo** token escopa certo aqui e escopa **nada** no detalhe. Logo **não é impersonation** — você esteve autenticada como `dana` o tempo todo. É um check que **existe** num handler e **falta** no outro. *(O `bola-sequential-id` faz essa isolação em três requests, em detalhe — aqui basta creditá-la e não reabrir.)*
- A diferença vs. o 01: lá a frase "um id não-adivinhável só encareceria a descoberta" era **teoria**; aqui ela é **fato demonstrado** — o id é não-adivinhável e o BOLA aconteceu mesmo assim.

**Metade B — o mesmo ataque do átomo 01, e a inversão nomeada:**
- **(a)** um **UUID inventado** no Repeater — ex.: `ffffffff-ffff-4fff-8fff-ffffffffffff` — com o Bearer **válido** da dana → **`404`**. Ter um token válido não conjura objetos; e o app **não vaza** quais UUIDs são reais — um chute só erra.
- **(b)** o **MESMO movimento que derrubou a base no `bola-sequential-id`** — mandar `GET /orders/§id§` pro **Intruder** e varrer uma **leva de UUIDs aleatórios** — **sabendo de antemão que ninguém acha um UUID por força bruta** (o espaço é ~2¹²²; isto é pra ver o que acontece, não uma tentativa séria de enumerar). Resultado: **tela inteira de `404`**.

  > **REDAÇÃO obrigatória (a ressalva mora na MESMA frase que propõe o passo):** não escrever "vamos enumerar os UUIDs"; escrever "veja o que acontece ao aplicar aqui a técnica do átomo anterior — sabendo que UUID não se acha por brute force". Sem essa ressalva o passo soa ingênuo.

- **A inversão, escrita explicitamente:** no `bola-sequential-id`, um **muro de `404` no Intruder era a prova do fix** (a app corrigida recusando você). Aqui, o **mesmo muro de `404`** sai da app **vulnerable** — e significa só "**não achei**", não "**não há o que achar**". O check continua **ausente**: alimente o Intruder (ou o Repeater) com o **id real vazado** (`376d2491-…`) e o objeto sai na hora, com PII. **Escrever a lição:** *a tela do Intruder não diz se a aplicação está corrigida — um muro de `404` é "não achei", não "não há o que achar".* (Esta é a **frase-âncora** do walkthrough — uma casa só; ver "Frases-âncora".)

**Conclusão do passo (§5):** a causa é a **object-level authorization ausente**, não o formato do id. O exploit do Step 1 teve sucesso pelo **mesmo check ausente** do 01; o UUID mudou **só o custo de descoberta** (de trivial pra inviável), **não o acesso**. Melhorar o id sem pôr o check é consertar o eixo errado.

### 7. Why the fix works (porta 8302) — o fix é o do átomo 01
Repetir contra o `fixed/` em `127.0.0.1:8302`:
- `GET /orders/376d2491-…` (o id vazado da alice) com o Bearer da dana → **`404`**. O pedido existe, mas não é seu — a guarda de posse recusa.
- `GET /orders/edec4558-…` (o pedido da **própria** dana) com o Bearer da dana → `200`. Donos continuam lendo os próprios pedidos. Sem/ruim token → `401`.
- **`404` indistinguível:** o `404` do pedido alheio (`376d2491-…`) é byte a byte o `404` de um UUID inventado (`ffffffff-…`) — **sem oráculo**. Mesma escolha e mesma razão do `bola-sequential-id`; **forward pro DIFF** (que referencia o DIFF do 01) pro argumento completo.
- **O fix é o do `bola-sequential-id`, byte a byte na guarda** — e ele **não** trocou nada do id (o id já era UUID, e continua). Prova de que a correção é **id-agnóstica**: mudou o tipo do id entre os dois átomos, e o fix é o mesmo predicado. **Forward pro DIFF** pra os dois fixes lado a lado.

**O walkthrough TERMINA aqui.** Sem script de exfiltração, sem automação além do Intruder do passo de contraste, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5).

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` em **cada** gêmeo, **self-contained, sem módulo compartilhado** — `package-lock.json` **commitado** por gêmeo. `app.ts` **difere** entre `vulnerable/` e `fixed/` só no predicado de posse do `GET /orders/:id`; **todo o resto é idêntico** entre as versões, incluindo `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json`.

**Herança do toolchain (CLAUDE.md §3.6 — fonte da verdade lida dos arquivos do `bola-sequential-id` NESTA fase):**

`tsconfig.json` — **idêntico** ao do `bola-sequential-id` (copiar):

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

- **`noUncheckedIndexedAccess: true` continua deliberado e didático** — e continua funcionando com **chave string (UUID)**: `ORDERS[req.params.id]` tipa como `Order | undefined`, então a guarda `!order` é **exigida pelo compilador** (sem ela, `order.owner` no `fixed/` dá `TS18048: 'order' is possibly 'undefined'`). **Validado nesta fase** com o toolchain exato (ver "Decisões que podem gerar dúvida"): typecheck limpo com a guarda, `TS18048` sem ela — mesmo comportamento do 01, agora com id string.

`Dockerfile` — **idêntico** ao do `bola-sequential-id`, incluindo a base `node:24.21.0-slim` (patch exato; nunca `latest` nem a tag móvel `node:24-slim`), `npm ci --omit=dev`, `USER node` no fim **sem `chown`**, `ENV HOST=0.0.0.0`, `EXPOSE 3000`:

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

`docker-compose.yml` — bind **só** em `127.0.0.1`, portas **8202/8302**:

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8202:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8302:3000"
```

- `package.json` de cada gêmeo: `"name": "bola-uuid-leaked"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Entrypoint `tsx`. **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **Roda como não-root, sem `chown`** — mesma justificativa do 01 (validada lá). Reconfirmar no smoke test da Fase 2: build OK, container sobe como `node`, `tsx` sem erro de permissão, endpoints respondendo, imagem só com `express` + `tsx`.

---

## Dependências extras

**Versões EXATAS herdadas do `bola-sequential-id` (§3.6) — lidas dos `package.json` dele NESTA fase. NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

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

- **Idênticas ao átomo 01.** `crypto` é **nativo** (`node:crypto`, para `randomBytes` do token) — não é dependência npm.
- **NÃO adicionar biblioteca de UUID** (`uuid`, `nanoid`, etc.). Os ids são **string literals fixos** no seed; nada é gerado em runtime, então não há necessidade de gerador. E `crypto.randomUUID` **também não** — o seed é literal, não gerado no boot (senão o walkthrough não poderia citar o id). Isto respeita "só inclua a lib se serve à falha ou ao fix" (§3.6): nenhuma lib de UUID serve a nenhum dos dois.
- **Classificação por RUNTIME:** `tsx` em `dependencies` (entrypoint que executa), `typescript`/`@types/*` em `devDependencies`. Gate combinado `npm audit --omit=dev` cobre exatamente o que a imagem `npm ci --omit=dev` instala e roda (`express` + `tsx`). **Escopo da imagem = escopo do audit = o que roda.**
- **Pin exato travado no `package-lock.json`** (commitado por gêmeo). Updates são **manuais** (CLAUDE.md §8.7). **Se algo no átomo 01 parecer desatualizado, seguir com o que está lá** — bump é decisão de corte de release, coordenada na série inteira (§3.6), não neste átomo.

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). BOLA é IDOR num endpoint de API — mesma classe — então a página conceitual de **IDOR** do PortSwigger é a escolha CLAUDE.md-compliant, **a mesma do `bola-sequential-id`**.

- **Primer (verificado por fetch NESTA fase — HTTP 200 direto, H1 "Insecure direct object references (IDOR)", intro conceitual "In this section, we will explain what insecure direct object references (IDOR) are…"):**
  `https://portswigger.net/web-security/access-control/idor`
  Texto do link: **"Insecure direct object references (IDOR)"** — preservado em **inglês** também no README PT (CLAUDE.md §7).

- **Referência suplementar (na descrição do README, pra ancorar "BOLA = #1 do OWASP API Top 10"):** a página **API1:2023** da OWASP API Security (H1 "API1:2023 Broken Object Level Authorization"). **Usar a URL que resolve 200 direto (re-verificada por fetch nesta emenda — sem redirect):**
  `https://owasp.github.io/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/` (com **barra final**).
  - **Já alinhada com o `bola-sequential-id`:** o chore na `main` (`fix(docs): update OWASP API Security links to resolving URLs`) trocou o link dos READMEs do átomo 01 da antiga `https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization` (que hoje faz **302 → 301** pra cá) por esta URL canônica. Os dois átomos usam a **mesma** URL — não há divergência a decidir.

**Fase 2:** re-confirmar as duas URLs por fetch na geração (o host da OWASP já migrou uma vez; pode mudar de novo).

---

## Política de cross-ref (CLAUDE.md §5 — mudou desde o átomo 01)

Publicação verificada **lendo `atoms/api/ROADMAP.md` e a árvore de `atoms/` NESTA fase**, não de memória.

- **`bola-sequential-id` está PUBLICADO em `main`** (átomo 01, `[x]` no ROADMAP; pasta com `docker-compose.yml` presente). Portanto **citá-lo é obrigatório e central**: creditar, contrastar, e mostrar os **dois fixes lado a lado** no DIFF. É o eixo do átomo inteiro.
- **PROIBIDO citar qualquer átomo de API NÃO publicado** (03 em diante: `bola-nested-resource`, `bfla-*`, etc.) — por nome, número ou descrição. Forward reference (CLAUDE.md §5). Verificado: só o 01 está publicado na série API.
- **Cross-ref a átomos WEB publicados é bem-vindo:**
  - **`idor-numeric-id`** (web/Flask, publicado) — o avô do arco; "o bug é a checagem ausente, não o id". Reusar o framing e o passo de contraste.
  - **`bola-rest`** (web/Flask, publicado) — o gêmeo web da classe BOLA. Creditar o núcleo; **não** contrastar sobre o *fix* (o código dos dois testa a posse depois da busca).
- **`idor-uuid-guessable` (web/Flask, PUBLICADO) — CROSS-REF OBRIGATÓRIO, escopo apertado. O mantenedor fechou: CITA.** Factual re-conferido **lendo os arquivos dele nesta emenda** (`README.md`, `vulnerable/app.py`, `WALKTHROUGH.md`): a variante demonstrada é **UUIDv1** (`uuid.uuid1(node=_NODE, clock_seq=_CLOCK_SEQ)`, com node + clock_seq fixos no processo); o metadado é o **`issued_at` em microssegundos exposto no dashboard `GET /`** (sem o UUID), que somado a um id v1 do próprio atacante reconstrói o id da vítima em ~10 candidatos; e a **lição 1 dele é literalmente a tese deste átomo** ("a hard-to-guess identifier is not an access control — even a perfectly random UUIDv4 is readable by anyone who obtains the id, because the missing check … was always the bug"). *(O atacante lá é `mallory`, não `dana` — não misturar o elenco.)* A citação tem **quatro partes, todas obrigatórias:**
  1. **Enquadramento = COMPLEMENTARIDADE, não sobreposição.** Os dois provam a mesma tese por **caminhos opostos** e se reforçam: o web mostra que **UUIDv1 é reconstruível a partir de metadado que a app expõe** — ou seja, "não-adivinhável" nunca foi verdade pra todo UUID; este mostra que **mesmo quando o id é genuinamente não-adivinhável (v4, e vindo de fora da app), o bug sobrevive inteiro**. Conclusão a escrever nos docs: **o formato do id não conserta nada — com o id sendo adivinhável ou não.**
  2. **A citação PROTEGE o passo de contraste — é esse o trabalho dela.** O walkthrough vai afirmar que **ninguém acha UUID por brute force**. Um aluno que depois abra o átomo web e veja um UUID sendo *reconstruído* pode concluir que este átomo foi ingênuo. **Nomear a distinção de versão — v1 carrega timestamp e MAC e é reconstruível; v4 é aleatório — mata a objeção antes de ela existir.** Registrar esse propósito é obrigatório: a **Fase 2 NÃO deve cortar a citação achando que é enfeite** — ela é a blindagem do passo de contraste.
  3. **Justificar por que ESTE átomo existe.** O átomo web ensina a tese como **uma lição entre várias**, e a **prova dele depende de o id TER SIDO adivinhável** (v1 reconstruível). Aqui a tese é o **átomo inteiro**, com o id **genuinamente fora de alcance** (v4, e chegando de fora da app). Escrever isso explicitamente: a citação **justifica a existência** deste átomo — não sugere que ele é redundante.
  4. **LIMITE DURO (o ponto mais importante desta emenda).** Citar o átomo web **APENAS pela lição do formato do id**. É **PROIBIDO mencionar, resumir, comparar ou aludir ao fix dele ou ao status code que ele usa**, em **qualquer** documento deste átomo (README, WALKTHROUGH, DIFF). O argumento do `404` aqui é **herdado do `bola-sequential-id` por referência e NÃO se reabre**. Se, na Fase 2, a redação encostar em **"lá é 403, aqui é 404"** (ou qualquer comparação de status/fix entre os átomos), **isso é violação — corte a frase inteira.**
- Termos técnicos (BOLA, IDOR, UUID, token, Bearer, object-level authorization, ownership check, enumeration oracle, brute force, PII, Trigger, payload) **não** se traduzem no PT (CLAUDE.md §7).

---

## Frases-âncora (uma casa só cada — CLAUDE.md §11 / template)

Nenhuma frase memorável aparece em **dois** documentos. Atribuição fixa:

- **WALKTHROUGH (uma casa):** a frase da inversão do Intruder — *"a tela do Intruder não diz se a aplicação está corrigida — um muro de 404 é 'não achei', não 'não há o que achar'."* Mora no passo de contraste (Metade B). **Não** repetir no DIFF nem no README.
- **DIFF (uma casa):** a conclusão dos dois fixes lado a lado — *"mudou o tipo do id, mudou a descoberta, mudou o walkthrough inteiro; a correção não mudou nada."* Mora na seção "os dois fixes lado a lado". **Não** repetir no WALKTHROUGH nem no README.
- **Não reusar** a frase-âncora do `bola-sequential-id` ("O mesmo check ausente não vaza um pedido: vaza a base…") — é a casa **dele**. Este átomo tem as suas.

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API1 — Broken Object Level Authorization** | Mesma classe do 01, de propósito. Request legítimo alcançou objeto fora do escopo (autorização), não injection. |
| Nome / classe (H1) | **Broken Object Level Authorization (BOLA)** — idêntico EN/PT | O título nomeia a classe; o slug (`bola-uuid-leaked`) qualifica a variante. Mesmo H1 do `bola-sequential-id`/`bola-rest` de propósito. |
| Papel na série | **Segundo átomo API; isola o formato do id como não-causa** | Complementa o 01: o 01 fixou o eixo "check" e deixou o id sequencial; este melhora o id (UUID) e deixa o check ausente. |
| Toolchain | **Herdado exato do `bola-sequential-id`** (express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; base `node:24.21.0-slim`) | §3.6 — herança de toolchain. Lido dos arquivos do 01 nesta fase. Bump é decisão de release. |
| Store | **Em memória (`Record<string, Order>`), sem banco** | BOLA não depende do storage. Chave string por causa do UUID. |
| Tipo do id | **`string` (UUID v4), fixo/hardcoded** | O eixo único que muda vs. o 01. Fixo pra o walkthrough citar o id literalmente e pra a premissa do vazamento fazer sentido. |
| Seed | **Espelho objeto-a-objeto do 01; só o tipo do id muda** | Prova por identidade: uma variável só. dana=1 (`edec4558-…`, era 1007); split 6/3/2 idêntico. |
| De onde vem o id | **De FORA da app (vazamento do mundo real), em uma frase** | Restrição dura "um bug só": nada na app vaza id alheio; sem endpoint de busca/dica/andaime. |
| Token | **Opaco, `crypto.randomBytes`; NÃO JWT** — idêntico ao 01 | Cripto-forte pra não ser 2ª vuln. O que virou UUID é o **id do objeto**, não o token. |
| Rotas | `POST /login`, `GET /orders` (escopada — correta nas 2), `GET /orders/:id` (vuln) | Superfície idêntica ao 01. Nenhum endpoint a mais. |
| Busca no handler | **`ORDERS[req.params.id]` (sem `Number()`)** | Chave é string (UUID). Diferença mecânica vs. 01, **idêntica** entre os gêmeos → **não** é o fix, **não** é lição. Typecheck validado nesta fase. |
| O bug | **Object-level authorization AUSENTE** em `GET /orders/:id` | Ausência de código, não payload. O UUID não muda o bug. |
| Fix (eixo único) | **Posse na mesma guarda da existência:** `if (!order \|\| order.owner !== caller) 404` | **Byte a byte o fix do 01** na região da guarda. Uma guarda, uma saída → indistinguibilidade estrutural. Sustenta a tese. |
| Status code do fix | **`404`** (não `403`), herdado do 01 | Mesma justificativa do 01; **referenciar**, não reinventar. Nuance: com UUID a pressão de oráculo relaxa, mas manter 404 inalterado É a tese (fix id-agnóstico). |
| Comentário do `fixed/` | **Herdado verbatim do 01** (inclui "a 403 here would be an enumeration oracle") | Mantém a região do fix byte-idêntica → tese máxima. A nuance UUID fica na prosa do DIFF, não no comentário. |
| Padrão de prova | **Trigger** (não Payload) | Não há sink; o exploit é id legítimo (vazado) num request legítimo. → passo de contraste obrigatório. |
| Passo de contraste | **(a) UUID inventado → 404; (b) Intruder de UUIDs aleatórios → muro de 404, com a inversão nomeada** | A ressalva ("ninguém acha UUID por brute force") mora na mesma frase que propõe (b). Muro de 404 = "não achei", não "não há o que achar". |
| Trilha | **100% Burp (Repeater + Intruder) / curl; SEM browser** | API-only (CLAUDE.md §3.3). O Intruder aqui serve à **inversão**, não à enumeração. |
| Impacto | **Escalação HORIZONTAL** — ler pedido+PII de outro usuário via id vazado | Honesto, sem overclaim. Não é RCE, não é vertical, não é enumeração da base. |
| Theory primer | **PortSwigger IDOR (bloco) + OWASP API1:2023 (suplementar)** | Mesma página do 01. URLs verificadas por fetch nesta fase (primer 200; OWASP com nova URL canônica). |
| Cross-ref | **`bola-sequential-id` central; web `idor-numeric-id`/`bola-rest` bem-vindos; `idor-uuid-guessable` CITA (escopo apertado)** | O 01 está publicado (citar). `idor-uuid-guessable`: só a lição do formato do id (complementaridade v1-reconstruível vs. v4-de-fora, blindando o passo de contraste); **fix/status dele OFF-LIMITS** (LIMITE DURO — ver Política de cross-ref). |

---

## Decisões que podem gerar dúvida durante implementação

- **Busca por string tipa limpo — VALIDADO nesta fase.** Com `noUncheckedIndexedAccess`, a dúvida real era se `req.params.id` seria `string` ou `string | undefined` (o que quebraria `ORDERS[req.params.id]`). Rodado `tsc --noEmit` (typescript **7.0.2**, tsconfig da série, `@types/express` **5.0.6**, `@types/node` **24.13.5** — o toolchain exato do 01) contra um sample com os dois handlers e o `Record<string, Order>`: **exit 0, limpo.** `req.params.id` resolve como **`string`** (a inferência de route param do Express 5 dá propriedade declarada, não index signature), então `ORDERS[req.params.id]` é `Order | undefined` e a guarda `!order` narrowa certo. Negativo confirmado: sem a guarda `!order`, `order.owner` → **`TS18048`**. Ou seja: **usar `ORDERS[req.params.id]` direto; NÃO** meter `String(...)`, `Number(...)`, nem `?? ""`. A Fase 2 roda `npm run typecheck` nos dois gêmeos como gate (host/CI, não container).
- **Tipos do Express 5 — retorno `Response` vs `void`.** Igual ao 01: os samples usam callbacks contextualmente tipados (retorno `void`), onde `return res.sendStatus(...)` **passa**. Se o gerador **anotar o retorno do handler explicitamente**, o TS reclama de devolver `Response` onde se espera `void`; a forma segura é **`res.sendStatus(401); return;`** (statement + `return` vazio), **nunca** `return res.sendStatus(...)`. Não anotar o retorno é o caminho do 01.
- **UUIDs do seed são canônicos e fixos.** Usar **exatamente** os doze da seção "Store" (não regenerar) pra a spec, o walkthrough e o DIFF citarem os mesmos literais.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia `usuário→token`, Bearer resolve de volta; `dana`/`alice`/`bob`/`carol` recebem tokens distintos e cripto-fortes (`randomBytes`). (Bloco idêntico ao 01.)
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido → **`401`** em `GET /orders` e `GET /orders/:id`.
3. **Vulnerable:** `GET /orders/376d2491-…` (alice) com o Bearer da **dana** → **`200`** com o pedido da alice + PII (BOLA); token permanece válido e intacto.
4. **Baseline correto:** `GET /orders` com o Bearer da dana lista **só** o `edec4558-…` (não vaza id nem pedido de outro); `GET /orders/edec4558-…` → `200`.
5. **Passo de contraste (a):** UUID inventado (`ffffffff-ffff-4fff-8fff-ffffffffffff`) com Bearer válido → **`404`**.
6. **Passo de contraste (b):** Intruder com leva de UUIDs aleatórios contra o **vulnerable** → **muro de `404`** (nenhum acerto — é o esperado; é a inversão, não enumeração).
7. **Fixed:** `GET /orders/376d2491-…` (alheio) → **`404`**; `GET /orders/edec4558-…` (próprio) → `200`; UUID inventado → `404` **byte-idêntico** ao do alheio (sem oráculo); sem/ruim token → `401`.
8. **`app.ts` DIFERE só no predicado de posse** do `GET /orders/:id` entre `vulnerable/` e `fixed/`. `POST /login`, `GET /orders`, helpers, imports, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` **idênticos** entre as versões.
9. **Região do fix byte-idêntica ao `bola-sequential-id`:** a linha `if (!order || order.owner !== caller) return res.sendStatus(404);` e o comentário `FIXED:` acima dela batem caractere a caractere com o `fixed/app.ts` do 01. (Conferir abrindo o arquivo do 01.)
10. **Nenhum vazamento de id/token** em resposta alguma: `order` serializado tem só `id/owner/customer/address/item/amount`; `GET /orders` não devolve pedido nem id de outro usuário; **nenhuma fonte de id alheio na app**. **Um bug só** (BOLA).
11. **Seed fixo:** os doze UUIDs são os literais canônicos desta spec; **nada** gerado no boot; **nenhuma** lib de UUID no `package.json`.
12. **API-only:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, sem render de HTML; sucesso sempre `application/json`.
13. **Bind:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1`; container `ENV HOST=0.0.0.0`. **Portas 8202 (vulnerable) / 8302 (fixed)**, internas `3000`, coerentes entre `EXPOSE`, `app.listen` e o compose.
14. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README; **`dana` feminino** no PT.
15. **Theory primer:** re-confirmar por fetch as duas URLs (primer PortSwigger; OWASP API1:2023 — usar a canônica `owasp.github.io/.../` que resolve 200, **a mesma já adotada pelos READMEs do átomo 01 na `main`**).
16. **`npm audit --omit=dev` em cada gêmeo**, advisories esperados **registrados**. O átomo é vulnerável na **lógica**, **não nas dependências** (idênticas ao 01). Meta: zero advisory de runtime.
17. **`npm run typecheck` (`tsc --noEmit`, typescript 7.0.2) verde nos DOIS gêmeos** — inclusive o `vulnerable/` (vulnerável na lógica, não no tipo). Gate de **host/CI**, não do container. (Shape validado nesta fase; ver "Decisões que podem gerar dúvida".)
18. **Frases-âncora:** cada uma numa casa só (WALKTHROUGH: inversão do Intruder; DIFF: dois fixes lado a lado); **não** reusar a frase-âncora do `bola-sequential-id`.
19. **README abre definindo "leaked" (E2):** o parágrafo de abertura (EN+PT), antes de qualquer passo, traz a frase de definição (id de FORA da app; a app não vaza id; único bug = check de posse ausente), coerente com a linha do átomo 02 no `atoms/api/ROADMAP.md`, **sem citar átomo**.
20. **Cross-ref `idor-uuid-guessable` — LIMITE DURO:** citado só pela lição do formato do id (v1-reconstruível vs. v4-de-fora, complementaridade). **Zero** menção/resumo/comparação/alusão ao fix ou status code dele em README/WALKTHROUGH/DIFF. Varredura na Fase 2: nenhum "403" (nem comparação de status) perto de `idor-uuid-guessable` nos docs; o argumento do `404` é o do `bola-sequential-id`, por referência.

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; toolchain herdado e lido dos arquivos do 01; shape TS validado; URLs re-verificadas por fetch nesta emenda. Os três pontos de atenção da versão anterior estão **resolvidos**: (i) a URL suplementar da OWASP foi corrigida na `main` e esta spec já usa a canônica; (ii) o cross-ref do `idor-uuid-guessable` foi **fechado — cita, escopo apertado, com LIMITE DURO** no fix/status; (iii) a wording da linha do átomo 02 no ROADMAP foi corrigida na `main`, e a definição de "leaked" dos READMEs (E2) segue essa mesma linha.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é uma **prova por identidade** com o `bola-sequential-id`. Cada arquivo deve poder ser lido com o arquivo par do 01 aberto ao lado; o que a spec diz ser "idêntico" tem que **ser** idêntico (seed objeto-a-objeto, bloco de auth, região do fix, toolchain). **Conferir abrindo os arquivos do 01**, nunca de memória.
- **A tese é o código, sem adjetivo.** Se a geração improvisar outra forma de fix (um segundo `if`, um `403`, uma saída diferente), a prova cai. A região do fix é **byte a byte** a do 01.
- **Dois eixos, sempre separados:** formato do id = **descoberta**; check ausente = **causa**. Aqui o eixo 1 foi levado ao máximo (UUID) e o bug sobreviveu — a metade espelhada da prova do 01.
- **Um bug só, restrição dura:** **nada** na app vaza id alheio. Se surgir vontade de um endpoint/campo que "dê" o id ao atacante, **PARE e pergunte** — o id vem **de fora**.
- **Token cripto-forte, intocado; o UUID é do OBJETO.** `randomBytes` no token (idêntico ao 01). O que virou UUID é o id do pedido. **PROIBIDO** técnicas de ataque a token.
- **O handler vulnerable CHAMA `authenticate()`** mas descarta a identidade — **não** transformar em "falha de autenticação". Seguir o passo de contraste.
- **Passo de contraste com a inversão nomeada** é obrigatório e é o beat-assinatura: (a) UUID inventado → 404; (b) Intruder de UUIDs aleatórios → muro de 404, **com a ressalva na mesma frase** de que ninguém acha UUID por brute force; e a lição explícita "muro de 404 = não achei, não = não há o que achar".
- **Status `404` (não `403`):** herdar do 01, **referenciar** o DIFF do 01, **não** reinventar o argumento nem propor `403`. A nuance (oráculo relaxa com UUID) entra a favor da tese (fix id-agnóstico), não como alternativa.
- **Cross-ref:** `bola-sequential-id` é central e publicado (citar, dois fixes lado a lado). Web `idor-numeric-id`/`bola-rest` bem-vindos. **`idor-uuid-guessable` CITA, escopo apertado** — só a lição do formato do id (complementaridade **v1-reconstruível vs. v4-de-fora**, que blinda o passo de contraste e justifica a existência deste átomo); **LIMITE DURO: o fix/status dele é off-limits em TODO doc** — nada de "lá é 403, aqui é 404" (ver Política de cross-ref, 4 partes). **Nenhum** átomo de API não-publicado (03+).
- **Impacto honesto:** escalação **horizontal** + exposição de **PII** via id **vazado**; **não** chamar de enumeração da base (não rola com UUID), nem RCE, nem vertical.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# bola-uuid-leaked — Broken Object Level Authorization (BOLA)`. Headers de seção **traduzidos** no PT; termos técnicos em inglês; **`dana` feminino** no PT.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série (id + classe + 1 linha), quando o mantenedor cortar a fase.
- **README abre definindo "leaked" (E2):** a primeira coisa lida (EN+PT), antes de qualquer passo, define "leaked" = o id circulou por um canal de **FORA** da app (chamado de suporte, print, link compartilhado), a app **não vaza id nenhum**, e o único bug é o check de posse ausente. Mesma definição da linha do átomo 02 no `atoms/api/ROADMAP.md`; **sem citar átomo** (texto sugerido na seção "De onde vem o id").
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 02 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec. *(A linha do átomo 02 no ROADMAP já foi corrigida na `main` pra bater com o design "id de fora, a app não vaza nada"; a definição de "leaked" dos READMEs (E2) segue essa mesma linha.)*
- **Validar manualmente na Fase 2** (CLAUDE.md §11): todos os itens do checklist acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8202` (vulnerable), `127.0.0.1:8302` (fixed). Bind **só** em `127.0.0.1`.

---

## Verificação factual do átomo 01 (conferida LENDO os arquivos nesta fase)

A tese depende de os dois átomos serem de fato idênticos naquilo que a spec afirma ser idêntico. Tudo abaixo foi conferido **lendo os arquivos publicados do `bola-sequential-id` nesta fase de planning** (não de memória):

- **Toolchain** (de `vulnerable/package.json` e `fixed/package.json`, idênticos): express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5.
- **`Dockerfile`** (os dois, idênticos): base `node:24.21.0-slim`, `npm ci --omit=dev`, `COPY tsconfig.json` + `COPY app.ts`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm","start"]`.
- **`tsconfig.json`** (os dois, idênticos): `nodenext`, `target/lib es2024`, `types: [node]`, `strict`, `noUncheckedIndexedAccess`, `esModuleInterop`, `noEmit`.
- **`docker-compose.yml`:** bind `127.0.0.1`, `8201:3000` / `8301:3000`.
- **`vulnerable/app.ts`:** handler `GET /orders/:id` com `const order = ORDERS[Number(req.params.id)]; if (!order) return res.sendStatus(404); … res.json(order);` e o comentário `VULNERABLE:`.
- **`fixed/app.ts`:** a guarda `if (!order || order.owner !== caller) return res.sendStatus(404);` e o comentário `FIXED: … (a 403 here would be an enumeration oracle).` — copiados verbatim nesta spec.
- **Auth:** `USERS = new Set([...])`, `TOKENS = new Map`, `issueToken` com `randomBytes(24).toString("base64url")`, `authenticate` por `Bearer`.
- **`GET /orders`:** `filter((o) => o.owner === caller)`, idêntico nas duas versões.
- **Seed:** doze pedidos `1001–1012`, owners alice(6)/bob(3)/carol(2)/dana(1, o 1007), com os nomes/endereços/itens/valores replicados objeto-a-objeto no seed UUID desta spec.
- **Docs:** H1 `# bola-sequential-id — Broken Object Level Authorization (BOLA)`; estrutura do README (banner, primer, stack note, API-only, auth-simulada, run, fixed version); WALKTHROUGH (Context/Spot the bug/How auth/Baseline/Step 1/Step 2/Step 3/Why the fix); DIFF (fix, uma guarda uma saída, 404-não-403, o que o fix NÃO faz, assimetria da lista, token opaco, "isto é BOLA"); primer PortSwigger IDOR + suplementar OWASP API1:2023.
- **Shape TS deste átomo:** `ORDERS[req.params.id]` (chave string) validado com `tsc --noEmit` no toolchain exato — limpo com a guarda, `TS18048` sem ela.
