# Spec — Átomo API 08: `auth-predictable-token`

> Documento de especificação para o Claude Code implementar o **oitavo átomo da série API** do projeto `atomicvulns` (Fase 2 API, "Property Authz & Auth", milestone `v1.2`; **terceiro átomo da fase**). Classe: **Broken Authentication**, o **API2:2023** do OWASP API Security Top 10 (2023). Este átomo **estreia a categoria API2**: a pasta `atoms/api/API2-broken-authentication/` **não existe ainda** e o 08 a cria, como o 06 criou a `API3-...` (diferente do 07, que apenas entrou numa pasta já aberta). Escrito com o template [`ATOM-SPEC-TEMPLATE-API.md`](../../templates/ATOM-SPEC-TEMPLATE-API.md).
>
> **A VIRADA DA SÉRIE — de authorization para authentication.** Os sete átomos anteriores perguntaram, de sete formas, **"você PODE fazer isto?"** — de quem é o objeto (BOLA, 01–03), você pode invocar esta função (BFLA, 04–05), quais campos pode ver/setar (BOPLA, 06–07). Todos trataram **o token como premissa confiável**: `authenticate()` devolvia uma identidade e o resto do handler decidia o que aquela identidade podia. Este átomo vira o holofote **pra dentro dessa premissa**: **"você É mesmo quem diz ser?"** O alvo é o mecanismo que os sete blindaram sete vezes — o **token**. A pergunta de auditoria cravada: **"o token é imprevisível pra quem não o recebeu?"** No `vulnerable/` a resposta é *não* — o token **é o identificador do usuário em base64url**, não entropia —, então o atacante **deriva** o token de outro usuário e **se passa por ele**. A falha é **anterior** à autorização: não é que um check de acesso faltou, é que a **identidade em si é forjável**, e com ela toda a autorização correta do sistema vira inútil.
>
> **BASE64URL É CODIFICAÇÃO, NÃO CRIPTO — e isso é a lição, não um detalhe.** O token vulnerável é o nome do usuário passado por `Buffer.from(user).toString("base64url")`. base64url é **codificação reversível** (um reencode de bytes pra um alfabeto seguro em URL), **não** um hash nem uma cifra. A lição é **AUTHENTICATION** — *"o servidor confiou num segredo que não era segredo"* —, **não** CRIPTO — *"eu quebrei o algoritmo"*. Não há algoritmo a quebrar: há um envelope a abrir e a refazer. Todo documento trata base64url como **codificação**, nunca como "cifra fraca" nem "hash fraco"; o aluno **não** pode sair achando que **assinar** o token resolveria a lição (é o que o **foil** do DIFF desmonta). O contraste com 01–07 mora no **código**: o fixed usa o **mesmo** `base64url`, alimentado com `randomBytes(24)` em vez do nome — mesma codificação, fonte oposta.
>
> **A GUARDA DE POSSE ESTÁ CERTA — o breach está a montante, na IDENTIDADE (disciplina herdada do 07, outro eixo).** A superfície é `GET /users/:handle` com a **mesma guarda de posse** de 05/06, **byte-idêntica e correta** (`if (req.params.handle !== caller) return res.sendStatus(403)`). Ela **não** é a falha — ela é o que **isola este átomo de BOLA**. O `clancy`, com o **próprio** token, em `GET /users/alice` leva **`403`**: a posse morde, ele não é dono. O bug não está na guarda; está em **quem a guarda compara** — o `caller`, que no `vulnerable/` vem de **decodificar o token**. Forje um token que decodifica pra `"alice"` e o `caller` **vira** `"alice"`; a guarda, correta, aprova, porque agora `handle === caller`. É o espelho exato da **disciplina anti-04 do 07**: lá a guarda **admin** estava certa e o bug era o **papel forjado**; aqui a guarda de **posse** está certa e o bug é a **identidade forjada**. Cravar em todo documento: *a guarda que você vê está certa; a mentira entra no `caller`, a montante.*
>
> **O DIFF NÃO CABE EM UMA LINHA — e isso é deliberado, decidido pelo mantenedor.** A previsibilidade só vira exploit se o servidor **DERIVA** a identidade (decode) em vez de **CONSULTAR** um vínculo que guardou (lookup). Isso toca **três pontos acoplados e inseparáveis**: (i) a **geração** do token (`issueToken`), (ii) a **resolução** em `authenticate`, e (iii) a **presença do mapa `TOKENS`** (que existe só no `fixed/`). Não dá pra ter token **auto-descritivo** E **lookup** ao mesmo tempo — são as duas pontas de um eixo conceitual único: **"de onde vem a identidade"** — do **conteúdo do token** (decode) ou de um **registro que o servidor guardou** (lookup). O DIFF documenta por que os três são inseparáveis, **como a NATUREZA da classe**, não como relaxamento de "um átomo = uma vuln" (que continua de pé: **uma vuln só** — identidade forjável). É o **primeiro** átomo da série cujo diff **modifica** o bloco de auth que os sete anteriores copiaram intacto.
>
> **Leitura obrigatória antes de gerar (CLAUDE.md §10.5), tudo já publicado em `main`:**
> 1. **Qualquer átomo de 01–07, inteiro, pelo BLOCO DE AUTH byte a byte** (`TOKENS`, `issueToken`, `authenticate`, `POST /login`): **05, 06 ou 07 servem**. Este é o **primeiro** átomo que **MODIFICA** esse bloco, então é obrigatório lê-lo **exato** do código publicado — o `fixed/` deste átomo **é** esse bloco, byte a byte, e o `vulnerable/` é a sua deformação mínima e consciente. Não reescrever de memória.
> 2. **`atoms/api/API5-broken-function-level-authz/bfla-method-based/` (05) e `atoms/api/API3-broken-object-property-level-authz/bopla-excessive-exposure/` (06), inteiros** — a origem da superfície **`GET /users/:handle` com guarda de posse** (correta, reusada aqui byte-idêntica) e o argumento `403`/RFC 9110. O `GET` deste átomo tem a forma do `GET` **fixed do 05** (retorna campos nomeados, não `...user`), estendida com o campo privado `email`.
> 3. **`atoms/api/API3-broken-object-property-level-authz/bopla-mass-assignment/` (07), inteiro** — o **par imediato** (átomo anterior) e o modelo de **densidade/estrutura/tom** mais recente desta spec, e a **disciplina anti-04** cujo formato este átomo espelha (guarda correta, o forjado é o que a alimenta).
>
> Tudo o que esta spec afirma sobre 01–07 foi conferido **lendo os arquivos publicados em `main`**, não de memória (ver "Verificação factual dos átomos publicados").
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit de código, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`). A validação em protótipo descartável foi feita **nesta fase** (ver "Validação de typecheck e runtime").

---

## Identidade

- **ID:** `auth-predictable-token`
- **Categoria OWASP (pasta / API Security Top 10 2023):** **API2 — Broken Authentication**
- **Pasta:** `atoms/api/API2-broken-authentication/auth-predictable-token/` — a pasta de categoria **NÃO EXISTE AINDA**. Este átomo **cria** `API2-broken-authentication/` e é o **primeiro** átomo dela (como o 06 criou `API3-...`). Criar a pasta de categoria **e** a do átomo.
- **Número sequencial (série API, conta do 01):** 08
- **Porta vulnerable:** `127.0.0.1:8208`
- **Porta fixed:** `127.0.0.1:8308`
- **Porta interna do container:** `3000` (igual a 01–07). Compose mapeia `127.0.0.1:8208:3000` e `127.0.0.1:8308:3000`.
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1); `ENV HOST=0.0.0.0` só dentro do container.
- **Fase / milestone:** Fase 2 API, `v1.2` (oitavo átomo; terceiro da fase).
- **Branch de trabalho:** `atom/auth-predictable-token` — criada na Fase 2 a partir de `main` atualizada.
- **H1 dos READMEs (idêntico em EN e PT):** `# auth-predictable-token — Broken Authentication`. O título nomeia a **classe**; o slug qualifica a variante (token previsível) (CLAUDE.md §5). **Primeiro H1 da série com este nome de classe** (01–03 BOLA, 04–05 BFLA, 06–07 BOPLA; 08 abre Broken Authentication).
- **Theory primer:** ver seção "Theory primer" (página **Authentication vulnerabilities** da PortSwigger — URL verificada por fetch nesta fase: HTTP 200, 0 redirects, H1 `Authentication vulnerabilities`).

---

## A tese do átomo

> **Autenticação prova *quem você é* — e um token previsível não prova nada, porque qualquer um pode produzi-lo.** O token emitido no login **é o identificador do usuário codificado em base64url**, não um valor aleatório. Como base64url é **reversível** e o insumo é um **handle público**, o atacante **reconstrói** o token de qualquer usuário a partir do nome e **se autentica como ele**. A pergunta de auditoria é **"o token é imprevisível pra quem não o recebeu?"** — e a resposta, no `vulnerable/`, é *não*.

### O eixo é a ORIGEM da identidade — decode vs. lookup

Os átomos de 01–07 perguntavam o que uma identidade **autenticada** podia fazer (authorization). Este pergunta se a identidade é **autêntica** (authentication). A diferença vive em **uma função** — `authenticate` — e na forma como ela responde "quem é o portador deste token?":

- **`vulnerable/` — DECODE.** `authenticate` **abre** o token e **acredita** no que leu: `Buffer.from(token, "base64url").toString("utf8")`. A identidade **vem do conteúdo do token**. Quem controla o conteúdo (qualquer cliente) controla a identidade.
- **`fixed/` — LOOKUP.** `authenticate` **consulta** um vínculo que o servidor guardou no login: `TOKENS.get(token)`. A identidade **vem de um registro server-side**. O token é um **ponteiro opaco** (`randomBytes(24)`): não carrega identidade nenhuma, só aponta pra uma que o servidor registrou.

**A falha não é "o token é fraco" no sentido cripto — é que a identidade VIAJA no token de forma derivável.** Fortalecer o token sem tirar a identidade de dentro dele (por exemplo, **assinando-o**) não ataca a raiz — é o que o **foil** do DIFF demonstra. A correção é mudar a **origem** da identidade: do token (que o cliente autora) pro servidor (que só ele autora).

### base64url é codificação, não criptografia — a lição depende disso

base64url mapeia 3 bytes em 4 caracteres de um alfabeto seguro em URL (`A–Z a–z 0–9 - _`, sem padding `=`). É uma **representação**, não um **segredo**: qualquer um codifica e decodifica, sem chave. Chamar isso de "cifra fraca" ou "hash fraco" **erra a lição** — não há criptografia aqui, nem boa nem má. Há uma **identidade pública embrulhada num papel transparente**. O exploit não "quebra" nada: ele **lê** o papel (seu próprio token → seu nome) e **embrulha outro** (o nome da vítima → o token dela). A classe é **Broken Authentication** porque o sistema aceitou, como prova de identidade, algo que **não é segredo de ninguém**.

### A guarda de posse está correta — isola de BOLA (disciplina herdada do 07)

A superfície é `GET /users/:handle`, e a guarda `if (req.params.handle !== caller) return res.sendStatus(403)` é a de 05/06, **byte-idêntica e correta**. Ela **passa a mentira adiante** sem culpa própria: compara `handle` (da URL) com `caller` (de `authenticate`). No `vulnerable/`, `caller` é **forjável**, então a guarda — fazendo exatamente o que deve — aprova um dono falso.

- **`clancy` com o próprio token em `GET /users/alice` → `403`.** A posse **morde**: ele não é dona do registro `alice`. Isso **prova** que a rota **não** tem bug de authz. Não é BOLA (check ausente); é identidade forjada.
- **Forje `base64url("alice")`, refaça o MESMO request trocando só o `Authorization` → `200` + o email da `alice`.** A guarda aprovou porque agora `caller === "alice"`. **A rota é a mesma, a authz é a mesma e está correta — mudou só quem o token diz que você é, e o servidor acreditou.**

**Espelho da anti-04 do 07:** lá a guarda **admin** estava certa e o bug era o **papel** forjado (gravado por mass assignment); aqui a guarda de **posse** está certa e o bug é a **identidade** forjada (derivada do token). Mesma disciplina, eixo diferente: *a guarda que você vê está certa; o breach está a montante.*

### O erro de leitura a combater — e ele determina o desenho

Três leituras erradas prováveis — **duas firmes** e **uma terceira cortável**. O WALKTHROUGH **nomeia cada uma e a desmonta** (ver "Walkthrough", Step 5):

1. **"Isto é BOLA — li o objeto de outro usuário." (LEITURA ERRADA CENTRAL — mais peso.)** O aluno vê `GET /users/alice` respondendo `200` com dado da vítima e pensa "acessei objeto alheio por falta de check". **Desarme:** o `403` do baseline (seu token em `/users/alice`) **prova** que o check de posse existe e **morde**. Você **não** leu o objeto de outro por ausência de check — você **virou** a `alice`. Authz **certa**, authentication **quebrada**. Em BOLA a identidade é real e o check falta; aqui o check está certo e a **identidade** é falsa.
2. **"Isto é roubo de token / replay."** O aluno pensa "você interceptou o token da `alice`". **Desarme:** você **não interceptou nada** — não houve sniff, nem sessão roubada, nem replay de credencial capturada. Você **construiu** o token da vítima a partir do **nome** (que é público — aparece no login). Não é furto; é **fabricação**.
3. **"É criptografia fraca." (cortável)** O aluno pensa "o hash/a cifra do token é fraca". **Desarme:** base64url **não é** criptografia — é codificação. Não há nada a **quebrar**, só a **decodificar**. A falha não é um algoritmo ruim; é **não haver segredo nenhum**. **Cortar se não couber em frase limpa** — mas é a leitura que mais protege o aluno de "achar que assinar resolve".

### Por que API2 (Broken Authentication)

O bug **não é** "input virou código" (injection — nada é parseado nem executado), **não é** "um objeto fora do escopo foi tocado" (BOLA — a guarda de posse está correta e o `403` do baseline prova), **não é** "um campo que não devia entrar/sair" (BOPLA — não há mass assignment nem over-serialization; a resposta devolve ao dono o que o dono pode ver). É **"o mecanismo que prova identidade pode ser forjado por qualquer um"** — **API2** no OWASP API Security Top 10 **2023**. Situe nessa edição, **sem arqueologia** (CLAUDE.md §5). Referência OWASP em **texto simples** (`API2:2023`), **sem link** — o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (a linha API2 **já existe**, listando `auth-predictable-token`, `auth-no-lockout`, `oauth-client-cred-unverified`). Por ser vuln de **autenticação/lógica** (Trigger, não Payload — o exploit é um token legítimo-de-forma, construído a partir de dado público), o **passo de contraste obrigatório** "o que a vuln NÃO é" é mandatório.

---

## O que este átomo acrescenta (vs. 01–07)

**Honestidade pedagógica:** 01–03 ensinaram BOLA (eixo do objeto); 04–05 BFLA (eixo da função); 06–07 BOPLA (eixo da propriedade, leitura e escrita). Todos **autorizam uma identidade que assumiram verdadeira**. Este **credita e não reabre** nenhum deles. Ele existe por três eixos novos:

1. **Primeiro átomo de AUTHENTICATION da série.** 01–07 responderam "o que esta identidade pode fazer?"; 08 responde "esta identidade é autêntica?". É a **virada** anunciada no ROADMAP (Fase 2: "a passagem para authentication"). A lição é que **toda** a authorization correta dos sete átomos anteriores **pressupõe** uma identidade confiável — e este átomo ataca exatamente essa pressuposição.
2. **Primeiro átomo que MODIFICA o bloco de auth** que 01–07 copiaram byte a byte. Nos sete, `TOKENS`/`issueToken`/`authenticate` eram **infraestrutura intocada** e cripto-forte, de propósito (um token previsível ali seria uma segunda vuln). Aqui o bloco de auth **é a superfície do bug**: o `fixed/` **é** o bloco canônico; o `vulnerable/` é a sua deformação. O que era premissa vira objeto de estudo.
3. **Primeiro diff deliberadamente NÃO-unitário — e a spec explica por quê.** 06 e 07 tinham diff de uma linha; aqui o eixo único (**decode vs. lookup**) se materializa em **três pontos inseparáveis** (geração, resolução, mapa). É o átomo que ensina que "um átomo = uma vuln" é sobre **uma lição**, não **uma linha**: a previsibilidade e o uso-sem-lookup são **a mesma falha vista de dois lados**, e separá-las seria mentir sobre a classe.

> **Contraste a cravar (WALKTHROUGH e DIFF):** em 01–07, "o ataque **não toca** o token" era disciplina repetida (o aluno lê 01, 02, 05, 06, 07 e vê essa frase) — justamente pra isolar BOLA/BFLA/BOPLA de problemas de identidade. **Este átomo é o reverso: o ataque é SÓ sobre o token.** Nomear essa inversão, creditando a premissa que os sete trataram como confiável — é o fio que amarra a Fase 1 inteira a este átomo.

---

## Feature simulada — perfil de conta com um dado privado (API-only, sem HTML)

**Perfil de conta de uma plataforma multiusuário — a mesma superfície de 05/06, agora do lado da identidade.** Cada usuário tem um perfil com um **nome de exibição** (display name) e um **email** privado. A API de self-service deixa o usuário **ler o próprio perfil** (`GET /users/:handle`), protegido por uma guarda de posse: você só vê o **seu** registro. Do ponto de vista do produto: "você loga e vê o seu perfil, com os seus dados de conta". O que o dev errou foi **como o login prova quem você é**: o token que ele emite **é o seu nome de usuário, só que codificado** — então qualquer um que saiba o nome de outra pessoa produz o token dela e lê o perfil dela.

**API-only por natureza** (CLAUDE.md §3.3): **sem `templates/`, sem HTML, sem browser**. Respostas em `application/json` via `res.json(...)`; erros via `res.sendStatus(...)`. Corpo JSON só no `POST /login`; auth via header `Authorization: Bearer <token>`. **Trilha 100% Burp/curl.**

### A "descoberta" é abrir o próprio token — e o ataque é embrulhar outro nome

Não há sink, não há payload malicioso. O exploit tem duas metades: (i) a **descoberta** — o aluno loga como `clancy`, **decodifica o próprio token** e vê que não é opaco, é o nome dele em base64url; (ii) o **ataque** — ele **codifica o nome da vítima** no mesmo formato e usa como token. A técnica que o átomo ensina é reconhecer um token **auto-descritivo** (que carrega a identidade dentro) e explorá-lo construindo a identidade de outro. O `email` da vítima na resposta é a **prova auto-contida**.

---

## Autenticação — AQUI MORA A VULN (a seção principal, não premissa)

**Esta é a seção central do átomo.** Nos sete anteriores, "Autenticação" descrevia infraestrutura confiável e a lição estava noutra seção (Rotas/Fix). Aqui **a lição é a autenticação**: a falha, a prova e o fix vivem todos neste bloco. O template prevê exatamente isto: *"se o átomo é sobre a própria autenticação, o modelo de auth É a superfície do bug — descreva a falha aqui, não a mitigue."*

`POST /login` recebe `{ "user": "<nome>" }`, valida contra os usuários seedados (via `USERS.has(user)`) e devolve `{ "token": "<token>" }`. **NÃO é JWT.** A diferença entre os gêmeos vive **inteira** em como o token é **gerado** e **resolvido**:

### `vulnerable/` — o token é a identidade codificada

```ts
function issueToken(user: string): string {
  return Buffer.from(user).toString("base64url");           // VULNERABLE: the name, encoded -- not entropy
}

function authenticate(req: express.Request): string | null {
  // VULNERABLE: decode the token and trust whoever it spells.
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return Buffer.from(token, "base64url").toString("utf8") || null;
}
```

- **`issueToken` NÃO guarda nada.** Não há `TOKENS.set`. O token é uma **função pura** do nome: `clancy` → `Y2xhbmN5`, sempre, em qualquer processo, pra sempre.
- **`authenticate` DECODIFICA e confia.** Não há `TOKENS.get`. O `caller` é literalmente o que o token disser, desde que decodifique pra uma string não-vazia.
- **`|| null` (não `?? null`) é deliberado e necessário.** `Buffer.from(token,"base64url").toString("utf8")` devolve **`""`** (string vazia) quando o token é ausente/vazio/indecodificável-pra-bytes (ex.: `"!!!"`, `"%%%"`, header ausente). `"" || null` → `null` → dispara o `401`. **Sem** o `|| null`, um token vazio viraria o `caller` `""` (falsy mas não-nulo) e o `401` **nunca** dispararia — nem pra request sem `Authorization`. O `|| null` é o que preserva o `401` honesto pra "sem/ruim token" (ver "Status code", a sutileza do 401 ausente). **Validado:** sem header → `401`; `Bearer !!!` → `401`.
- **Sem `import { randomBytes }`** no `vulnerable/` — não há aleatoriedade a importar. (O TS fica limpo; ver "Validação".)

### `fixed/` — o bloco de auth canônico de 01–07, byte a byte

```ts
import { randomBytes } from "node:crypto";
// ...
const TOKENS = new Map<string, string>();                   // opaque token -> username (in-memory; NOT a JWT)

function issueToken(user: string): string {
  const token = randomBytes(24).toString("base64url");      // crypto-strong opaque value
  TOKENS.set(token, user);
  return token;
}

function authenticate(req: express.Request): string | null {
  // Authentication only: resolve the Bearer token to a username, or null.
  const header = req.header("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return TOKENS.get(token) ?? null;
}
```

- **Este bloco é o de 01–07, copiado, não reescrito.** Conferido nesta fase: `md5` do trecho `issueToken`…fim de `authenticate` do `fixed/` bate com 05/06/07; o handler `POST /login` e o rodapé `listen` também. **A fonte da verdade é o código publicado** — ler e copiar, não digitar de memória.
- **`?? null` (nullish), não `|| null`.** `Map.get` devolve `string | undefined`; `?? null` converte o `undefined` do miss. (Os dois gêmeos têm `authenticate: string | null` — assinaturas coerentes.)
- **O token é opaco:** `randomBytes(24)` → 24 bytes aleatórios → 32 caracteres base64url. Não carrega identidade; só aponta pra uma que `TOKENS` registrou no login.

**O que a auth prova e o que NÃO prova (a lição, explícita):**

- **Autenticação prova *quem você é* — e é exatamente isso que o `vulnerable/` falha em provar.** No `fixed/`, só quem recebeu o token no login tem como apresentá-lo (ele é imprevisível). No `vulnerable/`, **qualquer um** que saiba um handle apresenta o token daquele handle.
- **O token ausente/ruim → `401` COM `WWW-Authenticate: Bearer`**, na rota protegida, nos dois gêmeos — **mas o que conta como "ruim" difere**, e essa diferença é material (ver "Status code").
- **A posse (*este objeto é seu?*) é checada e está CORRETA nos dois gêmeos.** Ela não é a falha; é o que isola de BOLA. No `vulnerable/`, ela aprova um dono **falso** porque o `caller` que ela recebe é forjado — a guarda está certa, a entrada é mentira.

**Usuários seedados (elenco da série — CLAUDE.md §5):**

- **`clancy`** — o **atacante** (você). Tem o **próprio** token (o baseline legítimo: self-read do próprio perfil → `200` com o email dele). (`clancy` é **masculino**; nos docs PT, "o atacante", "você mesmo", "dele". O masculino genérico do **papel** — "o dono", "o chamador" — coincide com o da pessoa; não há distinção a manter.)
- **`alice`** — a **vítima impersonada**. O atacante **nunca recebe** o token dela; ele o **constrói** a partir do handle `alice` e lê o perfil privado dela. `alice` **não loga** em nenhum passo do walkthrough.

**Requisito de README (EN+PT) — declarar o atalho:** o login sem senha é um **atalho deliberado do laboratório, não a vulnerabilidade**. Uma frase, **sem citar átomo** (mesmo requisito de 01–07). **Cuidado redacional:** este átomo é sobre autenticação, então a frase do atalho tem que distinguir **com clareza** "login sem senha = atalho de palco" de "token previsível = a vuln". O passwordless **não** é a falha; a falha é o **formato do token** que o login emite. Escrever de modo que o aluno não confunda o atalho com a lição.

---

## Store / dados — dois usuários, um email privado cada

**Sem banco** (CLAUDE.md §3.4). Estruturas TS. O `USERS` é **só-leitura** neste átomo (ver "Estado"); o `TOKENS` existe **só no `fixed/`** e cresce no login.

```ts
// --- Simulated identity: a token minted at login; users read their own profile ---
// Each user owns exactly the record keyed by their own handle; ownership is handle == caller.
// email is private account data -- the owner may read it; nobody else should reach it.
// There is no is_admin and no passwordHash here: this atom is about WHO the caller is,
// not what role they hold (that is API5) nor which fields serialize (that is API3).
type User = { displayName: string; email: string };
const USERS = new Map<string, User>([
  ["clancy", { displayName: "Clancy Park",  email: "clancy@mail.example" }],    // attacker (you) -- reads his OWN profile for the baseline
  ["alice",  { displayName: "Alice Nguyen", email: "alice@secret.example" }],   // the impersonated victim -- her token is never issued to you
]);
```

- **`email` é o dado PRIVADO e a prova.** Domínios reservados/óbvios de teste (`@mail.example`, `@secret.example`) — RFC 2606 reserva `.example`; **sem PII real** (CLAUDE.md §8.3). O `secret.example` da `alice` sinaliza, só pelo texto, "isto era pra ser privado".
- **SEM `is_admin`.** Não há privilégio a escalar — **não é authz**. Incluir um flag de papel convidaria a leitura "virei admin" (isso é 04/07). A prova é **ler dado privado da vítima**, não ganhar poder.
- **SEM `passwordHash`.** Era o vazamento do 06; aqui não serve a nada e o login é passwordless. **Não incluir.**
- **Posse = `handle === caller`.** Herdada de 05/06. Aqui ela **está correta** e **afasta o BOLA**; a falha é o `caller` que a alimenta.
- **`clancy` tem email próprio pro baseline.** `GET /users/clancy` com o token do `clancy` → `200` com `clancy@mail.example`: self-read legítimo, a feature funcionando. É o contraste honesto que mostra que a rota **serve o dono** corretamente — antes de o ataque mostrar que "dono" é forjável.
- **Dois usuários, dois campos, nenhum a mais.** Superfície mínima.

### Por que `Map`, e o que ele defende (e não) aqui

**Decisão do mantenedor: `Map<string, User>` pro `USERS`, por continuidade com 04–07.** `Map.get(req.params.handle)` tipa o registro como `User | undefined`, forçando a guarda `!user` (herança estrutural; ver "Anatomia"). O `USERS` **não** é tocado pelo ataque (o `GET` só lê). O `TOKENS` do `fixed/` é `Map<string, string>` — idêntico a 01–07.

> **Nota de segurança do decode (validada, e material do DIFF em uma frase).** No `vulnerable/`, `authenticate` faz `Buffer.from(token, "base64url").toString("utf8")`. Um token que decodifica pra **bytes não-UTF-8** (ex.: `"////"`) vira uma string de caracteres de substituição (U+FFFD) — **truthy**, logo um `caller` não-vazio que **não** é handle seedado → cai na **posse** (`403`) ou no `!user` (`404`), **nunca `500`**. **Validado:** `Bearer ////` → `403`; `Bearer Zm9v` (`"foo"`) em `/users/foo` → `404`; nenhum crash. O decode é **total** (nunca lança): é por isso que o servidor "confia em qualquer coisa". Documentar como fato verificado, não como lição paralela.

---

## Estado — imutável (o átomo só LÊ); o `TOKENS` do fixed cresce, mas não é a lição

**Diferente do 07** (que escrevia no `USERS`), este átomo **não muda o store de usuários**: `GET /users/:handle` é **só-leitura e idempotente**. Não há ordem de passos a respeitar, não há "antes/depois".

- **`USERS` nunca muda.** Reler `GET /users/alice` com o token forjado dá `200` + o mesmo email, quantas vezes forem. Sem dependência de ordem.
- **O `TOKENS` do `fixed/` cresce no login** (cada login registra um par token→usuário). Isso é **mecânica da auth**, não a lição — e **não existe no `vulnerable/`** (que não guarda nada). Mencionar só pra explicar por que o `fixed/` sobrevive a restart diferente do `vulnerable/`.
- **CONSEQUÊNCIA REAL a documentar (impacto honesto, validado por lógica do código):** no `vulnerable/`, **restart não invalida token nenhum** — não há estado por trás dele; `base64url("alice")` vale antes e depois do restart, pra sempre. No `fixed/`, restart **esvazia** `TOKENS` → todo token emitido vira `401` (religar). **A impossibilidade de revogar** um token previsível é parte do impacto, sem inflar: um token que o servidor não registrou, ele também não consegue desregistrar.
- **Gêmeos independentes.** Cada build sobe o próprio seed e (no `fixed/`) o próprio `TOKENS` vazio.
- **Requisito de README (EN+PT), a única casa da frase do restart:** uma frase diz que a identidade do `fixed/` vive num mapa em memória que o restart zera (religar emite tokens novos), e que no `vulnerable/` o token não tem estado por trás — derrubar/subir não muda nada, porque não há nada a mudar. **Não** repetir no WALKTHROUGH nem no DIFF.

---

## Rotas — duas rotas, nenhuma a mais

Imports no `fixed/`: `import express from "express";` e `import { randomBytes } from "node:crypto";`. No `vulnerable/`: **só** `import express from "express";` (sem `randomBytes`). Bootstrap (`const app = express();` + `app.use(express.json());`), `USERS`, e o rodapé `listen` são **idênticos** entre os gêmeos. O que **difere** é o bloco de auth (`TOKENS`, `issueToken`, `authenticate`) — ver "Autenticação" e "Fix". Superfície: **duas rotas** — `POST /login` e `GET /users/:handle` (byte-idêntica nos dois gêmeos).

**O que NÃO existe, e por quê:**

- **SEM `GET /me` — não criar, nem como opção.** Seria **tautológico**: "quem sou eu?" → o servidor devolve quem o token diz, o que apenas **reafirma** a identidade forjada sem provar acesso a dado de **outro**. A prova é o dado **privado da vítima** (`GET /users/alice`), e o papel de "o servidor me chama de X" já é cumprido pela **decodificação CLI do próprio token** no Step 3 — sem rota nova. A superfície é **exatamente duas rotas**; **não** criar `/me` em nenhuma hipótese.
- **SEM rota admin, SEM `PATCH`/`DELETE`, SEM listagem pública, SEM índice de rotas.** Superfície mínima. Não há escrita (não é 05/07), não há papel (não é 04/06-admin).
- **SEM `GET /users` (coleção).** A prova é um registro privado nomeado (`alice`), não uma coleção.

### `POST /login` — obter o próprio token (handler idêntico entre os gêmeos; o token emitido difere)

Recebe `{ "user": "<nome>" }`, valida contra `USERS` (via `USERS.has(user)`), devolve `{ "token": issueToken(user) }`. **O handler é byte-idêntico nos dois gêmeos** — o que difere é o `issueToken` que ele chama. Usuário desconhecido/ausente → `400` (higiene).

```ts
app.post("/login", (req, res) => {
  const user = req.body?.user;
  if (!USERS.has(user)) return res.sendStatus(400);
  res.json({ token: issueToken(user) });
});
```

- **O handler NÃO está no diff; o `issueToken` está.** O diff do `POST /login` é zero linhas; a diferença de comportamento (token previsível vs. opaco) vem da função que ele chama. Cravar isso no DIFF: *a rota de login é a mesma; o que mudou foi o que "emitir um token" significa.*
- **O handle viaja no login.** O `user` do body é o nome público; é o insumo do token. Nomear no walkthrough que **handles são públicos** (premissa do impacto): o atacante sabe `alice` porque handles aparecem no login/na plataforma, não porque vazaram.

### `GET /users/:handle` — ler o próprio perfil (a superfície; byte-idêntica nos dois gêmeos)

Autentica (Bearer → `caller`), confere a **posse** (`:handle === caller`, senão `403`), busca o registro, devolve os campos do perfil. **Byte-idêntica em `vulnerable/` e `fixed/`** — **fora do diff**. A diferença entre os gêmeos é **quem `authenticate` diz que o `caller` é**, não esta rota. Handler **≤ ~30 linhas** (tem 7).

```ts
// Ownership-guarded profile read. IDENTICAL in both builds -- this guard is NOT the bug.
// It compares the URL's handle against the caller that authenticate() returned. The guard is
// correct; in the vulnerable build the caller it trusts is forgeable, one layer up.
app.get("/users/:handle", (req, res) => {
  const caller = authenticate(req);
  if (caller === null) return res.set("WWW-Authenticate", "Bearer").sendStatus(401);
  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only
  const user = USERS.get(req.params.handle);
  if (!user) return res.sendStatus(404);
  res.json({ handle: req.params.handle, displayName: user.displayName, email: user.email });
});
```

- **A guarda de posse é byte-idêntica à de 05/06** (`grep -Fxc` = 1; conferido nesta fase). Ela **não é a falha** — é o que **afasta o BOLA** e dá o `403` do baseline (`clancy` em `/users/alice` com o próprio token).
- **`caller` é o ponto onde a mentira entra.** No `vulnerable/`, `authenticate` o deriva do token; forjar o token forja o `caller`. A rota **confia** no `caller` como qualquer rota deve confiar no retorno de `authenticate` — a traição está **dentro** de `authenticate`, não aqui.
- **A resposta devolve `email` — e isso NÃO é over-serialization (não é o 06).** Os **dois** gêmeos devolvem `email`; ele é dado privado que **o dono pode ver**. A falha não é "um campo vazou na resposta" (06); é "a pessoa errada é o dono". Cravar pra não confundir com BOPLA: aqui a resposta está **correta pro dono** — o problema é que "dono" foi forjado. (Por isso **não** se usa `...user` nem se esconde `email`: a lição não é o shape da resposta.)
- **O `404` do `!user` é higiene, byte-idêntica, raramente alcançável.** No `vulnerable/`, é alcançável por um caminho exótico: um token que decodifica pra um handle **não-seedado igual ao `:handle`** (ex.: `Bearer Zm9v` = `"foo"` em `GET /users/foo` → posse passa, `!user` → `404`). No `fixed/`, inalcançável (o token nunca resolve pra handle não-seedado). **Validado nos dois.**

> **Bind do servidor** (rodapé idêntico a 01–07): `const PORT = Number(process.env.PORT ?? 3000); const HOST = process.env.HOST ?? "127.0.0.1"; app.listen(PORT, HOST);` — **validado nesta fase**: sem `PORT`, sobe em `3000`; o socket escuta em `127.0.0.1` (confirmado no `ss -ltnp`), não em `0.0.0.0`.

> **UM handler no "Spot the bug": `authenticate` (o do `vulnerable/`).** A falha não está numa **rota** — está na **função de autenticação**. O "Spot the bug" mostra `authenticate` decodificando; o `GET /users/:handle` é apresentado como a rota **corretamente guardada** cuja entrada (`caller`) é envenenada a montante. **NÃO** mostrar as duas rotas como se uma fosse "a vulnerável" (isso é 05); a rota não é o bug.

---

## Fix — identidade opaca com vínculo server-side (o bloco de 01–07), e por que o eixo não é uma linha

O gêmeo `fixed/` **é** o bloco de auth canônico de 01–07, byte a byte: `issueToken` gera `randomBytes(24).toString("base64url")` e **guarda** `TOKENS.set(token, user)`; `authenticate` faz `TOKENS.get(token) ?? null` (**lookup**, não decode); e o mapa `const TOKENS` existe pra sustentar o vínculo. O `vulnerable/` é a **remoção** desses três — o token vira função pura do nome e a resolução vira decode.

```diff
- // vulnerable: identity travels INSIDE the token (base64url of the name), resolved by decoding it
- function issueToken(user: string): string {
-   return Buffer.from(user).toString("base64url");           // the name, encoded -- not entropy
- }
- function authenticate(req: express.Request): string | null {
-   const header = req.header("authorization") ?? "";
-   const token = header.startsWith("Bearer ") ? header.slice(7) : "";
-   return Buffer.from(token, "base64url").toString("utf8") || null;   // decode and trust
- }
+ // fixed: the token is an opaque pointer; identity lives in a record the server kept at login
+ const TOKENS = new Map<string, string>();                   // opaque token -> username
+ function issueToken(user: string): string {
+   const token = randomBytes(24).toString("base64url");      // crypto-strong opaque value
+   TOKENS.set(token, user);                                  // bind token -> identity, server-side
+   return token;
+ }
+ function authenticate(req: express.Request): string | null {
+   const header = req.header("authorization") ?? "";
+   const token = header.startsWith("Bearer ") ? header.slice(7) : "";
+   return TOKENS.get(token) ?? null;                         // look up; an unknown token is nobody
+ }
```

(No topo, o `fixed/` acrescenta `import { randomBytes } from "node:crypto";` — a quarta linha do diff, exigida pela geração do token.)

**A leitura correta do fix (cravar no DIFF):** a correção **não** é "um token mais forte". É **mudar a origem da identidade**: tirá-la de **dentro do token** (onde o cliente a autora) e colocá-la num **registro do servidor** (onde só o servidor a autora). O token deixa de **afirmar** quem você é e passa a **referenciar** uma afirmação que o servidor guardou. Por isso `randomBytes`: um ponteiro opaco **não pode** ser derivado de um handle — não há o que decodificar, só o que procurar, e procurar um token que ninguém registrou devolve "ninguém" (`401`).

### Por que o diff toca TRÊS pontos, e por que são inseparáveis

Este é o ponto que a spec existe pra blindar. O diff **não cabe em uma linha**, e isso **não** afrouxa "um átomo = uma vuln":

- **Os três pontos são um eixo só.** (i) `issueToken` com `randomBytes`+`TOKENS.set`, (ii) `authenticate` com `TOKENS.get`, (iii) a existência de `const TOKENS`. Eles são **as faces de uma única decisão**: *a identidade vem do conteúdo do token (decode) ou de um vínculo guardado (lookup)?* Não existe meio-termo coerente: um token **opaco** (iii + i) **exige** lookup (ii), porque não há identidade dentro pra decodificar; um token **auto-descritivo** (vulnerable) **dispensa** `TOKENS`, porque a identidade já viaja nele. **Mudar um ponto sem os outros não compila como lógica** — um `authenticate` com `TOKENS.get` sem um `issueToken` que faça `TOKENS.set` autentica **ninguém**; um `issueToken` com `randomBytes` sem lookup perde a identidade.
- **É a NATUREZA da classe, não um relaxamento da regra.** A regra "um átomo = uma vuln" é sobre **uma lição**: *identidade forjável*. A lição é **uma**. O que são três é a **expressão em código** dessa lição, porque authentication-por-token-opaco é, por construção, um trio generate/store/resolve. Documentar assim: **uma vuln, um eixo, três pontos acoplados** — e dizer explicitamente que separá-los seria **mentir** sobre como a classe funciona.
- **Contraste honesto com 06/07 (uma frase):** lá o diff era **uma linha** porque a lição era **uma projeção** (um `res.json`, um `USERS.set`); aqui a lição é um **mecanismo** (como a identidade nasce e é resolvida), e mecanismo tem partes. **Não** é mais complexo por desleixo; é mais largo porque a classe é mais fundamental.

### FOIL no DIFF: assinar o token = a quase-correção ERRADA (validado nesta fase)

Mostrar, no DIFF, a alternativa **descartada** — e por que foi descartada (mesmo papel do foil whitelist-vs-blacklist de 06/07):

```ts
// CONSIDERED AND REJECTED -- sign the token so it can't be forged, but keep the identity inside it.
import { createHmac, timingSafeEqual } from "node:crypto";
const SECRET = "changeme";
function issueToken(user: string): string {
  const body = Buffer.from(user).toString("base64url");
  const sig = createHmac("sha256", SECRET).update(user).digest("base64url");
  return `${body}.${sig}`;                                   // name.signature -- still self-describing
}
function authenticate(req: express.Request): string | null {
  const raw = (req.header("authorization") ?? "").replace(/^Bearer /, "");
  const [body, sig] = raw.split(".");
  if (!body || !sig) return null;
  const user = Buffer.from(body, "base64url").toString("utf8");
  const expected = createHmac("sha256", SECRET).update(user).digest("base64url");
  const a = Buffer.from(sig), b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  return user;                                               // verified -- but identity still came from the token
}
```

- **A assinatura "funciona" contra ESTE exploit.** Um atacante que só sabe o nome `alice` **não** consegue produzir o HMAC sem o `SECRET`, então `base64url("alice")` sozinho não passa. **Validado nesta fase:** o foil **type-checa** (`tsc --noEmit` exit 0) e, em runtime, um token legítimo de `alice` verifica (retorna `"alice"`), enquanto um `base64url("alice")` **sem** assinatura é rejeitado.
- **Mas ela erra a LIÇÃO.** A identidade **continua viajando no token** — agora com integridade. O fix de verdade é mais **fundamental**: a identidade **não devia** viajar no token de forma derivável **de jeito nenhum**; o vínculo opaco server-side (lookup) é a correção, não "remendar o token auto-descritivo com uma assinatura". A assinatura troca "qualquer um forja" por "quem tem o segredo forja, e o token vira um mini-JWT caseiro" — herdando **toda** a superfície de gestão de chave/algoritmo que o token opaco **não tem**.
- **E abre uma porta que este átomo NÃO quer abrir:** assinatura/HMAC/JWT é **outra conversa** (gestão de segredo, confusão de algoritmo, expiração). Trazê-la como "o fix" arrastaria o átomo pra uma classe inteira que não é a dele. O foil existe pra **fechar** essa porta explicitamente: *assinar parece resolver e type-checa, mas mantém a identidade no token — a lição é tirá-la de lá.*
- **Enquadrar sem apelo à autoridade, mas é honesto dizer:** tokens de sessão opacos resolvidos server-side são a recomendação padrão exatamente porque **não** carregam identidade forjável nem exigem gestão de chave no caminho crítico. Mencionar o princípio, **não** importar maquinaria: **nenhuma** lib de JWT/HMAC entra no átomo (o `node:crypto` do foil existe só no bloco ilustrativo do DIFF, não no `fixed/`, que usa só `randomBytes`).

> **Generalizar, não importar maquinaria.** Em 1–2 frases no DIFF: em escala, "token opaco + lookup" é o que frameworks de sessão fazem (um id de sessão aleatório mapeado a um registro server-side); JWT resolve o mesmo problema por **outro** caminho (claims assinados), com **outro** conjunto de armadilhas. **NÃO** trazer `jsonwebtoken`/`jose` pro átomo — só nomear que o token opaco é um dos dois caminhos canônicos, e o que este átomo ensina é **por que a identidade não pode ser derivável**, não qual biblioteca usar.

---

## Status code

- **`GET /users/alice` com token FORJADO (`vulnerable/`) → `200` + email da `alice`.** A guarda de posse aprova (`caller === "alice"` após o decode); a resposta é a do dono — só que o "dono" é forjado. **Este `200` é o clímax.** No `fixed/`, o mesmo token forjado → **`401`** (não está no `TOKENS`).
- **`GET /users/alice` com token LEGÍTIMO do `clancy` → `403` nos DOIS gêmeos.** Baseline de posse: credencial presente e válida (`clancy`), insuficiente pra **este** objeto (`alice`). RFC 9110 §15.5.4 (conferido em texto bruto nesta fase): *"If authentication credentials were provided in the request, the server considers them insufficient to grant access."* A guarda compara **identidade antes da busca**, não revela existência → sem username enumeration (mesmo argumento de 05/06; **forward**, não recontar).
- **`GET /users/clancy` com token do `clancy` → `200` (self-read).** A feature funcionando: o dono lê o próprio email. Baseline legítimo nos dois gêmeos.
- **Sem/ruim token → `401` com `WWW-Authenticate: Bearer`.** RFC 9110 §15.5.2 (conferido em texto bruto): o `401` **MUST** carregar o challenge; indica que a request *"lacks valid authentication credentials"*.
- **A SUTILEZA — o `401` honesto AUSENTE no `vulnerable/` (material do DIFF, não um passo do walkthrough):** o que conta como "token ruim" **difere** entre os gêmeos, e a diferença **é** a vuln.
  - No `fixed/`, **todo** token não-registrado → `401` (lookup miss). Existe a categoria "credencial presente mas **não reconhecida**".
  - No `vulnerable/`, essa categoria **quase não existe**. O servidor **decodifica qualquer coisa e confia**: um token que decodifica pra string **não-vazia** é aceito como **aquela identidade**. Então um token "ruim" cai em:
    - decode **vazio** (`""`, `"!!!"`, header ausente) → `null` → **`401`** (o único `401` honesto que o `vulnerable/` emite — e ele existe **por acidente** do `|| null`, não por reconhecer invalidade);
    - decode pra handle **não-dono** (`base64url("alice")` em `/users/clancy`, ou bytes não-UTF-8) → **`403`** (posse);
    - decode pra handle **não-seedado** igual ao `:handle` (`"foo"` em `/users/foo`) → **`404`** (`!user`).
  - **A AUSÊNCIA de um `401` honesto pra "token não reconhecido" é SINTOMA da vuln:** no `vulnerable/` **não há** token não reconhecido — todo decode não-vazio **é** reconhecido como alguém. Escrever isso no DIFF como **observação** (não como passo): *um servidor que nunca diz "não te reconheço" é um servidor que reconhece qualquer um.* **Validado:** `fixed/` `Bearer YWxpY2U` → `401`; `vulnerable/` `Bearer YWxpY2U` em `/users/clancy` → `403`, em `/users/alice` → `200`.
- **`POST /login` com usuário desconhecido/ausente → `400`** (higiene, igual a 01–07).
- **Nunca `500`.** O decode do `vulnerable/` é total (bytes não-UTF-8 viram U+FFFD, não exceção). **Validado:** nenhum caminho de token lixo dá `500`.

> **Regra de bolso (a mesma de 01/05/06/07):** a existência do alvo é sensível (ou revelada)? Aqui **não** — a posse compara identidade antes da busca → **`403`** honesto. O critério é o da série. **Não** reabrir; **forward** pro DIFF do 05.

---

## Padrão de prova — Trigger (forja de identidade; prova auto-contida no dado da vítima)

`[ ] Payload` / `[x] **Trigger**`. Não há sink nem input malicioso parseado: o exploit é **uma ação legítima-de-forma** — apresentar um `Authorization: Bearer <token>` bem-formado. O "malicioso" é só que o token foi **construído** a partir de um nome público, não recebido no login.

- **BASELINE ≠ EXPLOIT.** O baseline é o `403` de `GET /users/alice` com o **próprio** token do `clancy` (posse morde). O exploit é o **mesmo request**, trocando só o `Authorization` por `base64url("alice")` → `200`. **A transição `403 → 200`, mesmo request, só o token muda, é o clímax.**
- **A prova É auto-contida — contraste honesto com o 07.** No 07 a prova exigia um **segundo caminho** (o termômetro), porque o `204` não ecoava nada. Aqui a resposta do **próprio** request exploit **carrega o dado privado da vítima** (`email` da `alice`): o `200` **mostra** o que foi roubado. Cravar: *a prova é o dado privado da vítima chegando na resposta do atacante, pelo request do atacante.* (É o arranjo do 06 — prova no corpo da resposta — mas por **identidade forjada**, não over-serialization.)
- **Sem dependência de ordem** (o `GET` é idempotente; o `USERS` não muda). Diferente do 07.
- **Por ser Trigger → passo de contraste OBRIGATÓRIO** (CLAUDE.md §5) — ver Walkthrough, Step 5.

---

## Walkthrough — estrutura e requests (7 steps)

Trabalhado **100% no Burp** (Repeater), `curl`/`base64` como equivalentes — **API-only, SEM trilha browser** (CLAUDE.md §3.3). **Sem Intruder:** a tese é forja de **uma** identidade conhecida, não enumeração. Cada request é um bloco colável: request-line (verbo explícito) + `Authorization: Bearer <token>` + corpo JSON no login. Tokens do `clancy` são **placeholders** (`<clancy-token>`); o token forjado da `alice` é **literal** (derivável, e mostrá-lo literal é a lição). **Uma conta loga:** só o `clancy` (a `alice` **nunca** loga — o atacante **constrói** o token dela).

**Abertura direta, sem encenação** (CLAUDE.md §5): a primeira frase situa a feature e a falha — "uma API de perfil serve `GET /users/:handle` ao dono do registro, atrás de uma guarda de posse correta; o login emite um token, e esse token é o seu nome em base64url" — não um personagem. Definir todo termo não-óbvio na estreia: "authentication (provar *quem você é*) vs. authorization (provar *que você pode*)", "opaque token (token opaco — valor sem significado, que só o servidor resolve)", "base64url (codificação reversível, não criptografia)", "impersonation (passar-se por outro usuário)".

**REQUISITO DE REDAÇÃO — clareza é requisito DURO.** Cada bloco de request é precedido de uma linha de rótulo que diz **MÉTODO**, **ALVO** e **o que aquela request ISOLA**. Formato (herdado de 06/07):

> **EN:** `Method: GET · Target: alice (not yours) · Isolates: the same correct ownership check, approving a forged owner`
>
> **PT:** `Método: GET · Alvo: alice (não seu) · Isola: a mesma guarda de posse correta, aprovando um dono forjado`

A prosa **NOMEIA as leituras erradas e as desarma uma a uma** — **duas firmes** ("é BOLA" — com mais peso; "é roubo de token") e **uma terceira cortável** ("é cripto fraca").

### 1. Context
- API de perfil de conta; `GET /users/:handle` entrega o perfil **ao dono** (guarda de posse correta); auth por **Bearer token opaco** emitido no login. Isto é **Broken Authentication** — **API2:2023** do OWASP API Security Top 10.
- **A VIRADA, nomeada (o coração do Step):** até aqui (01–07) a pergunta foi sempre **"você PODE fazer isto?"** (authorization) — e o token era premissa confiável. Agora a pergunta é **"você É mesmo quem diz ser?"** (authentication). Definir **authentication vs. authorization** com a frase da PortSwigger (autenticação = verificar que você é quem afirma; autorização = verificar que você pode algo). Definir **opaque token**, **impersonation**.
- **A inversão da disciplina de 01–07 (uma frase, creditando):** nos átomos anteriores, "o ataque **não toca** o token" era a regra, pra isolar a authz. **Aqui o ataque é só sobre o token.** Você é o `clancy`, e vai descobrir que o seu token não é opaco — é o seu nome — e usar isso pra **virar** a `alice`. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar **UMA** função: `authenticate` do `vulnerable/`. Ela faz `Buffer.from(token, "base64url").toString("utf8")` — **decodifica o token e confia**. Pergunta de auditoria — **diferente** de BOLA/BFLA/BOPLA: não "cadê o check?" nem "quais campos?", mas **"o token é imprevisível pra quem não o recebeu?"** → **não**: ele é o nome, codificado. Quem sabe o nome, tem o token.
- **Contraste no CÓDIGO com 01–07 (cravar, uma frase):** o `fixed/` (e os sete átomos anteriores) usa o **MESMO** `base64url` — mas sobre `randomBytes(24)`, não sobre o nome, e **guarda** o par num mapa pra resolver por lookup. **Mesma codificação, fonte oposta, resolução oposta.** A string do token parece igual (base64url); o que mudou é **de onde ela vem** e **como é resolvida**.
- **Mostrar o `GET /users/:handle` como a rota CORRETAMENTE guardada** (não como "a vulnerável"): a guarda de posse é a de 05/06, byte-idêntica. A falha **não** está nela; está no `caller` que `authenticate` entrega. **NÃO** apresentar duas rotas como assimetria (isso é 05); a assimetria é entre **decode e lookup**, dentro de `authenticate`.

### 3. How auth works in this lab — abra o SEU token (DESCOBERTA, sem ataque ainda)
- Logar como `clancy` (`POST /login` com `{"user":"clancy"}`, bloco colável) → `{ "token": "<clancy-token>" }`.
- **Decodificar o PRÓPRIO token** — a revelação. O token do `clancy` é `Y2xhbmN5`. `echo -n Y2xhbmN5 | base64 -d` → **`clancy`**. (Ou, no Burp, o Decoder.) **Não é opaco — é o seu nome.** Sem segredo, sem aleatoriedade: o "token" é um envelope transparente com o seu handle dentro.
- **Nota de codificação:** `clancy` (6 bytes) dá `Y2xhbmN5` sem padding — `base64` e `base64url` coincidem aqui. O caso com padding (`alice`) e a explicação cheia ficam no Step 4.
- **Este Step é DESCOBERTA, o Step 4 é ATAQUE.** Aqui você só **lê** o que o seu token é. Ainda não forjou nada. **Se na redação os dois Steps ficarem redundantes, fundir** — mas a separação discovery→attack é didática: primeiro "o que É o meu token?", depois "construo o de outro".

### 4. Exploit — three movements, and the climax is `403 → 200` on one swapped header
Apontar o Burp pro `vulnerable/` em `127.0.0.1:8208`. Com o `<clancy-token>` do Step 3:

1. **Baseline — a posse morde.** `GET /users/alice` com o **seu** `<clancy-token>` → **`403`**.
   > `Method: GET · Target: alice (not yours) · Isolates: ownership exists and bites — your real identity is not alice`

   **CRAVAR:** a rota **tem** check de posse e ele **funciona**. Você, sendo `clancy`, **não** lê o perfil da `alice`. Guarde este `403` — o Step prova com ele que **não é BOLA**.
2. **Forja — construa o token da vítima.** O token é o nome em base64url; o nome da vítima é `alice`. `echo -n alice | base64` → **`YWxpY2U=`**.
   > `Method: (build) · Target: alice's token · Isolates: a victim token reconstructed from a public handle — no interception`

   **Nota de codificação (DURA, validada):** `alice` tem 5 bytes → 7 caracteres base64 **+ 1 padding `=`**, então `echo -n alice | base64` dá `YWxpY2U=` (com `=`), enquanto a forma **base64url** (a que o servidor usaria) é `YWxpY2U` (**sem** `=`). **O servidor aceita as duas** (o decoder base64url do Node tolera padding) — **validado**: tanto `YWxpY2U` quanto `YWxpY2U=` decodificam pra `alice`. Pra estes handles (ASCII minúsculo) base64 e base64url diferem **só no padding `=`**, nunca nos caracteres `+`/`/` (que nenhum desses bytes gera). Escrever o comando que **reproduz o token real** e dizer que o `=` é opcional aqui; se um handle tivesse bytes que gerassem `+`/`/`, aí `base64` e `base64url` divergiriam de verdade e o comando certo seria `basenc --base64url`.
3. **Impersonation — o MESMO request, só o token muda.** Refazer o `GET /users/alice` trocando **só** o `Authorization` por `Bearer YWxpY2U` → **`200`** + `{"handle":"alice","displayName":"Alice Nguyen","email":"alice@secret.example"}`.
   > `Method: GET · Target: alice · Isolates: same URL, same correct guard — only who the token claims you are changed`

   **A mesma URL, a mesma rota, a mesma authz CORRETA — mudou só quem o token diz que você é, e o servidor acreditou.** Você está lendo o email privado da `alice`. Não burlou a guarda: **satisfez** a guarda, porque forjou a identidade que ela compara.

> **Frase-âncora do WALKTHROUGH (uma casa só):** *The ownership check was right both times — all you changed was the name the token spells, and a token that spells your name is a name anyone can spell.* / *A guarda de posse estava certa nas duas vezes — você só mudou o nome que o token soletra, e um token que soletra o seu nome é um nome que qualquer um soletra.* Mora no fim do Step 4 (o clímax). **Não** repetir no DIFF nem no README. *(Manter distância das âncoras de 01–07 — ver "Frases-âncora".)*

### 5. Step — What the vuln is NOT (passo de contraste OBRIGATÓRIO)
Nomear e desarmar — **duas firmes** e **uma terceira cortável**. **Zero requests novos** além dos que o aluno já tem (o `403` do baseline e o `200` do exploit bastam).

1. **"Isto é BOLA — li o objeto de outro por falta de check." (LEITURA ERRADA CENTRAL — mais peso, parágrafo próprio.)** **Desarma:** volte ao baseline do Step 4 — `GET /users/alice` com o **seu** token deu **`403`**. O check de posse **existe e morde**. Você **não** leu o objeto da `alice` por ausência de autorização; você **virou** a `alice` e aí a autorização, **correta**, te serviu o objeto dela. **Authz certa, authentication quebrada.** Em BOLA a identidade é real e o check falta; aqui o check está certo e a **identidade é falsa**. (Mesmo argumento de posse de 05/06 — **forward** pro DIFF do 05 pro critério de status; não recontar.)
2. **"Isto é roubo de token / replay / você interceptou a sessão da `alice`."** **Desarma:** você **não interceptou nada**. Não houve sniff de rede, nem cookie roubado, nem token capturado e **reenviado**. Você **construiu** o token da `alice` do zero, a partir do **handle** dela — que é **público** (aparece no login, na plataforma). É **fabricação a partir de dado público**, não furto de segredo. A diferença importa: contra roubo, você rotaciona o token vazado; contra **isto**, não há o que rotacionar — todo token é derivável.
3. **"É criptografia fraca — o token usa um hash/cifra ruim." (cortável)** **Uma frase:** base64url **não é** criptografia, é **codificação** — não há chave, não há algoritmo a quebrar, só um envelope a abrir. A falha não é "a cripto é fraca"; é **não haver cripto nenhuma, nem segredo nenhum**. Por isso **assinar** o token (dar-lhe integridade) não é a lição — ver o fix. **Se não couber limpo, cortar** e ficar com (1) + (2) — mas é a leitura que mais protege o aluno de achar que "assinar resolve".

**Conclusão a escrever explicitamente:** a rota de perfil **não tem** bug de autorização — a guarda de posse está **correta** e o `403` do baseline prova. A falha é **anterior**: o **token não prova identidade**, porque qualquer um o produz a partir de um nome público. Você não leu objeto alheio (não é BOLA), não roubou credencial (não é replay), não quebrou cripto (não há cripto). Você **forjou a identidade**. A pergunta certa é *"o token é imprevisível pra quem não o recebeu?"*.

### 6. Step — Impact (honesto)
- **Impersonation TOTAL de qualquer usuário cujo handle se conheça.** Handles são **públicos** (nomear essa premissa explicitamente): aparecem no login e na plataforma. Para **cada** handle, o atacante deriva o token e **se autentica como aquele usuário** — acesso autenticado aos dados privados da vítima (aqui, o `email`; num sistema real, tudo que a sessão da vítima alcança).
- **A authz correta do sistema vira inútil.** Toda a disciplina de 01–07 (checar objeto, função, propriedade) **pressupõe** uma identidade confiável. Quando a identidade é forjável, os checks **continuam rodando certo** — e **servem o atacante**, porque ele **é** a vítima aos olhos do servidor. É o que torna esta classe tão grave: não derruba um muro, **falsifica o crachá que abre todos**.
- **Não-revogável (consequência real, validada por lógica):** no `vulnerable/`, não há estado por trás do token, então **não há como invalidá-lo** — restart não ajuda, trocar nada ajuda; enquanto o handle existir, o token dele é derivável. Mencionar sem inflar.
- **O que o impacto NÃO é (disciplina dura):**
  - **Não é escalação de privilégio.** Não há admin, não há papel. Você **vira outro usuário comum**, não um superusuário. (Isso é 04/07 — outra classe.)
  - **Não é RCE, não é dump de base.** Você lê **um** perfil por vez, o da identidade que forjou. O que foi provado é **impersonation + leitura de dado privado**, e é suficiente.
  - **Não é bypass de autorização.** A autorização **funcionou** — ela só autorizou uma identidade falsa. O bypass foi da **autenticação**.

### 7. Why the fix works (porta 8308)
Apontar o Burp pro `fixed/` em `127.0.0.1:8308` e logar lá (cada build tem o próprio mapa de tokens). **Repetir a sequência:**
- `POST /login` como `clancy` → `{ "token": "<novo-clancy-token>" }`. **Decodificar esse token agora NÃO devolve `clancy`** — é 24 bytes aleatórios (`echo -n <token> | base64 -d` sai lixo binário, não um nome). O token virou **opaco**.
- `GET /users/clancy` com ele → **`200`** (self-read funciona: a feature está viva).
- **Forjar `base64url("alice")` e mandar em `GET /users/alice` → `401`.** O servidor **não reconhece** o token: ele não está no `TOKENS` (ninguém o registrou no login). **O token agora não diz nada sobre quem você é — só o registro do servidor diz.** `echo -n alice | base64` ainda produz `YWxpY2U=`, mas isso deixou de ser um token válido: não há identidade **dentro** dele pra decodificar, e o lookup **falha**.
- **Posse e baseline não mudaram:** `GET /users/alice` com o token **legítimo** do `clancy` → `403` (posse); sem/ruim token → `401` + challenge.
- **O fix é a origem da identidade:** `randomBytes` + `TOKENS.set` no login, `TOKENS.get` no authenticate. **Forward pro DIFF** pro eixo **decode-vs-lookup**, pro **foil** (por que **assinar** o token mantém a identidade dentro dele e erra a lição), pra nota do **`401` honesto** que só o `fixed/` consegue emitir, e pra explicação de **por que o diff toca três pontos inseparáveis**.

**O walkthrough TERMINA aqui.** Sem Intruder, sem automação, **sem** seção de exercícios/variações, **sem** trilha browser (CLAUDE.md §5).

---

## Frases-âncora (uma casa só cada — CLAUDE.md §11 / template)

Nenhuma frase memorável aparece em **dois** documentos. Atribuição fixa:

- **WALKTHROUGH (uma casa):** *"The ownership check was right both times — all you changed was the name the token spells, and a token that spells your name is a name anyone can spell."* / *"A guarda de posse estava certa nas duas vezes — você só mudou o nome que o token soletra, e um token que soletra o seu nome é um nome que qualquer um soletra."* Mora no fim do Step 4.
- **DIFF (uma casa):** *"Identity that travels inside the token is identity the client can author; the fix does not harden the token, it stops reading identity from it."* / *"Identidade que viaja dentro do token é identidade que o cliente pode autorar; o fix não blinda o token, ele para de ler identidade de dentro dele."* Mora na seção do fix.
- **Conferido contra 01–07 (lidas nesta fase); NÃO reusar nem colar:**
  - 01 — W: *"The same missing check doesn't leak an order: it leaks the collection…"*; D: *"`404` when existence itself leaks; `403` when admitting existence is fine."*
  - 02 — W: *"a wall of 404s is 'didn't find,' not 'nothing to find.'"*; D: *"the id type changed … the correction changed nothing."*
  - 03 — W: *"Authorization present is not authorization sufficient — what matters is which question it answers."*; D: *"No information was missing — the question was."*
  - 04 — W: *"The endpoint never cared whose account the target was…"*; D: *"The fix adds no check about the target at all — it asks only whether the caller may run the function."*
  - 05 — W: *"One URL answered the read safely and the write wide open…"*; D: *"The fix invents nothing: it carries the `GET` handler's ownership guard onto the `PATCH` handler…"*
  - 06 — W: *"Owning the object was never the same as being cleared for every field on it…"*; D: *"`...user` serializes the object the store holds; the allow-list serializes the object the caller is cleared to read — BOPLA is the distance between the two."*
  - 07 — W: *"A write that answers `204` proves nothing about what it wrote — the proof was the admin door: `403` a minute ago, open now."*; D: *"The vulnerable handler asks the request which properties to write; the fixed one already knows — and `is_admin` was never among them."*
- **Atenção especial:** (i) a do **WALKTHROUGH** deste átomo usa "the name the token spells / anyone can spell" — cuidar pra **não** ecoar o "the attack never touches the token" de 01/02/05/06/07 (é o **oposto** temático: aqui o ataque é só o token — e essa inversão é material, mas a **frase-âncora** não deve colar com a deles); (ii) a do **DIFF** usa "identity that travels inside the token / stops reading identity from it" — distinta da construção "X serializes…; the allow-list serializes…" do 06 e da "asks the request / already knows" do 07. O corte deste átomo é **origem da identidade (decode vs. lookup)**, não projeção de campos.

---

## Anatomia dos gêmeos e container

`app.ts` + `package.json` + `package-lock.json` + `tsconfig.json` + `Dockerfile` em **cada** gêmeo, **self-contained, sem módulo compartilhado**; lockfile **commitado** por gêmeo. `app.ts` **difere** no **bloco de auth** (`import { randomBytes }`, `const TOKENS`, `issueToken`, `authenticate`); todo o resto — `app.use(express.json())`, `USERS`, `POST /login`, `GET /users/:handle` **inteiro**, rodapé `listen` — é **idêntico** entre as versões.

**Herança de toolchain (CLAUDE.md §3.6) — lida dos arquivos publicados de 01–07 nesta fase (os `Dockerfile` e `tsconfig.json` batem por md5 nos sete átomos; `package.json` difere só no `name`):**

`tsconfig.json` (copiar — idêntico a 01–07):

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

- **A guarda `!user` é higiene byte-idêntica nos dois gêmeos** (o `| undefined` vem da assinatura do `Map.get`, com `noUncheckedIndexedAccess` ligado por herança). **Validado nesta fase:** os dois gêmeos saem `tsc --noEmit` **exit 0** com a guarda; o `GET /users/:handle` é idêntico, então a guarda não diverge entre eles. O `?.` não aparece no `GET` (a guarda de posse é comparação de string; o `!user` é a única desreferência, explícita).
- **FLAG TS (validada):** o `vulnerable/` type-checa **limpo** sem `TOKENS` e com `authenticate` retornando o decode (`Buffer.from(...).toString("utf8") || null`): a assinatura `string | null` é coerente com a do `fixed/` (`TOKENS.get(token) ?? null`). O `vulnerable/` **não importa** `node:crypto` (não usa `randomBytes`) e isso é limpo. **Sem `any` solto, sem `@ts-ignore`.**

`Dockerfile` (idêntico a 01–07 — copiar; base `node:24.21.0-slim`, patch exato, nunca `latest` nem a tag móvel `node:24-slim`):

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

`docker-compose.yml` (bind **só** em `127.0.0.1`, portas **8208/8308**):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8208:3000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8308:3000"
```

- `package.json` de cada gêmeo: `"name": "auth-predictable-token"`, `"private": true`, `"type": "module"`, `"scripts": { "start": "tsx app.ts", "typecheck": "tsc --noEmit" }`. Entrypoint `tsx`. **Sem `templates/`, sem `COPY templates`** (API-only). Sem `apt`, sem banco.
- **`node:crypto` é nativo** (`randomBytes` no `fixed/`) — não é dependência npm. O `vulnerable/` usa só `Buffer` (global) e `express`.
- **Roda como não-root, sem `chown`** — mesma justificativa de 01–07. Reconfirmar no smoke test da Fase 2: build OK, container sobe como `node`, `tsx` sem erro de permissão, endpoints respondendo, imagem só com `express` + `tsx`.

---

## Dependências extras

**Nenhuma dependência nova.** Versões **exatas herdadas** de 01–07 — lidas do `package.json` publicado do 07 e conferidas contra os demais. **NÃO consultar npm, NÃO atualizar, NÃO escrever faixa:**

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

- Base `node:24.21.0-slim` (lida dos `Dockerfile`, md5 idêntico nos sete átomos). Nenhuma divergência de toolchain.
- Classificação por **runtime**: `tsx` em `dependencies` (entrypoint que executa); `typescript`/`@types/*` em `devDependencies`. `npm audit --omit=dev` cobre exatamente o que a imagem `npm ci --omit=dev` instala e roda (`express` + `tsx`). **Escopo da imagem = escopo do audit = o que roda.** **Validado nesta fase:** `npm ci` do `package.json`/`package-lock.json` do 07 instala limpo; os gêmeos rodam com `tsx`. (Rodar `npm audit --omit=dev` por gêmeo na geração e registrar os advisories esperados — meta: 0 de runtime, como em 01–07.)
- **NÃO adicionar biblioteca de JWT/assinatura/cripto** (`jsonwebtoken`, `jose`, etc.): o fix é token opaco + lookup, feito com `randomBytes` nativo; o foil (assinatura) é **bloco ilustrativo do DIFF**, não entra no `fixed/`, e usa só `node:crypto` nativo. Trazer lib de JWT sugeriria que a lição é "use JWT" — e **não é** (ver "Fix"/foil). Respeita "só inclua a lib se serve à demonstração da falha ou ao fix" (§3.6).
- **Pin exato travado no `package-lock.json`** (commitado por gêmeo). Updates **manuais** (CLAUDE.md §8.7). Bump é decisão de corte de release (§3.6), não deste átomo.

---

## Theory primer

Bloco obrigatório no topo do `README.md` e `README.pt-BR.md` (após título+descrição, antes de "How to run"). A casa conceitual é a **página "Authentication vulnerabilities" da PortSwigger Web Security Academy** — a página inteira é o conceito-mãe.

- **Primer (verificado por fetch NESTA fase — HTTP 200, 0 redirects, H1 `Authentication vulnerabilities` com `id="authentication-vulnerabilities"`):**
  `https://portswigger.net/web-security/authentication`
  Texto do link: **"Authentication vulnerabilities"** — o **H1 da página**, como a PortSwigger a apresenta (mesmo padrão de 04/05/06, que usam o H1 da página), preservado em **inglês** também no README PT (CLAUDE.md §7).
- **Por que a PÁGINA (H1) e não um anchor — diferente do 07:** o 07 linkou uma **seção** (`#mass-assignment-vulnerabilities`) porque mass assignment era uma subseção nomeada de outra página. Aqui o conceito-mãe (**autenticação forjável porque o token é derivável**) **não tem subseção própria** na PortSwigger — a organização deles é por mecanismo (**password-based**, **MFA/2FA**, **other authentication mechanisms**), e "token derivável do username" não é um deles. O conceito-mãe é a **página inteira**, que **abre justamente com a distinção authentication-vs-authorization** — a virada deste átomo. Por isso linkamos a página (H1), não um anchor. É a **mesma regra** ("a forma como a PortSwigger apresenta"), aplicada a um caso onde a casa é a página, não uma seção.
- **A página cobre o conceito-mãe (conferido lendo o texto nesta fase):** abre com *"authentication is the process of verifying that a user is who they claim to be"* e a subseção *"What is the difference between authentication and authorization?"* — exatamente a distinção que ancora a lição. Ela **não** tem um lab de "token = username em base64url" (a Academy cobre isso por outras vias), e **não se finge** que tem: o primer dá **o quê** (o que é authentication e por que falha), o átomo dá **o como** (no código).

Formato exato EN:

```markdown
> **Theory primer:** Read [PortSwigger: Authentication vulnerabilities](https://portswigger.net/web-security/authentication)
> before working through this atom. The atoms in this repo show
> *how* a vulnerability happens in code; the Academy explains *what*
> it is and why it matters.
```

Formato exato PT:

```markdown
> **Teoria primeiro:** Leia [PortSwigger: Authentication vulnerabilities](https://portswigger.net/web-security/authentication)
> antes de fazer este átomo. Os átomos deste repo mostram *como* uma
> vulnerabilidade acontece no código; a Academy explica *o que* ela é
> e por que importa.
```

**OWASP: sem link inline.** Os docs citam `API2:2023` em texto simples; o link canônico vive na tabela de Cobertura do `atoms/api/ROADMAP.md` (conferido: a linha **API2** já existe, apontando `auth-predictable-token`, `auth-no-lockout`, `oauth-client-cred-unverified`).

**Fase 2 (geração):** **re-confirmar a URL por fetch** (200, sem redirect, H1 `Authentication vulnerabilities`) antes de cravar. **Se a página não encaixar, PARAR e perguntar ao mantenedor** — não substituir por conta própria.

---

## Política de cross-ref (CLAUDE.md §5)

Publicação verificada **lendo `atoms/api/ROADMAP.md` e a árvore de `atoms/` NESTA fase**, não de memória: na série API, **01–07 estão publicados** (`[x]`, pastas completas); **09 em diante não** (08 é este; `auth-no-lockout` e `oauth-client-cred-unverified` estão `[ ]`).

- **01–07 — a premissa de token confiável que este átomo ATACA.** O crédito central: os sete trataram o token como premissa confiável (`issueToken`/`authenticate` cripto-fortes, intocados) e repetiram "o ataque não toca o token" pra isolar a authz. **Este átomo inverte isso** — nomear a inversão creditando a premissa, **sem reabrir** a lição de nenhum deles. Pode citar 01–07 em bloco como "a série até aqui"; é o fio da Fase 1→2.
- **`bfla-method-based` (05) e `bopla-excessive-exposure` (06) — origem do `GET /users/:handle` e da guarda de posse** (reusada aqui byte-idêntica, **correta**). Creditar: a superfície de perfil, a guarda de posse que **afasta o BOLA**, e o argumento `403`/RFC 9110 (**forward** pro DIFF do 05, não recontar). O `GET` deste átomo tem a forma do `GET` **fixed do 05** (campos nomeados, não `...user`), com o campo `email` acrescentado.
- **`bopla-mass-assignment` (07) — crédito pela DISCIPLINA do "a guarda está certa, o forjado está a montante".** Lá a guarda **admin** estava correta e o bug era o **papel** forjado; aqui a guarda de **posse** está correta e o bug é a **identidade** forjada. Creditar o **formato da disciplina** (não a classe BOPLA): uma frase de contraste, com link relativo pro átomo. **Sem reabrir** mass assignment.
- **`bola-sequential-id` (01), `bola-uuid-leaked` (02), `bola-nested-resource` (03) — o contraste "não é BOLA".** Em 02 especificamente, a disciplina "o ataque não toca o token — você não decodifica, altera ou forja" é **o oposto exato** deste átomo; o contraste é didático e pode ser nomeado (02 está publicado). Creditar sem reabrir.
- **PROIBIDO citar qualquer átomo de API NÃO publicado** (09 em diante) — por nome, número ou descrição. **Em particular, NÃO antecipar `auth-no-lockout` nem `oauth-client-cred-unverified`** (os outros dois de API2). Se a geração sentir vontade de dizer "outra forma de Broken Authentication", **generalizar** ("outras falhas de autenticação — brute force sem lockout, validação de credencial incompleta — são classes vizinhas") **sem nomear os átomos futuros**.
- **Átomos web — NÃO há par direto a citar.** A série web não tem um átomo "token = username codificado" publicado na mesma forma; **não** inventar contraste. Se a geração quiser ancorar, **linkar a PortSwigger** (o primer), não um átomo web.
- Termos técnicos em inglês no PT (Broken Authentication, authentication, authorization, opaque token, impersonation, base64url, encoding, token, Bearer, ownership check, lookup, decode, Trigger, payload, replay, brute force, sink, source).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / API Top 10 2023) | **API2 — Broken Authentication** | Primeiro átomo da categoria; **cria** a pasta `API2-broken-authentication/` (como o 06 criou a API3). A virada authz→authn. |
| Pasta | **`API2-broken-authentication/` (NOVA — criar)** | Não existe ainda. Este átomo a estreia. |
| Nome / classe (H1) | **Broken Authentication** — idêntico EN/PT | Primeiro H1 da série com esse nome; o slug (`auth-predictable-token`) qualifica a variante. |
| A tese | **O token é imprevisível pra quem não o recebeu?** | No vulnerable, não: é o nome em base64url. Identidade forjável. |
| Eixo | **Origem da identidade: decode (token) vs. lookup (registro server-side)** | Uma lição; três pontos acoplados no código (geração, resolução, mapa). |
| Cenário | **Forja: `clancy` deriva o token da `alice` e lê o perfil dela** | A prova é dado privado da vítima na resposta do atacante. |
| Superfície | **Duas rotas:** `POST /login`, `GET /users/:handle` (byte-idêntica nos gêmeos) | Mínimo pra autenticar e pra provar. A falha vive em `authenticate`, não numa rota. |
| **SEM** `GET /me` | **Omissão deliberada e definitiva** | Tautológico (reafirma a identidade forjada sem provar acesso a dado de outro). A prova é `GET /users/alice`; o papel de "o servidor me chama de X" é o decode CLI do Step 3. Superfície = duas rotas; não criar `/me`. |
| **SEM** rota admin / `is_admin` | **Omissão deliberada** | Não há privilégio a escalar — não é authz (04/07). A prova é impersonation + leitura de dado privado. |
| Token vulnerable | **`issueToken(user) = Buffer.from(user).toString("base64url")`; `authenticate` decodifica** | O nome, codificado; decode-and-trust. Sem `TOKENS`, sem `randomBytes`. |
| Token fixed | **Bloco de 01–07 byte a byte: `randomBytes(24).toString("base64url")` + `TOKENS.set`; `authenticate` faz `TOKENS.get`** | Opaco + lookup. O fixed **é** o bloco canônico; o vulnerable é sua deformação. |
| `\|\| null` vs `?? null` | **vulnerable usa `\|\| null` (decode dá `""`); fixed usa `?? null` (Map.get dá `undefined`)** | Ambos `string \| null`. O `\|\| null` preserva o `401` honesto pra token vazio no vulnerable. |
| base64url, não hash/cifra | **Codificação reversível, deliberada** | A lição é authentication ("segredo que não era segredo"), não cripto. Nada a quebrar, só decodificar. |
| Diff não-unitário | **Deliberado: 3 pontos inseparáveis (geração, resolução, mapa)** | A natureza da classe; "um átomo = uma vuln" é sobre uma lição, não uma linha. |
| Foil | **Assinar o token (base64url + HMAC) — descartado no DIFF** | "Funciona" contra o exploit mas mantém identidade no token; erra a lição e abre a porta de JWT/HMAC. Type-checa (validado). |
| Store | **`Map<string, User>`, `User = { displayName, email }`** | Herança de 04–07. `email` é o dado privado (a prova). **Sem `is_admin`, sem `passwordHash`.** |
| Seed | **`clancy` (atacante, self-read baseline) e `alice` (vítima, nunca loga)** | `clancy` tem email próprio pro `200` de baseline; `alice` é impersonada, seu token nunca é emitido. |
| Email fake | **`clancy@mail.example`, `alice@secret.example`** | Domínios `.example` reservados (RFC 2606); `secret.example` sinaliza "privado". Sem PII real. |
| Estado | **Imutável (só lê). `TOKENS` do fixed cresce no login, mas não é a lição** | Sem dependência de ordem. Restart: fixed zera tokens; vulnerable não tem estado (token não-revogável). |
| Status codes | **`200` forjado (vuln); `403` posse; `200` self-read; `401` sem/ruim token; `400` login desconhecido; `404` `!user` raramente alcançável** | `403` por identidade antes da busca (herança 05/06, forward); `401`/`WWW-Authenticate` RFC 9110 §15.5.2. |
| Sutileza do 401 ausente | **Observação no DIFF, não um passo** | No vulnerable não há "token não reconhecido" — todo decode não-vazio é alguém; só decode vazio dá `401`. Sintoma da vuln. |
| Padrão de prova | **Trigger; auto-contida** (dado privado da vítima na resposta) | Contraste: 07 precisou de segundo caminho (termômetro); aqui a resposta do próprio exploit prova. → passo de contraste obrigatório. |
| Passo de contraste | **(1) não é BOLA — PESO MAIOR (o `403` do baseline prova posse correta); (2) não é roubo/replay (construído, não interceptado); (3) não é cripto fraca (cortável)** | Zero requests novos além do baseline e do exploit. |
| Trilha | **100% Burp (Repeater) / curl / base64 CLI; SEM Intruder; SEM browser** | API-only (CLAUDE.md §3.3). A tese é forja de uma identidade, não enumeração. |
| Impacto | **Impersonation total de qualquer handle público; leitura de dado privado; não-revogável** | **Não inflar:** não é priv-esc (sem admin), não é RCE/dump, não é bypass de authz (a authz funcionou sobre identidade falsa). |
| Theory primer | **PortSwigger "Authentication vulnerabilities" (página inteira, H1)** | Conceito-mãe sem subseção própria; a página abre com authn-vs-authz. Diferente do 07 (que linkou um anchor). |
| Cross-ref | **01–07 = premissa atacada; 05/06 guarda de posse; 07 disciplina "guarda certa/forjado a montante"; 02 contraste "ataque não toca o token"; NENHUM átomo de API 09+; sem par web** | 01–07 publicados; 08+ não. |

---

## Decisões que podem gerar dúvida durante implementação

- **`Buffer.from(token, "base64url")` tolera padding e caracteres inválidos?** **Sim — validado:** `YWxpY2U` e `YWxpY2U=` decodificam pra `alice`; `.` e espaços são ignorados; input indecodificável-pra-bytes vira `""` ou U+FFFD, **nunca** lança. O decode é **total** (por isso "confia em qualquer coisa"). Não envolver em try/catch — não há o que capturar.
- **`|| null` no vulnerable `authenticate` — manter.** `?? null` **não** pegaria a string vazia (só `null`/`undefined`), e um token vazio viraria `caller = ""` → o `401` nunca dispararia. Usar **`|| null`** (truthiness) pra que decode-vazio → `null` → `401`. **Validado:** sem header → `401`; `Bearer !!!` → `401`; `Bearer ////` → `403` (não-vazio, posse morde).
- **Tipos do Express 5 — retorno `Response` vs `void`.** Igual a 01–07: callbacks **sem** anotação de retorno, onde `return res.set(...).sendStatus(...)` passa. Se anotar, usar `...; return;`. **Não anotar é o caminho da série.**
- **O `vulnerable/` type-checa sem `TOKENS` e sem `randomBytes`?** **Sim — validado:** `authenticate` retorna `string | null` coerente; sem imports não-usados; `tsc --noEmit` exit 0. **Não** deixar um `import { randomBytes }` órfão no vulnerable (erraria "declarado e não usado" sob `strict`? — na verdade TS não barra import não-usado por default, mas é sujeira; **remover** o import no vulnerable).
- **O `GET /users/:handle` é byte-idêntico nos dois gêmeos.** O `diff -r vulnerable fixed` deve mostrar **só** o bloco de auth (import, `TOKENS`, `issueToken`, `authenticate`). Se o `GET`, o `POST /login`, o `USERS` ou o rodapé divergirem, **PARE** — o eixo vazou pra fora do bloco de auth.
- **Ordem no arquivo:** imports, `const app`/`express.json()`, `USERS`, bloco de auth (`TOKENS`/`issueToken`/`authenticate`), `POST /login`, `GET /users/:handle`, rodapé `listen`. (No vulnerable, sem `TOKENS` e sem o import de `randomBytes`.)
- **Corpo JSON só no `POST /login`** → `app.use(express.json())` é obrigatório e idêntico a 01–07. O `GET` não tem corpo. Não remover o middleware.
- **JSON malformado no `POST /login` → `400` com stack trace no HTML** (handler de erro default do Express, herdado de 01–07). **Não** é novidade nem lição deste átomo; **não** corrigir (seria outro eixo). Se o aluno esbarrar nisso, não faz parte do átomo.
- **base64 vs base64url na CLI:** explicação cheia e validação no Step 4 do Walkthrough (padding do `alice`; servidor aceita as duas formas; só divergiriam em `+`/`/`, que estes handles não geram). Aqui: remeter ao Step 4, não repetir.
- **Decode do próprio token no fixed → lixo, não um nome.** `echo -n <token-opaco> | base64 -d` sai binário. É a prova visual de que o token virou opaco. Mencionar que pode não imprimir "limpo" no terminal (bytes aleatórios).

---

## Validação de typecheck e runtime (feita NESTA fase de planning)

Montei um protótipo descartável fora do repo (scratchpad da sessão) com o **toolchain EXATO** herdado de 01–07 (`npm ci` do `package.json`/`package-lock.json` do 07 — express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; node **24.22.0** no host, patch acima da base `node:24.21.0-slim` da imagem, mesma major/minor) e o `tsconfig.json` da série (byte a byte), construí os **dois gêmeos** exatamente como esta spec os descreve, e rodei `tsc --noEmit` + exercitei os endpoints com `tsx`. Observado (não raciocinado):

**Typecheck (`tsc` 7.0.2):**

| Teste | Resultado observado |
|---|---|
| `fixed/app.ts` (bloco de auth de 01–07, `TOKENS.get` lookup) | **exit 0**, limpo |
| `vulnerable/app.ts` (`issueToken` = base64url do nome; `authenticate` = decode `\|\| null`; sem `TOKENS`, sem `randomBytes`) | **exit 0**, limpo |
| foil (assinatura HMAC: `createHmac` + `timingSafeEqual`, identidade ainda no token) | **exit 0** |

**Runtime — a sequência da prova** (servidores `tsx` nas portas 8208/8308; token do `clancy` obtido via `POST /login`):

| Passo | vulnerable (8208) | fixed (8308) |
|---|---|---|
| `clancy` token, decodificado (`base64 -d`) | **`clancy`** (o token É o nome) | **24 bytes aleatórios** (opaco; lixo binário) |
| `GET /users/clancy` com token do `clancy` (self-read) | **`200`** `{handle, displayName, email: clancy@mail.example}` | **`200`**, idêntico |
| `GET /users/alice` com token do `clancy` (baseline posse) | **`403`** | **`403`** |
| **forja** `base64url("alice")` → `GET /users/alice` | **`200`** `{handle:"alice", …, email:"alice@secret.example"}` | **`401`** (não está no `TOKENS`) |
| sem token → `GET /users/alice` | **`401`** + `WWW-Authenticate: Bearer` | idem |
| `Bearer !!!` (decode vazio) → `GET /users/alice` | **`401`** (`\|\| null`) | **`401`** (lookup miss) |
| `Bearer ////` (decode não-UTF-8, truthy) → `GET /users/alice` | **`403`** (posse; caller ≠ alice) | **`401`** (lookup miss) |
| `Bearer Zm9v` (`"foo"`) → `GET /users/foo` | **`404`** (posse passa, `!user`) | **`401`** |
| `POST /login` usuário desconhecido | **`400`** | **`400`** |
| socket bind (`ss -ltnp`) | `127.0.0.1:8208` | `127.0.0.1:8308` |

**Round-trip base64url (observado, não raciocinado):** `alice` → `Buffer.from("alice").toString("base64url")` = `YWxpY2U` → `Buffer.from("YWxpY2U","base64url").toString("utf8")` = `alice` (round-trip exato). CLI: `echo -n alice | base64` = `YWxpY2U=` (padding); `echo -n clancy | base64` = `Y2xhbmN5` (sem padding, = base64url). `echo -n Y2xhbmN5 | base64 -d` = `clancy`. Ambos `YWxpY2U` e `YWxpY2U=` → `alice` no decoder do Node.

**Byte-identidade conferida (`md5`/`grep -Fxc`):**

- Bloco `issueToken`…fim de `authenticate` do **`fixed/`** → **md5 idêntico** ao de 05/06/07; handler `POST /login` e rodapé `listen` idênticos; o `fixed/` **é** o bloco de auth canônico.
- Guarda de posse `  if (req.params.handle !== caller) return res.sendStatus(403);  // ownership: your own record only` → **`grep -Fxc` = 1** no `GET` dos dois gêmeos e idêntica à de 05/06.
- `diff -r vulnerable fixed` (protótipo) → **só** o bloco de auth difere (import de `randomBytes`, `const TOKENS`, corpo de `issueToken`, retorno de `authenticate`); `POST /login`, `GET /users/:handle`, `USERS`, bootstrap e rodapé **idênticos**.
- Handler `GET /users/:handle` do protótipo: **7 linhas** (limite da série: ~30). `authenticate` do vulnerable: 4 linhas.

**Foil (assinatura) — observado:** `tsc --noEmit` exit 0; em runtime, `issueToken("clancy")` → `Y2xhbmN5.<hmac>`; `authenticate` de um token **legitimamente emitido** de `alice` → `"alice"` (verifica); um `base64url("alice")` **sem** assinatura → rejeitado (`null`). Confirma: a assinatura bloqueia **este** exploit, mas mantém a identidade dentro do token — por isso é foil, não fix.

**Primer e RFC (conferidos nesta fase):**

- `https://portswigger.net/web-security/authentication` → **HTTP 200, 0 redirects**, H1 `Authentication vulnerabilities` (`id="authentication-vulnerabilities"` no HTML); abre com a distinção authentication-vs-authorization.
- RFC 9110 em **texto bruto** (`rfc-editor.org/rfc/rfc9110.txt`): **§15.5.2** (401 — *"MUST send a WWW-Authenticate header field"*; *"lacks valid authentication credentials"*), **§15.5.4** (403 — *"credentials … insufficient to grant access"*; o `404`-pra-esconder-existência é `MAY`, não se aplica).

**Conclusões cravadas:** os dois gêmeos saem `tsc` exit 0; o `fixed/` é o bloco de auth de 01–07 byte a byte; o `vulnerable/` é sua deformação mínima (decode em vez de lookup, sem `TOKENS`, sem `randomBytes`), coerente em tipo (`string | null`); o round-trip base64url é exato; token lixo nunca dá `500` (`401`/`403`/`404` conforme o decode); a prova é a transição `403 → 200` no **mesmo** request com o token trocado, com o email privado da vítima na resposta; o `fixed/` emite `401` pra o token forjado (lookup miss), e **só** o `fixed/` tem a categoria "token não reconhecido"; o foil (assinatura) type-checa e bloqueia o exploit mas mantém a identidade no token. A Fase 2 ainda roda `npm run typecheck` nos dois gêmeos como gate oficial (host/CI) e um smoke test completo em container.

---

## Riscos técnicos a validar na geração (checklist — Fase 2, CLAUDE.md §11)

1. **`POST /login`** mapeia usuário→token e devolve `{ token }`; **handler byte-idêntico nos dois gêmeos**, só o `issueToken` difere. `clancy`/`alice` são seedados; `USERS.has(user)` valida membership.
2. **vulnerable — token previsível:** `POST /login` como `clancy` → token que **decodifica pra `clancy`** (`base64 -d`). `issueToken` = `Buffer.from(user).toString("base64url")`, **sem** `TOKENS.set`, **sem** `randomBytes`. **Se o token do vulnerable não decodificar pro nome, está errado — PARE.**
3. **fixed — token opaco:** `POST /login` como `clancy` → 32 chars base64url que **não** decodificam pra nome; `TOKENS.get` resolve. Bloco de auth **md5-idêntico** a 05/06/07. **Se decodificar pro nome, o fixed está contaminado — PARE.**
4. **Autenticação imposta:** sem Bearer, ou Bearer que decodifica pra vazio → **`401`** com `WWW-Authenticate: Bearer`, nos dois gêmeos.
5. **Baseline de posse (afasta BOLA):** `GET /users/alice` com o token **legítimo** do `clancy` → **`403`** nos dois gêmeos. **Se der `200` antes da forja, a posse está quebrada — PARE.**
6. **vulnerable — a forja:** `base64url("alice")` em `GET /users/alice` → **`200`** + `email` da `alice`. **A transição `403 → 200` (só o token muda) é o átomo.**
7. **fixed — a forja falha:** o MESMO `base64url("alice")` em `GET /users/alice` → **`401`** (não está no `TOKENS`). O self-read do `clancy` continua `200`; a posse continua `403`.
8. **Self-read legítimo:** `GET /users/clancy` com o token do `clancy` → **`200`** + `clancy@mail.example`, nos dois gêmeos (a feature funciona).
9. **Token lixo nunca `500`:** `Bearer ////` → `403` (vuln) / `401` (fixed); `Bearer Zm9v` em `/users/foo` → `404` (vuln) / `401` (fixed); `Bearer !!!` → `401` nos dois. **Se algum caminho der `500`, o decode lançou — PARE** (não deveria; o decode é total).
10. **`app.ts` DIFERE só no bloco de auth** (import de `randomBytes`, `const TOKENS`, `issueToken`, `authenticate`). `POST /login`, `GET /users/:handle` **inteiro**, bootstrap, `USERS`, rodapé, `Dockerfile`, `package.json`, `package-lock.json`, `tsconfig.json` **idênticos**. `diff -r` mostra só o bloco de auth. **Se vazar pra fora, PARE.**
11. **A guarda de posse é byte-idêntica à de 05/06** (`grep -Fxc`); o bloco de auth do `fixed/` é md5-idêntico ao de 05/06/07.
12. **Seed:** `clancy` e `alice`, cada um com `displayName` e `email` fake (domínios `.example`); **sem `is_admin`, sem `passwordHash`**, nenhum campo extra. **Nenhuma credencial/PII real.**
13. **A resposta do `GET` devolve `email` nos DOIS gêmeos** (não é over-serialization — não é o 06): o `email` é dado do dono; a falha é que "dono" foi forjado. **Um bug só** (Broken Authentication).
14. **Superfície mínima:** só `POST /login` e `GET /users/:handle`. **Sem** `GET /me` (não criar — superfície = duas rotas), **sem** rota admin, **sem** `PATCH`/`DELETE`, **sem** listagem, **sem** índice.
15. **Estado imutável:** o `USERS` não muda; sem dependência de ordem. README declara o restart na única casa (fixed: tokens voltam ao zero; vulnerable: token não tem estado, não-revogável).
16. **API-only:** **sem** `templates/`, Dockerfile **sem** `COPY templates`, sem HTML; respostas `application/json` (ou `401`/`403`/`404` sem corpo via `sendStatus`).
17. **Bind/portas:** `app.listen` default `127.0.0.1`; compose bind **só** `127.0.0.1`; container `ENV HOST=0.0.0.0`. **Portas 8208 (vulnerable) / 8308 (fixed)**, internas `3000`, coerentes entre `EXPOSE`, `app.listen` e o compose.
18. **Docs EN+PT sincronizadas** no mesmo commit; **nenhum header de seção PT byte-idêntico ao par EN** (exceto o h1 do README); banner de aviso em todo README. (`clancy` masculino no PT.)
19. **README declara o atalho** (EN+PT, sem citar átomo): login passwordless é atalho de laboratório; **distinguir com clareza** do token previsível, que é a vuln.
20. **Theory primer:** re-confirmar por fetch `https://portswigger.net/web-security/authentication` (200, sem redirect, H1 `Authentication vulnerabilities`); texto do link "Authentication vulnerabilities", em inglês também no PT. Se não encaixar, **PARAR e perguntar**.
21. **RFC 9110** conferido em texto bruto nesta fase: **§15.5.2 (401, `WWW-Authenticate` obrigatório)** e **§15.5.4 (403)**. O argumento do `403` **referencia** o DIFF do 05; o argumento do `401`-honesto-ausente é **novo** deste átomo e fica no DIFF dele.
22. **`npm audit --omit=dev` em cada gêmeo**, advisories esperados registrados. O átomo é vulnerável na **AUTENTICAÇÃO** (token derivável), **não nas dependências**. Meta: zero advisory de runtime.
23. **`npm run typecheck` (`tsc --noEmit`, typescript 7.0.2) verde nos DOIS gêmeos** — inclusive o `vulnerable/`. Gate de **host/CI**, não do container.
24. **Diff não-unitário documentado:** o DIFF explica que o eixo (decode-vs-lookup) toca três pontos inseparáveis e **por quê** (um átomo = uma lição, não uma linha). **Se o DIFF tentar reduzir a uma linha, está errado** — mentiria sobre a classe.
25. **Foil no DIFF:** o bloco de assinatura (HMAC) com a explicação "funciona contra o exploit mas mantém a identidade no token → erra a lição e abre JWT/HMAC". **Type-checa** (validado). **Nenhuma** lib de JWT/assinatura entra no `fixed/`.
26. **Frases-âncora:** cada uma numa casa só (WALKTHROUGH: "o nome que o token soletra / qualquer um soletra"; DIFF: "identidade que viaja no token / parar de ler identidade de dentro dele"); **não** reusar nem ecoar as de 01–07 — atenção à inversão de "the attack never touches the token" (02/05/06/07): é material, mas a âncora não deve colar com a deles.
27. **Rótulo em todo bloco do WALKTHROUGH** (EN e PT): método · alvo · o que isola. A prosa **nomeia e desarma** as leituras erradas: duas firmes ("é BOLA" — **mais peso**; "é roubo/replay") e uma terceira cortável ("é cripto fraca").
28. **DISCIPLINA "guarda certa / breach a montante" (gate de redação):** em WALKTHROUGH e DIFF, está escrito **explicitamente** que a guarda de posse está **correta**, que o `403` do baseline prova, e que a mentira entra no `caller` (a identidade), **a montante** em `authenticate`. **Se um revisor conseguir ler o átomo como "a rota de perfil tem BOLA" ou "faltou um check de autorização", reescrever.**
29. **Cross-ref:** 01–07 = premissa de token confiável que este átomo inverte; 05/06 = guarda de posse e superfície; 07 = disciplina "guarda certa/forjado a montante"; 02 = contraste "o ataque não toca o token"; **nenhum** átomo de API 09+; **não** antecipar `auth-no-lockout`/`oauth-client-cred-unverified`; sem par web.
30. **Impacto honesto:** impersonation total de qualquer handle público + leitura de dado privado + não-revogável. **Não inflar** — não é priv-esc (sem admin), não é RCE/dump, não é bypass de **autorização** (a autorização funcionou sobre identidade falsa; o bypass é de **autenticação**).

**Bloqueante remanescente:** nenhum. Design fechado pelo mantenedor; toolchain herdado e lido dos arquivos de 01–07; URL do primer verificada por fetch (200, 0 redirects, H1 correto) e seções do RFC 9110 (§15.5.2, §15.5.4) conferidas em texto bruto nesta fase; shape TS, comportamento dos endpoints nos dois gêmeos, o round-trip base64url, o comportamento de token lixo e o foil (assinatura) validados em protótipo com o toolchain exato (ver "Validação de typecheck e runtime"). Resto é smoke test em container na Fase 2.

---

## Notas específicas pro Claude Code

- **Princípio guia:** a lição é **autenticação forjável** — o token não prova identidade porque é derivável de um dado público. Se o aluno sair achando "li o objeto de outro por falta de check" (BOLA), "roubei o token" (replay) ou "a cripto é fraca", o átomo falhou.
- **A VIRADA é o enquadramento inteiro.** Nomear explicitamente, no Context do WALKTHROUGH e na tese do README, que os sete átomos anteriores perguntaram "você pode?" e este pergunta "você é mesmo?". Creditar a premissa de token confiável que a Fase 1 manteve. **Sem reabrir** nenhuma lição de 01–07.
- **base64url é CODIFICAÇÃO, nunca "cifra fraca".** Qualquer frase que trate o token como cripto está **errada**. Não há segredo, não há algoritmo. O foil (assinar) existe pra matar a leitura "assinar resolve".
- **A guarda de posse está CERTA — o breach está a montante.** A rota de perfil **não** tem bug de authz; o `403` do baseline prova. A mentira entra no `caller`, dentro de `authenticate`. Repetir em três lugares (Spot the bug, Step 5 item 1, DIFF). **Espelha a disciplina anti-04 do 07** (guarda certa, o forjado a montante) — creditar o formato, não reabrir BOPLA.
- **A prova é o dado privado da vítima na resposta do atacante** (`200` + email da `alice`), no **mesmo** request do baseline (`403`) com o token trocado. Auto-contida — diferente do 07 (que precisou do termômetro). Qualquer frase que precise de um "segundo caminho" pra provar está errada aqui.
- **UM handler no "Spot the bug": `authenticate` do vulnerable.** A falha não está numa rota — está na função de autenticação. **NÃO** mostrar duas rotas como assimetria (isso é 05).
- **O diff toca três pontos, e isso é a NATUREZA da classe.** Explicar no DIFF por que geração+resolução+mapa são inseparáveis (não dá pra ter token auto-descritivo E lookup). **NÃO** tentar espremer num diff de uma linha; **NÃO** apresentar como "exceção à regra um-átomo-uma-vuln" — é uma vuln (identidade forjável), um eixo (decode vs. lookup), três pontos.
- **Sem `is_admin`, sem papel, sem admin.** Não é escalação de privilégio. O impacto é **virar outro usuário comum** e ler o dado privado dele. Não copiar seed de 04/06/07 com `is_admin`.
- **`email` nos DOIS gêmeos — não é over-serialization.** A resposta está correta pro dono; a falha é que o dono foi forjado. Não esconder `email` no fixed (não é o 06); não usar `...user` (desnecessário e confundiria com 06).
- **CLI base64 vs base64url:** a nota cheia vive numa casa só (Step 4). Nos docs gerados, explicar o padding UMA vez (Step 4, onde `alice` entra) e remeter nos outros pontos — não repetir a dissertação do padding em cada passo.
- **Elenco:** `clancy` atacante **masculino** (self-read baseline); `alice` vítima impersonada que **não loga**. Sem personagem novo, sem admin.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico: `# auth-predictable-token — Broken Authentication`. Headers de seção **traduzidos** no PT; termos técnicos em inglês.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`, linha do átomo no padrão da série (frase única e densa, fechando com a categoria e o CWE entre parênteses). Para token previsível o CWE idiomático é **CWE-340 (Generation of Predictable Numbers or Identifiers)** — **conferir na geração** (o 06 fechou com `API3 …, CWE-213`; o 07 com `CWE-915`). O corte da release `v1.2` é trabalho de mantenedor, pós-merge (CLAUDE.md §12).
- **ROADMAP.md (`atoms/api/ROADMAP.md`):** marcar o átomo 08 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): todos os itens do checklist acima. Se as portas host não forem alcançáveis do sandbox, validar via `docker exec` + `node`/`curl` de dentro do container.
- **Portas:** `127.0.0.1:8208` (vulnerable), `127.0.0.1:8308` (fixed). Bind **só** em `127.0.0.1`.

---

## Verificação factual dos átomos publicados (conferida LENDO os arquivos nesta fase)

A spec afirma herança e contraste com 01–07; tudo abaixo foi conferido **lendo os arquivos publicados nesta fase de planning** (não de memória):

1. **Toolchain** — `package.json` dos sete átomos com express 5.2.1, tsx 4.23.13, typescript 7.0.2, @types/express 5.0.6, @types/node 24.13.5; scripts `start: tsx app.ts`, `typecheck: tsc --noEmit`; `name` por átomo, `private: true`, `type: module`.
2. **`Dockerfile`** — **md5 idêntico nos sete** (`cad28299…`): `node:24.21.0-slim`, `npm ci --omit=dev`, `COPY tsconfig.json` + `COPY app.ts`, `ENV HOST=0.0.0.0`, `EXPOSE 3000`, `USER node` no fim sem `chown`, `CMD ["npm","start"]`.
3. **`tsconfig.json`** — **md5 idêntico nos sete** (`9a2dc4f6…`): `nodenext`, `target/lib es2024`, `types [node]`, `strict`, `noUncheckedIndexedAccess`, `esModuleInterop`, `noEmit`.
4. **`docker-compose.yml`** — bind `127.0.0.1`; `8201/8301` (01) … `8207/8307` (07). Este átomo: **`8208/8308`**.
5. **Bloco de auth (o que este átomo MODIFICA)** — nos sete: `const TOKENS = new Map<string, string>()`, `issueToken` com `randomBytes(24).toString("base64url")` + `TOKENS.set(token, user)`, `authenticate` resolvendo `Bearer` via `TOKENS.get(token) ?? null`, `USERS.has(user)` no login, `res.set("WWW-Authenticate", "Bearer").sendStatus(401)` nos handlers protegidos. Conferido nesta fase: o trecho `issueToken`…fim de `authenticate` tem **md5 idêntico** em 05/06/07; o `fixed/` deste átomo o reusa **byte a byte**, e o `vulnerable/` o deforma (decode em vez de lookup; remove `TOKENS` e o import de `randomBytes`).
6. **Átomo 06 (`bopla-excessive-exposure`)** e **05 (`bfla-method-based`)** — origem do `GET /users/:handle` com guarda de posse (`if (req.params.handle !== caller) return res.sendStatus(403)`), byte-idêntica (`grep -Fxc` = 1). O `GET` **fixed do 05** retorna `{ handle, displayName }` (campos nomeados); este átomo retorna `{ handle, displayName, email }`, mesma forma com o campo privado acrescentado. `USERS = new Map<string, User>` em 04–07.
7. **Átomo 07 (`bopla-mass-assignment`)** — a **disciplina** "a guarda (admin) está correta e byte-idêntica ao fix do 04; o bug é o papel forjado, a montante, no `PATCH`". Este átomo espelha o **formato** (guarda de posse correta; o forjado é a identidade, a montante, em `authenticate`), **sem** reabrir mass assignment. 07 é o par imediato e o modelo de densidade desta spec.
8. **Átomo 02 (`bola-uuid-leaked`)** — a disciplina publicada "o ataque **não toca** o token: você não decodifica, altera ou forja" (WALKTHROUGH e DIFF). Este átomo é o **oposto exato** (o ataque é só o token), e a inversão é creditável porque 02 está publicado.
9. **Elenco** — `clancy` atacante (masculino) em todos; `alice` vítima principal; `carol` admin no 04; `bob`/`carol` operadores no 03. Este átomo: `clancy` (self-read baseline) e `alice` (impersonada, não loga), **sem admin**.
10. **H1** — 01–03: `# <id> — Broken Object Level Authorization (BOLA)`; 04/05: `# <id> — Broken Function Level Authorization (BFLA)`; 06/07: `# <id> — Broken Object Property Level Authorization (BOPLA)`. Este: **`# auth-predictable-token — Broken Authentication`** (primeiro da série com essa classe).
11. **Primers publicados** — 01–03: IDOR (`/web-security/access-control/idor`); 04–05: Access control (`/web-security/access-control`); 06: Information disclosure (`/web-security/information-disclosure`); 07: seção Mass assignment de `/web-security/api-testing#mass-assignment-vulnerabilities`. Todos com o **H1 da página** como texto do link, exceto 07 (seção). Este átomo: **página inteira** `Authentication vulnerabilities` (`/web-security/authentication`), H1 como texto do link — sem anchor, porque o conceito-mãe não tem subseção própria.
12. **Publicação** — `atoms/api/ROADMAP.md`: **01–07 `[x]`**, **08 (`auth-predictable-token`) `[ ]`**, 09+ `[ ]`. Árvore de `atoms/api/`: `API1-...` (três átomos), `API3-...` (dois), `API5-...` (dois); **`API2-...` NÃO existe** — este átomo a cria. A linha API2 da tabela de Cobertura do ROADMAP já lista os três átomos de API2.
13. **Comportamento herdado** — JSON malformado no `POST /login` responde `400` com stack trace no corpo HTML (handler de erro default do Express). Idêntico ao que este átomo fará; **não** é novidade nem lição deste átomo.
