# Spec — Átomo 15: `session-fixation`

> Documento de especificação para o Claude Code implementar o décimo-quinto átomo do projeto `atomicvulns` (Fase 3 — "Access Control & Autenticação", milestone `v0.3.0`). Este átomo **FECHA a Fase 3** (é o 5º e último átomo da fase — confirmado no `ROADMAP.md`) e **muda de eixo**: sai de A01 (IDOR/BOLA — 03/11/12) e A02 (a trilogia JWT — 05/13/14) e entra em **A07 — Identification and Authentication Failures**. É o **primeiro átomo A07 do repo** (a pasta `atoms/A07-auth-failures/` ainda não existe — a Fase 2 a cria) e o **primeiro átomo de SESSÃO** do projeto: o primeiro que usa **cookies de sessão** de forma central. Os JWT eram stateless (token auto-contido no header); IDOR/BOLA usavam tokens/ids em header. Aqui o eixo é o **ciclo de vida de uma sessão server-side**.
>
> **A lição em uma linha:** uma sessão autenticada NÃO deve carregar um identificador que existia ANTES da autenticação — porque qualquer coisa conhecida antes do login pode ter sido plantada por um atacante. O bug é o servidor **não emitir um NOVO session id no instante em que o nível de privilégio da sessão muda** (anônimo → autenticado). O fix é uma linha conceitual: **REGENERAR o session id no login**.
>
> Leia junto com `CLAUDE.md` (Seções 3.3 — este átomo **TEM HTML e trilha dupla**, NÃO é API-only; §5 — passo "o que a vuln NÃO é" obrigatório; §6 — didático > realista; §8 — segurança; §10.5 — leitura de referência; e a seção "Memória de projeto" — o Claude Code **não grava memória por conta própria**, propõe no fim), `ROADMAP.md`, e — como molde — os átomos HTML de **lógica** já publicados (`idor-numeric-id` (03), `sqli-union-basic` (01, referência canônica de HTML/Jinja2), `idor-uuid-guessable` (11), `bola-rest` (12)) e, **de leve, para o contraste conceitual**, a trilogia JWT (05/13/14 — eles **forjam/quebram a prova de identidade**; fixation **captura a sessão sem forjar nada**).
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, templates — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Nota de planning 1 — posição na Fase 3: 15 FECHA a Fase 3 (confirmado; sem discrepância)

> **Confirmado contra o `ROADMAP.md` (fonte da verdade; `CLAUDE.md` §9/§10.5).** A Fase 3 ("Access Control & Autenticação", `v0.3.0`) tem **cinco** átomos — `11 idor-uuid-guessable`, `12 bola-rest`, `13 jwt-weak-secret`, `14 jwt-key-confusion`, **`15 session-fixation`** — e o **15 é o quinto e último**, marcado `[ ]` (os quatro anteriores já `[x]` em `main`). **Logo o 15 é o phase-closer da Fase 3.** Isto **honra e resolve** a "Nota de planning 1" da spec do 14, que registrou que *"o `session-fixation` (15) é o phase-closer, não o 14"* — o 14 fechou a **trilogia JWT**, o 15 fecha a **fase**. Sem discrepância a reconciliar aqui.
>
> **Primeiro átomo A07 do repo.** O `ROADMAP.md` lista `session-fixation` sob "A07 Auth Failures". Não há nenhuma pasta `atoms/A07-auth-failures/` hoje (confirmado: o repo tem A01, A02, A03, A10). A Fase 2 **cria** a pasta `atoms/A07-auth-failures/session-fixation/`. *(O `ROADMAP.md` também lista um `weak-password-reset` como A07 mais adiante (átomo 37, Fase 7) — **não-publicado**, portanto **proibido** referenciá-lo ou foreshadowá-lo no conteúdo do átomo, `CLAUDE.md` §5. Enquadrar o 15 apenas como "o primeiro átomo A07 do projeto", sem prometer outros.)*

## Nota de planning 2 — versionamento/release fica FORA desta spec

> O 15 fecha a Fase 3, o que dispara a release `v0.3.0` (marco publicável, `ROADMAP.md`). **Isso é trabalho de release, não de átomo** — não entra nesta spec nem no conteúdo do átomo. O átomo se descreve como "átomo 15, o que fecha a Fase 3"; **CHANGELOG/tag/anúncio de release** são uma tarefa própria do mantenedor, pós-merge (`CLAUDE.md` §10.4). O conteúdo publicado do átomo **não** anuncia a release nem a Fase 4 (ver "Política de referência cross-átomo": ZERO foreshadow).

---

## Identidade

- **ID:** `session-fixation`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A07 — Identification and Authentication Failures**. Pasta `atoms/A07-auth-failures/` (segue a convenção de slug curto das pastas: `A07-auth-failures`, espelhando `A01-broken-access-control`, `A02-cryptographic-failures`). Confirmado contra o `ROADMAP.md` ("A07 Auth Failures"). **Primeiro átomo desta categoria no repo.** Em prosa (README/DIFF/CHANGELOG) usar o nome OWASP completo — **"A07 — Identification and Authentication Failures"** — como os irmãos usam os nomes completos ("Broken Access Control", "Cryptographic Failures").
- **Pasta:** `atoms/A07-auth-failures/session-fixation/`
- **Número sequencial:** 15
- **Porta vulnerable:** `127.0.0.1:8015`
- **Porta fixed:** `127.0.0.1:8115`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (`CLAUDE.md` §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–14.
- **Fase / milestone:** Fase 3, `v0.3.0`. **Quinto e último átomo da Fase 3 — phase-closer** (ver Nota de planning 1). Versionamento/release **fora desta spec** (Nota de planning 2).
- **Branch de trabalho:** `atom/session-fixation`. Convenção `atom/<id>` (`CLAUDE.md` §6). Branch já criada nesta fase de planning.
- **Theory primer (registrar candidato, confirmar por fetch na Fase 2):** página conceitual de session fixation / session management na PortSwigger Web Security Academy — ver seção "Theory primer". **Confirmar por fetch na Fase 2, não inventar.**
- **H1 dos READMEs (idêntico em EN e PT, `CLAUDE.md` §7):** candidato `# session-fixation — Session fixation` — segue o padrão dos irmãos (`id` + nome canônico da vuln em inglês; ex. `bola-rest — Broken Object Level Authorization (BOLA)`, `jwt-none-alg — JWT alg=none signature bypass`). Como o `id` já **é** o nome da vuln, a descrição é o nome canônico em inglês. **Opcional (Fase 2 decide):** um qualificador descritivo curto, no estilo dos H1s da trilogia JWT, ex. `# session-fixation — Session fixation (session id not regenerated at login)`, fixando o mecanismo. Manter a forma "`id` — descrição em inglês"; texto exato confirmável na Fase 2.

---

## Classe de vulnerabilidade

**Session fixation.** Uma app web com login e uma área autenticada. O servidor mantém **sessões server-side** num store (`SESSIONS = {session_id: {...}}`) e identifica cada sessão por um **cookie `session_id` opaco** (só o id viaja no cookie; os dados ficam no servidor) — o padrão clássico de PHP (`PHPSESSID`), Java (`JSESSIONID`) e da maioria dos frameworks server-side. O visitante anônimo já recebe um `session_id` (normal). No login, o servidor **autentica a sessão atual mantendo o MESMO `session_id`** — não emite um id novo quando o privilégio muda de anônimo para autenticado. Essa não-regeneração é o bug inteiro.

O atacante **obtém um `session_id` válido do servidor** (basta um `GET /` anônimo — o servidor emite um id) e o **planta** no navegador da vítima **ANTES** dela logar (no mundo real, via link/URL, cookie de subdomínio, ou XSS; no lab, o aluno seta o cookie à mão). A vítima loga **normalmente**, com **as credenciais dela** (senha correta, ato 100% legítimo). Mas como o servidor **não troca o `session_id` no login**, aquela sessão — agora autenticada como a vítima — **ainda carrega o id que o atacante conhece**. O atacante usa esse id e **entra na sessão autenticada da vítima**. Ele **nunca soube a senha**.

### A lição-coração

> **"Uma sessão autenticada não pode ser identificada por algo que existia antes da autenticação. O bug é o servidor não emitir um NOVO session id no instante em que o nível de privilégio da sessão muda (anônimo → autenticado)."**

**O mecanismo (o que torna contraintuitivo — cravar no WALKTHROUGH e no DIFF).** Na maioria das vulns o atacante **ROUBA** algo da vítima. Em session fixation o atacante **DÁ** algo à vítima: ele **planta** um `session_id` conhecido no navegador dela **antes** do login, e **espera** ela autenticar aquele id. A vítima faz tudo certo — credenciais dela, senha correta, login legítimo. O erro é do **servidor**, que eleva ao estado autenticado um id que já era conhecido por um terceiro. Direção invertida (o atacante **fornece**, não subtrai) e timing invertido (ele age **antes** do login, não depois).

**Sub-lição (cravar): o ÚNICO ponto de divergência é o instante da autenticação.** As duas versões (vulnerable e fixed) fazem o **mesmo** antes do login (emitem um `session_id` pra sessão anônima — normal) e o **mesmo** depois (têm uma sessão autenticada — normal). A diferença é **cirúrgica e pontual**: no login, a vulnerable **mantém** o id; a fixed **regenera**. Não é "antes" que diverge, não é "depois" — é o **momento exato** em que a sessão muda de anônima para autenticada. Bug pontual.

### DISTINÇÃO CENTRAL — FIXATION vs HIJACKING (a lição que separa quem entende)

Session fixation **NÃO é** session hijacking. Este é o mal-entendido vizinho que o átomo tem que isolar — cravar no WALKTHROUGH (passo "o que a vuln NÃO é", obrigatório por `CLAUDE.md` §5) e no DIFF:

| | **HIJACKING (roubo)** | **FIXATION (fixação — ESTE átomo)** |
|---|---|---|
| O que o atacante faz | **ROUBA** um `session_id` **já autenticado** | **FORNECE** um `session_id` **antes** da autenticação |
| Como | sniffing, XSS lendo o cookie, malware — pega algo que **já existe** | planta um id conhecido e **deixa a vítima autenticá-lo** |
| Timing | **DEPOIS** do login (a sessão já é autenticada) | **ANTES** do login (a sessão ainda é anônima) |
| Direção | o atacante **subtrai** (lê/copia da vítima) | o atacante **acrescenta** (dá à vítima) |
| O atacante leu o cookie autenticado da vítima? | **sim** — é o ataque | **não** — ele teve o id desde antes do login |

**A frase-regra:** *hijacking rouba DEPOIS; fixation planta ANTES.* O atacante de fixation **nunca acessou a sessão autenticada da vítima diretamente nem leu o cookie dela** — ele **teve o id, desde antes**, e a **vítima** é quem o elevou a autenticado. Confundir os dois leva o aluno a "consertar" fixation com defesas de **roubo de cookie** (HttpOnly/Secure) — que **não** resolvem (ver "O bug e o fix", nota obrigatória).

### Contraste com o arco (eixo NOVO — A07)

O contraste principal é **CONCEITUAL**, não com um átomo específico. Paralelo bom (citável de leve, os JWT são publicados): a trilogia JWT (05/13/14) era sobre **FORJAR/QUEBRAR a prova de identidade** — o atacante fabricava ou adulterava o **token** (a credencial). Session fixation é sobre **CAPTURAR a sessão SEM forjar nada**: o atacante não falsifica credencial nenhuma, não adivinha, não quebra cripto — ele explora o **CICLO DE VIDA da sessão** (o servidor não trocar o id no login). Distingue também do eixo **A01** desta fase (03/11/12: IDOR/BOLA — ausência de check de autorização sobre um objeto): lá o atacante lê **dado de outro user** com a **própria** identidade; aqui ele **assume a sessão autenticada** de outro user sem nunca provar ser ele.

### Por que A07 (Identification and Authentication Failures)

Session fixation é uma falha de **gerenciamento de sessão** — sub-tópico canônico de A07 no OWASP Top 10 2021 (que absorveu o antigo A2:2017 "Broken Authentication" e cita explicitamente "session fixation" e "não invalidar/rotacionar session ids"). A superfície é o **ciclo de vida da sessão** (emissão do id, elevação de privilégio no login, invalidação). Coerente com o eixo de **autenticação/identidade** da Fase 3, mas num sub-eixo (sessão) que os JWT (stateless, sem sessão server-side) não tocavam.

---

## Uma vuln só — o id é FORTE, a senha é trivial de propósito, sem XSS, flags idênticas

Invariante inegociável (`CLAUDE.md` §2, "um átomo = uma vulnerabilidade"): a **única** falha é o servidor **não regenerar o `session_id` no login**. Garantias (todas validar na Fase 2):

- **O `session_id` é IMPREVISÍVEL — `secrets.token_urlsafe(32)` — nas DUAS versões.** Este é o ponto mais fácil de estragar: se o id fosse adivinhável, o átomo teria **DUAS** vulns (id fraco + não-regeneração). A vuln deste átomo é a **NÃO-REGENERAÇÃO**; o id em si é forte, e a vulnerable e a fixed **geram ids idênticos em força** (a mesma `secrets.token_urlsafe`). Cravar: *"o atacante não adivinhou o id — o servidor o entregou (um `GET /` anônimo), e o bug é que esse id sobrevive ao login."*
- **A senha é DELIBERADAMENTE trivial.** Credenciais fixas e óbvias (`alice` / `password123`), verificação **trivial** (comparação direta, **sem** hashing, **sem** bcrypt, **sem** rate limiting). A senha existe só pra dar **realismo à narrativa** (a vítima loga com as credenciais dela, ato legítimo) — **não** é objeto de estudo. Senha em texto claro no código é **intencional** (dummy de lab, `CLAUDE.md` §8.3), **não** é uma segunda vuln. O DIFF/README **deve** notar: *"a autenticação está simplificada de propósito; a falha não é a senha nem o login, é o `session_id` não regenerar."*
- **Autoescape do Jinja LIGADO (default), sem XSS.** O `session_id` e o `user` são refletidos no HTML via `{{ }}` (escapados) — **sem** `|safe`, **sem** `Markup`, **sem** `render_template_string`. O `session_id` é base64url (`token_urlsafe`, sem metacaracteres HTML) e o `user` vem de um dict fixo; ainda assim passam pelo escape. **Sem XSS acidental.**
- **Servidor NÃO é "permissivo" (não adota id arbitrário do cliente).** O servidor só honra ids que **ele mesmo emitiu** (`current_session()` cria um id novo se o cookie trouxer um id desconhecido). Adotar um id arbitrário inventado pelo cliente seria um **segundo flavor** de fixation (session adoption) — **fora de escopo**. A única falha é: um id **legitimamente emitido** pelo servidor **sobrevive ao login**. Isso casa com a encenação (o atacante **obtém** um id via `GET /`, não inventa um).
- **As flags de cookie são IDÊNTICAS nas duas versões** (ver "Decisão: flags de cookie") — logo **não** fazem parte do diff. A única diferença vulnerable × fixed é a regeneração no login.
- **Sem banco, sem segunda superfície:** `SESSIONS` e `CREDENTIALS` em memória; `/account` devolve só dado fake benigno; nenhum segredo/PII real; a chave de assinatura do Flask **não** é usada (não usamos `flask.session` — ver "A decisão estrutural").

---

## A decisão estrutural — sessão SERVER-SIDE MANUAL (a "Saída B" do 15): por quê (TRAVADA)

**O ponto que faz o átomo existir** — e é o **mesmo movimento honesto do 14** (a "SAÍDA B"): *a ferramenta padrão da linguagem já mitiga o bug ingênuo, então o átomo tem que modelar o anti-padrão onde a vuln realmente vive no mundo real.*

**NÃO usar `flask.session`.** A sessão nativa do Flask é um **cookie assinado client-side**: o **conteúdo** da sessão (o dict inteiro) é serializado, assinado com a `SECRET_KEY` e guardado **no cookie**, no cliente. Ela **não tem** um `session_id` opaco server-side pra "fixar", e **regenera por natureza**: quando o login faz `session["authenticated"] = True; session["user"] = "alice"`, o **valor do cookie muda** (agora codifica o dict autenticado, re-assinado) — o cookie pré-login (dict anônimo) e o pós-login (dict autenticado) são **valores diferentes**. Um atacante não consegue "plantar" um valor que vire autenticado: pra o cookie dizer `authenticated: True` ele precisaria **forjar a assinatura** (precisa da `SECRET_KEY` — isso seria **outra** vuln, secret fraco/vazado, não fixation); e mesmo plantando um cookie anônimo, após o login da vítima o cookie **muda** pro valor autenticado (que o atacante não tem). **Então um átomo "vulnerável" construído sobre `flask.session` NÃO seria vulnerável** — mesma armadilha estrutural do PyJWT no 14 (a ferramenta padrão já mitiga).

**A saída TRAVADA — SAÍDA B: sessão SERVER-SIDE MANUAL.** Um dict `SESSIONS = {session_id: {dados}}` no servidor, e um cookie `session_id` **opaco** (só o id, não os dados). É o padrão **PHP (`PHPSESSID`) / Java (`JSESSIONID`) / maioria dos frameworks server-side**, e é **exatamente** onde session fixation mora no mundo real: sessões com um id no cookie que precisa ser **rotacionado** na mudança de privilégio. O DIFF/README **DEVE** explicar **POR QUE** sessão manual e não `flask.session` (senão o aluno pensa *"por que esse dev reinventou a sessão em vez de usar a do framework?"*). Resposta honesta a cravar:

- **Muitos servidores reais têm exatamente essa forma:** todo framework server-side com store de sessão + id no cookie (PHP, Java, Rails, Django, Express-session...) precisa **rotacionar o id no login**, e esquecer de fazê-lo é o bug. A vuln vive na **política de ciclo de vida da sessão**, não na tecnologia de cookie do Flask.
- **A própria resistência do `flask.session` é a lição de que a escolha de mecanismo importa** — e de que o bug sobrevive em **sessões server-side com id no cookie** (a esmagadora maioria fora do mundo Flask-signed-cookie). O `flask.session` "regenera por design"; o átomo modela o mecanismo que **não** regenera sozinho e **exige** a regeneração explícita no login.

*(Paralelo direto com o 14: lá o PyJWT moderno **recusa** a key confusion ingênua, então o vulnerable verifica **na mão**; aqui o `flask.session` **resiste** à fixation por design, então o vulnerable usa uma **sessão server-side manual**. Em ambos: "a lib/mecanismo padrão mitiga; o bug vive em quem faz X à mão / de outro jeito". Registrar esse paralelo no DIFF — é a mesma disciplina de honestidade didática do projeto.)*

---

## Feature simulada — app web com login e área autenticada (TEM HTML, trilha dupla)

**Uma app web mínima com três telas/rotas:** a home (mostra se você está anônimo ou logado, e um form de login), o `POST /login` (autentica), e a página `/account` (área protegida, só sessão autenticada). Do ponto de vista do dev, *"o usuário anônimo navega, faz login, e vira autenticado — a mesma sessão que ele já tinha agora está logada"* — mas **reaproveitar a mesma sessão (o mesmo id) através da fronteira de privilégio** é a porta.

**Tipo de átomo:** `[x] com HTML` / `[ ] API-only` — **decisão travada** (volta ao molde web clássico que a trilogia JWT API-only deixou de lado). Justificativa: session fixation é uma vuln de **navegador/cookie de sessão**; a encenação (anônimo → login → área logada) e a **prova visual** (o `session_id` mudar ou não no login) ficam muito mais claras com uma UI mínima. Consequências (molde do `idor-numeric-id`/`sqli-union-basic`): há `templates/`, `render_template`, cookies; WALKTHROUGH em **trilha dupla** (Burp principal + browser secundária, `CLAUDE.md` §3.3). HTML mínimo (banner, form, dica de Burp, ≤40 linhas por template, sem frameworks de front).

---

## Modelo de identidade e dados — sem banco (SESSIONS + CREDENTIALS em memória)

**Sem banco** (o storage segue a superfície do bug, `CLAUDE.md` §3.4 — a sessão vive num dict em memória, não precisa de SQLite). Nota "Stack note — no database" no README, espelhando os irmãos de lógica (`idor-numeric-id`). **Estado de processo único** aceitável (nada persiste; restart zera as sessões).

- **`SESSIONS = {}`** — store server-side: `{session_id: {"authenticated": bool, "user": str | None}}`.
- **`CREDENTIALS = {"alice": "password123"}`** — credencial **dummy trivial** (`CLAUDE.md` §8.3). Uma vítima é suficiente. Verificação por comparação direta (sem hash) — **intencional**, não é a lição.
- **Dado da conta (benigno, sem PII real).** `/account` mostra algo claramente "privado da alice" mas **fake** — ex. `Signed in as alice · Email alice@example.test · Plan: Pro · Balance: $4,200.00`. Torna a **vitória do atacante concreta** (ele vê a página privada da vítima) sem nenhum dado sensível real.

---

## Rotas — o coração está no `/login`

Imports (idênticos vulnerable × fixed):

```python
import os
import secrets
from flask import Flask, request, redirect, render_template, make_response, abort
```

Constantes, store e helper no topo. **A diferença vulnerable × fixed é APENAS o bloco pós-checagem de credenciais no `POST /login`** — todo o resto (`current_session`, `GET /`, `GET /account`, `SESSIONS`, `CREDENTIALS`, rodapé, templates) é **byte-idêntico**.

```python
app = Flask(__name__)

# In-memory server-side session store: {session_id: {"authenticated": bool, "user": str|None}}.
# Models the classic server-side session pattern (PHP's PHPSESSID, Java's JSESSIONID): an
# OPAQUE session id travels in the cookie, the session data stays on the server. We do NOT use
# flask.session on purpose — its signed client-side cookie has no server-side id to fix and
# regenerates by design, so session fixation cannot live there (see DIFF.md).
SESSIONS = {}

# DUMMY lab credential — trivial by design. The password is NOT the object of study; auth is
# simplified so the ONLY variable is what happens to the session id at login. Plaintext is
# intentional here (CLAUDE.md §8.3), not a second vulnerability.
CREDENTIALS = {"alice": "password123"}


def current_session():
    # Return (sid, session_dict) for the request's cookie, issuing a fresh ANONYMOUS session
    # if the cookie is missing or unknown to the server. The server only honors ids it issued
    # (it does not adopt arbitrary client-supplied ids), and the id is unguessable
    # (secrets.token_urlsafe) in BOTH versions — the bug is non-regeneration, not a weak id.
    sid = request.cookies.get("session_id")
    if not sid or sid not in SESSIONS:
        sid = secrets.token_urlsafe(32)
        SESSIONS[sid] = {"authenticated": False, "user": None}
    return sid, SESSIONS[sid]
```

### `GET /` — emitir/reusar o `session_id`, mostrar o estado + form de login (idêntico nas duas versões)

```python
@app.route("/")
def index():
    sid, sess = current_session()
    resp = make_response(render_template("index.html", sid=sid, sess=sess))
    resp.set_cookie("session_id", sid, httponly=True, samesite="Lax")
    return resp
```

- Visitante anônimo sem cookie → `current_session()` emite um id, cria `SESSIONS[id] = {anônimo}`, e o `Set-Cookie` entrega o id. **Emitir id pra anônimo é NORMAL, não é o bug.**
- Com cookie válido → reusa. O `Set-Cookie` é reafirmado a cada `/` (mesmo valor; inofensivo, e deixa o id visível na resposta do Burp).

### `POST /login` — VULNERABLE (mantém o id: o coração materializado)

```python
@app.route("/login", methods=["POST"])
def login():
    sid, sess = current_session()
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    if CREDENTIALS.get(user) != password:
        abort(401)  # trivial credential check — the password is not the object of study
    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. The id that
    # existed before login (possibly attacker-planted) now identifies an AUTHENTICATED session.
    # No new id when the privilege level changes (anonymous -> authenticated) = session fixation.
    sess["authenticated"] = True
    sess["user"] = user
    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated
```

### `POST /login` — FIXED (regenera o id: o fix inteiro)

```python
@app.route("/login", methods=["POST"])
def login():
    sid, sess = current_session()
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    if CREDENTIALS.get(user) != password:
        abort(401)  # trivial credential check — the password is not the object of study
    # FIXED: authenticate, then REGENERATE the session id. Rebind the now-authenticated session
    # onto a NEW id and discard the old one, so any id that existed before login (possibly
    # attacker-planted) can never become authenticated. This regeneration is the whole fix.
    sess["authenticated"] = True
    sess["user"] = user
    new_sid = secrets.token_urlsafe(32)
    SESSIONS[new_sid] = sess          # rebind the (now-authenticated) session onto a NEW id
    del SESSIONS[sid]                 # discard the old (possibly planted) id
    resp = redirect("/account")
    resp.set_cookie("session_id", new_sid, httponly=True, samesite="Lax")
    return resp
```

- **O CONTRASTE é o diff (obrigatório):** as duas versões marcam `sess["authenticated"] = True; sess["user"] = user` **igual** (autenticar é o mesmo). A fixed **acrescenta**: gera um `new_sid`, **rebind**a a sessão (agora autenticada) nesse id novo, **deleta** o id antigo, e seta o cookie novo. O bloco pós-checagem é o **único** ponto de divergência. Diff **lógica-diferente** (código adicionado), o mesmo TIPO dos A01 e dos JWT.
- **`SESSIONS[new_sid] = sess` + `del SESSIONS[sid]`** genuinamente **migra a sessão** (o mesmo objeto, agora rebindado a um id novo) e **descarta** o antigo — é literalmente a "regeneração de session id" do mundo real (preserva o objeto de sessão, troca o identificador). Como `current_session()` garante `sid in SESSIONS`, o `del` é seguro. Aqui a sessão não carrega dado pré-login digno de preservar além do que acabamos de setar; **numa app real você copiaria estado benigno pré-login (carrinho, locale) pro id novo — mas NUNCA o id em si.** (Nota mencionável no DIFF.)

### `GET /account` — área protegida (idêntico nas duas versões)

```python
@app.route("/account")
def account():
    sid = request.cookies.get("session_id")
    sess = SESSIONS.get(sid) if sid else None
    if not sess or not sess["authenticated"]:
        return redirect("/")  # not an authenticated session -> back to the login page
    return render_template("account.html", sid=sid, user=sess["user"])
```

- **Decisão do Claude Code (sinalizada):** sessão não-autenticada em `/account` → **`redirect("/")`** (a home/login), não `403`. Justificativa: é o comportamento **web-natural** (usuário não-logado cai na tela de login) e casa com a trilha browser (o aluno "cai" no login). No Burp, o `302 → /` é um sinal de "negado" perfeitamente legível. **`403` é alternativa igualmente aceitável** (mais "API-like"); a Fase 2 pode trocar se preferir o status explícito — o importante é que a **sessão não-autenticada não vê `/account`**.
- **`/account` NÃO cria sessão** (diferente de `GET /`): só **consome** sessões autenticadas. No fixed, o id antigo do atacante foi **deletado** (`del SESSIONS[sid]`) → `SESSIONS.get(old_sid)` é `None` → redirect. O id plantado não só está não-autenticado: **sumiu.**

### Rodapé (idêntico nas duas versões)

```python
if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

---

## Decisão: mostrar o `session_id` na página (sinalizada — Claude Code decide)

**Decisão travada pelo Claude Code: SIM, exibir o `session_id` na página** (na home e na `/account`), via `{{ sid }}` (escapado). Justificativa (`CLAUDE.md` §6 — didático > realista, o mantenedor não tem preferência forte):

- A **prova central** deste átomo é *"o `session_id` é o MESMO antes e depois do login"* (vulnerable) vs *"MUDA no login"* (fixed). Exibir o id **torna essa prova glanceable**: o aluno loga e **vê** o id continuar idêntico (vulnerable) ou virar outro (fixed), sem precisar ler o cookie no Burp/DevTools a cada passo. É o observável mais importante do átomo — reduzir o atrito pra observá-lo vale a pequena artificialidade.
- **Custo (artificialidade):** apps reais não imprimem o session id na tela. **Mitigação:** uma nota de uma linha no README/WALKTHROUGH — *"apps reais não exibem o session id; ele aparece aqui só pra a comparação antes/depois-do-login ficar visível num relance — num engagement real você o leria do cookie, no Burp ou no DevTools."*
- **Não é uma segunda vuln:** o modelo de ameaça do átomo **já assume** que o atacante conhece o id (ele o **plantou**). Exibi-lo apenas concretiza essa premissa; não vaza nada que o exploit já não pressuponha. E passa pelo autoescape do Jinja (sem XSS).

## Decisão: flags de cookie (sinalizada — Claude Code decide)

**Decisão travada pelo Claude Code: setar `httponly=True, samesite="Lax"` nas DUAS versões; NÃO setar `secure`.** Justificativa:

- **Flags idênticas nas duas versões** → **não** entram no diff (a única diferença é a regeneração). Mantém "uma vuln só".
- **`HttpOnly` presente na vulnerable É pedagógico, não acidental:** preempta estruturalmente o mal-entendido *"eu conserto adicionando HttpOnly"*. O aluno vê que a vulnerable **já tem** HttpOnly + SameSite e **continua explorável** — porque essas flags protegem contra **roubo** de cookie (hijacking), e fixation **não rouba**. Você **não** pode "consertar com HttpOnly": já está lá, e o bug persiste. O fix é **regenerar**.
- **`secure` NÃO é setado** porque o lab roda em **HTTP puro local** (`127.0.0.1:8015`); com `Secure` o cookie não seria enviado sobre HTTP e **quebraria o lab**. Nota no DIFF: *"em produção você setaria `Secure`, mas ele é ortogonal à fixation — endereça interceptação/roubo, não o ciclo de vida da sessão."*
- **Nota (não vira toca de coelho):** `HttpOnly` bloqueia **um** vetor de plantio (o `document.cookie` via JS) e o roubo via JS — mas fixation tem vetores não-JS (id de sessão em URL, etc.), e, de todo modo, o fix durável é a **regeneração**, não as flags. Manter isso como nota curta no DIFF, não um tratado.

---

## HTML — `templates/index.html` e `templates/account.html` (mínimos, molde do repo)

Molde do `idor-numeric-id`/`sqli-union-basic`: `<!doctype>`, banner de aviso obrigatório, ≤40 linhas, ≤5 linhas de CSS inline, **sem** frameworks, **sem** JS (não é uma vuln client-side), dica de Burp no rodapé. Templates **idênticos** entre vulnerable e fixed (o diff vive só no `app.py`). Candidatos (Fase 2 finaliza texto exato):

**`templates/index.html`** (~24 linhas):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Account Portal</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}code{background:#eee;padding:0 .3em;word-break:break-all;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>Account Portal</h1>
<p>Your session id: <code>{{ sid }}</code></p>
{% if sess.authenticated %}
<p>Status: <strong>logged in as {{ sess.user }}</strong>. <a href="/account">Go to my account &rarr;</a></p>
{% else %}
<p>Status: <strong>anonymous</strong> (not logged in).</p>
<form method="post" action="/login">
<input name="user" value="alice">
<input name="password" value="password123">
<button type="submit">Log in</button>
</form>
{% endif %}
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

**`templates/account.html`** (~22 linhas):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>My Account &mdash; {{ user }}</title>
<style>body{font-family:sans-serif;max-width:720px;margin:2em auto;padding:0 1em;}code{background:#eee;padding:0 .3em;word-break:break-all;}.acct{background:#eee;padding:.8em;border-radius:4px;}</style>
</head>
<body>
<p><strong>&#9888; Intentionally vulnerable. Run locally only.</strong></p>
<h1>My Account</h1>
<p>Your session id: <code>{{ sid }}</code></p>
<div class="acct">
<p>Signed in as <strong>{{ user }}</strong>.</p>
<p>Email: {{ user }}@example.test &middot; Plan: Pro &middot; Balance: $4,200.00</p>
</div>
<p><a href="/">&larr; Home</a></p>
<p><em>Open with Burp proxy enabled, interact once, then work from Burp Repeater.</em></p>
</body>
</html>
```

- **Form pré-preenchido** `alice` / `password123` (o campo de senha mostra o valor em texto — o password **não é** o objeto de estudo, então exibi-lo plano reforça a triviália; login em um clique). *(Fase 2 pode usar `type="password"` se preferir realismo — irrelevante à lição.)*
- `word-break:break-all` no `<code>` só pra o id longo não estourar a linha. CSS dentro do limite (≤5 linhas efetivas).

---

## O bug e o fix — diff de LÓGICA-DIFERENTE (código adicionado no `/login`)

**Tipo de diff: lógica-diferente** — o `POST /login` vulnerable **mantém** o id; o fixed **acrescenta** a regeneração (novo id + rebind + del do antigo + cookie novo). É o tipo dos **A01** e dos **JWT** (código presente e alterado), **NÃO** o valor-diferente do 13 nem o app-idêntico de um par XSS. O `app.py` difere **apenas** no bloco pós-checagem de credenciais do `/login`; todo o resto (`current_session`, `/`, `/account`, `SESSIONS`, `CREDENTIALS`, rodapé) e **os dois templates** são **byte-idênticos**. Diff colável (candidato — Fase 2 gera o real):

```diff
     if CREDENTIALS.get(user) != password:
         abort(401)  # trivial credential check — the password is not the object of study
-    # VULNERABLE: authenticate the CURRENT session, keeping the SAME session_id. The id that
-    # existed before login (possibly attacker-planted) now identifies an AUTHENTICATED session.
-    # No new id when the privilege level changes (anonymous -> authenticated) = session fixation.
+    # FIXED: authenticate, then REGENERATE the session id. Rebind the now-authenticated session
+    # onto a NEW id and discard the old one, so any id that existed before login (possibly
+    # attacker-planted) can never become authenticated. This regeneration is the whole fix.
     sess["authenticated"] = True
     sess["user"] = user
-    return redirect("/account")  # cookie unchanged — the pre-login sid is now authenticated
+    new_sid = secrets.token_urlsafe(32)
+    SESSIONS[new_sid] = sess          # rebind the now-authenticated session onto a NEW id
+    del SESSIONS[sid]                 # discard the old (possibly planted) id
+    resp = redirect("/account")
+    resp.set_cookie("session_id", new_sid, httponly=True, samesite="Lax")
+    return resp
```

### Notas obrigatórias no `DIFF.md`

1. **A lição-coração (o núcleo).** Regenerar o `session_id` quando o nível de privilégio muda (anônimo → autenticado). O id pré-autenticação **não pode sobreviver** à autenticação. As duas versões autenticam igual (`sess["authenticated"] = True`); o fix **acrescenta** a rotação do id. *"Authenticate is the same; the fix adds giving the session a fresh id and killing the old one."*
2. **FIXATION vs HIJACKING (cravar — a distinção que separa quem entende).** Hijacking **rouba** um id **já autenticado** (depois do login); fixation **planta** um id **antes** do login e deixa a vítima autenticá-lo. Direção (dar vs subtrair) e timing (antes vs depois). O fix (regeneração) mata **fixation** especificamente: mesmo que o atacante tenha o id pré-login, ele morre no instante do login.
3. **POR QUE sessão server-side manual, e não `flask.session` (obrigatório — SAÍDA B).** O `flask.session` é um cookie assinado client-side: não há id server-side pra fixar, e ele **regenera por design** (o cookie pós-login codifica o user autenticado, re-assinado, e difere do pré-login). Um átomo sobre `flask.session` **não** seria vulnerável — mesma armadilha do PyJWT no 14. Session fixation vive em **sessões server-side com id opaco no cookie** (PHPSESSID/JSESSIONID), que é o que este átomo modela. **Mesmo movimento honesto do 14:** "a lib/mecanismo padrão mitiga; o bug vive em quem faz X de outro jeito".
4. **Flags de cookie NÃO consertam fixation (obrigatório — o mal-entendido vizinho clássico).** `HttpOnly`/`Secure`/`SameSite` ajudam contra **roubo** de cookie (hijacking) — o atacante **planta**, não **rouba**; ele **não precisa ler** o cookie da vítima. A vulnerable **já seta** `HttpOnly`+`SameSite` e **continua explorável**. O fix é **REGENERAR o id**, não blindar o cookie. (Senão o aluno "conserta" com HttpOnly e acha que resolveu.) `Secure` fica de fora só porque o lab é HTTP local — ortogonal à fixation.
5. **O id é FORTE nas duas versões — o bug não é id adivinhável.** `secrets.token_urlsafe(32)` na vulnerable **e** na fixed; a força do id é idêntica. Se o id fosse fraco, seria **outra** vuln (id previsível). A vuln aqui é a **NÃO-REGENERAÇÃO**; regeneração — não imprevisibilidade — é o fix.
6. **Nuance de migração (mencionável).** O fix rebind**a** o objeto de sessão num id novo e descarta o antigo. Aqui não há estado pré-login digno de preservar além do que acabamos de setar; numa app real você copiaria estado benigno pré-login (carrinho, locale) pro id novo — **nunca o id em si**.

---

## A encenação dos dois papéis (o aluno faz atacante E vítima) + a cadeia do ataque

Diferente dos outros átomos (o atacante agia sozinho, com a própria identidade), session fixation tem **DOIS ATORES em DOIS MOMENTOS**. Não há vítima real no lab — **o aluno joga os dois papéis**, e o WALKTHROUGH **deixa isso EXPLÍCITO** (rotular cada beat "COMO ATACANTE" / "COMO VÍTIMA"). A cadeia (validar rodando na Fase 2):

1. **COMO ATACANTE (parte 1) — obter um `session_id`.** `GET /` **sem cookie** → o servidor emite `SID_A` (`Set-Cookie: session_id=SID_A`) e cria `SESSIONS[SID_A] = {anônimo}`. Esse é o id que o atacante **conhece** e **plantaria** (no mundo real, via link/URL/XSS; no lab, o aluno **anota** o `SID_A`). Recon **honesto** — pegar um id anônimo é permitido.
2. **COMO VÍTIMA — autenticar aquele id.** Com `Cookie: session_id=SID_A`, `POST /login` com `user=alice` + a senha correta → `302 → /account`, sessão **agora AUTENTICADA**. **Prova-chave:** o `session_id` continua `SID_A` (na vulnerable). A vítima logou com **as credenciais dela**, ato **100% legítimo**.
3. **COMO ATACANTE (parte 2) — entrar na sessão autenticada.** Num request **separado**, `GET /account` com `Cookie: session_id=SID_A` → **`200`**, a conta da alice. O atacante **entrou na conta autenticada** sem **nunca** ter sabido a senha.

**PROVA-CHAVE (cravar, mostrar explicitamente):** na vulnerable, o `session_id` **antes** (`SID_A`, pós-`GET /` anônimo) e **depois** do login (`SID_A`, pós-`POST /login`) é o **MESMO** — por isso o `SID_A` que o atacante tem funciona no passo 3. Na fixed, o id **muda** no login (`SID_A` → `SID_B`), então o `SID_A` do atacante fica **inútil** (foi descartado).

---

## A trilha — Burp principal + browser secundária (trilha dupla, `CLAUDE.md` §3.3)

Este átomo **volta ao molde HTML de trilha dupla** (a trilogia JWT API-only o deixou de lado). O Burp é a trilha **principal** porque a prova cirúrgica exige **controle explícito do cookie por request** — e é isso que encena os dois papéis num id só.

- **Trilha principal — Burp (Repeater).** Cada request é um bloco colável. O aluno controla o header `Cookie: session_id=...` explicitamente em cada request, o que **é** o que permite jogar atacante e vítima com o **mesmo** id: `GET /` (pegar `SID_A`), `POST /login` (autenticar `SID_A` como a vítima), `GET /account` (entrar como atacante com `SID_A`). É a parte que ensina a profissão — controle cru do cookie e do fluxo.
- **Trilha secundária — browser (opcional, baixa fricção).** Mostra a **prova visual** num relance: abrir `/` (anônimo, id `SID_A` na tela), logar pelo form (vítima), e **ver o `session_id` continuar `SID_A`** na `/account` (vulnerable) — ou **mudar** (fixed). O "atacante entrando na sessão" é mais limpo no Burp (o cookie jar de **um** browser não segura os dois papéis com o mesmo id simultaneamente); pra encená-lo no browser, o aluno setaria o cookie `session_id=SID_A` num private window via **DevTools → Application → Cookies** e visitaria `/account`. Espelha o molde do `idor-numeric-id` (browser pra o visual fácil; Burp pra o controle cirúrgico de header/cookie).

**Sem JS, sem execução client-side** — a prova NÃO exige JavaScript rodando (diferente de XSS): a "prova" é o **status/redirect e o id no cookie**, que o Burp lê perfeitamente. Logo o Burp é primário sem a exceção do §3.3 (não é átomo client-side).

---

## Walkthrough — estrutura e beats

Trilha principal **Burp**, secundária **browser**. Ids são placeholders da sessão real capturada na Fase 2. Estrutura de beats (molde do `idor-numeric-id`, com a encenação de dois papéis explícita):

> **Abertura — plantar a lição.** Tease: *você vai entrar na conta autenticada da alice sem nunca saber a senha dela. Não vai roubar o cookie dela (isso seria hijacking), não vai forjar token nenhum (isso era a trilogia JWT), não vai adivinhar o id (ele é forte). Você vai FORNECER à vítima um `session_id` que você já conhece, deixar ela logar normalmente com a senha dela — e, porque o servidor não troca o id no login, aquele id que você tem agora está autenticado como ela.*

1. **Context.** App web com login: `GET /` (pega uma sessão, mostra anônimo/logado + form), `POST /login` (autentica), `GET /account` (área protegida). Isto é **A07 — session fixation**. **Dois atores, dois momentos: você joga atacante E vítima.** Trilha: Burp (principal) + browser (secundária).
2. **Spot the bug.** Mostrar `vulnerable/app.py` — o `POST /login`. O bloco pós-credencial **muta a sessão atual no lugar** e **mantém o mesmo id**. Nenhum id novo quando anônimo → autenticado. Pergunta de auditoria: *"o `session_id` muda quando o nível de privilégio muda?"* → **não**. Esse é o bug. Foreshadow do fix: **regenerar o id no login**.
3. **How sessions work in this lab.** Sessão **server-side manual** (`SESSIONS` dict + cookie `session_id` opaco). Explicar **por que não `flask.session`** (cookie assinado client-side, regenera por design, não há id server-side pra fixar — o átomo modela o padrão PHPSESSID/JSESSIONID onde fixation mora). Nota: apps reais não imprimem o id na tela; ele aparece aqui só pra a comparação ficar visível.
4. **Baseline — a app funcionando.** `GET /` (anônimo, id `SID_A` na tela + `Set-Cookie`), `POST /login` alice (autentica), `GET /account` (a página da alice). Uso normal, legítimo.
5. **The attack (o núcleo — VALIDAR RODANDO).** A cadeia de dois papéis, com beats rotulados:
   - **5a — COMO ATACANTE (parte 1):** `GET /` sem cookie → anotar `SID_A` do `Set-Cookie`. É o id que você plantaria.
   - **5b — COMO VÍTIMA:** com `Cookie: session_id=SID_A`, `POST /login` `user=alice&password=password123` → `302 → /account`. Mostrar que o id **continua `SID_A`** depois do login (a prova). A vítima logou com a senha dela — legítimo.
   - **5c — COMO ATACANTE (parte 2):** request separado, `GET /account` com `Cookie: session_id=SID_A` → **`200`**, conta da alice. Você entrou, sem saber a senha.
   - **Prova-chave:** `SID_A` antes == `SID_A` depois do login.
6. **What the vuln is NOT (passo de contraste — `CLAUDE.md` §5, obrigatório).** Isola a causa e desmonta os mal-entendidos vizinhos. Provar no Repeater:
   - **NÃO é adivinhar o id.** `secrets.token_urlsafe(32)` — imprevisível. Você não adivinhou; o servidor te **entregou** o id (`GET /`), e o bug é ele **sobreviver** ao login. (Preempta a confusão "id fraco".)
   - **NÃO é crackear/saber a senha.** A vítima digitou a **própria** senha correta; você **nunca** submeteu credenciais. O login foi 100% legítimo — todo o seu tráfego foi `GET /` (anônimo) + `GET /account` (com o id plantado).
   - **NÃO é session hijacking (a grande).** Hijacking **rouba** um id **já autenticado** (depois); fixation **planta** um id **antes** e deixa a vítima autenticá-lo. Você **não leu** o cookie autenticado da vítima — você tinha o id **desde antes** dela logar. Direção (dar vs subtrair) e timing (antes vs depois).
   - **NÃO é problema de flag de cookie.** A vulnerable **já tem** `HttpOnly`+`SameSite` — e continua explorável. Flags param **roubo** (hijacking), não fixation (você **planta**, não lê o cookie dela). Apontar as flags na resposta.
   - **O que É (prova cirúrgica):** o `session_id` antes == depois do login (vulnerable). A **única** correção que funciona é **regenerar o id no login** (a fixed: o id muda, o id plantado morre). Não flag, não id mais forte, não senha melhor.
7. **Impact (honesto — sem overclaim).** **Captura de sessão / account takeover:** o atacante entra na conta autenticada da vítima. Ele **nunca soube a senha** — fixou o id antes e a vítima elevou a sessão. **NÃO é RCE.** Sem overclaim.
8. **Why the fix works (porta 8115).** Repetir a cadeia contra o `fixed/`:
   - 5a idêntico (pega `SID_A` anônimo).
   - 5b (vítima loga) → a resposta seta um cookie **NOVO** `SID_B` (regenerado); a sessão autenticada está sob `SID_B`.
   - 5c (atacante replaya `SID_A` em `/account`) → **`redirect → /`** (o `SID_A` foi descartado, nunca virou autenticado). O id plantado está **morto**.
   - Tudo mais idêntico: mesmos endpoints, mesmos templates, mesma geração de id. **A única mudança é a regeneração no login.**
   - **A lição do diff:** autenticar é o mesmo; o fix **acrescenta** dar um id novo à sessão e matar o antigo. (Forward pro `DIFF.md`.)

**Trilha browser (secundária, opcional)** logo após a principal: a prova visual (logar e ver o id ficar igual na vulnerable / mudar na fixed), com o passo "atacante entra" descrito via DevTools cookie edit em private window. **Sem** seção de exercícios/variações (`CLAUDE.md` §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## O container

`Dockerfile` **idêntico** entre vulnerable e fixed, e **com HTML** (`COPY templates`, como o `idor-numeric-id`). Só Flask via pip (sem `apt`, sem chaves, sem banco). Esqueleto (o mesmo dos átomos HTML):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

`docker-compose.yml` (esqueleto de duas services, molde do `idor-numeric-id`, bind **só** `127.0.0.1`):

```yaml
services:
  vulnerable:
    build: ./vulnerable
    ports:
      - "127.0.0.1:8015:5000"
  fixed:
    build: ./fixed
    ports:
      - "127.0.0.1:8115:5000"
```

---

## Bibliotecas — só Flask

- **`Flask==3.0.0`** — a **mesma** dos átomos HTML (`sqli-union-basic`, `idor-numeric-id`, etc.). `os` e `secrets` são **stdlib** (não vão no `requirements`). **Nada** de banco, PyJWT, cryptography, `apt`, ou qualquer outra lib — `CLAUDE.md` §3.6 (só a lib que serve à demonstração/fix; aqui, nenhuma além do Flask).
- **`requirements.txt` (idêntico vulnerable × fixed):**

```
Flask==3.0.0
```

- **Sem pin behavior-critical:** a vuln (não-regenerar o id) é **agnóstica de versão** do Flask — é lógica de aplicação pura. O pin é só reprodutibilidade, coerente com os irmãos.

---

## Renderização / "um átomo = uma vuln"

**TEM HTML** (não API-only), **autoescape do Jinja LIGADO** (default). O `session_id` e o `user` refletidos passam pelo escape (`{{ }}`) — sem `|safe`/`Markup`/`render_template_string` → **sem XSS acidental**. Garantir que a **única** superfície é a não-regeneração do id no login:

- **Senha trivial de propósito** (não é vuln — dummy de lab, `CLAUDE.md` §8.3).
- **Id forte** (`secrets.token_urlsafe`, imprevisível — não empilha "id adivinhável").
- **Flags de cookie idênticas** nas duas versões (não é a lição, não entra no diff).
- **Servidor não-permissivo** (só honra ids que emitiu — não empilha "session adoption").
- **Sem banco, sem dado real**; `/account` só dado fake benigno; **`flask.session` não usado** (sem dependência de `SECRET_KEY`).
- **Erros via `abort()`/`redirect()`** (padrão Flask): status/redirect é o sinal do exploit (`200`/`302`/`401`); corpo do erro é imaterial e **não reflete input** (sem XSS).

---

## Theory primer

`CLAUDE.md` §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página **conceitual** da vuln (a que responde "what is X?"), **não** a página de listagem de labs. **Confirmar a URL por fetch na Fase 2 — não inventar** (se não confirmar, perguntar ao mantenedor, `CLAUDE.md` §5).

- **Preferência:** se houver uma página **específica de session fixation** na Academy, **usá-la**.
- **Candidatos a checar por fetch na Fase 2 (nesta ordem):**
  1. Uma página/seção dedicada de **session fixation** (procurar sob `/web-security/...`; a Academy pode cobri-la dentro de **Authentication** ou de gerenciamento de sessão).
  2. A página conceitual de **Authentication** (`https://portswigger.net/web-security/authentication`) — cobre falhas de sessão/autenticação e é o fallback conceitual coerente com A07.
  - Se a Academy **não** tiver uma página conceitual de session fixation com framing "what is X?", **perguntar ao mantenedor** qual usar (a de Authentication vs uma referência canônica externa, ex. OWASP "Session fixation") — **não** linkar uma página de listagem de labs, e **não** inventar URL.
- **Texto do link:** preservar o nome em **inglês** também no README PT (convenção `CLAUDE.md` §7 — ex. "Session fixation" ou "Authentication", exatamente como a PortSwigger nomear a página).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A07 — Identification and Authentication Failures** (`atoms/A07-auth-failures/`) | ROADMAP lista session-fixation em A07; sub-tópico canônico de gerenciamento de sessão. **Primeiro átomo A07 do repo** (pasta nova). |
| Posição na Fase 3 | **Quinto e último — FECHA a Fase 3** | ROADMAP: 11/12/13/14/**15**; honra a Nota de planning 1 do 14 (o 15 é o phase-closer). |
| Eixo | **NOVO — A07 sessão** (sai de A01/A02) | Primeiro átomo de sessão / de cookies de sessão do repo. |
| Nome / classe | **Session fixation** | O atacante fornece um id antes do login; a vítima o autentica; o servidor não regenera. |
| Lição-coração | **"a sessão autenticada não pode ser identificada por algo que existia antes da autenticação; regenerar o id no login"** + sub-lição "o único ponto de divergência é o instante do login" | O bug é a não-regeneração na mudança de privilégio. |
| Distinção central | **FIXATION ≠ HIJACKING** (dar-antes vs roubar-depois) | O mal-entendido vizinho a isolar (`CLAUDE.md` §5). O atacante nunca lê o cookie autenticado da vítima. |
| Decisão estrutural | **Sessão server-side MANUAL** (`SESSIONS` dict + cookie `session_id` opaco); **NÃO `flask.session`** | `flask.session` resiste a fixation por design (cookie assinado client-side, regenera por natureza) — "Saída B", o mesmo movimento honesto do 14. Fixation mora em PHPSESSID/JSESSIONID. |
| Tipo de átomo | **Com HTML, trilha dupla** (Burp principal + browser secundária) | Vuln de navegador/cookie; a prova visual (id muda ou não no login) pede UI mínima. Volta ao molde do `idor-numeric-id`. |
| Feature | **App web login** (`/`, `/login`, `/account`), sessões em memória | Habitat canônico de session fixation. Sem banco. |
| `POST /login` | senha **trivial** (`alice`/`password123`, compare direto), sem hash/rate-limit | A senha dá realismo à narrativa mas **não** é a lição (`CLAUDE.md` §8.3). |
| O bug | **`/login` autentica a sessão atual mantendo o mesmo `session_id`** | Não emite id novo na mudança de privilégio (anônimo → autenticado). |
| Fix (único eixo) | **Regenerar o `session_id` no login** (novo id + rebind da sessão + `del` do antigo + cookie novo) | O id pré-login não sobrevive à autenticação; o id plantado morre. |
| Diff | **Lógica-diferente** (código adicionado no `/login`) | Tipo dos A01/JWT; **não** valor-diferente (13) nem app-idêntico (par XSS). |
| Mostrar o `session_id` na página | **Sim** (via `{{ sid }}`, escapado) | A prova central (id igual/diferente no login) fica glanceable (`CLAUDE.md` §6). Nota de artificialidade; não é 2ª vuln (o atacante já conhece o id). |
| Flags de cookie | **`HttpOnly`+`SameSite=Lax` nas duas versões; sem `Secure`** | Idênticas → fora do diff; `HttpOnly` presente na vulnerable preempta "consertar com flag"; `Secure` quebraria o lab HTTP local. |
| `/account` não-autenticado | **`redirect("/")`** (`403` alternativa aceitável) | Web-natural (cai no login); no fixed o id antigo foi deletado → redirect. |
| Id de sessão | **`secrets.token_urlsafe(32)` nas DUAS versões** | Imprevisível; a vuln é a NÃO-REGENERAÇÃO, **não** id fraco. Cravar. |
| Servidor permissivo? | **Não** — só honra ids que emitiu | Adotar id arbitrário do cliente seria 2º flavor (session adoption), fora de escopo. |
| Bibliotecas | **Só `Flask==3.0.0`** | `os`/`secrets` stdlib. Sem banco/JWT/crypto. Pin não behavior-critical. |
| Trilha | **Burp (principal) + browser (secundária)** | Controle explícito do cookie por request encena os dois papéis; browser pro visual. Sem JS. |
| Nº de beats | **Context → spot the bug → how sessions work → baseline → attack (2 papéis) → o que a vuln NÃO é → impacto → fix** | Molde do `idor-numeric-id` com a cadeia de dois papéis explícita. |
| Impacto | **Captura de sessão / account takeover.** Não RCE. | Honesto; o atacante nunca soube a senha. |
| Theory primer | **PortSwigger session fixation / Authentication** (confirmar por fetch na Fase 2) | `CLAUDE.md` manda PortSwigger; URL confirmada por fetch, não inventada. |
| Erros | **`abort()`/`redirect()` crus**; status/redirect é o sinal | Consistente com os irmãos. Corpo não reflete input (sem XSS). |
| `app.py` vulnerable × fixed | **Diferem só no bloco pós-credencial do `/login`** | Resto (helper, `/`, `/account`, store, templates) byte-idêntico. Diff lógica-diferente. |
| Dockerfile / compose | Esqueleto do `idor-numeric-id` (**com** `COPY templates`); portas 8015/8115 | Idêntico entre versões; bind só `127.0.0.1`. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–5 são os centrais; 6–10 são higiene técnica. Todos são validação **na geração** (`CLAUDE.md` §11), não decisões pendentes.

1. **`GET /` sem cookie** → emite um `session_id` (`Set-Cookie`), cria `SESSIONS[id]` anônima. Com cookie existente **conhecido** → reusa. Com cookie **desconhecido** → emite um id novo (servidor não-permissivo). Confirmar que o id é `secrets.token_urlsafe` (imprevisível).
2. **`POST /login` alice + senha correta** → autentica. **VULNERABLE:** o `session_id` do cookie **DEPOIS** do login é **IDÊNTICO** ao de antes (capturar os dois — home anônima e `/account` pós-login — e provar igualdade). **FIXED:** o `session_id` **MUDA** no login (capturar os dois, provar diferença); o id antigo é **descartado** (`SESSIONS` não tem mais o `old_sid`).
3. **O ATAQUE (item central — VALIDAR RODANDO):** (a) obter um `session_id` anônimo `SID_A` (atacante); (b) com `SID_A` no cookie, `POST /login` como alice (vítima); (c) `GET /account` com o **MESMO** `SID_A` → no **VULNERABLE**, entra na conta da alice (`200`, dado autenticado). **CAPTURAR** a cadeia real (os três requests/responses). No **FIXED**: o `SID_A` pré-login, após o login da vítima, **NÃO** dá acesso a `/account` (a sessão autenticada tem um id novo `SID_B` que o atacante não conhece; o `SID_A` foi deletado) → `redirect → /`. **Se a cadeia não reproduzir, PARAR e avisar o mantenedor — NÃO inventar** os ids/responses.
4. **Senha errada** → não autentica (`401`); a sessão continua anônima. **`/account` sem sessão autenticada** → `redirect → /` (ou `403` se a Fase 2 optar).
5. **fixation ≠ hijacking demonstrável:** o atacante **nunca leu** o cookie autenticado da vítima — ele teve o id **ANTES** do login. (Conceitual, provado pela cadeia do item 3: todo o tráfego do atacante é `GET /` anônimo + `GET /account` com o id plantado; ele nunca submeteu credenciais nem leu resposta autenticada da vítima antes de plantar.)
6. **`app.py` vulnerable × fixed:** confirmar por `diff` que a mudança é **só** o bloco pós-credencial do `/login` (mantém id vs regenera+rebind+del+cookie novo), e que o resto (`current_session`, `/`, `/account`, `SESSIONS`, `CREDENTIALS`, rodapé) e **os dois templates** são **byte-idênticos**. Diff **lógica-diferente**.
7. **Uma vuln só:** autoescape do Jinja ligado (`session_id`/`user` refletidos são escapados — sem `|safe`); senha trivial **intencional** (não é vuln); `secrets.token_urlsafe` (id forte — não empilha "id adivinhável"); flags de cookie idênticas nas duas versões (não é a lição); servidor não-permissivo (não empilha "session adoption"); `flask.session` **não** usado; `/account` só dado fake benigno; sem XSS.
8. **HTML mínimo:** `templates/index.html` e `templates/account.html` ≤40 linhas cada, banner de aviso, dica de Burp, sem frameworks, sem JS. Templates idênticos entre vulnerable e fixed. Trilha dupla no WALKTHROUGH (Burp principal + browser secundária).
9. **Theory primer por fetch:** confirmar a URL da PortSwigger (session fixation / Authentication) — página conceitual "what is X?", não listagem de labs. Se não houver página conceitual de session fixation, **perguntar ao mantenedor**. Não inventar.
10. **Higiene:** portas `8015`/`8115` bind **só** `127.0.0.1` (compose). `Flask==3.0.0` instala limpo no `python:3.11-slim`. Cookie com `path` sensato (default `/` serve), `HttpOnly`+`SameSite=Lax`, **sem** `Secure` (lab HTTP). `./atom up session-fixation` sobe sem erro. Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox (memória `validating-atoms-via-docker-exec`) — a cadeia de ataque roda com controle explícito do header `Cookie` (Burp/`curl`/`http.client`), porque o cookie jar de **um** browser não segura os dois papéis com o mesmo id.

**Bloqueante remanescente:** nenhum de decisão. **Pendências de Fase 2 (não bloqueantes agora):** validar a cadeia de ataque rodando (item 3); confirmar a URL do primer por fetch (item 9); gerar os arquivos e rodar o smoke test (`./atom up`).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo **fecha a Fase 3** e **abre o eixo A07/sessão**. Cada beat deve poder ser lido com o `idor-numeric-id` aberto ao lado (molde de HTML/lógica/trilha dupla/"o que a vuln NÃO é") e, de leve, com os JWT (contraste conceitual: eles forjam a prova de identidade; fixation captura a sessão sem forjar). **Abrir e fechar** na lição-coração: a sessão autenticada não pode carregar um id pré-autenticação → regenerar no login. E na distinção **fixation ≠ hijacking** (dar-antes vs roubar-depois).
- **Leitura obrigatória antes de gerar (`CLAUDE.md` §10.5):** `sqli-union-basic` (01, referência canônica — HTML/Jinja2/Dockerfile/compose/tom); `idor-numeric-id` (03, **o molde mais próximo** — HTML de lógica, trilha dupla, passo "o que a vuln NÃO é", README com "Stack note — no database" e "Authentication, simulated"); de leve `idor-uuid-guessable` (11) e `bola-rest` (12) pelo eixo access-control; e a trilogia JWT (05/13/14) **só pelo contraste conceitual** (não copiar o molde API-only deles). Ler também esta spec.
- **SAÍDA B é o coração estrutural:** o vulnerable usa **sessão server-side manual** (não `flask.session`); explicar **por quê** (o `flask.session` resiste à fixation por design; fixation mora em sessões server-side com id no cookie — PHPSESSID/JSESSIONID). Sem isso o aluno acha que o dev reinventou a roda à toa. Cravar no DIFF e no WALKTHROUGH — é o mesmo movimento honesto do 14.
- **A prova é o id (não) mudar no login (risco #3).** Capturar a cadeia real dos três requests e mostrar `SID_A` antes == depois (vulnerable) / `SID_A` → `SID_B` (fixed). **Se não bater rodando, PARAR e avisar — NÃO inventar** ids/responses.
- **Uma vuln só:** id forte (`secrets.token_urlsafe`) nas duas versões; senha trivial intencional; autoescape ligado; flags idênticas; servidor não-permissivo; sem `flask.session`; sem XSS. A **única** superfície é a não-regeneração no login.
- **A encenação de dois papéis é explícita no WALKTHROUGH:** rotular cada beat "COMO ATACANTE" / "COMO VÍTIMA". O aluno joga os dois. A prova-chave é o id igual antes/depois do login (vulnerable).
- **Impacto honesto:** **captura de sessão / account takeover**; o atacante **nunca soube a senha**. **NÃO** RCE. Sem overclaim.
- **Política de referência cross-átomo:** OK citar **de leve** os átomos **publicados** (JWT 05/13/14 pelo contraste "forjar a identidade vs capturar a sessão"; A01 03/11/12 pelo eixo access-control). **PROIBIDO** referenciar/foreshadowar **qualquer** átomo não publicado ou fase futura. **Crítico:** o 15 **FECHA a Fase 3** — **ZERO foreshadow**: NÃO anunciar a Fase 4, NÃO antecipar átomos futuros (inclui o `weak-password-reset`/37, também A07 mas não-publicado), NÃO prometer nada além do 15, NÃO anunciar a release `v0.3.0` no conteúdo do átomo.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF). H1 idêntico em EN e PT (`session-fixation — Session fixation`, texto exato / qualificador opcional confirmável na Fase 2). Termos técnicos (session, session id, session fixation, session hijacking, cookie, `HttpOnly`/`SameSite`/`Secure`, login, authenticate, anonymous, regenerate, PHPSESSID/JSESSIONID, account takeover, plant/forge) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger (session fixation / Authentication), nome da página preservado em inglês no PT. **Confirmar a URL por fetch na Fase 2** — se não houver página conceitual de session fixation, **perguntar ao mantenedor**.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 15: `session-fixation` — session id not regenerated at login (A07 Identification and Authentication Failures). `` (padrão das linhas dos átomos 06–14). *(A entrada de release `v0.3.0` no CHANGELOG é trabalho de release do mantenedor — Nota de planning 2 — não do átomo.)*
- **ROADMAP.md:** marcar o átomo 15 como `[x]` **só na geração+validação** (proposta ao mantenedor, `CLAUDE.md` §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (`CLAUDE.md` §11): itens 1–10; reproduzir baseline → cadeia de ataque (atacante pega `SID_A` → vítima loga → atacante entra em `/account`, `200`) → contraste (id igual antes/depois) → fixed (id regenera, `SID_A` morre → redirect). Validar via `docker exec` + `python http.client`/`curl` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8015` (vulnerable), `127.0.0.1:8115` (fixed). Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre a URL do primer (ou se a Academy não tiver página de session fixation), a forma exata do H1, ou se a cadeia de ataque não reproduzir rodando, **perguntar/ajustar e documentar** antes de inventar (`CLAUDE.md`).

---

## Proposta de memória (opcional — decisão do mantenedor, `CLAUDE.md` "Memória de projeto")

Não gravei nada (a regra: o Claude Code propõe, o mantenedor decide). **Candidato único, se você quiser um pointer de recall rápido independente do spec/DIFF:**

- **`session-fixation-not-flask-session`** — *"O átomo session-fixation (15) usa uma sessão server-side manual (`SESSIONS` dict + cookie `session_id` opaco), NÃO `flask.session` — a nativa resiste a fixation por design (cookie assinado client-side, regenera por natureza, sem id server-side pra fixar). Mesma armadilha estrutural do PyJWT no atom 14 ('a ferramenta padrão mitiga; o bug vive em quem faz X à mão'). Session fixation mora em sessões server-side com id no cookie (PHPSESSID/JSESSIONID)."* — tipo `project`/`reference`.

**Ressalva:** esse fato já vai ficar **registrado no spec commitado e no DIFF** do átomo (a regra de memória desaconselha duplicar o que o repo já grava). Proponho **não** gravar por ora, salvo se você quiser o recall rápido fora do spec. Sua decisão.
