# Spec — Átomo API 05: `bfla-method-based`

> Documento de especificação para o Claude Code implementar o **quinto átomo da série API** do projeto `atomicvulns` (Fase 1 API, "Authorization: Object & Function", milestone `v1.1`; **fecha a fase** — é o último dos cinco). Classe: **BFLA — Broken Function Level Authorization**, o **API5:2023** do OWASP API Security Top 10 (2023) — a **mesma categoria do átomo 04** (`bfla-admin-function`), de propósito: a pasta `API5-broken-function-level-authz/` já existe, e este é o segundo átomo dela. Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **Este átomo move o 04 um passo pra perto de produção.** O 04 mostrou um endpoint admin **sem check nenhum** — a função inteira desprotegida. Este mostra uma falha mais sutil e mais comum: a autorização **existe e funciona** num método do path (`GET`), e **falta** em outro método do **mesmo** path (`PATCH`). O dev protegeu a leitura, achou que protegeu o recurso, e deixou a escrita aberta. A lição transferível, a cravar em todo doc: **autorização se aplica a (método + path), não a path.** Tudo o que esta spec afirma sobre os átomos 01–04 foi conferido **lendo os arquivos publicados nesta fase**, não de memória (ver "Verificação factual dos átomos publicados").
>
> **O EIXO DUPLO — e a disciplina que ele exige.** A autorização que varia por método aqui é um check de **posse** (object-level, o mesmo dos átomos de BOLA/API1): cada usuário pode ler/editar o **próprio** registro, não o dos outros. O `PATCH` desprotegido ignora esse check. O átomo costura dois eixos: o eixo da **vulnerabilidade** é o **MÉTODO** (API5/BFLA); a posse é só o **conteúdo** do check que varia. A pergunta de auditoria é **"a autorização cobre todos os métodos deste path?"**, NÃO "de quem é o objeto?". **Sem essa disciplina o átomo é lido como BOLA — e não é.** Toda a redação (código, WALKTHROUGH, DIFF) existe pra manter esse eixo visível.
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **`atoms/api/API5-broken-function-level-authz/bfla-admin-function/`, inteiro** — o **irmão de categoria** (mesmo API5). Define a pasta, o bloco de auth com `Map<string, User>`, o tratamento de prototype pollution por `Map`, o argumento `403`/RFC 9110, e a forma dos seis documentos. O contraste 04↔05 (eixo da **função** vs eixo do **método**) é material deste átomo.
> 2. **`atoms/api/API1-broken-object-level-authz/bola-sequential-id/` e `bola-uuid-leaked/`, inteiros** — a **origem do check de posse** que este átomo reusa como conteúdo. O `order.owner === caller` deles é o ancestral do `handle === caller` daqui.
> 3. **`atoms/api/API1-broken-object-level-authz/bola-nested-resource/`, inteiro** — o precedente da armadilha do **"check que existe e passa"**: no 03, no eixo do objeto (pai vs filho); aqui, no eixo do método (`GET` vs `PATCH`). Também o precedente do gate **antes** da busca e do `403` honesto por existência não-sensível.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Identidade

- **ID:** `bfla-method-based`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API5 — Broken Function Level Authorization**
- **Pasta:** `atoms/api/API5-broken-function-level-authz/bfla-method-based/` — **segunda pasta da categoria API5**; a `API5-broken-function-level-authz/` já existe (nasceu com o átomo 04).
- **Número sequencial (série API, conta do 01):** 05
- **Porta vulnerable:** `127.0.0.1:8205`
- **Porta fixed:** `127.0.0.1:8305`
- **Porta interna do container:** `3000` (igual a 01–04). Compose mapeia `127.0.0.1:8205:3000` e `127.0.0.1:8305:3000`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1); `ENV HOST=0.0.0.0` só dentro do container.
- **Fase / milestone:** Fase 1 API, `v1.1` (quinto átomo; **fecha a fase**).
- **Branch de trabalho:** `atom/bfla-method-based` — criada nesta fase a partir de `main` atualizada.
- **H1 dos READMEs (idêntico em EN e PT):** `# bfla-method-based — Broken Function Level Authorization (BFLA)`. O título nomeia a **classe**; o slug qualifica a variante (CLAUDE.md §5). Mesmo H1 do átomo 04 (mesma classe), de propósito — o que distingue é o slug e a demonstração.
- **Theory primer:** ver seção "Theory primer" (URL verificada por fetch nesta fase — HTTP 200, sem redirect; é a **mesma** página do átomo 04, Access control, **não** a de IDOR).

---

## A tese do átomo

> **A autorização se aplica a (método + path), não a path.** O servidor tem um check de posse no `GET /users/:handle` — e ele funciona: você só lê o seu próprio registro. O `PATCH /users/:handle`, o **mesmo path**, não tem esse check. O dev guardou a leitura, achou que guardou o recurso, e deixou a escrita aberta. Autenticado e dono do próprio registro não é autorizado a **escrever** no de outro — mas o método que escreve nunca pergunta de quem é o registro.

### O eixo é o método — e isso é a lição inteira

Os átomos de API1 (01–03) perguntavam sobre o **objeto** (*de quem é este pedido?*). O átomo 04 perguntava sobre a **capacidade/função** (*você pode promover alguém?*), com a função **inteira** desprotegida. Aqui a pergunta de auditoria é mais afiada: **"a autorização cobre todos os métodos deste path?"** — e a resposta, no `vulnerable/`, é *não*: cobre o `GET`, não cobre o `PATCH`. A falha **não** é que o check de posse esteja errado (ele está certo, e morde no `GET`); é que ele **não cobre todos os métodos** do path.

### O eixo duplo, e a disciplina que ele exige

A autorização que varia por método **é** um check de posse — object-level, idêntico em espírito ao `order.owner === caller` de 01/02. Isso cria o risco de o aluno ler o átomo como BOLA. A disciplina que desarma esse risco:

- **O eixo da VULNERABILIDADE é o MÉTODO (API5/BFLA).** O que está quebrado é a **cobertura de autorização por método** de um path. É function-level authorization — o controle de acesso à *operação* (o par método+path), não ao *objeto*.
- **A posse é só o CONTEÚDO do check que varia.** Que o check seja de posse (e não de papel, como no 04) é detalhe de *o que* a autorização confere; não muda o eixo da falha, que é *qual método* ela cobre.
- **A pergunta de auditoria cravada:** *"a autorização cobre todos os métodos deste path?"* — **NÃO** *"de quem é o objeto?"*. Toda a redação serve a manter esse eixo em foco.

### O erro de leitura a combater — e ele determina o desenho

Este átomo tem **duas** leituras erradas prováveis, e o desenho existe pra desarmar as duas. O WALKTHROUGH **nomeia cada uma e a desmonta** (ver "Walkthrough"):

1. **"Isto é BOLA."** O aluno vê um registro alheio sendo escrito e pensa "mexi no objeto de outro" — raciocínio de objeto. **Desarme (pelo passo de contraste):** o `GET /users/alice` com o seu token dá **`403`** — o check de posse **existe, está correto e morde**; a object-level authorization **não está quebrada**. Se fosse BOLA, o `GET` também vazaria. Não vaza. Logo a falha não é o check de posse estar errado; é ele não cobrir o `PATCH`.
2. **"Isto é o átomo 04 de novo."** O aluno pensa "endpoint sem check, igual ao 04". **Desarme (pelo mesmo contraste):** o `403` do `GET /users/alice` prova que **há** autorização funcionando neste path — diferente do 04, onde a função não tinha check **nenhum**. 04 = função inteira sem authz; 05 = authz presente num método, ausente em outro do **mesmo** path.

> **A armadilha do "check que existe e passa", agora no eixo do método.** O 03 mostrou um check presente apontando pro objeto errado (o pai, não o filho). Aqui o check está presente e **correto** — só não cobre todos os métodos. O revisor apressado vê o check de posse no `GET`, conclui "o recurso está protegido", e não percebe que o `PATCH` do mesmo path passou em branco.

### Por que API5 (Broken Function Level Authorization)

O bug **não é** "input virou código" (injection) nem "um objeto fora do escopo foi lido" (BOLA, o eixo do objeto). É **"um método de um path não tem a autorização que os outros métodos têm"** — controle de acesso **no nível da função/operação**: **API5** no OWASP API Security Top 10 **2023**. É o caso canônico de method-based BFLA — o mesmo que a PortSwigger descreve em "Broken access control resulting from platform misconfiguration" (um método restrito, outro tolerado no mesmo URL). Situe nessa edição, **sem arqueologia** (CLAUDE.md §5). Referência OWASP em **texto simples** (`API5:2023`), **sem link** — o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md`. Por ser vuln de **lógica/autorização** (Trigger, não Payload), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório (ver "Walkthrough").

---

## O que este átomo acrescenta (vs. 01–04)

**Honestidade pedagógica:** 01–03 ensinaram BOLA (o eixo do objeto); 04 estreou API5/BFLA com uma função inteira sem check (eixo da função, escalação **vertical**). Este **credita e não reabre** nada disso. Ele existe por três eixos novos:

1. **A falha é de COBERTURA POR MÉTODO, não de ausência total.** Primeiro átomo em que a autorização **existe e funciona** num método do path e **falta** em outro. No 04 a função não tinha check nenhum; aqui o `GET` tem o check certo e o `PATCH` não. É mais perto de produção: o bug de método-esquecido é um dos jeitos mais comuns de BFLA aparecer no mundo real.
2. **Mesma categoria (API5), outro eixo dentro dela.** 04 = eixo da **função** (uma capacidade admin-only sem check → vertical). 05 = eixo do **método** (um método de um path sem o check que o irmão-método tem → horizontal, entre pares). A pasta `API5-*` ganha a segunda volta, e o contraste 04↔05 **é** material.
3. **O check que falta é de POSSE, reusado dos átomos de BOLA.** O conteúdo do check (`handle === caller`) é o descendente direto do `order.owner === caller` de 01/02 — mas aqui ele é o *conteúdo* de um check que varia por método, não a lição em si. O átomo mostra a posse como a série já a conhece, e desloca a lição pro eixo do método.

> **Contraste a cravar (WALKTHROUGH e DIFF):** no 04 o handler não checava **nada** sobre o chamador; aqui o handler-irmão (`GET`) checa **certo** e o handler atacado (`PATCH`) não checa. Mesma categoria (API5), eixos diferentes: função inteira ausente (04) vs um método descoberto num path cujos outros métodos estão cobertos (05).

---

## Feature simulada — configurações de conta (API-only, sem HTML)

**Perfil de conta de uma plataforma multiusuário.** Cada usuário tem um perfil com um **nome de exibição** (display name). A API de self-service deixa o usuário **ver** o próprio perfil (`GET /users/:handle`) e **editar** o nome de exibição (`PATCH /users/:handle`). Do ponto de vista do produto, "você só mexe no seu próprio perfil" — e o `GET` até confere isso. O que o dev esqueceu foi conferir o mesmo no `PATCH`.

**API-only por natureza** (CLAUDE.md §3.3 — a série API é API-only): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`; erros via `res.sendStatus(...)` (igual a 01–04). Requests com corpo JSON no `POST /login` e no `PATCH`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl** (ver "Walkthrough").

### A descoberta é "tente o outro método" — e isso é parte legítima da classe

Diferente do átomo 04 (onde a descoberta do endpoint admin foi **declarada** como premissa, pra não encenar o que BFLA real não tem), aqui a "descoberta" **é** a técnica: o atacante já edita o **próprio** perfil pelo `PATCH`, então aponta o mesmo `PATCH` pro handle de outra pessoa. Tentar o outro método num path que você já acessa **é** o movimento de method-based BFLA — não há nada a declarar nem a esconder. Nenhum endpoint de descoberta, nenhum índice de rotas, nenhum erro que confirme existência: a superfície é mínima e o único bug é a cobertura de método ausente (ver "Rotas").

---

## Autenticação — token opaco, cripto-forte (mesmo mecanismo de 01–04)

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados e devolve `{ "token": "<opaco>" }`. Mapa `token → usuário` **em memória**, resolvido por lookup. **NÃO é JWT.** Os helpers de auth (imports, `TOKENS`, `issueToken`, `authenticate`) são **byte a byte** os de 01–04 (conferido: linhas de auth idênticas; md5 do bloco batendo) — **copiar, não reescrever**. Token com `randomBytes(24).toString("base64url")`: um token previsível seria uma segunda vulnerabilidade e violaria "um átomo = uma vuln" (CLAUDE.md §2). O ataque **não toca** o token.

**Estrutura de `USERS` — `Map<string, User>`, igual ao 04 (e pela mesma razão estrutural).** Em 01–03, `USERS` é um `Set<string>` (a identidade é só o handle). Aqui cada usuário carrega um **nome de exibição editável**, então `USERS` é um **`Map<string, User>`** onde `User = { displayName: string }`. O `Map` (em vez de objeto literal) **não é escolha estética**: o `PATCH` **escreve** através de um lookup por chave-string vinda do path (`:handle`), e um objeto literal abriria **prototype pollution** (`__proto__`/`constructor`) — a segunda vuln que o 04 também teve que fechar. Ver "Store / dados". O `USERS.has(user)` do `POST /login` é a mesma forma de toda a série (Set e Map compartilham `.has`).

**O que a auth prova e o que NÃO prova (deixar explícito — faz parte da lição):**

- **Autenticação prova *quem você é*.** Token ausente/ruim → `401`, no `vulnerable/` exatamente como no `fixed/`.
- **A posse (*este registro é seu?*) é *o que você tem direito de operar*.** No `GET`, essa pergunta é feita (nos dois gêmeos). No `PATCH` do `vulnerable/`, **não** é feita; no `fixed/`, passa a ser. Essa é a única diferença entre os gêmeos.

**Usuários seedados (elenco da série — CLAUDE.md §5):**

- **`clancy`** — o **atacante** (você). Dono do **próprio** registro (`clancy`). É `clancy` que edita o registro da `alice`, sem ter direito. (Elenco da série API: `clancy` é **masculino**; nos docs PT, "o atacante", "você mesmo", "dele". O masculino do **papel** — "o dono", "o chamador" — coincide com o da pessoa; não há distinção a manter.)
- **`alice`** — a **vítima**. Dona do **próprio** registro (`alice`): é o perfil que `clancy` edita no exploit.

**SEM admin.** Este átomo **não precisa** de papel administrativo — e não tê-lo o mantém distinto do 04 (que precisava de um admin seedado pra mostrar a função funcionando pra quem pode). Aqui o **caminho positivo do fix** é `clancy` editando o **próprio** registro (`PATCH /users/clancy` → `200`), que a mesma conta atacante já pode fazer legitimamente. Dois usuários bastam; nenhum papel.

**Requisito de README (EN+PT) — declarar o atalho:** o login sem senha é um **atalho deliberado do laboratório, não a vulnerabilidade**, e a autenticação em si **é imposta** (token ruim → `401`). Uma frase, **sem citar átomo** (mesmo requisito de 01–04).

---

## Store / dados — usuários com um campo editável, em memória

**Sem banco** (CLAUDE.md §3.4). Estruturas TS. O `TOKENS` cresce a cada login; o `USERS` tem o nome de exibição de cada um e **muda em runtime** quando um `PATCH` acontece (ver "Estado mutável").

```ts
// --- Simulated identity: an opaque, server-side token; users own their own profile ---
// Each user owns exactly the record keyed by their own handle. displayName is an ordinary,
// editable field -- NOT a privilege flag (that would collide with bfla-admin-function and the
// future bopla- atoms, and blur which axis this atom teaches). Ownership here is handle == caller.
// A Map, not a plain object: PATCH writes THROUGH a path-string lookup, so an object literal
// would expose prototype pollution (__proto__/constructor); Map.get() never walks the chain.
type User = { displayName: string };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park"  }],   // attacker (you) -- owns this record
  ["alice",  { displayName: "Alice Nguyen" }],   // victim -- owns this record; edited in the exploit
]);
```

- **`displayName` é um campo COMUM**, não um flag de privilégio. Escrever `is_admin`/papel aqui invadiria o átomo 04 e o futuro `bopla-mass-assignment`, e embaralharia qual é a lição. Dado fake óbvio, sem PII real (handles de login + nomes de exibição claramente de teste).
- **Posse = `handle === caller`.** Cada usuário é dono do registro cuja chave é o próprio handle. É o `order.owner === caller` de 01/02 colapsado na própria chave: o "dono" do registro `alice` é `alice`.
- **Nenhum outro campo, nenhum outro usuário.** Superfície mínima: o registro tem só `displayName`; o seed tem só `clancy` e `alice`. Não há papel, não há admin (ver "Autenticação").

### Por que `Map`, e não `Record` — o `:handle` abre prototype pollution (validado nesta fase)

**Decisão do mantenedor, mesma do 04, e a razão tem que ficar escrita.** O `PATCH` **escreve** através de `USERS.get(req.params.handle)` seguido de `user.displayName = ...`. Se `USERS` fosse **objeto literal** (`Record`), o lookup seria `USERS[req.params.handle]` — e o objeto literal traria `Object.prototype` na cadeia, abrindo **prototype pollution**, que tem átomo web dedicado neste repo:

- `PATCH /users/__proto__` faz `USERS["__proto__"]` devolver `Object.prototype` (**truthy** — a guarda `!user` **não pega**), e a linha seguinte executa `Object.prototype.displayName = <input>`. A partir daí **todo objeto do processo** sem `displayName` próprio herda o valor injetado. (`constructor` cai na mesma armadilha.) **Validado em protótipo nesta fase** (ver "Validação de typecheck e runtime"): com `Record`, `__proto__` → `200` e `({}).displayName` fica poluído; com `Map`, `__proto__`/`constructor` → `404` e `({}).displayName` continua `undefined`.
- Isso violaria "um átomo = uma vuln" (CLAUDE.md §2) — o átomo é de BFLA, não de prototype pollution.

**Por que o risco aparece aqui (e, em API1, só apareceu no 04):** este átomo **escreve** através de um lookup com chave-string vinda do path — a mesma superfície do 04. Os átomos 01/03 usam `Number(...)` na chave (`Number("__proto__")` é `NaN`) ou só **leem**; o 02 indexa por string mas só lê. Escrever através da chave-string é o que traz o risco — e a correção é estrutural: **`Map<string, User>`**. Ganhos (os mesmos três do 04):

1. **`Map.get()` não percorre a cadeia de protótipo.** `USERS.get("__proto__")`/`USERS.get("constructor")` → `undefined` → `404` (no `vulnerable/`, onde o `PATCH` chega ao lookup). O problema **desaparece estruturalmente**.
2. **`USERS.has(user)` no `POST /login`** continua a MESMA forma da série.
3. **`Map.get()` tipa como `User | undefined`** (independente de `noUncheckedIndexedAccess`), então a guarda `!user` é **exigida pelo compilador** (o `PATCH` e o `GET` desreferenciam `user.displayName`).

> **Alternativa CONSIDERADA e DESCARTADA:** `Record` + `Object.hasOwn(...)`. Funciona, mas a guarda fica arbitrária pra quem lê e esconde o motivo. O `Map` torna a intenção estrutural. **Não reintroduzir o `Record`.** (Idêntico ao veredito do 04.)

---

## Rotas — superfície mínima, três rotas, nenhuma a mais

Imports: `import express from "express";` e `import { randomBytes } from "node:crypto";`. Bootstrap (`const app = express();` + `app.use(express.json());`), `USERS`, `TOKENS`, `issueToken`, `authenticate` e o rodapé `listen` são **idênticos** entre `vulnerable/` e `fixed/`. Superfície: **três rotas, nenhuma a mais** — `POST /login`, `GET /users/:handle` (correto nos dois gêmeos) e `PATCH /users/:handle` (o vulnerável). **Sem** `GET /users` (listagem), **sem** `GET /me`, **sem** DELETE, **sem** índice de rotas.

> **Nota de nomenclatura do parâmetro.** A superfície no enunciado aparece como `/users/:id`; a spec a realiza como `/users/:handle` — o recurso é o registro de usuário endereçado pelo handle de login, e a posse é `:handle === caller`, exatamente a forma que o `Map<string, User>` (chave = handle) e o elenco da série (`:handle` no 04) já usam. É escolha **mínima/estilística** de consistência com o 04, **não** uma lição; não promover a contraste pedagógico.

### `POST /login` — obter o próprio token (idêntico nas três versões anteriores)

Recebe `{ "user": "<nome>" }`, valida contra `USERS` (via `USERS.has(user)`), devolve um token opaco. Sem senha (atalho de auth). Usuário desconhecido/ausente → `400` (higiene).

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

### `GET /users/:handle` — ler o próprio perfil (CORRETO nos DOIS gêmeos — a prova viva da authz de posse)

Este endpoint **nunca é a falha**. Ele autentica, confere a **posse** (`:handle === caller`), e só então devolve o registro. É a prova de que a object-level authorization **existe e funciona neste servidor** — o que afasta o átomo 04 (lá não havia check nenhum) e desarma a leitura "isto é BOLA" (o check de posse está correto).

```ts
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  res.json({ handle: req.params.handle, displayName: user.displayName });
});
```

- **A guarda de posse vem ANTES da busca.** Depois dela, `:handle === caller`, e `caller` é sempre um handle seedado (tokens só são emitidos pra usuários válidos) — então o `USERS.get(...)` sempre acha, e o `404` do `!user` é **inalcançável em runtime no `GET`**. Ele fica porque o compilador o **exige** (`user.displayName` desreferencia `user`; sem a guarda, `TS18048` — validado nesta fase). Guarda honesta e exigida pelo tipo, mesmo que não dispare no `GET`.
- **A resposta é o próprio registro do chamador** (`{ handle, displayName }`) — nunca de terceiro, porque a posse barra qualquer `:handle` que não seja o seu.

### `PATCH /users/:handle` — a rota VULNERÁVEL (editar o perfil)

Edita o `displayName` do registro `:handle`. Autentica (Bearer ruim → `401`), busca o alvo, escreve o campo, e devolve o **delta** (o handle do path + o valor gravado). **NÃO** tem a guarda de posse que o `GET` tem. Handler **≤ ~30 linhas** (tem ~8).

```ts
app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  // VULNERABLE: the GET handler on this same path guards the record with an ownership
  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
  // the path -- guarding the read left the write on the same resource wide open.
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);                               // unknown target user
  user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
  res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
});
```

- **Source:** o `:handle` do alvo + o token (a identidade — que o `PATCH` autentica mas não usa pra autorizar a operação). **Sink conceitual:** a escrita **sem** comparar `:handle` ao chamador, quando o método-irmão (`GET`) compara. O bug é **o que não está lá, ao lado do que está** (no `GET`, uma rota acima) — não greppa; audita-se perguntando **"a autorização cobre todos os métodos deste path?"**.
- **A resposta NÃO é leitura de objeto alheio.** O corpo é o **delta**: `handle` é eco do input do chamador, e `displayName` é o valor que ele **acabou de gravar** (`req.body?.displayName`). Não é o registro privado da `alice` sendo lido de volta — é o que o atacante escreveu. **Cravar no DIFF e no WALKTHROUGH:** o `PATCH` **escreve e ecoa o próprio input**, não devolve dado de terceiro — o que mantém o átomo no eixo da **operação**, não no do objeto. (O walkthrough sempre envia corpo com `displayName`, então o valor ecoado é o do atacante.)
- **`USERS.get(req.params.handle)` → `User | undefined`:** a guarda `!user` é **exigida pelo compilador** (o `user.displayName = ...` desreferencia). **Validado nesta fase:** sem a guarda, `tsc` dá `TS18048: 'user' is possibly 'undefined'`. O `Map` (em vez de `Record`) fecha a prototype pollution que o `:handle` abriria.

> **Bind do servidor** (rodapé idêntico a 01–04): `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);`

> **DOIS HANDLERS INDEPENDENTES, não um middleware por método.** O `GET` tem a guarda de posse na cadeia; o `PATCH` simplesmente não tem. A assimetria é visível **linha a linha** — um handler lista a proteção, o outro não. **NÃO** usar um middleware único que discrimina por método por dentro (`if (req.method === "GET") ...`): seria um bug artificial que desloca a atenção. Os dois handlers compartilham tudo menos a guarda — mesmo path, mesmo recurso, mesma forma de resposta (`{ handle, displayName }`) — pra que o contraste conceitual entre eles seja **só** o check de posse.

---

## Fix — estender ao `PATCH` a MESMA guarda de posse que o `GET` já tem

O gêmeo `fixed/` difere **APENAS por uma guarda de posse acrescentada ao `PATCH`**, logo depois da autenticação, **byte-idêntica à linha que o `GET` já tem**. **Nenhuma outra linha muda** — `POST /login`, `GET /users/:handle`, helpers, imports, `USERS`, o rodapé, o `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` são **idênticos**.

```ts
app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
  // FIXED: the same ownership check the GET handler already has, now on PATCH too --
  // authorization covers every method of the path, not just the one the dev remembered.
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);                               // unknown target user
  user.displayName = req.body?.displayName ?? user.displayName;        // state change -- not a read
  res.json({ handle: req.params.handle, displayName: user.displayName }); // the state delta, echoed input
});
```

Diff mínimo (o eixo único):

```diff
   if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);  // AUTHENTICATION only
-  // VULNERABLE: the GET handler on this same path guards the record with an ownership
-  // check; this PATCH handler has none. Authorization belongs to (method + path), not to
-  // the path -- guarding the read left the write on the same resource wide open.
+  // FIXED: the same ownership check the GET handler already has, now on PATCH too --
+  // authorization covers every method of the path, not just the one the dev remembered.
+  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);                               // unknown target user
```

**A leitura correta do fix (cravar no DIFF):** a autorização **não pertence ao recurso "em geral"**, nem a uma tela — ela pertence a **cada par (método + path)**. O `GET` já perguntava *este registro é seu?*; o fix é **estender ao `PATCH` a mesma pergunta**. A guarda acrescentada é **byte-idêntica** à linha que já existe no `GET` (`if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only`) — não um check novo, mas o check que já estava no arquivo, aplicado ao método que o esquecera.

- **A guarda vem ANTES da busca do alvo** (igual ao `GET`, igual à disciplina do 03): um não-dono recebe `403` sem que o alvo seja consultado — o gate **não vaza** nada sobre quais handles existem.
- **A guarda é uma comparação de strings, não um lookup** (`req.params.handle !== caller`). Diferente do fix do 04 (`USERS.get(caller)?.is_admin`, que busca o papel do chamador no `Map` e por isso exige `?.`), aqui **não há `.get(caller)`** — só a comparação do handle do path com o handle do chamador, ambos `string` (o `caller` já narrowado de `string | null` pra `string` pela guarda do `401`). Nenhum `?.` envolvido na guarda; o `| undefined` que força a guarda `!user` vem do `USERS.get(req.params.handle)` abaixo dela, igual nos dois gêmeos.

**CRAVAR no DIFF — o fix NÃO é o de 01/02, nem o de 03, nem o de 04, e isso é a lição.** Quatro formas porque quatro perguntas:

- **01/02** — *é seu?* → predicado de posse **sobre o objeto**, acrescentado à guarda **depois** da busca (`order.owner !== caller`).
- **03** — *é desta loja?* → **mover a busca** pro escopo do pai (`ordersOf(storeId).find(...)`).
- **04** — *você pode invocar esta função?* → guarda de **papel** do chamador, antes de tudo (`USERS.get(caller)?.is_admin`).
- **05** — *todos os métodos deste path estão cobertos?* → **a mesma guarda de posse que o irmão-método (`GET`) já tinha, agora no método que a esquecera** (`req.params.handle !== caller`).

A lição transferível não é "o fix é sempre X"; é **autorize cada par (método + path), no eixo que a operação exige**.

---

## Status code: `403` (não `404`) — o critério da série, aplicado a uma posse checada antes da busca

O `GET` de registro alheio e o `PATCH` de registro alheio (no `fixed/`) retornam **`403`** — **não `404`**. Isso **não** é exceção à série nem critério novo: é o **mesmo critério** de 01–04 (*a existência do alvo é sensível?*), aplicado a um check de natureza específica. A spec crava a decisão com argumento próprio; **não copiar por inércia nem o `404` do pedido nem o `403` do 04**.

**O critério é um só, e vem do 01** (DIFF do `bola-sequential-id`): *"`404` when existence itself leaks; `403` when admitting existence is fine"*, ancorado no RFC 9110 §15.5.4. Os átomos de pedido (01/03) dão `404` porque a existência do pedido é sensível (id-space enumerável → `403`-vs-`404` seria enumeration oracle); o 02 herda o `404` sem id-space pra varrer; o 03 já dá `403` pra loja (slug público, existência não-sensível); o 04 dá `403` pra função conhecida.

**Aqui o critério dá `403`, e a razão é mais forte que no 04: o check de posse roda ANTES da busca e é uma comparação de identidade.** A guarda é `req.params.handle !== caller`:

- **Ela não consulta o store** — compara o handle do path ao handle do chamador. Um refusal revela **só** "este handle não é o seu", que é um fato que o chamador **já sabe** (ele sabe o próprio handle; ele mesmo digitou `alice`). **Nada sobre existência é consultado ou revelado.**
- **O `403` dispara idêntico pra handle alheio-que-existe E pra handle inexistente.** `GET /users/alice` (existe) e `GET /users/zzz` (não existe) caem no mesmo `handle !== caller` → **mesmo `403`**. Logo **não há username enumeration**: o atacante não distingue "alice existe" de "zzz não existe" — a existência fica escondida como **efeito colateral** do predicado de identidade, enquanto o status permanece **honesto**. Sem id-space, sem busca antes do gate, **não há oráculo** — e por isso a pressão que forçou o `404` do pedido no 01/03 simplesmente não existe aqui.

**Por que `403` é a resposta honesta (ancorar no RFC 9110 — texto bruto conferido nesta fase):**

- **RFC 9110 §15.5.4 (403 Forbidden):** *"The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it."* E, decisivo: *"If authentication credentials were provided in the request, the server considers them insufficient to grant access."* É exatamente o caso — o token é válido (credencial presente), mas não autoriza **este** par (método + path) sobre **este** recurso. `403` diz a verdade.
- **O `404` do §15.5.4 é uma OPÇÃO (`MAY`) pra esconder existência** — *"An origin server that wishes to 'hide' the current existence of a forbidden target resource MAY instead respond with a status code of 404 (Not Found)."* Serve quando a existência **é sensível**. Aqui a guarda já não revela existência nenhuma (predicado de identidade, antes da busca), então não há o que esconder, e o `403` honesto é o certo.
- **O `401` (§15.5.2) é a camada de baixo**, intocada: token ausente/ruim → `401` COM `WWW-Authenticate: Bearer` (*"The server generating a 401 response MUST send a WWW-Authenticate header field … containing at least one challenge"* — §15.5.2). Os `403` **não** carregam esse header (o chamador já está autenticado; não há o que pedir). Confirmado lendo os `app.ts` publicados: todo handler faz `res.set("WWW-Authenticate", "Bearer").sendStatus(401)`.

**Consistência entre os dois endpoints:** o `GET` alheio e o `PATCH` alheio (no `fixed/`) dão o **mesmo `403`**, porque é a **mesma guarda** (byte-idêntica) nos dois métodos. É o ponto do fix: estender ao `PATCH` a resposta que o `GET` já dava. **Não** divergir (um `403`, outro `404`) — isso reabriria, no eixo do status, exatamente o buraco de cobertura que o átomo existe pra fechar.

**O `404` do alvo inexistente (só no `vulnerable/`, no `PATCH`) é ortogonal.** No `vulnerable/`, sem guarda de posse, `PATCH /users/nobody` chega ao lookup → `404` (alvo não existe). No `fixed/`, o mesmo request bate `403` **antes** do lookup (o gate roda primeiro), então nem alcança o `404`. Registrar no DIFF em uma frase: o `404` de alvo inexistente existe no `vulnerable/` como higiene; no `fixed/` o gate o precede.

**Regra de bolso — um critério só, o da série: a existência do alvo é sensível (ou revelada)?** Sim → **`404`** (o pedido de 01/03, id-space enumerável). Não → **`403`** honesto (a loja do 03; a função do 04; e aqui, a posse checada por comparação de identidade **antes** da busca, que não revela existência nenhuma). O RFC 9110 oferece os dois (§15.5.4); quem escolhe é a natureza do check, não o átomo.

---

## Padrão de prova — Trigger

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **usar um método legítimo** (`PATCH`) num path legítimo, com um token legítimo, contra um recurso que não é seu — porque aquele método não tem o check que o método-irmão tem. Trocar nada no token; só mudar o **verbo HTTP** e o alvo. Por ser **Trigger**, o **passo de contraste é obrigatório** (CLAUDE.md §5) — ver Walkthrough, Step 2.

---

## Estado mutável — o endpoint atacado escreve (como no 04)

O endpoint atacado (`PATCH`) **muda estado** (escreve `displayName`). Tratamento explícito:

- **As escritas são reais, mas nenhuma resposta do walkthrough depende do acúmulo.** **Verificado contra o comportamento do código nesta fase** (não presumido): a resposta do `PATCH` ecoa o `displayName` **enviado** (`req.body?.displayName`), então rodar o mesmo request duas vezes dá status e corpo **idênticos** (observado: `PATCH /users/alice` → `200 {"handle":"alice","displayName":"PWNED"}` nas duas vezes). O único passo que lê um registro (`GET /users/clancy`) lê o **próprio** de `clancy`, que o walkthrough **nunca escreve** (o contraste usa `GET /users/clancy`, não `PATCH /users/clancy`), então sempre devolve o seed (`"Clancy Park"`). Os passos podem ser repetidos em qualquer ordem.
- **SEM endpoint de "desfazer".** Nenhum passo precisa reverter nada; um endpoint de restore seria superfície a mais sem lição.
- **Gêmeos independentes.** Editar na 8205 não muda nada na 8305; o seed de cada build é próprio.
- **Requisito de README (EN+PT), a única casa da frase do restart:** uma frase diz que o estado vive em memória e que `./atom down bfla-method-based && ./atom up bfla-method-based` devolve o seed original (nomes de exibição seedados; tokens zerados → logar de novo). **Não** repetir no WALKTHROUGH nem no DIFF.

---

## Walkthrough — estrutura e requests

Trabalhado **100% no Burp** (Repeater), `curl` como equivalente — **API-only, SEM trilha browser** (CLAUDE.md §3.3). **Sem Intruder:** a tese não é escala/enumeração; é a cobertura de método ausente, provada em requests únicos. Cada request é um bloco colável: request-line (**com o verbo explícito** — `GET`/`PATCH`) + `Authorization: Bearer <token>` + corpo JSON quando houver. Tokens são **placeholders** (`<clancy-token>`) — variam por login; handles são **literais** (seed fixo).

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de perfil serve `GET /users/:handle` e `PATCH /users/:handle` no mesmo path; o `GET` confere que o registro é seu, o `PATCH` não" — não um personagem. Definir todo termo não-óbvio na estreia: "BFLA (Broken Function Level Authorization)", "function-level authorization", "method-based BFLA", "ownership check", "opaque token".

**REQUISITO DE REDAÇÃO — clareza é requisito DURO (o mantenedor enfatizou).** Cada bloco de request é precedido de uma linha de rótulo que diz explicitamente **MÉTODO**, **ALVO** e **o que aquela linha ISOLA**. Formato sugerido:

> **EN:** `Method: PATCH · Target: alice (not yours) · Isolates: the write has no ownership check`
>
> **PT:** `Método: PATCH · Alvo: alice (não é seu) · Isola: a escrita não tem check de posse`

A prosa **NOMEIA as duas leituras erradas** — "isto é BOLA" e "isto é o átomo 04 de novo" — e as **desarma uma a uma**, em vez de só descrever o que acontece. Tratar o leitor como quem vai confundir, e prevenir a confusão.

### 1. Context
- API de perfil de conta; auth por Bearer token opaco; `GET /users/:handle` lê o perfil, `PATCH /users/:handle` edita o `displayName`. Isto é **BFLA** — **API5:2023** do OWASP API Security Top 10. **Contraste de abertura:** os átomos de API1 perguntavam sobre o objeto (*de quem é?*); o 04 perguntava sobre a função (*você pode invocar?*), com a função inteira sem check; aqui a pergunta é sobre o **método**: *a autorização cobre todos os métodos deste path?* — e o `PATCH` não é coberto. A descoberta não é passo: você já edita o seu perfil pelo `PATCH`, então aponta o mesmo `PATCH` pro handle de outro. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar os **dois handlers lado a lado**, mesmo path: o `GET` tem `if (req.params.handle !== caller) return res.sendStatus(403);`; o `PATCH` **não tem essa linha**. A assimetria é visível. Pergunta de auditoria — **diferente** da de BOLA e da do 04: não "cadê o check de dono?" (BOLA), nem "cadê o check de papel?" (04), mas **"a autorização cobre todos os métodos deste path?"** → cobre o `GET`, não cobre o `PATCH`.
- Creditar o eixo: no 03 o check existia e apontava pro objeto errado; aqui o check existe e **está certo** — só não cobre todos os métodos. Notar que a classe **não greppa**: não há string perigosa, há um check presente num método e ausente em outro.

### 3. How auth works in this lab (subseção curta)
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo), cripto-forte (`randomBytes`), mapeado ao usuário. Dois pontos: (i) a **autenticação É imposta** (token ruim → `401`); (ii) se a **posse** do registro é checada é outra pergunta — e o `GET` checa, o `PATCH` do `vulnerable/` não. **Disciplina cravada:** o ataque **não toca** o token (não decodifica, não adultera) — fica válido e do `clancy` o tempo todo. A posse é `req.params.handle === caller`.

### 4. Baseline — logar e ver a posse funcionando no `GET`
- `POST /login` com `{"user":"clancy"}` → `{"token":"<clancy-token>"}`. Bloco colável (request-line + `Content-Type: application/json` + corpo). *(Rótulo: método `POST`, logando como `clancy`.)*
- `GET /users/clancy` com `<clancy-token>` → `200`, `{"handle":"clancy","displayName":"Clancy Park"}`. *(Rótulo: `GET` · alvo `clancy` (seu) · isola: a leitura do próprio registro passa.)* A feature funciona, e a authz de posse está lá.
- `GET /users/alice` com `<clancy-token>` → **`403`**. *(Rótulo: `GET` · alvo `alice` (não é seu) · isola: a leitura alheia é recusada.)* **O servidor SABE fazer o check de posse** e recusa a leitura do registro da `alice`. Guardar essa resposta — ela é o que afasta tanto o 04 (que não tinha check nenhum) quanto a leitura "isto é BOLA" (o check de posse está correto).

### 5. Step 1 — Write another user's record through the unguarded method (BFLA confirmado)
- `clancy` edita o perfil da **alice** pelo `PATCH`:
  ```
  PATCH /users/alice HTTP/1.1
  Host: 127.0.0.1:8205
  Authorization: Bearer <clancy-token>
  Content-Type: application/json

  {"displayName": "pwned by clancy"}
  ```
  *(Rótulo: `PATCH` · alvo `alice` (não é seu) · isola: a escrita não tem o check que a leitura tem.)* Resposta — **`200`** com `{"handle":"alice","displayName":"pwned by clancy"}`.
- **A MESMA URL que recusou a sua leitura (`GET /users/alice` → `403`) aceitou a sua escrita (`PATCH /users/alice` → `200`).** Você escreveu num registro que **não é seu**, com o seu próprio token válido, só **trocando o verbo HTTP**. O que explica o sucesso é que **aquele método estava desprotegido** — não um objeto seu, não uma identidade forjada. Isso é **BFLA**: a autorização se aplica a (método + path), e guardar o `GET` nunca guardou o `PATCH`.
- **A resposta não é leitura de objeto alheio.** O corpo diz só o que você **gravou** (`displayName` é o que você mandou; `handle` é o que você pôs no path). Nada de registro privado da `alice` voltando. Guardar essa observação: é o que separa esta classe de BOLA.

### 6. Step 2 — What the vuln is NOT (passo de contraste OBRIGATÓRIO — três requests, a clareza é requisito DURO)
Todos com o `<clancy-token>`. A prosa nomeia e desarma as duas leituras erradas.

1. **`GET /users/alice` → `403`.** *(Rótulo: `GET` · alvo `alice` (não é seu) · isola: o check de posse existe e morde.)* **Desarma "isto é o átomo 04 de novo":** há autorização funcionando neste path — diferente do 04, onde a função não tinha check nenhum. O servidor sabe recusar o acesso alheio.
2. **`PATCH /users/alice` → `200`.** *(Rótulo: `PATCH` · alvo `alice` (não é seu) · isola: mesmo path, mesmo recurso alheio, método diferente — e passa.)* A proteção do `GET` **não está aqui**. Entre (1) e (2) só o **método** mudou, e o veredito virou.
3. **`GET /users/clancy` → `200`.** *(Rótulo: `GET` · alvo `clancy` (seu) · isola: a leitura do próprio registro passa.)* **Desarma "isto é BOLA":** o `403` do passo (1) **não** era "`GET` é sempre barrado" — era o **check de posse funcionando**. O `GET` autoriza quando deve (seu registro → `200`) e recusa quando deve (registro alheio → `403`). A object-level authorization **está presente e correta**; o problema é o `PATCH` não ter check **nenhum**.

**Conclusão a escrever explicitamente:** a autorização de objeto está **presente, correta e aplicada — no `GET`** (passos 1 e 3 provam: recusa o alheio, autoriza o próprio). O `PATCH` sobre o **mesmo** objeto, pelo **mesmo** usuário, **nunca passa por ela** (passo 2). A falha **NÃO** é o check de posse estar errado (não é BOLA); **NÃO** é a função não ter check nenhum (não é o 04). É o check **não cobrir todos os métodos do path**. A pergunta certa é *"a autorização cobre todos os métodos deste path?"*, não *"de quem é o objeto?"*.

> **(Opcional, curto) Sem token → `401`.** `PATCH /users/alice` **sem** `Authorization` → `401` (com `WWW-Authenticate: Bearer`). Prova, de passagem, que o eixo não é autenticação quebrada: sem identidade, nada roda. Uma linha; não alongar — o núcleo do contraste são os três requests acima.

> **Frase-âncora do WALKTHROUGH (uma casa só):** *One URL answered the read safely and the write wide open — because authorization attaches to the pair (method, path), and guarding the GET never guards the PATCH.* / *Uma mesma URL respondeu à leitura com segurança e à escrita escancarada — porque a autorização se prende ao par (método, path), e guardar o GET nunca guarda o PATCH.* Mora no fim do Step 2. **Não** repetir no DIFF nem no README. *(Manter distância da âncora do 03 — "which question it answers": a do 03 é sobre um check apontado pro objeto errado; esta é sobre a cobertura por método. Não colar as frases.)*

### 7. Why the fix works (porta 8305)
Apontar o Burp pro `fixed/` em `127.0.0.1:8305` e logar lá (cada build tem o próprio mapa de tokens):
- `PATCH /users/alice` (com o token do `clancy` da 8305) → **`403`** (body `Forbidden`). *(Rótulo: `PATCH` · alvo `alice` (não é seu) · isola: a mesma guarda do `GET`, agora no `PATCH`.)* O `PATCH` agora checa a posse **antes** da busca do alvo — a alice nunca é editada.
- **A feature ainda funciona pra o dono:** `PATCH /users/clancy` (seu próprio registro) com o seu token → **`200`**, `{"handle":"clancy","displayName":"<o que você enviou>"}`. O fix não quebrou a edição de perfil; só restringiu a quem é dono. **Nenhum admin é necessário** — o caminho positivo é você editando o seu próprio registro.
- **O `GET` não mudou:** `GET /users/clancy` → `200`, `GET /users/alice` → `403` — iguais nos dois gêmeos. Sem/ruim token ainda → `401`.
- **`403`, não `404`:** o não-dono recebe `403` (não um `404` que fingiria que o registro não existe) — a guarda compara identidade **antes** da busca, não revela existência nenhuma, e `403` diz a verdade ("você está autenticado e não é dono deste registro"). **Forward pro DIFF** pro argumento completo (RFC 9110 §15.5.4; o critério da série; por que o oracle que força o `404` do pedido no 01/03 não se aplica a uma posse checada por comparação de identidade antes da busca).

**O walkthrough TERMINA aqui.** Sem Intruder, sem automação, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5 — termina onde a falha foi mostrada e o fix explicado).

### Impacto (uma frase honesta, no fim do walkthrough)
Escalação **horizontal**: escrever no registro de um **par** (mesmo nível) através de um método desprotegido. Não é vertical (não há ganho de papel — por isso **sem admin** no seed), não é RCE. O achado é um usuário comum alterando o perfil de outro usuário comum pelo `PATCH`, enquanto o `GET` do mesmo path recusa a leitura alheia. Contraste honesto com o 04 (mesma categoria API5, mas aquele era vertical — ganhar papel admin).

---

## Frases-âncora (uma casa só cada — CLAUDE.md §11 / template)

Nenhuma frase memorável aparece em **dois** documentos. Atribuição fixa:

- **WALKTHROUGH (uma casa):** *"One URL answered the read safely and the write wide open — because authorization attaches to the pair (method, path), and guarding the GET never guards the PATCH."* / *"Uma mesma URL respondeu à leitura com segurança e à escrita escancarada — porque a autorização se prende ao par (método, path), e guardar o GET nunca guarda o PATCH."* Mora no fim do Step 2.
- **DIFF (uma casa):** *"The fix invents nothing: it carries the GET handler's ownership guard onto the PATCH handler, so the question the read already asked is finally asked by the write."* / *"O fix não inventa nada: ele leva a guarda de posse do handler GET para o handler PATCH, pra que a pergunta que a leitura já fazia seja finalmente feita pela escrita."* Mora na seção do fix.
- **Não reusar** as âncoras de 01 ("…it leaks the base/collection…"), 02 ("…a wall of 404s is 'didn't find'…"; "…the correction changed nothing"), 03 ("Authorization present is not authorization sufficient — what matters is which question it answers."; "No information was missing — the question was.") nem 04 ("The endpoint never cared whose account the target was…"; "The fix adds no check about the target at all — it asks only whether the caller may run the function."). **Atenção especial à do 03** ("which question it answers") e à do 04 (sobre o alvo): as deste átomo são sobre a **cobertura por método** (o par método+path), um corte distinto. Não colar as frases.

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` + `Dockerfile` em **cada** gêmeo, **self-contained, sem módulo compartilhado**; lockfile **commitado** por gêmeo. `app.ts` **difere** só pela guarda de posse acrescentada no `PATCH /users/:handle` (+ o comentário); todo o resto é idêntico entre as versões.

**Herança de toolchain (CLAUDE.md §3.6) — lida dos arquivos publicados de 01–04 nesta fase (os `package.json`, `Dockerfile` e `tsconfig.json` batem por md5 nos quatro átomos, incluindo o irmão de categoria `bfla-admin-function`):**

`tsconfig.json` (copiar — idêntico a 01–04):

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

- **A guarda `!user` é FORÇADA pelo compilador** — em **ambos** os handlers (o `GET` desreferencia `user.displayName` no `res.json`; o `PATCH` em `user.displayName = ...`). Sem ela, `tsc` dá **`TS18048: 'user' is possibly 'undefined'`** (observado nesta fase nos dois métodos — ver "Validação de typecheck e runtime"). O `| undefined` vem da **assinatura do `Map.get`** (independente do `noUncheckedIndexedAccess`, que continua ligado por herança). **A guarda de posse do fix NÃO envolve `.get(caller)`** (é comparação de string), então **não há `?.`** nela — diferente do fix do 04. Os docs **podem** afirmar que o compilador força a guarda `!user` nos dois métodos.

`Dockerfile` (idêntico a 01–04 — copiar; base `node:24.21.0-slim`, patch exato, nunca `latest` nem a tag móvel `node:24-slim`):

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

`docker-compose.yml` (bind **só** em `127.0.0.1`, portas **8205/8305**):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8205:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8305:3000"
```

- `package.json` de cada gêmeo: `"name": "bfla-method-based"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Entrypoint `tsx`. **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **Roda como não-root, sem `chown`** — mesma justificativa de 01–04 (validada lá). Reconfirmar no smoke test da Fase 2: build OK, container sobe como `node`, `tsx` sem erro de permissão, endpoints respondendo, imagem só com `express` + `tsx`.

---

## Dependências extras

**Nenhuma dependência nova.** Versões **exatas herdadas** de 01–04 — lidas dos `package.json` publicados (idênticos nos quatro átomos) e conferidas nos `package-lock.json` commitados. **NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

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

- Base `node:24.21.0-slim` (lida dos `Dockerfile`, md5 idêntico nos quatro átomos). Nenhuma divergência.
- Classificação por **runtime**: `tsx` em `dependencies` (entrypoint que executa); `typescript`/`@types/*` em `devDependencies` (build/checagem). `npm audit --omit=dev` cobre exatamente o que a imagem `npm ci --omit=dev` instala e roda (`express` + `tsx`). **Escopo da imagem = escopo do audit = o que roda.**
- `crypto` é **nativo** (`node:crypto`, para `randomBytes` do token) — não é dependência npm. **Nenhuma lib de autorização/RBAC, nenhum middleware de auth** — a guarda de posse é um `if` de uma linha. Isso respeita "só inclua a lib se serve à falha ou ao fix" (§3.6).
- **Pin exato travado no `package-lock.json`** (commitado por gêmeo). Updates **manuais** (CLAUDE.md §8.7). Se algo em 01–04 parecer desatualizado, **seguir com o que está lá** — bump é decisão de corte de release, coordenada na série inteira (§3.6), não neste átomo.

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). **BFLA não tem página própria no PortSwigger** — a Web Security Academy trata a classe sob **Access control**, e o method-based BFLA especificamente sob "Broken access control resulting from platform misconfiguration" (um método restrito, outro tolerado no mesmo URL). É a **mesma página do átomo 04** (a casa conceitual de BFLA), e **NÃO** a página de IDOR usada por 01–03.

- **Primer (verificado por fetch NESTA fase — HTTP 200 direto, sem redirect; H1 "Access control vulnerabilities and privilege escalation"; primeira seção "What is access control?"; cobre o ataque por método HTTP no corpo, seção "Broken access control resulting from platform misconfiguration"):**
  `https://portswigger.net/web-security/access-control`
  Texto do link: **"Access control vulnerabilities and privilege escalation"** — a forma como a PortSwigger apresenta a página (H1), preservada em **inglês** também no README PT (CLAUDE.md §7).

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

**OWASP: sem link inline.** Os docs citam `API5:2023` em texto simples; o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (conferido: os READMEs de 01–04 seguem isso). A linha da categoria API5 **já existe** na tabela de Cobertura do ROADMAP (conferido nesta fase), apontando `bfla-admin-function` e `bfla-method-based`.

**Fase 2:** re-confirmar a URL do primer por fetch na geração (a PortSwigger às vezes reorganiza caminhos).

---

## Política de cross-ref (CLAUDE.md §5)

Publicação verificada **lendo `atoms/api/ROADMAP.md` e a árvore de `atoms/` NESTA fase**, não de memória: na série API, **01, 02, 03 e 04 estão publicados** (`[x]`, pastas completas); **06 em diante não** (05 é este; 06 `bopla-excessive-exposure` em diante é Fase 2, **não publicada**).

- **`bfla-admin-function` (04) — o irmão de categoria, central no contraste.** Mesma categoria API5. Contraste: 04 = eixo da **função** (uma função admin-only **sem check nenhum**, escalação vertical); 05 = eixo do **método** (um método de um path **sem o check que o método-irmão tem**, escalação horizontal). Creditar o `Map`/prototype-pollution e o argumento `403`/RFC 9110 do 04 (referenciar, não recontar o argumento inteiro).
- **`bola-sequential-id` (01) e `bola-uuid-leaked` (02) — a origem do check de posse** que este átomo reusa como conteúdo (`order.owner === caller` → `handle === caller`). Creditar: a posse é o *conteúdo* do check que varia por método, não a lição.
- **`bola-nested-resource` (03) — o precedente da armadilha "check que existe e passa"** (lá no eixo do objeto: pai vs filho; aqui no eixo do método: `GET` vs `PATCH`) e da disciplina do **gate antes da busca** + `403` honesto por existência não-sensível. Creditar por essa simetria de método.
- **PROIBIDO citar qualquer átomo de API NÃO publicado** (06 em diante: `bopla-excessive-exposure`, `bopla-mass-assignment`, `auth-*`, etc.) — por nome, número ou descrição. **Em particular, NÃO antecipar** mass assignment / BOPLA como "a próxima volta" nem sugerir que escrever um campo de privilégio seria o próximo passo. Forward reference (CLAUDE.md §5). Verificado: só 01–04 publicados.
- **Átomos web de A01** (`idor-numeric-id`, `bola-rest`, `idor-uuid-guessable`) — todos horizontais (IDOR/BOLA, eixo do objeto). **Não há gêmeo web de method-based BFLA** pra creditar; esta spec **não afirma nada** sobre eles além do que se puder conferir lendo o átomo na Fase 2.
- Termos técnicos em inglês no PT (BFLA, BOLA, function-level authorization, object-level authorization, ownership check, method, path, privilege escalation, token, Bearer, enumeration oracle, prototype pollution, Trigger, payload).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API5 — Broken Function Level Authorization** | Segundo átomo da categoria. Um método de um path sem a autorização que os outros métodos têm — controle de acesso no nível da função/operação, não do objeto. |
| Nome / classe (H1) | **Broken Function Level Authorization (BFLA)** — idêntico EN/PT | Título nomeia a classe; o slug (`bfla-method-based`) qualifica a variante. Mesmo H1 do 04 (mesma classe). |
| Pasta | **`API5-broken-function-level-authz/` (já existe)** | Segunda pasta da categoria; o 04 criou a `API5-*`. |
| Papel na série | **Fecha a Fase 1; move o 04 pra perto de produção** | 04 = função sem check nenhum; 05 = check presente num método, ausente em outro do mesmo path. Eixo da função → eixo do método. |
| A tese | **Autorização se aplica a (método + path), não a path** | O dev guardou a leitura, achou que guardou o recurso, deixou a escrita aberta. |
| A superfície atacada | **`PATCH /users/:handle`** (vuln); `GET /users/:handle` correto nos 2 | O `GET` é a prova viva de que a authz de posse existe e funciona; o `PATCH` é o método descoberto. |
| Campo editado | **`displayName` (comum)**, nunca um flag de privilégio | Escrever papel/`is_admin` invadiria o 04 e o futuro `bopla-mass-assignment` e embaralharia o eixo. |
| Forma do código | **Dois handlers independentes** — `GET` com a guarda, `PATCH` sem | Assimetria visível linha a linha. NÃO um middleware que discrimina por método por dentro (bug artificial). |
| Seed | **`clancy` (atacante) e `alice` (vítima), cada um dono do próprio registro; SEM admin** | Posse = `handle === caller`. Sem admin: o caminho positivo do fix é `clancy` editando o próprio registro — distingue do 04 (que precisava de admin). |
| Store | **`Map<string, User>`, `User = { displayName }`** | O `PATCH` escreve através de lookup por chave-string do path → `Map` (não `Record`) fecha prototype pollution (`__proto__`/`constructor`), e tipa `user` como `User \| undefined` (guarda `!user` exigida). |
| Token | **Opaco, `crypto.randomBytes`; NÃO JWT** — idêntico a 01–04 | Cripto-forte pra não ser 2ª vuln. O ataque não toca o token. |
| Fix (eixo único) | **`if (req.params.handle !== caller) return 403` no `PATCH`, byte-idêntico à linha do `GET`, antes da busca** | Estender ao `PATCH` a MESMA guarda de posse que o `GET` já tem. Comparação de identidade (sem `.get(caller)`, sem `?.`). |
| Status code | **`403`** (não `404`), igual no `GET` alheio e no `PATCH` alheio (fixed) | Guarda compara identidade **antes** da busca → não revela existência (dispara igual pra alheio-existente e inexistente → sem username enumeration). RFC 9110 §15.5.4: credencial presente, insuficiente → `403` honesto. O argumento de `404` do pedido (01/03) não transfere. |
| Alvo inexistente | **`404` só no `vulnerable/` (PATCH, pós-lookup); no `fixed/` o `403` precede** | Higiene; no fixed o gate roda antes do lookup. |
| Resposta de sucesso | **`{ "handle": "<alvo>", "displayName": "<enviado>" }`** | O **delta** (eco do input + o valor gravado), não registro privado de terceiro. Mantém no eixo da operação. |
| Corpo dos erros — `sendStatus` | **`res.sendStatus(...)` (401/403/404); sucesso via `res.json(...)`** | Igual a 01–04. |
| Estado | **Mutável; escritas reais, nenhuma resposta depende do acúmulo; sem undo** | Verificado contra o código: `PATCH` ecoa o input → re-run idêntico; o único `GET` lido é o próprio de `clancy`, nunca escrito no walkthrough. Gêmeos independentes. |
| Padrão de prova | **Trigger** (não Payload) | Não há sink; o exploit é trocar o verbo HTTP num path legítimo. → passo de contraste obrigatório. |
| Passo de contraste | **(1) GET alice → 403; (2) PATCH alice → 200; (3) GET clancy → 200** | (1)+(3) afastam BOLA (o check de posse existe e está correto) e o 04 (há check neste path); (2) é o bug. Clareza é requisito duro: cada bloco rotula método/alvo/o-que-isola; a prosa nomeia e desarma as duas leituras erradas. |
| Trilha | **100% Burp (Repeater) / curl; SEM Intruder; SEM browser** | API-only (CLAUDE.md §3.3). A tese não é escala/enumeração. |
| Impacto | **Escalação HORIZONTAL** — escrever no registro de um par via método desprotegido | Honesto: não é vertical (sem ganho de papel — por isso sem admin), não é RCE. Contraste com o 04 (vertical). |
| Theory primer | **PortSwigger Access control** (mesma do 04), seção method-based | BFLA não tem página própria; Access control é a casa. **Diferente** da página de IDOR de 01–03. URL verificada por fetch nesta fase (200, sem redirect). |
| Cross-ref | **04 central (eixo método vs função); 01–03 (posse e "check presente"); nenhum átomo de API 06+** | 01–04 publicados. 06+ não-publicados → proibido, inclusive antecipar BOPLA/mass assignment. |

---

## Decisões que podem gerar dúvida durante implementação

- **Membership no `POST /login` — `USERS.has(user)`.** Com `USERS` sendo `Map<string, User>`, é a mesma forma de 01–04 (Set e Map compartilham `.has`). `req.body?.user` é `any` → `Map.has(any)` aceita. **Validado nesta fase:** `tsc --noEmit` limpo (exit 0).
- **Guarda `!user` FORÇADA pelo compilador nos DOIS métodos — validado nesta fase.** `USERS.get(req.params.handle)` é `User | undefined`; `user.displayName` desreferencia (no `GET`, dentro do `res.json`; no `PATCH`, na atribuição). **Observado:** removendo a guarda, `tsc` dá **`TS18048`** em ambos os handlers.
- **A guarda de posse do fix NÃO usa `?.`.** É `req.params.handle !== caller` — `caller` já é `string` (narrowado da guarda do `401`), `req.params.handle` é `string`. Sem `.get(caller)`, sem `User | undefined`, sem `?.`. Diferente do fix do 04 (`USERS.get(caller)?.is_admin`). **Não** usar `!` nem `?.` aqui.
- **A guarda de posse vem ANTES da busca do alvo** (nos dois métodos, nos dois gêmeos para o `GET`; só no `fixed/` para o `PATCH`). É o que garante o `403` sem revelar existência.
- **Escrita do `PATCH`:** `user.displayName = req.body?.displayName ?? user.displayName`. `req.body?.displayName` é `any`; `any ?? string` → atribuível a `string`. **Validado:** typecheck limpo; runtime no-op gracioso se o corpo omitir `displayName`. O walkthrough sempre envia corpo, então o valor ecoado é o do atacante.
- **Corpo do `PATCH` precisa de `app.use(express.json())`** (o `POST /login` e o `PATCH` usam o body) — idêntico a 01–04, não remover.
- **Verbo HTTP.** `GET` (ler) e `PATCH` (editar o `displayName`) são os verbos naturais. **Não** transformar a escolha do verbo numa discussão de REST-design — o eixo é "a autorização cobre todos os métodos?", não "qual verbo é mais correto".
- **Tipos do Express 5 — retorno `Response` vs `void`.** Igual a 01–04: callbacks sem anotação de retorno, onde `return res.sendStatus(...)` passa. Se anotar o retorno, usar `res.sendStatus(...); return;`. Não anotar é o caminho da série.

---

## Validação de typecheck e runtime (feita NESTA fase de planning)

Montei um protótipo local com o **toolchain EXATO** herdado de 01–04 (express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5) e o `tsconfig.json` da série (byte a byte), reconstruí os **dois gêmeos** a partir dos samples desta spec **já com o `Map`**, e rodei `tsc --noEmit` + exercitei os endpoints com `tsx`. Observado (não raciocinado):

**Typecheck (`tsc` 7.0.2):**

| Teste | Resultado observado |
|---|---|
| `vulnerable/app.ts` (Map; `GET` com guarda de posse; `PATCH` sem) | **exit 0**, limpo |
| `fixed/app.ts` (Map; `PATCH` com a guarda de posse do `GET`) | **exit 0**, limpo |
| **[prova negativa]** remover `!user` do `PATCH` | **`TS18048: 'user' is possibly 'undefined'`** |
| **[prova negativa]** remover `!user` do `GET` (o `user.displayName` no `res.json` força) | **`TS18048: 'user' is possibly 'undefined'`** |
| `USERS.has(user)` / `USERS.get(handle)` com `Map` | compilam limpos (dois gêmeos exit 0) |

**Runtime — comportamento dos endpoints** (servidores `tsx` nas portas 8205/8305):

| Request (token do `clancy`) | vulnerable (8205) | fixed (8305) |
|---|---|---|
| `GET /users/clancy` (próprio) | `200` | `200` |
| `GET /users/alice` (alheio) | **`403`** | **`403`** |
| `PATCH /users/alice` (alheio) | **`200`** `{"handle":"alice","displayName":"PWNED"}` | **`403`** |
| `PATCH /users/alice` (re-run) | `200`, **corpo idêntico** | `403` |
| `PATCH /users/clancy` (próprio) | `200` | `200` (feature intacta) |
| `PATCH /users/alice` sem token | `401` | `401` |
| `PATCH /users/nobody` (inexistente) | `404` | `403` (gate antes do lookup) |
| `PATCH /users/__proto__` | `404` | `403` |
| `PATCH /users/constructor` | `404` | `403` |

**Runtime — prototype pollution, `Record` vs `Map`** (lógica do `PATCH` reproduzida, alvos `__proto__`/`constructor`):

| Store | `__proto__` | `({}).displayName` poluído? |
|---|---|---|
| **`Record`** (descartado) | **`200`** (guarda `!user` NÃO pega) | **SIM** — `({}).displayName === "<input>"` no processo (verificado em processo limpo) |
| **`Map`** (correção) | **`404`** | **não** — `({}).displayName === undefined` (verificado em processo limpo) |

- **Conclusões cravadas:** os dois gêmeos saem exit 0; a guarda `!user` é forçada nos **dois** métodos (`TS18048`); a guarda de posse do fix é uma comparação de string (sem `?.`); o `Map` fecha a prototype pollution **estruturalmente** (o `Record` poluiria de verdade — não teórico); nenhuma resposta do walkthrough depende de acúmulo (re-run do `PATCH` idêntico). A Fase 2 ainda roda `npm run typecheck` nos dois gêmeos como gate oficial (host/CI) e um smoke test completo.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia `usuário→token`, Bearer resolve de volta; `clancy`/`alice` recebem tokens distintos e cripto-fortes (`randomBytes`). Bloco de auth byte a byte o de 01–04; `USERS` é `Map<string, User>`; membership segue `USERS.has(user)`.
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido → **`401`** com `WWW-Authenticate: Bearer`, nas duas versões, nos dois métodos.
3. **`GET` correto nos DOIS gêmeos:** `GET /users/clancy` (próprio) → **`200`** `{"handle":"clancy","displayName":"Clancy Park"}`; `GET /users/alice` (alheio) → **`403`**.
4. **Vulnerable — BFLA:** `PATCH /users/alice` com o token do **`clancy`** → **`200`**, `{"handle":"alice","displayName":"<enviado>"}`. A escrita é real mas o corpo ecoa o input (não dado alheio).
5. **Vulnerable — indiferença ao método-irmão:** a MESMA URL que deu `403` no `GET` (`/users/alice`) dá `200` no `PATCH`. É o núcleo do contraste.
6. **Vulnerable — alvo inexistente:** `PATCH /users/nobody` com token válido → **`404`** (pós-lookup, sem guarda de posse).
7. **Vulnerable — prototype pollution fechada pelo `Map`:** `PATCH /users/__proto__` e `PATCH /users/constructor` → **`404`**, e **nenhuma** propriedade acrescentada a `Object.prototype` (`({}).displayName` segue `undefined`). **Se der `200` ou poluir, o `Map` não foi aplicado — PARE.**
8. **Fixed — o não-dono é recusado:** `PATCH /users/alice` com o token do **`clancy`** → **`403`** (body `Forbidden`); `alice` **não** é editada (o `403` sai antes da escrita).
9. **Fixed — a feature funciona pro dono:** `PATCH /users/clancy` (próprio) com o token do `clancy` → **`200`**. Sem/ruim token ainda → `401`. **Sem admin envolvido.**
10. **Fixed — `403` antes da busca:** `PATCH /users/nobody` (inexistente) com token válido → **`403`** (não `404`) — o gate roda antes do lookup, não vaza existência de alvo. `PATCH /users/__proto__` → `403`.
11. **Fixed — `GET` inalterado:** `GET /users/clancy` → `200`, `GET /users/alice` → `403` — iguais ao vulnerable.
12. **`app.ts` DIFERE só pela guarda de posse** (`if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only` + o comentário) acrescentada ao `PATCH` entre `vulnerable/` e `fixed/`, e essa linha é **byte-idêntica** à que já existe no `GET`. `POST /login`, `GET`, helpers, imports, `USERS`, rodapé, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` **idênticos** entre as versões.
13. **Resposta não vaza dado alheio nem token:** o sucesso serializa só `{ handle, displayName }` (eco do input); nenhum token em resposta alguma. **Um bug só** (BFLA).
14. **Superfície mínima:** só `POST /login`, `GET /users/:handle`, `PATCH /users/:handle`. **Sem** listagem, **sem** `GET /me`, **sem** DELETE, **sem** índice de rotas.
15. **Estado mutável:** escritas reais, mas nenhuma resposta do walkthrough depende do acúmulo — rodar a sequência duas vezes dá status e corpos idênticos (o `PATCH` ecoa o input; o único `GET` lido é o próprio de `clancy`, nunca escrito). Gêmeos independentes (8205 ↔ 8305).
16. **API-only:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, sem render de HTML; sucesso sempre `application/json`.
17. **Bind/portas:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1`; container `ENV HOST=0.0.0.0`. **Portas 8205 (vulnerable) / 8305 (fixed)**, internas `3000`, coerentes entre `EXPOSE`, `app.listen` e o compose.
18. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README. (`clancy` masculino no PT; coincide com o masculino do papel.)
19. **Theory primer:** re-confirmar por fetch `https://portswigger.net/web-security/access-control` (200, sem redirect); texto do link "Access control vulnerabilities and privilege escalation", em inglês no PT. **Confirmar que NÃO é a página de IDOR de 01–03** (é a mesma do 04).
20. **RFC 9110** citado como nesta spec: **§15.5.4 (403 Forbidden)** (credencial presente, insuficiente; `404` como `MAY` pra esconder existência) e **§15.5.2 (401 Unauthorized)** (`WWW-Authenticate` obrigatório). Texto bruto conferido nesta fase em `rfc-editor.org/rfc/rfc9110.txt`; **reconfirmar na geração** antes de cravar as citações.
21. **`npm audit --omit=dev` em cada gêmeo**, advisories esperados **registrados**. O átomo é vulnerável na **LÓGICA** (cobertura de método ausente), **não nas dependências** (idênticas a 01–04). Meta: zero advisory de runtime.
22. **`npm run typecheck` (`tsc --noEmit`, typescript 7.0.2) verde nos DOIS gêmeos** — inclusive o `vulnerable/`. Gate de **host/CI**, não do container. **Shape validado nesta fase** (ver "Validação").
23. **Frases-âncora:** cada uma numa casa só (WALKTHROUGH: o par método+path; DIFF: o fix leva a guarda do `GET` pro `PATCH`); **não** reusar as âncoras de 01/02/03/04 — em especial, manter distância da de 03 ("which question it answers") e das do 04.
24. **Rótulo em todo bloco do WALKTHROUGH** (EN e PT): método · alvo · o que isola. A prosa **nomeia e desarma** as duas leituras erradas ("isto é BOLA", "isto é o 04 de novo").
25. **Cross-ref:** 04 central (eixo método vs função); 01–03 (posse e "check presente"); **nenhum** átomo de API 06+; **nenhuma** antecipação de BOPLA/mass assignment.

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; toolchain herdado e lido dos arquivos de 01–04; URL do primer e seções do RFC 9110 verificadas por fetch/texto bruto nesta fase; shape TS, comportamento dos endpoints e a prototype pollution validados em protótipo com o toolchain exato (ver "Validação de typecheck e runtime"). Resto é smoke test na Fase 2.

---

## Notas específicas pro Claude Code

- **Princípio guia:** a lição é **autorização se aplica a (método + path), não a path**. Cada doc deve manter o eixo do **método** visível: o `GET` guarda a posse, o `PATCH` não; a MESMA URL recusa a leitura alheia e aceita a escrita alheia. Se o aluno sair achando "li/mexi no objeto de outro" (BOLA) ou "o endpoint não tinha check" (o 04), o átomo falhou.
- **O eixo duplo é a disciplina.** O check que varia por método **é** de posse (object-level) — mas o eixo da vuln é o **método** (function-level/API5). A pergunta de auditoria é "a autorização cobre todos os métodos deste path?", não "de quem é o objeto?". **Não deixar a prosa deslizar pra BOLA.**
- **O `GET` é intocável e correto nos dois gêmeos.** Ele é a prova viva de que a authz de posse existe. **NÃO** removê-lo nem enfraquecê-lo "pra simplificar" — ele é o que afasta as duas leituras erradas.
- **Dois handlers independentes, não um middleware por método.** A assimetria linha a linha é a lição. Um middleware que discrimina por método por dentro seria um bug artificial — **PARE** se a geração tender a isso.
- **Fix = a MESMA guarda do `GET`, no `PATCH`, byte-idêntica, antes da busca.** `if (req.params.handle !== caller) return res.sendStatus(403);`. Comparação de identidade, **sem `?.`**. Diferente dos fixes de 01/02 (predicado de posse pós-busca), 03 (mover a busca) e 04 (guarda de papel com `?.`). Dizer por que é diferente faz parte da lição.
- **Status `403`, não `404`.** Argumento próprio: a guarda compara identidade antes da busca → não revela existência (dispara igual pra alheio-existente e inexistente). RFC 9110 §15.5.4. **Não** copiar o `404` do pedido (01/03) por reflexo, nem divergir entre `GET` e `PATCH`.
- **Campo editado é COMUM (`displayName`).** **NUNCA** `is_admin`/papel — isso invadiria o 04 e o futuro `bopla-mass-assignment` e embaralharia o eixo. Se a geração sentir vontade de escrever um campo de privilégio, **PARE**.
- **Resposta do `PATCH` é o delta (eco do input), não dado alheio.** `{ handle, displayName }` com o valor enviado. **Não** devolver o registro "antigo" da `alice`.
- **`Map`, não `Record`.** O `PATCH` escreve através de chave-string do path → prototype pollution se for objeto literal. `Map` fecha estruturalmente (validado). **Não** reintroduzir `Record` + `Object.hasOwn`.
- **SEM admin, SEM demote, SEM listagem, SEM `GET /me`.** O caminho positivo do fix é `clancy` editando o próprio registro. Superfície: três rotas, nenhuma a mais.
- **Impacto honesto:** escalação **horizontal** (escrever no registro de um par via método desprotegido); **não** vertical, **não** RCE. Contraste com o 04 (vertical).
- **Elenco:** `clancy` atacante **masculino** (concordância coincide com a do papel — "o dono", "o chamador"); `alice` vítima. Reuso do elenco; sem personagem novo; **sem admin**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# bfla-method-based — Broken Function Level Authorization (BFLA)`. Headers de seção **traduzidos** no PT; termos técnicos em inglês.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série. Este átomo **fecha a Fase 1 API** — o corte da release `v1.1` é trabalho de mantenedor, pós-merge (CLAUDE.md §12), fora do escopo da geração do átomo.
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 05 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): todos os itens do checklist acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8205` (vulnerable), `127.0.0.1:8305` (fixed). Bind **só** em `127.0.0.1`.

---

## Verificação factual dos átomos publicados (conferida LENDO os arquivos nesta fase)

A spec afirma herança e contraste com 01–04; tudo abaixo foi conferido **lendo os arquivos publicados nesta fase de planning** (não de memória):

1. **Toolchain** — `package.json` dos quatro átomos (incluindo `bfla-admin-function`) com express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; scripts `start: tsx app.ts`, `typecheck: tsc --noEmit`; `name` por átomo, `private: true`, `type: module`. (`package.json` do 04 difere dos de 01–03 só no `name` — md5 distinto por isso.)
2. **`Dockerfile`** — **md5 idêntico nos quatro** átomos (`cad28299…`): `node:24.21.0-slim`, `npm ci --omit=dev`, `COPY tsconfig.json` + `COPY app.ts`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm","start"]`.
3. **`tsconfig.json`** — **md5 idêntico nos quatro** (`9a2dc4f6…`): `nodenext`, `target/lib es2024`, `types [node]`, `strict`, `noUncheckedIndexedAccess`, `esModuleInterop`, `noEmit`.
4. **`docker-compose.yml`** — bind `127.0.0.1`; `8201/8301` (01), `8202/8302` (02), `8203/8303` (03), `8204/8304` (04). Este átomo: `8205/8305`.
5. **Bloco de auth** — `TOKENS = new Map<string,string>`, `issueToken` com `randomBytes(24).toString("base64url")`, `authenticate` por `Bearer`, `USERS.has(user)` no login, `res.set("WWW-Authenticate", "Bearer").sendStatus(401)` nos handlers. 01–03 têm `USERS = new Set([...])`; **04 usa `USERS = new Map<string, User>`** (`User = { is_admin }`) — este átomo segue a forma do 04 (`User = { displayName }`).
6. **Fix do 04** — `if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);` (guarda de **papel** do chamador, com `?.` pelo `Map.get`); comentário `FIXED:` com "checked right after authentication … BEFORE the target is ever looked up". Devolve `403` (não `404`), com o argumento RFC 9110 §15.5.4 e o critério da série no DIFF. Trilha só Repeater (sem Intruder). `Map` escolhido pra fechar prototype pollution no `:handle`.
7. **Fix de 01/02** — `if (!order || order.owner !== caller) return res.sendStatus(404);` (predicado de posse **depois** da busca). **03** — `const order = ordersOf(req.params.storeId).find(...)` (move a **busca** pro escopo do pai); `403` pra loja (existência não-sensível), `404` pro pedido (id-space enumerável).
8. **Status de 01–04** — 01/03 devolvem `404` indistinguível pro pedido (oráculo de enumeração sobre id); 02 herda o `404`; 03 dá `403` pra loja; 04 dá `403` pra função conhecida. O DIFF do 01 fecha com *"`404` when existence itself leaks; `403` when admitting existence is fine"* (RFC 9110 §15.5.4/§15.5.5).
9. **Elenco** — `clancy` é o atacante (masculino) em código e docs; `alice` é a vítima/vítima-principal em todos. `carol` é a admin no 04; `bob`/`carol` operadores no 03. Este átomo usa só `clancy` e `alice`, sem admin.
10. **H1** — 01–03: `# <id> — Broken Object Level Authorization (BOLA)`; 04: `# bfla-admin-function — Broken Function Level Authorization (BFLA)`. Este: `# bfla-method-based — Broken Function Level Authorization (BFLA)`, idêntico EN/PT.
11. **Primer** — 01–03 usam PortSwigger **IDOR** (`/web-security/access-control/idor`); **04 usa Access control** (`/web-security/access-control`). Este átomo segue o 04 (mesma página; verificada por fetch nesta fase, 200, sem redirect). `APIX:2023` em texto simples, sem link OWASP nos docs; link canônico na tabela de Cobertura do ROADMAP (linha API5 já aponta os dois `bfla-*`).
12. **Publicação** — `atoms/api/ROADMAP.md`: 01–04 `[x]`, 05 (`bfla-method-based`) `[ ]`, 06+ `[ ]`. Árvore de `atoms/api/`: existem `API1-broken-object-level-authz/` (três átomos) e `API5-broken-function-level-authz/` (um átomo, o 04) — nenhuma outra pasta `APIX-*` ainda.
