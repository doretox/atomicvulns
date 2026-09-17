# Spec — Átomo 12: `bola-rest`

> Documento de especificação para o Claude Code implementar o décimo-segundo átomo do projeto `atomicvulns` (Fase 3, **segundo átomo da fase** — "Access Control & Autenticação", milestone `v0.3.0`; **não** fecha a fase). Este átomo é o **BOLA (Broken Object Level Authorization)** — a variante moderna, em API REST, do IDOR, e o **#1 do OWASP API Security Top 10 (API1:2023)**. Leia junto com `CLAUDE.md` (Seções 3.3, 3.4, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — três átomos de referência já publicados em `main`:
> 1. **`atoms/A01-broken-access-control/idor-numeric-id/` (03) — o avô do arco.** Primeira formulação da lição "o bug é a checagem AUSENTE, não input que virou código". Reusar o passo de contraste "o que a vuln NÃO é", o vocabulário de broken access control, e o framing "IDOR não greppa por string perigosa; audita-se lendo o endpoint e perguntando 'cadê o check de dono?'". O exploit "`/notes/1` → `/notes/2`" (incrementar um id) é o ancestral direto do movimento deste átomo.
> 2. **`atoms/A01-broken-access-control/idor-uuid-guessable/` (11) — o irmão imediato.** Provou que **trocar o formato do id não é controle de acesso** ("theater"): mesmo um UUID que *parece* seguro vaza sem ownership check, e aquele v1 nem era imprevisível (reconstruível). **Este átomo é o próximo degrau da mesma escada:** o 11 disse "esconder/embaralhar o id não protege"; o 12 leva ao limite — **na API o id é PÚBLICO por design** (está no path, é sequencial, o cliente legítimo já o manuseia), não há nada pra adivinhar nem reconstruir, e por isso a autorização por objeto é a **única** linha de defesa — e está ausente. Reusar a tabela de contraste A01, o frame "reshaping the id is a losing game", e a regra de bolso 403-vs-404 do DIFF do 11 (aqui ela **vira a lição**).
> 3. **`atoms/A01-broken-access-control/path-traversal-basic/` (10) — o outro A01 publicado.** Referência **leve**, só pro contraste de status code (o 10 usa `404` por recurso **fora do domínio** da app; este usa `404` por outro motivo — evitar oráculo de enumeração sobre ids sequenciais).
>
> Esta spec captura apenas as decisões *específicas* deste átomo. Onde os irmãos A01 já resolveram a forma (dados em memória sem banco, passo de contraste obrigatório, forma do DIFF/WALKTHROUGH/README, `app.py` diferente entre vulnerable/fixed), a instrução é **reusar a forma**, não reinventar. **Diferença estrutural central:** este é o **primeiro átomo API-only do repo** — sem HTML, sem templates, sem browser (CLAUDE.md §3.3 lista "BOLA em REST" como categoria naturalmente API-only). Ver "Feature simulada" e "Walkthrough".
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, ou qualquer arquivo do átomo — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Identidade

- **ID:** `bola-rest`
- **Categoria OWASP (pasta / Web Top 10 2021):** A01 — Broken Access Control (mesma convenção de diretório do `idor-numeric-id`, `idor-uuid-guessable` e `path-traversal-basic`).
- **Também é (e principalmente):** **BOLA — Broken Object Level Authorization**, o **API1:2023**, item **#1** do **OWASP API Security Top 10 (2023)**. BOLA é o nome que a comunidade de API security dá ao IDOR quando ele mora num endpoint REST: mesma causa raiz (checagem de autorização por objeto ausente), mesmo fix (cruzar o dono do objeto com o chamador).
- **Pasta:** `atoms/A01-broken-access-control/bola-rest/`
- **Número sequencial:** 12
- **Porta vulnerable:** `127.0.0.1:8012`
- **Porta fixed:** `127.0.0.1:8112`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–11.
- **Fase / milestone:** Fase 3, `v0.3.0` (segundo átomo da fase; **não** fecha a fase — versionamento/release fica pra depois, fora desta spec).
- **Branch de trabalho:** `atom/bola-rest`. **Nota de convenção:** o histórico real usa `atom/<id>` (confirmado nos head refs dos PRs #14–#20: `atom/path-traversal-basic`, `atom/idor-uuid-guessable`, etc.), alinhado ao `CLAUDE.md` §6 — **não** a forma `atom-12-...`. Branch já criada nesta fase de planning.
- **Theory primer (registrar candidatos, NÃO buscar/inserir agora — confirmar por fetch na Fase 2):** ver seção "Theory primer" abaixo. Candidato do bloco: a mesma página de IDOR do PortSwigger usada por 03/11 (BOLA é IDOR em API); referência suplementar: OWASP API Security Top 10 API1:2023.
- **H1 dos READMEs (idêntico em EN e PT):** `# bola-rest — Broken Object Level Authorization (BOLA)` (segue o padrão do 03/11 `id — Nome canônico da vuln (qualificador)`; o qualificador de forma dos irmãos vira aqui o acrônimo `(BOLA)`, o nome que circula na comunidade de API).

---

## Classe de vulnerabilidade

**BOLA (Broken Object Level Authorization) / IDOR em API REST.** Uma API serve um objeto privado (um pedido) por `GET /api/orders/<id>`, valida o token do chamador (**autenticação** funciona), e ainda assim devolve o objeto **sem cruzar o dono do objeto (`order["owner"]`) com o usuário do token**. IDOR e BOLA são a mesma classe: "IDOR" é o vocabulário da web (PortSwigger, OWASP Web Top 10 A01), "BOLA" é o vocabulário de API (OWASP API Security Top 10 API1:2023). Mesma causa raiz que o `idor-numeric-id` (03) e o `idor-uuid-guessable` (11): **ownership check ausente** — aqui chamado, no dialeto de API, de **object-level authorization** ausente.

### A lição-coração: duas facetas

> **"Estar autenticado não é estar autorizado."**
> Um token válido prova **quem você é**; não diz nada sobre **se este objeto é seu.**

**Faceta 1 (o cerne) — authenticated ≠ authorized.** O token prova identidade (**authentication**); não prova permissão sobre **este** objeto (**object-level authorization**). O BOLA é exatamente esse gap: o endpoint valida o token — você está autenticado **de verdade**, como **você mesmo**, com um token **legítimo emitido pelo servidor** — e mesmo assim serve o objeto de outro usuário, porque **nunca cruza o dono do objeto com o dono do token**. A armadilha, em que **dev e atacante caem**: *"o request é autenticado, logo o acesso é legítimo."* É falso. Autenticação diz "você é a mallory"; autorização por objeto diz "este pedido é da mallory?" — e o endpoint vulnerável só faz a primeira pergunta.

**Faceta 2 (o contexto que distingue do 11) — na API o id é público por design.** Numa API REST o id do objeto é **cidadão de primeira classe**: está no **path**, é **sequencial**, é **documentado**, e o **cliente legítimo já os manuseia** (a própria `GET /api/orders` te devolve os seus). O atacante **NÃO adivinha nem reconstrói nada** — contraste **direto** com o 11, onde o id *parecia* opaco e era preciso reconstruí-lo a partir de um timestamp. Aqui os ids **são a interface**. Por isso a autorização por objeto é a **ÚNICA** linha de defesa que poderia existir — e ela está **ausente**. Onde o 11 ensinou "obscurecer o id não protege", o 12 mostra o mundo em que **não há sequer obscuridade a perder**: o id é aberto, e ainda assim isso nunca foi o problema.

As duas facetas se somam numa causa única: **não há check de autorização por objeto.** A Faceta 1 é a lição principal (o passo de contraste obrigatório carrega ela); a Faceta 2 é o enquadramento que ancora o átomo no mundo de API e o diferencia do irmão 11.

### O que este átomo acrescenta ao arco (evolução sobre 03/11)

O 03 e o 11 fingiam identidade com um header **self-asserted** (`X-User-ID`) — não havia autenticação de verdade; você *dizia* quem era. O 12 **sobe um degrau de realismo:** há **autenticação genuína** — um token opaco, emitido pelo servidor, validado em toda request (Bearer ruim → `401`). E é justamente **por existir autenticação real** que a distinção "authenticated ≠ authorized" fica nítida: nos irmãos não havia auth pra confundir com authz; aqui há, e o átomo prova que **mesmo com autenticação correta, a autorização por objeto pode faltar**. Diferença fina, mas central, no passo de contraste: no 03 o endpoint **ignorava** a identidade por completo; aqui o endpoint **lê** o token pra autenticar, mas **descarta** a identidade na hora de autorizar o objeto — a forma mais comum e realista do bug.

### Por que A01 (Broken Access Control) — a moldura é a mesma dos irmãos

O bug **não é** "input virou código" (injection). É **"um request legítimo alcançou um objeto fora do seu escopo autorizado"** — o chamador pediu um pedido que não é dele e a API entregou. Isso é controle de acesso a objeto: **A01** no Web Top 10, **API1** no API Top 10. Por ser vuln de **lógica/autorização** (e não de payload), o passo de contraste obrigatório "o que a vuln NÃO é" (CLAUDE.md §5) é **mandatório** — e aqui carrega **peso duplo**, porque desmonta DOIS mal-entendidos vizinhos: *"isso é falha de autenticação"* (Faceta 1) e *"isso é porque o id era adivinhável"* (Faceta 2).

### Contraste com os irmãos A01 (tabela — vai no fechamento do WALKTHROUGH; a prosa no DIFF)

| Átomo (A01) | O objeto é alcançado por… | O id é… | O que falta no código |
|---|---|---|---|
| `idor-numeric-id` (03) | trocar um id (`/notes/1` → `/notes/2`) | inteiro sequencial | ownership check (a nota é sua?) |
| `idor-uuid-guessable` (11) | **reconstruir** e usar o UUID | UUIDv1 reconstruível (*parece* opaco) | ownership check (o recibo é seu?) |
| `bola-rest` (12) | **ler o próprio id na API e pedir o vizinho** (`GET /api/orders/41`) | **inteiro sequencial, público por design de API** | **object-level authorization** (o pedido é seu?) — **o mesmo check** |
| `path-traversal-basic` (10) | navegar o filesystem (`notes.txt` → `../../etc/passwd`) | caminho de arquivo | confinement check (o path caiu na pasta?) |

Os três de IDOR/BOLA (03, 11, 12) dividem **exatamente** a mesma causa e o mesmo fix (checar o dono contra o chamador) — diferem só no **formato/origem do id** e no **quanto de autenticação existe em volta**. O arco: **03** (id sequencial, "é só contar") → **11** (UUID, "*parece* imprevisível, mas nem é") → **12** (API, "o id é público por design; não há o que esconder, então a autorização é tudo"). Cada degrau remove uma ilusão de que a *forma* do id é um controle. O 10 divide a família A01 mas por outro eixo (confinamento de caminho, não ownership).

**Frame quotável (cravar no fechamento do WALKTHROUGH e no DIFF):** *No `idor-uuid-guessable` provamos que embaralhar o id era "theater" — obscuridade, não autorização. Aqui não sobra nem obscuridade pra perder: numa API o id é público por contrato — a própria listagem te entrega o seu, e o vizinho é o próximo inteiro. O token prova que você é você; ele não diz de quem é este pedido. A autorização por objeto era a única linha de defesa, e ela não existe.*

---

## Por que token opaco, e não JWT (decisão técnica — registrar)

O token é uma **string opaca (valor aleatório)**, **não** um JWT. O servidor guarda um **mapa `token → usuário` em memória** e resolve por lookup. Decisão **deliberada**, e por quê:

- **(a) Um JWT puxaria o foco pro lugar errado.** Com um JWT na mesa, o instinto do aluno é **atacar o token** — decodificar, `alg:none`, trocar o `sub`, forjar assinatura. Isso **NÃO é a lição deste átomo**. O token do 12 é **sólido, legítimo, e o ataque NÃO o toca**. A falha mora inteiramente no endpoint que serve o objeto sem checar dono.
- **(b) Um JWT funcional aqui faria foreshadow de arco não-publicado.** Manipulação de JWT é objeto de átomos futuros ainda não em `main`. Introduzir um JWT explorável violaria a política de não antecipar átomos não-publicados (CLAUDE.md §5, "Referências cross-átomo"). **Proibido.**
- **(c) Opaco é igualmente real em produção.** OAuth2 opaque access tokens e sessões server-side são exatamente isto: um valor aleatório que o servidor resolve pra uma identidade. Não há perda de realismo — há **remoção de distração**.

**CRAVAR (no WALKTHROUGH e no DIFF):** o ataque deixa o token **INTACTO e VÁLIDO**; ele nunca é decodificado, adulterado, nem forjado. O alvo é o **endpoint que serve o objeto sem checar dono**. Ao falar de autenticação, manter sempre o frame *"o token é válido e o ataque não o toca"* — **sem** mencionar técnicas de ataque a token (isso é arco futuro).

---

## Feature simulada — API REST de pedidos (API-only, sem HTML)

**Pedidos (orders).** Uma API REST de e-commerce: cada pedido tem `id`, `owner`, `item` e `amount`. O cliente autentica com um token e lê seus pedidos. Do ponto de vista do dev, "o cliente só vê os pedidos dele" — mas o endpoint de detalhe esqueceu de garantir isso.

**Tipo de átomo:** `[ ] com HTML` / `[x] API-only` — **travado com o mantenedor.** CLAUDE.md §3.3 lista **"BOLA em REST"** explicitamente como categoria **naturalmente API-only**: sem `templates/`, sem browser; a interação é 100% via Burp/curl. Consequências:
- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas em `application/json` via `jsonify`.
- Requests com corpo JSON (no `POST /login`); auth via header `Authorization: Bearer <token>`.
- **Sem trilha browser.** CLAUDE.md §3.3: *"Em átomos API-only, a trilha secundária não existe — só a principal, via Burp/curl."* Ver "Walkthrough".

**Primeiro átomo API-only do repo.** Todos os 11 átomos publicados têm HTML (inclusive o 05/`jwt-none-alg`, que CLAUDE.md cita como categoria típica de API mas foi feito com HTML). **Não há, portanto, um átomo de referência in-repo pro formato API-only** — o formato segue CLAUDE.md §3.3 e adapta a estrutura de WALKTHROUGH dos irmãos 03/11 **removendo a trilha browser** e trocando UI-baseline por request-baseline no Burp. Registrar isso pro Claude Code da Fase 2 não procurar um espelho que não existe.

---

## Modelo de identidade e dados — sem banco

**Sem banco** (como o 03 e o 11; CLAUDE.md §3.4 — o storage segue a superfície do bug: BOLA não depende da camada de storage, é uma checagem de autorização ausente acima de qualquer store). Dados em estruturas Python em memória. Nota "Stack note — no database" no README, espelhando 03/11.

**Dois usuários, papéis explícitos (reuso da dupla do 11):**

- **`mallory`** — a **atacante** (você). Faz login como si mesma e obtém **o próprio token**.
- **`alice`** — a **vítima**. Tem pedido seedado; é o alvo que a `mallory` não deveria conseguir ler.

**Autenticação simulada — token opaco, sem senha.** `POST /login` recebe `{"user": "<nome>"}` e devolve `{"token": "<opaco>"}`. **Sem senha** — auth real (senha, hashing) está **fora de escopo**, exatamente como o `X-User-ID` self-asserted dos irmãos 03/11 era o atalho "auth fora de escopo". O login existe **só pra provar que o token é legítimo, emitido pelo servidor, e mapeado a um usuário real** — é o que dá a `mallory` uma sessão **genuína e própria**. (Consequência do atalho: como não há senha, tecnicamente qualquer um poderia pedir o token de qualquer usuário no `/login` — isso é a mesma simplificação de "identidade auto-declarada" dos irmãos, **não** é a vuln sob estudo. O walkthrough faz login como `mallory` e ataca com o token **dela**; o único bug é a **object-level authorization ausente** no `GET /api/orders/<id>`, **não** o login sem senha.)

**Seed de pedidos — ids sequenciais com a vítima "no meio" (torna a inferência óbvia):**

```python
# Order ids are a single GLOBAL sequence, so adjacent ids belong to different
# users. mallory owns 40 and 42; alice owns 41 — the gap mallory sees in her own list.
ORDERS = {
    40: {"id": 40, "owner": "mallory", "item": "Wireless mouse", "amount": "$29.90"},
    41: {"id": 41, "owner": "alice",   "item": "Standing desk",  "amount": "$589.00"},
    42: {"id": 42, "owner": "mallory", "item": "USB-C cable",    "amount": "$12.99"},
}
```

- **Por que a `mallory` dona de 40 **e** 42, e a `alice` de 41 (o "gap"):** a `GET /api/orders` da `mallory` devolve `[40, 42]` — o **buraco em 41 salta aos olhos** dentro da própria lista dela. Não há adivinhação nem direção a escolher: o id da vítima está **literalmente entre dois que a `mallory` possui**. Modela um **contador global de pedidos** que interliga usuários (traço real de API), reforçando a Faceta 2 (ids sequenciais, públicos por design). *Alternativa considerada e preterida:* uma ordem cada, adjacente (`mallory=40`, `alice=41`), ecoando o "`/notes/1`→`/notes/2`" do 03 — mais minimalista, mas a inferência "existe um 41" é menos gritante que um buraco visível. O gap venceu por ser **mais óbvio** (CLAUDE.md §2, didático > minimalista quando o custo é uma linha de seed).
- **Dado fake óbvio** (CLAUDE.md §8.3): nomes de produto + preço, **sem PII, sem cartão real, sem segredo**. Quatro campos só: `id`, `owner`, `item`, `amount`. (Impacto honesto na leitura cross-user: "o que a `alice` comprou e por quanto" — dado de compra privado, sem precisar inventar PII.)
- **Estado mutável de processo único** (o `TOKENS` cresce a cada login; restart zera). Aceitável no lab; notar, como o 11 notou pro seu store.

---

## Rotas

Imports necessários: `import os`, `import secrets`, `from flask import Flask, request, jsonify, abort`. (**Sem** `sqlite3`, **sem** `subprocess`, **sem** `render_template` — não há templates. `secrets` é stdlib, pra o token opaco. `abort` e `jsonify` usados nas duas versões.)

Constantes e helpers no topo do `app.py` (**idênticos** entre vulnerable e fixed):

```python
USERS = {"mallory", "alice"}   # mallory = attacker (you); alice = victim
TOKENS = {}                    # opaque token -> username (in-memory; NOT a JWT)

def _issue_token(user):
    token = secrets.token_urlsafe(24)   # opaque random value; a server-side session token
    TOKENS[token] = user
    return token

def _authenticate():
    # Authentication only: resolve the Bearer token to a user, or 401.
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    user = TOKENS.get(token)
    if user is None:
        abort(401)
    return user
```

### `POST /login` — obter o próprio token (idêntico nas duas versões)

Recebe `{"user": "<nome>"}`, valida contra `USERS` e devolve um token opaco recém-emitido, mapeado ao usuário. Sem senha (atalho de auth fora de escopo).

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user")
    if user not in USERS:
        abort(400)                       # operational hygiene; orthogonal to the bug
    return jsonify({"token": _issue_token(user)})
```

- Token **fresco a cada login** (valor aleatório de `secrets`). Logins repetidos geram tokens distintos, todos válidos — walkthrough usa **placeholders** (`<mallory-token>`), como o 11 usou pros UUIDs que variam por boot. `mallory` e `alice` recebem tokens **distintos**, cada um resolvendo ao seu dono (risco #1).
- Usuário desconhecido/ausente → `400` (higiene, ortogonal ao bug; não é a lição).

### `GET /api/orders` — listar os pedidos do próprio chamador (idêntico nas duas versões — o baseline **correto**)

Autentica e devolve **só** os pedidos do chamador. **Corretamente escopado nas duas versões** — é aqui que o dev demonstra que *sabe* filtrar por dono. É o canal pelo qual a `mallory` vê os próprios ids (40, 42) e infere o vizinho (41).

```python
@app.route("/api/orders")
def list_orders():
    caller = _authenticate()
    return jsonify([o for o in ORDERS.values() if o["owner"] == caller])
```

> **Enquadramento (importante pra "um átomo = uma vuln"):** que a **listagem** filtre certo por dono, mas o **detalhe** (`GET /api/orders/<id>`) **não** — essa **assimetria é a assinatura do BOLA no mundo real**: o dev escopa a lista e esquece o mesmo check no endpoint de item. Não é "segunda vuln"; é a prova de que o dev **sabia** filtrar (fez na lista) e **omitiu** no detalhe. A `GET /api/orders` **não** vaza os pedidos da `alice` (risco #4).

### `GET /api/orders/<int:order_id>` — **a rota vulnerável**

Autentica (Bearer ruim → `401`: a **autenticação funciona**, de propósito), busca o pedido, e o devolve — **sem** cruzar `order["owner"]` com o chamador. Converter `<int:...>` (id sequencial); id inexistente → `404` (higiene, idêntica nas duas versões).

```python
@app.route("/api/orders/<int:order_id>")
def get_order(order_id):
    _authenticate()                      # require a valid token (401 otherwise) — AUTHENTICATION only
    order = ORDERS.get(order_id)
    if order is None:
        abort(404)
    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
    # checking that order["owner"] is the authenticated caller. Being authenticated
    # is not being authorized for THIS object. (BOLA — no object-level check.)
    return jsonify(order)
```

- **Source:** o `<int:order_id>` do path (o objeto pedido) + o token no `Authorization` (a identidade — que o vulnerable **autentica mas ignora na autorização**).
- **Sink conceitual:** o retorno do pedido sem comparar `order["owner"]` com o chamador autenticado. O bug é **o que não está lá** (a checagem) — não greppa por string perigosa; greppa por endpoint que devolve objeto user-scoped e pergunta **"cadê o check de dono?"**. Aqui há o agravante didático de que o endpoint **chama `_authenticate()`** (logo "parece" que cuida de identidade) — mas **descarta** o resultado na hora de autorizar.
- **`abort(401)`** (via `_authenticate`) para token ausente/inválido: a autenticação **funciona**; é o que prova, no passo de contraste, que o bug **não** é de autenticação.
- **`abort(404)`** para pedido inexistente: higiene operacional, idêntica nas duas versões (ortogonal ao bug e ao fix).

### Versão **fixed** — UM eixo muda (a autorização por objeto)

```python
@app.route("/api/orders/<int:order_id>")
def get_order(order_id):
    caller = _authenticate()             # bind the authenticated identity...
    order = ORDERS.get(order_id)
    if order is None:
        abort(404)
    # FIXED: object-level authorization — serve the order only to its owner.
    # 404 (not 403) so "exists but not yours" is indistinguishable from "doesn't
    # exist": with sequential ids, a 403 would be an enumeration oracle.
    if order["owner"] != caller:
        abort(404)
    return jsonify(order)
```

- **`app.py` DIFERE** entre vulnerable e fixed (o bug/checagem mora no código — igual ao 03/10/11, inverso do par XSS). **Só a rota `get_order` muda**; `POST /login`, `GET /api/orders`, helpers e imports são **idênticos**.
- **Diff mínimo, um eixo só:** promover `_authenticate()` → `caller = _authenticate()` (a autenticação, que era descartada, passa a ser **retida**) + a linha `if order["owner"] != caller: abort(404)`. A "autorização" é o condicional adicionado; a ligação (`caller = ...`) é a **estrutura mínima** que o check exige. O DIFF literalmente mostra "authenticated ≠ authorized": o vulnerable **autentica e descarta a identidade**; o fixed **retém e confere**.
- **CRAVAR no DIFF:** o fix **NÃO** troca o id sequencial por UUID, **NÃO** o randomiza, **NÃO** o esconde. O id permanece exatamente tão público e sequencial quanto antes. Trocar o id repetiria a meia-lição que o 11 já demoliu. **O id ser trivial/sequencial é PARTE da lição** (na API o id é público por design); a correção é **só** a autorização por objeto.

---

## Autenticação vs. autorização — o `_authenticate()` e o gap

Este átomo é o primeiro do repo onde há **autenticação de verdade** (token, `401`), então a distinção auth/authz precisa ficar explícita no código, no WALKTHROUGH e no DIFF:

- **Autenticação (presente e correta nas duas versões):** `_authenticate()` resolve o Bearer pra um usuário ou aborta `401`. Todo endpoint da API a chama. É a resposta à pergunta **"quem é você?"**.
- **Autorização por objeto (ausente no vulnerable, presente no fixed):** cruzar `order["owner"]` com o chamador. É a resposta à pergunta **"este objeto é seu?"**.
- O vulnerable **faz a primeira e pula a segunda**. Pior: ele **chama** `_authenticate()` (logo o token é validado — `401` em token ruim), o que faz o endpoint *parecer* consciente de identidade — mas ele **joga fora** essa identidade em vez de autorizar com ela. É a forma mais comum e realista do BOLA (diferente do 03, onde o endpoint ignorava a identidade por completo).

---

## Status code do fix: `404` (não `403`)

O fix retorna **`404`** para pedido de não-dono, **NÃO `403`**. E o pedido inexistente também é `404`. Resultado: "existe mas não é seu" e "não existe" ficam **indistinguíveis**.

**Motivo:** id **SEQUENCIAL**. Um `403` confirmaria existência ("existe, mas você não pode") e, com ids sequenciais, entregaria um **ORÁCULO DE ENUMERAÇÃO** (`403`=existe, `404`=não existe → a `mallory` mapeia **todos** os pedidos, de todos os usuários, varrendo os inteiros). O `404` uniforme **não vaza existência** — a atacante não consegue nem saber quais ids existem.

**Nota OBRIGATÓRIA no DIFF, contrastando com os irmãos (a regra de bolso vira a lição deste átomo):**

- **`idor-uuid-guessable` (11) usa `403`** — e ali é seguro, porque o id é um **UUID (espaço não-enumerável)**: um oráculo `403`/`404` sobre UUIDs é inútil (você não varre 2¹²² ids). O DIFF do 11 já **antecipou este átomo**: *"A 403 here does confirm the receipt exists; if that mattered, 404 would be the defense-in-depth choice."* Aqui **importa** — porque o id é sequencial.
- **`idor-numeric-id` (03) usa `403` com ids sequenciais** — e ali um `403` **também** confirma existência (03 tem o mesmo oráculo latente). Enquadrar com honestidade, **sem** dizer que o 03 "errou": o 03 foi a primeira formulação, priorizou a **clareza semântica** (`403 = forbidden`, "este objeto existe e não é pra você") e o oráculo de enumeração **não era a lição dele**. O 12, modelando uma API onde **enumerar é o movimento-assinatura do BOLA**, faz do oráculo **a lição** — e por isso escolhe `404`.
- **`path-traversal-basic` (10) usa `404`** por **outro motivo**: lá o "recurso" está **fora do domínio** da app (um path que escapou do diretório), e `404` recusa confirmar que exista algo ali. Aqui é um objeto **da** app (existe), mas o `404` esconde essa existência **de propósito**, contra enumeração.
- **Regra de bolso (extensão da do 11):** **`403`** quando admitir existência é ok **ou o id não é enumerável**; **`404`** quando a **própria existência vaza** — e **id sequencial faz a existência vazar**.

---

## O container

`Dockerfile` **idêntico** entre vulnerable e fixed (como todos os átomos). **API-only → NÃO inclui `COPY templates`** (não há templates — esta é a diferença em relação ao Dockerfile do 11). `secrets` é stdlib → **nada** de `apt`, só o Flask no pip. Esqueleto dos átomos 03/11 **menos** a linha de templates:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
```

`app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)` no rodapé do `app.py` (idêntico ao 03/10/11). `docker-compose.yml`: `127.0.0.1:8012:5000` (vulnerable), `127.0.0.1:8112:5000` (fixed) — esqueleto de duas services do 03/10/11, **sem** `sysctls`. Bind **só** em `127.0.0.1`.

---

## Renderização / "um átomo = uma vuln"

**API-only, respostas JSON via `jsonify`** — **sem templates**, logo **sem risco de XSS acidental**: nenhum valor é refletido em contexto HTML (a saída é `application/json`, não HTML). Isso **elimina de origem** a preocupação de reflected XSS que os átomos com HTML precisam tratar com autoescape — aqui não há superfície HTML.

Garantir que a **única** vuln é o BOLA; **nada** de segunda falha empilhada:

- **Sem vazamento de token.** O objeto `order` tem só `id/owner/item/amount` — **nenhum token** é serializado em resposta alguma. Tokens vivem só no mapa `TOKENS`. A `GET /api/orders` lista **só** os pedidos do próprio token (não vaza pedidos nem token de outro usuário).
- **`POST /login`** devolve **só** o token do usuário pedido (e é o atalho de auth fora de escopo — ver "Modelo de identidade").
- **Erros via `abort()` cru** (padrão Flask, HTML estático): o **status code é o sinal do exploit** (`200`/`401`/`404`/`400`); o corpo do erro é imaterial pra lição e **não reflete input** (sem XSS). Consistente com 03/10/11, que usam `abort()` cru. Um error handler JSON seria um polimento cosmético — **mencionável, não aplicado** (mantém o código mínimo, CLAUDE.md §3.6).

---

## Fix

O fix corrige o **único eixo** que a lição expõe: a **object-level authorization ausente**. O DIFF deve deixar cristalino que é **uma** mudança (a autorização), e que ela **não** mexe no id.

```diff
 @app.route("/api/orders/<int:order_id>")
 def get_order(order_id):
-    _authenticate()                      # require a valid token (401 otherwise) — AUTHENTICATION only
+    caller = _authenticate()
     order = ORDERS.get(order_id)
     if order is None:
         abort(404)
-    # VULNERABLE: the request is authenticated, but the order is returned WITHOUT
-    # checking that order["owner"] is the authenticated caller. Being authenticated
-    # is not being authorized for THIS object. (BOLA — no object-level check.)
+    # FIXED: object-level authorization — serve the order only to its owner.
+    # 404 (not 403) so "exists but not yours" is indistinguishable from "doesn't
+    # exist": with sequential ids, a 403 would be an enumeration oracle.
+    if order["owner"] != caller:
+        abort(404)
     return jsonify(order)
```

O fixed lê a identidade **autenticada** (que o vulnerable descartava) e a compara com `order["owner"]` antes de devolver. Mismatch → `404`. Esse condicional fecha o BOLA: a classe é "o servidor devolve um objeto user-scoped sem checar que o chamador é o dono", e a remediação é exatamente a negação disso.

### Notas obrigatórias no DIFF.md

1. **"Reshaping the id is a losing game" (paralelo direto ao 03/11).** A correção **não** é esconder/embaralhar/UUID-izar o id — é **conferir o dono**. Amarrar ao 11 (que já provou que UUID era "theater") e ao 03 (mesmo fix). O agravante deste átomo: numa API o id é **público por contrato**, então "esconder o id" nem é uma opção coerente — a autorização é a única defesa possível.
2. **BOLA não greppa por string perigosa.** Como no 03/11: acha-se **lendo endpoints** que devolvem objeto user-scoped e perguntando "cadê o check de dono?". Agravante aqui: o endpoint **chama `_authenticate()`**, o que desarma o revisor apressado ("tem auth, deve estar ok") — mas autenticar não é autorizar.
3. **"Authenticated ≠ authorized" — visível no próprio diff.** O vulnerable **autentica e descarta** a identidade (`_authenticate()` chamado só pelo efeito de `401`); o fixed **retém e confere** (`caller = _authenticate()` + comparação). A linha `_authenticate()` → `caller = _authenticate()` é literalmente a identidade deixando de ser jogada fora.
4. **`404` vs `403` (a nota de status code inteira da seção "Status code do fix"):** por que `404` aqui (id sequencial → oráculo de enumeração), por que `403` foi ok no 11 (UUID não-enumerável), o oráculo latente do 03, e o `404` por-outro-motivo do 10. Regra de bolso incluída.
5. **A assimetria lista-vs-detalhe é a assinatura do BOLA** (ver "Rotas"/`GET /api/orders`): a listagem escapa correta em **ambas** as versões; só o detalhe faltava com o check. Prova que o dev sabia filtrar e omitiu — não é segunda vuln.
6. **Token opaco, intocado** (ver "Por que token opaco"): notar que o token é uma sessão server-side opaca e que **o ataque não o inspeciona nem modifica** — o token permanece válido e da própria `mallory` o tempo todo. **Sem** mencionar técnicas de ataque a token.

---

## Walkthrough — estrutura e payloads

Trabalhado **100% no Burp (Repeater)** — API-only, **sem trilha browser** (CLAUDE.md §3.3). Cada request é um bloco colável no Repeater: request-line + header `Authorization: Bearer <token>` + corpo JSON quando houver. Tokens/ids são **placeholders** (variam por boot/login), como o 11 fez. Estrutura de beats (espelha 03/11 menos o browser):

> **Abertura — plantar as duas facetas.** Tease: *você vai ler o pedido da `alice` usando o **seu próprio** token, perfeitamente válido — só incrementando um id que a própria API te deu. E no fim vai ver que o endpoint nunca checa de quem é o pedido: qualquer id que você segure, autenticado como você mesmo, já bastava. O token prova que você é você; ele não diz de quem é este pedido.*

### 1. Context
- API REST de pedidos; auth por Bearer token; `GET /api/orders/<id>` é o "ver um pedido". Isto é **BOLA** — o IDOR em API, **#1 do OWASP API Top 10**. Trilha 100% Burp/curl (API-only, sem browser).

### 2. Spot the bug
- Mostrar a view vulnerable. Apontar que ela **chama `_authenticate()`** (autentica — `401` em token ruim) mas **não** compara `order["owner"]` com o chamador. O bug é **o que não está lá**. Pergunta de auditoria: **"onde este endpoint confere que o pedido é do chamador?"** → em lugar nenhum. Notar que **não greppa** (ausência de código) e que ter `_authenticate()` ali **engana** o revisor apressado.

### 3. How auth works in this lab (subseção curta)
- Token opaco via `POST /login` (**sem senha** — atalho de auth fora de escopo, o mesmo espírito do `X-User-ID` self-asserted dos irmãos 03/11; auth real precisaria de senha). O token é **real, emitido pelo servidor, opaco**, mapeado ao seu usuário. Dois pontos: (i) a **autenticação É imposta** (token ruim → `401`); (ii) se a identidade do token é **usada pra autorizar o objeto** é outra pergunta — e o vulnerable não usa. **Disciplina cravada:** o ataque **não toca** o token (não decodifica, não adultera) — ele fica válido e seu o tempo todo.

### 4. Baseline — a API funcionando (Repeater)
- `POST /login` com `{"user":"mallory"}` → `{"token":"<mallory-token>"}` (o seu vai diferir). Bloco:
  ```
  POST /login HTTP/1.1
  Host: 127.0.0.1:8012
  Content-Type: application/json

  {"user": "mallory"}
  ```
- `GET /api/orders` com `Authorization: Bearer <mallory-token>` → `200`, lista com os pedidos da `mallory` (**40 e 42**), **só os dela**. Repare: ids são **inteiros pequenos e sequenciais**, e há um **buraco em 41**.
- `GET /api/orders/40` com o Bearer da `mallory` → `200`, o próprio pedido. A feature faz o que promete.

### 5. Step 1 — Infer the neighbor's id
- A própria API te entregou seus ids (`40`, `42`). Ids são um **contador global**, então `41` (o buraco entre os seus) é de outro cliente. **Sem adivinhar, sem reconstruir** — você só leu seus ids e olhou o vizinho. (Tease de contraste com o 11: lá você reconstruía um UUID a partir de um timestamp; aqui o id **é** a interface, entregue de bandeja.)

### 6. Step 2 — Read the victim's order (BOLA confirmado)
- `GET /api/orders/41` com o Bearer da **`mallory`** → `200` com o pedido da **`alice`** (`Standing desk`, `$589.00`). Bloco:
  ```
  GET /api/orders/41 HTTP/1.1
  Host: 127.0.0.1:8012
  Authorization: Bearer <mallory-token>
  ```
- Você leu o pedido de outro usuário usando **o seu próprio token válido**, só incrementando um id. Isso é **BOLA**. (Nota: um id inexistente como `39` → `404`; no vulnerable a existência vaza por `200`-vs-`404`, mas no `200` você já leva o objeto inteiro de qualquer jeito.)

### 7. Step 3 — What the vuln is NOT (passo de contraste OBRIGATÓRIO — CLAUDE.md §5 — PESO DUPLO)
Isola a causa real e desmonta os DOIS mal-entendidos vizinhos.

- **(a) NÃO é falha de autenticação.** Pegue a request do BOLA (`GET /api/orders/41`, Bearer da `mallory` → `200`, pedido da `alice`). Agora:
  - **remova** o header `Authorization` → **`401`**;
  - **corrompa** o token (troque um caractere) → **`401`**;
  - **restaure** o Bearer válido da `mallory` → **`200`**, pedido da `alice` de novo.
  A **autenticação funciona perfeitamente** — rejeita token ausente e token ruim. E mesmo assim, **com o seu token genuíno**, você leu o pedido da `alice`. Logo a falha **não é** de autenticação: você esteve corretamente autenticado como `mallory` o tempo todo. O gap é **autorização** — ser autenticado como `mallory` nunca foi cruzado com o dono do pedido. **Estar autenticado não é estar autorizado.**
  > **Contraste fino com o 03:** lá o endpoint **ignorava** a identidade por completo (trocar o header não mudava nada). Aqui o endpoint **lê** o token pra autenticar (token ruim → `401`), mas **descarta** a identidade na hora de autorizar. É a forma mais comum do BOLA — e a distinção auth/authz só fica visível **porque** há autenticação real (que os irmãos self-asserted não tinham).
- **(b) NÃO é sobre o id ser adivinhável.** Você não adivinhou nem reconstruiu nada — a `GET /api/orders` te deu seus ids e o buraco em `41` apontou o alvo. Contraste com o irmão UUID (11): lá o id **parecia** imprevisível e você teve que reconstruí-lo; a lição de lá foi "embaralhar o id não é controle". Aqui o id é **público por design de API** — clientes **devem** manejar ids; é o contrato. Então o fix **não** é UUID-izar/randomizar o id (o 11 já provou que é "theater"). **Prova:** o app fixed mantém o id sequencial **intacto** e só acrescenta o check de dono. O formato do id nunca foi o problema; a **object-level authorization ausente** era.
- **Uma causa, duas facetas:** ausência de autorização por objeto.

### 8. Fechamento — Why this is BOLA
- Tabela de contraste A01 (seção "Classe de vulnerabilidade") + o frame quotável ("no `idor-uuid-guessable` embaralhar o id era theater; aqui nem sobra obscuridade — o id é público por contrato; o token prova quem você é, não de quem é o pedido"). Amarrar ao 03 e ao 11 (mesma causa, mesmo fix — o check de dono); citar de **leve** o 10 (família A01, e forward pro DIFF quanto ao contraste de status code). **Sem** foreshadow de átomos não publicados; **sem** frame de ataque a token.

### 9. Impact (honesto — sem overclaim)
- Escalação **HORIZONTAL** de privilégio: leitura de dado de pedido de outro usuário do **mesmo nível** (o que a `alice` comprou e por quanto). **NÃO é RCE. NÃO é escalação vertical.** Enquadrar sem inflar: o BOLA é o **#1 do OWASP API Top 10** justamente por ser **onipresente e de alto impacto** em APIs reais (dados de pedido/conta costumam carregar PII que **encadeia** pra mais ataques), mas o impacto **deste átomo** é a leitura cross-user em si.

### 10. Why the fix works (porta 8112)
Repetir a cadeia contra o fixed:
- `GET /api/orders/41` com o Bearer da `mallory` → **`404`** (não `403`, não `200`). Você segura um token válido e ainda assim é barrado — o fixed compara `order["owner"]` com o chamador. Este check **sozinho** fecha o BOLA.
- `GET /api/orders/40` com o Bearer da `mallory` (o dela) → `200`. Dono lê o próprio.
- Autenticação **ainda** imposta: sem/ruim token → `401`.
- **`404`, não `403`:** com id sequencial, um `403` confirmaria existência e viraria oráculo de enumeração (`403`=existe/`404`=não → mapeia todos os pedidos). O `404` torna "existe mas não é seu" indistinguível de "não existe". (Forward pro DIFF pra discussão completa e o contraste com o `403` do 03/11 e o `404` do 10.)
- **O fix mantém o id sequencial** (não virou UUID) — prova de que o formato do id nunca foi o fix.

**Sem seção de trilha browser** (API-only) e **sem** seção de exercícios/variações (CLAUDE.md §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## Dependências extras

```
Flask==3.0.0
```

Idêntico aos átomos 01/02/06/07/08/09/10/11. `secrets` é stdlib. **Nada** de pip além do Flask, **nada** de `apt`, **sem** banco, **sem** templates. CLAUDE.md §3.6 respeitado.

---

## Theory primer

CLAUDE.md §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**. BOLA é IDOR num endpoint de API — mesma classe — então a página conceitual de IDOR do PortSwigger (a mesma que 03 e 11 já usam) é a escolha compatível com o CLAUDE.md.

- **Candidato do bloco (primer, CLAUDE.md-compliant — confirmar por fetch na Fase 2):** [PortSwigger: Insecure direct object references (IDOR)](https://portswigger.net/web-security/access-control/idor) — **mesma** página de 03/11 (URL já confirmada in-repo). **Na Fase 2, verificar por fetch** se o PortSwigger tem uma página conceitual mais **específica de API/BOLA** (ex.: dentro do material de "API testing"); **se** existir uma claramente melhor pra BOLA, preferi-la; **senão**, usar a página de IDOR. O texto do link preserva **"Insecure direct object references (IDOR)"** em inglês também no README PT (convenção v0.1.0 / 03 / 11).
- **Referência suplementar (na abertura/descrição do README, pra ancorar "BOLA = #1 do OWASP API Top 10" — confirmar por fetch na Fase 2, NÃO inventar):** **OWASP API Security Top 10 (2023), API1:2023 — Broken Object Level Authorization**, página oficial do projeto OWASP API Security. A URL exata **deve** ser confirmada por fetch na Fase 2 (provavelmente sob `owasp.org/API-Security/…`, mas **verificar**, não cravar).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A01 — Broken Access Control** | "Request legítimo alcançou objeto fora do escopo" (acesso), não injection. Mesma moldura e fix do 03/11. |
| Nome / classe | **BOLA — Broken Object Level Authorization (API1:2023)**, o IDOR em API | É o #1 do OWASP API Top 10; a face de API do IDOR. Mesma causa/fix, dialeto de API. |
| Posição no arco | 03 (int sequencial) → 11 (UUID reconstruível) → **12 (id público por design de API)** | Fecha o arco IDOR/BOLA: cada degrau remove uma ilusão de que a *forma* do id protege. |
| Lição-coração | **"Estar autenticado não é estar autorizado"** (Faceta 1) + **"na API o id é público por design"** (Faceta 2) | Faceta 1 é o cerne (passo de contraste); Faceta 2 distingue do 11 e ancora no mundo de API. |
| Token | **Opaco (valor aleatório), mapa `token→user` em memória; NÃO JWT** | (a) JWT puxaria o foco pra atacar o token (não é a lição); (b) foreshadowaria arco JWT não-publicado; (c) opaco é real (OAuth2 opaque / sessão server-side). O ataque **não toca** o token. |
| Auth real? | **Sim, há autenticação genuína** (token, `401`), sem senha | Sobe um degrau de realismo sobre o `X-User-ID` self-asserted de 03/11 — é o que torna a distinção auth/authz nítida. Senha = fora de escopo. |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | CLAUDE.md §3.3 lista "BOLA em REST" como categoria naturalmente API-only. **Primeiro API-only do repo.** |
| Feature | **API REST de pedidos** (`/login`, `/api/orders`, `/api/orders/<id>`), em memória | Endpoint REST de detalhe é o habitat canônico do BOLA. Sem banco (storage segue a superfície do bug). |
| Identidade / dados | `mallory` (atacante/você) + `alice` (vítima); token opaco por login; sem banco | Reusa a dupla de papéis do 11. Login prova que o token é legítimo e próprio. |
| Método HTTP | `POST /login` (mint token), `GET /api/orders` (lista escopada), `GET /api/orders/<int>` (vuln) | REST-ish mínimo. A lista dá à `mallory` seus próprios ids (infere o vizinho). |
| Seed de ids | **`mallory` dona de 40 e 42; `alice` de 41** (o "gap" no meio) | Contador global interliga usuários; o buraco em 41 na lista da `mallory` torna a inferência **óbvia** (didático > minimalista por 1 linha). Alternativa (1 ordem cada, adjacente) preterida. |
| Estrutura do pedido | `id`, `owner`, `item`, `amount` — dado fake benigno | Sem PII, sem cartão, sem segredo (CLAUDE.md §8.3). |
| O bug | **Object-level authorization AUSENTE** em `GET /api/orders/<id>` | Ausência de código, não payload. Não greppa. O endpoint autentica mas descarta a identidade na autorização. |
| Fix (único eixo) | **`if order["owner"] != caller: abort(404)`** (+ reter `caller = _authenticate()`) | O cerne e único fix. Diff limpo de uma autorização. O id **não** é trocado por UUID. |
| Status code do fix | **`404`** (não `403`) | Id sequencial: `403` viraria oráculo de enumeração. `404` esconde existência. Nota obrigatória contrastando com `403` do 03/11 e `404` do 10. |
| `GET /api/orders` (lista) | **Corretamente escopada nas duas versões** (filtra por dono) | Baseline correto (não vaza a `alice`); a assimetria lista-ok/detalhe-quebrado é a assinatura do BOLA. |
| Erros | **`abort()` cru** (padrão Flask); status code é o sinal | Consistente com 03/10/11. Corpo não reflete input (sem XSS). JSON-error handler = polimento mencionável, não aplicado. |
| Renderização | **JSON via `jsonify`, sem templates** | API-only elimina superfície HTML → sem XSS acidental. Nenhum token serializado em resposta. Um bug só. |
| `app.py` vulnerable × fixed | **Diferem** (só a rota `get_order`) | Igual ao 03/10/11, inverso do par XSS. Um eixo muda. |
| Dockerfile | Esqueleto 03/11 **menos `COPY templates`** | Sem `apt`, sem banco, sem templates. Idêntico entre as versões. |
| Trilha | **100% Burp/curl (Repeater); SEM browser** | API-only (CLAUDE.md §3.3: a trilha secundária não existe). |
| Nº de steps | **Baseline + 3 steps + fechamento + fix** | Baseline → infer neighbor → read victim → "o que a vuln NÃO é". Step 3 = contraste obrigatório (peso duplo). |
| Impacto | **Escalação horizontal** (ler pedido de outro user). **Não** RCE, **não** vertical. | Honesto, sem overclaim. Nota: BOLA é #1 do OWASP API Top 10 pela onipresença/impacto, mas o impacto do átomo é a leitura cross-user. |
| Theory primer | **PortSwigger IDOR (bloco) + OWASP API1:2023 (suplementar)** | CLAUDE.md manda PortSwigger; BOLA=IDOR em API. OWASP API1:2023 ancora "o #1 de API". URLs confirmadas por fetch na Fase 2. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–7 são os que o mantenedor pediu explicitamente; 8–11 são higiene técnica desta spec. Todos são validação **na geração** (CLAUDE.md §11), não decisões pendentes.

1. **`POST /login` mapeia `usuário→token`** e o Bearer resolve de volta ao usuário correto: `mallory` e `alice` recebem tokens **distintos**; cada token resolve ao seu dono.
2. **Autenticação funciona:** sem Bearer, ou Bearer inválido/corrompido → **`401`** tanto em `GET /api/orders` quanto em `GET /api/orders/<id>`.
3. **Vulnerable:** `GET /api/orders/41` (id da `alice`) com o Bearer da **`mallory`** → **`200`** com o pedido da `alice` (BOLA confirmado); o token permanece **válido e intacto** (nenhuma decodificação/alteração no ataque).
4. **Baseline correto:** `GET /api/orders` com o Bearer da `mallory` lista **só** os pedidos da `mallory` (40 e 42; **não** vaza os da `alice`); ler o próprio (`GET /api/orders/40`) → `200`.
5. **Fixed:** `GET /api/orders/41` com o Bearer da `mallory` → **`404`** (não `403`, não `200`); dono lendo o próprio (`/api/orders/40`) → `200`; autenticação ainda `401` sem token.
6. **Converter `<int:...>`** aceita os ids sequenciais; id inexistente (ex.: `39`, `999`) → `404` no vulnerable e no fixed (coerente com o fix; no fixed, `404` de não-dono e `404` de inexistente são **indistinguíveis** — sem oráculo).
7. **`app.py` DIFERE só na rota `get_order`** (a linha da autorização + a estrutura mínima: `_authenticate()` → `caller = _authenticate()` e o comentário). `POST /login`, `GET /api/orders`, helpers, imports, `Dockerfile`, `requirements.txt` **idênticos** entre as versões.
8. **Nenhum vazamento de token** em resposta alguma: `order` serializado tem só `id/owner/item/amount`; `GET /api/orders` não devolve pedidos nem token de outro usuário. **Um bug só** (BOLA), nada empilhado.
9. **`secrets.token_urlsafe(24)`** disponível (stdlib) e gera tokens **distintos** entre logins; `_authenticate()` fatia `Bearer ` corretamente (`auth[7:]`), e token vazio/mal-formado → `401`.
10. **Erros via `abort()` cru** entregam o status code esperado; corpo é padrão Flask, estático, **sem** input refletido (sem XSS). (Se o mantenedor quiser JSON nos erros na revisão, é adição opcional de um error handler — **não** aplicar sem pedido.)
11. **API-only confirmado:** **sem** diretório `templates/`, Dockerfile **sem** `COPY templates`, `app.py` **sem** `render_template`; todas as respostas de sucesso em `application/json`.

**Bloqueante remanescente:** nenhum. Spec revisada e assinada pelo mantenedor; o Theory primer está decidido (PortSwigger IDOR no bloco + OWASP API1:2023 suplementar). Resto é validação na Fase 2 (incluindo confirmar as duas URLs do primer por fetch).

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **degrau final do arco IDOR/BOLA** (03 → 11 → 12) e o **primeiro API-only do repo**. Cada parágrafo do walkthrough deve poder ser lido com o 11 aberto ao lado; a diferença ("o id não é mais 'opaco a reconstruir' — é público por contrato de API, e ainda assim isso nunca foi o problema; a autorização por objeto é tudo") tem que estar visível. **Abrir e fechar** na dupla-faceta: "authenticated ≠ authorized" + "o id é público por design".
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `idor-numeric-id` (03) e `idor-uuid-guessable` (11) **inteiros** (irmãos diretos — reusar passo de contraste, framing A01, forma de README/WALKTHROUGH/DIFF; citar o "theater/obfuscation" do 11 e o "reshaping the id is a losing game"; reusar/estender a regra de bolso 403-vs-404 do DIFF do 11) **e** `path-traversal-basic` (10) de leve (contraste de status code `404`). **Não** existe átomo API-only publicado — o formato API-only segue CLAUDE.md §3.3, adaptando o WALKTHROUGH dos irmãos **sem** trilha browser.
- **Átomo stateless, sem banco, sem templates** (como o 03/11, e API-only): dados em `dict`/`set` em memória, token opaco em `TOKENS`, seed dos pedidos no import. **Sem** `sqlite3`, `init_db()`, `DB_PATH`, `render_template`, `templates/`.
- **`app.py` DIFERE entre vulnerable e fixed** (só a rota `get_order`: a autorização por objeto). `Dockerfile` (sem `COPY templates`) e `requirements.txt` idênticos entre as versões.
- **O ponto técnico frágil é a distinção auth/authz** — seguir à risca a seção "Autenticação vs. autorização": `_authenticate()` presente e correto nas duas versões (`401`); o vulnerable **chama e descarta** a identidade, o fixed **retém e confere**. **Não** transformar isto em "falha de autenticação".
- **Token opaco, intocado:** o ataque **nunca** decodifica, adultera ou forja o token — ele fica válido e da `mallory` o tempo todo. **PROIBIDO** mencionar técnicas de ataque a token (decode, `alg:none`, forjar, trocar `sub`) — isso é arco JWT **não-publicado**. Manter o frame "o token é válido e o ataque não o toca".
- **Passo de contraste obrigatório (Step 3), PESO DUPLO:** (a) remova/corrompa o Bearer → `401` (auth funciona) vs. Bearer válido → BOLA (authz ausente); frisar o contraste fino com o 03 (lá a identidade era ignorada; aqui é autenticada e descartada). (b) você não adivinhou/reconstruiu — o id veio da API; o fix mantém o id sequencial (não UUID-iza), provando que a forma do id nunca foi o problema. Espelha o Step 4/5 do 03/11.
- **Status code `404` (não `403`):** cravar a razão do oráculo de enumeração (id sequencial) e a nota obrigatória de contraste com 03/11 (`403`) e 10 (`404` por outro motivo). **Não** copiar o `403` do 03/11 por reflexo.
- **Assimetria lista-vs-detalhe:** `GET /api/orders` filtra certo por dono nas duas versões; só o `GET /api/orders/<id>` faltava com o check. É a assinatura realista do BOLA — não é segunda vuln.
- **Impacto honesto:** escalação **horizontal**; **não** chamar de RCE nem de escalação vertical. Sem overclaim. Nota sobre BOLA ser o #1 do OWASP API Top 10 é enquadramento, não inflação.
- **Renderização JSON:** `jsonify`, sem templates → sem XSS acidental; nenhum token serializado; **um bug só**. Erros via `abort()` cru (status code é o sinal).
- **Cross-atom reference policy:** OK e **desejável** referenciar `idor-numeric-id` (03) e `idor-uuid-guessable` (11, irmãos diretos) e `path-traversal-basic` (10, mesma família A01) **explicitamente**; OK citar os demais em `main` (01/02/04/06/07/08/09). **PROIBIDO** referenciar/foreshadowar qualquer átomo da Fase 3+ ainda não publicado (`jwt-weak-secret`, `jwt-key-confusion`, `session-fixation`, `mass-assignment`, etc.). **NÃO** referenciar o `jwt-none-alg` (05) — embora publicado, ele é sobre **atacar** o token, o que colide com a disciplina "o token é válido e o ataque não o toca" deste átomo; deixá-lo de fora mantém o frame limpo.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0. H1 idêntico: `# bola-rest — Broken Object Level Authorization (BOLA)`. Termos técnicos (BOLA, IDOR, object-level authorization, ownership check, token, Bearer, enumeration oracle, payload) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger IDOR (mesma URL de 03/11, texto `Insecure direct object references (IDOR)` preservado em inglês no PT) + referência suplementar ao OWASP API1:2023 na descrição. **Buscar/confirmar as URLs por fetch na Fase 2** (não inventar); na Fase 2, checar também se há página PortSwigger mais BOLA/API-específica melhor que a de IDOR.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 12: `bola-rest` — Broken Object Level Authorization (BOLA) in a REST API (A01 Broken Access Control). `` (padrão das linhas dos átomos 06–11).
- **ROADMAP.md:** marcar o átomo 12 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): itens 1–11 do checklist acima; reproduzir baseline → infer → BOLA → contraste (a: `401` sem/ruim token, `200` com token válido; b: fix mantém id sequencial) → fixed (`404` de não-dono, `200` de dono, `401` sem token). Validar via `docker exec` + `python http.client` de dentro do container se as portas host não forem alcançáveis do sandbox.
- **Portas:** `127.0.0.1:8012` (vulnerable), `127.0.0.1:8112` (fixed). Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre nome exato de aba/opção do Burp (Repeater basta pros 2–3 sends; Intruder é overkill aqui — poucos ids), **perguntar antes de inventar** (CLAUDE.md).
