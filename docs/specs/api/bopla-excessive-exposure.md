# Spec — Átomo API 06: `bopla-excessive-exposure`

> Documento de especificação para o Claude Code implementar o **sexto átomo da série API** do projeto `atomicvulns` (Fase 2 API, "Property Authz & Auth", milestone `v1.2`; **abre a fase**). Classe: **BOPLA — Broken Object Property Level Authorization**, o **API3:2023** do OWASP API Security Top 10 (2023) — categoria **nova na série**: este é o **primeiro** átomo dela, e nasce com a pasta `API3-broken-object-property-level-authz/` (greenfield; diferente do 05, que caiu numa `API5-*` já existente). Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **A face de leitura de BOPLA.** Os átomos de authorization da série subiram por granularidade: **objeto** (BOLA/API1 — 01–03: *de quem é este objeto?*), **função** (BFLA/API5 — 04–05: *você pode invocar esta operação?*). Este desce um nível a mais, pro grão da **propriedade**: o chamador **tem** direito de ler este objeto — é o registro **dele** —, mas a resposta devolve **campos que ele não pode ver**. É a **face de leitura** de BOPLA (API3:2023), o que a indústria chama de *excessive data exposure* (exposição excessiva de dados). A pergunta de auditoria cravada, diferente de todas as anteriores: **"a resposta devolve só os campos que este chamador pode ver?"** Tudo o que esta spec afirma sobre os átomos 01–05 foi conferido **lendo os arquivos publicados em `main`**, não de memória (ver "Verificação factual dos átomos publicados").
>
> **O CENÁRIO É SELF-READ — e isso é a disciplina.** `clancy` lê o **próprio** registro (`GET /users/clancy`), autorizado no nível de objeto **porque o registro é dele**. É o **isolamento máximo** do BOLA: ele lê o objeto **dele**, então "li o objeto de outro = BOLA" simplesmente **não se aplica**; a única coisa errada que sobra vive no grão da propriedade. A guarda de posse do 05 continua lá, **byte-idêntica**, e **passa** na self-read — a falha nova vive **uma linha abaixo**, na serialização. **Sem essa disciplina o átomo é lido como BOLA — e não é.** Toda a redação (código, WALKTHROUGH, DIFF) existe pra manter o eixo da **propriedade** visível.
>
> **A INVERSÃO 05↔06 (material do átomo).** No 05, o `GET /users/:handle` era a **prova viva** do check correto (recusava a leitura alheia com `403`). No 06, o **mesmo** `GET` é o **vulnerável**: mesma guarda de posse em cima, **falha nova embaixo** (o objeto inteiro serializado). O átomo reusa a superfície exata do 05 e inverte o papel do handler.
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **`atoms/api/API5-broken-function-level-authz/bfla-method-based/`, inteiro** — herança **direta** da superfície `/users/:handle`: o bloco de auth, o `Map<string, User>`, a **guarda de posse** `if (req.params.handle !== caller) return res.sendStatus(403);` (byte-idêntica aqui), o argumento `403`/RFC 9110, e a forma dos seis documentos. A **inversão de papel do `GET`** (lá prova-viva, aqui vulnerável) é material deste átomo.
> 2. **`atoms/api/API5-broken-function-level-authz/bfla-admin-function/`, inteiro** — o precedente do `Map<string, User>` e do flag `is_admin` (snake_case). Aqui `is_admin` reaparece como **campo vazado**, **não** como lição — ver disciplina abaixo.
> 3. **`atoms/api/API1-broken-object-level-authz/bola-sequential-id/`, `bola-uuid-leaked/`, `bola-nested-resource/`, inteiros** — a **origem do check de posse** (`order.owner === caller` → `handle === caller`) que este átomo **mantém e faz passar** na self-read, pra deixar claro que a object-level authorization **não é** a falha aqui.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`). A validação em protótipo descartável foi feita **nesta fase** (ver "Validação de typecheck e runtime").

---

## Identidade

- **ID:** `bopla-excessive-exposure`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API3 — Broken Object Property Level Authorization**
- **Pasta:** `atoms/api/API3-broken-object-property-level-authz/bopla-excessive-exposure/` — **pasta NOVA, primeira da categoria API3** (não existe ainda; greenfield). O átomo nasce criando a pasta `API3-broken-object-property-level-authz/`.
- **Número sequencial (série API, conta do 01):** 06
- **Porta vulnerable:** `127.0.0.1:8206`
- **Porta fixed:** `127.0.0.1:8306`
- **Porta interna do container:** `3000` (igual a 01–05). Compose mapeia `127.0.0.1:8206:3000` e `127.0.0.1:8306:3000`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1); `ENV HOST=0.0.0.0` só dentro do container.
- **Fase / milestone:** Fase 2 API, `v1.2` (sexto átomo; **abre a fase**).
- **Branch de trabalho:** `atom/bopla-excessive-exposure` — criada na Fase 2 a partir de `main` atualizada.
- **H1 dos READMEs (idêntico em EN e PT):** `# bopla-excessive-exposure — Broken Object Property Level Authorization (BOPLA)`. O título nomeia a **classe**; o slug qualifica a variante (CLAUDE.md §5). H1 **novo** na série (primeira aparição de BOPLA).
- **Theory primer:** ver seção "Theory primer" (URL verificada por fetch nesta fase — HTTP 200, sem redirect; é a página **Information disclosure**, **não** a de IDOR de 01–03 nem a de Access control de 04–05).

---

## A tese do átomo

> **A autorização se aplica no nível da PROPRIEDADE, não só do objeto nem da função.** O chamador tem direito de ler este objeto — é o registro **dele** —, mas a resposta devolve **campos que ele não pode ver**. O handler autoriza corretamente o **objeto** (a guarda de posse do 05, intacta) e então serializa o **objeto inteiro**, deixando cada campo server-side (o `passwordHash`, o `is_admin`) pegar carona com o campo público (`displayName`). A pergunta de auditoria é **"a resposta devolve só os campos que este chamador pode ver?"** — e a resposta, no `vulnerable/`, é *não*.

### O eixo é a propriedade — e isso é a lição inteira

Os átomos de API1 (01–03) perguntavam sobre o **objeto** (*de quem é este objeto?*). Os de API5 (04–05) perguntavam sobre a **função/operação** (*você pode invocar isto? / a autorização cobre todos os métodos?*). Aqui a pergunta desce um grão: **"a resposta devolve só os campos que este chamador pode ver?"** — e a resposta, no `vulnerable/`, é *não*: devolve `displayName` (público) **e** `passwordHash` **e** `is_admin` (internos). A falha **não** é ler o objeto de outro (a posse barra isso com `403`), **não** é invocar uma função proibida (não há função privilegiada aqui); é a resposta **entregar propriedades demais** de um objeto que o chamador legitimamente pode ler.

### Self-read: o isolamento máximo do BOLA, e a disciplina que ele impõe

O cenário é deliberadamente a **self-read**: `clancy` lê o **próprio** registro, `GET /users/clancy` com o token do `clancy`. Isso é escolha de desenho, não detalhe:

- **Object-level authorization está presente, correta, e PASSA.** A guarda `if (req.params.handle !== caller) return res.sendStatus(403);` — a do 05, byte-idêntica — roda e **aprova**, porque `clancy` é dono do registro `clancy`. Não há objeto alheio sendo lido.
- **Logo "isto é BOLA" não tem onde se apoiar.** Em um átomo onde o atacante lê o objeto de **outro**, o aluno pode confundir property-exposure com object-access. Aqui ele lê o **próprio** objeto; a única coisa errada que sobra é **property-level**. O `403` de `GET /users/alice` (token do `clancy`) confirma, de graça, que o check de objeto existe e morde — é o passo "não é BOLA" caindo no colo.
- **A pergunta de auditoria cravada:** *"a resposta devolve só os campos que este chamador pode ver?"* — **NÃO** *"de quem é o objeto?"* (BOLA) nem *"você pode invocar esta operação?"* (BFLA). Toda a redação serve a manter esse eixo em foco.

### A inversão 05↔06 — o mesmo `GET`, papel invertido

No 05, o `GET /users/:handle` era a **prova viva** de que a authz de posse existia e funcionava (recusava a leitura alheia, afastava a leitura "não é BOLA"). Aqui o **mesmo** `GET` é o **vulnerável**: a guarda de posse continua em cima, byte-idêntica, e **passa** na self-read; a falha nova vive **uma linha abaixo**, na serialização (`res.json({ handle, ...user })`). **A assimetria do 06 é DENTRO do handler** (authz de objeto certa, serialização solta), não **entre** dois handlers do mesmo path (como era no 05: `GET` guardado, `PATCH` não). Cravar o contraste 05↔06 em WALKTHROUGH e DIFF.

### O erro de leitura a combater — e ele determina o desenho

Este átomo tem leituras erradas prováveis — **duas firmes** e **uma terceira cortável** —, e o desenho existe pra desarmá-las. O WALKTHROUGH **nomeia cada uma e a desmonta** (ver "Walkthrough"); a terceira ("controle no cliente é controle") entra **como princípio, se couber em uma frase limpa** — não há UI neste átomo:

1. **"Isto é BOLA."** O aluno vê campos sensíveis e pensa "li dado que não era meu" — raciocínio de objeto. **Desarme:** `clancy` lê o **próprio** registro; e `GET /users/alice` com o token dele dá **`403`** — a object-level authorization **existe, está correta e morde**. Não há objeto alheio na jogada. A falha é no conteúdo do **seu** objeto, não no acesso a um alheio.
2. **"Isto é crypto fraco (o átomo web `crypto-weak-hash`)."** O aluno vê `passwordHash` e pensa "a lição é a força do hash". **Desarme:** a lição é o hash **ESTAR na resposta**, não a qualidade dele. O `passwordHash` jamais deveria sair do servidor, qualquer que fosse o algoritmo. Crypto fraco é **outra classe** (tem átomo web próprio); aqui o problema é **exposição**.
3. **"Controle no cliente é controle."** O aluno pensa "numa app real a tela não mostraria esses campos". **Desarme (como PRINCÍPIO):** num app real a UI até omitiria os campos — mas o pentester lê o **raw** de qualquer jeito; a filtragem tem que ser **server-side**. **RESSALVA DURA:** a série é **API-only, NÃO há UI neste átomo** — enquadrar como princípio ("num app real a UI esconderia; aqui não há UI, e é exatamente esse o ponto"), **nunca** apontar pra uma tela que não existe.

### Por que API3 (Broken Object Property Level Authorization)

O bug **não é** "input virou código" (injection), **não é** "um objeto fora do escopo foi lido" (BOLA — o chamador lê o objeto **dele**), **não é** "uma operação proibida foi invocada" (BFLA — não há função privilegiada). É **"a resposta entrega propriedades de um objeto que o chamador não pode ver"** — controle de acesso **no nível da propriedade**: **API3** no OWASP API Security Top 10 **2023**, na sua **face de leitura** (*excessive data exposure*). Situe nessa edição, **sem arqueologia** (CLAUDE.md §5 — nomear a categoria vigente, não "era API3 em 2019" nem recontar a fusão de edições). Referência OWASP em **texto simples** (`API3:2023`), **sem link** — o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (a linha API3 **já existe**, apontando `bopla-excessive-exposure` e `bopla-mass-assignment`). Por ser vuln de **lógica/autorização** (Trigger, não Payload), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório (ver "Walkthrough").

---

## O que este átomo acrescenta (vs. 01–05)

**Honestidade pedagógica:** 01–03 ensinaram BOLA (o eixo do objeto); 04–05 ensinaram BFLA (o eixo da função/operação). Este **credita e não reabre** nada disso. Ele existe por três eixos novos:

1. **Primeiro átomo no grão da PROPRIEDADE.** O chamador está **totalmente autorizado para o objeto** (posse presente, correta, e **passa** na self-read) e a **única** coisa errada está no nível do **campo**. É a estreia da categoria API3 e do conceito de property-level authorization na série.
2. **Primeiro átomo em que a self-read É o exploit.** Em 01–05 o exploit tocava um objeto/operação que não era do chamador (outro pedido, outra loja, outro registro, outro método). Aqui o chamador lê o **próprio** registro e o vazamento **já está ali** — isolamento máximo do BOLA. A prova é **auto-contida** (ver "Padrão de prova").
3. **A inversão do `GET` do 05.** Reusa a superfície exata do 05 (`/users/:handle`, `Map<string, User>`, guarda de posse) e **inverte o papel do `GET`**: lá prova-viva do check correto, aqui o handler vulnerável. Mesma guarda em cima, falha nova embaixo (serialização). O contraste 05↔06 **é** material.

> **Contraste a cravar (WALKTHROUGH e DIFF):** no 05 o `GET` recusava a leitura alheia e **essa recusa** era a prova de que a authz funcionava; aqui o `GET` **aprova** a self-read (corretamente, no nível do objeto) e **vaza campos** no nível da propriedade. Mesma guarda de posse, dois papéis: no 05 ela definia a lição (cobertura por método), aqui ela **afasta** a leitura errada (não é BOLA) enquanto a lição mora uma linha abaixo.

---

## Feature simulada — perfil de conta (API-only, sem HTML)

**Perfil de conta de uma plataforma multiusuário.** Cada usuário tem um perfil com um **nome de exibição** (display name) público. A API de self-service deixa o usuário **ver o próprio perfil** (`GET /users/:handle`). Do ponto de vista do produto, "você vê o seu perfil, com o seu nome de exibição" — e a posse até confere que o registro é seu. O que o dev esqueceu foi **filtrar o que a resposta devolve**: o registro guarda, ao lado do `displayName`, campos server-side (`passwordHash`, `is_admin`) que nunca deveriam sair — e o handler serializa o objeto **inteiro**.

**API-only por natureza** (CLAUDE.md §3.3 — a série API é API-only): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`; erros via `res.sendStatus(...)` (igual a 01–05). Request com corpo JSON só no `POST /login`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl** (ver "Walkthrough").

### A "descoberta" é inspecionar o corpo cru — e isso é a técnica

Não há endpoint a descobrir, nem ator a encenar. A vulnerabilidade se manifesta na resposta **legítima** à leitura **legítima** do próprio perfil: o aluno loga como `clancy`, lê `GET /users/clancy`, e os campos internos **já estão no corpo**. A "técnica" é **olhar o raw response no Repeater** — exatamente o reflexo que separa o pentester de quem confia na UI. Nenhum segundo request, nenhum segundo ator, nenhum payload (ver "Padrão de prova").

---

## Autenticação — token opaco, cripto-forte (mesmo mecanismo de 01–05)

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados e devolve `{ "token": "<opaco>" }`. Mapa `token → usuário` **em memória**, resolvido por lookup. **NÃO é JWT.** Os helpers de auth (imports, `TOKENS`, `issueToken`, `authenticate`) são **byte a byte** os de 01–05 (conferido: md5 do bloco batendo) — **copiar, não reescrever**. Token com `randomBytes(24).toString("base64url")`: um token previsível seria uma segunda vulnerabilidade e violaria "um átomo = uma vuln" (CLAUDE.md §2). O ataque **não toca** o token.

**Estrutura de `USERS` — `Map<string, User>`, igual a 04/05.** Cada usuário carrega agora **três** campos: `displayName` (público), `passwordHash` (dummy, server-side) e `is_admin` (interno). Ver "Store / dados".

**O que a auth prova e o que NÃO prova (deixar explícito — faz parte da lição):**

- **Autenticação prova *quem você é*.** Token ausente/ruim → `401` COM `WWW-Authenticate: Bearer`, no `vulnerable/` exatamente como no `fixed/`.
- **A posse (*este objeto é seu?*) é checada e PASSA na self-read** — nos dois gêmeos. O chamador lê o próprio registro; a object-level authorization não é a falha.
- **A property-level authorization (*quais campos você pode ver?*) é o que o `vulnerable/` não faz** e o `fixed/` passa a fazer. Essa é a única diferença entre os gêmeos.

**Usuários seedados (elenco da série — CLAUDE.md §5):**

- **`clancy`** — o **atacante** (você). Dono do **próprio** registro (`clancy`), que ele lê no exploit. (Elenco da série API: `clancy` é **masculino**; nos docs PT, "o atacante", "você mesmo", "dele". O masculino genérico do **papel** — "o dono", "o chamador" — coincide com o da pessoa; não há distinção a manter.)
- **`alice`** — existe **apenas** pra sustentar o `403` do passo de contraste (`GET /users/alice` com o token do `clancy`). Ela **não** é lida com sucesso em nenhum passo; o exploit inteiro acontece no registro do `clancy`.

**AMBOS `is_admin: false`, SEM admin.** Este átomo **não precisa** de papel administrativo — e não tê-lo reforça o eixo: o vazamento é do **campo** (`is_admin` **estar** na resposta) e do **padrão** (objeto inteiro serializado), **não do valor** `true`. Nenhum usuário é admin; ninguém é promovido; o flag volta `false` e **ainda assim** é um vazamento, porque é um campo interno que escapou. Ver a disciplina em "Store / dados".

**Requisito de README (EN+PT) — declarar o atalho:** o login sem senha é um **atalho deliberado do laboratório, não a vulnerabilidade**; e o `passwordHash` é **dado dummy realista stored-side, NÃO usado pelo login, NÃO é credencial real**. Uma frase, **sem citar átomo** (mesmo requisito de 01–05).

---

## Store / dados — registro com um campo público e dois campos server-side, em memória

**Sem banco** (CLAUDE.md §3.4). Estruturas TS. O `TOKENS` cresce a cada login; o `USERS` é **imutável em runtime** (este átomo só **lê** — não há escrita; ver "Estado mutável").

```ts
// --- Simulated identity: an opaque, server-side token; users own their own profile ---
// Each user owns exactly the record keyed by their own handle; ownership is handle == caller.
// Next to the one public field (displayName) the record carries two server-side fields:
// passwordHash -- a dummy, bcrypt-shaped string the passwordless login never reads -- and
// is_admin, an internal role flag. Neither is meant to leave the server.
// A Map, as in the series' other user stores: Map.get() types the record as User | undefined.
type User = { displayName: string; passwordHash: string; is_admin: boolean };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park",  passwordHash: "$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpasswordCLANCY", is_admin: false }],  // attacker (you) -- reads his own record
  ["alice",  { displayName: "Alice Nguyen", passwordHash: "$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpassword.ALICE", is_admin: false }],  // the other account -- exists only to make GET /users/alice a 403
]);
```

- **`displayName` é o ÚNICO campo público.** `passwordHash` e `is_admin` são server-side: existem no store, nunca deveriam entrar numa resposta de perfil. O `vulnerable/` os devolve; o `fixed/` não.
- **`passwordHash` é dummy GRITANTE, bcrypt-shaped.** Formato bcrypt (`$2b$12$` + 22 chars de salt + 31 chars de hash = 60 chars), mas o conteúdo (`DUMMYsaltFORlabUSEonly…`, `…NOTaREALpassword…`) grita "teste". **Validado nesta fase:** comprimento 60, charset `[./A-Za-z0-9]` no corpo — tem a **forma** de um bcrypt real sem **ser** um (CLAUDE.md §8.3: sem credencial real). O login **nunca o lê** (é passwordless); ele existe só pra ser o artefato de credencial que o bug vaza.
- **`is_admin` em snake_case — continuidade cosmética com o 04, NÃO lição.** O campo reaparece com a grafia do 04 por consistência de store; **não** se promove essa grafia a contraste pedagógico (mesma regra da nota `:handle`-vs-`:id` do 05). **AMBOS `false`:** o vazamento é do **campo e do padrão** (objeto inteiro serializado), **não do valor** — não escrever a prosa como se `true` fosse o prêmio. `is_admin` é **somente-leitura** neste átomo: o walkthrough mostra o flag **voltando** na resposta; **NÃO** sugere flipá-lo, **NÃO** insinua que escrevê-lo seria o próximo passo (forward reference proibida — ver "Política de cross-ref").
- **Posse = `handle === caller`.** Herdada do 05 (que a herdou de `order.owner === caller` de 01/02). Aqui ela **passa** na self-read e **afasta** o BOLA; não é a lição.
- **Dois usuários, nenhum admin, nenhum campo além dos três.** Superfície mínima.

### Por que `Map`, e por que — ao contrário do 05 — NÃO é defesa de prototype pollution (honesto)

**Decisão do mantenedor: `Map<string, User>`, por continuidade com 04/05.** No 05 o `Map` tinha **dois** papéis: tipar `user` como `User | undefined` (forçando a guarda `!user`) **e** fechar prototype pollution, porque o `PATCH` **escrevia** através de um lookup por chave-string do path (`USERS.get(req.params.handle)` seguido de `user.X = ...`). **Aqui só há `GET`**, e a guarda de posse (`req.params.handle !== caller → 403`) roda **antes** do `USERS.get(...)` — então um `:handle` de `__proto__`/`constructor` nunca alcança o lookup (bate `403` porque `"__proto__" !== "clancy"`). **Validado nesta fase:** `GET /users/__proto__` e `GET /users/constructor` → `403` nos dois gêmeos. Logo:

- **O `Map` aqui NÃO é defesa de prototype pollution** — não há escrita, e a posse precede o lookup. Promovê-lo a isso seria afirmação falsa sobre o código. Descrever honestamente: `Map` é **herança estrutural** (continuidade com a forma de store de 04/05) e dá o tipo `User | undefined` que torna a guarda `!user` **exigida no `fixed/`** (ver abaixo). **Nada de prototype pollution na prosa deste átomo.**
- **`USERS.has(user)` no `POST /login`** continua a MESMA forma da série (Set e Map compartilham `.has`).

> **Sobre a guarda `!user` — assimetria honesta entre os gêmeos (validada nesta fase).** `USERS.get(req.params.handle)` tipa `User | undefined`. No `fixed/`, `user.displayName` **desreferencia** → a guarda `!user` é **exigida pelo compilador** (sem ela, `TS18048`). No `vulnerable/`, `res.json({ handle, ...user })` **espalha** `User | undefined`, e espalhar `undefined` é **no-op aceito pelo TS** → a guarda **NÃO é forçada** no `vulnerable/`. **Mantê-la byte-idêntica nos dois gêmeos** como higiene (e pra o diff ser só a linha do `res.json`), mesmo sendo type-forced só no `fixed/`. Em runtime ela é **inalcançável** nos dois: a posse garante `handle === caller`, e `caller` é sempre um handle seedado, então o `USERS.get(...)` sempre acha. Guarda honesta, exigida pelo tipo no `fixed/`, inalcançável em runtime. Registrar esse TS18048 (presença no `fixed/`, ausência no `vulnerable/`) nos docs.

---

## Rotas — superfície mínima, duas rotas, nenhuma a mais

Imports: `import express from "express";` e `import { randomBytes } from "node:crypto";`. Bootstrap (`const app = express();` + `app.use(express.json());`), `USERS`, `TOKENS`, `issueToken`, `authenticate` e o rodapé `listen` são **idênticos** entre `vulnerable/` e `fixed/`. Superfície: **duas rotas, nenhuma a mais** — `POST /login` e `GET /users/:handle` (o vulnerável). **Sem** `PATCH` (escrita de propriedade é **fora de escopo** — não citar nem antecipar), **sem** `GET /users` (listagem), **sem** `GET /me`, **sem** índice de rotas. O `app.use(express.json())` fica (o `POST /login` usa o body) — idêntico a 01–05.

### `POST /login` — obter o próprio token (idêntico às cinco versões anteriores)

Recebe `{ "user": "<nome>" }`, valida contra `USERS` (via `USERS.has(user)`), devolve um token opaco. Sem senha (atalho de auth). Usuário desconhecido/ausente → `400` (higiene).

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

### `GET /users/:handle` — ler o próprio perfil (a rota VULNERÁVEL)

Autentica (Bearer ruim → `401`), confere a **posse** (`:handle === caller`, senão `403`), busca o registro, e serializa o **objeto inteiro** (`...user`), vazando `passwordHash` + `is_admin`. **A guarda de posse é correta e passa na self-read; a falha vive na linha do `res.json`.** Handler **≤ ~30 linhas** (tem ~8).

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

- **A guarda de posse vem ANTES da busca** e **passa** na self-read (`clancy` lê `clancy`). É byte-idêntica à do `GET` do 05. Ela **não é a falha** — é o que **afasta** o BOLA (e o que dá o `403` do passo de contraste em `GET /users/alice`).
- **Source:** o objeto `user` no store (com os campos internos). **Sink conceitual:** o `...user` (spread do objeto inteiro) numa resposta — a serialização que não filtra. O bug é **o campo (e o padrão) que não deviam estar na resposta**, não um input malicioso. Não greppa; audita-se perguntando **"a resposta devolve só os campos que este chamador pode ver?"**.
- **`handle` continua a chave do `Map`, não um campo de `User`.** `{ handle: req.params.handle, ...user }`: `handle` é posto explicitamente (eco do path), e `...user` espalha os campos do registro (`displayName`, `passwordHash`, `is_admin`). Sem colisão (`User` não tem `handle`). **Validado em runtime:** corpo `{"handle":"clancy","displayName":"Clancy Park","passwordHash":"$2b$12$DUMMY…","is_admin":false}`.
- **`USERS.get(req.params.handle)` → `User | undefined`:** a guarda `!user` é higiene (type-forced só no `fixed/`; ver nota em "Store / dados"), inalcançável em runtime.

> **Bind do servidor** (rodapé idêntico a 01–05): `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);`

> **UM HANDLER, assimetria INTERNA.** Ao contrário do 05 (dois handlers no mesmo path, a assimetria **entre** eles), aqui a assimetria é **dentro** do `GET`: authz de objeto correta (a guarda de posse) **e** serialização solta (o `...user`), separadas por uma linha. O WALKTHROUGH mostra **um** handler (não dois lado a lado como o 05). **NÃO** inventar um segundo handler nem um filtro condicional — a lição é a linha do `res.json`.

---

## Fix — serializar uma allow-list (whitelist) dos campos públicos, não o objeto inteiro

O gêmeo `fixed/` difere **APENAS pela linha do `res.json`**: troca o spread do objeto inteiro por uma **allow-list** (whitelist — lista explícita dos campos que podem sair). **Nenhuma outra linha muda** — `POST /login`, a guarda de posse, o `!user`, helpers, imports, `USERS`, o rodapé, o `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` são **idênticos**.

```ts
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // FIXED: the response names the fields the caller may see -- an allow-list, not the stored
  // object. A field added to User later stays server-side until someone deliberately exposes it.
  res.json({ handle: req.params.handle, displayName: user.displayName });
});
```

Diff mínimo (o eixo único):

```diff
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);
-  // VULNERABLE: the ownership check above is right -- this IS your record. But the response
-  // spreads the WHOLE stored object, so every server-side field rides along with the public
-  // one. Authorization applies to each property returned, not only to the object.
-  res.json({ handle: req.params.handle, ...user });
+  // FIXED: the response names the fields the caller may see -- an allow-list, not the stored
+  // object. A field added to User later stays server-side until someone deliberately exposes it.
+  res.json({ handle: req.params.handle, displayName: user.displayName });
```

**A leitura correta do fix (cravar no DIFF):** a autorização não pertence só ao **objeto** — pertence a cada **propriedade** que a resposta devolve. O handler já autorizava o objeto (a posse); o fix **estende a autorização ao grão do campo**, nomeando explicitamente o que pode sair. **Validado:** a linha do `fixed/` — `res.json({ handle: req.params.handle, displayName: user.displayName });` — é **byte-idêntica** à linha de resposta do `GET` do 05 (conferido: `grep -Fxc` = 1 em ambos os arquivos). O 06 vulnerável regride exatamente a resposta que o 05 já serializava corretamente; o fix a restaura.

- **Whitelist, não blacklist — e isso é o coração do DIFF (ver foil abaixo).** A allow-list nomeia o que **pode** sair; tudo o mais fica dentro por padrão.
- **DTO/serializer — generalizar, NÃO importar maquinaria.** Em 1–2 frases no DIFF: em escala, essa projeção vira um **serializer/DTO** (Data Transfer Object) compartilhado — um objeto que define, num lugar só, o shape público de cada entidade. **NÃO** trazer essa maquinaria pro átomo (quebraria o diff de uma linha); só nomear o princípio.

### BLACKLIST = FOIL instrutivo no DIFF, NÃO o fix (validado nesta fase)

Mostrar, no DIFF, a alternativa **descartada** — e por que foi descartada (mesmo papel do `Record`+`Object.hasOwn` descartado no 05):

```ts
// CONSIDERED AND REJECTED -- a blacklist (deny-list): strip the known-bad fields.
const { passwordHash, is_admin, ...safe } = user;
res.json({ handle: req.params.handle, ...safe });
```

- **A blacklist "funciona" hoje** — remove `passwordHash` e `is_admin`, a resposta sai limpa.
- **Mas ela FALHA ABERTO (fails open):** um campo sensível **novo**, adicionado ao `User` amanhã (um `internalNote`, um `resetToken`), **vaza sozinho** — ninguém lembrou de acrescentá-lo à deny-list. A whitelist **FALHA FECHADO (fails closed):** o campo novo é **invisível** até alguém deliberadamente liberá-lo.
- **Validado nesta fase (foil em protótipo, tsc exit 0):** com um campo novo `internalNote` acrescentado ao `User`, `spread` (o vulnerable) **vaza** o campo novo; `blacklist` **também vaza** o campo novo; `whitelist` **continua limpa**. É a prova de que a diferença whitelist-vs-blacklist **não é estética** — é fail-closed vs fail-open. Registrar a tabela do foil no DIFF.

---

## Status code — herança pura do 05, sem argumento novo

O 06 é **mais simples em status que o 05**. Os status são herança direta do 05 — **referenciar o argumento do 05, não recontar**:

- **`GET /users/clancy` (self-read) → `200`.** O caminho feliz. No `vulnerable/`, o `200` já carrega o vazamento (campos internos no corpo); no `fixed/`, o `200` traz só `{ handle, displayName }`.
- **`GET /users/alice` (token do `clancy`) → `403`.** **Mesmo argumento do 05:** a guarda de posse compara **identidade antes da busca** (`req.params.handle !== caller`), não consulta o store, não revela existência (dispara igual pra handle alheio-existente e inexistente → sem username enumeration). RFC 9110 §15.5.4: credencial presente, considerada insuficiente → `403` honesto; o `404` como `MAY` pra esconder existência não se aplica (não há existência a esconder). **Este `403` é, de graça, o passo "não é BOLA".** **Referenciar o DIFF do 05** pro argumento completo (RFC 9110, o critério da série, por que o oráculo que força o `404` do pedido no 01/03 não se aplica a uma posse checada por identidade antes da busca) — **não recontar**.
- **Sem/ruim token → `401` com `WWW-Authenticate: Bearer`** (RFC 9110 §15.5.2 — o `401` MUST carregar o challenge; o `403` não carrega, o chamador já está autenticado). Igual a 01–05.
- **O `404` do `!user` é higiene byte-idêntica nos dois gêmeos, INALCANÇÁVEL em runtime.** A guarda de posse garante `handle === caller`, sempre seedado → o `USERS.get(...)` sempre acha. **Validado:** `GET /users/nobody` → `403` (a posse barra antes do lookup, `"nobody" !== "clancy"`), **não** `404`. **Sem `404` de alvo-inexistente** alcançável (não há `PATCH` nem rota que leia alvo alheio depois do gate). O 06 tem **menos** status alcançáveis que o 05 (que tinha um `404` real no `PATCH /users/nobody` do `vulnerable/`).

> **Regra de bolso (a mesma do 05/01):** a existência do alvo é sensível (ou revelada)? Aqui **não** — a posse compara identidade antes da busca e não revela existência nenhuma → **`403`** honesto. O critério é um só, o da série; quem escolhe é a natureza do check, não o átomo. **Não** reabrir o argumento; **forward** pro DIFF do 05.

---

## Padrão de prova — Trigger (auto-contida: a resposta crua É a prova)

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **uma ação legítima com efeito observável** — ler o próprio perfil e **inspecionar o corpo cru**. O campo sensível volta na **mesma resposta**, **pra você**, **sem segundo ator e sem segundo request**.

- **BASELINE = EXPLOIT.** Não há movimento de ataque separado da leitura legítima: você lê o seu perfil e o vazamento **já está ali**. O "exploit" é inspecionar o raw no Repeater. Baseline e exploit são **a mesma request** — distinção honesta a cravar.
- **A prova é AUTO-CONTIDA — e é o contraste honesto com o 05.** No 05, o `200`/eco do `PATCH` **não** provava a modificação (era eco do input do atacante), e a prova precisou de um **segundo ator** (a vítima lendo o próprio registro). Aqui a self-read **prova direto**: o `passwordHash` e o `is_admin` estão no corpo que **você** recebeu, do registro que é **seu**. Nenhuma vítima, nenhum segundo login, nenhuma leitura de confirmação. Cravar: "diferente do 05, a prova aqui não precisa de um segundo ator — ela está no corpo da sua própria resposta".
- **Por ser Trigger → passo de contraste OBRIGATÓRIO** (CLAUDE.md §5) — ver Walkthrough, Step 5.

---

## Estado mutável — nenhum (este átomo só LÊ)

Ao contrário do 04 e do 05 (cujo endpoint atacado **escrevia**), este átomo **não muda estado**: `GET /users/:handle` só lê. Tratamento explícito:

- **`USERS` é imutável em runtime.** Nenhuma request escreve nele. O `TOKENS` cresce a cada login (como em toda a série), mas o conteúdo dos perfis não muda.
- **Toda request é idempotente e determinística.** Re-rodar `GET /users/clancy` dá sempre o mesmo corpo; a ordem dos passos do walkthrough não importa (não há dependência plant→read como no 05). Isso **simplifica** o átomo e reforça a prova auto-contida.
- **Gêmeos independentes.** O seed de cada build é próprio; não há o que "desfazer".
- **Requisito de README (EN+PT), a única casa da frase do restart:** uma frase diz que o estado (tokens) vive em memória e que `./atom down bopla-excessive-exposure && ./atom up bopla-excessive-exposure` zera os tokens (logar de novo); os perfis voltam ao seed (nunca mudam em runtime, de todo jeito). **Não** repetir no WALKTHROUGH nem no DIFF.

---

## Walkthrough — estrutura e requests (7 steps)

Trabalhado **100% no Burp** (Repeater), `curl` como equivalente — **API-only, SEM trilha browser** (CLAUDE.md §3.3). **Sem Intruder:** a tese não é escala/enumeração; é a propriedade exposta, provada em requests únicos. Cada request é um bloco colável: request-line (verbo explícito) + `Authorization: Bearer <token>` + corpo JSON no `POST /login`. Tokens são **placeholders** (`<clancy-token>`); handles são **literais** (seed fixo). **Uma conta é logada:** só o `clancy` (a `alice` nunca é lida com sucesso — só sustenta o `403` do contraste, e esse `403` nem exige o token dela).

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de perfil serve `GET /users/:handle`; a guarda de posse confere que o registro é seu, e então a resposta devolve o objeto inteiro — com os campos internos junto" — não um personagem. Definir todo termo não-óbvio na estreia: "BOPLA (Broken Object Property Level Authorization)", "excessive data exposure", "property-level authorization", "allow-list (whitelist)", "opaque token".

**REQUISITO DE REDAÇÃO — clareza é requisito DURO.** Cada bloco de request é precedido de uma linha de rótulo que diz **MÉTODO**, **ALVO** e **o que aquela request ISOLA**. Formato sugerido:

> **EN:** `Method: GET · Target: clancy (yours) · Isolates: your own record comes back with internal fields attached`
>
> **PT:** `Método: GET · Alvo: clancy (seu) · Isola: o seu próprio registro volta com os campos internos junto`

A prosa **NOMEIA as leituras erradas e as desarma uma a uma**, em vez de só descrever o que acontece: **duas firmes** — "isto é BOLA" e "isto é crypto fraco" — e **uma terceira, "controle no cliente é controle", como PRINCÍPIO, se couber em uma frase limpa** (não há UI neste átomo; ver Step de contraste, item 3). Se não couber, cortar a terceira e ficar só com as duas firmes.

### 1. Context
- API de perfil de conta; auth por Bearer token opaco; `GET /users/:handle` lê o perfil. Isto é **BOPLA** — **API3:2023** do OWASP API Security Top 10 —, na sua **face de leitura** (*excessive data exposure*: a resposta devolve propriedades que deveria ocultar). Definir os termos. **Contraste de abertura:** os átomos de API1 perguntavam sobre o objeto (*de quem é?*); os de API5 sobre a função/operação (*você pode invocar? / a autorização cobre todos os métodos?*); aqui a pergunta desce ao **campo**: *a resposta devolve só os campos que este chamador pode ver?* Você é o `clancy`, e vai ler o **seu próprio** registro — autorizado no nível do objeto — e encontrar nele campos que nunca deveriam ter saído do servidor. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar **UM** handler (`GET /users/:handle`) — **não** dois lado a lado como o 05. A assimetria é **interna**: a guarda de posse (`if (req.params.handle !== caller) return res.sendStatus(403);`) está **presente e correta**, e **uma linha abaixo** o `res.json({ handle, ...user })` espalha o objeto inteiro. Pergunta de auditoria — **diferente** da de BOLA e da de BFLA: não "cadê o check de dono?" (presente, e passa), não "a autorização cobre todos os métodos?" (só há `GET`), mas **"a resposta devolve só os campos que este chamador pode ver?"** → não: devolve `passwordHash` e `is_admin` junto.
- **Inversão 05↔06, cravar:** no 05 esta **mesma** guarda de posse era a prova-viva do check correto (no `GET` que recusava a leitura alheia); aqui ela continua correta — e **afasta** o BOLA — mas a falha nova mora na linha de baixo, na serialização. Notar que a classe **não greppa**: não há string perigosa, há um objeto inteiro indo pra resposta.

### 3. How auth works in this lab (subseção curta)
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo), cripto-forte (`randomBytes`), mapeado ao usuário. **Dois pontos:** (i) a **autenticação É imposta** (token ruim → `401`); (ii) a **posse** do objeto é checada **e passa** na self-read — você lê o **seu** registro. **Disciplina cravada:** o ataque **não toca** o token (não decodifica, não adultera) — fica válido e do `clancy` o tempo todo. O que o laboratório **não** faz: usar o `passwordHash` no login (é passwordless) — ele é dado stored-side dummy, não credencial real (declarar o atalho).

### 4. Baseline = Exploit — log in and read your own profile
- `POST /login` com `{"user":"clancy"}` → `{"token":"<clancy-token>"}`. Bloco colável (request-line + `Content-Type: application/json` + corpo). *(Rótulo: `POST` · logando como `clancy`.)*
- `GET /users/clancy` com `<clancy-token>` → **`200`**. *(Rótulo: `GET` · alvo `clancy` (seu) · isola: o seu próprio registro volta — com os campos internos junto.)* Corpo:
  ```json
  {"handle":"clancy","displayName":"Clancy Park","passwordHash":"$2b$12$DUMMYsaltFORlabUSEonlyDUMMYhashNOTaREALpasswordCLANCY","is_admin":false}
  ```
- **Esta é a prova, e ela é auto-contida.** Você pediu o **seu** perfil, totalmente autorizado, e a resposta trouxe `passwordHash` e `is_admin` — campos server-side que jamais deveriam sair. **Não houve segundo ator, não houve segundo request, não houve payload:** baseline e exploit são a **mesma** leitura legítima; o "exploit" é **olhar o corpo cru no Repeater**. **Contraste honesto com o 05:** lá o `200` do `PATCH` era eco do seu input e **não** provava a modificação — a prova precisou da vítima lendo o próprio registro; aqui a self-read **prova direto**, no corpo que é seu. Cravar essa diferença.

### 5. Step — What the vuln is NOT (passo de contraste OBRIGATÓRIO)
Nomear e desarmar as leituras erradas — **duas firmes** (BOLA, crypto fraco) e **uma terceira cortável** (controle no cliente, como princípio; sem UI, ver item 3). **Um** único request novo (o `403` de BOLA); o resto se desarma com a resposta que o aluno **já tem** (zero requests novos).

1. **"Isto é BOLA — li dado que não era meu."** `GET /users/alice` com o `<clancy-token>` → **`403`**. *(Rótulo: `GET` · alvo `alice` (não é seu) · isola: a posse existe e morde — você não lê o objeto da alice.)* **Desarma:** a object-level authorization está **presente e correta**; você **não** leu o objeto de outro — leu o **seu**. O problema não é acesso a objeto alheio; é o **conteúdo do seu próprio objeto**. (Este `403` é o mesmo argumento do 05 — posse por identidade antes da busca; **forward** pro DIFF do 05, não recontar.)
2. **"Isto é crypto fraco."** Usando a resposta do Step 4 (zero requests novos): **uma frase** — a lição é o `passwordHash` **ESTAR** na resposta, **não** a qualidade do hash. Qualquer que fosse o algoritmo, ele jamais deveria ter saído do servidor. Crypto fraco é outra classe; aqui o eixo é **exposição**.
3. **"Controle no cliente é controle."** **Uma frase, como PRINCÍPIO:** num app real a UI poderia omitir esses campos da tela — mas o pentester lê o **raw** de qualquer jeito; a filtragem tem que ser **server-side**. **RESSALVA DURA:** a série é API-only, **não há UI neste átomo** — enquadrar como princípio ("num app real a UI esconderia; aqui não há UI, e é exatamente esse o ponto"), **nunca** apontar pra uma tela inexistente. Se não couber em uma frase limpa, **cortar** este ângulo e ficar só com (1) + (2).

**Conclusão a escrever explicitamente:** você está **totalmente autorizado para o objeto** (é o seu registro, a posse aprova) e **ainda assim** a resposta te entregou campos que você não pode ver. A falha **NÃO** é ler objeto alheio (não é BOLA), **NÃO** é a qualidade do hash (não é crypto fraco), **NÃO** é a UI (não há UI). É a resposta **devolver propriedades demais**. A pergunta certa é *"a resposta devolve só os campos que este chamador pode ver?"*.

> **Frase-âncora do WALKTHROUGH (uma casa só):** *Owning the object was never the same as being cleared for every field on it — and the raw body shipped all of them, because the only authorization in the path stopped at the object.* / *Ser dono do objeto nunca foi o mesmo que ter liberação pra cada campo dele — e o corpo cru entregou todos, porque a única autorização no caminho parou no objeto.* Mora no fim do Step de contraste. **Não** repetir no DIFF nem no README. *(Manter distância da âncora do 03 — "which question it answers": a do 03 é sobre um check apontado pro objeto errado; esta é sobre o grão da propriedade. Não colar as frases.)*

### 6. Step — Impact (honesto)
- **Dois impactos reais, nenhum inflado:**
  1. **Recon de schema interno.** A resposta expõe a **forma** do registro server-side — que existe um `is_admin`, que existe um `passwordHash`. Mesmo com `is_admin: false`, o atacante aprende **que o campo existe** e como se chama: material pra montar ataques futuros (mapa do modelo interno). Enquadrar como **information disclosure** (casa do primer).
  2. **Artefato de credencial exposto.** O `passwordHash` é um artefato que **jamais** deveria sair numa resposta. Num sistema real, um hash vazado habilita **offline cracking** (quebra fora do servidor, sem rate-limit). Cravar assim — **"artefato de credencial que nunca devia sair na resposta; num sistema real habilita offline cracking"**.
- **O que o impacto NÃO é (disciplina dura):**
  - **NÃO é escalação.** `is_admin` volta `false`; ninguém vira admin. O vazamento é do **campo** e do **padrão** (objeto inteiro serializado), **não do valor**. **NÃO** sugerir flipar o flag (forward reference a mass assignment — proibido).
  - **NÃO é cracking.** O login é passwordless e o `passwordHash` é dummy — **não há senha real a quebrar**. A prosa **NÃO** pode deslizar pra "e aqui eu quebro a senha" nem pra "o bcrypt tá fraco". A lição é **EXPOSIÇÃO**, não a qualidade do hash.

### 7. Why the fix works (porta 8306)
Apontar o Burp pro `fixed/` em `127.0.0.1:8306` e logar lá (cada build tem o próprio mapa de tokens):
- `GET /users/clancy` (token do `clancy` da 8306) → **`200`**, corpo **`{"handle":"clancy","displayName":"Clancy Park"}`**. *(Rótulo: `GET` · alvo `clancy` (seu) · isola: a allow-list — só os campos públicos voltam.)* Os campos internos (`passwordHash`, `is_admin`) **sumiram** da resposta; a feature (ler o próprio perfil) **continua intacta**.
- **A posse e o `401` não mudaram:** `GET /users/alice` (token do `clancy`) → `403` (igual nos dois gêmeos); sem/ruim token → `401` com `WWW-Authenticate: Bearer`. A única coisa que mudou entre os gêmeos é a linha do `res.json`.
- **O fix é a allow-list (whitelist):** a resposta **nomeia** os campos que podem sair, em vez de espalhar o objeto. **Forward pro DIFF** pro foil whitelist-vs-blacklist (por que nomear o permitido falha fechado, enquanto remover o proibido falha aberto) e pra nota do serializer/DTO.

**O walkthrough TERMINA aqui.** Sem Intruder, sem automação, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5 — termina onde a falha foi mostrada e o fix explicado).

---

## Frases-âncora (uma casa só cada — CLAUDE.md §11 / template)

Nenhuma frase memorável aparece em **dois** documentos. Atribuição fixa:

- **WALKTHROUGH (uma casa):** *"Owning the object was never the same as being cleared for every field on it — and the raw body shipped all of them, because the only authorization in the path stopped at the object."* / *"Ser dono do objeto nunca foi o mesmo que ter liberação pra cada campo dele — e o corpo cru entregou todos, porque a única autorização no caminho parou no objeto."* Mora no fim do Step de contraste.
- **DIFF (uma casa):** *"`...user` serializes the object the store holds; the allow-list serializes the object the caller is cleared to read — BOPLA is the distance between the two."* / *"`...user` serializa o objeto que o store guarda; a allow-list serializa o objeto que o chamador tem liberação de ler — BOPLA é a distância entre os dois."* Mora na seção do fix.
- **Não reusar** as âncoras de 01 ("…it leaks the collection…"; "`404` when existence itself leaks; `403` when admitting existence is fine"), 02 ("…a wall of 404s is 'didn't find'…"; "…the correction changed nothing"), 03 ("Authorization present is not authorization sufficient — what matters is **which question it answers**."; "No information was missing — the question was."), 04 ("The endpoint never cared whose account the target was…"; "The fix adds no check about the target at all…") nem 05 ("One URL answered the read safely and the write wide open…"; "The fix invents nothing: it carries the GET handler's ownership guard onto the PATCH handler…"). **Atenção especial à do 03** ("which question it answers") e à do 05 (o par método+path): as deste átomo são sobre o **grão da propriedade** / "a resposta entrega campo demais" — um corte distinto. Não colar as frases.

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` + `Dockerfile` em **cada** gêmeo, **self-contained, sem módulo compartilhado**; lockfile **commitado** por gêmeo. `app.ts` **difere** só pela linha do `res.json` no `GET /users/:handle` (+ o comentário); todo o resto é idêntico entre as versões.

**Herança de toolchain (CLAUDE.md §3.6) — lida dos arquivos publicados de 01–05 nesta fase (os `Dockerfile` e `tsconfig.json` batem por md5 nos cinco átomos; `package.json` difere só no `name`):**

`tsconfig.json` (copiar — idêntico a 01–05, md5 `9a2dc4f6…`):

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

- **A guarda `!user` é FORÇADA pelo compilador só no `fixed/`** (o `user.displayName` desreferencia); no `vulnerable/`, o spread `...user` de `User | undefined` é no-op aceito → **não** força. O `| undefined` vem da **assinatura do `Map.get`** (independente do `noUncheckedIndexedAccess`, que continua ligado por herança — **validado nesta fase**: desligá-lo não muda o `TS18048`). Manter a guarda **byte-idêntica nos dois gêmeos** como higiene e pra o diff ser só a linha do `res.json`. **Sem `?.` em lugar nenhum** (a guarda de posse é comparação de string; o `!user` é a única desreferência guardada).

`Dockerfile` (idêntico a 01–05 — copiar; base `node:24.21.0-slim`, patch exato, nunca `latest` nem a tag móvel `node:24-slim`; md5 `cad28299…`):

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

`docker-compose.yml` (bind **só** em `127.0.0.1`, portas **8206/8306**):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8206:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8306:3000"
```

- `package.json` de cada gêmeo: `"name": "bopla-excessive-exposure"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Entrypoint `tsx`. **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **Roda como não-root, sem `chown`** — mesma justificativa de 01–05 (validada lá). Reconfirmar no smoke test da Fase 2: build OK, container sobe como `node`, `tsx` sem erro de permissão, endpoints respondendo, imagem só com `express` + `tsx`.

---

## Dependências extras

**Nenhuma dependência nova.** Versões **exatas herdadas** de 01–05 — lidas dos `package.json` publicados (idênticos no corpo nos cinco átomos) e conferidas nos `package-lock.json` commitados (md5 do lock de 05 idêntico entre os gêmeos). **NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

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

- Base `node:24.21.0-slim` (lida dos `Dockerfile`, md5 idêntico nos cinco átomos). Nenhuma divergência.
- Classificação por **runtime**: `tsx` em `dependencies` (entrypoint que executa); `typescript`/`@types/*` em `devDependencies` (build/checagem). `npm audit --omit=dev` cobre exatamente o que a imagem `npm ci --omit=dev` instala e roda (`express` + `tsx`). **Escopo da imagem = escopo do audit = o que roda.**
- `crypto` é **nativo** (`node:crypto`, para `randomBytes` do token) — não é dependência npm. **NÃO adicionar `bcrypt` nem nenhuma lib de hashing** — o `passwordHash` é uma **string dummy literal**, nunca computada nem verificada (o login é passwordless). Trazer `bcrypt` seria sugerir que a qualidade do hash é a lição — e **não é** (ver "A tese"). **Nenhuma lib de serialização/DTO** — a allow-list é um objeto literal de uma linha. Respeita "só inclua a lib se serve à falha ou ao fix" (§3.6).
- **Pin exato travado no `package-lock.json`** (commitado por gêmeo). Updates **manuais** (CLAUDE.md §8.7). Se algo em 01–05 parecer desatualizado, **seguir com o que está lá** — bump é decisão de corte de release, coordenada na série inteira (§3.6), não neste átomo.

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). A casa conceitual da face de leitura de BOPLA (excessive data exposure) na PortSwigger Web Security Academy é a página **Information disclosure** — ela nomeia explicitamente "unnecessarily exposing highly sensitive information" e "data about other users" entre os exemplos de disclosure. **NÃO** é a página de IDOR usada por 01–03, **nem** a de Access control usada por 04–05.

- **Primer (verificado por fetch NESTA fase — HTTP 200, sem redirect; `<title>` "Information disclosure vulnerabilities | Web Security Academy"; H1 "Information disclosure vulnerabilities"; primeira seção "What is information disclosure?"; cobre a exposição de dados sensíveis/de outros usuários no corpo):**
  `https://portswigger.net/web-security/information-disclosure`
  Texto do link: **"Information disclosure vulnerabilities"** — a forma como a PortSwigger apresenta a página (H1), preservada em **inglês** também no README PT (CLAUDE.md §7). *(Nota: o átomo web `debug-enabled` linka a mesma URL com o texto curto "Information disclosure"; aqui usamos o H1 completo por consistência com o precedente da série API — 04/05 também linkam suas páginas pelo H1 completo ("Access control vulnerabilities and privilege escalation"). Divergência deliberada do átomo web, ratificada pelo mantenedor; ambos apontam pra mesma página.)*

Formato exato EN:

```markdown
> **Theory primer:** Read [PortSwigger: Information disclosure vulnerabilities](https://portswigger.net/web-security/information-disclosure)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato exato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: Information disclosure vulnerabilities](https://portswigger.net/web-security/information-disclosure)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

**OWASP: sem link inline.** Os docs citam `API3:2023` em texto simples; o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (conferido: a linha **API3** já existe, apontando `bopla-excessive-exposure` e `bopla-mass-assignment`).

**Fase 2 (geração):** **re-confirmar a URL do primer por fetch** (200, sem redirect) antes de cravar. **Se a página não encaixar com a face de leitura (excessive data exposure), PARAR e perguntar ao mantenedor** — não substituir por conta própria.

---

## Política de cross-ref (CLAUDE.md §5)

Publicação verificada **lendo `atoms/api/ROADMAP.md` e a árvore de `atoms/` NESTA fase**, não de memória: na série API, **01, 02, 03, 04 e 05 estão publicados** (`[x]`, pastas completas); **07 em diante não** (06 é este; 07 `bopla-mass-assignment` em diante é Fase 2, **não publicada**).

- **`bfla-method-based` (05) — herança direta e contraste central.** Reusa a superfície `/users/:handle`, o `Map<string, User>`, a guarda de posse (byte-idêntica), o bloco de auth, o argumento `403`/RFC 9110. Contraste: 05 = eixo do **método** (BFLA; a assimetria **entre** `GET` e `PATCH`); 06 = eixo da **propriedade** (BOPLA; a assimetria **dentro** do `GET`). A **inversão de papel do `GET`** (lá prova-viva, aqui vulnerável) é material. Creditar o argumento de status **referenciando** o DIFF do 05, não recontando.
- **`bfla-admin-function` (04) — precedente do `Map<string, User>` e do flag `is_admin`.** Aqui `is_admin` reaparece como **campo vazado** (ambos `false`), não como lição. Creditar o `Map`/forma de store.
- **`bola-sequential-id` (01), `bola-uuid-leaked` (02), `bola-nested-resource` (03) — origem do check de posse** (`order.owner === caller` → `handle === caller`) que este átomo **mantém e faz passar** na self-read, pra provar que a object-level authorization **não é** a falha. Creditar a posse como o que **afasta** o BOLA.
- **Átomo web `crypto-weak-hash` (A02) — contraste no Step de contraste.** Publicado (conferido: `atoms/web/A02-cryptographic-failures/crypto-weak-hash/`). O 06 **desarma** a leitura "isto é crypto fraco": a lição é o hash **estar** na resposta, não a qualidade dele. **Citar por nome é permitido** (publicado), mas **com disciplina** — o contraste é "exposição ≠ qualidade do hash", não um convite a estudar crypto aqui.
- **PROIBIDO citar qualquer átomo de API NÃO publicado** (07 em diante: `bopla-mass-assignment`, `auth-*`, etc.) — por nome, número ou descrição. **Em particular, NÃO antecipar a FACE DE ESCRITA de BOPLA (mass assignment)** nem sugerir que **escrever** um campo (ex.: flipar `is_admin`) seria o próximo passo. A face de escrita é **fora de escopo** deste átomo. Forward reference (CLAUDE.md §5). Verificado: só 01–05 (API) publicados.
- **Átomo web `mass-assignment` (A01) — NÃO citar como "a outra face".** Embora publicado na série web, citá-lo aqui reabriria a antecipação da face de escrita que a disciplina proíbe. **Não** referenciar.
- Termos técnicos em inglês no PT (BOPLA, BOLA, BFLA, excessive data exposure, property-level authorization, object-level authorization, allow-list, whitelist, blacklist, deny-list, serializer, DTO, information disclosure, offline cracking, token, Bearer, ownership check, Trigger, payload).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API3 — Broken Object Property Level Authorization** | Primeiro átomo da categoria. A autorização falha no grão da **propriedade**: o chamador pode ler o objeto, mas a resposta devolve campos que ele não pode ver. |
| Pasta | **`API3-broken-object-property-level-authz/` (NOVA, greenfield)** | Primeira pasta da categoria; o 06 a cria (diferente do 05, que caiu numa pasta já existente). |
| Nome / classe (H1) | **Broken Object Property Level Authorization (BOPLA)** — idêntico EN/PT | Título nomeia a classe; o slug (`bopla-excessive-exposure`) qualifica a variante (face de leitura). |
| Face de BOPLA | **Leitura (excessive data exposure)** | A resposta entrega propriedades demais. A face de escrita (mass assignment) é fora de escopo — não citar nem antecipar. |
| A tese | **Autorização se aplica no nível da propriedade, não só do objeto/função** | O dev autorizou o objeto (a posse) e serializou o objeto inteiro, vazando os campos internos. |
| Cenário | **Self-read: `clancy` lê o próprio registro** | Isolamento máximo do BOLA — ele lê o objeto dele, então "li objeto de outro" não se aplica; só sobra property-level. |
| A superfície atacada | **`GET /users/:handle`** (vuln); só ele + `POST /login` | Reusa a superfície do 05; inverte o papel do `GET` (lá prova-viva, aqui vulnerável). |
| Superfície | **Duas rotas** (`POST /login`, `GET /users/:handle`) | SEM `PATCH` (escrita fora de escopo), sem listagem, sem `GET /me`, sem índice. Mais simples que o 05. |
| Guarda de posse | **`if (req.params.handle !== caller) return res.sendStatus(403);` — byte-idêntica à do 05, presente e PASSA na self-read** | Não é a falha; é o que afasta o BOLA e dá o `403` do contraste. |
| Serialização vulnerável | **`res.json({ handle: req.params.handle, ...user })`** | Spread do objeto inteiro vaza `passwordHash` + `is_admin`. `handle` é a chave do `Map`, não campo de `User`. |
| Store | **`Map<string, User>`, `User = { displayName, passwordHash, is_admin }`** | Herança estrutural de 04/05. `Map.get` tipa `User \| undefined` (guarda `!user` type-forced no `fixed/`). **NÃO** é defesa de prototype pollution aqui (só há leitura; posse precede o lookup). |
| Seed | **`clancy` e `alice`, AMBOS `is_admin: false`, SEM admin** | `clancy` lê o próprio; `alice` existe só pra sustentar o `403` do contraste. Sem admin: o vazamento é do campo/padrão, não do valor `true`. |
| `passwordHash` | **String dummy bcrypt-shaped (60 chars), nunca computada/verificada** | Artefato de credencial realista stored-side; login é passwordless, não a lê. Dummy gritante (CLAUDE.md §8.3). |
| `is_admin` | **Somente-leitura; snake_case por continuidade com o 04** | O walkthrough mostra o flag voltando; NÃO sugere flipá-lo (forward ref proibida). Grafia é cosmética, não lição. |
| Token | **Opaco, `crypto.randomBytes`; NÃO JWT** — idêntico a 01–05 | Cripto-forte pra não ser 2ª vuln. O ataque não toca o token. |
| Fix (eixo único) | **Allow-list: `res.json({ handle: req.params.handle, displayName: user.displayName })`, byte-idêntica à resposta do `GET` do 05** | Estende a autorização ao grão do campo: nomeia o que pode sair. Diff de uma linha. |
| Blacklist | **FOIL descartado no DIFF, NÃO o fix** | `const { passwordHash, is_admin, ...safe } = user` funciona hoje mas falha ABERTO (campo novo vaza sozinho); whitelist falha FECHADO. Validado por foil. |
| DTO/serializer | **Generalizar em 1–2 frases no DIFF; NÃO importar maquinaria** | Em escala a projeção vira um serializer/DTO compartilhado; trazê-lo quebraria o diff de uma linha. |
| Status code | **`200` self; `403` alheio (token clancy); `401` sem/ruim token; `404` do `!user` inalcançável** | Herança pura do 05 (posse por identidade antes da busca → `403`, sem enumeration). Referenciar o 05, não recontar. Mais simples que o 05 (sem `404` alcançável). |
| Corpo dos erros — `sendStatus` | **`res.sendStatus(...)` (401/403/404); sucesso via `res.json(...)`** | Igual a 01–05. |
| Estado | **Imutável; só leitura; sem undo** | Nenhuma escrita. Toda request idempotente/determinística. Gêmeos independentes. |
| Padrão de prova | **Trigger** (não Payload); **auto-contida** (baseline = exploit) | Não há sink; o exploit é ler o próprio perfil e inspecionar o raw. A prova está no corpo da própria resposta — sem segundo ator (contraste honesto com o 05). → passo de contraste obrigatório. |
| Passo de contraste | **(1) GET alice → 403 (não é BOLA); (2) não é crypto fraco; (3) controle no cliente ≠ controle (princípio)** | (1) usa 1 request novo; (2) e (3) usam a resposta já obtida. (3) como PRINCÍPIO — não há UI; se não couber em 1 frase, cortar. |
| Trilha | **100% Burp (Repeater) / curl; SEM Intruder; SEM browser** | API-only (CLAUDE.md §3.3). A tese não é escala/enumeração. |
| Impacto | **Recon de schema interno + artefato de credencial exposto; information disclosure** | Honesto: NÃO é escalação (`is_admin` false, não flipar), NÃO é cracking (login passwordless, hash dummy). A lição é EXPOSIÇÃO, não a qualidade do hash. |
| Theory primer | **PortSwigger Information disclosure** (`/web-security/information-disclosure`) | Casa da excessive data exposure. **Diferente** de IDOR (01–03) e Access control (04–05). URL verificada por fetch nesta fase (200, sem redirect). |
| Cross-ref | **05 central (propriedade vs método; inversão do GET); 04 (Map/is_admin); 01–03 (posse); web `crypto-weak-hash` (contraste); nenhum átomo de API 07+** | 01–05 (API) publicados. 07+ não-publicados → proibido, inclusive antecipar a face de escrita (mass assignment). |

---

## Decisões que podem gerar dúvida durante implementação

- **Membership no `POST /login` — `USERS.has(user)`.** Com `USERS` sendo `Map<string, User>`, é a mesma forma de 04/05 (Set e Map compartilham `.has`). `req.body?.user` é `any` → `Map.has(any)` aceita. **Validado nesta fase:** `tsc --noEmit` limpo (exit 0) nos dois gêmeos.
- **Guarda `!user`: forçada só no `fixed/`.** `USERS.get(req.params.handle)` é `User | undefined`. No `fixed/`, `user.displayName` força a guarda (sem ela, `TS18048`). No `vulnerable/`, `...user` espalha `User | undefined` — **no-op aceito** pelo TS, guarda **não** forçada. Manter byte-idêntica nos dois (higiene + diff limpo). **Validado nesta fase** (ver "Validação"). Inalcançável em runtime nos dois (posse garante handle seedado).
- **`handle` é a chave do `Map`, não campo de `User`.** `{ handle: ..., ...user }` não colide (`User` não tem `handle`). O `handle` sai explícito; o `...user` traz `displayName`/`passwordHash`/`is_admin`. **Validado** no corpo runtime.
- **Spread de `undefined` em runtime** (caso hipotético, inalcançável): `{ handle: "x", ...undefined }` é `{ handle: "x" }` em JS (spread de `undefined` é no-op, não lança). Não é um caminho atingível (posse barra), mas registrar que não quebraria.
- **`passwordHash` é LITERAL, não computado.** Não importar `bcrypt`, não chamar hashing. A string tem **forma** bcrypt (60 chars, `$2b$12$…`) e conteúdo gritantemente dummy. **Validado:** comprimento 60, charset ok.
- **`Map`, não `Record` — mas sem narrativa de prototype pollution.** Só há leitura, e a posse precede o lookup; `__proto__`/`constructor` batem `403` antes do `USERS.get`. **Validado:** `GET /users/__proto__` → `403`. **NÃO** escrever prosa de prototype pollution neste átomo (seria falsa) — o `Map` é continuidade estrutural + typing.
- **Tipos do Express 5 — retorno `Response` vs `void`.** Igual a 01–05: callbacks sem anotação de retorno, onde `return res.sendStatus(...)` passa. Se anotar o retorno, usar `res.sendStatus(...); return;`. Não anotar é o caminho da série.
- **Corpo só no `POST /login`** (o `GET` não tem corpo). `app.use(express.json())` fica (idêntico a 01–05, não remover).

---

## Validação de typecheck e runtime (feita NESTA fase de planning)

Montei um protótipo descartável fora do repo (scratchpad da sessão) com o **toolchain EXATO** herdado de 01–05 (`npm ci` do `package.json`/`package-lock.json` do 05 — express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; node 24.21.0) e o `tsconfig.json` da série (byte a byte), reconstruí os **dois gêmeos** a partir dos samples desta spec, e rodei `tsc --noEmit` + exercitei os endpoints com `tsx`. Observado (não raciocinado):

**Typecheck (`tsc` 7.0.2):**

| Teste | Resultado observado |
|---|---|
| `vulnerable/app.ts` (Map; posse no `GET`; `res.json({ handle, ...user })`) | **exit 0**, limpo |
| `fixed/app.ts` (Map; `res.json({ handle, displayName: user.displayName })`) | **exit 0**, limpo |
| **[prova negativa]** remover `!user` do **vulnerable** (`...user`) | **exit 0** — espalhar `User \| undefined` é no-op aceito; guarda **NÃO** forçada |
| **[prova negativa]** remover `!user` do **fixed** (`user.displayName`) | **`TS18048: 'user' is possibly 'undefined'`** — guarda forçada |
| **[flag]** fixed-sem-guarda com `noUncheckedIndexedAccess: false` | **`TS18048` persiste** — o `\| undefined` vem da assinatura do `Map.get`, não do flag |
| whitelist/blacklist/spread foil (`tsc --noEmit`) | **exit 0** |

**Runtime — comportamento dos endpoints** (servidores `tsx` nas portas 8206/8306, token do `clancy`):

| Request | vulnerable (8206) | fixed (8306) |
|---|---|---|
| `GET /users/clancy` (self) | `200` `{"handle":"clancy","displayName":"Clancy Park","passwordHash":"$2b$12$DUMMY…CLANCY","is_admin":false}` | `200` `{"handle":"clancy","displayName":"Clancy Park"}` |
| `GET /users/clancy` (re-run) | `200`, **corpo idêntico** | `200`, **corpo idêntico** |
| `GET /users/alice` (token clancy) | **`403`** | **`403`** |
| `GET /users/alice` (token alice) | `200` **com** `passwordHash`+`is_admin` | `200` `{"handle":"alice","displayName":"Alice Nguyen"}` |
| `GET /users/nobody` (token clancy) | **`403`** (posse antes do lookup; o `404` não alcança) | **`403`** |
| `GET /users/__proto__` / `/constructor` | **`403`** | **`403`** |
| `GET /users/clancy` sem token | `401` + `WWW-Authenticate: Bearer` | `401` + `WWW-Authenticate: Bearer` |
| `GET /users/clancy` token ruim | `401` + `WWW-Authenticate: Bearer` | `401` + `WWW-Authenticate: Bearer` |
| `PATCH /users/clancy` / `GET /users` / `GET /me` | `404` (rota inexistente — superfície é só login+GET) | `404` |
| `POST /login` usuário desconhecido | `400` | `400` |

- **Tokens:** `clancy` e `alice` recebem tokens distintos e cripto-fortes (base64url, 32 chars). Login confirmado nos dois gêmeos.

**Runtime — foil whitelist vs blacklist vs spread** (campo novo `internalNote` acrescentado ao `User`, como "amanhã alguém adiciona um campo sensível"):

| Projeção | hoje (3 campos) | amanhã (+`internalNote`) |
|---|---|---|
| **spread** (`...user`) — o vulnerable | vaza `passwordHash`+`is_admin` | **vaza também** `internalNote` |
| **blacklist** (`const {passwordHash,is_admin,...safe}=user`) — descartado | limpo | **vaza** `internalNote` (**fails open**) |
| **whitelist** (`{displayName}`) — o fix | limpo | **continua limpo** (**fails closed**) |

- **`passwordHash` dummy:** comprimento **60**, forma `$2b$12$` + 22 (salt) + 31 (hash), charset `[./A-Za-z0-9]` — bcrypt-shaped sem ser real. **Verificado.**
- **Byte-identidade do fix:** a linha `res.json({ handle: req.params.handle, displayName: user.displayName });` do `fixed/` é **byte-idêntica** à linha de resposta do `GET` do 05 (`grep -Fxc` = 1 em ambos). **Verificado.**
- **Conclusões cravadas:** os dois gêmeos saem exit 0; a guarda `!user` é type-forced só no `fixed/` (mantida como higiene nos dois, inalcançável em runtime); o `Map` **não** é defesa de prototype pollution aqui (leitura-só, posse antes do lookup → `__proto__`/`constructor` dão `403`); a prova é **auto-contida** (o vazamento está no corpo da self-read do `clancy`); whitelist falha fechado, blacklist falha aberto (foil). A Fase 2 ainda roda `npm run typecheck` nos dois gêmeos como gate oficial (host/CI) e um smoke test completo.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia `usuário→token`, Bearer resolve de volta; `clancy`/`alice` recebem tokens distintos e cripto-fortes (`randomBytes`). Bloco de auth byte a byte o de 01–05; `USERS` é `Map<string, User>` com `User = { displayName, passwordHash, is_admin }`; membership segue `USERS.has(user)`.
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido → **`401`** com `WWW-Authenticate: Bearer`, nas duas versões.
3. **Vulnerable — BOPLA (a prova auto-contida):** `GET /users/clancy` com o token do **`clancy`** → **`200`** com `passwordHash` **e** `is_admin` no corpo, ao lado de `displayName`. O vazamento está na self-read; **sem segundo ator**.
4. **Posse presente e correta (afasta o BOLA):** `GET /users/alice` com o token do **`clancy`** → **`403`** nos dois gêmeos. O chamador **não** lê o objeto da alice; a object-level authorization morde.
5. **Fixed — allow-list:** `GET /users/clancy` com o token do `clancy` → **`200`** com **só** `{"handle":"clancy","displayName":"Clancy Park"}`. `passwordHash` e `is_admin` **sumiram**. Feature intacta.
6. **Fixed — posse e 401 inalterados:** `GET /users/alice` (token clancy) → `403`; sem/ruim token → `401` + challenge. Iguais ao vulnerable.
7. **`404` do `!user` inalcançável:** `GET /users/nobody` (token válido) → **`403`** (posse barra antes do lookup), **não** `404`, nos dois gêmeos. `GET /users/__proto__` / `/constructor` → `403`. **Se der `404` ou `200`, a ordem da guarda está errada — PARE.**
8. **`app.ts` DIFERE só pela linha do `res.json`** (`{ handle, ...user }` → `{ handle, displayName: user.displayName }`) + o comentário, no `GET /users/:handle`. `POST /login`, a guarda de posse, o `!user`, helpers, imports, `USERS`, rodapé, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` **idênticos** entre as versões.
9. **A linha do fix é byte-idêntica à resposta do `GET` do 05** (`res.json({ handle: req.params.handle, displayName: user.displayName });`). Conferir com `grep -Fxc`.
10. **`passwordHash` é dummy gritante, bcrypt-shaped, literal** (60 chars, `$2b$12$…`, conteúdo "DUMMY…NOTaREALpassword…"). **Sem `bcrypt`**, sem hashing, sem verificação (login passwordless). **Nenhuma credencial real.**
11. **`is_admin` ambos `false`, snake_case, somente-leitura.** O walkthrough mostra o flag **voltando**; **NÃO** sugere flipá-lo, **NÃO** antecipa escrita. Sem admin no seed.
12. **Resposta não vaza token:** nenhuma resposta serializa token. O vazamento é dos campos internos do perfil. **Um bug só** (BOPLA, face de leitura).
13. **Superfície mínima:** só `POST /login` e `GET /users/:handle`. **Sem** `PATCH`, **sem** listagem, **sem** `GET /me`, **sem** índice de rotas.
14. **Estado imutável:** nenhuma escrita; toda request idempotente. Gêmeos independentes (8206 ↔ 8306). README declara o restart (tokens em memória) na única casa (sem repetir em WALKTHROUGH/DIFF).
15. **API-only:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, sem render de HTML; sucesso sempre `application/json`.
16. **Bind/portas:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1`; container `ENV HOST=0.0.0.0`. **Portas 8206 (vulnerable) / 8306 (fixed)**, internas `3000`, coerentes entre `EXPOSE`, `app.listen` e o compose.
17. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README. (`clancy` masculino no PT; coincide com o masculino do papel.)
18. **README declara os atalhos** (EN+PT, sem citar átomo): login passwordless é atalho de laboratório; `passwordHash` é dummy stored-side não usado pelo login, não é credencial real.
19. **Theory primer:** re-confirmar por fetch `https://portswigger.net/web-security/information-disclosure` (200, sem redirect); texto do link "Information disclosure vulnerabilities", em inglês no PT. **Confirmar que NÃO é a página de IDOR (01–03) nem a de Access control (04–05).** Se a página não encaixar com a face de leitura, **PARAR e perguntar**.
20. **RFC 9110** referenciado **via DIFF do 05**, não recontado: **§15.5.4 (403 Forbidden)** (credencial presente, insuficiente; `404` como `MAY`) e **§15.5.2 (401 Unauthorized)** (`WWW-Authenticate` obrigatório). Texto bruto conferido nesta fase em `rfc-editor.org/rfc/rfc9110.txt`; **reconfirmar na geração** se for citar diretamente.
21. **`npm audit --omit=dev` em cada gêmeo**, advisories esperados **registrados**. O átomo é vulnerável na **LÓGICA** (serialização sem filtro), **não nas dependências** (idênticas a 01–05). Meta: zero advisory de runtime.
22. **`npm run typecheck` (`tsc --noEmit`, typescript 7.0.2) verde nos DOIS gêmeos** — inclusive o `vulnerable/`. Gate de **host/CI**, não do container. **Shape validado nesta fase** (ver "Validação").
23. **Frases-âncora:** cada uma numa casa só (WALKTHROUGH: objeto vs campo; DIFF: `...user` vs allow-list, "BOPLA é a distância entre os dois"); **não** reusar as âncoras de 01–05 — em especial, manter distância da de 03 ("which question it answers") e das do 05.
24. **Rótulo em todo bloco do WALKTHROUGH** (EN e PT): método · alvo · o que isola. A prosa **nomeia e desarma** as leituras erradas: **duas firmes** ("é BOLA", "é crypto fraco") e **uma terceira** ("controle no cliente é controle") **como princípio, cortável** se não couber em uma frase limpa (não há UI).
25. **Cross-ref:** 05 central (propriedade vs método; inversão do `GET`); 04 (Map/`is_admin`); 01–03 (posse); web `crypto-weak-hash` (contraste exposição≠qualidade); **nenhum** átomo de API 07+; **nenhuma** antecipação da face de escrita (mass assignment), inclusive **não** citar o web `mass-assignment`.
26. **Impacto honesto:** recon de schema interno + artefato de credencial exposto (information disclosure; offline cracking num sistema real). **NÃO** escalação (`is_admin` false, não flipar), **NÃO** cracking aqui (passwordless, hash dummy). A prosa **não** desliza pra "bcrypt fraco" nem "quebro a senha".

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; toolchain herdado e lido dos arquivos de 01–05; URL do primer verificada por fetch (200, sem redirect) e seções do RFC 9110 conferidas em texto bruto nesta fase; shape TS, comportamento dos endpoints e o foil whitelist-vs-blacklist validados em protótipo com o toolchain exato (ver "Validação de typecheck e runtime"). Resto é smoke test na Fase 2.

---

## Notas específicas pro Claude Code

- **Princípio guia:** a lição é **autorização se aplica no nível da propriedade, não só do objeto**. Cada doc deve manter o eixo do **campo** visível: a posse do objeto está certa e passa, e **ainda assim** a resposta vaza propriedades internas. Se o aluno sair achando "li o objeto de outro" (BOLA) ou "o bcrypt tá fraco" (crypto), o átomo falhou.
- **Self-read é a disciplina.** O `clancy` lê o **próprio** registro. **Nunca** escrever a prosa como se ele lesse o de outro — isso é BOLA, e o átomo existe pra isolar o contrário. O `403` de `GET /users/alice` é o que crava "não é BOLA".
- **A inversão do `GET` do 05 é material.** Lá o `GET` era a prova-viva do check correto; aqui o **mesmo** `GET` é o vulnerável (mesma guarda em cima, falha nova embaixo). Cravar o contraste.
- **UM handler, assimetria interna.** Mostrar **um** `GET` (não dois lado a lado como o 05). A lição é a linha do `res.json`. **NÃO** inventar segundo handler nem filtro condicional.
- **Fix = allow-list (whitelist), byte-idêntica à resposta do `GET` do 05.** `res.json({ handle: req.params.handle, displayName: user.displayName })`. **NÃO** usar blacklist como fix — ela é FOIL no DIFF (falha aberto). Dizer por que whitelist falha fechado faz parte da lição.
- **`passwordHash` é EXPOSIÇÃO, não crypto.** Enquadrar como artefato de credencial que jamais devia sair; num sistema real habilita offline cracking. **NUNCA** "e aqui eu quebro a senha" nem "o hash tá fraco". A prosa não pode deslizar pra a classe de crypto.
- **`is_admin` é somente-leitura, ambos `false`.** O vazamento é do **campo e do padrão**, não do valor. **NÃO** sugerir flipar o flag; **NÃO** antecipar a face de escrita (mass assignment). Se a geração sentir vontade de escrever um campo, **PARE**.
- **`Map`, mas SEM prototype pollution na prosa.** Só há leitura; a posse precede o lookup. O `Map` é continuidade estrutural + typing (`User | undefined`). Afirmar defesa de prototype pollution aqui seria **falso** — não fazer.
- **Status `403`/`401`: herança pura do 05.** **Referenciar** o DIFF do 05 pro argumento (RFC 9110, critério da série), **não recontar**. O `404` do `!user` é higiene inalcançável.
- **Prova auto-contida (contraste com o 05).** A prova está no corpo da self-read do `clancy` — **sem segundo ator**. No 05 a prova precisou da vítima; aqui não. Cravar a diferença, com honestidade.
- **Elenco:** `clancy` atacante **masculino** (concordância coincide com a do papel); `alice` só sustenta o `403` do contraste (nunca lida com sucesso). Reuso do elenco; sem personagem novo; **sem admin**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# bopla-excessive-exposure — Broken Object Property Level Authorization (BOPLA)`. Headers de seção **traduzidos** no PT; termos técnicos em inglês.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série. Este átomo **abre a Fase 2 API**; o corte da release `v1.2` é trabalho de mantenedor, pós-merge (CLAUDE.md §12), fora do escopo da geração do átomo.
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 06 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): todos os itens do checklist acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8206` (vulnerable), `127.0.0.1:8306` (fixed). Bind **só** em `127.0.0.1`.

---

## Verificação factual dos átomos publicados (conferida LENDO os arquivos nesta fase)

A spec afirma herança e contraste com 01–05; tudo abaixo foi conferido **lendo os arquivos publicados nesta fase de planning** (não de memória):

1. **Toolchain** — `package.json` dos cinco átomos com express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; scripts `start: tsx app.ts`, `typecheck: tsc --noEmit`; `name` por átomo, `private: true`, `type: module`. (`package.json` difere entre átomos só no `name` — md5 distinto por isso; dentro de um átomo, vulnerable e fixed têm `package.json` idêntico.)
2. **`Dockerfile`** — **md5 idêntico nos cinco** átomos (`cad28299…`): `node:24.21.0-slim`, `npm ci --omit=dev`, `COPY tsconfig.json` + `COPY app.ts`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm","start"]`.
3. **`tsconfig.json`** — **md5 idêntico nos cinco** (`9a2dc4f6…`): `nodenext`, `target/lib es2024`, `types [node]`, `strict`, `noUncheckedIndexedAccess`, `esModuleInterop`, `noEmit`.
4. **`docker-compose.yml`** — bind `127.0.0.1`; `8201/8301` (01), `8202/8302` (02), `8203/8303` (03), `8204/8304` (04), `8205/8305` (05). Este átomo: `8206/8306`.
5. **Bloco de auth** — `TOKENS = new Map<string,string>`, `issueToken` com `randomBytes(24).toString("base64url")`, `authenticate` por `Bearer`, `USERS.has(user)` no login, `res.set("WWW-Authenticate", "Bearer").sendStatus(401)` nos handlers. 01–03 têm `USERS = new Set([...])`; **04 e 05 usam `USERS = new Map<string, User>`** (`User = { is_admin }` no 04; `User = { displayName }` no 05) — este átomo segue a forma do 05 ampliada (`User = { displayName, passwordHash, is_admin }`).
6. **Átomo 05 (`bfla-method-based`)** — superfície `POST /login`, `GET /users/:handle` (guarda de posse `if (req.params.handle !== caller) return res.sendStatus(403);`, resposta `res.json({ handle: req.params.handle, displayName: user.displayName });`), `PATCH /users/:handle` (o vulnerável lá). Fix do 05 acrescenta a guarda de posse ao `PATCH`. **Este átomo reusa o `GET` do 05 e o torna vulnerável** (serializa `...user` em vez da allow-list); o fix do 06 **restaura exatamente** a linha de resposta do `GET` do 05 (byte-idêntica, conferido por `grep -Fxc`).
7. **Átomo 04 (`bfla-admin-function`)** — `USERS = new Map<string, User>` com `User = { is_admin: boolean }`, flag em snake_case; `carol` é a única admin; fix `if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);`. Este átomo herda a forma do `Map` e reusa `is_admin` como **campo vazado** (ambos `false`), não como lição.
8. **Status de 01–05** — 01/03 devolvem `404` indistinguível pro pedido (oráculo de enumeração sobre id); 02 herda o `404`; 03 dá `403` pra loja; 04 dá `403` pra função conhecida; 05 dá `403` pra posse checada por identidade antes da busca. O DIFF do 05 ancora o `403` em RFC 9110 §15.5.4 e no critério da série — **este átomo referencia o 05**.
9. **Elenco** — `clancy` é o atacante (masculino) em código e docs; `alice` é a vítima/vítima-principal em todos. `carol` admin no 04; `bob`/`carol` operadores no 03. Este átomo usa `clancy` (lê o próprio) e `alice` (só sustenta o `403` do contraste), **sem admin**.
10. **H1** — 01–03: `# <id> — Broken Object Level Authorization (BOLA)`; 04/05: `# <id> — Broken Function Level Authorization (BFLA)`. Este: `# bopla-excessive-exposure — Broken Object Property Level Authorization (BOPLA)`, idêntico EN/PT — **primeiro BOPLA da série**.
11. **Primer** — 01–03 usam PortSwigger **IDOR** (`/web-security/access-control/idor`); 04–05 usam **Access control** (`/web-security/access-control`); o web `debug-enabled` usa **Information disclosure** (`/web-security/information-disclosure`, texto curto "Information disclosure"). Este átomo usa **Information disclosure** com o texto do H1 completo ("Information disclosure vulnerabilities"); verificada por fetch nesta fase (200, sem redirect). `APIX:2023` em texto simples, sem link OWASP nos docs; link canônico na tabela de Cobertura do ROADMAP (a linha **API3 já existe**, apontando os dois `bopla-*`).
12. **Átomo web `crypto-weak-hash`** — publicado em `atoms/web/A02-cryptographic-failures/crypto-weak-hash/`; armazena senha como MD5 unsalted (vulnerable) e bcrypt salgado (fixed); a lição dele é a **qualidade do primitivo de hash**. Este átomo **contrasta** com ele (exposição ≠ qualidade do hash), sem reabrir a classe de crypto.
13. **Publicação** — `atoms/api/ROADMAP.md`: 01–05 `[x]`, 06 (`bopla-excessive-exposure`) `[ ]`, 07+ `[ ]`. Árvore de `atoms/api/`: existem `API1-broken-object-level-authz/` (três átomos) e `API5-broken-function-level-authz/` (dois átomos) — **nenhuma** pasta `API3-*` ainda (este átomo a cria). A linha API3 da tabela de Cobertura do ROADMAP já lista `bopla-excessive-exposure` e `bopla-mass-assignment`.
