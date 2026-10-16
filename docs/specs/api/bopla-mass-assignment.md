# Spec — Átomo API 07: `bopla-mass-assignment`

> Documento de especificação para o Claude Code implementar o **sétimo átomo da série API** do projeto `atomicvulns` (Fase 2 API, "Property Authz & Auth", milestone `v1.2`; **segundo átomo da fase**). Classe: **BOPLA — Broken Object Property Level Authorization**, o **API3:2023** do OWASP API Security Top 10 (2023) — categoria **já aberta** pelo 06: a pasta `API3-broken-object-property-level-authz/` **já existe** e este átomo apenas entra nela (diferente do 06, que a criou). Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **A face de escrita de BOPLA.** O 06 ensinou a **face de leitura**: a resposta devolvia campos que o chamador não pode ver. Este átomo é a **mesma raiz, direção oposta** — a requisição **escreve** campos que o chamador não pode setar. É o que a indústria chama de *mass assignment* (ou *auto-binding*). A pergunta de auditoria cravada, simétrica à do 06: **"o write é escopado aos campos que este chamador pode setar?"** No 06 o pecado era espalhar o registro **na resposta** (`...user` saindo); aqui é espalhar o body **no registro** (`...req.body` entrando). Mesma raiz — **confiar no objeto inteiro** —, duas direções: é exatamente por isso que a OWASP fundiu leitura e escrita numa categoria só em 2023. Tudo o que esta spec afirma sobre os átomos 01–06 foi conferido **lendo os arquivos publicados em `main`**, não de memória (ver "Verificação factual dos átomos publicados").
>
> **O CENÁRIO É SELF-UPDATE — e isso é a disciplina (herdada do 06).** `clancy` faz `PATCH /users/clancy`: escreve no **próprio** registro, autorizado no nível do objeto **porque o registro é dele**. É o **isolamento máximo** do BOLA — ele escreve no objeto **dele**, então "escrevi no objeto de outro = BOLA" simplesmente **não se aplica**; a única coisa errada que sobra vive no grão da **propriedade**. A guarda de posse do 05/06 continua lá, **byte-idêntica**, e **passa** no self-update. A falha nova vive **uma linha abaixo**, no write.
>
> **A PROVA NÃO É O ECO — e isso está cravado na ARQUITETURA.** O `PATCH` responde **`204 No Content`** nos **dois** gêmeos: corpo vazio, nada a ecoar. Essa é a lição mais cara da Fase 1 (o `200`/eco do `PATCH` do 05 **não** provava a escrita) promovida a **status code**: aqui não existe eco possível, então a prova é **obrigada** a ir pro **termômetro** — `GET /admin/users`, uma rota admin-only, **corretamente guardada**, que responde `403` antes do ataque e `200` depois. O write não diz nada; quem fala é o estado lido por outro caminho.
>
> **DISCIPLINA ANTI-04 (requisito de redação DURO).** O termômetro **tem** check de role e ele **está correto** — é a linha do **fix do 04**, byte-idêntica. O `403` inicial **prova** que a função está guardada. O bug **não é** função desprotegida (isso é o 04); é o **papel forjado** que a função legitimamente confere. Cravar em todo documento: *a guarda que você vê está certa; o breach está a montante, no `PATCH`.* Se o aluno sair achando "invoquei uma rota admin" ou "a rota admin é fraca", **o átomo falhou**.
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **`atoms/api/API3-broken-object-property-level-authz/bopla-excessive-exposure/`, inteiro** — o **par direto** deste átomo (a face de leitura). Herança: a superfície `/users/:handle`, o `Map<string, User>`, a guarda de posse, o flag `is_admin`, a forma dos seis documentos e o eixo único do diff (uma linha + comentário). A **simetria leitura↔escrita** é material deste átomo; a **lição do 06 não se reabre**.
> 2. **`atoms/api/API5-broken-function-level-authz/bfla-method-based/`, inteiro** — a origem do `PATCH /users/:handle`, do bloco de auth e do argumento `403`/RFC 9110. **Conferir o que o `PATCH` do 05 responde** (`200` + corpo, eco do input): o `204` deste átomo é **divergência deliberada**, creditada como tal.
> 3. **`atoms/api/API5-broken-function-level-authz/bfla-admin-function/`, inteiro** — a rota admin e o check de role. A **disciplina anti-04 depende de ler como o 04 fez**: lá a função **não tinha** o check (e o fix o acrescentou); aqui a função **tem** o check, ele funciona, e mesmo assim o atacante entra.
> 4. **`atoms/api/API1-broken-object-level-authz/bola-sequential-id/`, `bola-uuid-leaked/`, `bola-nested-resource/`, inteiros** — a **origem do check de posse** (`order.owner === caller` → `handle === caller`) que este átomo **mantém e faz passar** no self-update.
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`). A validação em protótipo descartável foi feita **nesta fase** (ver "Validação de typecheck e runtime").

---

## Identidade

- **ID:** `bopla-mass-assignment`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API3 — Broken Object Property Level Authorization**
- **Pasta:** `atoms/api/API3-broken-object-property-level-authz/bopla-mass-assignment/` — a pasta de categoria **JÁ EXISTE** (criada pelo 06). Este é o **segundo** átomo dela; **não** criar pasta de categoria nova.
- **Número sequencial (série API, conta do 01):** 07
- **Porta vulnerable:** `127.0.0.1:8207`
- **Porta fixed:** `127.0.0.1:8307`
- **Porta interna do container:** `3000` (igual a 01–06). Compose mapeia `127.0.0.1:8207:3000` e `127.0.0.1:8307:3000`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1); `ENV HOST=0.0.0.0` só dentro do container.
- **Fase / milestone:** Fase 2 API, `v1.2` (sétimo átomo; segundo da fase).
- **Branch de trabalho:** `atom/bopla-mass-assignment` — criada na Fase 2 a partir de `main` atualizada.
- **H1 dos READMEs (idêntico em EN e PT):** `# bopla-mass-assignment — Broken Object Property Level Authorization (BOPLA)`. O título nomeia a **classe**; o slug qualifica a variante (CLAUDE.md §5). H1 **igual ao do 06** — é a mesma classe, outra face; a distinção vive no slug e na primeira linha da descrição.
- **Theory primer:** ver seção "Theory primer" (URL verificada por fetch nesta fase — HTTP 200, sem redirect; é a seção **Mass assignment vulnerabilities** da página **API testing**, **não** a de IDOR de 01–03, **nem** a de Access control de 04–05, **nem** a de Information disclosure do 06).

---

## A tese do átomo

> **A autorização se aplica no nível da PROPRIEDADE — e no lado da ESCRITA isso quer dizer: a requisição pode setar só os campos que o chamador pode escrever.** O chamador tem direito de editar **este** registro — é o registro **dele**, e a posse aprova —, mas o write não é **escopado aos campos que ele pode setar**: o handler mescla o **body inteiro** no registro, e `is_admin` entra pelo body junto com o `displayName` legítimo. A pergunta de auditoria é **"o write é escopado aos campos que este chamador pode setar?"** — e a resposta, no `vulnerable/`, é *não*.

### O eixo é a propriedade, do lado da escrita — e isso é a lição inteira

Os átomos de API1 (01–03) perguntavam sobre o **objeto** (*de quem é este objeto?*). Os de API5 (04–05) perguntavam sobre a **função/operação** (*você pode invocar isto? / a autorização cobre todos os métodos?*). O 06 desceu ao grão da **propriedade** pelo lado da **leitura** (*a resposta devolve só os campos que este chamador pode ver?*). Aqui a mesma pergunta vira para a **escrita**: **"o write é escopado aos campos que este chamador pode setar?"** — e a resposta, no `vulnerable/`, é *não*: o body nomeia `is_admin`, o spread o grava, e o chamador vira admin.

A falha **não** é escrever no objeto de outro (a posse barra isso com `403`), **não** é invocar uma função proibida (a função privilegiada está guardada e o `403` inicial prova); é o write **aceitar propriedades demais** de um objeto que o chamador legitimamente pode editar.

### A simetria 06↔07 — mesma raiz, duas direções

É o contraste central do átomo, e ele mora no **código**, não na retórica:

| | 06 — `bopla-excessive-exposure` (leitura) | 07 — `bopla-mass-assignment` (escrita) |
|---|---|---|
| A linha do pecado | `res.json({ handle: req.params.handle, ...user })` | `USERS.set(req.params.handle, { ...user, ...req.body })` |
| O que espalha | o **registro** na **resposta** (`...user` **saindo**) | o **body** no **registro** (`...req.body` **entrando**) |
| Pergunta de auditoria | a resposta devolve só os campos que este chamador pode **ver**? | o write é escopado aos campos que este chamador pode **setar**? |
| O fix | allow-list de **leitura** (nomear o que pode sair) | allow-list de **escrita** (nomear o que pode entrar) |
| A raiz | confiar no objeto inteiro | confiar no objeto inteiro |

**É por isso que a OWASP fundiu as duas faces em BOPLA (API3:2023).** Escrever essa simetria nos docs **creditando o 06**, sem reescrever a lição dele: o aluno que fez o 06 reconhece a forma; o que não fez entende mesmo assim (cada átomo é auto-contido).

### Self-update: o isolamento máximo do BOLA (a disciplina do 06, aplicada à escrita)

O cenário é deliberadamente o **self-update**: `clancy` faz `PATCH /users/clancy` com o token do `clancy`. Escolha de desenho, não detalhe:

- **Object-level authorization está presente, correta, e PASSA.** A guarda `if (req.params.handle !== caller) return res.sendStatus(403);` — a de 05/06, byte-idêntica — roda e **aprova**, porque `clancy` é dono do registro `clancy`. Nenhum objeto alheio é tocado.
- **Logo "isto é BOLA" não tem onde se apoiar.** `PATCH /users/alice` com o token do `clancy` dá **`403`** nos dois gêmeos — o passo "não é BOLA" cai no colo.
- **A pergunta de auditoria cravada:** *"o write é escopado aos campos que este chamador pode setar?"* — **NÃO** *"de quem é o objeto?"* (BOLA) nem *"você pode invocar esta operação?"* (BFLA).

### A prova é o termômetro, não o eco — a lição mais cara da Fase 1, cravada no status code

No 05 o `200` do `PATCH` era **eco do input do atacante** e não provava a escrita; a prova precisou de um **segundo ator** (a vítima lendo o próprio registro). Este átomo resolve o problema **na arquitetura**: o `PATCH` responde **`204 No Content`** — sem corpo, nos **dois** gêmeos. Não há o que ecoar, então a prova é **obrigada** a ir buscar o estado por **outro caminho**: `GET /admin/users`, o **termômetro**.

- **O `204` é idêntico nos dois gêmeos.** No `vulnerable/` ele gravou `is_admin`; no `fixed/` ele ignorou. **Nem o status nem o corpo denunciam qual** — de propósito. A armadilha que o átomo existe pra ensinar a não cair é exatamente *"o write respondeu ok, logo pegou"*.
- **O termômetro é comportamental e sequencial:** `403` antes do `PATCH`, `200` depois (no `vulnerable/`); `403` **sempre** (no `fixed/`). O clímax do átomo é essa transição — uma porta que destrava.

### A disciplina anti-04 — a leitura errada central

O 04 ensinou **BFLA**: uma função admin-only **sem check de role**, invocável por qualquer autenticado. Este átomo tem uma rota admin — e é **o oposto** disso:

- **O check de role existe e está correto.** `if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);` — a linha é **byte-idêntica** à do **fix do 04** (conferido com `grep -Fxc`; ver "Verificação factual"). Ela lê o papel **do store**, não do token.
- **O `403` inicial é a prova viva disso.** Antes do `PATCH`, `clancy` bate na porta e leva `403`. A função **está guardada**.
- **O bug é o PAPEL FORJADO que a função legitimamente confere.** O atacante não burlou a guarda: ele **satisfez** a guarda, porque escreveu o papel que ela consulta. **A guarda que você vê está certa; o breach está a montante, no `PATCH`.**
- **Creditar o 04 sem reabrir a lição dele:** lá a função **faltava** o check de role (e o fix o acrescentou); aqui ela **tem** o check, ele **funciona**, e o atacante entra mesmo assim. Dois átomos, duas causas, a mesma porta.

### O erro de leitura a combater — e ele determina o desenho

Três leituras erradas prováveis — **duas firmes** e **uma terceira cortável**. O WALKTHROUGH **nomeia cada uma e a desmonta** (ver "Walkthrough", Step 5):

1. **"Isto é BOLA."** O aluno vê um `PATCH` e um flag de privilégio e pensa "mexi em coisa que não era minha". **Desarme:** `clancy` escreve no **próprio** registro; `PATCH /users/alice` com o token dele dá **`403`** — a object-level authorization existe e morde. Você escreve no **seu** registro; o que está errado é **qual campo** o write aceitou.
2. **"Isto é BFLA / isto é o átomo 04."** **ESTA É A LEITURA ERRADA CENTRAL — tratar com mais peso.** O aluno vê `GET /admin/users` respondendo `200` e conclui "invoquei uma função admin sem ser admin". **Desarme:** o `403` do Step 3 já provou que a função **está guardada**; o `200` do Step 4 não é a guarda falhando, é a guarda **funcionando** sobre um papel que o atacante **forjou**. Função desprotegida é outra classe (e outro átomo); aqui a guarda está certa e o breach está **a montante**.
3. **"É só um campo ecoado." (cortável)** O aluno pensa "o servidor devolveu o que eu mandei, grande coisa". **Desarme:** o `204` **nega o eco** — não voltou campo nenhum. A prova foi o **privilégio**, não um valor devolvido. **Cortar se não couber em frase limpa.**

### Por que API3 (Broken Object Property Level Authorization)

O bug **não é** "input virou código" (injection — nada é parseado nem executado), **não é** "um objeto fora do escopo foi tocado" (BOLA — o chamador escreve no objeto **dele**), **não é** "uma função sem autorização foi invocada" (BFLA — a função admin está guardada e o `403` inicial prova). É **"o write aceita propriedades que o chamador não pode setar"** — controle de acesso **no nível da propriedade**: **API3** no OWASP API Security Top 10 **2023**, na sua **face de escrita** (*mass assignment*). Situe nessa edição, **sem arqueologia** (CLAUDE.md §5 — nomear a categoria vigente; **não** contar que mass assignment já foi um risco separado em edições antigas, nem recontar a fusão). Referência OWASP em **texto simples** (`API3:2023`), **sem link** — o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (a linha API3 **já existe**, apontando `bopla-excessive-exposure` e `bopla-mass-assignment`). Por ser vuln de **lógica/autorização** (Trigger, não Payload), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório.

---

## O que este átomo acrescenta (vs. 01–06)

**Honestidade pedagógica:** 01–03 ensinaram BOLA (eixo do objeto); 04–05 ensinaram BFLA (eixo da função/método); 06 ensinou BOPLA na face de leitura. Este **credita e não reabre** nada disso. Ele existe por três eixos novos:

1. **Primeiro átomo no grão da propriedade do lado da ESCRITA.** O 06 provou que autorização é devida a cada campo **devolvido**; este prova que ela é devida a cada campo **gravado**. Fecha a categoria API3 com as duas faces e explica, pelo código, por que elas são uma categoria só.
2. **Primeiro átomo cuja prova é COMPORTAMENTAL e SEQUENCIAL — e cujo endpoint atacado deliberadamente se cala.** O `204` mata o eco na arquitetura; o efeito só aparece lendo o estado por **outro endpoint**, numa ordem que importa. 05 precisou de um **segundo ator**; 06 provou **na própria resposta**; aqui é o **mesmo ator, outro caminho, depois**. É a lição "efeito observável se prova lendo o estado, nunca pelo eco do write" virada **passo obrigatório**.
3. **Primeira escalação de privilégio criada pela ESCRITA DE UMA PROPRIEDADE.** No 04 a escalação veio de invocar uma função de promoção **desprotegida**; aqui **não existe função de promoção** — o papel é gravado por um update de perfil comum, e a função admin está guardada o tempo todo. O lab nasce **sem nenhum admin**: o único admin que ele chega a ter é o que o **bug** cria.

> **Contraste a cravar (WALKTHROUGH e DIFF):** no 06, a mesma raiz vazava o registro **na resposta**; aqui ela deixa o body **entrar no registro**. No 04, a função admin **não tinha** check de role; aqui ela **tem**, correto, e o atacante passa mesmo assim. No 05, a prova da escrita exigiu a vítima; aqui o `204` garante que a prova venha do **estado**, não do eco.

---

## Feature simulada — atualização de perfil (API-only, sem HTML)

**Perfil de conta de uma plataforma multiusuário — a mesma feature do 05/06, agora pelo lado da escrita.** Cada usuário tem um perfil com um **nome de exibição** (display name) editável. A API de self-service deixa o usuário **atualizar o próprio perfil** (`PATCH /users/:handle`), e a plataforma tem uma **área administrativa** mínima (`GET /admin/users`) que só administradores podem consultar. Do ponto de vista do produto: "você edita o seu nome de exibição; a área admin é para administradores". O que o dev esqueceu foi **escopar o write aos campos que o usuário pode setar**: o handler mescla o body **inteiro** no registro, e o registro guarda, ao lado do `displayName`, um flag interno `is_admin` que decide quem entra na área administrativa.

**API-only por natureza** (CLAUDE.md §3.3): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`; sucesso sem corpo e erros via `res.sendStatus(...)`. Corpo JSON no `POST /login` e no `PATCH`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl.**

### A "descoberta" é acrescentar uma chave ao body — e a prova é olhar outro endpoint

Não há sink, não há payload. A vulnerabilidade se manifesta numa escrita **legítima** no registro **legítimo**: o aluno loga como `clancy`, manda o update de perfil que a feature oferece — e acrescenta **uma chave a mais** no JSON. O servidor responde `204` e não comenta. A técnica que o átomo ensina é a **segunda metade**: ir ler o efeito **em outro lugar** (ver "Padrão de prova").

---

## Autenticação — token opaco, cripto-forte (mesmo mecanismo de 01–06)

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados e devolve `{ "token": "<opaco>" }`. Mapa `token → usuário` **em memória**, resolvido por lookup. **NÃO é JWT.** Os helpers de auth (imports, bootstrap, `TOKENS`, `issueToken`, `authenticate`) e o `POST /login` são **byte a byte** os de 01–06 (conferido nesta fase: md5 do bloco `TOKENS`…`authenticate` e do handler de login batendo com 05 e 06) — **copiar, não reescrever**. Token com `randomBytes(24).toString("base64url")`: um token previsível seria uma segunda vulnerabilidade e violaria "um átomo = uma vuln" (CLAUDE.md §2). O ataque **não toca** o token.

**O que a auth prova e o que NÃO prova (deixar explícito — faz parte da lição):**

- **Autenticação prova *quem você é*.** Token ausente/ruim → `401` COM `WWW-Authenticate: Bearer`, nas três rotas, no `vulnerable/` exatamente como no `fixed/`.
- **A posse (*este objeto é seu?*) é checada e PASSA no self-update** — nos dois gêmeos. A object-level authorization não é a falha.
- **O papel (*você é admin?*) é checado na rota admin, corretamente, e vem do STORE** — não do token. Essa distinção é **material**: o token do `clancy` é o mesmo do começo ao fim; o que muda é o **estado** que a guarda consulta. **A identidade não mudou; o papel mudou.** Cravar isso é o que impede a leitura "forjei um token/me passei por admin".
- **A property-level write authorization (*quais campos você pode setar?*) é o que o `vulnerable/` não faz** e o `fixed/` passa a fazer. Essa é a única diferença entre os gêmeos.

**Usuários seedados (elenco da série — CLAUDE.md §5):**

- **`clancy`** — o **atacante** (você). Dono do **próprio** registro, que ele edita no exploit. (Elenco da série API: `clancy` é **masculino**; nos docs PT, "o atacante", "você mesmo", "dele". O masculino genérico do **papel** — "o dono", "o chamador" — coincide com o da pessoa; não há distinção a manter.)
- **`alice`** — existe **apenas** pra sustentar o `403` do passo de contraste (`PATCH /users/alice` com o token do `clancy`). Ela **nunca** é escrita com sucesso em nenhum passo, e **não precisa logar** em nenhum momento do walkthrough.

**AMBOS `is_admin: false`, SEM admin no seed.** Diferente do 04 (que seeda `carol` como a admin legítima), este átomo **não tem** administrador nenhum: o único admin que o lab chega a ter é o que **o bug cria**. Isso é desenho, não economia — é o que transforma o `403 → 200` do termômetro numa **escalação de verdade**, não numa comparação com uma conta privilegiada pré-existente.

**Requisito de README (EN+PT) — declarar o atalho:** o login sem senha é um **atalho deliberado do laboratório, não a vulnerabilidade**. Uma frase, **sem citar átomo** (mesmo requisito de 01–06).

---

## Store / dados — dois campos, um gravável pelo usuário, um não

**Sem banco** (CLAUDE.md §3.4). Estruturas TS. O `TOKENS` cresce a cada login; o `USERS` **muda em runtime** (este átomo **escreve** — ver "Estado mutável").

```ts
// --- Simulated identity: an opaque, server-side token; users own their own profile ---
// Each user owns exactly the record keyed by their own handle; ownership is handle == caller.
// displayName is the one field a user may edit. is_admin is an internal role flag: it decides
// who may call GET /admin/users, and a profile update must never accept it from the body.
// NOBODY is seeded as an admin -- the only admin this lab can have is one the bug creates.
// A Map, as in the series' other user stores: Map.get() types the record as User | undefined.
type User = { displayName: string; is_admin: boolean };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park",  is_admin: false }],   // attacker (you) -- updates his OWN record
  ["alice",  { displayName: "Alice Nguyen", is_admin: false }],   // the other account -- exists only to make PATCH /users/alice a 403
]);
```

- **`displayName` é o ÚNICO campo gravável pelo usuário.** `is_admin` é interno: existe no store, é consultado pela rota admin, e **nunca** deveria ser aceito vindo do body. O `vulnerable/` aceita; o `fixed/` não.
- **SEM `passwordHash`.** O campo era o vazamento do 06; aqui **não serve a nada** (o alvo é a escrita, não a leitura, e nenhuma rota serializa o registro). **Não incluir** — superfície mínima, e nada de dado sobrando pra confundir a lição.
- **`is_admin` em snake_case — continuidade cosmética com 04/06, NÃO lição.** O campo já existe com essa grafia nos dois átomos; manter. **Não** promover a grafia a contraste pedagógico (mesma regra da nota `:handle`-vs-`:id` do 05).
- **Posse = `handle === caller`.** Herdada de 05/06 (que a herdaram de `order.owner === caller` de 01–03). Aqui ela **passa** no self-update e **afasta** o BOLA; não é a lição.
- **Dois usuários, nenhum admin, nenhum campo além dos dois.** Superfície mínima.

### Por que `Map`, e o que ele NÃO defende aqui (honesto, e validado)

**Decisão do mantenedor: `Map<string, User>`, por continuidade com 04/05/06.** No 05 o `Map` tinha **dois** papéis: tipar `user` como `User | undefined` e fechar prototype pollution, porque o `PATCH` **escrevia** através de um lookup por chave-string do path. Aqui o `PATCH` também escreve — mas a guarda de posse roda **antes** do `USERS.get(...)`, então um `:handle` de `__proto__`/`constructor` nunca alcança o lookup (bate `403` porque `"__proto__" !== "clancy"`). **Validado nesta fase:** `PATCH /users/__proto__` → `403` nos dois gêmeos.

**O vetor novo deste átomo é `__proto__` NO BODY, não no path — e ele foi testado (ver "Validação").** `{ ...user, ...req.body }` com um body `{"__proto__":{"polluted":1}}` **não polui** `Object.prototype`: tanto o `JSON.parse` quanto o object spread criam a chave como **own property** (via `CreateDataProperty`, não `[[Set]]`), então a chave `"__proto__"` entra como propriedade inerte do registro e o protótipo global fica intacto. **Observado:** depois do `PATCH`, `({}).polluted` é `undefined`, `Object.keys({})` é `[]`, e o protótipo do registro continua sendo `Object.prototype`. **É por isso que o spread é mais seguro que `Object.assign` aqui** — e é por isso que este átomo continua sendo **um bug só**.

> **Disciplina de prosa:** mencionar prototype pollution nos docs do átomo **só** se for pra dizer o que foi **verificado** (o spread não polui) — e de preferência **não mencionar**: a classe não é a lição, e trazê-la à tona num átomo de mass assignment convida o aluno a procurar o bug errado. O `Map` é **herança estrutural** + typing. A nota técnica do `__proto__`-no-body **cabe no DIFF em uma frase**, como "o que foi testado e não acontece", nunca como lição.

> **Sobre a guarda `!user` — assimetria honesta entre os gêmeos (validada nesta fase).** `USERS.get(req.params.handle)` tipa `User | undefined`. No `fixed/`, o `user.displayName` do ternário **desreferencia** e o literal perde a obrigatoriedade de `is_admin` → sem a guarda o `tsc` dá **dois** erros (`TS18048: 'user' is possibly 'undefined'` **e** `TS2345`, porque `{ ...user, displayName }` vira `{ is_admin?: boolean }`). No `vulnerable/`, `{ ...user, ...req.body }` espalha `User | undefined` **e** um `any` (o `req.body`), e o `any` **lava o tipo do literal inteiro** → sem a guarda o `tsc` sai **exit 0**: a guarda **NÃO é forçada** no `vulnerable/`. **Mantê-la byte-idêntica nos dois gêmeos** como higiene (e pra o diff ser só a linha do `USERS.set`), mesmo sendo type-forced só no `fixed/`. Em runtime ela é **inalcançável** nos dois: a posse garante `handle === caller`, e `caller` é sempre um handle seedado. Registrar esse comportamento nos docs — e notar a honestidade da observação: **é o mesmo `any` do `req.body` que torna o bug possível e que silencia o compilador no gêmeo vulnerável.**

---

## Estado mutável — há escrita, há ordem, e o README declara o restart

**Diferente do 06** (que só lia e era idempotente), este átomo **muda estado** — e isso impõe tratamento explícito:

- **`USERS` muda em runtime.** O `PATCH` reescreve a entrada do `Map`. O `displayName` e, no `vulnerable/`, o `is_admin` do `clancy` ficam alterados enquanto o processo viver.
- **A ordem dos passos IMPORTA.** O termômetro só responde `200` **depois** do `PATCH`; pedi-lo antes é `403` — e esse `403` é **parte da prova**, não um erro do aluno. O walkthrough **depende** da sequência `403 → PATCH → 200` e diz isso explicitamente.
- **O `PATCH` é idempotente, o roteiro não.** Repetir o mesmo `PATCH` dá o mesmo estado final (`204` sempre); o que não se pode fazer é ler o termômetro "antes" depois de já ter escrito.
- **Gêmeos independentes.** O seed de cada build é próprio: um `is_admin` forjado na 8207 é invisível na 8307.
- **Restart zera tudo.** `./atom down bopla-mass-assignment && ./atom up bopla-mass-assignment` devolve `clancy` a `is_admin: false` (termômetro volta a `403`) e esvazia o mapa de tokens (o token antigo passa a dar `401`; logar de novo). **Validado nesta fase** (processo reiniciado: termômetro `403`, token antigo `401`).
- **Requisito de README (EN+PT), a única casa da frase do restart:** uma frase diz que o estado vive em memória e que derrubar/subir o átomo devolve tudo ao seed — **os tokens emitidos e o `is_admin` forjado**. **Não** repetir no WALKTHROUGH nem no DIFF.

---

## Rotas — três rotas, nenhuma a mais

Imports: `import express from "express";` e `import { randomBytes } from "node:crypto";`. Bootstrap (`const app = express();` + `app.use(express.json());`), `USERS`, `TOKENS`, `issueToken`, `authenticate` e o rodapé `listen` são **idênticos** entre `vulnerable/` e `fixed/`. Superfície: **três rotas** — `POST /login`, `PATCH /users/:handle` (a vulnerável) e `GET /admin/users` (o termômetro, byte-idêntico nos dois gêmeos).

**O que NÃO existe, e por quê:**

- **SEM `GET /users/:handle`.** Um read-back do próprio registro reintroduziria a tensão com o **fix do 06**, que existe justamente pra **esconder** `is_admin` da resposta. Serializar o flag aqui seria regredir a lição do átomo irmão; não serializá-lo faria do read-back um passo inútil. A omissão é **deliberada**: a prova é o **termômetro**, não um read-back. Escrever isso no DIFF em uma frase — é a pergunta que o aluno atento vai fazer.
- **SEM listagem pública de usuários, SEM `GET /me`, SEM índice de rotas.** Superfície mínima.
- **SEM função de promoção.** Não há `POST /admin/users/:handle/promote` (isso é o 04). O papel neste átomo não é conferido por função nenhuma — ele é **gravado** por um update de perfil.

### `POST /login` — obter o próprio token (idêntico às seis versões anteriores)

Recebe `{ "user": "<nome>" }`, valida contra `USERS` (via `USERS.has(user)`), devolve um token opaco. Sem senha (atalho de auth). Usuário desconhecido/ausente → `400` (higiene).

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

### `PATCH /users/:handle` — atualizar o próprio perfil (a rota VULNERÁVEL)

Autentica (Bearer ruim → `401`), confere a **posse** (`:handle === caller`, senão `403`), busca o registro, mescla o **body inteiro** nele e responde **`204`**. **A guarda de posse é correta e passa no self-update; a falha vive na linha do `USERS.set`.** Handler **≤ ~30 linhas** (tem 12).

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

- **A guarda de posse vem ANTES da busca** e **passa** no self-update. É byte-idêntica à de 05/06 (conferido com `grep -Fxc`). Ela **não é a falha** — é o que **afasta** o BOLA (e o que dá o `403` do passo de contraste em `PATCH /users/alice`).
- **Source:** o `req.body` (um objeto JSON controlado pelo cliente). **Sink conceitual:** o `...req.body` dentro do `USERS.set` — o write que não filtra. Não greppa; audita-se perguntando **"o write é escopado aos campos que este chamador pode setar?"**.
- **`res.sendStatus(204)` é a escolha arquitetural do átomo** (ver "Status code"): sucesso sem corpo, nos dois gêmeos, pra que **não exista eco** a confundir com prova. **Validado em runtime:** resposta sem corpo, **sem** `Content-Type`, **sem** `Content-Length`.
- **`USERS.set(...)` em vez de mutate-in-place.** O 05 mutava (`user.displayName = ...`); aqui os **dois** gêmeos usam `USERS.set(handle, { ... })` — spread-into-set — pra que a diferença entre eles seja **só o conteúdo do objeto**, mantendo o eixo único e o espelho exato com o 06 (lá, dois `res.json`; aqui, dois `USERS.set`). **NÃO usar mutate-in-place no `fixed/`:** divergiria o mecanismo e quebraria o diff de uma linha.

### `GET /admin/users` — o termômetro (CORRETA nos dois gêmeos, fora do diff)

Rota admin-only, **read-only**, **byte-idêntica** em `vulnerable/` e `fixed/` — **não entra no diff**. Autentica, confere o **papel lendo o STORE** e devolve a lista de handles. O que muda entre os gêmeos não é esta rota: é se o `PATCH` a alimenta com um flag forjado.

```ts
// Admin-only, read-only, and IDENTICAL in both builds -- this guard is NOT the bug. It reads
// the caller's role from the STORE (the state the PATCH above writes), not from the token (which
// the attack never touches), so it reflects who the caller IS NOW, not who logged in.
app.get("/admin/users", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);
  res.json([...USERS.keys()]);   // handles only -- no record fields in the body
});
```

- **A linha da guarda é BYTE-IDÊNTICA à do fix do 04** (`grep -Fxc` = 1 nos dois arquivos; conferido nesta fase). Creditar isso no DIFF é o jeito mais econômico de cravar "esta guarda está certa — é a mesma que o 04 ensinou a escrever".
- **Lê o ESTADO, não a identidade.** `USERS.get(caller)?.is_admin` consulta o store — o que o `PATCH` muda —, **não** um claim do token, que o ataque nunca toca. É essa escolha que faz a rota funcionar como termômetro.
- **O corpo NÃO é o prêmio.** Devolve só `[...USERS.keys()]` — handles, nenhum campo de registro. Não serializa `is_admin` nem nada do `User`, **mantendo o fix do 06 intacto**. O que prova a escalação é o **status** (`403` → `200`), não o dado. Cravar isso: o aluno não deve sair achando que "vazou a lista de usuários".
- **Ordem no arquivo:** `POST /login`, depois o `PATCH` (o vulnerável, o centro da leitura), depois o termômetro.

> **Bind do servidor** (rodapé idêntico a 01–06): `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);` — **validado nesta fase**: sem `PORT`, sobe em `3000`; o socket escuta em `127.0.0.1`, não em `0.0.0.0`.

> **DOIS HANDLERS, UM BUG.** O `PATCH` é o vulnerável; o `GET /admin/users` é **correto nos dois gêmeos** e existe pra ser o instrumento de prova (e o desarme do "é o 04"). O "Spot the bug" mostra **só o `PATCH`**; o termômetro é apresentado no Step 3, como **a função guardada**. **NÃO** mostrar os dois lado a lado como se fosse uma assimetria entre handlers (isso é o 05).

---

## Fix — allow-list de ESCRITA: nomear o único campo gravável

O gêmeo `fixed/` difere **APENAS pela linha do `USERS.set`** (e o comentário acima dela): troca a mescla do body inteiro por uma **allow-list de escrita** — o handler nomeia o campo que o chamador pode setar. **Nenhuma outra linha muda** — `POST /login`, a guarda de posse, o `!user`, o `res.sendStatus(204)`, a rota `GET /admin/users` **inteira**, helpers, imports, `USERS`, rodapé, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` são **idênticos**.

```ts
app.patch("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  // FIXED: the write names the one field the caller may set -- an allow-list, not the request
  // body. is_admin is not in the list, so a body that carries it changes nothing; a field added
  // to User later stays caller-unwritable until someone deliberately names it here.
  USERS.set(req.params.handle, { ...user, displayName: typeof req.body?.displayName === "string" ? req.body.displayName : user.displayName });
  res.sendStatus(204);                                           // no content: nothing to echo back
});
```

Diff mínimo (o eixo único):

```diff
   const user = USERS.get(req.params.handle);
   if (!user) return res.sendStatus(404);
-  // VULNERABLE: the ownership check above is right -- this IS your record. But the write
-  // merges the WHOLE request body into the record, so every property the body names is set,
-  // is_admin included. Authorization applies to each property written, not only to the object.
-  USERS.set(req.params.handle, { ...user, ...req.body });
+  // FIXED: the write names the one field the caller may set -- an allow-list, not the request
+  // body. is_admin is not in the list, so a body that carries it changes nothing; a field added
+  // to User later stays caller-unwritable until someone deliberately names it here.
+  USERS.set(req.params.handle, { ...user, displayName: typeof req.body?.displayName === "string" ? req.body.displayName : user.displayName });
   res.sendStatus(204);                                           // no content: nothing to echo back
```

**A leitura correta do fix (cravar no DIFF):** a autorização não pertence só ao **objeto** — pertence a cada **propriedade que a requisição grava**. O handler já autorizava o objeto (a posse); o fix **estende a autorização ao grão do campo no lado da escrita**, nomeando explicitamente o que pode entrar. Os dois gêmeos chamam o **mesmo** `USERS.set` com o **mesmo** registro-base (`...user`); o que muda é **quem decide o resto do objeto** — o body, ou o handler.

- **O ternário `typeof … === "string"` faz parte da allow-list, NÃO é uma segunda lição.** Ele existe porque `req.body` é `any`: sem o teste, um `{"displayName": {"x":1}}` gravaria um não-string num campo tipado `string` (mentira de tipo que o TS não pega). Nomear o campo **e** aceitar só o tipo dele é a forma honesta e mínima de "só este campo pode entrar". **NÃO** transformar isso em prosa sobre input validation — uma frase no DIFF basta, enquadrada como parte do "nomear o campo".
- **O ternário referencia `user.displayName` de propósito:** é o que torna a guarda `!user` **exigida pelo compilador** no `fixed/` (ver "Store / dados"), e é o fallback correto quando o body não traz o campo (`PATCH` sem `displayName` → registro inalterado, `204`). **Validado:** body vazio, body ausente e `displayName` não-string deixam o registro intacto.
- **Divergência deliberada em relação ao 05, a creditar:** o `PATCH` do 05 escrevia com mutate-in-place e `??` (`user.displayName = req.body?.displayName ?? user.displayName`). Aqui os dois gêmeos usam `USERS.set` com spread, pelo eixo único e pelo espelho com o 06. **Não** promover a diferença a lição — é escolha estrutural, descrita como tal.
- **DTO/serializer, do lado da escrita — generalizar, NÃO importar maquinaria.** Em 1–2 frases no DIFF: em escala, essa projeção vira um **schema de entrada** (um DTO de update, um validador declarativo) que define, num lugar só, quais campos cada papel pode escrever. **NÃO** trazer `zod`/`joi`/`class-validator` pro átomo (quebraria o diff de uma linha e a regra de dependências mínimas); só nomear o princípio.

### BLACKLIST DE ESCRITA = FOIL instrutivo no DIFF, NÃO o fix (validado nesta fase)

Mostrar, no DIFF, a alternativa **descartada** — e por que foi descartada (mesmo papel do foil do 06, agora do lado da escrita):

```ts
// CONSIDERED AND REJECTED -- a deny-list on the write: strip the known-bad field from the body.
const { is_admin, ...rest } = req.body ?? {};
USERS.set(req.params.handle, { ...user, ...rest });
```

- **A deny-list "funciona" hoje** — remove `is_admin` do body, e a escalação de hoje não acontece.
- **Mas ela FALHA ABERTO (fails open):** um campo privilegiado **novo**, adicionado ao `User` amanhã (um `is_staff`, um `plan`, um `creditBalance`), **fica gravável sozinho** — ninguém lembrou de acrescentá-lo à deny-list. A allow-list **FALHA FECHADO (fails closed):** o campo novo é **não-gravável** até alguém deliberadamente nomeá-lo.
- **Validado nesta fase (foil em protótipo, `tsc --noEmit` exit 0):** com um segundo campo privilegiado `is_staff` no `User`, o **spread** (o vulnerable) grava `is_admin` **e** `is_staff`; a **deny-list** bloqueia `is_admin` mas **grava `is_staff`**; a **allow-list** não grava nenhum dos dois. A diferença **não é estética** — é a direção em que o erro corre. Registrar a tabela do foil no DIFF.
- **A própria PortSwigger (o primer) recomenda allow-list** dos campos atualizáveis; a deny-list aparece lá como complemento, não como substituta. Mencionar sem transformar em apelo à autoridade.

---

## Status code

- **`PATCH /users/clancy` (self-update) → `204 No Content` nos DOIS gêmeos.** No `vulnerable/` o write gravou `is_admin`; no `fixed/` ignorou — e **nem o status nem o corpo denunciam qual**. Isso é **desenho**, não economia: mata o eco na arquitetura e obriga a prova a ir pro estado. **RFC 9110 §15.3.5** (conferido em texto bruto nesta fase): o `204` indica que o servidor **cumpriu a requisição com sucesso** e que **não há conteúdo adicional a enviar**; "a 204 response is terminated by the end of the header section; **it cannot contain content**". É literalmente o status que **não pode** ecoar. **Validado em runtime:** corpo vazio, sem `Content-Type`, sem `Content-Length`, nos dois gêmeos.
- **DIVERGÊNCIA DELIBERADA EM RELAÇÃO AO 05 — creditar explicitamente.** Conferido lendo o 05: o `PATCH` dele responde **`200` com corpo** (`res.json({ handle: req.params.handle, displayName: user.displayName })`), e o próprio DIFF do 05 explica que esse corpo é **eco do input** e **não** prova a escrita. Este átomo **leva a conclusão do 05 ao status code**: se o eco não prova, que não exista eco. Escrever assim no DIFF — **uma frase**, creditando o 05 —, pra não parecer inconsistência acidental entre átomos irmãos.
- **`PATCH /users/alice` (token do `clancy`) → `403`.** **Mesmo argumento de 05/06:** a guarda de posse compara **identidade antes da busca**, não consulta o store, não revela existência (dispara igual pra handle alheio-existente e inexistente → sem username enumeration). RFC 9110 §15.5.4 (conferido em texto bruto): credencial presente, considerada insuficiente → `403` honesto; o `404` como `MAY` pra esconder existência não se aplica. **Referenciar o DIFF do 05** pro argumento completo — **não recontar**.
- **`GET /admin/users` → `403` (não-admin) / `200` (admin).** `403` pelo mesmo critério: credencial presente, insuficiente para a função; a existência da área admin é premissa, não segredo (mesmo argumento do 04). **O `403 → 200` é o clímax da prova.**
- **Sem/ruim token → `401` com `WWW-Authenticate: Bearer`**, nas **três** rotas. RFC 9110 §15.5.2 (conferido em texto bruto): o `401` **MUST** carregar o challenge; o `403` não carrega, o chamador já está autenticado. Igual a 01–06.
- **O `404` do `!user` no `PATCH` é higiene byte-idêntica nos dois gêmeos, INALCANÇÁVEL em runtime.** A guarda de posse garante `handle === caller`, sempre seedado. **Validado:** `PATCH /users/nobody` e `PATCH /users/__proto__` → **`403`** (a posse barra antes do lookup), **não** `404`. *(Diferente do 05, que tinha um `404` real alcançável no `PATCH` do `vulnerable/` porque lá **não havia** guarda de posse nesse handler.)*
- **`POST /login` com usuário desconhecido/ausente → `400`** (higiene, igual a 01–06).

> **Regra de bolso (a mesma de 01/05/06):** a existência do alvo é sensível (ou revelada)? Aqui **não** — a posse compara identidade antes da busca → **`403`** honesto. O critério é um só, o da série. **Não** reabrir o argumento; **forward** pro DIFF do 05.

---

## Padrão de prova — Trigger (comportamental e sequencial: o estado lido por outro caminho)

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso: o exploit é **uma ação legítima com efeito observável** — um update de perfil com **uma chave a mais** no JSON.

- **BASELINE ≠ EXPLOIT (ao contrário do 06).** O baseline do **comportamento** é o `403` do termômetro **antes** do ataque (Step 3); o baseline da **feature** é o próprio `displayName` dentro do body do exploit (o update é real e legítimo — ele só carrega uma chave a mais). **Não** se escreve um `PATCH` "só de baseline": o `204` seria idêntico e não ensinaria nada — pior, reforçaria a armadilha de ler o status como prova.
- **A prova NÃO é auto-contida — e esse é o contraste honesto com o 06 e com o 05.** No 06, o vazamento estava no corpo da própria resposta (prova auto-contida). No 05, o eco não provava e a prova exigiu um **segundo ator** (a vítima). Aqui é um terceiro arranjo: **mesmo ator, outro endpoint, depois** — o estado se lê pelo termômetro. Cravar: *efeito observável se prova lendo o estado por outro caminho, nunca pelo eco do write.*
- **Há dependência de ordem** (`403` → `PATCH` → `200`) e ela é **parte da lição**, não um incômodo: a transição **é** a prova.
- **Por ser Trigger → passo de contraste OBRIGATÓRIO** (CLAUDE.md §5) — ver Walkthrough, Step 5.

---

## Walkthrough — estrutura e requests (7 steps)

Trabalhado **100% no Burp** (Repeater), `curl` como equivalente — **API-only, SEM trilha browser** (CLAUDE.md §3.3). **Sem Intruder:** a tese não é escala/enumeração. Cada request é um bloco colável: request-line (verbo explícito) + `Authorization: Bearer <token>` + corpo JSON quando houver. Tokens são **placeholders** (`<clancy-token>`); handles são **literais** (seed fixo). **Uma conta é logada:** só o `clancy` (a `alice` nunca é escrita com sucesso e **não loga**).

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de perfil serve `PATCH /users/:handle`; a guarda de posse confere que o registro é seu, e então o handler mescla o body inteiro no registro" — não um personagem. Definir todo termo não-óbvio na estreia: "BOPLA (Broken Object Property Level Authorization)", "mass assignment (auto-binding)", "property-level write authorization", "allow-list (whitelist) de escrita", "opaque token".

**REQUISITO DE REDAÇÃO — clareza é requisito DURO.** Cada bloco de request é precedido de uma linha de rótulo que diz **MÉTODO**, **ALVO** e **o que aquela request ISOLA**. Formato (herdado do 06):

> **EN:** `Method: PATCH · Target: clancy (yours) · Isolates: a field the profile form never offered goes in with the one it did`
>
> **PT:** `Método: PATCH · Alvo: clancy (seu) · Isola: um campo que o formulário de perfil nunca ofereceu entra junto com o que ele ofereceu`

A prosa **NOMEIA as leituras erradas e as desarma uma a uma** — **duas firmes** ("é BOLA", "é BFLA/é o 04", esta com mais peso) e **uma terceira cortável** ("é só um campo ecoado").

### 1. Context
- API de perfil de conta; auth por Bearer token opaco; `PATCH /users/:handle` atualiza o perfil. Isto é **BOPLA** — **API3:2023** do OWASP API Security Top 10 —, na sua **face de escrita**, o que a indústria chama de **mass assignment** (ou *auto-binding*): o framework/handler liga propriedades da requisição a campos do objeto interno, e a requisição acaba podendo setar campos que o dev nunca pretendeu expor. Definir os termos.
- **Contraste de abertura com o 06** (uma frase, creditando, sem reabrir): lá a pergunta era *"a resposta devolve só os campos que você pode VER?"*; aqui é *"a requisição pode SETAR só os campos que você pode escrever?"*. Mesma raiz — confiar no objeto inteiro —, duas direções.
- Você é o `clancy`, e vai editar o **seu próprio** registro — autorizado no nível do objeto — e descobrir que o write aceitou um campo que nunca foi seu pra escrever. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar **UM** handler: o `PATCH /users/:handle`. A assimetria é **interna**: a guarda de posse (`if (req.params.handle !== caller) return res.sendStatus(403);`) está **presente e correta**, e **uma linha abaixo** o `USERS.set(req.params.handle, { ...user, ...req.body })` mescla o body inteiro. Pergunta de auditoria — **diferente** da de BOLA e da de BFLA: não "cadê o check de dono?" (presente, e passa), não "a autorização cobre todos os métodos?" (o método está guardado), mas **"o write é escopado aos campos que este chamador pode setar?"** → não: o que o body nomear, o registro recebe.
- **Simetria com o 06 no CÓDIGO (cravar, uma frase):** lá a linha do pecado era `res.json({ handle, ...user })` — o registro **saindo** inteiro; aqui é `USERS.set(handle, { ...user, ...req.body })` — o body **entrando** inteiro. A classe **não greppa**: não há string perigosa, há um objeto inteiro atravessando a fronteira.
- **Não mostrar o termômetro aqui.** Ele entra no Step 3, como a função guardada.

### 3. How auth works in this lab (subseção curta) — e o termômetro, provado guardado
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo), cripto-forte (`randomBytes`), mapeado ao usuário. **Dois pontos:** (i) a **autenticação É imposta** (token ruim → `401` + challenge); (ii) a **posse** do objeto é checada **e passa** no self-update.
- **Disciplina cravada:** o ataque **não toca** o token (não decodifica, não adultera, não forja) — ele fica válido e do `clancy` do começo ao fim. **A identidade nunca muda; o que muda é o estado que o servidor consulta.**
- **APRESENTAR o termômetro AQUI e provar que está guardado.** `GET /admin/users` é a área administrativa: ela checa o papel do chamador **lendo o store** e recusa quem não é admin. Rodar agora, como `clancy` (ainda não-admin):

  > `Method: GET · Target: /admin/users · Isolates: the admin function is guarded — and you are not an admin`

  → **`403`**. **Esse `403` é a linha de base da prova E o desarme antecipado do "é o 04":** a função **tem** check de role e ele **funciona**. Guardar esse resultado — o Step 4 volta aqui.
- **Nota de desenho a escrever em uma frase:** não há rota que leia o seu registro de volta; a única janela para o estado é esta porta administrativa. É de propósito — o que importa não é ver o campo, é ver **o que o campo faz**.

### 4. Exploit — three movements, and the `204` is NOT the proof
Apontar o Burp pro `vulnerable/` em `127.0.0.1:8207`. Logar como `clancy` (`POST /login`, bloco colável) e então:

1. **O write.** `PATCH /users/clancy` com `{"displayName":"Clancy Parked","is_admin":true}` → **`204`**, **corpo vazio**.
   > `Method: PATCH · Target: clancy (yours) · Isolates: the body carries one key the profile form never offered`

   **CRAVAR:** o corpo vazio é **de propósito** — não há o que ecoar. **Não caia na armadilha "o write respondeu ok, logo pegou":** um `204` diz que a requisição foi cumprida, não **o que** foi gravado. O gêmeo corrigido responde **exatamente este mesmo `204`** e não grava nada.
2. **A prova.** `GET /admin/users` com o **mesmo** token → **`200`**, corpo `["clancy","alice"]`.
   > `Method: GET · Target: /admin/users · Isolates: the door that answered 403 in Step 3 now opens`

   A mesma request, o mesmo token, a mesma guarda — e o resultado virou. **O que mudou foi o estado que a guarda consulta.**
3. **Nomear o efeito.** Você **forjou** `is_admin` por mass assignment — pela porta de um update de perfil — e a função privilegiada passou a te aceitar, **funcionando como foi escrita**. Nada no corpo do `200` é o prêmio (são handles); o prêmio é o **status**: uma função que te recusava agora te atende.

**A lição da Fase 1 virada passo, a escrever explicitamente:** efeito observável se prova **lendo o estado por outro caminho**, nunca pelo eco do write. Aqui o átomo tirou o eco da mesa pra que não houvesse atalho.

> **Frase-âncora do WALKTHROUGH (uma casa só):** *A write that answers `204` proves nothing about what it wrote — the proof was the admin door: `403` a minute ago, open now.* / *Um write que responde `204` não prova nada sobre o que escreveu — quem provou foi a porta de admin: `403` um minuto atrás, aberta agora.* Mora no fim do Step 4 (o clímax). **Não** repetir no DIFF nem no README. *(Manter distância da âncora do 02 — "a wall of 404s is 'didn't find,' not 'nothing to find'": a do 02 é sobre ler resultado de enumeração; esta é sobre o eco do write não ser prova. Não colar as frases.)*

### 5. Step — What the vuln is NOT (passo de contraste OBRIGATÓRIO)
Nomear e desarmar — **duas firmes** e **uma terceira cortável**. **Um** único request novo (o `403` de posse); o resto se desarma com o que o aluno **já tem**.

1. **"Isto é BOLA — escrevi em algo que não era meu."** `PATCH /users/alice` com o `<clancy-token>` e `{"is_admin":true}` → **`403`**.
   > `Method: PATCH · Target: alice (not yours) · Isolates: ownership exists and bites — you only write your own record`

   **Desarma:** a object-level authorization está **presente e correta**; você **não** escreveu no registro de ninguém — escreveu no **seu**. O problema não é o objeto; é **qual campo** o write aceitou. (Mesmo argumento de posse de 05/06 — **forward** pro DIFF do 05, não recontar.)
2. **"Isto é BFLA — invoquei uma função admin." / "Isto é o átomo 04."** **ESTA É A LEITURA ERRADA CENTRAL — mais peso, parágrafo próprio, zero requests novos.** **Desarma:** volte ao Step 3. A rota admin **checou** o seu papel e te recusou com `403` — a função **está guardada**, e continua guardada depois do exploit: ela nunca deixou de checar. O que mudou não foi a guarda; foi **a resposta que o store dá a ela**. Em BFLA a função **não pergunta** (ou pergunta a coisa errada); aqui ela pergunta certo, e a mentira estava no **estado** que ela consulta. **A guarda que você vê está certa; o breach está a montante, no `PATCH`.** Função admin desprotegida é outra classe — ela tem o próprio átomo nesta série, e **não é este**.
3. **"É só um campo ecoado." (cortável)** **Uma frase:** não voltou campo nenhum — o write respondeu `204`, sem corpo. A prova foi o **privilégio**, não um valor devolvido. Se não couber limpo, **cortar** e ficar com (1) + (2).

**Conclusão a escrever explicitamente:** você está **totalmente autorizado para o objeto** (é o seu registro, a posse aprova) e a função privilegiada está **corretamente guardada** — e **ainda assim** você virou admin. A falha **NÃO** é escrever em objeto alheio (não é BOLA), **NÃO** é uma função sem check de role (não é BFLA), **NÃO** é um eco de resposta. É o write **aceitar propriedades demais**. A pergunta certa é *"o write é escopado aos campos que este chamador pode setar?"*.

### 6. Step — Impact (honesto)
- **Escalação de privilégio REAL e verificada.** `clancy` nasce `is_admin: false`, **não há admin no seed**, e ele **vira** admin por um update de perfil. O acesso administrativo está **comprovado** pelo termômetro (`403` → `200`), não suposto. Num sistema real, a mesma chave a mais no body é a distância entre uma conta comum e o painel de administração.
- **Contraste honesto com o 06** (uma frase): lá o impacto era **recon** — `is_admin` vazando com valor `false`, sem ninguém virar admin; aqui é **escalação verificada**. Mesmo campo, faces opostas da mesma categoria.
- **O que o impacto NÃO é (disciplina dura):**
  - **Não inflar.** O admin deste lab só **lista handles** — e está certo assim: o átomo não precisa de mais. Não escrever como se a área admin desse RCE, dump de base ou takeover de terceiros. O que foi provado é o **acesso**, e é suficiente.
  - **Não é vazamento de dados.** O corpo do `200` traz handles, nada de campo de registro. **Não** descrever o `200` como "vazou a lista de usuários".
  - **Não é bypass de autenticação.** O token é o mesmo, legítimo, do começo ao fim.

### 7. Why the fix works (porta 8307)
Apontar o Burp pro `fixed/` em `127.0.0.1:8307` e logar lá (cada build tem o próprio mapa de tokens). **Repetir a sequência inteira:**
- `GET /admin/users` → **`403`** (como na 8207, antes do ataque).
- `PATCH /users/clancy` com `{"displayName":"Clancy Parked","is_admin":true}` → **`204` — IGUAL!** Mesmo status, mesmo corpo vazio. **Nada na resposta mudou.**
- `GET /admin/users` → **continua `403`**.
- **Mesmo write, mesmo status, efeito MORTO.** O termômetro que **não dispara** é a prova do fix. E a feature continua viva: o `displayName` que você mandou **foi gravado** — só o `is_admin` foi ignorado.
- **O fix é a allow-list de escrita:** o handler **nomeia** o único campo que o chamador pode setar, em vez de mesclar o body. **Forward pro DIFF** pro foil allow-list-vs-deny-list (por que nomear o permitido falha fechado, enquanto remover o proibido falha aberto), pra nota do `__proto__`-no-body validado inócuo, e pro crédito da divergência de status em relação ao 05.
- **Posse e `401` não mudaram:** `PATCH /users/alice` (token do `clancy`) → `403`; sem/ruim token → `401` + challenge. A única coisa diferente entre os gêmeos é a linha do `USERS.set`.

**O walkthrough TERMINA aqui.** Sem Intruder, sem automação, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5).

---

## Frases-âncora (uma casa só cada — CLAUDE.md §11 / template)

Nenhuma frase memorável aparece em **dois** documentos. Atribuição fixa:

- **WALKTHROUGH (uma casa):** *"A write that answers `204` proves nothing about what it wrote — the proof was the admin door: `403` a minute ago, open now."* / *"Um write que responde `204` não prova nada sobre o que escreveu — quem provou foi a porta de admin: `403` um minuto atrás, aberta agora."* Mora no fim do Step 4.
- **DIFF (uma casa):** *"The vulnerable handler asks the request which properties to write; the fixed one already knows — and `is_admin` was never among them."* / *"O handler vulnerável pergunta à requisição quais propriedades escrever; o corrigido já sabe — e `is_admin` nunca esteve entre elas."* Mora na seção do fix.
- **Conferido contra 01–06 (lidas nesta fase); NÃO reusar nem colar:**
  - 01 — W: *"The same missing check doesn't leak an order: it leaks the collection…"*; D: *"`404` when existence itself leaks; `403` when admitting existence is fine."*
  - 02 — W: *"The Intruder screen doesn't tell you whether the app is fixed — a wall of 404s is 'didn't find,' not 'nothing to find.'"*; D: *"the id type changed, the discovery changed, the whole walkthrough changed; the correction changed nothing."*
  - 03 — W: *"Authorization present is not authorization sufficient — what matters is which question it answers."*; D: *"No information was missing — the question was."*
  - 04 — W: *"The endpoint never cared whose account the target was…"*; D: *"The fix adds no check about the target at all — it asks only whether the caller may run the function."*
  - 05 — W: *"One URL answered the read safely and the write wide open…"*; D: *"The fix invents nothing: it carries the `GET` handler's ownership guard onto the `PATCH` handler…"*
  - 06 — W: *"Owning the object was never the same as being cleared for every field on it…"*; D: *"`...user` serializes the object the store holds; the allow-list serializes the object the caller is cleared to read — BOPLA is the distance between the two."*
- **Atenção especial:** (i) à do **02**, pela vizinhança temática ("a resposta não quer dizer o que parece") — a deste átomo é sobre **o eco do write não ser prova**, outro corte; (ii) à do **06**, que usa a construção "X serializa …; a allow-list serializa …; BOPLA é a distância entre os dois" — **não** repetir essa construção espelhada no 07, mesmo sendo tentador. A âncora do DIFF deste átomo é sobre **quem decide a lista de campos**.

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` + `Dockerfile` em **cada** gêmeo, **self-contained, sem módulo compartilhado**; lockfile **commitado** por gêmeo. `app.ts` **difere** só pela linha do `USERS.set` no `PATCH` (+ o comentário); todo o resto — inclusive a rota `GET /admin/users` inteira — é idêntico entre as versões.

**Herança de toolchain (CLAUDE.md §3.6) — lida dos arquivos publicados de 01–06 nesta fase (os `Dockerfile` e `tsconfig.json` batem por md5 nos seis átomos; `package.json` difere só no `name`):**

`tsconfig.json` (copiar — idêntico a 01–06, md5 `9a2dc4f6…`):

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

- **A guarda `!user` é FORÇADA pelo compilador só no `fixed/`** (o `user.displayName` do ternário desreferencia; sem a guarda saem `TS18048` **e** `TS2345`). No `vulnerable/`, o `any` do `req.body` no spread **lava o tipo do literal** → não força. O `| undefined` vem da **assinatura do `Map.get`** (independente do `noUncheckedIndexedAccess`, que continua ligado por herança — **validado nesta fase**: desligá-lo não muda os erros). Manter a guarda **byte-idêntica nos dois gêmeos** como higiene e pra o diff ser só a linha do `USERS.set`. **Sem `?.` no `PATCH`** (a guarda de posse é comparação de string; o `!user` é a única desreferência guardada). O `?.` do termômetro (`USERS.get(caller)?.is_admin`) é herança byte-idêntica do fix do 04.

`Dockerfile` (idêntico a 01–06 — copiar; base `node:24.21.0-slim`, patch exato, nunca `latest` nem a tag móvel `node:24-slim`; md5 `cad28299…`):

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

`docker-compose.yml` (bind **só** em `127.0.0.1`, portas **8207/8307**):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8207:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8307:3000"
```

- `package.json` de cada gêmeo: `"name": "bopla-mass-assignment"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Entrypoint `tsx`. **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **Roda como não-root, sem `chown`** — mesma justificativa de 01–06. Reconfirmar no smoke test da Fase 2: build OK, container sobe como `node`, `tsx` sem erro de permissão, endpoints respondendo, imagem só com `express` + `tsx`.

---

## Dependências extras

**Nenhuma dependência nova.** Versões **exatas herdadas** de 01–06 — lidas do `package.json` publicado do 06 e conferidas contra os demais. **NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

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

- Base `node:24.21.0-slim` (lida dos `Dockerfile`, md5 idêntico nos seis átomos). Nenhuma divergência de toolchain.
- Classificação por **runtime**: `tsx` em `dependencies` (entrypoint que executa); `typescript`/`@types/*` em `devDependencies`. `npm audit --omit=dev` cobre exatamente o que a imagem `npm ci --omit=dev` instala e roda (`express` + `tsx`). **Escopo da imagem = escopo do audit = o que roda.** **Validado nesta fase:** `npm audit --omit=dev` = **0 vulnerabilities** nos dois gêmeos com esse `package-lock.json`.
- `crypto` é **nativo** (`node:crypto`, para `randomBytes`) — não é dependência npm. **NÃO adicionar biblioteca de validação/schema** (`zod`, `joi`, `class-validator`, `ajv`): a allow-list é um objeto literal de uma linha, e trazer um validador sugeriria que a lição é input validation — e **não é** (ver "Fix"). Respeita "só inclua a lib se serve à demonstração da falha ou ao fix" (§3.6).
- **Pin exato travado no `package-lock.json`** (commitado por gêmeo). Updates **manuais** (CLAUDE.md §8.7). Se algo em 01–06 parecer desatualizado, **seguir com o que está lá** — bump é decisão de corte de release (§3.6), não deste átomo.

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). A casa conceitual de mass assignment na PortSwigger Web Security Academy é a **seção "Mass assignment vulnerabilities" da página "API testing"** — **não** existe página dedicada (conferido nesta fase: `/web-security/mass-assignment` e `/web-security/api-testing/mass-assignment` dão **404**).

- **Primer (verificado por fetch NESTA fase — HTTP 200, sem redirect, âncora presente no HTML como `id="mass-assignment-vulnerabilities"`):**
  `https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities`
  Texto do link: **"Mass assignment vulnerabilities"** — o nome da **seção**, como a PortSwigger a apresenta, preservado em **inglês** também no README PT (CLAUDE.md §7).
- **A seção cobre exatamente o nosso cenário (conferido lendo o texto da página nesta fase):** define mass assignment como auto-binding de parâmetros da requisição a campos do objeto interno; o exemplo é um `PATCH /api/users/` com `isAdmin` acrescentado ao body; e a verificação proposta é literalmente o nosso **termômetro** — *"browse the application as wiener to see whether you can access admin functionality"*. A seção de prevenção recomenda **allowlist** dos campos atualizáveis — o nosso fix.
- **Por que o texto do link é o da SEÇÃO e não o H1 da página:** o precedente da série é usar o **H1 da página** (04/05: "Access control vulnerabilities and privilege escalation"; 06: "Information disclosure vulnerabilities"), mas aqui o H1 é **"API testing"**, que não nomeia a vuln. Usar o nome da seção é a adaptação fiel da mesma regra ("a forma como a PortSwigger apresenta"). *(Nota: o átomo **web** `mass-assignment` linka a MESMA URL com o texto curto "Mass assignment". Divergência cosmética deliberada, no mesmo espírito da divergência já ratificada no 06, onde o web `debug-enabled` usa "Information disclosure" e a série API usa o título completo. Ambos apontam pra mesma seção.)*

Formato exato EN:

```markdown
> **Theory primer:** Read [PortSwigger: Mass assignment vulnerabilities](https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato exato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: Mass assignment vulnerabilities](https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

**OWASP: sem link inline.** Os docs citam `API3:2023` em texto simples; o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (conferido: a linha **API3** já existe, apontando `bopla-excessive-exposure` e `bopla-mass-assignment`).

**Fase 2 (geração):** **re-confirmar a URL por fetch** (200, sem redirect, âncora presente) antes de cravar. **Se a seção não encaixar, PARAR e perguntar ao mantenedor** — não substituir por conta própria.

---

## Política de cross-ref (CLAUDE.md §5)

Publicação verificada **lendo `atoms/api/ROADMAP.md` e a árvore de `atoms/` NESTA fase**, não de memória: na série API, **01, 02, 03, 04, 05 e 06 estão publicados** (`[x]`, pastas completas); **08 em diante não** (07 é este; `auth-predictable-token`, `auth-no-lockout`, `oauth-client-cred-unverified` e tudo das Fases 3–4 estão `[ ]`).

- **`bopla-excessive-exposure` (06) — o PAR direto, e o contraste central.** Mesma categoria, mesma superfície de perfil, mesma forma de store, mesmo flag `is_admin`, mesmo eixo único de diff. Creditar a **simetria leitura↔escrita** com cuidado: **uma menção no Context, uma no Spot the bug, uma no Impact** — e **nunca reescrever a lição do 06**. Quem não fez o 06 tem que entender este átomo mesmo assim.
- **`bfla-admin-function` (04) — crédito obrigatório pela disciplina anti-04.** Lá a função admin **faltava** o check de role (e o fix o acrescentou); aqui a função **tem** o check — **byte-idêntico ao fix do 04** — e ele funciona. Creditar **sem reabrir** a lição de BFLA.
- **`bfla-method-based` (05) — origem do `PATCH /users/:handle` e do argumento de status.** Creditar: a posse que este átomo reusa, o argumento `403`/RFC 9110 (**forward**, não recontar), e a **divergência deliberada do `204`** contra o `200`+eco do 05, ancorada na própria conclusão do DIFF do 05 (o eco não prova).
- **`bola-sequential-id` (01), `bola-uuid-leaked` (02), `bola-nested-resource` (03) — origem do check de posse** que este átomo **mantém e faz passar** no self-update. Creditar a posse como o que **afasta** o BOLA.
- **Átomo web `mass-assignment` (A01) — publicado; NÃO citar.** Conferido: existe em `atoms/web/A01-broken-access-control/mass-assignment/`, é a mesma classe em Flask (`account.update(data)` → allowlist de campos) e usa a **mesma URL de primer**. **Não citá-lo** nos docs deste átomo: dizer "é o mesmo" seria falso no detalhe que importa (a série API ensina a classe como **property-level write authorization** dentro de BOPLA/API3, com um fluxo de prova inteiramente diferente — sem read-back, com `204` e termômetro), e reabriria uma lição que já tem casa própria. Se a geração sentir vontade de comparar, **não comparar**.
- **PROIBIDO citar qualquer átomo de API NÃO publicado** (08 em diante) — por nome, número ou descrição. **Em particular, NÃO nomear o átomo futuro de verbose errors** ao descrever o `400` com stack trace de JSON malformado (ver "Decisões que podem gerar dúvida"); descrever genericamente, se for mencionar, como "outra classe (misconfiguration)".
- **O átomo 04 pode ser nomeado no Step 5** ("isto não é o 04") porque está publicado — e nomeá-lo é **mais** didático que aludir. Mas **sem** reabrir o conteúdo dele: uma frase de contraste, com link relativo pro átomo.
- Termos técnicos em inglês no PT (BOPLA, BOLA, BFLA, mass assignment, auto-binding, property-level write authorization, object-level authorization, allow-list, whitelist, deny-list, blacklist, fail open, fail closed, DTO, token, Bearer, ownership check, role, Trigger, payload, privilege escalation).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API3 — Broken Object Property Level Authorization** | Segundo átomo da categoria; a pasta já existe (criada pelo 06). Fecha API3 com as duas faces. |
| Pasta | **`API3-broken-object-property-level-authz/` (JÁ EXISTE)** | O 06 a criou; este átomo só entra nela. **Não** criar pasta de categoria. |
| Nome / classe (H1) | **Broken Object Property Level Authorization (BOPLA)** — idêntico EN/PT, **igual ao do 06** | O título nomeia a classe; o slug (`bopla-mass-assignment`) qualifica a variante (face de escrita). |
| Face de BOPLA | **Escrita (mass assignment)** | A requisição seta campos que o chamador não pode escrever. Espelho do 06 (leitura). |
| A tese | **O write tem que ser escopado aos campos que o chamador pode setar** | A posse aprova o objeto; o write aceita o objeto inteiro que o body mandar. |
| Cenário | **Self-update: `clancy` faz `PATCH` no próprio registro** | Isolamento máximo do BOLA — ele escreve no objeto dele; só sobra property-level. |
| Campo-alvo | **`is_admin`** | Par simétrico do 06: o mesmo campo que lá **vazava na leitura**, aqui é **gravado na escrita**. |
| Superfície | **Três rotas:** `POST /login`, `PATCH /users/:handle` (vuln), `GET /admin/users` (termômetro) | Mínimo necessário pra escrever e pra provar. |
| **SEM** `GET /users/:handle` | **Omissão deliberada** | Um read-back reintroduziria a tensão com o fix do 06 (que **esconde** `is_admin` da resposta). A prova é o termômetro, não o read-back. |
| **SEM** função de promoção | **Omissão deliberada** | Promover por função é o 04. Aqui o papel é **gravado** por um update de perfil comum. |
| Resposta do `PATCH` | **`204 No Content` nos DOIS gêmeos** | Mata o eco na arquitetura (RFC 9110 §15.3.5: o 204 **não pode** conter corpo). Nem status nem corpo denunciam qual gêmeo é qual. |
| Divergência vs. 05 | **Deliberada e creditada** | O `PATCH` do 05 responde `200`+corpo (eco); o DIFF do 05 já diz que o eco não prova. O 07 leva essa conclusão ao status code. |
| Write vulnerável | **`USERS.set(req.params.handle, { ...user, ...req.body })`** | Mescla o body inteiro; `is_admin:true` do body sobrescreve. Espelho de `res.json({...user})` do 06. |
| Fix (eixo único) | **Allow-list de escrita: `USERS.set(req.params.handle, { ...user, displayName: typeof req.body?.displayName === "string" ? req.body.displayName : user.displayName })`** | Nomeia o único campo gravável; `is_admin` do body é ignorado. Diff de uma linha + comentário. |
| Mecanismo do write | **`USERS.set` com spread nos DOIS gêmeos (não mutate-in-place)** | Mantém o eixo único: só o **conteúdo do objeto** muda entre os gêmeos. Divergência estrutural vs. o 05, descrita como escolha, não lição. |
| O `typeof … === "string"` | **Parte da allow-list, não segunda lição** | `req.body` é `any`; sem o teste, um não-string entraria num campo `string`. Uma frase no DIFF; **sem** biblioteca de validação. |
| Deny-list de escrita | **FOIL descartado no DIFF, NÃO o fix** | `const { is_admin, ...rest } = req.body ?? {}` funciona hoje mas **falha aberto** (campo novo vira gravável); allow-list **falha fechado**. Validado por foil. |
| Termômetro | **`GET /admin/users`, read-only, admin-only, BYTE-IDÊNTICO nos dois gêmeos** | Fora do diff. O que muda é se o `PATCH` o alimenta com um flag forjado. |
| Check do termômetro | **`if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);` — byte-idêntico ao fix do 04** | Lê o papel **do STORE** (o que o `PATCH` muda), não do token (que não muda). Credita o 04 e crava que a guarda está correta. |
| Corpo do termômetro | **`[...USERS.keys()]` — só handles** | Não serializa `is_admin` nem campos de registro: mantém o fix do 06 intacto. O prêmio é o **status**, não o dado. |
| Store | **`Map<string, User>`, `User = { displayName, is_admin }`** | Herança de 04/05/06. `Map.get` tipa `User \| undefined`. **Sem `passwordHash`** (era do 06; aqui não serve a nada). |
| Seed | **`clancy` e `alice`, AMBOS `is_admin: false`, SEM admin** | O átomo **cria** o admin pelo bug (é a escalação). `alice` só sustenta o `403` de posse e nunca loga. |
| `is_admin` | **snake_case por continuidade com 04/06; gravável só pelo bug** | Grafia é cosmética, não lição. |
| Token | **Opaco, `crypto.randomBytes`; NÃO JWT** — idêntico a 01–06 | Cripto-forte pra não ser 2ª vuln. O ataque não toca o token: **a identidade não muda, o estado muda**. |
| Status codes | **`204` self-update (ambos); `403` posse alheia; `403`/`200` termômetro; `401` sem/ruim token; `400` login desconhecido; `404` do `!user` inalcançável** | `403` por identidade antes da busca (herança de 05/06, **forward**); `204` ancorado no RFC 9110 §15.3.5. |
| Estado | **MUTÁVEL, com dependência de ordem** | Diferente do 06. Restart zera tokens **e** o `is_admin` forjado; README declara na única casa. |
| Padrão de prova | **Trigger**; **comportamental e sequencial** (não auto-contida) | Mesmo ator, outro endpoint, depois. Contraste: 05 = segundo ator; 06 = auto-contida. → passo de contraste obrigatório. |
| Passo de contraste | **(1) `PATCH /users/alice` → 403 (não é BOLA); (2) não é BFLA/não é o 04 — PESO MAIOR; (3) não é eco (cortável)** | (1) usa 1 request novo; (2) e (3) usam o que o aluno já tem. |
| Trilha | **100% Burp (Repeater) / curl; SEM Intruder; SEM browser** | API-only (CLAUDE.md §3.3). A tese não é escala. |
| Impacto | **Escalação de privilégio real e verificada pelo termômetro** | `clancy` nasce não-admin, vira admin pelo bug. **Não inflar** (o admin só lista handles); **não** é vazamento de dados nem bypass de autenticação. |
| Theory primer | **PortSwigger "Mass assignment vulnerabilities"** (seção da página *API testing*) | Não existe página dedicada (404 conferido). A seção cobre PATCH+isAdmin e o próprio termômetro. |
| Cross-ref | **06 par direto; 04 crédito anti-BFLA; 05 posse/status/divergência do 204; 01–03 posse; NENHUM átomo de API 08+; NÃO citar o web `mass-assignment`** | 01–06 publicados. O web `mass-assignment` é a mesma classe em outra série — citá-lo reabriria lição com casa própria. |

---

## Decisões que podem gerar dúvida durante implementação

- **`res.sendStatus(204)` vs `res.status(204).end()`.** Usar **`res.sendStatus(204)`** — é a forma da série pra resposta sem corpo. **Validado nesta fase:** o Express 5 remove corpo e headers de entidade no `204`; a resposta sai **sem** `Content-Type` e **sem** `Content-Length`, corpo vazio. Não inventar `res.json({})` nem `res.end()`.
- **Tipos do Express 5 — retorno `Response` vs `void`.** Igual a 01–06: callbacks **sem** anotação de retorno, onde `return res.sendStatus(...)` passa. Se anotar o retorno, usar `res.sendStatus(...); return;`. **Não anotar é o caminho da série.**
- **Guarda `!user`: forçada só no `fixed/`.** No `fixed/` o ternário desreferencia `user` → sem a guarda saem `TS18048` **e** `TS2345`. No `vulnerable/` o `any` do `req.body` lava o tipo do literal → `tsc` **exit 0** sem a guarda. Manter byte-idêntica nos dois (higiene + diff limpo). Inalcançável em runtime nos dois.
- **`USERS.set(handle, { ...user, ...req.body })` type-checa limpo?** **Sim — validado:** `req.body` é `any`, o spread relaxa o literal inteiro, `tsc --noEmit` exit 0 nos dois gêmeos.
- **`req.body` quando não há corpo.** Com `express.json()` montado e requisição sem corpo, `req.body` fica `undefined`: `{ ...user, ...undefined }` é no-op em JS (não lança) → `204`, registro inalterado. **Validado nos dois gêmeos.** O `fixed/` usa `req.body?.displayName` (optional chaining) pelo mesmo motivo.
- **Body que não é objeto.** JSON array (`[1,2]`) → o spread copia os índices como chaves (`"0"`, `"1"`) no registro; **inerte** (nada serializa o registro) e **não** afeta `is_admin`. JSON escalar (`"foo"`, `null`) e JSON malformado → **`400`** do `body-parser`, **antes** do handler.
- **O `400` de JSON malformado vem com stack trace no corpo HTML** (handler de erro default do Express, sem `NODE_ENV=production`). **Isso é herdado de 01–06** — **conferido nesta fase rodando o `app.ts` publicado do 06**, que responde igual no `POST /login`. **Não** é novidade deste átomo, **não** é a lição e **não** se corrige aqui (seria um segundo eixo). Se o aluno esbarrar nisso ao digitar JSON errado no Repeater, não é parte do átomo. **Não** nomear o átomo futuro de verbose errors.
- **`__proto__` no body: testado, inócuo.** `{"__proto__":{"polluted":1}}` não polui `Object.prototype` (spread e `JSON.parse` usam `CreateDataProperty`, não `[[Set]]`): a chave entra como **own property** inerte do registro. **Validado:** `({}).polluted === undefined`, `Object.keys({})` vazio, protótipo do registro intacto, `is_admin` inalterado, termômetro segue `403`. No `fixed/`, a allow-list nem guarda a chave. **Se na geração isso mudar de comportamento (poluir), PARE e reporte** — viraria um segundo bug e exigiria redesenho.
- **Valores não-booleanos em `is_admin` (vulnerable).** O spread grava o que vier: `{"is_admin":"false"}` grava a **string** `"false"` (truthy → vira admin), `{"is_admin":0}` grava `0` (falsy → não vira). É mentira de tipo que o TS não pega, porque `req.body` é `any`. **Observado e registrado aqui; NÃO levar pro walkthrough** — abriria uma segunda lição (coerção de tipos) e distrairia da autorização. O walkthrough usa o booleano `true`.
- **Campos-lixo no body (`{"foo":1}`).** No `vulnerable/`, viram propriedades do registro; **inertes** (nenhuma rota lê ou serializa o registro além do `is_admin` pelo termômetro). No `fixed/`, ignorados. **Validado.**
- **Membership no `POST /login` — `USERS.has(user)`.** Mesma forma de 04/05/06 (`Map` compartilha `.has` com `Set`); `req.body?.user` é `any`. **Validado:** `tsc` limpo.
- **Ordem das rotas no arquivo:** `POST /login`, `PATCH /users/:handle`, `GET /admin/users`. O vulnerável fica no centro da leitura; o termômetro por último.
- **Corpo JSON em duas rotas** (`POST /login` e `PATCH`) → `app.use(express.json())` é obrigatório e idêntico a 01–06. Não remover.

---

## Validação de typecheck e runtime (feita NESTA fase de planning)

Montei um protótipo descartável fora do repo (scratchpad da sessão) com o **toolchain EXATO** herdado de 01–06 (`npm ci` do `package.json`/`package-lock.json` do 06 — express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; node **24.21.0** no host, igual à base da imagem) e o `tsconfig.json` da série (byte a byte), construí os **dois gêmeos** exatamente como esta spec os descreve, e rodei `tsc --noEmit` + exercitei os endpoints com `tsx`. Observado (não raciocinado):

**Typecheck (`tsc` 7.0.2):**

| Teste | Resultado observado |
|---|---|
| `vulnerable/app.ts` (`USERS.set(handle, { ...user, ...req.body })`, `sendStatus(204)`, termômetro) | **exit 0**, limpo |
| `fixed/app.ts` (allow-list com ternário `typeof`) | **exit 0**, limpo |
| **[prova negativa]** remover `!user` do **vulnerable** | **exit 0** — o `any` do `req.body` lava o tipo do literal; guarda **NÃO** forçada |
| **[prova negativa]** remover `!user` do **fixed** | **`TS18048: 'user' is possibly 'undefined'`** + **`TS2345`** (`{ is_admin?: boolean }` não é `User`) — guarda forçada |
| **[flag]** fixed-sem-guarda com `noUncheckedIndexedAccess: false` | **erros persistem** — o `\| undefined` vem da assinatura do `Map.get`, não do flag |
| foil allow-list / deny-list / spread (`tsc --noEmit`) | **exit 0** |

**Runtime — a sequência da prova** (servidores `tsx` nas portas 8207/8307, token do `clancy`):

| Passo | vulnerable (8207) | fixed (8307) |
|---|---|---|
| `GET /admin/users` **antes** do PATCH | **`403`** | **`403`** |
| `PATCH /users/clancy` `{"displayName":"Clancy Parked","is_admin":true}` | **`204`**, corpo vazio, sem `Content-Type`/`Content-Length` | **`204`**, idêntico |
| `GET /admin/users` **depois** do PATCH | **`200`** `["clancy","alice"]` | **`403`** (efeito morto) |
| `PATCH /users/alice` (token clancy) | **`403`** | **`403`** |
| `GET /admin/users` como `alice` (nunca patchada) | **`403`** | **`403`** |
| `PATCH /users/nobody` (token clancy) | **`403`** (posse antes do lookup; o `404` não alcança) | **`403`** |
| `PATCH /users/__proto__` (token clancy) | **`403`** | **`403`** |
| `PATCH` / `GET /admin/users` sem token ou com token ruim | `401` + `WWW-Authenticate: Bearer` | idem |
| `POST /login` usuário desconhecido | `400` | `400` |
| `GET /users/clancy`, `GET /me` (rotas inexistentes) | `404` do Express | `404` |
| **restart do processo** | termômetro volta a **`403`**; token antigo → **`401`** | idem |

**Runtime — o write, campo a campo (gêmeo vulnerable, via rota de probe descartável):**

| Body enviado | Efeito no registro | Termômetro depois |
|---|---|---|
| `{"displayName":"Clancy Parked"}` | só `displayName` muda | `403` |
| `{"is_admin":true}` | `is_admin: true` gravado | **`200`** |
| `{"foo":1}` | chave `foo` gravada, **inerte** | `403` |
| `{"__proto__":{"polluted":1}}` | own-property `__proto__` no registro; **`({}).polluted` continua `undefined`**, `Object.keys({})` vazio, protótipo do registro intacto | `403` |
| `[1,2]` (array) | chaves `"0"`,`"1"` gravadas, inertes | `403` |
| `"foo"` / `null` / JSON malformado | **`400`** do `body-parser` (com stack trace no HTML — **comportamento herdado**, conferido idêntico no `app.ts` publicado do 06) | — |
| sem corpo | nada muda, `204` | `403` |

**Runtime — o mesmo no gêmeo fixed:** `{"displayName":"...","is_admin":true}`, `{"__proto__":{...}}`, `{"foo":1,"is_admin":true}`, `{"displayName":123}`, `{}` e sem-corpo → **todos `204`**, e o registro **permanece com exatamente duas own-properties** (`displayName`, `is_admin`), com `is_admin: false` sempre. `displayName` só muda quando o body traz uma **string**.

**Runtime — foil allow-list vs deny-list vs spread** (um segundo campo privilegiado `is_staff` acrescentado ao `User`, como "amanhã alguém adiciona um campo"):

| Projeção do write | hoje (`{"is_admin":true}`) | amanhã (`{"is_staff":true}`) |
|---|---|---|
| **spread** (`...req.body`) — o vulnerable | grava `is_admin` | **grava também** `is_staff` |
| **deny-list** (`const {is_admin, ...rest} = req.body`) — descartado | bloqueia `is_admin` | **grava** `is_staff` (**fails open**) |
| **allow-list** (`displayName` nomeado) — o fix | bloqueia | **continua bloqueando** (**fails closed**) |

**Byte-identidade conferida (`grep -Fxc` = 1 em cada arquivo, `md5sum` nos blocos):**

- Guarda de posse `  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only` → **idêntica** no 05 (`GET`), no 06 (`GET`) e neste `PATCH`.
- Guarda do termômetro `  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);` → **byte-idêntica à linha do fix do 04**.
- Bloco de auth (`TOKENS` → fim de `authenticate`), handler `POST /login` e rodapé `listen` → **md5 idêntico** ao de 05 e 06.
- Handler `PATCH` do protótipo: **12 linhas** (limite da série: ~30). Linha mais longa do `fixed/`: 142 chars (abaixo das linhas de seed do 06, que chegam a ~190).

**Outras checagens:** `npm audit --omit=dev` → **0 vulnerabilities** nos dois gêmeos; sem `PORT`, o app sobe em `3000`; o socket escuta em `127.0.0.1` (confirmado no `ss -ltnp`), não em `0.0.0.0`.

**Conclusões cravadas:** os dois gêmeos saem exit 0; a guarda `!user` é type-forced só no `fixed/` (mantida como higiene nos dois, inalcançável em runtime); `__proto__` no body **não** polui (um bug só); a prova é o termômetro (`403 → 204 → 200` no vulnerable; `403 → 204 → 403` no fixed) e **nunca** o eco do write; allow-list de escrita falha fechado, deny-list falha aberto. A Fase 2 ainda roda `npm run typecheck` nos dois gêmeos como gate oficial (host/CI) e um smoke test completo em container.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia usuário→token, Bearer resolve de volta; `clancy`/`alice` recebem tokens distintos e cripto-fortes (`randomBytes`). Bloco de auth byte a byte o de 01–06; `USERS` é `Map<string, User>` com `User = { displayName, is_admin }`; membership por `USERS.has(user)`.
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido → **`401`** com `WWW-Authenticate: Bearer`, **nas três rotas**, nas duas versões.
3. **Termômetro guardado ANTES do exploit:** `GET /admin/users` com o token do `clancy` → **`403`** nos dois gêmeos. **Se der `200` antes do `PATCH`, o seed está errado (alguém nasceu admin) — PARE.**
4. **Vulnerable — mass assignment:** `PATCH /users/clancy` com `{"displayName":"...","is_admin":true}` → **`204` com corpo vazio**; em seguida `GET /admin/users` → **`200`** com `["clancy","alice"]`. **A transição `403 → 200` é o átomo.**
5. **Fixed — allow-list de escrita:** a MESMA sequência → `PATCH` **`204`** (idêntico!) e `GET /admin/users` **`403`**. O `displayName` enviado **foi** gravado (feature intacta); o `is_admin` **não**.
6. **O `204` é byte-equivalente nos dois gêmeos:** sem corpo, sem `Content-Type`, sem `Content-Length`. **Se algum gêmeo devolver corpo no `PATCH`, o desenho quebrou — PARE.**
7. **Posse presente e correta (afasta o BOLA):** `PATCH /users/alice` com o token do `clancy` → **`403`** nos dois gêmeos; o registro da `alice` **nunca** muda.
8. **`404` do `!user` inalcançável:** `PATCH /users/nobody` e `PATCH /users/__proto__` (token válido) → **`403`** (posse antes do lookup), **não** `404`, nos dois gêmeos. **Se der `404` ou `204`, a ordem da guarda está errada — PARE.**
9. **`__proto__` no BODY é inócuo:** depois de `PATCH /users/clancy` com `{"__proto__":{"polluted":1}}`, `({}).polluted` é `undefined` e o termômetro segue `403`. **Se poluir, PARE e reporte** (seria um segundo bug — violaria um-átomo-uma-vuln).
10. **`app.ts` DIFERE só pela linha do `USERS.set`** (+ o comentário) no `PATCH`. `POST /login`, a guarda de posse, o `!user`, o `res.sendStatus(204)`, **a rota `GET /admin/users` inteira**, helpers, imports, `USERS`, rodapé, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` **idênticos** entre as versões.
11. **A guarda do termômetro é byte-idêntica à do fix do 04** (`grep -Fxc`); a guarda de posse é byte-idêntica à de 05/06 (`grep -Fxc`).
12. **Seed sem admin:** `clancy` e `alice`, ambos `is_admin: false`, nenhum `passwordHash`, nenhum campo extra. **Nenhuma credencial real.**
13. **Resposta não vaza token nem campos de registro:** o termômetro devolve só handles; o `PATCH` não devolve nada. **Um bug só** (BOPLA, face de escrita).
14. **Superfície mínima:** só `POST /login`, `PATCH /users/:handle`, `GET /admin/users`. **Sem** `GET /users/:handle`, **sem** listagem pública, **sem** `GET /me`, **sem** rota de promoção, **sem** índice.
15. **Estado mutável tratado:** ordem `403 → PATCH → 200` explicitada no walkthrough; gêmeos independentes (8207 ↔ 8307); README declara o restart na única casa (tokens **e** `is_admin` forjado voltam ao seed). Reinício de processo confirmado zerando os dois.
16. **API-only:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, sem HTML; sucesso é `204` (sem corpo) ou `application/json`.
17. **Bind/portas:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1`; container `ENV HOST=0.0.0.0`. **Portas 8207 (vulnerable) / 8307 (fixed)**, internas `3000`, coerentes entre `EXPOSE`, `app.listen` e o compose.
18. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README. (`clancy` masculino no PT.)
19. **README declara o atalho** (EN+PT, sem citar átomo): login passwordless é atalho de laboratório, não a vulnerabilidade.
20. **Theory primer:** re-confirmar por fetch `https://portswigger.net/web-security/api-testing#mass-assignment-vulnerabilities` (200, sem redirect, âncora presente); texto do link "Mass assignment vulnerabilities", em inglês também no PT. **Confirmar que é a seção de mass assignment** (não IDOR de 01–03, não Access control de 04–05, não Information disclosure do 06). Se não encaixar, **PARAR e perguntar**.
21. **RFC 9110** conferido em texto bruto nesta fase: **§15.3.5 (204 No Content** — "cannot contain content"**)**, **§15.5.4 (403)** e **§15.5.2 (401, `WWW-Authenticate` obrigatório)**. O argumento do `403` **referencia** o DIFF do 05; o do `204` é argumento **novo** deste átomo e fica no DIFF dele.
22. **`npm audit --omit=dev` em cada gêmeo**, advisories esperados registrados. O átomo é vulnerável na **LÓGICA** (write sem escopo), **não nas dependências**. Meta: zero advisory de runtime (**0 observado nesta fase**).
23. **`npm run typecheck` (`tsc --noEmit`, typescript 7.0.2) verde nos DOIS gêmeos** — inclusive o `vulnerable/`. Gate de **host/CI**, não do container.
24. **Frases-âncora:** cada uma numa casa só (WALKTHROUGH: o `204` que não prova / a porta que destrava; DIFF: quem decide a lista de campos); **não** reusar nem espelhar as de 01–06 — atenção à do **02** (vizinhança temática) e à do **06** (não repetir a construção "a distância entre os dois").
25. **Rótulo em todo bloco do WALKTHROUGH** (EN e PT): método · alvo · o que isola. A prosa **nomeia e desarma** as leituras erradas: duas firmes ("é BOLA"; "é BFLA/é o 04" — **com mais peso**) e uma terceira cortável ("é só um eco").
26. **DISCIPLINA ANTI-04 (gate de redação):** em WALKTHROUGH e DIFF, está escrito **explicitamente** que a rota admin **está corretamente guardada**, que o `403` inicial prova isso, e que o breach está **a montante**, no `PATCH`. **Se um revisor conseguir ler o átomo como "invoquei uma rota admin" ou "a rota admin é fraca", reescrever.**
27. **Cross-ref:** 06 (par direto, simetria leitura↔escrita, sem reabrir); 04 (crédito da guarda correta); 05 (posse, status, divergência do `204`); 01–03 (posse); **nenhum** átomo de API 08+; **NÃO** citar o átomo web `mass-assignment`; **não** nomear o futuro átomo de verbose errors ao falar do `400` de JSON malformado.
28. **Impacto honesto:** escalação de privilégio real e verificada (`clancy` nasce não-admin e vira admin). **Não inflar** — o admin só lista handles; **não** é vazamento de dados (o corpo traz handles) nem bypass de autenticação (o token é o mesmo, legítimo).

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; toolchain herdado e lido dos arquivos de 01–06; URL do primer verificada por fetch (200, sem redirect, âncora presente, conteúdo conferido) e seções do RFC 9110 (§15.3.5, §15.5.2, §15.5.4) conferidas em texto bruto nesta fase; shape TS, comportamento dos endpoints nos dois gêmeos, o teste de `__proto__`-no-body e o foil allow-list-vs-deny-list validados em protótipo com o toolchain exato (ver "Validação de typecheck e runtime"). Resto é smoke test em container na Fase 2.

---

## Notas específicas pro Claude Code

- **Princípio guia:** a lição é **autorização se aplica no nível da propriedade também na ESCRITA** — o write tem que ser escopado aos campos que o chamador pode setar. Se o aluno sair achando "escrevi no registro de outro" (BOLA) ou "invoquei uma função admin desprotegida" (BFLA/04), o átomo falhou.
- **Self-update é a disciplina.** O `clancy` escreve no **próprio** registro. **Nunca** escrever a prosa como se ele escrevesse no de outro. O `403` de `PATCH /users/alice` é o que crava "não é BOLA".
- **DISCIPLINA ANTI-04, a mais importante deste átomo.** A rota admin **está guardada**, com a guarda **byte-idêntica ao fix do 04**, e o `403` do Step 3 prova. O bug é o **papel forjado**, não função desprotegida. Repetir isso em três lugares (Step 3, Step 5 item 2, DIFF). **Creditar o 04 sem reabrir a lição dele.**
- **A prova é o termômetro, nunca o eco.** O `PATCH` responde `204` **nos dois gêmeos** — de propósito. Qualquer frase que sugira que o `204` prova a escrita está **errada** e tem que ser reescrita. Esta é a lição mais cara da Fase 1 e o átomo existe pra cravá-la.
- **UM handler no "Spot the bug": o `PATCH`.** O termômetro entra no Step 3 como a função guardada. **NÃO** mostrar dois handlers lado a lado (isso é o 05) nem inventar um terceiro.
- **Fix = allow-list de escrita, no MESMO `USERS.set`.** **NÃO** usar mutate-in-place no `fixed/`; **NÃO** usar deny-list como fix (ela é FOIL no DIFF, e falha aberto). Dizer por que a allow-list falha fechado faz parte da lição.
- **O ternário `typeof` é parte de "nomear o campo", não uma lição de validação.** Uma frase no DIFF. **Nenhuma** biblioteca de schema/validação entra neste átomo.
- **`is_admin` aqui é ESCRITO** (ao contrário do 06, onde era só lido). Não há `passwordHash` neste átomo. **Não** copiar o seed do 06 sem tirar o campo.
- **Simetria com o 06: creditar, não reescrever.** Três menções no máximo (Context, Spot the bug, Impact). O átomo é auto-contido pra quem não fez o 06.
- **`Map`, mas SEM narrativa de prototype pollution.** O que foi **testado** (o `__proto__` no body não polui) cabe em **uma frase no DIFF**, como fato verificado — nunca como lição, nunca como segundo eixo.
- **Status: `403`/`401` são herança (forward pro DIFF do 05, não recontar); o `204` é argumento NOVO** e fica no DIFF deste átomo, ancorado no RFC 9110 §15.3.5 e creditando a divergência em relação ao `200`+eco do 05.
- **Elenco:** `clancy` atacante **masculino**; `alice` só sustenta o `403` de posse e **não loga**. Sem personagem novo, **sem admin no seed**.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# bopla-mass-assignment — Broken Object Property Level Authorization (BOPLA)`. Headers de seção **traduzidos** no PT; termos técnicos em inglês.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série (frase única e densa, fechando com a categoria e o CWE entre parênteses — o 06 usou `API3 Broken Object Property Level Authorization, CWE-213`; para mass assignment o CWE idiomático é **CWE-915**, como o átomo web já registra — **conferir na geração**). O corte da release `v1.2` é trabalho de mantenedor, pós-merge (CLAUDE.md §12).
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 07 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): todos os itens do checklist acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8207` (vulnerable), `127.0.0.1:8307` (fixed). Bind **só** em `127.0.0.1`.

---

## Verificação factual dos átomos publicados (conferida LENDO os arquivos nesta fase)

A spec afirma herança e contraste com 01–06; tudo abaixo foi conferido **lendo os arquivos publicados nesta fase de planning** (não de memória):

1. **Toolchain** — `package.json` dos seis átomos com express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; scripts `start: tsx app.ts`, `typecheck: tsc --noEmit`; `name` por átomo, `private: true`, `type: module`.
2. **`Dockerfile`** — **md5 idêntico nos seis** (`cad28299…`): `node:24.21.0-slim`, `npm ci --omit=dev`, `COPY tsconfig.json` + `COPY app.ts`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm","start"]`.
3. **`tsconfig.json`** — **md5 idêntico nos seis** (`9a2dc4f6…`): `nodenext`, `target/lib es2024`, `types [node]`, `strict`, `noUncheckedIndexedAccess`, `esModuleInterop`, `noEmit`.
4. **`docker-compose.yml`** — bind `127.0.0.1`; `8201/8301` (01) … `8206/8306` (06). Este átomo: **`8207/8307`**.
5. **Bloco de auth** — `TOKENS = new Map<string,string>`, `issueToken` com `randomBytes(24).toString("base64url")`, `authenticate` por `Bearer`, `USERS.has(user)` no login, `res.set("WWW-Authenticate", "Bearer").sendStatus(401)` nos handlers. 01–03 usam `USERS = new Set([...])`; **04, 05 e 06 usam `USERS = new Map<string, User>`** (`User = { is_admin }` no 04; `{ displayName }` no 05; `{ displayName, passwordHash, is_admin }` no 06). Este átomo: `{ displayName, is_admin }`.
6. **Átomo 06 (`bopla-excessive-exposure`)** — `GET /users/:handle` com a guarda de posse e `res.json({ handle: req.params.handle, ...user })` no vulnerable; fix troca por `res.json({ handle: req.params.handle, displayName: user.displayName })`. Primer: Information disclosure. Estado **imutável** (só lê), prova **auto-contida**, foil **whitelist vs blacklist de leitura**, âncoras citadas acima. Este átomo é a **face de escrita** da mesma categoria, reusando a forma e invertendo a direção.
7. **Átomo 05 (`bfla-method-based`)** — `GET /users/:handle` guardado por posse; `PATCH /users/:handle` **sem** guarda no vulnerable (o bug), escrevendo com `user.displayName = req.body?.displayName ?? user.displayName` e respondendo **`res.json({ handle, displayName })` — `200` com corpo**. O DIFF do 05 afirma explicitamente que esse corpo é **eco do input** e **não** prova a escrita, e que a prova veio da vítima lendo o próprio registro. **O `204` deste átomo é divergência deliberada daquele `200`, e a spec manda creditá-la.** O fix do 05 acrescenta ao `PATCH` a guarda de posse byte-idêntica à do `GET`.
8. **Átomo 04 (`bfla-admin-function`)** — `POST /admin/users/:handle/promote` sem check de role no vulnerable; fix acrescenta **`  if (!USERS.get(caller)?.is_admin) return res.sendStatus(403);`** — a linha que este átomo reusa **byte-idêntica** no termômetro (conferido por `grep -Fxc` = 1 em ambos). Seed do 04 tem `carol` como admin legítima; **este átomo não seeda admin nenhum**.
9. **Átomos 01–03** — origem do check de posse (`order.owner === caller`, `operates(caller, storeId)`), e do critério `404`-vs-`403` (01/03 usam `404` indistinguível porque a existência do pedido é sensível). Este átomo usa `403` pelo critério de 05/06 (posse por identidade **antes** da busca).
10. **Elenco** — `clancy` atacante (masculino) em todos; `alice` vítima principal; `carol` admin no 04; `bob`/`carol` operadores no 03. Este átomo: `clancy` (edita o próprio) e `alice` (só sustenta o `403`), **sem admin**.
11. **H1** — 01–03: `# <id> — Broken Object Level Authorization (BOLA)`; 04/05: `# <id> — Broken Function Level Authorization (BFLA)`; 06: `# bopla-excessive-exposure — Broken Object Property Level Authorization (BOPLA)`. Este: **mesmo nome de classe do 06**, slug diferente.
12. **Primers publicados** — 01–03: IDOR (`/web-security/access-control/idor`); 04–05: Access control (`/web-security/access-control`); 06: Information disclosure (`/web-security/information-disclosure`), todos com o **H1 da página** como texto do link. Este átomo: seção **Mass assignment vulnerabilities** de `/web-security/api-testing` (não há página dedicada — 404 conferido em dois caminhos plausíveis).
13. **Átomo web `mass-assignment` (A01)** — publicado em `atoms/web/A01-broken-access-control/mass-assignment/`; Flask, `POST /profile` com `account.update(data)`, fix com `ALLOWED_FIELDS`, prova por `GET /profile` (read-back) **e** `GET /admin` (`403` → `200`), primer na **mesma URL** com texto "Mass assignment". **Não citar** nos docs deste átomo (ver "Política de cross-ref"); a divergência de desenho (sem read-back, `204`, termômetro) é deliberada e está justificada nesta spec.
14. **Publicação** — `atoms/api/ROADMAP.md`: 01–06 `[x]`, **07 (`bopla-mass-assignment`) `[ ]`**, 08+ `[ ]`. Árvore de `atoms/api/`: `API1-broken-object-level-authz/` (três átomos), `API3-broken-object-property-level-authz/` (**um** átomo — o 06; este entra como segundo) e `API5-broken-function-level-authz/` (dois átomos). A linha API3 da tabela de Cobertura do ROADMAP já lista os dois `bopla-*`.
15. **Comportamento herdado conferido em runtime no `app.ts` publicado do 06** — JSON malformado no `POST /login` responde `400` com stack trace no corpo HTML (handler de erro default do Express). Idêntico ao que este átomo fará; **não** é novidade nem lição deste átomo.
