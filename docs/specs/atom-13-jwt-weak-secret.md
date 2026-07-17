# Spec — Átomo 13: `jwt-weak-secret`

> Documento de especificação para o Claude Code implementar o décimo-terceiro átomo do projeto `atomicvulns` (Fase 3, **terceiro átomo da fase** — "Access Control & Autenticação", milestone `v0.3.0`; **não** fecha a fase). Este é o **segundo ataque a JWT do repo** e o irmão direto do `jwt-none-alg` (05): onde o 05 foi *"a fechadura nem trancava"* (`alg:none`, o servidor não verificava), o 13 é *"a fechadura tranca — corretamente — mas a chave é fraca"* (HS256 verificado direito, secret adivinhável e quebrável por brute force). O eixo mudou de A01 (o arco IDOR/BOLA de 03/11/12) para **A02 — Cryptographic Failures**. Leia junto com `CLAUDE.md` (Seções 3.3, 3.6, 5, 8, 10.5), `ROADMAP.md`, e — obrigatoriamente — dois átomos de referência já publicados em `main`:
> 1. **`atoms/A02-cryptographic-failures/jwt-none-alg/` (05) — o irmão JWT direto, e o contraste É a lição.** Reusar TODO o vocabulário de JWT (header/payload/signature, `sub`/`role`, `Bearer`, HS256, `jwt.encode`/`jwt.decode`), a forma de README/WALKTHROUGH/DIFF, e a dupla de claims `{"sub": "...", "role": "user"|"admin"}`. Estabelecer o par explícito **"05 = a fechadura não trancava (`alg:none`, não verifica)" vs "13 = a fechadura tranca mas a chave é fraca (HS256 verificado, secret quebrável)"**. No 05 você **arranca** a assinatura; no 13 você a **refaz**, perfeitamente legítima, com o secret roubado. Nota importante: o `decode` do 13 (nas duas versões) é **idêntico ao `decode` FIXED do 05** — `jwt.decode(token, SECRET, algorithms=["HS256"])`. O 13 **começa** onde o 05 terminou (a lição do 05 já aprendida: `algorithms=` positivo, sem branch no header) e mostra a **próxima** falha: mesmo com o algoritmo tratado certo, um secret fraco derruba tudo.
> 2. **`atoms/A01-broken-access-control/bola-rest/` (12) — o átomo anterior, e o molde API-only.** O 12 é o **primeiro átomo API-only do repo** (JSON via `jsonify`, sem templates, sem browser, `POST /login` sem senha). Reusar essa estrutura: forma do `POST /login` (corpo JSON, sem senha, "auth ceremony fora de escopo"), respostas JSON, WALKTHROUGH **sem trilha browser**, README com as notas "API only — no HTML, no browser" e "Authentication, simulated". A diferença central em relação ao 12: aqui o token **É um JWT** e o ataque **o toca** (decodifica, quebra o secret, forja) — o inverso da disciplina do 12 ("o token é opaco e o ataque nunca o toca"). Por isso este átomo **referencia o 05 explicitamente** (o 12 proibia citar o 05 para preservar aquele frame; aqui o frame é o oposto).
>
> Esta spec captura apenas as decisões *específicas* deste átomo. Onde 05 e 12 já resolveram a forma (vocabulário JWT, claims `sub`/`role`, estrutura API-only, `POST /login` sem senha, forma de DIFF/WALKTHROUGH/README), a instrução é **reusar a forma**, não reinventar. **Diferença estrutural central deste átomo:** dois artefatos inéditos no repo — (a) um **diff que muda só um VALOR** (a constante do secret), com a lógica byte-idêntica entre `vulnerable/` e `fixed/`; e (b) uma **wordlist** commitada como asset do lab. Ver "O bug e o fix" e "A wordlist".
>
> **Escopo desta fase (PLANNING):** só a spec. Nada de `vulnerable/`, `fixed/`, README, WALKTHROUGH, DIFF, nem a wordlist — isso é a Fase 2. Nada de commit, merge, ou alteração de convenções (`CLAUDE.md`/`ROADMAP.md`).

---

## Nota de planning — débito preexistente do 05 (memória do mantenedor; NÃO é ação deste átomo)

> O `WALKTHROUGH.md` do `jwt-none-alg` (05, §5) foreshadowa os átomos **13 e 14 por número** (*"atoms 13 and 14 will exploit other flavors of the same shape"*), o que **fere a política** do projeto de não referenciar átomos não-publicados (CLAUDE.md §5). Isso é um **débito do 05**, a ser tratado numa **tarefa separada** (provavelmente ao gerar o 14) — **não se mexe no 05 agora, nem neste átomo**. O **13 não reciproca nem herda o problema**: não foreshadowa o 14, não nomeia um terceiro átomo JWT (ver "Política de referência cross-átomo" nas Notas pro Claude Code). **Registrado aqui apenas para não se perder.**

---

## Identidade

- **ID:** `jwt-weak-secret`
- **Categoria OWASP (pasta / Web Top 10 2021):** **A02 — Cryptographic Failures** (mesma pasta do `jwt-none-alg`: `atoms/A02-cryptographic-failures/`). Confirmado contra o repo: o 05 está em `A02-cryptographic-failures/` e o `ROADMAP.md` lista o 13 como "A02 Cryptographic Failures". Um secret de baixa entropia numa assinatura HMAC é uma falha criptográfica clássica (chave fraca), não injection nem quebra de controle de acesso — A02 é a moldura correta e coerente com o irmão.
- **Também é (contexto):** o **segundo ataque a JWT do projeto**. O 05 e o 13 são **dois ataques distintos a JWT** — não antecipar aqui, nem no átomo publicado, um terceiro (ver "Contraste com irmãos" e "Política de referência cross-átomo"). *(Nota interna de planning: há um terceiro átomo JWT planejado no `ROADMAP.md`, não publicado; por política **não é nomeado** nesta spec nem no átomo.)*
- **Pasta:** `atoms/A02-cryptographic-failures/jwt-weak-secret/`
- **Número sequencial:** 13
- **Porta vulnerable:** `127.0.0.1:8013`
- **Porta fixed:** `127.0.0.1:8113`
- **Bind:** **somente** `127.0.0.1` no `docker-compose.yml` (CLAUDE.md §8.1). Container roda com `ENV HOST=0.0.0.0` interno (pro forwarding do Docker alcançar o Flask); exposição host restrita a `127.0.0.1` pelo compose — mesmo padrão dos átomos 01–12.
- **Fase / milestone:** Fase 3, `v0.3.0` (terceiro átomo da fase; **não** fecha a fase — versionamento/release fica pra depois, fora desta spec).
- **Branch de trabalho:** `atom/jwt-weak-secret`. Convenção `atom/<id>` (CLAUDE.md §6, confirmada nos head refs dos PRs #14–#21). Branch já criada nesta fase de planning.
- **Theory primer (registrar candidato, NÃO buscar/inserir agora — confirmar por fetch na Fase 2):** ver seção "Theory primer". Candidato: a **mesma** página de JWT attacks do PortSwigger que o 05 usa.
- **H1 dos READMEs (idêntico em EN e PT, CLAUDE.md §7):** `# jwt-weak-secret — JWT weak signing secret (brute-forced)` (segue o padrão do 05 `id — Nome/descrição da vuln`; o 05 é `jwt-none-alg — JWT alg=none signature bypass`, então o 13 espelha a forma com "JWT weak signing secret" + o qualificador "(brute-forced)" que fixa o vetor). Texto exato do H1 confirmável na Fase 2, mas manter a forma "`id` — descrição em inglês".

---

## Classe de vulnerabilidade

**JWT com secret de assinatura fraco (low-entropy HMAC key), quebrável por brute force / dictionary attack.** A app assina seus JWTs com HS256 (HMAC-SHA256) e **verifica a assinatura corretamente** em todos os endpoints protegidos (`jwt.decode(..., algorithms=["HS256"])`). Não há `alg:none`, não há branch no header, não há bug de lógica na verificação. A falha é **inteiramente a ENTROPIA DO SECRET**: ele é uma senha adivinhável, presente numa wordlist. Um atacante captura um JWT legítimo, quebra o secret HS256 por brute force contra uma wordlist, e — de posse do secret — **forja tokens válidos à vontade** (qualquer `sub`, qualquer `role`), que passam na verificação porque estão assinados com a chave correta.

### A lição-coração

> **"Um mecanismo de segurança correto ainda é inútil se depender de um segredo fraco."**
> A assinatura HMAC-SHA256 é criptograficamente sólida e o servidor a verifica direito. A porta tranca — perfeitamente. Só que a chave estava anotada num post-it: o secret é uma palavra de dicionário. Quem acha a chave abre a porta como se fosse o dono.

**O cerne.** A assinatura HMAC-SHA256 é **sólida**; o servidor a verifica **corretamente**. Não há falha de algoritmo (o algoritmo é forte), não há falha de verificação (a verificação roda e rejeita assinaturas inválidas — token com assinatura errada → `401`; `alg:none` → `401`). A **única** fraqueza é o **valor** do secret: baixa entropia, adivinhável, num dicionário. Quebrado o secret, o atacante refaz assinaturas **genuínas** — o servidor não tem como distinguir um token forjado com o secret certo de um token que ele mesmo emitiu, porque **são a mesma coisa**: bytes assinados com a chave correta.

**Sub-lição (cravar):** **"JWT assinado" não é sinônimo de "seguro".** A assinatura é **tão forte quanto o secret**. Assinado com uma senha de dicionário é assinado **com nada** — a verificação de assinatura vira teatro no instante em que a chave é adivinhável. *(Paralelo leve com o 11, publicado, que ensinou "UUID não é sinônimo de imprevisível": mesma forma de armadilha — um mecanismo que "parece forte" — `role` assinado, `id` opaco — colapsando porque a propriedade que o sustentaria — entropia da chave, imprevisibilidade do id — não estava lá.)*

### Distinção explícita do 05 (o contraste É a lição — CRAVAR no WALKTHROUGH e no DIFF)

| | `jwt-none-alg` (05) | `jwt-weak-secret` (13) |
|---|---|---|
| **Metáfora** | A fechadura **não trancava** | A fechadura **tranca — corretamente** — mas a chave é fraca |
| **Onde está a falha** | No **design** da verificação (aceita `alg:none`, pula a assinatura) | No **valor** do secret (a verificação está correta; a chave é adivinhável) |
| **O algoritmo/verificação** | Contornado (`verify_signature: False` num branch) | **Rodando e correto** (`algorithms=["HS256"]`, sem branch) |
| **O que o atacante faz com a assinatura** | **Arranca** (larga a signature, `alg:none`) | **Refaz** (assina de novo, legítima, com o secret quebrado) |
| **O bug no código** | Código **presente e errado** (o branch `alg:none`) | Um **VALOR** errado (a constante `SECRET`) — a lógica está certa |
| **O fix** | **Remover** o branch `alg:none` (05 deletou 4 linhas) | **Trocar o valor** do secret (fraco → forte); zero linhas de lógica tocadas |

O elo conceitual: o 05 martelou *"looks-like-crypto is not is-crypto"* — um `jwt.decode(...)` cercado de `SECRET` e `algorithms=` **parece** um security boundary; se algum caminho pula a verificação, não é. O 13 **afia** a mesma tese para o caso em que a verificação **não** é pulada: mesmo rodando `algorithms=["HS256"]` corretamente, ainda **não** é um boundary de verdade se o **secret** for adivinhável. **05 = o boundary era contornável (o algoritmo); 13 = o boundary roda, mas a chave que o sustenta é fraca.** Ambos são *"parece um boundary, não é um boundary"* — a tese recorrente do 05 — agora aplicada à **CHAVE**, não ao ALGORITMO.

**Callback ao próprio 05 (publicado, permitido):** a §5 do WALKTHROUGH do 05 já **nomeou** "weak shared secrets that survive a brute-force" como um dos jeitos de "perder esse jogo". Este átomo **é exatamente esse flavor** concretizado. O 13 pode dizer, no fechamento: *"o `jwt-none-alg` (§5) apontou o secret fraco como outra forma de perder este jogo — este átomo é essa forma."* **Não** transformar isso em foreshadow de átomo futuro (ver "Política de referência cross-átomo").

### O que este átomo acrescenta ao arco — escalação VERTICAL

Os átomos A01 desta fase (11 `idor-uuid-guessable`, 12 `bola-rest`) ensinaram escalação **HORIZONTAL**: acessar o dado de **outro usuário do mesmo nível**. O 13 sobe o eixo: ensina escalação **VERTICAL**. O JWT carrega uma claim de privilégio (`role: user` legítimo vs `role: admin` forjado). Quebrar o secret e forjar `role: admin` te dá **poder** (acesso administrativo), não só outra identidade. É um impacto **honestamente mais alto e distinto** do arco A01 — e a forja permite qualquer claim (`sub` e `role`), então na prática o atacante controla **toda a autenticação** daquela app. (Ver "Impacto".)

### Por que A02 (Cryptographic Failures)

O bug **não é** "input virou código" (injection) nem "faltou um check de dono" (broken access control / o arco A01). É **"a chave criptográfica que protege a assinatura tem entropia insuficiente e cai por brute force"** — uma falha de **criptografia** (chave fraca). No Web Top 10 2021 isso é **A02 — Cryptographic Failures**, exatamente onde o `jwt-none-alg` (05) já mora. Manter a coerência de pasta e categoria com o irmão.

---

## Uma vuln só — HS256 verificado CORRETAMENTE, `alg:none` REJEITADO

Invariante inegociável do átomo (CLAUDE.md §2, "um átomo = uma vulnerabilidade"): a **única** falha é o secret fraco. Para garantir isso, o servidor **DEVE** verificar a assinatura HS256 corretamente e **rejeitar** qualquer outra fraqueza:

- **`jwt.decode(token, SECRET, algorithms=["HS256"])`** — lista de algoritmos **positiva e fechada** em HS256. **Nunca** lista vazia, **nunca** `none`, **nunca** branch no `header["alg"]`. Isso é literalmente o `decode` **FIXED do 05**. Consequência: um token `alg:none` (o exploit do 05) → **rejeitado** (`401`) aqui. Se o 13 aceitasse `alg:none`, **empilharia a vuln do 05 sobre a do 13** — dois bugs, violando "um átomo = uma vuln". **PROIBIDO.**
- **Token com assinatura inválida (secret errado)** → `401`. A verificação **funciona**: só um token assinado com o secret **correto** passa. É isso que prova, no passo de contraste, que a falha **não** é de verificação — é só do valor da chave.
- **Sem segunda falha empilhada:** nenhum secret exposto em resposta (o `SECRET` nunca é serializado em lugar nenhum), nenhuma outra claim confiável sem verificar assinatura, nenhum endpoint que pule o `decode`. A **única** superfície é a entropia do `SECRET`.

**Cravar no WALKTHROUGH e no DIFF:** o ataque **não** contorna a verificação — ele a **satisfaz**, com a chave que quebrou. A assinatura que o atacante produz é indistinguível de uma emitida pelo servidor, porque usa a mesma chave. Isso é o oposto do 05 (lá a verificação era pulada).

---

## Feature simulada — API com autenticação JWT (API-only, sem HTML)

**Uma API com login por token JWT.** O cliente faz login e recebe um JWT assinado (`role: user`). Um endpoint comum aceita qualquer token válido; um endpoint administrativo exige `role: admin`. Do ponto de vista do dev, "só admins acessam a área admin, e a assinatura HS256 garante que ninguém forja um token" — mas o secret que assina tudo é uma senha de dicionário.

**Tipo de átomo:** `[ ] com HTML` / `[x] API-only` — **decisão do Claude Code, sinalizada e travada aqui.** Justificativa:
- **CLAUDE.md §3.3 lista "JWT (todas as variantes)" como categoria naturalmente API-only.** É a orientação direta da convenção.
- **O exploit é 100% token-cêntrico:** capturar o JWT → quebrar o secret → forjar → replay. Não há interação de UI que faça parte do exploit; um form/HTML seria cenário artificial (CLAUDE.md §3.3, "não se força um frontend artificial").
- **Coerência com o 12** (átomo imediatamente anterior, também auth real por token, `POST /login` sem senha): o 13 é o **segundo API-only do repo** e reusa o molde do 12.
- **Elimina superfície de XSS acidental** (sem templates, sem reflexão em HTML).
- **Nota sobre o irmão 05:** o 05 foi feito **com HTML** (uma página de contexto que emite o token). O 13 **diverge** disso e vai API-only — por §3.3, pela natureza do exploit, e pelo precedente do 12. **O contraste com o 05 é sobre a VULNERABILIDADE (`alg:none` vs secret fraco), não sobre o layout de arquivos** — a diferença de estrutura (05 com HTML, 13 API-only) não enfraquece o par; a lição do par mora no bug, não nos templates. Registrar isso pro Claude Code da Fase 2 não tentar espelhar os templates do 05.

Consequências (idênticas às do 12):
- **Sem HTML, sem `templates/`, sem `render_template`.** Respostas em `application/json` via `jsonify`.
- Corpo JSON no `POST /login`; auth via header `Authorization: Bearer <jwt>`.
- **Sem trilha browser** no WALKTHROUGH (CLAUDE.md §3.3: "Em átomos API-only, a trilha secundária não existe"). Ver "Walkthrough" para a nuance da ferramenta externa (john) na trilha principal.

---

## Modelo de identidade e dados — sem banco

**Sem banco** (como 03/11/12; CLAUDE.md §3.4 — o storage segue a superfície do bug: um secret fraco não depende de camada de storage). Dados em estruturas Python em memória. Nota "Stack note — no database" no README, espelhando os irmãos.

**Autenticação simulada — JWT sem senha.** `POST /login` recebe `{"user": "<nome>"}` (default `alice`) e devolve um **JWT HS256** com claims `{"sub": "<nome>", "role": "user"}`, assinado com o **secret fraco**. **Sem senha** — auth real (senha, hashing) está **fora de escopo**, exatamente como no 12 (e como o token auto-emitido do 05). O login existe **só pra dar ao aluno um token legítimo pra atacar**.

- **`role` é SEMPRE `"user"` no `/login`.** O servidor **nunca** emite um token `role: admin`. Esse é o ponto: você **não** consegue simplesmente "logar como admin" — tem que **forjar** (quebrar o secret + assinar). A claim de privilégio é atribuída server-side como `user`; virar `admin` exige a chave.
- **O `sub` é incidental à lição.** O que carrega privilégio é `role`, não `sub`. O username no corpo é conveniência (default `alice`) pra o token parecer real; não é a vuln, e um "login como qualquer nome" é a mesma simplificação de auth-sem-senha do 12, **não** uma segunda falha.

**Dado admin fake (benigno, sem PII/segredo — CLAUDE.md §8.3).** O `GET /admin/users` devolve uma lista curta de usuários fake — só `user` + `role`, **nada** de senha, PII, ou o `SECRET`. Candidato:

```python
# Admin-only directory. Benign fake data: no PII, no secrets, and never the SECRET.
USERS = [
    {"user": "alice", "role": "user"},
    {"user": "bob",   "role": "user"},
    {"user": "carol", "role": "admin"},
]
```

**Estado mutável de processo único** aceitável no lab (nada persiste; restart zera). Não há store de tokens (JWT é stateless — o servidor não guarda tokens, só o `SECRET` pra verificar). Diferença do 12, que tinha um mapa `TOKENS`; aqui o JWT carrega o estado.

---

## Rotas

Imports: `import os`, `import jwt`, `from flask import Flask, request, jsonify, abort`. (**Sem** `render_template` — não há templates; **sem** `sqlite3`, `secrets`, `subprocess`. `jwt` é o PyJWT — ver "Biblioteca JWT".)

Constantes e helpers no topo do `app.py`. **ATENÇÃO — a ÚNICA diferença entre vulnerable e fixed é o valor de `SECRET`.** Todo o resto (helpers, rotas, imports) é **byte-idêntico**.

```python
app = Flask(__name__)

# VULNERABLE: weak, dictionary-crackable signing secret. This single VALUE is the
# entire vulnerability — the verification logic below is correct.
SECRET = "sup3rs3cr3t"   # <- candidato; Fase 2 confirma crack + posição na wordlist

USERS = [
    {"user": "alice", "role": "user"},
    {"user": "bob",   "role": "user"},
    {"user": "carol", "role": "admin"},
]


def decode(token):
    # HS256 enforced as a positive, closed allowlist. No alg:none branch, no header
    # branch. This is byte-identical to jwt-none-alg's FIXED decode: the algorithm is
    # handled correctly. The only weakness is the value of SECRET above.
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def authenticate():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        abort(401)
    try:
        return decode(auth.split(" ", 1)[1].strip())
    except jwt.PyJWTError:
        abort(401)
```

### `POST /login` — obter um JWT legítimo (idêntico nas duas versões)

Recebe `{"user": "<nome>"}` (default `alice`), assina um JWT `role: user` com o `SECRET`, devolve `{"token": "<jwt>"}`. Sem senha. `role` sempre `user` — o servidor nunca emite `admin`.

```python
@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    user = body.get("user", "alice")          # no password — auth ceremony out of scope
    token = jwt.encode({"sub": user, "role": "user"}, SECRET, algorithm="HS256")
    return jsonify({"token": token})          # role is always "user"; /login never mints admin
```

- `jwt.encode(...)` em PyJWT 2.x retorna `str` (confirmado pelo uso do 05) → `jsonify` direto funciona.
- O JWT é assinado com o secret fraco — é este token que o aluno captura e ataca.

### `GET /api/profile` — baseline, qualquer token válido (idêntico nas duas versões)

Autentica (Bearer ruim → `401`) e devolve as claims do chamador. Prova que "seu token funciona"; é onde o Burp captura o JWT no header.

```python
@app.route("/api/profile")
def profile():
    claims = authenticate()
    return jsonify({"sub": claims.get("sub"), "role": claims.get("role")})
```

### `GET /admin/users` — endpoint admin, exige `role: admin` (idêntico nas duas versões)

Autentica, e só devolve os dados se a claim `role` for `admin`. Token legítimo (`role: user`) → `403`. Token **forjado** (`role: admin`, assinado com o secret quebrado) → `200`.

```python
@app.route("/admin/users")
def admin_users():
    claims = authenticate()
    if claims.get("role") != "admin":
        abort(403)
    return jsonify(USERS)
```

- **`403` (não `404`)** para `role: user`: aqui é semanticamente correto ("você está autenticado, mas não é admin") e **não** há oráculo de enumeração a temer (o endpoint é fixo, não indexa objetos por id sequencial — diferente do 12). Não copiar o `404` do 12 por reflexo; o motivo do `404` de lá (id sequencial → oráculo) não existe aqui.
- **A verificação de assinatura acontece dentro de `authenticate()`/`decode()`** — antes de qualquer checagem de `role`. Um token com assinatura inválida nunca chega no `if role != admin`; morre em `401` no `decode`.

### Rodapé (idêntico nas duas versões)

```python
if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000)
```

---

## O bug e o fix — o diff INÉDITO (só um VALOR muda)

**O bug NÃO é código ausente nem lógica errada — é um VALOR.** O `app.py` do `vulnerable/` e do `fixed/` diferem **SÓ na constante `SECRET`**. A lógica é **IDÊNTICA**: mesmo algoritmo (HS256), mesma verificação (`algorithms=["HS256"]`), mesmos endpoints, mesmos helpers, mesmos imports. Byte-idênticos, exceto uma linha.

### Por que este diff é inédito no repo (a taxonomia — cravar no DIFF)

O repo já teve dois tipos de diff; este é um **terceiro**:

1. **Lógica diferente** (os A01 — 03/10/11/12, e o próprio 05): o `app.py` difere numa **rota/função** — um check adicionado, um branch removido. O bug/fix mora no **código**.
2. **`app.py` idêntico** (o par XSS, ex. `xss-reflected`): a diferença vive no **template** (um `|safe` a menos); o `app.py` é igual entre as versões.
3. **Mesma lógica, VALOR diferente** (**este átomo, 13**): o `app.py` difere, mas **só numa constante** — nenhuma linha de lógica muda. **A segurança morava INTEIRAMENTE no valor do segredo, não no código.**

**A lição do diff:** a correção **não foi tocar uma linha de lógica** — foi trocar `SECRET = "<fraco>"` por `SECRET = "<forte>"`. O DIFF deve deixar isso cristalino: um diff de **uma linha**, e essa linha é um **dado**, não uma instrução.

### O fix — secret forte (CSPRNG, alta entropia)

```diff
-SECRET = "sup3rs3cr3t"   # weak, dictionary-crackable
+SECRET = "<43-char CSPRNG value, e.g. from secrets.token_urlsafe(32)>"   # strong, not in any wordlist
```

- **Como gerar (Fase 2):** rodar `python -c "import secrets; print(secrets.token_urlsafe(32))"` **uma vez** e colar o **literal** resultante (43 chars base64url) em `fixed/app.py`. **NÃO** escrever `SECRET = secrets.token_urlsafe(32)` — isso regeraria o secret a cada boot do processo, e tokens não sobreviveriam a um restart. É um **valor forte, fixo**.
- **Resultado:** o **mesmo** john contra a **mesma** wordlist, agora sobre um JWT do `fixed/`, **NÃO acha** o secret (não está na lista; e brute-forçar 32 bytes aleatórios é inviável de qualquer forma). E o token forjado com o secret **antigo** (fraco) → `401` no `fixed/` (a assinatura não bate mais com o secret forte). Endpoints e verificação **idênticos** — só a chave mudou.

### Nota obrigatória no DIFF — "o secret forte está visível no `fixed/app.py`, e por que isso não fura a lição"

O secret forte fica **hardcoded e visível** no `fixed/app.py` (está no repo). Isso **não** enfraquece a lição, e o DIFF deve explicar por quê:
- **O modelo de ataque é "o atacante tem um JWT + uma wordlist", não "o atacante lê seu código-fonte".** Num deploy real o fonte não é público; o atacante parte do token. A lição é: **brute-forçar o secret a partir do token é inviável** quando o secret tem alta entropia — e isso continua verdade mesmo com o valor visível no lab.
- **O lab hardcoda os dois secrets (fraco e forte) por estabilidade e inspeção** — o aluno precisa de um valor fixo pra reproduzir. Isso é conveniência de lab.
- **Nota "mencionável, não aplicada" (padrão do 12 pro JSON-error-handler):** um fix de produção **também** tiraria o secret do fonte (env var / secret manager). Mas isso é **outra** preocupação (secret management), e este átomo **isola o eixo da entropia** — por isso as duas versões hardcodam, mudando só o valor. **Não** transformar o átomo num átomo de secret-management; a lição é entropia.

### Notas obrigatórias no DIFF.md

1. **O diff inédito (a taxonomia acima).** Mesma lógica, um valor. A segurança morava no valor, não no código. Um diff de uma linha, e a linha é um dado.
2. **Contraste explícito com o 05 (obrigatório).** O fix do 05 **removeu** código (4 linhas, o branch `alg:none`); o fix do 13 é ainda menor — **não remove nem adiciona lógica**, troca um literal. 05 = a verificação era contornável; 13 = a verificação roda, mas a chave é fraca. Ambos = "parece boundary, não é boundary", aplicado ao ALGORITMO (05) vs à CHAVE (13). Incluir o callback à §5 do 05 (que já nomeou "weak brute-forceable secrets").
3. **A sub-lição: "assinado" ≠ "seguro".** Uma assinatura é tão forte quanto a chave; assinada com palavra de dicionário, é assinada com nada. O `decode` do 13 é o `decode` FIXED do 05 — algoritmo tratado certo — e ainda assim cai, porque a chave é fraca. A lição do 05 (allowlist de algoritmos) é **necessária mas não suficiente**.
4. **O secret forte visível no `fixed/` (a nota do modelo de ataque acima).**
5. **`403` (não `404`) no `/admin/users`** — semanticamente correto e sem oráculo aqui; **não** é o caso do `404` do 12 (que existia por id sequencial). Nota curta pra evitar cópia reflexa.

---

## A wordlist

**Incluir no átomo um arquivo `wordlist-sample.txt`** com **~1000** senhas comuns/plausíveis. **Artefato inédito no repo** (o template de átomo da CLAUDE.md §5 não prevê wordlist) — registrar como asset do lab.

- **Localização:** na **raiz do átomo** — `atoms/A02-cryptographic-failures/jwt-weak-secret/wordlist-sample.txt`. É um asset do WALKTHROUGH (usado pelo ataque), não parte do app `vulnerable/`/`fixed/` — a raiz é o lugar natural, análogo ao `burp/` opcional do §5. **NÃO** vai dentro de `vulnerable/` ou `fixed/` (não é copiada pro container; o crack roda no terminal do aluno, fora do container).
- **NÃO é a rockyou.** Não commitar rockyou (~130MB, senhas reais vazadas, ferramental do atacante — não conteúdo do lab). É uma lista **curada e curta** de senhas óbvias/comuns + alguns "secrets de dev preguiçoso" plausíveis. **Nenhum arquivo grande commitado** (CLAUDE.md §8).
- **O secret fraco DEVE estar na lista, por volta da posição ~980 de ~1000** — perto do fim, pra o john mostrar tentativas rolando na tela **antes** de achar. O aluno quer **VER a ferramenta trabalhando**. Se na validação (Fase 2) o crack sair instantâneo demais, **ajustar a posição/tamanho** e documentar.
- **Conteúdo:** senhas comuns genéricas (estilo top-1000: `123456`, `password`, `qwerty`, `admin`, `letmein`, ...) + um punhado de "dev secrets" plausíveis (`secret`, `changeme`, `jwt_secret`, `supersecret`, ...), com o secret escolhido (`sup3rs3cr3t` ou o fallback) plantado perto do fim. Curadoria própria; **não** copiar de fonte vazada.

### Realidade vs. conveniência (o que o WALKTHROUGH diz sobre a rockyou)

- O walkthrough **USA a wordlist do átomo** (sucesso rápido, zero atrito).
- E **menciona** que, no mundo real, se usaria a **rockyou** — apontando a **FONTE CANÔNICA** (vem no Kali em `/usr/share/wordlists/rockyou.txt`, ou via a distribuição do John the Ripper), e explicando que **o secret escolhido está nela também**.
- **SEM `wget` de URL volátil** (URLs soltas de rockyou apodrecem — CLAUDE.md desencoraja links quebráveis). **SEM redistribuir** a rockyou. Só **mencionar + apontar a fonte canônica**, sem tutoriar.
- **Fase 2 deve confirmar** que o secret escolhido está na rockyou (se a rockyou estiver disponível no ambiente; `grep -x "<secret>" /usr/share/wordlists/rockyou.txt`). **Se o secret primário não estiver na rockyou**, cair pra um fallback que esteja (candidatos de alta confiança: `changeme123`, `secret123`, `password123`) — pra a afirmação "está na rockyou também" ser **honesta**, não inventada.

---

## A ferramenta (john) — usar e linkar, NÃO ensinar; e a trilha

O átomo ensina a **VULNERABILIDADE** (secret fraco), **NÃO** a ferramenta. Disciplina:

- **Mostrar o passo a passo do ataque:** o comando do john contra a wordlist, o **output real** do secret encontrado, a forja, o replay. Mas **NÃO** virar tutorial de john: nada de "como instalar", nada de explicar wordlist do zero, nada de flags uma a uma.
- **Linkar o GitHub do John the Ripper** (`openwall/john`) pra quem não conhece ir aprender por conta. **Confirmar a URL exata por fetch na Fase 2** (provavelmente `https://github.com/openwall/john`). Mesmo tratamento pra a rockyou (mencionar + fonte canônica, sem tutorial).

### A trilha — Burp planta/replaya, o terminal (john) quebra

CLAUDE.md §3.3 põe o Burp como ferramenta primária, com uma **exceção** explícita: quando a *prova* da vuln exige algo que o Burp não faz (o exemplo da §3.3 é o browser executando JS em XSS — "o Burp planta e manipula as requests ... e o browser observa a execução"). **Este átomo é análogo:** a prova exige **quebrar um secret**, coisa que o Burp não faz. Então a **trilha principal** divide as ferramentas, espelhando a lógica da exceção da §3.3:

- **Burp (Repeater):** captura o JWT legítimo (do response do `/login` e/ou do header `Authorization` do `/api/profile`) e faz o **replay** do token forjado no `/admin/users`. Esta é a parte "profissão" — controle cru do request, do header, do token.
- **Terminal do aluno (john):** quebra o secret HS256 contra a wordlist do átomo. **Fora do Burp, fora do container.** É o passo central e novo.
- **Terminal do aluno (Python one-liner):** forja o token `role: admin` com o secret quebrado (ver "A forja do token").

Isso **não** é a "trilha secundária" (que, sendo API-only, **não existe** — CLAUDE.md §3.3). É a trilha **principal**, que legitimamente usa uma ferramenta externa porque a vuln exige. Registrar isso pro Claude Code da Fase 2: a estrutura do WALKTHROUGH é Burp+terminal na trilha principal, **sem** trilha browser.

---

## Biblioteca JWT — PyJWT (coerência com o 05)

- **Escolha: PyJWT**, o padrão de fato em Flask, e a **mesma lib que o 05 usa**. Confirmado por leitura do 05: `requirements.txt` do 05 pina **`PyJWT==2.12.1`** (vulnerable e fixed idênticos). O 13 **reusa a mesma versão** (`PyJWT==2.12.1`) por coerência.
- **`requirements.txt` do 13:** `Flask==3.0.0` + `PyJWT==2.12.1` (idêntico ao do 05, e idêntico entre vulnerable e fixed). É o segundo átomo do repo (depois do 05) a depender de PyJWT; para **este** `requirements.txt`, é a primeira dependência além do Flask (o 12 era Flask-only).
- **Nota sobre o pin (CLAUDE.md §8.7):** o 05 pina PyJWT porque o comportamento de uma versão **é** objeto de estudo (como ele trata `alg:none`). No **13**, o pin é só **coerência/reprodutibilidade** — a vuln (secret fraco) é **agnóstica de versão** (sign/verify HS256 é estável entre versões do PyJWT; o crack roda no john, independente da lib). Ainda assim, pinar é a convenção do projeto (Dependabot off, updates manuais). Registrar a distinção: **o pin do 13 não é behavior-critical como o do 05**.
- **Fase 2:** confirmar que `PyJWT==2.12.1` instala e que `jwt.encode`/`jwt.decode` HS256 se comportam como especificado; se houver qualquer razão pra divergir da versão do 05, **sinalizar ao mantenedor** antes.

---

## A forja do token — one-liner Python (recomendado)

Depois de quebrar o secret, o aluno forja o token `role: admin`. **Recomendado: um one-liner Python com o PyJWT** (didático, sem dependência extra além da lib que o átomo já usa):

```bash
python -c "import jwt; print(jwt.encode({'sub': 'alice', 'role': 'admin'}, 'sup3rs3cr3t', algorithm='HS256'))"
```

- Substituir `'sup3rs3cr3t'` pelo secret **quebrado** (o mesmo valor, agora "descoberto" pelo john) e ajustar as claims (`sub` livre, `role: admin` é o que importa).
- **Ancorar a lição da REFORJA:** este é o inverso do 05. No 05 você **arrancava** a assinatura (`alg:none`, terceiro segmento vazio); aqui você **produz uma assinatura genuína** com o secret roubado — o servidor a aceita porque é matematicamente idêntica a uma que ele mesmo emitiria.
- **Alternativa mencionável (não recomendada como primária):** ferramentas de JWT (ex.: jwt.io, jwt_tool). O one-liner Python vence por não exigir nada além do PyJWT já presente e por ser transparente (o aluno vê exatamente o que assina).
- **O snippet mostrado DEVE ser real e ter rodado** (validação Fase 2 — capturar o token de saída real).

---

## Renderização / "um átomo = uma vuln"

**API-only, respostas JSON via `jsonify`** — **sem templates**, logo **sem risco de XSS acidental** (nenhum valor refletido em contexto HTML; a saída é `application/json`). Isso **elimina de origem** a preocupação de reflected XSS.

Garantir que a **única** vuln é o secret fraco (ver também "Uma vuln só"):
- **`algorithms=["HS256"]`** no `decode` — `alg:none` e outros algs **rejeitados** (senão empilharia a vuln do 05).
- **Sem vazamento do `SECRET`** em resposta alguma — o `SECRET` só aparece nas chamadas `jwt.encode`/`jwt.decode`, nunca é serializado. O `/admin/users` devolve só dado fake benigno (`user`/`role`), **nunca** o secret.
- **Sem store de token** (JWT é stateless) — nenhum mapa a vazar.
- **Erros via `abort()` cru** (padrão Flask): o **status code é o sinal do exploit** (`200`/`401`/`403`); corpo do erro é imaterial e **não reflete input** (sem XSS). Consistente com 03/05/10/11/12. Um error handler JSON seria polimento cosmético — **mencionável, não aplicado** (código mínimo, CLAUDE.md §3.6).

---

## Walkthrough — estrutura e beats

Trabalhado na **trilha principal Burp + terminal** (ver "A ferramenta (john) — a trilha"), **sem trilha browser** (API-only). Cada request é um bloco colável no Repeater; comandos de terminal (john, one-liner de forja) em blocos `bash`. Tokens são **placeholders** (variam por login/boot). Estrutura de beats:

> **Abertura — plantar a lição.** Tease: *você vai pegar um JWT legítimo, com uma assinatura HS256 perfeitamente válida, e quebrar o secret que a assina — porque o dev escolheu uma palavra de dicionário. Com o secret na mão, você forja um token `role: admin` que o servidor aceita como genuíno — não porque a verificação de assinatura está quebrada (ela está correta), mas porque agora você tem a chave. A fechadura tranca; a chave estava num post-it.*

### 1. Context
- API com auth por JWT: `POST /login` (dá seu token `role: user`), `GET /api/profile` (qualquer token válido), `GET /admin/users` (exige `role: admin`). HS256, verificado **corretamente**. Isto é **A02 — secret de assinatura fraco**. Trilha: Burp (captura + replay) + terminal (john quebra, Python forja). API-only, sem browser. **Distinguir do 05 já aqui:** lá a fechadura não trancava (`alg:none`); aqui tranca — a chave é que é fraca.

### 2. Spot the bug
- Mostrar o `vulnerable/app.py`. Apontar que o `decode` está **correto** — `jwt.decode(token, SECRET, algorithms=["HS256"])`, allowlist positiva, **sem** branch `alg:none` (contraste direto com o 05, cujo `decode` tinha o branch). **O bug não está nesta linha.** O bug é o **VALOR**: `SECRET = "sup3rs3cr3t"` — uma palavra de dicionário (leet). Pergunta de auditoria: **"esse secret é forte?"** → não, está num dicionário. O bug é um **VALOR**, não código ausente (como os A01) nem lógica errada. Foreshadow do diff inédito: "guarde isso — a correção vai ser trocar uma constante, não uma linha de lógica".

### 3. How JWT auth works here (recap curto)
- Recap mínimo: JWT é `header.payload.signature`; a signature é o **HMAC-SHA256 de `header.payload` com o `SECRET`**; o servidor recomputa com o `SECRET` e rejeita se não bater. **Forjar um token exige saber o `SECRET`.** (Pra a anatomia completa de um JWT decodificado à mão, apontar pro 05 — o átomo é auto-contido, mas não repete o primer inteiro; o foco aqui é o crack.) Cravar: **o servidor impõe `algorithms=["HS256"]`** — `alg:none` (o truque do 05) **não** funciona aqui; aquele bug está fechado. Isso planta o passo de contraste.

### 4. Baseline — a API funcionando (Repeater)
- `POST /login` com `{"user":"alice"}` → `{"token":"<jwt>"}` (role `user`). Bloco colável.
- `GET /api/profile` com `Authorization: Bearer <jwt>` → `200`, `{"sub":"alice","role":"user"}`. Seu token funciona.
- `GET /admin/users` com o mesmo token → **`403`**. Você está autenticado, mas não é admin. Baseline legítimo — a autorização por `role` funciona.

### 5. Step 1 — Capture the JWT (Burp)
- O JWT está no response do `/login` e no header `Authorization` das suas requests ao `/api/profile`. Copie-o (é o token que você vai quebrar). Bloco mostrando onde ele aparece no Burp.

### 6. Step 2 — Crack the signing secret (terminal, john — o passo central)
- Salvar o JWT num arquivo e rodar o **john** contra a **wordlist do átomo**. Mostrar o **output REAL** (Fase 2), com tentativas rolando **antes** do hit, terminando no secret encontrado. Ferramenta **usada, não ensinada**; link `openwall/john`.
- **Aside de mundo real:** na prática se usaria a **rockyou** (fonte canônica: Kali `/usr/share/wordlists/rockyou.txt` ou via a distribuição do john); o secret escolhido está nela também. Sem `wget`, sem redistribuir — só apontar a fonte.
- *(Fase 2 confirma o comando exato — john jumbo em formato JWT/HMAC-SHA256; fallback hashcat `-m 16500` — e captura o output real. Se nenhum dos dois estiver disponível no ambiente, PARAR e avisar o mantenedor — NÃO inventar o output.)*

### 7. Step 3 — Forge an admin token (terminal, Python one-liner)
- Com o secret quebrado, forjar `{"sub":"alice","role":"admin"}` assinado em HS256 com o secret (one-liner Python + PyJWT). Mostrar o snippet real e o token de saída. **Cravar a REFORJA:** ao contrário do 05 (você arrancava a assinatura), aqui você **produz uma assinatura genuína** — indistinguível de uma emitida pelo servidor, porque usa a mesma chave.

### 8. Step 4 — Replay the forged token (Burp)
- `GET /admin/users` com `Authorization: Bearer <forged-jwt>` → **`200`**, o dado admin. **Escalação vertical confirmada.** Você não contornou a verificação — você a **satisfez**, com a chave que quebrou.

### 9. What the vuln is NOT (passo de contraste — isola a causa e crava o par com o 05)
Serve à §5 do CLAUDE.md em espírito (isolar a causa real, desmontar o mal-entendido vizinho — aqui, a confusão com o 05 e com "o algoritmo é fraco") e enacta a validação #2. Provar, no Repeater:
- **NÃO é falha de verificação.** Pegue o token forjado e **troque um caractere da assinatura** (ou assine com um secret errado, ex. `"wrongkey"`) → **`401`**. A verificação **funciona**: só a assinatura com o secret **correto** passa.
- **NÃO é `alg:none` (não é o bug do 05).** Monte um token `alg:none` (o exploit do 05) e mande no `/admin/users` → **`401`**. Aqui `algorithms=["HS256"]` está imposto; aquele bug está fechado.
- **NÃO é o algoritmo.** HS256/HMAC-SHA256 é criptograficamente sólido — não foi "quebrado", foi **adivinhado pela chave**.
- **É SÓ a entropia do secret.** Só o token assinado com o secret **quebrado** (correto, porém fraco) passa. A falha inteira é a chave adivinhável.
- **Par explícito com o 05:** 05 = a fechadura não trancava (`alg:none`, verificação pulada); 13 = a fechadura tranca certo, mas a chave é fraca (post-it). No 05 você arranca a assinatura; aqui você a refaz, legítima, com a chave roubada.

### 10. Impact (honesto — sem overclaim)
- Escalação **VERTICAL** de privilégio: com o secret, o atacante forja **qualquer** token — vira admin, ou qualquer usuário, com qualquer claim. O impacto é **controle da autenticação** daquela app: *"você é quem disser que é, com o privilégio que quiser."* **NÃO é RCE.** Sem overclaim. Notar que é honestamente **mais alto** que a escalação **horizontal** dos átomos A01 desta fase (11/12 liam dado de outro usuário do mesmo nível; aqui você **vira admin**).

### 11. Why the fix works (porta 8113)
Repetir a cadeia contra o `fixed/`:
- Capture um JWT do `fixed/` e rode o **MESMO** john contra a **MESMA** wordlist → **NÃO acha** (o secret forte não está na lista; e brute-forçar 32 bytes aleatórios é inviável).
- O token forjado com o secret **antigo** (fraco) → **`401`** no `fixed/` (a assinatura não bate com o secret forte).
- Tudo mais **idêntico**: mesmos endpoints, mesma verificação, mesmo `algorithms=["HS256"]`. **A única mudança é o valor do `SECRET`.**
- **A lição do diff:** o fix **não foi uma linha de lógica** — foi `SECRET = "<fraco>"` → `SECRET = "<forte>"`. A segurança morava **inteiramente no valor**. (Forward pro DIFF pra o diff inédito completo e o contraste com o 05.)

**Sem seção de trilha browser** (API-only) e **sem** seção de exercícios/variações (CLAUDE.md §5 — o walkthrough termina onde a falha foi mostrada e o fix explicado).

---

## O container

`Dockerfile` **idêntico** entre vulnerable e fixed (como todos os átomos), e **idêntico ao do 12** (API-only → **sem `COPY templates`**). O 05 tinha `COPY templates`; o 13 **não** (é API-only). PyJWT instala via pip (sem `apt`). Esqueleto:

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

- **A `wordlist-sample.txt` NÃO é copiada pro container** (não há `COPY wordlist`): o crack roda no terminal do aluno, fora do container. A wordlist é asset do lab, na raiz do átomo.
- `docker-compose.yml`: `127.0.0.1:8013:5000` (vulnerable), `127.0.0.1:8113:5000` (fixed) — esqueleto de duas services do 05/12, sem `sysctls`. Bind **só** em `127.0.0.1`.

---

## Dependências extras

```
Flask==3.0.0
PyJWT==2.12.1
```

Idêntico ao `requirements.txt` do 05 (vulnerable e fixed iguais entre si e ao 05). `os`/`jwt` cobrem os imports. **Nada** de banco, templates, `apt`, ou outra lib. CLAUDE.md §3.6 respeitado. (A `wordlist-sample.txt` é asset, não dependência pip.)

---

## Theory primer

CLAUDE.md §5 exige um bloco de Theory primer linkando pra **PortSwigger Web Security Academy**, na página conceitual da vuln. O 05 (irmão JWT) já usa **[PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt)** — confirmado in-repo no README do 05. Weak/brute-forced secret é uma sub-classe dos ataques a JWT cobertos nessa página.

- **Candidato do bloco (confirmar por fetch na Fase 2):** [PortSwigger: JWT attacks](https://portswigger.net/web-security/jwt) — **a mesma página do 05**, por coerência entre os dois átomos JWT.
- **Fase 2:** verificar por fetch se o PortSwigger tem uma **sub-página/seção específica de weak secret / brute-forcing secrets** (ex.: dentro de `/web-security/jwt`, uma âncora tipo "brute-forcing secret keys"). **Se** existir uma página conceitual claramente mais específica pra secret fraco, **preferi-la**; **senão**, usar a página geral de JWT attacks (mesma do 05). **Não inventar a URL** — confirmar por fetch.
- **Texto do link:** preservar **"JWT attacks"** em inglês também no README PT (convenção CLAUDE.md §7 / 05).

---

## Decisões já tomadas, justificadas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Categoria (pasta / Web Top 10) | **A02 — Cryptographic Failures** | Secret de baixa entropia numa assinatura HMAC = falha de criptografia (chave fraca). Mesma pasta/categoria do 05 (confirmado no repo e no ROADMAP). |
| Nome / classe | **JWT weak signing secret (brute-forced)** | Segundo ataque a JWT do repo; a assinatura é sólida, o secret é que é fraco. |
| Posição no arco | Segundo ataque a JWT (após o 05) | 05 = `alg:none` (não verifica) → 13 = HS256 verificado, secret fraco. O contraste é a lição. **Não** antecipar um terceiro. |
| Lição-coração | **"Mecanismo correto é inútil com segredo fraco"** + sub-lição "assinado ≠ seguro" | A verificação HS256 está correta; a falha é 100% a entropia do secret. |
| Contraste com o 05 | **Explícito e obrigatório** ("fechadura não trancava" vs "tranca com a chave num post-it"; arranca vs refaz a assinatura) | O 05 é o irmão direto; o par é o núcleo pedagógico. (O 12 proibia citar o 05; aqui é o oposto — o frame exige.) |
| Escalação | **VERTICAL** (`role: user` → `role: admin` forjado) | Distingue do arco A01 (11/12 = horizontal). Forjar dá **poder**, não só outra identidade. |
| Tipo de átomo | **API-only** (sem HTML, sem templates, sem browser) | CLAUDE.md §3.3 lista "JWT (todas as variantes)" como naturalmente API-only; exploit token-cêntrico; molde do 12. (05 usou HTML; o 13 diverge — o contraste é sobre a vuln, não o layout.) |
| Feature | **API JWT** (`/login`, `/api/profile`, `/admin/users`), em memória | Habitat canônico de JWT. Sem banco (storage segue a superfície do bug). |
| `POST /login` | JSON `{"user"}` (default `alice`), **sem senha**, `role` sempre `user`, devolve JWT HS256 | Reusa o molde do 12. Login nunca emite `admin` → força a forja. Senha = fora de escopo. |
| `GET /api/profile` | Qualquer token válido → claims | Baseline ("seu token funciona") + ponto de captura do JWT. |
| `GET /admin/users` | Exige `role: admin` → dado fake; `user` → `403` | O alvo da escalação vertical. `403` (não `404`) — sem oráculo aqui (não é id sequencial como no 12). |
| O bug | **Um VALOR: `SECRET` fraco** (`sup3rs3cr3t` candidato) | Não é código ausente nem lógica errada. A verificação está correta. |
| Verificação | **`jwt.decode(token, SECRET, algorithms=["HS256"])`** nas duas versões | Idêntica ao `decode` FIXED do 05. `alg:none` rejeitado → **uma vuln só**. |
| Fix (único eixo) | **Trocar `SECRET` fraco → forte** (`secrets.token_urlsafe(32)`, literal fixo) | A segurança morava no valor. Diff de uma linha, e a linha é um dado. Não gerar por request (sobrevive a restart). |
| Diff | **Inédito: mesma lógica, VALOR diferente** | Terceiro tipo de diff do repo (≠ lógica-diferente dos A01/05; ≠ app.py-idêntico do par XSS). |
| Secret forte visível no `fixed/` | **Aceito; nota no DIFF** (modelo de ataque = token+wordlist, não ler o fonte; produção externalizaria — mencionável, não aplicado) | Isola o eixo da entropia; não vira átomo de secret-management. |
| Wordlist | **`wordlist-sample.txt` na raiz, ~1000 entradas, secret ~pos 980, NÃO rockyou** | Ver o john trabalhar; asset curado e pequeno; sem arquivo grande commitado. |
| rockyou | **Mencionar + fonte canônica** (Kali / distribuição do john), sem `wget`, sem redistribuir | Realidade sem apodrecer link nem redistribuir senhas vazadas. |
| Ferramenta de crack | **john** (usar/linkar `openwall/john`, não ensinar); **hashcat `-m 16500`** fallback | Ensina a vuln, não a ferramenta. |
| Forja | **One-liner Python + PyJWT** (`jwt.encode`) | Didático, sem dependência extra; transparente. Ancora a "reforja" (inverso do 05). |
| Biblioteca JWT | **PyJWT==2.12.1** (mesma do 05) | Padrão de fato; coerência com o irmão. Pin é coerência aqui (não behavior-critical como no 05). |
| Trilha | **Burp (captura+replay) + terminal (john crack + Python forja); SEM browser** | API-only; a exceção da §3.3 (ferramenta que o Burp não faz, como o browser no XSS) cobre o john na trilha principal. |
| Nº de beats | **Baseline + 4 steps + contraste + impacto + fix** | Baseline → capturar → quebrar → forjar → replay → "o que a vuln NÃO é" (crava o par com o 05). |
| Impacto | **Escalação vertical / controle da auth.** Não RCE. | Honesto, mais alto que o horizontal do 11/12, sem overclaim. |
| Theory primer | **PortSwigger JWT attacks (mesma do 05)**; checar seção de weak secret na Fase 2 | CLAUDE.md manda PortSwigger; coerência com o 05. URL confirmada por fetch na Fase 2. |
| Erros | **`abort()` cru**; status code é o sinal | Consistente com 03/05/10/11/12. Corpo não reflete input (sem XSS). |
| `app.py` vulnerable × fixed | **Diferem só na constante `SECRET`** | Lógica byte-idêntica. O diff inédito. |
| Dockerfile / compose | Esqueleto do 12 (API-only, sem `COPY templates`); portas 8013/8113 | Idêntico entre versões; bind só `127.0.0.1`. |

---

## Riscos técnicos a validar na Fase 2 (checklist — NÃO validar agora)

Itens 1–9 são os que o mantenedor pediu explicitamente; 10–12 são higiene técnica desta spec. Todos são validação **na geração** (CLAUDE.md §11), não decisões pendentes.

1. **`POST /login`** devolve um JWT **HS256 válido** com `{"sub": "...", "role": "user"}`; o secret usado é o **fraco**. Decodificar o JWT confirma as claims e `alg: HS256`.
2. **Verificação correta:** token com **assinatura inválida** (secret errado / caractere trocado) → **`401`**; token **`alg:none`** (o exploit do 05) → **REJEITADO** (`401`), provando que a única vuln é o secret, **não** o alg. `GET /api/profile` e `GET /admin/users` ambos exigem token válido (sem/ruim → `401`).
3. **Baseline:** token legítimo (`role: user`) acessa `GET /api/profile` → `200`; `GET /admin/users` com `role: user` → **`403`**.
4. **CRACK REAL (o item central):** rodar o **john de verdade** contra o JWT gerado + a wordlist do átomo, e **CONFIRMAR** que acha o secret. **CAPTURAR o OUTPUT REAL** (com tentativas visíveis) pro walkthrough. Se não houver john, **TENTAR hashcat** (`-m 16500`); se **nenhum dos dois** estiver disponível ou não der pra rodar, **PARAR e avisar o mantenedor** — **NÃO inventar** o output. Confirmar que o secret está **~posição 980** e que o john mostra progresso antes de achar (se sair instantâneo, ajustar posição/tamanho e documentar).
5. **FORJA:** com o secret quebrado, forjar um JWT `role: admin` (one-liner Python + PyJWT) e confirmar `GET /admin/users` com o token forjado → **`200`** (escalação vertical confirmada). Capturar o snippet real e o request/response real.
6. **Fixed:** gerar o secret forte com `secrets.token_urlsafe(32)` (literal fixo no `fixed/app.py`). Rodar o **MESMO** john contra um JWT do `fixed/` + a wordlist → **NÃO acha** (confirmar a falha). Token forjado com o secret **antigo** (fraco) → **`401`** no `fixed/` (assinatura não bate). Endpoints e verificação idênticos.
7. **`app.py` DIFERE SÓ na constante `SECRET`** (o valor). Lógica, algoritmo, endpoints, verificação, helpers, imports — **IDÊNTICOS** entre versões. **Confirmar por `diff`** que só a linha do `SECRET` muda.
8. **A wordlist** tem **~1000 entradas**, o secret está **~posição 980**, e é uma lista **curada** (**NÃO** a rockyou). **Nenhum arquivo grande commitado.** Confirmar (se a rockyou estiver disponível) que o secret escolhido **está na rockyou também** (`grep -x`); se não, cair pro fallback (`changeme123`/`secret123`/`password123`) e ajustar.
9. **Link do john** (`openwall/john` no GitHub) confirmado por **fetch**. **Primer JWT do PortSwigger** confirmado por fetch (mesma URL do 05; checar se há seção específica de weak/brute-forced secret).
10. **Uma vuln só:** `algorithms=["HS256"]` imposto; nenhum secret serializado em resposta; `/admin/users` devolve só dado fake benigno; sem store de token. Nada empilhado sobre o secret fraco.
11. **API-only confirmado:** **sem** diretório `templates/`, Dockerfile **sem** `COPY templates`, `app.py` **sem** `render_template`; todas as respostas de sucesso em `application/json`. Wordlist **não** copiada pro container.
12. **`PyJWT==2.12.1`** (mesma do 05) instala e `jwt.encode`/`jwt.decode` HS256 se comportam como especificado; `jwt.encode` retorna `str`. Portas `8013`/`8113` bindando **só** em `127.0.0.1`.

**Bloqueante remanescente:** nenhum. Spec para revisão do mantenedor. Pendências de Fase 2 (não bloqueantes agora): confirmar o secret primário (`sup3rs3cr3t`) craqueia + está na rockyou (senão fallback); capturar o output real do john; confirmar a URL do primer e do john por fetch; gerar o secret forte literal.

---

## Notas específicas pro Claude Code

- **Princípio guia:** este átomo é o **segundo ataque a JWT do repo** e o irmão direto do **05**. Cada beat do walkthrough deve poder ser lido com o 05 aberto ao lado; o par **"05 = a fechadura não trancava (`alg:none`) / 13 = a fechadura tranca mas a chave é fraca (secret quebrável)"** tem que estar visível na abertura, no passo de contraste e no fechamento. **Abrir e fechar** na lição-coração: mecanismo correto + segredo fraco = inútil; "assinado ≠ seguro".
- **Leitura obrigatória antes de gerar (CLAUDE.md §10.5):** `jwt-none-alg` (05) **inteiro** (irmão JWT — reusar vocabulário, claims `sub`/`role`, forma de README/WALKTHROUGH/DIFF; o `decode` do 13 é o `decode` FIXED do 05; citar a §5 do 05 que já nomeou "weak brute-forceable secrets") **e** `bola-rest` (12) **inteiro** (molde API-only — `POST /login` sem senha, JSON, WALKTHROUGH sem browser, README com "API only" e "Authentication, simulated"). Ler também esta spec e o `sqli-union-basic` (referência canônica, CLAUDE.md §10.5).
- **Átomo stateless, sem banco, sem templates, API-only** (como o 12): dados em memória, JWT stateless (sem store de token). **Sem** `sqlite3`, `init_db()`, `render_template`, `templates/`.
- **`app.py` DIFERE entre vulnerable e fixed SÓ na constante `SECRET`** — validar por `diff` que **nenhuma linha de lógica** muda. `Dockerfile` (sem `COPY templates`) e `requirements.txt` (Flask + PyJWT==2.12.1) idênticos entre as versões.
- **O ponto técnico frágil é o crack real (risco #4).** Rodar john/hashcat de verdade, capturar output real, confirmar a posição ~980. **Se não der pra rodar nenhum cracker, PARAR e avisar — NÃO inventar output.**
- **Uma vuln só:** `algorithms=["HS256"]` **obrigatório**; `alg:none` deve dar `401` (senão empilha a vuln do 05). Nenhum secret vazado; nenhuma segunda falha.
- **A ferramenta john é USADA, não ensinada:** passo a passo do ataque sim; tutorial de instalação/flags não. Linkar `openwall/john`. rockyou: mencionar + fonte canônica, **sem `wget`, sem redistribuir**.
- **A forja é o inverso do 05:** você **refaz** a assinatura (genuína, com o secret quebrado), não a **arranca**. Cravar isso.
- **Impacto honesto:** escalação **VERTICAL** / controle da autenticação; **não** RCE. Sem overclaim. Notar que é mais alto que o horizontal do 11/12.
- **Política de referência cross-átomo:** OK e **obrigatório** referenciar `jwt-none-alg` (05) explicitamente (o contraste é a lição). OK citar **de leve** os A01 desta fase (11/12) pelo eixo horizontal-vs-vertical, e o 11 pelo paralelo "UUID ≠ imprevisível" / "assinado ≠ seguro". **PROIBIDO** referenciar/foreshadowar **qualquer** átomo não publicado, incluindo o **terceiro átomo JWT** (não nomear, não antecipar). Ao falar da relação JWT, enquadrar como **"05 e 13 são dois ataques a JWT"** — **sem** prometer um terceiro no conteúdo publicado. **Observação (débito preexistente do 05 — ver a "Nota de planning" no topo desta spec):** o WALKTHROUGH do 05 (§5) já foreshadowa "atoms 13 and 14" por número; isso é um débito do 05, **não** um convite a reciprocar — o 13 **não** deve foreshadowar o 14. Key-confusion só pode aparecer como **conceito** (do jeito que o 05 já o mencionou genericamente), nunca como átomo prometido.
- **Bilíngue PT+EN no mesmo commit** (README, WALKTHROUGH, DIFF), padrão v0.1.0. H1 idêntico em EN e PT (forma `jwt-weak-secret — JWT weak signing secret (brute-forced)`, texto exato confirmável na Fase 2). Termos técnicos (JWT, HS256, HMAC, secret, brute force, wordlist, payload, sign/verify, claim, forge, `Bearer`) **não** se traduzem no PT.
- **Theory primer obrigatório** no topo do `README.md` e `README.pt-BR.md` (Fase 2): bloco PortSwigger JWT attacks (mesma URL do 05, texto `JWT attacks` preservado em inglês no PT). **Confirmar a URL por fetch na Fase 2** (e checar se há seção específica de weak secret melhor).
- **`wordlist-sample.txt`** na raiz do átomo (asset do lab, **não** copiada pro container). ~1000 entradas curadas, secret ~pos 980, **não** rockyou, **sem arquivo grande**.
- **CHANGELOG.md (Fase 2, NÃO agora):** em `[Unreleased] / Added`: `` Added atom 13: `jwt-weak-secret` — JWT weak signing secret, brute-forced (A02 Cryptographic Failures). `` (padrão das linhas dos átomos 06–12).
- **ROADMAP.md:** marcar o átomo 13 como `[x]` **só na geração+validação** (proposta ao mantenedor, CLAUDE.md §10.4). **Não** alterar ROADMAP nesta fase de spec.
- **Validar manualmente na Fase 2** (CLAUDE.md §11): itens 1–12 do checklist; reproduzir baseline → capturar → **crack real (john)** → forja → replay (`200` admin) → contraste (assinatura errada/`alg:none` → `401`) → fixed (john falha, token antigo → `401`). Validar via `docker exec` + `python http.client` de dentro do container se as portas host não forem alcançáveis do sandbox (o crack roda no host/terminal, fora do container).
- **Portas:** `127.0.0.1:8013` (vulnerable), `127.0.0.1:8113` (fixed). Bind **só** em `127.0.0.1`.
- Se houver dúvida sobre o comando exato do john/hashcat, a URL do primer/john, ou o secret primário não craquear/não estar na rockyou, **perguntar/ajustar e documentar** antes de inventar (CLAUDE.md).
